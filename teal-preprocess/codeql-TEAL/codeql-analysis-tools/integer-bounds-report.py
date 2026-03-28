#!/usr/bin/env python3
"""
Generate a human-readable integer bounds report for a TEAL program.

Runs the integerBoundsReport.ql query against a CodeQL database, then
merges the results with the original source to produce an annotated
line-by-line report showing computed integer bounds.

Usage:
    python integer-bounds-report.py -d <database> [-s <source-dir>] [-o <output>]

Examples:
    python codeql-analysis-tools/integer-bounds-report.py -d test-projects/loop-test-db
    python codeql-analysis-tools/integer-bounds-report.py -d test-projects/xgov-db -o report.txt
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


QUERY_REL = "teal/ql/lib/codeql/integerBoundsReport.ql"


class BoundsInfo(NamedTuple):
    opcode: str
    lo: int
    hi: int
    col: int


def format_bound(hi: int) -> str:
    """Format a bound value, replacing -1 with MAX_UINT64."""
    return "MAX_UINT64" if hi == -1 else str(hi)


def format_range(lo: int, hi: int) -> str:
    """Format a [lo, hi] range for display."""
    if lo == hi:
        return f"={lo}"
    return f"[{lo}, {format_bound(hi)}]"


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

    # Try extracted src/ directory
    src_archive = database / "src"
    if src_archive.is_dir():
        return _scan_directory(src_archive)

    # Try src.zip (CodeQL's default source archive format)
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
    """Extract .teal files from a CodeQL src.zip to a temp directory and return mappings."""
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
    """Read a source file and return {line_number: line_text}."""
    lines = {}
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            lines[i] = line.rstrip("\n")
    return lines


def build_report(rows: list[dict], source_map: dict[str, Path]) -> str:
    """Build the annotated report from query results and source files."""
    # Group rows by file
    by_file: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_file[row["file"]].append(row)

    output_parts = []

    for rel_path, file_rows in sorted(by_file.items()):
        # Load source
        source_lines: dict[int, str] = {}
        resolved = source_map.get(rel_path) or source_map.get(Path(rel_path).name)
        if resolved and resolved.is_file():
            source_lines = read_source_lines(resolved)

        # Group by line
        by_line: dict[int, list[BoundsInfo]] = defaultdict(list)
        for row in file_rows:
            line = int(row["line"])
            by_line[line].append(BoundsInfo(
                opcode=row["opcode"],
                lo=int(row["lo"]),
                hi=int(row["hi"]),
                col=int(row["col"]),
            ))

        # Determine line range
        max_line = max(
            max(source_lines.keys()) if source_lines else 0,
            max(by_line.keys()) if by_line else 0,
        )

        # Build output
        output_parts.append(f"{'=' * 80}")
        output_parts.append(f"File: {rel_path}")
        output_parts.append(f"{'=' * 80}")
        output_parts.append("")

        # Header
        output_parts.append(
            f"{'Line':>4}  {'Bounds':>24}  {'Source'}"
        )
        output_parts.append(f"{'─' * 4}  {'─' * 24}  {'─' * 40}")

        for line_no in range(1, max_line + 1):
            src = source_lines.get(line_no, "")

            if line_no in by_line:
                nodes = by_line[line_no]
                # If multiple opcodes on same line, show all
                if len(nodes) == 1:
                    bounds_str = format_range(nodes[0].lo, nodes[0].hi)
                else:
                    parts = []
                    for n in sorted(nodes, key=lambda x: x.col):
                        parts.append(f"{n.opcode}:{format_range(n.lo, n.hi)}")
                    bounds_str = " ".join(parts)
            else:
                bounds_str = ""

            output_parts.append(
                f"{line_no:>4}  {bounds_str:>24}  {src}"
            )

        output_parts.append("")

    # Summary statistics
    total = len(rows)
    exact = sum(1 for r in rows if int(r["lo"]) == int(r["hi"]))
    bounded = sum(1 for r in rows if int(r["hi"]) != -1 and int(r["lo"]) != int(r["hi"]))
    unbounded = sum(1 for r in rows if int(r["hi"]) == -1)

    output_parts.append("Summary:")
    output_parts.append(f"  Total opcodes with bounds: {total}")
    output_parts.append(f"  Exact (lo=hi):             {exact}")
    output_parts.append(f"  Bounded range:             {bounded}")
    output_parts.append(f"  Unbounded (hi=MAX):        {unbounded}")
    output_parts.append("")
    output_parts.append("Legend:")
    output_parts.append("  =N          exact value N")
    output_parts.append("  [lo, hi]    value in range [lo, hi]")
    output_parts.append("  MAX_UINT64  upper bound unknown (2^64 - 1)")
    output_parts.append("")

    return "\n".join(output_parts)


def _path(p: str) -> Path:
    return Path(p).expanduser().resolve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="integer-bounds-report",
        description="Generate an integer bounds report for a TEAL program.",
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
        help="Path to the .ql query file. Defaults to integerBoundsReport.ql.",
    )

    args = parser.parse_args(argv)

    # Resolve query path
    repo_root = Path(__file__).resolve().parent.parent
    query = args.query or (repo_root / QUERY_REL)
    if not query.is_file():
        print(f"Query not found: {query}", file=sys.stderr)
        return 1

    print(f"Running integer bounds query on {args.database.name}...", file=sys.stderr)

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
