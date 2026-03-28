/**
 * Stack depth analysis for TEAL programs.
 *
 * Computes stack depth bounds at every CFG node by propagating depths
 * forward from program entry (depth=0) through basic blocks.
 *
 * Detects three classes of violations:
 * - Stack overflow: depth exceeds the AVM limit of 1000
 * - Stack underflow: opcode tries to consume more items than available
 * - Inconsistent depth: different paths to the same node produce different depths
 */

private import codeql.teal.ast.AST
private import codeql.teal.cfg.BasicBlocks
private import codeql.teal.cfg.CFG::CfgImpl

/**
 * Holds if `delta` is the total stack depth change across basic block `bb`.
 * Only holds when all AST nodes in the block have known stack effects.
 * For blocks with only virtual nodes (e.g., entry blocks), delta is 0.
 */
predicate basicBlockDelta(BasicBlock bb, int delta) {
  forall(int i, AstNode n |
    n = bb.getNode(i).(AstCfgNode).getAstNode() |
    exists(n.getStackDelta())
  ) and
  delta = sum(int i, AstNode n |
    n = bb.getNode(i).(AstCfgNode).getAstNode() |
    n.getStackDelta()
  )
}

/** Holds if basic block `bb` ends with a retsub that has an affecting proto. */
private predicate endsWithRetsubProto(BasicBlock bb, RetsubOpcode retsub, ProtoOpcode proto) {
  exists(int last |
    last = bb.length() - 1 and
    retsub = bb.getNode(last).(AstCfgNode).getAstNode() and
    proto = retsub.getAffectingProto()
  )
}

/**
 * Holds if `depth` is a possible stack depth at the entry of basic block `bb`.
 * Entry blocks start at depth 0. Other blocks inherit depth from predecessors.
 * Bounded to [0, 1000] to ensure termination.
 */
predicate bbEntryDepth(BasicBlock bb, int depth) {
  bb instanceof EntryBasicBlock and depth = 0
  or
  // Normal case: predecessor does NOT end with retsub-with-proto
  not bb instanceof EntryBasicBlock and
  exists(BasicBlock pred, int predDepth, int predDelta |
    pred = bb.getAPredecessor() and
    not endsWithRetsubProto(pred, _, _) and
    bbEntryDepth(pred, predDepth) and
    basicBlockDelta(pred, predDelta) and
    depth = predDepth + predDelta and
    depth >= 0 and depth <= 1000
  )
  or
  // Retsub-with-proto case: depth after return = subroutine entry depth - A + B
  // where A = proto input count, B = proto output count
  not bb instanceof EntryBasicBlock and
  exists(BasicBlock pred, RetsubOpcode retsub, ProtoOpcode proto, int entryDepth |
    pred = bb.getAPredecessor() and
    endsWithRetsubProto(pred, retsub, proto) and
    bbEntryDepth(retsub.getEntrypoint().getBasicBlock(), entryDepth) and
    depth = entryDepth - proto.getNumberOfInputArgs() + proto.getNumberOfOutputArgs() and
    depth >= 0 and depth <= 1000
  )
}

/**
 * Gets the cumulative stack delta at position `pos` in basic block `bb`,
 * before the node at that position executes.
 * Only holds if all prior AST nodes have known stack effects.
 */
int intraBlockOffset(BasicBlock bb, int pos) {
  pos in [0 .. bb.length() - 1] and
  exists(bb.getNode(pos).(AstCfgNode).getAstNode()) and
  forall(int i, AstNode n |
    i in [0 .. pos - 1] and n = bb.getNode(i).(AstCfgNode).getAstNode() |
    exists(n.getStackDelta())
  ) and
  result = sum(int i, AstNode n |
    i in [0 .. pos - 1] and n = bb.getNode(i).(AstCfgNode).getAstNode() |
    n.getStackDelta()
  )
}

/**
 * Holds if `depth` is a possible stack depth before AST node `n` executes.
 * There may be multiple possible depths if different paths reach `n` with
 * different stack states.
 */
predicate nodeStackDepth(AstNode n, int depth) {
  exists(BasicBlock bb, int pos, int offset, int entryDepth |
    bb = n.getBasicBlock() and
    pos = n.getIndexInBasicBlock() and
    offset = intraBlockOffset(bb, pos) and
    bbEntryDepth(bb, entryDepth) and
    depth = entryDepth + offset
  )
}

/**
 * Holds if `minDepth` and `maxDepth` are the minimum and maximum possible
 * stack depths before AST node `n` executes.
 */
predicate nodeStackDepthBefore(AstNode n, int minDepth, int maxDepth) {
  minDepth = min(int d | nodeStackDepth(n, d) | d) and
  maxDepth = max(int d | nodeStackDepth(n, d) | d)
}

/**
 * Holds if `minDepth` and `maxDepth` are the minimum and maximum possible
 * stack depths after AST node `n` executes.
 */
predicate nodeStackDepthAfter(AstNode n, int minDepth, int maxDepth) {
  exists(int beforeMin, int beforeMax, int delta |
    nodeStackDepthBefore(n, beforeMin, beforeMax) and
    delta = n.getStackDelta() and
    minDepth = beforeMin + delta and
    maxDepth = beforeMax + delta
  )
}

/** Holds if node `n` causes a stack overflow (depth exceeds 1000 after execution). */
predicate stackOverflow(AstNode n, int maxDepth) {
  nodeStackDepthAfter(n, _, maxDepth) and
  maxDepth > 1000
}

/** Holds if node `n` causes a stack underflow (tries to consume more items than available). */
predicate stackUnderflow(AstNode n, int minDepth) {
  exists(int consumed |
    nodeStackDepthBefore(n, minDepth, _) and
    consumed = n.getNumberOfConsumedArgs() and
    consumed != -1 and
    minDepth < consumed
  )
}

/** Holds if different paths to node `n` produce different stack depths. */
predicate inconsistentStackDepth(AstNode n, int minDepth, int maxDepth) {
  nodeStackDepthBefore(n, minDepth, maxDepth) and
  minDepth != maxDepth
}

/**
 * Holds if `delta` is the effective stack delta of `retsub`, accounting for proto.
 * With proto: delta = -depth + proto.outputArgs (clears subroutine frame, keeps outputs).
 * Without proto: delta = 0.
 */
predicate retsubEffectiveDelta(RetsubOpcode retsub, int delta) {
  exists(ProtoOpcode proto, int depth |
    proto = retsub.getAffectingProto() and
    nodeStackDepth(retsub, depth) and
    delta = -depth + proto.getNumberOfOutputArgs()
  )
  or
  not exists(retsub.getAffectingProto()) and
  delta = 0
}
