#pragma once

// Reusable property helpers for AVM formal verification with CBMC.
//
// These functions work with the CBMC-specific bounded types defined in
// cbmc_avm.h (fixed arrays, no STL containers). They are designed to be
// used within property expressions in the AVM_verify_template.
//
// Requires: cbmc_avm.h already included (provides BlockchainState, StackValue, etc.)

// ---------------------------------------------------------------------------
// VERIFY_ASSERT: Generates a proper CBMC assertion that reports violations.
// ---------------------------------------------------------------------------
#ifndef VERIFY_ASSERT
#define VERIFY_ASSERT(expr) __CPROVER_assert((expr), #expr)
#endif

// ExecResult enum is defined in cbmc_avm.h (REJECT=0, ACCEPT=1, PANIC=2)

// ---------------------------------------------------------------------------
// Key matching helper (used internally)
// ---------------------------------------------------------------------------

inline bool _key_match(const uint8_t* a, uint32_t alen, const uint8_t* b, uint32_t blen) {
    if (alen != blen) return false;
    return _cbmc_byteequal(a, b, alen);
}

// Make a key from a string literal. Returns length, fills buf.
// Uses _cbmc_strcopy (8 chars/iteration) to avoid unwind issues with long key names.
inline uint32_t _str_key(const char* s, uint8_t* buf) {
    return _cbmc_strcopy(buf, s);
}

// ---------------------------------------------------------------------------
// Global state property helpers
// ---------------------------------------------------------------------------

// Get a global value by raw key. Returns pointer to StackValue or NULL.
inline StackValue* prop_get_global(BlockchainState& BS, const uint8_t* key, uint32_t key_len) {
    return gs_get(BS.globals, key, key_len);
}

// Get a global value by string key.
inline StackValue* prop_get_global(BlockchainState& BS, const char* key_str) {
    uint8_t key[CBMC_BYTES_MAX];
    uint32_t len = _str_key(key_str, key);
    return gs_get(BS.globals, key, len);
}

// Get a global value from a specific GlobalState (for per-app globals).
inline StackValue* prop_get_global(GlobalState& gs, const char* key_str) {
    uint8_t key[CBMC_BYTES_MAX];
    uint32_t len = _str_key(key_str, key);
    return gs_get(gs, key, len);
}

// Get global int value, with default if not found.
inline uint64_t prop_get_global_int(BlockchainState& BS, const char* key_str, uint64_t dflt) {
    StackValue* v = prop_get_global(BS, key_str);
    if (!v) return dflt;
    return v->value;
}

// Get global int from a specific GlobalState (for per-app globals like _app_globals_42).
inline uint64_t prop_get_global_int(GlobalState& gs, const char* key_str, uint64_t dflt) {
    StackValue* v = prop_get_global(gs, key_str);
    if (!v) return dflt;
    return v->value;
}

// Get global bytes value. Returns pointer to data and sets out_len. NULL if not found.
inline uint8_t* prop_get_global_bytes(BlockchainState& BS, const char* key_str, uint32_t* out_len) {
    StackValue* v = prop_get_global(BS, key_str);
    if (!v || !v->_is_bytes) return 0;
    *out_len = v->byteslice_len;
    return v->byteslice;
}

// Check if a global key exists.
inline bool prop_global_exists(BlockchainState& BS, const char* key_str) {
    return prop_get_global(BS, key_str) != 0;
}

// Check if a global int value changed between two states.
inline bool prop_global_int_changed(BlockchainState& before, BlockchainState& after, const char* key_str) {
    StackValue* vb = prop_get_global(before, key_str);
    StackValue* va = prop_get_global(after, key_str);
    if ((vb == 0) != (va == 0)) return true;
    if (!vb) return false;
    return vb->value != va->value;
}

// Check if a global value changed (int or bytes).
inline bool prop_global_changed(BlockchainState& before, BlockchainState& after, const char* key_str) {
    StackValue* vb = prop_get_global(before, key_str);
    StackValue* va = prop_get_global(after, key_str);
    if ((vb == 0) != (va == 0)) return true;
    if (!vb) return false;
    if (vb->_is_bytes != va->_is_bytes) return true;
    if (!vb->_is_bytes) return vb->value != va->value;
    if (vb->byteslice_len != va->byteslice_len) return true;
    return !_cbmc_byteequal(vb->byteslice, va->byteslice, vb->byteslice_len);
}

