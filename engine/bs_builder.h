#pragma once

// bs_builder.h — BlockchainState & Transaction Group Builder for CBMC Verification
//
// Provides a contract-agnostic API for defining initial blockchain state and
// transaction groups using __CPROVER_assume() constraints. This enables:
//
//   1. Programmatic definition of "valid initial states"
//   2. Symbolic but bounded transaction group construction
//   3. Asking: "from any valid initial state, can a transaction reach an invalid state?"
//
// Usage pattern in verification templates:
//
//   BlockchainState BS;
//   bs_init(BS);
//   bs_symbolic(BS);                                    // all fields symbolic
//   bs_assume_global_int(BS, "counter", 42);            // concrete global
//   bs_assume_global_int_range(BS, "counter", 0, 100);  // bounded global
//   bs_assume_box_exists(BS, key, 8, 43);               // pre-existing box
//
//   Txn TxnGroup[4];
//   txg_init(TxnGroup, 4);
//   txg_symbolic_appcall(TxnGroup[0], app_id, 4);      // symbolic app call
//   txg_assume_method(TxnGroup[0], 0x78, 0x40, ...);   // constrain method
//   txg_assume_sender(TxnGroup, 4, addr);               // same sender for all
//
// Requires: cbmc_avm.h, cbmc_opcodes.h already included.
//           extern "C" { uint64_t nondet_uint64(); ... } declared.

#include <string.h>

// ===========================================================================
// BlockchainState Builder — Initial State Assumptions
// ===========================================================================

// ---------------------------------------------------------------------------
// bs_symbolic: Make all scalar fields of BS nondeterministic (symbolic).
// After calling this, add __CPROVER_assume constraints to narrow the search.
// ---------------------------------------------------------------------------

inline void bs_symbolic(BlockchainState& BS) {
    BS.app_balance = nondet_uint64();
    BS.latest_timestamp = nondet_uint64();
    BS.round = nondet_uint64();
    BS.min_txn_fee = nondet_uint64();
    BS.min_balance = nondet_uint64();
    BS.group_size = nondet_uint64();
}

// ---------------------------------------------------------------------------
// bs_assume_sane_defaults: Apply basic sanity assumptions to symbolic BS.
// These hold for any real Algorand state.
// ---------------------------------------------------------------------------

inline void bs_assume_sane_defaults(BlockchainState& BS) {
    __CPROVER_assume(BS.round >= 1);
    __CPROVER_assume(BS.min_txn_fee >= 1000);
    __CPROVER_assume(BS.min_balance >= 100000);
    __CPROVER_assume(BS.latest_timestamp >= 1000000000ULL);  // after ~2001
    __CPROVER_assume(BS.latest_timestamp <= 2000000000ULL);  // before ~2033
    __CPROVER_assume(BS.group_size >= 1);
    __CPROVER_assume(BS.group_size <= 16);
}

// ---------------------------------------------------------------------------
// Global state assumptions
// ---------------------------------------------------------------------------

// Set a concrete integer global value.
inline void bs_assume_global_int(BlockchainState& BS, const char* key, uint64_t value) {
    uint8_t kbuf[CBMC_BYTES_MAX];
    uint32_t klen = _cbmc_strcopy(kbuf, key);
    gs_put(BS.globals, kbuf, klen, sv_int(value));
}

// Set a symbolic integer global, constrained to [lo, hi].
inline void bs_assume_global_int_range(BlockchainState& BS, const char* key,
                                        uint64_t lo, uint64_t hi) {
    uint64_t val = nondet_uint64();
    __CPROVER_assume(val >= lo && val <= hi);
    uint8_t kbuf[CBMC_BYTES_MAX];
    uint32_t klen = _cbmc_strcopy(kbuf, key);
    gs_put(BS.globals, kbuf, klen, sv_int(val));
}

// Set a concrete bytes global value.
inline void bs_assume_global_bytes(BlockchainState& BS, const char* key,
                                    const uint8_t* data, uint32_t data_len) {
    uint8_t kbuf[CBMC_BYTES_MAX];
    uint32_t klen = _cbmc_strcopy(kbuf, key);
    gs_put(BS.globals, kbuf, klen, sv_bytes(data, data_len));
}

