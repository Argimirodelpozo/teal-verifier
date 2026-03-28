/**
 * Byte array length bounds analysis for TEAL stack variables.
 *
 * Computes [lo, hi] length bounds for every byte-array-producing opcode
 * output by propagating bounds from producers to consumers through the
 * SSA chain.
 *
 * Bounds are [lo, hi] pairs where lo >= 0 and hi >= lo.
 * AVM maximum byte array length is 4096.
 * Sentinel value -1 for hi means "unknown length" (up to 4096).
 * Exact lengths: [v, v] (lo = hi).
 */

private import codeql.teal.ast.AST
private import codeql.teal.SSA.SSA
private import codeql.teal.ast.IntegerBounds
private import codeql.teal.ast.internal.TreeSitter

/**
 * Clamp a computed upper bound: if it exceeds 4096 or is negative
 * (due to overflow), return -1 (unknown).
 */
bindingset[v]
private int clampHi(int v) {
  if v < 0 then result = -1
  else if v > 4096 then result = -1
  else result = v
}

/**
 * Add two upper bounds, respecting the -1 sentinel.
 * If either is -1 (unknown), the result is -1.
 */
bindingset[a, b]
private int addHi(int a, int b) {
  if a = -1 or b = -1 then result = -1
  else result = clampHi(a + b)
}

/**
 * Return the maximum of two upper bounds, respecting -1 sentinel.
 */
bindingset[a, b]
private int maxHi(int a, int b) {
  if a = -1 or b = -1 then result = -1
  else if a >= b then result = a
  else result = b
}

/**
 * Return the minimum of two upper bounds, respecting -1 sentinel.
 * min(-1, x) = x, min(x, -1) = x.
 */
bindingset[a, b]
private int minHi(int a, int b) {
  if a = -1 then result = b
  else if b = -1 then result = a
  else if a <= b then result = a
  else result = b
}

/**
 * Compute byte length from a hex string like "0xABCD" → 2.
 * Empty "0x" → 0.
 */
bindingset[hexValue]
private int hexByteLength(string hexValue) {
  if hexValue.matches("0x%")
  then result = (hexValue.length() - 2) / 2
  else result = -1
}

/**
 * Holds if `field` is a 32-byte address field on a transaction opcode.
 */
private predicate isAddressFieldName(string field) {
  field = "Sender" or
  field = "Receiver" or
  field = "CloseRemainderTo" or
  field = "AssetSender" or
  field = "AssetReceiver" or
  field = "AssetCloseTo" or
  field = "RekeyTo"
}

/**
 * Holds if `field` is a 32-byte address field on a global opcode.
 */
private predicate isGlobalAddressFieldName(string field) {
  field = "ZeroAddress" or
  field = "CreatorAddress" or
  field = "CurrentApplicationAddress"
}

// ---------------------------------------------------------------------------
// Seed bounds: base cases derived from opcode semantics alone (no inputs)
// ---------------------------------------------------------------------------

/**
 * Holds if opcode `n` has known byte array length bounds [lo, hi] purely
 * from its own semantics (no input bounds needed).
 */