// ---------------------------------------------------------------------------
// Local state property helpers
// ---------------------------------------------------------------------------

// Get a local value by address + string key.
inline StackValue* prop_get_local(BlockchainState& BS, const uint8_t* addr, const char* key_str) {
    uint8_t key[CBMC_BYTES_MAX];
    uint32_t len = _str_key(key_str, key);
    return ls_get(BS.locals, addr, key, len);
}

// Get local int value, with default.
inline uint64_t prop_get_local_int(BlockchainState& BS, const uint8_t* addr,
                                    const char* key_str, uint64_t dflt) {
    StackValue* v = prop_get_local(BS, addr, key_str);
    if (!v) return dflt;
    return v->value;
}

// Check if a local key changed.
inline bool prop_local_changed(BlockchainState& before, BlockchainState& after,
                                const uint8_t* addr, const char* key_str) {
    StackValue* vb = prop_get_local(before, addr, key_str);
    StackValue* va = prop_get_local(after, addr, key_str);
    if ((vb == 0) != (va == 0)) return true;
    if (!vb) return false;
    if (vb->_is_bytes != va->_is_bytes) return true;
    if (!vb->_is_bytes) return vb->value != va->value;
    if (vb->byteslice_len != va->byteslice_len) return true;
    return !_cbmc_byteequal(vb->byteslice, va->byteslice, vb->byteslice_len);
}

// ---------------------------------------------------------------------------
// Box state property helpers
// ---------------------------------------------------------------------------

// Get box data by string key. Returns pointer to data, sets out_len. NULL if not found.
inline uint8_t* prop_get_box(BlockchainState& BS, const char* key_str, uint32_t* out_len) {
    uint8_t key[CBMC_BYTES_MAX];
    uint32_t len = _str_key(key_str, key);
    return box_get_entry(BS.boxes, key, len, out_len);
}

// Get box data by raw key.
inline uint8_t* prop_get_box(BlockchainState& BS, const uint8_t* key, uint32_t key_len,
                              uint32_t* out_len) {
    return box_get_entry(BS.boxes, key, key_len, out_len);
}

// Check if a box exists by string key.
inline bool prop_box_exists(BlockchainState& BS, const char* key_str) {
    uint8_t key[CBMC_BYTES_MAX];
    uint32_t len = _str_key(key_str, key);
    return box_exists(BS.boxes, key, len);
}

// Get box size by string key (0 if not found).
inline uint32_t prop_box_size(BlockchainState& BS, const char* key_str) {
    uint32_t out_len = 0;
    uint8_t* data = prop_get_box(BS, key_str, &out_len);
    return data ? out_len : 0;
}

// Read a big-endian uint64 from box data at a byte offset.
inline uint64_t prop_box_read_uint64(const uint8_t* data, uint32_t data_len, uint32_t offset) {
    uint64_t val = 0;
    for (uint32_t i = 0; i < 8 && (offset + i) < data_len; i++)
        val = (val << 8) | data[offset + i];
    return val;
}

// Read a single byte from box data at offset (0 if out of bounds).
inline uint8_t prop_box_read_byte(const uint8_t* data, uint32_t data_len, uint32_t offset) {
    if (offset >= data_len) return 0;
    return data[offset];
}

// Check if box data matches expected bytes.
inline bool prop_box_data_equals(const uint8_t* data, uint32_t data_len,
                                  const uint8_t* expected, uint32_t expected_len) {
    if (data_len != expected_len) return false;
    return _cbmc_byteequal(data, expected, data_len);
}

// Check if a box changed between two states (by string key).
inline bool prop_box_changed(BlockchainState& before, BlockchainState& after, const char* key_str) {
    uint8_t key[CBMC_BYTES_MAX];
    uint32_t len = _str_key(key_str, key);
    BoxEntry* eb = box_find(before.boxes, key, len);
    BoxEntry* ea = box_find(after.boxes, key, len);
    if ((eb == 0) != (ea == 0)) return true;
    if (!eb) return false;
    if (eb->data_len != ea->data_len) return true;
    return !_cbmc_byteequal(eb->data, ea->data, eb->data_len);
}

// Count active boxes.
inline uint32_t prop_box_count(BlockchainState& BS) {
    uint32_t count = 0;
    for (uint32_t i = 0; i < BS.boxes.count; i++) {
        if (BS.boxes.entries[i].active) count++;
    }
    return count;
}

