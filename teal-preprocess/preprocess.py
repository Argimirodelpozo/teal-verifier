#!/usr/bin/env python3
"""
preprocess.py — CodeQL static analysis of TEAL contracts → CBMC verification metadata.

Runs 6 CodeQL bounds/constraints queries against a TEAL contract and produces:
  1. Annotated TEAL with inline bounds comments
  2. JSON metadata with suggested CBMC bounds
  3. C++ setup code snippet for the verifier

Requires:
  - CodeQL CLI (codeql on PATH or --codeql)
  - codeql-TEAL submodule (git submodule update --init)

Usage:
    python teal-preprocess/preprocess.py --source examples/council/Council.approval.teal
    python teal-preprocess/preprocess.py --source contract.teal --database /path/to/db
    python teal-preprocess/preprocess.py --source contract.teal --output-dir ./preprocessed/ -v
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent.resolve()
CODEQL_TEAL_DIR = SCRIPT_DIR / "codeql-TEAL"
QUERY_DIR = CODEQL_TEAL_DIR / "teal" / "ql" / "lib" / "codeql"
EXTRACTOR_DIR = CODEQL_TEAL_DIR / "teal" / "extractor-pack"

QUERIES = {
    "integer_bounds": "integerBoundsReport.ql",
    "bytearray_bounds": "bytearrayBoundsReport.ql",
    "stack_depth": "stackDepthReport.ql",
    "scratch_space": "scratchSpaceReport.ql",
    "value_constraints": "valueConstraintsReport.ql",
    "combined_bounds": "combinedBoundsReport.ql",
}

# Column schemas for each query (for documentation / validation)
QUERY_COLUMNS = {
    "integer_bounds": ["file", "line", "col", "opcode", "lo", "hi"],
    "bytearray_bounds": ["file", "line", "col", "opcode", "lo", "hi", "value"],
    "stack_depth": ["file", "line", "col", "opcode", "depth_before", "delta"],
    "scratch_space": [
        "file", "line", "col", "opcode", "slot", "type", "lo", "hi", "value", "origin",
    ],
    "value_constraints": ["file", "line", "col", "opcode", "inputKind", "constrainedValue"],
    "combined_bounds": ["file", "line", "col", "opcode", "kind", "lo", "hi", "value"],
}

# Default CBMC bounds from engine/cbmc_avm.h
CBMC_DEFAULTS = {
    "CBMC_STACK_MAX": 32,
    "CBMC_BYTES_MAX": 128,
    "CBMC_SCRATCH_SLOTS": 256,
    "CBMC_MAX_APP_ARGS": 8,
    "CBMC_MAX_FRAMES": 8,
    "CBMC_MAX_BOXES": 4,
    "CBMC_BOX_MAX_SIZE": 64,
    "CBMC_MAX_INNER_TXNS": 4,
    "CBMC_MAX_LOCAL_KEYS": 4,
    "CBMC_GLOBAL_NUM_UINT": 16,
    "CBMC_GLOBAL_NUM_BYTESLICE": 16,
    "CBMC_LOCAL_NUM_UINT": 16,
    "CBMC_LOCAL_NUM_BYTESLICE": 16,
}

MAX_UINT64 = (1 << 64) - 1

# ---------------------------------------------------------------------------
# CodeQL invocation
# ---------------------------------------------------------------------------


def find_codeql(override: str | None) -> str:
    """Find codeql binary: --codeql flag > PATH > ~/tools/codeql/."""
    if override:
        p = Path(override).expanduser().resolve()
        if p.exists():
            return str(p)
        raise FileNotFoundError(f"CodeQL binary not found: {override}")

    found = shutil.which("codeql")
    if found:
        return found

    home_codeql = Path.home() / "tools" / "codeql" / "codeql"
    if home_codeql.exists():
        return str(home_codeql)

    raise FileNotFoundError(
        "CodeQL CLI not found. Install it or use --codeql to specify the path.\n"
        "  https://github.com/github/codeql-cli-binaries"
    )


def validate_submodule() -> None:
    """Check that codeql-TEAL submodule is initialized."""
    if not EXTRACTOR_DIR.exists():
        print(
            "ERROR: codeql-TEAL submodule not initialized.\n"
            "  Run: git submodule update --init teal-preprocess/codeql-TEAL",
            file=sys.stderr,
        )
        sys.exit(1)


def _setup_extractor_search_path() -> Path:
    """
    Create a temporary .codeql-extractors directory structure that CodeQL
    can use via --search-path.

    The extractor-pack is at teal/extractor-pack/ inside codeql-TEAL.
    CodeQL's --search-path expects a directory containing <lang>/ subdirs.
    We copy extractor-pack contents into <tmpdir>/teal/ and fix permissions
    (git may not preserve +x on shell scripts and binaries).
    """
    tmpdir = Path(tempfile.mkdtemp(prefix="codeql-ext-"))
    teal_dir = tmpdir / "teal"
    shutil.copytree(EXTRACTOR_DIR, teal_dir)
    # Fix execute permissions on scripts and binaries
    tools_dir = teal_dir / "tools"
    if tools_dir.exists():
        for sh in tools_dir.glob("*.sh"):
            sh.chmod(sh.stat().st_mode | 0o111)
        for plat_dir in tools_dir.iterdir():
            if plat_dir.is_dir():
                for binary in plat_dir.iterdir():
                    if binary.is_file():
                        binary.chmod(binary.stat().st_mode | 0o111)
    return tmpdir


def create_database(
    source_path: Path, codeql: str, timeout: int, verbose: bool,
) -> Path:
    """Create a CodeQL database for a TEAL source file. Returns db path."""
    db_dir = Path(tempfile.mkdtemp(prefix="teal-db-"))
    ext_dir = _setup_extractor_search_path()

    cmd = [
        codeql,
        "database",
        "create",
        str(db_dir),
        "--overwrite",
        "-l", "teal",
        "-s", str(source_path.parent),
        "--search-path", str(ext_dir),
    ]

    if verbose:
        print(f"  Creating CodeQL database: {' '.join(cmd)}", file=sys.stderr)

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        shutil.rmtree(db_dir, ignore_errors=True)
        shutil.rmtree(ext_dir, ignore_errors=True)
        raise RuntimeError(f"CodeQL database creation timed out after {timeout}s")

    # Clean up extractor symlink dir
    shutil.rmtree(ext_dir, ignore_errors=True)

    if result.returncode != 0:
        shutil.rmtree(db_dir, ignore_errors=True)
        raise RuntimeError(
            f"CodeQL database creation failed:\n{result.stderr}\n{result.stdout}"
        )

    return db_dir


def run_query(
    db: Path, query_name: str, codeql: str, timeout: int, verbose: bool,
) -> list[dict]:
    """Run a single CodeQL query and return parsed CSV rows as dicts."""
    ql_path = QUERY_DIR / QUERIES[query_name]
    if not ql_path.exists():
        print(f"  WARNING: Query file not found: {ql_path}", file=sys.stderr)
        return []

    with tempfile.TemporaryDirectory(prefix="codeql-q-") as tmpdir:
        bqrs_path = Path(tmpdir) / "result.bqrs"
        csv_path = Path(tmpdir) / "result.csv"

        # Step 1: Run query
        query_cmd = [
            codeql, "query", "run",
            "--database", str(db),
            str(ql_path),
            "--output", str(bqrs_path),
        ]

        if verbose:
            print(f"  Running {query_name}...", file=sys.stderr)

        try:
            result = subprocess.run(
                query_cmd, capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            print(
                f"  WARNING: Query {query_name} timed out after {timeout}s",
                file=sys.stderr,
            )
            return []

        if result.returncode != 0:
            print(
                f"  WARNING: Query {query_name} failed:\n{result.stderr[:500]}",
                file=sys.stderr,
            )
            return []

        # Step 2: Decode BQRS to CSV
        decode_cmd = [
            codeql, "bqrs", "decode",
            "--format=csv",
            "--output", str(csv_path),
            str(bqrs_path),
        ]

        try:
            result = subprocess.run(
                decode_cmd, capture_output=True, text=True, timeout=60,
            )
        except subprocess.TimeoutExpired:
            print(
                f"  WARNING: BQRS decode for {query_name} timed out",
                file=sys.stderr,
            )
            return []

        if result.returncode != 0:
            print(
                f"  WARNING: BQRS decode for {query_name} failed:\n{result.stderr[:500]}",
                file=sys.stderr,
            )
            return []

        # Step 3: Parse CSV
        if not csv_path.exists():
            return []

        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            return list(reader)


def run_all_queries(
    db: Path, codeql: str, timeout: int, verbose: bool,
) -> dict[str, list[dict]]:
    """Run all 6 queries. Returns {query_name: [row_dicts]}."""
    results = {}
    for name in QUERIES:
        try:
            rows = run_query(db, name, codeql, timeout, verbose)
            results[name] = rows
            if verbose:
                print(f"    {name}: {len(rows)} rows", file=sys.stderr)
        except Exception as e:
            print(f"  WARNING: {name} failed: {e}", file=sys.stderr)
            results[name] = []
    return results


# ---------------------------------------------------------------------------
# Source scanning (regex-based structural features)
# ---------------------------------------------------------------------------


def scan_source_features(source_path: Path) -> dict:
    """Regex-scan TEAL source for structural features."""
    text = source_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    features = {
        "total_lines": len(lines),
        "callsub_targets": set(),
        "box_ops": 0,
        "inner_txn_submits": 0,
        "store_slots": set(),
        "load_slots": set(),
        "global_put_keys": set(),
        "global_get_keys": set(),
        "local_put_keys": set(),
        "has_itxn_begin": False,
    }

    for line in lines:
        stripped = line.strip()
        # Skip comments and empty lines
        if not stripped or stripped.startswith("//"):
            continue

        # callsub targets
        m = re.match(r"callsub\s+(\w+)", stripped)
        if m:
            features["callsub_targets"].add(m.group(1))

        # box operations
        if re.match(r"box_(create|put|del|extract|replace|get|len|resize|splice)\b", stripped):
            features["box_ops"] += 1

        # inner transactions
        if stripped == "itxn_submit" or stripped == "itxn_next":
            features["inner_txn_submits"] += 1
        if stripped == "itxn_begin":
            features["has_itxn_begin"] = True

        # scratch store/load
        m = re.match(r"store\s+(\d+)", stripped)
        if m:
            features["store_slots"].add(int(m.group(1)))
        m = re.match(r"load\s+(\d+)", stripped)
        if m:
            features["load_slots"].add(int(m.group(1)))

        # global state keys (heuristic: pushbytes before app_global_put)
        m = re.match(r'pushbytes\s+"([^"]*)"', stripped)
        if m:
            # Look ahead for app_global_put/get within 5 lines
            pass  # We'll use a second pass below

    # Second pass: track pushbytes → app_global_put/get pairs
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("app_global_put"):
            # Look back for pushbytes key
            for j in range(max(0, i - 10), i):
                m = re.match(r'pushbytes?\s+"([^"]*)"', lines[j].strip())
                if m:
                    features["global_put_keys"].add(m.group(1))
                    break
        if stripped.startswith("app_global_get"):
            for j in range(max(0, i - 5), i):
                m = re.match(r'pushbytes?\s+"([^"]*)"', lines[j].strip())
                if m:
                    features["global_get_keys"].add(m.group(1))
                    break
        if stripped.startswith("app_local_put"):
            for j in range(max(0, i - 10), i):
                m = re.match(r'pushbytes?\s+"([^"]*)"', lines[j].strip())
                if m:
                    features["local_put_keys"].add(m.group(1))
                    break

    # Convert sets to sorted lists for JSON
    features["callsub_targets"] = sorted(features["callsub_targets"])
    features["store_slots"] = sorted(features["store_slots"])
    features["load_slots"] = sorted(features["load_slots"])
    features["global_put_keys"] = sorted(features["global_put_keys"])
    features["global_get_keys"] = sorted(features["global_get_keys"])
    features["local_put_keys"] = sorted(features["local_put_keys"])

    return features


# ---------------------------------------------------------------------------
# CBMC bounds computation
# ---------------------------------------------------------------------------


def _safe_int(val: str, default: int = 0) -> int:
    """Parse string to int, return default on failure."""
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _next_mult(n: int, mult: int) -> int:
    """Round up to next multiple of mult."""
    return ((n + mult - 1) // mult) * mult


def _next_pow2(n: int) -> int:
    """Round up to next power of 2, minimum 32."""
    if n <= 32:
        return 32
    return 1 << math.ceil(math.log2(n))


def compute_cbmc_bounds(
    results: dict[str, list[dict]], features: dict,
) -> dict[str, int]:
    """Derive suggested CBMC #define values from CodeQL results and source features."""
    suggested = {}

    # --- CBMC_STACK_MAX ---
    max_depth = 0
    for row in results.get("stack_depth", []):
        depth_before = _safe_int(row.get("depth_before", "0"))
        delta = _safe_int(row.get("delta", "0"))
        peak = depth_before + max(delta, 0)
        max_depth = max(max_depth, peak)
    if max_depth > 0:
        stack_max = _next_mult(max_depth + 4, 4)  # +4 margin, round to mult of 4
        if stack_max != CBMC_DEFAULTS["CBMC_STACK_MAX"]:
            suggested["CBMC_STACK_MAX"] = stack_max

    # --- CBMC_BYTES_MAX ---
    max_bytes = 0
    for row in results.get("bytearray_bounds", []):
        hi = _safe_int(row.get("hi", "0"))
        if hi > 0 and hi < MAX_UINT64:
            max_bytes = max(max_bytes, hi)
    # Also check combined_bounds for bytes
    for row in results.get("combined_bounds", []):
        if row.get("kind") == "bytes":
            hi = _safe_int(row.get("hi", "0"))
            if hi > 0 and hi < MAX_UINT64:
                max_bytes = max(max_bytes, hi)
    if max_bytes > 0:
        bytes_max = _next_pow2(max_bytes)
        if bytes_max != CBMC_DEFAULTS["CBMC_BYTES_MAX"]:
            suggested["CBMC_BYTES_MAX"] = bytes_max

    # --- CBMC_MAX_FRAMES ---
    n_callsubs = len(features.get("callsub_targets", []))
    if n_callsubs > 0:
        frames = n_callsubs + 2  # +2 margin
        if frames != CBMC_DEFAULTS["CBMC_MAX_FRAMES"]:
            suggested["CBMC_MAX_FRAMES"] = frames

    # --- CBMC_SCRATCH_SLOTS ---
    all_slots = set(features.get("store_slots", [])) | set(features.get("load_slots", []))
    # Also from CodeQL scratch_space results
    for row in results.get("scratch_space", []):
        slot = _safe_int(row.get("slot", "-1"), -1)
        if slot >= 0:
            all_slots.add(slot)
    if all_slots:
        scratch_max = max(all_slots) + 1
        if scratch_max != CBMC_DEFAULTS["CBMC_SCRATCH_SLOTS"]:
            suggested["CBMC_SCRATCH_SLOTS"] = scratch_max

    # --- CBMC_MAX_BOXES ---
    if features.get("box_ops", 0) > 0:
        # Estimate: min 1 if any box ops, up to count of box_create/box_put
        box_count = max(1, min(features["box_ops"], 8))
        if box_count != CBMC_DEFAULTS["CBMC_MAX_BOXES"]:
            suggested["CBMC_MAX_BOXES"] = box_count

    # --- CBMC_MAX_INNER_TXNS ---
    itxn_count = features.get("inner_txn_submits", 0)
    if itxn_count > 0 and itxn_count != CBMC_DEFAULTS["CBMC_MAX_INNER_TXNS"]:
        suggested["CBMC_MAX_INNER_TXNS"] = itxn_count

    # --- CBMC_GLOBAL_NUM_UINT / BYTESLICE ---
    global_keys = set(features.get("global_put_keys", [])) | set(
        features.get("global_get_keys", [])
    )
    if global_keys:
        n_globals = len(global_keys) + 2  # +2 margin
        if n_globals != CBMC_DEFAULTS["CBMC_GLOBAL_NUM_UINT"]:
            suggested["CBMC_GLOBAL_NUM_UINT"] = n_globals
        if n_globals != CBMC_DEFAULTS["CBMC_GLOBAL_NUM_BYTESLICE"]:
            suggested["CBMC_GLOBAL_NUM_BYTESLICE"] = n_globals

    # --- CBMC_LOCAL_NUM_UINT / BYTESLICE ---
    local_keys = features.get("local_put_keys", [])
    if local_keys:
        n_locals = len(local_keys) + 2
        if n_locals != CBMC_DEFAULTS["CBMC_LOCAL_NUM_UINT"]:
            suggested["CBMC_LOCAL_NUM_UINT"] = n_locals
        if n_locals != CBMC_DEFAULTS["CBMC_LOCAL_NUM_BYTESLICE"]:
            suggested["CBMC_LOCAL_NUM_BYTESLICE"] = n_locals

    return suggested


