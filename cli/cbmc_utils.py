"""Shared CBMC utility functions used by conftest.py and verify_contract.py."""

import os
import re
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def find_cbmc_bin(name: str) -> str:
    """Find a CBMC binary, preferring ~/local/bin (newer version) over system."""
    local = Path.home() / "local" / "bin" / name
    if local.exists():
        return str(local)
    found = shutil.which(name)
    return found if found else name


def check_cbmc() -> bool:
    """Check if CBMC is available."""
    try:
        result = subprocess.run(
            [find_cbmc_bin("cbmc"), "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def compile_and_verify(
    cpp_file: Path | str,
    goto_bin: Path | str | None = None,
    *,
    unwind: int = 20,
    timeout: int = 120,
    property_only: bool = False,
    unwinding_assertions: bool = True,
    object_bits: int | None = 10,
    trace: bool = False,
    extra_args: list[str] | None = None,
    stream_logs: bool = False,
    cleanup_goto: bool = False,
) -> dict:
    """Compile a C++ file with goto-cc and verify with CBMC.

    Args:
        cpp_file: Path to the generated C++ verification harness.
        goto_bin: Path for the GOTO binary. Auto-derived from cpp_file if None.
        unwind: CBMC unwinding bound.
        timeout: CBMC verification timeout in seconds.
        property_only: Skip standard checks, only verify user assertions.
        unwinding_assertions: Warn when unwind bound is insufficient.
        object_bits: CBMC --object-bits value. None omits the flag.
        trace: Pass --trace to CBMC for counterexample extraction.
        extra_args: Additional raw arguments to pass to CBMC.
        stream_logs: Stream CBMC output to console in real time.
        cleanup_goto: Delete the GOTO binary after verification.

    Returns:
        {
            "verified": bool,
            "stdout": str,
            "stderr": str,
            "returncode": int,
            "generated_cpp": str,
            "trace": str | None,
        }
    """
    cpp_file = str(cpp_file)
    if goto_bin is None:
        goto_bin = cpp_file + ".goto"
    goto_bin = str(goto_bin)

    # Step 1: Compile with goto-cc
    compile_cmd = [
        find_cbmc_bin("goto-cc"),
        "-std=c++17",
        "-DCBMC_VERIFICATION",
        "-I", str(PROJECT_ROOT / "engine"),
        "-o", goto_bin,
        cpp_file,
    ]
    if property_only:
        compile_cmd.append("-DCBMC_ASSUME_VALID_OPS")

    try:
        compile_result = subprocess.run(
            compile_cmd, capture_output=True, text=True, timeout=60,
        )
    except subprocess.TimeoutExpired:
        return {
            "verified": False,
            "stdout": "",
            "stderr": "goto-cc compilation timed out",
            "returncode": -1,
            "generated_cpp": cpp_file,
        }

    if compile_result.returncode != 0:
        return {
            "verified": False,
            "stdout": compile_result.stdout,
            "stderr": f"goto-cc failed:\n{compile_result.stderr}",
            "returncode": compile_result.returncode,
            "generated_cpp": cpp_file,
        }

    # Step 2: Build CBMC command
    verify_cmd = [
        find_cbmc_bin("cbmc"),
        goto_bin,
        "--unwind", str(unwind),
    ]
    if object_bits is not None:
        verify_cmd.extend(["--object-bits", str(object_bits)])
    if unwinding_assertions:
        verify_cmd.append("--unwinding-assertions")
    else:
        verify_cmd.append("--no-unwinding-assertions")
    if property_only:
        verify_cmd.append("--drop-unused-functions")
        verify_cmd.extend(["--no-standard-checks", "--no-built-in-assertions"])
        if not trace:
            verify_cmd.append("--slice-formula")
    if trace:
        verify_cmd.append("--trace")
    if stream_logs:
        verify_cmd.extend(["--verbosity", "9", "--timestamp", "monotonic", "--flush"])
    if extra_args:
        verify_cmd.extend(extra_args)

    # Step 3: Run CBMC
    try:
        if stream_logs:
            proc = subprocess.Popen(
                verify_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            stdout_lines = []
            for line in proc.stdout:
                print(line, end="", flush=True)
                stdout_lines.append(line)
            proc.wait(timeout=timeout)
            stdout_data = "".join(stdout_lines)
            stderr_data = ""
            returncode = proc.returncode
        else:
            result = subprocess.run(
                verify_cmd, capture_output=True, text=True, timeout=timeout,
            )
            stdout_data = result.stdout
            stderr_data = result.stderr
            returncode = result.returncode
    except subprocess.TimeoutExpired:
        if stream_logs:
            proc.kill()
        return {
            "verified": False,
            "stdout": "",
            "stderr": f"CBMC timed out after {timeout}s",
            "returncode": -1,
            "generated_cpp": cpp_file,
        }
    finally:
        if cleanup_goto:
            try:
                os.unlink(goto_bin)
            except OSError:
                pass

    # Step 4: Determine result
    if property_only:
        verified = _check_user_assertions(stdout_data)
    else:
        verified = "VERIFICATION SUCCESSFUL" in (stdout_data + stderr_data)

    trace_text = None
    if trace and not verified:
        trace_text = _extract_trace(stdout_data)

    return {
        "verified": verified,
        "stdout": stdout_data,
        "stderr": stderr_data,
        "returncode": returncode,
        "generated_cpp": cpp_file,
        "trace": trace_text,
    }


_USER_ASSERTION_RE = re.compile(r'\[main\.assertion\.\d+\].*:\s+(SUCCESS|FAILURE)')


def _extract_trace(stdout: str) -> str:
    """Extract the counterexample trace from CBMC output."""
    lines = stdout.split("\n")
    trace_lines = []
    in_trace = False
    for line in lines:
        if "Counterexample" in line or line.startswith("Trace for "):
            in_trace = True
        if in_trace:
            if line.startswith("** ") or "VERIFICATION" in line:
                break
            trace_lines.append(line)
    return "\n".join(trace_lines) if trace_lines else ""


def _check_user_assertions(stdout: str) -> bool:
    """Check if all user-defined assertions (main.assertion.*) passed.

    When CBMC reports VERIFICATION FAILED due to built-in safety checks
    but our custom property assertions all passed, this returns True.
    Falls back to "VERIFICATION SUCCESSFUL" check if no main.assertion
    lines are found.
    """
    results = _USER_ASSERTION_RE.findall(stdout)
    if not results:
        return "VERIFICATION SUCCESSFUL" in stdout
    return all(r == "SUCCESS" for r in results)
