import codeql.teal.ast.AST

/** The `b+` opcode: big-endian unsigned integer addition. */
class BaddOpcode extends AstNode instanceof TOpcode_badd {
    override int getStackDelta() { result = -1 }
}

/** The `b-` opcode: big-endian unsigned integer subtraction. */
class BsubOpcode extends AstNode instanceof TOpcode_bsub {
    override int getStackDelta() { result = -1 }
}

/** The `b/` opcode: big-endian unsigned integer division. */
class BdivOpcode extends AstNode instanceof TOpcode_bdiv {
    override int getStackDelta() { result = -1 }
}

/** The `b*` opcode: big-endian unsigned integer multiplication. */
class BmulOpcode extends AstNode instanceof TOpcode_bmul {
    override int getStackDelta() { result = -1 }
}

/** The `b%` opcode: big-endian unsigned integer modulo. */
class BmodOpcode extends AstNode instanceof TOpcode_bmod {
    override int getStackDelta() { result = -1 }
}

/** The `bsqrt` opcode: big-endian unsigned integer square root. */
class BsqrtOpcode extends AstNode instanceof TOpcode_bsqrt {
    override int getStackDelta() { result = 0 }
}
