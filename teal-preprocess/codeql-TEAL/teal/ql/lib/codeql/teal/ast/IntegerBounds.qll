/**
 * Integer bounds analysis for TEAL stack variables.
 *
 * Computes [lo, hi] integer bounds for every opcode output by propagating
 * bounds from producers to consumers through the SSA chain.
 *
 * Bounds are [lo, hi] pairs where lo >= 0 and hi >= lo.
 * TEAL integers are uint64 [0, 2^64-1], but CodeQL int maxes at ~2^31.
 * Sentinel value -1 for hi means "unbounded above" (unknown/too large).
 * Exact values: [v, v] (lo = hi).
 */

private import codeql.teal.ast.AST
private import codeql.teal.SSA.SSA
private import codeql.teal.ast.IntegerConstants

/**
 * Clamp a computed upper bound: if it overflows CodeQL int range or is
 * negative (due to overflow), return -1 (unbounded).
 */
bindingset[v]
private int clampHi(int v) {
  if v < 0 then result = -1 else result = v
}

/**
 * Combine two upper bounds, respecting the -1 sentinel.
 * If either is -1 (unbounded), the result is -1.
 */
bindingset[a, b]
private int addHi(int a, int b) {
  if a = -1 or b = -1 then result = -1
  else result = clampHi(a + b)
}

/**
 * Multiply two upper bounds, respecting the -1 sentinel.
 */
