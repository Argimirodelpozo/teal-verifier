private import codeql.teal.cfg.BasicBlocks
private import codeql.Locations
private import codeql.teal.cfg.CFG as Cfg
private import codeql.teal.ast.AST
private import codeql.teal.ast.IntegerConstants
private import codeql.teal.SSA.SSA


//HOW COULD WE SIMULATE AN OP having a high consumption in an arbitrary point?
// That way we could know the exact shape the stack could be in
// SSAVar getMaybeLivingStackVarsAtOp(AstNode n){
//     result = n.getConsumedValues()
// }

//TODO: here we output, for each op, the shape of the stack here
// if there is more than one, we mark it
// basically we "pretend" that a given op consumes 1, 2, 3, 4... args until result does not change anymore
// then we show them