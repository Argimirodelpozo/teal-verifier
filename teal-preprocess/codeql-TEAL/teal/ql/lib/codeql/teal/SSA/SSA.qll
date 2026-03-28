private import codeql.teal.cfg.BasicBlocks
private import codeql.Locations
private import codeql.teal.cfg.CFG as Cfg
private import codeql.teal.ast.AST
private import codeql.teal.ast.IntegerConstants
// private import codeql.teal.SSA.SSA


// private newtype TDefinition = 
//   TWriteDef(BasicBlock bb, int bbi, int varInternalIdx, AstNode n){
//   n = bb.getNode(bbi).getAstNode() and
//   bbi in [0 .. bb.length()-1] and
//   varInternalIdx in [1 .. bb.getNode(bbi).getAstNode().getNumberOfOutputArgs()]
//   }
//   or TPhiNode(BasicBlock bb, int stackOrd, boolean comesFromVars){
//   exists (SSAVar v | v.getDeclarationNode().getBasicBlock() = bb.getAPredecessor() and 
//     v.reachesEndOfOriginBB() and stackOrd = v.outStackOrder() and comesFromVars = true)
//     or exists(PhiNode n, BasicBlock b, int ord| b = bb.getAPredecessor() and
//       n = TPhiNode(b, ord, _) and not exists(phiNodeGetsConsumedBy(ord, b)) and comesFromVars = false
//       and stackOrd = 
//       ord - strictcount(int k | k in [1 .. ord - 1] and 
//         exists(phiNodeGetsConsumedBy(k, b)))
//       )
//   }
//   // or TPhiNode(BasicBlock bb, int stackOrd, boolean comesFromVars){
//   //   exists (SSAWriteDefinition v | v.getDeclarationNode().getBasicBlock() = bb.getAPredecessor() and 
//   //     not exists(writeDefGetsConsumedBy(stackOrd, v.getDeclarationNode(), v.getBasicBlock())) 
//   //     and stackOrd = v.outStackOrder() and comesFromVars = true)
//   //     or exists(PhiNode n, BasicBlock b| b = bb.getAPredecessor() and
//   //       n = TPhiNode(b, stackOrd, _) and not exists(phiNodeGetsConsumedBy(stackOrd, b)) and comesFromVars = false)
//   //   }


// // int computeStackOrderForPhi(BasicBlock originalBB, int originalStackOrder, BasicBlock currentBB){
// //   result = originalStackOrder - strictcount(int k | k in [1 .. originalStackOrder - 1] and 
// //     exists(phiNodeGetsConsumedBy(k, originalBB)))
// // }


// int stackConsumption(BasicBlock bb){
//   result = sum(AstNode n | n = bb.getANode().getAstNode() | n.getNumberOfConsumedArgs())                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
// }

// int stackContribution(BasicBlock bb){
//   result = sum(AstNode n | n = bb.getANode().getAstNode() | n.getNumberOfOutputArgs())
// }

// cached
// int stackDelta(BasicBlock bb){
//   result = stackContribution(bb) - stackConsumption(bb)
// }


// int stackAtBeginning(BasicBlock bb){

//   if not exists(bb.getAPredecessor()) then result = 0
//   else
//     result = max(sum(stackDelta(bb.getAPredecessor*())))
// }


// // int stackAtBeginning_aux(BasicBlock current, BasicBlock target){
// //   current != target and
// //   result = stackDelta(current) + 
// //     stackAtBeginning_aux(current.getASuccessor(), target)
// //   or 
// //   current = target and result = 0
// // }

// // int stackAtBeginning(BasicBlock bb){
// //   result = stackAtBeginning_aux(bb.getScope().(Program).getChild(0).getBasicBlock(), bb)
// // }



// abstract class Definition extends TDefinition{
//   abstract string toString();

//   abstract Location getLocation();
// }


// class PhiNode extends Definition instanceof TPhiNode{

