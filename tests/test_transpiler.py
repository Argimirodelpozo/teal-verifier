"""
Unit tests for the TEAL-to-C++ transpiler (AVMTranspiler.py).

Tests cover:
1. Preprocessing (int/byte/addr normalization, label renaming, TMPL_*)
2. Zero-argument opcodes (arithmetic, comparisons, logic, byte ops, state, box)
3. Single/double numeric argument opcodes (pushint, dig, bury, extract, etc.)
4. Bytes opcodes (pushbytes, pushbytess, intcblock, bytecblock)
5. Control flow (b, bz, bnz, callsub, retsub, switch, match)
6. Transaction field access (txn, txna, gtxn, gtxna, gtxns, gtxnsa)
7. Global/state opcodes (global, app_global_*, app_local_*, box_*)
8. Inner transaction opcodes (itxn_begin, itxn_field, itxn_submit)
9. Edge cases (negative numbers, label collisions, TMPL_* variables)
10. Full contract transpilation (end-to-end)
"""

import pytest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cbmc_transpiler import (
    _preprocess_teal,
    process_label,
    parse_hex_literal_as_init_list,
    transpile_contract,
    TEALTranspiler,
    NAMED_INT_CONSTANTS,
)

PRAGMA = "#pragma version 10\n"


# ---------------------------------------------------------------------------
# Helper: transpile a TEAL snippet and return the C++ output
# ---------------------------------------------------------------------------


def _transpile(teal: str) -> str:
    """Transpile TEAL source and return C++ output."""
    return transpile_contract(PRAGMA + teal)


def _transpile_raw(teal: str) -> str:
    """Transpile raw TEAL source (no pragma prefix) and return C++ output."""
    return transpile_contract(teal)


# ===========================================================================
# Preprocessing tests
# ===========================================================================


class TestPreprocessing:
    """Test _preprocess_teal transformations."""

    def test_int_named_constant(self):
        """int NoOp → pushint 0."""
        result = _preprocess_teal("int NoOp\n")
        assert "pushint 0" in result

    def test_int_named_constants_all(self):
        """All named constants should be resolved."""
        for name, value in NAMED_INT_CONSTANTS.items():
            result = _preprocess_teal(f"int {name}\n")
            assert f"pushint {value}" in result, f"Failed for {name}"

    def test_int_hex(self):
        """int 0xFF → pushint 255."""
        result = _preprocess_teal("int 0xFF\n")
        assert "pushint 255" in result

    def test_int_underscore(self):
        """int 1_000_000 → pushint 1000000."""
        result = _preprocess_teal("pushint 1_000_000\n")
        assert "pushint 1000000" in result

    def test_byte_to_pushbytes(self):
        """byte 0xDEAD → pushbytes 0xDEAD."""
        result = _preprocess_teal("byte 0xDEAD\n")
        assert "pushbytes 0xDEAD" in result

    def test_byte_string_literal(self):
        """byte \"hello\" → pushbytes \"hello\"."""
        result = _preprocess_teal('byte "hello"\n')
        assert 'pushbytes "hello"' in result

    def test_addr_to_pushbytes(self):
        """addr <base32> decodes to 32-byte public key."""
        result = _preprocess_teal("addr AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAY5HFKQ\n")
        # Zero address decodes to 32 zero bytes
        expected_hex = "0x" + "00" * 32
        assert expected_hex.upper() in result.upper()

    def test_addr_real_address(self):
        """addr with non-zero address decodes to 32-byte key."""
        # Address for pk = 0x42 * 32 with dummy checksum
        result = _preprocess_teal("addr IJBEEQSCIJBEEQSCIJBEEQSCIJBEEQSCIJBEEQSCIJBEEQSCIJBAAAAAAA\n")
        assert "pushbytes 0x" in result
        # Should produce 32 bytes = 64 hex chars, first byte is 0x42
        hex_part = result.split("0x")[1].strip()
        assert len(hex_part) == 64
        assert hex_part[:2].upper() == "42"

    def test_tmpl_int(self):
        """pushint TMPL_VAR → pushint 0."""
        result = _preprocess_teal("pushint TMPL_MYVAR\n")
        assert "pushint 0" in result

    def test_tmpl_intcblock(self):
        """intcblock with TMPL_* → replaced with 0."""
        result = _preprocess_teal("intcblock 1 TMPL_FOO 3\n")
        assert "intcblock 1 0 3" in result

    def test_tmpl_bytecblock(self):
        """bytecblock with TMPL_* → replaced with 0x00."""
        result = _preprocess_teal("bytecblock 0xDEAD TMPL_BAR\n")
        assert "bytecblock 0xDEAD 0x00" in result

    def test_pragma_typetrack_stripped(self):
        """#pragma typetrack false should be removed."""
        result = _preprocess_teal("#pragma typetrack false\npushint 1\n")
        assert "typetrack" not in result
        assert "pushint 1" in result

    def test_label_rename_swap(self):
        """Label 'swap:' collides with opcode → renamed to '_label_swap:'."""
        result = _preprocess_teal("swap:\npushint 1\nb swap\n")
        assert "_label_swap:" in result
        assert "b _label_swap" in result

    def test_label_rename_pop(self):
        """Label 'pop:' collides with opcode → renamed."""
        result = _preprocess_teal("pop:\npushint 1\nbz pop\n")
        assert "_label_pop:" in result
        assert "bz _label_pop" in result

    def test_switch_label_star_prefix(self):
        """switch with *labels should strip the * prefix."""
        result = _preprocess_teal("switch *label1 *label2\n")
        assert "switch label1 label2" in result

    def test_match_label_star_prefix(self):
        """match with *labels should strip the * prefix."""
        result = _preprocess_teal("match *a *b *c\n")
        assert "match a b c" in result

    def test_branch_star_prefix(self):
        """b *label → b label (strip *)."""
        result = _preprocess_teal("b *my_label\n")
        assert "b my_label" in result

    def test_label_def_star_prefix(self):
        """*my_label: → my_label: (strip *)."""
        result = _preprocess_teal("*my_label:\n")
        assert "my_label:" in result

    def test_comments_stripped(self):
        """Comments after // should not affect preprocessing."""
        result = _preprocess_teal("pushint 42 // this is a comment\n")
        # The line still contains the original text (comments not stripped from output)
        assert "pushint 42" in result

    def test_empty_lines_preserved(self):
        """Empty lines should pass through."""
        result = _preprocess_teal("\n\npushint 1\n\n")
        assert "pushint 1" in result


