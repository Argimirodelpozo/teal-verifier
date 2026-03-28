"""
Tests for the template generator (template-generator/generator.py).

Tests cover JSON parsing, C++ emission, presets, addresses, global/local state,
boxes, assets, transaction types, method selectors, logicsig mode, and
end-to-end generation with inline configs.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from template_generator.generator import (
    generate_template,
    TemplateConfig,
    Bounds,
    Address,
    GlobalVar,
    LocalKey,
    LocalAccount,
    Box,
    AssetParam,
    AssetHolding,
    AppBalance,
    AppAccount,
    InitialState,
    PayTxn,
    AxferTxn,
    AcfgTxn,
    AfrzTxn,
    AppcallTxn,
    TxnGroup,
    LsigArgs,
    DEFAULT_BOUNDS,
)


# ============================================================================
# Bounds & Presets
# ============================================================================


class TestBounds:
    def test_default_preset(self):
        b = Bounds.from_json({})
        assert b.values == DEFAULT_BOUNDS

    def test_minimal_preset(self):
        b = Bounds.from_json({"preset": "minimal"})
        assert b.values["CBMC_STACK_MAX"] == 16
        assert b.values["CBMC_BYTES_MAX"] == 32

    def test_permissive_preset(self):
        b = Bounds.from_json({"preset": "permissive"})
        assert b.values["CBMC_STACK_MAX"] == 1000
        assert b.values["CBMC_BYTES_MAX"] == 4096

    def test_bounds_override(self):
        b = Bounds.from_json({"preset": "minimal", "bounds": {"CBMC_STACK_MAX": 64}})
        assert b.values["CBMC_STACK_MAX"] == 64
        # Other minimal values preserved
        assert b.values["CBMC_BYTES_MAX"] == 32

    def test_unknown_preset_falls_back_to_default(self):
        b = Bounds.from_json({"preset": "nonexistent"})
        assert b.values == DEFAULT_BOUNDS

    def test_emit_produces_defines(self):
        b = Bounds.from_json({"preset": "minimal"})
        output = b.emit()
        assert "#define CBMC_STACK_MAX 16" in output
        assert "#define CBMC_BYTES_MAX 32" in output

    def test_emit_sorted(self):
        b = Bounds.from_json({})
        output = b.emit()
        defines = [line for line in output.splitlines() if line.startswith("#define")]
        keys = [d.split()[1] for d in defines]
        assert keys == sorted(keys)


# ============================================================================
# Address
# ============================================================================


class TestAddress:
    def test_concrete_address(self):
        addr = Address.from_json("manager", [1] * 32)
        assert not addr.is_symbolic
        assert addr.concrete == [1] * 32

    def test_symbolic_address(self):
        addr = Address.from_json("attacker", "symbolic")
        assert addr.is_symbolic
        assert addr.concrete is None

    def test_wrong_length_raises(self):
        with pytest.raises(ValueError, match="32 bytes"):
            Address.from_json("bad", [1, 2, 3])

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError):
            Address.from_json("bad", 42)

    def test_emit_concrete(self):
        addr = Address.from_json("mgr", [0] * 31 + [1])
        out = addr.emit()
        assert "uint8_t mgr[32]" in out
        assert "{" in out and "}" in out

    def test_emit_symbolic(self):
        addr = Address.from_json("atk", "symbolic")
        out = addr.emit()
        assert "uint8_t atk[32]" in out
        assert "nondet_uint64" in out


# ============================================================================
# GlobalVar
# ============================================================================


class TestGlobalVar:
    def test_int_concrete_value(self):
        g = GlobalVar.from_json({"key": "counter", "type": "int", "value": 42})
        out = g.emit()
        assert "gs_put" in out
        assert "sv_int(42)" in out

    def test_int_range(self):
        g = GlobalVar.from_json({"key": "status", "type": "int", "range": [0, 100]})
        out = g.emit()
        assert "nondet_uint64" in out
        assert ">= 0" in out
        assert "<= 100" in out

    def test_int_symbolic_var(self):
        g = GlobalVar.from_json(
            {"key": "score", "type": "int", "symbolic_var": "initial_score", "range": [0, 1000]}
        )
        out = g.emit()
        assert "uint64_t initial_score" in out
        assert "__CPROVER_assume" in out
        assert "gs_put" in out

    def test_bytes_hex(self):
        g = GlobalVar.from_json({"key": "admin", "type": "bytes", "hex": "AABBCCDD"})
        out = g.emit()
        assert "sv_bytes" in out
        assert "170, 187, 204, 221" in out  # 0xAA, 0xBB, 0xCC, 0xDD

    def test_bytes_value_list(self):
        g = GlobalVar.from_json({"key": "tag", "type": "bytes", "value": [72, 101]})
        out = g.emit()
        assert "sv_bytes" in out
        assert "72, 101" in out

    def test_direct_false_uses_bs_assume(self):
        g = GlobalVar.from_json({"key": "x", "type": "int", "value": 5, "direct": False})
        out = g.emit()
        assert "bs_assume_global_int" in out
        assert "gs_put" not in out

    def test_direct_false_range(self):
        g = GlobalVar.from_json({"key": "x", "type": "int", "range": [1, 10], "direct": False})
        out = g.emit()
        assert "bs_assume_global_int_range" in out

    def test_type_defaults_to_int(self):
        g = GlobalVar.from_json({"key": "x", "value": 7})
        assert g.type == "int"

    def test_no_initializer_comment(self):
        g = GlobalVar.from_json({"key": "empty"})
        out = g.emit()
        assert "no initializer" in out


# ============================================================================
# LocalKey & LocalAccount
# ============================================================================


class TestLocalKey:
    def test_int_value(self):
        lk = LocalKey.from_json({"key": "balance", "type": "int", "value": 500})
        out = lk.emit("sender")
        assert 'bs_assume_local_int(BS, sender, "balance", 500)' in out

    def test_int_range(self):
        lk = LocalKey.from_json({"key": "level", "type": "int", "range": [1, 10]})
        out = lk.emit("addr")
        assert "nondet_uint64" in out
        assert ">= 1" in out
        assert "<= 10" in out

    def test_int_symbolic_var(self):
        lk = LocalKey.from_json(
            {"key": "r1", "type": "int", "symbolic_var": "r1_init", "range": [1000, 999999]}
        )
        out = lk.emit("pool")
        assert "uint64_t r1_init" in out
        assert "bs_assume_local_int(BS, pool" in out

    def test_bytes_hex(self):
        lk = LocalKey.from_json({"key": "data", "type": "bytes", "hex": "DEADBEEF"})
        out = lk.emit("user")
        assert "bs_assume_local_bytes" in out
        assert "222, 173, 190, 239" in out


class TestLocalAccount:
    def test_opted_in(self):
        la = LocalAccount.from_json({"address": "sender", "opted_in": True})
        out = la.emit()
        assert "bs_assume_local_opt_in(BS, sender)" in out

    def test_not_opted_in(self):
        la = LocalAccount.from_json({"address": "sender", "opted_in": False})
        out = la.emit()
        assert "opt_in" not in out

    def test_with_keys(self):
        la = LocalAccount.from_json({
            "address": "pool",
            "opted_in": True,
            "keys": [
                {"key": "asset_1_id", "type": "int", "value": 100},
                {"key": "asset_2_id", "type": "int", "value": 200},
            ],
        })
        out = la.emit()
        assert "opt_in" in out
        assert "asset_1_id" in out
        assert "asset_2_id" in out


# ============================================================================
# Box
# ============================================================================


class TestBox:
    def test_key_str_zeros(self):
        b = Box.from_json({"key_str": "metadata", "size": 128, "init": "zeros"}, idx=0)
        out = b.emit()
        assert "bs_assume_box_zeroed" in out
        assert '"metadata"' in out
        assert "128" in out

    def test_key_hex_symbolic(self):
        b = Box.from_json({"key_hex": "00000001", "size": 64, "init": "symbolic"}, idx=1)
        out = b.emit()
        assert "bs_assume_box_symbolic" in out
        assert "_box_key_1" in out

    def test_key_bytes_absent(self):
        b = Box.from_json({"key_bytes": [0, 0, 0, 1], "init": "absent"}, idx=2)
        out = b.emit()
        assert "bs_assume_box_absent" in out

    def test_data_hex_auto_init(self):
        b = Box.from_json({"key_str": "cfg", "data_hex": "FF00FF00"}, idx=0)
        assert b.init == "data"
        out = b.emit()
        assert "bs_assume_box" in out
        assert "_box_data_0" in out

    def test_data_bytes(self):
        b = Box.from_json({"key_str": "x", "data_bytes": [1, 2, 3]}, idx=3)
        assert b.init == "data"
        out = b.emit()
        assert "1, 2, 3" in out

    def test_no_key_comment(self):
        b = Box.from_json({"size": 64}, idx=0)
        out = b.emit()
        assert "no key specified" in out


# ============================================================================
# Assets
# ============================================================================


class TestAssetParam:
    def test_basic(self):
        a = AssetParam.from_json({"id": 123, "manager": "mgr"})
        out = a.emit()
        assert "bs_assume_asset_params(BS, 123, mgr, mgr)" in out

    def test_separate_creator(self):
        a = AssetParam.from_json({"id": 456, "manager": "mgr", "creator": "creator"})
        out = a.emit()
        assert "bs_assume_asset_params(BS, 456, mgr, creator)" in out


class TestAssetHolding:
    def test_concrete(self):
        ah = AssetHolding.from_json({"address": "user", "asset_id": 100, "balance": 1000, "frozen": False})
        out = ah.emit()
        assert "bs_assume_asset_holding(BS, user, 100, 1000, false)" in out

    def test_symbolic(self):
        ah = AssetHolding.from_json({"address": "user", "asset_id": 200})
        out = ah.emit()
        assert "bs_assume_asset_holding_symbolic(BS, user, 200)" in out

    def test_frozen_true(self):
        ah = AssetHolding.from_json({"address": "u", "asset_id": 1, "balance": 0, "frozen": True})
        out = ah.emit()
        assert "true" in out


# ============================================================================
# AppBalance & AppAccount
# ============================================================================


class TestAppBalance:
    def test_concrete_value(self):
        ab = AppBalance.from_json(1000000)
        out = ab.emit()
        assert "BS.app_balance = 1000000" in out

    def test_min_only(self):
        ab = AppBalance.from_json({"min": 100000})
        out = ab.emit()
        assert "bs_assume_min_app_balance(BS, 100000)" in out

    def test_min_max_range(self):
        ab = AppBalance.from_json({"min": 1000, "max": 999999})
        out = ab.emit()
        assert "bs_assume_app_balance_range(BS, 1000, 999999)" in out

    def test_dict_value(self):
        ab = AppBalance.from_json({"value": 5000})
        out = ab.emit()
        assert "BS.app_balance = 5000" in out

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError):
            AppBalance.from_json("invalid")


class TestAppAccount:
    def test_concrete_balance(self):
        aa = AppAccount.from_json({"app_id": 1, "address": "APP_ADDR", "balance": 10000000})
        out = aa.emit()
        assert "bs_assume_app_account(BS, APP_ADDR, 10000000)" in out

    def test_range_balance(self):
        aa = AppAccount.from_json(
            {"app_id": 42, "address": "INNER", "balance": {"min": 1000, "max": 999999}}
        )
        out = aa.emit()
        assert "bs_assume_app_account_range(BS, INNER, 1000, 999999)" in out

    def test_symbolic_balance(self):
        aa = AppAccount.from_json({"app_id": 2, "address": "X"})
        out = aa.emit()
        assert "bs_assume_app_account_symbolic(BS, X)" in out


# ============================================================================
# InitialState
# ============================================================================


class TestInitialState:
    def test_symbolic_init_mode(self):
        st = InitialState.from_json({"init_mode": "symbolic"})
        out = st.emit()
        assert "bs_valid_initial_state(BS)" in out

    def test_zero_init_mode(self):
        st = InitialState.from_json({"init_mode": "zero"})
        out = st.emit()
        assert "BlockchainState BS = {}" in out
        assert "num_uint" in out

    def test_init_mode(self):
        st = InitialState.from_json({"init_mode": "init"})
        out = st.emit()
        assert "bs_init(BS)" in out

    def test_zero_init_legacy(self):
        st = InitialState.from_json({"zero_init": True})
        assert st.init_mode == "zero"

    def test_blockchain_fields(self):
        st = InitialState.from_json({
            "latest_timestamp": 1700000000,
            "round": 100,
            "min_txn_fee": 1000,
            "min_balance": 100000,
            "max_txn_life": 1000,
            "group_size": 3,
        })
        out = st.emit()
        assert "BS.latest_timestamp = 1700000000" in out
        assert "BS.round = 100" in out
        assert "BS.min_txn_fee = 1000" in out
        assert "BS.min_balance = 100000" in out
        assert "BS.max_txn_life = 1000" in out
        assert "BS.group_size = 3" in out


# ============================================================================
# Transaction Types
# ============================================================================


class TestPayTxn:
    def test_basic_pay(self):
        t = PayTxn.from_json({"type": "pay"}, idx=0)
        out = t.emit()
        assert "txg_symbolic_pay(TxnGroup[0])" in out

    def test_pay_with_receiver(self):
        t = PayTxn.from_json({"type": "pay", "receiver": "mgr"}, idx=1)
        out = t.emit()
        assert "txg_assume_receiver(TxnGroup[1], mgr)" in out

    def test_pay_receiver_app(self):
        t = PayTxn.from_json({"type": "pay", "receiver": "app"}, idx=0)
        out = t.emit()
        assert "_cbmc_bytecopy(TxnGroup[0].Receiver, BS.CurrentApplicationAddress, 32)" in out

    def test_pay_concrete_amount(self):
        t = PayTxn.from_json({"type": "pay", "amount": 10000}, idx=0)
        out = t.emit()
        assert "TxnGroup[0].Amount = 10000" in out

    def test_pay_amount_range(self):
        t = PayTxn.from_json({"type": "pay", "amount_range": [1000, 99999]}, idx=0)
        out = t.emit()
        assert "txg_assume_amount_range(TxnGroup[0], 1000, 99999)" in out

    def test_pay_close_to(self):
        t = PayTxn.from_json({"type": "pay", "close_to": "closer"}, idx=0)
        out = t.emit()
        assert "CloseRemainderTo" in out
        assert "closer" in out


class TestAxferTxn:
    def test_basic_axfer(self):
        t = AxferTxn.from_json({"type": "axfer"}, idx=0)
        out = t.emit()
        assert "txg_symbolic_axfer(TxnGroup[0])" in out

    def test_axfer_with_asset(self):
        t = AxferTxn.from_json({"type": "axfer", "xfer_asset": 100, "asset_receiver": "pool"}, idx=2)
        out = t.emit()
        assert "txg_assume_xfer_asset(TxnGroup[2], 100)" in out
        assert "txg_assume_asset_receiver(TxnGroup[2], pool)" in out

    def test_axfer_amount_range(self):
        t = AxferTxn.from_json({"type": "axfer", "asset_amount_range": [0, 1000000]}, idx=0)
        out = t.emit()
        assert "txg_assume_asset_amount_range(TxnGroup[0], 0, 1000000)" in out

    def test_axfer_concrete_amount(self):
        t = AxferTxn.from_json({"type": "axfer", "asset_amount": 50000}, idx=0)
        out = t.emit()
        assert "TxnGroup[0].AssetAmount = 50000" in out

    def test_axfer_clawback(self):
        t = AxferTxn.from_json({"type": "axfer", "asset_sender": "clawback_addr"}, idx=0)
        out = t.emit()
        assert "AssetSender" in out
        assert "clawback_addr" in out

    def test_axfer_close_to(self):
        t = AxferTxn.from_json({"type": "axfer", "asset_close_to": "closer"}, idx=0)
        out = t.emit()
        assert "AssetCloseTo" in out


class TestAcfgTxn:
    def test_basic_acfg(self):
        t = AcfgTxn.from_json({"type": "acfg"}, idx=0)
        out = t.emit()
        assert "txg_symbolic_acfg(TxnGroup[0])" in out

    def test_acfg_with_fields(self):
        t = AcfgTxn.from_json({
            "type": "acfg", "config_asset": 123,
            "manager": "mgr", "reserve": "rsv", "freeze": "frz", "clawback": "clw",
        }, idx=0)
        out = t.emit()
        assert "TxnGroup[0].ConfigAsset = 123" in out
        assert "ConfigAssetManager" in out
        assert "ConfigAssetReserve" in out
        assert "ConfigAssetFreeze" in out
        assert "ConfigAssetClawback" in out


class TestAfrzTxn:
    def test_basic_afrz(self):
        t = AfrzTxn.from_json({"type": "afrz"}, idx=0)
        out = t.emit()
        assert "txg_symbolic_afrz(TxnGroup[0])" in out

    def test_afrz_with_fields(self):
        t = AfrzTxn.from_json({
            "type": "afrz", "freeze_asset": 123,
            "freeze_account": "target", "frozen": True,
        }, idx=1)
        out = t.emit()
        assert "TxnGroup[1].FreezeAsset = 123" in out
        assert "FreezeAssetAccount" in out
        assert "FreezeAssetFrozen = 1" in out

    def test_afrz_frozen_false(self):
        t = AfrzTxn.from_json({"type": "afrz", "frozen": False}, idx=0)
        out = t.emit()
        assert "FreezeAssetFrozen = 0" in out


# ============================================================================
# AppcallTxn & Method Selectors
# ============================================================================


class TestAppcallTxn:
    def test_basic_appcall(self):
        t = AppcallTxn.from_json({"type": "appcall", "num_args": 2}, idx=0)
        out = t.emit()
        assert "TxnGroup[0].TypeEnum = 6" in out
        assert "TxnGroup[0].ApplicationID = app_id" in out
        assert "TxnGroup[0].NumAppArgs = 2" in out

    def test_on_completion_noop(self):
        t = AppcallTxn.from_json({"type": "appcall", "on_completion": "noop"}, idx=0)
        out = t.emit()
        assert "TxnGroup[0].apan = 0;" in out

    def test_on_completion_symbolic(self):
        t = AppcallTxn.from_json({"type": "appcall", "on_completion": "symbolic"}, idx=0)
        out = t.emit()
        assert "nondet_uint8" in out
        assert "_oc <= 5" in out

    def test_on_completion_int(self):
        t = AppcallTxn.from_json({"type": "appcall", "on_completion": 3}, idx=0)
        out = t.emit()
        assert "TxnGroup[0].apan = 3;" in out

    def test_sender_override(self):
        t = AppcallTxn.from_json({"type": "appcall", "sender": "attacker"}, idx=0)
        out = t.emit()
        assert "memcpy(TxnGroup[0].Sender, attacker, 32)" in out

    def test_single_method_selector_hex(self):
        t = AppcallTxn.from_json(
            {"type": "appcall", "num_args": 1, "arg_sizes": [4], "method_selector": "8636ADC3"},
            idx=0,
        )
        out = t.emit()
        assert "TxnGroup[0].AppArgs[0][0] = 0x86" in out
        assert "TxnGroup[0].AppArgs[0][1] = 0x36" in out
        assert "TxnGroup[0].AppArgs[0][2] = 0xAD" in out
        assert "TxnGroup[0].AppArgs[0][3] = 0xC3" in out

    def test_single_method_selector_bytes(self):
        t = AppcallTxn.from_json(
            {"type": "appcall", "num_args": 1, "arg_sizes": [4], "method_selector": [0xAA, 0xBB, 0xCC, 0xDD]},
            idx=0,
        )
        out = t.emit()
        assert "0xAA" in out
        assert "0xDD" in out

    def test_multiple_method_selectors(self):
        t = AppcallTxn.from_json(
            {
                "type": "appcall", "num_args": 1, "arg_sizes": [4],
                "method_selectors": ["8636ADC3", "CA6A3910"],
            },
            idx=0,
        )
        out = t.emit()
        assert "__CPROVER_assume" in out
        assert "0x8636ADC3" in out.upper() or "0x8636adc3" in out.lower()

    def test_invalid_selector_length_raises(self):
        with pytest.raises(ValueError, match="4 bytes"):
            AppcallTxn._parse_selector("AABB")  # 2 bytes, not 4

    def test_arg_sizes_chunked(self):
        t = AppcallTxn.from_json(
            {"type": "appcall", "num_args": 1, "arg_sizes": [32]}, idx=0,
        )
        out = t.emit()
        # 32 bytes = 4 uint64 chunks, no tail
        assert "for (uint8_t _c = 0; _c < 4; _c++)" in out
        assert "memcpy" in out

    def test_arg_sizes_with_tail(self):
        t = AppcallTxn.from_json(
            {"type": "appcall", "num_args": 1, "arg_sizes": [11]}, idx=0,
        )
        out = t.emit()
        # 11 bytes = 1 chunk (8 bytes) + 3 tail bytes
        assert "for (uint8_t _c = 0; _c < 1; _c++)" in out
        assert "nondet_uint8()" in out


# ============================================================================
# TxnGroup
# ============================================================================


class TestTxnGroup:
    def test_single_appcall(self):
        tg = TxnGroup.from_json({
            "transactions": [{"type": "appcall", "num_args": 2}],
        })
        assert tg.size == 1
        assert tg.app_index == 0

    def test_auto_detect_app_index(self):
        tg = TxnGroup.from_json({
            "transactions": [
                {"type": "pay"},
                {"type": "appcall", "num_args": 1},
            ],
        })
        assert tg.app_index == 1

    def test_explicit_app_index(self):
        tg = TxnGroup.from_json({
            "transactions": [{"type": "pay"}, {"type": "appcall"}],
            "app_index": 1,
        })
        assert tg.app_index == 1

    def test_same_sender(self):
        tg = TxnGroup.from_json({
            "transactions": [{"type": "pay"}, {"type": "appcall"}],
            "same_sender": True,
        })
        out = tg.emit(app_id=1)
        assert "txg_assume_same_sender(TxnGroup, 2)" in out

    def test_multi_txn_group(self):
        tg = TxnGroup.from_json({
            "transactions": [
                {"type": "pay", "amount": 2000, "receiver": "pool"},
                {"type": "appcall", "num_args": 1, "on_completion": "noop"},
                {"type": "axfer", "xfer_asset": 100},
            ],
        })
        assert tg.size == 3
        out = tg.emit(app_id=1)
        assert "Txn TxnGroup[3]" in out
        assert "txg_init(TxnGroup, 3)" in out
        assert "txg_symbolic_pay" in out
        assert "TypeEnum = 6" in out
        assert "txg_symbolic_axfer" in out

    def test_no_appcall_app_index_none(self):
        tg = TxnGroup.from_json({
            "transactions": [{"type": "pay"}, {"type": "pay"}],
        })
        assert tg.app_index is None
        out = tg.emit(app_id=1)
        assert "uint8_t currentTxn = 0" in out


# ============================================================================
# LsigArgs
# ============================================================================


class TestLsigArgs:
    def test_basic(self):
        la = LsigArgs.from_json({"num_args": 1, "arg_sizes": [1]})
        out = la.emit()
        assert "ctx.NumLsigArgs = 1" in out
        assert "ctx.LsigArgLens[0] = 1" in out

    def test_defaults(self):
        la = LsigArgs.from_json({})
        assert la.num_args == 2
        assert la.arg_sizes == [8, 8]


# ============================================================================
# TemplateConfig (top-level)
# ============================================================================


class TestTemplateConfig:
    def test_minimal_config(self):
        tc = TemplateConfig.from_json({"preset": "minimal"})
        assert tc.mode == "application"
        assert tc.app_id == 1

    def test_logicsig_mode_explicit(self):
        tc = TemplateConfig.from_json({"mode": "logicsig"})
        assert tc.mode == "logicsig"
        assert tc.lsig_args is not None

    def test_logicsig_mode_implicit(self):
        tc = TemplateConfig.from_json({"lsig_args": {"num_args": 1, "arg_sizes": [4]}})
        assert tc.mode == "logicsig"

    def test_creator_address_in_emit(self):
        tc = TemplateConfig.from_json({
            "addresses": {"creator": [3] * 32},
            "creator_address": "creator",
        })
        out = tc.emit()
        assert "memcpy(ctx.CreatorAddress, creator, 32)" in out

    def test_app_address_in_emit(self):
        tc = TemplateConfig.from_json({
            "addresses": {"app_addr": [4] * 32},
            "app_address": "app_addr",
        })
        out = tc.emit()
        assert "memcpy(ctx.CurrentApplicationAddress, app_addr, 32)" in out

    def test_emit_has_all_placeholders(self):
        out = TemplateConfig.from_json({}).emit()
        assert "//Function prototypes" in out
        assert "//PROPERTIES_PLACEHOLDER" in out
        assert "//CONTRACT_CALL_PLACEHOLDER" in out
        assert "//PROPERTY_CHECKS_PLACEHOLDER" in out
        assert "//METHOD_CONSTRAINT_PLACEHOLDER" in out

    def test_emit_has_includes(self):
        out = TemplateConfig.from_json({}).emit()
        assert '#include "cbmc_avm.h"' in out
        assert '#include "cbmc_opcodes.h"' in out
        assert '#include "properties.h"' in out
        assert '#include "bs_builder.h"' in out

    def test_emit_has_nondet_externs(self):
        out = TemplateConfig.from_json({}).emit()
        assert "nondet_uint64" in out
        assert "nondet_uint8" in out
        assert "nondet_bool" in out

    def test_emit_has_verify_context(self):
        out = TemplateConfig.from_json({}).emit()
        assert "struct VerifyContext" in out
        assert "bs_before" in out
        assert "bs_after" in out

    def test_emit_logicsig_no_app_id(self):
        out = TemplateConfig.from_json({"mode": "logicsig"}).emit()
        assert "LogicSig mode" in out
        assert "ctx.CurrentApplicationID" not in out

    def test_emit_application_sets_app_id(self):
        out = TemplateConfig.from_json({"app_id": 42}).emit()
        assert "ctx.CurrentApplicationID = app_id" in out
        assert "uint64_t app_id = 42" in out


# ============================================================================
# generate_template() — public API
# ============================================================================


class TestGenerateTemplate:
    def test_returns_string(self):
        out = generate_template({"preset": "minimal"})
        assert isinstance(out, str)
        assert len(out) > 100

    def test_minimal_compiles_structure(self):
        out = generate_template({"preset": "minimal"})
        assert "int main()" in out
        assert "return 0;" in out
        assert "_contract_end:" in out


# ============================================================================
# End-to-end: inline configs (no coupling to examples/)
# ============================================================================


class TestAMMStyleConfig:
    """End-to-end test with an AMM-like config (multi-txn, local state, symbolic vars)."""

    CONFIG = {
        "preset": "default",
        "app_id": 1,
        "bounds": {
            "CBMC_STACK_MAX": 24,
            "CBMC_BYTES_MAX": 64,
            "CBMC_SCRATCH_SLOTS": 32,
            "CBMC_MAX_LOCAL_ACCOUNTS": 2,
            "CBMC_MAX_LOCAL_KEYS": 12,
        },
        "addresses": {
            "ADDR_POOL": [4] * 32,
            "ADDR_USER": [5] * 32,
            "ADDR_MANAGER": [1] * 32,
        },
        "initial_state": {
            "init_mode": "init",
            "app_balance": 10000000,
            "latest_timestamp": 1700000000,
            "round": 100,
            "group_size": 3,
            "globals": [
                {"key": "fee_manager", "type": "bytes", "value": [1] * 32},
            ],
            "local_accounts": [
                {
                    "address": "ADDR_POOL",
                    "opted_in": True,
                    "keys": [
                        {"key": "asset_1_id", "type": "int", "value": 100},
                        {"key": "reserves", "type": "int", "symbolic_var": "r_init", "range": [1000, 1000000]},
                    ],
                }
            ],
        },
        "txn_group": {
            "transactions": [
                {"type": "pay", "amount": 100000, "receiver": "ADDR_POOL"},
                {"type": "axfer", "xfer_asset": 100, "asset_amount": 50000, "asset_receiver": "ADDR_POOL"},
                {"type": "appcall", "num_args": 4, "arg_sizes": [4, 11, 8, 8], "on_completion": "noop", "sender": "ADDR_USER"},
            ],
            "same_sender": True,
            "app_index": 2,
        },
    }

    @pytest.fixture
    def output(self):
        return TemplateConfig.from_json(self.CONFIG).emit()

    def test_has_addresses(self, output):
        assert "ADDR_POOL" in output
        assert "ADDR_MANAGER" in output

    def test_init_mode(self, output):
        assert "bs_init(BS)" in output

    def test_local_account_setup(self, output):
        assert "bs_assume_local_opt_in(BS, ADDR_POOL)" in output
        assert "asset_1_id" in output

    def test_symbolic_vars(self, output):
        assert "uint64_t r_init" in output

    def test_three_txn_group(self, output):
        assert "Txn TxnGroup[3]" in output
        assert "txg_symbolic_pay" in output
        assert "txg_symbolic_axfer" in output
        assert "txg_assume_same_sender" in output

    def test_app_index(self, output):
        assert "uint8_t currentTxn = 2" in output


class TestMultiAxferConfig:
    """End-to-end test with a burn-style 5-txn group and multiple axfers."""

    CONFIG = {
        "preset": "default",
        "app_id": 1,
        "bounds": {"CBMC_SCRATCH_SLOTS": 253},
        "addresses": {
            "ADDR_POOL": [1] * 32,
            "ADDR_POOLER": [2] * 32,
        },
        "initial_state": {
            "init_mode": "init",
            "group_size": 5,
        },
        "txn_group": {
            "transactions": [
                {"type": "pay", "amount": 2000, "receiver": "ADDR_POOL"},
                {"type": "appcall", "num_args": 1, "arg_sizes": [4], "on_completion": "noop"},
                {"type": "axfer", "xfer_asset": 100, "asset_receiver": "ADDR_POOLER"},
                {"type": "axfer", "xfer_asset": 200, "asset_receiver": "ADDR_POOLER"},
                {"type": "axfer", "xfer_asset": 300, "asset_receiver": "ADDR_POOL"},
            ],
            "app_index": 1,
        },
    }

    @pytest.fixture
    def output(self):
        return TemplateConfig.from_json(self.CONFIG).emit()

    def test_five_txn_group(self, output):
        assert "Txn TxnGroup[5]" in output

    def test_app_index_1(self, output):
        assert "uint8_t currentTxn = 1" in output

    def test_multiple_axfer(self, output):
        assert output.count("txg_symbolic_axfer") == 3

    def test_scratch_slots_bound(self, output):
        assert "#define CBMC_SCRATCH_SLOTS 253" in output


class TestLogicSigConfig:
    """Test logicsig mode with inline config."""

    CONFIG = {
        "preset": "minimal",
        "mode": "logicsig",
        "lsig_args": {"num_args": 1, "arg_sizes": [1]},
        "txn_group": {"transactions": [{"type": "pay"}]},
    }

    @pytest.fixture
    def output(self):
        return TemplateConfig.from_json(self.CONFIG).emit()

    def test_logicsig_mode(self, output):
        assert "LogicSig mode" in output

    def test_no_current_app_id(self, output):
        assert "ctx.CurrentApplicationID = app_id" not in output

    def test_lsig_args(self, output):
        assert "ctx.NumLsigArgs = 1" in output
        assert "ctx.LsigArgLens[0] = 1" in output

    def test_app_id_zero(self, output):
        assert "uint64_t app_id = 0" in output


class TestCouncilStyleConfig:
    """End-to-end test with a council-like config (globals, assets, bound overrides)."""

    CONFIG = {
        "preset": "default",
        "app_id": 1,
        "bounds": {"CBMC_STACK_MAX": 32, "CBMC_BYTES_MAX": 64, "CBMC_MAX_GLOBALS": 8, "CBMC_MAX_BOXES": 2},
        "addresses": {
            "manager": [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
            "unauthorized": [2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2],
        },
        "initial_state": {
            "app_balance": {"min": 100000},
            "globals": [
                {"key": "member_count", "type": "int", "value": 0},
                {"key": "proposal_count", "type": "int", "value": 0},
            ],
            "assets": [{"id": 100, "manager": "manager", "creator": "manager"}],
        },
        "txn_group": {
            "transactions": [
                {"type": "appcall", "num_args": 4, "arg_sizes": [4, 8, 8, 32], "on_completion": "symbolic"}
            ],
            "app_index": 0,
        },
    }

    @pytest.fixture
    def output(self):
        return TemplateConfig.from_json(self.CONFIG).emit()

    def test_bound_overrides(self, output):
        assert "#define CBMC_STACK_MAX 32" in output
        assert "#define CBMC_MAX_BOXES 2" in output

    def test_addresses(self, output):
        assert "uint8_t manager[32]" in output
        assert "uint8_t unauthorized[32]" in output

    def test_globals(self, output):
        assert "member_count" in output
        assert "proposal_count" in output

    def test_assets(self, output):
        assert "bs_assume_asset_params(BS, 100, manager, manager)" in output

    def test_min_balance(self, output):
        assert "bs_assume_min_app_balance(BS, 100000)" in output


# ============================================================================
# Edge cases
# ============================================================================


class TestEdgeCases:
    def test_empty_config(self):
        out = generate_template({})
        assert "int main()" in out

    def test_no_transactions(self):
        out = generate_template({"txn_group": {"transactions": []}})
        assert "Txn TxnGroup[0]" in out

    def test_global_bytes_direct_false(self):
        g = GlobalVar.from_json({"key": "data", "type": "bytes", "hex": "FF", "direct": False})
        out = g.emit()
        assert "bs_assume_global_bytes" in out

    def test_method_selector_via_method_selectors_single(self):
        """method_selectors with a single entry should emit hardcoded bytes, not assume-or."""
        t = AppcallTxn.from_json(
            {"type": "appcall", "num_args": 1, "arg_sizes": [4], "method_selectors": ["AABBCCDD"]},
            idx=0,
        )
        out = t.emit()
        assert "0xAA" in out
        # Single selector should use direct assignment, not the multi-selector assume-or pattern
        assert "constrain to one of" not in out

    def test_box_absent_ignores_data(self):
        """If init=absent, data_hex should not trigger data mode."""
        b = Box.from_json({"key_str": "x", "init": "absent", "data_hex": "FF"}, idx=0)
        assert b.init == "absent"
        out = b.emit()
        assert "bs_assume_box_absent" in out

    def test_pay_amount_takes_precedence_over_range(self):
        """If both amount and amount_range are set, amount wins."""
        t = PayTxn.from_json({"type": "pay", "amount": 5000, "amount_range": [1, 9999]}, idx=0)
        out = t.emit()
        assert "TxnGroup[0].Amount = 5000" in out
        assert "amount_range" not in out