//   BasicBlock getBasicBlock(){TPhiNode(result, _, _) = this}
//   int getIndexInPreStack(){
//     exists(boolean c | TPhiNode(_, result, c) = this and c = true) or
//     exists(boolean c, int j, int k | TPhiNode(_, k, c) = this and c = false
//       // and j = max(PhiNode n, int h | n.getBasicBlock() = this.getBasicBlock() and n = TPhiNode(n.getBasicBlock(), h ,true) | h)
//       and j = count(PhiNode n | n.getBasicBlock() = this.getBasicBlock() and n = TPhiNode(n.getBasicBlock(), _ ,true))
//       and result = j+k)
//   }
//   // Definition getOrigin(){TPhiNode(result) = this}

//   // //how many phis includes total number (valid and invalid)
//   // int howManyPhis(){
//   //   result = count(PhiNode n | n.getBasicBlock() = this.getBasicBlock())
//   // }

//   // int getID(){
//   //   exists(PhiNode phi | phi.getBasicBlock() = this.getBasicBlock().getAPredecessor() and 
//   //     rank[h]())
//   // }

//   // SSAVar getAnInput_var(){result = rank[this.getIndexInPreStack()]
//   //   (SSAVar v | v = this.getBasicBlock().getAPredecessor().getANode().getAstNode().getAnOutputVar() and 
//   //     v.reachesEndOfOriginBB() |
//   //   v order by v.getBBI())}

//   predicate hasInputFromBlock(BasicBlock b){
//     b.getASuccessor() = this.getBasicBlock() and 
//     exists(SSAVar v | v.reachesEndOfOriginBB()) or
//     exists(PhiNode n | n.reachesEndOfOriginBB())
//   }

//   // Definition getInput(int i){
//   //   result = 
//   // }

//   PhiNode getAnInput(){result = rank[this.getIndexInPreStack()]
//     (PhiNode n | this.getBasicBlock().getAPredecessor() = n.getBasicBlock() and 
//     n.reachesEndOfOriginBB() | n order by n.getIndexInPreStack())}

//   Definition getAnInput2(){result = rank[this.getIndexInPreStack()]
//       (PhiNode n | this.getBasicBlock().getAPredecessor() = n.getBasicBlock() and 
//       n.reachesEndOfOriginBB() | n order by n.getIndexInPreStack()) or
//       result = rank[this.getIndexInPreStack()]
//       (SSAVar n | this.getBasicBlock().getAPredecessor() = n.getBasicBlock() and 
//       n.reachesEndOfOriginBB() | n.toWriteDef() order by n.outStackOrder())
//     }

//     override string toString(){
//       // if 
//       // this = TPhiNode(_, _, false) 
//       // then
//         result = "phi" + this.getBasicBlock().getFirstNode().getAstNode().getLineNumber() 
//           + "_" + this.getIndexInPreStack()
//       // else 
//       //   exists(SSAVar v | v.reachesEndOfOriginBB() and
//       //   result = "phi_" + this.getIndexInPreStack() + " = PHI(" + 
//       //   v + " " + v.getLineNumber() + ")")
//     }

//     // Location showAllInput(){
//     //   exists(SSAVar v| v.reachesEndOfOriginBB() 
//     //   and v.getBasicBlock() = this.getBasicBlock().getAPredecessor() | result = v.getLocation())
//     //   // result = concat(SSAVar v | v.reachesEndOfOriginBB() 
//     //   //   and v.getBasicBlock() = this.getBasicBlock().getAPredecessor() | v.toString(), " ")
//     // }
  
//     override Location getLocation(){result = this.getBasicBlock().getLocation()}

//     /** Holds if `(this, v)` reaches the end of its origin basic block. */
//   predicate reachesEndOfOriginBB() {
//     not exists(this.getConsumedBy())
//   }

//   cached
//   AstNode getConsumedBy(){
//       result = rank[1](AstNode end|
//           end = this.getBasicBlock().getANode().getAstNode() and
//           this.getIndexInPreStack() + getPartialStackSizeBeforeOutput(end.getBasicBlock().getFirstNode().getAstNode(), end) <= 0
//           | end order by end.getLineNumber()
//       )
//   }
// }

// class SSAWriteDefinition extends Definition instanceof TWriteDef{

//   BasicBlock getBasicBlock(){this = TWriteDef(result, _, _, _)}
//   int getBasicBlockIndex(){this = TWriteDef(_, result, _, _)}
//   int getVarInternalIndex(){this = TWriteDef(_, _, result, _)}
//   AstNode getDeclarationNode(){
//     this = TWriteDef(_, _, _, result)
//   }

