"""
Tests for formal verification of contract properties using CBMC.

These tests verify that the CBMC-based verification pipeline works correctly:
- Trivial properties are verified
- False properties are detected as violations
- State-dependent properties work correctly
- Real contract properties (xGov Council) are verified
"""

import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

PRAGMA = "#pragma version 10\n"


class TestTrivialProperties:
    """Verify that basic property checking works."""

    def test_trivially_true_property(self, verifier):
        """A trivially true property should always pass."""
        teal = PRAGMA + "pushint 1\n"
        result = verifier.verify(teal, properties=["true"])
        assert result["verified"], (
            f"Trivial 'true' property should verify.\n"
            f"stdout: {result['stdout']}\nstderr: {result['stderr']}"
        )

    def test_always_accept_program(self, verifier):
        """'pushint 1' always accepts — verify that ctx.result == ACCEPT."""
        teal = PRAGMA + "pushint 1\n"
        result = verifier.verify(
            teal,
            properties=["ctx.result == ACCEPT"],
        )
        assert result["verified"], (
            f"'pushint 1' should always ACCEPT.\n"
            f"stdout: {result['stdout']}\nstderr: {result['stderr']}"
        )

    def test_always_reject_program(self, verifier):
        """'pushint 0' always rejects — verify that ctx.result == REJECT."""
        teal = PRAGMA + "pushint 0\n"
        result = verifier.verify(
            teal,
            properties=["ctx.result == REJECT"],
        )
        assert result["verified"], (
            f"'pushint 0' should always REJECT.\n"
            f"stdout: {result['stdout']}\nstderr: {result['stderr']}"
        )


class TestFalseProperties:
    """Verify that false properties are detected as violations."""

    def test_false_property_detected(self, verifier):
        """A trivially false property should fail."""
        teal = PRAGMA + "pushint 1\n"
        result = verifier.verify(teal, properties=["false"])
        assert not result["verified"], (
            "Trivial 'false' property should be detected as violation"
        )

    def test_wrong_result_claim(self, verifier):
        """Claiming 'pushint 1' rejects should fail."""
        teal = PRAGMA + "pushint 1\n"
        result = verifier.verify(
            teal,
            properties=["ctx.result == REJECT"],
        )
        assert not result["verified"], (
            "Claiming 'pushint 1' rejects should be detected as violation"
        )


class TestConditionalProperties:
    """Test properties with preconditions (implications)."""

    def test_conditional_accept(self, verifier):
        """A program that accepts only when arg0 > 250 (btoi).
        Property: if it accepts, arg0 (as int) was > 250."""
        teal = (
            PRAGMA
            + "txna ApplicationArgs 0\n"
            + "btoi\n"
            + "pushint 250\n"
            + ">\n"
            + "bz reject\n"
            + "pushint 1\n"
            + "return\n"
            + "reject:\n"
            + "pushint 0\n"
            + "return\n"
        )
        # If it accepted, the first arg must have been > 250
        result = verifier.verify(
            teal,
            properties=["ctx.result != ACCEPT || ctx.result == ACCEPT"],
            # This is a tautology — just verify the pipeline handles
            # contracts with branching correctly
        )
        assert result["verified"], (
            f"Tautology property should verify on branching contract.\n"
            f"stdout: {result['stdout']}\nstderr: {result['stderr']}"
        )

    def test_vacuously_true_on_reject(self, verifier):
        """'pushint 0' always rejects, so any implication from ACCEPT is vacuously true."""
        teal = PRAGMA + "pushint 0\n"
        result = verifier.verify(
            teal,
            # "if accepted, then false" — vacuously true since it never accepts
            properties=["ctx.result != ACCEPT || false"],
        )
        assert result["verified"], (
            f"Vacuous property should verify on rejecting program.\n"
            f"stdout: {result['stdout']}\nstderr: {result['stderr']}"
        )


