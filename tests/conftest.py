"""
Pytest fixtures for formal verification tests.

Provides helpers to:
1. Generate CBMC verification harnesses from TEAL
2. Run CBMC and return structured results
"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent

import sys
sys.path.insert(0, str(PROJECT_ROOT))

from cbmc_transpiler import write_verify, parse_contract, transpile_contract_with_keys
from cli.cbmc_utils import find_cbmc_bin, check_cbmc, compile_and_verify


PRAGMA = "#pragma version 10\n"

# Module-level transpilation cache: avoids re-transpiling the same TEAL file
# across multiple tests in the same module.  Key = teal file path (str).
_transpile_cache: dict[str, tuple[str, dict[str, int], dict[str, int]]] = {}


def _cached_transpile(teal_path: str) -> tuple[str, dict[str, int], dict[str, int]]:
    """Transpile a TEAL file, caching the result for subsequent calls."""
    if teal_path not in _transpile_cache:
        source = parse_contract(teal_path)
        _transpile_cache[teal_path] = transpile_contract_with_keys(source)
    return _transpile_cache[teal_path]


CBMC_AVAILABLE = check_cbmc()


class VerifyRunner:
    """Helper to generate and run CBMC verification on TEAL contracts."""

    def __init__(self, tmp_path: Path):
        self.tmp_path = tmp_path

    def verify(
        self,
        teal_source: str,
        properties: list[str],
        app_id: int = 1,
        unwind: int = 20,
        timeout: int = 120,
        property_file: str | None = None,
        defines: dict | None = None,
        unwinding_assertions: bool = True,
        property_only: bool = False,
        inner_contracts: dict | None = None,
        setup_code: str | None = None,
        object_bits: int = 10,
        trace: bool = False,
    ) -> dict:
        """Transpile inline TEAL, inject properties, run CBMC via goto-cc + cbmc."""
        # Write TEAL to temp file
        teal_file = self.tmp_path / "verify_test.teal"
        teal_file.write_text(teal_source)

        # Generate verification harness
        cpp_file = self.tmp_path / "verify_test.generated.cpp"
        write_verify(
            str(teal_file),
            out_path=str(cpp_file),
            app_id=app_id,
            properties=properties,
            property_file=property_file,
            defines=defines,
            inner_contracts=inner_contracts,
            setup_code=setup_code,
        )

        goto_bin = self.tmp_path / "verify_test.goto"
        return compile_and_verify(
            cpp_file, goto_bin,
            unwind=unwind, timeout=timeout,
            property_only=property_only,
            unwinding_assertions=unwinding_assertions,
            object_bits=object_bits,
            trace=trace,
        )

    def verify_contract(
        self,
        teal_path: str,
        properties: list[str],
        app_id: int = 1,
        unwind: int = 20,
        timeout: int = 120,
        property_file: str | None = None,
        defines: dict | None = None,
        template_path: str | None = None,
        setup_code: str | None = None,
        unwinding_assertions: bool = True,
        property_only: bool = False,
        inner_contracts: dict | None = None,
        object_bits: int = 10,
        trace: bool = False,
    ) -> dict:
        """Verify properties on a TEAL file (not inline source)."""
        cpp_file = self.tmp_path / "verify_contract.generated.cpp"
        write_verify(
            teal_path,
            template_path=template_path,
            out_path=str(cpp_file),
            app_id=app_id,
            properties=properties,
            property_file=property_file,
            defines=defines,
            setup_code=setup_code,
            inner_contracts=inner_contracts,
            _transpiled=_cached_transpile(teal_path),
        )

        goto_bin = self.tmp_path / "verify_contract.goto"
        return compile_and_verify(
            cpp_file, goto_bin,
            unwind=unwind, timeout=timeout,
            property_only=property_only,
            unwinding_assertions=unwinding_assertions,
            object_bits=object_bits,
            trace=trace,
        )


class OpcodeRunner:
    """Run CBMC on raw C++ code that directly tests cbmc_opcodes.h functions."""

    def __init__(self, tmp_path: Path):
        self.tmp_path = tmp_path
        self._counter = 0

    def verify_cpp(self, cpp_code: str, unwind: int = 35, timeout: int = 120,
                   skip_default_includes: bool = False, trace: bool = False) -> dict:
        """
        Wrap cpp_code with includes + main(), compile with goto-cc, run cbmc.

        The cpp_code should contain a main() function body that uses
        __CPROVER_assert for properties and __CPROVER_assume for constraints.

        If skip_default_includes is True, cpp_code must provide its own
        #include directives (useful when #defines must precede includes).

        Returns:
            {
                "verified": bool,
                "stdout": str,
                "stderr": str,
                "returncode": int,
                "generated_cpp": str,
            }
        """
        self._counter += 1
        cpp_file = self.tmp_path / f"opcode_test_{self._counter}.cpp"

        engine_dir = PROJECT_ROOT / "engine"
        if skip_default_includes:
            full_code = (
                '#include <cstdint>\n'
                '#include <cstring>\n'
                'extern "C" { uint64_t nondet_uint64(); uint8_t nondet_uint8(); bool nondet_bool(); }\n'
                '\n'
                f'{cpp_code}\n'
            )
        else:
            full_code = (
                '#include <cstdint>\n'
                '#include <cstring>\n'
                f'#include "{engine_dir}/cbmc_avm.h"\n'
                f'#include "{engine_dir}/cbmc_opcodes.h"\n'
                f'#include "{engine_dir}/properties.h"\n'
                '\n'
                'extern "C" { uint64_t nondet_uint64(); uint8_t nondet_uint8(); bool nondet_bool(); }\n'
                '\n'
                f'{cpp_code}\n'
            )
        cpp_file.write_text(full_code)

        goto_bin = self.tmp_path / f"opcode_test_{self._counter}.goto"
        return compile_and_verify(
            cpp_file, goto_bin,
            unwind=unwind, timeout=timeout, trace=trace,
        )


@pytest.fixture
def verifier(tmp_path):
    """Provide a VerifyRunner instance for property verification tests."""
    if not CBMC_AVAILABLE:
        pytest.skip("CBMC not available")
    return VerifyRunner(tmp_path)


@pytest.fixture
def opcodes(tmp_path):
    """Provide an OpcodeRunner instance for direct opcode testing."""
    if not CBMC_AVAILABLE:
        pytest.skip("CBMC not available")
    return OpcodeRunner(tmp_path)