//     /** Holds if `(this, v)` reaches the end of its origin basic block. */
//     predicate reachesEndOfOriginBB() {
//       not exists(writeDefGetsConsumedBy(this.getVarInternalIndex(), this.getDeclarationNode(), this.getBasicBlock())) 
//       // not exists(this.getDeclarationNode().getConsumedBy_new(this.getVarInternalIndex()))
//   }

//   int outStackOrder(){
//     this = rank[result](SSAWriteDefinition v | 
//       // this.getDeclarationNode().getBasicBlock().getANode().getAstNode().getAnOutputVar_new() = v 
//       // and 
//       v.reachesEndOfOriginBB() | v order by v.getDeclarationNode().getLineNumber() desc)
//   }

//   override string toString(){result = "out(" + this.getDeclarationNode() + ")_" + this.getVarInternalIndex()}

//   override Location getLocation(){
//     result = this.getDeclarationNode().getLocation()
//   }
// }

newtype TDefinition = 
  TSSAVar(int varIndex, AstNode n){
    varIndex in [1 .. n.getNumberOfOutputArgs()]
  } or
  TDirectPhi(int varIndex, BasicBlock bb){
    exists(SSAVar v | v.reachesEndOfOriginBB()
    and bb = v.getBasicBlock().getASuccessor() and
    varIndex = v.outStackOrder())
  } or
  TIndirectPhi(int varIndex, BasicBlock bb){
    exists(TDirectPhi phi, int k, BasicBlock b | 
      phi = TDirectPhi(k, b) and varIndex = phiNodeExitIndex(k, b) and
      bb = b.getASuccessor())
      or not exists(TDirectPhi phi, int k, BasicBlock b | 
        phi = TDirectPhi(k, b) and varIndex = phiNodeExitIndex(k, b) and
        bb = b.getASuccessor()) and
      exists(TIndirectPhi phi, int k, BasicBlock b | phi = TIndirectPhi(k, b) and
        bb = b.getASuccessor() and varIndex = phiNodeExitIndex(k, b) 
        // and exists(phi.getGenerator())
      )
  }

abstract class Definition extends TDefinition{
  abstract string toString();

  abstract Location getLocation();

  abstract int getOrd();

  // predicate definesAt(SSAVar v, int i, BasicBlock bb){
  //   this instanceof SSAWriteDef and v.toDef() = this 
  //     and v.getDeclarationNode() = bb.getNode(i).getAstNode() or
  //   this instanceof DirectPhi and i = -1 and this.(DirectPhi).getBasicBlock() = bb
  //     and v.getBasicBlock() = bb and v = bb.getFirstNode().getAstNode() 
  //     and v.getInternalOutputIndex() = this.(DirectPhi).getInitialStackIndex()
  //     or
  //   this instanceof IndirectPhi and i = -1 and this.(IndirectPhi).getBasicBlock() = bb
  //     and v.getBasicBlock() = bb and v = bb.getFirstNode().getAstNode()
  //     and v.getInternalOutputIndex() = this.(IndirectPhi).getInitialStackIndex()
  // }


}

class SSAWriteDef extends Definition instanceof TSSAVar{
  SSAVar v;

  SSAWriteDef(){this = TSSAVar(v.getInternalOutputIndex(), v.getDeclarationNode())}

  override string toString(){
    result = "var_" + v.getDeclarationNode() + "_" + v.getInternalOutputIndex()
  }

  override Location getLocation(){result = v.getDeclarationNode().getLocation()}

  AstNode getRHS(){result = v.getDeclarationNode()}

  SSAVar getVar(){result = v}

  override int getOrd(){result = -1}
}

//TODO: try with this one, and see if it still causes 
//  the "cartesian explosion" bug with simple flow queries
// newtype TStackVar = TSSaVarType(int index, Location loc){
//   exists(AstNode n | n.getLocation() = loc and index in [1 .. n.getNumberOfOutputArgs()])
// }


class SSAVar extends AstNode{
int varInternalIndex;
// boolean phi;
// string varIdentifier;