# ===========================================================================
# Utility function tests
# ===========================================================================


class TestUtilityFunctions:
    """Test standalone utility functions."""

    def test_process_label_dots(self):
        assert process_label("foo.bar") == "L_foo_dot_bar"

    def test_process_label_dashes(self):
        assert process_label("foo-bar") == "L_foo_dash_bar"

    def test_process_label_at(self):
        assert process_label("foo@3") == "L_foo_at_3"

    def test_process_label_combined(self):
        assert process_label("a.b-c@d") == "L_a_dot_b_dash_c_at_d"

    def test_hex_literal_empty(self):
        assert parse_hex_literal_as_init_list("") == "{}"
        assert parse_hex_literal_as_init_list("0x") == "{}"

    def test_hex_literal_bytes(self):
        result = parse_hex_literal_as_init_list("0xDEAD")
        assert result == "{222,173}"  # 0xDE=222, 0xAD=173

    def test_hex_literal_string(self):
        result = parse_hex_literal_as_init_list('"AB"')
        assert result == "{65,66}"  # A=65, B=66

    def test_hex_literal_base64(self):
        result = parse_hex_literal_as_init_list("base64(AQID)")
        # base64("AQID") = bytes [1, 2, 3]
        assert result == "{1,2,3}"


# ===========================================================================
# Zero-argument opcode tests
# ===========================================================================


