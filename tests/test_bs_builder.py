"""
Tests for the BlockchainState builder abstraction (bs_builder.h).

Verifies that the builder functions correctly set up initial state
using __CPROVER_assume() constraints, and that CBMC can verify properties
against these constrained states.
"""

import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


class TestBSSymbolicInit:
    """Test bs_symbolic + bs_assume_sane_defaults."""

    def test_sane_defaults_round_positive(self, opcodes):
        """bs_assume_sane_defaults constrains round >= 1."""
        result = opcodes.verify_cpp("""
    #include "bs_builder.h"
    int main() {
        BlockchainState BS;
        bs_valid_initial_state(BS);
        __CPROVER_assert(BS.round >= 1, "round >= 1");
        return 0;
    }
    """)
        assert result["verified"], f"round should be >= 1:\n{result['stderr']}"

    def test_sane_defaults_min_fee(self, opcodes):
        """bs_assume_sane_defaults constrains min_txn_fee >= 1000."""
        result = opcodes.verify_cpp("""
    #include "bs_builder.h"
    int main() {
        BlockchainState BS;
        bs_valid_initial_state(BS);
        __CPROVER_assert(BS.min_txn_fee >= 1000, "min_txn_fee >= 1000");
        return 0;
    }
    """)
        assert result["verified"], f"min_txn_fee should be >= 1000:\n{result['stderr']}"

    def test_sane_defaults_timestamp_bounded(self, opcodes):
        """Timestamp should be in sane range."""
        result = opcodes.verify_cpp("""
    #include "bs_builder.h"
    int main() {
        BlockchainState BS;
        bs_valid_initial_state(BS);
        __CPROVER_assert(BS.latest_timestamp >= 1000000000ULL, "ts lower bound");
        __CPROVER_assert(BS.latest_timestamp <= 2000000000ULL, "ts upper bound");
        return 0;
    }
    """)
        assert result["verified"], f"timestamp bounds failed:\n{result['stderr']}"

    def test_sane_defaults_group_size_bounded(self, opcodes):
        """Group size should be in [1, 16]."""
        result = opcodes.verify_cpp("""
    #include "bs_builder.h"
    int main() {
        BlockchainState BS;
        bs_valid_initial_state(BS);
        __CPROVER_assert(BS.group_size >= 1, "group_size >= 1");
        __CPROVER_assert(BS.group_size <= 16, "group_size <= 16");
        return 0;
    }
    """)
        assert result["verified"], f"group_size bounds failed:\n{result['stderr']}"


class TestBSGlobalAssumptions:
    """Test global state assumption helpers."""

    def test_assume_global_int(self, opcodes):
        """bs_assume_global_int sets a concrete value retrievable by prop_get_global_int."""
        result = opcodes.verify_cpp("""
    #include "bs_builder.h"
    #include "properties.h"
    int main() {
        BlockchainState BS;
        bs_init(BS);
        bs_assume_global_int(BS, "counter", 42);
        uint64_t val = prop_get_global_int(BS, "counter", 0);
        __CPROVER_assert(val == 42, "counter should be 42");
        return 0;
    }
    """)
        assert result["verified"], f"global int assumption failed:\n{result['stderr']}"

    def test_assume_global_int_range(self, opcodes):
        """bs_assume_global_int_range constrains value to [lo, hi]."""
        result = opcodes.verify_cpp("""
    #include "bs_builder.h"
    #include "properties.h"
    int main() {
        BlockchainState BS;
        bs_init(BS);
        bs_assume_global_int_range(BS, "score", 10, 100);
        uint64_t val = prop_get_global_int(BS, "score", 0);
        __CPROVER_assert(val >= 10, "score >= 10");
        __CPROVER_assert(val <= 100, "score <= 100");
        return 0;
    }
    """)
        assert result["verified"], f"global int range failed:\n{result['stderr']}"

    def test_assume_global_bytes(self, opcodes):
        """bs_assume_global_bytes sets concrete bytes retrievable."""
        result = opcodes.verify_cpp("""
    #include "bs_builder.h"
    #include "properties.h"
    int main() {
        BlockchainState BS;
        bs_init(BS);
        const uint8_t data[] = {0xDE, 0xAD};
        bs_assume_global_bytes(BS, "tag", data, 2);
        uint32_t out_len;
        uint8_t* got = prop_get_global_bytes(BS, "tag", &out_len);
        __CPROVER_assert(got != 0, "tag should exist");
        __CPROVER_assert(out_len == 2, "tag should be 2 bytes");
        __CPROVER_assert(got[0] == 0xDE, "first byte");
        __CPROVER_assert(got[1] == 0xAD, "second byte");
        return 0;
    }
    """)
        assert result["verified"], f"global bytes assumption failed:\n{result['stderr']}"

    def test_assume_global_absent(self, opcodes):
        """bs_assume_global_absent ensures key does not exist."""
        result = opcodes.verify_cpp("""
    #include "bs_builder.h"
    #include "properties.h"
    int main() {
        BlockchainState BS;
        bs_init(BS);
        bs_assume_global_absent(BS, "missing");
        __CPROVER_assert(!prop_global_exists(BS, "missing"), "key should not exist");
        return 0;
    }
    """)
        assert result["verified"], f"global absent assumption failed:\n{result['stderr']}"


