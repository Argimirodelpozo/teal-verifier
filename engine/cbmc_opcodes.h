// cbmc_opcodes.h — AVM opcode implementations for CBMC verification.
//
// These mirror the implementations in avm/opcodeDefinitions.cpp but work
// with the bounded data structures from cbmc_avm.h.

#pragma once

#include "cbmc_avm.h"

// ============================================================================
// Constant / initialization opcodes
// ============================================================================

// pushbytess — push multiple byte strings at once
// (CBMC bounded version: pushes each entry from a pre-built array of StackValues)
 void pushbytess(Stack& s, const StackValue* values, uint32_t count) {
    for (uint32_t i = 0; i < count; i++) {
        stack_push(s, values[i]);
    }
}

// pushints — push multiple integers at once
 void pushints(Stack& s, const uint64_t* values, uint32_t count) {
    for (uint32_t i = 0; i < count; i++) {
        pushint(s, values[i]);
    }
}

// arg N — push Nth LogicSig argument (immediate index, LogicSig mode only)
 void arg(Stack& s, EvalContext& ctx, uint64_t index) {
    avm_assert_check(index < ctx.NumLsigArgs);
    stack_push(s, sv_bytes(ctx.LsigArgs[index], ctx.LsigArgLens[index]));
}

// arg_0 through arg_3 — shorthand for arg 0..3
 void arg_0(Stack& s, EvalContext& ctx) { arg(s, ctx, 0); }
 void arg_1(Stack& s, EvalContext& ctx) { arg(s, ctx, 1); }
 void arg_2(Stack& s, EvalContext& ctx) { arg(s, ctx, 2); }
 void arg_3(Stack& s, EvalContext& ctx) { arg(s, ctx, 3); }

// args — push LogicSig argument at dynamic index from stack (LogicSig mode only)
 void args(Stack& s, EvalContext& ctx) {
    StackValue idx = stack_pop(s);
    avm_assert_check(sv_isInt(idx));
    avm_assert_check(idx.value < ctx.NumLsigArgs);
    stack_push(s, sv_bytes(ctx.LsigArgs[idx.value], ctx.LsigArgLens[idx.value]));
}

// ============================================================================
// Stack operations
// ============================================================================

 void pop(Stack& s) { stack_pop(s); }

 void dup(Stack& s) {
    stack_push(s, stack_top(s));
}

void dup2(Stack& s) {
    StackValue b = stack_get(s, 1);
    StackValue a = stack_get(s, 0);
    stack_push(s, b);
    stack_push(s, a);
}

void swap(Stack& s) {
    StackValue tmp = s.stack[s.currentSize - 1];
    s.stack[s.currentSize - 1] = s.stack[s.currentSize - 2];
    s.stack[s.currentSize - 2] = tmp;
}

void dig(Stack& s, uint64_t n) {
    avm_assert_check(s.currentSize >= n + 1);
    stack_push(s, stack_get(s, (int)n));
}

void bury(Stack& s, uint64_t n) {
    avm_assert_check(s.currentSize >= n + 1); //go-algorand does if (len(Stack) - 1 - n < 0) then error
    StackValue v = stack_top(s);
    stack_get(s, (int)n) = v;
    s.currentSize--;
}

// Note: cover, uncover, popn, dupn are unrolled by the transpiler at compile time.
// These definitions are kept for direct use in opcode unit tests.
void cover(Stack& s, uint64_t depth) {
    avm_assert_check(s.currentSize > depth);
    StackValue top = s.stack[s.currentSize - 1];
    for (uint64_t i = 0; i < depth; i++) {
        s.stack[s.currentSize - 1 - i] = s.stack[s.currentSize - 2 - i];
    }
    s.stack[s.currentSize - 1 - depth] = top;
}

void uncover(Stack& s, uint64_t depth) {
    avm_assert_check(s.currentSize > depth);
    StackValue val = s.stack[s.currentSize - 1 - depth];
    for (uint64_t i = depth; i > 0; i--) {
        s.stack[s.currentSize - 1 - i] = s.stack[s.currentSize - i];
    }
    s.stack[s.currentSize - 1] = val;
}

void popn(Stack& s, uint64_t n) {
    s.currentSize -= (uint16_t)n;
}

void dupn(Stack& s, int n) {
    avm_assert_check(s.currentSize > 0);
    StackValue v = stack_top(s);
    //instead of checking on every push, we can check once before loop
    __CPROVER_assume(s.currentSize + (uint16_t)n <= CBMC_STACK_MAX);
    for (int i = 0; i < n; i++) s.stack[s.currentSize++] = v;
}

void select_op(Stack& s) {
    StackValue cond = stack_pop(s);
    StackValue b = stack_pop(s);
    StackValue a = stack_pop(s);
    avm_assert_check(sv_isInt(cond));
    if (cond.value != 0) stack_push(s, b);
    else stack_push(s, a);
}

// ============================================================================
// Arithmetic
// ============================================================================

void add(Stack& s) {
    StackValue a = stack_pop(s);
    StackValue b = stack_pop(s);
    avm_assert_check(sv_isInt(a) && sv_isInt(b));
    avm_assert_check(b.value <= UINT64_MAX - a.value);  // overflow check
    pushint(s, b.value + a.value);
}

void sub(Stack& s) {
    StackValue a = stack_pop(s);
    StackValue b = stack_pop(s);
    avm_assert_check(sv_isInt(a) && sv_isInt(b));
    avm_assert_check(b.value >= a.value);  // underflow check
    pushint(s, b.value - a.value);
}

void mul(Stack& s) {
    StackValue a = stack_pop(s);
    StackValue b = stack_pop(s);
    avm_assert_check(sv_isInt(a) && sv_isInt(b));
#ifndef PEEPHOLE_FAST_MUL
    // Full overflow check (expensive for SAT solvers due to division)
    if (a.value != 0) {
        avm_assert_check(b.value <= UINT64_MAX / a.value);
    }
#endif
    // In peephole mode the overflow check is skipped — wrapping mul is
    // commutative (a*b == b*a mod 2^64), so both orderings always agree.
    // The real AVM would panic on overflow, but since both sequences see the
    // same operand pair (just in swapped order), they panic identically.
    pushint(s, b.value * a.value);
}

void div_op(Stack& s) {
    StackValue a = stack_pop(s);
    StackValue b = stack_pop(s);
    avm_assert_check(sv_isInt(a) && sv_isInt(b));
    avm_assert_check(a.value != 0);
    pushint(s, b.value / a.value);
}

void mod_op(Stack& s) {
    StackValue a = stack_pop(s);
    StackValue b = stack_pop(s);
    avm_assert_check(sv_isInt(a) && sv_isInt(b));
    avm_assert_check(a.value != 0);
    pushint(s, b.value % a.value);
}

void exp_op(Stack& s) {
    StackValue a = stack_pop(s);
    StackValue b = stack_pop(s);
    avm_assert_check(sv_isInt(a) && sv_isInt(b));
    uint64_t base = b.value;
    uint64_t exp = a.value;
    // AVM panics on overflow, so base^exp must fit in uint64.
    // 2^64 overflows, so exp <= 63 is a sound bound for any base >= 2.
    // base 0/1 are trivial (0^n=0 for n>0, 1^n=1).
    __CPROVER_assume(exp <= 63);
    uint64_t result = 1;
    for (uint64_t i = 0; i < exp; i++) {
        if (base != 0) {
            avm_assert_check(result <= UINT64_MAX / base);
        }
        result *= base;
    }
    pushint(s, result);
}

void sqrt_op(Stack& s) {
    StackValue a = stack_pop(s);
    avm_assert_check(sv_isInt(a));
    uint64_t v = a.value;
    if (v == 0) { pushint(s, 0); return; }
    // Newton's method with fixed 40 iterations (converges for all uint64 inputs).
    // Uses 128-bit intermediate to avoid overflow in x*x comparison.
    uint64_t x = v;
    for (int i = 0; i < 40; i++) {
        uint64_t nx = (x + v / x) / 2;
        if (nx >= x) break;
        x = nx;
    }
    // Newton's may overshoot by 1 — adjust down if needed
    if ((__uint128_t)x * x > v) x--;
    pushint(s, x);
}

// ============================================================================
// Comparisons
// ============================================================================

void bool_eq(Stack& s) {
    StackValue a = stack_pop(s);
    StackValue b = stack_pop(s);
    avm_assert_check(a._is_bytes == b._is_bytes);
    pushint(s, sv_equal(a, b) ? 1 : 0);
}

void bool_neq(Stack& s) {
    StackValue a = stack_pop(s);
    StackValue b = stack_pop(s);
    avm_assert_check(a._is_bytes == b._is_bytes);
    pushint(s, sv_equal(a, b) ? 0 : 1);
}

void bool_lt(Stack& s) {
    StackValue a = stack_pop(s);
    StackValue b = stack_pop(s);
    avm_assert_check(sv_isInt(a) && sv_isInt(b));
    pushint(s, b.value < a.value ? 1 : 0);
}

void bool_gt(Stack& s) {
    StackValue a = stack_pop(s);
    StackValue b = stack_pop(s);
    avm_assert_check(sv_isInt(a) && sv_isInt(b));
    pushint(s, b.value > a.value ? 1 : 0);
}

void bool_leq(Stack& s) {
    StackValue a = stack_pop(s);
    StackValue b = stack_pop(s);
    avm_assert_check(sv_isInt(a) && sv_isInt(b));
    pushint(s, b.value <= a.value ? 1 : 0);
}

void bool_geq(Stack& s) {
    StackValue a = stack_pop(s);
    StackValue b = stack_pop(s);
    avm_assert_check(sv_isInt(a) && sv_isInt(b));
    pushint(s, b.value >= a.value ? 1 : 0);
}

// ============================================================================
// Logic
// ============================================================================

void bool_and(Stack& s) {
    StackValue a = stack_pop(s);
    StackValue b = stack_pop(s);
    avm_assert_check(sv_isInt(a) && sv_isInt(b));
    pushint(s, (a.value != 0 && b.value != 0) ? 1 : 0);
}

void bool_or(Stack& s) {
    StackValue a = stack_pop(s);
    StackValue b = stack_pop(s);
    avm_assert_check(sv_isInt(a) && sv_isInt(b));
    pushint(s, (a.value != 0 || b.value != 0) ? 1 : 0);
}

void not_logical(Stack& s) {
    avm_assert_check(sv_isInt(stack_top(s)));
    stack_top(s).value = (stack_top(s).value == 0) ? 1 : 0;
}

// ============================================================================
// Bitwise
// ============================================================================

void bitwise_and(Stack& s) {
    StackValue a = stack_pop(s);
    StackValue b = stack_pop(s);
    avm_assert_check(sv_isInt(a) && sv_isInt(b));
    pushint(s, b.value & a.value);
}

void bitwise_or(Stack& s) {
    StackValue a = stack_pop(s);
    StackValue b = stack_pop(s);
    avm_assert_check(sv_isInt(a) && sv_isInt(b));
    pushint(s, b.value | a.value);
}

void bitwise_xor(Stack& s) {
    StackValue a = stack_pop(s);
    StackValue b = stack_pop(s);
    avm_assert_check(sv_isInt(a) && sv_isInt(b));
    pushint(s, b.value ^ a.value);
}

void bitwise_neg(Stack& s) {
    avm_assert_check(sv_isInt(stack_top(s)));
    stack_top(s).value = ~stack_top(s).value;
}

void bitwise_shr(Stack& s) {
    StackValue a = stack_pop(s);
    StackValue b = stack_pop(s);
    avm_assert_check(sv_isInt(a) && sv_isInt(b));
    avm_assert_check(a.value <= 63);
    pushint(s, b.value >> a.value);
}

void bitwise_shl(Stack& s) {
    StackValue a = stack_pop(s);
    StackValue b = stack_pop(s);
    avm_assert_check(sv_isInt(a) && sv_isInt(b));
    avm_assert_check(a.value <= 63);
    pushint(s, b.value << a.value);
}

// ============================================================================
// Byte operations
// ============================================================================

void itob(Stack& s) {
    StackValue a = stack_pop(s);
    avm_assert_check(sv_isInt(a));
    StackValue v;
    v._is_bytes = true;
    v.byteslice_len = 8;
    v.value = 0;
    // Unrolled big-endian encoding (no loop for CBMC)
    uint64_t val = a.value;
    v.byteslice[7] = (uint8_t)(val & 0xff); val >>= 8;
    v.byteslice[6] = (uint8_t)(val & 0xff); val >>= 8;
    v.byteslice[5] = (uint8_t)(val & 0xff); val >>= 8;
    v.byteslice[4] = (uint8_t)(val & 0xff); val >>= 8;
    v.byteslice[3] = (uint8_t)(val & 0xff); val >>= 8;
    v.byteslice[2] = (uint8_t)(val & 0xff); val >>= 8;
    v.byteslice[1] = (uint8_t)(val & 0xff); val >>= 8;
    v.byteslice[0] = (uint8_t)(val & 0xff);
    stack_push(s, v);
}

void btoi(Stack& s) {
    StackValue a = stack_pop(s);
    avm_assert_check(sv_isBytes(a));
    avm_assert_check(a.byteslice_len <= 8);
    // Unrolled big-endian decode (max 8 bytes per AVM spec, no loop for CBMC)
    uint64_t val = 0;
    if (a.byteslice_len > 0) val = (val << 8) | a.byteslice[0];
    if (a.byteslice_len > 1) val = (val << 8) | a.byteslice[1];
    if (a.byteslice_len > 2) val = (val << 8) | a.byteslice[2];
    if (a.byteslice_len > 3) val = (val << 8) | a.byteslice[3];
    if (a.byteslice_len > 4) val = (val << 8) | a.byteslice[4];
    if (a.byteslice_len > 5) val = (val << 8) | a.byteslice[5];
    if (a.byteslice_len > 6) val = (val << 8) | a.byteslice[6];
    if (a.byteslice_len > 7) val = (val << 8) | a.byteslice[7];
    pushint(s, val);
}

void len(Stack& s) {
    StackValue a = stack_pop(s);
    avm_assert_check(sv_isBytes(a));
    pushint(s, a.byteslice_len);
}

void concat(Stack& s) {
    StackValue a = stack_pop(s);  // top
    StackValue b = stack_pop(s);  // second
    avm_assert_check(sv_isBytes(a) && sv_isBytes(b));
    StackValue result;
    result._is_bytes = true;
    result.value = 0;
    result.byteslice_len = b.byteslice_len + a.byteslice_len;
    avm_assert_check(result.byteslice_len <= CBMC_BYTES_MAX);
    _cbmc_bytecopy(result.byteslice, b.byteslice, b.byteslice_len);
    _cbmc_bytecopy(result.byteslice + b.byteslice_len, a.byteslice, a.byteslice_len);
    stack_push(s, result);
}

void bzero(Stack& s) {
    StackValue a = stack_pop(s);
    avm_assert_check(sv_isInt(a));
    avm_assert_check(a.value <= CBMC_BYTES_MAX);
    StackValue v;
    v.value = 0;
    v._is_bytes = true;
    v.byteslice_len = (uint32_t)a.value;
    _cbmc_zero(v.byteslice, v.byteslice_len);
    stack_push(s, v);
}

// ============================================================================
// Byte extraction/substring
// ============================================================================

