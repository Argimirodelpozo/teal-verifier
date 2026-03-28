/**
 * @name Updatable Application
 * @description Detects stateful TEAL contracts that can be updated.
 *              An application is updatable if OnCompletion == UpdateApplication (4)
 *              can reach an approval exit without being blocked.
 * @kind problem
 * @severity high
 * @id teal/is-updatable
 * @tags security
 *      tealer
 */

import codeql.teal.ast.AST
import TealerCommon

from Program prog, BasicBlock approvalBB
where
  approvalBB = approvalExit() and
  approvalBB.getFirstNode().getAstNode().getProgram() = prog and
  approvalExitUnguardedForAction(approvalBB, onCompletionUpdateApplication())
select prog,
  "Application is updatable: OnCompletion == UpdateApplication can reach an approval exit without a guard."
