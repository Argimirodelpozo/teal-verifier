// To create db, from root folder do:
// codeql database create --overwrite --search-path codeql/teal/extractor-pack -l teal test-projects/db1 -s test-projects/

private import codeql.teal.ast.internal.TreeSitter
private import codeql.teal.ast.AST
private import codeql.teal.SSA.SSA
private import codeql.teal.cfg.BasicBlocks
private import codeql.teal.cfg.CFG::CfgImpl
private import codeql.teal.cfg.CFG
private import codeql.teal.ast.InnerTransactions
private import codeql.teal.dataflow.Dataflow
private import codeql.teal.ast.BinaryComparison

private import codeql.teal.ast.Transaction

// Simple ABI method getter
// We get all basic blocks dominated by an EQUALS comparison with appArgs 0


class TComparison = TOpcode_neq or TOpcode_eq or TOpcode_lte or TOpcode_lt
    or TOpcode_gte or TOpcode_gt;

AstNode getConditionalsDominatingOp(AstNode op){
    exists(AstNode n | n.getBasicBlock().dominates(op.getBasicBlock()) and
        n instanceof TComparison | result = n)
}

AstNode getJumpDominatedByCondition(AstNode cond){
    exists(AstNode op | cond = getConditionalsDominatingOp(op) and result = op
    and (op instanceof TOpcode_bnz or op instanceof TOpcode_bz) )
}

predicate getMatchRouterAbiMethod(AstNode n){
    n instanceof TOpcode_match and
        n.getStackInputByOrder(1).(SSAWriteDef).getVar().getDeclarationNode() instanceof TxnaOpcode
        // and n.getStackInputByOrder(1).(SSAWriteDef).getVar().getDeclarationNode().(TxnaOpcode).getField() = "ApplicationArgs"
        // toTreeSitter(n).(Teal::MatchOpcode).getChild(i) = 
}

predicate getAbiMethod(BasicBlock bb){
    exists(AstNode jmp | 
        // cond.getAn.(TxnaOpcode).getField() = "ApplicationArgs"
        // and appArgs.(TxnaOpcode).getIndex() = 0
        // and 
        // getJumpDominatedByCondition(cond) = jmp
        // and jmp.getBasicBlock().reaches(bb)
        // and cond.getAnOp().(SSAWriteDef).getVar().getDeclarationNode() instanceof TxnaOpcode
        // and 
        jmp.getBasicBlock().getASuccessor() = bb
        // and
        // (
        //     getConditionalsDominatingOp(bb.getLastNode().getAstNode()).getStackInputByOrder(0).(Txna)
        //     or
        //     getConditionalsDominatingOp(bb.getLastNode().getAstNode()).getStackInputByOrder(0)
        // ) 
    )
}

// predicate getAppArgs(){
//     result = 
// }

// AstNode getAppArgsComparison(){
//     exists(AstNode n | n instanceof TOpcode_eq and )
// }


from Dataflow::Node op, Dataflow::Node n
where op.getUnderlyingASTNode().(TxnaOpcode).getField() = "ApplicationArgs" and
op.getUnderlyingASTNode().(TxnaOpcode).getIndex() = 0
// op != n and LocalFlow::localFlow(op, n)
select op.getUnderlyingASTNode().getLineNumber()*1000 + n.getUnderlyingASTNode().getLineNumber(), op.getUnderlyingASTNode().getFile(), op, n