/**
 * @name Missing AssetCloseTo Validation
 * @description Detects contracts (especially LogicSigs) that do not validate
 *              the AssetCloseTo transaction field. Without this check,
 *              an attacker can transfer all of an ASA out of the account.
 * @kind problem
 * @severity high
 * @id teal/can-close-asset
 * @tags security
 *      tealer
 */

import codeql.teal.ast.AST
import codeql.teal.SSA.SSA
import codeql.teal.cfg.BasicBlocks
import TealerCommon

from Program prog
where
  not txnFieldIsChecked("AssetCloseTo")
select prog,
  "Contract does not validate txn AssetCloseTo — assets can be drained from the account."