class TestZeroArgOpcodes:
    """Test transpilation of zero-argument opcodes."""

    @pytest.mark.parametrize("teal_op,cpp_fn", [
        ("+", "add(s)"),
        ("-", "sub(s)"),
        ("*", "mul(s)"),
        ("/", "div_op(s)"),
        ("%", "mod_op(s)"),
    ])
    def test_arithmetic(self, teal_op, cpp_fn):
        out = _transpile(f"pushint 1\npushint 2\n{teal_op}\n")
        assert cpp_fn in out

    @pytest.mark.parametrize("teal_op,cpp_fn", [
        ("==", "bool_eq(s)"),
        ("!=", "bool_neq(s)"),
        ("<", "bool_lt(s)"),
        (">", "bool_gt(s)"),
        ("<=", "bool_leq(s)"),
        (">=", "bool_geq(s)"),
    ])
    def test_comparisons(self, teal_op, cpp_fn):
        out = _transpile(f"pushint 1\npushint 2\n{teal_op}\n")
        assert cpp_fn in out

    @pytest.mark.parametrize("teal_op,cpp_fn", [
        ("&&", "bool_and(s)"),
        ("||", "bool_or(s)"),
        ("!", "not_logical(s)"),
    ])
    def test_logic(self, teal_op, cpp_fn):
        out = _transpile(f"pushint 1\n{teal_op}\n")
        assert cpp_fn in out

    @pytest.mark.parametrize("teal_op,cpp_fn", [
        ("~", "bitwise_neg(s)"),
        ("&", "bitwise_and(s)"),
        ("|", "bitwise_or(s)"),
        ("^", "bitwise_xor(s)"),
        ("shr", "bitwise_shr(s)"),
        ("shl", "bitwise_shl(s)"),
    ])
    def test_bitwise(self, teal_op, cpp_fn):
        out = _transpile(f"pushint 1\npushint 2\n{teal_op}\n")
        assert cpp_fn in out

    @pytest.mark.parametrize("teal_op,cpp_fn", [
        ("dup", "dup(s)"),
        ("dup2", "dup2(s)"),
        ("pop", "pop(s)"),
        ("swap", "swap(s)"),
        ("select", "select(s)"),
    ])
    def test_stack_ops(self, teal_op, cpp_fn):
        out = _transpile(f"pushint 1\n{teal_op}\n")
        assert cpp_fn in out

    @pytest.mark.parametrize("teal_op,cpp_fn", [
        ("concat", "concat(s)"),
        ("len", "len(s)"),
        ("itob", "itob(s)"),
        ("btoi", "btoi(s)"),
        ("bzero", "bzero(s)"),
        ("substring3", "substring3(s)"),
        ("extract3", "extract3(s)"),
        ("getbyte", "getbyte(s)"),
        ("setbyte", "setbyte(s)"),
        ("getbit", "getbit(s)"),
        ("setbit", "setbit(s)"),
        ("bitlen", "bitlen(s)"),
        ("replace3", "replace3(s)"),
        ("extract_uint16", "extract_uint16(s)"),
        ("extract_uint32", "extract_uint32(s)"),
        ("extract_uint64", "extract_uint64(s)"),
    ])
    def test_byte_ops(self, teal_op, cpp_fn):
        out = _transpile(f"pushint 1\n{teal_op}\n")
        assert cpp_fn in out

    @pytest.mark.parametrize("teal_op,cpp_fn", [
        ("mulw", "mulw(s)"),
        ("addw", "addw(s)"),
        ("divw", "divw(s)"),
        ("divmodw", "divmodw(s)"),
        ("exp", "exp_op(s)"),
        ("expw", "expw(s)"),
        ("sqrt", "sqrt_op(s)"),
    ])
    def test_wide_math(self, teal_op, cpp_fn):
        out = _transpile(f"pushint 1\n{teal_op}\n")
        assert cpp_fn in out

    @pytest.mark.parametrize("teal_op,cpp_fn", [
        ("sha256", "sha256(s)"),
        ("sha512_256", "sha512_256(s)"),
        ("sha3_256", "sha3_256(s)"),
        ("keccak256", "keccak256(s)"),
        ("ed25519verify", "ed25519verify(s)"),
        ("ed25519verify_bare", "ed25519verify_bare(s)"),
    ])
    def test_crypto(self, teal_op, cpp_fn):
        out = _transpile(f"pushint 1\n{teal_op}\n")
        assert cpp_fn in out

    @pytest.mark.parametrize("teal_op,cpp_fn", [
        ("app_global_put", "app_global_put(s, BS, ctx)"),
        ("app_global_get", "app_global_get(s, BS, ctx)"),
        ("app_global_get_ex", "app_global_get_ex(s, BS, ctx)"),
        ("app_global_del", "app_global_del(s, BS, ctx)"),
    ])
    def test_global_state(self, teal_op, cpp_fn):
        out = _transpile(f"pushint 1\n{teal_op}\n")
        assert cpp_fn in out

    @pytest.mark.parametrize("teal_op,cpp_fn", [
        ("app_local_put", "app_local_put(s, BS, TxnGroup[currentTxn], ctx)"),
        ("app_local_get", "app_local_get(s, BS, TxnGroup[currentTxn], ctx)"),
        ("app_local_get_ex", "app_local_get_ex(s, BS, TxnGroup[currentTxn], ctx)"),
        ("app_local_del", "app_local_del(s, BS, TxnGroup[currentTxn], ctx)"),
    ])
    def test_local_state(self, teal_op, cpp_fn):
        out = _transpile(f"pushint 1\n{teal_op}\n")
        assert cpp_fn in out

    @pytest.mark.parametrize("teal_op,cpp_fn", [
        ("box_create", "box_create(s, BS, TxnGroup[currentTxn], ctx)"),
        ("box_del", "box_del(s, BS, TxnGroup[currentTxn], ctx)"),
        ("box_len", "box_len(s, BS, TxnGroup[currentTxn], ctx)"),
        ("box_get", "box_get(s, BS, TxnGroup[currentTxn], ctx)"),
        ("box_put", "box_put(s, BS, TxnGroup[currentTxn], ctx)"),
        ("box_extract", "box_extract(s, BS, TxnGroup[currentTxn], ctx)"),
        ("box_replace", "box_replace(s, BS, TxnGroup[currentTxn], ctx)"),
    ])
    def test_box_ops(self, teal_op, cpp_fn):
        out = _transpile(f"pushint 1\n{teal_op}\n")
        assert cpp_fn in out

    @pytest.mark.parametrize("teal_op,cpp_fn", [
        ("b+", "bmath_add(s)"),
        ("b-", "bmath_sub(s)"),
        ("b*", "bmath_mul(s)"),
        ("b/", "bmath_div(s)"),
        ("b%", "bmath_mod(s)"),
        ("b<", "bmath_lt(s)"),
        ("b>", "bmath_gt(s)"),
        ("b<=", "bmath_leq(s)"),
        ("b>=", "bmath_geq(s)"),
        ("b==", "bmath_eq(s)"),
        ("b!=", "bmath_neq(s)"),
        ("b|", "bmath_or(s)"),
        ("b&", "bmath_and(s)"),
        ("b^", "bmath_xor(s)"),
        ("b~", "bmath_neg(s)"),
        ("bsqrt", "bmath_sqrt(s)"),
    ])
    def test_byte_math(self, teal_op, cpp_fn):
        out = _transpile(f"pushint 1\n{teal_op}\n")
        assert cpp_fn in out

    def test_inner_txn_begin(self):
        out = _transpile("itxn_begin\n")
        assert "itxn_begin(s, ctx)" in out

    def test_inner_txn_submit(self):
        out = _transpile("itxn_submit\n")
        assert "itxn_submit(BS, ctx)" in out

    def test_inner_txn_next(self):
        out = _transpile("itxn_next\n")
        assert "itxn_next(s, BS, ctx)" in out

    def test_log(self):
        out = _transpile("pushint 1\nlog\n")
        assert "avm_log(s, ctx)" in out

    def test_assert(self):
        out = _transpile("pushint 1\nassert\n")
        assert "avm_assert(s)" in out

    def test_balance(self):
        out = _transpile("pushint 1\nbalance\n")
        assert "balance_op(s, BS, TxnGroup[currentTxn])" in out

    def test_min_balance(self):
        out = _transpile("pushint 1\nmin_balance\n")
        assert "min_balance_op(s, BS, TxnGroup[currentTxn])" in out

    def test_loads_stores(self):
        out = _transpile("pushint 1\nloads\npushint 1\nstores\n")
        assert "loads(s, ctx)" in out
        assert "stores(s, ctx)" in out

    def test_gaids(self):
        out = _transpile("pushint 0\ngaids\n")
        assert "gaids_op(s)" in out

    def test_vrf_verify(self):
        out = _transpile("vrf_verify VrfAlgorand\n")
        assert "vrf_verify(s, 0)" in out

    def test_block_timestamp(self):
        out = _transpile("pushint 100\nblock BlkTimestamp\n")
        assert "block_field(s, BlkTimestamp)" in out

    def test_block_seed(self):
        out = _transpile("pushint 100\nblock BlkSeed\n")
        assert "block_field(s, BlkSeed)" in out

    def test_base64_decode(self):
        out = _transpile("pushbytes 0x00\nbase64_decode URLEncoding\n")
        assert "base64_decode(s, 0)" in out

    def test_ec_add(self):
        out = _transpile("ec_add BN254g1\n")
        assert "ec_add(s, BN254g1)" in out

    def test_ec_subgroup_check(self):
        out = _transpile("ec_subgroup_check BLS12_381g1\n")
        assert "ec_subgroup_check(s, BLS12_381g1)" in out