// ---------------------------------------------------------------------------
// Direct-index global state assumptions (for transpiler-assigned indices)
// ---------------------------------------------------------------------------

// Set a concrete integer global at a transpiler-assigned index.
inline void bs_assume_global_int_idx(BlockchainState& BS, uint32_t idx,
                                      const char* key, uint64_t value) {
    uint8_t kbuf[CBMC_BYTES_MAX];
    uint32_t klen = _cbmc_strcopy(kbuf, key);
    gs_put_idx(BS.globals, idx, kbuf, klen, sv_int(value));
}

// Set a concrete bytes global at a transpiler-assigned index.
inline void bs_assume_global_bytes_idx(BlockchainState& BS, uint32_t idx,
                                        const char* key,
                                        const uint8_t* data, uint32_t data_len) {
    uint8_t kbuf[CBMC_BYTES_MAX];
    uint32_t klen = _cbmc_strcopy(kbuf, key);
    gs_put_idx(BS.globals, idx, kbuf, klen, sv_bytes(data, data_len));
}

// Assume a global key does NOT exist (useful for fresh state).
inline void bs_assume_global_absent(BlockchainState& BS, const char* key) {
    uint8_t kbuf[CBMC_BYTES_MAX];
    uint32_t klen = _cbmc_strcopy(kbuf, key);
    __CPROVER_assume(gs_get(BS.globals, kbuf, klen) == 0);
}

// ---------------------------------------------------------------------------
// Box state assumptions
// ---------------------------------------------------------------------------

// Pre-create a box with concrete data.
// Returns pointer to created box entry (or NULL if at capacity).
inline BoxEntry* bs_assume_box(BlockchainState& BS, const uint8_t* key, uint32_t key_len,
                                const uint8_t* data, uint32_t data_len) {
    BoxEntry* e = box_create_entry(BS.boxes, key, key_len, data_len);
    if (e && data && data_len > 0) {
        uint32_t clen = (data_len < CBMC_BOX_MAX_SIZE) ? data_len : CBMC_BOX_MAX_SIZE;
        _cbmc_bytecopy(e->data, data, clen);
    }
    return e;
}

// Pre-create a box with zeroed data of given size.
inline BoxEntry* bs_assume_box_zeroed(BlockchainState& BS, const uint8_t* key,
                                       uint32_t key_len, uint32_t size) {
    return box_create_entry(BS.boxes, key, key_len, size);
}

// Pre-create a box with symbolic data of given size.
// Each byte of data is nondeterministic.
inline BoxEntry* bs_assume_box_symbolic(BlockchainState& BS, const uint8_t* key,
                                         uint32_t key_len, uint32_t size) {
    BoxEntry* e = box_create_entry(BS.boxes, key, key_len, size);
    if (e) {
        uint32_t fill = (size < CBMC_BOX_MAX_SIZE) ? size : CBMC_BOX_MAX_SIZE;
        for (uint32_t i = 0; i < fill; i++) {
            e->data[i] = nondet_uint8();
        }
    }
    return e;
}

// Assume a box does NOT exist for a given key.
inline void bs_assume_box_absent(BlockchainState& BS, const uint8_t* key, uint32_t key_len) {
    __CPROVER_assume(box_find(BS.boxes, key, key_len) == 0);
}

// Assume no boxes exist at all.
inline void bs_assume_no_boxes(BlockchainState& BS) {
    __CPROVER_assume(BS.boxes.count == 0);
}

// ---------------------------------------------------------------------------
// Local state assumptions
// ---------------------------------------------------------------------------

// Set a concrete local int value for an account.
inline void bs_assume_local_int(BlockchainState& BS, const uint8_t* addr,
                                 const char* key, uint64_t value) {
    uint8_t kbuf[CBMC_BYTES_MAX];
    uint32_t klen = _cbmc_strcopy(kbuf, key);
    ls_put(BS.locals, addr, kbuf, klen, sv_int(value));
}

