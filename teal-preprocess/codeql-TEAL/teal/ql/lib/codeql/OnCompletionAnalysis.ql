// To create db, from root folder do:
// codeql database create --overwrite --search-path codeql/teal/extractor-pack -l teal test-projects/db1 -s test-projects/
// codeql-linux64/codeql/codeql database create --overwrite --search-path codeql/teal/extractor-pack -l teal test-projects/db1 -s test-projects/

private import codeql.teal.ast.internal.TreeSitter
private import codeql.teal.ast.AST
private import codeql.teal.SSA.SSA
private import codeql.teal.cfg.BasicBlocks
private import codeql.teal.cfg.CFG::CfgImpl
private import codeql.teal.cfg.CFG
private import codeql.teal.ast.InnerTransactions
private import codeql.teal.dataflow.Dataflow
private import codeql.teal.ast.BinaryComparison
private import codeql.teal.cfg.Completion
private import codeql.teal.ast.Jumps
private import codeql.teal.ast.IntegerConstants

private import codeql.teal.ast.Transaction

TxnOpcode onCompletionActionGet(){
    result.getField() = "OnCompletion"
}

int compareWithConstantInt(LogicalComparisonOp op){
    getGenerator(op.firstOp()).tryCastToInt() = result
    or
    getGenerator(op.secondOp()).tryCastToInt() = result
}

LogicalComparisonOp onCompletionConditional(){
    // (result.toString() = "==" or result.toString() = "!=") and
    getGenerator(result.firstOp()) = onCompletionActionGet().getOutputVar(1)
    // and getGenerator(result.secondOp()).tryCastToInt() = 0
    or
    getGenerator(result.secondOp()) = onCompletionActionGet().getOutputVar(1)
    // and getGenerator(result.firstOp()).tryCastToInt() = 0)
}

BasicBlock getAllExitBlocks(){
    result.getLastNode().getAstNode() instanceof TContractExitOpcode
}

BasicBlock getAllPossibleApprovalExits(){
    result = getAllExitBlocks() and 
    result.getLastNode().getAstNode() instanceof ReturnOpcode
    and (
        result.getLastNode().getAstNode().(ReturnOpcode).getTopOfStackAtEnd().tryCastToInt() != 0 or
        not exists(result.getLastNode().getAstNode().(ReturnOpcode).getTopOfStackAtEnd().tryCastToInt())
    )
}

BasicBlock getAllPossibleRejectionExits(){
    any()
    // result = getAllExitBlocks() and 
    // result.getLastNode().getAstNode() instanceof ReturnOpcode
    // and (
    //     result.getLastNode().getAstNode().(ReturnOpcode).getTopOfStackAtEnd().tryCastToInt() != 0 or
    //     not exists(result.getLastNode().getAstNode().(ReturnOpcode).getTopOfStackAtEnd().tryCastToInt())
    // )
}

StackVar findBranchGoverningVariable(BasicBlock bb){
    bb.getLastNode().getAstNode() instanceof SimpleConditionalBranches and
    result = bb.getLastNode().getAstNode().getConsumedVars()
    or
    result = bb.getLastNode().getAstNode().(ReturnOpcode).getTopOfStackAtEnd()
}

BasicBlock getCertainApprovalExits(){
    result = getAllExitBlocks() and findBranchGoverningVariable(result).tryCastToInt() != 0
}

BasicBlock getCertainRejectionExits(){
    result.getLastNode().getAstNode() instanceof ErrOpcode or
    result = getAllExitBlocks() and findBranchGoverningVariable(result).tryCastToInt() = 0
}


//simple detection. has some problems
predicate isDeletable(Program prog){
    exists(LogicalComparisonOp op | 
        op.getProgram() = prog and
        op = onCompletionConditional() and
        compareWithConstantInt(op) = 3 and
        exists(BasicBlock b | b = getAllPossibleApprovalExits()
        and not op.getBasicBlock().dominates(b)
        )
    )
}


// txna ApplicationArgs 0
// pushbytes 0x676f7665726e616e6365 // "governance"
// ==
// bnz main_l14
// err
//ESTE PATRON implica que de aca en mas el appargs0 vale esto
//como podemos codificar este comportamiento en cql?
predicate inputValueDeterminedByPath(TxnaOpcode op, BasicBlock b){
    // findBranchGoverningVariable(b).
    exists(Completion::BooleanSuccessor s | s.getValue() = true and
        op.getBasicBlock().(ConditionBlock).controls(b, s)
    )
}



// //TODO: finish. Should be block right after the block containing the deployment,
// // with the correct condition. Then find reachable by this block and bingo
// BasicBlock firstDeploymentBlock(){
//     exists(Completion::BooleanSuccessor s | s.getValue() = true and
//         result = deploymentCondition().(AstNode).getBasicBlock().getASuccessor(s)
//     )
//     //     (
//     //         (
//     //             s.getValue() = true and
//     //             result = b.getLastNode().getAstNode().(BnzOpcode).getNextNode(true).getBasicBlock()
//     //         )
//     //         or
//     //         (
//     //             s.getValue() = false and 
//     //             result = b.getLastNode().getAstNode().(BzOpcode).getNextNode(false).getBasicBlock()
//     //         )
//     //     )
//     // )
// }

//TODO: get basic blocks dominated by this

from Program prog
where not isDeletable(prog)
select prog