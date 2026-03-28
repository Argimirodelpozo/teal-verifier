import codeql.teal.ast.AST
private import codeql.teal.ast.internal.TreeSitter

/** The `dig` opcode: duplicate value from depth N of the stack. */
class DigOpcode extends AstNode, TOpcode_dig {
    DigOpcode() { toTreeSitter(this) instanceof Teal::SingleNumericArgumentOpcode }

    override int getStackDelta() { result = 1 }

    int getValue() { result =
        toTreeSitter(this).(Teal::SingleNumericArgumentOpcode).getValue().getValue().toInt() }
}

/** The `proto` opcode: declare subroutine prototype (input/output counts). */
class ProtoOpcode extends AstNode instanceof TOpcode_proto {
    override int getStackDelta() { result = 0 }

    int getNumberOfInputArgs() {
        result = toTreeSitter(this).(Teal::DoubleNumericArgumentOpcode).getValue1().toString().toInt()
    }

    override int getNumberOfOutputArgs() {
        result = toTreeSitter(this).(Teal::DoubleNumericArgumentOpcode).getValue2().toString().toInt()
    }
}

/** The `pop` opcode: remove top of stack. */
class PopOpcode extends AstNode instanceof TOpcode_pop {
    override int getStackDelta() { result = -1 }
}

/** The `popn` opcode: remove N values from stack. */
class PopnOpcode extends AstNode instanceof TOpcode_popn {
    override int getStackDelta() {
        result = -toTreeSitter(this).(Teal::SingleNumericArgumentOpcode).getValue().toString().toInt()
    }
}

/** The `dup` opcode: duplicate top of stack. */
class DupOpcode extends AstNode instanceof TOpcode_dup {
    override int getStackDelta() { result = 1 }
}

/** The `dup2` opcode: duplicate top two values of stack. */
class Dup2Opcode extends AstNode instanceof TOpcode_dup2 {
    override int getStackDelta() { result = 2 }
}

/** The `dupn` opcode: duplicate top of stack N times. */
class DupnOpcode extends AstNode instanceof TOpcode_dupn {
    override int getStackDelta() {
        result = toTreeSitter(this).(Teal::SingleNumericArgumentOpcode).getValue().toString().toInt()
    }
}

/** The `swap` opcode: swap top two values of stack. */
class SwapOpcode extends AstNode instanceof TOpcode_swap {
    override int getStackDelta() { result = 0 }
}

/** The `bury` opcode: replace value at depth N of the stack. */
class BuryOpcode extends AstNode instanceof TOpcode_bury {
    override int getStackDelta() { result = -1 }
}

/** The `cover` opcode: move top of stack to depth N. */
class CoverOpcode extends AstNode instanceof TOpcode_cover {
    override int getStackDelta() { result = 0 }
}

/** The `uncover` opcode: move value from depth N to top of stack. */
class UncoverOpcode extends AstNode instanceof TOpcode_uncover {
    override int getStackDelta() { result = 0 }
}

/** The `frame_dig` opcode: access value relative to frame pointer. */
class FrameDigOpcode extends AstNode instanceof TOpcode_frame_dig {
    override int getStackDelta() { result = 1 }
}

/** The `frame_bury` opcode: store value relative to frame pointer. */
class FrameBuryOpcode extends AstNode instanceof TOpcode_frame_bury {
    override int getStackDelta() { result = -1 }
}

/** The `select` opcode: conditional select between two values. */
class SelectOpcode extends AstNode instanceof TOpcode_select {
    override int getStackDelta() { result = -2 }
}
