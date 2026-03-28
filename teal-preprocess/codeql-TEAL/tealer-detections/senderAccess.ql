/**
 * @name Unoptimized Sender Access
 * @description Flags patterns where `gtxn <i> Sender` is used to access the
 *              sender of the current transaction (group index matches self),
 *              when `txn Sender` would be more efficient.
 * @kind problem
 * @severity recommendation
 * @id teal/sender-access
 * @tags optimization
 *      tealer
 */

import codeql.teal.ast.AST
import codeql.teal.ast.internal.TreeSitter

from GtxnOpcode gtxn
where
  gtxn.getField() = "Sender" and
  toTreeSitter(gtxn).(Teal::GtxnOpcode).getChild().getValue().toInt() = 0
select gtxn,
  "gtxn 0 Sender at line " + gtxn.getLineNumber().toString() +
    " accesses the sender of the first transaction — use `txn Sender` if this is self."
