private import codeql.teal.ast.AST
private import codeql.teal.cfg.BasicBlocks
private import codeql.teal.SSA.SSA
private import codeql.teal.ast.internal.TreeSitter

class TInnerTransactionStart = TOpcode_itxn_begin or TOpcode_itxn_next;
class TInnerTransactionEnd = TOpcode_itxn_next or TOpcode_itxn_submit;

class InnerTransactionStart extends AstNode instanceof TInnerTransactionStart {
    InnerTransactionEnd getItxnClosure() {
        this != result and
        this.reaches(result)
    }
}

class InnerTransactionEnd extends AstNode instanceof TInnerTransactionEnd {
}

class InnerTransactionBegin extends InnerTransactionStart instanceof TOpcode_itxn_begin {
    override int getStackDelta() { result = 0 }
}

class InnerTransactionField extends AstNode instanceof TOpcode_itxn_field {
    override int getStackDelta() { result = -1 }

    predicate contributesToItxn(InnerTransactionStart begin, InnerTransactionEnd itxnClosure) {
        //eliminate trivial case itxn_next = itxn_next
        begin != itxnClosure and
        begin.getItxnClosure() = itxnClosure and
        begin.reaches(this) and this.reaches(itxnClosure)
    }

    SSAVar getItxnFieldVal() {
        result = this.getConsumedVars()
    }

    string getItxnField() {
        result = toTreeSitter(this).(Teal::ItxnFieldOpcode).getTxnField().toString()
    }
}

class InnerTransactionNext extends InnerTransactionStart, InnerTransactionEnd instanceof TOpcode_itxn_next {
    override int getStackDelta() { result = 0 }
}

class InnerTransactionSubmit extends InnerTransactionEnd instanceof TOpcode_itxn_submit {
    override int getStackDelta() { result = 0 }

    InnerTransactionStart getStart() {
        result.getItxnClosure() = this
    }

    InnerTransactionBegin getItxnBegin() {
        result.getItxnClosure() = this or
        result.getItxnClosure() = this.getItxnNext()
    }

    InnerTransactionNext getItxnNext() {
        result.getItxnClosure() = this
    }

    //TODO: get group
    AstNode crossContractCallNextOp() {
        if exists(InnerTransactionField field |
            field.contributesToItxn(this.getStart(), this)
        )
        // disallow reentrancy
        then exists(AstNode n | n.getFile() != this.getFile() and result = n)
        else none()
    }
}

class ItxnFieldName extends string {
    ItxnFieldName() {
        this = "Sender" or this = "Fee" or this = "FirstValid" or
        this = "FirstValidTime" or this = "LastValid" or this = "Note" or
        this = "Lease" or this = "Receiver" or this = "Amount" or this = "CloseRemainderTo" or
        this = "VotePK" or this = "SelectionPK" or this = "VoteFirst" or this = "VoteLast" or
        this = "VoteKeyDilution" or this = "Type" or this = "TypeEnum" or this = "XferAsset" or
        this = "AssetAmount" or this = "AssetSender" or this = "AssetReceiver" or
        this = "AssetCloseTo" or this = "GroupIndex" or this = "TxID" or this = "ApplicationID" or
        this = "OnCompletion" or this = "NumAppArgs" or this = "NumAccounts" or
        this = "ApprovalProgram" or this = "ClearStateProgram" or this = "RekeyTo" or
        this = "ConfigAsset" or this = "ConfigAssetTotal" or this = "ConfigAssetDecimals" or
        this = "ConfigAssetDefaultFrozen" or this = "ConfigAssetUnitName" or
        this = "ConfigAssetName" or this = "ConfigAssetURL" or this = "ConfigAssetMetadataHash" or
        this = "ConfigAssetManager" or this = "ConfigAssetReserve" or this = "ConfigAssetFreeze" or
        this = "ConfigAssetClawback" or this = "FreezeAsset" or this = "FreezeAssetAccount" or
        this = "FreezeAssetFrozen" or this = "NumAssets" or this = "NumApplications" or
        this = "GlobalNumUint" or this = "GlobalNumByteSlice" or this = "LocalNumUint" or
        this = "LocalNumByteSlice" or this = "ExtraProgramPages" or this = "Nonparticipation" or
        this = "NumLogs" or this = "CreatedAssetID" or this = "CreatedApplicationID" or
        this = "LastLog" or this = "StateProofPK" or this = "NumApprovalProgramPages" or
        this = "NumClearStateProgramPages"
    }
}

/** The `itxn` opcode: access last inner transaction fields. */
class ItxnOpcode extends AstNode instanceof TOpcode_itxn {
    override int getStackDelta() { result = 1 }
}

/** The `itxna` opcode: access last inner transaction array fields. */
class ItxnaOpcode extends AstNode instanceof TOpcode_itxna {
    override int getStackDelta() { result = 1 }
}

/** The `itxnas` opcode: access last inner transaction array fields by stack index. */
class ItxnasOpcode extends AstNode instanceof TOpcode_itxnas {
    override int getStackDelta() { result = 0 }
}