predicate seedBytesBounds(AstNode n, int lo, int hi) {
  // pushbytes 0xABCD → exact length from hex literal
  exists(string hexValue |
    hexValue = toTreeSitter(n).(Teal::PushbytesOpcode).getValue().toString() |
    lo = hexByteLength(hexValue) and hi = lo
  )
  or
  // bytec → exact length from bytecblock entry
  exists(string hexValue | hexValue = n.(BytecOpcode).getValue() |
    lo = hexByteLength(hexValue) and hi = lo
  )
  or
  exists(string hexValue | hexValue = n.(Bytec0Opcode).getValue() |
    lo = hexByteLength(hexValue) and hi = lo
  )
  or
  exists(string hexValue | hexValue = n.(Bytec1Opcode).getValue() |
    lo = hexByteLength(hexValue) and hi = lo
  )
  or
  exists(string hexValue | hexValue = n.(Bytec2Opcode).getValue() |
    lo = hexByteLength(hexValue) and hi = lo
  )
  or
  exists(string hexValue | hexValue = n.(Bytec3Opcode).getValue() |
    lo = hexByteLength(hexValue) and hi = lo
  )
  or
  // Hash opcodes: always 32-byte output
  (n instanceof Sha256Opcode or
   n instanceof Sha512_256Opcode or
   n instanceof Keccak256Opcode or
   n instanceof Sha3_256Opcode or
   n instanceof MimcOpcode) and
  lo = 32 and hi = 32
  or
  // itob: integer to big-endian bytes, always 8 bytes
  n instanceof ItobOpcode and lo = 8 and hi = 8
  or
  // Txn address fields: 32 bytes
  exists(TxnOpcode txn | txn = n |
    txn.isBytesField() and
    isAddressFieldName(txn.getField()) and
    lo = 32 and hi = 32
  )
  or
  // Txn other bytes fields: unknown length
  exists(TxnOpcode txn | txn = n |
    txn.isBytesField() and
    not isAddressFieldName(txn.getField()) and
    lo = 0 and hi = -1
  )
  or
  // Txna Accounts: 32-byte addresses
  exists(TxnaOpcode txna | txna = n |
    txna.isAddressField() and
    lo = 32 and hi = 32
  )
  or
  // Txna other bytes fields: unknown length
  exists(TxnaOpcode txna | txna = n |
    txna.isBytesField() and
    not txna.isAddressField() and
    lo = 0 and hi = -1
  )
  or
  // Gtxn address fields: 32 bytes
  exists(GtxnOpcode gtxn | gtxn = n |
    gtxn.isBytesField() and
    isAddressFieldName(gtxn.getField()) and
    lo = 32 and hi = 32
  )
  or
  // Gtxn other bytes fields: unknown length
  exists(GtxnOpcode gtxn | gtxn = n |
    gtxn.isBytesField() and
    not isAddressFieldName(gtxn.getField()) and
    lo = 0 and hi = -1
  )
  or
  // Gtxns address fields: 32 bytes
  exists(GtxnsOpcode gtxns | gtxns = n |
    gtxns.isBytesField() and
    isAddressFieldName(gtxns.getField()) and
    lo = 32 and hi = 32
  )
  or
  // Gtxns other bytes fields: unknown length
  exists(GtxnsOpcode gtxns | gtxns = n |
    gtxns.isBytesField() and
    not isAddressFieldName(gtxns.getField()) and
    lo = 0 and hi = -1
  )
  or
  // Global address fields: 32 bytes
  exists(GlobalOpcode g | g = n |
    g.isBytesField() and
    isGlobalAddressFieldName(g.getField()) and
    lo = 32 and hi = 32
  )
  or
  // Global other bytes fields: unknown length
  exists(GlobalOpcode g | g = n |
    g.isBytesField() and
    not isGlobalAddressFieldName(g.getField()) and
    lo = 0 and hi = -1
  )
  or
  // App state get: could return bytes, unknown length
  (n instanceof AppGlobalGetOpcode or
   n instanceof AppLocalGetOpcode or
   n instanceof AppGlobalGetExOpcode or
   n instanceof AppLocalGetExOpcode) and
  lo = 0 and hi = -1
  or
  // Box get/extract: unknown length
  (n instanceof BoxGetOpcode or
   n instanceof BoxExtractOpcode) and
  lo = 0 and hi = -1
  or
  // Byte arithmetic: unknown length
  (n instanceof BaddOpcode or
   n instanceof BsubOpcode or
   n instanceof BmulOpcode or
   n instanceof BdivOpcode or
   n instanceof BmodOpcode or
   n instanceof BsqrtOpcode) and
  lo = 0 and hi = -1
  or
  // Bitwise byte ops: unknown length
  (n instanceof BorOpcode or
   n instanceof BandOpcode or
   n instanceof BxorOpcode or
   n instanceof BnotOpcode) and
  lo = 0 and hi = -1
  or
  // EC ops producing byte output: unknown length
  (n instanceof EcAddOpcode or
   n instanceof EcMulOpcode or
   n instanceof EcMapToOpcode or
   n instanceof EcMultiScalarMulOpcode) and
  lo = 0 and hi = -1
  or
  // Crypto ops producing byte output
  (n instanceof EcdsaPkDecompressOpcode or
   n instanceof EcdsaPkRecoverOpcode or
   n instanceof VrfVerifyOpcode) and
  lo = 0 and hi = -1
  or
  // Base64 decode: unknown length
  n instanceof Base64DecodeOpcode and lo = 0 and hi = -1
  or
  // Args: unknown length
  (n instanceof ArgsOpcode or
   n instanceof ArgOpcode or
   n instanceof Arg0Opcode or
   n instanceof Arg1Opcode or
   n instanceof Arg2Opcode or
   n instanceof Arg3Opcode) and
  lo = 0 and hi = -1
  or
  // JSON ref: unknown length
  n instanceof JsonRefOpcode and lo = 0 and hi = -1
}

