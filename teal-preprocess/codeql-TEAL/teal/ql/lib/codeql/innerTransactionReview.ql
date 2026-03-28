/**
 * @id teal/inner-txn-summary
 * @name Inner transaction review
 * @kind table
 */


// To create db, from root folder do:
// codeql database create --overwrite --search-path codeql/teal/extractor-pack -l teal test-projects/db1 -s test-projects/

private import codeql.teal.ast.internal.TreeSitter
private import codeql.teal.ast.AST
// private import codeql.teal.SSA.SSAOpcodeDefinitions
private import codeql.teal.cfg.BasicBlocks
private import codeql.teal.cfg.CFG::CfgImpl
private import codeql.teal.ast.InnerTransactions
// private import codeql.teal.SSA.SSAOpcodeDefinitions

// AstNode advance(AstNode current, AstNode end){
//     result != end and
//     (
//         result = current or 
//         result = advance(current.getBasicBlock().getNode(current.getIndexInBasicBlock()).getASuccessor().getAstNode(), end)
//         // start.getBasicBlock() = end.getBasicBlock() and result = start.getNextLine() or
//         // start.getBasicBlock().reaches(result.getBasicBlock()) and result.getBasicBlock().reaches(end.getBasicBlock())
//     )
// }

// from AstNode submit, AstNode input
// where submit instanceof TOpcode_itxn_submit and
// input.getBasicBlock().reaches(submit.getBasicBlock()) and 
// (input instanceof TOpcode_itxn_begin 
//     // or input instanceof TOpcode_itxn_field
//     ) 
// and
// not exists(AstNode mid | mid = advance(input, submit) and mid instanceof TOpcode_itxn_submit)
// select submit, advance(input, submit), input

from InnerTransactionField field, InnerTransactionStart start, InnerTransactionEnd end
where field.contributesToItxn(start, end)
select start, start.getLocation(), start.getLocation().getStartLine(), field.getLocation().getStartLine(), field.getItxnField(), field.getConsumedValues(), field.getConsumedVars(), end, end.getLocation().getStartLine()