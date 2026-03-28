import codeql.teal.ast.AST

/** The `log` opcode: write bytes to transaction log. */
class LogOpcode extends AstNode instanceof TOpcode_log {
    override int getStackDelta() { result = -1 }
}
