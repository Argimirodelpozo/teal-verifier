private import codeql.Locations
private import codeql.teal.ast.internal.TreeSitter::Teal

class PrintAstConfiguration extends string {
    PrintAstConfiguration() { this = "PrintAstConfiguration" }
  
    /**
     * Holds if the given node should be printed.
     */
    predicate shouldPrintNode(AstNode n) { 
        not n instanceof Comment
        and (
          not n instanceof Token
          or exists(AstNode n2| n.getParent() = n2)
        )
    }
  }

private predicate shouldPrintNode(AstNode n) {
any(PrintAstConfiguration config).shouldPrintNode(n)
}

/**
 * A node in the output tree.
 */
class PrintAstNode extends AstNode {  
    /**
     * Gets the child node with name `edgeName`. Typically this is the name of the
     * predicate used to access the child.
     */
    PrintAstNode getChild(string edgeName) { exists(int id| id.toString() = edgeName | result = this.getAFieldOrChild(id)) }
  
    /** Get the Location of this AST node */
    Location getLocation() { result = this.(AstNode).getLocation() }
  
    final PrintAstNode getAFieldOrChild(int id) {
      exists(PrintAstNode n| n.(AstNode).getParent() = this.(AstNode) | n.getParentIndex() = id and result = n)
    }

    /** Gets a child of this node. */
    final PrintAstNode getAChild() { result = this.getChild(_) }
  
    /** Gets the parent of this node, if any. */
    final PrintAstNode getParent() { result.getAChild() = this }
  
    /** Gets a value used to order this node amongst its siblings. */
    int getOrder() {
      this =
        rank[result](AstNode p, Location l, File f |
          l = p.getLocation() and
          f = l.getFile()
        |
          p
          order by
            f.getBaseName(), f.getAbsolutePath(), l.getStartLine(), l.getStartColumn(),
            l.getEndLine(), l.getEndColumn()
        )
    }
  
    /**
     * Gets the value of the property of this node, where the name of the property
     * is `key`.
     */
    final string getProperty(string key) {
      key = "semmle.label" and
      result = this.toString()
      or
      key = "semmle.order" and result = this.getOrder().toString()
    }
}

/**
 * Holds if `node` belongs to the output tree, and its property `key` has the
 * given `value`.
 */
query predicate nodes(PrintAstNode node, string key, string value) {
    value = node.getProperty(key) and shouldPrintNode(node)
}

/**
 * Holds if `target` is a child of `source` in the AST, and property `key` of
 * the edge has the given `value`.
 */
query predicate edges(PrintAstNode source, PrintAstNode target, string key, string value) {
    shouldPrintNode(source) and
    shouldPrintNode(target) and
    target = source.getAFieldOrChild(_) and
    (
        key = "semmle.label" and
        value = strictconcat(int id | source.getAFieldOrChild(id) = target | id.toString(), "/")
        or
        key = "semmle.order" and
        value = target.getProperty("semmle.order")
    )
}

/**
 * Holds if property `key` of the graph has the given `value`.
 */
query predicate graphProperties(string key, string value) {
    key = "semmle.graphKind" and value = "tree"
}