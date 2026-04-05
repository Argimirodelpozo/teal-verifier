#!/usr/bin/env python3
"""
verify_contract.py — Formal verification of TEAL contract properties using CBMC.

Orchestrates the full workflow:
1. Transpile TEAL contract to C++ verification harness
2. Inject user-defined properties
3. Run CBMC bounded model checker
4. Parse and report results (VERIFIED / FAILED with counterexample)

Usage:
    # Verify a trivial property
    python verify_contract.py examples/council/Council.approval.teal --property "true"

    # Verify a meaningful property
    python verify_contract.py contract.teal \\
        --property "ctx.result != ACCEPT || get_global(ctx.bs_after, 1, \\"counter\\").first.value > 0"

    # Use a property file
    python verify_contract.py contract.teal --property-file my_props.cpp

    # Tune CBMC parameters
    python verify_contract.py contract.teal --property "..." --unwind 30 --timeout 300

    # Override bounds via CLI
    python verify_contract.py contract.teal --property "true" \\
        --bounds CBMC_STACK_MAX=32 CBMC_BYTES_MAX=64

    # Override bounds via JSON config file
    python verify_contract.py contract.teal --property "true" --bounds-file bounds.json
"""

import argparse
import json as json_mod
import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

from cbmc_transpiler import write_verify
from .cbmc_utils import compile_and_verify