// ---------------------------------------------------------------------------
// Balance property helpers
// ---------------------------------------------------------------------------

// Get app balance.
inline uint64_t prop_app_balance(BlockchainState& BS) {
    return BS.app_balance;
}

// Get account balance by address.
inline uint64_t prop_account_balance(BlockchainState& BS, const uint8_t* addr) {
    AccountEntry* e = acct_find(BS.accounts, addr);
    return e ? e->balance : 0;
}

// Check if app balance changed.
inline bool prop_app_balance_changed(BlockchainState& before, BlockchainState& after) {
    return before.app_balance != after.app_balance;
}

// ---------------------------------------------------------------------------
// Transaction property helpers
// ---------------------------------------------------------------------------

// Check if txn has a specific method selector (first 4 bytes of arg 0).
inline bool prop_txn_method_is(Txn& txn, uint8_t b0, uint8_t b1, uint8_t b2, uint8_t b3) {
    if (txn.NumAppArgs == 0 || txn.AppArgLens[0] < 4) return false;
    return txn.AppArgs[0][0] == b0 && txn.AppArgs[0][1] == b1 &&
           txn.AppArgs[0][2] == b2 && txn.AppArgs[0][3] == b3;
}

// Get OnCompletion value.
inline uint8_t prop_on_completion(Txn& txn) {
    return txn.apan;
}

// ---------------------------------------------------------------------------
// Log property helpers
// ---------------------------------------------------------------------------

// Get number of logs emitted.
inline uint32_t prop_num_logs(EvalContext& ctx) {
    return ctx.NumLogs;
}

// Get log data at index. Returns pointer and sets out_len. NULL if out of range.
inline uint8_t* prop_get_log(EvalContext& ctx, uint32_t idx, uint32_t* out_len) {
    if (idx >= ctx.NumLogs) return 0;
    *out_len = ctx.LogLens[idx];
    return ctx.Logs[idx];
}

// ===========================================================================
// High-level property patterns
// ===========================================================================

// ---------------------------------------------------------------------------
// Monotonic properties
// ---------------------------------------------------------------------------

// Global int only increases (or stays same) between states.
inline bool prop_global_int_monotonic_inc(BlockchainState& before, BlockchainState& after,
                                           const char* key_str) {
    uint64_t vb = prop_get_global_int(before, key_str, 0);
    uint64_t va = prop_get_global_int(after, key_str, 0);
    return va >= vb;
}

// Global int only decreases (or stays same).
inline bool prop_global_int_monotonic_dec(BlockchainState& before, BlockchainState& after,
                                           const char* key_str) {
    uint64_t vb = prop_get_global_int(before, key_str, 0);
    uint64_t va = prop_get_global_int(after, key_str, 0);
    return va <= vb;
}

// ---------------------------------------------------------------------------
// Bounded properties
// ---------------------------------------------------------------------------

// Global int stays in [lo, hi] after execution.
inline bool prop_global_int_bounded(BlockchainState& BS, const char* key_str,
                                     uint64_t lo, uint64_t hi) {
    StackValue* v = prop_get_global(BS, key_str);
    if (!v) return true;  // absent key is trivially in bounds
    return v->value >= lo && v->value <= hi;
}

// ---------------------------------------------------------------------------
// Conservation property
// ---------------------------------------------------------------------------

// App balance not created from thin air: after balance <= before balance + txn amounts.
// Simple form: checks that balance did not increase.
inline bool prop_balance_conserved(BlockchainState& before, BlockchainState& after) {
    return after.app_balance <= before.app_balance;
}

// Balance conservation for a specific app (multi-contract).
// Uses AccountsState lookup — the app must be registered via bs_assume_app_account().
inline bool prop_balance_conserved_for(BlockchainState& before, BlockchainState& after,
                                        const uint8_t* addr) {
    return prop_account_balance(after, addr) <= prop_account_balance(before, addr);
}

// ---------------------------------------------------------------------------
// Authorization properties
// ---------------------------------------------------------------------------

// Sender matches expected address.
inline bool prop_sender_is(Txn& txn, const uint8_t* expected_addr) {
    return _cbmc_byteequal(txn.Sender, expected_addr, 32);
}