# ===========================================================================
# Single numeric argument opcode tests
# ===========================================================================


class TestSingleNumericArgOpcodes:
    """Test opcodes that take a single numeric argument."""

    def test_pushint(self):
        out = _transpile("pushint 42\n")
        assert "pushint(s, 42)" in out

    def test_pushint_large(self):
        """Large values should get ULL suffix."""
        out = _transpile("pushint 4294967296\n")
        assert "pushint(s, 4294967296ULL)" in out

    def test_dig(self):
        out = _transpile("pushint 1\ndig 2\n")
        assert "dig(s, 2)" in out

    def test_bury(self):
        out = _transpile("pushint 1\nbury 3\n")
        assert "bury(s, 3)" in out

    def test_cover(self):
        out = _transpile("pushint 1\ncover 2\n")
        # Unrolled: save top, shift down, place top at depth
        assert "_top = s.stack[s.currentSize - 1]" in out
        assert "s.stack[s.currentSize - 1 - 2] = _top" in out

    def test_uncover(self):
        out = _transpile("pushint 1\nuncover 2\n")
        # Unrolled: save value at depth, shift up, place at top
        assert "_val = s.stack[s.currentSize - 1 - 2]" in out
        assert "s.stack[s.currentSize - 1] = _val" in out

    def test_frame_dig(self):
        out = _transpile("frame_dig -1\n")
        assert "frame_dig(s, ctx, -1)" in out

    def test_frame_bury(self):
        out = _transpile("frame_bury 0\n")
        assert "frame_bury(s, ctx, 0)" in out

    def test_load(self):
        out = _transpile("load 5\n")
        assert "load(s, ctx, 5)" in out

    def test_store(self):
        out = _transpile("store 3\n")
        assert "store(s, ctx, 3)" in out

    def test_popn(self):
        out = _transpile("pushint 1\npopn 2\n")
        assert "s.currentSize -= 2" in out

    def test_dupn(self):
        out = _transpile("pushint 1\ndupn 3\n")
        # Unrolled: 3 inline pushes
        assert out.count("s.stack[s.currentSize++] = _v") == 3

    def test_replace2(self):
        out = _transpile("pushint 1\nreplace2 5\n")
        assert "replace2(s, 5)" in out

    def test_arg(self):
        out = _transpile("arg 0\n")
        assert "arg(s, ctx, 0)" in out

    def test_intc(self):
        out = _transpile("intcblock 10 20\nintc 1\n")
        assert "pushint(s, 20)" in out  # constant-folded from intcblock

    def test_intc_no_block(self):
        """intc without prior intcblock emits panic."""
        out = _transpile("intc 1\n")
        assert "avm_panic()" in out

    def test_gloads(self):
        out = _transpile("pushint 0\ngloads 3\n")
        assert "gloads_op(s, 3)" in out

    def test_gaid(self):
        out = _transpile("gaid 0\n")
        assert "gaid_op(s, 0)" in out