// ---------------------------------------------------------------------------
// Value tracking for known byte array constants
// ---------------------------------------------------------------------------

/**
 * Holds when the byte array at opcode `n` is the known constant `value`
 * (hex string like "0xABCD").
 */
predicate seedBytesValue(AstNode n, string value) {
  value = toTreeSitter(n).(Teal::PushbytesOpcode).getValue().toString()
  or
  value = n.(BytecOpcode).getValue()
  or
  value = n.(Bytec0Opcode).getValue()
  or
  value = n.(Bytec1Opcode).getValue()
  or
  value = n.(Bytec2Opcode).getValue()
  or
  value = n.(Bytec3Opcode).getValue()
}

/**
 * Holds if SSA variable `v` has known byte array constant `value`.
 */
predicate varBytesValue(SSAVar v, string value) {
  opcodeBytesValue(v.getDeclarationNode(), value)
}

/**
 * Holds if the `inputOrd`-th input to opcode `n` has known byte array
 * constant `value`.
 */
private predicate inputBytesValue(AstNode n, int inputOrd, string value) {
  exists(Definition def |
    def = n.getStackInputByOrder(inputOrd) |
    exists(SSAVar sv |
      sv = getGenerator(def) |
      varBytesValue(sv, value)
    )
  )
}

/**
 * Holds when opcode `n` produces a byte array with known constant `value`,
 * either from a seed constant or propagated through identity operations.
 */
predicate opcodeBytesValue(AstNode n, string value) {
  seedBytesValue(n, value)
  or
  // dup: same value as input
  n instanceof DupOpcode and
  n.inputIsPredictable() and
  inputBytesValue(n, 1, value)
  or
  // select: either branch value
  n instanceof SelectOpcode and
  n.inputIsPredictable() and
  (inputBytesValue(n, 2, value) or inputBytesValue(n, 3, value))
}

// ---------------------------------------------------------------------------
// Variable bounds: bounds on SSA variables based on their declaring opcode
// ---------------------------------------------------------------------------

/**
 * Holds if SSA variable `v` has byte array length bounds [lo, hi].
 * Derived from the opcode that defines the variable.
 */
predicate varBytesBounds(SSAVar v, int lo, int hi) {
  opcodeBytesBounds(v.getDeclarationNode(), lo, hi)
}

// ---------------------------------------------------------------------------
// Input bounds: byte length bounds flowing into an opcode's input position
// ---------------------------------------------------------------------------

/**
 * Holds if the `inputOrd`-th input to opcode `n` has byte array length
 * bounds [lo, hi]. Derived from the SSA variable that feeds this input.
 */
predicate inputBytesBounds(AstNode n, int inputOrd, int lo, int hi) {
  exists(Definition def |
    def = n.getStackInputByOrder(inputOrd) |
    exists(SSAVar sv |
      sv = getGenerator(def) |
      varBytesBounds(sv, lo, hi)
    )
  )
}

/**
 * Integer bounds on an input position, delegating to IntegerBounds.
 * Used for cross-analysis (e.g., bzero length, extract3 length).
 */
private predicate inputIntBounds(AstNode n, int inputOrd, int lo, int hi) {
  inputBounds(n, inputOrd, lo, hi)
}

// ---------------------------------------------------------------------------
// Transfer bounds: computed from input bounds (byte operations, etc.)
// ---------------------------------------------------------------------------

/**
 * Holds if opcode `n` has byte array length bounds [lo, hi] computed
 * from its input bounds. Only applies when `inputIsPredictable()` holds.
 */
