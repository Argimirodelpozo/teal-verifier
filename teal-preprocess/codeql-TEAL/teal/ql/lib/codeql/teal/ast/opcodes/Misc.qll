import codeql.teal.ast.AST

/** The `arg` opcode: push LogicSig argument by immediate index. */
class ArgOpcode extends AstNode instanceof TOpcode_arg {
    override int getStackDelta() { result = 1 }
}

/** The `arg_0` opcode: push LogicSig argument 0. */
class Arg0Opcode extends AstNode instanceof TOpcode_arg_0 {
    override int getStackDelta() { result = 1 }
}

/** The `arg_1` opcode: push LogicSig argument 1. */
class Arg1Opcode extends AstNode instanceof TOpcode_arg_1 {
    override int getStackDelta() { result = 1 }
}

/** The `arg_2` opcode: push LogicSig argument 2. */
class Arg2Opcode extends AstNode instanceof TOpcode_arg_2 {
    override int getStackDelta() { result = 1 }
}

/** The `arg_3` opcode: push LogicSig argument 3. */
class Arg3Opcode extends AstNode instanceof TOpcode_arg_3 {
    override int getStackDelta() { result = 1 }
}

/** The `args` opcode: push LogicSig argument by stack index. */
class ArgsOpcode extends AstNode instanceof TOpcode_args {
    override int getStackDelta() { result = 0 }
}

/** The `block` opcode: access block fields. */
class BlockOpcode extends AstNode instanceof TOpcode_block {
    override int getStackDelta() { result = 0 }
}
