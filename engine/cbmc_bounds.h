// cbmc_bounds.h — All tunable bounds for CBMC verification.
//
// These control the size of fixed arrays in the AVM model. Smaller values
// make CBMC faster (fewer symbolic variables, shorter loops) but may
// truncate the state space. Templates override these with #define before
// #include "cbmc_bounds.h" (or "cbmc_avm.h" which includes this).
//
// Each bound documents:
//   - What it controls
//   - Where it's primarily used
//   - Real Algorand AVM limit (for reference)
//   - Performance impact (how much increasing it costs)

#pragma once

// ---------------------------------------------------------------------------
// Stack & Values
// ---------------------------------------------------------------------------

// Max operand stack depth.
// Used: Stack struct (array of StackValue), stack_push/stack_pop bounds check.
// AVM limit: 1000. Impact: HIGH — each slot is a full StackValue (~4KB at BYTES_MAX=4096).
#ifndef CBMC_STACK_MAX
#define CBMC_STACK_MAX 32
#endif

// Max byteslice length (bytes per StackValue, box key, log entry, etc.).
// Used: StackValue.byteslice[], GlobalEntry.key[], BoxEntry.key[], app args.
// AVM limit: 4096. Impact: VERY HIGH — appears in every StackValue, multiplied by stack/globals/locals.
#ifndef CBMC_BYTES_MAX
#define CBMC_BYTES_MAX 128
#endif

// Max byte-math operand size (b+, b-, b*, b/).
// Used: bmath_add, bmath_sub, bmath_mul, bmath_divmod operand buffers.
// AVM limit: 64 (512-bit arithmetic). Impact: LOW — only affects byte math ops.
#ifndef CBMC_BMATH_MAX
#define CBMC_BMATH_MAX 64
#endif

// ---------------------------------------------------------------------------
// Scratch Space
// ---------------------------------------------------------------------------

// Number of scratch space slots (store/load).
// Used: EvalContext.sp[] array.
// AVM limit: 256. Impact: MODERATE — 256 StackValues, but most contracts use few slots.
#ifndef CBMC_SCRATCH_SLOTS
#define CBMC_SCRATCH_SLOTS 16
#endif

// ---------------------------------------------------------------------------
// Subroutine Frames
// ---------------------------------------------------------------------------

// Max callsub nesting depth.
// Used: EvalContext.frames[] array, proto/retsub frame management.
// AVM limit: ~unlimited (bounded by stack). Impact: LOW — small struct per frame.
#ifndef CBMC_MAX_FRAMES
#define CBMC_MAX_FRAMES 8
#endif

// ---------------------------------------------------------------------------
// Global State
// ---------------------------------------------------------------------------

// Max global state key-value entries (total across uint + bytes).
// Used: GlobalState.entries[] array, gs_get/gs_put loop bounds.
// AVM limit: 64 uint + 64 bytes = 128 total. Impact: HIGH — each entry has a full StackValue.
#ifndef CBMC_MAX_GLOBALS
#define CBMC_MAX_GLOBALS 16
#endif

// Max global uint entries allowed by schema enforcement.
// Used: app_global_put schema check (counts existing uint entries).
// AVM limit: 64. Impact: LOW — only affects schema enforcement loop.
#ifndef CBMC_GLOBAL_NUM_UINT
#define CBMC_GLOBAL_NUM_UINT 16
#endif

// Max global byteslice entries allowed by schema enforcement.
// Used: app_global_put schema check (counts existing bytes entries).
// AVM limit: 64. Impact: LOW — only affects schema enforcement loop.
#ifndef CBMC_GLOBAL_NUM_BYTESLICE
#define CBMC_GLOBAL_NUM_BYTESLICE 16
#endif

// ---------------------------------------------------------------------------
// Local State
// ---------------------------------------------------------------------------

// Max accounts with local state (per app).
// Used: LocalState.accounts[] array, ls_find_account loop bounds.
// AVM limit: 4 per transaction (sender + 3 foreign). Impact: HIGH — each account has local keys.
#ifndef CBMC_MAX_LOCAL_ACCOUNTS
#define CBMC_MAX_LOCAL_ACCOUNTS 4
#endif

// Max local state keys per account.
// Used: LocalEntry.entries[] array, ls_get/ls_put loop bounds.
// AVM limit: 16 uint + 16 bytes = 32 total. Impact: MODERATE — each key has a full StackValue.
#ifndef CBMC_MAX_LOCAL_KEYS
#define CBMC_MAX_LOCAL_KEYS 4
#endif

// Max local uint entries allowed by schema enforcement.
// Used: app_local_put schema check.
// AVM limit: 16. Impact: LOW.
#ifndef CBMC_LOCAL_NUM_UINT
#define CBMC_LOCAL_NUM_UINT 16
#endif

// Max local byteslice entries allowed by schema enforcement.
// Used: app_local_put schema check.
// AVM limit: 16. Impact: LOW.
#ifndef CBMC_LOCAL_NUM_BYTESLICE
#define CBMC_LOCAL_NUM_BYTESLICE 16
#endif

// ---------------------------------------------------------------------------
// Box Storage
// ---------------------------------------------------------------------------

// Max concurrent boxes in the state model.
// Used: BoxState.entries[] array, box_find loop bounds.
// AVM limit: 8 references per transaction group. Impact: MODERATE — each box has BOX_MAX_SIZE data.
#ifndef CBMC_MAX_BOXES
#define CBMC_MAX_BOXES 4
#endif

