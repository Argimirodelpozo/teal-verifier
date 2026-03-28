import codeql.teal.ast.AST

/** The `&&` opcode: logical AND. */
class AndOpcode extends AstNode instanceof TOpcode_and {
    override int getStackDelta() { result = -1 }
}

/** The `||` opcode: logical OR. */
class OrOpcode extends AstNode instanceof TOpcode_or {
    override int getStackDelta() { result = -1 }
}

/** The `&` opcode: bitwise AND. */
class BitandOpcode extends AstNode instanceof TOpcode_bitand {
    override int getStackDelta() { result = -1 }
}

/** The `|` opcode: bitwise OR. */
class BitorOpcode extends AstNode instanceof TOpcode_bitor {
    override int getStackDelta() { result = -1 }
}

/** The `^` opcode: bitwise XOR. */
class BitxorOpcode extends AstNode instanceof TOpcode_bitxor {
    override int getStackDelta() { result = -1 }
}

/** The `~` opcode: bitwise NOT. */
class BitnotOpcode extends AstNode instanceof TOpcode_bitnot {
    override int getStackDelta() { result = 0 }
}

/** The `b|` opcode: byte-array bitwise OR. */
class BorOpcode extends AstNode instanceof TOpcode_bor {
    override int getStackDelta() { result = -1 }
}

/** The `b&` opcode: byte-array bitwise AND. */
class BandOpcode extends AstNode instanceof TOpcode_band {
    override int getStackDelta() { result = -1 }
}

/** The `b^` opcode: byte-array bitwise XOR. */
class BxorOpcode extends AstNode instanceof TOpcode_bxor {
    override int getStackDelta() { result = -1 }
}

/** The `b~` opcode: byte-array bitwise NOT. */
class BnotOpcode extends AstNode instanceof TOpcode_bnot {
    override int getStackDelta() { result = 0 }
}
