#!/usr/bin/env python3
"""
Template Generator for TEAL Formal Verification.

Generates C++ verification harness templates from JSON configuration.
The generated template can be used with write_verify() or verify_contract.py.

Usage:
    python -m template-generator.generator config.json -o my_template.cpp
    python template-generator/generator.py config.json -o my_template.cpp
"""

from __future__ import annotations

import json
import sys
import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ============================================================================
# Bound presets
# ============================================================================

AVM_REAL_BOUNDS: dict[str, int] = {
    "CBMC_STACK_MAX": 1000,
    "CBMC_BYTES_MAX": 4096,
    "CBMC_SCRATCH_SLOTS": 256,
    "CBMC_MAX_APP_ARGS": 16,
    "CBMC_MAX_GLOBALS": 64,
    "CBMC_GLOBAL_NUM_UINT": 64,
    "CBMC_GLOBAL_NUM_BYTESLICE": 64,
    "CBMC_LOCAL_NUM_UINT": 16,
    "CBMC_LOCAL_NUM_BYTESLICE": 16,
    "CBMC_MAX_LOCAL_ACCOUNTS": 4,
    "CBMC_MAX_LOCAL_KEYS": 16,
    "CBMC_MAX_LOGS": 32,
    "CBMC_MAX_LOG_LEN": 1024,
    "CBMC_MAX_INNER_TXNS": 256,
    "CBMC_MAX_INNER_DEPTH": 8,
    "CBMC_MAX_FRAMES": 256,
    "CBMC_MAX_BOXES": 8,
    "CBMC_BOX_MAX_SIZE": 32768,
    "CBMC_MAX_GROUP_SIZE": 16,
    "CBMC_MAX_ACCOUNTS": 4,
    "CBMC_MAX_TXN_ACCOUNTS": 4,
    "CBMC_MAX_TXN_ASSETS": 8,
    "CBMC_MAX_TXN_APPS": 8,
    "CBMC_MAX_TXN_LOGS": 32,
    "CBMC_MAX_LSIG_ARGS": 255,
    "CBMC_MAX_ASSETS": 8,
    "CBMC_MAX_ASSET_HOLDINGS": 8,
    "CBMC_BMATH_MAX": 64,
}

DEFAULT_BOUNDS: dict[str, int] = {
    "CBMC_STACK_MAX": 32,
    "CBMC_BYTES_MAX": 128,
    "CBMC_SCRATCH_SLOTS": 256,
    "CBMC_MAX_APP_ARGS": 8,
    "CBMC_MAX_GLOBALS": 16,
    "CBMC_GLOBAL_NUM_UINT": 16,
    "CBMC_GLOBAL_NUM_BYTESLICE": 16,
    "CBMC_LOCAL_NUM_UINT": 16,
    "CBMC_LOCAL_NUM_BYTESLICE": 16,
    "CBMC_MAX_LOCAL_ACCOUNTS": 4,
    "CBMC_MAX_LOCAL_KEYS": 4,
    "CBMC_MAX_LOGS": 8,
    "CBMC_MAX_LOG_LEN": 256,
    "CBMC_MAX_INNER_TXNS": 4,
    "CBMC_MAX_INNER_DEPTH": 2,
    "CBMC_MAX_FRAMES": 8,
    "CBMC_MAX_BOXES": 4,
    "CBMC_BOX_MAX_SIZE": 64,
    "CBMC_MAX_GROUP_SIZE": 4,
    "CBMC_MAX_ACCOUNTS": 4,
    "CBMC_MAX_TXN_ACCOUNTS": 4,
    "CBMC_MAX_TXN_ASSETS": 4,
    "CBMC_MAX_TXN_APPS": 4,
    "CBMC_MAX_TXN_LOGS": 4,
    "CBMC_MAX_LSIG_ARGS": 4,
    "CBMC_MAX_ASSETS": 4,
    "CBMC_MAX_ASSET_HOLDINGS": 4,
    "CBMC_BMATH_MAX": 64,
}

MINIMAL_BOUNDS: dict[str, int] = {
    **DEFAULT_BOUNDS,
    "CBMC_STACK_MAX": 16,
    "CBMC_BYTES_MAX": 32,
    "CBMC_MAX_GLOBALS": 4,
    "CBMC_MAX_LOGS": 4,
    "CBMC_MAX_LOG_LEN": 32,
    "CBMC_SCRATCH_SLOTS": 16,
    "CBMC_MAX_APP_ARGS": 4,
}

PRESETS = {
    "default": DEFAULT_BOUNDS,
    "permissive": AVM_REAL_BOUNDS,
    "minimal": MINIMAL_BOUNDS,
}


# ============================================================================
# Model classes — each knows how to populate from JSON and emit C++
# ============================================================================


@dataclass
class Bounds:
    """All CBMC verification bounds."""
    values: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_BOUNDS))

    @classmethod
    def from_json(cls, config: dict) -> Bounds:
        preset = config.get("preset", "default")
        base = dict(PRESETS.get(preset, DEFAULT_BOUNDS))
        base.update(config.get("bounds", {}))
        return cls(values=base)

    def emit(self) -> str:
        lines = ["// Bounds (see engine/cbmc_bounds.h for documentation)"]
        for key in sorted(self.values):
            lines.append(f"#define {key} {self.values[key]}")
        return "\n".join(lines)


@dataclass
class Address:
    """A 32-byte Algorand address — concrete or symbolic."""
    name: str
    concrete: list[int] | None = None  # 32 bytes, or None for symbolic

    @property
    def is_symbolic(self) -> bool:
        return self.concrete is None

    @classmethod
    def from_json(cls, name: str, spec: Any) -> Address:
        if spec == "symbolic":
            return cls(name=name)
        if isinstance(spec, list):
            if len(spec) != 32:
                raise ValueError(f"Address '{name}' must be 32 bytes, got {len(spec)}")
            return cls(name=name, concrete=spec)
        raise ValueError(f"Address '{name}': expected 'symbolic' or [32 bytes]")

    def emit(self) -> str:
        if self.concrete is not None:
            vals = ", ".join(str(b) for b in self.concrete)
            return f"    uint8_t {self.name}[32] = {{{vals}}};"
        return (
            f"    uint8_t {self.name}[32];\n"
            f"    for (uint8_t _i = 0; _i < 4; _i++)\n"
            f"        ((uint64_t*){self.name})[_i] = nondet_uint64();"
        )


