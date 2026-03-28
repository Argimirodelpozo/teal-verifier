/**
 * @name Stack depth debug
 * @description Shows all possible stack depths at each node.
 * @id teal/stack-depth-debug
 */

import codeql.teal.ast.AST
import codeql.teal.ast.StackDepth

from AstNode n, int depthBefore
where nodeStackDepth(n, depthBefore)
select
  n.getLocation().getStartLine() as line,
  n.toString() as opcode,
  depthBefore as depth_before,
  n.getStackDelta() as delta
order by line
