# Template Generator JSON Syntax Reference

Complete reference for the JSON configuration format used by the template generator
to produce C++ verification harness templates.

## Top-Level Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `preset` | `string` | `"default"` | Bound preset: `"minimal"`, `"default"`, or `"permissive"` |
| `bounds` | `object` | `{}` | Override individual CBMC bounds (merged on top of preset) |
| `mode` | `string` | `"application"` | `"application"` or `"logicsig"` |
| `app_id` | `int` | `1` | Application ID for the verified contract |
| `addresses` | `object` | `{}` | Named addresses used throughout the config |
| `creator_address` | `string` | `null` | Address name ref to set `ctx.CreatorAddress` |
| `app_address` | `string` | `null` | Address name ref to set `ctx.CurrentApplicationAddress` |
| `initial_state` | `object` | `{}` | Initial blockchain state configuration |
| `txn_group` | `object` | single appcall | Transaction group configuration |
| `lsig_args` | `object` | `null` | LogicSig arguments (implies `mode: "logicsig"`) |

---

## `preset`

Controls the base CBMC bounds. Individual bounds in `bounds` override these.

| Preset | Stack | Bytes | Globals | Boxes | Box Size | Use Case |
|--------|-------|-------|---------|-------|----------|----------|
| `"minimal"` | 16 | 32 | 4 | 4 | 64 | Fast iteration, small contracts |
| `"default"` | 32 | 128 | 16 | 4 | 64 | Balanced for most contracts |
| `"permissive"` | 1000 | 4096 | 64 | 8 | 32768 | Real AVM limits (very slow) |

---

## `bounds`

Override any CBMC bound by name. These are emitted as `#define` directives.
See `engine/cbmc_bounds.h` for the full list with documentation.

```json
{
    "bounds": {
        "CBMC_STACK_MAX": 32,
        "CBMC_BYTES_MAX": 64,
        "CBMC_MAX_GLOBALS": 28,
        "CBMC_MAX_BOXES": 8,
        "CBMC_BOX_MAX_SIZE": 128,
        "CBMC_MAX_FRAMES": 12,
        "CBMC_SCRATCH_SLOTS": 253,
        "CBMC_MAX_INNER_TXNS": 8,
        "CBMC_MAX_INNER_DEPTH": 2,
        "CBMC_MAX_ASSETS": 4,
        "CBMC_MAX_ASSET_HOLDINGS": 4,
        "CBMC_BMATH_MAX": 64
    }
}
```

All available bounds:

| Bound | Default | Minimal | Permissive | Description |
|-------|---------|---------|------------|-------------|
| `CBMC_STACK_MAX` | 32 | 16 | 1000 | Max stack depth |
| `CBMC_BYTES_MAX` | 128 | 32 | 4096 | Max byteslice length |
| `CBMC_SCRATCH_SLOTS` | 256 | 16 | 256 | Number of scratch space slots |
| `CBMC_MAX_APP_ARGS` | 8 | 4 | 16 | Max application arguments |
| `CBMC_MAX_GLOBALS` | 16 | 4 | 64 | Max global state entries (total) |
| `CBMC_GLOBAL_NUM_UINT` | 16 | 16 | 64 | Max global uint entries per schema |
| `CBMC_GLOBAL_NUM_BYTESLICE` | 16 | 16 | 64 | Max global byteslice entries per schema |
| `CBMC_LOCAL_NUM_UINT` | 16 | 16 | 16 | Max local uint entries per schema |
| `CBMC_LOCAL_NUM_BYTESLICE` | 16 | 16 | 16 | Max local byteslice entries per schema |
| `CBMC_MAX_LOCAL_ACCOUNTS` | 4 | 4 | 4 | Max accounts with local state |
| `CBMC_MAX_LOCAL_KEYS` | 4 | 4 | 16 | Max local state keys per account |
| `CBMC_MAX_LOGS` | 8 | 4 | 32 | Max log entries |
| `CBMC_MAX_LOG_LEN` | 256 | 32 | 1024 | Max log entry length |
| `CBMC_MAX_INNER_TXNS` | 4 | 4 | 256 | Max inner transactions |
| `CBMC_MAX_INNER_DEPTH` | 2 | 2 | 8 | Max inner app call recursion depth |
| `CBMC_MAX_FRAMES` | 8 | 8 | 256 | Max callsub nesting depth |
| `CBMC_MAX_BOXES` | 4 | 4 | 8 | Max concurrent boxes |
| `CBMC_BOX_MAX_SIZE` | 64 | 64 | 32768 | Max box data size |
| `CBMC_MAX_GROUP_SIZE` | 4 | 4 | 16 | Max transaction group size |
| `CBMC_MAX_ACCOUNTS` | 4 | 4 | 4 | Max accounts in state model |
| `CBMC_MAX_TXN_ACCOUNTS` | 4 | 4 | 4 | Max accounts array per txn |
| `CBMC_MAX_TXN_ASSETS` | 4 | 4 | 8 | Max assets array per txn |
| `CBMC_MAX_TXN_APPS` | 4 | 4 | 8 | Max apps array per txn |
| `CBMC_MAX_TXN_LOGS` | 4 | 4 | 32 | Max logs array per txn |
| `CBMC_MAX_LSIG_ARGS` | 4 | 4 | 255 | Max LogicSig arguments |
| `CBMC_MAX_ASSETS` | 4 | 4 | 8 | Max assets in asset params state |
| `CBMC_MAX_ASSET_HOLDINGS` | 4 | 4 | 8 | Max asset holdings in state model |
| `CBMC_BMATH_MAX` | 64 | 64 | 64 | Max byte math operand size |