@dataclass
class GlobalVar:
    """A global state variable with initial value or constraints.

    When direct=True (auto-detected for long keys), emits gs_put() with
    explicit key bytes instead of bs_assume_global_int() which has an
    internal string-copy loop that requires higher unwind bounds.
    """
    key: str
    type: str = "int"  # "int" or "bytes"
    value: int | list[int] | None = None
    hex_value: str | None = None
    range: tuple[int, int] | None = None
    symbolic_var: str | None = None  # named symbolic variable (accessible from setup_code)
    direct: bool = True  # use gs_put directly (avoids _cbmc_strcopy loop)

    @classmethod
    def from_json(cls, obj: dict) -> GlobalVar:
        g = cls(key=obj["key"], type=obj.get("type", "int"))
        if "value" in obj:
            g.value = obj["value"]
        if "hex" in obj:
            g.hex_value = obj["hex"]
        if "range" in obj:
            g.range = tuple(obj["range"])
        g.symbolic_var = obj.get("symbolic_var")
        g.direct = obj.get("direct", True)
        return g

    def _emit_direct(self) -> str:
        """Emit gs_put with explicit key casting (no _cbmc_strcopy loop)."""
        klen = len(self.key)
        if self.type == "int" and self.symbolic_var:
            # Named symbolic variable — accessible from setup_code
            var = self.symbolic_var
            lines = [f'    uint64_t {var} = nondet_uint64();']
            if self.range:
                lo, hi = self.range
                lines.append(f'    __CPROVER_assume({var} >= {lo} && {var} <= {hi});')
            lines.append(f'    gs_put(BS.globals, (const uint8_t*)"{self.key}", '
                         f'{klen}, sv_int({var}));')
            return '\n'.join(lines)
        if self.type == "int" and self.value is not None:
            return (f'    gs_put(BS.globals, (const uint8_t*)"{self.key}", '
                    f'{klen}, sv_int({self.value}));')
        if self.type == "int" and self.range:
            lo, hi = self.range
            return (f'    {{ uint64_t _v = nondet_uint64(); '
                    f'__CPROVER_assume(_v >= {lo} && _v <= {hi}); '
                    f'gs_put(BS.globals, (const uint8_t*)"{self.key}", '
                    f'{klen}, sv_int(_v)); }}')
        if self.type == "bytes":
            data = None
            if self.hex_value:
                data = list(bytes.fromhex(self.hex_value))
            elif isinstance(self.value, list):
                data = self.value
            if data is not None:
                arr = ", ".join(str(b) for b in data)
                return (f'    {{ uint8_t _v[] = {{{arr}}}; '
                        f'gs_put(BS.globals, (const uint8_t*)"{self.key}", '
                        f'{klen}, sv_bytes(_v, {len(data)})); }}')
        return f'    // GlobalVar "{self.key}": no initializer (direct mode)'

    def emit(self) -> str:
        if self.direct:
            return self._emit_direct()
        if self.type == "int":
            if self.range:
                return f'    bs_assume_global_int_range(BS, "{self.key}", {self.range[0]}, {self.range[1]});'
            if self.value is not None:
                return f'    bs_assume_global_int(BS, "{self.key}", {self.value});'
        elif self.type == "bytes":
            data = None
            if self.hex_value:
                data = list(bytes.fromhex(self.hex_value))
            elif isinstance(self.value, list):
                data = self.value
            if data is not None:
                arr = ", ".join(str(b) for b in data)
                return (f"    {{ uint8_t _v[] = {{{arr}}}; "
                        f'bs_assume_global_bytes(BS, "{self.key}", _v, {len(data)}); }}')
        return f'    // GlobalVar "{self.key}": no initializer'


@dataclass
class LocalKey:
    """A local state key for a specific account.

    For ints: concrete value, range [lo, hi], or symbolic_var (named nondet).
    For bytes: hex string, or byte array [0,1,...].
    """
    key: str
    type: str = "int"
    value: int | list[int] | None = None
    hex_value: str | None = None
    range: tuple[int, int] | None = None
    symbolic_var: str | None = None  # named symbolic variable (accessible from setup_code)

    @classmethod
    def from_json(cls, obj: dict) -> LocalKey:
        lk = cls(key=obj["key"], type=obj.get("type", "int"))
        if "value" in obj:
            lk.value = obj["value"]
        if "hex" in obj:
            lk.hex_value = obj["hex"]
        if "range" in obj:
            lk.range = tuple(obj["range"])
        lk.symbolic_var = obj.get("symbolic_var")
        return lk

    def emit(self, addr_name: str) -> str:
        if self.type == "int":
            if self.symbolic_var:
                var = self.symbolic_var
                lines = [f'    uint64_t {var} = nondet_uint64();']
                if self.range:
                    lo, hi = self.range
                    lines.append(f'    __CPROVER_assume({var} >= {lo} && {var} <= {hi});')
                lines.append(f'    bs_assume_local_int(BS, {addr_name}, "{self.key}", {var});')
                return '\n'.join(lines)
            if self.range:
                # Emit bounded nondeterministic local int
                lo, hi = self.range
                return (f'    {{ uint64_t _v = nondet_uint64(); '
                        f'__CPROVER_assume(_v >= {lo} && _v <= {hi}); '
                        f'bs_assume_local_int(BS, {addr_name}, "{self.key}", _v); }}')
            if self.value is not None:
                return f'    bs_assume_local_int(BS, {addr_name}, "{self.key}", {self.value});'
        elif self.type == "bytes":
            data = None
            if self.hex_value:
                data = list(bytes.fromhex(self.hex_value))
            elif isinstance(self.value, list):
                data = self.value
            if data is not None:
                arr = ", ".join(str(b) for b in data)
                return (f'    {{ uint8_t _v[] = {{{arr}}}; '
                        f'bs_assume_local_bytes(BS, {addr_name}, "{self.key}", _v, {len(data)}); }}')
        return f'    // LocalKey "{self.key}" for {addr_name}: no initializer'