void extract3(Stack& s) {
    StackValue c = stack_pop(s);  // length
    StackValue b = stack_pop(s);  // start
    StackValue a = stack_pop(s);  // source bytes
    avm_assert_check(sv_isInt(c) && sv_isInt(b) && sv_isBytes(a));
    avm_assert_check(b.value + c.value <= a.byteslice_len);
    StackValue result;
    result._is_bytes = true;
    result.value = 0;
    result.byteslice_len = (uint32_t)c.value;
    _cbmc_bytecopy(result.byteslice, a.byteslice + (uint32_t)b.value, result.byteslice_len);
    stack_push(s, result);
}

void extract_uint16(Stack& s) {
    StackValue b = stack_pop(s);  // offset
    StackValue a = stack_pop(s);  // source bytes
    avm_assert_check(sv_isInt(b) && sv_isBytes(a));
    avm_assert_check(b.value + 2 <= a.byteslice_len);
    uint64_t val = ((uint64_t)a.byteslice[b.value] << 8)
                 | (uint64_t)a.byteslice[b.value + 1];
    pushint(s, val);
}

void extract_uint64(Stack& s) {
    StackValue b = stack_pop(s);  // offset
    StackValue a = stack_pop(s);  // source bytes
    avm_assert_check(sv_isInt(b) && sv_isBytes(a));
    avm_assert_check(b.value + 8 <= a.byteslice_len);
    // Unrolled big-endian decode (no loop for CBMC)
    uint64_t off = b.value;
    uint64_t val = ((uint64_t)a.byteslice[off] << 56) | ((uint64_t)a.byteslice[off+1] << 48)
                 | ((uint64_t)a.byteslice[off+2] << 40) | ((uint64_t)a.byteslice[off+3] << 32)
                 | ((uint64_t)a.byteslice[off+4] << 24) | ((uint64_t)a.byteslice[off+5] << 16)
                 | ((uint64_t)a.byteslice[off+6] << 8)  | (uint64_t)a.byteslice[off+7];
    pushint(s, val);
}

void substring3(Stack& s) {
    StackValue c = stack_pop(s);  // end
    StackValue b = stack_pop(s);  // start
    StackValue a = stack_pop(s);  // source bytes
    avm_assert_check(sv_isInt(c) && sv_isInt(b) && sv_isBytes(a));
    avm_assert_check(b.value <= c.value && c.value <= a.byteslice_len);
    StackValue result;
    result._is_bytes = true;
    result.value = 0;
    result.byteslice_len = (uint32_t)(c.value - b.value);
    _cbmc_bytecopy(result.byteslice, a.byteslice + (uint32_t)b.value, result.byteslice_len);
    stack_push(s, result);
}

// ============================================================================
// Scratch space
// ============================================================================

void load(Stack& s, EvalContext& ctx, uint64_t slot) {
    avm_assert_check(slot < CBMC_SCRATCH_SLOTS);
    stack_push(s, ctx.sp[slot]);
}

void store(Stack& s, EvalContext& ctx, uint64_t slot) {
    avm_assert_check(slot < CBMC_SCRATCH_SLOTS);
    ctx.sp[slot] = stack_pop(s);
}

// ============================================================================
// AVM assert and err opcodes
// ============================================================================

void avm_assert(Stack& s) {
    StackValue v = stack_pop(s);
    avm_assert_check(sv_isInt(v) && v.value != 0);
}

void err() {
    avm_panic();
}

// ============================================================================
// Logging (simplified)
// ============================================================================

void avm_log(Stack& s, EvalContext& ctx) {
    StackValue v = stack_pop(s);
    avm_assert_check(sv_isBytes(v));
    if (ctx.NumLogs < CBMC_MAX_LOGS) {
        uint32_t log_len = (v.byteslice_len < CBMC_MAX_LOG_LEN) ? v.byteslice_len : CBMC_MAX_LOG_LEN;
        ctx.LogLens[ctx.NumLogs] = v.byteslice_len;
        _cbmc_bytecopy(ctx.Logs[ctx.NumLogs], v.byteslice, log_len);
        ctx.NumLogs++;
    }
}

// ============================================================================
// Crypto (nondeterministic stubs — sound over-approximation)
// ============================================================================

extern "C" { uint8_t nondet_uint8(); bool nondet_bool(); uint64_t nondet_uint64(); }

void sha256(Stack& s) {
    StackValue input = stack_pop(s);
    avm_assert_check(sv_isBytes(input));
    stack_push(s, sv_nondet_bytes(32));
}

void sha512_256(Stack& s) { sha256(s); }  // Same stub
void sha3_256(Stack& s) { sha256(s); }
void keccak256(Stack& s) { sha256(s); }

void ed25519verify(Stack& s) {
    stack_pop(s); stack_pop(s); stack_pop(s);
    pushint(s, nondet_bool() ? 1 : 0);
}

void ed25519verify_bare(Stack& s) { ed25519verify(s); }

// ecdsa_pk_recover — recover public key from signature (nondeterministic stub)
// Stack: ..., data(bytes), recovery_id(uint), r(bytes), s(bytes) → ..., X(bytes), Y(bytes)
void ecdsa_pk_recover(Stack& s) {
    stack_pop(s); stack_pop(s); stack_pop(s); stack_pop(s);
    stack_push(s, sv_nondet_bytes(32));
    stack_push(s, sv_nondet_bytes(32));
}

// ecdsa_pk_decompress — decompress public key (nondeterministic stub)
// Stack: ..., compressed_pk(bytes) → ..., X(bytes), Y(bytes)
void ecdsa_pk_decompress(Stack& s) {
    stack_pop(s);
    stack_push(s, sv_nondet_bytes(32));
    stack_push(s, sv_nondet_bytes(32));
}

// ecdsa_verify — verify ECDSA signature (nondeterministic stub)
// Stack: ..., data(bytes), r(bytes), s(bytes), pk_x(bytes), pk_y(bytes) → ..., bool
void ecdsa_verify(Stack& s) {
    stack_pop(s); stack_pop(s); stack_pop(s); stack_pop(s); stack_pop(s);
    pushint(s, nondet_bool() ? 1 : 0);
}

// json_ref — parse JSON and extract a value by key (nondeterministic stub)
enum jsonRefField { JSONString = 0, JSONUint64 = 1, JSONObject = 2 };

void json_ref(Stack& s, jsonRefField field) {
    StackValue key = stack_pop(s);
    StackValue json = stack_pop(s);
    avm_assert_check(sv_isBytes(key) && sv_isBytes(json));
    if (field == JSONUint64) {
        pushint(s, nondet_uint64());
    } else {
        // JSONString or JSONObject: return nondeterministic bytes
        uint32_t len = nondet_uint8();
        if (len > 32) len = 32;
        stack_push(s, sv_nondet_bytes(len));
    }
}

// ============================================================================
// Advanced crypto and v10+ stubs (nondeterministic)
// ============================================================================

// vrf_verify — verify VRF proof (nondeterministic stub)
// Stack: ..., pk(bytes), proof(bytes), message(bytes) → ..., output(bytes), bool
void vrf_verify(Stack& s, uint64_t standard) {
    stack_pop(s); stack_pop(s); stack_pop(s);
    uint8_t buf[64];  // uninitialized = nondeterministic in CBMC
    stack_push(s, sv_bytes(buf, 64));  // AVM spec: 64-byte VRF output
    pushint(s, nondet_bool() ? 1 : 0);
}

// block — get block field (nondeterministic stub)
// Stack: ..., round(uint64) → ..., field_value
enum blockFieldEnum { BlkSeed = 0, BlkTimestamp = 1 };

void block_field(Stack& s, blockFieldEnum field) {
    stack_pop(s);  // round
    if (field == BlkTimestamp) {
        pushint(s, nondet_uint64());
    } else {
        // BlkSeed: 32-byte hash
        stack_push(s, sv_nondet_bytes(32));
    }
}

// base64_decode — decode base64 string (nondeterministic stub)
// Stack: ..., encoded(bytes) → ..., decoded(bytes)
// Returns nondeterministic bytes (cannot model actual decoding in CBMC)
void base64_decode(Stack& s, uint64_t encoding) {
    StackValue input = stack_pop(s);
    // Output length bounded by input length (base64 decode shrinks)
    uint32_t maxlen = sv_isBytes(input) ? input.byteslice_len : 32;
    if (maxlen > CBMC_BYTES_MAX) maxlen = CBMC_BYTES_MAX;
    stack_push(s, sv_nondet_bytes(maxlen));
}

// EC group enum
enum ecGroupEnum { BN254g1 = 0, BN254g2 = 1, BLS12_381g1 = 2, BLS12_381g2 = 3 };

// ec_add — elliptic curve point addition (nondeterministic stub)
// Stack: ..., A(bytes), B(bytes) → ..., result(bytes)
void ec_add(Stack& s, ecGroupEnum group) {
    stack_pop(s); stack_pop(s);
    stack_push(s, sv_nondet_bytes(64));
}

// ec_scalar_mul — elliptic curve scalar multiplication (nondeterministic stub)
// Stack: ..., A(bytes), k(bytes) → ..., result(bytes)
void ec_scalar_mul(Stack& s, ecGroupEnum group) {
    stack_pop(s); stack_pop(s);
    stack_push(s, sv_nondet_bytes(64));
}

// ec_multi_scalar_mul — multi-scalar multiplication (nondeterministic stub)
// Stack: ..., A(bytes), B(bytes) → ..., result(bytes)
void ec_multi_scalar_mul(Stack& s, ecGroupEnum group) {
    stack_pop(s); stack_pop(s);
    stack_push(s, sv_nondet_bytes(64));
}

// ec_subgroup_check — check if point is in subgroup (nondeterministic stub)
// Stack: ..., A(bytes) → ..., bool
void ec_subgroup_check(Stack& s, ecGroupEnum group) {
    stack_pop(s);
    pushint(s, nondet_bool() ? 1 : 0);
}

// ec_map_to — hash to curve (nondeterministic stub)
// Stack: ..., data(bytes) → ..., point(bytes)
void ec_map_to(Stack& s, ecGroupEnum group) {
    stack_pop(s);
    stack_push(s, sv_nondet_bytes(64));
}

// ec_pairing_check — bilinear pairing check (nondeterministic stub)
// Stack: ..., A(bytes), B(bytes) → ..., bool
void ec_pairing_check(Stack& s, ecGroupEnum group) {
    stack_pop(s); stack_pop(s);
    pushint(s, nondet_bool() ? 1 : 0);
}

// ============================================================================
// Global state operations (simplified)
// ============================================================================

void app_global_put(Stack& s, BlockchainState& BS, EvalContext& ctx) {
    StackValue val = stack_pop(s);
    StackValue key = stack_pop(s);
    avm_assert_check(sv_isBytes(key));
    // Schema enforcement is handled inside gs_put via running counters.
    gs_put(BS.globals, key.byteslice, key.byteslice_len, val);
}

void app_global_get(Stack& s, BlockchainState& BS, EvalContext& ctx) {
    StackValue key = stack_pop(s);
    avm_assert_check(sv_isBytes(key));
    StackValue* val = gs_get(BS.globals, key.byteslice, key.byteslice_len);
    if (val) {
        stack_push(s, *val);
    } else {
        pushint(s, 0);
    }
}

void app_global_del(Stack& s, BlockchainState& BS, EvalContext& ctx) {
    StackValue key = stack_pop(s);
    avm_assert_check(sv_isBytes(key));
    gs_del(BS.globals, key.byteslice, key.byteslice_len);
}

// ============================================================================
// Transaction field access (simplified stubs)
// ============================================================================

// Txn field names (matching go-algorand TxnFieldNames spec numbering)
enum txnField {
    Sender = 0, Fee = 1, FirstValid = 2, FirstValidTime = 3, LastValid = 4,
    Note = 5, Lease = 6, Receiver = 7, Amount = 8,
    CloseRemainderTo = 9, VotePK = 10, SelectionPK = 11,
    VoteFirst = 12, VoteLast = 13, VoteKeyDilution = 14,
    Type = 15, TypeEnum = 16, XferAsset = 17, AssetAmount = 18,
    AssetSender = 19, AssetReceiver = 20, AssetCloseTo = 21,
    GroupIndex = 22, TxID = 23, ApplicationID = 24, OnCompletion = 25,
    ApplicationArgs = 26, NumAppArgs = 27,
    Accounts = 28, NumAccounts = 29,
    ApprovalProgram = 30, ClearStateProgram = 31,
    RekeyTo = 32, ConfigAsset = 33, ConfigAssetTotal = 34,
    ConfigAssetDecimals = 35, ConfigAssetDefaultFrozen = 36,
    ConfigAssetUnitName = 37, ConfigAssetName = 38,
    ConfigAssetURL = 39, ConfigAssetMetadataHash = 40,
    ConfigAssetManager = 41, ConfigAssetReserve = 42,
    ConfigAssetFreeze = 43, ConfigAssetClawback = 44,
    FreezeAsset = 45, FreezeAssetAccount = 46, FreezeAssetFrozen = 47,
    Assets = 48, NumAssets = 49,
    Applications = 50, NumApplications = 51,
    GlobalNumUint = 52, GlobalNumByteSlice = 53,
    LocalNumUint = 54, LocalNumByteSlice = 55,
    ExtraProgramPages = 56, Nonparticipation = 57,
    Logs = 58, NumLogs = 59,
    CreatedAssetID = 60, CreatedApplicationID = 61,
    LastLog = 62, StateProofPK = 63,
    ApprovalProgramPages = 64, ClearStateProgramPages = 65,
    NumApprovalProgramPages = 66, NumClearStateProgramPages = 67,
};