bindingset[a, b]
private int mulHi(int a, int b) {
  if a = -1 or b = -1 then result = -1
  else result = clampHi(a * b)
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
 * Divide lo by hi bound for division lower bound.
 * Returns 0 if divisor upper bound is -1 (unbounded).
 */
bindingset[loNum, hiDen]
private int divLo(int loNum, int hiDen) {
  if hiDen = -1 then result = 0
  else if hiDen = 0 then result = 0
  else result = loNum / hiDen
}

/**
 * Divide hi by lo bound for division upper bound.
 */
bindingset[hiNum, loDen]
private int divHi(int hiNum, int loDen) {
  if hiNum = -1 then result = -1
  else if loDen <= 0 then result = -1
  else result = hiNum / loDen
}

// ---------------------------------------------------------------------------
// Seed bounds: base cases derived from opcode semantics alone (no inputs)
// ---------------------------------------------------------------------------

/**
 * Holds if opcode `n` has known integer output bounds [lo, hi] purely from
 * its own semantics (no input bounds needed).
 */
predicate seedBounds(AstNode n, int lo, int hi) {
  // Integer constants: exact value [v, v]
  lo = n.(IntegerConstant).getValue() and
  hi = lo
  or
  // Comparisons always produce 0 or 1
  n instanceof LogicalComparisonOp and lo = 0 and hi = 1
  or
  // Logical NOT: 0 or 1
  n instanceof NotOpcode and lo = 0 and hi = 1
  or
  // app_opted_in: boolean result
  n instanceof AppOptedInOpcode and lo = 0 and hi = 1
  or
  // getbit: always 0 or 1
  n instanceof GetbitOpcode and lo = 0 and hi = 1
  or
  // Transaction fields with known bounded ranges
  exists(TxnOpcode txn | txn = n |
    lo = min(int v | v = txn.bounded()) and
    hi = max(int v | v = txn.bounded())
  )
  or
  // Global integer fields: non-negative, unbounded above
  exists(GlobalOpcode g | g = n and g.isIntegerField() |
    lo = 0 and hi = -1
  )
  or
  // len, bitlen: non-negative integer
  n instanceof LenOpcode and lo = 0 and hi = -1
  or
  n instanceof BitlenOpcode and lo = 0 and hi = -1
  or
  // btoi: byte array to integer, result is [0, unbounded]
  n instanceof BtoiOpcode and lo = 0 and hi = -1
  or
  // extract_uint16: [0, 65535]
  n instanceof ExtractUint16Opcode and lo = 0 and hi = 65535
  or
  // extract_uint32: [0, 2^31-1] (clamped to CodeQL int range)
  n instanceof ExtractUint32Opcode and lo = 0 and hi = -1
  or
  // extract_uint64: [0, unbounded]
  n instanceof ExtractUint64Opcode and lo = 0 and hi = -1
  or
  // box_create, box_del: boolean results
  n instanceof BoxCreateOpcode and lo = 0 and hi = 1
  or
  n instanceof BoxDelOpcode and lo = 0 and hi = 1
  or
  // ed25519verify, ecdsa_verify, ec_subgroup_check, ec_pairing_check: boolean results
  n instanceof Ed25519verifyOpcode and lo = 0 and hi = 1
  or
  n instanceof Ed25519verifyBareOpcode and lo = 0 and hi = 1
  or
  n instanceof EcdsaVerifyOpcode and lo = 0 and hi = 1
  or
  n instanceof EcSubgroupCheckOpcode and lo = 0 and hi = 1
  or
  n instanceof EcPairingCheckOpcode and lo = 0 and hi = 1
  or
  // getbyte: [0, 255]
  n instanceof GetbyteOpcode and lo = 0 and hi = 255
}

// ---------------------------------------------------------------------------
// Variable bounds: bounds on SSA variables based on their declaring opcode
// ---------------------------------------------------------------------------

/**
 * Holds if SSA variable `v` has bounds [lo, hi].
 * Derived from the opcode that defines the variable.
 */
predicate varBounds(SSAVar v, int lo, int hi) {
  opcodeBounds(v.getDeclarationNode(), lo, hi)
}

// ---------------------------------------------------------------------------
// Input bounds: bounds flowing into an opcode's input position
// ---------------------------------------------------------------------------

/**
 * Holds if the `inputOrd`-th input to opcode `n` has bounds [lo, hi].
 * Bounds are derived from the SSA variable that feeds this input.
 */
predicate inputBounds(AstNode n, int inputOrd, int lo, int hi) {
  exists(Definition def |
    def = n.getStackInputByOrder(inputOrd) |
    exists(SSAVar sv |
      sv = getGenerator(def) |
      varBounds(sv, lo, hi)
    )
  )
}

// ---------------------------------------------------------------------------
// Transfer bounds: computed from input bounds (arithmetic, etc.)
// ---------------------------------------------------------------------------

/**
 * Holds if opcode `n` has output bounds [lo, hi] computed from its input bounds.
 * Only applies when `inputIsPredictable()` holds.
 */
predicate transferBounds(AstNode n, int lo, int hi) {
  // Addition: [lo1+lo2, clamp(hi1+hi2)]
  n instanceof IntegerAddOpcode and
  n.inputIsPredictable() and
  exists(int lo1, int hi1, int lo2, int hi2 |
    inputBounds(n, 1, lo1, hi1) and
    inputBounds(n, 2, lo2, hi2) |
    lo = lo1 + lo2 and
    hi = addHi(hi1, hi2)
  )
  or
  // Subtraction: [max(0, lo1-hi2), hi1] (uint64 underflow panics)
  n instanceof SubOpcode and
  n.inputIsPredictable() and
  exists(int lo1, int hi1, int hi2 |
    inputBounds(n, 1, lo1, hi1) and
    inputBounds(n, 2, _, hi2) |
    (
      if hi2 = -1 then lo = 0
      else if lo1 - hi2 > 0 then lo = lo1 - hi2
      else lo = 0
    ) and
    (
      if hi1 = -1 then hi = -1
      else hi = hi1
    )
  )
  or
  // Multiplication: [lo1*lo2, clamp(hi1*hi2)]
  n instanceof MulOpcode and
  n.inputIsPredictable() and
  exists(int lo1, int hi1, int lo2, int hi2 |
    inputBounds(n, 1, lo1, hi1) and
    inputBounds(n, 2, lo2, hi2) |
    lo = lo1 * lo2 and
    hi = mulHi(hi1, hi2)
  )
  or
  // Division: if lo2 > 0: [lo1/hi2, hi1/lo2], else [0, -1]
  n instanceof DivOpcode and
  n.inputIsPredictable() and
  exists(int lo1, int hi1, int lo2, int hi2 |
    inputBounds(n, 1, lo1, hi1) and
    inputBounds(n, 2, lo2, hi2) |
    if lo2 > 0 then (
      lo = divLo(lo1, hi2) and
      hi = divHi(hi1, lo2)
    ) else (
      lo = 0 and hi = -1
    )
  )
  or
  // Modulo: if hi2 > 0: [0, hi2-1], else [0, -1]
  n instanceof ModOpcode and
  n.inputIsPredictable() and
  exists(int hi2 |
    inputBounds(n, 2, _, hi2) |
    lo = 0 and
    (if hi2 > 0 and hi2 != -1 then hi = hi2 - 1 else hi = -1)
  )
  or
  // Square root: conservative [0, hi1] (sqrt can only decrease or stay same)
  n instanceof SqrtOpcode and
  n.inputIsPredictable() and
  exists(int hi1 |
    inputBounds(n, 1, _, hi1) |
    lo = 0 and hi = hi1
  )
  or
  // Shift right: [0, hi1] (shifting right can only decrease)
  n instanceof ShrOpcode and
  n.inputIsPredictable() and
  exists(int hi1 |
    inputBounds(n, 1, _, hi1) |
    lo = 0 and hi = hi1
  )
  or
  // Shift left: [lo1, unbounded] (conservative; shift left can overflow)
  n instanceof ShlOpcode and
  n.inputIsPredictable() and
  exists(int lo1 |
    inputBounds(n, 1, lo1, _) |
    lo = lo1 and hi = -1
  )
  or
  // Select: union of two branches [min(lo_a, lo_b), max(hi_a, hi_b)]
  // select pops (B, A, cond) and pushes A if cond!=0 else B
  // Input order: 1=cond (closest/top), 2=A (second), 3=B (third/deepest)
  n instanceof SelectOpcode and
  n.inputIsPredictable() and
  exists(int loA, int hiA, int loB, int hiB |
    inputBounds(n, 2, loA, hiA) and
    inputBounds(n, 3, loB, hiB) |
    (if loA <= loB then lo = loA else lo = loB) and
    hi = maxHi(hiA, hiB)
  )
  or
  // Dup: same bounds as input
  n instanceof DupOpcode and
  n.inputIsPredictable() and
  inputBounds(n, 1, lo, hi)
  or
  // Logical AND: result is 0 if either input is 0, else 1; conservative [0, max(hi1, hi2)]
  // In TEAL, && is logical (not bitwise), result is second arg if both nonzero, else 0
  n instanceof AndOpcode and
  n.inputIsPredictable() and
  exists(int hi1, int hi2 |
    inputBounds(n, 1, _, hi1) and
    inputBounds(n, 2, _, hi2) |
    lo = 0 and hi = maxHi(hi1, hi2)
  )
  or
  // Logical OR: result is first nonzero arg, else 0
  n instanceof OrOpcode and
  n.inputIsPredictable() and
  exists(int hi1, int hi2 |
    inputBounds(n, 1, _, hi1) and
    inputBounds(n, 2, _, hi2) |
    lo = 0 and hi = maxHi(hi1, hi2)
  )
  or
  // Bitwise AND: [0, min(hi1, hi2)]
  n instanceof BitandOpcode and
  n.inputIsPredictable() and
  exists(int hi1, int hi2 |
    inputBounds(n, 1, _, hi1) and
    inputBounds(n, 2, _, hi2) |
    lo = 0 and hi = minHi(hi1, hi2)
  )
  or
  // Bitwise OR: [0, max(hi1, hi2)] (conservative)
  n instanceof BitorOpcode and
  n.inputIsPredictable() and
  exists(int hi1, int hi2 |
    inputBounds(n, 1, _, hi1) and
    inputBounds(n, 2, _, hi2) |
    lo = 0 and hi = maxHi(hi1, hi2)
  )
  or
  // Bitwise XOR: [0, max(hi1, hi2)] (conservative)
  n instanceof BitxorOpcode and
  n.inputIsPredictable() and
  exists(int hi1, int hi2 |
    inputBounds(n, 1, _, hi1) and
    inputBounds(n, 2, _, hi2) |
    lo = 0 and hi = maxHi(hi1, hi2)
  )
}

// ---------------------------------------------------------------------------
// Combined opcode bounds: seed OR transfer (union, no negation)
// ---------------------------------------------------------------------------

/**
 * Holds if opcode `n` has integer output bounds [lo, hi].
 * Uses seed bounds when no transfer bounds are available, transfer bounds
 * when they exist, or the intersection when both exist.
 *
 * To avoid non-monotonic recursion (transfer -> input -> var -> opcode),
 * we simply take the union of all applicable bounds.
 */
predicate opcodeBounds(AstNode n, int lo, int hi) {
  seedBounds(n, lo, hi)
  or
  transferBounds(n, lo, hi)
}

/**
 * Format the upper bound for display: -1 becomes "MAX_UINT64".
 */
bindingset[hi]
string formatHi(int hi) {
  if hi = -1 then result = "MAX_UINT64"
  else result = hi.toString()
}