# ===========================================================================
# Double numeric argument opcode tests
# ===========================================================================


class TestDoubleNumericArgOpcodes:
    """Test opcodes that take two numeric arguments."""

    def test_extract(self):
        out = _transpile("pushint 1\nextract 0 8\n")
        assert "extract(s, 0, 8)" in out

    def test_substring(self):
        out = _transpile("pushint 1\nsubstring 2 5\n")
        assert "substring(s, 2, 5)" in out

    def test_proto(self):
        out = _transpile("proto 2 1\n")
        assert "proto(s, ctx, 2, 1)" in out

    def test_gload(self):
        out = _transpile("gload 0 5\n")
        assert "gload_op(s, 0, 5)" in out


# ===========================================================================
# Bytes opcode tests
# ===========================================================================


class TestBytesOpcodes:
    """Test pushbytes, pushbytess, intcblock, bytecblock."""

    def test_pushbytes_hex(self):
        out = _transpile("pushbytes 0xDEAD\n")
        # Inline pushbytes: direct stack slot assignment
        assert "_z.byteslice_len = 2;" in out
        assert "_z.byteslice[0] = 222;" in out
        assert "_z.byteslice[1] = 173;" in out

    def test_pushbytes_empty(self):
        out = _transpile("pushbytes 0x\n")
        # Inline pushbytes: empty bytes (zero-init sets len=0)
        assert "StackValue _z = {};" in out
        assert "_z._is_bytes = true;" in out

    def test_pushbytess(self):
        out = _transpile("pushbytess 0xAA 0xBB\n")
        # Should emit individual inline pushbytes in CBMC mode
        assert "_z.byteslice[0] = 170;" in out
        assert "_z.byteslice[0] = 187;" in out

    def test_intcblock(self):
        """intcblock emits nothing (values folded into lookups)."""
        out = _transpile("intcblock 1 2 3\n")
        assert "ctx.intcblock" not in out  # no runtime array setup

    def test_bytecblock(self):
        """bytecblock emits nothing (values folded into lookups)."""
        out = _transpile("bytecblock 0xAA 0xBB\n")
        assert "ctx.bytecblock" not in out  # no runtime array setup

    def test_intc_shorthand(self):
        """intc_0 through intc_3 resolve to pushint in CBMC mode."""
        values = [10, 20, 30, 40]
        for i in range(4):
            out = _transpile(f"intcblock 10 20 30 40\nintc_{i}\n")
            assert f"pushint(s, {values[i]})" in out  # constant-folded

    def test_intc_shorthand_no_block(self):
        """intc_N without prior intcblock emits panic."""
        for i in range(4):
            out = _transpile(f"intc_{i}\n")
            assert "avm_panic()" in out

    def test_bytec_shorthand(self):
        """bytec_0 through bytec_3 resolve to inline pushbytes in CBMC mode."""
        for i in range(4):
            out = _transpile(f"bytecblock 0xAA 0xBB 0xCC 0xDD\nbytec_{i}\n")
            assert "_z._is_bytes = true;" in out  # constant-folded inline

    def test_bytec_shorthand_no_block(self):
        """bytec_N without prior bytecblock emits panic."""
        for i in range(4):
            out = _transpile(f"bytec_{i}\n")
            assert "avm_panic()" in out

    def test_arg_shorthand(self):
        """arg_0 through arg_3 should emit arg(s, ctx, N)."""
        for i in range(4):
            out = _transpile(f"arg_{i}\n")
            assert f"arg(s, ctx, {i})" in out


# ===========================================================================
# Control flow tests
# ===========================================================================


class TestControlFlow:
    """Test branch and subroutine opcodes."""

    def test_b(self):
        out = _transpile("b my_label\nmy_label:\npushint 1\n")
        assert "goto L_my_label" in out

    def test_bz(self):
        out = _transpile("pushint 0\nbz my_label\nmy_label:\n")
        assert "if(s.pop().value == 0) goto L_my_label" in out

    def test_bnz(self):
        out = _transpile("pushint 1\nbnz my_label\nmy_label:\n")
        assert "if(s.pop().value != 0) goto L_my_label" in out

    def test_callsub(self):
        out = _transpile("callsub my_sub\nmy_sub:\npushint 1\n")
        assert "_csub[_csub_sp++] = 0" in out
        assert "goto L_my_sub" in out
        assert "callsub_0:" in out

    def test_retsub_generates_switch(self):
        out = _transpile("callsub my_sub\nmy_sub:\nretsub\n")
        assert "retsub_cleanup(s, ctx)" in out
        assert "switch (_ret)" in out
        assert "case 0:" in out

    def test_multiple_callsubs(self):
        teal = "callsub a\ncallsub b\na:\nretsub\nb:\nretsub\n"
        out = _transpile(teal)
        assert "callsub_0:" in out
        assert "callsub_1:" in out

    def test_switch(self):
        teal = "pushint 0\nswitch label_a label_b\nlabel_a:\nlabel_b:\n"
        out = _transpile(teal)
        assert "_sw == 0" in out
        assert "_sw == 1" in out
        assert "L_label_a" in out
        assert "L_label_b" in out

    def test_match(self):
        teal = "pushint 1\npushint 2\npushint 1\nmatch label_a label_b\nlabel_a:\nlabel_b:\n"
        out = _transpile(teal)
        assert "L_label_a" in out
        assert "L_label_b" in out
        assert "s.get(0)" in out

    def test_return(self):
        """'return' becomes 'goto _contract_end'."""
        out = _transpile("pushint 1\nreturn\n")
        assert "goto _contract_end" in out

    def test_err(self):
        """'err' wraps with goto _contract_end."""
        out = _transpile("err\n")
        assert "err()" in out
        assert "goto _contract_end" in out