    SSAVar(){ 
      exists(AstNode n| this = n and varInternalIndex in [1 .. n.getNumberOfOutputArgs()])}

    string getIdentifier(){result = "V" + "#" + this.getInternalOutputIndex().toString() + "@L" + this.getLineNumberInFile()}

    SSAWriteDef toDef(){result = TSSAVar(this.getInternalOutputIndex(), this)}
    // SSAWriteDefinition toWriteDef(){result.getBasicBlock() = this.getDeclarationNode().getBasicBlock()
    //   and result.getBasicBlockIndex() = this.getBBI() and result.getVarInternalIndex() = this.getInternalOutputIndex()}

    AstNode getDeclarationNode(){result = this}

    int getInternalOutputIndex(){result = varInternalIndex}

    int getBBI(){this.getDeclarationNode().getBasicBlock().getNode(result).getAstNode() = this.getDeclarationNode()}

  /** Holds if `(this, v)` reaches the end of its origin basic block. */
  predicate reachesEndOfOriginBB() {
      not exists(this.getDeclarationNode().getConsumedBy(this))
  }

  int outStackOrder(){
    this = rank[result](SSAVar v | this.getDeclarationNode().getBasicBlock().getANode().getAstNode().getAnOutputVar() = v and v.reachesEndOfOriginBB() | 
     v order by v.getDeclarationNode().getLineNumber() desc)
    //  v order by v.getDeclarationNode().getLineNumber())
  }

  int tryAsInt(){
    result = this.getDeclarationNode().(IntegerConstant).getValue()
    // or result = this.getDeclarationNode().(IntegerAddOpcode).
    //or
    //TODO: add all cases of operations that end up becoming integer constants
    //e.g. a btoi of a byte constant
  }

  override string toString(){result = this.getIdentifier()}
}

class DirectPhi extends Definition instanceof TDirectPhi{
  int initialStackIndex;
  BasicBlock bb;

  DirectPhi(){
    exists(SSAVar v | v.reachesEndOfOriginBB()
      and bb = v.getBasicBlock().getASuccessor() 
      and v.reaches(bb.getFirstNode().getAstNode())
      and
      initialStackIndex = v.outStackOrder() and
      this = TDirectPhi(initialStackIndex, bb)
      )
  }

  int getInitialStackIndex(){result = initialStackIndex}

  BasicBlock getBasicBlock(){result = bb}

  override int getOrd(){result = this.getInitialStackIndex()}

  // IndirectPhi getInput(){
  //   result.getBasicBlock() = bb.getAPredecessor() and
  //   this = phiNodeExitIndex(result, result.getBasicBlock())
  // }

  SSAVar getOriginatingInput(){
    result.getBasicBlock() = bb.getAPredecessor() and
    this.getInitialStackIndex() = result.outStackOrder()
  }

  override Location getLocation(){result = bb.getFirstNode().getLocation()}

  override string toString(){
    result = "phi_" + bb.getFirstNode() + "_" + this.getInitialStackIndex()
  }

  AstNode getConsumedBy(){
    result = phiNodeGetsConsumedBy(initialStackIndex, bb)
  }

  // override Location getLocation(){result = this.getBasicBlock().getLocation()}
}

// DirectPhi getStackInput_DP(int stackOrder, BasicBlock bb){
//   result.getBasicBlock().getASuccessor() = bb and
//   stackOrder = phiNodeExitIndex(result.getInitialStackIndex(), result.getBasicBlock())
// }

// IndirectPhi getStackInput_IP(int stackOrder, BasicBlock bb){
//   result.getBasicBlock().getASuccessor() = bb and
//   stackOrder = phiNodeExitIndex(result, result.getBasicBlock())
// }

// SSAVar getStackInput_Var(int stackOrder, BasicBlock bb){
//   result.getBasicBlock().getASuccessor() = bb and
//   stackOrder = result.outStackOrder()
// }

SSAVar getGenerator(Definition def){
  def instanceof DirectPhi and result = def.(DirectPhi).getOriginatingInput()
  or def instanceof IndirectPhi and result = getGenerator(def.(IndirectPhi).getGenerator()) 
  or def instanceof SSAWriteDef and result.toDef() = def
}


