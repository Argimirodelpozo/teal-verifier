/**
 * @name Rekeyable Logic Signature
 * @description Detects contracts that do not validate the RekeyTo transaction
 *              field. Without this check, an attacker can rekey the account
 *              to themselves, gaining full control.
 * @kind problem
 * @severity high
 * @id teal/rekey-to
 * @tags security
 *      tealer
 */

import codeql.teal.ast.AST
import codeql.teal.SSA.SSA
import codeql.teal.cfg.BasicBlocks
import TealerCommon

from Program prog
where
  not txnFieldIsChecked("RekeyTo")
select prog,
  "Contract does not validate txn RekeyTo — the account can be rekeyed to an attacker's address."