---

## `addresses`

Named 32-byte Algorand addresses. Referenced by name in other fields.

```json
{
    "addresses": {
        "manager": [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
        "attacker": "symbolic"
    }
}
```

Each address is either:
- **Concrete**: `[b0, b1, ..., b31]` — a 32-element array of byte values (0-255)
- **Symbolic**: `"symbolic"` — nondeterministic, CBMC explores all possible values

Address names become C++ variables (`uint8_t name[32]`) and can be referenced
from `sender`, `receiver`, `manager`, `creator`, `asset_receiver`, etc. fields.

---

## `initial_state`

Configures the `BlockchainState BS` before contract execution.

```json
{
    "initial_state": {
        "init_mode": "symbolic",
        "app_balance": {"min": 100000},
        "latest_timestamp": 1700000000,
        "round": 100,
        "min_txn_fee": 1000,
        "min_balance": 100000,
        "max_txn_life": 1000,
        "group_size": 1,
        "globals": [...],
        "local_accounts": [...],
        "boxes": [...],
        "assets": [...],
        "asset_holdings": [...]
    }
}
```

### `init_mode`

| Mode | C++ Output | When to Use |
|------|-----------|-------------|
| `"symbolic"` | `bs_valid_initial_state(BS)` | Default. Symbolic state with sane Algorand defaults. |
| `"zero"` | `BlockchainState BS = {};` | Contracts with many globals (avoids `gs_init` loop). Requires explicit field setup. |
| `"init"` | `bs_init(BS)` | Zero-init data structures only (no symbolic fields). |

The deprecated `"zero_init": true` is equivalent to `"init_mode": "zero"`.

### `app_balance`

Three forms:

```json
"app_balance": 1000000
"app_balance": {"min": 100000}
"app_balance": {"min": 100000, "max": 999999}
"app_balance": {"value": 500000}
```

| Field | Type | Description |
|-------|------|-------------|
| (bare int) | `int` | Concrete balance |
| `value` | `int` | Concrete balance (same as bare int) |
| `min` | `int` | Minimum balance (`bs_assume_min_app_balance`) |
| `max` | `int` | Maximum balance (used with `min` for range) |

Note: `app_balance` is a legacy single-app shortcut. For multi-contract verification,
use `app_accounts` instead (see below).

### `app_accounts`

Register apps as accounts in `AccountsState`. In Algorand, apps ARE accounts — each has
its own address and balance. Use this for multi-contract verification where each app
needs an independent balance that gets debited by its own inner payments.

