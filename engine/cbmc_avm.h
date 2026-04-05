// cbmc_avm.h — Bounded AVM data structures for CBMC verification.
//
// These mirror the structures in avm/AVMCommon.h but use fixed-size arrays
// instead of STL containers, and avoid constructors (CBMC 5.12 limitation).
// All initialization is done via free functions.

#pragma once

#include <cstdint>
#include <cstring>

// All tunable bounds are in cbmc_bounds.h (with documentation).
// Templates override bounds with #define before including this file.
#include "cbmc_bounds.h"

// ---------------------------------------------------------------------------
// StackValue — dual-typed: either uint64 or byteslice
// ---------------------------------------------------------------------------

struct StackValue {
    uint8_t byteslice[CBMC_BYTES_MAX];
    uint16_t byteslice_len;
    uint64_t value;
    bool _is_bytes;
};

inline StackValue sv_int(uint64_t v) {
    StackValue sv;
    sv.value = v;
    sv._is_bytes = false;
    sv.byteslice_len = 0;
    return sv;
}

// Chunked byte copy for CBMC — 16 bytes per iteration reduces loop count by 16x.
// Standard memcpy uses an internal CBMC loop subject to --unwind; at unwind=25,
// a 32-byte memcpy makes the path infeasible (__CPROVER_assume(false) at i=25).
// This chunked version needs only ceil(len/16) iterations:
//   len=32 → 2 iterations (needs unwind >= 3)
//   len=64 → 4 iterations (needs unwind >= 5)
//   len=128 → 8 iterations (needs unwind >= 9)
inline void _cbmc_bytecopy(uint8_t* dst, const uint8_t* src, uint32_t len) {
    uint32_t i = 0;
    for (; i + 16 <= len; i += 16) {
        dst[i]    = src[i];    dst[i+1]  = src[i+1];
        dst[i+2]  = src[i+2];  dst[i+3]  = src[i+3];
        dst[i+4]  = src[i+4];  dst[i+5]  = src[i+5];
        dst[i+6]  = src[i+6];  dst[i+7]  = src[i+7];
        dst[i+8]  = src[i+8];  dst[i+9]  = src[i+9];
        dst[i+10] = src[i+10]; dst[i+11] = src[i+11];
        dst[i+12] = src[i+12]; dst[i+13] = src[i+13];
        dst[i+14] = src[i+14]; dst[i+15] = src[i+15];
    }
    // Remaining bytes (at most 15, fully unrolled)
    if (i < len) { dst[i] = src[i]; i++; }
    if (i < len) { dst[i] = src[i]; i++; }
    if (i < len) { dst[i] = src[i]; i++; }
    if (i < len) { dst[i] = src[i]; i++; }
    if (i < len) { dst[i] = src[i]; i++; }
    if (i < len) { dst[i] = src[i]; i++; }
    if (i < len) { dst[i] = src[i]; i++; }
    if (i < len) { dst[i] = src[i]; i++; }
    if (i < len) { dst[i] = src[i]; i++; }
    if (i < len) { dst[i] = src[i]; i++; }
    if (i < len) { dst[i] = src[i]; i++; }
    if (i < len) { dst[i] = src[i]; i++; }
    if (i < len) { dst[i] = src[i]; i++; }
    if (i < len) { dst[i] = src[i]; i++; }
    if (i < len) { dst[i] = src[i]; }
}

// Zero a byte array in 16-byte chunks. Same iteration count as _cbmc_bytecopy.
//   len=32 → 2 iterations (needs unwind >= 3)
//   len=64 → 4 iterations (needs unwind >= 5)
//   len=128 → 8 iterations (needs unwind >= 9)
inline void _cbmc_zero(uint8_t* dst, uint32_t len) {
    uint32_t i = 0;
    for (; i + 16 <= len; i += 16) {
        dst[i]    = 0; dst[i+1]  = 0; dst[i+2]  = 0; dst[i+3]  = 0;
        dst[i+4]  = 0; dst[i+5]  = 0; dst[i+6]  = 0; dst[i+7]  = 0;
        dst[i+8]  = 0; dst[i+9]  = 0; dst[i+10] = 0; dst[i+11] = 0;
        dst[i+12] = 0; dst[i+13] = 0; dst[i+14] = 0; dst[i+15] = 0;
    }
    if (i < len) { dst[i] = 0; i++; }
    if (i < len) { dst[i] = 0; i++; }
    if (i < len) { dst[i] = 0; i++; }
    if (i < len) { dst[i] = 0; i++; }
    if (i < len) { dst[i] = 0; i++; }
    if (i < len) { dst[i] = 0; i++; }
    if (i < len) { dst[i] = 0; i++; }
    if (i < len) { dst[i] = 0; i++; }
    if (i < len) { dst[i] = 0; i++; }
    if (i < len) { dst[i] = 0; i++; }
    if (i < len) { dst[i] = 0; i++; }
    if (i < len) { dst[i] = 0; i++; }
    if (i < len) { dst[i] = 0; i++; }
    if (i < len) { dst[i] = 0; i++; }
    if (i < len) { dst[i] = 0; }
}

// Fill a 32-byte address with nondeterministic values using uint64 chunks.
// 4 iterations (needs unwind >= 5) instead of 32 per-byte iterations.
inline void _cbmc_addr_nondet(uint8_t* dst) {
    uint64_t c0 = nondet_uint64(); memcpy(dst,      &c0, 8);
    uint64_t c1 = nondet_uint64(); memcpy(dst + 8,  &c1, 8);
    uint64_t c2 = nondet_uint64(); memcpy(dst + 16, &c2, 8);
    uint64_t c3 = nondet_uint64(); memcpy(dst + 24, &c3, 8);
}