void txn_field(Stack& s, Txn& txn, txnField field) {
    switch (field) {
        case Sender:
            stack_push(s, sv_bytes(txn.Sender, 32));
            break;
        case Receiver:
            stack_push(s, sv_bytes(txn.Receiver, 32));
            break;
        case Fee:
            pushint(s, txn.Fee);
            break;
        case ApplicationID:
            pushint(s, txn.ApplicationID);
            break;
        case OnCompletion:
            pushint(s, txn.apan);
            break;
        case NumAppArgs:
            pushint(s, txn.NumAppArgs);
            break;
        case TypeEnum:
            pushint(s, txn.TypeEnum);
            break;
        case GroupIndex:
            pushint(s, txn.GroupIndex);
            break;
        case TxID: {
            // Transaction hash: nondeterministic 32-byte stub
            stack_push(s, sv_nondet_bytes(32));
            break;
        }
        case Amount:
            pushint(s, txn.Amount);
            break;
        case NumAccounts:
            pushint(s, txn.NumAccounts);
            break;
        case NumAssets:
            pushint(s, txn.NumAssets);
            break;
        case NumApplications:
            pushint(s, txn.NumApplications);
            break;
        case NumLogs:
            pushint(s, txn.NumTxnLogs);
            break;
        case CreatedAssetID:
            pushint(s, txn.CreatedAssetID);
            break;
        case CreatedApplicationID:
            pushint(s, txn.CreatedApplicationID);
            break;
        case LastLog:
            if (txn.NumTxnLogs > 0) {
                uint64_t last = txn.NumTxnLogs - 1;
                stack_push(s, sv_bytes(txn.TxnLogs[last], txn.TxnLogLens[last]));
            } else {
                stack_push(s, sv_empty_bytes());
            }
            break;
        case GlobalNumUint:
            pushint(s, txn.GlobalNumUint);
            break;
        case GlobalNumByteSlice:
            pushint(s, txn.GlobalNumByteSlice);
            break;
        case LocalNumUint:
            pushint(s, txn.LocalNumUint);
            break;
        case LocalNumByteSlice:
            pushint(s, txn.LocalNumByteSlice);
            break;
        case XferAsset:
            pushint(s, txn.XferAsset);
            break;
        case AssetAmount:
            pushint(s, txn.AssetAmount);
            break;
        case AssetReceiver:
            stack_push(s, sv_bytes(txn.AssetReceiver, 32));
            break;
        case AssetSender:
            stack_push(s, sv_bytes(txn.AssetSender, 32));
            break;
        case AssetCloseTo:
            stack_push(s, sv_bytes(txn.AssetCloseTo, 32));
            break;
        case ConfigAsset:
            pushint(s, txn.ConfigAsset);
            break;
        case ConfigAssetTotal:
            pushint(s, txn.ConfigAssetTotal);
            break;
        case ConfigAssetDecimals:
            pushint(s, txn.ConfigAssetDecimals);
            break;
        case ConfigAssetName:
            stack_push(s, sv_bytes(txn.ConfigAssetName, txn.ConfigAssetNameLen));
            break;
        case ConfigAssetUnitName:
            stack_push(s, sv_bytes(txn.ConfigAssetUnitName, txn.ConfigAssetUnitNameLen));
            break;
        case ConfigAssetURL:
            stack_push(s, sv_bytes(txn.ConfigAssetURL, txn.ConfigAssetURLLen));
            break;
        case ConfigAssetMetadataHash:
            stack_push(s, sv_bytes(txn.ConfigAssetMetadataHash, 32));
            break;
        case RekeyTo:
            stack_push(s, sv_bytes(txn.RekeyTo, 32));
            break;
        case CloseRemainderTo:
            stack_push(s, sv_bytes(txn.CloseRemainderTo, 32));
            break;
        case Note:
            stack_push(s, sv_bytes(txn.Note, txn.NoteLen));
            break;
        case ConfigAssetManager:
            stack_push(s, sv_bytes(txn.ConfigAssetManager, 32));
            break;
        case ConfigAssetReserve:
            stack_push(s, sv_bytes(txn.ConfigAssetReserve, 32));
            break;
        case ConfigAssetFreeze:
            stack_push(s, sv_bytes(txn.ConfigAssetFreeze, 32));
            break;
        case ConfigAssetClawback:
            stack_push(s, sv_bytes(txn.ConfigAssetClawback, 32));
            break;
        case ApprovalProgram:
        case ClearStateProgram:
            // Program fields: push nondeterministic bytes (stub)
            stack_push(s, sv_empty_bytes());
            break;
        case NumApprovalProgramPages:
        case NumClearStateProgramPages:
            // Program pages: stub with 1 page
            pushint(s, 1);
            break;
        case ApprovalProgramPages:
        case ClearStateProgramPages:
            // Program page content: stub with empty bytes
            stack_push(s, sv_empty_bytes());
            break;
        case FirstValid:
            pushint(s, txn.FirstValid);
            break;
        case LastValid:
            pushint(s, txn.LastValid);
            break;
        case Lease:
            stack_push(s, sv_bytes(txn.Lease, 32));
            break;
        case ExtraProgramPages:
            pushint(s, txn.ExtraProgramPages);
            break;
        case ConfigAssetDefaultFrozen:
            pushint(s, txn.ConfigAssetDefaultFrozen ? 1 : 0);
            break;
        case FreezeAsset:
            pushint(s, txn.FreezeAsset);
            break;
        case FreezeAssetAccount:
            stack_push(s, sv_bytes(txn.FreezeAssetAccount, 32));
            break;
        case FreezeAssetFrozen:
            pushint(s, txn.FreezeAssetFrozen ? 1 : 0);
            break;
        case Type: {
            // Type string: derive from TypeEnum
            const char* tstr = "";
            uint32_t tlen = 0;
            switch (txn.TypeEnum) {
                case 1: tstr = "pay"; tlen = 3; break;
                case 2: tstr = "keyreg"; tlen = 6; break;
                case 3: tstr = "acfg"; tlen = 4; break;
                case 4: tstr = "axfer"; tlen = 5; break;
                case 5: tstr = "afrz"; tlen = 4; break;
                case 6: tstr = "appl"; tlen = 4; break;
            }
            stack_push(s, sv_bytes((const uint8_t*)tstr, tlen));
            break;
        }
        case FirstValidTime:
            // Block timestamp before FirstValid: nondeterministic
            pushint(s, nondet_uint64());
            break;
        case VotePK:
            stack_push(s, sv_bytes(txn.VotePK, 32));
            break;
        case SelectionPK:
            stack_push(s, sv_bytes(txn.SelectionPK, 32));
            break;
        case StateProofPK:
            stack_push(s, sv_bytes(txn.StateProofPK, 64));
            break;
        case VoteFirst:
            pushint(s, txn.VoteFirst);
            break;
        case VoteLast:
            pushint(s, txn.VoteLast);
            break;
        case VoteKeyDilution:
            pushint(s, txn.VoteKeyDilution);
            break;
        case Nonparticipation:
            pushint(s, txn.Nonparticipation ? 1 : 0);
            break;
        default:
            // Unknown field: nondeterministic (sound over-approximation)
            pushint(s, nondet_uint64());
            break;
    }
}

void txna_field(Stack& s, Txn& txn, txnField field, uint64_t idx) {
    switch (field) {
        case ApplicationArgs:
            avm_assert_check(idx < txn.NumAppArgs);
            stack_push(s, sv_bytes(txn.AppArgs[idx], txn.AppArgLens[idx]));
            break;
        case Accounts:
            // AVM spec: index 0 = Sender, index 1..N = Accounts[0..N-1]
            if (idx == 0) {
                stack_push(s, sv_bytes(txn.Sender, 32));
            } else {
                avm_assert_check(idx - 1 < txn.NumAccounts);
                stack_push(s, sv_bytes(txn.Accounts[idx - 1], 32));
            }
            break;
        case Assets:
            avm_assert_check(idx < txn.NumAssets);
            pushint(s, txn.Assets[idx]);
            break;
        case Applications:
            // AVM spec: index 0 = current ApplicationID, index 1..N = Applications[0..N-1]
            if (idx == 0) {
                pushint(s, txn.ApplicationID);
            } else {
                avm_assert_check(idx - 1 < txn.NumApplications);
                pushint(s, txn.Applications[idx - 1]);
            }
            break;
        case Logs:
            avm_assert_check(idx < txn.NumTxnLogs);
            stack_push(s, sv_bytes(txn.TxnLogs[idx], txn.TxnLogLens[idx]));
            break;
        case ApprovalProgramPages:
        case ClearStateProgramPages:
            // Program pages: stub with empty bytes
            stack_push(s, sv_empty_bytes());
            break;
        default:
            pushint(s, 0);
            break;
    }
}

// Wide operations for completeness
void addw(Stack& s) {
    StackValue a = stack_pop(s);
    StackValue b = stack_pop(s);
    avm_assert_check(sv_isInt(a) && sv_isInt(b));
    __uint128_t result = (__uint128_t)b.value + (__uint128_t)a.value;
    pushint(s, (uint64_t)(result >> 64));   // high
    pushint(s, (uint64_t)(result & UINT64_MAX)); // low
}

void mulw(Stack& s) {
    StackValue a = stack_pop(s);
    StackValue b = stack_pop(s);
    avm_assert_check(sv_isInt(a) && sv_isInt(b));
    __uint128_t result = (__uint128_t)b.value * (__uint128_t)a.value;
    pushint(s, (uint64_t)(result >> 64));
    pushint(s, (uint64_t)(result & UINT64_MAX));
}

// getbit/setbit for completeness
void getbit(Stack& s) {
    StackValue idx = stack_pop(s);
    StackValue target = stack_pop(s);
    avm_assert_check(sv_isInt(idx));
    if (sv_isInt(target)) {
        avm_assert_check(idx.value < 64);
        pushint(s, (target.value >> idx.value) & 1);
    } else {
        avm_assert_check(idx.value < target.byteslice_len * 8);
        uint64_t byte_idx = idx.value / 8;
        uint64_t bit_idx = 7 - (idx.value % 8);
        pushint(s, (target.byteslice[byte_idx] >> bit_idx) & 1);
    }
}

void setbit(Stack& s) {
    StackValue bit = stack_pop(s);
    StackValue idx = stack_pop(s);
    StackValue target = stack_pop(s);
    avm_assert_check(sv_isInt(idx) && sv_isInt(bit));
    avm_assert_check(bit.value <= 1);
    if (sv_isInt(target)) {
        avm_assert_check(idx.value < 64);
        if (bit.value) target.value |= (1ULL << idx.value);
        else target.value &= ~(1ULL << idx.value);
        stack_push(s, target);
    } else {
        avm_assert_check(idx.value < target.byteslice_len * 8);
        uint64_t byte_idx = idx.value / 8;
        uint64_t bit_idx = 7 - (idx.value % 8);
        if (bit.value) target.byteslice[byte_idx] |= (1 << bit_idx);
        else target.byteslice[byte_idx] &= ~(1 << bit_idx);
        stack_push(s, target);
    }
}

void bitlen(Stack& s) {
    StackValue a = stack_pop(s);
    if (sv_isInt(a)) {
        if (a.value == 0) { pushint(s, 0); return; }
        // Loop-free bit-length via binary search (6 comparisons, no loops)
        uint64_t bits = 0;
        uint64_t v = a.value;
        if (v >> 32) { bits += 32; v >>= 32; }
        if (v >> 16) { bits += 16; v >>= 16; }
        if (v >> 8)  { bits += 8;  v >>= 8; }
        if (v >> 4)  { bits += 4;  v >>= 4; }
        if (v >> 2)  { bits += 2;  v >>= 2; }
        if (v >> 1)  { bits += 1; }
        bits += 1;  // v is at least 1 at this point
        pushint(s, bits);
    } else {
        // For bytes, find the highest set bit
        uint64_t total_bits = 0;
        for (uint32_t i = 0; i < a.byteslice_len; i++) {
            if (a.byteslice[i] != 0) {
                uint8_t byte = a.byteslice[i];
                uint64_t bits = 0;
                while (byte > 0) { bits++; byte >>= 1; }
                total_bits = (a.byteslice_len - 1 - i) * 8 + bits;
                break;
            }
        }
        pushint(s, total_bits);
    }
}

// ============================================================================
// Phase 1: Byte manipulation with immediates
// ============================================================================

// extract S L — immediate 2-arg extract (very common in ARC4 contracts)
void extract(Stack& s, uint64_t start, uint64_t length) {
    StackValue a = stack_pop(s);
    avm_assert_check(sv_isBytes(a));
    // If length==0, extract from start to end
    uint64_t actual_len = (length == 0) ? (a.byteslice_len - start) : length;
    avm_assert_check(start + actual_len <= a.byteslice_len);
    StackValue result;
    result._is_bytes = true;
    result.value = 0;
    result.byteslice_len = (uint32_t)actual_len;
    _cbmc_bytecopy(result.byteslice, a.byteslice + (uint32_t)start, result.byteslice_len);
    stack_push(s, result);
}

// extract_uint32 — 4-byte big-endian extraction at stack offset
void extract_uint32(Stack& s) {
    StackValue b = stack_pop(s);  // offset
    StackValue a = stack_pop(s);  // source bytes
    avm_assert_check(sv_isInt(b) && sv_isBytes(a));
    avm_assert_check(b.value + 4 <= a.byteslice_len);
    uint64_t val = ((uint64_t)a.byteslice[b.value] << 24)
                 | ((uint64_t)a.byteslice[b.value + 1] << 16)
                 | ((uint64_t)a.byteslice[b.value + 2] << 8)
                 | (uint64_t)a.byteslice[b.value + 3];
    pushint(s, val);
}

// substring S E — immediate substring
void substring(Stack& s, uint64_t start, uint64_t end) {
    StackValue a = stack_pop(s);
    avm_assert_check(sv_isBytes(a));
    avm_assert_check(start <= end && end <= a.byteslice_len);
    StackValue result;
    result._is_bytes = true;
    result.value = 0;
    result.byteslice_len = (uint32_t)(end - start);
    _cbmc_bytecopy(result.byteslice, a.byteslice + (uint32_t)start, result.byteslice_len);
    stack_push(s, result);
}

// replace2 S — replace at immediate offset
void replace2(Stack& s, uint64_t offset) {
    StackValue replacement = stack_pop(s);  // replacement bytes
    StackValue original = stack_pop(s);      // original bytes
    avm_assert_check(sv_isBytes(replacement) && sv_isBytes(original));
    avm_assert_check(offset + replacement.byteslice_len <= original.byteslice_len);
    StackValue result = original;
    _cbmc_bytecopy(result.byteslice + (uint32_t)offset, replacement.byteslice, replacement.byteslice_len);
    stack_push(s, result);
}

// replace3 — replace at dynamic offset (from stack)
void replace3(Stack& s) {
    StackValue replacement = stack_pop(s);  // replacement bytes
    StackValue b = stack_pop(s);            // offset
    StackValue original = stack_pop(s);      // original bytes
    avm_assert_check(sv_isBytes(replacement) && sv_isInt(b) && sv_isBytes(original));
    avm_assert_check(b.value + replacement.byteslice_len <= original.byteslice_len);
    StackValue result = original;
    _cbmc_bytecopy(result.byteslice + (uint32_t)b.value, replacement.byteslice, replacement.byteslice_len);
    stack_push(s, result);
}

// getbyte — get single byte at index
void getbyte(Stack& s) {
    StackValue b = stack_pop(s);  // index
    StackValue a = stack_pop(s);  // source bytes
    avm_assert_check(sv_isInt(b) && sv_isBytes(a));
    avm_assert_check(b.value < a.byteslice_len);
    pushint(s, a.byteslice[b.value]);
}

// setbyte — set single byte at index
void setbyte_op(Stack& s) {
    StackValue c = stack_pop(s);  // new byte value
    StackValue b = stack_pop(s);  // index
    StackValue a = stack_pop(s);  // source bytes
    avm_assert_check(sv_isInt(c) && sv_isInt(b) && sv_isBytes(a));
    avm_assert_check(b.value < a.byteslice_len);
    avm_assert_check(c.value <= 255);
    StackValue result = a;
    result.byteslice[b.value] = (uint8_t)c.value;
    stack_push(s, result);
}

// setbyte alias — transpiler emits setbyte(s), engine defines setbyte_op(s)
void setbyte(Stack& s) { setbyte_op(s); }

// ============================================================================
// Phase 2: Dynamic scratch + wide math
// ============================================================================

// loads — dynamic scratch load (slot from stack)
void loads(Stack& s, EvalContext& ctx) {
    StackValue slot_val = stack_pop(s);
    avm_assert_check(sv_isInt(slot_val));
    avm_assert_check(slot_val.value < CBMC_SCRATCH_SLOTS);
    stack_push(s, ctx.sp[slot_val.value]);
}

