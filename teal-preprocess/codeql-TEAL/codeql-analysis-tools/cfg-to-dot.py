"""Run the cfgEdges.ql query and produce a Graphviz DOT file.

Usage:
    python cfg-to-dot.py -d <database> -o cfg.dot

The script runs the cfgEdges.ql query against the given CodeQL database,
parses the EDGE-encoded results, and writes a DOT digraph to the output path.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

QUERY_PATH = Path(__file__).resolve().parent.parent / "teal" / "ql" / "lib" / "codeql" / "cfgEdges.ql"

EDGE_STYLE = {
    "NormalSuccessor": "",
    "BooleanSuccessor(true)": 'color=green fontcolor=green label="true"',
    "BooleanSuccessor(false)": 'color=red fontcolor=red label="false"',
    "RetsubSuccessor": 'style=dashed label="retsub"',
}


def run_query(database: Path, codeql: str = "codeql") -> list[str]:
    """Run cfgEdges.ql and return the decoded CSV rows (message column)."""
    tmp_bqrs = database.parent / ".cfg_tmp.bqrs"
    tmp_csv = database.parent / ".cfg_tmp.csv"

    subprocess.run(
        [codeql, "query", "run", "--database", str(database), str(QUERY_PATH),
         "--output", str(tmp_bqrs)],
        check=True, capture_output=True, text=True,
    )
    subprocess.run(
        [codeql, "bqrs", "decode", "--format=csv", "--output", str(tmp_csv),
         str(tmp_bqrs)],
        check=True, capture_output=True, text=True,
    )

    with tmp_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header:
            rows = []
        else:
            msg_idx = len(header) - 1  # message is the last column
            rows = [row[msg_idx] for row in reader]

    tmp_bqrs.unlink(missing_ok=True)
    tmp_csv.unlink(missing_ok=True)
    return rows


def parse_edges(rows: list[str]) -> list[dict[str, str]]:
    """Parse EDGE|src_loc|src_label|dst_loc|dst_label|type rows."""
    edges = []
    for row in rows:
        parts = row.split("|")
        if len(parts) < 6 or parts[0] != "EDGE":
            continue
        edges.append({
            "src_loc": parts[1],
            "src_label": parts[2],
            "dst_loc": parts[3],
            "dst_label": parts[4],
            "type": parts[5],
        })
    return edges


def make_node_id(loc: str) -> str:
    """Convert '3:1' to 'n3_1'."""
    return "n" + loc.replace(":", "_")


def escape_dot(s: str) -> str:
    """Escape a string for DOT label use."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def build_dot(edges: list[dict[str, str]]) -> str:
    """Build a DOT digraph string from parsed edges."""
    nodes: dict[str, str] = {}  # node_id -> label
    lines = ['digraph CFG {', '  rankdir=TB;', '  node [shape=box fontname="Courier" fontsize=10];',
             '  edge [fontname="Courier" fontsize=9];']

    for e in edges:
        src_id = make_node_id(e["src_loc"])
        dst_id = make_node_id(e["dst_loc"])
        nodes.setdefault(src_id, f'L{e["src_loc"]}  {e["src_label"]}')
        nodes.setdefault(dst_id, f'L{e["dst_loc"]}  {e["dst_label"]}')

        attrs = EDGE_STYLE.get(e["type"], "")
        lines.append(f'  {src_id} -> {dst_id} [{attrs}];')

    # emit node declarations with labels
    for nid, label in sorted(nodes.items()):
        lines.append(f'  {nid} [label="{escape_dot(label)}"];')

    lines.append("}")
    return "\n".join(lines) + "\n"


def _path(p: str) -> Path:
    return Path(p).expanduser().resolve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cfg-to-dot",
        description="Run cfgEdges.ql and produce a Graphviz DOT file.",
    )
    parser.add_argument("-d", "--database", type=_path, required=True,
                        help="Path to the CodeQL database.")
    parser.add_argument("-o", "--out", type=_path, required=True,
                        help="Output .dot file path.")
    parser.add_argument("--codeql", default="codeql",
                        help="Path to codeql binary (default: codeql).")

    args = parser.parse_args(argv)

    print(f"Running cfgEdges.ql on {args.database} ...", file=sys.stderr)
    rows = run_query(args.database, codeql=args.codeql)

    edges = parse_edges(rows)
    if not edges:
        print("No CFG edges found.", file=sys.stderr)
        return 1

    dot = build_dot(edges)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(dot, encoding="utf-8")
    print(f"Wrote {len(edges)} edges to {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