class TestBSBoxAssumptions:
    """Test box state assumption helpers."""

    def test_assume_box_concrete(self, opcodes):
        """bs_assume_box creates a box with concrete data."""
        result = opcodes.verify_cpp("""
    #include "bs_builder.h"
    #include "properties.h"
    int main() {
        BlockchainState BS;
        bs_init(BS);
        uint8_t key[] = {0, 0, 0, 0, 0, 0, 0, 42};
        uint8_t data[] = {1, 2, 3, 4, 5};
        bs_assume_box(BS, key, 8, data, 5);
        uint32_t out_len;
        uint8_t* got = prop_get_box(BS, key, 8, &out_len);
        __CPROVER_assert(got != 0, "box should exist");
        __CPROVER_assert(out_len == 5, "box data should be 5 bytes");
        __CPROVER_assert(got[0] == 1, "byte 0");
        __CPROVER_assert(got[4] == 5, "byte 4");
        return 0;
    }
    """)
        assert result["verified"], f"box assumption failed:\n{result['stderr']}"

    def test_assume_box_zeroed(self, opcodes):
        """bs_assume_box_zeroed creates a box with all zeros."""
        result = opcodes.verify_cpp("""
    #include "bs_builder.h"
    #include "properties.h"
    int main() {
        BlockchainState BS;
        bs_init(BS);
        uint8_t key[] = {1, 2, 3};
        bs_assume_box_zeroed(BS, key, 3, 10);
        uint32_t out_len;
        uint8_t* got = prop_get_box(BS, key, 3, &out_len);
        __CPROVER_assert(got != 0, "box should exist");
        __CPROVER_assert(out_len == 10, "box size should be 10");
        __CPROVER_assert(got[0] == 0, "byte 0 should be 0");
        __CPROVER_assert(got[9] == 0, "byte 9 should be 0");
        return 0;
    }
    """)
        assert result["verified"], f"box zeroed assumption failed:\n{result['stderr']}"

    def test_assume_box_absent(self, opcodes):
        """bs_assume_box_absent ensures box does not exist."""
        result = opcodes.verify_cpp("""
    #include "bs_builder.h"
    #include "properties.h"
    int main() {
        BlockchainState BS;
        bs_init(BS);
        uint8_t key[] = {9, 9, 9};
        bs_assume_box_absent(BS, key, 3);
        BoxEntry* e = box_find(BS.boxes, key, 3);
        __CPROVER_assert(e == 0, "box should not exist");
        return 0;
    }
    """)
        assert result["verified"], f"box absent assumption failed:\n{result['stderr']}"

    def test_assume_no_boxes(self, opcodes):
        """bs_assume_no_boxes ensures empty box state."""
        result = opcodes.verify_cpp("""
    #include "bs_builder.h"
    int main() {
        BlockchainState BS;
        bs_init(BS);
        bs_assume_no_boxes(BS);
        __CPROVER_assert(BS.boxes.count == 0, "no boxes");
        return 0;
    }
    """)
        assert result["verified"], f"no boxes assumption failed:\n{result['stderr']}"


class TestBSBalanceAssumptions:
    """Test balance assumption helpers."""

    def test_assume_min_app_balance(self, opcodes):
        """bs_assume_min_app_balance constrains app balance."""
        result = opcodes.verify_cpp("""
    #include "bs_builder.h"
    int main() {
        BlockchainState BS;
        bs_valid_initial_state(BS);
        bs_assume_min_app_balance(BS, 1000000);
        __CPROVER_assert(BS.app_balance >= 1000000, "app balance >= 1M");
        return 0;
    }
    """)
        assert result["verified"], f"min app balance failed:\n{result['stderr']}"

    def test_assume_app_balance_range(self, opcodes):
        """bs_assume_app_balance_range constrains to [lo, hi]."""
        result = opcodes.verify_cpp("""
    #include "bs_builder.h"
    int main() {
        BlockchainState BS;
        bs_valid_initial_state(BS);
        bs_assume_app_balance_range(BS, 500, 1000);
        __CPROVER_assert(BS.app_balance >= 500, "balance >= 500");
        __CPROVER_assert(BS.app_balance <= 1000, "balance <= 1000");
        return 0;
    }
    """)
        assert result["verified"], f"app balance range failed:\n{result['stderr']}"