// Chunked byte equality check for CBMC — same rationale as _cbmc_bytecopy.
inline bool _cbmc_byteequal(const uint8_t* a, const uint8_t* b, uint32_t len) {
    uint32_t i = 0;
    for (; i + 16 <= len; i += 16) {
        if (a[i]    != b[i]    || a[i+1]  != b[i+1]  ||
            a[i+2]  != b[i+2]  || a[i+3]  != b[i+3]  ||
            a[i+4]  != b[i+4]  || a[i+5]  != b[i+5]  ||
            a[i+6]  != b[i+6]  || a[i+7]  != b[i+7]  ||
            a[i+8]  != b[i+8]  || a[i+9]  != b[i+9]  ||
            a[i+10] != b[i+10] || a[i+11] != b[i+11] ||
            a[i+12] != b[i+12] || a[i+13] != b[i+13] ||
            a[i+14] != b[i+14] || a[i+15] != b[i+15])
            return false;
    }
    // Remaining bytes (at most 15, fully unrolled)
    if (i < len && a[i] != b[i]) return false; i++;
    if (i < len && a[i] != b[i]) return false; i++;
    if (i < len && a[i] != b[i]) return false; i++;
    if (i < len && a[i] != b[i]) return false; i++;
    if (i < len && a[i] != b[i]) return false; i++;
    if (i < len && a[i] != b[i]) return false; i++;
    if (i < len && a[i] != b[i]) return false; i++;
    if (i < len && a[i] != b[i]) return false; i++;
    if (i < len && a[i] != b[i]) return false; i++;
    if (i < len && a[i] != b[i]) return false; i++;
    if (i < len && a[i] != b[i]) return false; i++;
    if (i < len && a[i] != b[i]) return false; i++;
    if (i < len && a[i] != b[i]) return false; i++;
    if (i < len && a[i] != b[i]) return false; i++;
    if (i < len && a[i] != b[i]) return false;
    return true;
}

// Chunked C-string to byte buffer copy for CBMC — avoids unwind issues with long key names.
// Copies up to null terminator, 8 chars per iteration. Returns length copied.
// A 33-char key needs ceil(33/8) = 5 iterations (needs unwind >= 6).
inline uint32_t _cbmc_strcopy(uint8_t* dst, const char* src) {
    uint32_t len = 0;
    while (true) {
        uint8_t c0 = (uint8_t)src[len]; if (c0 == 0) break; dst[len++] = c0;
        uint8_t c1 = (uint8_t)src[len]; if (c1 == 0) break; dst[len++] = c1;
        uint8_t c2 = (uint8_t)src[len]; if (c2 == 0) break; dst[len++] = c2;
        uint8_t c3 = (uint8_t)src[len]; if (c3 == 0) break; dst[len++] = c3;
        uint8_t c4 = (uint8_t)src[len]; if (c4 == 0) break; dst[len++] = c4;
        uint8_t c5 = (uint8_t)src[len]; if (c5 == 0) break; dst[len++] = c5;
        uint8_t c6 = (uint8_t)src[len]; if (c6 == 0) break; dst[len++] = c6;
        uint8_t c7 = (uint8_t)src[len]; if (c7 == 0) break; dst[len++] = c7;
    }
    return len;
}

// Helper: copy byteslice to a 32-byte address field
inline void _cbmc_sv_to_addr(uint8_t* dst, const uint8_t* src, uint32_t src_len) {
    uint32_t clen = (src_len < 32) ? src_len : 32;
    _cbmc_bytecopy(dst, src, clen);
}

inline StackValue sv_bytes(const uint8_t* data, uint32_t len) {
    StackValue sv;
    sv._is_bytes = true;
    sv.value = 0;
    sv.byteslice_len = (len < CBMC_BYTES_MAX) ? len : CBMC_BYTES_MAX;
    _cbmc_bytecopy(sv.byteslice, data, sv.byteslice_len);
    // Zero tail bytes for correct struct comparison in match/switch routing.
    // Without this, nondeterministic tails cause 2^N path explosion in routing.
    if (sv.byteslice_len < CBMC_BYTES_MAX) {
        _cbmc_zero(sv.byteslice + sv.byteslice_len, CBMC_BYTES_MAX - sv.byteslice_len);
    }
    return sv;
}

inline StackValue sv_empty_bytes() {
    StackValue sv;
    sv._is_bytes = true;
    sv.value = 0;
    sv.byteslice_len = 0;
    _cbmc_zero(sv.byteslice, CBMC_BYTES_MAX);
    return sv;
}

// Create a StackValue with nondeterministic bytes content.
// Uses uint64 chunks (max 8 iterations for 64-byte values) instead of
// per-byte loops (which needed unwind >= 33 for 32-byte values).
// Zeroes padding beyond `len` to keep only needed bytes symbolic.
inline StackValue sv_nondet_bytes(uint32_t len) {
    StackValue sv;
    sv.value = 0;
    sv._is_bytes = true;
    sv.byteslice_len = len;
    // Zero padding beyond len (keeps only needed bytes symbolic)
    if (len < CBMC_BYTES_MAX) {
        _cbmc_zero(sv.byteslice + len, CBMC_BYTES_MAX - len);
    }
    // Fill first `len` bytes with nondeterministic uint64 chunks.
    // For len=32: 4 iterations (needs unwind >= 5).
    // For len=64: 8 iterations (needs unwind >= 9).
    for (uint32_t i = 0; i + 8 <= len; i += 8) {
        uint64_t chunk = nondet_uint64();
        memcpy(sv.byteslice + i, &chunk, 8);
    }
    uint32_t tail = len % 8;
    if (tail > 0) {
        uint64_t chunk = nondet_uint64();
        memcpy(sv.byteslice + (len - tail), &chunk, tail);
    }
    return sv;
}

inline bool sv_isInt(const StackValue& v) { return !v._is_bytes; }
inline bool sv_isBytes(const StackValue& v) { return v._is_bytes; }

inline bool sv_bytes_equal(const StackValue& a, const StackValue& b) {
    if (a.byteslice_len != b.byteslice_len) return false;
    return _cbmc_byteequal(a.byteslice, b.byteslice, a.byteslice_len);
}

inline bool sv_equal(const StackValue& a, const StackValue& b) {
    if (a._is_bytes != b._is_bytes) return false;
    if (!a._is_bytes) return a.value == b.value;
    return sv_bytes_equal(a, b);
}

