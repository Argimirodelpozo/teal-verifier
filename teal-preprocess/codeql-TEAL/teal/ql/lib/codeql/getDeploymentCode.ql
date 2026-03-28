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
private import codeql.teal.cfg.Completion
private import codeql.teal.ast.Jumps

private import codeql.teal.ast.Transaction

TxnOpcode currentAppIDGet(){
    result.getField() = "ApplicationID"
}

//TODO: exclusive or
LogicalComparisonOp compareWithZero(){
    getGenerator(result.firstOp()).tryCastToInt() = 0
    or
    getGenerator(result.secondOp()).tryCastToInt() = 0
}

LogicalComparisonOp deploymentCondition(){
    (result.toString() = "==" or result.toString() = "!=") and
    (getGenerator(result.firstOp()) = currentAppIDGet().getOutputVar(1)
    and getGenerator(result.secondOp()).tryCastToInt() = 0
    or
    getGenerator(result.secondOp()) = currentAppIDGet().getOutputVar(1)
    and getGenerator(result.firstOp()).tryCastToInt() = 0)
}

//TODO: finish. Should be block right after the block containing the deployment,
// with the correct condition. Then find reachable by this block and bingo
BasicBlock firstDeploymentBlock(){
    exists(Completion::BooleanSuccessor s | s.getValue() = true and
        result = deploymentCondition().(AstNode).getBasicBlock().getASuccessor(s) and
        deploymentCondition().getOperator() = "=="
        or
        s.getValue() = false and
        result = deploymentCondition().(AstNode).getBasicBlock().getASuccessor(s) and
        deploymentCondition().getOperator() = "!="
    )
    //     (
    //         (
    //             s.getValue() = true and
    //             result = b.getLastNode().getAstNode().(BnzOpcode).getNextNode(true).getBasicBlock()
    //         )
    //         or
    //         (
    //             s.getValue() = false and 
    //             result = b.getLastNode().getAstNode().(BzOpcode).getNextNode(false).getBasicBlock()
    //         )
    //     )
    // )
}

BasicBlock deploymentCFG(){
    result = firstDeploymentBlock().getAPredecessor+() or
    result = firstDeploymentBlock().getASuccessor*()
    
}

//TODO: get basic blocks dominated by this

from AstNode n
select n