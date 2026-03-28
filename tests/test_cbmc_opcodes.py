"""
Exhaustive CBMC-based tests for individual AVM opcode implementations.

Each test writes a small C++ main() that:
1. Sets up symbolic/concrete inputs
2. Calls opcode function(s) from cbmc_opcodes.h
3. Asserts properties with __CPROVER_assert
4. Runs through CBMC to verify for all inputs

Organized by phase matching the opcode expansion plan.
"""

import pytest


# ============================================================================
# Constants / Initialization Opcodes
# ============================================================================

class TestIntcBytec:
    """Tests for pushint/pushbytes constant operations (intcblock/bytecblock resolved at transpile time)."""

    def test_pushint_multiple(self, opcodes):
        """pushint pushes correct integer values."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);

    pushint(s, 42);
    StackValue r0 = stack_pop(s);
    __CPROVER_assert(r0.value == 42, "pushint 42");

    pushint(s, 99);
    StackValue r1 = stack_pop(s);
    __CPROVER_assert(r1.value == 99, "pushint 99");

    pushint(s, 0);
    StackValue r2 = stack_pop(s);
    __CPROVER_assert(r2.value == 0, "pushint 0");
    return 0;
}
""")
        assert result["verified"], f"pushint multiple failed:\n{result['stderr']}"

    def test_pushint_sequence(self, opcodes):
        """Multiple pushint calls push and pop in stack order."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);

    pushint(s, 10);
    pushint(s, 20);
    pushint(s, 30);
    pushint(s, 40);

    __CPROVER_assert(stack_pop(s).value == 40, "top");
    __CPROVER_assert(stack_pop(s).value == 30, "second");
    __CPROVER_assert(stack_pop(s).value == 20, "third");
    __CPROVER_assert(stack_pop(s).value == 10, "bottom");
    return 0;
}
""")
        assert result["verified"], f"pushint sequence failed:\n{result['stderr']}"

    def test_pushbytes_basic(self, opcodes):
        """pushbytes pushes correct byteslice values."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t d0[] = {0xAA, 0xBB};
    uint8_t d1[] = {0xCC};

    pushbytes(s, d0, 2);
    StackValue r0 = stack_pop(s);
    __CPROVER_assert(r0._is_bytes, "pushbytes 0 is bytes");
    __CPROVER_assert(r0.byteslice_len == 2, "pushbytes 0 len");
    __CPROVER_assert(r0.byteslice[0] == 0xAA, "pushbytes 0 byte0");
    __CPROVER_assert(r0.byteslice[1] == 0xBB, "pushbytes 0 byte1");

    pushbytes(s, d1, 1);
    StackValue r1 = stack_pop(s);
    __CPROVER_assert(r1.byteslice_len == 1, "pushbytes 1 len");
    __CPROVER_assert(r1.byteslice[0] == 0xCC, "pushbytes 1 byte0");
    return 0;
}
""")
        assert result["verified"], f"pushbytes basic failed:\n{result['stderr']}"

    def test_pushbytes_sequence(self, opcodes):
        """Multiple pushbytes calls push and pop in stack order."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t d0[] = {0x10};
    uint8_t d1[] = {0x20};
    uint8_t d2[] = {0x30};
    uint8_t d3[] = {0x40};

    pushbytes(s, d0, 1);
    pushbytes(s, d1, 1);
    pushbytes(s, d2, 1);
    pushbytes(s, d3, 1);

    __CPROVER_assert(stack_pop(s).byteslice[0] == 0x40, "top");
    __CPROVER_assert(stack_pop(s).byteslice[0] == 0x30, "second");
    __CPROVER_assert(stack_pop(s).byteslice[0] == 0x20, "third");
    __CPROVER_assert(stack_pop(s).byteslice[0] == 0x10, "bottom");
    return 0;
}
""")
        assert result["verified"], f"pushbytes sequence failed:\n{result['stderr']}"


class TestPushMultiple:
    """Tests for pushints and pushbytess."""

    def test_pushints(self, opcodes):
        """pushints pushes multiple integers in order."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint64_t vals[] = {10, 20, 30};
    pushints(s, vals, 3);
    __CPROVER_assert(s.currentSize == 3, "3 values pushed");
    // Last pushed is on top
    __CPROVER_assert(stack_pop(s).value == 30, "top is 30");
    __CPROVER_assert(stack_pop(s).value == 20, "next is 20");
    __CPROVER_assert(stack_pop(s).value == 10, "bottom is 10");
    return 0;
}
""")
        assert result["verified"], f"pushints failed:\n{result['stderr']}"

    def test_pushbytess(self, opcodes):
        """pushbytess pushes multiple byte strings in order."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t d0[] = {0x01};
    uint8_t d1[] = {0x02, 0x03};
    StackValue vals[2];
    vals[0] = sv_bytes(d0, 1);
    vals[1] = sv_bytes(d1, 2);
    pushbytess(s, vals, 2);
    __CPROVER_assert(s.currentSize == 2, "2 values pushed");
    StackValue top = stack_pop(s);
    __CPROVER_assert(top.byteslice_len == 2, "top is 2-byte");
    __CPROVER_assert(top.byteslice[0] == 0x02, "top b0");
    StackValue bot = stack_pop(s);
    __CPROVER_assert(bot.byteslice_len == 1, "bot is 1-byte");
    __CPROVER_assert(bot.byteslice[0] == 0x01, "bot b0");
    return 0;
}
""")
        assert result["verified"], f"pushbytess failed:\n{result['stderr']}"


class TestArgs:
    """Tests for arg/args opcodes (LogicSig arguments, NOT txn ApplicationArgs)."""

    def test_arg_immediate(self, opcodes):
        """arg N pushes the Nth LogicSig argument."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    // Set up LogicSig arguments
    ctx.LsigArgs[0][0] = 0xAA; ctx.LsigArgs[0][1] = 0xBB; ctx.LsigArgLens[0] = 2;
    ctx.LsigArgs[1][0] = 0xCC; ctx.LsigArgLens[1] = 1;
    ctx.NumLsigArgs = 2;

    arg(s, ctx, 0);
    StackValue r0 = stack_pop(s);
    __CPROVER_assert(r0._is_bytes, "is bytes");
    __CPROVER_assert(r0.byteslice_len == 2, "arg0 len");
    __CPROVER_assert(r0.byteslice[0] == 0xAA, "arg0 b0");
    __CPROVER_assert(r0.byteslice[1] == 0xBB, "arg0 b1");

    arg(s, ctx, 1);
    StackValue r1 = stack_pop(s);
    __CPROVER_assert(r1.byteslice_len == 1, "arg1 len");
    __CPROVER_assert(r1.byteslice[0] == 0xCC, "arg1 b0");
    return 0;
}
""")
        assert result["verified"], f"arg immediate failed:\n{result['stderr']}"

    def test_args_dynamic(self, opcodes):
        """args pops index from stack and pushes that LogicSig argument."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    ctx.LsigArgs[0][0] = 0x10; ctx.LsigArgLens[0] = 1;
    ctx.LsigArgs[1][0] = 0x20; ctx.LsigArgLens[1] = 1;
    ctx.NumLsigArgs = 2;

    pushint(s, 1);
    args(s, ctx);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.byteslice[0] == 0x20, "dynamic args index 1");
    return 0;
}
""")
        assert result["verified"], f"args dynamic failed:\n{result['stderr']}"

    def test_arg_shorthand(self, opcodes):
        """arg_0 through arg_3 match arg with corresponding index."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    ctx.LsigArgs[0][0] = 0xA0; ctx.LsigArgLens[0] = 1;
    ctx.LsigArgs[1][0] = 0xA1; ctx.LsigArgLens[1] = 1;
    ctx.LsigArgs[2][0] = 0xA2; ctx.LsigArgLens[2] = 1;
    ctx.LsigArgs[3][0] = 0xA3; ctx.LsigArgLens[3] = 1;
    ctx.NumLsigArgs = 4;

    arg_0(s, ctx);
    __CPROVER_assert(stack_pop(s).byteslice[0] == 0xA0, "arg_0");
    arg_1(s, ctx);
    __CPROVER_assert(stack_pop(s).byteslice[0] == 0xA1, "arg_1");
    arg_2(s, ctx);
    __CPROVER_assert(stack_pop(s).byteslice[0] == 0xA2, "arg_2");
    arg_3(s, ctx);
    __CPROVER_assert(stack_pop(s).byteslice[0] == 0xA3, "arg_3");
    return 0;
}
""")
        assert result["verified"], f"arg shorthand failed:\n{result['stderr']}"


class TestItxnNext:
    """Tests for itxn_next opcode."""

    def test_itxn_next_multi_group(self, opcodes):
        """itxn_next allows submitting multiple inner txns in a group."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);

    itxn_begin(s, ctx);
    pushint(s, 100);
    itxn_field_set(s, ctx, Fee);

    itxn_next(s, BS, ctx);
    // First txn recorded, now building second
    __CPROVER_assert(ctx.inner_count == 1, "one recorded after next");
    __CPROVER_assert(ctx.building_itxn, "still building");

    pushint(s, 200);
    itxn_field_set(s, ctx, Fee);

    itxn_submit(BS, ctx);
    __CPROVER_assert(ctx.inner_count == 2, "two total after submit");

    // Read back both
    gitxn_field(s, ctx, 0, Fee);
    __CPROVER_assert(stack_pop(s).value == 100, "first fee");
    gitxn_field(s, ctx, 1, Fee);
    __CPROVER_assert(stack_pop(s).value == 200, "second fee");
    return 0;
}
""")
        assert result["verified"], f"itxn_next failed:\n{result['stderr']}"


# ============================================================================
# Phase 1: Byte Manipulation Ops
# ============================================================================

class TestExtract:
    """Tests for extract (immediate), extract_uint32, extract_uint16/64."""

    def test_extract_basic(self, opcodes):
        """extract 2 4 on an 8-byte value returns the correct 4 bytes."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    // Push 8-byte value: [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08]
    uint8_t data[8] = {0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08};
    stack_push(s, sv_bytes(data, 8));
    extract(s, 2, 4);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "result is bytes");
    __CPROVER_assert(r.byteslice_len == 4, "length is 4");
    __CPROVER_assert(r.byteslice[0] == 0x03, "byte 0");
    __CPROVER_assert(r.byteslice[1] == 0x04, "byte 1");
    __CPROVER_assert(r.byteslice[2] == 0x05, "byte 2");
    __CPROVER_assert(r.byteslice[3] == 0x06, "byte 3");
    return 0;
}
""")
        assert result["verified"], f"extract basic failed:\n{result['stderr']}"

    def test_extract_roundtrip_with_itob(self, opcodes):
        """itob → extract 2 4 → extract_uint32 should recover middle 4 bytes."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    // Push a concrete value, itob to get 8 bytes, extract middle 4
    pushint(s, 0x0102030405060708ULL);
    itob(s);
    // Now stack has [01,02,03,04,05,06,07,08]
    // extract 2 4 -> [03,04,05,06]
    extract(s, 2, 4);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice_len == 4, "len 4");
    __CPROVER_assert(r.byteslice[0] == 0x03, "b0");
    __CPROVER_assert(r.byteslice[1] == 0x04, "b1");
    __CPROVER_assert(r.byteslice[2] == 0x05, "b2");
    __CPROVER_assert(r.byteslice[3] == 0x06, "b3");
    return 0;
}
""")
        assert result["verified"], f"extract roundtrip failed:\n{result['stderr']}"

    def test_extract_uint32_at_offset(self, opcodes):
        """extract_uint32 correctly decodes big-endian 4 bytes."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t data[8] = {0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x02};
    stack_push(s, sv_bytes(data, 8));
    pushint(s, 0);  // offset
    extract_uint32(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(!r._is_bytes, "result is int");
    __CPROVER_assert(r.value == 1, "first uint32 is 1");

    stack_push(s, sv_bytes(data, 8));
    pushint(s, 4);  // offset
    extract_uint32(s);
    r = stack_pop(s);
    __CPROVER_assert(r.value == 2, "second uint32 is 2");
    return 0;
}
""")
        assert result["verified"], f"extract_uint32 failed:\n{result['stderr']}"


class TestSubstring:
    """Tests for substring (immediate) and substring3 (dynamic)."""

    def test_substring_immediate(self, opcodes):
        """substring 0 4 of 8-byte value returns first 4 bytes."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t data[8] = {0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF, 0x11, 0x22};
    stack_push(s, sv_bytes(data, 8));
    substring(s, 0, 4);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice_len == 4, "len 4");
    __CPROVER_assert(r.byteslice[0] == 0xAA, "b0");
    __CPROVER_assert(r.byteslice[3] == 0xDD, "b3");
    return 0;
}
""")
        assert result["verified"], f"substring immediate failed:\n{result['stderr']}"

    def test_extract_vs_substring_equivalence(self, opcodes):
        """extract S L ≡ substring S (S+L) for all valid ranges."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s1; stack_init(s1);
    Stack s2; stack_init(s2);
    uint8_t data[8] = {0x10, 0x20, 0x30, 0x40, 0x50, 0x60, 0x70, 0x80};

    // extract(2, 3)
    stack_push(s1, sv_bytes(data, 8));
    extract(s1, 2, 3);
    StackValue r1 = stack_pop(s1);

    // substring(2, 5)  (2+3=5)
    stack_push(s2, sv_bytes(data, 8));
    substring(s2, 2, 5);
    StackValue r2 = stack_pop(s2);

    __CPROVER_assert(sv_equal(r1, r2), "extract S L == substring S (S+L)");
    return 0;
}
""")
        assert result["verified"], f"extract vs substring failed:\n{result['stderr']}"


class TestReplace:
    """Tests for replace2 and replace3."""

    def test_replace2_preserves_length(self, opcodes):
        """replace2 doesn't change byteslice length."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t orig[8] = {0,0,0,0,0,0,0,0};
    uint8_t rep[2] = {0xFF, 0xFE};
    stack_push(s, sv_bytes(orig, 8));
    stack_push(s, sv_bytes(rep, 2));
    replace2(s, 3);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice_len == 8, "length preserved");
    __CPROVER_assert(r.byteslice[3] == 0xFF, "replaced byte 0");
    __CPROVER_assert(r.byteslice[4] == 0xFE, "replaced byte 1");
    __CPROVER_assert(r.byteslice[0] == 0, "untouched byte 0");
    __CPROVER_assert(r.byteslice[5] == 0, "untouched byte 5");
    return 0;
}
""")
        assert result["verified"], f"replace2 failed:\n{result['stderr']}"

    def test_replace3_dynamic(self, opcodes):
        """replace3 at dynamic offset works correctly."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t orig[8] = {1,2,3,4,5,6,7,8};
    uint8_t rep[3] = {0xA0, 0xB0, 0xC0};
    stack_push(s, sv_bytes(orig, 8));
    pushint(s, 2);  // offset
    stack_push(s, sv_bytes(rep, 3));
    replace3(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.byteslice_len == 8, "length preserved");
    __CPROVER_assert(r.byteslice[0] == 1, "untouched 0");
    __CPROVER_assert(r.byteslice[1] == 2, "untouched 1");
    __CPROVER_assert(r.byteslice[2] == 0xA0, "replaced 2");
    __CPROVER_assert(r.byteslice[3] == 0xB0, "replaced 3");
    __CPROVER_assert(r.byteslice[4] == 0xC0, "replaced 4");
    __CPROVER_assert(r.byteslice[5] == 6, "untouched 5");
    return 0;
}
""")
        assert result["verified"], f"replace3 failed:\n{result['stderr']}"


class TestGetSetByte:
    """Tests for getbyte and setbyte_op."""

    def test_getbyte_setbyte_roundtrip(self, opcodes):
        """setbyte then getbyte at same index returns the set value."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t data[4] = {0,0,0,0};
    // setbyte: set index 2 to 0x42
    stack_push(s, sv_bytes(data, 4));
    pushint(s, 2);     // index
    pushint(s, 0x42);  // value
    setbyte_op(s);
    // getbyte: read index 2
    pushint(s, 2);
    getbyte(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(!r._is_bytes, "result is int");
    __CPROVER_assert(r.value == 0x42, "roundtrip value");
    return 0;
}
""")
        assert result["verified"], f"getbyte/setbyte roundtrip failed:\n{result['stderr']}"

    def test_getbyte_reads_correct_index(self, opcodes):
        """getbyte at various indices returns correct bytes."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t data[4] = {0xAA, 0xBB, 0xCC, 0xDD};
    stack_push(s, sv_bytes(data, 4));
    pushint(s, 0);
    getbyte(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 0xAA, "byte 0");

    stack_push(s, sv_bytes(data, 4));
    pushint(s, 3);
    getbyte(s);
    r = stack_pop(s);
    __CPROVER_assert(r.value == 0xDD, "byte 3");
    return 0;
}
""")
        assert result["verified"], f"getbyte failed:\n{result['stderr']}"


# ============================================================================
# Phase 2: Dynamic Scratch + Wide Math
# ============================================================================

class TestDynamicScratch:
    """Tests for loads and stores (dynamic scratch access)."""

    def test_loads_stores_roundtrip(self, opcodes):
        """stores then loads at same slot returns the stored value."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);

    // stores: slot 5, value 42
    pushint(s, 5);    // slot
    pushint(s, 42);   // value
    stores(s, ctx);

    // loads: slot 5
    pushint(s, 5);
    loads(s, ctx);
    StackValue r = stack_pop(s);
    __CPROVER_assert(!r._is_bytes, "is int");
    __CPROVER_assert(r.value == 42, "roundtrip value");
    return 0;
}
""")
        assert result["verified"], f"loads/stores roundtrip failed:\n{result['stderr']}"

    def test_loads_matches_load(self, opcodes):
        """loads with pushint N ≡ load N."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);

    // Set scratch directly
    ctx.sp[10] = sv_int(99);

    // load 10
    Stack s1; stack_init(s1);
    load(s1, ctx, 10);
    StackValue r1 = stack_pop(s1);

    // loads with pushint 10
    Stack s2; stack_init(s2);
    pushint(s2, 10);
    loads(s2, ctx);
    StackValue r2 = stack_pop(s2);

    __CPROVER_assert(sv_equal(r1, r2), "loads matches load");
    return 0;
}
""")
        assert result["verified"], f"loads vs load failed:\n{result['stderr']}"


class TestWideMath:
    """Tests for divw, divmodw, expw."""

    def test_divw_basic(self, opcodes):
        """divw of mulw result recovers the original value."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    // 10 * 20 = 200 (fits in low word)
    pushint(s, 10);
    pushint(s, 20);
    mulw(s);
    // stack: high=0, low=200
    // divw: (0:200) / 10 = 20
    pushint(s, 10);
    divw(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 20, "divw recovers original");
    return 0;
}
""")
        assert result["verified"], f"divw basic failed:\n{result['stderr']}"

    def test_divmodw_basic(self, opcodes):
        """divmodw: quotient * divisor + remainder = original."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    // (0:17) divmod (0:5) = q=3, r=2
    pushint(s, 0);   // a_high
    pushint(s, 17);  // a_low
    pushint(s, 0);   // b_high
    pushint(s, 5);   // b_low
    divmodw(s);
    // stack: q_high, q_low, r_high, r_low
    StackValue r_low = stack_pop(s);
    StackValue r_high = stack_pop(s);
    StackValue q_low = stack_pop(s);
    StackValue q_high = stack_pop(s);
    __CPROVER_assert(q_high.value == 0, "q_high");
    __CPROVER_assert(q_low.value == 3, "q_low");
    __CPROVER_assert(r_high.value == 0, "r_high");
    __CPROVER_assert(r_low.value == 2, "r_low");
    // Verify: 3*5 + 2 = 17
    __CPROVER_assert(q_low.value * 5 + r_low.value == 17, "q*d+r == original");
    return 0;
}
""")
        assert result["verified"], f"divmodw basic failed:\n{result['stderr']}"

    def test_expw_basic(self, opcodes):
        """expw: base^2 via expw matches mulw."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s1; stack_init(s1);
    Stack s2; stack_init(s2);
    // expw: 100^2
    pushint(s1, 100);
    pushint(s1, 2);
    expw(s1);
    StackValue ew_high = stack_pop(s1);
    StackValue ew_low = stack_pop(s1);

    // mulw: 100*100
    pushint(s2, 100);
    pushint(s2, 100);
    mulw(s2);
    StackValue mw_high = stack_pop(s2);
    StackValue mw_low = stack_pop(s2);

    __CPROVER_assert(ew_high.value == mw_high.value, "high words match");
    __CPROVER_assert(ew_low.value == mw_low.value, "low words match");
    return 0;
}
""")
        assert result["verified"], f"expw basic failed:\n{result['stderr']}"


# ============================================================================
# Phase 3: Subroutine Frame Ops
# ============================================================================

class TestFrameOps:
    """Tests for proto, frame_dig, frame_bury, retsub_cleanup."""

    def test_proto_frame_dig(self, opcodes):
        """proto 2 1, then frame_dig -1 and frame_dig -2 retrieve args."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    // Push two args
    pushint(s, 100);  // arg0
    pushint(s, 200);  // arg1
    proto(s, ctx, 2, 1);
    // frame_dig -1 = last arg (200)
    frame_dig(s, ctx, -1);
    StackValue r1 = stack_pop(s);
    __CPROVER_assert(r1.value == 200, "frame_dig -1 = last arg");
    // frame_dig -2 = first arg (100)
    frame_dig(s, ctx, -2);
    StackValue r2 = stack_pop(s);
    __CPROVER_assert(r2.value == 100, "frame_dig -2 = first arg");
    return 0;
}
""")
        assert result["verified"], f"proto/frame_dig failed:\n{result['stderr']}"

    def test_frame_bury_dig_roundtrip(self, opcodes):
        """frame_bury then frame_dig returns same value."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    // Push two args
    pushint(s, 10);
    pushint(s, 20);
    proto(s, ctx, 2, 1);
    // frame_bury -1 with new value
    pushint(s, 999);
    frame_bury(s, ctx, -1);
    // frame_dig -1 should return 999
    frame_dig(s, ctx, -1);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 999, "frame_bury then frame_dig roundtrip");
    return 0;
}
""")
        assert result["verified"], f"frame_bury/dig roundtrip failed:\n{result['stderr']}"

    def test_retsub_cleanup_stack(self, opcodes):
        """After retsub_cleanup, stack has frame base + num_returns values."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    // Some pre-existing stack
    pushint(s, 1);  // below frame
    // Push two args
    pushint(s, 10);
    pushint(s, 20);
    proto(s, ctx, 2, 1);
    // Push a local variable (on top of args)
    pushint(s, 30);
    // Push the return value
    pushint(s, 42);
    // retsub_cleanup: should keep only 1 return value at frame base
    retsub_cleanup(s, ctx);
    // Stack should be: [1, 42] (pre-frame value + return value)
    __CPROVER_assert(s.currentSize == 2, "stack size after cleanup");
    StackValue ret = stack_pop(s);
    __CPROVER_assert(ret.value == 42, "return value preserved");
    StackValue pre = stack_pop(s);
    __CPROVER_assert(pre.value == 1, "pre-frame value preserved");
    return 0;
}
""")
        assert result["verified"], f"retsub_cleanup failed:\n{result['stderr']}"

    def test_nested_frames(self, opcodes):
        """Two proto calls; inner frame_dig doesn't see outer args."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    // Outer frame: 2 args
    pushint(s, 100);
    pushint(s, 200);
    proto(s, ctx, 2, 1);
    // Push inner args
    pushint(s, 300);
    pushint(s, 400);
    // Inner frame: 2 args
    proto(s, ctx, 2, 1);
    // frame_dig -1 in inner frame should be 400 (inner last arg), not 200 (outer)
    frame_dig(s, ctx, -1);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 400, "inner frame_dig sees inner args");
    __CPROVER_assert(ctx.frame_count == 2, "two frames active");
    return 0;
}
""")
        assert result["verified"], f"nested frames failed:\n{result['stderr']}"


