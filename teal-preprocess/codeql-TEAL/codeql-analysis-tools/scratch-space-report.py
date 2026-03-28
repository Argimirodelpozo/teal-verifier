#!/usr/bin/env python3
"""
Generate a human-readable scratch space inference report for a TEAL program.

Runs the scratchSpaceReport.ql query against a CodeQL database, then
merges the results with the original source to produce an annotated
line-by-line report showing inferred types, bounds, values, and origins
for every store/load opcode.

Usage:
    python scratch-space-report.py -d <database> [-s <source-dir>] [-o <output>]

Examples:
    python codeql-analysis-tools/scratch-space-report.py -d test-projects/xgov-db
    python codeql-analysis-tools/scratch-space-report.py -d test-projects/xgov-db -o report.txt
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


QUERY_REL = "teal/ql/lib/codeql/scratchSpaceReport.ql"


class ScratchInfo(NamedTuple):
    opcode: str
    slot: int
    type: str
    lo: int
    hi: int
    value: str
    origin: str
    col: int


def format_int_bound(hi: int) -> str:
    return "MAX_UINT64" if hi == -1 else str(hi)


def format_bytes_bound(hi: int) -> str:
    return "MAX_BYTES" if hi == -1 else str(hi)


def format_range(type_: str, lo: int, hi: int) -> str:
    if type_ == "int":
        if lo == hi:
            return f"={lo}"
        return f"[{lo}, {format_int_bound(hi)}]"
    else:
        if lo == hi:
            return f"={lo}B"
        return f"[{lo}, {format_bytes_bound(hi)}]B"


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


def _truncate(s: str, max_len: int = 18) -> str:
    if not s or len(s) <= max_len:
        return s
    return s[:max_len - 2] + ".."


def build_report(rows: list[dict], source_map: dict[str, Path]) -> str:
    """Build the annotated report from query results and source files."""
    by_file: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_file[row["file"]].append(row)

    output_parts = []

    for rel_path, file_rows in sorted(by_file.items()):
        source_lines: dict[int, str] = {}
        resolved = source_map.get(rel_path) or source_map.get(Path(rel_path).name)
        if resolved and resolved.is_file():
            source_lines = read_source_lines(resolved)

        by_line: dict[int, list[ScratchInfo]] = defaultdict(list)
        for row in file_rows:
            line = int(row["line"])
            by_line[line].append(ScratchInfo(
                opcode=row["opcode"],
                slot=int(row["slot"]),
                type=row["type"],
                lo=int(row["lo"]),
                hi=int(row["hi"]),
                value=row.get("value", ""),
                origin=row.get("origin", ""),
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
            f"{'Line':>4}  {'Op':>5}  {'Slot':>4}  {'Type':>5}  "
            f"{'Bounds':>20}  {'Value':>18}  {'Origin':>18}  {'Source'}"
        )
        output_parts.append(
            f"{'~' * 4}  {'~' * 5}  {'~' * 4}  {'~' * 5}  "
            f"{'~' * 20}  {'~' * 18}  {'~' * 18}  {'~' * 30}"
        )

        for line_no in range(1, max_line + 1):
            src = source_lines.get(line_no, "")

            if line_no in by_line:
                entries = sorted(by_line[line_no], key=lambda x: (x.col, x.type))
                for i, e in enumerate(entries):
                    bounds_str = format_range(e.type, e.lo, e.hi)
                    val_str = _truncate(e.value)
                    origin_str = _truncate(e.origin)
                    # Only show source on the first entry for this line
                    src_str = src if i == 0 else ""
                    output_parts.append(
                        f"{line_no:>4}  {e.opcode:>5}  {e.slot:>4}  {e.type:>5}  "
                        f"{bounds_str:>20}  {val_str:>18}  {origin_str:>18}  {src_str}"
                    )
            else:
                output_parts.append(
                    f"{line_no:>4}  {'':>5}  {'':>4}  {'':>5}  "
                    f"{'':>20}  {'':>18}  {'':>18}  {src}"
                )

        output_parts.append("")

    # Summary
    total = len(rows)
    stores = sum(1 for r in rows if r["opcode"] == "store")
    loads = sum(1 for r in rows if r["opcode"] == "load")
    int_rows = sum(1 for r in rows if r["type"] == "int")
    bytes_rows = sum(1 for r in rows if r["type"] == "bytes")
    slots = len(set(int(r["slot"]) for r in rows))

    output_parts.append("Summary:")
    output_parts.append(f"  Total entries:     {total}")
    output_parts.append(f"  Store opcodes:     {stores}")
    output_parts.append(f"  Load opcodes:      {loads}")
    output_parts.append(f"  Integer type:      {int_rows}")
    output_parts.append(f"  Bytes type:        {bytes_rows}")
    output_parts.append(f"  Distinct slots:    {slots}")
    output_parts.append("")
    output_parts.append("Legend:")
    output_parts.append("  =N          exact integer value N")
    output_parts.append("  [lo, hi]    integer value in range [lo, hi]")
    output_parts.append("  =NB         exact byte array length N")
    output_parts.append("  [lo, hi]B   byte array length in range [lo, hi]")
    output_parts.append("  MAX_UINT64  upper integer bound unknown")
    output_parts.append("  MAX_BYTES   upper byte length unknown (up to 4096)")
    output_parts.append("")

    return "\n".join(output_parts)


def _path(p: str) -> Path:
    return Path(p).expanduser().resolve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scratch-space-report",
        description="Generate a scratch space inference report for a TEAL program.",
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
        help="Path to the .ql query file. Defaults to scratchSpaceReport.ql.",
    )

    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parent.parent
    query = args.query or (repo_root / QUERY_REL)
    if not query.is_file():
        print(f"Query not found: {query}", file=sys.stderr)
        return 1

    print(f"Running scratch space query on {args.database.name}...", file=sys.stderr)

    try:
        rows = run_query(args.database, query)
    except subprocess.CalledProcessError as e:
        print(f"Query failed:\n{e.stderr}", file=sys.stderr)
        return 1

    if not rows:
        print("No results (no store/load opcodes with inferred info).", file=sys.stderr)
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
