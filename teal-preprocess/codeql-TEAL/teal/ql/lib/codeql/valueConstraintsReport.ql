/**
 * @name Value constraints report
 * @description Reports branch-sensitive value constraints for user inputs at each opcode.
 * @id teal/value-constraints-report
 */

import codeql.teal.ast.AST
import codeql.teal.ast.ValueConstraints

from AstNode n, string inputKindStr, string constValue, string file
where
  inputBoundAtPoint(n, inputKindStr, constValue) and
  file = n.getLocation().getFile().getRelativePath()
select
  file,
  n.getLocation().getStartLine() as line,
  n.getLocation().getStartColumn() as col,
  n.toString() as opcode,
  inputKindStr as inputKind,
  constValue as constrainedValue
