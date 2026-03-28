import codeql.teal.ast.AST

/** The `concat` opcode: concatenate two byte arrays. */
class ConcatOpcode extends AstNode instanceof TOpcode_concat {
    override int getStackDelta() { result = -1 }
}

/** The `substring` opcode: extract substring by immediate start and end. */
class SubstringOpcode extends AstNode instanceof TOpcode_substring {
    override int getStackDelta() { result = 0 }
}

/** The `substring3` opcode: extract substring by stack start and end. */
class Substring3Opcode extends AstNode instanceof TOpcode_substring3 {
    override int getStackDelta() { result = -2 }
}

/** The `extract` opcode: extract bytes by immediate start and length. */
class ExtractOpcode extends AstNode instanceof TOpcode_extract {
    override int getStackDelta() { result = 0 }
}

/** The `extract3` opcode: extract bytes by stack start and length. */
class Extract3Opcode extends AstNode instanceof TOpcode_extract3 {
    override int getStackDelta() { result = -2 }
}

/** The `extract_uint16` opcode: extract 16-bit unsigned integer. */
class ExtractUint16Opcode extends AstNode instanceof TOpcode_extract_uint16 {
    override int getStackDelta() { result = -1 }
}

/** The `extract_uint32` opcode: extract 32-bit unsigned integer. */
class ExtractUint32Opcode extends AstNode instanceof TOpcode_extract_uint32 {
    override int getStackDelta() { result = -1 }
}

/** The `extract_uint64` opcode: extract 64-bit unsigned integer. */
class ExtractUint64Opcode extends AstNode instanceof TOpcode_extract_uint64 {
    override int getStackDelta() { result = -1 }
}

/** The `replace2` opcode: replace bytes at immediate offset. */
class Replace2Opcode extends AstNode instanceof TOpcode_replace2 {
    override int getStackDelta() { result = -1 }
}

/** The `replace3` opcode: replace bytes at stack offset. */
class Replace3Opcode extends AstNode instanceof TOpcode_replace3 {
    override int getStackDelta() { result = -2 }
}

/** The `len` opcode: get length of byte array. */
class LenOpcode extends AstNode instanceof TOpcode_len {
    override int getStackDelta() { result = 0 }
}

/** The `bitlen` opcode: get bit length of value. */
class BitlenOpcode extends AstNode instanceof TOpcode_bitlen {
    override int getStackDelta() { result = 0 }
}

/** The `getbit` opcode: get bit at index. */
class GetbitOpcode extends AstNode instanceof TOpcode_getbit {
    override int getStackDelta() { result = -1 }
}

/** The `setbit` opcode: set bit at index. */
class SetbitOpcode extends AstNode instanceof TOpcode_setbit {
    override int getStackDelta() { result = -2 }
}

/** The `getbyte` opcode: get byte at index. */
class GetbyteOpcode extends AstNode instanceof TOpcode_getbyte {
    override int getStackDelta() { result = -1 }
}

/** The `setbyte` opcode: set byte at index. */
class SetbyteOpcode extends AstNode instanceof TOpcode_setbyte {
    override int getStackDelta() { result = -2 }
}

/** The `itob` opcode: convert integer to big-endian bytes. */
class ItobOpcode extends AstNode instanceof TOpcode_itob {
    override int getStackDelta() { result = 0 }
}

/** The `btoi` opcode: convert big-endian bytes to integer. */
class BtoiOpcode extends AstNode instanceof TOpcode_btoi {
    override int getStackDelta() { result = 0 }
}

/** The `base64_decode` opcode: decode base64 encoded bytes. */
class Base64DecodeOpcode extends AstNode instanceof TOpcode_base64_decode {
    override int getStackDelta() { result = 0 }
}

/** The `json_ref` opcode: extract value from JSON. */
class JsonRefOpcode extends AstNode instanceof TOpcode_json_ref {
    override int getStackDelta() { result = -1 }
}