@dataclass
class LocalAccount:
    """An account's local state setup."""
    address: str  # reference to an Address name
    opted_in: bool = True
    keys: list[LocalKey] = field(default_factory=list)

    @classmethod
    def from_json(cls, obj: dict) -> LocalAccount:
        la = cls(
            address=obj["address"],
            opted_in=obj.get("opted_in", True),
        )
        la.keys = [LocalKey.from_json(k) for k in obj.get("keys", [])]
        return la

    def emit(self) -> str:
        lines = []
        if self.opted_in:
            lines.append(f"    bs_assume_local_opt_in(BS, {self.address});")
        for k in self.keys:
            lines.append(k.emit(self.address))
        return "\n".join(lines)


@dataclass
class Box:
    """A box storage entry.

    init modes:
    - "zeros": box exists, all bytes zero (default)
    - "symbolic": box exists, all bytes nondeterministic
    - "absent": box does not exist
    - "data": box exists with concrete data from data_hex or data_bytes
    """
    idx: int = 0  # unique index for variable naming
    key_str: str | None = None
    key_hex: str | None = None
    key_bytes: list[int] | None = None
    size: int = 64
    init: str = "zeros"
    data_hex: str | None = None
    data_bytes: list[int] | None = None

    @classmethod
    def from_json(cls, obj: dict, idx: int) -> Box:
        init = obj.get("init", "zeros")
        # Auto-detect "data" init if data_hex or data_bytes is present
        if ("data_hex" in obj or "data_bytes" in obj) and init not in ("absent",):
            init = "data"
        return cls(
            idx=idx,
            key_str=obj.get("key_str"),
            key_hex=obj.get("key_hex"),
            key_bytes=obj.get("key_bytes"),
            size=obj.get("size", 64),
            init=init,
            data_hex=obj.get("data_hex"),
            data_bytes=obj.get("data_bytes"),
        )

    def _emit_key(self, lines: list[str]) -> tuple[str, int] | None:
        """Emit key variable and return (key_expr, key_len), or None."""
        if self.key_str is not None:
            return f'(const uint8_t*)"{self.key_str}"', len(self.key_str)
        elif self.key_hex is not None:
            data = list(bytes.fromhex(self.key_hex))
            arr = ", ".join(str(b) for b in data)
            var = f"_box_key_{self.idx}"
            lines.append(f"    uint8_t {var}[] = {{{arr}}};")
            return var, len(data)
        elif self.key_bytes is not None:
            arr = ", ".join(str(b) for b in self.key_bytes)
            var = f"_box_key_{self.idx}"
            lines.append(f"    uint8_t {var}[] = {{{arr}}};")
            return var, len(self.key_bytes)
        return None

    def emit(self) -> str:
        lines = []
        key_info = self._emit_key(lines)
        if key_info is None:
            return "    // Box: no key specified"
        key_expr, key_len = key_info

        if self.init == "zeros":
            lines.append(f"    bs_assume_box_zeroed(BS, {key_expr}, {key_len}, {self.size});")
        elif self.init == "symbolic":
            lines.append(f"    bs_assume_box_symbolic(BS, {key_expr}, {key_len}, {self.size});")
        elif self.init == "absent":
            lines.append(f"    bs_assume_box_absent(BS, {key_expr}, {key_len});")
        elif self.init == "data":
            data = None
            if self.data_hex:
                data = list(bytes.fromhex(self.data_hex))
            elif self.data_bytes:
                data = self.data_bytes
            if data is not None:
                arr = ", ".join(str(b) for b in data)
                dvar = f"_box_data_{self.idx}"
                lines.append(f"    uint8_t {dvar}[] = {{{arr}}};")
                lines.append(f"    bs_assume_box(BS, {key_expr}, {key_len}, {dvar}, {len(data)});")
            else:
                lines.append(f"    // Box {self.idx}: init=data but no data_hex/data_bytes")
        return "\n".join(lines)


@dataclass
class AssetParam:
    """An asset in the asset params state model."""
    id: int
    manager: str = "manager"
    creator: str | None = None

    @classmethod
    def from_json(cls, obj: dict) -> AssetParam:
        return cls(
            id=obj["id"],
            manager=obj.get("manager", "manager"),
            creator=obj.get("creator"),
        )

    def emit(self) -> str:
        creator = self.creator or self.manager
        return f"    bs_assume_asset_params(BS, {self.id}, {self.manager}, {creator});"


@dataclass
class AssetHolding:
    """An asset holding for an account."""
    address: str
    asset_id: int
    balance: int | None = None
    frozen: bool | None = None

    @classmethod
    def from_json(cls, obj: dict) -> AssetHolding:
        return cls(
            address=obj["address"],
            asset_id=obj["asset_id"],
            balance=obj.get("balance"),
            frozen=obj.get("frozen"),
        )

    def emit(self) -> str:
        if self.balance is not None or self.frozen is not None:
            bal = self.balance if self.balance is not None else 0
            frozen = "true" if self.frozen else "false"
            return f"    bs_assume_asset_holding(BS, {self.address}, {self.asset_id}, {bal}, {frozen});"
        return f"    bs_assume_asset_holding_symbolic(BS, {self.address}, {self.asset_id});"


