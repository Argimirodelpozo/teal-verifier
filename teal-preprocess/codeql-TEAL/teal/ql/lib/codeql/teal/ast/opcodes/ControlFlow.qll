import codeql.teal.ast.AST
import codeql.teal.ast.internal.TreeSitter
import codeql.teal.SSA.SSA
private import codeql.teal.cfg.BasicBlocks

/** Exit opcodes that terminate contract execution. */
class ContractExitOpcode extends AstNode instanceof TContractExitOpcode {
}

/** The `return` opcode: ends program execution with top-of-stack value. */
class ReturnOpcode extends ContractExitOpcode instanceof TOpcode_return {
    override int getStackDelta() { result = 0 }

    SSAVar getTopOfStackAtEnd() {
        result.getBasicBlock() = this.getBasicBlock()
        and result.outStackOrder() = 1
    }
}

/** The `err` opcode: immediately fails the program. */
class ErrOpcode extends ContractExitOpcode instanceof TOpcode_err {
    override int getStackDelta() { result = 0 }
}

/** The `assert` opcode: fails if top of stack is zero. */
class AssertOpcode extends ContractExitOpcode instanceof TOpcode_assert {
    override int getStackDelta() { result = -1 }
}

/** Unconditional branch opcodes. */
class UnconditionalBranches extends AstNode instanceof TUnconditionalBranches {
}

/** The `b` opcode: unconditional branch to label. */
class BOpcode extends UnconditionalBranches instanceof TOpcode_b {
    override int getStackDelta() { result = 0 }

    Label getTargetLabel() {
        exists(Label l |
        l.getProgram() = this.getProgram() and
        l.getName() = toTreeSitter(this).(Teal::BOpcode).getChild().getValue() | result = l)
    }
}

/** The `callsub` opcode: call a subroutine. */
class CallsubOpcode extends UnconditionalBranches instanceof TOpcode_callsub {
    override int getStackDelta() { result = 0 }

    Label getTargetLabel() {
        exists(Label l |
            l.getProgram() = this.getProgram() and
            l.getName() = toTreeSitter(this).(Teal::CallsubOpcode).getChild().getValue() | result = l)
    }

    Subroutine getSubroutine() {
        result.getCallingOpcode() = this and result = this.getTargetLabel()
    }
}

/** The `retsub` opcode: return from subroutine. */
class RetsubOpcode extends UnconditionalBranches instanceof TOpcode_retsub {
    override int getStackDelta() {
        // Retsub's local stack delta is 0; the effective subroutine-level delta
        // (accounting for proto) is computed by retsubEffectiveDelta in StackDepth.qll
        result = 0
    }

    Label getEntrypoint() {
        exists(int i, Label l | i <= this.getPreviousLine().getParentIndex() and
            this.getProgram().getChild(i) = l and exists(l.getCallsubToLabel()) and not
            exists(int h, Label l2 | h < this.getParentIndex() and h > i and
                this.getProgram().getChild(h) = l2 and exists(l2.getCallsubToLabel())
            ) | result = l
        )
    }

    // predicate isReachableWithoutProto()

    ProtoOpcode getAffectingProto() {
        result = this.getEntrypoint().getNextLine()
    }

    AstNode predictRetsubReturn() {
        result = this.getEntrypoint().getCallsubToLabel().getNextLine()
    }
}

/** Simple conditional branch opcodes (bnz, bz). */
class SimpleConditionalBranches extends AstNode instanceof TSimpleConditionalBranches {
    Label getTargetLabel() {exists(Label l |
        l.getProgram() = this.getProgram() and (
            l.getName() = toTreeSitter(this).(Teal::BnzOpcode).getChild().(Teal::Token).getValue()
            or l.getName() = toTreeSitter(this).(Teal::BzOpcode).getChild().(Teal::Token).getValue()
        )
        | result = l)}

    SSAVar getGoverningVal() {
        result = this.getConsumedVars()
    }
}

/** The `bnz` opcode: branch if top of stack is non-zero. */
class BnzOpcode extends SimpleConditionalBranches instanceof TOpcode_bnz {
    override int getStackDelta() { result = -1 }

    AstNode getNextNode(boolean s) {
        s = true and result = this.getTargetLabel() or
        s = false and result = this.getNextLine()
    }
}

/** The `bz` opcode: branch if top of stack is zero. */
class BzOpcode extends SimpleConditionalBranches instanceof TOpcode_bz {
    override int getStackDelta() { result = -1 }

    AstNode getNextNode(boolean s) {
        s = false and result = this.getTargetLabel() or
        s = true and result = this.getNextLine()
    }
}

/** Multi-target conditional branch opcodes (switch, match). */
class MultiTargetConditionalBranch extends AstNode instanceof TMultiTargetConditionalBranch {
    Label getTargetLabels() {
        result.getName() = toTreeSitter(this).(Teal::SwitchOpcode).getChild(_).getValue() or
        result.getName() = toTreeSitter(this).(Teal::MatchOpcode).getChild(_).getValue()
    }

    Label getTargetLabel(int i) {
        result.getName() = toTreeSitter(this).(Teal::SwitchOpcode).getChild(i).getValue() or
        result.getName() = toTreeSitter(this).(Teal::MatchOpcode).getChild(i).getValue()
    }
}

/** The `switch` opcode: branch to one of multiple labels based on top of stack. */
class SwitchOpcode extends MultiTargetConditionalBranch {
    SwitchOpcode() { toTreeSitter(this) instanceof Teal::SwitchOpcode }

    override int getStackDelta() { result = -1 }
}

/** The `match` opcode: branch to label matching top of stack. */
class MatchOpcode extends MultiTargetConditionalBranch {
    MatchOpcode() { toTreeSitter(this) instanceof Teal::MatchOpcode }

    override int getStackDelta() {
        result = -(count(toTreeSitter(this).(Teal::MatchOpcode).getChild(_)) + 1)
    }

     // Get next node. 0 represents failure (continue to next line)
     // 1 to label count represents the corresponding label
    AstNode getNextNode(int value) {
        value = 0 and result = this.getNextLine()
        or
        value > 0 and result = this.getTargetLabel(value-1)
    }
}