```json
"app_accounts": [
    {"app_id": 1, "address": "ADDR_APP", "balance": 10000000},
    {"app_id": 42, "address": "ADDR_INNER", "balance": {"min": 1000, "max": 999999}},
    {"app_id": 99, "address": "ADDR_OTHER"}
]
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `app_id` | `int` | **required** | Application ID |
| `address` | `string` | **required** | Address name ref (from `addresses` section) |
| `balance` | `int` or `object` | `null` | Balance constraint (see below) |

**Balance formats:**
- `42` or `{"value": 42}` — concrete balance
- `{"min": 1000, "max": 999999}` — bounded nondeterministic range
- omitted — fully symbolic (nondeterministic)

When an app is registered as an account, `_itxn_apply_effects` debits that account's
balance (via `acct_find`) instead of the global `BS.app_balance`. The `balance` opcode
and `acct_params_get AcctBalance` also return the correct per-app balance.

### `globals`

Array of global state variables to pre-populate.

```json
"globals": [
    {"key": "counter", "type": "int", "value": 42},
    {"key": "status", "type": "int", "range": [0, 100]},
    {"key": "total", "type": "int", "symbolic_var": "initial_total", "range": [0, 1000]},
    {"key": "admin", "type": "bytes", "hex": "AABBCCDD"},
    {"key": "tag", "type": "bytes", "value": [72, 101, 108, 108, 111]},
    {"key": "flag", "type": "int", "direct": false}
]
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `key` | `string` | **required** | Global state key name |
| `type` | `string` | `"int"` | `"int"` or `"bytes"` |
| `value` | `int` or `[int]` | `null` | Concrete value (int for ints, byte array for bytes) |
| `hex` | `string` | `null` | Hex-encoded byte value (bytes type only) |
| `range` | `[lo, hi]` | `null` | Nondeterministic value bounded to [lo, hi] (int type only) |
| `symbolic_var` | `string` | `null` | Named C++ variable for the value (accessible from `setup_code`) |
| `direct` | `bool` | `true` | Use `gs_put()` directly (avoids `_cbmc_strcopy` loop, lower unwind needed) |

**`symbolic_var` usage**: When set, emits `uint64_t name = nondet_uint64();` as a named
variable that can be referenced in `setup_code` passed to `verify_contract()`.

**`direct` mode** (default `true`): Emits `gs_put(BS.globals, (const uint8_t*)"key", len, value)`.
When `false`, uses `bs_assume_global_int(BS, "key", value)` which has an internal string-copy
loop requiring higher unwind bounds.

### `local_accounts`

Array of per-account local state setups.

```json
"local_accounts": [
    {
        "address": "sender",
        "opted_in": true,
        "keys": [
            {"key": "balance", "type": "int", "value": 500},
            {"key": "level", "type": "int", "range": [1, 10]},
            {"key": "score", "type": "int", "symbolic_var": "initial_score"},
            {"key": "data", "type": "bytes", "hex": "DEADBEEF"},
            {"key": "name", "type": "bytes", "value": [65, 66, 67]}
        ]
    }
]
```

**`local_accounts[*]` fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `address` | `string` | **required** | Reference to a named address |
| `opted_in` | `bool` | `true` | Whether the account is opted in (`bs_assume_local_opt_in`) |
| `keys` | `array` | `[]` | Local state key-value pairs |

**`keys[*]` fields** (same as globals, minus `direct`):

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `key` | `string` | **required** | Local state key name |
| `type` | `string` | `"int"` | `"int"` or `"bytes"` |
| `value` | `int` or `[int]` | `null` | Concrete value |
| `hex` | `string` | `null` | Hex-encoded byte value (bytes type only) |
| `range` | `[lo, hi]` | `null` | Nondeterministic bounded range (int type only) |
| `symbolic_var` | `string` | `null` | Named C++ variable for the value |

### `boxes`

Array of box storage entries.