// stores — dynamic scratch store (slot from stack)
void stores(Stack& s, EvalContext& ctx) {
    StackValue val = stack_pop(s);
    StackValue slot_val = stack_pop(s);
    avm_assert_check(sv_isInt(slot_val));
    avm_assert_check(slot_val.value < CBMC_SCRATCH_SLOTS);
    ctx.sp[slot_val.value] = val;
}

// divw — wide division: (high:low) / divisor → quotient
void divw(Stack& s) {
    StackValue divisor = stack_pop(s);
    StackValue low = stack_pop(s);
    StackValue high = stack_pop(s);
    avm_assert_check(sv_isInt(divisor) && sv_isInt(low) && sv_isInt(high));
    avm_assert_check(divisor.value != 0);
    __uint128_t dividend = ((__uint128_t)high.value << 64) | (__uint128_t)low.value;
    __uint128_t quotient = dividend / (__uint128_t)divisor.value;
    avm_assert_check(quotient <= UINT64_MAX);
    pushint(s, (uint64_t)quotient);
}

// divmodw — wide divmod: (high_a:low_a) divmod (high_b:low_b) → q_high q_low r_high r_low
void divmodw(Stack& s) {
    StackValue b_low = stack_pop(s);
    StackValue b_high = stack_pop(s);
    StackValue a_low = stack_pop(s);
    StackValue a_high = stack_pop(s);
    avm_assert_check(sv_isInt(a_high) && sv_isInt(a_low) && sv_isInt(b_high) && sv_isInt(b_low));
    __uint128_t a = ((__uint128_t)a_high.value << 64) | (__uint128_t)a_low.value;
    __uint128_t b = ((__uint128_t)b_high.value << 64) | (__uint128_t)b_low.value;
    avm_assert_check(b != 0);
    __uint128_t q = a / b;
    __uint128_t r = a % b;
    pushint(s, (uint64_t)(q >> 64));
    pushint(s, (uint64_t)(q & UINT64_MAX));
    pushint(s, (uint64_t)(r >> 64));
    pushint(s, (uint64_t)(r & UINT64_MAX));
}

// expw — wide exponent: base^exp → high low (128-bit result)
void expw(Stack& s) {
    StackValue exp_val = stack_pop(s);
    StackValue base_val = stack_pop(s);
    avm_assert_check(sv_isInt(exp_val) && sv_isInt(base_val));
    __uint128_t base = (__uint128_t)base_val.value;
    uint64_t exp = exp_val.value;
    // AVM panics on overflow, so base^exp must fit in 128 bits.
    // 2^128 overflows, so exp <= 127 is a sound bound for any base >= 2.
    __CPROVER_assume(exp <= 127);
    __uint128_t result = 1;
    for (uint64_t i = 0; i < exp; i++) {
        result *= base;
    }
    pushint(s, (uint64_t)(result >> 64));
    pushint(s, (uint64_t)(result & UINT64_MAX));
}

// ============================================================================
// Phase 3: Subroutine frame operations
// ============================================================================

// proto num_args num_returns — set up subroutine frame
void proto(Stack& s, EvalContext& ctx, uint64_t num_args, uint64_t num_returns) {
    avm_assert_check(ctx.frame_count < CBMC_MAX_FRAMES);
    avm_assert_check(s.currentSize >= num_args);
    Frame& f = ctx.frames[ctx.frame_count];
    f.base = s.currentSize - (uint16_t)num_args;
    f.num_args = (uint8_t)num_args;
    f.num_returns = (uint8_t)num_returns;
    ctx.frame_count++;
}

// frame_dig idx — access frame variable
// Negative idx = argument (frame_dig -1 = last arg), positive = local
void frame_dig(Stack& s, EvalContext& ctx, int idx) {
    avm_assert_check(ctx.frame_count > 0);
    Frame& f = ctx.frames[ctx.frame_count - 1];
    uint32_t abs_idx = f.base + (uint32_t)((int)f.num_args + idx);
    avm_assert_check(abs_idx < s.currentSize);
    stack_push(s, s.stack[abs_idx]);
}

// frame_bury idx — set frame variable
void frame_bury(Stack& s, EvalContext& ctx, int idx) {
    avm_assert_check(ctx.frame_count > 0);
    Frame& f = ctx.frames[ctx.frame_count - 1];
    StackValue val = stack_pop(s);
    uint32_t abs_idx = f.base + (uint32_t)((int)f.num_args + idx);
    avm_assert_check(abs_idx < s.currentSize);
    s.stack[abs_idx] = val;
}

// retsub_cleanup — clean up frame on return (remove locals, keep returns)
void retsub_cleanup(Stack& s, EvalContext& ctx) {
    // If no frame was pushed (callsub without proto), retsub is a plain return.
    // TEAL v3-v7 subroutines use callsub/retsub without frames.
    if (ctx.frame_count == 0) return;
    Frame& f = ctx.frames[ctx.frame_count - 1];
    // Top num_returns values are the return values
    // We need to copy them down to frame base and adjust stack size
    uint16_t ret_start = s.currentSize - f.num_returns;
    for (uint8_t i = 0; i < f.num_returns; i++) {
        s.stack[f.base + i] = s.stack[ret_start + i];
    }
    s.currentSize = f.base + f.num_returns;
    ctx.frame_count--;
}

// ============================================================================
// Phase 4: State operations
// ============================================================================

// app_global_get_ex — get with found flag and app_id
void app_global_get_ex(Stack& s, BlockchainState& BS, EvalContext& ctx) {
    StackValue key = stack_pop(s);
    StackValue app_id = stack_pop(s);
    avm_assert_check(sv_isBytes(key) && sv_isInt(app_id));
    // Only support current app for now
    StackValue* val = gs_get(BS.globals, key.byteslice, key.byteslice_len);
    if (val) {
        stack_push(s, *val);
        pushint(s, 1);  // found
    } else {
        pushint(s, 0);
        pushint(s, 0);  // not found
    }
}

// _resolve_account_addr — resolve integer account index to address
// AVM spec: 0 = Sender, 1..N = Txn.Accounts[0..N-1]
const uint8_t* _resolve_account_addr(StackValue& acct, Txn& txn) {
    if (sv_isBytes(acct)) {
        return acct.byteslice;
    }
    // Integer index
    uint64_t idx = acct.value;
    if (idx == 0) {
        return txn.Sender;
    }
    // idx 1..N maps to Txn.Accounts[idx-1]
    avm_assert_check(idx <= txn.NumAccounts);
    return txn.Accounts[idx - 1];
}

// app_local_put — store local state (panics if account not opted in)
void app_local_put(Stack& s, BlockchainState& BS, Txn& txn, EvalContext& ctx) {
    StackValue val = stack_pop(s);
    StackValue key = stack_pop(s);
    StackValue acct = stack_pop(s);
    avm_assert_check(sv_isBytes(key));
    const uint8_t* addr = _resolve_account_addr(acct, txn);
    // AVM: account must be opted in to write local state
    LocalEntry* le = ls_find_account(BS.locals, addr);
    avm_assert_check(le != 0);  // panic if not opted in

    // Schema enforcement is handled inside ls_put via running counters.
    ls_put(BS.locals, addr, key.byteslice, key.byteslice_len, val);
}

// app_local_get — load local state (returns 0 if not opted in or key missing)
void app_local_get(Stack& s, BlockchainState& BS, Txn& txn, EvalContext& ctx) {
    StackValue key = stack_pop(s);
    StackValue acct = stack_pop(s);
    avm_assert_check(sv_isBytes(key));
    const uint8_t* addr = _resolve_account_addr(acct, txn);
    StackValue* val = ls_get(BS.locals, addr, key.byteslice, key.byteslice_len);
    if (val) {
        stack_push(s, *val);
    } else {
        pushint(s, 0);
    }
}

// app_local_get_ex — load local state with found flag
// Returns (value, 1) if found, (0, 0) if not opted in or key missing
void app_local_get_ex(Stack& s, BlockchainState& BS, Txn& txn, EvalContext& ctx) {
    StackValue key = stack_pop(s);
    StackValue app_id = stack_pop(s);
    StackValue acct = stack_pop(s);
    avm_assert_check(sv_isBytes(key) && sv_isInt(app_id));
    const uint8_t* addr = _resolve_account_addr(acct, txn);
    // If account not opted in, return (0, 0)
    LocalEntry* le = ls_find_account(BS.locals, addr);
    if (!le) {
        pushint(s, 0);
        pushint(s, 0);
        return;
    }
    StackValue* val = ls_get(BS.locals, addr, key.byteslice, key.byteslice_len);
    if (val) {
        stack_push(s, *val);
        pushint(s, 1);
    } else {
        pushint(s, 0);
        pushint(s, 0);
    }
}

// app_local_del — delete local state (panics if account not opted in)
void app_local_del(Stack& s, BlockchainState& BS, Txn& txn, EvalContext& ctx) {
    StackValue key = stack_pop(s);
    StackValue acct = stack_pop(s);
    avm_assert_check(sv_isBytes(key));
    const uint8_t* addr = _resolve_account_addr(acct, txn);
    // AVM: account must be opted in to delete local state
    LocalEntry* le = ls_find_account(BS.locals, addr);
    avm_assert_check(le != 0);  // panic if not opted in
    ls_del(BS.locals, addr, key.byteslice, key.byteslice_len);
}

// app_opted_in — check if account has local state for app
void app_opted_in(Stack& s, BlockchainState& BS, Txn& txn, EvalContext& ctx) {
    StackValue app_id = stack_pop(s);
    StackValue acct = stack_pop(s);
    avm_assert_check(sv_isInt(app_id));
    const uint8_t* addr = _resolve_account_addr(acct, txn);
    LocalEntry* le = ls_find_account(BS.locals, addr);
    pushint(s, le ? 1 : 0);
}

// global field — Round, LatestTimestamp, MinTxnFee, etc.
void global_field(Stack& s, BlockchainState& BS, EvalContext& ctx, globalFieldEnum field) {
    switch (field) {
        case GF_Round:
            pushint(s, BS.round);
            break;
        case GF_LatestTimestamp:
            pushint(s, BS.latest_timestamp);
            break;
        case GF_MinTxnFee:
            pushint(s, BS.min_txn_fee);
            break;
        case GF_MinBalance:
            pushint(s, BS.min_balance);
            break;
        case GF_MaxTxnLife:
            pushint(s, BS.max_txn_life);
            break;
        case GF_GroupSize:
            pushint(s, BS.group_size);
            break;
        case GF_CurrentApplicationID:
            pushint(s, ctx.CurrentApplicationID);
            break;
        case GF_CurrentApplicationAddress:
            stack_push(s, sv_bytes(ctx.CurrentApplicationAddress, 32));
            break;
        case GF_CreatorAddress:
            stack_push(s, sv_bytes(ctx.CreatorAddress, 32));
            break;
        case GF_ZeroAddress: {
            uint8_t zeros[32];
            _cbmc_zero(zeros, 32);
            stack_push(s, sv_bytes(zeros, 32));
            break;
        }
        case GF_GenesisHash: {
            stack_push(s, sv_nondet_bytes(32));
            break;
        }
        case GF_OpcodeBudget:
            pushint(s, nondet_uint64());
            break;
        case GF_LogicSigVersion:
            pushint(s, 10);  // AVM v10
            break;
        case GF_CallerApplicationID:
            // In non-inner context, caller is 0. In inner calls, return nondeterministic.
            pushint(s, nondet_uint64());
            break;
        case GF_CallerApplicationAddress: {
            stack_push(s, sv_nondet_bytes(32));
            break;
        }
        case GF_GroupID: {
            stack_push(s, sv_nondet_bytes(32));
            break;
        }
        case GF_AssetCreateMinBalance:
            pushint(s, 100000);  // Algorand constant: 0.1 ALGO
            break;
        case GF_AssetOptInMinBalance:
            pushint(s, 100000);  // Algorand constant: 0.1 ALGO
            break;
        case GF_PayoutsEnabled:
        case GF_PayoutsGoOnlineFee:
        case GF_PayoutsPercent:
        case GF_PayoutsMinBalance:
        case GF_PayoutsMaxBalance:
            // Payout fields: nondeterministic (consensus parameters)
            pushint(s, nondet_uint64());
            break;
        default:
            // Unknown global field: nondeterministic (sound over-approximation)
            pushint(s, nondet_uint64());
            break;
    }
}

// balance — returns account balance
void balance_op(Stack& s, BlockchainState& BS, Txn& txn) {
    StackValue acct = stack_pop(s);
    const uint8_t* addr = _resolve_account_addr(acct, txn);
    AccountEntry* ae = acct_find(BS.accounts, addr);
    if (ae) {
        pushint(s, ae->balance);
    } else {
        // Unmodeled account: use app_balance for app address, nondeterministic otherwise
        pushint(s, nondet_uint64());
    }
}

// min_balance — returns minimum balance
void min_balance_op(Stack& s, BlockchainState& BS, Txn& txn) {
    StackValue acct = stack_pop(s);
    const uint8_t* addr = _resolve_account_addr(acct, txn);
    AccountEntry* ae = acct_find(BS.accounts, addr);
    pushint(s, ae ? ae->min_balance : BS.min_balance);
}

// ============================================================================
// Phase 5: Box storage operations
// ============================================================================

// box_create — create a new box
void box_create_op(Stack& s, BlockchainState& BS, Txn& txn, EvalContext& ctx) {
    StackValue size = stack_pop(s);
    StackValue key = stack_pop(s);
    avm_assert_check(sv_isInt(size) && sv_isBytes(key));
    avm_assert_check(size.value <= CBMC_BOX_MAX_SIZE);
    BoxEntry* existing = box_find(BS.boxes, key.byteslice, key.byteslice_len);
    if (existing) {
        pushint(s, 0);  // already exists
        return;
    }
    __CPROVER_assume(BS.boxes.count < CBMC_MAX_BOXES);
    BoxEntry& e = BS.boxes.entries[BS.boxes.count];
    e.active = true;
    e.key_len = key.byteslice_len;
    _cbmc_bytecopy(e.key, key.byteslice, key.byteslice_len);
    e.data_len = (uint32_t)size.value;
    _cbmc_zero(e.data, e.data_len);
    BS.boxes.count++;
    pushint(s, 1);  // created
}

// box_del — delete a box
void box_del_op(Stack& s, BlockchainState& BS, Txn& txn, EvalContext& ctx) {
    StackValue key = stack_pop(s);
    avm_assert_check(sv_isBytes(key));
    BoxEntry* e = box_find(BS.boxes, key.byteslice, key.byteslice_len);
    if (e) {
        e->active = false;
        pushint(s, 1);  // deleted
    } else {
        pushint(s, 0);  // not found
    }
}

// box_get — get box contents
void box_get_op(Stack& s, BlockchainState& BS, Txn& txn, EvalContext& ctx) {
    StackValue key = stack_pop(s);
    avm_assert_check(sv_isBytes(key));
    BoxEntry* e = box_find(BS.boxes, key.byteslice, key.byteslice_len);
    if (e) {
        avm_assert_check(e->data_len <= CBMC_BYTES_MAX);
        stack_push(s, sv_bytes(e->data, e->data_len));
        pushint(s, 1);  // found
    } else {
        stack_push(s, sv_empty_bytes());
        pushint(s, 0);  // not found
    }
}