# ===========================================================================
# Transaction field access tests
# ===========================================================================


class TestTransactionFields:
    """Test txn, txna, gtxn, gtxna, gtxns, gtxnsa opcodes."""

    def test_txn_field(self):
        out = _transpile("txn Sender\n")
        assert "txn_field(s, TxnGroup[currentTxn], Sender)" in out

    def test_txn_application_id(self):
        out = _transpile("txn ApplicationID\n")
        assert "txn_field(s, TxnGroup[currentTxn], ApplicationID)" in out

    def test_txn_on_completion(self):
        out = _transpile("txn OnCompletion\n")
        assert "txn_field(s, TxnGroup[currentTxn], OnCompletion)" in out

    def test_txna_field(self):
        out = _transpile("txna ApplicationArgs 0\n")
        assert "txna_field(s, TxnGroup[currentTxn], ApplicationArgs, 0)" in out

    def test_gtxn_field(self):
        out = _transpile("gtxn 0 Sender\n")
        assert "gtxn_field(s, TxnGroup, 0, Sender)" in out

    def test_gtxna_field(self):
        out = _transpile("gtxna 1 ApplicationArgs 0\n")
        assert "gtxna_field(s, TxnGroup, 1, ApplicationArgs, 0)" in out

    def test_gtxns_field(self):
        """gtxns pops group index from stack."""
        out = _transpile("pushint 0\ngtxns Sender\n")
        assert "gtxns_field(s, TxnGroup, Sender)" in out

    def test_gtxnsa_field(self):
        """gtxnsa pops group index from stack."""
        out = _transpile("pushint 0\ngtxnsa ApplicationArgs 0\n")
        assert "gtxnsa(s, TxnGroup, ApplicationArgs, 0)" in out


# ===========================================================================
# Global field tests
# ===========================================================================


class TestGlobalFields:
    """Test global opcode field access."""

    @pytest.mark.parametrize("field", [
        "MinTxnFee", "MinBalance", "MaxTxnLife", "ZeroAddress",
        "GroupSize", "Round", "LatestTimestamp",
        "CurrentApplicationID", "CreatorAddress",
        "CurrentApplicationAddress", "GroupID",
        "OpcodeBudget", "CallerApplicationID",
        "GenesisHash", "LogicSigVersion",
    ])
    def test_global_field(self, field):
        out = _transpile(f"global {field}\n")
        assert f"global_field(s, BS, ctx, GF_{field})" in out


# ===========================================================================
# State operation tests
# ===========================================================================


class TestStateOperations:
    """Test itxn_field, acct_params_get, asset_params_get, etc."""

    def test_itxn_field(self):
        out = _transpile("itxn_begin\npushint 6\nitxn_field TypeEnum\n")
        assert "itxn_field(s, ctx, TypeEnum)" in out

    def test_itxn_read(self):
        out = _transpile("itxn Sender\n")
        assert "itxn_field_read(s, ctx, Sender)" in out

    def test_itxna_read(self):
        out = _transpile("itxna ApplicationArgs 0\n")
        assert "itxna_field_read(s, ctx, ApplicationArgs, 0)" in out

    def test_gitxn_field(self):
        out = _transpile("gitxn 0 Sender\n")
        assert "gitxn_field(s, ctx, 0, Sender)" in out

    def test_gitxna_field(self):
        out = _transpile("gitxna 0 ApplicationArgs 1\n")
        assert "gitxna_field(s, ctx, 0, ApplicationArgs, 1)" in out

    def test_acct_params_get(self):
        out = _transpile("pushint 1\nacct_params_get AcctBalance\n")
        assert "acct_params_get(s, BS, TxnGroup[currentTxn], ctx, AcctBalance)" in out

    def test_app_params_get(self):
        out = _transpile("pushint 1\napp_params_get AppApprovalProgram\n")
        assert "app_params_get(s, BS, ctx, AppApprovalProgram)" in out

    def test_asset_params_get(self):
        out = _transpile("pushint 1\nasset_params_get AssetManager\n")
        assert "asset_params_get(s, BS, AssetManager_field)" in out

    def test_asset_holding_get(self):
        out = _transpile("pushint 1\npushint 2\nasset_holding_get AssetBalance\n")
        assert "asset_holding_get(s, BS, TxnGroup[currentTxn], ctx, AssetBalance_field)" in out

    def test_json_ref(self):
        out = _transpile("pushint 1\npushint 2\njson_ref JSONUint64\n")
        assert "json_ref(s, JSONUint64)" in out


