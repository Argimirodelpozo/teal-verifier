/**
 * @name CFG Edges
 * @description Outputs all CFG edges for conversion to DOT format.
 * @id tealql/cfg-edges
 * @kind problem
 */

import codeql.teal.cfg.CFG
import codeql.teal.cfg.CFG::CfgImpl
import codeql.teal.cfg.CFG::CfgScope
import codeql.teal.cfg.Completion::Completion
import codeql.teal.ast.AST

string astNodeLabel(AstCfgNode n) {
  result = n.getAstNode().getAPrimaryQlClass() + ": " + n.getAstNode().toString()
}

from AstCfgNode pred, AstCfgNode succ, SuccessorType t
where succ = pred.getASuccessor(t)
select pred,
  "EDGE|" + pred.getLocation().getStartLine() + ":" + pred.getLocation().getStartColumn() + "|" +
    astNodeLabel(pred) + "|" + succ.getLocation().getStartLine() + ":" +
    succ.getLocation().getStartColumn() + "|" + astNodeLabel(succ) + "|" + t.toString()