predicate transferBytesBounds(AstNode n, int lo, int hi) {
  // concat: [lo1+lo2, clamp(hi1+hi2)]
  n instanceof ConcatOpcode and
  n.inputIsPredictable() and
  exists(int lo1, int hi1, int lo2, int hi2 |
    inputBytesBounds(n, 1, lo1, hi1) and
    inputBytesBounds(n, 2, lo2, hi2) |
    lo = lo1 + lo2 and
    hi = addHi(hi1, hi2)
  )
  or
  // substring s e (immediate): exact [e-s, e-s]
  n instanceof SubstringOpcode and
  exists(int s, int e |
    s = toTreeSitter(n).(Teal::DoubleNumericArgumentOpcode).getValue1().toString().toInt() and
    e = toTreeSitter(n).(Teal::DoubleNumericArgumentOpcode).getValue2().toString().toInt() and
    e >= s |
    lo = e - s and hi = lo
  )
  or
  // substring3: conservative [0, -1] (would need integer bounds on start/end)
  n instanceof Substring3Opcode and
  lo = 0 and hi = -1
  or
  // extract s l (immediate, l > 0): exact [l, l]
  // extract s 0 (l=0 means "rest from position s"): [0, hi_input]
  n instanceof ExtractOpcode and
  exists(int l |
    l = toTreeSitter(n).(Teal::DoubleNumericArgumentOpcode).getValue2().toString().toInt() |
    if l > 0 then (
      lo = l and hi = l
    ) else (
      n.inputIsPredictable() and
      exists(int hiInput |
        inputBytesBounds(n, 1, _, hiInput) |
        lo = 0 and hi = hiInput
      )
    )
  )
  or
  // extract3: use IntegerBounds on length (top of stack, inputOrd=1)
  n instanceof Extract3Opcode and
  n.inputIsPredictable() and
  exists(int loLen, int hiLen |
    inputIntBounds(n, 1, loLen, hiLen) |
    lo = loLen and
    hi = clampHi(hiLen)
  )
  or
  // replace2: same length as target byte array (inputOrd=2)
  n instanceof Replace2Opcode and
  n.inputIsPredictable() and
  inputBytesBounds(n, 2, lo, hi)
  or
  // replace3: same length as target byte array (inputOrd=3)
  n instanceof Replace3Opcode and
  n.inputIsPredictable() and
  inputBytesBounds(n, 3, lo, hi)
  or
  // setbit: same length as target (inputOrd=3)
  n instanceof SetbitOpcode and
  n.inputIsPredictable() and
  inputBytesBounds(n, 3, lo, hi)
  or
  // setbyte: same length as target (inputOrd=3)
  n instanceof SetbyteOpcode and
  n.inputIsPredictable() and
  inputBytesBounds(n, 3, lo, hi)
  or
  // bzero: length = integer on stack → use IntegerBounds (inputOrd=1)
  n instanceof BzeroOpcode and
  n.inputIsPredictable() and
  exists(int loInt, int hiInt |
    inputIntBounds(n, 1, loInt, hiInt) |
    lo = loInt and
    hi = clampHi(hiInt)
  )
  or
  // dup: same bounds as input
  n instanceof DupOpcode and
  n.inputIsPredictable() and
  inputBytesBounds(n, 1, lo, hi)
  or
  // select: union of two branches [min(lo_a, lo_b), max(hi_a, hi_b)]
  // Input order: 1=cond (top), 2=A (second), 3=B (deepest)
  n instanceof SelectOpcode and
  n.inputIsPredictable() and
  exists(int loA, int hiA, int loB, int hiB |
    inputBytesBounds(n, 2, loA, hiA) and
    inputBytesBounds(n, 3, loB, hiB) |
    (if loA <= loB then lo = loA else lo = loB) and
    hi = maxHi(hiA, hiB)
  )
}

// ---------------------------------------------------------------------------
// Combined opcode bounds: seed OR transfer (union, no negation)
// ---------------------------------------------------------------------------

/**
 * Holds if opcode `n` has byte array length bounds [lo, hi].
 * Uses seed bounds when no transfer bounds are available, transfer bounds
 * when they exist, or both when both apply.
 */
predicate opcodeBytesBounds(AstNode n, int lo, int hi) {
  seedBytesBounds(n, lo, hi)
  or
  transferBytesBounds(n, lo, hi)
}

/**
 * Format the upper bound for display: -1 becomes "MAX_BYTES(4096)".
 */
bindingset[hi]
string formatBytesHi(int hi) {
  if hi = -1 then result = "MAX_BYTES(4096)"
  else result = hi.toString()
}