# ---------------------------------------------------------------------------
# Output generation
# ---------------------------------------------------------------------------


def generate_annotated_teal(
    source_path: Path, results: dict[str, list[dict]],
) -> str:
    """Generate annotated TEAL with inline bounds comments."""
    lines = source_path.read_text(encoding="utf-8").splitlines()

    # Index results by line number
    int_bounds_by_line: dict[int, list[dict]] = {}
    for row in results.get("integer_bounds", []):
        ln = _safe_int(row.get("line", "0"))
        if ln > 0:
            int_bounds_by_line.setdefault(ln, []).append(row)

    bytes_bounds_by_line: dict[int, list[dict]] = {}
    for row in results.get("bytearray_bounds", []):
        ln = _safe_int(row.get("line", "0"))
        if ln > 0:
            bytes_bounds_by_line.setdefault(ln, []).append(row)

    stack_by_line: dict[int, list[dict]] = {}
    for row in results.get("stack_depth", []):
        ln = _safe_int(row.get("line", "0"))
        if ln > 0:
            stack_by_line.setdefault(ln, []).append(row)

    scratch_by_line: dict[int, list[dict]] = {}
    for row in results.get("scratch_space", []):
        ln = _safe_int(row.get("line", "0"))
        if ln > 0:
            scratch_by_line.setdefault(ln, []).append(row)

    constraints_by_line: dict[int, list[dict]] = {}
    for row in results.get("value_constraints", []):
        ln = _safe_int(row.get("line", "0"))
        if ln > 0:
            constraints_by_line.setdefault(ln, []).append(row)

    annotated = []
    for i, line in enumerate(lines, start=1):
        parts = []

        # Integer bounds
        if i in int_bounds_by_line:
            for row in int_bounds_by_line[i]:
                lo = _safe_int(row.get("lo", "0"))
                hi = _safe_int(row.get("hi", "-1"), -1)
                if lo == hi and lo >= 0:
                    parts.append(f"int: ={lo}")
                elif hi == -1 or hi >= MAX_UINT64:
                    parts.append(f"int: [{lo}, MAX]")
                else:
                    parts.append(f"int: [{lo}, {hi}]")

        # Byte array bounds
        if i in bytes_bounds_by_line:
            for row in bytes_bounds_by_line[i]:
                lo = _safe_int(row.get("lo", "0"))
                hi = _safe_int(row.get("hi", "0"))
                if lo == hi:
                    parts.append(f"bytes: ={lo}B")
                elif hi < 0 or hi >= MAX_UINT64:
                    parts.append(f"bytes: [{lo}, MAX]B")
                else:
                    parts.append(f"bytes: [{lo}, {hi}]B")

        # Stack depth
        if i in stack_by_line:
            row = stack_by_line[i][0]  # Take first
            depth = _safe_int(row.get("depth_before", "0"))
            delta = _safe_int(row.get("delta", "0"))
            parts.append(f"stack: {depth}\u2192{depth + delta}")

        # Scratch space
        if i in scratch_by_line:
            for row in scratch_by_line[i]:
                slot = _safe_int(row.get("slot", "-1"), -1)
                typ = row.get("type", "?")
                lo = _safe_int(row.get("lo", "0"))
                hi = _safe_int(row.get("hi", "0"))
                if slot >= 0:
                    if lo == hi and lo >= 0:
                        parts.append(f"scratch[{slot}]: {typ} ={lo}")
                    else:
                        parts.append(f"scratch[{slot}]: {typ} [{lo}, {hi}]")

        # Value constraints
        if i in constraints_by_line:
            for row in constraints_by_line[i]:
                kind = row.get("inputKind", "?")
                val = row.get("constrainedValue", "?")
                parts.append(f"constrained: {kind}={val}")

        if parts:
            annotation = "  // " + "  ".join(parts)
            # Pad to at least column 40, or 4 past line end
            pad_col = max(40, len(line) + 4)
            padded_line = line.ljust(pad_col)
            annotated.append(padded_line + annotation)
        else:
            annotated.append(line)

    return "\n".join(annotated) + "\n"