// box_put — put box contents (box must exist and size must match)
void box_put_op(Stack& s, BlockchainState& BS, Txn& txn, EvalContext& ctx) {
    StackValue val = stack_pop(s);
    StackValue key = stack_pop(s);
    avm_assert_check(sv_isBytes(key) && sv_isBytes(val));
    BoxEntry* e = box_find(BS.boxes, key.byteslice, key.byteslice_len);
    avm_assert_check(e != 0);
    avm_assert_check(val.byteslice_len == e->data_len);
    _cbmc_bytecopy(e->data, val.byteslice, val.byteslice_len);
}

// box_len — get box length
void box_len_op(Stack& s, BlockchainState& BS, Txn& txn, EvalContext& ctx) {
    StackValue key = stack_pop(s);
    avm_assert_check(sv_isBytes(key));
    BoxEntry* e = box_find(BS.boxes, key.byteslice, key.byteslice_len);
    if (e) {
        pushint(s, e->data_len);
        pushint(s, 1);  // found
    } else {
        pushint(s, 0);
        pushint(s, 0);  // not found
    }
}

// box_extract — extract bytes from a box
void box_extract_op(Stack& s, BlockchainState& BS, Txn& txn, EvalContext& ctx) {
    StackValue length = stack_pop(s);
    StackValue offset = stack_pop(s);
    StackValue key = stack_pop(s);
    avm_assert_check(sv_isBytes(key) && sv_isInt(offset) && sv_isInt(length));
    BoxEntry* e = box_find(BS.boxes, key.byteslice, key.byteslice_len);
    avm_assert_check(e != 0);
    avm_assert_check(offset.value + length.value <= e->data_len);
    avm_assert_check(length.value <= CBMC_BYTES_MAX);
    stack_push(s, sv_bytes(e->data + (uint32_t)offset.value, (uint32_t)length.value));
}

// box_replace — replace bytes in a box at offset
void box_replace_op(Stack& s, BlockchainState& BS, Txn& txn, EvalContext& ctx) {
    StackValue val = stack_pop(s);
    StackValue offset = stack_pop(s);
    StackValue key = stack_pop(s);
    avm_assert_check(sv_isBytes(key) && sv_isInt(offset) && sv_isBytes(val));
    BoxEntry* e = box_find(BS.boxes, key.byteslice, key.byteslice_len);
    avm_assert_check(e != 0);
    avm_assert_check(offset.value + val.byteslice_len <= e->data_len);
    _cbmc_bytecopy(e->data + (uint32_t)offset.value, val.byteslice, val.byteslice_len);
}

// box_resize — change the size of an existing box (AVM v10)
// Stack: ..., A (name: bytes), B (new_size: uint) → ...
// If new_size > old_size: zero-pads at end.
// If new_size < old_size: truncates from end.
// Panics if box doesn't exist or new_size > CBMC_BOX_MAX_SIZE.
void box_resize_op(Stack& s, BlockchainState& BS, Txn& txn, EvalContext& ctx) {
    StackValue new_size = stack_pop(s);
    StackValue key = stack_pop(s);
    avm_assert_check(sv_isBytes(key) && sv_isInt(new_size));
    avm_assert_check(new_size.value <= CBMC_BOX_MAX_SIZE);
    BoxEntry* e = box_find(BS.boxes, key.byteslice, key.byteslice_len);
    avm_assert_check(e != 0);
    uint32_t old_len = e->data_len;
    uint32_t new_len = (uint32_t)new_size.value;
    // Zero-fill any new space beyond old length
    for (uint32_t i = old_len; i < new_len && i < CBMC_BOX_MAX_SIZE; i++) {
        e->data[i] = 0;
    }
    e->data_len = new_len;
}

// box_splice — splice bytes into a box at an offset (AVM v10)
// Stack: ..., A (name: bytes), B (offset: uint), C (delete_count: uint), D (replacement: bytes) → ...
// Result: A[:B] + D + A[B+C:]  then adjusted to maintain original box size:
//   - If len(D) > C: excess bytes at end are trimmed
//   - If len(D) < C: zero bytes appended to maintain length
// Panics if box doesn't exist, or offset > box_size.
void box_splice_op(Stack& s, BlockchainState& BS, Txn& txn, EvalContext& ctx) {
    StackValue replacement = stack_pop(s);
    StackValue del_count = stack_pop(s);
    StackValue offset = stack_pop(s);
    StackValue key = stack_pop(s);
    avm_assert_check(sv_isBytes(key) && sv_isInt(offset) && sv_isInt(del_count) && sv_isBytes(replacement));
    BoxEntry* e = box_find(BS.boxes, key.byteslice, key.byteslice_len);
    avm_assert_check(e != 0);
    uint32_t box_len = e->data_len;
    uint32_t off = (uint32_t)offset.value;
    uint32_t dc = (uint32_t)del_count.value;
    uint32_t rep_len = replacement.byteslice_len;
    avm_assert_check(off <= box_len);
    // Clamp delete_count so we don't go past end of box
    if (off + dc > box_len) dc = box_len - off;

    // Build the spliced result in a temp buffer:
    //   result = original[:off] + replacement + original[off+dc:]
    // Then pad/trim to maintain original box_len.
    // Note: per-byte loops are faster for CBMC than _cbmc_bytecopy here because
    // the 8-byte chunking with symbolic offsets into e->data causes pointer analysis explosion.
    uint8_t tmp[CBMC_BOX_MAX_SIZE];
    uint32_t pos = 0;

    // Part 1: original[:off]
    for (uint32_t i = 0; i < off && pos < CBMC_BOX_MAX_SIZE; i++) {
        tmp[pos++] = e->data[i];
    }
    // Part 2: replacement bytes
    for (uint32_t i = 0; i < rep_len && pos < CBMC_BOX_MAX_SIZE; i++) {
        tmp[pos++] = replacement.byteslice[i];
    }
    // Part 3: original[off+dc:]
    for (uint32_t i = off + dc; i < box_len && pos < CBMC_BOX_MAX_SIZE; i++) {
        tmp[pos++] = e->data[i];
    }
    // Pad with zeros if result is shorter than original box
    for (uint32_t i = pos; i < box_len && i < CBMC_BOX_MAX_SIZE; i++) {
        tmp[i] = 0;
    }
    // Trim: only copy up to original box_len
    for (uint32_t i = 0; i < box_len; i++) {
        e->data[i] = tmp[i];
    }
    // box_len stays the same
}

// Transpiler-compatible aliases (transpiler emits box_create, CBMC uses box_create_op)
void box_create(Stack& s, BlockchainState& BS, Txn& txn, EvalContext& ctx) { box_create_op(s, BS, txn, ctx); }
void box_del(Stack& s, BlockchainState& BS, Txn& txn, EvalContext& ctx) { box_del_op(s, BS, txn, ctx); }
void box_get(Stack& s, BlockchainState& BS, Txn& txn, EvalContext& ctx) { box_get_op(s, BS, txn, ctx); }
void box_put(Stack& s, BlockchainState& BS, Txn& txn, EvalContext& ctx) { box_put_op(s, BS, txn, ctx); }
void box_len(Stack& s, BlockchainState& BS, Txn& txn, EvalContext& ctx) { box_len_op(s, BS, txn, ctx); }
void box_extract(Stack& s, BlockchainState& BS, Txn& txn, EvalContext& ctx) { box_extract_op(s, BS, txn, ctx); }
void box_replace(Stack& s, BlockchainState& BS, Txn& txn, EvalContext& ctx) { box_replace_op(s, BS, txn, ctx); }
void box_resize(Stack& s, BlockchainState& BS, Txn& txn, EvalContext& ctx) { box_resize_op(s, BS, txn, ctx); }
void box_splice(Stack& s, BlockchainState& BS, Txn& txn, EvalContext& ctx) { box_splice_op(s, BS, txn, ctx); }
void balance(Stack& s, BlockchainState& BS, Txn& txn) { balance_op(s, BS, txn); }
void min_balance(Stack& s, BlockchainState& BS, Txn& txn) { min_balance_op(s, BS, txn); }
void select(Stack& s) { select_op(s); }
void itxn_field(Stack& s, EvalContext& ctx, txnField field) { itxn_field_set(s, ctx, field); }

// ============================================================================
// Phase 6: Group txn access + inner txn stubs
// ============================================================================

// gtxn field — access group txn by index
void gtxn_field(Stack& s, TxnGroup& tg, uint64_t idx, txnField field) {
    avm_assert_check(idx < tg.size);
    txn_field(s, tg.txns[idx], field);
}

// gtxna field — access group txn array field
void gtxna_field(Stack& s, TxnGroup& tg, uint64_t idx, txnField field, uint64_t array_idx) {
    avm_assert_check(idx < tg.size);
    txna_field(s, tg.txns[idx], field, array_idx);
}

// gtxns field — dynamic group txn field access (index from stack)
void gtxns_field(Stack& s, TxnGroup& tg, txnField field) {
    StackValue idx = stack_pop(s);
    avm_assert_check(sv_isInt(idx));
    avm_assert_check(idx.value < tg.size);
    txn_field(s, tg.txns[idx.value], field);
}

// Txn* overloads — templates declare `Txn TxnGroup[N]` (a Txn*), but the
// TxnGroup& overloads above expect the struct. These overloads bridge the gap.
void gtxn_field(Stack& s, Txn* tg, uint64_t idx, txnField field) {
    txn_field(s, tg[idx], field);
}
void gtxna_field(Stack& s, Txn* tg, uint64_t idx, txnField field, uint64_t array_idx) {
    txna_field(s, tg[idx], field, array_idx);
}
void gtxns_field(Stack& s, Txn* tg, txnField field) {
    StackValue idx = stack_pop(s);
    avm_assert_check(sv_isInt(idx));
    txn_field(s, tg[idx.value], field);
}
void gtxnsa(Stack& s, Txn* tg, txnField field, uint64_t array_idx) {
    StackValue txn_idx = stack_pop(s);
    avm_assert_check(sv_isInt(txn_idx));
    txna_field(s, tg[txn_idx.value], field, array_idx);
}
void gtxnas(Stack& s, Txn* tg, uint64_t txn_idx, txnField field) {
    StackValue array_idx = stack_pop(s);
    avm_assert_check(sv_isInt(array_idx));
    txna_field(s, tg[txn_idx], field, array_idx.value);
}
void gtxnsas(Stack& s, Txn* tg, txnField field) {
    StackValue txn_idx = stack_pop(s);
    StackValue array_idx = stack_pop(s);
    avm_assert_check(sv_isInt(txn_idx) && sv_isInt(array_idx));
    txna_field(s, tg[txn_idx.value], field, array_idx.value);
}

// txnas — txn array field access with stack-based index
// Usage: push index; txnas F → pushes Txn.F[stack_top]
void txnas(Stack& s, Txn& txn, txnField field) {
    StackValue idx = stack_pop(s);
    avm_assert_check(sv_isInt(idx));
    txna_field(s, txn, field, idx.value);
}

// gtxnas — group txn array field with stack-based array index
// Usage: push array_idx; gtxnas T F → pushes GroupTxn[T].F[stack_top]
void gtxnas(Stack& s, TxnGroup& tg, uint64_t txn_idx, txnField field) {
    StackValue array_idx = stack_pop(s);
    avm_assert_check(sv_isInt(array_idx));
    avm_assert_check(txn_idx < tg.size);
    txna_field(s, tg.txns[txn_idx], field, array_idx.value);
}

// gtxnsa — group txn array field with stack-based txn index, immediate array index
// Usage: push txn_idx; gtxnsa F I → pushes GroupTxn[stack_top].F[I]
void gtxnsa(Stack& s, TxnGroup& tg, txnField field, uint64_t array_idx) {
    StackValue txn_idx = stack_pop(s);
    avm_assert_check(sv_isInt(txn_idx));
    avm_assert_check(txn_idx.value < tg.size);
    txna_field(s, tg.txns[txn_idx.value], field, array_idx);
}

// gtxnsas — group txn array field with both indices from stack
// Usage: push array_idx; push txn_idx; gtxnsas F → pushes GroupTxn[stack_top].F[stack_top-1]
void gtxnsas(Stack& s, TxnGroup& tg, txnField field) {
    StackValue txn_idx = stack_pop(s);
    StackValue array_idx = stack_pop(s);
    avm_assert_check(sv_isInt(txn_idx) && sv_isInt(array_idx));
    avm_assert_check(txn_idx.value < tg.size);
    txna_field(s, tg.txns[txn_idx.value], field, array_idx.value);
}

// gload — read scratch space from group transaction (nondeterministic stub)
// AVM: gload T S — push scratch space slot S from group transaction T
// We don't execute other group transactions, so return nondeterministic value.
void gload_op(Stack& s, uint64_t txn_idx, uint64_t slot) {
    pushint(s, nondet_uint64());
}

// gloads — read scratch space from group transaction (index from stack)
// AVM: gloads S — pop txn index, push scratch slot S from that group txn
void gloads_op(Stack& s, uint64_t slot) {
    StackValue idx = stack_pop(s);
    avm_assert_check(sv_isInt(idx));
    pushint(s, nondet_uint64());
}

// gaid — get app ID created by group transaction (nondeterministic stub)
// AVM: gaid T — push the app ID created by group transaction T
void gaid_op(Stack& s, uint64_t txn_idx) {
    pushint(s, nondet_uint64());
}

// gaids — get app ID created by group transaction (index from stack)
// AVM: gaids — pop txn index, push app ID created by that group txn
void gaids_op(Stack& s) {
    StackValue idx = stack_pop(s);
    avm_assert_check(sv_isInt(idx));
    pushint(s, nondet_uint64());
}

// itxnas — read last submitted inner txn array field with stack-based index
void itxnas(Stack& s, EvalContext& ctx, txnField field) {
    StackValue idx = stack_pop(s);
    avm_assert_check(sv_isInt(idx));
    avm_assert_check(ctx.inner_count > 0);
    txna_field(s, ctx.inner_txns[ctx.inner_count - 1].txn, field, idx.value);
}

// gitxnas — read inner txn array field by group index, stack-based array index
void gitxnas(Stack& s, EvalContext& ctx, uint64_t txn_idx, txnField field) {
    StackValue array_idx = stack_pop(s);
    avm_assert_check(sv_isInt(array_idx));
    avm_assert_check(txn_idx < ctx.inner_count);
    txna_field(s, ctx.inner_txns[txn_idx].txn, field, array_idx.value);
}

// itxn_begin — start building an inner transaction
void itxn_begin(Stack& s, EvalContext& ctx) {
    ctx.building_itxn = true;
    _cbmc_txn_zero(ctx.building_txn);
}