// ---------------------------------------------------------------------------
// Stack
// ---------------------------------------------------------------------------

struct Stack {
    uint16_t currentSize;
    StackValue stack[CBMC_STACK_MAX];

    // Member functions matching the transpiler's generated code
    StackValue pop() { return stack[--currentSize]; }
    void push(StackValue v) { stack[currentSize++] = v; }
    StackValue& get(int i) { return stack[currentSize - i - 1]; }
    void discard(uint64_t n) { currentSize -= (uint16_t)n; }
};

inline void stack_init(Stack& s) { s.currentSize = 0; }

inline StackValue stack_pop(Stack& s) {
    __CPROVER_assume(s.currentSize > 0);
    return s.stack[--s.currentSize];
}

inline StackValue& stack_top(Stack& s) {
    return s.stack[s.currentSize - 1];
}

inline StackValue& stack_get(Stack& s, int i) {
    return s.stack[s.currentSize - i - 1];
}

inline void stack_push(Stack& s, StackValue v) {
    __CPROVER_assume(s.currentSize < CBMC_STACK_MAX);
    s.stack[s.currentSize++] = v;
}

// Value-based StackValue equality — compares only meaningful bytes, not tail padding.
// Used by transpiled switch routing instead of struct == (which compares uninitialized tails).
// Loop needs unwind >= max(byteslice_len/8 + 1, byteslice_len%8 + 1).
// For 4-byte method selectors: needs unwind >= 5.
inline bool _sv_eq(const StackValue& a, const StackValue& b) {
    if (a._is_bytes != b._is_bytes) return false;
    if (!a._is_bytes) return a.value == b.value;
    if (a.byteslice_len != b.byteslice_len) return false;
    return _cbmc_byteequal(a.byteslice, b.byteslice, a.byteslice_len);
}

inline void stack_discard(Stack& s, uint64_t n) {
    s.currentSize -= (uint16_t)n;
}

// Convenience
inline void pushint(Stack& s, uint64_t val) { stack_push(s, sv_int(val)); }
inline void pushbytes(Stack& s, const uint8_t* data, uint32_t len) {
    stack_push(s, sv_bytes(data, len));
}

// Overload for transpiler's initializer-list syntax: pushbytes(s, {0x01, 0x02})
// CBMC 5.12 doesn't support std::initializer_list, so we use a struct.
struct __cbmc_bytes_init {
    uint8_t data[CBMC_BYTES_MAX];
    uint32_t len;
};
inline void pushbytes(Stack& s, __cbmc_bytes_init b) {
    stack_push(s, sv_bytes(b.data, b.len));
}

// ---------------------------------------------------------------------------
// Key hash — O(1) comparison for CBMC (eliminates inner comparison loop)
// ---------------------------------------------------------------------------

// Loop-free hash: uses key_len + 6 sampled bytes as fingerprint.
// No loops = no CBMC unwinding needed. Collision-free for any keys
// Exact key comparison: length must match, then byte-equal via chunked comparison.
// Replaces the old _cbmc_key_hash fingerprint which was collision-prone.
// Cost: 1 length comparison + _cbmc_byteequal (1-2 iterations for typical 4-15 byte keys).
inline bool _cbmc_key_equal(const uint8_t* a, uint32_t alen,
                             const uint8_t* b, uint32_t blen) {
    if (alen != blen) return false;
    return _cbmc_byteequal(a, b, alen);
}


// ---------------------------------------------------------------------------
// Panic flag and assert macros (needed by gs_put/ls_put schema enforcement)
// ---------------------------------------------------------------------------

// Global panic flag (CBMC mode)
static bool __avm_panicked = false;

// AVM panic: set flag only (DO NOT use __CPROVER_assume(false) — it cuts the
// execution path, preventing CBMC from checking panic-agreement between sequences)
#define avm_panic() do { __avm_panicked = true; } while(0)

// AVM assert: if expression fails, panic.
// In ASSUME_VALID_OPS mode (property verification), prune invalid paths instead
// of branching into them. This is sound because TEAL's type system guarantees
// type correctness, so the pruned paths are unreachable in real execution.
#ifdef CBMC_ASSUME_VALID_OPS
#define avm_assert_check(expr) __CPROVER_assume(expr)
#else
#define avm_assert_check(expr) do { if (!(expr)) { avm_panic(); } } while(0)
#endif

// ---------------------------------------------------------------------------
// Global state key-value store (bounded)
// ---------------------------------------------------------------------------

struct GlobalEntry {
    uint8_t key[CBMC_BYTES_MAX];
    uint16_t key_len;
    StackValue value;
    bool active;
};

struct GlobalState {
    GlobalEntry entries[CBMC_MAX_GLOBALS];
    uint8_t count;
    uint8_t num_uint;    // schema limit: max uint entries allowed (constant after init)
    uint8_t num_bytes;   // schema limit: max bytes entries allowed (constant after init)
    uint8_t uint_count;  // running count of active uint entries
    uint8_t bytes_count; // running count of active bytes entries
};

inline void gs_init(GlobalState& gs) {
    gs.count = 0;
    gs.num_uint = CBMC_GLOBAL_NUM_UINT;
    gs.num_bytes = CBMC_GLOBAL_NUM_BYTESLICE;
    gs.uint_count = 0;
    gs.bytes_count = 0;
    for (uint32_t i = 0; i < CBMC_MAX_GLOBALS; i++) gs.entries[i].active = false;
}

inline StackValue* gs_get(GlobalState& gs, const uint8_t* key, uint32_t key_len) {
    for (uint32_t i = 0; i < CBMC_MAX_GLOBALS; i++) {
        if (gs.entries[i].active && _cbmc_key_equal(gs.entries[i].key, gs.entries[i].key_len, key, key_len))
            return &gs.entries[i].value;
    }
    return 0;
}