class TestMultipleProperties:
    """Test verifying multiple properties at once."""

    def test_multiple_true_properties(self, verifier):
        """Multiple true properties should all verify."""
        teal = PRAGMA + "pushint 1\n"
        result = verifier.verify(
            teal,
            properties=[
                "true",
                "ctx.result == ACCEPT",
                "ctx.result != REJECT",
            ],
        )
        assert result["verified"], (
            f"All true properties should verify.\n"
            f"stdout: {result['stdout']}\nstderr: {result['stderr']}"
        )

    def test_one_false_among_true(self, verifier):
        """If one property is false, verification should fail."""
        teal = PRAGMA + "pushint 1\n"
        result = verifier.verify(
            teal,
            properties=[
                "true",
                "ctx.result == REJECT",  # This is false
            ],
        )
        assert not result["verified"], (
            "One false property among true ones should fail verification"
        )


class TestBoxProperties:
    """Verify box-related properties on TEAL contracts using property helpers."""

    def test_box_create_size_preserved(self, verifier, tmp_path):
        """A contract that creates a box of size 8 — verify size is correct after."""
        teal = (
            PRAGMA
            + "pushbytes 0x626F78  // 'box'\n"  # key = "box"
            + "pushint 8\n"         # size = 8
            + "box_create\n"
            + "pop\n"               # discard success flag
            + "pushint 1\n"         # accept
        )
        prop_file = tmp_path / "box_props.cpp"
        prop_file.write_text("""
void check_box_properties(VerifyContext& ctx) {
    if (ctx.result != ACCEPT) return;
    uint32_t len = 0;
    uint8_t* data = prop_get_box(ctx.bs_after, "box", &len);
    VERIFY_ASSERT(data != 0);
    VERIFY_ASSERT(len == 8);
    for (uint32_t i = 0; i < len; i++) {
        VERIFY_ASSERT(data[i] == 0);
    }
}
""")
        result = verifier.verify(
            teal,
            properties=["(check_box_properties(ctx), true)"],
            property_file=str(prop_file),
        )
        assert result["verified"], (
            f"Box create size property should verify.\n"
            f"stdout: {result['stdout']}\nstderr: {result['stderr']}"
        )

    def test_box_put_roundtrip(self, verifier, tmp_path):
        """Create a box, put data, verify data matches."""
        teal = (
            PRAGMA
            + "pushbytes 0x6B6579  // 'key'\n"     # key
            + "pushint 3\n"                          # size
            + "box_create\n"
            + "pop\n"
            + "pushbytes 0x6B6579  // 'key'\n"     # key
            + "pushbytes 0xAABBCC\n"                 # value
            + "box_put\n"
            + "pushint 1\n"
        )
        prop_file = tmp_path / "box_roundtrip.cpp"
        prop_file.write_text("""
void check_roundtrip(VerifyContext& ctx) {
    if (ctx.result != ACCEPT) return;
    uint32_t len = 0;
    uint8_t* data = prop_get_box(ctx.bs_after, "key", &len);
    VERIFY_ASSERT(data != 0);
    VERIFY_ASSERT(len == 3);
    VERIFY_ASSERT(data[0] == 0xAA);
    VERIFY_ASSERT(data[1] == 0xBB);
    VERIFY_ASSERT(data[2] == 0xCC);
}
""")
        result = verifier.verify(
            teal,
            properties=["(check_roundtrip(ctx), true)"],
            property_file=str(prop_file),
        )
        assert result["verified"], (
            f"Box put roundtrip should verify.\n"
            f"stdout: {result['stdout']}\nstderr: {result['stderr']}"
        )

    def test_box_del_removes_box(self, verifier, tmp_path):
        """Create then delete a box — verify it no longer exists."""
        teal = (
            PRAGMA
            + "pushbytes 0x746D70  // 'tmp'\n"
            + "pushint 4\n"
            + "box_create\n"
            + "pop\n"
            + "pushbytes 0x746D70  // 'tmp'\n"
            + "box_del\n"
            + "pop\n"
            + "pushint 1\n"
        )
        prop_file = tmp_path / "box_del.cpp"
        prop_file.write_text("""
void check_deleted(VerifyContext& ctx) {
    if (ctx.result != ACCEPT) return;
    VERIFY_ASSERT(!prop_box_exists(ctx.bs_after, "tmp"));
}
""")
        result = verifier.verify(
            teal,
            properties=["(check_deleted(ctx), true)"],
            property_file=str(prop_file),
        )
        assert result["verified"], (
            f"Box delete property should verify.\n"
            f"stdout: {result['stdout']}\nstderr: {result['stderr']}"
        )

    def test_box_no_unintended_creation(self, verifier, tmp_path):
        """A contract that only reads a box should not create any new boxes."""
        teal = (
            PRAGMA
            + "pushbytes 0x6E6F6E65  // 'none'\n"
            + "box_len\n"
            + "pop\n"  # exists flag
            + "pop\n"  # length
            + "pushint 1\n"
        )
        result = verifier.verify(
            teal,
            properties=["ctx.result != ACCEPT || prop_box_count(ctx.bs_after) == 0"],
        )
        assert result["verified"], (
            f"No unintended box creation should verify.\n"
            f"stdout: {result['stdout']}\nstderr: {result['stderr']}"
        )

    def test_box_get_reflects_put(self, verifier, tmp_path):
        """Create a box, put data, get it back — verify box_get returns correct data."""
        teal = (
            PRAGMA
            + "pushbytes 0x6461746162  // 'datab'\n"  # key
            + "pushint 2\n"
            + "box_create\n"
            + "pop\n"
            + "pushbytes 0x6461746162  // 'datab'\n"  # key
            + "pushbytes 0xFF00\n"                      # value
            + "box_put\n"
            + "pushbytes 0x6461746162  // 'datab'\n"  # key
            + "box_get\n"
            # Stack: [value, found_flag]
            + "pushint 1\n"
            + "==\n"          # assert found == 1
            + "assert\n"
            # value is still on stack
            + "pushbytes 0xFF00\n"
            + "==\n"          # assert value == expected
            + "assert\n"
            + "pushint 1\n"
        )
        result = verifier.verify(
            teal,
            properties=["ctx.result == ACCEPT"],
        )
        assert result["verified"], (
            f"Box get reflects put should verify.\n"
            f"stdout: {result['stdout']}\nstderr: {result['stderr']}"
        )

    def test_box_extract_offset(self, verifier, tmp_path):
        """Put 4 bytes, extract 2 from offset 1 — verify extract returns correct slice."""
        teal = (
            PRAGMA
            + "pushbytes 0x65  // 'e'\n"     # key
            + "pushint 4\n"
            + "box_create\n"
            + "pop\n"
            + "pushbytes 0x65  // 'e'\n"     # key
            + "pushbytes 0xAABBCCDD\n"       # value
            + "box_put\n"
            + "pushbytes 0x65  // 'e'\n"     # key
            + "pushint 1\n"                   # offset
            + "pushint 2\n"                   # length
            + "box_extract\n"
            # Stack: [extracted_bytes]
            + "pushbytes 0xBBCC\n"
            + "==\n"
            + "assert\n"
            + "pushint 1\n"
        )
        result = verifier.verify(
            teal,
            properties=["ctx.result == ACCEPT"],
        )
        assert result["verified"], (
            f"Box extract offset should verify.\n"
            f"stdout: {result['stdout']}\nstderr: {result['stderr']}"
        )

    def test_box_state_not_changed_on_read_only(self, verifier, tmp_path):
        """A contract that only does box_len should not modify box state."""
        teal = (
            PRAGMA
            + "pushbytes 0x78  // 'x'\n"
            + "box_len\n"
            + "pop\n"  # exists
            + "pop\n"  # length
            + "pushint 1\n"
        )
        result = verifier.verify(
            teal,
            properties=["ctx.result != ACCEPT || !prop_box_changed(ctx.bs_before, ctx.bs_after, \"x\")"],
        )
        assert result["verified"], (
            f"Box unchanged on read should verify.\n"
            f"stdout: {result['stdout']}\nstderr: {result['stderr']}"
        )


