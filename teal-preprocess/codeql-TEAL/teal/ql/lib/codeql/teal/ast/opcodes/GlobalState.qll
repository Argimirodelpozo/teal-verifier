import codeql.teal.ast.AST
import codeql.teal.ast.internal.TreeSitter
import codeql.teal.cfg.BasicBlocks
import codeql.teal.SSA.SSA

// Mostly constants set by protocol
/** The `global` opcode: access global fields. */
class GlobalOpcode extends AstNode instanceof TOpcode_global {
    override int getStackDelta() { result = 1 }

    string getField() {
        result = toTreeSitter(this).(Teal::GlobalOpcode).getGlobalField()
    }

    predicate isIntegerField() {
        this.getField() = "MinTxnFee"
        or this.getField() = "MinBalance"
        or this.getField() = "MaxTxnLife"
        or this.getField() = "LogicSigVersion"
        or this.getField() = "GroupSize"
        or this.getField() = "Round"
    }

    predicate isBytesField() {
        not this.isIntegerField()
    }

    predicate fieldIsProtocolConstant() {
        this.getField() = "MinTxnFee" or
        this.getField() = "MinBalance" or
        this.getField() = "MaxTxnLife" or
        this.getField() = "ZeroAddress" or
        this.getField() = "LogicSigVersion"
    }
}

/** The `app_opted_in` opcode: check if account has opted in to application. */
class AppOptedInOpcode extends AstNode instanceof TOpcode_app_opted_in {
    override int getStackDelta() { result = -1 }
}

/** The `app_local_get` opcode: get local state value. */
class AppLocalGetOpcode extends AstNode instanceof TOpcode_app_local_get {
    override int getStackDelta() { result = -1 }
}

/** The `app_local_get_ex` opcode: get local state value with existence flag. */
class AppLocalGetExOpcode extends AstNode instanceof TOpcode_app_local_get_ex {
    override int getStackDelta() { result = -1 }
}

/** The `app_global_get` opcode: get global state value. */
class AppGlobalGetOpcode extends AstNode instanceof TOpcode_app_global_get {
    override int getStackDelta() { result = 0 }
}

/** The `app_global_get_ex` opcode: get global state value with existence flag. */
class AppGlobalGetExOpcode extends AstNode instanceof TOpcode_app_global_get_ex {
    override int getStackDelta() { result = 0 }
}

/** The `app_local_put` opcode: set local state value. */
class AppLocalPutOpcode extends AstNode instanceof TOpcode_app_local_put {
    override int getStackDelta() { result = -3 }
}

/** The `app_global_put` opcode: set global state value. */
class AppGlobalPutOpcode extends AstNode instanceof TOpcode_app_global_put {
    override int getStackDelta() { result = -2 }
}

/** The `app_local_del` opcode: delete local state value. */
class AppLocalDelOpcode extends AstNode instanceof TOpcode_app_local_del {
    override int getStackDelta() { result = -2 }
}

/** The `app_global_del` opcode: delete global state value. */
class AppGlobalDelOpcode extends AstNode instanceof TOpcode_app_global_del {
    override int getStackDelta() { result = -1 }
}

/** The `app_params_get` opcode: get application parameter. */
class AppParamsGetOpcode extends AstNode instanceof TOpcode_app_params_get {
    override int getStackDelta() { result = 1 }
}

/** The `asset_holding_get` opcode: get asset holding field. */
class AssetHoldingGetOpcode extends AstNode instanceof TOpcode_asset_holding_get {
    override int getStackDelta() { result = 0 }
}

/** The `asset_params_get` opcode: get asset parameter. */
class AssetParamsGetOpcode extends AstNode instanceof TOpcode_asset_params_get {
    override int getStackDelta() { result = 1 }
}

/** The `acct_params_get` opcode: get account parameter. */
class AcctParamsGetOpcode extends AstNode instanceof TOpcode_acct_params_get {
    override int getStackDelta() { result = 1 }
}

/** The `balance` opcode: get account balance. */
class BalanceOpcode extends AstNode instanceof TOpcode_balance {
    override int getStackDelta() { result = 0 }
}

/** The `min_balance` opcode: get account minimum balance. */
class MinBalanceOpcode extends AstNode instanceof TOpcode_min_balance {
    override int getStackDelta() { result = 0 }
}

/** The `online_stake` opcode: get account online stake. */
class OnlineStakeOpcode extends AstNode instanceof TOpcode_online_stake {
    override int getStackDelta() { result = 1 }
}

/** The `voter_params_get` opcode: get voter parameter. */
class VoterParamsGetOpcode extends AstNode instanceof TOpcode_voter_params_get {
    override int getStackDelta() { result = 1 }
}