inline void gs_put(GlobalState& gs, const uint8_t* key, uint32_t key_len, StackValue val) {
    // Single-pass: find existing match or first empty slot
    uint32_t first_empty = CBMC_MAX_GLOBALS;
    for (uint32_t i = 0; i < CBMC_MAX_GLOBALS; i++) {
        if (gs.entries[i].active && _cbmc_key_equal(gs.entries[i].key, gs.entries[i].key_len, key, key_len)) {
            // Update existing — track type change
            if (gs.entries[i].value._is_bytes && !val._is_bytes) {
                gs.bytes_count--; gs.uint_count++;
            } else if (!gs.entries[i].value._is_bytes && val._is_bytes) {
                gs.uint_count--; gs.bytes_count++;
            }
            gs.entries[i].value = val;
            return;
        }
        if (!gs.entries[i].active && first_empty == CBMC_MAX_GLOBALS)
            first_empty = i;
    }
    // Insert in first empty slot (with schema enforcement)
    if (first_empty < CBMC_MAX_GLOBALS) {
        if (val._is_bytes)
            avm_assert_check(gs.bytes_count < gs.num_bytes);
        else
            avm_assert_check(gs.uint_count < gs.num_uint);
        gs.entries[first_empty].active = true;
        gs.entries[first_empty].key_len = key_len;
        _cbmc_bytecopy(gs.entries[first_empty].key, key, key_len);
        gs.entries[first_empty].value = val;
        if (val._is_bytes) gs.bytes_count++; else gs.uint_count++;
    }
}

inline void gs_del(GlobalState& gs, const uint8_t* key, uint32_t key_len) {
    for (uint32_t i = 0; i < CBMC_MAX_GLOBALS; i++) {
        if (gs.entries[i].active && _cbmc_key_equal(gs.entries[i].key, gs.entries[i].key_len, key, key_len)) {
            if (gs.entries[i].value._is_bytes) gs.bytes_count--; else gs.uint_count--;
            gs.entries[i].active = false;
            return;
        }
    }
}

// ---------------------------------------------------------------------------
// Direct-index global state ops (O(1), no scanning, no hashing)
// Used by transpiler for compile-time known keys with fixed array indices.
// ---------------------------------------------------------------------------

inline StackValue* gs_get_idx(GlobalState& gs, uint32_t idx) {
    if (!gs.entries[idx].active) return 0;
    return &gs.entries[idx].value;
}

inline void gs_put_idx(GlobalState& gs, uint32_t idx,
                        const uint8_t* key, uint32_t key_len, StackValue val) {
    if (!gs.entries[idx].active) {
        gs.entries[idx].key_len = key_len;
        _cbmc_bytecopy(gs.entries[idx].key, key, key_len);
        if (val._is_bytes) gs.bytes_count++; else gs.uint_count++;
    } else {
        // Track type change
        if (gs.entries[idx].value._is_bytes && !val._is_bytes) {
            gs.bytes_count--; gs.uint_count++;
        } else if (!gs.entries[idx].value._is_bytes && val._is_bytes) {
            gs.uint_count--; gs.bytes_count++;
        }
    }
    gs.entries[idx].active = true;
    gs.entries[idx].value = val;
}

inline void gs_del_idx(GlobalState& gs, uint32_t idx) {
    if (gs.entries[idx].active) {
        if (gs.entries[idx].value._is_bytes) gs.bytes_count--; else gs.uint_count--;
    }
    gs.entries[idx].active = false;
}

// ---------------------------------------------------------------------------
// Subroutine frames (Phase 3)
// ---------------------------------------------------------------------------

struct Frame {
    uint16_t base;        // stack index of the first argument
    uint8_t num_args;
    uint8_t num_returns;
};

// ---------------------------------------------------------------------------
// Local state (Phase 4)
// ---------------------------------------------------------------------------

struct LocalEntry {
    uint8_t account[32];
    GlobalEntry entries[CBMC_MAX_LOCAL_KEYS];
    uint8_t count;
    bool active;
    uint8_t num_uint;    // schema limit: max uint entries allowed (constant after init)
    uint8_t num_bytes;   // schema limit: max bytes entries allowed (constant after init)
    uint8_t uint_count;  // running count of active uint entries
    uint8_t bytes_count; // running count of active bytes entries
};

struct LocalState {
    LocalEntry accounts[CBMC_MAX_LOCAL_ACCOUNTS];
    uint8_t count;
};

inline void ls_init(LocalState& ls) {
    ls.count = 0;
    for (int i = 0; i < CBMC_MAX_LOCAL_ACCOUNTS; i++) ls.accounts[i].active = false;
}

inline bool _addr_equal(const uint8_t* a, const uint8_t* b) {
    return _cbmc_byteequal(a, b, 32);
}

inline LocalEntry* ls_find_account(LocalState& ls, const uint8_t* addr) {
    for (uint32_t i = 0; i < ls.count; i++) {
        if (ls.accounts[i].active && _addr_equal(ls.accounts[i].account, addr))
            return &ls.accounts[i];
    }
    return 0;
}

inline LocalEntry* ls_ensure_account(LocalState& ls, const uint8_t* addr) {
    LocalEntry* e = ls_find_account(ls, addr);
    if (e) return e;
    __CPROVER_assume(ls.count < CBMC_MAX_LOCAL_ACCOUNTS);
    LocalEntry* ne = &ls.accounts[ls.count];
    ne->active = true;
    ne->count = 0;
    ne->num_uint = CBMC_LOCAL_NUM_UINT;
    ne->num_bytes = CBMC_LOCAL_NUM_BYTESLICE;
    ne->uint_count = 0;
    ne->bytes_count = 0;
    _cbmc_bytecopy(ne->account, addr, 32);
    for (int j = 0; j < CBMC_MAX_LOCAL_KEYS; j++) ne->entries[j].active = false;
    ls.count++;
    return ne;
}