// Max box data size in bytes.
// Used: BoxEntry.data[] array, box_create/box_put bounds.
// AVM limit: 32768 (32 KB). Impact: VERY HIGH — directly sizes each box's data buffer.
#ifndef CBMC_BOX_MAX_SIZE
#define CBMC_BOX_MAX_SIZE 64
#endif

// ---------------------------------------------------------------------------
// Transaction Group
// ---------------------------------------------------------------------------

// Max transactions per atomic group.
// Used: TxnGroup.txns[] array, gtxn/gtxns index bounds.
// AVM limit: 16. Impact: MODERATE — each Txn struct is large (~2KB+).
#ifndef CBMC_MAX_GROUP_SIZE
#define CBMC_MAX_GROUP_SIZE 4
#endif

// ---------------------------------------------------------------------------
// Transaction Fields
// ---------------------------------------------------------------------------

// Max application call arguments.
// Used: Txn.AppArgs[][] and Txn.AppArgLens[] arrays.
// AVM limit: 16. Impact: MODERATE — each arg is BYTES_MAX bytes.
#ifndef CBMC_MAX_APP_ARGS
#define CBMC_MAX_APP_ARGS 8
#endif

// Max foreign accounts per transaction.
// Used: Txn.Accounts[][] array, account reference resolution.
// AVM limit: 4. Impact: LOW — 4 × 32 bytes.
#ifndef CBMC_MAX_TXN_ACCOUNTS
#define CBMC_MAX_TXN_ACCOUNTS 4
#endif

// Max foreign assets per transaction.
// Used: Txn.Assets[] array.
// AVM limit: 8. Impact: LOW — 8 × uint64.
#ifndef CBMC_MAX_TXN_ASSETS
#define CBMC_MAX_TXN_ASSETS 4
#endif

// Max foreign apps per transaction.
// Used: Txn.Applications[] array.
// AVM limit: 8. Impact: LOW — 8 × uint64.
#ifndef CBMC_MAX_TXN_APPS
#define CBMC_MAX_TXN_APPS 4
#endif

// Max log entries accessible per transaction (for gtxn log access).
// Used: Txn.TxnLogLens[] array.
// AVM limit: 32. Impact: LOW.
#ifndef CBMC_MAX_TXN_LOGS
#define CBMC_MAX_TXN_LOGS 4
#endif

// ---------------------------------------------------------------------------
// Accounts
// ---------------------------------------------------------------------------

// Max accounts in the account state model (for balance/min_balance tracking).
// Used: AccountsState.entries[] array, acct_find loop bounds.
// AVM limit: depends on references. Impact: LOW — small struct per account.
#ifndef CBMC_MAX_ACCOUNTS
#define CBMC_MAX_ACCOUNTS 4
#endif

// ---------------------------------------------------------------------------
// Assets
// ---------------------------------------------------------------------------

// Max assets in the asset params state model.
// Used: AssetParamsState.entries[] array, aps_find loop bounds.
// AVM limit: depends on references. Impact: LOW — fixed struct per asset.
#ifndef CBMC_MAX_ASSETS
#define CBMC_MAX_ASSETS 4
#endif

// Max asset holdings in the holding state model.
// Used: AssetHoldingState.entries[] array, ahs_find loop bounds.
// AVM limit: depends on references. Impact: LOW — small struct per holding.
#ifndef CBMC_MAX_ASSET_HOLDINGS
#define CBMC_MAX_ASSET_HOLDINGS 4
#endif

// ---------------------------------------------------------------------------
// Logging
// ---------------------------------------------------------------------------

// Max log entries per app call.
// Used: EvalContext.Logs[][] array, log opcode bounds.
// AVM limit: 32. Impact: MODERATE — each log is MAX_LOG_LEN bytes.
#ifndef CBMC_MAX_LOGS
#define CBMC_MAX_LOGS 8
#endif

// Max single log entry length in bytes.
// Used: EvalContext.Logs[][CBMC_MAX_LOG_LEN] array.
// AVM limit: 1024. Impact: MODERATE — multiplied by MAX_LOGS.
#ifndef CBMC_MAX_LOG_LEN
#define CBMC_MAX_LOG_LEN 256
#endif

// ---------------------------------------------------------------------------
// Inner Transactions
// ---------------------------------------------------------------------------

// Max inner transactions per group.
// Used: EvalContext.inner_txns[] array.
// AVM limit: 256. Impact: HIGH — each InnerTxn contains a full Txn struct.
#ifndef CBMC_MAX_INNER_TXNS
#define CBMC_MAX_INNER_TXNS 4
#endif

// Max inner app call recursion depth.
// Used: _cbmc_dispatch_inner_app recursion guard.
// AVM limit: 8. Impact: LOW — just a counter check.
#ifndef CBMC_MAX_INNER_DEPTH
#define CBMC_MAX_INNER_DEPTH 2
#endif

// ---------------------------------------------------------------------------
// Constant Blocks
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// LogicSig Arguments
// ---------------------------------------------------------------------------

// Max logic signature arguments.
// Used: EvalContext.LsigArgs[][] array, arg/args opcodes.
// AVM limit: 255. Impact: MODERATE — each arg is BYTES_MAX bytes.
#ifndef CBMC_MAX_LSIG_ARGS
#define CBMC_MAX_LSIG_ARGS 4
#endif
