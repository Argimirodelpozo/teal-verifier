/**
 * Scratch space type and bounds inference for TEAL store/load opcodes.
 *
 * For each `store`/`load`, infers the type (int vs bytes), bounds, exact
 * value, and origin SSA variable by cross-referencing IntegerBounds and
 * BytearrayBounds on the stored variable's declaration node.
 */

import codeql.teal.ast.AST
import codeql.teal.SSA.SSA
import codeql.teal.ast.IntegerBounds
import codeql.teal.ast.BytearrayBounds
import codeql.teal.ast.opcodes.ScratchSpace

/**
 * Holds if `store` writes to scratch slot `slot` and the stored value has
 * type `type` with bounds [lo, hi], optional exact `value`, and SSA origin
 * `origin`.
 *
 * Type inference:
 * - "int" if the stored variable's declaration has integer bounds
 * - "bytes" if the stored variable's declaration has byte array bounds
 * - Both rows emitted if both hold (e.g., app_global_get)
 */
predicate scratchStoreInfo(
  StoreOpcode store, int slot, string type, int lo, int hi, string value,
  string origin
) {
  slot = store.getSPVarIndex() and
  exists(SSAVar sv | sv = store.getScratchSpaceStoredVariable() |
    // Integer bounds on stored variable
    type = "int" and
    opcodeBounds(sv.getDeclarationNode(), lo, hi) and
    (
      if lo = hi
      then value = lo.toString()
      else value = ""
    ) and
    origin = sv.getIdentifier()
    or
    // Byte array bounds on stored variable
    type = "bytes" and
    opcodeBytesBounds(sv.getDeclarationNode(), lo, hi) and
    (
      if opcodeBytesValue(sv.getDeclarationNode(), value)
      then any()
      else value = ""
    ) and
    origin = sv.getIdentifier()
  )
}

/**
 * Holds if `load` reads from scratch slot `slot` and the loaded value has
 * type `type` with bounds [lo, hi], optional exact `value`, and SSA origin
 * `origin`. Traced through the influencing store.
 */
predicate scratchLoadInfo(
  LoadOpcode load, int slot, string type, int lo, int hi, string value,
  string origin
) {
  slot = load.getSPVarIndex() and
  exists(StoreOpcode store | store = load.getInfluencingStore() |
    scratchStoreInfo(store, slot, type, lo, hi, value, origin)
  )
}
