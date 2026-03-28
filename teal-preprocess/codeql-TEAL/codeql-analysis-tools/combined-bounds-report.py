#!/usr/bin/env python3
"""
Generate a combined integer + byte array bounds report for a TEAL program.

Runs the combinedBoundsReport.ql query against a CodeQL database, then
merges both kinds of bounds into a single annotated line-by-line view
with separate columns for int bounds and byte bounds.

Usage:
    python combined-bounds-report.py -d <database> [-s <source-dir>] [-o <output>]

Examples:
    python codeql-analysis-tools/combined-bounds-report.py -d test-projects/xgov-db
    python codeql-analysis-tools/combined-bounds-report.py -d test-projects/xgov-db -o report.txt
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import NamedTuple


QUERY_REL = "teal/ql/lib/codeql/combinedBoundsReport.ql"


class BoundsEntry(NamedTuple):
    opcode: str
    kind: str
    lo: int
    hi: int
    value: str
    col: int


def format_int_bound(hi: int) -> str:
    return "MAX" if hi == -1 else str(hi)


def format_bytes_bound(hi: int) -> str:
    return "MAX_BYTES" if hi == -1 else str(hi)


def format_int_range(lo: int, hi: int) -> str:
    if lo == hi:
        return f"={lo}"
    return f"[{lo}, {format_int_bound(hi)}]"


def format_bytes_range(lo: int, hi: int) -> str:
    if lo == hi:
        return f"={lo}B"
    return f"[{lo}, {format_bytes_bound(hi)}]B"


def _truncate(s: str, max_len: int = 16) -> str:
    if not s or len(s) <= max_len:
        return s
    return s[:max_len - 2] + ".."


def run_query(database: Path, query: Path, codeql: str = "codeql") -> list[dict]:
    """Run a CodeQL query and return parsed CSV rows."""
    with tempfile.TemporaryDirectory() as tmp:
        bqrs = Path(tmp) / "result.bqrs"
        csv_path = Path(tmp) / "result.csv"

        subprocess.run(
            [codeql, "query", "run", "--database", str(database),
             str(query), "--output", str(bqrs)],
            check=True, capture_output=True, text=True,
        )
        subprocess.run(
            [codeql, "bqrs", "decode", "--format=csv",
             "--output", str(csv_path), str(bqrs)],
            check=True, capture_output=True, text=True,
        )

        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            return list(reader)


def find_source_files(database: Path, source_dir: Path | None) -> dict[str, Path]:
    """Map relative paths from query results to actual source files."""
    if source_dir is not None:
        return _scan_directory(source_dir)

    src_archive = database / "src"
    if src_archive.is_dir():
        return _scan_directory(src_archive)

    src_zip = database / "src.zip"
    if src_zip.is_file():
        return _extract_from_zip(src_zip)

    return {}


def _scan_directory(source_dir: Path) -> dict[str, Path]:
    result = {}
    for teal_file in source_dir.rglob("*.teal"):
        result[str(teal_file.relative_to(source_dir))] = teal_file
        result[teal_file.name] = teal_file
    return result


def _extract_from_zip(src_zip: Path) -> dict[str, Path]:
    extract_dir = Path(tempfile.mkdtemp(prefix="codeql-src-"))
    result = {}
    with zipfile.ZipFile(src_zip) as zf:
        for name in zf.namelist():
            if name.endswith(".teal"):
                zf.extract(name, extract_dir)
                extracted = extract_dir / name
                result[Path(name).name] = extracted
                result[name] = extracted
    return result


def read_source_lines(path: Path) -> dict[int, str]:
    lines = {}
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            lines[i] = line.rstrip("\n")
    return lines


def build_report(rows: list[dict], source_map: dict[str, Path]) -> str:
    """Build the merged annotated report from query results and source files."""
    by_file: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_file[row["file"]].append(row)

    output_parts = []

    for rel_path, file_rows in sorted(by_file.items()):
        source_lines: dict[int, str] = {}
        resolved = source_map.get(rel_path) or source_map.get(Path(rel_path).name)
        if resolved and resolved.is_file():
            source_lines = read_source_lines(resolved)

        # Group by line, collecting both int and bytes entries
        by_line: dict[int, list[BoundsEntry]] = defaultdict(list)
        for row in file_rows:
            line = int(row["line"])
            by_line[line].append(BoundsEntry(
                opcode=row["opcode"],
                kind=row["kind"],
                lo=int(row["lo"]),
                hi=int(row["hi"]),
                value=row.get("value", ""),
                col=int(row["col"]),
            ))

        max_line = max(
            max(source_lines.keys()) if source_lines else 0,
            max(by_line.keys()) if by_line else 0,
        )

        output_parts.append(f"{'=' * 90}")
        output_parts.append(f"File: {rel_path}")
        output_parts.append(f"{'=' * 90}")
        output_parts.append("")

        output_parts.append(
            f"{'Line':>4}   {'Int Bounds':>18}   {'Byte Bounds':>18}   "
            f"{'Value':>16}   {'Source'}"
        )
        output_parts.append(
            f"{'~' * 4}   {'~' * 18}   {'~' * 18}   "
            f"{'~' * 16}   {'~' * 40}"
        )

        for line_no in range(1, max_line + 1):
            src = source_lines.get(line_no, "")

            if line_no in by_line:
                entries = by_line[line_no]

                # Separate int and bytes entries
                int_entries = [e for e in entries if e.kind == "int"]
                bytes_entries = [e for e in entries if e.kind == "bytes"]

                # Format int bounds column
                if len(int_entries) == 0:
                    int_str = ""
                elif len(int_entries) == 1:
                    int_str = format_int_range(int_entries[0].lo, int_entries[0].hi)
                else:
                    parts = []
                    for e in sorted(int_entries, key=lambda x: x.col):
                        parts.append(f"{e.opcode}:{format_int_range(e.lo, e.hi)}")
                    int_str = " ".join(parts)

                # Format bytes bounds column
                if len(bytes_entries) == 0:
                    bytes_str = ""
                elif len(bytes_entries) == 1:
                    bytes_str = format_bytes_range(bytes_entries[0].lo, bytes_entries[0].hi)
                else:
                    parts = []
                    for e in sorted(bytes_entries, key=lambda x: x.col):
                        parts.append(f"{e.opcode}:{format_bytes_range(e.lo, e.hi)}")
                    bytes_str = " ".join(parts)

                # Collect values from all entries
                values = [e.value for e in entries if e.value]
                value_str = _truncate(" ".join(values)) if values else ""
            else:
                int_str = ""
                bytes_str = ""
                value_str = ""

            output_parts.append(
                f"{line_no:>4}   {int_str:>18}   {bytes_str:>18}   "
                f"{value_str:>16}   {src}"
            )

        output_parts.append("")

    # Summary statistics
    total = len(rows)
    int_total = sum(1 for r in rows if r["kind"] == "int")
    bytes_total = sum(1 for r in rows if r["kind"] == "bytes")
    int_exact = sum(1 for r in rows if r["kind"] == "int" and int(r["lo"]) == int(r["hi"]))
    bytes_exact = sum(1 for r in rows if r["kind"] == "bytes" and int(r["lo"]) == int(r["hi"]))
    int_unbounded = sum(1 for r in rows if r["kind"] == "int" and int(r["hi"]) == -1)
    bytes_unbounded = sum(1 for r in rows if r["kind"] == "bytes" and int(r["hi"]) == -1)
    with_value = sum(1 for r in rows if r.get("value", ""))
    # Count lines that have both int and bytes bounds
    lines_with_both = 0
    for file_rows_list in by_file.values():
        by_line_temp: dict[int, set[str]] = defaultdict(set)
        for row in file_rows_list:
            by_line_temp[int(row["line"])].add(row["kind"])
        lines_with_both += sum(1 for kinds in by_line_temp.values() if "int" in kinds and "bytes" in kinds)

    output_parts.append("Summary:")
    output_parts.append(f"  Total entries:              {total}")
    output_parts.append(f"  Integer bounds:             {int_total} ({int_exact} exact, {int_unbounded} unbounded)")
    output_parts.append(f"  Byte array bounds:          {bytes_total} ({bytes_exact} exact, {bytes_unbounded} unbounded)")
    output_parts.append(f"  Lines with both kinds:      {lines_with_both}")
    output_parts.append(f"  Entries with known value:   {with_value}")
    output_parts.append("")
    output_parts.append("Legend:")
    output_parts.append("  =N          exact integer value N")
    output_parts.append("  [lo, hi]    integer value in range [lo, hi]")
    output_parts.append("  MAX         upper integer bound unknown (2^64 - 1)")
    output_parts.append("  =NB         exact byte array length N bytes")
    output_parts.append("  [lo, hi]B   byte array length in range [lo, hi] bytes")
    output_parts.append("  MAX_BYTES   upper byte length unknown (up to 4096)")
    output_parts.append("")

    return "\n".join(output_parts)


def _path(p: str) -> Path:
    return Path(p).expanduser().resolve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="combined-bounds-report",
        description="Generate a combined integer + byte array bounds report for a TEAL program.",
    )
    parser.add_argument(
        "-d", "--database", type=_path, required=True,
        help="Path to the CodeQL database directory.",
    )
    parser.add_argument(
        "-s", "--source-dir", type=_path, default=None,
        help="Path to the TEAL source directory. If omitted, uses the database's source archive.",
    )
    parser.add_argument(
        "-o", "--out", type=_path, default=None,
        help="Output file path. If omitted, prints to stdout.",
    )
    parser.add_argument(
        "-q", "--query", type=_path, default=None,
        help="Path to the .ql query file. Defaults to combinedBoundsReport.ql.",
    )

    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parent.parent
    query = args.query or (repo_root / QUERY_REL)
    if not query.is_file():
        print(f"Query not found: {query}", file=sys.stderr)
        return 1

    print(f"Running combined bounds query on {args.database.name}...", file=sys.stderr)

    try:
        rows = run_query(args.database, query)
    except subprocess.CalledProcessError as e:
        print(f"Query failed:\n{e.stderr}", file=sys.stderr)
        return 1

    if not rows:
        print("No results (empty program or no opcodes with bounds).", file=sys.stderr)
        return 0

    source_map = find_source_files(args.database, args.source_dir)
    report = build_report(rows, source_map)

    if args.out:
        args.out.write_text(report, encoding="utf-8")
        print(f"Report written to {args.out}", file=sys.stderr)
    else:
        print(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
