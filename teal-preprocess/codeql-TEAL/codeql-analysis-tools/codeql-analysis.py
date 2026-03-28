from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def run_codeql_query(
    *,
    database: Path,
    query: Path,
    output_csv: Path,
    tmp_bqrs_path: Path,
    codeql: str = "codeql",
) -> None:
    """
    Runs:
      codeql query run --database <db> <query> --output <tmp_bqrs_path>
      codeql bqrs decode --format=csv --output <output_csv> <tmp_bqrs_path>
    """
    tmp_bqrs_path.parent.mkdir(parents=True, exist_ok=True)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    query_cmd = [
        codeql,
        "query",
        "run",
        "--database",
        str(database),
        str(query),
        "--output",
        str(tmp_bqrs_path),
    ]

    bqrs_decode_cmd = [
        codeql,
        "bqrs",
        "decode",
        "--format=csv",
        "--output",
        str(output_csv),
        str(tmp_bqrs_path),
    ]

    try:
        subprocess.run(query_cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print("CodeQL query run failed", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        raise

    try:
        subprocess.run(bqrs_decode_cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print("CodeQL bqrs decode failed", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        raise


def csv_to_json(csv_path: Path) -> dict[str, Any]:
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        return {"columns": [], "rows": []}

    columns = rows[0]
    data_rows = rows[1:]

    return {
        "columns": columns,
        "rows": [
            {columns[i]: (r[i] if i < len(r) else None) for i in range(len(columns))}
            for r in data_rows
        ],
    }


def analyze_to_json(
    *,
    database: Path,
    query: Path,
    output_json: Path,
    codeql: str = "codeql",
) -> None:
    tmp_bqrs = output_json.with_suffix(".bqrs")
    tmp_csv = output_json.with_suffix(".csv")

    run_codeql_query(
        database=database,
        query=query,
        output_csv=tmp_csv,
        tmp_bqrs_path=tmp_bqrs,
        codeql=codeql,
    )

    result = csv_to_json(tmp_csv)

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, indent=2), encoding="utf-8")


def _path(p: str) -> Path:
    return Path(p).expanduser().resolve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="codeql-to-json",
        description="Run a CodeQL query and export results as JSON.",
    )
    parser.add_argument(
        "-d",
        "--database",
        type=_path,
        required=True,
        help="Path to the CodeQL database directory.",
    )
    parser.add_argument(
        "-q",
        "--query",
        type=_path,
        required=True,
        help="Path to the .ql query file.",
    )
    parser.add_argument(
        "-o",
        "--out",
        type=_path,
        required=True,
        help="Path to write JSON output (e.g. results.json).",
    )

    args = parser.parse_args(argv)

    analyze_to_json(
        database=args.database,
        query=args.query,
        output_json=args.out,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())