```json
"boxes": [
    {"key_str": "metadata", "size": 128, "init": "zeros"},
    {"key_hex": "00000001", "size": 64, "init": "symbolic"},
    {"key_bytes": [0,0,0,1], "size": 64, "init": "absent"},
    {"key_str": "config", "data_hex": "FF00FF00AABB"},
    {"key_hex": "00000002", "data_bytes": [1, 2, 3, 4, 5, 6, 7, 8]}
]
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `key_str` | `string` | `null` | Box key as a string |
| `key_hex` | `string` | `null` | Box key as hex bytes |
| `key_bytes` | `[int]` | `null` | Box key as byte array |
| `size` | `int` | `64` | Box data size in bytes |
| `init` | `string` | `"zeros"` | Initialization mode (see below) |
| `data_hex` | `string` | `null` | Concrete data as hex (auto-sets `init: "data"`) |
| `data_bytes` | `[int]` | `null` | Concrete data as byte array (auto-sets `init: "data"`) |

Exactly one of `key_str`, `key_hex`, or `key_bytes` must be provided.

**Initialization modes:**

| Mode | Description | C++ |
|------|-------------|-----|
| `"zeros"` | Box exists, all bytes zero | `bs_assume_box_zeroed()` |
| `"symbolic"` | Box exists, all bytes nondeterministic | `bs_assume_box_symbolic()` |
| `"absent"` | Box does NOT exist | `bs_assume_box_absent()` |
| `"data"` | Box exists with concrete data | `bs_assume_box()` |

### `assets`

Array of assets in the asset params state model.

```json
"assets": [
    {"id": 123, "manager": "manager", "creator": "manager"},
    {"id": 456, "manager": "admin"}
]
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `int` | **required** | Asset ID |
| `manager` | `string` | `"manager"` | Address name ref for asset manager |
| `creator` | `string` | same as `manager` | Address name ref for asset creator |

### `asset_holdings`

Array of asset holdings for specific accounts.

