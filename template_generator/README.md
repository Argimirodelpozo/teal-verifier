# Template Generator

Generates C++ verification harness templates from JSON configuration.
The generated template is used with `write_verify()` or `verify_contract.py`
to verify properties of TEAL smart contracts.

## Usage

```bash
# Generate from JSON config to file
python template-generator/generator.py config.json -o my_template.cpp

# Print to stdout
python template-generator/generator.py config.json

# Override preset from CLI
python template-generator/generator.py config.json --preset permissive -o template.cpp

# Use the generated template with the verifier
python verify_contract.py my_contract.teal --template my_template.cpp --property "true" --unwind 20
```

## JSON Configuration Schema

### Presets

Three bound presets control the CBMC search space size:

| Preset | Stack | Bytes | Globals | Boxes | Box Size | Description |
|--------|-------|-------|---------|-------|----------|-------------|
| `minimal` | 16 | 32 | 4 | 4 | 64 | Fast iteration, small contracts |
| `default` | 32 | 128 | 16 | 4 | 64 | Balanced for most contracts |
| `permissive` | 1000 | 4096 | 64 | 8 | 32768 | Real AVM limits (slow) |

Individual bounds can always be overridden via the `bounds` field.
See `engine/cbmc_bounds.h` for the full list with documentation.

### Full Schema

```json
{
    "preset": "default",

    "bounds": {
        "CBMC_STACK_MAX": 32,
        "CBMC_BYTES_MAX": 128
    },

    "app_id": 1,

    "addresses": {
        "manager": [1,2,...,32],
        "sender": "symbolic"
    },

    "creator_address": "manager",

    "initial_state": {
        "zero_init": false,
        "app_balance": 1000000,
        "latest_timestamp": 1700000000,
        "round": 100,
        "min_txn_fee": 1000,
        "min_balance": 100000,
        "max_txn_life": 1000,
        "group_size": 1,

        "globals": [
            {"key": "counter", "type": "int", "value": 42},
            {"key": "status", "type": "int", "range": [0, 100]},
            {"key": "admin", "type": "bytes", "hex": "AABB..."},
            {"key": "tag", "type": "bytes", "value": [72, 101, 108, 108, 111]}
        ],

        "local_accounts": [
            {
                "address": "sender",
                "opted_in": true,
                "keys": [
                    {"key": "balance", "type": "int", "value": 500},
                    {"key": "level", "type": "int", "range": [1, 10]},
                    {"key": "data", "type": "bytes", "hex": "DEADBEEF"},
                    {"key": "name", "type": "bytes", "value": [65, 66, 67]}
                ]
            }
        ],

        "boxes": [
            {"key_str": "metadata", "size": 128, "init": "zeros"},
            {"key_hex": "00000001", "size": 64, "init": "symbolic"},
            {"key_bytes": [0,0,0,1], "size": 64, "init": "absent"},
            {"key_str": "config", "data_hex": "FF00FF00AABB"},
            {"key_hex": "00000002", "data_bytes": [1, 2, 3, 4, 5, 6, 7, 8]}
        ],

        "assets": [
            {"id": 123, "manager": "manager", "creator": "manager"}
        ],

        "asset_holdings": [
            {"address": "sender", "asset_id": 123, "balance": 1000, "frozen": false},
            {"address": "sender", "asset_id": 456}
        ]
    },

    "txn_group": {
        "transactions": [
            {"type": "pay"},
            {"type": "pay", "amount": 10000, "receiver": "manager"},
            {"type": "pay", "amount_range": [1000, 99999]},

            {"type": "appcall", "num_args": 4, "arg_sizes": [4,8,8,32],
             "on_completion": "symbolic"},
            {"type": "appcall", "on_completion": "noop",
             "method_selectors": ["8636ADC3", "CA6A3910"]},
            {"type": "appcall", "on_completion": 0,
             "method_selector": "8636ADC3"},

            {"type": "axfer", "xfer_asset": 123, "asset_receiver": "sender"},
            {"type": "axfer", "asset_amount_range": [0, 1000000]},

            {"type": "acfg", "config_asset": 123, "manager": "manager"},

            {"type": "afrz", "freeze_asset": 123, "freeze_account": "sender",
             "frozen": true}
        ],
        "app_index": 1,
        "same_sender": true
    }
}
```

### Transaction Types

All transaction types start with a symbolic base (via `txg_symbolic_*`) and
then apply concrete constraints from the JSON.

| Type | Base | Configurable Fields |
|------|------|-------------------|
| `pay` | `txg_symbolic_pay` | `amount`, `amount_range`, `receiver`, `close_to` |
| `axfer` | `txg_symbolic_axfer` | `xfer_asset`, `asset_amount`, `asset_amount_range`, `asset_receiver`, `asset_sender`, `asset_close_to` |
| `acfg` | `txg_symbolic_acfg` | `config_asset`, `manager`, `reserve`, `freeze`, `clawback` |
| `afrz` | `txg_symbolic_afrz` | `freeze_asset`, `freeze_account`, `frozen` |
| `appcall` | manual setup | `num_args`, `arg_sizes`, `on_completion`, `method_selectors`, `method_selector`, `sender` |

### Addresses

Addresses can be:
- **Concrete**: `[1,2,...,32]` — a 32-byte array
- **Symbolic**: `"symbolic"` — nondeterministic (CBMC explores all values)

Address names are used by reference in other fields (e.g., `"receiver": "manager"`).

### LogicSig Mode

Set `"mode": "logicsig"` (or include `"lsig_args"`) to generate a LogicSig
verification harness instead of an application call harness.

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

Differences from application mode:
- No `CurrentApplicationID` is set on the evaluation context
- `ctx.LsigArgs` is populated with symbolic arguments of the specified sizes
- `app_id` is 0 in the generated template
- The transaction group represents the transaction(s) being authorized

The transpiler can auto-detect LogicSig mode via `detect_contract_mode(source)`,
which checks for `arg`/`arg_0..3`/`args` opcodes (LogicSig-only) vs app-only
opcodes (`app_global_get`, `itxn_begin`, etc.).

### Notes

- The `app_index` field in `txn_group` specifies which transaction is the
  verified app call. If omitted, the generator auto-detects the first `appcall`.
  It can be `null` if there is no app call in the group.
- Properties and `setup_code` are NOT part of the JSON — they are passed
  separately to `write_verify()` at verification time.
- The generated template contains all 5 standard placeholders:
  `//Function prototypes`, `//PROPERTIES_PLACEHOLDER`, `//CONTRACT_CALL_PLACEHOLDER`,
  `//PROPERTY_CHECKS_PLACEHOLDER`, `//METHOD_CONSTRAINT_PLACEHOLDER`.

## Example Configs

See `examples/template_configs/` for ready-to-use configurations:
- `minimal.json` — fast iteration with small bounds
- `council_like.json` — council-style with addresses, globals, assets
- `permissive.json` — full AVM bounds (for reference, very slow)
- `logicsig.json` — LogicSig with symbolic arguments