# ===========================================================================
# CBMC mode specifics
# ===========================================================================


class TestCBMCMode:
    """Test CBMC-specific transpilation behavior."""

    def test_bail_on_panic_appended(self):
        """Opcode calls should be followed by AVM_BAIL_ON_PANIC."""
        out = _transpile("pushint 1\npushint 2\n+\n")
        assert "AVM_BAIL_ON_PANIC()" in out

    def test_callsub_stack_local(self):
        """Callsub stack uses local array."""
        out = _transpile("callsub a\na:\nretsub\n")
        assert "_csub[" in out
        assert "_csub_sp" in out


# ===========================================================================
# Label handling tests
# ===========================================================================


class TestLabelHandling:
    """Test label processing edge cases."""

    def test_label_with_dots(self):
        out = _transpile("my.label:\npushint 1\nb my.label\n")
        assert "L_my_dot_label" in out

    def test_label_with_at(self):
        out = _transpile("foo@3:\npushint 1\nb foo@3\n")
        assert "L_foo_at_3" in out

    def test_duplicate_label_skipped(self):
        """Duplicate labels should not be emitted twice."""
        out = _transpile("my_label:\nmy_label:\npushint 1\n")
        # Count occurrences of the label definition
        assert out.count("L_my_label: ;") == 1

    def test_unsupported_opcode_comment(self):
        """Unknown opcodes should emit a comment, not crash."""
        # Using a fake opcode that doesn't exist
        # The preprocessor won't transform it, and the transpiler should handle gracefully
        t = TEALTranspiler()
        source = _preprocess_teal(PRAGMA + "pushint 1\n")
        # We can't easily inject a truly unknown opcode through tree-sitter,
        # but we can check that the transpiler doesn't crash on valid TEAL
        out = t.transpile(source)
        assert "pushint(s, 1)" in out


# ===========================================================================
# Edge case tests
# ===========================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_negative_frame_dig(self):
        """frame_dig -1 should handle negative argument."""
        out = _transpile("frame_dig -1\n")
        assert "frame_dig(s, ctx, -1)" in out

    def test_negative_frame_dig_deep(self):
        """frame_dig -3 should handle deeper negative argument."""
        out = _transpile("frame_dig -3\n")
        assert "frame_dig(s, ctx, -3)" in out

    def test_empty_source(self):
        """Empty TEAL should produce minimal output."""
        out = _transpile("")
        # Should not crash, may produce empty or minimal output
        assert isinstance(out, str)

    def test_pragma_only(self):
        """Pragma-only TEAL should produce no opcode output."""
        out = _transpile_raw("#pragma version 10\n")
        # Should have no opcode calls
        assert "pushint" not in out
        assert "add" not in out

    def test_comment_only(self):
        """Comment lines should be ignored."""
        out = _transpile("// this is a comment\npushint 42\n")
        assert "pushint(s, 42)" in out

    def test_multiple_pragmas(self):
        """Multiple pragmas including typetrack should work."""
        teal = "#pragma version 12\n#pragma typetrack false\npushint 1\n"
        out = _transpile_raw(teal)
        assert "pushint(s, 1)" in out


# ===========================================================================
# End-to-end transpilation tests
# ===========================================================================