# ============================================================================
# Phase 4: State Operations
# ============================================================================

class TestGlobalGetEx:
    """Tests for app_global_get_ex."""

    def test_global_get_ex_found(self, opcodes):
        """Put then get_ex returns value + found=1."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    ctx.CurrentApplicationID = 1;
    // global put: stack order is [key, value] (value on top)
    uint8_t key[] = {'h','e','l','l','o'};
    stack_push(s, sv_bytes(key, 5));  // key
    pushint(s, 42);                    // value (on top)
    app_global_put(s, BS, ctx);
    // global get_ex: stack order is [app_id, key] (key on top)
    pushint(s, 1);
    stack_push(s, sv_bytes(key, 5));
    app_global_get_ex(s, BS, ctx);
    StackValue found = stack_pop(s);
    StackValue val = stack_pop(s);
    __CPROVER_assert(found.value == 1, "found flag");
    __CPROVER_assert(val.value == 42, "value");
    return 0;
}
""")
        assert result["verified"], f"global_get_ex found failed:\n{result['stderr']}"

    def test_global_get_ex_not_found(self, opcodes):
        """get_ex on missing key returns 0 + found=0."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    uint8_t key[] = {'m','i','s','s'};
    pushint(s, 1);
    stack_push(s, sv_bytes(key, 4));
    app_global_get_ex(s, BS, ctx);
    StackValue found = stack_pop(s);
    StackValue val = stack_pop(s);
    __CPROVER_assert(found.value == 0, "not found");
    __CPROVER_assert(val.value == 0, "default zero");
    return 0;
}
""")
        assert result["verified"], f"global_get_ex not found failed:\n{result['stderr']}"


class TestLocalState:
    """Tests for local state operations."""

    def test_local_put_get_roundtrip(self, opcodes):
        """local put then get returns the stored value."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    Txn txn;
    __CPROVER_array_set(txn.Sender, 1);
    txn.ApplicationID = 1;
    // Opt in the sender
    ls_ensure_account(BS.locals, txn.Sender);

    uint8_t key[] = {'k','e','y'};
    // local put: stack [acct, key, value] with value on top
    // app_local_put pops: val, key, acct
    pushint(s, 0);  // account index = Sender
    stack_push(s, sv_bytes(key, 3));  // key
    pushint(s, 123);                   // value
    app_local_put(s, BS, txn, ctx);

    // local get: stack [acct, key] with key on top
    // app_local_get pops: key, acct
    pushint(s, 0);  // account
    stack_push(s, sv_bytes(key, 3));  // key
    app_local_get(s, BS, txn, ctx);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 123, "local get returns put value");
    return 0;
}
""")
        assert result["verified"], f"local put/get roundtrip failed:\n{result['stderr']}"

    def test_local_del_then_get(self, opcodes):
        """del then get returns default 0."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    Txn txn;
    __CPROVER_array_set(txn.Sender, 1);
    // Opt in the sender
    ls_ensure_account(BS.locals, txn.Sender);

    uint8_t key[] = {'x'};
    // put: [acct, key, value]
    pushint(s, 0);
    stack_push(s, sv_bytes(key, 1));
    pushint(s, 77);
    app_local_put(s, BS, txn, ctx);

    // del: [acct, key]
    pushint(s, 0);
    stack_push(s, sv_bytes(key, 1));
    app_local_del(s, BS, txn, ctx);

    // get: [acct, key]
    pushint(s, 0);
    stack_push(s, sv_bytes(key, 1));
    app_local_get(s, BS, txn, ctx);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 0, "deleted key returns 0");
    return 0;
}
""")
        assert result["verified"], f"local del then get failed:\n{result['stderr']}"

    def test_opted_in_after_local_put(self, opcodes):
        """app_opted_in returns 1 after local state exists."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    Txn txn;
    __CPROVER_array_set(txn.Sender, 1);

    // Before any local state, opted_in should be 0
    // app_opted_in pops: app_id, acct
    pushint(s, 0);  // acct (sender)
    pushint(s, 1);  // app_id
    app_opted_in(s, BS, txn, ctx);
    StackValue r1 = stack_pop(s);
    __CPROVER_assert(r1.value == 0, "not opted in initially");

    // Put some local state
    uint8_t key[] = {'z'};
    pushint(s, 0);                    // acct
    stack_push(s, sv_bytes(key, 1));  // key
    pushint(s, 1);                    // value
    app_local_put(s, BS, txn, ctx);

    // Now opted_in should be 1
    pushint(s, 0);  // acct
    pushint(s, 1);  // app_id
    app_opted_in(s, BS, txn, ctx);
    StackValue r2 = stack_pop(s);
    __CPROVER_assert(r2.value == 1, "opted in after put");
    return 0;
}
""")
        assert result["verified"], f"opted_in failed:\n{result['stderr']}"


class TestGlobalField:
    """Tests for global_field opcode."""

    def test_global_field_round(self, opcodes):
        """global_field(Round) returns BS.round."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    BS.round = 12345;
    global_field(s, BS, ctx, GF_Round);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 12345, "round matches");
    return 0;
}
""")
        assert result["verified"], f"global_field round failed:\n{result['stderr']}"

    def test_global_field_latest_timestamp(self, opcodes):
        """global_field(LatestTimestamp) returns BS.latest_timestamp."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    BS.latest_timestamp = 1700000000;
    global_field(s, BS, ctx, GF_LatestTimestamp);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 1700000000, "timestamp matches");
    return 0;
}
""")
        assert result["verified"], f"global_field timestamp failed:\n{result['stderr']}"

    def test_global_field_min_txn_fee(self, opcodes):
        """global_field(MinTxnFee) returns BS.min_txn_fee."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    // default is 1000
    global_field(s, BS, ctx, GF_MinTxnFee);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 1000, "min txn fee matches");
    return 0;
}
""")
        assert result["verified"], f"global_field min_txn_fee failed:\n{result['stderr']}"

    def test_global_field_current_app_id(self, opcodes):
        """global_field(CurrentApplicationID) returns ctx.CurrentApplicationID."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    ctx.CurrentApplicationID = 42;
    global_field(s, BS, ctx, GF_CurrentApplicationID);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 42, "app id matches");
    return 0;
}
""")
        assert result["verified"], f"global_field current_app_id failed:\n{result['stderr']}"


class TestBalance:
    """Tests for balance and min_balance ops."""

    def test_balance_app(self, opcodes):
        """balance with index 0 returns sender's balance from AccountsState."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    BlockchainState BS; bs_init(BS);
    Txn txn; memset(&txn, 0, sizeof(Txn));
    // Set up sender address
    memset(txn.Sender, 0xAA, 32);
    // Add sender to accounts state with known balance
    BS.accounts.entries[0].active = true;
    memcpy(BS.accounts.entries[0].address, txn.Sender, 32);
    BS.accounts.entries[0].balance = 5000000;
    BS.accounts.count = 1;
    pushint(s, 0);  // index 0 = Sender
    balance_op(s, BS, txn);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 5000000, "sender balance");
    return 0;
}
""")
        assert result["verified"], f"balance failed:\n{result['stderr']}"

    def test_min_balance(self, opcodes):
        """min_balance returns default for index 0."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    BlockchainState BS; bs_init(BS);
    Txn txn; memset(&txn, 0, sizeof(Txn));
    pushint(s, 0);
    min_balance_op(s, BS, txn);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 100000, "default min balance");
    return 0;
}
""")
        assert result["verified"], f"min_balance failed:\n{result['stderr']}"


# ============================================================================
# Phase 5: Box Storage
# ============================================================================

class TestBoxOps:
    """Tests for box_create, box_del, box_get, box_put, box_len, box_extract, box_replace."""

    def test_box_create_get(self, opcodes):
        """Create then get returns zero-filled bytes + found=1."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    Txn txn;

    uint8_t key[] = {'b','o','x','1'};
    // box_create: key="box1", size=8
    stack_push(s, sv_bytes(key, 4));
    pushint(s, 8);
    box_create_op(s, BS, txn, ctx);
    StackValue created = stack_pop(s);
    __CPROVER_assert(created.value == 1, "created=1");

    // box_get
    stack_push(s, sv_bytes(key, 4));
    box_get_op(s, BS, txn, ctx);
    StackValue found = stack_pop(s);
    StackValue data = stack_pop(s);
    __CPROVER_assert(found.value == 1, "found=1");
    __CPROVER_assert(data._is_bytes, "is bytes");
    __CPROVER_assert(data.byteslice_len == 8, "len=8");
    // All zeros
    for (int i = 0; i < 8; i++) {
        __CPROVER_assert(data.byteslice[i] == 0, "zero-filled");
    }
    return 0;
}
""")
        assert result["verified"], f"box create/get failed:\n{result['stderr']}"

    def test_box_put_get_roundtrip(self, opcodes):
        """Create, put, get returns the written value."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    Txn txn;

    uint8_t key[] = {'b'};
    uint8_t val[4] = {0xDE, 0xAD, 0xBE, 0xEF};
    // create
    stack_push(s, sv_bytes(key, 1));
    pushint(s, 4);
    box_create_op(s, BS, txn, ctx);
    stack_pop(s);  // discard created flag

    // put
    stack_push(s, sv_bytes(key, 1));
    stack_push(s, sv_bytes(val, 4));
    box_put_op(s, BS, txn, ctx);

    // get
    stack_push(s, sv_bytes(key, 1));
    box_get_op(s, BS, txn, ctx);
    StackValue found = stack_pop(s);
    StackValue data = stack_pop(s);
    __CPROVER_assert(found.value == 1, "found");
    __CPROVER_assert(data.byteslice[0] == 0xDE, "b0");
    __CPROVER_assert(data.byteslice[1] == 0xAD, "b1");
    __CPROVER_assert(data.byteslice[2] == 0xBE, "b2");
    __CPROVER_assert(data.byteslice[3] == 0xEF, "b3");
    return 0;
}
""")
        assert result["verified"], f"box put/get roundtrip failed:\n{result['stderr']}"

    def test_box_del_then_get(self, opcodes):
        """Del then get returns found=0."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    Txn txn;

    uint8_t key[] = {'d'};
    // create
    stack_push(s, sv_bytes(key, 1));
    pushint(s, 4);
    box_create_op(s, BS, txn, ctx);
    stack_pop(s);

    // del
    stack_push(s, sv_bytes(key, 1));
    box_del_op(s, BS, txn, ctx);
    stack_pop(s);  // discard deleted flag

    // get
    stack_push(s, sv_bytes(key, 1));
    box_get_op(s, BS, txn, ctx);
    StackValue found = stack_pop(s);
    stack_pop(s);  // discard data
    __CPROVER_assert(found.value == 0, "not found after del");
    return 0;
}
""")
        assert result["verified"], f"box del then get failed:\n{result['stderr']}"

    def test_box_len_matches(self, opcodes):
        """box_len returns create size."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    Txn txn;

    uint8_t key[] = {'l'};
    stack_push(s, sv_bytes(key, 1));
    pushint(s, 16);
    box_create_op(s, BS, txn, ctx);
    stack_pop(s);

    stack_push(s, sv_bytes(key, 1));
    box_len_op(s, BS, txn, ctx);
    StackValue found = stack_pop(s);
    StackValue len = stack_pop(s);
    __CPROVER_assert(found.value == 1, "found");
    __CPROVER_assert(len.value == 16, "len matches create size");
    return 0;
}
""")
        assert result["verified"], f"box_len failed:\n{result['stderr']}"

    def test_box_extract_offset(self, opcodes):
        """box_extract at offset returns correct slice."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    Txn txn;

    uint8_t key[] = {'e'};
    uint8_t val[8] = {0x10, 0x20, 0x30, 0x40, 0x50, 0x60, 0x70, 0x80};
    // create + put
    stack_push(s, sv_bytes(key, 1));
    pushint(s, 8);
    box_create_op(s, BS, txn, ctx);
    stack_pop(s);
    stack_push(s, sv_bytes(key, 1));
    stack_push(s, sv_bytes(val, 8));
    box_put_op(s, BS, txn, ctx);

    // box_extract: offset=2, length=3
    stack_push(s, sv_bytes(key, 1));
    pushint(s, 2);
    pushint(s, 3);
    box_extract_op(s, BS, txn, ctx);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice_len == 3, "len 3");
    __CPROVER_assert(r.byteslice[0] == 0x30, "b0");
    __CPROVER_assert(r.byteslice[1] == 0x40, "b1");
    __CPROVER_assert(r.byteslice[2] == 0x50, "b2");
    return 0;
}
""")
        assert result["verified"], f"box_extract failed:\n{result['stderr']}"

    def test_box_replace_partial(self, opcodes):
        """box_replace at offset, rest unchanged."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    Txn txn;

    uint8_t key[] = {'r'};
    uint8_t val[8] = {1,2,3,4,5,6,7,8};
    uint8_t rep[2] = {0xAA, 0xBB};
    // create + put
    stack_push(s, sv_bytes(key, 1));
    pushint(s, 8);
    box_create_op(s, BS, txn, ctx);
    stack_pop(s);
    stack_push(s, sv_bytes(key, 1));
    stack_push(s, sv_bytes(val, 8));
    box_put_op(s, BS, txn, ctx);

    // box_replace: offset=3
    stack_push(s, sv_bytes(key, 1));
    pushint(s, 3);
    stack_push(s, sv_bytes(rep, 2));
    box_replace_op(s, BS, txn, ctx);

    // box_get to verify
    stack_push(s, sv_bytes(key, 1));
    box_get_op(s, BS, txn, ctx);
    stack_pop(s);  // found
    StackValue data = stack_pop(s);
    __CPROVER_assert(data.byteslice[0] == 1, "unchanged 0");
    __CPROVER_assert(data.byteslice[2] == 3, "unchanged 2");
    __CPROVER_assert(data.byteslice[3] == 0xAA, "replaced 3");
    __CPROVER_assert(data.byteslice[4] == 0xBB, "replaced 4");
    __CPROVER_assert(data.byteslice[5] == 6, "unchanged 5");
    return 0;
}
""")
        assert result["verified"], f"box_replace failed:\n{result['stderr']}"

    def test_box_resize_grow(self, opcodes):
        """box_resize growing zero-pads new bytes."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    Txn txn;

    uint8_t key[] = {'r','g'};
    uint8_t val[4] = {0xAA, 0xBB, 0xCC, 0xDD};
    // create size=4, put data
    stack_push(s, sv_bytes(key, 2));
    pushint(s, 4);
    box_create_op(s, BS, txn, ctx);
    stack_pop(s);
    stack_push(s, sv_bytes(key, 2));
    stack_push(s, sv_bytes(val, 4));
    box_put_op(s, BS, txn, ctx);

    // resize to 8
    stack_push(s, sv_bytes(key, 2));
    pushint(s, 8);
    box_resize_op(s, BS, txn, ctx);

    // verify via box_get
    stack_push(s, sv_bytes(key, 2));
    box_get_op(s, BS, txn, ctx);
    StackValue found = stack_pop(s);
    StackValue data = stack_pop(s);
    __CPROVER_assert(found.value == 1, "found");
    __CPROVER_assert(data.byteslice_len == 8, "new len=8");
    __CPROVER_assert(data.byteslice[0] == 0xAA, "orig 0");
    __CPROVER_assert(data.byteslice[3] == 0xDD, "orig 3");
    __CPROVER_assert(data.byteslice[4] == 0, "padded 4");
    __CPROVER_assert(data.byteslice[7] == 0, "padded 7");
    return 0;
}
""")
        assert result["verified"], f"box_resize grow failed:\n{result['stderr']}"

    def test_box_resize_shrink(self, opcodes):
        """box_resize shrinking truncates from end."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    Txn txn;

    uint8_t key[] = {'r','s'};
    uint8_t val[8] = {1,2,3,4,5,6,7,8};
    // create size=8, put data
    stack_push(s, sv_bytes(key, 2));
    pushint(s, 8);
    box_create_op(s, BS, txn, ctx);
    stack_pop(s);
    stack_push(s, sv_bytes(key, 2));
    stack_push(s, sv_bytes(val, 8));
    box_put_op(s, BS, txn, ctx);

    // resize to 3
    stack_push(s, sv_bytes(key, 2));
    pushint(s, 3);
    box_resize_op(s, BS, txn, ctx);

    // verify via box_len and box_get
    stack_push(s, sv_bytes(key, 2));
    box_len_op(s, BS, txn, ctx);
    StackValue f = stack_pop(s);
    StackValue len = stack_pop(s);
    __CPROVER_assert(f.value == 1, "found");
    __CPROVER_assert(len.value == 3, "shrunk to 3");

    stack_push(s, sv_bytes(key, 2));
    box_get_op(s, BS, txn, ctx);
    stack_pop(s);
    StackValue data = stack_pop(s);
    __CPROVER_assert(data.byteslice_len == 3, "data len=3");
    __CPROVER_assert(data.byteslice[0] == 1, "kept 0");
    __CPROVER_assert(data.byteslice[1] == 2, "kept 1");
    __CPROVER_assert(data.byteslice[2] == 3, "kept 2");
    return 0;
}
""")
        assert result["verified"], f"box_resize shrink failed:\n{result['stderr']}"

    def test_box_resize_same_size(self, opcodes):
        """box_resize to same size is a no-op."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    Txn txn;

    uint8_t key[] = {'n'};
    uint8_t val[4] = {0x10, 0x20, 0x30, 0x40};
    stack_push(s, sv_bytes(key, 1));
    pushint(s, 4);
    box_create_op(s, BS, txn, ctx);
    stack_pop(s);
    stack_push(s, sv_bytes(key, 1));
    stack_push(s, sv_bytes(val, 4));
    box_put_op(s, BS, txn, ctx);

    // resize to same size
    stack_push(s, sv_bytes(key, 1));
    pushint(s, 4);
    box_resize_op(s, BS, txn, ctx);

    // verify unchanged
    stack_push(s, sv_bytes(key, 1));
    box_get_op(s, BS, txn, ctx);
    stack_pop(s);
    StackValue data = stack_pop(s);
    __CPROVER_assert(data.byteslice_len == 4, "same len");
    __CPROVER_assert(data.byteslice[0] == 0x10, "b0");
    __CPROVER_assert(data.byteslice[3] == 0x40, "b3");
    return 0;
}
""")
        assert result["verified"], f"box_resize same size failed:\n{result['stderr']}"

    def test_box_splice_equal_length(self, opcodes):
        """box_splice replacing same-length segment (simple replacement)."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    Txn txn;

    uint8_t key[] = {'s','e'};
    uint8_t val[8] = {1,2,3,4,5,6,7,8};
    // create + put
    stack_push(s, sv_bytes(key, 2));
    pushint(s, 8);
    box_create_op(s, BS, txn, ctx);
    stack_pop(s);
    stack_push(s, sv_bytes(key, 2));
    stack_push(s, sv_bytes(val, 8));
    box_put_op(s, BS, txn, ctx);

    // splice: offset=2, delete=3, replacement={0xAA, 0xBB, 0xCC}
    uint8_t rep[3] = {0xAA, 0xBB, 0xCC};
    stack_push(s, sv_bytes(key, 2));
    pushint(s, 2);   // offset
    pushint(s, 3);   // delete count
    stack_push(s, sv_bytes(rep, 3));  // replacement
    box_splice_op(s, BS, txn, ctx);

    // verify: {1, 2, 0xAA, 0xBB, 0xCC, 6, 7, 8}
    stack_push(s, sv_bytes(key, 2));
    box_get_op(s, BS, txn, ctx);
    stack_pop(s);
    StackValue data = stack_pop(s);
    __CPROVER_assert(data.byteslice_len == 8, "size unchanged");
    __CPROVER_assert(data.byteslice[0] == 1, "before splice");
    __CPROVER_assert(data.byteslice[1] == 2, "before splice");
    __CPROVER_assert(data.byteslice[2] == 0xAA, "spliced 0");
    __CPROVER_assert(data.byteslice[3] == 0xBB, "spliced 1");
    __CPROVER_assert(data.byteslice[4] == 0xCC, "spliced 2");
    __CPROVER_assert(data.byteslice[5] == 6, "after splice");
    __CPROVER_assert(data.byteslice[6] == 7, "after splice");
    __CPROVER_assert(data.byteslice[7] == 8, "after splice");
    return 0;
}
""")
        assert result["verified"], f"box_splice equal length failed:\n{result['stderr']}"

    def test_box_splice_insert_longer(self, opcodes):
        """box_splice with replacement longer than delete: end bytes trimmed."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    Txn txn;

    uint8_t key[] = {'s','l'};
    uint8_t val[8] = {1,2,3,4,5,6,7,8};
    stack_push(s, sv_bytes(key, 2));
    pushint(s, 8);
    box_create_op(s, BS, txn, ctx);
    stack_pop(s);
    stack_push(s, sv_bytes(key, 2));
    stack_push(s, sv_bytes(val, 8));
    box_put_op(s, BS, txn, ctx);

    // splice: offset=2, delete=1, replacement={0xAA, 0xBB, 0xCC} (3 bytes replacing 1)
    // logical result: {1, 2, 0xAA, 0xBB, 0xCC, 4, 5, 6, 7, 8} = 10 bytes
    // trimmed to 8: {1, 2, 0xAA, 0xBB, 0xCC, 4, 5, 6}
    uint8_t rep[3] = {0xAA, 0xBB, 0xCC};
    stack_push(s, sv_bytes(key, 2));
    pushint(s, 2);
    pushint(s, 1);
    stack_push(s, sv_bytes(rep, 3));
    box_splice_op(s, BS, txn, ctx);

    stack_push(s, sv_bytes(key, 2));
    box_get_op(s, BS, txn, ctx);
    stack_pop(s);
    StackValue data = stack_pop(s);
    __CPROVER_assert(data.byteslice_len == 8, "size unchanged");
    __CPROVER_assert(data.byteslice[0] == 1, "b0");
    __CPROVER_assert(data.byteslice[1] == 2, "b1");
    __CPROVER_assert(data.byteslice[2] == 0xAA, "spliced");
    __CPROVER_assert(data.byteslice[3] == 0xBB, "spliced");
    __CPROVER_assert(data.byteslice[4] == 0xCC, "spliced");
    __CPROVER_assert(data.byteslice[5] == 4, "shifted");
    __CPROVER_assert(data.byteslice[6] == 5, "shifted");
    __CPROVER_assert(data.byteslice[7] == 6, "trimmed end");
    return 0;
}
""")
        assert result["verified"], f"box_splice insert longer failed:\n{result['stderr']}"

    def test_box_splice_delete_more(self, opcodes):
        """box_splice with delete > replacement: zero-padded at end."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    Txn txn;

    uint8_t key[] = {'s','d'};
    uint8_t val[8] = {1,2,3,4,5,6,7,8};
    stack_push(s, sv_bytes(key, 2));
    pushint(s, 8);
    box_create_op(s, BS, txn, ctx);
    stack_pop(s);
    stack_push(s, sv_bytes(key, 2));
    stack_push(s, sv_bytes(val, 8));
    box_put_op(s, BS, txn, ctx);

    // splice: offset=1, delete=4, replacement={0xFF} (1 byte replacing 4)
    // logical result: {1, 0xFF, 6, 7, 8} = 5 bytes
    // padded to 8: {1, 0xFF, 6, 7, 8, 0, 0, 0}
    uint8_t rep[1] = {0xFF};
    stack_push(s, sv_bytes(key, 2));
    pushint(s, 1);
    pushint(s, 4);
    stack_push(s, sv_bytes(rep, 1));
    box_splice_op(s, BS, txn, ctx);

    stack_push(s, sv_bytes(key, 2));
    box_get_op(s, BS, txn, ctx);
    stack_pop(s);
    StackValue data = stack_pop(s);
    __CPROVER_assert(data.byteslice_len == 8, "size unchanged");
    __CPROVER_assert(data.byteslice[0] == 1, "b0");
    __CPROVER_assert(data.byteslice[1] == 0xFF, "replaced");
    __CPROVER_assert(data.byteslice[2] == 6, "shifted");
    __CPROVER_assert(data.byteslice[3] == 7, "shifted");
    __CPROVER_assert(data.byteslice[4] == 8, "shifted");
    __CPROVER_assert(data.byteslice[5] == 0, "zero-padded");
    __CPROVER_assert(data.byteslice[6] == 0, "zero-padded");
    __CPROVER_assert(data.byteslice[7] == 0, "zero-padded");
    return 0;
}
""")
        assert result["verified"], f"box_splice delete more failed:\n{result['stderr']}"

    def test_box_splice_at_start(self, opcodes):
        """box_splice at offset 0."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    Txn txn;

    uint8_t key[] = {'s','0'};
    uint8_t val[4] = {0x10, 0x20, 0x30, 0x40};
    stack_push(s, sv_bytes(key, 2));
    pushint(s, 4);
    box_create_op(s, BS, txn, ctx);
    stack_pop(s);
    stack_push(s, sv_bytes(key, 2));
    stack_push(s, sv_bytes(val, 4));
    box_put_op(s, BS, txn, ctx);

    // splice at offset 0: delete 2, insert {0xAA, 0xBB}
    uint8_t rep[2] = {0xAA, 0xBB};
    stack_push(s, sv_bytes(key, 2));
    pushint(s, 0);
    pushint(s, 2);
    stack_push(s, sv_bytes(rep, 2));
    box_splice_op(s, BS, txn, ctx);

    // result: {0xAA, 0xBB, 0x30, 0x40}
    stack_push(s, sv_bytes(key, 2));
    box_get_op(s, BS, txn, ctx);
    stack_pop(s);
    StackValue data = stack_pop(s);
    __CPROVER_assert(data.byteslice_len == 4, "size unchanged");
    __CPROVER_assert(data.byteslice[0] == 0xAA, "new 0");
    __CPROVER_assert(data.byteslice[1] == 0xBB, "new 1");
    __CPROVER_assert(data.byteslice[2] == 0x30, "orig 2");
    __CPROVER_assert(data.byteslice[3] == 0x40, "orig 3");
    return 0;
}
""")
        assert result["verified"], f"box_splice at start failed:\n{result['stderr']}"


