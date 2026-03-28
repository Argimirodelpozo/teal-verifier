/**
 * Missing Fee Field Validation — v1 (token-based heuristic)
 *
 * What this query does:
 * It flags TEAL LogicSig sources that do NOT appear to validate `Txn.Fee`.
 *
 * How we decide this (very roughly):
 * A "good" LogicSig usually contains,
 *   - `txn`        (accessing a transaction field)
 *   - `Fee`        (specifically reading the fee)
 *   - `<=`         (comparing the fee to a bound)
 *   - `assert`     (enforcing the comparison)
 *
 * If a TEAL source is missing this overall pattern,
 * we flag it as potentially vulnerable.
 *
 * Note:
 * This version is NOT control-flow aware.
 * It does NOT prove the check runs on all paths.
 * It only checks whether these tokens appear anywhere in the source.
 *
 * Later versions will:
 *   - use the Control Flow Graph (e.g can only succesfuly exit when there is fee check)
 *   - experiment dominance (Is it possible to reach B without going through A?)
 *   - ensure fee validation cannot be bypassed (Every successful exit must be preceded by a fee validation)
 *      - proved via CFG (to know all paths) & Dominance (to ensure enforcement on all paths)
 */

import codeql.teal.ast.internal.TreeSitter // bare form of AST when codeql extracts
//import codeql.teal.ast.AST

/**
 * Identifies the root AST node representing an entire TEAL source file
 */
predicate isSource(Teal::AstNode n) {
  n.toString() = "Source"
}

/**
 * True if `n` is the same node as `root`, or appears anywhere inside `root`.
 * Linear node 
 */
predicate isDescendant(Teal::AstNode n, Teal::AstNode root) {
  n = root or
  exists(Teal::AstNode p |
    n.getParent() = p and
    isDescendant(p, root)
  )
}

/**
 * Checks whether a given TEAL source contains a specific token
 * somewhere in its AST (txn class somewhere in ast folder)
 */
predicate sourceHasToken(Teal::AstNode src, string tok) {
  exists(Teal::AstNode n |
    isDescendant(n, src) and
    n.toString() = tok
  )
}

/**
 * Definition of "Fee is validated".
 *
 * This does NOT guarantee correctness, it only checks that
 * the shape of a fee check appears in the source
 * this is a lower way to go about things (update it)
 * e.g getField fee
 */
predicate looksLikeFeeValidated(Teal::AstNode src) {
  sourceHasToken(src, "txn") and
  sourceHasToken(src, "Fee") and
  sourceHasToken(src, "<=") and
  sourceHasToken(src, "assert")
}

/**
 * Report any TEAL source that does NOT appear to validate Txn.Fee.
 */
from Teal::AstNode src
where
  isSource(src) and
  not looksLikeFeeValidated(src)
select
  src,
  "Potential missing Txn.Fee validation (no txn Fee <= assert pattern found)."
