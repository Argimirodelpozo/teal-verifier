#!/usr/bin/env python3
"""
Generate a human-readable stack depth report for a TEAL program.

Runs the stackDepthReport.ql query against a CodeQL database, then
merges the results with the original source to produce an annotated
line-by-line report showing possible stack depths.

Usage:
    python stack-depth-report.py -d <database> [-s <source-dir>] [-o <output>]

Examples:
    python codeql-analysis-tools/stack-depth-report.py -d test-projects/loop-test-db
    python codeql-analysis-tools/stack-depth-report.py -d test-projects/loop-test-db -o report.txt
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


QUERY_REL = "teal/ql/lib/codeql/stackDepthReport.ql"


class NodeInfo(NamedTuple):
    opcode: str
    depth_before: int
    delta: int
    col: int


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
                # Map by filename (most common match)
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

        # Group by line: collect all nodes and their depths
        # line -> list of NodeInfo
        by_line: dict[int, list[NodeInfo]] = defaultdict(list)
        for row in file_rows:
            line = int(row["line"])
            by_line[line].append(NodeInfo(
                opcode=row["opcode"],
                depth_before=int(row["depth_before"]),
                delta=int(row["delta"]),
                col=int(row["col"]),
            ))

        # For each line, compute the aggregate depth range (before) and after
        # A line may have multiple opcodes; we show the range across all of them
        line_summary: dict[int, tuple[set[int], set[int], list[str]]] = {}
        for line, nodes in sorted(by_line.items()):
            depths_before: set[int] = set()
            depths_after: set[int] = set()
            opcodes: list[str] = []
            seen_opcodes: set[str] = set()

            for n in nodes:
                depths_before.add(n.depth_before)
                depths_after.add(n.depth_before + n.delta)
                if n.opcode not in seen_opcodes:
                    opcodes.append(n.opcode)
                    seen_opcodes.add(n.opcode)

            line_summary[line] = (depths_before, depths_after, opcodes)

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
            f"{'Line':>4}  {'Before':>12}  {'After':>12}  {'Source'}"
        )
        output_parts.append(f"{'─' * 4}  {'─' * 12}  {'─' * 12}  {'─' * 40}")

        for line_no in range(1, max_line + 1):
            src = source_lines.get(line_no, "")

            if line_no in line_summary:
                depths_before, depths_after, opcodes = line_summary[line_no]
                before_str = format_depth_set(depths_before)
                after_str = format_depth_set(depths_after)
            else:
                before_str = ""
                after_str = ""

            output_parts.append(
                f"{line_no:>4}  {before_str:>12}  {after_str:>12}  {src}"
            )

        output_parts.append("")

    # Append a legend
    output_parts.append("Legend:")
    output_parts.append("  Before = possible stack depths before the line executes")
    output_parts.append("  After  = possible stack depths after the line executes")
    output_parts.append("  {a,b}  = multiple possible depths (inconsistent paths)")
    output_parts.append("")

    return "\n".join(output_parts)


def format_depth_set(depths: set[int]) -> str:
    """Format a set of depths as a compact string."""
    if not depths:
        return ""
    sorted_depths = sorted(depths)
    if len(sorted_depths) == 1:
        return str(sorted_depths[0])
    return "{" + ",".join(str(d) for d in sorted_depths) + "}"


def _path(p: str) -> Path:
    return Path(p).expanduser().resolve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="stack-depth-report",
        description="Generate a stack depth report for a TEAL program.",
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
        help="Path to the .ql query file. Defaults to stackDepthReport.ql.",
    )

    args = parser.parse_args(argv)

    # Resolve query path
    repo_root = Path(__file__).resolve().parent.parent
    query = args.query or (repo_root / QUERY_REL)
    if not query.is_file():
        print(f"Query not found: {query}", file=sys.stderr)
        return 1

    print(f"Running stack depth query on {args.database.name}...", file=sys.stderr)

    try:
        rows = run_query(args.database, query)
    except subprocess.CalledProcessError as e:
        print(f"Query failed:\n{e.stderr}", file=sys.stderr)
        return 1

    if not rows:
        print("No results (empty program or no reachable opcodes).", file=sys.stderr)
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
