/**
 * Branch-sensitive value constraints for user inputs.
 *
 * Uses ConditionBlock.controls(bb, BooleanSuccessor) to determine what
 * constant value an input is constrained to at a given program point.
 * For example, after `txna ApplicationArgs 0 ; pushbytes 0x... ; == ; bnz handler`,
 * the handler knows the exact method selector value.
 */

import codeql.teal.ast.AST
import codeql.teal.SSA.SSA
import codeql.teal.cfg.BasicBlocks
import codeql.teal.ast.BytearrayBounds
private import codeql.teal.cfg.Completion::Completion

/**
 * Canonical identifier for an input source — two opcodes with the same
 * inputKind read the same external value within a transaction.
 */
string inputKind(AstNode n) {
  result = "txn:" + n.(TxnOpcode).getField()
  or
  result = "txna:" + n.(TxnaOpcode).getField() + ":" + n.(TxnaOpcode).getIndex().toString()
  or
  result = "global:" + n.(GlobalOpcode).getField()
}

/**
 * Resolves an SSAVar through scratch space load/store indirection.
 * If `sv` was declared by a `load` opcode with a unique dominating store,
 * follow the chain to the variable that was stored. Recurses to handle
 * chained store/load patterns.
 */
SSAVar resolveVar(SSAVar sv) {
  not sv.getDeclarationNode() instanceof LoadOpcode and result = sv
  or
  result = resolveVar(sv.getDeclarationNode().(LoadOpcode).getScratchSpaceStoredVariable())
}

/**
 * Holds if SSA variable `sv` is a known constant, binding `constValue`
 * to its representation (integer toString or byte hex value).
 * Resolves through scratch space loads so that a stored constant
 * is recognized when later loaded.
 */
predicate isConstantVar(SSAVar sv, string constValue) {
  exists(SSAVar resolved | resolved = resolveVar(sv) |
    constValue = resolved.getDeclarationNode().(IntegerConstant).getValue().toString()
    or
    seedBytesValue(resolved.getDeclarationNode(), constValue)
  )
}

/**
 * Identifies a ConditionBlock whose branch tests an equality guard:
 * the governing comparison's input traced to a user input and a constant.
 * `equalBranch` is the BooleanSuccessor on which equality holds.
 */
predicate equalityGuard(
  ConditionBlock cb, string inputKindStr, AstNode inputOpcode,
  string constValue, BooleanSuccessor equalBranch
) {
  exists(SimpleConditionalBranches branch, SSAVar governingVar, AstNode compNode |
    // The branch opcode lives in this condition block
    branch.getBasicBlock() = cb and
    // The branch's governing value is an SSA var
    governingVar = branch.getGoverningVal() and
    // Trace through SSA to the declaring opcode
    compNode = governingVar.getDeclarationNode() and
    (
      // Case 1: == comparison — equality holds on true branch
      // Note: use IntegerEqualsOpcode (based on TOpcode_eq) rather than
      // EqualsComparisonOpcode, because the latter relies on getOperator()
      // which is broken when the node is also an SSAVar (toString override).
      compNode instanceof IntegerEqualsOpcode and
      equalBranch.getValue() = true and
      exists(
        Definition firstDef, Definition secondDef, SSAVar firstVar, SSAVar secondVar,
        SSAVar firstResolved, SSAVar secondResolved
      |
        firstDef = compNode.(LogicalComparisonOp).firstOp() and
        secondDef = compNode.(LogicalComparisonOp).secondOp() and
        firstVar = getGenerator(firstDef) and
        secondVar = getGenerator(secondDef) and
        firstResolved = resolveVar(firstVar) and
        secondResolved = resolveVar(secondVar) and
        (
          // first is constant, second is input
          isConstantVar(firstVar, constValue) and
          inputKindStr = inputKind(secondResolved.getDeclarationNode()) and
          inputOpcode = secondResolved.getDeclarationNode()
          or
          // second is constant, first is input
          isConstantVar(secondVar, constValue) and
          inputKindStr = inputKind(firstResolved.getDeclarationNode()) and
          inputOpcode = firstResolved.getDeclarationNode()
        )
      )
      or
      // Case 2: != comparison — equality holds on false branch
      compNode instanceof IntegerNotEqualsOpcode and
      equalBranch.getValue() = false and
      exists(
        Definition firstDef, Definition secondDef, SSAVar firstVar, SSAVar secondVar,
        SSAVar firstResolved, SSAVar secondResolved
      |
        firstDef = compNode.(LogicalComparisonOp).firstOp() and
        secondDef = compNode.(LogicalComparisonOp).secondOp() and
        firstVar = getGenerator(firstDef) and
        secondVar = getGenerator(secondDef) and
        firstResolved = resolveVar(firstVar) and
        secondResolved = resolveVar(secondVar) and
        (
          isConstantVar(firstVar, constValue) and
          inputKindStr = inputKind(secondResolved.getDeclarationNode()) and
          inputOpcode = secondResolved.getDeclarationNode()
          or
          isConstantVar(secondVar, constValue) and
          inputKindStr = inputKind(firstResolved.getDeclarationNode()) and
          inputOpcode = firstResolved.getDeclarationNode()
        )
      )
    )
  )
}

/**
 * At `point`, the input identified by `inputKindStr` is constrained to `constValue`.
 */
predicate inputBoundAtPoint(AstNode point, string inputKindStr, string constValue) {
  exists(ConditionBlock cb, BooleanSuccessor s |
    equalityGuard(cb, inputKindStr, _, constValue, s) and
    cb.controls(point.getBasicBlock(), s)
  )
}

/**
 * Convenience: at `point`, the specific opcode's semantic input is constrained.
 */
predicate opcodeBoundAtPoint(AstNode point, AstNode inputOpcode, string constValue) {
  inputBoundAtPoint(point, inputKind(inputOpcode), constValue)
}

/**
 * All constant values that an input kind is ever compared against.
 */
predicate inputValueDictionary(string inputKindStr, string constValue) {
  equalityGuard(_, inputKindStr, _, constValue, _)
}