class TestBoxHelpers:
    """Tests for box state helper functions (box_create_entry, box_put_entry, box_get_entry, etc.)."""

    def test_box_create_and_get_entry(self, opcodes):
        """box_create_entry creates a zero-filled box, box_get_entry retrieves it."""
        result = opcodes.verify_cpp("""
int main() {
    BlockchainState BS; bs_init(BS);
    uint8_t key[] = {'t','e','s','t'};

    box_create_entry(BS.boxes, key, 4, 8);

    uint32_t out_len = 0;
    uint8_t* data = box_get_entry(BS.boxes, key, 4, &out_len);
    __CPROVER_assert(data != 0, "box found");
    __CPROVER_assert(out_len == 8, "box len is 8");
    __CPROVER_assert(data[0] == 0, "zero-filled");
    __CPROVER_assert(data[7] == 0, "zero-filled end");
    return 0;
}
""")
        assert result["verified"], f"box_create_and_get_entry failed:\n{result['stderr']}"

    def test_box_put_get_entry(self, opcodes):
        """box_put_entry stores data, box_get_entry retrieves it."""
        result = opcodes.verify_cpp("""
int main() {
    BlockchainState BS; bs_init(BS);
    uint8_t key[] = {'k','1'};
    uint8_t val[] = {0xAA, 0xBB, 0xCC};

    box_put_entry(BS.boxes, key, 2, val, 3);

    uint32_t out_len = 0;
    uint8_t* data = box_get_entry(BS.boxes, key, 2, &out_len);
    __CPROVER_assert(data != 0, "box found");
    __CPROVER_assert(out_len == 3, "data len");
    __CPROVER_assert(data[0] == 0xAA, "byte 0");
    __CPROVER_assert(data[1] == 0xBB, "byte 1");
    __CPROVER_assert(data[2] == 0xCC, "byte 2");
    return 0;
}
""")
        assert result["verified"], f"box_put_get_entry failed:\n{result['stderr']}"

    def test_box_del_entry(self, opcodes):
        """box_del_entry removes a box, subsequent get returns NULL."""
        result = opcodes.verify_cpp("""
int main() {
    BlockchainState BS; bs_init(BS);
    uint8_t key[] = {'d'};
    uint8_t val[] = {0x01};

    box_put_entry(BS.boxes, key, 1, val, 1);
    __CPROVER_assert(box_exists(BS.boxes, key, 1), "exists before del");

    box_del_entry(BS.boxes, key, 1);
    __CPROVER_assert(!box_exists(BS.boxes, key, 1), "gone after del");

    uint32_t out_len = 0;
    uint8_t* data = box_get_entry(BS.boxes, key, 1, &out_len);
    __CPROVER_assert(data == 0, "get returns NULL");
    return 0;
}
""")
        assert result["verified"], f"box_del_entry failed:\n{result['stderr']}"

    def test_box_overwrite_entry(self, opcodes):
        """box_put_entry overwrites existing box data."""
        result = opcodes.verify_cpp("""
int main() {
    BlockchainState BS; bs_init(BS);
    uint8_t key[] = {'o','w'};
    uint8_t v1[] = {0x11, 0x22};
    uint8_t v2[] = {0x33, 0x44, 0x55};

    box_put_entry(BS.boxes, key, 2, v1, 2);
    box_put_entry(BS.boxes, key, 2, v2, 3);

    uint32_t out_len = 0;
    uint8_t* data = box_get_entry(BS.boxes, key, 2, &out_len);
    __CPROVER_assert(data != 0, "box found");
    __CPROVER_assert(out_len == 3, "new len");
    __CPROVER_assert(data[0] == 0x33, "new byte 0");
    __CPROVER_assert(data[1] == 0x44, "new byte 1");
    __CPROVER_assert(data[2] == 0x55, "new byte 2");
    return 0;
}
""")
        assert result["verified"], f"box_overwrite_entry failed:\n{result['stderr']}"

    def test_box_create_idempotent(self, opcodes):
        """box_create_entry on existing box returns existing entry unchanged."""
        result = opcodes.verify_cpp("""
int main() {
    BlockchainState BS; bs_init(BS);
    uint8_t key[] = {'x'};
    uint8_t val[] = {0xFF};

    box_put_entry(BS.boxes, key, 1, val, 1);
    BoxEntry* e = box_create_entry(BS.boxes, key, 1, 4);

    // Should return existing entry, not overwrite with zeros
    __CPROVER_assert(e->data_len == 1, "original len preserved");
    __CPROVER_assert(e->data[0] == 0xFF, "original data preserved");
    return 0;
}
""")
        assert result["verified"], f"box_create_idempotent failed:\n{result['stderr']}"


# ============================================================================
# Phase 6: Group Txn + Inner Txn
# ============================================================================

class TestGroupTxn:
    """Tests for gtxn_field and gtxns_field."""

    def test_gtxn_field_sender(self, opcodes):
        """gtxn 0 Sender returns group txn 0 sender."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    TxnGroup tg; tg_init(tg);
    tg.size = 2;
    __CPROVER_array_set(tg.txns[0].Sender, 0xAA);
    __CPROVER_array_set(tg.txns[1].Sender, 0xBB);
    tg.txns[0].Fee = 1000;
    tg.txns[1].Fee = 2000;

    gtxn_field(s, tg, 0, Sender);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice_len == 32, "32 bytes");
    __CPROVER_assert(r.byteslice[0] == 0xAA, "sender byte");

    gtxn_field(s, tg, 1, Fee);
    StackValue r2 = stack_pop(s);
    __CPROVER_assert(r2.value == 2000, "txn 1 fee");
    return 0;
}
""")
        assert result["verified"], f"gtxn_field failed:\n{result['stderr']}"

    def test_gtxns_dynamic(self, opcodes):
        """gtxns with dynamic index from stack works."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    TxnGroup tg; tg_init(tg);
    tg.size = 2;
    tg.txns[0].Fee = 100;
    tg.txns[1].Fee = 200;

    pushint(s, 1);
    gtxns_field(s, tg, Fee);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 200, "dynamic gtxns fee");
    return 0;
}
""")
        assert result["verified"], f"gtxns failed:\n{result['stderr']}"


class TestInnerTxn:
    """Tests for itxn_begin, itxn_field, itxn_submit, itxn_field_read."""

    def test_itxn_begin_submit(self, opcodes):
        """begin + set fields + submit succeeds."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);

    itxn_begin(s, ctx);
    __CPROVER_assert(ctx.building_itxn, "building flag set");

    // Set fee
    pushint(s, 1000);
    itxn_field_set(s, ctx, Fee);

    // Set amount
    pushint(s, 5000);
    itxn_field_set(s, ctx, Amount);

    // Submit
    itxn_submit(BS, ctx);
    __CPROVER_assert(!ctx.building_itxn, "building flag cleared");
    __CPROVER_assert(ctx.inner_count == 1, "one inner txn");
    __CPROVER_assert(ctx.inner_txns[0].submitted, "submitted flag");
    return 0;
}
""")
        assert result["verified"], f"itxn begin/submit failed:\n{result['stderr']}"

    def test_itxn_field_read_after_submit(self, opcodes):
        """Can read back submitted fields."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);

    itxn_begin(s, ctx);
    pushint(s, 777);
    itxn_field_set(s, ctx, Fee);
    pushint(s, 999);
    itxn_field_set(s, ctx, Amount);
    itxn_submit(BS, ctx);

    // Read back fee
    itxn_field_read(s, ctx, Fee);
    StackValue r1 = stack_pop(s);
    __CPROVER_assert(r1.value == 777, "fee readback");

    // Read back amount
    itxn_field_read(s, ctx, Amount);
    StackValue r2 = stack_pop(s);
    __CPROVER_assert(r2.value == 999, "amount readback");
    return 0;
}
""")
        assert result["verified"], f"itxn field read failed:\n{result['stderr']}"

    def test_gitxn_field(self, opcodes):
        """gitxn reads inner txn by group index."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);

    // Submit two inner txns
    itxn_begin(s, ctx);
    pushint(s, 100);
    itxn_field_set(s, ctx, Fee);
    itxn_submit(BS, ctx);

    itxn_begin(s, ctx);
    pushint(s, 200);
    itxn_field_set(s, ctx, Fee);
    itxn_submit(BS, ctx);

    __CPROVER_assert(ctx.inner_count == 2, "two inner txns");

    // gitxn 0 Fee
    gitxn_field(s, ctx, 0, Fee);
    StackValue r1 = stack_pop(s);
    __CPROVER_assert(r1.value == 100, "first inner fee");

    // gitxn 1 Fee
    gitxn_field(s, ctx, 1, Fee);
    StackValue r2 = stack_pop(s);
    __CPROVER_assert(r2.value == 200, "second inner fee");
    return 0;
}
""")
        assert result["verified"], f"gitxn_field failed:\n{result['stderr']}"


# ============================================================================
# Inner transaction state effects
# ============================================================================

class TestItxnStateEffects:
    """Tests that inner transactions apply state effects."""

    def test_itxn_payment_deducts_balance(self, opcodes):
        """Payment inner txn deducts Amount from app_balance."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    BS.app_balance = 10000;

    itxn_begin(s, ctx);
    pushint(s, 1);  // TypeEnum = pay
    itxn_field_set(s, ctx, TypeEnum);
    pushint(s, 3000);
    itxn_field_set(s, ctx, Amount);
    itxn_submit(BS, ctx);

    __CPROVER_assert(BS.app_balance == 7000, "balance deducted");
    return 0;
}
""")
        assert result["verified"], f"itxn payment deduct failed:\n{result['stderr']}"

    def test_itxn_payment_insufficient_panics(self, opcodes):
        """Payment inner txn with insufficient balance panics."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    BS.app_balance = 100;

    itxn_begin(s, ctx);
    pushint(s, 1);  // TypeEnum = pay
    itxn_field_set(s, ctx, TypeEnum);
    pushint(s, 500);  // More than balance
    itxn_field_set(s, ctx, Amount);
    itxn_submit(BS, ctx);

    __CPROVER_assert(__avm_panicked, "should panic on insufficient balance");
    return 0;
}
""")
        assert result["verified"], f"itxn payment insufficient failed:\n{result['stderr']}"

    def test_itxn_payment_multiple(self, opcodes):
        """Multiple payment inner txns deduct cumulatively."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    BS.app_balance = 10000;

    // First payment: 2000
    itxn_begin(s, ctx);
    pushint(s, 1);
    itxn_field_set(s, ctx, TypeEnum);
    pushint(s, 2000);
    itxn_field_set(s, ctx, Amount);
    itxn_submit(BS, ctx);

    __CPROVER_assert(BS.app_balance == 8000, "after first payment");

    // Second payment: 3000
    itxn_begin(s, ctx);
    pushint(s, 1);
    itxn_field_set(s, ctx, TypeEnum);
    pushint(s, 3000);
    itxn_field_set(s, ctx, Amount);
    itxn_submit(BS, ctx);

    __CPROVER_assert(BS.app_balance == 5000, "after second payment");
    return 0;
}
""")
        assert result["verified"], f"itxn multiple payments failed:\n{result['stderr']}"

    def test_itxn_asset_transfer_updates_holdings(self, opcodes):
        """Asset transfer inner txn updates sender and receiver holdings."""
        result = opcodes.verify_cpp("""
int main() {
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);

    // Set up app address (sender for inner txns)
    // Use memset instead of __CPROVER_array_set to avoid SAT solver
    // interaction issues with _addr_is_set loop in close-to handling.
    memset(ctx.CurrentApplicationAddress, 0xAA, 32);

    // Set up sender holding (app address, 0xAA...)
    AssetHoldingState& ahs = BS.asset_holdings;
    ahs.entries[0].active = true;
    ahs.entries[0].asset_id = 42;
    memset(ahs.entries[0].account, 0xAA, 32);
    ahs.entries[0].balance = 1000;
    ahs.entries[0].frozen = false;
    ahs.entries[0].opted_in = true;
    // Set up receiver holding (0xBB...)
    ahs.entries[1].active = true;
    ahs.entries[1].asset_id = 42;
    memset(ahs.entries[1].account, 0xBB, 32);
    ahs.entries[1].balance = 500;
    ahs.entries[1].frozen = false;
    ahs.entries[1].opted_in = true;
    ahs.count = 2;

    // Build inner txn directly (avoid 32-byte stack copies)
    Txn itxn;
    memset(&itxn, 0, sizeof(Txn));
    itxn.TypeEnum = 4;  // axfer
    itxn.AssetAmount = 300;
    memset(itxn.AssetReceiver, 0xBB, 32);
    itxn.XferAsset = 42;

    // Apply effects directly
    _itxn_apply_effects(BS, ctx, itxn);

    __CPROVER_assert(!__avm_panicked, "no panic");
    __CPROVER_assert(ahs.entries[0].balance == 700, "sender balance reduced");
    __CPROVER_assert(ahs.entries[1].balance == 800, "receiver balance increased");
    return 0;
}
""")
        assert result["verified"], f"itxn asset transfer failed:\n{result['stderr']}"

    def test_itxn_asset_transfer_unmodeled_noop(self, opcodes):
        """Asset transfer with unmodeled holdings is a no-op (sound)."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    BS.app_balance = 5000;

    uint8_t receiver[32]; memset(receiver, 0xBB, 32);

    itxn_begin(s, ctx);
    pushint(s, 4);  // TypeEnum = axfer
    itxn_field_set(s, ctx, TypeEnum);
    pushint(s, 100);
    itxn_field_set(s, ctx, Amount);
    stack_push(s, sv_bytes(receiver, 32));
    itxn_field_set(s, ctx, Receiver);
    pushint(s, 99);
    itxn_field_set(s, ctx, Assets);

    itxn_submit(BS, ctx);

    // No panic, no state change (holdings not modeled)
    __CPROVER_assert(!__avm_panicked, "should not panic");
    __CPROVER_assert(BS.app_balance == 5000, "app balance unchanged");
    return 0;
}
""")
        assert result["verified"], f"itxn asset transfer unmodeled failed:\n{result['stderr']}"

    def test_itxn_next_applies_effects(self, opcodes):
        """itxn_next applies state effects before starting next txn."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    BS.app_balance = 10000;

    itxn_begin(s, ctx);
    pushint(s, 1);  // pay
    itxn_field_set(s, ctx, TypeEnum);
    pushint(s, 2000);
    itxn_field_set(s, ctx, Amount);

    itxn_next(s, BS, ctx);
    __CPROVER_assert(BS.app_balance == 8000, "first payment applied");

    pushint(s, 1);  // pay
    itxn_field_set(s, ctx, TypeEnum);
    pushint(s, 3000);
    itxn_field_set(s, ctx, Amount);

    itxn_submit(BS, ctx);
    __CPROVER_assert(BS.app_balance == 5000, "second payment applied");
    return 0;
}
""")
        assert result["verified"], f"itxn_next effects failed:\n{result['stderr']}"

    def test_itxn_sets_sender_to_app_address(self, opcodes):
        """Inner txn sender is set to CurrentApplicationAddress."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    BS.app_balance = 10000;

    uint8_t app_addr[32]; memset(app_addr, 0xAA, 32);
    memcpy(ctx.CurrentApplicationAddress, app_addr, 32);

    itxn_begin(s, ctx);
    pushint(s, 1);
    itxn_field_set(s, ctx, TypeEnum);
    pushint(s, 100);
    itxn_field_set(s, ctx, Amount);
    itxn_submit(BS, ctx);

    // Read back sender
    itxn_field_read(s, ctx, Sender);
    StackValue sv = stack_pop(s);
    __CPROVER_assert(sv._is_bytes, "sender is bytes");
    __CPROVER_assert(sv.byteslice[0] == 0xAA, "sender byte 0");
    __CPROVER_assert(sv.byteslice[31] == 0xAA, "sender byte 31");
    return 0;
}
""")
        assert result["verified"], f"itxn sender failed:\n{result['stderr']}"

    def test_itxn_payment_close_remainder(self, opcodes):
        """Payment inner txn with CloseRemainderTo zeroes app balance."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    BS.app_balance = 10000;

    // Build inner payment with CloseRemainderTo
    Txn itxn;
    memset(&itxn, 0, sizeof(Txn));
    itxn.TypeEnum = 1;  // pay
    itxn.Amount = 3000;
    memset(itxn.CloseRemainderTo, 0xCC, 32);  // non-zero = close

    _itxn_apply_effects(BS, ctx, itxn);

    __CPROVER_assert(!__avm_panicked, "no panic");
    __CPROVER_assert(BS.app_balance == 0, "balance zeroed after close");
    return 0;
}
""")
        assert result["verified"], f"itxn payment close failed:\n{result['stderr']}"

    def test_itxn_asset_close_to(self, opcodes):
        """Asset transfer inner txn with AssetCloseTo zeroes sender holding."""
        result = opcodes.verify_cpp("""
int main() {
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);

    __CPROVER_array_set(ctx.CurrentApplicationAddress, (uint8_t)0xAA);

    // Set up sender holding (app = 0xAA)
    AssetHoldingState& ahs = BS.asset_holdings;
    ahs.entries[0].active = true;
    ahs.entries[0].asset_id = 42;
    __CPROVER_array_set(ahs.entries[0].account, (uint8_t)0xAA);
    ahs.entries[0].balance = 1000;
    ahs.entries[0].opted_in = true;
    // Set up receiver holding (0xBB)
    ahs.entries[1].active = true;
    ahs.entries[1].asset_id = 42;
    __CPROVER_array_set(ahs.entries[1].account, (uint8_t)0xBB);
    ahs.entries[1].balance = 500;
    ahs.entries[1].opted_in = true;
    // Set up close-to holding (0xCC)
    ahs.entries[2].active = true;
    ahs.entries[2].asset_id = 42;
    __CPROVER_array_set(ahs.entries[2].account, (uint8_t)0xCC);
    ahs.entries[2].balance = 200;
    ahs.entries[2].opted_in = true;
    ahs.count = 3;

    // Build inner axfer with AssetCloseTo
    Txn itxn;
    memset(&itxn, 0, sizeof(Txn));
    itxn.TypeEnum = 4;  // axfer
    itxn.XferAsset = 42;
    itxn.AssetAmount = 300;
    __CPROVER_array_set(itxn.AssetReceiver, (uint8_t)0xBB);
    __CPROVER_array_set(itxn.AssetCloseTo, (uint8_t)0xCC);

    _itxn_apply_effects(BS, ctx, itxn);

    __CPROVER_assert(!__avm_panicked, "no panic");
    __CPROVER_assert(ahs.entries[0].balance == 0, "sender zeroed");
    __CPROVER_assert(ahs.entries[1].balance == 800, "receiver got 300");
    __CPROVER_assert(ahs.entries[2].balance == 900, "close-to got remaining 700");
    return 0;
}
""")
        assert result["verified"], f"itxn asset close-to failed:\n{result['stderr']}"

    def test_itxn_asset_freeze_updates_holding(self, opcodes):
        """Asset freeze inner txn updates frozen flag on modeled holding."""
        result = opcodes.verify_cpp("""
int main() {
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);

    memset(ctx.CurrentApplicationAddress, 0xAA, 32);

    // Set up a holding for account 0xBB, asset 42, initially unfrozen
    AssetHoldingState& ahs = BS.asset_holdings;
    ahs.entries[0].active = true;
    ahs.entries[0].asset_id = 42;
    memset(ahs.entries[0].account, 0xBB, 32);
    ahs.entries[0].balance = 1000;
    ahs.entries[0].frozen = false;
    ahs.entries[0].opted_in = true;
    ahs.count = 1;

    // Build inner afrz: freeze the holding
    Txn itxn;
    memset(&itxn, 0, sizeof(Txn));
    itxn.TypeEnum = 5;  // afrz
    itxn.FreezeAsset = 42;
    memset(itxn.FreezeAssetAccount, 0xBB, 32);
    itxn.FreezeAssetFrozen = true;

    _itxn_apply_effects(BS, ctx, itxn);

    __CPROVER_assert(!__avm_panicked, "no panic");
    __CPROVER_assert(ahs.entries[0].frozen == true, "holding is now frozen");
    __CPROVER_assert(ahs.entries[0].balance == 1000, "balance unchanged");

    // Unfreeze
    itxn.FreezeAssetFrozen = false;
    _itxn_apply_effects(BS, ctx, itxn);

    __CPROVER_assert(ahs.entries[0].frozen == false, "holding is now unfrozen");
    return 0;
}
""")
        assert result["verified"], f"itxn asset freeze failed:\n{result['stderr']}"

    def test_itxn_asset_freeze_unmodeled_noop(self, opcodes):
        """Asset freeze on unmodeled holding is a no-op (sound over-approximation)."""
        result = opcodes.verify_cpp("""
int main() {
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);

    memset(ctx.CurrentApplicationAddress, 0xAA, 32);

    // No holdings in the model

    // Build inner afrz for unmodeled account
    Txn itxn;
    memset(&itxn, 0, sizeof(Txn));
    itxn.TypeEnum = 5;  // afrz
    itxn.FreezeAsset = 42;
    memset(itxn.FreezeAssetAccount, 0xBB, 32);
    itxn.FreezeAssetFrozen = true;

    _itxn_apply_effects(BS, ctx, itxn);

    __CPROVER_assert(!__avm_panicked, "no panic on unmodeled freeze");
    return 0;
}
""")
        assert result["verified"], f"itxn asset freeze unmodeled failed:\n{result['stderr']}"


# ============================================================================
# Cross-phase integration tests
# ============================================================================