// Set a concrete local bytes value for an account.
inline void bs_assume_local_bytes(BlockchainState& BS, const uint8_t* addr,
                                   const char* key, const uint8_t* data, uint32_t dlen) {
    uint8_t kbuf[CBMC_BYTES_MAX];
    uint32_t klen = _cbmc_strcopy(kbuf, key);
    ls_put(BS.locals, addr, kbuf, klen, sv_bytes(data, dlen));
}

// ---------------------------------------------------------------------------
// Direct-index local state assumptions (for transpiler-assigned indices)
// ---------------------------------------------------------------------------

// Set a concrete local int at a transpiler-assigned key index.
inline void bs_assume_local_int_idx(BlockchainState& BS, const uint8_t* addr,
                                     uint32_t idx, const char* key, uint64_t value) {
    uint8_t kbuf[CBMC_BYTES_MAX];
    uint32_t klen = _cbmc_strcopy(kbuf, key);
    ls_put_idx(BS.locals, addr, idx, kbuf, klen, sv_int(value));
}

// Set a concrete local bytes at a transpiler-assigned key index.
inline void bs_assume_local_bytes_idx(BlockchainState& BS, const uint8_t* addr,
                                       uint32_t idx, const char* key,
                                       const uint8_t* data, uint32_t dlen) {
    uint8_t kbuf[CBMC_BYTES_MAX];
    uint32_t klen = _cbmc_strcopy(kbuf, key);
    ls_put_idx(BS.locals, addr, idx, kbuf, klen, sv_bytes(data, dlen));
}

// Opt-in an account to the app (create LocalEntry so local state ops succeed).
inline void bs_assume_local_opt_in(BlockchainState& BS, const uint8_t* addr) {
    ls_ensure_account(BS.locals, addr);
}

// ---------------------------------------------------------------------------
// Scratch space assumptions
// ---------------------------------------------------------------------------

// Set a concrete scratch space int value.
inline void bs_assume_scratch_int(EvalContext& ctx, uint32_t slot, uint64_t value) {
    ctx.sp[slot] = sv_int(value);
}

// Set a concrete scratch space bytes value.
inline void bs_assume_scratch_bytes(EvalContext& ctx, uint32_t slot,
                                     const uint8_t* data, uint32_t dlen) {
    ctx.sp[slot] = sv_bytes(data, dlen);
}

// ---------------------------------------------------------------------------
// Balance assumptions
// ---------------------------------------------------------------------------

// Assume app balance is at least `min_bal`.
inline void bs_assume_min_app_balance(BlockchainState& BS, uint64_t min_bal) {
    __CPROVER_assume(BS.app_balance >= min_bal);
}

// Assume app balance is in range [lo, hi].
inline void bs_assume_app_balance_range(BlockchainState& BS, uint64_t lo, uint64_t hi) {
    __CPROVER_assume(BS.app_balance >= lo && BS.app_balance <= hi);
}

// Register an app as an account (apps ARE accounts in Algorand).
// Use this for multi-contract verification so each app has its own balance.
inline AccountEntry* bs_assume_app_account(BlockchainState& BS, const uint8_t* app_addr, uint64_t balance) {
    return acct_add(BS.accounts, app_addr, balance);
}

// Register an app account with symbolic (nondeterministic) balance.
inline AccountEntry* bs_assume_app_account_symbolic(BlockchainState& BS, const uint8_t* app_addr) {
    AccountEntry* e = acct_add(BS.accounts, app_addr, 0);
    e->balance = nondet_uint64();
    return e;
}

// Register an app account with bounded balance.
inline AccountEntry* bs_assume_app_account_range(BlockchainState& BS, const uint8_t* app_addr,
                                                   uint64_t lo, uint64_t hi) {
    AccountEntry* e = acct_add(BS.accounts, app_addr, 0);
    e->balance = nondet_uint64();
    __CPROVER_assume(e->balance >= lo && e->balance <= hi);
    return e;
}


// ---------------------------------------------------------------------------
// Asset params assumptions
// ---------------------------------------------------------------------------

