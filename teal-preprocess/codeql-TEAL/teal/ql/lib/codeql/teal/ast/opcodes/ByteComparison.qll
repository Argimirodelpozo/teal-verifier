import codeql.teal.ast.AST

/** The `b<` opcode: big-endian unsigned integer less than. */
class BltOpcode extends AstNode instanceof TOpcode_blt {
    override int getStackDelta() { result = -1 }
}

/** The `b>` opcode: big-endian unsigned integer greater than. */
class BgtOpcode extends AstNode instanceof TOpcode_bgt {
    override int getStackDelta() { result = -1 }
}

/** The `b<=` opcode: big-endian unsigned integer less than or equal. */
class BlteOpcode extends AstNode instanceof TOpcode_blte {
    override int getStackDelta() { result = -1 }
}

/** The `b>=` opcode: big-endian unsigned integer greater than or equal. */
class BgteOpcode extends AstNode instanceof TOpcode_bgte {
    override int getStackDelta() { result = -1 }
}

/** The `b==` opcode: big-endian unsigned integer equality. */
class BeqOpcode extends AstNode instanceof TOpcode_beq {
    override int getStackDelta() { result = -1 }
}

/** The `b!=` opcode: big-endian unsigned integer inequality. */
class BneqOpcode extends AstNode instanceof TOpcode_bneq {
    override int getStackDelta() { result = -1 }
}