def generate_metadata(
    source_path: Path,
    results: dict[str, list[dict]],
    bounds: dict[str, int],
    features: dict,
) -> dict:
    """Generate JSON metadata."""
    # Compute summary stats
    max_stack = 0
    for row in results.get("stack_depth", []):
        depth = _safe_int(row.get("depth_before", "0"))
        delta = _safe_int(row.get("delta", "0"))
        max_stack = max(max_stack, depth + max(delta, 0))

    max_bytes = 0
    for row in results.get("bytearray_bounds", []):
        hi = _safe_int(row.get("hi", "0"))
        if 0 < hi < MAX_UINT64:
            max_bytes = max(max_bytes, hi)

    scratch_slots_used = set()
    for row in results.get("scratch_space", []):
        slot = _safe_int(row.get("slot", "-1"), -1)
        if slot >= 0:
            scratch_slots_used.add(slot)
    scratch_slots_used |= set(features.get("store_slots", []))
    scratch_slots_used |= set(features.get("load_slots", []))

    exact_ints = sum(
        1
        for row in results.get("integer_bounds", [])
        if _safe_int(row.get("lo", "0")) == _safe_int(row.get("hi", "-1"), -1)
        and _safe_int(row.get("lo", "0")) >= 0
    )

    exact_bytes = sum(
        1
        for row in results.get("bytearray_bounds", [])
        if row.get("value", "") != ""
    )

    # Serialize analysis results (convert all values to native types)
    analysis = {}
    for name, rows in results.items():
        serialized = []
        for row in rows:
            typed_row = {}
            for k, v in row.items():
                # Try to convert numeric fields
                try:
                    typed_row[k] = int(v)
                except (ValueError, TypeError):
                    typed_row[k] = v
            serialized.append(typed_row)
        analysis[name] = serialized

    return {
        "contract": source_path.name,
        "source_path": str(source_path.resolve()),
        "suggested_cbmc_bounds": bounds,
        "summary": {
            "total_lines": features.get("total_lines", 0),
            "max_stack_depth": max_stack,
            "max_bytes_length": max_bytes,
            "scratch_slots_used": sorted(scratch_slots_used),
            "callsub_count": len(features.get("callsub_targets", [])),
            "exact_int_values": exact_ints,
            "exact_byte_values": exact_bytes,
        },
        "analysis": analysis,
    }