// Add an asset to the params state with concrete manager and creator.
// Other fields (total, decimals, etc.) are set to defaults; modify the
// returned pointer to customize.
inline AssetParams* bs_assume_asset_params(BlockchainState& BS, uint64_t asset_id,
                                            const uint8_t* manager, const uint8_t* creator) {
    AssetParamsState& aps = BS.asset_params;
    // Check if already exists
    AssetParams* existing = aps_find(aps, asset_id);
    if (existing) return existing;
    __CPROVER_assume(aps.count < CBMC_MAX_ASSETS);
    AssetParams& e = aps.entries[aps.count];
    e.active = true;
    e.asset_id = asset_id;
    e.total = 0;
    e.decimals = 0;
    e.default_frozen = false;
    _cbmc_bytecopy(e.manager, manager, 32);
    _cbmc_zero(e.reserve, 32);
    _cbmc_zero(e.freeze, 32);
    _cbmc_zero(e.clawback, 32);
    _cbmc_bytecopy(e.creator, creator, 32);
    e.unit_name_len = 0;
    e.name_len = 0;
    e.url_len = 0;
    _cbmc_zero(e.metadata_hash, 32);
    aps.count++;
    return &e;
}

// Assume asset manager is a specific address.
inline void bs_assume_asset_manager(BlockchainState& BS, uint64_t asset_id,
                                     const uint8_t* manager) {
    AssetParams* ap = aps_find(BS.asset_params, asset_id);
    if (ap) {
        _cbmc_bytecopy(ap->manager, manager, 32);
    }
}

// ---------------------------------------------------------------------------
// Asset holding assumptions
// ---------------------------------------------------------------------------

// Add asset holding for an account with concrete balance and frozen state.
inline AssetHolding* bs_assume_asset_holding(BlockchainState& BS, const uint8_t* addr,
                                              uint64_t asset_id, uint64_t balance, bool frozen) {
    AssetHoldingState& ahs = BS.asset_holdings;
    // Check if already exists
    AssetHolding* existing = ahs_find(ahs, addr, asset_id);
    if (existing) {
        existing->balance = balance;
        existing->frozen = frozen;
        existing->opted_in = true;
        return existing;
    }
    __CPROVER_assume(ahs.count < CBMC_MAX_ASSET_HOLDINGS);
    AssetHolding& e = ahs.entries[ahs.count];
    e.active = true;
    e.asset_id = asset_id;
    _cbmc_bytecopy(e.account, addr, 32);
    e.balance = balance;
    e.frozen = frozen;
    e.opted_in = true;
    ahs.count++;
    return &e;
}

// Add asset holding with symbolic balance.
inline AssetHolding* bs_assume_asset_holding_symbolic(BlockchainState& BS, const uint8_t* addr,
                                                       uint64_t asset_id) {
    uint64_t bal = nondet_uint64();
    bool frz = nondet_bool();
    return bs_assume_asset_holding(BS, addr, asset_id, bal, frz);
}

// ===========================================================================
// Transaction Group Builder — Symbolic Transaction Construction
// ===========================================================================

// ---------------------------------------------------------------------------
// txg_init: Zero-initialize a transaction group array.
// ---------------------------------------------------------------------------

inline void txg_init(Txn* tg, uint32_t count) {
    for (uint8_t i = 0; i < count; i++) {
        _cbmc_txn_zero(tg[i]);
        tg[i].GroupIndex = i;
    }
}

// ---------------------------------------------------------------------------
// txg_concretize_unused: Lock heavy, rarely-used Txn fields to their zero
// (memset) values. CBMC can constant-propagate these away, shrinking the SAT
// formula. Call after txg_init for each txn, then override specific fields
// as needed per-contract.
//
// Covers: keyreg fields (VotePK, SelectionPK, StateProofPK, ...),
//         acfg byte/address fields (ConfigAssetName, Manager, ...),
//         afrz fields (FreezeAsset, FreezeAssetAccount, ...),
//         Note, Lease, AssetSender.
// ---------------------------------------------------------------------------