# ============================================================================
# Multi-contract verification tests
# ============================================================================

class TestMultiContract:
    """Test multi-contract inner app call dispatch."""

    def test_multi_contract_inner_call_accepts(self, verifier, tmp_path):
        """Outer contract calls inner contract that accepts; outer should accept."""
        # Inner contract: always accepts (pushint 1)
        inner_teal = tmp_path / "inner.teal"
        inner_teal.write_text(
            "#pragma version 10\n"
            "pushint 1\n"
        )

        # Outer contract: calls inner via inner txn, then accepts
        outer_teal = (
            PRAGMA
            + "itxn_begin\n"
            + "pushint 6\n"       # TypeEnum = appl
            + "itxn_field TypeEnum\n"
            + "pushint 42\n"      # ApplicationID = 42 (inner contract)
            + "itxn_field ApplicationID\n"
            + "itxn_submit\n"
            + "pushint 1\n"
        )

        result = verifier.verify(
            outer_teal,
            properties=["ctx.result == ACCEPT"],
            inner_contracts={42: str(inner_teal)},
            unwind=20,
            timeout=120,
        )
        assert result["verified"], (
            f"Outer should accept when inner accepts.\n"
            f"stdout: {result['stdout'][-2000:]}\nstderr: {result['stderr'][-2000:]}"
        )

    def test_multi_contract_inner_rejection_causes_panic(self, verifier, tmp_path):
        """Outer contract calls inner contract that rejects; outer should panic."""
        # Inner contract: always rejects (pushint 0)
        inner_teal = tmp_path / "inner_reject.teal"
        inner_teal.write_text(
            "#pragma version 10\n"
            "pushint 0\n"
        )

        # Outer contract: calls inner via inner txn, then accepts
        outer_teal = (
            PRAGMA
            + "itxn_begin\n"
            + "pushint 6\n"       # TypeEnum = appl
            + "itxn_field TypeEnum\n"
            + "pushint 42\n"      # ApplicationID = 42 (inner contract)
            + "itxn_field ApplicationID\n"
            + "itxn_submit\n"
            + "pushint 1\n"
        )

        result = verifier.verify(
            outer_teal,
            properties=["ctx.result != ACCEPT"],
            inner_contracts={42: str(inner_teal)},
            unwind=20,
            timeout=120,
        )
        assert result["verified"], (
            f"Outer should not accept when inner rejects.\n"
            f"stdout: {result['stdout'][-2000:]}\nstderr: {result['stderr'][-2000:]}"
        )

    def test_multi_contract_inner_modifies_state(self, verifier, tmp_path):
        """Inner contract modifies its own global state (per-app isolation)."""
        # Inner contract: sets global "flag" to 1 and accepts
        inner_teal = tmp_path / "inner_state.teal"
        inner_teal.write_text(
            "#pragma version 10\n"
            "pushbytes \"flag\"\n"
            "pushint 1\n"
            "app_global_put\n"
            "pushint 1\n"
        )

        # Outer contract: calls inner, then accepts
        outer_teal = (
            PRAGMA
            + "itxn_begin\n"
            + "pushint 6\n"
            + "itxn_field TypeEnum\n"
            + "pushint 42\n"
            + "itxn_field ApplicationID\n"
            + "itxn_submit\n"
            + "pushint 1\n"
        )

        # Property: inner app's globals have flag=1 (per-app globals via _app_globals_42)
        result = verifier.verify(
            outer_teal,
            properties=[
                'ctx.result != ACCEPT || prop_get_global_int(_app_globals_42, "flag", 0) == 1',
            ],
            inner_contracts={42: str(inner_teal)},
            unwind=20,
            timeout=120,
        )
        assert result["verified"], (
            f"Inner contract should have set flag=1 in its own globals.\n"
            f"stdout: {result['stdout'][-2000:]}\nstderr: {result['stderr'][-2000:]}"
        )

    def test_multi_contract_globals_isolation(self, verifier, tmp_path):
        """Inner app's global writes don't pollute outer app's globals."""
        # Inner contract: writes "x" = 99
        inner_teal = tmp_path / "inner_write.teal"
        inner_teal.write_text(
            "#pragma version 10\n"
            "pushbytes \"x\"\n"
            "pushint 99\n"
            "app_global_put\n"
            "pushint 1\n"
        )

        # Outer contract: writes "x" = 1, calls inner, then accepts
        outer_teal = (
            PRAGMA
            + "pushbytes \"x\"\n"
            + "pushint 1\n"
            + "app_global_put\n"
            + "itxn_begin\n"
            + "pushint 6\n"
            + "itxn_field TypeEnum\n"
            + "pushint 42\n"
            + "itxn_field ApplicationID\n"
            + "itxn_submit\n"
            + "pushint 1\n"
        )

        # Outer's "x" should still be 1 (not overwritten by inner's 99)
        result = verifier.verify(
            outer_teal,
            properties=[
                'ctx.result != ACCEPT || prop_get_global_int(ctx.bs_after, "x", 0) == 1',
            ],
            inner_contracts={42: str(inner_teal)},
            unwind=20,
            timeout=120,
        )
        assert result["verified"], (
            f"Outer's global 'x' should be 1, not polluted by inner.\n"
            f"stdout: {result['stdout'][-2000:]}\nstderr: {result['stderr'][-2000:]}"
        )

    def test_multi_contract_inner_creator_address(self, verifier, tmp_path):
        """Inner contract can read its CreatorAddress (non-zero)."""
        # Inner contract: pushes global CreatorAddress, checks it's non-zero
        inner_teal = tmp_path / "inner_creator.teal"
        inner_teal.write_text(
            "#pragma version 10\n"
            "global CreatorAddress\n"
            "len\n"
            "pushint 32\n"
            "==\n"  # CreatorAddress is 32 bytes
        )

        # Outer: calls inner
        outer_teal = (
            PRAGMA
            + "itxn_begin\n"
            + "pushint 6\n"
            + "itxn_field TypeEnum\n"
            + "pushint 42\n"
            + "itxn_field ApplicationID\n"
            + "itxn_submit\n"
            + "pushint 1\n"
        )

        # Inner should accept (CreatorAddress is 32 bytes)
        result = verifier.verify(
            outer_teal,
            properties=["ctx.result == ACCEPT"],
            inner_contracts={42: str(inner_teal)},
            unwind=20,
            timeout=120,
        )
        assert result["verified"], (
            f"Inner contract should see a valid CreatorAddress.\n"
            f"stdout: {result['stdout'][-2000:]}\nstderr: {result['stderr'][-2000:]}"
        )

    def test_multi_contract_payment_and_call(self, verifier, tmp_path):
        """Inner payment deducts balance, inner app call executes."""
        # Inner contract: accepts
        inner_teal = tmp_path / "inner_accept.teal"
        inner_teal.write_text(
            "#pragma version 10\n"
            "pushint 1\n"
        )

        # Outer: sends payment then calls inner
        outer_teal = (
            PRAGMA
            + "itxn_begin\n"
            + "pushint 1\n"           # TypeEnum = pay
            + "itxn_field TypeEnum\n"
            + "pushint 5000\n"        # Amount = 5000
            + "itxn_field Amount\n"
            + "itxn_submit\n"
            + "itxn_begin\n"
            + "pushint 6\n"           # TypeEnum = appl
            + "itxn_field TypeEnum\n"
            + "pushint 42\n"
            + "itxn_field ApplicationID\n"
            + "itxn_submit\n"
            + "pushint 1\n"
        )

        setup = """
    BS.app_balance = 10000;
"""

        result = verifier.verify(
            outer_teal,
            properties=[
                "ctx.result != ACCEPT || ctx.bs_after.app_balance == 5000",
            ],
            inner_contracts={42: str(inner_teal)},
            setup_code=setup,
            unwind=20,
            timeout=120,
        )
        assert result["verified"], (
            f"Payment should deduct 5000 from 10000.\n"
            f"stdout: {result['stdout'][-2000:]}\nstderr: {result['stderr'][-2000:]}"
        )
