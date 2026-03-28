/**
 * @name Print AST
 * @description Produces a representation of a file's Abstract Syntax Tree.
 *              This query is used by the VS Code extension.
 * @id teal/print-ast
 * @kind graph
 * @tags ide-contextual-queries/print-ast
 */

import codeql.Locations

private import codeql.teal.ideContextual.IDEContextual
import codeql.teal.ideContextual.printAst
private import codeql.teal.ast.internal.TreeSitter::Teal

/**
 * The source file to generate an AST from.
 */
external string selectedSourceFile();

/**
 * A configuration that only prints nodes in the selected source file.
 */
class Cfg extends PrintAstConfiguration {
    override predicate shouldPrintNode(AstNode n) {
      super.shouldPrintNode(n) and
      n.getLocation().getFile() = getFileBySourceArchiveName(selectedSourceFile())
    }
  }