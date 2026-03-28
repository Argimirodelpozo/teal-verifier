import codeql.teal.ast.AST
import codeql.teal.ast.internal.TreeSitter
import codeql.teal.cfg.BasicBlocks
import codeql.teal.SSA.SSA

/** The `load` opcode: load value from scratch space by index. */
class LoadOpcode extends AstNode instanceof TOpcode_load {
    override int getStackDelta() { result = 1 }

    int getSPVarIndex() {
        result = toTreeSitter(this).(Teal::LoadOpcode).getValue().toString().toInt()
    }

    SSAVar getScratchSpaceStoredVariable() {
        result = this.getInfluencingStore().getScratchSpaceStoredVariable()
    }

    StoreOpcode getInfluencingStore() {
        exists(StoreOpcode store | store.getSPVarIndex() = this.getSPVarIndex() and store.reaches(this)
            and store.getBasicBlock().dominates(this.getBasicBlock())
            and not exists(StoreOpcode alt_store |
                alt_store.getSPVarIndex() = this.getSPVarIndex() and
                store.reaches(alt_store) and
                alt_store.reaches(this) and
                alt_store != store and
                store.getBasicBlock().dominates(alt_store.getBasicBlock()) and alt_store.getBasicBlock().dominates(this.getBasicBlock()))
            and result = store)
    }
}

/** The `store` opcode: store value to scratch space by index. */
class StoreOpcode extends AstNode instanceof TOpcode_store {
    override int getStackDelta() { result = -1 }

    int getSPVarIndex() {
        result = toTreeSitter(this).(Teal::StoreOpcode).getValue().toString().toInt()
    }

    SSAVar getScratchSpaceStoredVariable() {
        result = this.getConsumedVars()
    }

    predicate isUnivocal() {
        count(this.getScratchSpaceStoredVariable()) = 1
    }
}

/** The `loads` opcode: load value from scratch space by stack index. */
class LoadsOpcode extends AstNode instanceof TOpcode_loads {
    override int getStackDelta() { result = 0 }
}

/** The `stores` opcode: store value to scratch space by stack index. */
class StoresOpcode extends AstNode instanceof TOpcode_stores {
    override int getStackDelta() { result = -2 }
}

/** The `gload` opcode: load scratch space value from another transaction in group. */
class GloadOpcode extends AstNode instanceof TOpcode_gload {
    override int getStackDelta() { result = 1 }
}

/** The `gloads` opcode: load scratch space value from another transaction by stack index. */
class GloadsOpcode extends AstNode instanceof TOpcode_gloads {
    override int getStackDelta() { result = 0 }
}

/** The `gloadss` opcode: load scratch space value from another transaction by stack group and slot. */
class GloadssOpcode extends AstNode instanceof TOpcode_gloadss {
    override int getStackDelta() { result = -1 }
}

/** The `gaid` opcode: get asset ID created by another transaction in group. */
class GaidOpcode extends AstNode instanceof TOpcode_gaid {
    override int getStackDelta() { result = 1 }
}

/** The `gaids` opcode: get asset ID created by another transaction by stack index. */
class GaidsOpcode extends AstNode instanceof TOpcode_gaids {
    override int getStackDelta() { result = 0 }
}