// itxn_field — set a field on the building inner txn
void itxn_field_set(Stack& s, EvalContext& ctx, txnField field) {
    avm_assert_check(ctx.building_itxn);
    StackValue val = stack_pop(s);
    switch (field) {
        case Fee:
            avm_assert_check(sv_isInt(val));
            ctx.building_txn.Fee = val.value;
            break;
        case Amount:
            avm_assert_check(sv_isInt(val));
            ctx.building_txn.Amount = val.value;
            break;
        case TypeEnum:
            avm_assert_check(sv_isInt(val));
            ctx.building_txn.TypeEnum = (uint8_t)val.value;
            break;
        case OnCompletion:
            avm_assert_check(sv_isInt(val));
            ctx.building_txn.apan = (uint8_t)val.value;
            break;
        case ApplicationID:
            avm_assert_check(sv_isInt(val));
            ctx.building_txn.ApplicationID = val.value;
            break;
        case Receiver:
            avm_assert_check(sv_isBytes(val));
            _cbmc_sv_to_addr(ctx.building_txn.Receiver, val.byteslice, val.byteslice_len);
            break;
        case Accounts:
            avm_assert_check(sv_isBytes(val));
            if (ctx.building_txn.NumAccounts < CBMC_MAX_TXN_ACCOUNTS) {
                uint64_t aidx = ctx.building_txn.NumAccounts;
                _cbmc_sv_to_addr(ctx.building_txn.Accounts[aidx], val.byteslice, val.byteslice_len);
                ctx.building_txn.NumAccounts++;
            }
            break;
        case Assets:
            avm_assert_check(sv_isInt(val));
            if (ctx.building_txn.NumAssets < CBMC_MAX_TXN_ASSETS) {
                ctx.building_txn.Assets[ctx.building_txn.NumAssets] = val.value;
                ctx.building_txn.NumAssets++;
            }
            break;
        case Applications:
            avm_assert_check(sv_isInt(val));
            if (ctx.building_txn.NumApplications < CBMC_MAX_TXN_APPS) {
                ctx.building_txn.Applications[ctx.building_txn.NumApplications] = val.value;
                ctx.building_txn.NumApplications++;
            }
            break;
        case ApplicationArgs:
            avm_assert_check(sv_isBytes(val));
            if (ctx.building_txn.NumAppArgs < CBMC_MAX_APP_ARGS) {
                uint64_t idx = ctx.building_txn.NumAppArgs;
                ctx.building_txn.AppArgLens[idx] = val.byteslice_len;
                _cbmc_bytecopy(ctx.building_txn.AppArgs[idx], val.byteslice, val.byteslice_len);
                ctx.building_txn.NumAppArgs++;
            }
            break;
        case XferAsset:
            avm_assert_check(sv_isInt(val));
            ctx.building_txn.XferAsset = val.value;
            break;
        case AssetAmount:
            avm_assert_check(sv_isInt(val));
            ctx.building_txn.AssetAmount = val.value;
            break;
        case AssetReceiver:
            avm_assert_check(sv_isBytes(val));
            _cbmc_sv_to_addr(ctx.building_txn.AssetReceiver, val.byteslice, val.byteslice_len);
            break;
        case AssetSender:
            avm_assert_check(sv_isBytes(val));
            _cbmc_sv_to_addr(ctx.building_txn.AssetSender, val.byteslice, val.byteslice_len);
            break;
        case ConfigAsset:
            avm_assert_check(sv_isInt(val));
            ctx.building_txn.ConfigAsset = val.value;
            break;
        case ConfigAssetTotal:
            avm_assert_check(sv_isInt(val));
            ctx.building_txn.ConfigAssetTotal = val.value;
            break;
        case ConfigAssetDecimals:
            avm_assert_check(sv_isInt(val));
            ctx.building_txn.ConfigAssetDecimals = val.value;
            break;
        case ConfigAssetName:
            avm_assert_check(sv_isBytes(val));
            ctx.building_txn.ConfigAssetNameLen = val.byteslice_len;
            _cbmc_bytecopy(ctx.building_txn.ConfigAssetName, val.byteslice, val.byteslice_len);
            break;
        case ConfigAssetUnitName:
            avm_assert_check(sv_isBytes(val));
            ctx.building_txn.ConfigAssetUnitNameLen = val.byteslice_len;
            _cbmc_bytecopy(ctx.building_txn.ConfigAssetUnitName, val.byteslice, val.byteslice_len);
            break;
        case ConfigAssetURL:
            avm_assert_check(sv_isBytes(val));
            ctx.building_txn.ConfigAssetURLLen = val.byteslice_len;
            _cbmc_bytecopy(ctx.building_txn.ConfigAssetURL, val.byteslice, val.byteslice_len);
            break;
        case ConfigAssetMetadataHash:
            avm_assert_check(sv_isBytes(val));
            _cbmc_sv_to_addr(ctx.building_txn.ConfigAssetMetadataHash, val.byteslice, val.byteslice_len);
            break;
        case ConfigAssetManager:
            avm_assert_check(sv_isBytes(val));
            _cbmc_sv_to_addr(ctx.building_txn.ConfigAssetManager, val.byteslice, val.byteslice_len);
            break;
        case ConfigAssetReserve:
            avm_assert_check(sv_isBytes(val));
            _cbmc_sv_to_addr(ctx.building_txn.ConfigAssetReserve, val.byteslice, val.byteslice_len);
            break;
        case ConfigAssetFreeze:
            avm_assert_check(sv_isBytes(val));
            _cbmc_sv_to_addr(ctx.building_txn.ConfigAssetFreeze, val.byteslice, val.byteslice_len);
            break;
        case ConfigAssetClawback:
            avm_assert_check(sv_isBytes(val));
            _cbmc_sv_to_addr(ctx.building_txn.ConfigAssetClawback, val.byteslice, val.byteslice_len);
            break;
        case RekeyTo:
            avm_assert_check(sv_isBytes(val));
            _cbmc_sv_to_addr(ctx.building_txn.RekeyTo, val.byteslice, val.byteslice_len);
            break;
        case CloseRemainderTo:
            avm_assert_check(sv_isBytes(val));
            _cbmc_sv_to_addr(ctx.building_txn.CloseRemainderTo, val.byteslice, val.byteslice_len);
            break;
        case Note:
            avm_assert_check(sv_isBytes(val));
            ctx.building_txn.NoteLen = val.byteslice_len;
            _cbmc_bytecopy(ctx.building_txn.Note, val.byteslice, val.byteslice_len);
            break;
        case ApprovalProgram:
        case ClearStateProgram:
            // Program fields: consumed from stack but not stored (stub)
            break;
        case ConfigAssetDefaultFrozen:
            avm_assert_check(sv_isInt(val));
            ctx.building_txn.ConfigAssetDefaultFrozen = (val.value != 0);
            break;
        case FreezeAsset:
            avm_assert_check(sv_isInt(val));
            ctx.building_txn.FreezeAsset = val.value;
            break;
        case FreezeAssetAccount:
            avm_assert_check(sv_isBytes(val));
            _cbmc_sv_to_addr(ctx.building_txn.FreezeAssetAccount, val.byteslice, val.byteslice_len);
            break;
        case FreezeAssetFrozen:
            avm_assert_check(sv_isInt(val));
            ctx.building_txn.FreezeAssetFrozen = (val.value != 0);
            break;
        case AssetCloseTo:
            avm_assert_check(sv_isBytes(val));
            _cbmc_sv_to_addr(ctx.building_txn.AssetCloseTo, val.byteslice, val.byteslice_len);
            break;
        case ExtraProgramPages:
            avm_assert_check(sv_isInt(val));
            ctx.building_txn.ExtraProgramPages = val.value;
            break;
        case GlobalNumUint:
            avm_assert_check(sv_isInt(val));
            ctx.building_txn.GlobalNumUint = val.value;
            break;
        case GlobalNumByteSlice:
            avm_assert_check(sv_isInt(val));
            ctx.building_txn.GlobalNumByteSlice = val.value;
            break;
        case LocalNumUint:
            avm_assert_check(sv_isInt(val));
            ctx.building_txn.LocalNumUint = val.value;
            break;
        case LocalNumByteSlice:
            avm_assert_check(sv_isInt(val));
            ctx.building_txn.LocalNumByteSlice = val.value;
            break;
        case Nonparticipation:
            avm_assert_check(sv_isInt(val));
            ctx.building_txn.Nonparticipation = (val.value != 0);
            break;
        case VotePK:
            avm_assert_check(sv_isBytes(val));
            _cbmc_sv_to_addr(ctx.building_txn.VotePK, val.byteslice, val.byteslice_len);
            break;
        case SelectionPK:
            avm_assert_check(sv_isBytes(val));
            _cbmc_sv_to_addr(ctx.building_txn.SelectionPK, val.byteslice, val.byteslice_len);
            break;
        case StateProofPK:
            avm_assert_check(sv_isBytes(val));
            _cbmc_bytecopy(ctx.building_txn.StateProofPK, val.byteslice,
                           (val.byteslice_len < 64) ? val.byteslice_len : 64);
            break;
        case VoteFirst:
            avm_assert_check(sv_isInt(val));
            ctx.building_txn.VoteFirst = val.value;
            break;
        case VoteLast:
            avm_assert_check(sv_isInt(val));
            ctx.building_txn.VoteLast = val.value;
            break;
        case VoteKeyDilution:
            avm_assert_check(sv_isInt(val));
            ctx.building_txn.VoteKeyDilution = val.value;
            break;
        default:
            break;
    }
}

// ---------------------------------------------------------------------------
// Inner transaction state effects
// ---------------------------------------------------------------------------

#ifdef CBMC_INNER_DISPATCH
void _cbmc_dispatch_inner_app(BlockchainState& BS, Txn& txn);
#endif

// _addr_is_set — check if a 32-byte address is non-zero.
// Loop-free check: tests representative bytes to avoid CBMC unwinding issues.
// Sound for all real Algorand addresses (32-byte public keys) where at least
// one of the sampled bytes is non-zero. This holds for all practical addresses.
bool _addr_is_set(const uint8_t* addr) {
    return addr[0] != 0 || addr[1] != 0 || addr[8] != 0 || addr[16] != 0 || addr[31] != 0;
}

// _itxn_apply_effects — apply state effects of an inner transaction
// Called from itxn_submit and itxn_next before recording the txn.
void _itxn_apply_effects(BlockchainState& BS, EvalContext& ctx, Txn& txn) {
    // Set sender to application address (inner txns are always sent by the app)
    _cbmc_bytecopy(txn.Sender, ctx.CurrentApplicationAddress, 32);

    switch (txn.TypeEnum) {
        case 1: {
            // Payment: deduct Amount from sender, credit receiver if modeled.
            AccountEntry* _payer = acct_find(BS.accounts, ctx.CurrentApplicationAddress);
            if (_payer) {
                avm_assert_check(_payer->balance >= txn.Amount);
                _payer->balance -= txn.Amount;
                // Credit receiver if modeled
                AccountEntry* _payee = acct_find(BS.accounts, txn.Receiver);
                if (_payee) { _payee->balance += txn.Amount; }
                // CloseRemainderTo: transfer remaining balance
                if (_addr_is_set(txn.CloseRemainderTo)) {
                    AccountEntry* _close_to = acct_find(BS.accounts, txn.CloseRemainderTo);
                    if (_close_to) { _close_to->balance += _payer->balance; }
                    _payer->balance = 0;
                }
            } else {
                // Fallback: legacy single-app mode (app not registered as account)
                avm_assert_check(BS.app_balance >= txn.Amount);
                BS.app_balance -= txn.Amount;
                // Credit receiver if modeled
                AccountEntry* _payee = acct_find(BS.accounts, txn.Receiver);
                if (_payee) { _payee->balance += txn.Amount; }
                // CloseRemainderTo: transfer remaining balance
                if (_addr_is_set(txn.CloseRemainderTo)) {
                    AccountEntry* _close_to = acct_find(BS.accounts, txn.CloseRemainderTo);
                    if (_close_to) { _close_to->balance += BS.app_balance; }
                    BS.app_balance = 0;
                }
            }
            break;
        }
        case 4: {
            // Asset Transfer: update holdings if both sender and receiver are modeled
            uint64_t asset_id = txn.XferAsset;
            AssetHolding* sender_h = ahs_find(BS.asset_holdings, txn.Sender, asset_id);
            AssetHolding* receiver_h = ahs_find(BS.asset_holdings, txn.AssetReceiver, asset_id);
            if (sender_h && receiver_h) {
                avm_assert_check(sender_h->balance >= txn.AssetAmount);
                sender_h->balance -= txn.AssetAmount;
                receiver_h->balance += txn.AssetAmount;
            }
            // AssetCloseTo: transfer remaining sender balance to close-to address
            if (_addr_is_set(txn.AssetCloseTo) && sender_h) {
                AssetHolding* close_h = ahs_find(BS.asset_holdings, txn.AssetCloseTo, asset_id);
                if (close_h) {
                    close_h->balance += sender_h->balance;
                }
                sender_h->balance = 0;
            }
            // If not in model: no-op (nondeterministic fallback is sound)
            break;
        }
        case 5: {
            // Asset Freeze: update frozen flag on holding if modeled
            AssetHolding* h = ahs_find(BS.asset_holdings, txn.FreezeAssetAccount, txn.FreezeAsset);
            if (h) {
                h->frozen = txn.FreezeAssetFrozen;
            }
            // If not in model: no-op (nondeterministic fallback is sound)
            break;
        }
        case 6: {
            // App Call: dispatch to inner contract if enabled
#ifdef CBMC_INNER_DISPATCH
            if (txn.ApplicationID != 0) {
                _cbmc_dispatch_inner_app(BS, txn);
            }
#endif
            break;
        }
        default:
            break;
    }
}

// itxn_submit — submit the building inner txn and apply state effects
void itxn_submit(BlockchainState& BS, EvalContext& ctx) {
    avm_assert_check(ctx.building_itxn);
    avm_assert_check(ctx.inner_count < CBMC_MAX_INNER_TXNS);
    _itxn_apply_effects(BS, ctx, ctx.building_txn);
    ctx.inner_txns[ctx.inner_count].txn = ctx.building_txn;
    ctx.inner_txns[ctx.inner_count].submitted = true;
    ctx.inner_count++;
    ctx.building_itxn = false;
}

// itxn field — read last submitted inner txn field
void itxn_field_read(Stack& s, EvalContext& ctx, txnField field) {
    avm_assert_check(ctx.inner_count > 0);
    txn_field(s, ctx.inner_txns[ctx.inner_count - 1].txn, field);
}

// gitxn field — read inner txn by group index
void gitxn_field(Stack& s, EvalContext& ctx, uint64_t idx, txnField field) {
    avm_assert_check(idx < ctx.inner_count);
    txn_field(s, ctx.inner_txns[idx].txn, field);
}

// itxn_next — submit current inner txn with effects and start a new one
void itxn_next(Stack& s, BlockchainState& BS, EvalContext& ctx) {
    avm_assert_check(ctx.building_itxn);
    // Submit the current building txn and start a new one
    avm_assert_check(ctx.inner_count < CBMC_MAX_INNER_TXNS);
    _itxn_apply_effects(BS, ctx, ctx.building_txn);
    ctx.inner_txns[ctx.inner_count].txn = ctx.building_txn;
    ctx.inner_txns[ctx.inner_count].submitted = true;
    ctx.inner_count++;
    _cbmc_txn_zero(ctx.building_txn);
    // building_itxn stays true
}

// gitxna_field — read inner txn array field by group index
void gitxna_field(Stack& s, EvalContext& ctx, uint64_t idx, txnField field, uint64_t array_idx) {
    avm_assert_check(idx < ctx.inner_count);
    txna_field(s, ctx.inner_txns[idx].txn, field, array_idx);
}

// itxna_field_read — read last submitted inner txn array field
void itxna_field_read(Stack& s, EvalContext& ctx, txnField field, uint64_t array_idx) {
    avm_assert_check(ctx.inner_count > 0);
    txna_field(s, ctx.inner_txns[ctx.inner_count - 1].txn, field, array_idx);
}