inline void ls_put(LocalState& ls, const uint8_t* addr, const uint8_t* key, uint32_t key_len, StackValue val) {
    LocalEntry* acct = ls_ensure_account(ls, addr);
    // Single-pass: find existing match or first empty slot
    uint32_t first_empty = CBMC_MAX_LOCAL_KEYS;
    for (uint32_t i = 0; i < CBMC_MAX_LOCAL_KEYS; i++) {
        if (acct->entries[i].active && _cbmc_key_equal(acct->entries[i].key, acct->entries[i].key_len, key, key_len)) {
            // Update existing — track type change
            if (acct->entries[i].value._is_bytes && !val._is_bytes) {
                acct->bytes_count--; acct->uint_count++;
            } else if (!acct->entries[i].value._is_bytes && val._is_bytes) {
                acct->uint_count--; acct->bytes_count++;
            }
            acct->entries[i].value = val;
            return;
        }
        if (!acct->entries[i].active && first_empty == CBMC_MAX_LOCAL_KEYS)
            first_empty = i;
    }
    // Insert in first empty slot (with schema enforcement)
    if (first_empty < CBMC_MAX_LOCAL_KEYS) {
        if (val._is_bytes)
            avm_assert_check(acct->bytes_count < acct->num_bytes);
        else
            avm_assert_check(acct->uint_count < acct->num_uint);
        acct->entries[first_empty].active = true;
        acct->entries[first_empty].key_len = key_len;
        _cbmc_bytecopy(acct->entries[first_empty].key, key, key_len);
        acct->entries[first_empty].value = val;
        if (val._is_bytes) acct->bytes_count++; else acct->uint_count++;
    }
}

inline StackValue* ls_get(LocalState& ls, const uint8_t* addr, const uint8_t* key, uint32_t key_len) {
    LocalEntry* acct = ls_find_account(ls, addr);
    if (!acct) return 0;
    for (uint32_t i = 0; i < CBMC_MAX_LOCAL_KEYS; i++) {
        if (acct->entries[i].active && _cbmc_key_equal(acct->entries[i].key, acct->entries[i].key_len, key, key_len))
            return &acct->entries[i].value;
    }
    return 0;
}

inline void ls_del(LocalState& ls, const uint8_t* addr, const uint8_t* key, uint32_t key_len) {
    LocalEntry* acct = ls_find_account(ls, addr);
    if (!acct) return;
    for (uint32_t i = 0; i < CBMC_MAX_LOCAL_KEYS; i++) {
        if (acct->entries[i].active && _cbmc_key_equal(acct->entries[i].key, acct->entries[i].key_len, key, key_len)) {
            if (acct->entries[i].value._is_bytes) acct->bytes_count--; else acct->uint_count--;
            acct->entries[i].active = false;
            return;
        }
    }
}

// ---------------------------------------------------------------------------
// Direct-index local state ops (O(1) per key, account still resolved by addr)
// Used by transpiler for compile-time known local keys with fixed array indices.
// ---------------------------------------------------------------------------

inline StackValue* ls_get_idx(LocalState& ls, const uint8_t* addr, uint32_t idx) {
    LocalEntry* acct = ls_find_account(ls, addr);
    if (!acct) return 0;
    if (!acct->entries[idx].active) return 0;
    return &acct->entries[idx].value;
}

inline void ls_put_idx(LocalState& ls, const uint8_t* addr, uint32_t idx,
                        const uint8_t* key, uint32_t key_len, StackValue val) {
    LocalEntry* acct = ls_ensure_account(ls, addr);
    if (!acct->entries[idx].active) {
        acct->entries[idx].key_len = key_len;
        _cbmc_bytecopy(acct->entries[idx].key, key, key_len);
        if (val._is_bytes) acct->bytes_count++; else acct->uint_count++;
    } else {
        // Track type change
        if (acct->entries[idx].value._is_bytes && !val._is_bytes) {
            acct->bytes_count--; acct->uint_count++;
        } else if (!acct->entries[idx].value._is_bytes && val._is_bytes) {
            acct->uint_count--; acct->bytes_count++;
        }
    }
    acct->entries[idx].active = true;
    acct->entries[idx].value = val;
}

inline void ls_del_idx(LocalState& ls, const uint8_t* addr, uint32_t idx) {
    LocalEntry* acct = ls_find_account(ls, addr);
    if (!acct) return;
    if (acct->entries[idx].active) {
        if (acct->entries[idx].value._is_bytes) acct->bytes_count--; else acct->uint_count--;
    }
    acct->entries[idx].active = false;
}

// ---------------------------------------------------------------------------
// Global field enum (Phase 4)
// ---------------------------------------------------------------------------

// Global field enum (matching go-algorand spec numbering)
enum globalFieldEnum {
    GF_MinTxnFee = 0, GF_MinBalance = 1, GF_MaxTxnLife = 2,
    GF_ZeroAddress = 3, GF_GroupSize = 4,
    GF_LogicSigVersion = 5, GF_Round = 6, GF_LatestTimestamp = 7,
    GF_CurrentApplicationID = 8, GF_CreatorAddress = 9,
    GF_CurrentApplicationAddress = 10, GF_GroupID = 11,
    GF_OpcodeBudget = 12, GF_CallerApplicationID = 13,
    GF_CallerApplicationAddress = 14,
    GF_AssetCreateMinBalance = 15, GF_AssetOptInMinBalance = 16,
    GF_GenesisHash = 17,
    GF_PayoutsEnabled = 18, GF_PayoutsGoOnlineFee = 19,
    GF_PayoutsPercent = 20, GF_PayoutsMinBalance = 21,
    GF_PayoutsMaxBalance = 22,
};

// ---------------------------------------------------------------------------
// Box storage (Phase 5)
// ---------------------------------------------------------------------------

struct BoxEntry {
    uint8_t key[CBMC_BYTES_MAX];
    uint16_t key_len;
    uint8_t data[CBMC_BOX_MAX_SIZE];
    uint32_t data_len;
    bool active;
};

struct BoxState {
    BoxEntry entries[CBMC_MAX_BOXES];
    uint32_t count;
};

inline void box_init(BoxState& bs) {
    bs.count = 0;
    for (int i = 0; i < CBMC_MAX_BOXES; i++) bs.entries[i].active = false;
}

