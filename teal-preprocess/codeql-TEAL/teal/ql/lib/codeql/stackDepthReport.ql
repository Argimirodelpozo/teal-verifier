/**
 * @name Stack depth report
 * @description Reports all possible stack depths at every program line.
 * @id teal/stack-depth-report
 */

import codeql.teal.ast.AST
import codeql.teal.ast.StackDepth

from AstNode n, int depthBefore, string file
where
  nodeStackDepth(n, depthBefore) and
  file = n.getLocation().getFile().getRelativePath()
select
  file,
  n.getLocation().getStartLine() as line,
  n.getLocation().getStartColumn() as col,
  n.toString() as opcode,
  depthBefore as depth_before,
  n.getStackDelta() as delta