class TestIntegration:
    """Tests combining opcodes from multiple phases."""

    def test_itob_extract_uint32(self, opcodes):
        """itob + extract_uint32 extracts correct 32-bit slice from uint64."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    // 0x00000001_00000002
    pushint(s, 0x0000000100000002ULL);
    itob(s);
    // Extract high 4 bytes (offset 0)
    dup(s);
    pushint(s, 0);
    extract_uint32(s);
    StackValue hi = stack_pop(s);
    __CPROVER_assert(hi.value == 1, "high 32 bits");
    // Extract low 4 bytes (offset 4)
    pushint(s, 4);
    extract_uint32(s);
    StackValue lo = stack_pop(s);
    __CPROVER_assert(lo.value == 2, "low 32 bits");
    return 0;
}
""")
        assert result["verified"], f"itob+extract_uint32 failed:\n{result['stderr']}"

    def test_global_state_with_byte_key(self, opcodes):
        """Global state with byte key works end-to-end."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);

    uint8_t key[6] = {'p','r','e','f','i','x'};
    // global_put: pops val (top), then key (second)
    stack_push(s, sv_bytes(key, 6));  // key
    pushint(s, 42);                    // value (top)
    app_global_put(s, BS, ctx);

    // global_get: pops key
    stack_push(s, sv_bytes(key, 6));
    app_global_get(s, BS, ctx);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 42, "global state roundtrip");
    return 0;
}
""")
        assert result["verified"], f"global state with byte key failed:\n{result['stderr']}"

    def test_frame_with_scratch(self, opcodes):
        """Subroutine frame ops work alongside scratch space."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);

    // Store in scratch
    pushint(s, 50);
    store(s, ctx, 0);

    // Set up frame
    pushint(s, 10);
    pushint(s, 20);
    proto(s, ctx, 2, 1);

    // Load from scratch inside frame
    load(s, ctx, 0);
    StackValue scr = stack_pop(s);
    __CPROVER_assert(scr.value == 50, "scratch works inside frame");

    // Frame dig still works
    frame_dig(s, ctx, -1);
    StackValue arg = stack_pop(s);
    __CPROVER_assert(arg.value == 20, "frame_dig works alongside scratch");
    return 0;
}
""")
        assert result["verified"], f"frame with scratch failed:\n{result['stderr']}"

    def test_box_with_extract(self, opcodes):
        """Box contents can be extracted with byte ops."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    Txn txn;

    uint8_t key[] = {'t'};
    uint8_t data[8] = {0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08};
    // Create and put
    stack_push(s, sv_bytes(key, 1));
    pushint(s, 8);
    box_create_op(s, BS, txn, ctx);
    stack_pop(s);
    stack_push(s, sv_bytes(key, 1));
    stack_push(s, sv_bytes(data, 8));
    box_put_op(s, BS, txn, ctx);

    // Get box contents
    stack_push(s, sv_bytes(key, 1));
    box_get_op(s, BS, txn, ctx);
    stack_pop(s);  // found flag
    // Now we have the bytes on stack; use extract to get middle
    extract(s, 2, 4);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.byteslice_len == 4, "extracted 4 bytes");
    __CPROVER_assert(r.byteslice[0] == 0x03, "correct extraction");
    return 0;
}
""")
        assert result["verified"], f"box with extract failed:\n{result['stderr']}"


# ============================================================================
# Byte Math (Big-Integer) Opcodes
# ============================================================================

class TestBmathAdd:
    """Tests for b+ (bmath_add)."""

    def test_bmath_add_basic(self, opcodes):
        """b+ of 0xFF + 0x01 = 0x0100 (carry propagation)."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t a[] = {0xFF};
    uint8_t b[] = {0x01};
    stack_push(s, sv_bytes(a, 1));
    stack_push(s, sv_bytes(b, 1));
    bmath_add(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice_len == 2, "len 2 from carry");
    __CPROVER_assert(r.byteslice[0] == 0x01, "high byte");
    __CPROVER_assert(r.byteslice[1] == 0x00, "low byte");
    return 0;
}
""")
        assert result["verified"], f"bmath_add basic failed:\n{result['stderr']}"

    def test_bmath_add_different_lengths(self, opcodes):
        """b+ with different-length operands: 0x0100 + 0x01 = 0x0101."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t a[] = {0x01, 0x00};
    uint8_t b[] = {0x01};
    stack_push(s, sv_bytes(a, 2));
    stack_push(s, sv_bytes(b, 1));
    bmath_add(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.byteslice_len == 2, "len 2");
    __CPROVER_assert(r.byteslice[0] == 0x01, "high byte");
    __CPROVER_assert(r.byteslice[1] == 0x01, "low byte");
    return 0;
}
""")
        assert result["verified"], f"bmath_add different lengths failed:\n{result['stderr']}"

    def test_bmath_add_commutative(self, opcodes):
        """b+ is commutative: A + B == B + A."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s1; stack_init(s1);
    Stack s2; stack_init(s2);
    uint8_t a[] = {0x12, 0x34};
    uint8_t b[] = {0x56, 0x78, 0x9A};
    // A + B
    stack_push(s1, sv_bytes(a, 2));
    stack_push(s1, sv_bytes(b, 3));
    bmath_add(s1);
    StackValue r1 = stack_pop(s1);
    // B + A
    stack_push(s2, sv_bytes(b, 3));
    stack_push(s2, sv_bytes(a, 2));
    bmath_add(s2);
    StackValue r2 = stack_pop(s2);
    __CPROVER_assert(sv_bytes_equal(r1, r2), "b+ commutative");
    return 0;
}
""")
        assert result["verified"], f"bmath_add commutative failed:\n{result['stderr']}"


class TestBmathSub:
    """Tests for b- (bmath_sub)."""

    def test_bmath_sub_basic(self, opcodes):
        """b- of 0x0100 - 0x01 = 0xFF."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t a[] = {0x01, 0x00};
    uint8_t b[] = {0x01};
    stack_push(s, sv_bytes(a, 2));
    stack_push(s, sv_bytes(b, 1));
    bmath_sub(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice_len == 1, "len 1 after strip");
    __CPROVER_assert(r.byteslice[0] == 0xFF, "result FF");
    return 0;
}
""")
        assert result["verified"], f"bmath_sub basic failed:\n{result['stderr']}"

    def test_bmath_sub_self_is_zero(self, opcodes):
        """b- of X - X = 0x00."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t a[] = {0xAB, 0xCD};
    stack_push(s, sv_bytes(a, 2));
    stack_push(s, sv_bytes(a, 2));
    bmath_sub(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice_len == 1, "minimal zero");
    __CPROVER_assert(r.byteslice[0] == 0x00, "zero value");
    return 0;
}
""")
        assert result["verified"], f"bmath_sub self failed:\n{result['stderr']}"


class TestBmathMul:
    """Tests for b* (bmath_mul)."""

    def test_bmath_mul_basic(self, opcodes):
        """b* of 0xFF * 0x02 = 0x01FE."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t a[] = {0xFF};
    uint8_t b[] = {0x02};
    stack_push(s, sv_bytes(a, 1));
    stack_push(s, sv_bytes(b, 1));
    bmath_mul(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice_len == 2, "len 2");
    __CPROVER_assert(r.byteslice[0] == 0x01, "high byte");
    __CPROVER_assert(r.byteslice[1] == 0xFE, "low byte");
    return 0;
}
""")
        assert result["verified"], f"bmath_mul basic failed:\n{result['stderr']}"

    def test_bmath_mul_commutative(self, opcodes):
        """b* is commutative: A * B == B * A."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s1; stack_init(s1);
    Stack s2; stack_init(s2);
    uint8_t a[] = {0x12, 0x34};
    uint8_t b[] = {0x56};
    // A * B
    stack_push(s1, sv_bytes(a, 2));
    stack_push(s1, sv_bytes(b, 1));
    bmath_mul(s1);
    StackValue r1 = stack_pop(s1);
    // B * A
    stack_push(s2, sv_bytes(b, 1));
    stack_push(s2, sv_bytes(a, 2));
    bmath_mul(s2);
    StackValue r2 = stack_pop(s2);
    __CPROVER_assert(sv_bytes_equal(r1, r2), "b* commutative");
    return 0;
}
""")
        assert result["verified"], f"bmath_mul commutative failed:\n{result['stderr']}"


class TestBmathDivMod:
    """Tests for b/ (bmath_div) and b% (bmath_mod)."""

    def test_bmath_div_basic(self, opcodes):
        """b/ of 0x0A / 0x03 = 0x03."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t a[] = {0x0A};
    uint8_t b[] = {0x03};
    stack_push(s, sv_bytes(a, 1));
    stack_push(s, sv_bytes(b, 1));
    bmath_div(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice_len == 1, "len 1");
    __CPROVER_assert(r.byteslice[0] == 0x03, "10/3=3");
    return 0;
}
""", unwind=35, timeout=120)
        assert result["verified"], f"bmath_div basic failed:\n{result['stderr']}"

    def test_bmath_mod_basic(self, opcodes):
        """b% of 0x0A % 0x03 = 0x01."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t a[] = {0x0A};
    uint8_t b[] = {0x03};
    stack_push(s, sv_bytes(a, 1));
    stack_push(s, sv_bytes(b, 1));
    bmath_mod(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice_len == 1, "len 1");
    __CPROVER_assert(r.byteslice[0] == 0x01, "10%3=1");
    return 0;
}
""", unwind=35, timeout=120)
        assert result["verified"], f"bmath_mod basic failed:\n{result['stderr']}"

    def test_bmath_divmod_identity(self, opcodes):
        """(A / B) * B + (A % B) == A."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t a[] = {0x01, 0x00};  // 256
    uint8_t b[] = {0x07};         // 7
    // q = 256 / 7 = 36 = 0x24
    stack_push(s, sv_bytes(a, 2));
    stack_push(s, sv_bytes(b, 1));
    bmath_div(s);
    StackValue q = stack_pop(s);
    // r = 256 % 7 = 4
    stack_push(s, sv_bytes(a, 2));
    stack_push(s, sv_bytes(b, 1));
    bmath_mod(s);
    StackValue r = stack_pop(s);
    // q * b
    stack_push(s, q);
    stack_push(s, sv_bytes(b, 1));
    bmath_mul(s);
    // q*b + r
    stack_push(s, r);
    bmath_add(s);
    StackValue result = stack_pop(s);
    // Should equal a (but stripped: 0x0100 -> might be 2 bytes)
    __CPROVER_assert(result.byteslice_len == 2, "len matches");
    __CPROVER_assert(result.byteslice[0] == 0x01, "high byte");
    __CPROVER_assert(result.byteslice[1] == 0x00, "low byte");
    return 0;
}
""", unwind=35, timeout=120)
        assert result["verified"], f"bmath_divmod identity failed:\n{result['stderr']}"


class TestBmathSqrt:
    """Tests for bsqrt (bmath_sqrt)."""

    def test_bmath_sqrt_perfect(self, opcodes):
        """bsqrt of 0x09 = 0x03."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t a[] = {0x09};
    stack_push(s, sv_bytes(a, 1));
    bmath_sqrt(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice_len == 1, "len 1");
    __CPROVER_assert(r.byteslice[0] == 0x03, "sqrt(9)=3");
    return 0;
}
""", unwind=35, timeout=300)
        assert result["verified"], f"bmath_sqrt perfect failed:\n{result['stderr']}"

    def test_bmath_sqrt_non_perfect(self, opcodes):
        """bsqrt of 0x0A = 0x03 (floor of sqrt(10) = 3)."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t a[] = {0x0A};
    stack_push(s, sv_bytes(a, 1));
    bmath_sqrt(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice[0] == 0x03, "floor sqrt(10)=3");
    return 0;
}
""", unwind=35, timeout=300)
        assert result["verified"], f"bmath_sqrt non-perfect failed:\n{result['stderr']}"


class TestBmathComparisons:
    """Tests for b<, b>, b<=, b>=, b==, b!=."""

    def test_bmath_lt_basic(self, opcodes):
        """b<: 0x01 < 0x02 = 1."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t a[] = {0x01};
    uint8_t b[] = {0x02};
    stack_push(s, sv_bytes(a, 1));
    stack_push(s, sv_bytes(b, 1));
    bmath_lt(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(!r._is_bytes, "result is int");
    __CPROVER_assert(r.value == 1, "1 < 2");
    return 0;
}
""")
        assert result["verified"], f"bmath_lt basic failed:\n{result['stderr']}"

    def test_bmath_eq_same(self, opcodes):
        """b==: X == X = 1."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t a[] = {0xAB, 0xCD};
    stack_push(s, sv_bytes(a, 2));
    stack_push(s, sv_bytes(a, 2));
    bmath_eq(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 1, "X == X");
    return 0;
}
""")
        assert result["verified"], f"bmath_eq same failed:\n{result['stderr']}"

    def test_bmath_neq_different(self, opcodes):
        """b!=: 0x01 != 0x02 = 1."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t a[] = {0x01};
    uint8_t b[] = {0x02};
    stack_push(s, sv_bytes(a, 1));
    stack_push(s, sv_bytes(b, 1));
    bmath_neq(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 1, "1 != 2");
    return 0;
}
""")
        assert result["verified"], f"bmath_neq different failed:\n{result['stderr']}"

    def test_bmath_compare_different_lengths(self, opcodes):
        """b<: 0xFF < 0x0100 = 1 (255 < 256)."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t a[] = {0xFF};
    uint8_t b[] = {0x01, 0x00};
    stack_push(s, sv_bytes(a, 1));
    stack_push(s, sv_bytes(b, 2));
    bmath_lt(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 1, "255 < 256");
    return 0;
}
""")
        assert result["verified"], f"bmath compare different lengths failed:\n{result['stderr']}"

    def test_bmath_geq_equal(self, opcodes):
        """b>=: X >= X = 1."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t a[] = {0x05};
    stack_push(s, sv_bytes(a, 1));
    stack_push(s, sv_bytes(a, 1));
    bmath_geq(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 1, "X >= X");
    return 0;
}
""")
        assert result["verified"], f"bmath_geq equal failed:\n{result['stderr']}"

    def test_bmath_gt_basic(self, opcodes):
        """b>: 0x02 > 0x01 = 1."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t a[] = {0x02};
    uint8_t b[] = {0x01};
    stack_push(s, sv_bytes(a, 1));
    stack_push(s, sv_bytes(b, 1));
    bmath_gt(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 1, "2 > 1");
    return 0;
}
""")
        assert result["verified"], f"bmath_gt basic failed:\n{result['stderr']}"

    def test_bmath_leq_less(self, opcodes):
        """b<=: 0x01 <= 0x02 = 1."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t a[] = {0x01};
    uint8_t b[] = {0x02};
    stack_push(s, sv_bytes(a, 1));
    stack_push(s, sv_bytes(b, 1));
    bmath_leq(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 1, "1 <= 2");
    return 0;
}
""")
        assert result["verified"], f"bmath_leq less failed:\n{result['stderr']}"


class TestBmathBitwise:
    """Tests for b&, b|, b^, b~."""

    def test_bmath_and_basic(self, opcodes):
        """b& of 0xFF & 0x0F = 0x0F."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t a[] = {0xFF};
    uint8_t b[] = {0x0F};
    stack_push(s, sv_bytes(a, 1));
    stack_push(s, sv_bytes(b, 1));
    bmath_bitand(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice_len == 1, "len 1");
    __CPROVER_assert(r.byteslice[0] == 0x0F, "FF & 0F = 0F");
    return 0;
}
""")
        assert result["verified"], f"bmath_and basic failed:\n{result['stderr']}"

    def test_bmath_or_basic(self, opcodes):
        """b| of 0xF0 | 0x0F = 0xFF."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t a[] = {0xF0};
    uint8_t b[] = {0x0F};
    stack_push(s, sv_bytes(a, 1));
    stack_push(s, sv_bytes(b, 1));
    bmath_bitor(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.byteslice_len == 1, "len 1");
    __CPROVER_assert(r.byteslice[0] == 0xFF, "F0 | 0F = FF");
    return 0;
}
""")
        assert result["verified"], f"bmath_or basic failed:\n{result['stderr']}"

    def test_bmath_xor_self_is_zero(self, opcodes):
        """b^ of X ^ X = all zeros (same length as X, NOT stripped)."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t a[] = {0xAB, 0xCD};
    stack_push(s, sv_bytes(a, 2));
    stack_push(s, sv_bytes(a, 2));
    bmath_bitxor(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice_len == 2, "length preserved");
    __CPROVER_assert(r.byteslice[0] == 0x00, "byte 0 zero");
    __CPROVER_assert(r.byteslice[1] == 0x00, "byte 1 zero");
    return 0;
}
""")
        assert result["verified"], f"bmath_xor self failed:\n{result['stderr']}"

    def test_bmath_neg_basic(self, opcodes):
        """b~ of 0x00 = 0xFF."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t a[] = {0x00};
    stack_push(s, sv_bytes(a, 1));
    bmath_bitneg(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice_len == 1, "len 1");
    __CPROVER_assert(r.byteslice[0] == 0xFF, "~00 = FF");
    return 0;
}
""")
        assert result["verified"], f"bmath_neg basic failed:\n{result['stderr']}"

    def test_bmath_and_different_lengths(self, opcodes):
        """b& with different lengths: shorter is left-padded with zeros."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t a[] = {0xFF, 0xFF};  // 2 bytes
    uint8_t b[] = {0x0F};         // 1 byte, left-padded to {0x00, 0x0F}
    stack_push(s, sv_bytes(a, 2));
    stack_push(s, sv_bytes(b, 1));
    bmath_bitand(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.byteslice_len == 2, "result is max length");
    __CPROVER_assert(r.byteslice[0] == 0x00, "high byte: FF & 00 = 00");
    __CPROVER_assert(r.byteslice[1] == 0x0F, "low byte: FF & 0F = 0F");
    return 0;
}
""")
        assert result["verified"], f"bmath_and different lengths failed:\n{result['stderr']}"


class TestBmathInputLimit:
    """Tests for input size limit enforcement."""

    def test_bmath_input_limit(self, opcodes):
        """Inputs > 64 bytes trigger panic."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    // Create a 65-byte input (exceeds CBMC_BMATH_MAX=64)
    uint8_t big[65];
    for (int i = 0; i < 65; i++) big[i] = 0x01;
    uint8_t small[] = {0x01};
    stack_push(s, sv_bytes(big, 65));
    stack_push(s, sv_bytes(small, 1));
    __avm_panicked = false;
    bmath_add(s);
    __CPROVER_assert(__avm_panicked, "should panic on >64 byte input");
    return 0;
}
""", unwind=70)
        assert result["verified"], f"bmath input limit failed:\n{result['stderr']}"


# ============================================================================
# Txn Array Access (txna_field extended + stack-indexed variants)
# ============================================================================

class TestTxnaAccounts:
    """Tests for txna Accounts array access."""

    def test_txna_accounts_basic(self, opcodes):
        """txna Accounts reads correct account addresses (AVM: 0=Sender, 1+=Accounts)."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    Txn txn;
    memset(&txn, 0, sizeof(txn));
    // Set up Sender (all 0xAA)
    for (int i = 0; i < 32; i++) txn.Sender[i] = 0xAA;
    // Set up Accounts[0] = first referenced account (all 0x01)
    for (int i = 0; i < 32; i++) txn.Accounts[0][i] = 0x01;
    // Set up Accounts[1] = second referenced account (all 0x02)
    for (int i = 0; i < 32; i++) txn.Accounts[1][i] = 0x02;
    txn.NumAccounts = 2;

    // AVM index 0 = Sender
    txna_field(s, txn, Accounts, 0);
    StackValue r0 = stack_pop(s);
    __CPROVER_assert(r0._is_bytes, "accounts[0] is bytes");
    __CPROVER_assert(r0.byteslice_len == 32, "accounts[0] is 32 bytes");
    __CPROVER_assert(r0.byteslice[0] == 0xAA, "accounts[0] = Sender");

    // AVM index 1 = Accounts[0]
    txna_field(s, txn, Accounts, 1);
    StackValue r1 = stack_pop(s);
    __CPROVER_assert(r1.byteslice[0] == 0x01, "accounts[1] = first ref account");

    // AVM index 2 = Accounts[1]
    txna_field(s, txn, Accounts, 2);
    StackValue r2 = stack_pop(s);
    __CPROVER_assert(r2.byteslice[0] == 0x02, "accounts[2] = second ref account");
    return 0;
}
""")
        assert result["verified"], f"txna accounts basic failed:\n{result['stderr']}"

    def test_txna_accounts_oob_panics(self, opcodes):
        """txna Accounts with out-of-bounds index triggers panic."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    Txn txn;
    memset(&txn, 0, sizeof(txn));
    txn.NumAccounts = 1;
    for (int i = 0; i < 32; i++) txn.Accounts[0][i] = 0xAA;

    __avm_panicked = false;
    txna_field(s, txn, Accounts, 2);
    __CPROVER_assert(__avm_panicked, "should panic on oob accounts access");
    return 0;
}
""")
        assert result["verified"], f"txna accounts oob failed:\n{result['stderr']}"


class TestTxnaAssets:
    """Tests for txna Assets array access."""

    def test_txna_assets_basic(self, opcodes):
        """txna Assets reads correct asset IDs."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    Txn txn;
    memset(&txn, 0, sizeof(txn));
    txn.Assets[0] = 12345;
    txn.Assets[1] = 67890;
    txn.NumAssets = 2;

    txna_field(s, txn, Assets, 0);
    StackValue r0 = stack_pop(s);
    __CPROVER_assert(!r0._is_bytes, "assets[0] is uint64");
    __CPROVER_assert(r0.value == 12345, "assets[0] value");

    txna_field(s, txn, Assets, 1);
    StackValue r1 = stack_pop(s);
    __CPROVER_assert(r1.value == 67890, "assets[1] value");
    return 0;
}
""")
        assert result["verified"], f"txna assets basic failed:\n{result['stderr']}"


class TestTxnaApplications:
    """Tests for txna Applications array access."""

    def test_txna_applications_basic(self, opcodes):
        """txna Applications reads correct app IDs (AVM: 0=current, 1+=ForeignApps)."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    Txn txn;
    memset(&txn, 0, sizeof(txn));
    txn.ApplicationID = 42;     // current app
    txn.Applications[0] = 100;  // first foreign app
    txn.Applications[1] = 200;  // second foreign app
    txn.NumApplications = 2;

    // AVM index 0 = current ApplicationID
    txna_field(s, txn, Applications, 0);
    StackValue r0 = stack_pop(s);
    __CPROVER_assert(!r0._is_bytes, "apps[0] is uint64");
    __CPROVER_assert(r0.value == 42, "apps[0] = current app");

    // AVM index 1 = Applications[0]
    txna_field(s, txn, Applications, 1);
    StackValue r1 = stack_pop(s);
    __CPROVER_assert(r1.value == 100, "apps[1] = first foreign app");

    // AVM index 2 = Applications[1]
    txna_field(s, txn, Applications, 2);
    StackValue r2 = stack_pop(s);
    __CPROVER_assert(r2.value == 200, "apps[2] = second foreign app");
    return 0;
}
""")
        assert result["verified"], f"txna applications basic failed:\n{result['stderr']}"


class TestTxnaLogs:
    """Tests for txna Logs array access."""

    def test_txna_logs_basic(self, opcodes):
        """txna Logs reads correct log entries."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    Txn txn;
    memset(&txn, 0, sizeof(txn));
    txn.TxnLogs[0][0] = 0xDE;
    txn.TxnLogs[0][1] = 0xAD;
    txn.TxnLogLens[0] = 2;
    txn.TxnLogs[1][0] = 0xBE;
    txn.TxnLogs[1][1] = 0xEF;
    txn.TxnLogLens[1] = 2;
    txn.NumTxnLogs = 2;

    txna_field(s, txn, Logs, 0);
    StackValue r0 = stack_pop(s);
    __CPROVER_assert(r0._is_bytes, "logs[0] is bytes");
    __CPROVER_assert(r0.byteslice_len == 2, "logs[0] len");
    __CPROVER_assert(r0.byteslice[0] == 0xDE, "logs[0] byte 0");

    txna_field(s, txn, Logs, 1);
    StackValue r1 = stack_pop(s);
    __CPROVER_assert(r1.byteslice[0] == 0xBE, "logs[1] byte 0");
    return 0;
}
""")
        assert result["verified"], f"txna logs basic failed:\n{result['stderr']}"