// Result is not ACCEPT unless sender matches expected address.
inline bool prop_requires_sender(ExecResult result, Txn& txn, const uint8_t* expected_addr) {
    if (result != ACCEPT) return true;  // non-accept is fine regardless
    return _cbmc_byteequal(txn.Sender, expected_addr, 32);
}

// ---------------------------------------------------------------------------
// Immutability properties
// ---------------------------------------------------------------------------

// A specific global key did not change.
inline bool prop_global_unchanged(BlockchainState& before, BlockchainState& after,
                                    const char* key_str) {
    return !prop_global_changed(before, after, key_str);
}

// No globals changed at all. O(N) — relies on gs_put/gs_put_idx preserving index positions.
inline bool prop_all_globals_unchanged(BlockchainState& before, BlockchainState& after) {
    for (uint32_t i = 0; i < CBMC_MAX_GLOBALS; i++) {
        if (before.globals.entries[i].active != after.globals.entries[i].active)
            return false;
        if (!before.globals.entries[i].active) continue;
        if (!sv_equal(before.globals.entries[i].value, after.globals.entries[i].value))
            return false;
    }
    return true;
}

// ---------------------------------------------------------------------------
// Box count properties
// ---------------------------------------------------------------------------

// Box count didn't increase (monotonic non-increasing).
inline bool prop_box_count_non_increasing(BlockchainState& before, BlockchainState& after) {
    return prop_box_count(after) <= prop_box_count(before);
}

// Box count didn't decrease (monotonic non-decreasing).
inline bool prop_box_count_non_decreasing(BlockchainState& before, BlockchainState& after) {
    return prop_box_count(after) >= prop_box_count(before);
}

// No box contents changed. O(N) — relies on index-stable box storage.
inline bool prop_all_boxes_unchanged(BlockchainState& before, BlockchainState& after) {
    for (uint32_t i = 0; i < CBMC_MAX_BOXES; i++) {
        if (before.boxes.entries[i].active != after.boxes.entries[i].active)
            return false;
        if (!before.boxes.entries[i].active) continue;
        if (before.boxes.entries[i].data_len != after.boxes.entries[i].data_len)
            return false;
        if (!_cbmc_byteequal(before.boxes.entries[i].data, after.boxes.entries[i].data,
                              before.boxes.entries[i].data_len))
            return false;
    }
    return true;
}

// ---------------------------------------------------------------------------
// Asset property helpers
// ---------------------------------------------------------------------------

// Asset balance didn't change (if in state model).
inline bool prop_asset_balance_unchanged(BlockchainState& before, BlockchainState& after,
                                          const uint8_t* addr, uint64_t asset_id) {
    AssetHolding* hb = ahs_find(before.asset_holdings, addr, asset_id);
    AssetHolding* ha = ahs_find(after.asset_holdings, addr, asset_id);
    if ((hb == 0) != (ha == 0)) return false;
    if (!hb) return true;  // both absent
    return hb->balance == ha->balance;
}

// Asset balance in range [lo, hi] after execution (if in state model).
inline bool prop_asset_balance_bounded(BlockchainState& BS, const uint8_t* addr,
                                        uint64_t asset_id, uint64_t lo, uint64_t hi) {
    AssetHolding* h = ahs_find(BS.asset_holdings, addr, asset_id);
    if (!h) return true;  // absent is trivially in bounds
    return h->balance >= lo && h->balance <= hi;
}

// ---------------------------------------------------------------------------
// Local state property helpers (high-level)
// ---------------------------------------------------------------------------

// A specific local key did not change.
inline bool prop_local_unchanged(BlockchainState& before, BlockchainState& after,
                                   const uint8_t* addr, const char* key_str) {
    return !prop_local_changed(before, after, addr, key_str);
}

// No local state changed for any account. O(accounts × keys) — relies on index-stable storage.
// Account indices are stable across before/after (ls_ensure_account appends, never reorders).
inline bool prop_all_locals_unchanged(BlockchainState& before, BlockchainState& after) {
    for (uint32_t a = 0; a < before.locals.count; a++) {
        if (!before.locals.accounts[a].active) continue;
        if (!after.locals.accounts[a].active) return false;  // account was removed
        for (uint32_t i = 0; i < CBMC_MAX_LOCAL_KEYS; i++) {
            if (before.locals.accounts[a].entries[i].active != after.locals.accounts[a].entries[i].active)
                return false;
            if (!before.locals.accounts[a].entries[i].active) continue;
            if (!sv_equal(before.locals.accounts[a].entries[i].value, after.locals.accounts[a].entries[i].value))
                return false;
        }
    }
    return true;
}

