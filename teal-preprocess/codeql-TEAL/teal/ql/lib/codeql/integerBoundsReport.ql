/**
 * @name Integer bounds report
 * @description Reports computed integer bounds [lo, hi] for every opcode output.
 * @id teal/integer-bounds-report
 */

import codeql.teal.ast.AST
import codeql.teal.ast.IntegerBounds

from AstNode n, int lo, int hi, string file
where
  opcodeBounds(n, lo, hi) and
  file = n.getLocation().getFile().getRelativePath()
select
  file,
  n.getLocation().getStartLine() as line,
  n.getLocation().getStartColumn() as col,
  n.toString() as opcode,
  lo,
  hi
