# teal-verifier

> **EXPERIMENTAL**: This project is in early development and should not be relied upon for production security decisions. APIs, verification semantics, and supported opcodes may change without notice. Use at your own risk.

Formal verification of Algorand TEAL smart contracts using [CBMC](https://www.cprover.org/cbmc/) (C Bounded Model Checker).

## Overview

teal-verifier transpiles TEAL bytecode into C++ and uses CBMC to formally verify user-defined properties hold for **all possible inputs** (up to a bounded search depth).

Unlike fuzz testing or unit testing, formal verification provides mathematical guarantees: if CBMC says **VERIFIED**, the property holds for every reachable state. If it says **FAILED**, it provides a concrete counterexample showing exactly how the property can be violated.

**Architecture**: Three-layer system:
- **Transpiler** (`cbmc_transpiler/AVMTranspiler.py`): TEAL -> C++ via tree-sitter-teal (~120 opcodes, all TEAL v10 control flow)
- **Engine** (`engine/`): Bounded AVM model (data structures, opcode implementations, property helpers, state builders)
- **CLI** (`cli/`): CBMC orchestration (compile with goto-cc, verify with cbmc, parse results)

## Prerequisites

- Python 3.10+
- [CBMC](https://www.cprover.org/cbmc/) (includes `cbmc` and `goto-cc` binaries)
- A C toolchain (needed to build `tree-sitter-teal` from source)
- **Git** (used by `pip` to fetch `tree-sitter-teal` from GitHub)

## Installation

### 1. Install CBMC

Download from [cprover.org/cbmc](https://www.cprover.org/cbmc/) or install via package manager:

```bash
# Ubuntu/Debian
sudo apt install cbmc

# macOS
brew install cbmc

# Or download binaries and place cbmc + goto-cc on your PATH
```

Verify: `cbmc --version` and `goto-cc --version` should both work.

### 2. Clone and install

```bash
git clone https://github.com/Argimirodelpozo/teal-verifier.git
cd teal-verifier
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
```

This installs `tree-sitter`, `tree-sitter-teal`, and `pytest`.

### 3. Verify the sample contract

```bash
python -m cli.verify_contract examples/counter.teal --property "true" --unwind 15 --property-only
```

If your environment exposes the CLI on `PATH`, you can also run:

```bash
teal-verify examples/counter.teal --property "true" --unwind 15 --property-only
```

## Walkthrough: Finding a Bug in a TEAL Contract

This section walks through the full verification workflow: writing a contract, defining properties, running the verifier, and interpreting results.

### 1. The Contract

Here's a simple counter contract. On each call it increments a global `"counter"` variable:

```teal
#pragma version 10
txn ApplicationID
bz create
txn OnCompletion
pushint 0
==
bz reject

// Increment counter
pushbytes "counter"
pushbytes "counter"
app_global_get
pushint 1
+
app_global_put
pushint 1
return

create:
pushbytes "counter"
pushint 0
app_global_put
pushint 1
return

reject:
pushint 0
return
```

A ready-made copy is included at `examples/counter.teal`.

### 2. Sanity Check: Does It Panic?

First, verify the contract doesn't crash on any input. The property `"true"` is trivially true -- this just checks for panics and assertion failures:

```bash
teal-verify examples/counter.teal --property "true" --unwind 15 --property-only
```

```
Transpiling examples/counter.teal...
Running CBMC (unwind=15, timeout=300s)...

VERIFIED: All properties hold for all inputs (up to unwind bound 15)
```

The contract handles all inputs without panicking.

### 3. Verify a Correct Property

Now verify something meaningful: the counter should only ever increase (monotonically non-decreasing). The property pattern is `ctx.result != ACCEPT || <condition>` -- "if the contract accepts, then the condition must hold":

```bash
teal-verify examples/counter.teal \
  --property 'ctx.result != ACCEPT || prop_global_int_monotonic_inc(ctx.bs_before, ctx.bs_after, "counter")' \
  --unwind 15 --property-only
```

```
VERIFIED: All properties hold for all inputs (up to unwind bound 15)
```

CBMC exhaustively explored all possible inputs and confirmed: the counter never decreases.

### 4. Catch a Bug: Unauthorized State Mutation

Now let's check a property that should **fail**. Suppose this contract is meant to be read-only for unauthorized callers, and we want to verify that no global state changes. We use `prop_all_globals_unchanged`:

```bash
teal-verify examples/counter.teal \
  --property 'ctx.result != ACCEPT || prop_all_globals_unchanged(ctx.bs_before, ctx.bs_after)' \
  --unwind 15 --property-only --stop-on-fail
```

```
FAILED: Property violation found!

Violated property:
  ctx.result != ACCEPT || prop_all_globals_unchanged(ctx.bs_before, ctx.bs_after)

VERIFICATION FAILED
```

CBMC found a counterexample: **any** caller can invoke the contract, it accepts, and it modifies the `"counter"` global. This is expected behavior for this contract, but if you intended state changes to be restricted (e.g., admin-only), this would be a real bug.

### 5. Get a Detailed Trace

Add `--trace` to see the exact execution path CBMC used to violate the property:

```bash
teal-verify examples/counter.teal \
  --property 'ctx.result != ACCEPT || prop_all_globals_unchanged(ctx.bs_before, ctx.bs_after)' \
  --unwind 15 --property-only --stop-on-fail --trace
```

The trace shows the complete state at each step: which opcodes executed, what values were on the stack, and how global state changed. Key excerpt:

```
gs_put(BS.globals, key.byteslice, 7, {.value=1, ._is_bytes=FALSE})
  ...
  vctx.bs_after.globals.entries[0].active=TRUE
  ...
  return_value_prop_all_globals_unchanged=FALSE
```

This confirms: `gs_put` was called (the counter was written), which caused `prop_all_globals_unchanged` to return `FALSE`, violating the property.

### 6. Understanding Results

| Result | Meaning |
|--------|---------|
| **VERIFIED** | Property holds for **all** inputs up to the unwind bound. Mathematical guarantee. |
| **FAILED** | CBMC found a concrete input that violates the property. Inspect the counterexample. |
| **Timeout** | CBMC ran out of time. Try reducing bounds, constraining inputs, or increasing `--timeout`. |

## Soundness

The verification uses **sound over-approximation**: crypto operations (SHA-256, Ed25519, etc.) and unconfigured external lookups return **nondeterministic values** -- CBMC explores all possible return values simultaneously.

- **VERIFIED = guaranteed safe**: If a property holds despite symbolic values, it holds for all concrete values too.
- **FAILED = needs inspection**: The counterexample may be spurious due to over-approximation.

State transitions, control flow, arithmetic, storage, and inner transactions are all modeled precisely. Only cryptographic operations are nondeterministic.

**What this does NOT cover**:
- Hash preimage relationships (e.g., `SHA256(x) == known_hash`)
- Ed25519 signature validation correctness
- Consensus-layer behavior (block production, fee pooling)

## Property Writing Guide

Properties are C++ boolean expressions evaluated after contract execution. They access `ctx.result` (`ACCEPT`, `REJECT`, `PANIC`), `ctx.bs_before`, and `ctx.bs_after`. Guard with `ctx.result != ACCEPT || <property>` -- rejections and panics are safe by definition.

### Pattern 1: State Transition

```cpp
// Counter only increases
"ctx.result != ACCEPT || prop_global_int_monotonic_inc(ctx.bs_before, ctx.bs_after, \"counter\")"
```

### Pattern 2: Access Control

```cpp
// Setup code (--setup-code or METHOD_CONSTRAINT_PLACEHOLDER):
uint8_t manager[32] = {/* known address */};
bs_assume_asset_params(BS, 123, manager, manager);
txg_assume_method(TxnGroup[0], 0xAB, 0xCD, 0xEF, 0x01);

// Property:
"prop_requires_sender(ctx.result, ctx.txn, manager)"
```

### Pattern 3: Immutability Under Specific Method

```cpp
// Setup: constrain to read_metadata method
txg_assume_method(TxnGroup[0], 0x12, 0x34, 0x56, 0x78);

// Property:
"ctx.result != ACCEPT || prop_all_globals_unchanged(ctx.bs_before, ctx.bs_after)"
```

### Pattern 4: Bounded State Invariant

```cpp
// Setup: assume counter starts in valid range
bs_assume_global_int_range(BS, "counter", 0, 1000);

// Property:
"ctx.result != ACCEPT || prop_global_int_bounded(ctx.bs_after, \"counter\", 0, 1000)"
```

### Pattern 5: Box Consistency

```cpp
"ctx.result != ACCEPT || prop_box_count_non_decreasing(ctx.bs_before, ctx.bs_after)"
```

### Pattern 6: Inner Transaction Effects

```cpp
// Contract never sends more than 1000 microAlgos via inner payments
"ctx.result != ACCEPT || ctx.bs_after.app_balance >= ctx.bs_before.app_balance - 1000"
```

### Pattern 7: Multi-Contract Verification

```python
result = verifier.verify_contract(
    "path/to/outer.teal",
    properties=['ctx.result != ACCEPT || prop_global_int_bounded(ctx.bs_after, "counter", 0, 100)'],
    inner_contracts={42: "path/to/inner.teal"},
    setup_code="BS.app_balance = 10000;",
    unwind=20,
)
```

When `inner_contracts` is provided, secondary contracts are transpiled and a dispatch function routes inner app calls by ApplicationID. Inner contract rejection causes outer contract panic (matching AVM semantics). Recursion is bounded by `CBMC_MAX_INNER_DEPTH`.

### Tips

1. **Guard with `ctx.result != ACCEPT`**: Most properties only matter on acceptance.
2. **Pre-state matters**: Use `bs_assume_*` to set up realistic initial conditions. Without constraints, the solver explores impossible states.
3. **Method constraining**: Use `txg_assume_method()` to focus on one ABI method at a time. Verifying all methods at once is slow.
4. **Bound tuning**: Start with small bounds and increase only if needed.

## Property Reference (`engine/properties.h`)

### Global State
| Helper | Description |
|--------|-------------|
| `prop_global_int_monotonic_inc(before, after, key)` | Global int only increases |
| `prop_global_int_monotonic_dec(before, after, key)` | Global int only decreases |
| `prop_global_int_bounded(BS, key, lo, hi)` | Global int in [lo, hi] |
| `prop_global_unchanged(before, after, key)` | Specific global key unchanged |
| `prop_all_globals_unchanged(before, after)` | No globals changed |

### Local State
| Helper | Description |
|--------|-------------|
| `prop_local_unchanged(before, after, addr, key)` | Specific local key unchanged |
| `prop_all_locals_unchanged(before, after)` | No local state changed |
| `prop_local_int_monotonic_inc(before, after, addr, key)` | Local int only increases |
| `prop_local_int_monotonic_dec(before, after, addr, key)` | Local int only decreases |
| `prop_local_int_bounded(BS, addr, key, lo, hi)` | Local int in [lo, hi] |

### Balance & Conservation
| Helper | Description |
|--------|-------------|
| `prop_balance_conserved(before, after)` | App balance did not increase |
| `prop_balance_conserved_for(before, after, addr)` | Specific app's balance did not increase |

### Authorization
| Helper | Description |
|--------|-------------|
| `prop_sender_is(txn, expected_addr)` | Sender matches expected address |
| `prop_requires_sender(result, txn, addr)` | ACCEPT only if sender matches |

### Boxes
| Helper | Description |
|--------|-------------|
| `prop_box_count_non_increasing(before, after)` | Box count didn't increase |
| `prop_box_count_non_decreasing(before, after)` | Box count didn't decrease |
| `prop_all_boxes_unchanged(before, after)` | No box contents changed |

### Assets
| Helper | Description |
|--------|-------------|
| `prop_asset_balance_unchanged(before, after, addr, id)` | Asset balance didn't change |
| `prop_asset_balance_bounded(BS, addr, id, lo, hi)` | Asset balance in [lo, hi] |

### Inner Transactions
| Helper | Description |
|--------|-------------|
| `prop_no_inner_txns(ctx)` | No inner transactions submitted |
| `prop_inner_txn_count(ctx)` | Number of inner transactions submitted |
| `prop_total_inner_payment(ctx)` | Total amount sent via inner payments |

### Safety
| Helper | Description |
|--------|-------------|
| `prop_no_rekey(txn)` | Transaction doesn't rekey |
| `prop_no_close_out(txn)` | Transaction doesn't close out balance |
| `prop_no_asset_close(txn)` | Transaction doesn't close asset holdings |

## BlockchainState Builder (`engine/bs_builder.h`)

Contract-agnostic API for defining initial blockchain state using `__CPROVER_assume()` constraints. Enables the pattern: *"from any valid initial state, can a transaction reach an invalid state?"*

### Quick Start

```cpp
#include "bs_builder.h"

int main() {
    BlockchainState BS;
    bs_valid_initial_state(BS);  // symbolic state + sane Algorand defaults

    bs_assume_global_int_range(BS, "counter", 0, 100);
    bs_assume_min_app_balance(BS, 1000000);

    uint8_t key[] = {0,0,0,0,0,0,0,42};
    bs_assume_box_zeroed(BS, key, 8, 43);

    Txn TxnGroup[2];
    txg_valid_group(TxnGroup, 2, 1, app_id, 4);
    txg_assume_method(TxnGroup[1], 0x78, 0x40, 0x78, 0x31);
    txg_assume_noop(TxnGroup[1]);
    // ... execute contract and check properties
}
```

### State Builders
| Function | Description |
|----------|-------------|
| `bs_valid_initial_state(BS)` | Symbolic state + sane Algorand defaults |
| `bs_assume_global_int(BS, key, val)` | Set concrete global int |
| `bs_assume_global_int_range(BS, key, lo, hi)` | Symbolic global int in [lo, hi] |
| `bs_assume_global_bytes(BS, key, data, len)` | Set concrete global bytes |
| `bs_assume_global_absent(BS, key)` | Key must NOT exist |
| `bs_assume_box_zeroed(BS, key, klen, size)` | Pre-create zeroed box |
| `bs_assume_box_symbolic(BS, key, klen, size)` | Pre-create box with symbolic data |
| `bs_assume_box_absent(BS, key, klen)` | Box must NOT exist |
| `bs_assume_min_app_balance(BS, min)` | App balance >= min |
| `bs_assume_app_balance_range(BS, lo, hi)` | App balance in [lo, hi] |
| `bs_assume_local_int(BS, addr, key, val)` | Set local int for account |
| `bs_assume_local_opt_in(BS, addr)` | Mark account as opted in |
| `bs_assume_asset_params(BS, id, manager, creator)` | Add asset with manager/creator |
| `bs_assume_asset_holding(BS, addr, id, balance, frozen)` | Add asset holding |
| `bs_assume_app_account(BS, addr, balance)` | Register app with balance (multi-contract) |

### Transaction Group Builders
| Function | Description |
|----------|-------------|
| `txg_init(tg, count)` | Zero-init array, set GroupIndex |
| `txg_valid_group(tg, count, app_idx, app_id, nargs)` | Mixed pay+appcall group |
| `txg_symbolic_appcall(txn, app_id, nargs)` | Symbolic app call |
| `txg_symbolic_pay(txn)` | Symbolic payment |
| `txg_symbolic_axfer(txn)` | Symbolic asset transfer |
| `txg_assume_method(txn, b0, b1, b2, b3)` | Constrain method selector |
| `txg_assume_noop(txn)` | OnCompletion = 0 |
| `txg_assume_same_sender(tg, count)` | All txns share first txn's sender |

## CLI Reference

```bash
# Basic verification
teal-verify contract.teal --property "true" --unwind 20

# Multiple properties
teal-verify contract.teal \
  -p 'ctx.result != ACCEPT || prop_all_globals_unchanged(ctx.bs_before, ctx.bs_after)' \
  -p 'ctx.result != ACCEPT || prop_balance_conserved(ctx.bs_before, ctx.bs_after)'

# Custom template (for complex setups: addresses, multi-txn groups, local state)
teal-verify contract.teal --template my_template.cpp --property "..."

# Performance tuning
teal-verify contract.teal --property "..." \
  --unwind 30 --timeout 600 --property-only \
  --bounds CBMC_STACK_MAX=32 CBMC_BYTES_MAX=64

# Debugging
teal-verify contract.teal --property "..." \
  --trace --stop-on-fail --verbose
```

### Solver Selection

By default, CBMC uses **MiniSat2** (SAT). The `--solver` flag lets you switch to an SMT or alternative SAT backend, which can dramatically change performance depending on the contract:

```bash
# Use Z3 (SMT) — good all-rounder for arithmetic-heavy contracts
teal-verify contract.teal --property "..." --solver z3

# Use Bitwuzla (SMT) — fastest for bitvector-heavy verification
teal-verify contract.teal --property "..." --solver bitwuzla

# Use CaDiCaL (SAT) — modern CDCL solver, often faster than MiniSat
teal-verify contract.teal --property "..." --solver cadical
```

| Solver | Type | Strengths | Weaknesses | Install |
|--------|------|-----------|------------|---------|
| `minisat` | SAT | CBMC default, no extra install, reliable | Slower on 64-bit arithmetic and large byte operations | Built into CBMC |
| `cadical` | SAT | Modern CDCL solver, faster on many SAT instances, good clause learning | Marginal improvement on arithmetic-heavy problems | `apt install cadical` or build from source |
| `kissat` | SAT | Competition-winning SAT solver, excellent on hard combinatorial instances | Similar to CaDiCaL; less tested with CBMC | Build from [source](https://github.com/arminbiere/kissat) |
| `z3` | SMT | Native bitvector reasoning, good all-rounder, handles arithmetic well | Higher per-query overhead than SAT solvers, slower on pure boolean problems | `apt install z3` / `brew install z3` |
| `bitwuzla` | SMT | State-of-the-art bitvector solver, best for fixed-width arithmetic (mul, div, mod) | Less mature CBMC integration, may not support all CBMC features | Build from [source](https://bitwuzla.github.io/) |
| `cvc5` | SMT | Strong on quantifiers and arrays, good theory combination | Slower than Bitwuzla on pure bitvector problems, higher memory usage | `apt install cvc5` or build from [source](https://cvc5.github.io/) |

**When to switch solvers:**
- Multiplication overflow checks, `bmath_*` operations, `exp` → try `bitwuzla` or `z3`
- Large state spaces with many globals/boxes → try `cadical`
- Timeouts with default solver → try `z3` first (best overall improvement for TEAL verification)

### Python API

```python
from tests.conftest import VerifyRunner

runner = VerifyRunner(tmp_path)

# Inline TEAL
result = runner.verify(
    teal_source="...",
    properties=["ctx.result != ACCEPT || prop_global_int_bounded(ctx.bs_after, \"counter\", 0, 100)"],
    unwind=20,
)

# File-based with custom template
result = runner.verify_contract(
    "path/to/contract.teal",
    template_path="path/to/template.cpp",
    properties=["ctx.result != ACCEPT || prop_all_globals_unchanged(ctx.bs_before, ctx.bs_after)"],
    unwind=20,
    property_only=True,
)
```

## Template Generator

For complex verification scenarios (multi-transaction groups, local state, assets, method selectors), use the template generator to create a custom C++ harness from a JSON config:

```bash
python template_generator/generator.py config.json -o my_template.cpp
teal-verify contract.teal --template my_template.cpp --property "..."
```

See `template_generator/JSON_SYNTAX.md` for the full configuration schema.

## CBMC Bounds

All data structures are bounded for SAT solver performance. Bounds are tunable via `--bounds` CLI flag or `#define` in templates:

| Bound | Default | Controls |
|-------|---------|----------|
| `CBMC_STACK_MAX` | 32 | Max stack depth |
| `CBMC_BYTES_MAX` | 128 | Max byteslice length |
| `CBMC_MAX_GLOBALS` | 16 | Max global state entries |
| `CBMC_MAX_BOXES` | 4 | Max concurrent boxes |
| `CBMC_BOX_MAX_SIZE` | 64 | Max box data size |
| `CBMC_MAX_FRAMES` | 8 | Max callsub nesting depth |
| `CBMC_MAX_INNER_DEPTH` | 2 | Max inner app call recursion |
| `CBMC_MAX_INNER_TXNS` | 4 | Max inner transactions per call |
| `CBMC_SCRATCH_SLOTS` | 256 | Max scratch space slots |
| `CBMC_MAX_ASSETS` | 4 | Max assets in state model |
| `CBMC_MAX_ASSET_HOLDINGS` | 4 | Max asset holdings in state model |

## Known Limitations

1. **Crypto operations**: All hash/signature operations are nondeterministic stubs -- cannot verify hash equality or signature correctness.
2. **Nondeterministic access control**: Tests checking "unauthorized sender rejects" may be vacuously true because `asset_params_get` returns symbolic AssetManager when the asset is not pre-populated. Use `bs_assume_asset_params()` to set concrete manager addresses.
3. **Bounded state space**: CBMC explores all paths up to the unwind bound. Use `--unwinding-assertions` to detect when the bound is insufficient.
4. **Missing opcodes**: `sumhash512`, `falcon_verify`, `online_stake`, `voter_params_get`, `mimc` emit `//UNSUPPORTED OPCODE`. Crypto/EC ops are nondeterministic stubs.
5. **goto-cc constraints**: No C++ lambdas; labels must be globally unique across translation units.
6. **Slow tests**: `test_box_resize_grow`, `test_box_resize_shrink`, `test_bmath_divmod_identity` timeout at 120s (CBMC solver performance).

## Running Tests

```bash
# All tests (exclude known slow ones)
pytest tests/ -v -k "not (test_box_resize_grow or test_box_resize_shrink or test_bmath_divmod_identity or test_trivial)"

# Specific test modules
pytest tests/test_cbmc_opcodes.py -v      # Opcode unit tests
pytest tests/test_transpiler.py -v         # Transpiler tests
pytest tests/test_template_generator.py -v # Template generator tests
pytest tests/test_verify_properties.py -v  # Property/integration tests
pytest tests/test_bs_builder.py -v         # BlockchainState builder tests
```

## Project Structure

```
teal-verifier/
├── engine/                  # C++ verification engine headers
│   ├── cbmc_avm.h           #   Bounded AVM data structures
│   ├── cbmc_opcodes.h       #   AVM opcode implementations (~120 opcodes)
│   ├── cbmc_bounds.h        #   Bound definitions and documentation
│   ├── properties.h         #   Property helper functions
│   ├── bs_builder.h         #   BlockchainState & TxnGroup builders
│   └── AVM_verify_template.cpp  # Default verification harness
├── cbmc_transpiler/         # TEAL-to-C++ transpiler
│   └── AVMTranspiler.py     #   Tree-sitter based transpiler (~1100 lines)
├── template_generator/      # JSON config to C++ template generator
│   ├── generator.py
│   └── JSON_SYNTAX.md       #   Full JSON configuration schema
├── cli/                     # CLI and CBMC orchestration
│   ├── verify_contract.py   #   CLI verification orchestrator
│   └── cbmc_utils.py        #   CBMC binary discovery and helpers
└── tests/                   # Test suite
    ├── test_cbmc_opcodes.py
    ├── test_transpiler.py
    ├── test_template_generator.py
    ├── test_verify_properties.py
    ├── test_bs_builder.py
    └── conftest.py
```
