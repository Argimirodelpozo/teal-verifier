/**
 * @name Byte array length bounds report
 * @description Reports computed byte array length bounds [lo, hi] for every opcode output.
 * @id teal/bytearray-bounds-report
 */

import codeql.teal.ast.AST
import codeql.teal.ast.BytearrayBounds

from AstNode n, int lo, int hi, string file, string value
where
  opcodeBytesBounds(n, lo, hi) and
  file = n.getLocation().getFile().getRelativePath() and
  (opcodeBytesValue(n, value) or not opcodeBytesValue(n, _) and value = "")
select
  file,
  n.getLocation().getStartLine() as line,
  n.getLocation().getStartColumn() as col,
  n.toString() as opcode,
  lo,
  hi,
  value