def generate_setup_code(
    source_path: Path,
    results: dict[str, list[dict]],
    bounds: dict[str, int],
    features: dict,
) -> str:
    """Generate C++ setup code snippet for the verifier."""
    lines = []
    contract_name = source_path.name

    lines.append(f"// Auto-generated from CodeQL analysis of {contract_name}")
    lines.append(f"// Run: python teal-preprocess/preprocess.py --source {source_path}")
    lines.append("")

    # Suggested #define overrides
    if bounds:
        lines.append("// Suggested #define overrides (place before #include \"cbmc_avm.h\"):")
        for name, val in sorted(bounds.items()):
            default = CBMC_DEFAULTS.get(name, "?")
            lines.append(f"//   #define {name} {val}  // default: {default}")
        lines.append("")

    # Scratch space setup from CodeQL inference
    scratch_rows = results.get("scratch_space", [])
    if scratch_rows:
        lines.append("// --- Scratch space (from CodeQL inference) ---")
        seen_slots = set()
        for row in scratch_rows:
            slot = _safe_int(row.get("slot", "-1"), -1)
            if slot < 0 or slot in seen_slots:
                continue
            seen_slots.add(slot)
            typ = row.get("type", "?")
            lo = _safe_int(row.get("lo", "0"))
            hi = _safe_int(row.get("hi", "0"))
            src_line = row.get("line", "?")

            if typ == "int" or typ == "uint":
                if lo == hi and lo >= 0:
                    lines.append(
                        f"bs_assume_scratch_int(BS, {slot}, {lo});"
                        f"  // exact value (line {src_line})"
                    )
                else:
                    lines.append(
                        f"// bs_assume_scratch_int: slot {slot} {typ} [{lo}, {hi}]"
                        f" (line {src_line})"
                    )
            elif typ == "bytes" or typ == "byteslice":
                lines.append(
                    f"// scratch slot {slot}: bytes [{lo}, {hi}]B (line {src_line})"
                )
            else:
                lines.append(
                    f"// scratch slot {slot}: {typ} [{lo}, {hi}] (line {src_line})"
                )
        lines.append("")

    # Value constraints
    constraint_rows = results.get("value_constraints", [])
    if constraint_rows:
        lines.append("// --- Value constraints (from CodeQL branch analysis) ---")
        for row in constraint_rows:
            kind = row.get("inputKind", "?")
            val = row.get("constrainedValue", "?")
            src_line = row.get("line", "?")
            opcode = row.get("opcode", "?")
            lines.append(f"// line {src_line}: {opcode} — {kind} = {val}")
        lines.append("")

    # Structural hints
    if features.get("callsub_targets"):
        lines.append(
            f"// Subroutines: {len(features['callsub_targets'])} "
            f"({', '.join(features['callsub_targets'][:10])})"
        )
    if features.get("box_ops", 0) > 0:
        lines.append(f"// Box operations: {features['box_ops']}")
    if features.get("inner_txn_submits", 0) > 0:
        lines.append(f"// Inner txn submits: {features['inner_txn_submits']}")
    if features.get("global_put_keys"):
        keys_str = ", ".join(f'"{k}"' for k in features["global_put_keys"][:10])
        lines.append(f"// Global state keys (put): {keys_str}")
    if features.get("local_put_keys"):
        keys_str = ", ".join(f'"{k}"' for k in features["local_put_keys"][:10])
        lines.append(f"// Local state keys (put): {keys_str}")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="CodeQL static analysis of TEAL contracts → CBMC verification metadata",
    )
    parser.add_argument(
        "--source", "-s",
        type=str,
        required=True,
        help="Path to .teal source file",
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default=None,
        help="Output directory (default: same directory as source)",
    )
    parser.add_argument(
        "--database", "-d",
        type=str,
        default=None,
        help="Path to existing CodeQL database (skips DB creation)",
    )
    parser.add_argument(
        "--codeql",
        type=str,
        default=None,
        help="Path to codeql binary (default: find in PATH)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Per-query timeout in seconds (default: 300)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args(argv)

    source_path = Path(args.source).resolve()
    if not source_path.exists():
        print(f"ERROR: Source file not found: {source_path}", file=sys.stderr)
        return 1

    # Validate submodule
    validate_submodule()

    # Find codeql
    try:
        codeql = find_codeql(args.codeql)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if args.verbose:
        print(f"Using CodeQL: {codeql}", file=sys.stderr)

    # Output directory
    if args.output_dir:
        out_dir = Path(args.output_dir)
    else:
        out_dir = source_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = source_path.stem  # e.g., "Council.approval"

    # Create or use existing database
    temp_db = None
    if args.database:
        db = Path(args.database).resolve()
        if not db.exists():
            print(f"ERROR: Database not found: {db}", file=sys.stderr)
            return 1
    else:
        print(f"Creating CodeQL database for {source_path.name}...", file=sys.stderr)
        try:
            db = create_database(source_path, codeql, args.timeout, args.verbose)
            temp_db = db
        except RuntimeError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1
        print(f"Database created: {db}", file=sys.stderr)

    try:
        # Run all queries
        print(f"Running 6 CodeQL queries...", file=sys.stderr)
        results = run_all_queries(db, codeql, args.timeout, args.verbose)

        total_rows = sum(len(rows) for rows in results.values())
        print(f"Total rows: {total_rows}", file=sys.stderr)

        # Scan source features
        features = scan_source_features(source_path)

        # Compute suggested bounds
        bounds = compute_cbmc_bounds(results, features)

        # Generate outputs
        annotated = generate_annotated_teal(source_path, results)
        metadata = generate_metadata(source_path, results, bounds, features)
        setup = generate_setup_code(source_path, results, bounds, features)

        # Write outputs
        annotated_path = out_dir / f"{stem}.annotated.teal"
        meta_path = out_dir / f"{stem}.meta.json"
        setup_path = out_dir / f"{stem}.setup.cpp"

        annotated_path.write_text(annotated, encoding="utf-8")
        meta_path.write_text(
            json.dumps(metadata, indent=2, default=str) + "\n", encoding="utf-8",
        )
        setup_path.write_text(setup, encoding="utf-8")

        # Summary
        print(f"\nOutputs written to {out_dir}/:", file=sys.stderr)
        print(f"  {annotated_path.name}  (annotated TEAL)", file=sys.stderr)
        print(f"  {meta_path.name}  (JSON metadata)", file=sys.stderr)
        print(f"  {setup_path.name}  (C++ setup code)", file=sys.stderr)

        if bounds:
            print(f"\nSuggested CBMC bounds:", file=sys.stderr)
            for name, val in sorted(bounds.items()):
                default = CBMC_DEFAULTS.get(name, "?")
                print(f"  {name} = {val}  (default: {default})", file=sys.stderr)
        else:
            print(f"\nAll CBMC bounds match defaults.", file=sys.stderr)

        return 0

    finally:
        # Clean up temp database
        if temp_db and temp_db.exists():
            shutil.rmtree(temp_db, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