// Local int only increases (or stays same).
inline bool prop_local_int_monotonic_inc(BlockchainState& before, BlockchainState& after,
                                           const uint8_t* addr, const char* key_str) {
    uint64_t vb = prop_get_local_int(before, addr, key_str, 0);
    uint64_t va = prop_get_local_int(after, addr, key_str, 0);
    return va >= vb;
}

// Local int only decreases (or stays same).
inline bool prop_local_int_monotonic_dec(BlockchainState& before, BlockchainState& after,
                                           const uint8_t* addr, const char* key_str) {
    uint64_t vb = prop_get_local_int(before, addr, key_str, 0);
    uint64_t va = prop_get_local_int(after, addr, key_str, 0);
    return va <= vb;
}

// Local int stays in [lo, hi] after execution.
inline bool prop_local_int_bounded(BlockchainState& BS, const uint8_t* addr,
                                     const char* key_str, uint64_t lo, uint64_t hi) {
    StackValue* v = prop_get_local(BS, addr, key_str);
    if (!v) return true;  // absent is trivially in bounds
    return v->value >= lo && v->value <= hi;
}

// ---------------------------------------------------------------------------
// Inner transaction property helpers
// ---------------------------------------------------------------------------

// No inner transactions were submitted.
inline bool prop_no_inner_txns(EvalContext& ctx) {
    return ctx.inner_count == 0;
}

// Number of inner transactions submitted.
inline uint32_t prop_inner_txn_count(EvalContext& ctx) {
    return ctx.inner_count;
}

// Total amount sent via inner payments (TypeEnum=1).
inline uint64_t prop_total_inner_payment(EvalContext& ctx) {
    uint64_t total = 0;
    for (uint32_t i = 0; i < ctx.inner_count; i++) {
        if (ctx.inner_txns[i].submitted && ctx.inner_txns[i].txn.TypeEnum == 1) {
            total += ctx.inner_txns[i].txn.Amount;
        }
    }
    return total;
}

// ---------------------------------------------------------------------------
// Safety property helpers
// ---------------------------------------------------------------------------

// Transaction does not rekey the sender (RekeyTo is zero address).
// Uses _addr_is_set (5-sample-byte check, loop-free).
inline bool prop_no_rekey(Txn& txn) {
    return !_addr_is_set(txn.RekeyTo);
}

// Transaction does not close out the account balance (CloseRemainderTo is zero).
inline bool prop_no_close_out(Txn& txn) {
    return !_addr_is_set(txn.CloseRemainderTo);
}

// Transaction does not close asset holdings (AssetCloseTo is zero).
inline bool prop_no_asset_close(Txn& txn) {
    return !_addr_is_set(txn.AssetCloseTo);
}

// ---------------------------------------------------------------------------
// Scratch space property helpers
// ---------------------------------------------------------------------------

// Get scratch slot value as int (returns default_val if slot is bytes or empty).
inline uint64_t prop_get_scratch_int(EvalContext& ctx, uint32_t slot, uint64_t default_val) {
    if (slot >= CBMC_SCRATCH_SLOTS) return default_val;
    StackValue& sv = ctx.sp[slot];
    return sv._is_bytes ? default_val : sv.value;
}

// All inner transactions have Fee == 0 (Tinyman pattern: fees paid by outer txn).
inline bool prop_all_inner_txns_zero_fee(EvalContext& ctx) {
    for (uint32_t i = 0; i < ctx.inner_count; i++) {
        if (ctx.inner_txns[i].submitted && ctx.inner_txns[i].txn.Fee != 0)
            return false;
    }
    return true;
}

// Scratch slot did not change between before and after contexts.
inline bool prop_scratch_unchanged(EvalContext& before, EvalContext& after, uint32_t slot) {
    if (slot >= CBMC_SCRATCH_SLOTS) return true;
    StackValue& sb = before.sp[slot];
    StackValue& sa = after.sp[slot];
    if (sb._is_bytes != sa._is_bytes) return false;
    if (!sb._is_bytes) return sb.value == sa.value;
    if (sb.byteslice_len != sa.byteslice_len) return false;
    for (uint32_t i = 0; i < sb.byteslice_len; i++) {
        if (sb.byteslice[i] != sa.byteslice[i]) return false;
    }
    return true;
}