inline void txg_concretize_unused(Txn& txn) {
    // Keyreg fields
    _cbmc_zero(txn.VotePK, 32);
    _cbmc_zero(txn.SelectionPK, 32);
    _cbmc_zero(txn.StateProofPK, 64);
    txn.VoteFirst = 0;
    txn.VoteLast = 0;
    txn.VoteKeyDilution = 0;
    txn.Nonparticipation = false;

    // Acfg fields
    txn.ConfigAssetNameLen = 0;
    txn.ConfigAssetUnitNameLen = 0;
    txn.ConfigAssetURLLen = 0;
    _cbmc_zero(txn.ConfigAssetMetadataHash, 32);
    _cbmc_zero(txn.ConfigAssetManager, 32);
    _cbmc_zero(txn.ConfigAssetReserve, 32);
    _cbmc_zero(txn.ConfigAssetFreeze, 32);
    _cbmc_zero(txn.ConfigAssetClawback, 32);
    txn.ConfigAssetDefaultFrozen = false;
    txn.ConfigAssetTotal = 0;
    txn.ConfigAssetDecimals = 0;
    txn.ConfigAsset = 0;

    // Afrz fields
    txn.FreezeAsset = 0;
    txn.FreezeAssetFrozen = false;
    _cbmc_zero(txn.FreezeAssetAccount, 32);

    // Note, Lease, AssetSender
    txn.NoteLen = 0;
    _cbmc_zero(txn.Lease, 32);
    _cbmc_zero(txn.AssetSender, 32);
}

// Convenience: concretize unused fields for all txns in a group.
inline void txg_concretize_unused_all(Txn* tg, uint32_t count) {
    for (uint32_t i = 0; i < count; i++) {
        txg_concretize_unused(tg[i]);
    }
}

// ---------------------------------------------------------------------------
// txg_symbolic_appcall: Set up a symbolic ABI application call.
//
// Creates a TypeEnum=6 (appl) transaction with:
//   - Symbolic OnCompletion (0-5)
//   - Symbolic app args (up to num_args, each up to 8 bytes)
//   - Symbolic Fee (>= 1000)
//   - Symbolic sender (32 nondeterministic bytes)
// ---------------------------------------------------------------------------

inline void txg_symbolic_appcall(Txn& txn, uint64_t app_id, uint8_t num_args) {
    txn.TypeEnum = 6;  // appl
    txn.ApplicationID = app_id;

    // Symbolic OnCompletion
    uint8_t oc = nondet_uint8();
    __CPROVER_assume(oc <= 5);
    txn.apan = oc;

    // Symbolic fee
    txn.Fee = nondet_uint64();
    __CPROVER_assume(txn.Fee >= 1000);

    // Symbolic amount
    txn.Amount = nondet_uint64();

    // Symbolic sender
    _cbmc_addr_nondet(txn.Sender);

    // Symbolic app args
    uint8_t nargs = num_args;
    if (nargs > CBMC_MAX_APP_ARGS) nargs = CBMC_MAX_APP_ARGS;
    txn.NumAppArgs = nargs;
    for (uint8_t a = 0; a < nargs; a++) {
        txn.AppArgLens[a] = 8;  // default 8 bytes per arg
        for (uint8_t j = 0; j < 8; j++) {
            txn.AppArgs[a][j] = nondet_uint8();
        }
    }
}

// ---------------------------------------------------------------------------
// txg_symbolic_pay: Set up a symbolic payment transaction.
// ---------------------------------------------------------------------------

inline void txg_symbolic_pay(Txn& txn) {
    txn.TypeEnum = 1;  // pay

    txn.Fee = nondet_uint64();
    __CPROVER_assume(txn.Fee >= 1000);

    txn.Amount = nondet_uint64();

    _cbmc_addr_nondet(txn.Sender);
    _cbmc_addr_nondet(txn.Receiver);
}

