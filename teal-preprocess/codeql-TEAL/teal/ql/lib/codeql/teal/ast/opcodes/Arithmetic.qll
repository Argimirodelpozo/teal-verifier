import codeql.teal.ast.AST

/** The `+` opcode: integer addition. */
class IntegerAddOpcode extends AstNode instanceof TOpcode_add {
    override int getStackDelta() { result = -1 }
}

/** The `-` opcode: integer subtraction. */
class SubOpcode extends AstNode instanceof TOpcode_sub {
    override int getStackDelta() { result = -1 }
}

/** The `*` opcode: integer multiplication. */
class MulOpcode extends AstNode instanceof TOpcode_mul {
    override int getStackDelta() { result = -1 }
}

/** The `/` opcode: integer division. */
class DivOpcode extends AstNode instanceof TOpcode_div {
    override int getStackDelta() { result = -1 }
}

/** The `%` opcode: integer modulo. */
class ModOpcode extends AstNode instanceof TOpcode_mod {
    override int getStackDelta() { result = -1 }
}

/** The `addw` opcode: wide integer addition (returns low and high words). */
class AddwOpcode extends AstNode instanceof TOpcode_addw {
    override int getStackDelta() { result = 0 }
}

/** The `mulw` opcode: wide integer multiplication (returns low and high words). */
class MulwOpcode extends AstNode instanceof TOpcode_mulw {
    override int getStackDelta() { result = 0 }
}

/** The `divmodw` opcode: wide integer division with modulo. */
class DivmodwOpcode extends AstNode instanceof TOpcode_divmodw {
    override int getStackDelta() { result = 0 }
}

/** The `exp` opcode: integer exponentiation. */
class ExpOpcode extends AstNode instanceof TOpcode_exp {
    override int getStackDelta() { result = -1 }
}

/** The `expw` opcode: wide integer exponentiation. */
class ExpwOpcode extends AstNode instanceof TOpcode_expw {
    override int getStackDelta() { result = 0 }
}

/** The `divw` opcode: wide integer division. */
class DivwOpcode extends AstNode instanceof TOpcode_divw {
    override int getStackDelta() { result = -2 }
}

/** The `sqrt` opcode: integer square root. */
class SqrtOpcode extends AstNode instanceof TOpcode_sqrt {
    override int getStackDelta() { result = 0 }
}

/** The `shl` opcode: bitwise shift left. */
class ShlOpcode extends AstNode instanceof TOpcode_shl {
    override int getStackDelta() { result = -1 }
}

/** The `shr` opcode: bitwise shift right. */
class ShrOpcode extends AstNode instanceof TOpcode_shr {
    override int getStackDelta() { result = -1 }
}
