private import codeql.teal.ast.AST
private import codeql.teal.ast.internal.TreeSitter


class TIntegerConstant = TOpcode_int or TOpcode_intc or TOpcode_intc_0 or
    TOpcode_intc_1 or TOpcode_intc_2 or TOpcode_intc_3 or TOpcode_pushint;


class IntegerConstant extends AstNode instanceof TIntegerConstant {
    abstract int getValue();
}

/** The `int` pseudo-opcode: push an integer constant. */
class IntOpcode extends IntegerConstant instanceof TOpcode_int {
    override int getStackDelta() { result = 1 }

    override int getValue() {
        result = toTreeSitter(this).(Teal::SingleNumericArgumentOpcode).getValue().toString().toInt()
    }
}

/** The `intcblock` opcode: define a block of integer constants. */
class IntcblockOpcode extends AstNode instanceof TOpcode_intcblock {
    override int getStackDelta() { result = 0 }

    int getValue(int i) {
        result = toTreeSitter(this).(Teal::IntcblockOpcode).getValue(i).toString().toInt()
    }
}

/** The `intc` opcode: push integer constant by index. */
class IntcOpcode extends IntegerConstant instanceof TOpcode_intc {
    override int getStackDelta() { result = 1 }

    int getIndex() {
        result = toTreeSitter(this).(Teal::IntcOpcode).getValue().toString().toInt()
    }

    //TODO: deberia ser el intcblock MAS CERCANO. Por ahora asumimos que hay uno solo
    override int getValue() {
        exists(IntcblockOpcode op |
            op.getBasicBlock().dominates(this.getBasicBlock()) and
            result = op.getValue(this.getIndex())
        )
    }
}

/** The `intc_0` opcode: push integer constant 0 from intcblock. */
class Intc0Opcode extends IntegerConstant instanceof TOpcode_intc_0 {
    override int getStackDelta() { result = 1 }

    //TODO: deberia ser el intcblock MAS CERCANO. Por ahora asumimos que hay uno solo
    override int getValue() {
        exists(IntcblockOpcode op |
            op.getBasicBlock().dominates(this.getBasicBlock()) and
            result = op.getValue(0)
        )
    }
}

/** The `intc_1` opcode: push integer constant 1 from intcblock. */
class Intc1Opcode extends IntegerConstant instanceof TOpcode_intc_1 {
    override int getStackDelta() { result = 1 }

    //TODO: deberia ser el intcblock MAS CERCANO. Por ahora asumimos que hay uno solo
    override int getValue() {
        exists(IntcblockOpcode op |
            op.getBasicBlock().dominates(this.getBasicBlock()) and
            result = op.getValue(1)
        )
    }
}

/** The `intc_2` opcode: push integer constant 2 from intcblock. */
class Intc2Opcode extends IntegerConstant instanceof TOpcode_intc_2 {
    override int getStackDelta() { result = 1 }

    //TODO: deberia ser el intcblock MAS CERCANO. Por ahora asumimos que hay uno solo
    override int getValue() {
        exists(IntcblockOpcode op |
            op.getBasicBlock().dominates(this.getBasicBlock()) and
            result = op.getValue(2)
        )
    }
}

/** The `intc_3` opcode: push integer constant 3 from intcblock. */
class Intc3Opcode extends IntegerConstant instanceof TOpcode_intc_3 {
    override int getStackDelta() { result = 1 }

    //TODO: deberia ser el intcblock MAS CERCANO. Por ahora asumimos que hay uno solo
    override int getValue() {
        exists(IntcblockOpcode op |
            op.getBasicBlock().dominates(this.getBasicBlock()) and
            result = op.getValue(3)
        )
    }
}

/** The `pushint` opcode: push an immediate integer constant. */
class PushintOpcode extends IntegerConstant instanceof TOpcode_pushint {
    override int getStackDelta() { result = 1 }

    override int getValue() {
        result = toTreeSitter(this).(Teal::SingleNumericArgumentOpcode).getValue().toString().toInt()
    }
}

/** The `pushints` opcode: push multiple immediate integer constants. */
class PushintsOpcode extends AstNode instanceof TOpcode_pushints {
    override int getStackDelta() {
        result = strictcount(toTreeSitter(this).(Teal::PushintsOpcode).getValue(_))
    }
}

/** The `bytecblock` opcode: define a block of byte constants. */
class BytecblockOpcode extends AstNode instanceof TOpcode_bytecblock {
    override int getStackDelta() { result = 0 }

    string getValue(int i) {
        result = toTreeSitter(this).(Teal::BytecblockOpcode).getChild(i).toString()
    }
}

/** The `bytec` opcode: push byte constant by index. */
class BytecOpcode extends AstNode instanceof TOpcode_bytec {
    override int getStackDelta() { result = 1 }

    int getIndex() {
        result = toTreeSitter(this).(Teal::SingleNumericArgumentOpcode).getValue().toString().toInt()
    }

    //TODO: deberia ser el bytecblock MAS CERCANO. Por ahora asumimos que hay uno solo
    string getValue() {
        result = any(BytecblockOpcode bytecblock).getValue(this.getIndex())
    }

    override string toString() { result = this.getValue() }
}

/** The `bytec_0` opcode: push byte constant 0 from bytecblock. */
class Bytec0Opcode extends AstNode instanceof TOpcode_bytec_0 {
    override int getStackDelta() { result = 1 }

    //TODO: deberia ser el bytecblock MAS CERCANO. Por ahora asumimos que hay uno solo
    string getValue() {
        result = any(BytecblockOpcode bytecblock).getValue(0)
    }

    override string toString() { result = this.getValue() }
}

/** The `bytec_1` opcode: push byte constant 1 from bytecblock. */
class Bytec1Opcode extends AstNode instanceof TOpcode_bytec_1 {
    override int getStackDelta() { result = 1 }

    //TODO: deberia ser el bytecblock MAS CERCANO. Por ahora asumimos que hay uno solo
    string getValue() {
        result = any(BytecblockOpcode bytecblock).getValue(1)
    }

    override string toString() { result = this.getValue() }
}

/** The `bytec_2` opcode: push byte constant 2 from bytecblock. */
class Bytec2Opcode extends AstNode instanceof TOpcode_bytec_2 {
    override int getStackDelta() { result = 1 }

    //TODO: deberia ser el bytecblock MAS CERCANO. Por ahora asumimos que hay uno solo
    string getValue() {
        result = any(BytecblockOpcode bytecblock).getValue(2)
    }

    override string toString() { result = this.getValue() }
}

/** The `bytec_3` opcode: push byte constant 3 from bytecblock. */
class Bytec3Opcode extends AstNode instanceof TOpcode_bytec_3 {
    override int getStackDelta() { result = 1 }

    //TODO: deberia ser el bytecblock MAS CERCANO. Por ahora asumimos que hay uno solo
    string getValue() {
        result = any(BytecblockOpcode bytecblock).getValue(3)
    }

    override string toString() { result = this.getValue() }
}

/** The `pushbytes` opcode: push an immediate byte constant. */
class PushbytesOpcode extends AstNode instanceof TOpcode_pushbytes {
    override int getStackDelta() { result = 1 }
}

/** The `pushbytess` opcode: push multiple immediate byte constants. */
class PushbytessOpcode extends AstNode instanceof TOpcode_pushbytess {
    override int getStackDelta() {
        result = strictcount(toTreeSitter(this).(Teal::PushbytessOpcode).getChild(_))
    }
}

/** The `bzero` opcode: push a zero-filled byte array. */
class BzeroOpcode extends AstNode instanceof TOpcode_bzero {
    override int getStackDelta() { result = 0 }
}