@dataclass
class AppBalance:
    """App balance initial constraint."""
    value: int | None = None
    min: int | None = None
    max: int | None = None

    @classmethod
    def from_json(cls, spec: Any) -> AppBalance:
        if isinstance(spec, (int, float)):
            return cls(value=int(spec))
        if isinstance(spec, dict):
            return cls(
                value=spec.get("value"),
                min=spec.get("min"),
                max=spec.get("max"),
            )
        raise ValueError(f"app_balance: expected int or dict, got {type(spec)}")

    def emit(self) -> str:
        if self.value is not None:
            return f"    BS.app_balance = {self.value};"
        if self.min is not None and self.max is not None:
            return f"    bs_assume_app_balance_range(BS, {self.min}, {self.max});"
        if self.min is not None:
            return f"    bs_assume_min_app_balance(BS, {self.min});"
        return "    // app_balance: no constraint"


@dataclass
class AppAccount:
    """An app registered as an account (apps are accounts in Algorand).

    Used for multi-contract verification where each app needs its own balance.
    """
    app_id: int
    address: str  # reference to a named Address
    balance: int | None = None
    balance_min: int | None = None
    balance_max: int | None = None

    @classmethod
    def from_json(cls, obj: dict) -> AppAccount:
        aa = cls(app_id=obj["app_id"], address=obj["address"])
        bal = obj.get("balance")
        if isinstance(bal, dict):
            aa.balance_min = bal.get("min")
            aa.balance_max = bal.get("max")
            aa.balance = bal.get("value")
        elif isinstance(bal, (int, float)):
            aa.balance = int(bal)
        return aa

    def emit(self) -> str:
        if self.balance is not None:
            return f"    bs_assume_app_account(BS, {self.address}, {self.balance});"
        if self.balance_min is not None:
            return f"    bs_assume_app_account_range(BS, {self.address}, {self.balance_min}, {self.balance_max or (1 << 63) - 1});"
        return f"    bs_assume_app_account_symbolic(BS, {self.address});"


@dataclass
class InitialState:
    """Complete initial blockchain state configuration.

    When zero_init=True, uses `BlockchainState BS = {};` (zero-init) instead
    of `bs_valid_initial_state(BS)`. This avoids gs_init()/ls_init() loops
    that require high unwind bounds for contracts with many global keys.
    You must then set blockchain fields explicitly via the fields below.
    """
    init_mode: str = "symbolic"  # "symbolic" (bs_valid_initial_state), "zero" (= {}), "init" (bs_init only)
    zero_init: bool = False  # deprecated, use init_mode="zero"
    app_balance: AppBalance | None = None
    latest_timestamp: int | None = None
    round: int | None = None
    min_txn_fee: int | None = None
    min_balance: int | None = None
    max_txn_life: int | None = None
    group_size: int | None = None
    globals: list[GlobalVar] = field(default_factory=list)
    local_accounts: list[LocalAccount] = field(default_factory=list)
    boxes: list[Box] = field(default_factory=list)
    assets: list[AssetParam] = field(default_factory=list)
    asset_holdings: list[AssetHolding] = field(default_factory=list)
    app_accounts: list[AppAccount] = field(default_factory=list)

    @classmethod
    def from_json(cls, obj: dict) -> InitialState:
        st = cls()
        st.init_mode = obj.get("init_mode", "symbolic")
        st.zero_init = obj.get("zero_init", False)
        if st.zero_init:
            st.init_mode = "zero"
        if "app_balance" in obj:
            st.app_balance = AppBalance.from_json(obj["app_balance"])
        st.latest_timestamp = obj.get("latest_timestamp")
        st.round = obj.get("round")
        st.min_txn_fee = obj.get("min_txn_fee")
        st.min_balance = obj.get("min_balance")
        st.max_txn_life = obj.get("max_txn_life")
        st.group_size = obj.get("group_size")
        st.globals = [GlobalVar.from_json(g) for g in obj.get("globals", [])]
        st.local_accounts = [LocalAccount.from_json(la) for la in obj.get("local_accounts", [])]
        st.boxes = [Box.from_json(b, i) for i, b in enumerate(obj.get("boxes", []))]
        st.assets = [AssetParam.from_json(a) for a in obj.get("assets", [])]
        st.asset_holdings = [AssetHolding.from_json(ah) for ah in obj.get("asset_holdings", [])]
        st.app_accounts = [AppAccount.from_json(aa) for aa in obj.get("app_accounts", [])]
        return st

    def emit(self) -> str:
        lines = ["    // --- Initial state ---"]
        if self.init_mode == "zero":
            lines.append("    BlockchainState BS = {};  // Zero-init (no loops)")
            lines.append("    BS.globals.num_uint = CBMC_GLOBAL_NUM_UINT;")
            lines.append("    BS.globals.num_bytes = CBMC_GLOBAL_NUM_BYTESLICE;")
        elif self.init_mode == "init":
            lines.append("    BlockchainState BS;")
            lines.append("    bs_init(BS);")
        else:
            lines.append("    BlockchainState BS;")
            lines.append("    bs_valid_initial_state(BS);")
        lines.append("")

        # Blockchain fields
        if self.app_balance:
            lines.append(self.app_balance.emit())
        if self.latest_timestamp is not None:
            lines.append(f"    BS.latest_timestamp = {self.latest_timestamp};")
        if self.round is not None:
            lines.append(f"    BS.round = {self.round};")
        if self.min_txn_fee is not None:
            lines.append(f"    BS.min_txn_fee = {self.min_txn_fee};")
        if self.min_balance is not None:
            lines.append(f"    BS.min_balance = {self.min_balance};")
        if self.max_txn_life is not None:
            lines.append(f"    BS.max_txn_life = {self.max_txn_life};")
        if self.group_size is not None:
            lines.append(f"    BS.group_size = {self.group_size};")

        for g in self.globals:
            lines.append(g.emit())
        for la in self.local_accounts:
            lines.append(la.emit())
        for b in self.boxes:
            lines.append(b.emit())
        for a in self.assets:
            lines.append(a.emit())
        for ah in self.asset_holdings:
            lines.append(ah.emit())
        for aa in self.app_accounts:
            lines.append(aa.emit())
        lines.append("")
        return "\n".join(lines)