// ---------------------------------------------------------------------------
// txg_symbolic_axfer: Set up a symbolic asset transfer transaction.
//
// Creates a TypeEnum=4 (axfer) transaction with:
//   - Symbolic XferAsset, AssetAmount, AssetReceiver, AssetSender
//   - Symbolic Fee (>= 1000)
//   - Symbolic sender (32 nondeterministic bytes)
// ---------------------------------------------------------------------------

inline void txg_symbolic_axfer(Txn& txn) {
    txn.TypeEnum = 4;  // axfer

    txn.Fee = nondet_uint64();
    __CPROVER_assume(txn.Fee >= 1000);

    txn.XferAsset = nondet_uint64();
    txn.AssetAmount = nondet_uint64();

    _cbmc_addr_nondet(txn.Sender);
    _cbmc_addr_nondet(txn.AssetReceiver);
    _cbmc_addr_nondet(txn.AssetSender);
    _cbmc_zero(txn.AssetCloseTo, 32);  // default no close-to
}

// ---------------------------------------------------------------------------
// txg_symbolic_acfg: Set up a symbolic asset configuration transaction.
//
// Creates a TypeEnum=3 (acfg) transaction with:
//   - Symbolic ConfigAsset (0 = create, non-zero = reconfigure/destroy)
//   - Symbolic config fields (total, decimals, name, manager, etc.)
//   - Symbolic Fee (>= 1000)
//   - Symbolic sender (32 nondeterministic bytes)
// ---------------------------------------------------------------------------

inline void txg_symbolic_acfg(Txn& txn) {
    txn.TypeEnum = 3;  // acfg

    txn.Fee = nondet_uint64();
    __CPROVER_assume(txn.Fee >= 1000);

    txn.ConfigAsset = nondet_uint64();
    txn.ConfigAssetTotal = nondet_uint64();
    txn.ConfigAssetDecimals = nondet_uint64();
    txn.ConfigAssetDefaultFrozen = nondet_bool();

    _cbmc_addr_nondet(txn.Sender);
    _cbmc_addr_nondet(txn.ConfigAssetManager);
    _cbmc_addr_nondet(txn.ConfigAssetReserve);
    _cbmc_addr_nondet(txn.ConfigAssetFreeze);
    _cbmc_addr_nondet(txn.ConfigAssetClawback);
}

// ---------------------------------------------------------------------------
// txg_symbolic_afrz: Set up a symbolic asset freeze transaction.
//
// Creates a TypeEnum=5 (afrz) transaction with:
//   - Symbolic FreezeAsset, FreezeAssetAccount, FreezeAssetFrozen
//   - Symbolic Fee (>= 1000)
//   - Symbolic sender
// ---------------------------------------------------------------------------

inline void txg_symbolic_afrz(Txn& txn) {
    txn.TypeEnum = 5;  // afrz

    txn.Fee = nondet_uint64();
    __CPROVER_assume(txn.Fee >= 1000);

    txn.FreezeAsset = nondet_uint64();
    txn.FreezeAssetFrozen = nondet_bool();

    _cbmc_addr_nondet(txn.Sender);
    _cbmc_addr_nondet(txn.FreezeAssetAccount);
}

// ---------------------------------------------------------------------------
// Asset transfer constraint helpers
// ---------------------------------------------------------------------------

// Set the asset being transferred.
inline void txg_assume_xfer_asset(Txn& txn, uint64_t asset_id) {
    txn.XferAsset = asset_id;
}

// Set asset receiver to a specific address.
inline void txg_assume_asset_receiver(Txn& txn, const uint8_t* receiver) {
    _cbmc_bytecopy(txn.AssetReceiver, receiver, 32);
}

// Constrain asset amount to range [lo, hi].
inline void txg_assume_asset_amount_range(Txn& txn, uint64_t lo, uint64_t hi) {
    __CPROVER_assume(txn.AssetAmount >= lo && txn.AssetAmount <= hi);
}

// ---------------------------------------------------------------------------
// Transaction group constraint helpers
// ---------------------------------------------------------------------------

