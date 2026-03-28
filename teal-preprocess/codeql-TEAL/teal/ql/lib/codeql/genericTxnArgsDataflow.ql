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


class TComparison = TOpcode_eq or TOpcode_lte or TOpcode_lt;

AstNode lengthExtraction(StackVar var){
    result instanceof TOpcode_len and 
    exists(Dataflow::Node src, Dataflow::Node sink | 
        src.(Dataflow::SsaDefinitionNode).asDefinition().(SSAWriteDef).getVar() = var
        and sink.getUnderlyingASTNode() = result and
        LocalFlow::localFlow(src, sink)
    )
}

predicate lengthCheckForVar(StackVar var, AssertOpcode assertion, AstNode comp){
    comp instanceof TComparison and
    assertion.getConsumedValues().(SSAWriteDef).getRHS() = comp
    and
    comp.getConsumedValues() = var.toDef() and
    exists(StackVar v | v != var and
        comp.getConsumedValues() = v.toDef()
        and exists(v.tryCastToInt()) and 
        count(comp.getConsumedValues()) = 2
    )
}


from Dataflow::Node op, Dataflow::Node n
where op.getUnderlyingASTNode().(TxnaOpcode).getField() = "ApplicationArgs" and
op != n and LocalFlow::localFlow(op, n)
select op.getUnderlyingASTNode().getLineNumber()*1000 + n.getUnderlyingASTNode().getLineNumber(), op.getUnderlyingASTNode().getFile(), op, n