class IndirectPhi extends Definition instanceof TIndirectPhi{
  int initialStackIndex;
  BasicBlock bb;

  IndirectPhi(){
    exists(DirectPhi phi | initialStackIndex = phiNodeExitIndex(phi.getInitialStackIndex(), phi.getBasicBlock())
      and bb = phi.getBasicBlock().getASuccessor()

      //testing
      and any(phi.getOriginatingInput()).reaches(bb.getFirstNode().getAstNode())

      and this = TIndirectPhi(initialStackIndex, bb)
      // and this = "IPhi_" + bb.getFirstNode().getAstNode() + "_" + initialStackIndex.toString() + "D"
      // and generator = phi
      ) 
      or 
      // not exists(DirectPhi phi | initialStackIndex = phiNodeExitIndex(phi.getInitialStackIndex(), phi.getBasicBlock())
      // and bb = phi.getBasicBlock().getASuccessor()) and
    exists(IndirectPhi phi | phi.getBasicBlock().getASuccessor() = bb and 
        initialStackIndex = phiNodeExitIndex(phi.getInitialStackIndex(), phi.getBasicBlock())
        
        //testing
        and exists(DirectPhi d_phi | d_phi = phi.getGenerator() and d_phi.getOriginatingInput().reaches(bb.getFirstNode().getAstNode())) 
        // and exists(phi.getGenerator()) 

        and this = TIndirectPhi(initialStackIndex, bb)
    )
  }

  BasicBlock getBasicBlock(){result = bb}

  override int getOrd(){result = this.getInitialStackIndex()}

  int getInitialStackIndex(){result = initialStackIndex}

  DirectPhi getGenerator(){
    exists(DirectPhi phi | this.getInitialStackIndex() = phiNodeExitIndex(phi.getInitialStackIndex(), phi.getBasicBlock())
      and bb = phi.getBasicBlock().getASuccessor() and result = phi) or
    exists(IndirectPhi phi | phi.getBasicBlock().getASuccessor() = bb and 
      this.getInitialStackIndex() = phiNodeExitIndex(phi.getInitialStackIndex(), phi.getBasicBlock()) 
      and result = phi.getGenerator())
  }

  override string toString(){
    result = "phi_" + bb.getFirstNode() + "_" + this.getInitialStackIndex()
  }

  AstNode getConsumedBy(){
    result = phiNodeGetsConsumedBy(initialStackIndex, bb)
  }

  override Location getLocation(){result = this.getBasicBlock().getLocation()}
}




// This function does the following calculation:
// given a hypothetical phi node at the start of a basic block,
// it tells me which nodes would be consumed and if so by which opcodes
cached
AstNode phiNodeGetsConsumedBy(int hypotheticalPhiIndex, BasicBlock b){
  hypotheticalPhiIndex in [1 .. 1000] and
    result = rank[1](AstNode end|
        end = b.getANode().getAstNode() and
        hypotheticalPhiIndex + getPartialStackSizeBeforeOutput(end.getBasicBlock().getFirstNode().getAstNode(), end) <= 0
        | end order by end.getLineNumber()
    )
}

cached
int phiNodeExitIndex(int hypotheticalPhiNodeExitIndex, BasicBlock b){
  hypotheticalPhiNodeExitIndex in [1 .. 1000] and
  not exists(phiNodeGetsConsumedBy(hypotheticalPhiNodeExitIndex, b)) and
  result = max(SSAVar v | v.getBasicBlock() = b | v.outStackOrder()) +
  hypotheticalPhiNodeExitIndex - count(int h | exists(phiNodeGetsConsumedBy(h, b)) and 
    h in [1 .. hypotheticalPhiNodeExitIndex])
}

// cached
// AstNode writeDefGetsConsumedBy(int writeDefInternalIndex, AstNode defNode, BasicBlock b){
//   writeDefInternalIndex in [1 .. defNode.getNumberOfOutputArgs()] and
//     result = rank[1](AstNode end|
//         end = b.getANode().getAstNode() and end.getLineNumber() > defNode.getLineNumber() and
//         writeDefInternalIndex + getPartialStackSizeBeforeOutput(defNode.getNextLine(), end) <= 0
//         | end order by end.getLineNumber()
//     )
// }