class TestTxnFieldsExtended:
    """Tests for newly added txn_field cases."""

    def test_txn_receiver(self, opcodes):
        """txn Receiver returns the correct 32-byte address."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    Txn txn;
    memset(&txn, 0, sizeof(txn));
    for (int i = 0; i < 32; i++) txn.Receiver[i] = (uint8_t)(i + 1);

    txn_field(s, txn, Receiver);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "receiver is bytes");
    __CPROVER_assert(r.byteslice_len == 32, "receiver is 32 bytes");
    __CPROVER_assert(r.byteslice[0] == 0x01, "receiver byte 0");
    __CPROVER_assert(r.byteslice[31] == 0x20, "receiver byte 31");
    return 0;
}
""")
        assert result["verified"], f"txn receiver failed:\n{result['stderr']}"

    def test_txn_num_fields(self, opcodes):
        """txn NumAccounts/NumAssets/NumApplications/NumLogs return correct counts."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    Txn txn;
    memset(&txn, 0, sizeof(txn));
    txn.NumAccounts = 3;
    txn.NumAssets = 2;
    txn.NumApplications = 1;
    txn.NumTxnLogs = 4;

    txn_field(s, txn, NumAccounts);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 3, "NumAccounts");

    txn_field(s, txn, NumAssets);
    r = stack_pop(s);
    __CPROVER_assert(r.value == 2, "NumAssets");

    txn_field(s, txn, NumApplications);
    r = stack_pop(s);
    __CPROVER_assert(r.value == 1, "NumApplications");

    txn_field(s, txn, NumLogs);
    r = stack_pop(s);
    __CPROVER_assert(r.value == 4, "NumLogs");
    return 0;
}
""")
        assert result["verified"], f"txn num fields failed:\n{result['stderr']}"

    def test_txn_created_ids(self, opcodes):
        """txn CreatedAssetID/CreatedApplicationID return correct values."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    Txn txn;
    memset(&txn, 0, sizeof(txn));
    txn.CreatedAssetID = 999;
    txn.CreatedApplicationID = 888;

    txn_field(s, txn, CreatedAssetID);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 999, "CreatedAssetID");

    txn_field(s, txn, CreatedApplicationID);
    r = stack_pop(s);
    __CPROVER_assert(r.value == 888, "CreatedApplicationID");
    return 0;
}
""")
        assert result["verified"], f"txn created ids failed:\n{result['stderr']}"

    def test_txn_last_log(self, opcodes):
        """txn LastLog returns the most recent log entry."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    Txn txn;
    memset(&txn, 0, sizeof(txn));
    txn.TxnLogs[0][0] = 0xAA;
    txn.TxnLogLens[0] = 1;
    txn.TxnLogs[1][0] = 0xBB;
    txn.TxnLogLens[1] = 1;
    txn.NumTxnLogs = 2;

    txn_field(s, txn, LastLog);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "last log is bytes");
    __CPROVER_assert(r.byteslice[0] == 0xBB, "last log is most recent");
    return 0;
}
""")
        assert result["verified"], f"txn last log failed:\n{result['stderr']}"

    def test_txn_last_log_empty(self, opcodes):
        """txn LastLog with no logs returns empty bytes."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    Txn txn;
    memset(&txn, 0, sizeof(txn));
    txn.NumTxnLogs = 0;

    txn_field(s, txn, LastLog);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "last log is bytes");
    __CPROVER_assert(r.byteslice_len == 0, "last log is empty when no logs");
    return 0;
}
""")
        assert result["verified"], f"txn last log empty failed:\n{result['stderr']}"


# ============================================================================
# Stack-indexed txn opcodes (txnas, gtxnas, gtxnsa, gtxnsas, itxnas, gitxnas)
# ============================================================================

class TestTxnas:
    """Tests for txnas — stack-indexed txn array access."""

    def test_txnas_app_args(self, opcodes):
        """txnas ApplicationArgs pops index from stack."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    Txn txn;
    memset(&txn, 0, sizeof(txn));
    txn.AppArgs[0][0] = 0x11;
    txn.AppArgLens[0] = 1;
    txn.AppArgs[1][0] = 0x22;
    txn.AppArgLens[1] = 1;
    txn.NumAppArgs = 2;

    pushint(s, 1);  // index on stack
    txnas(s, txn, ApplicationArgs);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice[0] == 0x22, "txnas args[1]");
    return 0;
}
""")
        assert result["verified"], f"txnas app args failed:\n{result['stderr']}"

    def test_txnas_accounts(self, opcodes):
        """txnas Accounts pops index from stack (AVM: 0=Sender, 1+=Accounts)."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    Txn txn;
    memset(&txn, 0, sizeof(txn));
    for (int i = 0; i < 32; i++) txn.Sender[i] = 0xCC;
    for (int i = 0; i < 32; i++) txn.Accounts[0][i] = 0xAA;
    for (int i = 0; i < 32; i++) txn.Accounts[1][i] = 0xBB;
    txn.NumAccounts = 2;

    // AVM index 0 = Sender
    pushint(s, 0);
    txnas(s, txn, Accounts);
    StackValue r0 = stack_pop(s);
    __CPROVER_assert(r0._is_bytes, "is bytes");
    __CPROVER_assert(r0.byteslice[0] == 0xCC, "txnas accounts[0] = Sender");

    // AVM index 1 = Accounts[0]
    pushint(s, 1);
    txnas(s, txn, Accounts);
    StackValue r1 = stack_pop(s);
    __CPROVER_assert(r1.byteslice[0] == 0xAA, "txnas accounts[1] = first ref");
    return 0;
}
""")
        assert result["verified"], f"txnas accounts failed:\n{result['stderr']}"


class TestGtxnas:
    """Tests for gtxnas — group txn array with stack-based array index."""

    def test_gtxnas_basic(self, opcodes):
        """gtxnas reads group txn array field with index from stack."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    TxnGroup tg; tg_init(tg);
    memset(&tg.txns[0], 0, sizeof(Txn));
    tg.txns[0].AppArgs[0][0] = 0x41;
    tg.txns[0].AppArgLens[0] = 1;
    tg.txns[0].AppArgs[1][0] = 0x42;
    tg.txns[0].AppArgLens[1] = 1;
    tg.txns[0].NumAppArgs = 2;
    tg.size = 1;

    pushint(s, 1);  // array index on stack
    gtxnas(s, tg, 0, ApplicationArgs);  // txn 0, field=ApplicationArgs
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice[0] == 0x42, "gtxnas args[1]");
    return 0;
}
""")
        assert result["verified"], f"gtxnas basic failed:\n{result['stderr']}"


class TestGtxnsa:
    """Tests for gtxnsa — group txn array with stack-based txn index."""

    def test_gtxnsa_basic(self, opcodes):
        """gtxnsa pops txn index from stack, uses immediate array index."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    TxnGroup tg; tg_init(tg);
    memset(&tg.txns[0], 0, sizeof(Txn));
    memset(&tg.txns[1], 0, sizeof(Txn));
    tg.txns[0].AppArgs[0][0] = 0x10;
    tg.txns[0].AppArgLens[0] = 1;
    tg.txns[0].NumAppArgs = 1;
    tg.txns[1].AppArgs[0][0] = 0x20;
    tg.txns[1].AppArgLens[0] = 1;
    tg.txns[1].NumAppArgs = 1;
    tg.size = 2;

    pushint(s, 1);  // txn index on stack
    gtxnsa(s, tg, ApplicationArgs, 0);  // field=ApplicationArgs, array_idx=0
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice[0] == 0x20, "gtxnsa reads txn[1].args[0]");
    return 0;
}
""")
        assert result["verified"], f"gtxnsa basic failed:\n{result['stderr']}"


class TestGtxnsas:
    """Tests for gtxnsas — both indices from stack."""

    def test_gtxnsas_basic(self, opcodes):
        """gtxnsas pops both txn index and array index from stack."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    TxnGroup tg; tg_init(tg);
    memset(&tg.txns[0], 0, sizeof(Txn));
    memset(&tg.txns[1], 0, sizeof(Txn));
    tg.txns[1].Assets[0] = 555;
    tg.txns[1].Assets[1] = 777;
    tg.txns[1].NumAssets = 2;
    tg.size = 2;

    pushint(s, 1);  // array index
    pushint(s, 1);  // txn index (popped first)
    gtxnsas(s, tg, Assets);
    StackValue r = stack_pop(s);
    __CPROVER_assert(!r._is_bytes, "is uint64");
    __CPROVER_assert(r.value == 777, "gtxnsas reads txn[1].assets[1]");
    return 0;
}
""")
        assert result["verified"], f"gtxnsas basic failed:\n{result['stderr']}"


class TestItxnas:
    """Tests for itxnas — inner txn array access with stack index."""

    def test_itxnas_basic(self, opcodes):
        """itxnas reads last submitted inner txn array field with stack index."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    // Simulate a submitted inner txn
    memset(&ctx.inner_txns[0], 0, sizeof(InnerTxn));
    ctx.inner_txns[0].txn.AppArgs[0][0] = 0xCC;
    ctx.inner_txns[0].txn.AppArgLens[0] = 1;
    ctx.inner_txns[0].txn.AppArgs[1][0] = 0xDD;
    ctx.inner_txns[0].txn.AppArgLens[1] = 1;
    ctx.inner_txns[0].txn.NumAppArgs = 2;
    ctx.inner_txns[0].submitted = true;
    ctx.inner_count = 1;

    pushint(s, 1);  // array index on stack
    itxnas(s, ctx, ApplicationArgs);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice[0] == 0xDD, "itxnas args[1]");
    return 0;
}
""")
        assert result["verified"], f"itxnas basic failed:\n{result['stderr']}"


class TestGitxnas:
    """Tests for gitxnas — inner txn by group index, stack array index."""

    def test_gitxnas_basic(self, opcodes):
        """gitxnas reads inner txn array field by group idx + stack array idx."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    memset(&ctx.inner_txns[0], 0, sizeof(InnerTxn));
    memset(&ctx.inner_txns[1], 0, sizeof(InnerTxn));
    ctx.inner_txns[0].txn.Assets[0] = 111;
    ctx.inner_txns[0].txn.NumAssets = 1;
    ctx.inner_txns[1].txn.Assets[0] = 222;
    ctx.inner_txns[1].txn.Assets[1] = 333;
    ctx.inner_txns[1].txn.NumAssets = 2;
    ctx.inner_txns[0].submitted = true;
    ctx.inner_txns[1].submitted = true;
    ctx.inner_count = 2;

    pushint(s, 1);  // array index on stack
    gitxnas(s, ctx, 1, Assets);  // inner txn 1
    StackValue r = stack_pop(s);
    __CPROVER_assert(!r._is_bytes, "is uint64");
    __CPROVER_assert(r.value == 333, "gitxnas inner[1].assets[1]");
    return 0;
}
""")
        assert result["verified"], f"gitxnas basic failed:\n{result['stderr']}"


# ============================================================================
# asset_params_get
# ============================================================================

class TestAssetParamsGet:
    """Tests for asset_params_get stub."""

    def test_asset_params_get_integer_field(self, opcodes):
        """asset_params_get for integer fields pushes uint64 + nondeterministic found flag."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    BlockchainState BS; bs_init(BS);

    pushint(s, 12345);  // asset ID
    asset_params_get(s, BS, 0);  // field 0 = AssetTotal (integer)
    StackValue found = stack_pop(s);
    StackValue val = stack_pop(s);
    __CPROVER_assert(!found._is_bytes, "found is uint64");
    __CPROVER_assert(found.value == 0 || found.value == 1, "found is bool");
    __CPROVER_assert(!val._is_bytes, "AssetTotal is uint64");
    return 0;
}
""")
        assert result["verified"], f"asset_params_get integer failed:\n{result['stderr']}"

    def test_asset_params_get_bytes_field(self, opcodes):
        """asset_params_get for byte fields pushes bytes + nondeterministic found flag."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    BlockchainState BS; bs_init(BS);

    pushint(s, 12345);  // asset ID
    asset_params_get(s, BS, 7);  // field 7 = AssetManager (address)
    StackValue found = stack_pop(s);
    StackValue val = stack_pop(s);
    __CPROVER_assert(found.value == 0 || found.value == 1, "found is bool");
    __CPROVER_assert(val._is_bytes, "AssetManager is bytes");
    __CPROVER_assert(val.byteslice_len == 32, "AssetManager is 32 bytes");
    return 0;
}
""")
        assert result["verified"], f"asset_params_get bytes failed:\n{result['stderr']}"

    def test_asset_params_get_nondet_found(self, opcodes):
        """asset_params_get found flag is not always 1 (can be 0)."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    BlockchainState BS; bs_init(BS);

    pushint(s, 99999);  // unknown asset ID
    asset_params_get(s, BS, 0);
    StackValue found = stack_pop(s);
    // This should FAIL — found is nondeterministic, not always 1
    __CPROVER_assert(found.value == 1, "found always 1");
    return 0;
}
""")
        assert not result["verified"], "found flag should be nondeterministic, not always 1"


# ============================================================================
# itxn_field_set extended (Receiver, Accounts, Assets, Applications)
# ============================================================================

class TestItxnFieldSetExtended:
    """Tests for itxn_field_set with newly added fields."""

    def test_itxn_field_set_receiver(self, opcodes):
        """itxn_field Receiver sets the Receiver field correctly."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);

    itxn_begin(s, ctx);
    // Zero out sender to prove Receiver writes to separate field
    for (int i = 0; i < 32; i++) ctx.building_txn.Sender[i] = 0x00;

    // Set Receiver
    uint8_t addr[32];
    for (int i = 0; i < 32; i++) addr[i] = 0x42;
    stack_push(s, sv_bytes(addr, 32));
    itxn_field_set(s, ctx, Receiver);

    // Verify Receiver is set and Sender is untouched
    __CPROVER_assert(ctx.building_txn.Receiver[0] == 0x42, "Receiver set correctly");
    __CPROVER_assert(ctx.building_txn.Sender[0] == 0x00, "Sender untouched");
    return 0;
}
""")
        assert result["verified"], f"itxn_field_set receiver failed:\n{result['stderr']}"

    def test_itxn_field_set_accounts(self, opcodes):
        """itxn_field Accounts appends accounts to the inner txn."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);

    itxn_begin(s, ctx);
    ctx.building_txn.NumAccounts = 0;

    uint8_t addr1[32];
    for (int i = 0; i < 32; i++) addr1[i] = 0xAA;
    stack_push(s, sv_bytes(addr1, 32));
    itxn_field_set(s, ctx, Accounts);

    uint8_t addr2[32];
    for (int i = 0; i < 32; i++) addr2[i] = 0xBB;
    stack_push(s, sv_bytes(addr2, 32));
    itxn_field_set(s, ctx, Accounts);

    __CPROVER_assert(ctx.building_txn.NumAccounts == 2, "2 accounts added");
    __CPROVER_assert(ctx.building_txn.Accounts[0][0] == 0xAA, "account 0 correct");
    __CPROVER_assert(ctx.building_txn.Accounts[1][0] == 0xBB, "account 1 correct");
    return 0;
}
""")
        assert result["verified"], f"itxn_field_set accounts failed:\n{result['stderr']}"

    def test_itxn_field_set_assets(self, opcodes):
        """itxn_field Assets appends asset IDs to the inner txn."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);

    itxn_begin(s, ctx);
    ctx.building_txn.NumAssets = 0;

    pushint(s, 100);
    itxn_field_set(s, ctx, Assets);
    pushint(s, 200);
    itxn_field_set(s, ctx, Assets);

    __CPROVER_assert(ctx.building_txn.NumAssets == 2, "2 assets added");
    __CPROVER_assert(ctx.building_txn.Assets[0] == 100, "asset 0 correct");
    __CPROVER_assert(ctx.building_txn.Assets[1] == 200, "asset 1 correct");
    return 0;
}
""")
        assert result["verified"], f"itxn_field_set assets failed:\n{result['stderr']}"

    def test_itxn_field_set_applications(self, opcodes):
        """itxn_field Applications appends app IDs to the inner txn."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);

    itxn_begin(s, ctx);
    ctx.building_txn.NumApplications = 0;

    pushint(s, 500);
    itxn_field_set(s, ctx, Applications);

    __CPROVER_assert(ctx.building_txn.NumApplications == 1, "1 app added");
    __CPROVER_assert(ctx.building_txn.Applications[0] == 500, "app 0 correct");
    return 0;
}
""")
        assert result["verified"], f"itxn_field_set applications failed:\n{result['stderr']}"


# ============================================================================
# Property helpers (properties.h)
# ============================================================================

class TestPropertyHelpers:
    """Tests for property helper functions in properties.h."""

    def test_prop_get_global_int(self, opcodes):
        """prop_get_global_int retrieves global int, returns default if missing."""
        result = opcodes.verify_cpp("""
int main() {
    BlockchainState BS; bs_init(BS);

    // No key yet — should return default
    __CPROVER_assert(prop_get_global_int(BS, "counter", 42) == 42, "default");

    // Set a global int
    uint8_t key[] = {'c','o','u','n','t','e','r'};
    gs_put(BS.globals, key, 7, sv_int(100));
    __CPROVER_assert(prop_get_global_int(BS, "counter", 0) == 100, "found");
    return 0;
}
""")
        assert result["verified"], f"prop_get_global_int failed:\n{result['stderr']}"

    def test_prop_global_changed(self, opcodes):
        """prop_global_changed detects int value changes between states."""
        result = opcodes.verify_cpp("""
int main() {
    BlockchainState before; bs_init(before);
    BlockchainState after; bs_init(after);

    uint8_t key[] = {'x'};
    gs_put(before.globals, key, 1, sv_int(10));
    gs_put(after.globals, key, 1, sv_int(10));
    __CPROVER_assert(!prop_global_changed(before, after, "x"), "same");

    gs_put(after.globals, key, 1, sv_int(20));
    __CPROVER_assert(prop_global_changed(before, after, "x"), "changed");
    return 0;
}
""")
        assert result["verified"], f"prop_global_changed failed:\n{result['stderr']}"

    def test_prop_get_box(self, opcodes):
        """prop_get_box retrieves box data by string key."""
        result = opcodes.verify_cpp("""
int main() {
    BlockchainState BS; bs_init(BS);

    // No box yet
    uint32_t out_len = 0;
    __CPROVER_assert(prop_get_box(BS, "mybox", &out_len) == 0, "not found");

    // Create a box with data
    uint8_t key[] = {'m','y','b','o','x'};
    uint8_t data[] = {0xAA, 0xBB, 0xCC};
    box_put_entry(BS.boxes, key, 5, data, 3);

    uint8_t* result = prop_get_box(BS, "mybox", &out_len);
    __CPROVER_assert(result != 0, "found");
    __CPROVER_assert(out_len == 3, "len");
    __CPROVER_assert(result[0] == 0xAA, "byte 0");
    __CPROVER_assert(result[2] == 0xCC, "byte 2");
    return 0;
}
""")
        assert result["verified"], f"prop_get_box failed:\n{result['stderr']}"

    def test_prop_box_changed(self, opcodes):
        """prop_box_changed detects box modifications between states."""
        result = opcodes.verify_cpp("""
int main() {
    BlockchainState before; bs_init(before);
    BlockchainState after; bs_init(after);

    uint8_t key[] = {'b'};
    uint8_t d1[] = {0x01, 0x02};
    uint8_t d2[] = {0x01, 0x03};

    box_put_entry(before.boxes, key, 1, d1, 2);
    box_put_entry(after.boxes, key, 1, d1, 2);
    __CPROVER_assert(!prop_box_changed(before, after, "b"), "same");

    box_put_entry(after.boxes, key, 1, d2, 2);
    __CPROVER_assert(prop_box_changed(before, after, "b"), "changed");
    return 0;
}
""")
        assert result["verified"], f"prop_box_changed failed:\n{result['stderr']}"

    def test_prop_box_read_uint64(self, opcodes):
        """prop_box_read_uint64 reads big-endian uint64 from box data."""
        result = opcodes.verify_cpp("""
int main() {
    BlockchainState BS; bs_init(BS);
    uint8_t key[] = {'d'};
    // Store 0x0000000000000100 = 256 at offset 0
    uint8_t data[] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00};
    box_put_entry(BS.boxes, key, 1, data, 8);

    uint32_t out_len = 0;
    uint8_t* d = prop_get_box(BS, "d", &out_len);
    __CPROVER_assert(d != 0, "found");
    uint64_t val = prop_box_read_uint64(d, out_len, 0);
    __CPROVER_assert(val == 256, "value is 256");
    return 0;
}
""")
        assert result["verified"], f"prop_box_read_uint64 failed:\n{result['stderr']}"

    def test_prop_box_count(self, opcodes):
        """prop_box_count counts active boxes."""
        result = opcodes.verify_cpp("""
int main() {
    BlockchainState BS; bs_init(BS);
    __CPROVER_assert(prop_box_count(BS) == 0, "empty");

    uint8_t k1[] = {'a'}; uint8_t k2[] = {'b'};
    uint8_t d[] = {0x01};
    box_put_entry(BS.boxes, k1, 1, d, 1);
    box_put_entry(BS.boxes, k2, 1, d, 1);
    __CPROVER_assert(prop_box_count(BS) == 2, "two boxes");

    box_del_entry(BS.boxes, k1, 1);
    __CPROVER_assert(prop_box_count(BS) == 1, "one after del");
    return 0;
}
""")
        assert result["verified"], f"prop_box_count failed:\n{result['stderr']}"

    def test_prop_txn_method_selector(self, opcodes):
        """prop_txn_method_is checks ABI method selector."""
        result = opcodes.verify_cpp("""
int main() {
    Txn txn; memset(&txn, 0, sizeof(txn));
    txn.NumAppArgs = 1;
    txn.AppArgs[0][0] = 0xDE; txn.AppArgs[0][1] = 0xAD;
    txn.AppArgs[0][2] = 0xBE; txn.AppArgs[0][3] = 0xEF;
    txn.AppArgLens[0] = 4;

    __CPROVER_assert(prop_txn_method_is(txn, 0xDE, 0xAD, 0xBE, 0xEF), "match");
    __CPROVER_assert(!prop_txn_method_is(txn, 0x00, 0x00, 0x00, 0x00), "no match");
    return 0;
}
""")
        assert result["verified"], f"prop_txn_method_selector failed:\n{result['stderr']}"


# ============================================================================
# Stack Operations
# ============================================================================