class TestTxgBuilder:
    """Test transaction group builder helpers."""

    def test_txg_init(self, opcodes):
        """txg_init zeros out transactions and sets GroupIndex."""
        result = opcodes.verify_cpp("""
    #include "bs_builder.h"
    int main() {
        Txn tg[3];
        txg_init(tg, 3);
        __CPROVER_assert(tg[0].GroupIndex == 0, "group index 0");
        __CPROVER_assert(tg[1].GroupIndex == 1, "group index 1");
        __CPROVER_assert(tg[2].GroupIndex == 2, "group index 2");
        __CPROVER_assert(tg[0].TypeEnum == 0, "type zeroed");
        return 0;
    }
    """)
        assert result["verified"], f"txg_init failed:\n{result['stderr']}"

    def test_txg_symbolic_appcall(self, opcodes):
        """txg_symbolic_appcall creates a valid symbolic app call."""
        result = opcodes.verify_cpp("""
    #include "bs_builder.h"
    int main() {
        Txn txn;
        memset(&txn, 0, sizeof(txn));
        txg_symbolic_appcall(txn, 42, 2);
        __CPROVER_assert(txn.TypeEnum == 6, "type is appl");
        __CPROVER_assert(txn.ApplicationID == 42, "app id");
        __CPROVER_assert(txn.apan <= 5, "oc bounded");
        __CPROVER_assert(txn.Fee >= 1000, "fee >= 1000");
        __CPROVER_assert(txn.NumAppArgs == 2, "2 args");
        return 0;
    }
    """)
        assert result["verified"], f"symbolic appcall failed:\n{result['stderr']}"

    def test_txg_symbolic_pay(self, opcodes):
        """txg_symbolic_pay creates a valid symbolic payment."""
        result = opcodes.verify_cpp("""
    #include "bs_builder.h"
    int main() {
        Txn txn;
        memset(&txn, 0, sizeof(txn));
        txg_symbolic_pay(txn);
        __CPROVER_assert(txn.TypeEnum == 1, "type is pay");
        __CPROVER_assert(txn.Fee >= 1000, "fee >= 1000");
        return 0;
    }
    """)
        assert result["verified"], f"symbolic pay failed:\n{result['stderr']}"

    def test_txg_assume_method(self, opcodes):
        """txg_assume_method constrains first 4 bytes of arg 0."""
        result = opcodes.verify_cpp("""
    #include "bs_builder.h"
    #include "properties.h"
    int main() {
        Txn txn;
        memset(&txn, 0, sizeof(txn));
        txg_symbolic_appcall(txn, 1, 4);
        txg_assume_method(txn, 0x78, 0x40, 0x78, 0x31);
        __CPROVER_assert(
            prop_txn_method_is(txn, 0x78, 0x40, 0x78, 0x31),
            "method selector matches"
        );
        return 0;
    }
    """)
        assert result["verified"], f"method assumption failed:\n{result['stderr']}"

    def test_txg_assume_noop(self, opcodes):
        """txg_assume_noop constrains OnCompletion to 0."""
        result = opcodes.verify_cpp("""
    #include "bs_builder.h"
    int main() {
        Txn txn;
        memset(&txn, 0, sizeof(txn));
        txg_symbolic_appcall(txn, 1, 2);
        txg_assume_noop(txn);
        __CPROVER_assert(txn.apan == 0, "oc should be NoOp");
        return 0;
    }
    """)
        assert result["verified"], f"noop assumption failed:\n{result['stderr']}"

    def test_txg_assume_same_sender(self, opcodes):
        """txg_assume_same_sender makes all txns share sender."""
        result = opcodes.verify_cpp("""
    #include "bs_builder.h"
    int main() {
        Txn tg[3];
        txg_init(tg, 3);
        txg_symbolic_appcall(tg[0], 1, 2);
        txg_symbolic_pay(tg[1]);
        txg_symbolic_pay(tg[2]);
        txg_assume_same_sender(tg, 3);
        __CPROVER_assert(
            memcmp(tg[0].Sender, tg[1].Sender, 32) == 0,
            "sender 0 == sender 1"
        );
        __CPROVER_assert(
            memcmp(tg[0].Sender, tg[2].Sender, 32) == 0,
            "sender 0 == sender 2"
        );
        return 0;
    }
    """)
        assert result["verified"], f"same sender failed:\n{result['stderr']}"

    def test_txg_set_arg_uint64(self, opcodes):
        """txg_set_arg_uint64 encodes value as big-endian itob."""
        result = opcodes.verify_cpp("""
    #include "bs_builder.h"
    int main() {
        Txn txn;
        memset(&txn, 0, sizeof(txn));
        txg_symbolic_appcall(txn, 1, 2);
        txg_set_arg_uint64(txn, 1, 42);
        // itob(42) = {0,0,0,0,0,0,0,42}
        __CPROVER_assert(txn.AppArgs[1][7] == 42, "low byte");
        __CPROVER_assert(txn.AppArgs[1][0] == 0, "high byte");
        __CPROVER_assert(txn.AppArgLens[1] == 8, "arg len");
        return 0;
    }
    """)
        assert result["verified"], f"set_arg_uint64 failed:\n{result['stderr']}"


