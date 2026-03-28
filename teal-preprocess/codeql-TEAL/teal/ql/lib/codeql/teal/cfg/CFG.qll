private import codeql.teal.ast.AST
private import codeql.controlflow.Cfg as CfgShared
private import codeql.Locations
private import codeql.teal.ast.internal.TreeSitter
private import codeql.teal.cfg.Completion::Completion

module CfgScope {
  abstract class CfgScope extends AstNode { }

  class ProgramScope extends CfgScope, Program { 
    
    // override string toString(){
    //   result = "ProgramScope"
    // }
  }

  // class CodeblockScope extends CfgScope, Codeblock { 
    
  //   // override string toString(){
  //   //   result = "CodeblockScope"
  //   // }
  // }
}

private module Implementation implements CfgShared::InputSig<Location> {
  import codeql.teal.ast.AST
  import codeql.teal.cfg.Completion::Completion
  import CfgScope

  predicate completionIsNormal(Completion c) { c instanceof NormalCompletion }

  // Not using CFG splitting, so the following are just dummy types.
  // private newtype TUnit = Unit()

  // class SplitKindBase = TUnit;

  // class Split extends TUnit {
  //   abstract string toString();
  // }

  predicate completionIsSimple(Completion c) { c instanceof SimpleCompletion }

  predicate completionIsValidFor(Completion c, AstNode e) { c.isValidFor(e) }

  CfgScope getCfgScope(AstNode e) {
    result = e.getProgram()
    // if e instanceof Program or e instanceof Codeblock then result = e.getProgram()
    // else 
    // result = e.getCodeblockStart().(Codeblock)
  }

  int maxSplits() { result = 0 }

  predicate scopeFirst(CfgScope scope, AstNode e) {
    first(scope.(Program), e)
    // or
    // not scope instanceof Program and
    // first(scope.(Codeblock), e)
  }

  predicate scopeLast(CfgScope scope, AstNode e, Completion c) {
    last(scope.(Program), e, c)
    // or
    // not scope instanceof Program and
    // last(scope.(Codeblock), e, c)
  }

  predicate successorTypeIsSimple(SuccessorType t) { t instanceof NormalSuccessor }

  predicate successorTypeIsCondition(SuccessorType t) { t instanceof BooleanSuccessor }

  SuccessorType getAMatchingSuccessorType(Completion c) { result = c.getAMatchingSuccessorType() }

  predicate isAbnormalExitType(SuccessorType t) { none() }

    /**
   * Gets an `id` of `node`. This is used to order the predecessors of a join
   * basic block.
   */
  int idOfAstNode(AstNode node){result = node.getLineNumber()}

  /**
   * Gets an `id` of `scope`. This is used to order the predecessors of a join
   * basic block.
   */
  int idOfCfgScope(CfgScope scope){result = scope.getCodeblockStart().getLineNumber()}
}

module CfgImpl = CfgShared::Make<Location, Implementation>;

private import CfgImpl
private import Completion
private import CfgScope
// private import codeql.teal.cfg.BasicBlocks


// /**
//  * A control flow node.
//  *
//  * A control flow node is a node in the control flow graph (CFG). There is a
//  * many-to-one relationship between CFG nodes and AST nodes.
//  *
//  * Only nodes that can be reached from an entry point are included in the CFG.
//  */
// class CfgNode extends CfgImpl::Node {
//   /** Gets the name of the primary QL class for this node. */
//   string getAPrimaryQlClass() { none() }

//   /** Gets the file of this control flow node. */
//   final File getFile() { result = this.getLocation().getFile() }

//   /** Gets a successor node of a given type, if any. */
//   final CfgNode getASuccessor(SuccessorType t) { result = super.getASuccessor(t) }

//   /** Gets an immediate successor, if any. */
//   final CfgNode getASuccessor() { result = this.getASuccessor(_) }

//   /** Gets an immediate predecessor node of a given flow type, if any. */
//   final CfgNode getAPredecessor(SuccessorType t) { result.getASuccessor(t) = this }

//   /** Gets an immediate predecessor, if any. */
//   final CfgNode getAPredecessor() { result = this.getAPredecessor(_) }

//   /** Gets the basic block that this control flow node belongs to. */
//   BasicBlock getBasicBlock() { result.getANode() = this }
// }








private class ProgramTree extends ControlFlowTree instanceof Program {
    override predicate propagatesAbnormal(AstNode child) { none() }

    override predicate first(AstNode first) { first(this.(Program).getChild(0).(CodeblockTree), first) }

