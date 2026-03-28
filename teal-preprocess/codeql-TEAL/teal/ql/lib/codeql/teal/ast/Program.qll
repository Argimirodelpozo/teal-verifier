private import codeql.Locations
private import codeql.teal.ast.internal.TreeSitter
private import codeql.teal.cfg.BasicBlocks
private import codeql.teal.SSA.SSA
private import codeql.teal.cfg.Completion::Completion
private import codeql.teal.ast.IntegerConstants
private import codeql.teal.ast.InnerTransactions
private import codeql.teal.ast.Jumps

class Program extends AstNode instanceof TSource{

    // This function excludes starting pragmas, comments and stuff that is not an AstNode but is still
    // a child of the Teal::Source
    AstNode getChild(int i){
        exists(int k |
            k = min(int h | 
                    exists(AstNode n | toTreeSitter(n) = toTreeSitter(this).(Teal::Source).getChild(h))
             ) | toTreeSitter(result) = toTreeSitter(this).(Teal::Source).getChild(k+i)
        )
    }

    override AstNode getParent(){none()}
}