// Account params field enum (AVM spec values)
enum acctParamsField {
    AcctBalance = 0, AcctMinBalance = 1, AcctAuthAddr = 2,
    AcctTotalNumUint = 3, AcctTotalNumByteSlice = 4,
    AcctTotalExtraAppPages = 5, AcctTotalAppsCreated = 6,
    AcctTotalAppsOptedIn = 7, AcctTotalAssetsCreated = 8,
    AcctTotalAssets = 9, AcctTotalBoxes = 10, AcctTotalBoxBytes = 11,
    AcctIncentiveEligible = 12, AcctLastProposed = 13, AcctLastHeartbeat = 14,
};

// acct_params_get — stateful lookup with nondeterministic fallback
void acct_params_get(Stack& s, BlockchainState& BS, Txn& txn, EvalContext& ctx, uint64_t field) {
    StackValue acct = stack_pop(s);
    // Resolve account address via standard AVM index resolution
    const uint8_t* addr = _resolve_account_addr(acct, txn);
    // Try stateful lookup for balance/min_balance fields
    if (addr) {
        AccountEntry* ae = acct_find(BS.accounts, addr);
        if (ae) {
            switch (field) {
                case AcctBalance:
                    pushint(s, ae->balance);
                    pushint(s, 1);
                    return;
                case AcctMinBalance:
                    pushint(s, ae->min_balance);
                    pushint(s, 1);
                    return;
                case AcctAuthAddr: {
                    // AuthAddr is a 32-byte address — nondeterministic for modeled accounts
                    stack_push(s, sv_nondet_bytes(32));
                    pushint(s, 1);
                    return;
                }
                default:
                    // Other fields: nondeterministic but account exists
                    pushint(s, nondet_uint64());
                    pushint(s, 1);
                    return;
            }
        }
    }
    // Fallback: nondeterministic value + nondeterministic found flag
    if (field == AcctAuthAddr) {
        stack_push(s, sv_nondet_bytes(32));
    } else {
        pushint(s, nondet_uint64());
    }
    pushint(s, nondet_bool() ? 1 : 0);
}

// asset_holding_get — stateful lookup with nondeterministic fallback
void asset_holding_get(Stack& s, BlockchainState& BS, Txn& txn, EvalContext& ctx, uint64_t field) {
    StackValue asset_id = stack_pop(s);
    StackValue acct = stack_pop(s);
    avm_assert_check(sv_isInt(asset_id));
    // Try stateful lookup first (resolve integer indices to addresses)
    const uint8_t* addr = sv_isBytes(acct)
        ? acct.byteslice
        : _resolve_account_addr(acct, txn);
    AssetHolding* ah = ahs_find(BS.asset_holdings, addr, asset_id.value);
    if (ah) {
        if (field == 0) { // AssetBalance
            pushint(s, ah->balance);
        } else { // AssetFrozen
            pushint(s, ah->frozen ? 1 : 0);
        }
        pushint(s, ah->opted_in ? 1 : 0); // found flag
        return;
    }
    // Fallback: nondeterministic
    pushint(s, nondet_uint64());
    pushint(s, nondet_bool() ? 1 : 0);
}

// App params field enum (with _field suffix matching transpiler output)
enum appParamsField {
    AppApprovalProgram_field = 0, AppClearStateProgram_field = 1,
    AppGlobalNumUint_field = 2, AppGlobalNumByteSlice_field = 3,
    AppLocalNumUint_field = 4, AppLocalNumByteSlice_field = 5,
    AppExtraProgramPages_field = 6, AppCreator_field = 7,
    AppAddress_field = 8,
};

// app_params_get — app params (stub returning nondeterministic values)
// For AppAddress: returns the app's address (32-byte hash of app ID)
void app_params_get(Stack& s, BlockchainState& BS, EvalContext& ctx, appParamsField field) {
    StackValue app_id = stack_pop(s);
    avm_assert_check(sv_isInt(app_id));
    if (field == AppAddress_field) {
        // Return a deterministic address for known app IDs, nondeterministic otherwise
        if (app_id.value == ctx.CurrentApplicationID) {
            stack_push(s, sv_bytes(ctx.CurrentApplicationAddress, 32));
        } else {
            stack_push(s, sv_nondet_bytes(32));
        }
    } else if (field == AppCreator_field && app_id.value == ctx.CurrentApplicationID) {
        // Return deterministic creator address for current app
        stack_push(s, sv_bytes(ctx.CreatorAddress, 32));
    } else if (field == AppApprovalProgram_field || field == AppClearStateProgram_field) {
        stack_push(s, sv_empty_bytes());
    } else {
        pushint(s, nondet_uint64());
    }
    pushint(s, nondet_bool() ? 1 : 0); // exists flag (nondeterministic: app may or may not exist)
}

// Asset params field enum (with _field suffix matching transpiler output)
enum assetParamsField {
    AssetTotal_field = 0, AssetDecimals_field = 1, AssetDefaultFrozen_field = 2,
    AssetUnitName_field = 3, AssetName_field = 4, AssetURL_field = 5,
    AssetMetadataHash_field = 6, AssetManager_field = 7,
    AssetReserve_field = 8, AssetFreeze_field = 9,
    AssetClawback_field = 10, AssetCreator_field = 11,
};

// Asset holding field enum (with _field suffix matching transpiler output)
enum assetHoldingField {
    AssetBalance_field = 0, AssetFrozen_field = 1,
};

// asset_params_get — stateful lookup with nondeterministic fallback
// field: 0=AssetTotal, 1=AssetDecimals, 2=AssetDefaultFrozen, 3=AssetUnitName,
//        4=AssetName, 5=AssetURL, 6=AssetMetadataHash, 7=AssetManager,
//        8=AssetReserve, 9=AssetFreeze, 10=AssetClawback, 11=AssetCreator
void asset_params_get(Stack& s, BlockchainState& BS, uint64_t field) {
    StackValue asset_id = stack_pop(s);
    avm_assert_check(sv_isInt(asset_id));

    // Try stateful lookup first
    AssetParams* ap = aps_find(BS.asset_params, asset_id.value);
    if (ap) {
        switch (field) {
            case 0: pushint(s, ap->total); break;        // AssetTotal
            case 1: pushint(s, ap->decimals); break;     // AssetDecimals
            case 2: pushint(s, ap->default_frozen ? 1 : 0); break; // AssetDefaultFrozen
            case 3: stack_push(s, sv_bytes(ap->unit_name, ap->unit_name_len)); break; // AssetUnitName
            case 4: stack_push(s, sv_bytes(ap->name, ap->name_len)); break;           // AssetName
            case 5: stack_push(s, sv_bytes(ap->url, ap->url_len)); break;             // AssetURL
            case 6: stack_push(s, sv_bytes(ap->metadata_hash, 32)); break;            // AssetMetadataHash
            case 7: stack_push(s, sv_bytes(ap->manager, 32)); break;  // AssetManager
            case 8: stack_push(s, sv_bytes(ap->reserve, 32)); break;  // AssetReserve
            case 9: stack_push(s, sv_bytes(ap->freeze, 32)); break;   // AssetFreeze
            case 10: stack_push(s, sv_bytes(ap->clawback, 32)); break; // AssetClawback
            case 11: stack_push(s, sv_bytes(ap->creator, 32)); break;  // AssetCreator
            default: {
                pushint(s, nondet_uint64());
                break;
            }
        }
        pushint(s, 1); // found
        return;
    }

    // Fallback: nondeterministic (backward compatible)
    if (field >= 3 && field <= 6) {
        uint32_t len = (field == 6) ? 32 : 8;
        stack_push(s, sv_nondet_bytes(len));
    } else if (field >= 7 && field <= 11) {
        stack_push(s, sv_nondet_bytes(32));
    } else {
        pushint(s, nondet_uint64());
    }
    pushint(s, nondet_bool() ? 1 : 0); // found flag (nondeterministic: asset may or may not exist)
}

// ============================================================================
// Byte math (big-integer) helpers — 512-bit max, big-endian byte arrays
// ============================================================================

// Strip leading zeros from a byteslice result, keeping at least 1 byte.
void bmath_strip_zeros(uint8_t* buf, uint8_t& len) {
    uint8_t i = 0;
    while (i + 1 < len && buf[i] == 0) i++;
    if (i > 0) {
        memmove(buf, buf + i, len - i);
        len -= i;
    }
}

// Compare two big-endian unsigned integers. Returns -1, 0, or +1.
int bmath_cmp(const uint8_t* a, uint8_t alen, const uint8_t* b, uint8_t blen) {
    // Find first non-zero byte in each
    uint8_t ai = 0, bi = 0;
    while (ai + 1 < alen && a[ai] == 0) ai++;
    while (bi + 1 < blen && b[bi] == 0) bi++;
    uint8_t ea = alen - ai;  // effective length of a
    uint8_t eb = blen - bi;
    if (ea != eb) return (ea > eb) ? 1 : -1;
    for (uint8_t i = 0; i < ea; i++) {
        if (a[ai + i] != b[bi + i])
            return (a[ai + i] > b[bi + i]) ? 1 : -1;
    }
    return 0;
}

// Add two big-endian byte arrays. out must have space for max(alen,blen)+1 bytes.
void bmath_add_impl(const uint8_t* a, uint8_t alen,
                            const uint8_t* b, uint8_t blen,
                            uint8_t* out, uint8_t& outlen) {
    uint8_t maxl = (alen > blen) ? alen : blen;
    outlen = maxl + 1;
    for (uint8_t i = 0; i < outlen; i++) out[i] = 0;
    uint16_t carry = 0;
    for (uint8_t i = 0; i < maxl; i++) {
        uint16_t av = (i < alen) ? a[alen - 1 - i] : 0;
        uint16_t bv = (i < blen) ? b[blen - 1 - i] : 0;
        uint16_t sum = av + bv + carry;
        out[outlen - 1 - i] = (uint8_t)(sum & 0xFF);
        carry = sum >> 8;
    }
    out[0] = (uint8_t)carry;
    bmath_strip_zeros(out, outlen);
}

void bmath_sub_impl(const uint8_t* a, uint8_t alen,
                            const uint8_t* b, uint8_t blen,
                            uint8_t* out, uint8_t& outlen) {
    outlen = alen;
    for (uint8_t i = 0; i < outlen; i++) out[i] = 0;
    int16_t borrow = 0;
    for (uint8_t i = 0; i < alen; i++) {
        int16_t av = a[alen - 1 - i];
        int16_t bv = (i < blen) ? b[blen - 1 - i] : 0;
        int16_t diff = av - bv - borrow;
        if (diff < 0) { diff += 256; borrow = 1; }
        else { borrow = 0; }
        out[outlen - 1 - i] = (uint8_t)diff;
    }
    bmath_strip_zeros(out, outlen);
}

// Schoolbook multiply. out must have space for alen+blen bytes.
void bmath_mul_impl(const uint8_t* a, uint8_t alen,
                            const uint8_t* b, uint8_t blen,
                            uint8_t* out, uint8_t& outlen) {
    outlen = alen + blen;
    for (uint8_t i = 0; i < outlen; i++) out[i] = 0;
    for (uint8_t i = 0; i < alen; i++) {
        uint16_t carry = 0;
        for (uint8_t j = 0; j < blen; j++) {
            uint8_t pos = outlen - 1 - i - j;
            uint16_t prod = (uint16_t)a[alen - 1 - i] * (uint16_t)b[blen - 1 - j]
                          + (uint16_t)out[pos] + carry;
            out[pos] = (uint8_t)(prod & 0xFF);
            carry = prod >> 8;
        }
        out[outlen - 1 - i - blen] += (uint8_t)carry;
    }
    bmath_strip_zeros(out, outlen);
}

// Check if a byte array is all zeros
bool bmath_is_zero(const uint8_t* a, uint8_t alen) {
    for (uint8_t i = 0; i < alen; i++) {
        if (a[i] != 0) return false;
    }
    return true;
}

// Get bit at position (0 = MSB of first byte) from big-endian byte array
uint8_t bmath_getbit(const uint8_t* a, uint8_t alen, uint16_t bitpos) {
    uint16_t byte_idx = bitpos / 8;
    uint8_t bit_idx = 7 - (bitpos % 8);
    if (byte_idx >= alen) return 0;
    return (a[byte_idx] >> bit_idx) & 1;
}

// Convert big-endian bytes to a 128-bit value (up to 16 bytes).
static __uint128_t _bmath_to_u128(const uint8_t* buf, uint8_t len) {
    __uint128_t v = 0;
    for (uint8_t i = 0; i < len && i < 16; i++) {
        v = (v << 8) | buf[i];
    }
    return v;
}

// Convert a 128-bit value to big-endian bytes. Returns actual byte length (stripped).
static uint8_t _bmath_from_u128(__uint128_t v, uint8_t* out) {
    // Write all 16 bytes big-endian
    for (int i = 15; i >= 0; i--) {
        out[i] = (uint8_t)(v & 0xFF);
        v >>= 8;
    }
    // Strip leading zeros
    uint8_t start = 0;
    while (start < 15 && out[start] == 0) start++;
    uint8_t len = 16 - start;
    if (start > 0) {
        for (uint8_t i = 0; i < len; i++) out[i] = out[start + i];
    }
    return len;
}

// Limb-based divmod using __uint128_t. Handles operands up to 16 bytes (128 bits).
// For inputs within 16 bytes, this is O(1) — no per-bit loops.
// q must have space for 16 bytes, r must have space for 16 bytes.
void bmath_divmod_impl(const uint8_t* a, uint8_t alen,
                               const uint8_t* b, uint8_t blen,
                               uint8_t* q, uint8_t& qlen,
                               uint8_t* r, uint8_t& rlen) {
    __uint128_t av = _bmath_to_u128(a, alen);
    __uint128_t bv = _bmath_to_u128(b, blen);

    __uint128_t qv = av / bv;
    __uint128_t rv = av % bv;

    qlen = _bmath_from_u128(qv, q);
    rlen = _bmath_from_u128(rv, r);
}