    override predicate succ(AstNode pred, AstNode succ, Completion c) {
      succ.getProgram() = this and pred.getProgram() = this and
      (
      last(pred.getCodeblockStart().(CodeblockTree), pred, c) and
      pred instanceof BzOpcode and
      first(pred.(BzOpcode).getNextNode(c.(ConditionalJumpCompletion).getValue()).(Codeblock), succ)
      or
      last(pred.getCodeblockStart().(CodeblockTree), pred, c) and
      pred instanceof BnzOpcode and
      first(pred.(BnzOpcode).getNextNode(c.(ConditionalJumpCompletion).getValue()).(Codeblock), succ)
      or
      last(pred.getCodeblockStart().(CodeblockTree), pred, c) and
      pred instanceof BOpcode and
      c instanceof UnconditionalJumpCompletion and
      first(pred.(BOpcode).getTargetLabel().(Codeblock), succ)
      or

      last(pred.getCodeblockStart().(CodeblockTree), pred, c) and
      pred instanceof MatchOpcode and
      c instanceof MultilabelJumpCompletion and
      first(pred.(MatchOpcode).getNextNode(_).(Codeblock), succ)
      or

      last(pred.getCodeblockStart().(CodeblockTree), pred, c) and
      pred instanceof CallsubOpcode and
      c instanceof UnconditionalJumpCompletion and
      first(pred.(CallsubOpcode).getTargetLabel().(Codeblock), succ)
      or
      last(pred.getCodeblockStart().(CodeblockTree), pred, c) and
      pred instanceof RetsubOpcode and
      c instanceof RetsubCompletion and
      succ = pred.(RetsubOpcode).predictRetsubReturn() and
      first(pred.(RetsubOpcode).predictRetsubReturn().(CodeblockTree), succ)

        or
        last(pred.getCodeblockStart().(CodeblockTree), pred, c) and
        pred.getNextLine() instanceof Label and succ = pred.getNextLine() and
        not (pred instanceof UnconditionalBranches 
          or pred instanceof SimpleConditionalBranches or pred instanceof ContractExitOpcode or
          pred instanceof MultiTargetConditionalBranch) 
        and
        c instanceof SimpleCompletion and
        first(pred.getNextLine().(Codeblock), succ)
        or
        last(pred.getCodeblockStart().(CodeblockTree), pred, c) and
        pred instanceof AssertOpcode and
        c.(AssertCompletion).getValue() = true and
        first(pred.getNextLine().(Codeblock), succ)
        or
        last(pred.getCodeblockStart().(CodeblockTree), pred, c) and
        pred instanceof ReturnOpcode and c instanceof ReturnCompletion and succ = this.(Program)
        or
        last(pred.getCodeblockStart().(CodeblockTree), pred, c) and
        pred instanceof ErrOpcode and c instanceof ErrCompletion and succ = this.(Program)
        or
        last(pred.getCodeblockStart().(CodeblockTree), pred, c) and
        pred instanceof AssertOpcode and c.(AssertCompletion).getValue() = false and succ = this.(Program)

      //TODO: test
      or
      last(pred.getCodeblockStart().(CodeblockTree), pred, c) and
      pred instanceof MultiTargetConditionalBranch and
      c instanceof UnconditionalJumpCompletion and
      first(pred.(MultiTargetConditionalBranch).getTargetLabels(), succ)
      )
  }

  override predicate last(AstNode last, Completion c) {
    last.getProgram() = this and(
      last = this and c instanceof SimpleCompletion
      // or
      // c instanceof SimpleCompletion and
      // last instanceof Label and not exists(last.(Label).getNextLine())
    )
  }
}

private class CodeblockTree extends ControlFlowTree instanceof Codeblock{

  override predicate propagatesAbnormal(AstNode child) { none() }

  override predicate first(AstNode first) { first = this.getCodeblockStart() }

  override predicate succ(AstNode pred, AstNode succ, Completion c) {
    pred.isInSameCodeblock(this) and succ.isInSameCodeblock(this) and 
    pred.isInSameCodeblock(succ)
    and succ = pred.getNextLine() and c instanceof SimpleCompletion
  }

  override predicate last(AstNode last, Completion c) {
    last.endsACodeblock() and last.isInSameCodeblock(this)
    and (
      last instanceof ReturnOpcode and c instanceof ReturnCompletion
      or last instanceof ErrOpcode and c instanceof ErrCompletion
      or last instanceof AssertOpcode and c instanceof AssertCompletion
      or last instanceof BOpcode and c instanceof UnconditionalJumpCompletion
      or last instanceof CallsubOpcode and c instanceof UnconditionalJumpCompletion

      or last instanceof MatchOpcode and c instanceof MultilabelJumpCompletion

      or last instanceof RetsubOpcode and c instanceof RetsubCompletion
      or last instanceof SimpleConditionalBranches and c instanceof ConditionalJumpCompletion
      or last.getNextLine() instanceof Label and not
        (last instanceof ContractExitOpcode or last instanceof UnconditionalBranches or
        last instanceof SimpleConditionalBranches or last instanceof MultiTargetConditionalBranch) 
        and c instanceof SimpleCompletion
    )
    // or last.isInSameCodeblock(this) and last.getNextLine() instanceof RetsubOpcode and c instanceof NormalCompletion
  }
}

private class OpcodeTree extends LeafTree instanceof AstNode {
  OpcodeTree(){
    not this instanceof Program
    and not this instanceof Codeblock
  }
}