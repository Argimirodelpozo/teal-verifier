/**
 * @name Unoptimized Gtxn — Constant Group Index
 * @description Flags gtxn operations that use a constant group index of 0
 *              in a context where the transaction is known to be at index 0.
 *              These could be replaced with the more efficient `txn` opcode.
 * @kind problem
 * @severity recommendation
 * @id teal/constant-gtxn
 * @tags optimization
 *      tealer
 */

import codeql.teal.ast.AST
import codeql.teal.ast.internal.TreeSitter

from GtxnOpcode gtxn
where
  toTreeSitter(gtxn).(Teal::GtxnOpcode).getChild().getValue().toInt() = 0
select gtxn,
  "gtxn at line " + gtxn.getLineNumber().toString() +
    " uses constant index 0 and could be replaced with `txn " + gtxn.getField() + "`."