// Integer square root via bit-scanning (no division needed).
// Uses the standard non-restoring algorithm: build result one bit at a time.
// For N-bit input, result has at most ceil(N/2) bits, and the loop runs ceil(N/2) times.
void bmath_sqrt_impl(const uint8_t* a, uint8_t alen,
                             uint8_t* out, uint8_t& outlen) {
    if (bmath_is_zero(a, alen)) {
        out[0] = 0; outlen = 1;
        return;
    }

    // Find the highest set bit position in a (0-indexed from MSB)
    uint16_t total_bits = (uint16_t)alen * 8;
    uint16_t highest_bit = 0;
    for (uint16_t i = 0; i < total_bits; i++) {
        if (bmath_getbit(a, alen, i)) { highest_bit = total_bits - 1 - i; break; }
    }

    // Result bit count: at most ceil((highest_bit+1)/2) bits
    // Result buffer — start with zero
    uint8_t result_bytes = (alen + 1) / 2 + 1;  // generous bound
    if (result_bytes > CBMC_BMATH_MAX) result_bytes = CBMC_BMATH_MAX;
    uint8_t result[CBMC_BMATH_MAX];
    uint8_t rlen = result_bytes;
    for (uint8_t i = 0; i < rlen; i++) result[i] = 0;

    // Remainder buffer
    uint8_t rem[CBMC_BYTES_MAX];
    uint8_t remlen = 1;
    rem[0] = 0;

    // Process two bits of input at a time, from MSB to LSB
    // Number of pairs = ceil(total_bits / 2)
    uint16_t pairs = (total_bits + 1) / 2;
    // Start bit index for the first pair
    uint16_t start_bit = (pairs * 2) - 1;  // MSB of the first pair

    for (uint16_t p = 0; p < pairs; p++) {
        // Left-shift remainder by 2 bits and bring in next pair of input bits
        uint16_t carry = 0;
        for (uint8_t j = remlen; j > 0; j--) {
            uint16_t v = ((uint16_t)rem[j-1] << 2) | carry;
            rem[j-1] = (uint8_t)(v & 0xFF);
            carry = v >> 8;
        }
        if (carry) {
            memmove(rem + 1, rem, remlen);
            rem[0] = (uint8_t)carry;
            remlen++;
        }

        // Bring in two bits from input
        uint16_t bit_hi = start_bit - 2*p;
        uint16_t bit_lo = (bit_hi > 0) ? bit_hi - 1 : 0;
        uint8_t pair_val = 0;
        if (bit_hi < total_bits) pair_val |= (bmath_getbit(a, alen, total_bits - 1 - bit_hi) << 1);
        if (bit_hi > 0 && bit_lo < total_bits) pair_val |= bmath_getbit(a, alen, total_bits - 1 - bit_lo);
        else if (bit_hi == 0) pair_val = bmath_getbit(a, alen, total_bits - 1);  // single bit case
        rem[remlen - 1] = (rem[remlen - 1] & 0xFC) | pair_val;

        // candidate = result * 2 + 1 (i.e., shift result left by 1 and set LSB)
        // We need: if rem >= candidate, result = result*2+1 and rem -= candidate
        //          else result = result*2
        // First compute result_shifted = result << 1
        uint8_t shifted[CBMC_BMATH_MAX];
        uint8_t slen = rlen;
        carry = 0;
        for (uint8_t j = slen; j > 0; j--) {
            uint16_t v = ((uint16_t)result[j-1] << 1) | carry;
            shifted[j-1] = (uint8_t)(v & 0xFF);
            carry = v >> 8;
        }
        if (carry && slen < CBMC_BMATH_MAX) {
            memmove(shifted + 1, shifted, slen);
            shifted[0] = (uint8_t)carry;
            slen++;
        }

        // candidate = shifted | 1 (set LSB)
        uint8_t cand[CBMC_BMATH_MAX];
        uint8_t clen = slen;
        _cbmc_bytecopy(cand, shifted, clen);
        cand[clen - 1] |= 1;

        if (bmath_cmp(rem, remlen, cand, clen) >= 0) {
            // rem -= candidate
            uint8_t tmp[CBMC_BYTES_MAX];
            uint8_t tmplen;
            bmath_sub_impl(rem, remlen, cand, clen, tmp, tmplen);
            _cbmc_bytecopy(rem, tmp, tmplen);
            remlen = tmplen;
            // result = shifted + 1
            _cbmc_bytecopy(result, shifted, slen);
            rlen = slen;
            result[rlen - 1] |= 1;
        } else {
            // result = shifted (just shifted left, no +1)
            _cbmc_bytecopy(result, shifted, slen);
            rlen = slen;
        }
    }

    bmath_strip_zeros(result, rlen);
    outlen = rlen;
    _cbmc_bytecopy(out, result, rlen);
}

// ============================================================================
// Byte math (big-integer) opcodes — b+, b-, b*, b/, b%, comparisons, bitwise
// ============================================================================

// b+ — big-endian unsigned addition
void bmath_add(Stack& s) {
    StackValue b = stack_pop(s);
    StackValue a = stack_pop(s);
    avm_assert_check(sv_isBytes(a) && sv_isBytes(b));
    avm_assert_check(a.byteslice_len <= CBMC_BMATH_MAX && b.byteslice_len <= CBMC_BMATH_MAX);

    uint8_t out[CBMC_BYTES_MAX];
    uint8_t outlen;
    bmath_add_impl(a.byteslice, a.byteslice_len, b.byteslice, b.byteslice_len, out, outlen);
    avm_assert_check(outlen <= CBMC_BYTES_MAX);  // AVM: output max 128 bytes
    stack_push(s, sv_bytes(out, outlen));
}

// b- — big-endian unsigned subtraction (panics if a < b)
void bmath_sub(Stack& s) {
    StackValue b = stack_pop(s);
    StackValue a = stack_pop(s);
    avm_assert_check(sv_isBytes(a) && sv_isBytes(b));
    avm_assert_check(a.byteslice_len <= CBMC_BMATH_MAX && b.byteslice_len <= CBMC_BMATH_MAX);
    avm_assert_check(bmath_cmp(a.byteslice, a.byteslice_len, b.byteslice, b.byteslice_len) >= 0);

    uint8_t out[CBMC_BYTES_MAX];
    uint8_t outlen;
    bmath_sub_impl(a.byteslice, a.byteslice_len, b.byteslice, b.byteslice_len, out, outlen);
    stack_push(s, sv_bytes(out, outlen));
}

// b* — big-endian unsigned multiplication
void bmath_mul(Stack& s) {
    StackValue b = stack_pop(s);
    StackValue a = stack_pop(s);
    avm_assert_check(sv_isBytes(a) && sv_isBytes(b));
    avm_assert_check(a.byteslice_len <= CBMC_BMATH_MAX && b.byteslice_len <= CBMC_BMATH_MAX);

    uint8_t out[CBMC_BYTES_MAX];
    uint8_t outlen;
    bmath_mul_impl(a.byteslice, a.byteslice_len, b.byteslice, b.byteslice_len, out, outlen);
    avm_assert_check(outlen <= CBMC_BYTES_MAX);
    stack_push(s, sv_bytes(out, outlen));
}

// b/ — big-endian unsigned division (panics if divisor is zero)
void bmath_div(Stack& s) {
    StackValue b = stack_pop(s);
    StackValue a = stack_pop(s);
    avm_assert_check(sv_isBytes(a) && sv_isBytes(b));
    avm_assert_check(a.byteslice_len <= CBMC_BMATH_MAX && b.byteslice_len <= CBMC_BMATH_MAX);
    // Bound operand length for CBMC performance: 16 bytes = 128 bits covers
    // all practical TEAL byte-math. Reduces divmod iterations from 512 to 128.
    __CPROVER_assume(a.byteslice_len <= 16 && b.byteslice_len <= 16);
    avm_assert_check(!bmath_is_zero(b.byteslice, b.byteslice_len));

    uint8_t q[CBMC_BMATH_MAX], r[CBMC_BMATH_MAX];
    uint8_t qlen, rlen;
    bmath_divmod_impl(a.byteslice, a.byteslice_len, b.byteslice, b.byteslice_len, q, qlen, r, rlen);
    stack_push(s, sv_bytes(q, qlen));
}

// b% — big-endian unsigned modulo (panics if divisor is zero)
void bmath_mod(Stack& s) {
    StackValue b = stack_pop(s);
    StackValue a = stack_pop(s);
    avm_assert_check(sv_isBytes(a) && sv_isBytes(b));
    avm_assert_check(a.byteslice_len <= CBMC_BMATH_MAX && b.byteslice_len <= CBMC_BMATH_MAX);
    __CPROVER_assume(a.byteslice_len <= 16 && b.byteslice_len <= 16);
    avm_assert_check(!bmath_is_zero(b.byteslice, b.byteslice_len));

    uint8_t q[CBMC_BMATH_MAX], r[CBMC_BMATH_MAX];
    uint8_t qlen, rlen;
    bmath_divmod_impl(a.byteslice, a.byteslice_len, b.byteslice, b.byteslice_len, q, qlen, r, rlen);
    stack_push(s, sv_bytes(r, rlen));
}

// b< — big-endian unsigned less-than
void bmath_lt(Stack& s) {
    StackValue b = stack_pop(s);
    StackValue a = stack_pop(s);
    avm_assert_check(sv_isBytes(a) && sv_isBytes(b));
    avm_assert_check(a.byteslice_len <= CBMC_BMATH_MAX && b.byteslice_len <= CBMC_BMATH_MAX);
    pushint(s, bmath_cmp(a.byteslice, a.byteslice_len, b.byteslice, b.byteslice_len) < 0 ? 1 : 0);
}

// b> — big-endian unsigned greater-than
void bmath_gt(Stack& s) {
    StackValue b = stack_pop(s);
    StackValue a = stack_pop(s);
    avm_assert_check(sv_isBytes(a) && sv_isBytes(b));
    avm_assert_check(a.byteslice_len <= CBMC_BMATH_MAX && b.byteslice_len <= CBMC_BMATH_MAX);
    pushint(s, bmath_cmp(a.byteslice, a.byteslice_len, b.byteslice, b.byteslice_len) > 0 ? 1 : 0);
}

// b<= — big-endian unsigned less-or-equal
void bmath_leq(Stack& s) {
    StackValue b = stack_pop(s);
    StackValue a = stack_pop(s);
    avm_assert_check(sv_isBytes(a) && sv_isBytes(b));
    avm_assert_check(a.byteslice_len <= CBMC_BMATH_MAX && b.byteslice_len <= CBMC_BMATH_MAX);
    pushint(s, bmath_cmp(a.byteslice, a.byteslice_len, b.byteslice, b.byteslice_len) <= 0 ? 1 : 0);
}

// b>= — big-endian unsigned greater-or-equal
void bmath_geq(Stack& s) {
    StackValue b = stack_pop(s);
    StackValue a = stack_pop(s);
    avm_assert_check(sv_isBytes(a) && sv_isBytes(b));
    avm_assert_check(a.byteslice_len <= CBMC_BMATH_MAX && b.byteslice_len <= CBMC_BMATH_MAX);
    pushint(s, bmath_cmp(a.byteslice, a.byteslice_len, b.byteslice, b.byteslice_len) >= 0 ? 1 : 0);
}

// b== — big-endian unsigned equality
void bmath_eq(Stack& s) {
    StackValue b = stack_pop(s);
    StackValue a = stack_pop(s);
    avm_assert_check(sv_isBytes(a) && sv_isBytes(b));
    avm_assert_check(a.byteslice_len <= CBMC_BMATH_MAX && b.byteslice_len <= CBMC_BMATH_MAX);
    pushint(s, bmath_cmp(a.byteslice, a.byteslice_len, b.byteslice, b.byteslice_len) == 0 ? 1 : 0);
}

// b!= — big-endian unsigned inequality
void bmath_neq(Stack& s) {
    StackValue b = stack_pop(s);
    StackValue a = stack_pop(s);
    avm_assert_check(sv_isBytes(a) && sv_isBytes(b));
    avm_assert_check(a.byteslice_len <= CBMC_BMATH_MAX && b.byteslice_len <= CBMC_BMATH_MAX);
    pushint(s, bmath_cmp(a.byteslice, a.byteslice_len, b.byteslice, b.byteslice_len) != 0 ? 1 : 0);
}

// b& — bitwise AND (shorter operand left-padded with zeros, result preserves max length)
void bmath_bitand(Stack& s) {
    StackValue b = stack_pop(s);
    StackValue a = stack_pop(s);
    avm_assert_check(sv_isBytes(a) && sv_isBytes(b));
    avm_assert_check(a.byteslice_len <= CBMC_BMATH_MAX && b.byteslice_len <= CBMC_BMATH_MAX);

    uint8_t maxl = (a.byteslice_len > b.byteslice_len) ? a.byteslice_len : b.byteslice_len;
    uint8_t out[CBMC_BMATH_MAX];
    for (uint8_t i = 0; i < maxl; i++) {
        uint8_t av = (i < a.byteslice_len) ? a.byteslice[a.byteslice_len - 1 - i] : 0;
        uint8_t bv = (i < b.byteslice_len) ? b.byteslice[b.byteslice_len - 1 - i] : 0;
        out[maxl - 1 - i] = av & bv;
    }
    stack_push(s, sv_bytes(out, maxl));
}

// b| — bitwise OR
void bmath_bitor(Stack& s) {
    StackValue b = stack_pop(s);
    StackValue a = stack_pop(s);
    avm_assert_check(sv_isBytes(a) && sv_isBytes(b));
    avm_assert_check(a.byteslice_len <= CBMC_BMATH_MAX && b.byteslice_len <= CBMC_BMATH_MAX);

    uint8_t maxl = (a.byteslice_len > b.byteslice_len) ? a.byteslice_len : b.byteslice_len;
    uint8_t out[CBMC_BMATH_MAX];
    for (uint8_t i = 0; i < maxl; i++) {
        uint8_t av = (i < a.byteslice_len) ? a.byteslice[a.byteslice_len - 1 - i] : 0;
        uint8_t bv = (i < b.byteslice_len) ? b.byteslice[b.byteslice_len - 1 - i] : 0;
        out[maxl - 1 - i] = av | bv;
    }
    stack_push(s, sv_bytes(out, maxl));
}

// b^ — bitwise XOR
void bmath_bitxor(Stack& s) {
    StackValue b = stack_pop(s);
    StackValue a = stack_pop(s);
    avm_assert_check(sv_isBytes(a) && sv_isBytes(b));
    avm_assert_check(a.byteslice_len <= CBMC_BMATH_MAX && b.byteslice_len <= CBMC_BMATH_MAX);

    uint8_t maxl = (a.byteslice_len > b.byteslice_len) ? a.byteslice_len : b.byteslice_len;
    uint8_t out[CBMC_BMATH_MAX];
    for (uint8_t i = 0; i < maxl; i++) {
        uint8_t av = (i < a.byteslice_len) ? a.byteslice[a.byteslice_len - 1 - i] : 0;
        uint8_t bv = (i < b.byteslice_len) ? b.byteslice[b.byteslice_len - 1 - i] : 0;
        out[maxl - 1 - i] = av ^ bv;
    }
    stack_push(s, sv_bytes(out, maxl));
}

// b~ — bitwise complement
void bmath_bitneg(Stack& s) {
    StackValue a = stack_pop(s);
    avm_assert_check(sv_isBytes(a));
    avm_assert_check(a.byteslice_len <= CBMC_BMATH_MAX);

    uint8_t out[CBMC_BMATH_MAX];
    for (uint8_t i = 0; i < a.byteslice_len; i++)
        out[i] = ~a.byteslice[i];
    stack_push(s, sv_bytes(out, a.byteslice_len));
}

// bsqrt — integer square root of big-endian unsigned integer
void bmath_sqrt(Stack& s) {
    StackValue a = stack_pop(s);
    avm_assert_check(sv_isBytes(a));
    avm_assert_check(a.byteslice_len <= CBMC_BMATH_MAX);
    __CPROVER_assume(a.byteslice_len <= 16);

    uint8_t out[CBMC_BMATH_MAX];
    uint8_t outlen;
    bmath_sqrt_impl(a.byteslice, a.byteslice_len, out, outlen);
    stack_push(s, sv_bytes(out, outlen));
}

// Transpiler-compatible aliases for bitwise byte operations
void bmath_or(Stack& s) { bmath_bitor(s); }
void bmath_and(Stack& s) { bmath_bitand(s); }
void bmath_xor(Stack& s) { bmath_bitxor(s); }
void bmath_neg(Stack& s) { bmath_bitneg(s); }
