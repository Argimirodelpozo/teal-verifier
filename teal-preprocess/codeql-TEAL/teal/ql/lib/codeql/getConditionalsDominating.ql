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

private import codeql.teal.ast.Transaction


class TComparison = TOpcode_neq or TOpcode_eq or TOpcode_lte or TOpcode_lt
    or TOpcode_gte or TOpcode_gt;

AstNode getConditionalsDominatingOp(AstNode op){
    exists(AstNode n | n.getBasicBlock().dominates(op.getBasicBlock()) and
        n instanceof TComparison | result = n)
}

AstNode getJumpDominatedByCondition(){
    exists(AstNode cond, AstNode op | cond = getConditionalsDominatingOp(op) and result = op
    and (op instanceof TOpcode_bnz or op instanceof TOpcode_bz) )
}


from Dataflow::Node op, Dataflow::Node n
where op.getUnderlyingASTNode().(TxnaOpcode).getField() = "ApplicationArgs" and
op != n and LocalFlow::localFlow(op, n)
select op.getUnderlyingASTNode().getLineNumber()*1000 + n.getUnderlyingASTNode().getLineNumber(), op.getUnderlyingASTNode().getFile(), op, n