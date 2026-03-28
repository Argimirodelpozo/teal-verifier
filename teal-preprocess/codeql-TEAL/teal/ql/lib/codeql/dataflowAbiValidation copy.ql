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


from AstNode n, int i
// where n.getTopOfStackAtEnd()
select n.getFile(), n.getLineNumber(), i, n.getStackInputByOrder(i)