def parse_cbmc_output(stdout: str, stderr: str) -> dict:
    """Parse CBMC output into a structured result.

    Handles both plain-text and --json-ui output formats.
    """
    result = {
        "verified": False,
        "properties": [],
        "counterexample": None,
        "error": None,
    }

    # Try JSON parse first (for --json-ui output)
    try:
        json_data = json_mod.loads(stdout)
        if isinstance(json_data, list):
            for item in json_data:
                if isinstance(item, dict):
                    if "cProverStatus" in item:
                        result["verified"] = item["cProverStatus"] == "success"
                    if "result" in item:
                        for prop in item["result"]:
                            status = prop.get("status", "")
                            desc = prop.get("description", "")
                            pid = prop.get("property", "")
                            result["properties"].append(
                                f"[{pid}] {desc}: {status}"
                            )
            return result
    except (json_mod.JSONDecodeError, TypeError, KeyError):
        pass

    # Plain-text parsing
    combined = stdout + stderr

    if "VERIFICATION SUCCESSFUL" in combined:
        result["verified"] = True

    if "VERIFICATION FAILED" in combined:
        result["verified"] = False

    # Extract property results
    for line in combined.split("\n"):
        if "property" in line.lower() and ("SUCCESS" in line or "FAILURE" in line):
            result["properties"].append(line.strip())

    # Extract counterexample trace (if any)
    if "Counterexample:" in combined or "Trace" in combined:
        trace_lines = []
        in_trace = False
        for line in combined.split("\n"):
            if "Counterexample:" in line or "State " in line:
                in_trace = True
            if in_trace:
                trace_lines.append(line)
        if trace_lines:
            result["counterexample"] = "\n".join(trace_lines[-50:])

    # Check for errors
    if "PARSING ERROR" in combined or "CONVERSION ERROR" in combined:
        result["error"] = combined

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Formally verify properties of TEAL contracts using CBMC"
    )
    parser.add_argument("contract", help="Path to .teal file")
    parser.add_argument(
        "--property", "-p",
        action="append",
        default=None,
        help="C++ property expression referencing VerifyContext ctx "
             "(can be specified multiple times)",
    )
    parser.add_argument(
        "--property-file",
        type=str,
        default=None,
        help="Path to a .cpp file with property function definitions",
    )
    parser.add_argument(
        "--app-id",
        type=int,
        default=1,
        help="Application ID for the contract (default: 1)",
    )
    parser.add_argument(
        "--unwind",
        type=int,
        default=20,
        help="CBMC unwinding bound (default: 20)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="CBMC timeout in seconds (default: 300)",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Path for generated C++ (default: temp file)",
    )
    parser.add_argument(
        "--template", "-t",
        type=str,
        default=None,
        help="Path to custom verification template",
    )
    parser.add_argument(
        "--keep-generated",
        action="store_true",
        help="Don't delete the generated C++ file",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print full CBMC output",
    )
    parser.add_argument(
        "--bounds",
        nargs="*",
        default=None,
        metavar="KEY=VALUE",
        help="Override CBMC bounds (e.g. CBMC_STACK_MAX=32 CBMC_BYTES_MAX=64)",
    )
    parser.add_argument(
        "--bounds-file",
        type=str,
        default=None,
        help="Path to JSON file with CBMC bound overrides "
             '(e.g. {"CBMC_STACK_MAX": 32, "CBMC_BYTES_MAX": 64})',
    )
    parser.add_argument(
        "--setup-code",
        type=str,
        default=None,
        help="C++ code to inject at METHOD_CONSTRAINT_PLACEHOLDER",
    )
    parser.add_argument(
        "--setup-code-file",
        type=str,
        default=None,
        help="Path to file containing setup code to inject",
    )
    parser.add_argument(
        "--property-only",
        action="store_true",
        help="Only check user properties (skip CBMC standard checks, "
             "drop unused functions for performance)",
    )
    parser.add_argument(
        "--solver",
        type=str,
        default=None,
        choices=["minisat", "cadical", "kissat", "z3", "bitwuzla", "cvc5"],
        help="SAT/SMT solver backend (default: minisat). "
             "SMT solvers (z3, bitwuzla, cvc5) can be 2-5x faster for "
             "arithmetic-heavy contracts.",
    )
    parser.add_argument(
        "--object-bits",
        type=int,
        default=None,
        help="CBMC --object-bits value (default: CBMC's default; "
             "use 10 for large contracts)",
    )
    parser.add_argument(
        "--output-cbmc-logs",
        action="store_true",
        help="Stream CBMC progress logs to console (timestamped phase "
             "transitions, variable/clause counts, runtime stats)",
    )
    parser.add_argument(
        "--cbmc-args",
        nargs=argparse.REMAINDER,
        default=None,
        help="Additional raw arguments to pass to CBMC (catch-all)",
    )

    # -- Dev / advanced CBMC options ----------------------------------------
    dev = parser.add_argument_group(
        "dev options",
        "Advanced CBMC flags for debugging, benchmarking, and solver tuning",
    )
    # Analysis
    dev.add_argument(
        "--trace",
        action="store_true",
        help="Show counterexample trace for failed properties",
    )
    dev.add_argument(
        "--stop-on-fail",
        action="store_true",
        help="Stop analysis at the first failed property (implies --trace)",
    )
    dev.add_argument(
        "--show-properties",
        action="store_true",
        help="List all properties in the harness without verifying",
    )
    dev.add_argument(
        "--localize-faults",
        action="store_true",
        help="Attempt to localize faults (experimental)",
    )
    # Unwinding
    dev.add_argument(
        "--partial-loops",
        action="store_true",
        help="Allow paths with partial (incomplete) loop unwindings",
    )
    dev.add_argument(
        "--no-unwinding-assertions",
        action="store_true",
        help="Disable unwinding assertions (unsound: may miss bugs "
             "if unwind bound is too low)",
    )
    dev.add_argument(
        "--slice-formula",
        action="store_true",
        help="Remove assignments unrelated to the property (can speed up SAT)",
    )
    dev.add_argument(
        "--symex-complexity-limit",
        type=int,
        default=None,
        metavar="N",
        help="Abandon paths whose guard exceeds complexity N",
    )
    # Instrumentation
    dev.add_argument(
        "--no-standard-checks",
        action="store_true",
        help="Disable all default safety checks (bounds, pointer, overflow, etc.)",
    )
    dev.add_argument(
        "--no-bounds-check",
        action="store_true",
        help="Disable array bounds checks",
    )
    dev.add_argument(
        "--no-pointer-check",
        action="store_true",
        help="Disable pointer safety checks",
    )
    dev.add_argument(
        "--no-div-by-zero-check",
        action="store_true",
        help="Disable integer division-by-zero checks",
    )
    dev.add_argument(
        "--no-signed-overflow-check",
        action="store_true",
        help="Disable signed integer overflow/underflow checks",
    )
    dev.add_argument(
        "--unsigned-overflow-check",
        action="store_true",
        help="Enable unsigned integer overflow/underflow checks",
    )
    dev.add_argument(
        "--memory-leak-check",
        action="store_true",
        help="Enable memory leak checks",
    )
    dev.add_argument(
        "--drop-unused-functions",
        action="store_true",
        help="Remove unreachable functions before solving "
             "(automatic with --property-only)",
    )
    # Backend / solver
    dev.add_argument(
        "--smt2",
        action="store_true",
        help="Use SMT2 solver (Z3) instead of default SAT solver",
    )
    dev.add_argument(
        "--z3",
        action="store_true",
        help="Use Z3 solver backend",
    )
    dev.add_argument(
        "--bitwuzla",
        action="store_true",
        help="Use Bitwuzla solver backend",
    )
    dev.add_argument(
        "--cvc5",
        action="store_true",
        help="Use CVC5 solver backend",
    )
    dev.add_argument(
        "--sat-solver",
        type=str,
        default=None,
        metavar="SOLVER",
        help="Use a specific SAT solver (e.g. cadical, kissat, minisat2)",
    )
    dev.add_argument(
        "--external-sat-solver",
        type=str,
        default=None,
        metavar="CMD",
        help="Command to invoke an external SAT solver process",
    )
    dev.add_argument(
        "--no-sat-preprocessor",
        action="store_true",
        help="Disable the SAT solver's built-in simplifier",
    )
    dev.add_argument(
        "--refine-arrays",
        action="store_true",
        help="Use refinement procedure for arrays only (can help with "
             "large array models)",
    )
    dev.add_argument(
        "--arrays-uf-always",
        action="store_true",
        help="Always encode arrays as uninterpreted functions "
             "(trades precision for speed)",
    )
    # Output / diagnostics
    dev.add_argument(
        "--json-ui",
        action="store_true",
        help="Use JSON-formatted CBMC output",
    )
    dev.add_argument(
        "--write-solver-stats-to",
        type=str,
        default=None,
        metavar="FILE",
        help="Write per-instruction SAT solver complexity stats to JSON file",
    )
    dev.add_argument(
        "--compact-trace",
        action="store_true",
        help="Give a compact counterexample trace",
    )
    dev.add_argument(
        "--trace-show-function-calls",
        action="store_true",
        help="Show function calls in the trace",
    )
    dev.add_argument(
        "--trace-hex",
        action="store_true",
        help="Show trace values in hexadecimal",
    )
    dev.add_argument(
        "--dimacs",
        action="store_true",
        help="Output the SAT formula in DIMACS CNF format (no solving)",
    )
    dev.add_argument(
        "--show-vcc",
        action="store_true",
        help="Show verification conditions without solving",
    )
    dev.add_argument(
        "--verbosity",
        type=int,
        default=None,
        metavar="N",
        help="CBMC verbosity level 0-10 (default: 6)",
    )
    dev.add_argument(
        "--beautify",
        action="store_true",
        help="Beautify the counterexample (greedy heuristic)",
    )
    dev.add_argument(
        "--symex-coverage-report",
        type=str,
        default=None,
        metavar="FILE",
        help="Generate a Cobertura XML coverage report",
    )
    dev.add_argument(
        "--validate-goto-model",
        action="store_true",
        help="Enable additional well-formedness checks on the goto program",
    )

    args = parser.parse_args()

    if not args.property and not args.property_file:
        parser.error("At least one --property or --property-file is required")

    # Parse bound overrides from --bounds and --bounds-file
    defines = {}
    if args.bounds_file:
        bf = Path(args.bounds_file)
        if not bf.exists():
            parser.error(f"Bounds file not found: {bf}")
        with open(bf) as f:
            file_bounds = json_mod.load(f)
        if not isinstance(file_bounds, dict):
            parser.error("Bounds file must contain a JSON object")
        for k, v in file_bounds.items():
            defines[str(k)] = v
    if args.bounds:
        for item in args.bounds:
            if "=" not in item:
                parser.error(
                    f"Invalid bound format '{item}': expected KEY=VALUE"
                )
            key, val = item.split("=", 1)
            defines[key] = int(val) if val.isdigit() else val

    # Parse setup code
    setup_code = args.setup_code
    if args.setup_code_file:
        scf = Path(args.setup_code_file)
        if not scf.exists():
            parser.error(f"Setup code file not found: {scf}")
        setup_code = scf.read_text(encoding="utf-8")

    # Generate verification harness
    if args.output:
        out_path = args.output
    else:
        fd, out_path = tempfile.mkstemp(suffix=".cpp", prefix="verify_")
        os.close(fd)

    try:
        print(f"Transpiling {args.contract}...")
        generated = write_verify(
            args.contract,
            template_path=args.template,
            out_path=out_path,
            app_id=args.app_id,
            properties=args.property,
            property_file=args.property_file,
            defines=defines if defines else None,
            setup_code=setup_code,
        )
        print(f"Generated: {generated}")

        if defines:
            print(f"Bounds: {defines}")

        # Build extra CBMC args from dev options
        dev_args = []
        # Boolean flags (flag name matches CBMC CLI flag)
        _bool_flags = [
            "trace", "stop_on_fail", "show_properties", "localize_faults",
            "partial_loops", "slice_formula",
            "no_standard_checks", "no_bounds_check", "no_pointer_check",
            "no_div_by_zero_check", "no_signed_overflow_check",
            "unsigned_overflow_check", "memory_leak_check",
            "drop_unused_functions", "smt2", "z3", "bitwuzla", "cvc5",
            "no_sat_preprocessor", "refine_arrays", "arrays_uf_always",
            "json_ui", "compact_trace", "trace_show_function_calls",
            "trace_hex", "dimacs", "show_vcc", "beautify",
            "validate_goto_model",
        ]
        for flag in _bool_flags:
            if getattr(args, flag, False):
                dev_args.append("--" + flag.replace("_", "-"))
        # Value flags
        _val_flags = [
            ("symex_complexity_limit", "symex-complexity-limit"),
            ("sat_solver", "sat-solver"),
            ("external_sat_solver", "external-sat-solver"),
            ("write_solver_stats_to", "write-solver-stats-to"),
            ("verbosity", "verbosity"),
            ("symex_coverage_report", "symex-coverage-report"),
        ]
        for attr, cbmc_flag in _val_flags:
            val = getattr(args, attr, None)
            if val is not None:
                dev_args.extend([f"--{cbmc_flag}", str(val)])

        # Map --solver to CBMC flags
        if args.solver:
            _smt_solvers = {"z3", "bitwuzla", "cvc5"}
            _sat_solvers = {"cadical", "kissat"}
            if args.solver in _smt_solvers:
                dev_args.append(f"--{args.solver}")
            elif args.solver in _sat_solvers:
                dev_args.extend(["--sat-solver", args.solver])
            # minisat is CBMC's default — no flag needed

        # Merge dev args with raw --cbmc-args
        extra = dev_args + (args.cbmc_args or [])

        unwinding_assertions = not args.no_unwinding_assertions

        solver_info = f", solver={args.solver}" if args.solver else ""
        print(f"Running CBMC (unwind={args.unwind}, timeout={args.timeout}s, "
              f"unwinding_assertions={unwinding_assertions}{solver_info})...")
        cbmc_result = compile_and_verify(
            generated,
            unwind=args.unwind,
            timeout=args.timeout,
            extra_args=extra if extra else None,
            property_only=args.property_only,
            unwinding_assertions=unwinding_assertions,
            object_bits=args.object_bits,
            stream_logs=args.output_cbmc_logs,
            cleanup_goto=True,
        )

        stdout = cbmc_result["stdout"]
        stderr = cbmc_result["stderr"]

        if args.verbose:
            print("\n--- CBMC stdout ---")
            print(stdout)
            print("--- CBMC stderr ---")
            print(stderr)
            print("-------------------\n")

        result = parse_cbmc_output(stdout, stderr)
        # compile_and_verify has smarter verification detection (property_only aware)
        result["verified"] = cbmc_result["verified"]

        if result.get("error"):
            print(f"\nERROR: CBMC encountered an error:")
            print(result["error"][:2000])
            sys.exit(2)

        if result["verified"]:
            print(f"\nVERIFIED: All properties hold for all inputs "
                  f"(up to unwind bound {args.unwind})")
            sys.exit(0)
        else:
            print(f"\nFAILED: Property violation found!")
            for prop in result["properties"]:
                print(f"  {prop}")
            if result["counterexample"]:
                print(f"\nCounterexample trace:")
                print(result["counterexample"])
            sys.exit(1)

    finally:
        if not args.keep_generated and not args.output:
            try:
                os.unlink(out_path)
            except OSError:
                pass


if __name__ == "__main__":
    main()