class TestTxgValidGroup:
    """Test the composite txg_valid_group helper."""

    def test_valid_group_structure(self, opcodes):
        """txg_valid_group creates a mixed pay+appcall group with shared sender."""
        result = opcodes.verify_cpp("""
    #include "bs_builder.h"
    int main() {
        Txn tg[2];
        txg_valid_group(tg, 2, 1, 42, 4);

        // tg[0] should be a payment
        __CPROVER_assert(tg[0].TypeEnum == 1, "txn 0 is pay");
        // tg[1] should be an app call
        __CPROVER_assert(tg[1].TypeEnum == 6, "txn 1 is appl");
        __CPROVER_assert(tg[1].ApplicationID == 42, "app id");
        __CPROVER_assert(tg[1].NumAppArgs == 4, "4 args");
        // Same sender
        __CPROVER_assert(
            memcmp(tg[0].Sender, tg[1].Sender, 32) == 0,
            "shared sender"
        );
        return 0;
    }
    """)
        assert result["verified"], f"valid group failed:\n{result['stderr']}"


class TestCompositeVerification:
    """Integration tests: use builder to set up state, run contract, check property."""

    def test_counter_increment_from_valid_state(self, opcodes):
        """
        Define a valid initial state (counter in [0, 100]), execute a simple
        counter-increment contract, verify counter increased.
        """
        result = opcodes.verify_cpp("""
    #include "bs_builder.h"
    #include "properties.h"

    int main() {
        // 1. Set up valid initial state
        BlockchainState BS;
        bs_valid_initial_state(BS);
        bs_assume_global_int_range(BS, "counter", 0, 100);

        // 2. Snapshot pre-state
        uint64_t counter_before = prop_get_global_int(BS, "counter", 0);

        // 3. Simulate contract: read counter, increment, write back
        StackValue* sv = prop_get_global(BS, "counter");
        __CPROVER_assume(sv != 0);
        uint64_t val = sv->value;
        __CPROVER_assume(val < 100);  // prevent overflow

        // Write incremented value
        uint8_t kbuf[7] = {'c','o','u','n','t','e','r'};
        gs_put(BS.globals, kbuf, 7, sv_int(val + 1));

        // 4. Verify property: counter increased by exactly 1
        uint64_t counter_after = prop_get_global_int(BS, "counter", 0);
        __CPROVER_assert(counter_after == counter_before + 1,
                          "counter incremented by 1");
        __CPROVER_assert(counter_after <= 101,
                          "counter still bounded");
        return 0;
    }
    """)
        assert result["verified"], f"counter increment verification failed:\n{result['stderr']}"

    def test_box_operation_from_valid_state(self, opcodes):
        """
        Pre-create a box, verify that box_extract returns correct data.
        Tests that builder-created boxes work with AVM opcodes.
        """
        result = opcodes.verify_cpp("""
    #include "bs_builder.h"

    int main() {
        // 1. Set up state with a pre-existing box
        BlockchainState BS;
        bs_init(BS);
        uint8_t key[] = {0, 0, 0, 0, 0, 0, 0, 1};
        uint8_t data[] = {0xAA, 0xBB, 0xCC, 0xDD, 0xEE};
        bs_assume_box(BS, key, 8, data, 5);

        // 2. Use AVM opcodes to read the box
        Stack s;
        stack_init(s);
        EvalContext ctx;
        ctx_init(ctx);
        ctx.CurrentApplicationID = 1;
        Txn txn;
        memset(&txn, 0, sizeof(txn));
        txn.ApplicationID = 1;

        // Push key and call box_len
        pushbytes(s, key, 8);
        box_len(s, BS, txn, ctx);

        // box_len pushes: length, exists_flag
        StackValue exists_flag = stack_pop(s);
        StackValue length = stack_pop(s);

        __CPROVER_assert(exists_flag.value == 1, "box exists");
        __CPROVER_assert(length.value == 5, "box length is 5");

        return 0;
    }
    """)
        assert result["verified"], f"box operation verification failed:\n{result['stderr']}"


