/**
 * @name Unprotected Deletable Application
 * @description Detects stateful TEAL contracts that can be deleted AND lack
 *              sender == creator access control on the delete path.
 *              More severe than is-deletable: anyone can delete the app.
 * @kind problem
 * @severity high
 * @id teal/unprotected-deletable
 * @tags security
 *      tealer
 */

import codeql.teal.ast.AST
import TealerCommon

from Program prog, BasicBlock approvalBB
where
  approvalBB = approvalExit() and
  approvalBB.getFirstNode().getAstNode().getProgram() = prog and
  approvalExitUnguardedForAction(approvalBB, onCompletionDeleteApplication()) and
  not senderCreatorGuardDominates(approvalBB)
select prog,
  "Application is deletable by anyone: no sender == creator check guards the approval path that allows DeleteApplication."
