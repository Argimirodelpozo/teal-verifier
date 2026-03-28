import codeql.teal.ast.AST

/** The `box_create` opcode: create a box. */
class BoxCreateOpcode extends AstNode instanceof TOpcode_box_create {
    override int getStackDelta() { result = -1 }
}

/** The `box_extract` opcode: extract bytes from a box. */
class BoxExtractOpcode extends AstNode instanceof TOpcode_box_extract {
    override int getStackDelta() { result = -2 }
}

/** The `box_replace` opcode: replace bytes in a box. */
class BoxReplaceOpcode extends AstNode instanceof TOpcode_box_replace {
    override int getStackDelta() { result = -3 }
}

/** The `box_del` opcode: delete a box. */
class BoxDelOpcode extends AstNode instanceof TOpcode_box_del {
    override int getStackDelta() { result = 0 }
}

/** The `box_len` opcode: get box length. */
class BoxLenOpcode extends AstNode instanceof TOpcode_box_len {
    override int getStackDelta() { result = 1 }
}

/** The `box_get` opcode: get entire box contents. */
class BoxGetOpcode extends AstNode instanceof TOpcode_box_get {
    override int getStackDelta() { result = 1 }
}

/** The `box_put` opcode: replace entire box contents. */
class BoxPutOpcode extends AstNode instanceof TOpcode_box_put {
    override int getStackDelta() { result = -2 }
}

/** The `box_splice` opcode: splice bytes into a box. */
class BoxSpliceOpcode extends AstNode instanceof TOpcode_box_splice {
    override int getStackDelta() { result = -4 }
}

/** The `box_resize` opcode: resize a box. */
class BoxResizeOpcode extends AstNode instanceof TOpcode_box_resize {
    override int getStackDelta() { result = -2 }
}