inline BoxEntry* box_find(BoxState& bs, const uint8_t* key, uint32_t key_len) {
    for (uint32_t i = 0; i < bs.count; i++) {
        if (bs.entries[i].active && _cbmc_key_equal(bs.entries[i].key, bs.entries[i].key_len, key, key_len))
            return &bs.entries[i];
    }
    return 0;
}

// box_create_entry — create a box with given key and size (zeroed data)
// Returns pointer to the new entry, or existing entry if already present.
inline BoxEntry* box_create_entry(BoxState& bs, const uint8_t* key, uint32_t key_len, uint32_t size) {
    BoxEntry* existing = box_find(bs, key, key_len);
    if (existing) return existing;
    // Try to reuse an inactive slot first
    for (uint32_t i = 0; i < bs.count; i++) {
        if (!bs.entries[i].active) {
            BoxEntry& e = bs.entries[i];
            e.active = true;
            e.key_len = key_len;
            _cbmc_bytecopy(e.key, key, key_len);
            e.data_len = size;
            uint32_t zlen = (size < CBMC_BOX_MAX_SIZE) ? size : CBMC_BOX_MAX_SIZE;
            _cbmc_zero(e.data, zlen);
            return &e;
        }
    }
    // No reusable slot — append
    __CPROVER_assume(bs.count < CBMC_MAX_BOXES);
    BoxEntry& e = bs.entries[bs.count];
    e.active = true;
    e.key_len = key_len;
    _cbmc_bytecopy(e.key, key, key_len);
    e.data_len = size;
    uint32_t zlen = (size < CBMC_BOX_MAX_SIZE) ? size : CBMC_BOX_MAX_SIZE;
    _cbmc_zero(e.data, zlen);
    bs.count++;
    return &e;
}

// box_put_entry — set box contents (creates if not exists, overwrites if exists)
inline void box_put_entry(BoxState& bs, const uint8_t* key, uint32_t key_len,
                          const uint8_t* data, uint32_t data_len) {
    BoxEntry* e = box_find(bs, key, key_len);
    if (!e) {
        __CPROVER_assume(bs.count < CBMC_MAX_BOXES);
        e = &bs.entries[bs.count];
        e->active = true;
        e->key_len = key_len;
        _cbmc_bytecopy(e->key, key, key_len);
        bs.count++;
    }
    e->data_len = data_len;
    uint32_t cplen = (data_len < CBMC_BOX_MAX_SIZE) ? data_len : CBMC_BOX_MAX_SIZE;
    _cbmc_bytecopy(e->data, data, cplen);
}

// box_get_entry — get box data pointer and length, returns NULL if not found
inline uint8_t* box_get_entry(BoxState& bs, const uint8_t* key, uint32_t key_len, uint32_t* out_len) {
    BoxEntry* e = box_find(bs, key, key_len);
    if (!e) return 0;
    *out_len = e->data_len;
    return e->data;
}

// box_del_entry — delete a box by key
inline void box_del_entry(BoxState& bs, const uint8_t* key, uint32_t key_len) {
    BoxEntry* e = box_find(bs, key, key_len);
    if (e) e->active = false;
}

// box_exists — check if a box exists
inline bool box_exists(BoxState& bs, const uint8_t* key, uint32_t key_len) {
    return box_find(bs, key, key_len) != 0;
}

// ---------------------------------------------------------------------------
// Account state (for balance, min_balance, etc.)
// ---------------------------------------------------------------------------

struct AccountEntry {
    uint8_t address[32];
    uint64_t balance;
    uint64_t min_balance;
    bool active;
};

struct AccountsState {
    AccountEntry entries[CBMC_MAX_ACCOUNTS];
    uint8_t count;
};

inline void accts_init(AccountsState& as) {
    as.count = 0;
    for (int i = 0; i < CBMC_MAX_ACCOUNTS; i++) as.entries[i].active = false;
}

inline AccountEntry* acct_find(AccountsState& as, const uint8_t* addr) {
    for (uint32_t i = 0; i < as.count; i++) {
        if (as.entries[i].active && _addr_equal(as.entries[i].address, addr))
            return &as.entries[i];
    }
    return 0;
}

// Add or update an account entry. Returns pointer to the entry.
inline AccountEntry* acct_add(AccountsState& as, const uint8_t* addr, uint64_t balance) {
    AccountEntry* existing = acct_find(as, addr);
    if (existing) { existing->balance = balance; return existing; }
    avm_assert_check(as.count < CBMC_MAX_ACCOUNTS);
    AccountEntry& e = as.entries[as.count];
    e.active = true;
    _cbmc_bytecopy(e.address, addr, 32);
    e.balance = balance;
    e.min_balance = 100000;
    as.count++;
    return &e;
}

// ---------------------------------------------------------------------------
// Asset params state (Phase 7 — enables DeFi verification)
// ---------------------------------------------------------------------------

struct AssetParams {
    uint64_t asset_id;
    uint64_t total;
    uint64_t decimals;
    bool default_frozen;
    uint8_t manager[32];
    uint8_t reserve[32];
    uint8_t freeze[32];
    uint8_t clawback[32];
    uint8_t creator[32];
    uint8_t unit_name[8];     // AssetUnitName (max 8 bytes on Algorand)
    uint8_t unit_name_len;
    uint8_t name[32];         // AssetName (max 32 bytes on Algorand)
    uint8_t name_len;
    uint8_t url[96];          // AssetURL (max 96 bytes on Algorand)
    uint8_t url_len;
    uint8_t metadata_hash[32]; // AssetMetadataHash (exactly 32 bytes)
    bool active;
};

struct AssetParamsState {
    AssetParams entries[CBMC_MAX_ASSETS];
    uint32_t count;
};

inline void aps_init(AssetParamsState& aps) {
    aps.count = 0;
    for (uint32_t i = 0; i < CBMC_MAX_ASSETS; i++) aps.entries[i].active = false;
}