# ============================================================================
# Transaction model classes
# ============================================================================


@dataclass
class PayTxn:
    """Payment transaction setup."""
    index: int = 0
    amount: int | None = None
    amount_range: tuple[int, int] | None = None
    receiver: str | None = None  # address name reference
    close_to: str | None = None

    @classmethod
    def from_json(cls, obj: dict, idx: int) -> PayTxn:
        t = cls(index=idx)
        if "amount" in obj:
            t.amount = obj["amount"]
        if "amount_range" in obj:
            t.amount_range = tuple(obj["amount_range"])
        if "receiver" in obj:
            t.receiver = obj["receiver"]
        if "close_to" in obj:
            t.close_to = obj["close_to"]
        return t

    def emit(self) -> str:
        i = self.index
        lines = [f"    // TxnGroup[{i}]: pay"]
        lines.append(f"    txg_symbolic_pay(TxnGroup[{i}]);")
        if self.receiver == "app":
            lines.append(f"    _cbmc_bytecopy(TxnGroup[{i}].Receiver, BS.CurrentApplicationAddress, 32);")
        elif self.receiver:
            lines.append(f"    txg_assume_receiver(TxnGroup[{i}], {self.receiver});")
        if self.amount is not None:
            lines.append(f"    TxnGroup[{i}].Amount = {self.amount};")
        elif self.amount_range:
            lines.append(f"    txg_assume_amount_range(TxnGroup[{i}], {self.amount_range[0]}, {self.amount_range[1]});")
        if self.close_to:
            lines.append(f"    _cbmc_bytecopy(TxnGroup[{i}].CloseRemainderTo, {self.close_to}, 32);")
        return "\n".join(lines)


@dataclass
class AxferTxn:
    """Asset transfer transaction setup."""
    index: int = 0
    xfer_asset: int | None = None
    asset_amount: int | None = None
    asset_amount_range: tuple[int, int] | None = None
    asset_receiver: str | None = None
    asset_sender: str | None = None
    asset_close_to: str | None = None

    @classmethod
    def from_json(cls, obj: dict, idx: int) -> AxferTxn:
        t = cls(index=idx)
        if "xfer_asset" in obj:
            t.xfer_asset = obj["xfer_asset"]
        if "asset_amount" in obj:
            t.asset_amount = obj["asset_amount"]
        if "asset_amount_range" in obj:
            t.asset_amount_range = tuple(obj["asset_amount_range"])
        if "asset_receiver" in obj:
            t.asset_receiver = obj["asset_receiver"]
        if "asset_sender" in obj:
            t.asset_sender = obj["asset_sender"]
        if "asset_close_to" in obj:
            t.asset_close_to = obj["asset_close_to"]
        return t

    def emit(self) -> str:
        i = self.index
        lines = [f"    // TxnGroup[{i}]: axfer"]
        lines.append(f"    txg_symbolic_axfer(TxnGroup[{i}]);")
        if self.xfer_asset is not None:
            lines.append(f"    txg_assume_xfer_asset(TxnGroup[{i}], {self.xfer_asset});")
        if self.asset_amount is not None:
            lines.append(f"    TxnGroup[{i}].AssetAmount = {self.asset_amount};")
        elif self.asset_amount_range:
            lo, hi = self.asset_amount_range
            lines.append(f"    txg_assume_asset_amount_range(TxnGroup[{i}], {lo}, {hi});")
        if self.asset_receiver:
            lines.append(f"    txg_assume_asset_receiver(TxnGroup[{i}], {self.asset_receiver});")
        if self.asset_sender:
            lines.append(f"    _cbmc_bytecopy(TxnGroup[{i}].AssetSender, {self.asset_sender}, 32);")
        if self.asset_close_to:
            lines.append(f"    _cbmc_bytecopy(TxnGroup[{i}].AssetCloseTo, {self.asset_close_to}, 32);")
        return "\n".join(lines)


@dataclass
class AcfgTxn:
    """Asset config transaction setup."""
    index: int = 0
    config_asset: int | None = None
    manager: str | None = None
    reserve: str | None = None
    freeze: str | None = None
    clawback: str | None = None

    @classmethod
    def from_json(cls, obj: dict, idx: int) -> AcfgTxn:
        t = cls(index=idx)
        if "config_asset" in obj:
            t.config_asset = obj["config_asset"]
        for f in ("manager", "reserve", "freeze", "clawback"):
            if f in obj:
                setattr(t, f, obj[f])
        return t

    def emit(self) -> str:
        i = self.index
        lines = [f"    // TxnGroup[{i}]: acfg"]
        lines.append(f"    txg_symbolic_acfg(TxnGroup[{i}]);")
        if self.config_asset is not None:
            lines.append(f"    TxnGroup[{i}].ConfigAsset = {self.config_asset};")
        if self.manager:
            lines.append(f"    _cbmc_bytecopy(TxnGroup[{i}].ConfigAssetManager, {self.manager}, 32);")
        if self.reserve:
            lines.append(f"    _cbmc_bytecopy(TxnGroup[{i}].ConfigAssetReserve, {self.reserve}, 32);")
        if self.freeze:
            lines.append(f"    _cbmc_bytecopy(TxnGroup[{i}].ConfigAssetFreeze, {self.freeze}, 32);")
        if self.clawback:
            lines.append(f"    _cbmc_bytecopy(TxnGroup[{i}].ConfigAssetClawback, {self.clawback}, 32);")
        return "\n".join(lines)