// Constrain all transactions in group to have the same sender.
inline void txg_assume_sender(Txn* tg, uint32_t count, const uint8_t* sender) {
    for (uint32_t i = 0; i < count; i++) {
        _cbmc_bytecopy(tg[i].Sender, sender, 32);
    }
}

// Constrain all transactions to have the same symbolic sender.
// (All txns in the group share sender identity.)
inline void txg_assume_same_sender(Txn* tg, uint32_t count) {
    if (count < 2) return;
    for (uint32_t i = 1; i < count; i++) {
        _cbmc_bytecopy(tg[i].Sender, tg[0].Sender, 32);
    }
}

// Constrain a transaction to use a specific ABI method selector.
inline void txg_assume_method(Txn& txn, uint8_t b0, uint8_t b1, uint8_t b2, uint8_t b3) {
    __CPROVER_assume(txn.NumAppArgs >= 1);
    __CPROVER_assume(txn.AppArgLens[0] >= 4);
    txn.AppArgs[0][0] = b0;
    txn.AppArgs[0][1] = b1;
    txn.AppArgs[0][2] = b2;
    txn.AppArgs[0][3] = b3;
}

// Constrain OnCompletion to NoOp (0).
inline void txg_assume_noop(Txn& txn) {
    txn.apan = 0;
}

// Constrain OnCompletion to a specific value.
inline void txg_assume_on_completion(Txn& txn, uint8_t oc) {
    txn.apan = oc;
}

// Set ApplicationID for an existing app call (non-zero = not a create).
inline void txg_assume_existing_app(Txn& txn, uint64_t app_id) {
    txn.ApplicationID = app_id;
    __CPROVER_assume(app_id != 0);
}

// Set payment receiver to a specific address.
inline void txg_assume_receiver(Txn& txn, const uint8_t* receiver) {
    _cbmc_bytecopy(txn.Receiver, receiver, 32);
}

// Constrain payment amount to range [lo, hi].
inline void txg_assume_amount_range(Txn& txn, uint64_t lo, uint64_t hi) {
    __CPROVER_assume(txn.Amount >= lo && txn.Amount <= hi);
}

// Set a concrete uint64 value in app arg at index (big-endian itob encoding).
inline void txg_set_arg_uint64(Txn& txn, uint8_t arg_idx, uint64_t value) {
    for (int i = 7; i >= 0; i--) {
        txn.AppArgs[arg_idx][i] = (uint8_t)(value & 0xFF);
        value >>= 8;
    }
    txn.AppArgLens[arg_idx] = 8;
}

// Set a concrete bytes value in app arg at index.
inline void txg_set_arg_bytes(Txn& txn, uint8_t arg_idx,
                               const uint8_t* data, uint8_t len) {
    _cbmc_bytecopy(txn.AppArgs[arg_idx], data, len);
    txn.AppArgLens[arg_idx] = len;
}


// ===========================================================================
// Composite Helpers — Common Verification Patterns
// ===========================================================================

// ---------------------------------------------------------------------------
// bs_valid_initial_state: Create a "sane" symbolic initial state.
// Combines bs_symbolic + bs_assume_sane_defaults.
// Users then add project-specific assumptions on top.
// ---------------------------------------------------------------------------

inline void bs_valid_initial_state(BlockchainState& BS) {
    bs_init(BS);
    bs_symbolic(BS);
    bs_assume_sane_defaults(BS);
}

// ---------------------------------------------------------------------------
// txg_valid_group: Create a valid symbolic transaction group.
//
// Sets up `count` transactions: txns[app_call_idx] is an app call with
// `num_args` symbolic args, all others are symbolic payments.
// All transactions share the same symbolic sender.
// ---------------------------------------------------------------------------

inline void txg_valid_group(Txn* tg, uint32_t count, uint32_t app_call_idx,
                             uint64_t app_id, uint8_t num_args) {
    txg_init(tg, count);
    for (uint32_t i = 0; i < count; i++) {
        if (i == app_call_idx) {
            txg_symbolic_appcall(tg[i], app_id, num_args);
        } else {
            txg_symbolic_pay(tg[i]);
        }
    }
    txg_assume_same_sender(tg, count);
}