```json
"asset_holdings": [
    {"address": "sender", "asset_id": 123, "balance": 1000, "frozen": false},
    {"address": "sender", "asset_id": 456}
]
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `address` | `string` | **required** | Address name ref for the account |
| `asset_id` | `int` | **required** | Asset ID |
| `balance` | `int` | `null` | Concrete balance (null = symbolic) |
| `frozen` | `bool` | `null` | Frozen flag (null = symbolic) |

When both `balance` and `frozen` are null, emits `bs_assume_asset_holding_symbolic()`.

---

## `txn_group`

Configures the transaction group sent to the contract.

```json
{
    "txn_group": {
        "transactions": [...],
        "app_index": 1,
        "same_sender": true
    }
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `transactions` | `array` | `[{appcall, 2 args}]` | Array of transaction configs |
| `app_index` | `int` | auto-detect | Index of the verified app call txn (null if none) |
| `same_sender` | `bool` | `false` | Force all txns to share the first txn's sender |

`app_index` auto-detects the first `appcall` transaction if omitted.

### Transaction: `pay`

Payment transaction. Base: `txg_symbolic_pay()`.

```json
{"type": "pay", "amount": 10000, "receiver": "manager", "close_to": "admin"}
{"type": "pay", "amount_range": [1000, 99999]}
{"type": "pay"}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `amount` | `int` | symbolic | Concrete payment amount |
| `amount_range` | `[lo, hi]` | - | Bounded nondeterministic amount |
| `receiver` | `string` | symbolic | Address name ref (or `"app"` for app address) |
| `close_to` | `string` | `null` | Address name ref for CloseRemainderTo |

### Transaction: `appcall`

Application call transaction. This is the main transaction type for contract verification.

```json
{
    "type": "appcall",
    "num_args": 4,
    "arg_sizes": [4, 8, 8, 32],
    "on_completion": "noop",
    "method_selectors": ["8636ADC3", "CA6A3910", "D15EDEFC"],
    "sender": "attacker"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `num_args` | `int` | `2` | Number of application arguments |
| `arg_sizes` | `[int]` | `[8] * num_args` | Size in bytes of each argument |
| `on_completion` | `string` or `int` | `"symbolic"` | OnCompletion value (see below) |
| `method_selectors` | `[string]` or `[array]` | `null` | Allowed ABI method selectors (see below) |
| `method_selector` | `string` or `[int]` | `null` | Single method selector (shorthand, see below) |
| `sender` | `string` | `null` | Address name ref for transaction sender |

**`on_completion` values:**

| Value | Description |
|-------|-------------|
| `"symbolic"` | Nondeterministic (0-5), CBMC explores all |
| `"noop"` | NoOp (0) |
| `0`-`5` | Concrete OnCompletion value |

OnCompletion numeric mapping: 0=NoOp, 1=OptIn, 2=CloseOut, 3=ClearState, 4=UpdateApplication, 5=DeleteApplication.

**`method_selectors` / `method_selector`:**

Constrains `AppArgs[0]` to one or more 4-byte ABI method selectors. This prevents
CBMC from exploring the routing logic for impossible selectors, significantly
reducing solving time.

Use `method_selectors` (plural) to allow a set of methods:

```json
"method_selectors": ["8636ADC3", "CA6A3910", "D15EDEFC"]
```

This emits a `__CPROVER_assume` that constrains the first 4 bytes of `AppArgs[0]`
to be one of the listed selectors. CBMC explores all allowed methods but skips
unknown ones. Mixed formats (hex strings and byte arrays) are accepted:

```json
"method_selectors": ["8636ADC3", [0xCA, 0x6A, 0x39, 0x10]]
```

Use `method_selector` (singular) as shorthand for a single-method constraint:

```json
"method_selector": "8636ADC3"
"method_selector": [134, 54, 173, 195]
```

**Behavior by count:**
- **Single selector**: Hardcodes the 4 bytes directly (assignment, no assume).
- **Multiple selectors**: Emits `__CPROVER_assume(_ms == 0x... || _ms == 0x... || ...)`.
- **No selector**: AppArgs[0] is fully nondeterministic (CBMC explores all 2^32 values).

The constraint is applied AFTER nondeterministic arg fill. When using selectors,
`arg_sizes[0]` should be at least 4 (the first 4 bytes are the selector;
remaining bytes stay nondeterministic).

Individual tests can further pin to a single method via `setup_code` by overwriting
`AppArgs[0][0..3]` with concrete bytes — this is compatible with the template's
assume-or constraint since the pinned value is one of the allowed selectors.

### Transaction: `axfer`

Asset transfer transaction. Base: `txg_symbolic_axfer()`.

```json
{"type": "axfer", "xfer_asset": 123, "asset_amount": 500, "asset_receiver": "sender"}
{"type": "axfer", "asset_amount_range": [0, 1000000]}
{"type": "axfer", "xfer_asset": 123, "asset_sender": "clawback", "asset_close_to": "admin"}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `xfer_asset` | `int` | symbolic | Asset ID being transferred |
| `asset_amount` | `int` | symbolic | Concrete transfer amount |
| `asset_amount_range` | `[lo, hi]` | - | Bounded nondeterministic amount |
| `asset_receiver` | `string` | symbolic | Address name ref for asset receiver |
| `asset_sender` | `string` | `null` | Address name ref for clawback sender |
| `asset_close_to` | `string` | `null` | Address name ref for AssetCloseTo |

### Transaction: `acfg`

Asset configuration transaction. Base: `txg_symbolic_acfg()`.

```json
{"type": "acfg", "config_asset": 123, "manager": "admin", "reserve": "treasury"}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `config_asset` | `int` | symbolic | Asset ID being configured |
| `manager` | `string` | symbolic | Address name ref for new manager |
| `reserve` | `string` | symbolic | Address name ref for new reserve |
| `freeze` | `string` | symbolic | Address name ref for new freeze |
| `clawback` | `string` | symbolic | Address name ref for new clawback |

### Transaction: `afrz`

Asset freeze transaction. Base: `txg_symbolic_afrz()`.

```json
{"type": "afrz", "freeze_asset": 123, "freeze_account": "sender", "frozen": true}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `freeze_asset` | `int` | symbolic | Asset ID being frozen/unfrozen |
| `freeze_account` | `string` | symbolic | Address name ref for account to freeze |
| `frozen` | `bool` | symbolic | Freeze flag (true=freeze, false=unfreeze) |

---

## `lsig_args`

LogicSig argument setup. Presence implies `mode: "logicsig"`.

```json
{
    "mode": "logicsig",
    "lsig_args": {
        "num_args": 2,
        "arg_sizes": [8, 32]
    }
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `num_args` | `int` | `2` | Number of LogicSig arguments |
| `arg_sizes` | `[int]` | `[8] * num_args` | Size in bytes of each argument |

In LogicSig mode:
- `app_id` is set to 0
- No `CurrentApplicationID` is set on the eval context
- `ctx.LsigArgs` is populated with nondeterministic arguments of specified sizes
- The transaction group represents the transaction(s) being authorized

---

## Complete Examples

### Minimal (fast iteration)

```json
{
    "preset": "minimal",
    "txn_group": {
        "transactions": [
            {"type": "appcall", "num_args": 2, "arg_sizes": [4, 8]}
        ]
    }
}
```

### ABI method-targeted verification

```json
{
    "preset": "default",
    "app_id": 1,
    "addresses": {
        "manager": [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
        "attacker": "symbolic"
    },
    "initial_state": {
        "app_balance": {"min": 100000},
        "globals": [
            {"key": "admin", "type": "bytes", "value": [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1]}
        ],
        "assets": [
            {"id": 100, "manager": "manager"}
        ]
    },
    "txn_group": {
        "transactions": [
            {"type": "pay", "receiver": "app"},
            {
                "type": "appcall",
                "num_args": 4,
                "arg_sizes": [4, 8, 8, 32],
                "on_completion": "noop",
                "method_selectors": ["8636ADC3", "CA6A3910", "D15EDEFC"]
            }
        ],
        "same_sender": true
    }
}
```

The template constrains CBMC to only explore the 3 listed methods. Individual
tests can further pin to one method via `setup_code`.

### Multi-txn group with access control

```json
{
    "preset": "default",
    "app_id": 42,
    "bounds": {
        "CBMC_MAX_GLOBALS": 28,
        "CBMC_MAX_BOXES": 8,
        "CBMC_BYTES_MAX": 64
    },
    "addresses": {
        "arranger": [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
        "investor": "symbolic"
    },
    "creator_address": "arranger",
    "initial_state": {
        "init_mode": "zero",
        "app_balance": {"min": 1000000, "max": 999999999},
        "globals": [
            {"key": "status", "type": "int", "value": 100},
            {"key": "total_units", "type": "int", "value": 1000},
            {"key": "circulating", "type": "int", "range": [0, 1000], "symbolic_var": "initial_circ"}
        ],
        "local_accounts": [
            {
                "address": "investor",
                "opted_in": true,
                "keys": [
                    {"key": "units", "type": "int", "range": [0, 100]}
                ]
            }
        ],
        "boxes": [
            {"key_str": "config", "size": 64, "init": "symbolic"},
            {"key_hex": "524D0001", "data_bytes": [1,0,0,0,0,0,0,0]}
        ],
        "assets": [
            {"id": 200, "manager": "arranger", "creator": "arranger"}
        ],
        "asset_holdings": [
            {"address": "investor", "asset_id": 200, "balance": 500}
        ]
    },
    "txn_group": {
        "transactions": [
            {"type": "pay", "amount_range": [0, 1000000], "receiver": "app"},
            {
                "type": "appcall",
                "num_args": 4,
                "arg_sizes": [4, 32, 8, 8],
                "on_completion": "noop",
                "method_selectors": ["ABCDEF01", "12345678"],
                "sender": "investor"
            }
        ],
        "app_index": 1,
        "same_sender": true
    }
}
```

### LogicSig

```json
{
    "preset": "minimal",
    "mode": "logicsig",
    "lsig_args": {
        "num_args": 1,
        "arg_sizes": [1]
    },
    "txn_group": {
        "transactions": [
            {"type": "pay"}
        ]
    }
}
```

---

## Generated Output

The generator produces a C++ file with these placeholders for the transpiler:

| Placeholder | Filled By | Description |
|-------------|-----------|-------------|
| `//Function prototypes` | Transpiler | Transpiled TEAL function declarations |
| `//CONTRACT_CALL_PLACEHOLDER` | Transpiler | Contract entry point invocation |
| `//PROPERTIES_PLACEHOLDER` | `write_verify()` | User property function definitions |
| `//PROPERTY_CHECKS_PLACEHOLDER` | `write_verify()` | `__CPROVER_assert(...)` calls |
| `//METHOD_CONSTRAINT_PLACEHOLDER` | `setup_code` param | Custom C++ setup code |

Properties and `setup_code` are NOT part of the JSON config. They are passed separately
to `write_verify()` or `verify_contract()` at verification time. The JSON config defines
the static harness structure; properties and setup code define what to verify per-test.