@dataclass
class AfrzTxn:
    """Asset freeze transaction setup."""
    index: int = 0
    freeze_asset: int | None = None
    freeze_account: str | None = None
    frozen: bool | None = None

    @classmethod
    def from_json(cls, obj: dict, idx: int) -> AfrzTxn:
        t = cls(index=idx)
        if "freeze_asset" in obj:
            t.freeze_asset = obj["freeze_asset"]
        if "freeze_account" in obj:
            t.freeze_account = obj["freeze_account"]
        if "frozen" in obj:
            t.frozen = obj["frozen"]
        return t

    def emit(self) -> str:
        i = self.index
        lines = [f"    // TxnGroup[{i}]: afrz"]
        lines.append(f"    txg_symbolic_afrz(TxnGroup[{i}]);")
        if self.freeze_asset is not None:
            lines.append(f"    TxnGroup[{i}].FreezeAsset = {self.freeze_asset};")
        if self.freeze_account:
            lines.append(f"    _cbmc_bytecopy(TxnGroup[{i}].FreezeAssetAccount, {self.freeze_account}, 32);")
        if self.frozen is not None:
            val = 1 if self.frozen else 0
            lines.append(f"    TxnGroup[{i}].FreezeAssetFrozen = {val};")
        return "\n".join(lines)


@dataclass
class AppcallTxn:
    """Application call transaction setup."""
    index: int = 0
    num_args: int = 2
    arg_sizes: list[int] = field(default_factory=lambda: [8, 8])
    on_completion: str | int = "symbolic"  # "symbolic", "noop", or 0-5
    sender: str | None = None  # address name reference
    method_selectors: list[list[int]] | None = None  # list of 4-byte ABI method selectors

    @classmethod
    def _parse_selector(cls, raw: str | list[int]) -> list[int]:
        """Parse a single selector from hex string or byte array."""
        if isinstance(raw, str):
            bs = list(bytes.fromhex(raw))
            if len(bs) != 4:
                raise ValueError(f"method_selector hex must be 4 bytes, got {len(bs)}")
            return bs
        if isinstance(raw, list):
            if len(raw) != 4:
                raise ValueError(f"method_selector must be 4 bytes, got {len(raw)}")
            return raw
        raise ValueError(f"method_selector: expected hex string or [4 bytes], got {type(raw)}")

    @classmethod
    def from_json(cls, obj: dict, idx: int) -> AppcallTxn:
        num_args = obj.get("num_args", 2)

        # Parse method_selectors: accepts a single selector or a list of selectors
        selectors = None
        raw = obj.get("method_selectors", obj.get("method_selector"))
        if raw is not None:
            if isinstance(raw, str):
                # Single hex string
                selectors = [cls._parse_selector(raw)]
            elif isinstance(raw, list) and len(raw) > 0:
                if isinstance(raw[0], list) or isinstance(raw[0], str):
                    # List of selectors: ["AABB...", ...] or [[0xAA,...], ...]
                    selectors = [cls._parse_selector(s) for s in raw]
                else:
                    # Single selector as byte array: [0xAA, 0xBB, 0xCC, 0xDD]
                    selectors = [cls._parse_selector(raw)]

        return cls(
            index=idx,
            num_args=num_args,
            arg_sizes=obj.get("arg_sizes", [8] * num_args),
            on_completion=obj.get("on_completion", "symbolic"),
            sender=obj.get("sender"),
            method_selectors=selectors,
        )

    def emit(self) -> str:
        i = self.index
        lines = [f"    // TxnGroup[{i}]: appcall"]
        lines.append(f"    TxnGroup[{i}].TypeEnum = 6;")
        lines.append(f"    TxnGroup[{i}].ApplicationID = app_id;")

        oc = self.on_completion
        if oc == "symbolic":
            lines.append(f"    {{ uint8_t _oc = nondet_uint8();")
            lines.append(f"      __CPROVER_assume(_oc <= 5);")
            lines.append(f"      TxnGroup[{i}].apan = _oc; }}")
        elif oc == "noop":
            lines.append(f"    TxnGroup[{i}].apan = 0;")
        elif isinstance(oc, int):
            lines.append(f"    TxnGroup[{i}].apan = {oc};")

        lines.append(f"    TxnGroup[{i}].NumAppArgs = {self.num_args};")
        for ai, sz in enumerate(self.arg_sizes):
            lines.append(f"    TxnGroup[{i}].AppArgLens[{ai}] = {sz};")
            # Use uint64 chunks to avoid per-byte nondet loops (4 iterations for 32 bytes)
            full_chunks = sz // 8
            tail = sz % 8
            if full_chunks > 0:
                lines.append(f"    for (uint8_t _c = 0; _c < {full_chunks}; _c++) {{")
                lines.append(f"        uint64_t _chunk = nondet_uint64();")
                lines.append(f"        memcpy(&TxnGroup[{i}].AppArgs[{ai}][_c * 8], &_chunk, 8);")
                lines.append(f"    }}")
            if tail > 0:
                for tb in range(tail):
                    lines.append(f"    TxnGroup[{i}].AppArgs[{ai}][{full_chunks * 8 + tb}] = nondet_uint8();")

        # Method selector constraint (after nondet fill)
        if self.method_selectors:
            sels = self.method_selectors
            if len(sels) == 1:
                # Single selector: hardcode bytes directly
                b = sels[0]
                lines.append(f"    // Method selector: 0x{b[0]:02X}{b[1]:02X}{b[2]:02X}{b[3]:02X}")
                lines.append(f"    TxnGroup[{i}].AppArgs[0][0] = 0x{b[0]:02X};")
                lines.append(f"    TxnGroup[{i}].AppArgs[0][1] = 0x{b[1]:02X};")
                lines.append(f"    TxnGroup[{i}].AppArgs[0][2] = 0x{b[2]:02X};")
                lines.append(f"    TxnGroup[{i}].AppArgs[0][3] = 0x{b[3]:02X};")
            else:
                # Multiple selectors: cast first 4 bytes to uint32 and assume-or
                lines.append(f"    // Method selectors: constrain to one of {len(sels)} methods")
                lines.append(f"    {{ uint32_t _ms = ((uint32_t)TxnGroup[{i}].AppArgs[0][0] << 24)")
                lines.append(f"                    | ((uint32_t)TxnGroup[{i}].AppArgs[0][1] << 16)")
                lines.append(f"                    | ((uint32_t)TxnGroup[{i}].AppArgs[0][2] << 8)")
                lines.append(f"                    |  (uint32_t)TxnGroup[{i}].AppArgs[0][3];")
                clauses = []
                for b in sels:
                    val = (b[0] << 24) | (b[1] << 16) | (b[2] << 8) | b[3]
                    clauses.append(f"_ms == 0x{val:08X}u /* {b[0]:02X}{b[1]:02X}{b[2]:02X}{b[3]:02X} */")
                assume_expr = "\n        || ".join(clauses)
                lines.append(f"      __CPROVER_assume({assume_expr}); }}")

        lines.append(f"    TxnGroup[{i}].Fee = nondet_uint64();")
        lines.append(f"    __CPROVER_assume(TxnGroup[{i}].Fee >= 1000);")

        if self.sender:
            lines.append(f"    memcpy(TxnGroup[{i}].Sender, {self.sender}, 32);")

        return "\n".join(lines)


