private import codeql.teal.ast.AST
private import codeql.teal.ast.internal.TreeSitter

class TLogicalComparisonOp = TOpcode_lt or TOpcode_lte or TOpcode_gt or TOpcode_gte or
    TOpcode_eq or TOpcode_neq;

class LogicalComparisonOp extends AstNode instanceof TLogicalComparisonOp {

    Definition firstOp() { result = this.(AstNode).getStackInputByOrder(1) }
    Definition secondOp() { result = this.(AstNode).getStackInputByOrder(2) }
    string getOperator() { result = this.(AstNode).toString() }

    Definition getAnOp() { result = this.firstOp() or result = this.secondOp() }
}

class EqualsComparisonOpcode extends LogicalComparisonOp {
    EqualsComparisonOpcode() { this.getOperator() = "==" }
}

class NotEqualsComparisonOpcode extends LogicalComparisonOp {
    NotEqualsComparisonOpcode() { this.getOperator() = "!=" }
}

/** The `not` opcode: logical NOT. */
class NotOpcode extends AstNode instanceof TOpcode_not {
    override int getStackDelta() { result = 0 }
}

/** The `<` opcode with integer value prediction. */
class IntegerLessThanOpcode extends AstNode instanceof TOpcode_lt {
    override int getStackDelta() { result = -1 }

    // TODO: re-enable when SSA type inference (tryCastToInt) is implemented
    // int predictValue() {
    //     exists(int a, int b, SSAVar ssa_a, SSAVar ssa_b |
    //         a = ssa_a.tryCastToInt() and
    //         b = ssa_b.tryCastToInt() and
    //         ssa_a != ssa_b |
    //         if a < b then result = 1 else result = 0
    //     )
    // }
}

/** The `<=` opcode with integer value prediction. */
class IntegerLteOpcode extends AstNode instanceof TOpcode_lte {
    override int getStackDelta() { result = -1 }

    // TODO: re-enable when SSA type inference (tryCastToInt) is implemented
    // int predictValue() {
    //     exists(int a, int b, SSAVar ssa_a, SSAVar ssa_b |
    //         a = ssa_a.tryCastToInt() and
    //         b = ssa_b.tryCastToInt() and
    //         ssa_a != ssa_b |
    //         if a <= b then result = 1 else result = 0
    //     )
    // }
}

/** The `>` opcode with integer value prediction. */
class IntegerGreaterThanOpcode extends AstNode instanceof TOpcode_gt {
    override int getStackDelta() { result = -1 }

    // TODO: re-enable when SSA type inference (tryCastToInt) is implemented
    // int predictValue() {
    //     exists(int a, int b, SSAVar ssa_a, SSAVar ssa_b |
    //         a = ssa_a.tryCastToInt() and
    //         b = ssa_b.tryCastToInt() and
    //         ssa_a != ssa_b |
    //         if a > b then result = 1 else result = 0
    //     )
    // }
}

/** The `>=` opcode with integer value prediction. */
class IntegerGteOpcode extends AstNode instanceof TOpcode_gte {
    override int getStackDelta() { result = -1 }

    // TODO: re-enable when SSA type inference (tryCastToInt) is implemented
    // int predictValue() {
    //     exists(int a, int b, SSAVar ssa_a, SSAVar ssa_b |
    //         a = ssa_a.tryCastToInt() and
    //         b = ssa_b.tryCastToInt() and
    //         ssa_a != ssa_b |
    //         if a >= b then result = 1 else result = 0
    //     )
    // }
}

/** The `==` opcode with integer value prediction. */
class IntegerEqualsOpcode extends AstNode instanceof TOpcode_eq {
    override int getStackDelta() { result = -1 }

    // TODO: re-enable when SSA type inference (tryCastToInt/StackVar) is implemented
    // int predictValue() {
    //     exists(int a, int b, StackVar ssa_a, StackVar ssa_b |
    //         a = ssa_a.tryCastToInt() and
    //         b = ssa_b.tryCastToInt() and
    //         ssa_a != ssa_b |
    //         if a = b then result = 1 else result = 0
    //     )
    // }
}

/** The `!=` opcode with integer value prediction. */
class IntegerNotEqualsOpcode extends AstNode instanceof TOpcode_neq {
    override int getStackDelta() { result = -1 }

    // TODO: re-enable when SSA type inference (tryCastToInt) is implemented
    // int predictValue() {
    //     exists(int a, int b, SSAVar ssa_a, SSAVar ssa_b |
    //         a = ssa_a.tryCastToInt() and
    //         b = ssa_b.tryCastToInt() and
    //         ssa_a != ssa_b |
    //         if a != b then result = 1 else result = 0
    //     )
    // }
}
