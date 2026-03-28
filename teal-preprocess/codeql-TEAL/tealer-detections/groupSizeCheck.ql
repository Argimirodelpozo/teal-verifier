/**
 * @name Missing GroupSize Validation
 * @description Detects contracts that use gtxn with absolute group indices
 *              without validating global GroupSize. An attacker can add extra
 *              transactions to the group if GroupSize is unchecked.
 * @kind problem
 * @severity high
 * @id teal/group-size-check
 * @tags security
 *      tealer
 */

import codeql.teal.ast.AST
import codeql.teal.SSA.SSA
import codeql.teal.cfg.BasicBlocks
import TealerCommon

from GtxnOpcode gtxn, Program prog
where
  gtxn.getProgram() = prog and
  not hasGroupSizeCheck()
select gtxn,
  "gtxn access at line " + gtxn.getLineNumber().toString() +
    " uses an absolute group index without validating global GroupSize."
