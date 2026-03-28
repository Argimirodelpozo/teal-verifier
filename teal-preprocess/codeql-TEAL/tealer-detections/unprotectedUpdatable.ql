/**
 * @name Unprotected Updatable Application
 * @description Detects stateful TEAL contracts that can be updated AND lack
 *              sender == creator access control on the update path.
 *              More severe than is-updatable: anyone can update the app.
 * @kind problem
 * @severity high
 * @id teal/unprotected-updatable
 * @tags security
 *      tealer
 */

import codeql.teal.ast.AST
import TealerCommon

from Program prog, BasicBlock approvalBB
where
  approvalBB = approvalExit() and
  approvalBB.getFirstNode().getAstNode().getProgram() = prog and
  approvalExitUnguardedForAction(approvalBB, onCompletionUpdateApplication()) and
  not senderCreatorGuardDominates(approvalBB)
select prog,
  "Application is updatable by anyone: no sender == creator check guards the approval path that allows UpdateApplication."