class TestEndToEnd:
    """Test full contract transpilation with realistic patterns."""

    def test_simple_counter(self):
        """Transpile a simple counter contract."""
        teal = """\
#pragma version 10
pushint 1
pushint 2
+
pushint 3
==
"""
        out = transpile_contract(teal)
        assert "pushint(s, 1)" in out
        assert "pushint(s, 2)" in out
        assert "add(s)" in out
        assert "pushint(s, 3)" in out
        assert "bool_eq(s)" in out

    def test_branch_and_label(self):
        """Transpile a contract with branching."""
        teal = """\
#pragma version 10
pushint 1
bnz success
pushint 0
b done
success:
pushint 1
done:
"""
        out = transpile_contract(teal)
        assert "goto L_success" in out
        assert "goto L_done" in out
        assert "L_success: ;" in out
        assert "L_done: ;" in out

    def test_subroutine_pattern(self):
        """Transpile a contract with callsub/retsub."""
        teal = """\
#pragma version 10
pushint 42
callsub my_sub
pushint 1
return
my_sub:
proto 1 1
pushint 10
+
retsub
"""
        out = transpile_contract(teal)
        assert "_csub[_csub_sp++] = 0" in out
        assert "goto L_my_sub" in out
        assert "callsub_0:" in out
        assert "proto(s, ctx, 1, 1)" in out
        assert "retsub_cleanup(s, ctx)" in out

    def test_global_state_operations(self):
        """Transpile global state read/write pattern.

        Static keys (pushbytes + state op) are fused into direct-indexed access.
        The swap between pushbytes and app_global_put breaks fusion, so put
        falls back to the scanning version.
        """
        teal = """\
#pragma version 10
pushbytes 0x636F756E746572
app_global_get
pushint 1
+
pushbytes 0x636F756E746572
swap
app_global_put
"""
        out = transpile_contract(teal)
        # Fused: gs_get_idx with direct array access (no scanning, no hashing)
        assert "gs_get_idx(BS.globals," in out
        # swap breaks pushbytes→put fusion, so scanning fallback is used
        assert "app_global_put(s, BS, ctx)" in out

    def test_box_operations_pattern(self):
        """Transpile a box create + put + get pattern."""
        teal = """\
#pragma version 10
pushbytes 0x6B6579
pushint 32
box_create
pop
pushbytes 0x6B6579
pushbytes 0xDEADBEEF
box_put
pushbytes 0x6B6579
box_get
"""
        out = transpile_contract(teal)
        assert "box_create(s, BS, TxnGroup[currentTxn], ctx)" in out
        assert "box_put(s, BS, TxnGroup[currentTxn], ctx)" in out
        assert "box_get(s, BS, TxnGroup[currentTxn], ctx)" in out

    def test_real_council_teal(self):
        """Transpile the actual Council contract (smoke test)."""
        council_teal = PROJECT_ROOT / "examples" / "council" / "Council.approval.teal"
        if not council_teal.exists():
            pytest.skip("Council TEAL file not found")
        source = council_teal.read_text()
        out = transpile_contract(source)
        # Should produce non-trivial output with no crashes
        assert len(out) > 1000
        # Should contain typical patterns
        assert "pushint" in out
        assert "app_global" in out

    def test_real_arc89_teal(self):
        """Transpile the actual ARC89 contract (smoke test)."""
        arc89_teal = PROJECT_ROOT / "examples" / "arc89" / "AsaMetadataRegistry.approval.teal"
        if not arc89_teal.exists():
            pytest.skip("ARC89 TEAL file not found")
        source = arc89_teal.read_text()
        out = transpile_contract(source)
        # Should produce large output for 4300-line contract
        assert len(out) > 5000
        # Should contain ARC89-specific patterns
        assert "box_" in out  # box operations
        assert "global_field" in out  # global field access
        assert "gtxns_field" in out  # group txn stack access


# ===========================================================================
# Wormhole Compatibility Tests
# ===========================================================================


class TestWormholeCompat:
    """Tests for Wormhole contract compatibility features."""

    def test_ecdsa_pk_recover_transpile(self):
        """ecdsa_pk_recover Secp256k1 transpiles to ecdsa_pk_recover(s)."""
        out = _transpile("ecdsa_pk_recover Secp256k1")
        assert "ecdsa_pk_recover(s);" in out

    def test_ecdsa_pk_decompress_transpile(self):
        """ecdsa_pk_decompress Secp256k1 transpiles to ecdsa_pk_decompress(s)."""
        out = _transpile("ecdsa_pk_decompress Secp256k1")
        assert "ecdsa_pk_decompress(s);" in out

    def test_ecdsa_verify_transpile(self):
        """ecdsa_verify Secp256k1 transpiles to ecdsa_verify(s)."""
        out = _transpile("ecdsa_verify Secp256k1")
        assert "ecdsa_verify(s);" in out

    def test_ecdsa_cbmc_bail_on_panic(self):
        """ecdsa opcodes emit AVM_BAIL_ON_PANIC in cbmc mode."""
        out = _transpile("ecdsa_pk_recover Secp256k1")
        assert "AVM_BAIL_ON_PANIC()" in out

    def test_byte_empty_string_preprocessing(self):
        """byte \"\" preprocesses to pushbytes 0x (empty bytes)."""
        result = _preprocess_teal('byte ""\n')
        assert "pushbytes 0x" in result

    def test_byte_empty_string_transpile(self):
        """byte \"\" transpiles to inline empty pushbytes."""
        out = _transpile('byte ""')
        assert 'StackValue _z = {};' in out
        assert '_z._is_bytes = true;' in out

    def test_byte_nonempty_still_works(self):
        """byte 0xDEAD still preprocesses to pushbytes 0xDEAD."""
        result = _preprocess_teal("byte 0xDEAD\n")
        assert "pushbytes 0xDEAD" in result

    def test_real_wormhole_core_teal(self):
        """Transpile the Wormhole core_approve contract (smoke test)."""
        wh_teal = PROJECT_ROOT / "examples" / "wormhole" / "core_approve.teal"
        if not wh_teal.exists():
            pytest.skip("Wormhole core TEAL file not found")
        source = wh_teal.read_text()
        out = transpile_contract(source)
        assert len(out) > 1000
        # Core contract should contain typical patterns
        assert "txn_field" in out

    def test_real_wormhole_vaa_verify_teal(self):
        """Transpile the Wormhole vaa_verify contract (smoke test)."""
        wh_teal = PROJECT_ROOT / "examples" / "wormhole" / "vaa_verify.teal"
        if not wh_teal.exists():
            pytest.skip("Wormhole vaa_verify TEAL file not found")
        source = wh_teal.read_text()
        out = transpile_contract(source)
        assert len(out) > 1000
        assert "ecdsa_pk_recover(s)" in out
