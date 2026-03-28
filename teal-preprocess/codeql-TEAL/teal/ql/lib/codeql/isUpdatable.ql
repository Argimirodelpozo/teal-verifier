/**
 * @name Updatable Application
 * @description Detects TEAL contracts that allow UpdateApplication.
 *              A contract is updatable if OnCompletion == 4 (UpdateApplication)
 *              is never explicitly checked/rejected.
 * @kind problem
 * @severity high
 * @id teal/is-updatable
 * @tags security
 */

import codeql.teal.ast.AST
import codeql.teal.cfg.BasicBlocks
import codeql.teal.ast.internal.TreeSitter
import codeql.teal.ast.opcodes.Transaction

/**
 * True if this node is a `txn OnCompletion` access
 */
predicate isOnCompletionAccess(AstNode n) {
  n instanceof TOpcode_txn and
  n.(TxnOpcode).getField() = "OnCompletion"
}

/**
 * True if this node pushes the integer 4 onto the stack
 * (covers `int 4` and `pushint 4`)
 */
predicate isIntFour(AstNode n) {
  (n instanceof TOpcode_int or n instanceof TOpcode_pushint) and
  toTreeSitter(n).(Teal::SingleNumericArgumentOpcode).getValue().toString() = "4"
}

/**
 * True if this basic block ends with an approval exit
 * i.e. its last AST node is a `return` or `int 1` / `return` pattern.
 * We use AnnotatedExitBasicBlock (normal exit) from BasicBlocks.
 */
predicate isApprovalExit(BasicBlock bb) {
  bb instanceof AnnotatedExitBasicBlock and
  bb.(AnnotatedExitBasicBlock).isNormal()
}

/**
 * True if the program contains a structural comparison of OnCompletion to 4.
 * Pattern: txn OnCompletion ... int 4 ... == (or !=)
 * We check at the token level (same approach as missingTxnFeeValidation)
 * since the AST-level operand wiring isn't exposed yet.
 */
predicate hasUpdateComparisonToken(Program p) {
  exists(AstNode txnNode, AstNode intNode, AstNode cmpNode |
    txnNode.getProgram() = p and
    isOnCompletionAccess(txnNode) and
    intNode.getProgram() = p and
    isIntFour(intNode) and
    cmpNode.getProgram() = p and
    (cmpNode instanceof TOpcode_eq or cmpNode instanceof TOpcode_neq)
  )
}

/**
 * Flag if:
 *  - The program has a normal (approval) exit
 *  - AND there is NO OnCompletion == 4 / != 4 comparison anywhere in it
 */
from Program p
where
  exists(BasicBlock bb |
    bb.getANode().getAstNode().getProgram() = p and
    isApprovalExit(bb)
  ) and
  not hasUpdateComparisonToken(p)
select p,
  "Application may be updatable: no OnCompletion == 4 check found."