# Union type for all transaction types
TxnConfig = PayTxn | AxferTxn | AcfgTxn | AfrzTxn | AppcallTxn

_TXN_PARSERS: dict[str, type] = {
    "pay": PayTxn,
    "axfer": AxferTxn,
    "acfg": AcfgTxn,
    "afrz": AfrzTxn,
    "appcall": AppcallTxn,
}


def _parse_txn(obj: dict, idx: int) -> TxnConfig:
    txn_type = obj.get("type", "appcall")
    parser = _TXN_PARSERS.get(txn_type)
    if not parser:
        raise ValueError(f"Unknown transaction type: {txn_type}")
    return parser.from_json(obj, idx)


@dataclass
class TxnGroup:
    """Transaction group configuration."""
    transactions: list[TxnConfig] = field(default_factory=list)
    app_index: int | None = None  # which txn is the verified app call (None = no appcall)
    same_sender: bool = False

    @classmethod
    def from_json(cls, obj: dict) -> TxnGroup:
        txns_raw = obj.get("transactions", [{"type": "appcall", "num_args": 2, "arg_sizes": [8, 8]}])
        txns = [_parse_txn(t, i) for i, t in enumerate(txns_raw)]

        # Auto-detect app_index if not specified: first appcall in the group
        app_index = obj.get("app_index")
        if app_index is None:
            for i, t in enumerate(txns):
                if isinstance(t, AppcallTxn):
                    app_index = i
                    break

        return cls(
            transactions=txns,
            app_index=app_index,
            same_sender=obj.get("same_sender", False),
        )

    @property
    def size(self) -> int:
        return len(self.transactions)

    def emit(self, app_id: int) -> str:
        n = self.size
        lines = [f"    // --- Transaction group ({n} txn{'s' if n > 1 else ''}) ---"]
        lines.append(f"    uint64_t app_id = {app_id};")
        lines.append(f"    Txn TxnGroup[{n}];")
        lines.append(f"    txg_init(TxnGroup, {n});")
        lines.append("")

        for txn in self.transactions:
            lines.append(txn.emit())
            lines.append("")

        if self.same_sender and n > 1:
            lines.append(f"    txg_assume_same_sender(TxnGroup, {n});")
            lines.append("")

        # currentTxn: the app call index, or 0 if no app call
        current = self.app_index if self.app_index is not None else 0
        lines.append(f"    uint8_t currentTxn = {current};")
        lines.append("")
        return "\n".join(lines)


# ============================================================================
# Top-level template
# ============================================================================


@dataclass
class LsigArgs:
    """LogicSig argument setup."""
    num_args: int = 2
    arg_sizes: list[int] = field(default_factory=lambda: [8, 8])

    @classmethod
    def from_json(cls, obj: dict) -> LsigArgs:
        num_args = obj.get("num_args", 2)
        return cls(
            num_args=num_args,
            arg_sizes=obj.get("arg_sizes", [8] * num_args),
        )

    def emit(self) -> str:
        lines = ["    // --- LogicSig arguments ---"]
        lines.append(f"    ctx.NumLsigArgs = {self.num_args};")
        for ai, sz in enumerate(self.arg_sizes):
            lines.append(f"    ctx.LsigArgLens[{ai}] = {sz};")
            lines.append(f"    for (uint8_t _j = 0; _j < {sz}; _j++)")
            lines.append(f"        ctx.LsigArgs[{ai}][_j] = nondet_uint8();")
        lines.append("")
        return "\n".join(lines)


