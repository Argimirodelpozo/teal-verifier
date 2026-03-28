/**
 * @name Missing CloseRemainderTo Validation
 * @description Detects contracts (especially LogicSigs) that do not validate
 *              the CloseRemainderTo transaction field. Without this check,
 *              an attacker can drain the account's entire Algo balance.
 * @kind problem
 * @severity high
 * @id teal/can-close-account
 * @tags security
 *      tealer
 */

import codeql.teal.ast.AST
import codeql.teal.SSA.SSA
import codeql.teal.cfg.BasicBlocks
import TealerCommon

from Program prog
where
  not txnFieldIsChecked("CloseRemainderTo")
select prog,
  "Contract does not validate txn CloseRemainderTo — account balance can be drained."