inline AssetParams* aps_find(AssetParamsState& aps, uint64_t asset_id) {
    for (uint32_t i = 0; i < aps.count; i++) {
        if (aps.entries[i].active && aps.entries[i].asset_id == asset_id)
            return &aps.entries[i];
    }
    return 0;
}


struct AssetHolding {
    uint64_t asset_id;
    uint8_t account[32];
    uint64_t balance;
    bool frozen;
    bool opted_in;
    bool active;
};

struct AssetHoldingState {
    AssetHolding entries[CBMC_MAX_ASSET_HOLDINGS];
    uint32_t count;
};

inline void ahs_init(AssetHoldingState& ahs) {
    ahs.count = 0;
    for (uint32_t i = 0; i < CBMC_MAX_ASSET_HOLDINGS; i++) ahs.entries[i].active = false;
}

inline AssetHolding* ahs_find(AssetHoldingState& ahs, const uint8_t* addr, uint64_t asset_id) {
    for (uint32_t i = 0; i < ahs.count; i++) {
        if (ahs.entries[i].active && _addr_equal(ahs.entries[i].account, addr)
            && ahs.entries[i].asset_id == asset_id)
            return &ahs.entries[i];
    }
    return 0;
}

// ---------------------------------------------------------------------------
// Simplified transaction (must be before InnerTxn/TxnGroup/EvalContext)
// ---------------------------------------------------------------------------

struct Txn {
    uint8_t Sender[32];
    uint64_t ApplicationID;
    uint8_t apan;  // OnComplete (0-5)
    uint64_t Fee;
    uint64_t Amount;
    uint8_t AppArgs[CBMC_MAX_APP_ARGS][CBMC_BYTES_MAX];
    uint16_t AppArgLens[CBMC_MAX_APP_ARGS];
    uint8_t NumAppArgs;
    uint8_t TypeEnum;
    uint8_t GroupIndex;
    // Accounts array: index 0 = Sender, 1..N = foreign accounts
    uint8_t Accounts[CBMC_MAX_TXN_ACCOUNTS][32];
    uint8_t NumAccounts;
    // Foreign assets array
    uint64_t Assets[CBMC_MAX_TXN_ASSETS];
    uint8_t NumAssets;
    // Foreign applications array: index 0 = current app, 1..N = foreign apps
    uint64_t Applications[CBMC_MAX_TXN_APPS];
    uint8_t NumApplications;
    // Logs (for inner transaction results)
    uint8_t TxnLogs[CBMC_MAX_TXN_LOGS][CBMC_MAX_LOG_LEN];
    uint16_t TxnLogLens[CBMC_MAX_TXN_LOGS];
    uint8_t NumTxnLogs;
    // Receiver address
    uint8_t Receiver[32];
    // Asset transfer fields
    uint64_t XferAsset;
    uint64_t AssetAmount;
    uint8_t AssetReceiver[32];
    uint8_t AssetSender[32];
    uint8_t AssetCloseTo[32];
    // Asset config fields
    uint64_t ConfigAssetTotal;
    uint8_t ConfigAssetDecimals;
    uint8_t ConfigAssetName[CBMC_BYTES_MAX];
    uint8_t ConfigAssetNameLen;
    uint8_t ConfigAssetUnitName[CBMC_BYTES_MAX];
    uint8_t ConfigAssetUnitNameLen;
    uint8_t ConfigAssetURL[CBMC_BYTES_MAX];
    uint16_t ConfigAssetURLLen;
    uint8_t ConfigAssetMetadataHash[32];
    uint64_t ConfigAsset;
    // Created IDs (from inner txns)
    uint64_t CreatedAssetID;
    uint64_t CreatedApplicationID;
    // Schema fields (creation-time parameters)
    uint8_t GlobalNumUint;
    uint8_t GlobalNumByteSlice;
    uint8_t LocalNumUint;
    uint8_t LocalNumByteSlice;
    // General transaction fields
    uint8_t RekeyTo[32];
    uint8_t CloseRemainderTo[32];
    uint8_t Note[CBMC_BYTES_MAX];
    uint16_t NoteLen;
    uint64_t FirstValid;
    uint64_t LastValid;
    uint8_t Lease[32];
    uint8_t ExtraProgramPages;
    // Asset config address fields
    uint8_t ConfigAssetManager[32];
    uint8_t ConfigAssetReserve[32];
    uint8_t ConfigAssetFreeze[32];
    uint8_t ConfigAssetClawback[32];
    bool ConfigAssetDefaultFrozen;
    // Asset freeze fields
    uint64_t FreezeAsset;
    uint8_t FreezeAssetAccount[32];
    bool FreezeAssetFrozen;
    // Key registration fields
    uint8_t VotePK[32];
    uint8_t SelectionPK[32];
    uint8_t StateProofPK[64];
    uint64_t VoteFirst;
    uint64_t VoteLast;
    uint64_t VoteKeyDilution;
    bool Nonparticipation;
};