@dataclass
class TemplateConfig:
    """Complete template configuration."""
    bounds: Bounds = field(default_factory=Bounds)
    mode: str = "application"  # "application" or "logicsig"
    app_id: int = 1
    creator_address: str | None = None  # address name ref for ctx.CreatorAddress
    app_address: str | None = None  # address name ref for ctx.CurrentApplicationAddress
    addresses: list[Address] = field(default_factory=list)
    initial_state: InitialState = field(default_factory=InitialState)
    txn_group: TxnGroup = field(default_factory=TxnGroup)
    lsig_args: LsigArgs | None = None

    @classmethod
    def from_json(cls, config: dict) -> TemplateConfig:
        tc = cls()
        tc.bounds = Bounds.from_json(config)
        tc.mode = config.get("mode", "application")
        tc.app_id = config.get("app_id", 1)
        tc.creator_address = config.get("creator_address")
        tc.app_address = config.get("app_address")
        tc.addresses = [
            Address.from_json(name, spec)
            for name, spec in config.get("addresses", {}).items()
        ]
        if "initial_state" in config:
            tc.initial_state = InitialState.from_json(config["initial_state"])
        if "txn_group" in config:
            tc.txn_group = TxnGroup.from_json(config["txn_group"])
        if tc.mode == "logicsig" or "lsig_args" in config:
            tc.mode = "logicsig"
            tc.lsig_args = LsigArgs.from_json(config.get("lsig_args", {}))
        return tc

    def emit(self) -> str:
        parts: list[str] = []

        # Header
        parts.append("// Auto-generated verification template")
        parts.append("// Generated by template-generator")
        parts.append("")

        # Bounds
        parts.append(self.bounds.emit())
        parts.append("")

        # Includes
        parts.append('#include "cbmc_avm.h"')
        parts.append('#include "cbmc_opcodes.h"')
        parts.append('#include "properties.h"')
        parts.append('#include "bs_builder.h"')
        parts.append("")

        # Nondet helpers
        parts.append("extern \"C\" {")
        parts.append("    uint64_t nondet_uint64();")
        parts.append("    uint8_t nondet_uint8();")
        parts.append("    bool nondet_bool();")
        parts.append("}")
        parts.append("")

        # Contract function type
        parts.append("typedef void (*ContractFn)(Stack& s, BlockchainState& BS, EvalContext& ctx,")
        parts.append("                           Txn* TxnGroup, uint8_t currentTxn);")
        parts.append("")
        parts.append("//Function prototypes")
        parts.append("")

        # VerifyContext — property expressions use ctx.bs_before, ctx.result, etc.
        # Note: goto-cc does not support reference struct members, so these
        # are value copies. The bs_before snapshot is necessary for comparative
        # properties; bs_after copies BS after execution.
        parts.append("struct VerifyContext {")
        parts.append("    BlockchainState bs_before;")
        parts.append("    BlockchainState bs_after;")
        parts.append("    ExecResult result;")
        parts.append("    EvalContext eval_ctx;")
        parts.append("};")
        parts.append("")

        # Properties placeholder
        parts.append("//PROPERTIES_PLACEHOLDER")
        parts.append("")

        # main()
        parts.append("int main() {")

        # Addresses
        if self.addresses:
            parts.append("    // --- Addresses ---")
            for addr in self.addresses:
                parts.append(addr.emit())
            parts.append("")

        # Initial state
        parts.append(self.initial_state.emit())

        # Transaction group
        parts.append(self.txn_group.emit(0 if self.mode == "logicsig" else self.app_id))

        # Method constraint placeholder
        parts.append("    //METHOD_CONSTRAINT_PLACEHOLDER")
        parts.append("")

        # Snapshot + execute + result
        parts.append("    // --- Snapshot pre-state ---")
        parts.append("    BlockchainState bs_before = BS;")
        parts.append("")
        parts.append("    // --- Execute contract ---")
        parts.append("    Stack s;")
        parts.append("    stack_init(s);")
        parts.append("    EvalContext ctx;")
        parts.append("    ctx_init(ctx);")
        if self.mode == "logicsig":
            parts.append("    // LogicSig mode: no app ID")
            if self.lsig_args:
                parts.append(self.lsig_args.emit())
        else:
            parts.append("    ctx.CurrentApplicationID = app_id;")
        if self.creator_address:
            parts.append(f"    memcpy(ctx.CreatorAddress, {self.creator_address}, 32);")
        if self.app_address:
            parts.append(f"    memcpy(ctx.CurrentApplicationAddress, {self.app_address}, 32);")
        parts.append("    __avm_panicked = false;")
        parts.append("")
        parts.append("    //CONTRACT_CALL_PLACEHOLDER")
        parts.append("")
        parts.append("_contract_end: ;")
        parts.append("")
        parts.append("    // --- Determine result ---")
        parts.append("    VerifyContext vctx;")
        parts.append("    vctx.bs_before = bs_before;")
        parts.append("    vctx.bs_after = BS;")
        parts.append("    vctx.eval_ctx = ctx;")
        parts.append("    if (__avm_panicked) {")
        parts.append("        vctx.result = PANIC;")
        parts.append("    } else if (s.currentSize == 0) {")
        parts.append("        vctx.result = REJECT;")
        parts.append("    } else if (!s.stack[s.currentSize - 1]._is_bytes && s.stack[s.currentSize - 1].value != 0) {")
        parts.append("        vctx.result = ACCEPT;")
        parts.append("    } else {")
        parts.append("        vctx.result = REJECT;")
        parts.append("    }")

        parts.append("")
        parts.append("    // --- Check properties ---")
        parts.append("    {")
        parts.append("        VerifyContext& ctx = vctx;")
        parts.append("        (void)ctx;")
        parts.append("        //PROPERTY_CHECKS_PLACEHOLDER")
        parts.append("    }")
        parts.append("")
        parts.append("    return 0;")
        parts.append("}")
        parts.append("")

        return "\n".join(parts)


# ============================================================================
# Public API
# ============================================================================


def generate_template(config: dict) -> str:
    """Generate a C++ verification template from a JSON configuration dict."""
    tc = TemplateConfig.from_json(config)
    return tc.emit()


def main():
    parser = argparse.ArgumentParser(
        description="Generate C++ verification template from JSON configuration."
    )
    parser.add_argument("config", help="JSON configuration file")
    parser.add_argument("-o", "--output", help="Output template file (default: stdout)")
    parser.add_argument(
        "--preset",
        choices=["default", "permissive", "minimal"],
        help="Override the preset in the config file",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    with open(config_path) as f:
        config = json.load(f)

    if args.preset:
        config["preset"] = args.preset

    template = generate_template(config)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(template, encoding="utf-8")
        print(f"Template written to {out_path}", file=sys.stderr)
    else:
        print(template)


if __name__ == "__main__":
    main()