class TestStackOps:
    """Tests for stack manipulation opcodes: pop, dup, dup2, swap, dig, bury,
    cover, uncover, popn, dupn, select_op."""

    def test_pop_removes_top(self, opcodes):
        """pop removes top value, leaving the one below."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 10);
    pushint(s, 20);
    pop(s);
    __CPROVER_assert(s.currentSize == 1, "one value left");
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 10, "remaining value is 10");
    return 0;
}
""")
        assert result["verified"], f"pop failed:\n{result['stderr']}"

    def test_dup_duplicates_top(self, opcodes):
        """dup copies the top value."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 42);
    dup(s);
    __CPROVER_assert(s.currentSize == 2, "two values");
    StackValue a = stack_pop(s);
    StackValue b = stack_pop(s);
    __CPROVER_assert(a.value == 42 && b.value == 42, "both are 42");
    return 0;
}
""")
        assert result["verified"], f"dup failed:\n{result['stderr']}"

    def test_dup2_duplicates_top_pair(self, opcodes):
        """dup2 duplicates the top two values."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 10);  // A
    pushint(s, 20);  // B
    dup2(s);
    __CPROVER_assert(s.currentSize == 4, "four values");
    StackValue d = stack_pop(s);  // top copy of B
    StackValue c = stack_pop(s);  // top copy of A
    StackValue b = stack_pop(s);  // original B
    StackValue a = stack_pop(s);  // original A
    __CPROVER_assert(a.value == 10 && c.value == 10, "A duplicated");
    __CPROVER_assert(b.value == 20 && d.value == 20, "B duplicated");
    return 0;
}
""")
        assert result["verified"], f"dup2 failed:\n{result['stderr']}"

    def test_swap_top_two(self, opcodes):
        """swap exchanges the top two values."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 10);  // A
    pushint(s, 20);  // B
    swap(s);
    StackValue top = stack_pop(s);
    StackValue bot = stack_pop(s);
    __CPROVER_assert(top.value == 10, "A is now on top");
    __CPROVER_assert(bot.value == 20, "B is now below");
    return 0;
}
""")
        assert result["verified"], f"swap failed:\n{result['stderr']}"

    def test_dig_n(self, opcodes):
        """dig N copies the value at depth N to the top."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 10);  // A  (depth 2)
    pushint(s, 20);  // B  (depth 1)
    pushint(s, 30);  // C  (depth 0 = top)
    dig(s, 2);
    __CPROVER_assert(s.currentSize == 4, "four values");
    StackValue top = stack_pop(s);
    __CPROVER_assert(top.value == 10, "dig 2 copies A to top");
    return 0;
}
""")
        assert result["verified"], f"dig failed:\n{result['stderr']}"

    def test_bury_n(self, opcodes):
        """bury N overwrites the value at depth N with the top, then removes top."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 10);  // A  (depth 2)
    pushint(s, 20);  // B  (depth 1)
    pushint(s, 30);  // C  (depth 0 = top)
    bury(s, 2);
    // C overwrites A's position, C removed from top
    // Stack: [30, 20]
    __CPROVER_assert(s.currentSize == 2, "two values");
    StackValue top = stack_pop(s);
    __CPROVER_assert(top.value == 20, "B remains");
    StackValue bot = stack_pop(s);
    __CPROVER_assert(bot.value == 30, "C replaced A");
    return 0;
}
""")
        assert result["verified"], f"bury failed:\n{result['stderr']}"

    def test_cover_n(self, opcodes):
        """cover N slides the top value under the next N values."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 10);  // A
    pushint(s, 20);  // B
    pushint(s, 30);  // C (top)
    cover(s, 2);
    // C slides under A,B => stack bottom-to-top: [30, 10, 20]
    __CPROVER_assert(s.currentSize == 3, "three values");
    StackValue v2 = stack_pop(s);  // top
    StackValue v1 = stack_pop(s);
    StackValue v0 = stack_pop(s);  // bottom
    __CPROVER_assert(v2.value == 20, "top is B");
    __CPROVER_assert(v1.value == 10, "middle is A");
    __CPROVER_assert(v0.value == 30, "bottom is C");
    return 0;
}
""")
        assert result["verified"], f"cover failed:\n{result['stderr']}"

    def test_uncover_n(self, opcodes):
        """uncover N brings the value at depth N to the top."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 10);  // A (depth 2)
    pushint(s, 20);  // B (depth 1)
    pushint(s, 30);  // C (depth 0 = top)
    uncover(s, 2);
    // A comes to top => stack bottom-to-top: [20, 30, 10]
    __CPROVER_assert(s.currentSize == 3, "three values");
    StackValue v2 = stack_pop(s);
    StackValue v1 = stack_pop(s);
    StackValue v0 = stack_pop(s);
    __CPROVER_assert(v2.value == 10, "top is A");
    __CPROVER_assert(v1.value == 30, "middle is C");
    __CPROVER_assert(v0.value == 20, "bottom is B");
    return 0;
}
""")
        assert result["verified"], f"uncover failed:\n{result['stderr']}"

    def test_popn(self, opcodes):
        """popn N removes N values from the stack."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 1);
    pushint(s, 2);
    pushint(s, 3);
    pushint(s, 4);
    popn(s, 3);
    __CPROVER_assert(s.currentSize == 1, "one left");
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 1, "bottom value remains");
    return 0;
}
""")
        assert result["verified"], f"popn failed:\n{result['stderr']}"

    def test_dupn(self, opcodes):
        """dupn N creates N additional copies of the top value."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 7);
    dupn(s, 3);
    __CPROVER_assert(s.currentSize == 4, "1 original + 3 copies");
    for (int i = 0; i < 4; i++) {
        StackValue v = stack_pop(s);
        __CPROVER_assert(v.value == 7, "all copies are 7");
    }
    return 0;
}
""")
        assert result["verified"], f"dupn failed:\n{result['stderr']}"

    def test_select_nonzero(self, opcodes):
        """select with nonzero condition selects B (second from top)."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 10);  // A
    pushint(s, 20);  // B
    pushint(s, 1);   // condition (nonzero)
    select_op(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 20, "nonzero selects B");
    return 0;
}
""")
        assert result["verified"], f"select nonzero failed:\n{result['stderr']}"

    def test_select_zero(self, opcodes):
        """select with zero condition selects A (third from top)."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 10);  // A
    pushint(s, 20);  // B
    pushint(s, 0);   // condition (zero)
    select_op(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 10, "zero selects A");
    return 0;
}
""")
        assert result["verified"], f"select zero failed:\n{result['stderr']}"


# ============================================================================
# Arithmetic
# ============================================================================

class TestArithmetic:
    """Tests for arithmetic opcodes: add, sub, mul, div_op, mod_op, exp_op, sqrt_op."""

    def test_add_basic(self, opcodes):
        """10 + 20 = 30."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 10);
    pushint(s, 20);
    add(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 30, "10+20=30");
    return 0;
}
""")
        assert result["verified"], f"add basic failed:\n{result['stderr']}"

    def test_add_commutative(self, opcodes):
        """a+b == b+a."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s1; stack_init(s1);
    Stack s2; stack_init(s2);
    pushint(s1, 7);
    pushint(s1, 13);
    add(s1);
    pushint(s2, 13);
    pushint(s2, 7);
    add(s2);
    __CPROVER_assert(stack_pop(s1).value == stack_pop(s2).value, "add commutative");
    return 0;
}
""")
        assert result["verified"], f"add commutative failed:\n{result['stderr']}"

    def test_sub_basic(self, opcodes):
        """30 - 10 = 20."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 30);
    pushint(s, 10);
    sub(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 20, "30-10=20");
    return 0;
}
""")
        assert result["verified"], f"sub basic failed:\n{result['stderr']}"

    def test_mul_basic(self, opcodes):
        """6 * 7 = 42."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 6);
    pushint(s, 7);
    mul(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 42, "6*7=42");
    return 0;
}
""")
        assert result["verified"], f"mul basic failed:\n{result['stderr']}"

    def test_div_basic(self, opcodes):
        """42 / 6 = 7."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 42);
    pushint(s, 6);
    div_op(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 7, "42/6=7");
    return 0;
}
""")
        assert result["verified"], f"div basic failed:\n{result['stderr']}"

    def test_mod_basic(self, opcodes):
        """17 % 5 = 2."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 17);
    pushint(s, 5);
    mod_op(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 2, "17%5=2");
    return 0;
}
""")
        assert result["verified"], f"mod basic failed:\n{result['stderr']}"

    def test_exp_basic(self, opcodes):
        """2^10 = 1024."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 2);
    pushint(s, 10);
    exp_op(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 1024, "2^10=1024");
    return 0;
}
""")
        assert result["verified"], f"exp basic failed:\n{result['stderr']}"

    def test_sqrt_basic(self, opcodes):
        """sqrt(16) = 4."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 16);
    sqrt_op(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 4, "sqrt(16)=4");
    return 0;
}
""")
        assert result["verified"], f"sqrt basic failed:\n{result['stderr']}"

    def test_sqrt_non_perfect(self, opcodes):
        """sqrt(10) = 3 (floor)."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 10);
    sqrt_op(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 3, "floor(sqrt(10))=3");
    return 0;
}
""")
        assert result["verified"], f"sqrt non-perfect failed:\n{result['stderr']}"


# ============================================================================
# Comparisons
# ============================================================================

class TestComparisons:
    """Tests for comparison opcodes: bool_eq, bool_neq, bool_lt, bool_gt, bool_leq, bool_geq."""

    def test_eq_true(self, opcodes):
        """5 == 5 → 1."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 5);
    pushint(s, 5);
    bool_eq(s);
    __CPROVER_assert(stack_pop(s).value == 1, "5==5");
    return 0;
}
""")
        assert result["verified"], f"eq true failed:\n{result['stderr']}"

    def test_eq_false(self, opcodes):
        """5 == 6 → 0."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 5);
    pushint(s, 6);
    bool_eq(s);
    __CPROVER_assert(stack_pop(s).value == 0, "5!=6");
    return 0;
}
""")
        assert result["verified"], f"eq false failed:\n{result['stderr']}"

    def test_neq_true(self, opcodes):
        """5 != 6 → 1."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 5);
    pushint(s, 6);
    bool_neq(s);
    __CPROVER_assert(stack_pop(s).value == 1, "5!=6");
    return 0;
}
""")
        assert result["verified"], f"neq true failed:\n{result['stderr']}"

    def test_neq_false(self, opcodes):
        """5 != 5 → 0."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 5);
    pushint(s, 5);
    bool_neq(s);
    __CPROVER_assert(stack_pop(s).value == 0, "5==5 neq is 0");
    return 0;
}
""")
        assert result["verified"], f"neq false failed:\n{result['stderr']}"

    def test_lt_true(self, opcodes):
        """3 < 5 → 1."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 3);
    pushint(s, 5);
    bool_lt(s);
    __CPROVER_assert(stack_pop(s).value == 1, "3<5");
    return 0;
}
""")
        assert result["verified"], f"lt true failed:\n{result['stderr']}"

    def test_lt_false(self, opcodes):
        """5 < 3 → 0."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 5);
    pushint(s, 3);
    bool_lt(s);
    __CPROVER_assert(stack_pop(s).value == 0, "5 not < 3");
    return 0;
}
""")
        assert result["verified"], f"lt false failed:\n{result['stderr']}"

    def test_gt_true(self, opcodes):
        """5 > 3 → 1."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 5);
    pushint(s, 3);
    bool_gt(s);
    __CPROVER_assert(stack_pop(s).value == 1, "5>3");
    return 0;
}
""")
        assert result["verified"], f"gt true failed:\n{result['stderr']}"

    def test_gt_false(self, opcodes):
        """3 > 5 → 0."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 3);
    pushint(s, 5);
    bool_gt(s);
    __CPROVER_assert(stack_pop(s).value == 0, "3 not > 5");
    return 0;
}
""")
        assert result["verified"], f"gt false failed:\n{result['stderr']}"

    def test_leq_true(self, opcodes):
        """3 <= 5 → 1."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 3);
    pushint(s, 5);
    bool_leq(s);
    __CPROVER_assert(stack_pop(s).value == 1, "3<=5");
    return 0;
}
""")
        assert result["verified"], f"leq true failed:\n{result['stderr']}"

    def test_leq_equal(self, opcodes):
        """5 <= 5 → 1."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 5);
    pushint(s, 5);
    bool_leq(s);
    __CPROVER_assert(stack_pop(s).value == 1, "5<=5");
    return 0;
}
""")
        assert result["verified"], f"leq equal failed:\n{result['stderr']}"

    def test_geq_true(self, opcodes):
        """5 >= 3 → 1."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 5);
    pushint(s, 3);
    bool_geq(s);
    __CPROVER_assert(stack_pop(s).value == 1, "5>=3");
    return 0;
}
""")
        assert result["verified"], f"geq true failed:\n{result['stderr']}"

    def test_geq_equal(self, opcodes):
        """5 >= 5 → 1."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 5);
    pushint(s, 5);
    bool_geq(s);
    __CPROVER_assert(stack_pop(s).value == 1, "5>=5");
    return 0;
}
""")
        assert result["verified"], f"geq equal failed:\n{result['stderr']}"

    def test_eq_bytes(self, opcodes):
        """Byte-slice equality check."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t a[] = {0xAA, 0xBB};
    uint8_t b[] = {0xAA, 0xBB};
    uint8_t c[] = {0xAA, 0xCC};
    stack_push(s, sv_bytes(a, 2));
    stack_push(s, sv_bytes(b, 2));
    bool_eq(s);
    __CPROVER_assert(stack_pop(s).value == 1, "same bytes eq");

    stack_push(s, sv_bytes(a, 2));
    stack_push(s, sv_bytes(c, 2));
    bool_eq(s);
    __CPROVER_assert(stack_pop(s).value == 0, "diff bytes neq");
    return 0;
}
""")
        assert result["verified"], f"eq bytes failed:\n{result['stderr']}"


# ============================================================================
# Logic
# ============================================================================

class TestLogic:
    """Tests for logical opcodes: bool_and, bool_or, not_logical."""

    def test_and_both_true(self, opcodes):
        """1 && 1 → 1."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 1);
    pushint(s, 1);
    bool_and(s);
    __CPROVER_assert(stack_pop(s).value == 1, "1&&1=1");
    return 0;
}
""")
        assert result["verified"], f"and both true failed:\n{result['stderr']}"

    def test_and_one_false(self, opcodes):
        """1 && 0 → 0."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 1);
    pushint(s, 0);
    bool_and(s);
    __CPROVER_assert(stack_pop(s).value == 0, "1&&0=0");
    return 0;
}
""")
        assert result["verified"], f"and one false failed:\n{result['stderr']}"

    def test_and_both_false(self, opcodes):
        """0 && 0 → 0."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 0);
    pushint(s, 0);
    bool_and(s);
    __CPROVER_assert(stack_pop(s).value == 0, "0&&0=0");
    return 0;
}
""")
        assert result["verified"], f"and both false failed:\n{result['stderr']}"

    def test_or_both_true(self, opcodes):
        """1 || 1 → 1."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 1);
    pushint(s, 1);
    bool_or(s);
    __CPROVER_assert(stack_pop(s).value == 1, "1||1=1");
    return 0;
}
""")
        assert result["verified"], f"or both true failed:\n{result['stderr']}"

    def test_or_one_true(self, opcodes):
        """0 || 1 → 1."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 0);
    pushint(s, 1);
    bool_or(s);
    __CPROVER_assert(stack_pop(s).value == 1, "0||1=1");
    return 0;
}
""")
        assert result["verified"], f"or one true failed:\n{result['stderr']}"

    def test_or_both_false(self, opcodes):
        """0 || 0 → 0."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 0);
    pushint(s, 0);
    bool_or(s);
    __CPROVER_assert(stack_pop(s).value == 0, "0||0=0");
    return 0;
}
""")
        assert result["verified"], f"or both false failed:\n{result['stderr']}"

    def test_not_zero(self, opcodes):
        """!0 → 1."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 0);
    not_logical(s);
    __CPROVER_assert(stack_pop(s).value == 1, "!0=1");
    return 0;
}
""")
        assert result["verified"], f"not zero failed:\n{result['stderr']}"

    def test_not_nonzero(self, opcodes):
        """!42 → 0."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 42);
    not_logical(s);
    __CPROVER_assert(stack_pop(s).value == 0, "!42=0");
    return 0;
}
""")
        assert result["verified"], f"not nonzero failed:\n{result['stderr']}"


# ============================================================================
# Bitwise
# ============================================================================

class TestBitwise:
    """Tests for bitwise opcodes: bitwise_and, bitwise_or, bitwise_xor,
    bitwise_neg, bitwise_shr, bitwise_shl."""

    def test_bitwise_and(self, opcodes):
        """0xFF00 & 0x0FF0 = 0x0F00."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 0xFF00);
    pushint(s, 0x0FF0);
    bitwise_and(s);
    __CPROVER_assert(stack_pop(s).value == 0x0F00, "bitwise and");
    return 0;
}
""")
        assert result["verified"], f"bitwise_and failed:\n{result['stderr']}"

    def test_bitwise_or(self, opcodes):
        """0xF000 | 0x000F = 0xF00F."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 0xF000);
    pushint(s, 0x000F);
    bitwise_or(s);
    __CPROVER_assert(stack_pop(s).value == 0xF00F, "bitwise or");
    return 0;
}
""")
        assert result["verified"], f"bitwise_or failed:\n{result['stderr']}"

    def test_bitwise_xor(self, opcodes):
        """0xFF ^ 0xFF = 0."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 0xFF);
    pushint(s, 0xFF);
    bitwise_xor(s);
    __CPROVER_assert(stack_pop(s).value == 0, "xor self is 0");
    return 0;
}
""")
        assert result["verified"], f"bitwise_xor failed:\n{result['stderr']}"

    def test_bitwise_neg(self, opcodes):
        """~0 = UINT64_MAX."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 0);
    bitwise_neg(s);
    __CPROVER_assert(stack_pop(s).value == UINT64_MAX, "~0 = UINT64_MAX");
    return 0;
}
""")
        assert result["verified"], f"bitwise_neg failed:\n{result['stderr']}"

    def test_shr(self, opcodes):
        """16 >> 2 = 4."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 16);
    pushint(s, 2);
    bitwise_shr(s);
    __CPROVER_assert(stack_pop(s).value == 4, "16>>2=4");
    return 0;
}
""")
        assert result["verified"], f"shr failed:\n{result['stderr']}"

    def test_shl(self, opcodes):
        """1 << 10 = 1024."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 1);
    pushint(s, 10);
    bitwise_shl(s);
    __CPROVER_assert(stack_pop(s).value == 1024, "1<<10=1024");
    return 0;
}
""")
        assert result["verified"], f"shl failed:\n{result['stderr']}"


# ============================================================================
# Byte Operations
# ============================================================================

class TestByteOps:
    """Tests for byte opcodes: itob, btoi, len, concat, bzero."""

    def test_itob_basic(self, opcodes):
        """itob(256) produces [0,0,0,0,0,0,1,0]."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 256);
    itob(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice_len == 8, "8 bytes");
    __CPROVER_assert(r.byteslice[6] == 1, "byte 6 is 1");
    __CPROVER_assert(r.byteslice[7] == 0, "byte 7 is 0");
    __CPROVER_assert(r.byteslice[0] == 0, "leading zeros");
    return 0;
}
""")
        assert result["verified"], f"itob basic failed:\n{result['stderr']}"

    def test_btoi_basic(self, opcodes):
        """btoi([0,0,0,0,0,0,1,0]) = 256."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t data[8] = {0,0,0,0,0,0,1,0};
    stack_push(s, sv_bytes(data, 8));
    btoi(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(!r._is_bytes, "is int");
    __CPROVER_assert(r.value == 256, "btoi=256");
    return 0;
}
""")
        assert result["verified"], f"btoi basic failed:\n{result['stderr']}"

    def test_itob_btoi_roundtrip(self, opcodes):
        """btoi(itob(X)) == X."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 12345678);
    itob(s);
    btoi(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 12345678, "roundtrip");
    return 0;
}
""")
        assert result["verified"], f"itob/btoi roundtrip failed:\n{result['stderr']}"

    def test_len_basic(self, opcodes):
        """len of 5-byte value = 5."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t data[5] = {1,2,3,4,5};
    stack_push(s, sv_bytes(data, 5));
    len(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 5, "len=5");
    return 0;
}
""")
        assert result["verified"], f"len basic failed:\n{result['stderr']}"

    def test_concat_basic(self, opcodes):
        """[AA,BB] ++ [CC] = [AA,BB,CC]."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t a[] = {0xAA, 0xBB};
    uint8_t b[] = {0xCC};
    stack_push(s, sv_bytes(a, 2));
    stack_push(s, sv_bytes(b, 1));
    concat(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice_len == 3, "len 3");
    __CPROVER_assert(r.byteslice[0] == 0xAA, "b0");
    __CPROVER_assert(r.byteslice[1] == 0xBB, "b1");
    __CPROVER_assert(r.byteslice[2] == 0xCC, "b2");
    return 0;
}
""")
        assert result["verified"], f"concat basic failed:\n{result['stderr']}"

    def test_bzero_basic(self, opcodes):
        """bzero(4) produces [0,0,0,0]."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 4);
    bzero(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice_len == 4, "len 4");
    __CPROVER_assert(r.byteslice[0] == 0, "b0 zero");
    __CPROVER_assert(r.byteslice[1] == 0, "b1 zero");
    __CPROVER_assert(r.byteslice[2] == 0, "b2 zero");
    __CPROVER_assert(r.byteslice[3] == 0, "b3 zero");
    return 0;
}
""")
        assert result["verified"], f"bzero basic failed:\n{result['stderr']}"


# ============================================================================
# Dynamic Extract / Substring
# ============================================================================

class TestDynamicExtract:
    """Tests for extract3, extract_uint16, extract_uint64, substring3."""

    def test_extract3_dynamic(self, opcodes):
        """extract3 with stack args extracts correct slice."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t data[8] = {0x10, 0x20, 0x30, 0x40, 0x50, 0x60, 0x70, 0x80};
    stack_push(s, sv_bytes(data, 8));
    pushint(s, 2);  // start
    pushint(s, 3);  // length
    extract3(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice_len == 3, "len 3");
    __CPROVER_assert(r.byteslice[0] == 0x30, "b0");
    __CPROVER_assert(r.byteslice[1] == 0x40, "b1");
    __CPROVER_assert(r.byteslice[2] == 0x50, "b2");
    return 0;
}
""")
        assert result["verified"], f"extract3 failed:\n{result['stderr']}"

    def test_extract_uint16(self, opcodes):
        """extract_uint16 decodes big-endian 2 bytes."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t data[4] = {0x00, 0x01, 0x00, 0xFF};
    stack_push(s, sv_bytes(data, 4));
    pushint(s, 0);  // offset
    extract_uint16(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(!r._is_bytes, "is int");
    __CPROVER_assert(r.value == 1, "0x0001 = 1");

    stack_push(s, sv_bytes(data, 4));
    pushint(s, 2);  // offset
    extract_uint16(s);
    r = stack_pop(s);
    __CPROVER_assert(r.value == 255, "0x00FF = 255");
    return 0;
}
""")
        assert result["verified"], f"extract_uint16 failed:\n{result['stderr']}"

    def test_extract_uint64(self, opcodes):
        """extract_uint64 decodes big-endian 8 bytes."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t data[8] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00};
    stack_push(s, sv_bytes(data, 8));
    pushint(s, 0);
    extract_uint64(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(!r._is_bytes, "is int");
    __CPROVER_assert(r.value == 256, "big-endian 256");
    return 0;
}
""")
        assert result["verified"], f"extract_uint64 failed:\n{result['stderr']}"

    def test_substring3_dynamic(self, opcodes):
        """substring3 with stack args extracts correct range."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t data[6] = {0xA0, 0xB0, 0xC0, 0xD0, 0xE0, 0xF0};
    stack_push(s, sv_bytes(data, 6));
    pushint(s, 1);  // start
    pushint(s, 4);  // end
    substring3(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice_len == 3, "len 3");
    __CPROVER_assert(r.byteslice[0] == 0xB0, "b0");
    __CPROVER_assert(r.byteslice[1] == 0xC0, "b1");
    __CPROVER_assert(r.byteslice[2] == 0xD0, "b2");
    return 0;
}
""")
        assert result["verified"], f"substring3 failed:\n{result['stderr']}"


# ============================================================================
# Assert / Err
# ============================================================================

class TestAssertErr:
    """Tests for avm_assert and err opcodes."""

    def test_assert_passes(self, opcodes):
        """avm_assert with nonzero value succeeds (no panic)."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    __avm_panicked = false;
    pushint(s, 1);
    avm_assert(s);
    __CPROVER_assert(!__avm_panicked, "assert with 1 does not panic");
    return 0;
}
""")
        assert result["verified"], f"assert passes failed:\n{result['stderr']}"

    def test_assert_fails(self, opcodes):
        """avm_assert with zero triggers panic."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    __avm_panicked = false;
    pushint(s, 0);
    avm_assert(s);
    __CPROVER_assert(__avm_panicked, "assert with 0 panics");
    return 0;
}
""")
        assert result["verified"], f"assert fails failed:\n{result['stderr']}"

    def test_err_panics(self, opcodes):
        """err() triggers panic."""
        result = opcodes.verify_cpp("""
int main() {
    __avm_panicked = false;
    err();
    __CPROVER_assert(__avm_panicked, "err panics");
    return 0;
}
""")
        assert result["verified"], f"err panics failed:\n{result['stderr']}"


