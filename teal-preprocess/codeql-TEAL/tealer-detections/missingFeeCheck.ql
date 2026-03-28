/**
 * @name Missing Fee Validation
 * @description Detects contracts (especially LogicSigs) that do not validate
 *              txn Fee on all approval paths. Without fee validation, an
 *              attacker can set an excessively high fee to drain funds.
 *              This is a CFG-aware improvement over the original token-based check.
 * @kind problem
 * @severity high
 * @id teal/missing-fee-check
 * @tags security
 *      tealer
 */

import codeql.teal.ast.AST
import codeql.teal.SSA.SSA
import codeql.teal.cfg.BasicBlocks
import TealerCommon

from Program prog
where
  not hasFeeCheck()
select prog,
  "Contract does not validate txn Fee — an attacker can set an excessively high fee to drain the account."
