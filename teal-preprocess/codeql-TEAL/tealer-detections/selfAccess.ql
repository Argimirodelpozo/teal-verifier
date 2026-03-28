/**
 * @name Unoptimized Self Access
 * @description Flags patterns where `txn GroupIndex` is loaded and then used
 *              with `gtxns` to access the current transaction's own fields.
 *              These could be simplified to a plain `txn` access.
 * @kind problem
 * @severity recommendation
 * @id teal/self-access
 * @tags optimization
 *      tealer
 */

import codeql.teal.ast.AST
import codeql.teal.SSA.SSA

from GtxnsOpcode gtxns, TxnOpcode groupIdx, SSAVar idxVar
where
  groupIdx.getField() = "GroupIndex" and
  idxVar = groupIdx.getAnOutputVar() and
  gtxns.getConsumedVars() = idxVar
select gtxns,
  "gtxns " + gtxns.getField() + " at line " + gtxns.getLineNumber().toString() +
    " accesses own transaction via txn GroupIndex — use `txn " + gtxns.getField() +
    "` instead."