# ============================================================================
# Logging
# ============================================================================

class TestLogging:
    """Tests for avm_log opcode."""

    def test_log_basic(self, opcodes):
        """log records bytes in context."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    uint8_t data[] = {0xAA, 0xBB, 0xCC};
    stack_push(s, sv_bytes(data, 3));
    avm_log(s, ctx);
    __CPROVER_assert(ctx.NumLogs == 1, "one log");
    __CPROVER_assert(ctx.LogLens[0] == 3, "log len 3");
    __CPROVER_assert(ctx.Logs[0][0] == 0xAA, "log byte 0");
    __CPROVER_assert(ctx.Logs[0][1] == 0xBB, "log byte 1");
    __CPROVER_assert(ctx.Logs[0][2] == 0xCC, "log byte 2");
    return 0;
}
""")
        assert result["verified"], f"log basic failed:\n{result['stderr']}"

    def test_log_multiple(self, opcodes):
        """Multiple logs increment counter."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    uint8_t d1[] = {0x01};
    uint8_t d2[] = {0x02};
    stack_push(s, sv_bytes(d1, 1));
    avm_log(s, ctx);
    stack_push(s, sv_bytes(d2, 1));
    avm_log(s, ctx);
    __CPROVER_assert(ctx.NumLogs == 2, "two logs");
    __CPROVER_assert(ctx.Logs[0][0] == 0x01, "first log");
    __CPROVER_assert(ctx.Logs[1][0] == 0x02, "second log");
    return 0;
}
""")
        assert result["verified"], f"log multiple failed:\n{result['stderr']}"


# ============================================================================
# Crypto Stubs
# ============================================================================

class TestCryptoStubs:
    """Tests for crypto stub opcodes: sha256, sha3_256, keccak256, ed25519verify."""

    def test_sha256_produces_32_bytes(self, opcodes):
        """sha256 returns a 32-byte bytes value."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t input[] = {0x01, 0x02, 0x03};
    stack_push(s, sv_bytes(input, 3));
    sha256(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice_len == 32, "32 bytes");
    return 0;
}
""")
        assert result["verified"], f"sha256 failed:\n{result['stderr']}"

    def test_sha3_256_is_bytes(self, opcodes):
        """sha3_256 returns a 32-byte bytes value."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t input[] = {0x04, 0x05};
    stack_push(s, sv_bytes(input, 2));
    sha3_256(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice_len == 32, "32 bytes");
    return 0;
}
""")
        assert result["verified"], f"sha3_256 failed:\n{result['stderr']}"

    def test_keccak256_is_bytes(self, opcodes):
        """keccak256 returns a 32-byte bytes value."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t input[] = {0x06};
    stack_push(s, sv_bytes(input, 1));
    keccak256(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice_len == 32, "32 bytes");
    return 0;
}
""")
        assert result["verified"], f"keccak256 failed:\n{result['stderr']}"

    def test_ed25519verify_returns_bool(self, opcodes):
        """ed25519verify result is 0 or 1."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t data[] = {0x01};
    uint8_t sig[64]; memset(sig, 0, 64);
    uint8_t key[32]; memset(key, 0, 32);
    stack_push(s, sv_bytes(data, 1));
    stack_push(s, sv_bytes(sig, 64));
    stack_push(s, sv_bytes(key, 32));
    ed25519verify(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes == false, "is int");
    __CPROVER_assert(r.value == 0 || r.value == 1, "0 or 1");
    return 0;
}
""")
        assert result["verified"], f"ed25519verify failed:\n{result['stderr']}"


# ============================================================================
# Global State (dedicated)
# ============================================================================

class TestGlobalState:
    """Tests for app_global_put, app_global_get, app_global_del."""

    def test_global_put_get_roundtrip(self, opcodes):
        """put then get returns value."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    uint8_t key[] = {'m','y','k'};
    stack_push(s, sv_bytes(key, 3));
    pushint(s, 999);
    app_global_put(s, BS, ctx);
    stack_push(s, sv_bytes(key, 3));
    app_global_get(s, BS, ctx);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 999, "put then get");
    return 0;
}
""")
        assert result["verified"], f"global put/get roundtrip failed:\n{result['stderr']}"

    def test_global_get_missing(self, opcodes):
        """get on missing key returns 0."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    uint8_t key[] = {'n','o'};
    stack_push(s, sv_bytes(key, 2));
    app_global_get(s, BS, ctx);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 0, "missing returns 0");
    return 0;
}
""")
        assert result["verified"], f"global get missing failed:\n{result['stderr']}"

    def test_global_del_then_get(self, opcodes):
        """del then get returns 0."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    uint8_t key[] = {'d','k'};
    // put
    stack_push(s, sv_bytes(key, 2));
    pushint(s, 77);
    app_global_put(s, BS, ctx);
    // del
    stack_push(s, sv_bytes(key, 2));
    app_global_del(s, BS, ctx);
    // get
    stack_push(s, sv_bytes(key, 2));
    app_global_get(s, BS, ctx);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 0, "deleted key returns 0");
    return 0;
}
""")
        assert result["verified"], f"global del then get failed:\n{result['stderr']}"

    def test_global_put_exceeds_uint_schema_panics(self, opcodes):
        """Putting more uints than CBMC_GLOBAL_NUM_UINT triggers panic."""
        result = opcodes.verify_cpp("""
#define CBMC_GLOBAL_NUM_UINT 2
#define CBMC_GLOBAL_NUM_BYTESLICE 2
#include "cbmc_avm.h"
#include "cbmc_opcodes.h"
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    // Put 2 uints (within schema)
    uint8_t k1[] = {'a'}; stack_push(s, sv_bytes(k1, 1)); pushint(s, 1);
    app_global_put(s, BS, ctx);
    uint8_t k2[] = {'b'}; stack_push(s, sv_bytes(k2, 1)); pushint(s, 2);
    app_global_put(s, BS, ctx);
    // Third uint exceeds schema — should panic
    uint8_t k3[] = {'c'}; stack_push(s, sv_bytes(k3, 1)); pushint(s, 3);
    app_global_put(s, BS, ctx);
    __CPROVER_assert(!__avm_panicked, "should not panic");
    return 0;
}
""", skip_default_includes=True)
        assert not result["verified"], \
            f"Expected panic when exceeding uint schema:\n{result['stderr']}"

    def test_global_put_update_existing_no_panic(self, opcodes):
        """Updating an existing key does not count as a new entry."""
        result = opcodes.verify_cpp("""
#define CBMC_GLOBAL_NUM_UINT 1
#define CBMC_GLOBAL_NUM_BYTESLICE 1
#include "cbmc_avm.h"
#include "cbmc_opcodes.h"
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    // Put 1 uint (fills schema)
    uint8_t k1[] = {'a'}; stack_push(s, sv_bytes(k1, 1)); pushint(s, 1);
    app_global_put(s, BS, ctx);
    // Update same key — should NOT panic
    stack_push(s, sv_bytes(k1, 1)); pushint(s, 99);
    app_global_put(s, BS, ctx);
    __CPROVER_assert(!__avm_panicked, "update should not panic");
    return 0;
}
""", skip_default_includes=True)
        assert result["verified"], \
            f"Updating existing key should not trigger schema panic:\n{result['stderr']}"

    def test_global_put_exceeds_bytes_schema_panics(self, opcodes):
        """Putting more byteslices than CBMC_GLOBAL_NUM_BYTESLICE triggers panic."""
        result = opcodes.verify_cpp("""
#define CBMC_GLOBAL_NUM_UINT 2
#define CBMC_GLOBAL_NUM_BYTESLICE 1
#include "cbmc_avm.h"
#include "cbmc_opcodes.h"
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    // Put 1 byteslice (fills schema)
    uint8_t k1[] = {'a'}; uint8_t v1[] = {0x42};
    stack_push(s, sv_bytes(k1, 1)); stack_push(s, sv_bytes(v1, 1));
    app_global_put(s, BS, ctx);
    // Second byteslice exceeds schema — should panic
    uint8_t k2[] = {'b'}; uint8_t v2[] = {0x43};
    stack_push(s, sv_bytes(k2, 1)); stack_push(s, sv_bytes(v2, 1));
    app_global_put(s, BS, ctx);
    __CPROVER_assert(!__avm_panicked, "should not panic");
    return 0;
}
""", skip_default_includes=True)
        assert not result["verified"], \
            f"Expected panic when exceeding byteslice schema:\n{result['stderr']}"


# ============================================================================
# Local Get-Ex
# ============================================================================

class TestLocalGetEx:
    """Tests for app_local_get_ex."""

    def test_local_get_ex_found(self, opcodes):
        """put then get_ex returns value + found=1."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    Txn txn;
    __CPROVER_array_set(txn.Sender, 1);
    // Opt in the sender (create LocalEntry so put succeeds)
    ls_ensure_account(BS.locals, txn.Sender);

    uint8_t key[] = {'e','x'};
    // local put
    pushint(s, 0);
    stack_push(s, sv_bytes(key, 2));
    pushint(s, 55);
    app_local_put(s, BS, txn, ctx);

    // local get_ex: pops key, app_id, acct
    pushint(s, 0);   // acct
    pushint(s, 1);   // app_id
    stack_push(s, sv_bytes(key, 2));  // key
    app_local_get_ex(s, BS, txn, ctx);
    StackValue found = stack_pop(s);
    StackValue val = stack_pop(s);
    __CPROVER_assert(found.value == 1, "found=1");
    __CPROVER_assert(val.value == 55, "value=55");
    return 0;
}
""")
        assert result["verified"], f"local get_ex found failed:\n{result['stderr']}"

    def test_local_get_ex_not_found(self, opcodes):
        """get_ex on missing returns 0 + found=0."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    Txn txn;
    __CPROVER_array_set(txn.Sender, 1);

    uint8_t key[] = {'n','f'};
    pushint(s, 0);
    pushint(s, 1);
    stack_push(s, sv_bytes(key, 2));
    app_local_get_ex(s, BS, txn, ctx);
    StackValue found = stack_pop(s);
    StackValue val = stack_pop(s);
    __CPROVER_assert(found.value == 0, "not found");
    __CPROVER_assert(val.value == 0, "default zero");
    return 0;
}
""")
        assert result["verified"], f"local get_ex not found failed:\n{result['stderr']}"

    def test_local_put_non_opted_in_panics(self, opcodes):
        """app_local_put panics if account is not opted in."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    Txn txn;
    __CPROVER_array_set(txn.Sender, 0x42);
    // Do NOT opt in — no ls_ensure_account

    uint8_t key[] = {'k'};
    pushint(s, 0);  // acct = sender
    stack_push(s, sv_bytes(key, 1));
    pushint(s, 99);
    app_local_put(s, BS, txn, ctx);

    __CPROVER_assert(__avm_panicked, "should panic on non-opted-in put");
    return 0;
}
""")
        assert result["verified"], f"local put non-opted-in failed:\n{result['stderr']}"

    def test_local_put_exceeds_uint_schema_panics(self, opcodes):
        """Putting more local uints than CBMC_LOCAL_NUM_UINT triggers panic."""
        result = opcodes.verify_cpp("""
#define CBMC_LOCAL_NUM_UINT 2
#define CBMC_LOCAL_NUM_BYTESLICE 2
#include "cbmc_avm.h"
#include "cbmc_opcodes.h"
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    Txn txn;
    memset(txn.Sender, 0x42, 32);
    // Opt in the account
    ls_ensure_account(BS.locals, txn.Sender);
    // Put 2 uints (within schema)
    uint8_t k1[] = {'a'}; pushint(s, 0); stack_push(s, sv_bytes(k1, 1)); pushint(s, 1);
    app_local_put(s, BS, txn, ctx);
    uint8_t k2[] = {'b'}; pushint(s, 0); stack_push(s, sv_bytes(k2, 1)); pushint(s, 2);
    app_local_put(s, BS, txn, ctx);
    // Third uint exceeds schema — should panic
    uint8_t k3[] = {'c'}; pushint(s, 0); stack_push(s, sv_bytes(k3, 1)); pushint(s, 3);
    app_local_put(s, BS, txn, ctx);
    __CPROVER_assert(!__avm_panicked, "should not panic");
    return 0;
}
""", skip_default_includes=True)
        assert not result["verified"], \
            f"Expected panic when exceeding local uint schema:\n{result['stderr']}"

    def test_local_put_update_existing_no_panic(self, opcodes):
        """Updating an existing local key does not count as a new entry."""
        result = opcodes.verify_cpp("""
#define CBMC_LOCAL_NUM_UINT 1
#define CBMC_LOCAL_NUM_BYTESLICE 1
#include "cbmc_avm.h"
#include "cbmc_opcodes.h"
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    Txn txn;
    memset(txn.Sender, 0x42, 32);
    // Opt in the account
    ls_ensure_account(BS.locals, txn.Sender);
    // Put 1 uint (fills schema)
    uint8_t k1[] = {'a'}; pushint(s, 0); stack_push(s, sv_bytes(k1, 1)); pushint(s, 1);
    app_local_put(s, BS, txn, ctx);
    // Update same key — should NOT panic
    pushint(s, 0); stack_push(s, sv_bytes(k1, 1)); pushint(s, 99);
    app_local_put(s, BS, txn, ctx);
    __CPROVER_assert(!__avm_panicked, "update should not panic");
    return 0;
}
""", skip_default_includes=True)
        assert result["verified"], \
            f"Updating existing local key should not trigger schema panic:\n{result['stderr']}"

    def test_local_get_ex_non_opted_in_returns_zero(self, opcodes):
        """app_local_get_ex returns (0, 0) for non-opted-in account."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);
    Txn txn;
    __CPROVER_array_set(txn.Sender, 0x42);
    // Do NOT opt in

    uint8_t key[] = {'k'};
    pushint(s, 0);   // acct = sender
    pushint(s, 1);   // app_id
    stack_push(s, sv_bytes(key, 1));
    app_local_get_ex(s, BS, txn, ctx);
    StackValue found = stack_pop(s);
    StackValue val = stack_pop(s);
    __CPROVER_assert(found.value == 0, "not found for non-opted-in");
    __CPROVER_assert(val.value == 0, "zero value for non-opted-in");
    return 0;
}
""")
        assert result["verified"], f"local get_ex non-opted-in failed:\n{result['stderr']}"


# ============================================================================
# Wide Math
# ============================================================================

class TestWideMathOps:
    """Tests for addw and mulw."""

    def test_addw_no_carry(self, opcodes):
        """addw with small values: carry=0."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 100);
    pushint(s, 200);
    addw(s);
    StackValue low = stack_pop(s);
    StackValue high = stack_pop(s);
    __CPROVER_assert(high.value == 0, "no carry");
    __CPROVER_assert(low.value == 300, "100+200=300");
    return 0;
}
""")
        assert result["verified"], f"addw no carry failed:\n{result['stderr']}"

    def test_addw_with_carry(self, opcodes):
        """addw with UINT64_MAX + 1 carries."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, UINT64_MAX);
    pushint(s, 1);
    addw(s);
    StackValue low = stack_pop(s);
    StackValue high = stack_pop(s);
    __CPROVER_assert(high.value == 1, "carry=1");
    __CPROVER_assert(low.value == 0, "low wraps to 0");
    return 0;
}
""")
        assert result["verified"], f"addw with carry failed:\n{result['stderr']}"

    def test_mulw_basic(self, opcodes):
        """mulw: 10*20=200 (low), carry=0."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 10);
    pushint(s, 20);
    mulw(s);
    StackValue low = stack_pop(s);
    StackValue high = stack_pop(s);
    __CPROVER_assert(high.value == 0, "no carry");
    __CPROVER_assert(low.value == 200, "10*20=200");
    return 0;
}
""")
        assert result["verified"], f"mulw basic failed:\n{result['stderr']}"


# ============================================================================
# Bit Operations
# ============================================================================

class TestBitOps:
    """Tests for getbit, setbit, bitlen."""

    def test_getbit_int(self, opcodes):
        """getbit on uint64: bit 0 of 5 (binary 101) is 1."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 5);   // binary 101
    pushint(s, 0);   // bit index 0
    getbit(s);
    __CPROVER_assert(stack_pop(s).value == 1, "bit 0 of 5 is 1");

    pushint(s, 5);
    pushint(s, 1);   // bit index 1
    getbit(s);
    __CPROVER_assert(stack_pop(s).value == 0, "bit 1 of 5 is 0");

    pushint(s, 5);
    pushint(s, 2);   // bit index 2
    getbit(s);
    __CPROVER_assert(stack_pop(s).value == 1, "bit 2 of 5 is 1");
    return 0;
}
""")
        assert result["verified"], f"getbit int failed:\n{result['stderr']}"

    def test_getbit_bytes(self, opcodes):
        """getbit on bytes: bit 0 of [0x80] is 1 (MSB first)."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t data[] = {0x80};  // 10000000
    stack_push(s, sv_bytes(data, 1));
    pushint(s, 0);  // bit 0 = MSB
    getbit(s);
    __CPROVER_assert(stack_pop(s).value == 1, "MSB of 0x80 is 1");

    stack_push(s, sv_bytes(data, 1));
    pushint(s, 7);  // bit 7 = LSB
    getbit(s);
    __CPROVER_assert(stack_pop(s).value == 0, "LSB of 0x80 is 0");
    return 0;
}
""")
        assert result["verified"], f"getbit bytes failed:\n{result['stderr']}"

    def test_setbit_int(self, opcodes):
        """setbit on uint64: set bit 1 of 5 (101) → 7 (111)."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 5);   // target = 5 (binary 101)
    pushint(s, 1);   // bit index 1
    pushint(s, 1);   // set to 1
    setbit(s);
    __CPROVER_assert(stack_pop(s).value == 7, "5 with bit 1 set = 7");
    return 0;
}
""")
        assert result["verified"], f"setbit int failed:\n{result['stderr']}"

    def test_setbit_bytes(self, opcodes):
        """setbit on bytes: set bit 7 of [0x00] → [0x01]."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t data[] = {0x00};
    stack_push(s, sv_bytes(data, 1));
    pushint(s, 7);   // bit 7 = LSB
    pushint(s, 1);   // set to 1
    setbit(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice[0] == 0x01, "LSB set");
    return 0;
}
""")
        assert result["verified"], f"setbit bytes failed:\n{result['stderr']}"

    def test_bitlen_int(self, opcodes):
        """bitlen of 255 = 8."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 255);
    bitlen(s);
    __CPROVER_assert(stack_pop(s).value == 8, "bitlen(255)=8");

    pushint(s, 256);
    bitlen(s);
    __CPROVER_assert(stack_pop(s).value == 9, "bitlen(256)=9");

    pushint(s, 0);
    bitlen(s);
    __CPROVER_assert(stack_pop(s).value == 0, "bitlen(0)=0");
    return 0;
}
""")
        assert result["verified"], f"bitlen int failed:\n{result['stderr']}"

    def test_bitlen_bytes(self, opcodes):
        """bitlen of byte array [0x01, 0x00] = 9."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t data[] = {0x01, 0x00};  // 256 in big-endian
    stack_push(s, sv_bytes(data, 2));
    bitlen(s);
    __CPROVER_assert(stack_pop(s).value == 9, "bitlen([0x01,0x00])=9");
    return 0;
}
""")
        assert result["verified"], f"bitlen bytes failed:\n{result['stderr']}"


# ============================================================================
# Static Scratch
# ============================================================================

class TestStaticScratch:
    """Tests for load and store (static scratch space)."""

    def test_store_load_roundtrip(self, opcodes):
        """store then load at same slot returns stored value."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    pushint(s, 42);
    store(s, ctx, 5);
    load(s, ctx, 5);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r.value == 42, "store/load roundtrip");
    return 0;
}
""")
        assert result["verified"], f"store/load roundtrip failed:\n{result['stderr']}"

    def test_multiple_slots(self, opcodes):
        """store/load from different slots are independent."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    pushint(s, 10);
    store(s, ctx, 0);
    pushint(s, 20);
    store(s, ctx, 1);
    pushint(s, 30);
    store(s, ctx, 2);
    load(s, ctx, 0);
    __CPROVER_assert(stack_pop(s).value == 10, "slot 0");
    load(s, ctx, 1);
    __CPROVER_assert(stack_pop(s).value == 20, "slot 1");
    load(s, ctx, 2);
    __CPROVER_assert(stack_pop(s).value == 30, "slot 2");
    return 0;
}
""")
        assert result["verified"], f"multiple slots failed:\n{result['stderr']}"


