import codeql.teal.ast.AST

/** The `sha256` opcode: SHA-256 hash. */
class Sha256Opcode extends AstNode instanceof TOpcode_sha256 {
    override int getStackDelta() { result = 0 }
}

/** The `sha512_256` opcode: SHA-512/256 hash. */
class Sha512_256Opcode extends AstNode instanceof TOpcode_sha512_256 {
    override int getStackDelta() { result = 0 }
}

/** The `keccak256` opcode: Keccak-256 hash. */
class Keccak256Opcode extends AstNode instanceof TOpcode_keccak256 {
    override int getStackDelta() { result = 0 }
}

/** The `sha3_256` opcode: SHA3-256 hash. */
class Sha3_256Opcode extends AstNode instanceof TOpcode_sha3_256 {
    override int getStackDelta() { result = 0 }
}

/** The `mimc` opcode: MiMC hash. */
class MimcOpcode extends AstNode instanceof TOpcode_mimc {
    override int getStackDelta() { result = 0 }
}
