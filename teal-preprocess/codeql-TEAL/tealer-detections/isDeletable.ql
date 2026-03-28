/**
 * @name Deletable Application
 * @description Detects stateful TEAL contracts that can be deleted.
 *              An application is deletable if OnCompletion == DeleteApplication (5)
 *              can reach an approval exit without being blocked.
 * @kind problem
 * @severity high
 * @id teal/is-deletable
 * @tags security
 *      tealer
 */

import codeql.teal.ast.AST
import TealerCommon

from Program prog, BasicBlock approvalBB
where
  approvalBB = approvalExit() and
  approvalBB.getFirstNode().getAstNode().getProgram() = prog and
  approvalExitUnguardedForAction(approvalBB, onCompletionDeleteApplication())
select prog,
  "Application is deletable: OnCompletion == DeleteApplication can reach an approval exit without a guard."