class TestAdvancedStubs:
    """Tests for v10+ advanced op stubs: vrf_verify, block, base64_decode, EC ops."""

    def test_vrf_verify_returns_output_and_bool(self, opcodes):
        """vrf_verify pushes 64-byte output + bool (AVM spec)."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    // Push 3 args: pk, proof, message
    uint8_t buf[32]; memset(buf, 0, 32);
    stack_push(s, sv_bytes(buf, 32));
    stack_push(s, sv_bytes(buf, 32));
    stack_push(s, sv_bytes(buf, 32));
    vrf_verify(s, 0);
    StackValue ok = stack_pop(s);
    StackValue out = stack_pop(s);
    __CPROVER_assert(!ok._is_bytes, "ok is int");
    __CPROVER_assert(out._is_bytes, "output is bytes");
    __CPROVER_assert(out.byteslice_len == 64, "output is 64 bytes");
    return 0;
}
""")
        assert result["verified"], f"vrf_verify failed:\n{result['stderr']}"

    def test_block_timestamp_returns_int(self, opcodes):
        """block BlkTimestamp pushes uint64."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 100);  // round number
    block_field(s, BlkTimestamp);
    StackValue r = stack_pop(s);
    __CPROVER_assert(!r._is_bytes, "timestamp is int");
    return 0;
}
""")
        assert result["verified"], f"block timestamp failed:\n{result['stderr']}"

    def test_block_seed_returns_bytes(self, opcodes):
        """block BlkSeed pushes 32-byte hash."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 100);
    block_field(s, BlkSeed);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "seed is bytes");
    __CPROVER_assert(r.byteslice_len == 32, "seed is 32 bytes");
    return 0;
}
""")
        assert result["verified"], f"block seed failed:\n{result['stderr']}"

    def test_base64_decode_returns_bytes(self, opcodes):
        """base64_decode pushes nondeterministic bytes."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t encoded[] = "SGVsbG8=";
    stack_push(s, sv_bytes(encoded, 8));
    base64_decode(s, 0);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "decoded is bytes");
    return 0;
}
""")
        assert result["verified"], f"base64_decode failed:\n{result['stderr']}"

    def test_ec_subgroup_check_returns_bool(self, opcodes):
        """ec_subgroup_check pushes bool."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t point[64]; memset(point, 0, 64);
    stack_push(s, sv_bytes(point, 64));
    ec_subgroup_check(s, BN254g1);
    StackValue r = stack_pop(s);
    __CPROVER_assert(!r._is_bytes, "result is int");
    __CPROVER_assert(r.value == 0 || r.value == 1, "result is bool");
    return 0;
}
""")
        assert result["verified"], f"ec_subgroup_check failed:\n{result['stderr']}"

    def test_ec_add_returns_bytes(self, opcodes):
        """ec_add pops 2 byte values and pushes 64-byte result."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t a[64]; memset(a, 0, 64);
    uint8_t b[64]; memset(b, 0, 64);
    stack_push(s, sv_bytes(a, 64));
    stack_push(s, sv_bytes(b, 64));
    ec_add(s, BN254g1);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "result is bytes");
    __CPROVER_assert(r.byteslice_len == 64, "result is 64 bytes");
    __CPROVER_assert(s.currentSize == 0, "stack empty");
    return 0;
}
""")
        assert result["verified"], f"ec_add failed:\n{result['stderr']}"

    def test_ec_scalar_mul_returns_bytes(self, opcodes):
        """ec_scalar_mul pops 2 byte values and pushes 64-byte result."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t point[64]; memset(point, 0, 64);
    uint8_t scalar[32]; memset(scalar, 0, 32);
    stack_push(s, sv_bytes(point, 64));
    stack_push(s, sv_bytes(scalar, 32));
    ec_scalar_mul(s, BN254g1);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "result is bytes");
    __CPROVER_assert(r.byteslice_len == 64, "result is 64 bytes");
    __CPROVER_assert(s.currentSize == 0, "stack empty");
    return 0;
}
""")
        assert result["verified"], f"ec_scalar_mul failed:\n{result['stderr']}"

    def test_ec_multi_scalar_mul_returns_bytes(self, opcodes):
        """ec_multi_scalar_mul pops 2 byte values and pushes 64-byte result."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t points[64]; memset(points, 0, 64);
    uint8_t scalars[32]; memset(scalars, 0, 32);
    stack_push(s, sv_bytes(points, 64));
    stack_push(s, sv_bytes(scalars, 32));
    ec_multi_scalar_mul(s, BN254g1);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "result is bytes");
    __CPROVER_assert(r.byteslice_len == 64, "result is 64 bytes");
    __CPROVER_assert(s.currentSize == 0, "stack empty");
    return 0;
}
""")
        assert result["verified"], f"ec_multi_scalar_mul failed:\n{result['stderr']}"

    def test_ec_map_to_returns_bytes(self, opcodes):
        """ec_map_to pops 1 byte value and pushes 64-byte result."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t input[32]; memset(input, 0, 32);
    stack_push(s, sv_bytes(input, 32));
    ec_map_to(s, BN254g1);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "result is bytes");
    __CPROVER_assert(r.byteslice_len == 64, "result is 64 bytes");
    __CPROVER_assert(s.currentSize == 0, "stack empty");
    return 0;
}
""")
        assert result["verified"], f"ec_map_to failed:\n{result['stderr']}"

    def test_ec_pairing_check_returns_bool(self, opcodes):
        """ec_pairing_check pops 2 byte values and pushes bool."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t a[64]; memset(a, 0, 64);
    uint8_t b[64]; memset(b, 0, 64);
    stack_push(s, sv_bytes(a, 64));
    stack_push(s, sv_bytes(b, 64));
    ec_pairing_check(s, BN254g1);
    StackValue r = stack_pop(s);
    __CPROVER_assert(!r._is_bytes, "result is int");
    __CPROVER_assert(r.value == 0 || r.value == 1, "result is bool");
    __CPROVER_assert(s.currentSize == 0, "stack empty");
    return 0;
}
""")
        assert result["verified"], f"ec_pairing_check failed:\n{result['stderr']}"

    def test_sha512_256_produces_32_bytes(self, opcodes):
        """sha512_256 returns a 32-byte bytes value."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t input[] = {0x01, 0x02, 0x03};
    stack_push(s, sv_bytes(input, 3));
    sha512_256(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice_len == 32, "32 bytes");
    __CPROVER_assert(s.currentSize == 0, "stack empty");
    return 0;
}
""")
        assert result["verified"], f"sha512_256 failed:\n{result['stderr']}"

    def test_ecdsa_pk_decompress_returns_two_values(self, opcodes):
        """ecdsa_pk_decompress pops 1, pushes 2 symbolic 32-byte values."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t compressed[33]; memset(compressed, 0, 33);
    stack_push(s, sv_bytes(compressed, 33));
    ecdsa_pk_decompress(s);
    StackValue y = stack_pop(s);
    StackValue x = stack_pop(s);
    __CPROVER_assert(x._is_bytes, "X is bytes");
    __CPROVER_assert(x.byteslice_len == 32, "X len 32");
    __CPROVER_assert(y._is_bytes, "Y is bytes");
    __CPROVER_assert(y.byteslice_len == 32, "Y len 32");
    __CPROVER_assert(s.currentSize == 0, "stack empty");
    return 0;
}
""")
        assert result["verified"], f"ecdsa_pk_decompress failed:\n{result['stderr']}"

    def test_json_ref_uint64_returns_int(self, opcodes):
        """json_ref JSONUint64 pops 2 bytes, pushes uint64."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t json[16]; memset(json, 0x41, 16);
    uint8_t key[3]; memset(key, 0x42, 3);
    stack_push(s, sv_bytes(json, 16));
    stack_push(s, sv_bytes(key, 3));
    json_ref(s, JSONUint64);
    StackValue r = stack_pop(s);
    __CPROVER_assert(!r._is_bytes, "result is int");
    __CPROVER_assert(s.currentSize == 0, "stack empty");
    return 0;
}
""")
        assert result["verified"], f"json_ref uint64 failed:\n{result['stderr']}"

    def test_json_ref_string_returns_bytes(self, opcodes):
        """json_ref JSONString pops 2 bytes, pushes bytes."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t json[16]; memset(json, 0x41, 16);
    uint8_t key[3]; memset(key, 0x42, 3);
    stack_push(s, sv_bytes(json, 16));
    stack_push(s, sv_bytes(key, 3));
    json_ref(s, JSONString);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "result is bytes");
    __CPROVER_assert(s.currentSize == 0, "stack empty");
    return 0;
}
""")
        assert result["verified"], f"json_ref string failed:\n{result['stderr']}"

    def test_json_ref_object_returns_bytes(self, opcodes):
        """json_ref JSONObject pops 2 bytes, pushes bytes."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t json[16]; memset(json, 0x41, 16);
    uint8_t key[3]; memset(key, 0x42, 3);
    stack_push(s, sv_bytes(json, 16));
    stack_push(s, sv_bytes(key, 3));
    json_ref(s, JSONObject);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "result is bytes");
    __CPROVER_assert(s.currentSize == 0, "stack empty");
    return 0;
}
""")
        assert result["verified"], f"json_ref object failed:\n{result['stderr']}"


class TestGroupScratch:
    """Tests for group scratch and group app ID opcodes."""

    def test_gload_returns_value(self, opcodes):
        """gload pushes a nondeterministic uint64."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    gload_op(s, 0, 5);  // txn 0, slot 5
    StackValue r = stack_pop(s);
    __CPROVER_assert(!r._is_bytes, "gload returns int");
    return 0;
}
""")
        assert result["verified"], f"gload failed:\n{result['stderr']}"

    def test_gloads_returns_value(self, opcodes):
        """gloads pops txn index and pushes a nondeterministic uint64."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 1);  // txn index
    gloads_op(s, 3);  // slot 3
    StackValue r = stack_pop(s);
    __CPROVER_assert(!r._is_bytes, "gloads returns int");
    return 0;
}
""")
        assert result["verified"], f"gloads failed:\n{result['stderr']}"

    def test_gaid_returns_value(self, opcodes):
        """gaid pushes a nondeterministic uint64 (app ID)."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    gaid_op(s, 0);
    StackValue r = stack_pop(s);
    __CPROVER_assert(!r._is_bytes, "gaid returns int");
    return 0;
}
""")
        assert result["verified"], f"gaid failed:\n{result['stderr']}"

    def test_gaids_returns_value(self, opcodes):
        """gaids pops txn index and pushes nondeterministic uint64."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    pushint(s, 2);  // txn index
    gaids_op(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(!r._is_bytes, "gaids returns int");
    return 0;
}
""")
        assert result["verified"], f"gaids failed:\n{result['stderr']}"


# ============================================================================
# Stub Operations
# ============================================================================

class TestStubOps:
    """Tests for stub opcodes: acct_params_get, asset_holding_get, app_params_get."""

    def test_acct_params_get(self, opcodes):
        """acct_params_get returns value + found flag (nondeterministic fallback)."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    BlockchainState BS; bs_init(BS);
    EvalContext ctx; ctx_init(ctx);
    Txn txn; memset(&txn, 0, sizeof(Txn));
    pushint(s, 0);  // account index
    acct_params_get(s, BS, txn, ctx, AcctBalance);
    StackValue found = stack_pop(s);
    StackValue val = stack_pop(s);
    __CPROVER_assert(!found._is_bytes, "found is int");
    __CPROVER_assert(!val._is_bytes, "val is int");
    return 0;
}
""")
        assert result["verified"], f"acct_params_get failed:\n{result['stderr']}"

    def test_acct_params_get_stateful(self, opcodes):
        """acct_params_get uses AccountsState when account is modeled."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    BlockchainState BS; bs_init(BS);
    EvalContext ctx; ctx_init(ctx);
    // Add an account with known balance
    uint8_t addr[32]; memset(addr, 0x42, 32);
    BS.accounts.entries[0].active = true;
    memcpy(BS.accounts.entries[0].address, addr, 32);
    BS.accounts.entries[0].balance = 5000000;
    BS.accounts.entries[0].min_balance = 100000;
    BS.accounts.count = 1;
    Txn txn; memset(&txn, 0, sizeof(Txn));
    // Query AcctBalance for that address
    stack_push(s, sv_bytes(addr, 32));
    acct_params_get(s, BS, txn, ctx, AcctBalance);
    StackValue found = stack_pop(s);
    StackValue val = stack_pop(s);
    __CPROVER_assert(found.value == 1, "found=1");
    __CPROVER_assert(val.value == 5000000, "balance=5000000");
    // Query AcctMinBalance
    stack_push(s, sv_bytes(addr, 32));
    acct_params_get(s, BS, txn, ctx, AcctMinBalance);
    found = stack_pop(s);
    val = stack_pop(s);
    __CPROVER_assert(found.value == 1, "found=1");
    __CPROVER_assert(val.value == 100000, "min_balance=100000");
    return 0;
}
""")
        assert result["verified"], f"acct_params_get stateful failed:\n{result['stderr']}"

    def test_asset_holding_get(self, opcodes):
        """asset_holding_get returns value + found flag."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    BlockchainState BS; bs_init(BS);
    Txn txn; memset(&txn, 0, sizeof(txn));
    EvalContext ctx; ctx_init(ctx);
    pushint(s, 0);      // account
    pushint(s, 12345);  // asset id
    asset_holding_get(s, BS, txn, ctx, 0);
    StackValue found = stack_pop(s);
    StackValue val = stack_pop(s);
    __CPROVER_assert(!found._is_bytes, "found is int");
    __CPROVER_assert(found.value == 0 || found.value == 1, "found is 0 or 1");
    __CPROVER_assert(!val._is_bytes, "val is int");
    return 0;
}
""")
        assert result["verified"], f"asset_holding_get failed:\n{result['stderr']}"

    def test_app_params_get(self, opcodes):
        """app_params_get returns value + nondeterministic found flag."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    BlockchainState BS; bs_init(BS);
    EvalContext ctx; ctx_init(ctx);
    pushint(s, 1);  // app id
    app_params_get(s, BS, ctx, AppGlobalNumUint_field);
    StackValue found = stack_pop(s);
    StackValue val = stack_pop(s);
    __CPROVER_assert(!found._is_bytes, "found is int");
    __CPROVER_assert(found.value == 0 || found.value == 1, "found is bool");
    __CPROVER_assert(!val._is_bytes, "val is int");
    return 0;
}
""")
        assert result["verified"], f"app_params_get failed:\n{result['stderr']}"

    def test_app_params_get_nondet_found(self, opcodes):
        """app_params_get found flag is not always 1 (can be 0)."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    BlockchainState BS; bs_init(BS);
    EvalContext ctx; ctx_init(ctx);
    pushint(s, 99);  // unknown app id
    app_params_get(s, BS, ctx, AppGlobalNumUint_field);
    StackValue found = stack_pop(s);
    // This should FAIL — found is nondeterministic, not always 1
    __CPROVER_assert(found.value == 1, "found always 1");
    return 0;
}
""")
        assert not result["verified"], "found flag should be nondeterministic, not always 1"

    def test_app_params_get_creator_current_app(self, opcodes):
        """app_params_get AppCreator returns ctx.CreatorAddress for current app."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    BlockchainState BS; bs_init(BS);
    EvalContext ctx; ctx_init(ctx);
    ctx.CurrentApplicationID = 42;
    uint8_t creator[32];
    memset(creator, 0xAB, 32);
    memcpy(ctx.CreatorAddress, creator, 32);
    pushint(s, 42);  // current app id
    app_params_get(s, BS, ctx, AppCreator_field);
    StackValue found = stack_pop(s);
    StackValue val = stack_pop(s);
    __CPROVER_assert(val._is_bytes, "creator is bytes");
    __CPROVER_assert(val.byteslice_len == 32, "creator is 32 bytes");
    __CPROVER_assert(val.byteslice[0] == 0xAB, "creator byte 0 matches");
    __CPROVER_assert(val.byteslice[31] == 0xAB, "creator byte 31 matches");
    return 0;
}
""")
        assert result["verified"], f"app_params_get creator current app failed:\n{result['stderr']}"


# ============================================================================
# Remaining Txn Array Field Access
# ============================================================================

class TestTxnArrayImmediate:
    """Tests for immediate-index txn array access: gtxna_field, gitxna_field,
    itxna_field_read, ed25519verify_bare."""

    def test_gtxna_field_app_args(self, opcodes):
        """gtxna_field reads array element from grouped txn by immediate indices."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    TxnGroup tg; tg_init(tg);
    tg.size = 2;

    // Set up txn 0 with 2 app args
    tg.txns[0].AppArgs[0][0] = 0xAA;
    tg.txns[0].AppArgLens[0] = 1;
    tg.txns[0].AppArgs[1][0] = 0xBB;
    tg.txns[0].AppArgLens[1] = 1;
    tg.txns[0].NumAppArgs = 2;

    // Set up txn 1 with 1 app arg
    tg.txns[1].AppArgs[0][0] = 0xCC;
    tg.txns[1].AppArgLens[0] = 1;
    tg.txns[1].NumAppArgs = 1;

    // gtxna 0 ApplicationArgs 1
    gtxna_field(s, tg, 0, ApplicationArgs, 1);
    StackValue r0 = stack_pop(s);
    __CPROVER_assert(r0._is_bytes, "is bytes");
    __CPROVER_assert(r0.byteslice[0] == 0xBB, "txn0 arg1");

    // gtxna 1 ApplicationArgs 0
    gtxna_field(s, tg, 1, ApplicationArgs, 0);
    StackValue r1 = stack_pop(s);
    __CPROVER_assert(r1.byteslice[0] == 0xCC, "txn1 arg0");
    return 0;
}
""")
        assert result["verified"], f"gtxna_field failed:\n{result['stderr']}"

    def test_gitxna_field_inner_txn_args(self, opcodes):
        """gitxna_field reads array element from inner txn by group index."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);

    // Submit inner txn 0 with app args
    itxn_begin(s, ctx);
    uint8_t arg0[] = {0x11, 0x22};
    stack_push(s, sv_bytes(arg0, 2));
    itxn_field_set(s, ctx, ApplicationArgs);
    uint8_t arg1[] = {0x33};
    stack_push(s, sv_bytes(arg1, 1));
    itxn_field_set(s, ctx, ApplicationArgs);
    itxn_submit(BS, ctx);

    // Submit inner txn 1 with app args
    itxn_begin(s, ctx);
    uint8_t arg2[] = {0x44, 0x55, 0x66};
    stack_push(s, sv_bytes(arg2, 3));
    itxn_field_set(s, ctx, ApplicationArgs);
    itxn_submit(BS, ctx);

    // gitxna 0 ApplicationArgs 1 — second arg of first inner txn
    gitxna_field(s, ctx, 0, ApplicationArgs, 1);
    StackValue r0 = stack_pop(s);
    __CPROVER_assert(r0._is_bytes, "is bytes");
    __CPROVER_assert(r0.byteslice[0] == 0x33, "inner txn 0 arg 1");

    // gitxna 1 ApplicationArgs 0 — first arg of second inner txn
    gitxna_field(s, ctx, 1, ApplicationArgs, 0);
    StackValue r1 = stack_pop(s);
    __CPROVER_assert(r1.byteslice_len == 3, "inner txn 1 arg 0 len");
    __CPROVER_assert(r1.byteslice[0] == 0x44, "inner txn 1 arg 0 byte 0");
    return 0;
}
""")
        assert result["verified"], f"gitxna_field failed:\n{result['stderr']}"

    def test_itxna_field_read_last_inner(self, opcodes):
        """itxna_field_read reads array element from last submitted inner txn."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    EvalContext ctx; ctx_init(ctx);
    BlockchainState BS; bs_init(BS);

    // Submit inner txn with two app args
    itxn_begin(s, ctx);
    uint8_t a0[] = {0xDE, 0xAD};
    stack_push(s, sv_bytes(a0, 2));
    itxn_field_set(s, ctx, ApplicationArgs);
    uint8_t a1[] = {0xBE, 0xEF};
    stack_push(s, sv_bytes(a1, 2));
    itxn_field_set(s, ctx, ApplicationArgs);
    itxn_submit(BS, ctx);

    // itxna ApplicationArgs 0
    itxna_field_read(s, ctx, ApplicationArgs, 0);
    StackValue r0 = stack_pop(s);
    __CPROVER_assert(r0._is_bytes, "is bytes");
    __CPROVER_assert(r0.byteslice[0] == 0xDE, "arg 0 byte 0");
    __CPROVER_assert(r0.byteslice[1] == 0xAD, "arg 0 byte 1");

    // itxna ApplicationArgs 1
    itxna_field_read(s, ctx, ApplicationArgs, 1);
    StackValue r1 = stack_pop(s);
    __CPROVER_assert(r1.byteslice[0] == 0xBE, "arg 1 byte 0");
    __CPROVER_assert(r1.byteslice[1] == 0xEF, "arg 1 byte 1");
    return 0;
}
""")
        assert result["verified"], f"itxna_field_read failed:\n{result['stderr']}"

    def test_ed25519verify_bare_returns_bool(self, opcodes):
        """ed25519verify_bare result is 0 or 1 (alias for ed25519verify)."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t data[] = {0x01};
    uint8_t sig[64]; memset(sig, 0, 64);
    uint8_t key[32]; memset(key, 0, 32);
    stack_push(s, sv_bytes(data, 1));
    stack_push(s, sv_bytes(sig, 64));
    stack_push(s, sv_bytes(key, 32));
    ed25519verify_bare(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes == false, "is int");
    __CPROVER_assert(r.value == 0 || r.value == 1, "0 or 1");
    return 0;
}
""")
        assert result["verified"], f"ed25519verify_bare failed:\n{result['stderr']}"


# ============================================================================
# Wormhole Compatibility: New Txn Fields + ECDSA
# ============================================================================

class TestWormholeCompat:
    """Tests for new txn fields and ECDSA stubs added for Wormhole contracts."""

    def test_txn_note_field(self, opcodes):
        """Txn Note field pushes correct variable-length bytes."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    Txn txn;
    memset(&txn, 0, sizeof(Txn));
    uint8_t note[] = {0x48, 0x65, 0x6C, 0x6C, 0x6F};
    memcpy(txn.Note, note, 5);
    txn.NoteLen = 5;
    txn_field(s, txn, Note);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice_len == 5, "len 5");
    __CPROVER_assert(r.byteslice[0] == 0x48, "byte 0");
    __CPROVER_assert(r.byteslice[4] == 0x6F, "byte 4");
    return 0;
}
""")
        assert result["verified"], f"txn Note failed:\n{result['stderr']}"

    def test_txn_rekey_to_field(self, opcodes):
        """Txn RekeyTo field pushes 32-byte address."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    Txn txn;
    memset(&txn, 0, sizeof(Txn));
    txn.RekeyTo[0] = 0xAA;
    txn.RekeyTo[31] = 0xBB;
    txn_field(s, txn, RekeyTo);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice_len == 32, "len 32");
    __CPROVER_assert(r.byteslice[0] == 0xAA, "byte 0");
    __CPROVER_assert(r.byteslice[31] == 0xBB, "byte 31");
    return 0;
}
""")
        assert result["verified"], f"txn RekeyTo failed:\n{result['stderr']}"

    def test_txn_close_remainder_to_field(self, opcodes):
        """Txn CloseRemainderTo field pushes 32-byte address."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    Txn txn;
    memset(&txn, 0, sizeof(Txn));
    txn.CloseRemainderTo[0] = 0xCC;
    txn_field(s, txn, CloseRemainderTo);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice_len == 32, "len 32");
    __CPROVER_assert(r.byteslice[0] == 0xCC, "byte 0");
    return 0;
}
""")
        assert result["verified"], f"txn CloseRemainderTo failed:\n{result['stderr']}"

    def test_txn_config_asset_manager_field(self, opcodes):
        """Txn ConfigAssetManager field pushes 32-byte address."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    Txn txn;
    memset(&txn, 0, sizeof(Txn));
    txn.ConfigAssetManager[0] = 0xDD;
    txn.ConfigAssetManager[31] = 0xEE;
    txn_field(s, txn, ConfigAssetManager);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice_len == 32, "len 32");
    __CPROVER_assert(r.byteslice[0] == 0xDD, "byte 0");
    __CPROVER_assert(r.byteslice[31] == 0xEE, "byte 31");
    return 0;
}
""")
        assert result["verified"], f"txn ConfigAssetManager failed:\n{result['stderr']}"

    def test_ecdsa_pk_recover_returns_two_values(self, opcodes):
        """ecdsa_pk_recover pops 4, pushes 2 symbolic 32-byte values."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t data[32]; memset(data, 0, 32);
    uint8_t r_val[32]; memset(r_val, 0x11, 32);
    uint8_t s_val[32]; memset(s_val, 0x22, 32);
    stack_push(s, sv_bytes(data, 32));
    pushint(s, 0);  // recovery_id
    stack_push(s, sv_bytes(r_val, 32));
    stack_push(s, sv_bytes(s_val, 32));
    ecdsa_pk_recover(s);
    StackValue y = stack_pop(s);
    StackValue x = stack_pop(s);
    __CPROVER_assert(x._is_bytes, "X is bytes");
    __CPROVER_assert(x.byteslice_len == 32, "X len 32");
    __CPROVER_assert(y._is_bytes, "Y is bytes");
    __CPROVER_assert(y.byteslice_len == 32, "Y len 32");
    __CPROVER_assert(s.currentSize == 0, "stack empty");
    return 0;
}
""")
        assert result["verified"], f"ecdsa_pk_recover failed:\n{result['stderr']}"

    def test_ecdsa_verify_returns_bool(self, opcodes):
        """ecdsa_verify pops 5, pushes 1 bool (0 or 1)."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t buf[32]; memset(buf, 0, 32);
    stack_push(s, sv_bytes(buf, 32));  // data
    stack_push(s, sv_bytes(buf, 32));  // r
    stack_push(s, sv_bytes(buf, 32));  // s
    stack_push(s, sv_bytes(buf, 32));  // pk_x
    stack_push(s, sv_bytes(buf, 32));  // pk_y
    ecdsa_verify(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(!r._is_bytes, "is int");
    __CPROVER_assert(r.value == 0 || r.value == 1, "0 or 1");
    __CPROVER_assert(s.currentSize == 0, "stack empty");
    return 0;
}
""")
        assert result["verified"], f"ecdsa_verify failed:\n{result['stderr']}"

    def test_setbyte_alias(self, opcodes):
        """setbyte(s) alias calls setbyte_op correctly."""
        result = opcodes.verify_cpp("""
int main() {
    Stack s; stack_init(s);
    uint8_t data[] = {0x00, 0x00, 0x00};
    stack_push(s, sv_bytes(data, 3));
    pushint(s, 1);    // index
    pushint(s, 0xFF); // new value
    setbyte(s);
    StackValue r = stack_pop(s);
    __CPROVER_assert(r._is_bytes, "is bytes");
    __CPROVER_assert(r.byteslice[0] == 0x00, "byte 0 unchanged");
    __CPROVER_assert(r.byteslice[1] == 0xFF, "byte 1 set");
    __CPROVER_assert(r.byteslice[2] == 0x00, "byte 2 unchanged");
    return 0;
}
""")
        assert result["verified"], f"setbyte alias failed:\n{result['stderr']}"
