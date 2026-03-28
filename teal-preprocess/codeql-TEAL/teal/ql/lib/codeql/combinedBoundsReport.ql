/**
 * @name Combined bounds report
 * @description Reports both integer and byte array bounds in a single union query with a kind discriminator.
 * @id teal/combined-bounds-report
 */

import codeql.teal.ast.AST
import codeql.teal.ast.IntegerBounds
import codeql.teal.ast.BytearrayBounds

from AstNode n, string file, int line, int col, string opcode, string kind, int lo, int hi, string value
where
  file = n.getLocation().getFile().getRelativePath() and
  line = n.getLocation().getStartLine() and
  col = n.getLocation().getStartColumn() and
  opcode = n.toString() and
  (
    kind = "int" and
    opcodeBounds(n, lo, hi) and
    (if lo = hi then value = lo.toString() else value = "")
    or
    kind = "bytes" and
    opcodeBytesBounds(n, lo, hi) and
    (if opcodeBytesValue(n, value) then any() else value = "")
  )
select file, line, col, opcode, kind, lo, hi, value
