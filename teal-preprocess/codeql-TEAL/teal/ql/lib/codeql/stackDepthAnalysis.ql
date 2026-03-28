/**
 * @name Stack depth analysis
 * @description Detects stack overflow, underflow, and inconsistent stack depth in TEAL programs.
 * @kind problem
 * @id teal/stack-depth
 * @problem.severity warning
 */

import codeql.teal.ast.AST
import codeql.teal.ast.StackDepth

from AstNode n, string msg
where
  exists(int maxDepth |
    stackOverflow(n, maxDepth) and
    msg =
      "Stack overflow: depth " + maxDepth.toString() + " exceeds AVM limit of 1000"
  )
  or
  exists(int minDepth |
    stackUnderflow(n, minDepth) and
    msg =
      "Stack underflow: depth " + minDepth.toString() + " but opcode consumes " +
        n.getNumberOfConsumedArgs().toString()
  )
  or
  exists(int minDepth, int maxDepth |
    inconsistentStackDepth(n, minDepth, maxDepth) and
    msg =
      "Inconsistent stack depth: paths disagree (" + minDepth.toString() + " vs " +
        maxDepth.toString() + ")"
  )
select n, msg