class TestScratchBuilder:
    """Test scratch space builder functions."""

    def test_scratch_int(self, opcodes):
        """bs_assume_scratch_int sets scratch slot to int value."""
        result = opcodes.verify_cpp("""
    #include "bs_builder.h"
    int main() {
        EvalContext ctx; ctx_init(ctx);
        bs_assume_scratch_int(ctx, 5, 42);
        __CPROVER_assert(ctx.sp[5].value == 42, "slot 5 = 42");
        __CPROVER_assert(!ctx.sp[5]._is_bytes, "slot 5 is int");
        return 0;
    }
    """)
        assert result["verified"], f"scratch int failed:\n{result['stderr']}"

    def test_scratch_bytes(self, opcodes):
        """bs_assume_scratch_bytes sets scratch slot to bytes value."""
        result = opcodes.verify_cpp("""
    #include "bs_builder.h"
    int main() {
        EvalContext ctx; ctx_init(ctx);
        uint8_t data[] = {1, 2, 3};
        bs_assume_scratch_bytes(ctx, 10, data, 3);
        __CPROVER_assert(ctx.sp[10]._is_bytes, "slot 10 is bytes");
        __CPROVER_assert(ctx.sp[10].byteslice_len == 3, "slot 10 len = 3");
        __CPROVER_assert(ctx.sp[10].byteslice[0] == 1, "byte 0");
        return 0;
    }
    """)
        assert result["verified"], f"scratch bytes failed:\n{result['stderr']}"


class TestLocalBytesBuilder:
    """Test local bytes builder and opt-in functions."""

    def test_local_bytes(self, opcodes):
        """bs_assume_local_bytes sets a byte-type local value."""
        result = opcodes.verify_cpp("""
    #include "bs_builder.h"
    int main() {
        Stack s; stack_init(s);
        BlockchainState BS; bs_init(BS);
        EvalContext ctx; ctx_init(ctx);
        Txn txn; memset(&txn, 0, sizeof(Txn));
        memset(txn.Sender, 0x42, 32);

        // Opt in and set local bytes
        bs_assume_local_opt_in(BS, txn.Sender);
        uint8_t data[] = {0xDE, 0xAD};
        bs_assume_local_bytes(BS, txn.Sender, "mykey", data, 2);

        // Read back via app_local_get
        pushint(s, 0);  // sender
        uint8_t key[] = {'m','y','k','e','y'};
        stack_push(s, sv_bytes(key, 5));
        app_local_get(s, BS, txn, ctx);
        StackValue r = stack_pop(s);
        __CPROVER_assert(r._is_bytes, "value is bytes");
        __CPROVER_assert(r.byteslice_len == 2, "len = 2");
        __CPROVER_assert(r.byteslice[0] == 0xDE, "byte 0");
        return 0;
    }
    """)
        assert result["verified"], f"local bytes failed:\n{result['stderr']}"

    def test_local_opt_in(self, opcodes):
        """bs_assume_local_opt_in creates LocalEntry so local_put succeeds."""
        result = opcodes.verify_cpp("""
    #include "bs_builder.h"
    int main() {
        Stack s; stack_init(s);
        BlockchainState BS; bs_init(BS);
        EvalContext ctx; ctx_init(ctx);
        Txn txn; memset(&txn, 0, sizeof(Txn));
        memset(txn.Sender, 0x42, 32);

        bs_assume_local_opt_in(BS, txn.Sender);

        // Should succeed without panic
        uint8_t key[] = {'k'};
        pushint(s, 0);
        stack_push(s, sv_bytes(key, 1));
        pushint(s, 99);
        app_local_put(s, BS, txn, ctx);

        __CPROVER_assert(!__avm_panicked, "no panic after opt-in");
        return 0;
    }
    """)
        assert result["verified"], f"local opt-in failed:\n{result['stderr']}"