// Zero a Txn struct efficiently: scalar fields by direct assignment, byte arrays
// via _cbmc_zero (8-byte chunks). Content arrays (AppArgs, Note, etc.) are NOT
// zeroed because their length fields are set to 0, making content inaccessible.
// Max iterations for any single loop: max(CBMC_MAX_APP_ARGS, 8) = 8 typically.
inline void _cbmc_txn_zero(Txn& t) {
    // Scalar / control fields (no loops needed)
    t.ApplicationID = 0;
    t.apan = 0;
    t.Fee = 0;
    t.Amount = 0;
    t.NumAppArgs = 0;
    t.TypeEnum = 0;
    t.GroupIndex = 0;
    t.NumAccounts = 0;
    t.NumAssets = 0;
    t.NumApplications = 0;
    t.NumTxnLogs = 0;
    t.XferAsset = 0;
    t.AssetAmount = 0;
    t.ConfigAssetTotal = 0;
    t.ConfigAssetDecimals = 0;
    t.ConfigAssetNameLen = 0;
    t.ConfigAssetUnitNameLen = 0;
    t.ConfigAssetURLLen = 0;
    t.ConfigAsset = 0;
    t.CreatedAssetID = 0;
    t.CreatedApplicationID = 0;
    t.GlobalNumUint = 0;
    t.GlobalNumByteSlice = 0;
    t.LocalNumUint = 0;
    t.LocalNumByteSlice = 0;
    t.NoteLen = 0;
    t.FirstValid = 0;
    t.LastValid = 0;
    t.ExtraProgramPages = 0;
    t.ConfigAssetDefaultFrozen = false;
    t.FreezeAsset = 0;
    t.FreezeAssetFrozen = false;
    t.VoteFirst = 0;
    t.VoteLast = 0;
    t.VoteKeyDilution = 0;
    t.Nonparticipation = false;
    // Address fields (32 bytes each → 4 iterations per _cbmc_zero call)
    _cbmc_zero(t.Sender, 32);
    _cbmc_zero(t.Receiver, 32);
    _cbmc_zero(t.AssetReceiver, 32);
    _cbmc_zero(t.AssetSender, 32);
    _cbmc_zero(t.AssetCloseTo, 32);
    _cbmc_zero(t.RekeyTo, 32);
    _cbmc_zero(t.CloseRemainderTo, 32);
    _cbmc_zero(t.Lease, 32);
    _cbmc_zero(t.ConfigAssetManager, 32);
    _cbmc_zero(t.ConfigAssetReserve, 32);
    _cbmc_zero(t.ConfigAssetFreeze, 32);
    _cbmc_zero(t.ConfigAssetClawback, 32);
    _cbmc_zero(t.ConfigAssetMetadataHash, 32);
    _cbmc_zero(t.FreezeAssetAccount, 32);
    _cbmc_zero(t.VotePK, 32);
    _cbmc_zero(t.SelectionPK, 32);
    _cbmc_zero(t.StateProofPK, 64);  // 8 iterations
    // Array control fields (small bounded loops)
    for (uint32_t i = 0; i < CBMC_MAX_APP_ARGS; i++) t.AppArgLens[i] = 0;
    for (uint32_t i = 0; i < CBMC_MAX_TXN_ACCOUNTS; i++) _cbmc_zero(t.Accounts[i], 32);
    for (uint32_t i = 0; i < CBMC_MAX_TXN_ASSETS; i++) t.Assets[i] = 0;
    for (uint32_t i = 0; i < CBMC_MAX_TXN_APPS; i++) t.Applications[i] = 0;
    for (uint32_t i = 0; i < CBMC_MAX_TXN_LOGS; i++) t.TxnLogLens[i] = 0;
}

struct InnerTxn {
    Txn txn;
    bool submitted;
};

struct TxnGroup {
    Txn txns[CBMC_MAX_GROUP_SIZE];
    uint8_t size;
};

inline void tg_init(TxnGroup& tg) { tg.size = 0; }

// ---------------------------------------------------------------------------
// Simplified blockchain state
// ---------------------------------------------------------------------------

struct BlockchainState {
    GlobalState globals;
    LocalState locals;
    BoxState boxes;
    AccountsState accounts;
    AssetParamsState asset_params;
    AssetHoldingState asset_holdings;
    uint64_t app_balance;
    uint64_t latest_timestamp;
    uint64_t round;
    uint32_t min_txn_fee;
    uint32_t min_balance;
    uint16_t max_txn_life;
    uint8_t group_size;
};

inline void bs_init(BlockchainState& bs) {
    gs_init(bs.globals);
    ls_init(bs.locals);
    box_init(bs.boxes);
    accts_init(bs.accounts);
    aps_init(bs.asset_params);
    ahs_init(bs.asset_holdings);
    bs.app_balance = 0;
    bs.latest_timestamp = 0;
    bs.round = 1;
    bs.min_txn_fee = 1000;
    bs.min_balance = 100000;
    bs.max_txn_life = 1000;
    bs.group_size = 1;
}

// ---------------------------------------------------------------------------
// Simplified EvalContext
// ---------------------------------------------------------------------------

struct EvalContext {
    StackValue sp[CBMC_SCRATCH_SLOTS]; // scratch space
    uint64_t CurrentApplicationID;
    uint8_t Logs[CBMC_MAX_LOGS][CBMC_MAX_LOG_LEN];
    uint16_t LogLens[CBMC_MAX_LOGS];
    uint8_t NumLogs;
    // Subroutine frames (Phase 3)
    Frame frames[CBMC_MAX_FRAMES];
    uint8_t frame_count;
    // Inner transactions (Phase 6)
    InnerTxn inner_txns[CBMC_MAX_INNER_TXNS];
    uint8_t inner_count;
    Txn building_txn;
    bool building_itxn;
    // Application address (32 bytes)
    uint8_t CurrentApplicationAddress[32];
    uint8_t CreatorAddress[32];
    // LogicSig arguments (only valid in LogicSig mode, not in app calls)
    uint8_t LsigArgs[CBMC_MAX_LSIG_ARGS][CBMC_BYTES_MAX];
    uint16_t LsigArgLens[CBMC_MAX_LSIG_ARGS];
    uint8_t NumLsigArgs;
};

inline void ctx_init(EvalContext& ctx) {
    ctx.CurrentApplicationID = 0;
    ctx.NumLogs = 0;
    ctx.frame_count = 0;
    ctx.inner_count = 0;
    ctx.building_itxn = false;
    ctx.NumLsigArgs = 0;
    _cbmc_zero(ctx.CurrentApplicationAddress, 32);
    _cbmc_zero(ctx.CreatorAddress, 32);
}

// ---------------------------------------------------------------------------
// Execution result
// ---------------------------------------------------------------------------

enum ExecResult { REJECT = 0, ACCEPT = 1, PANIC = 2 };

// Short-circuit macro: after any operation that might panic, skip the rest of
// the contract if already panicked. This prevents CBMC from analyzing dead
// code paths after a panic, dramatically reducing verification time.
#define AVM_BAIL_ON_PANIC() do { if (__avm_panicked) goto _contract_end; } while(0)
