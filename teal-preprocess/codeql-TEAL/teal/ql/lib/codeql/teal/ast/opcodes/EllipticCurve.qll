import codeql.teal.ast.AST

/** The `ec_add` opcode: elliptic curve point addition. */
class EcAddOpcode extends AstNode instanceof TOpcode_ec_add {
    override int getStackDelta() { result = -1 }
}

/** The `ec_mul` opcode: elliptic curve scalar multiplication. */
class EcMulOpcode extends AstNode instanceof TOpcode_ec_mul {
    override int getStackDelta() { result = -1 }
}

/** The `ec_pairing_check` opcode: elliptic curve pairing check. */
class EcPairingCheckOpcode extends AstNode instanceof TOpcode_ec_pairing_check {
    override int getStackDelta() { result = -1 }
}

/** The `ec_multi_scalar_mul` opcode: elliptic curve multi-scalar multiplication. */
class EcMultiScalarMulOpcode extends AstNode instanceof TOpcode_ec_multi_scalar_mul {
    override int getStackDelta() { result = -1 }
}

/** The `ec_subgroup_check` opcode: elliptic curve subgroup check. */
class EcSubgroupCheckOpcode extends AstNode instanceof TOpcode_ec_subgroup_check {
    override int getStackDelta() { result = 0 }
}

/** The `ec_map_to` opcode: map to elliptic curve point. */
class EcMapToOpcode extends AstNode instanceof TOpcode_ec_map_to {
    override int getStackDelta() { result = 0 }
}
