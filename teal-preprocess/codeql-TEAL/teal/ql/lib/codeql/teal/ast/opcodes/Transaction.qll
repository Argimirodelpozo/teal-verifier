import codeql.teal.ast.AST
import codeql.teal.ast.internal.TreeSitter
import codeql.teal.cfg.BasicBlocks
import codeql.teal.SSA.SSA

/** The `txn` opcode: access current transaction fields. */
class TxnOpcode extends AstNode instanceof TOpcode_txn {
    override int getStackDelta() { result = 1 }

    string getField() {
        result = toTreeSitter(this).(Teal::TxnOpcode).getTxnField().(Teal::Token).getValue().toString()
    }

    predicate isIntegerField() {
        this.getField() = "NumApprovalProgramPages" or
        this.getField() = "NumClearProgramPages" or
        this.getField() = "Nonparticipation" or
        this.getField() = "ExtraProgramPages" or
        this.getField() = "NumAppArgs" or
        this.getField() = "OnCompletion" or
        this.getField() = "TypeEnum"
    }

    predicate isBytesField() {
        not this.isIntegerField()
    }

    //TODO: review limits
    int bounded() {
        this.getField() = "NumApprovalProgramPages" and result in [0 .. 4] or
        this.getField() = "NumClearProgramPages" and result in [0 .. 4] or
        this.getField() = "Nonparticipation" and result in [0 .. 1] or
        this.getField() = "ExtraProgramPages" and result in [0 .. 4] or
        this.getField() = "NumAppArgs" and result in
            [0 .. max(getAppArgsRead(_, this.getProgram()).(TxnaOpcode).getIndex())] or
        this.getField() = "OnCompletion" and result in [0 .. 5] or
        this.getField() = "Type" and result in [0 .. 8]
    }
}

/** The `txna` opcode: access current transaction array fields. */
class TxnaOpcode extends AstNode instanceof TOpcode_txna {
    override int getStackDelta() { result = 1 }

    string getField() {
        result = toTreeSitter(this).(Teal::TxnaOpcode).getTxnArrayField()
    }

    int getIndex() {
        result = toTreeSitter(this).(Teal::TxnaOpcode).getIndex().getValue().toInt()
    }

    predicate isIntegerField() {
        this.getField() = "Assets" or
        this.getField() = "Applications"
    }

    predicate isBytesField() {
        not this.isIntegerField()
    }

    predicate isAddressField() {
        this.isBytesField() and
        this.getField() = "Accounts"
    }
}

AstNode getAppArgsRead(int i, Program p) {result.(TxnaOpcode).getField() = "ApplicationArgs" and
    result.(TxnaOpcode).getIndex() = i and result.getProgram() = p}

AstNode getOnCompletionUsage() {result.(TxnaOpcode).getField() = "OnCompletion"}

/** The `gtxn` opcode: access group transaction fields by index. */
class GtxnOpcode extends AstNode instanceof TOpcode_gtxn {
    override int getStackDelta() { result = 1 }

    string getField() {
        result = toTreeSitter(this).(Teal::GtxnOpcode).getTxnField().(Teal::Token).getValue().toString()
    }

    predicate isIntegerField() {
        this.getField() = "NumApprovalProgramPages" or
        this.getField() = "NumClearProgramPages" or
        this.getField() = "Nonparticipation" or
        this.getField() = "ExtraProgramPages" or
        this.getField() = "NumAppArgs" or
        this.getField() = "OnCompletion" or
        this.getField() = "Type"
    }

    predicate isBytesField() {
        not this.isIntegerField()
    }
}

/** The `gtxns` opcode: access group transaction fields by stack index. */
class GtxnsOpcode extends AstNode instanceof TOpcode_gtxns {
    override int getStackDelta() { result = 0 }

    string getField() {
        result = toTreeSitter(this).(Teal::GtxnsOpcode).getTxnField().(Teal::Token).getValue().toString()
    }

    predicate isIntegerField() {
        this.getField() = "NumApprovalProgramPages" or
        this.getField() = "NumClearProgramPages" or
        this.getField() = "Nonparticipation" or
        this.getField() = "ExtraProgramPages" or
        this.getField() = "NumAppArgs" or
        this.getField() = "OnCompletion" or
        this.getField() = "Type"
    }

    predicate isBytesField() {
        not this.isIntegerField()
    }
}

/** The `txnas` opcode: access current transaction array fields by stack index. */
class TxnasOpcode extends AstNode instanceof TOpcode_txnas {
    override int getStackDelta() { result = 0 }
}

/** The `gtxna` opcode: access group transaction array fields. */
class GtxnaOpcode extends AstNode instanceof TOpcode_gtxna {
    override int getStackDelta() { result = 1 }
}

/** The `gtxnas` opcode: access group transaction array fields by stack index. */
class GtxnasOpcode extends AstNode instanceof TOpcode_gtxnas {
    override int getStackDelta() { result = 0 }
}

/** The `gtxnsa` opcode: access group transaction array fields by stack group index. */
class GtxnsaOpcode extends AstNode instanceof TOpcode_gtxnsa {
    override int getStackDelta() { result = 0 }
}

/** The `gtxnsas` opcode: access group transaction array fields by stack group and array index. */
class GtxnsasOpcode extends AstNode instanceof TOpcode_gtxnsas {
    override int getStackDelta() { result = -1 }
}

/** The `gitxn` opcode: access inner transaction fields by index. */
class GitxnOpcode extends AstNode instanceof TOpcode_gitxn {
    override int getStackDelta() { result = 1 }
}

/** The `gitxna` opcode: access inner transaction array fields by index. */
class GitxnaOpcode extends AstNode instanceof TOpcode_gitxna {
    override int getStackDelta() { result = 1 }
}

/** The `gitxnas` opcode: access inner transaction array fields by stack index. */
class GitxnasOpcode extends AstNode instanceof TOpcode_gitxnas {
    override int getStackDelta() { result = 0 }
}
