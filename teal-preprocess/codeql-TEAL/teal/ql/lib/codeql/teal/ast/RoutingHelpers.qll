private import codeql.teal.ast.AST
private import codeql.teal.ast.internal.TreeSitter
private import codeql.teal.ast.Transaction
private import codeql.teal.dataflow.Dataflow


BasicBlock bareMethodEntryBlock(){
    exists(AstNode n, AstNode txn | txn.(TxnOpcode).getField() = "NumAppArgs" and
        (
            n.(BnzOpcode).getConsumedVars() = txn.getOutputVar(_) and 
            result = n.(BnzOpcode).getNextNode(false).getBasicBlock()
            or
            n.(BzOpcode).getConsumedVars() = txn.getOutputVar(_) and 
            result = n.(BzOpcode).getNextNode(true).getBasicBlock()
        )
    )
    // in this case, a bare method is "implicit"
    // TODO: we may go through a path that does not use
    // any Application Args, and therefore is
    // implicitly any amount of args (including 0)
    or not exists(TxnOpcode txn | txn.getField() = "NumAppArgs")
}

BasicBlock abiMethodEntryBlock(){
    exists(
        TxnaOpcode appArgsRead_0, Dataflow::Node src, Dataflow::Node m | 
        appArgsRead_0.getField() = "ApplicationArgs" and
        appArgsRead_0.getIndex() = 0 and
        src.getUnderlyingASTNode() = appArgsRead_0 
        and
        LocalFlow::localFlow(src, m) and (
        result = m.getUnderlyingASTNode().(MatchOpcode).getTargetLabels().getBasicBlock()
        )
    )
    // and result = 
}

BasicBlock subroutineEntryBlock(){
    exists(
        CallsubOpcode call | 
        call.getTargetLabel() = result.getFirstNode().getAstNode().(Label)
    )
}


//TODO: direct comparison with zero (== 0), indirect comparison with zero
// (== 0 & others)
BasicBlock initEntryBlock(){
    exists(AstNode n, AstNode txn | txn.(TxnOpcode).getField() = "ApplicationID" and
        (
            n.(BnzOpcode).getConsumedVars() = txn.getOutputVar(_) and 
            result = n.(BnzOpcode).getNextNode(false).getBasicBlock()
            or
            n.(BzOpcode).getConsumedVars() = txn.getOutputVar(_) and 
            result = n.(BzOpcode).getNextNode(true).getBasicBlock()
        )
    )
}


class Method extends BasicBlock{
    string getName(){
        result = this.getFirstNode().getAstNode().(Label).getName()
    }

    BasicBlock getAllFunctionBlocks(){
        this.reaches(result)
    }

    abstract string printClassName();

    //number of arguments
    abstract int getNumParameters();
    abstract int getNumReturns();

    //type of arguments
    // TODO
}


class AbiMethod extends Method{
    
    AbiMethod(){
        this = abiMethodEntryBlock()
    }

    override string printClassName(){result = "ABI external method"}

    override int getNumParameters(){
        result = 0
    }

    override int getNumReturns(){
        result = 0
    }

    //TODO: is this correct? Basically:
    // we look for consumed vars that are not generated inside the function
    // this means, the consumed vars are generated from OUTSIDE
    // then, we may assume they are parameters
    // this analysis gets complicated with frame_dig and frame_bury, which
    // we are not considering (yet) but also give away parameters
    AstNode getTopOfStackEntryVars(){
        result = this.getAllFunctionBlocks().getANode().getAstNode().getConsumedVars() and
        not exists(
            AstNode n | this.getAllFunctionBlocks().getANode().getAstNode() = n and 
            n.getAnOutputVar() = result
        )
    }
}

class SubroutineMethod extends Method{

    SubroutineMethod(){
        this = subroutineEntryBlock() 
        // and this != any(AbiMethod m) //is this necessary?
    }

    override string printClassName(){result = "Subroutine"}

    //TODO: proto opcode class
    //TODO: If there is no Proto opcode, maybe we can do something like:
    //  -for entry label, give me stack variables
    //  -for stack variables, give me subset of variables that are/may be used anywhere in the function
    //      this is the number of parameters.
    //  -if type is certain, we got the signature. If type is uncertain, let me know with some kind of marker
    //
    // in abi methods this should be easier, as it's only txn args we need to care about
    // Note that this will give us only bytearray or uint64 arg types.
    //      deeper inference is needed in order to express more complex types, aggregates, biguint, etc.
    //      but for now this will do, and for "decompilation" sake we can always try and infer those things upstream.
    override int getNumParameters(){
        result = toTreeSitter(this.getNode(1).getAstNode().(TOpcode_proto)).(Teal::DoubleNumericArgumentOpcode).getValue1().toString().toInt()
    }

    override int getNumReturns(){
        result = toTreeSitter(this.getNode(1).getAstNode().(TOpcode_proto)).(Teal::DoubleNumericArgumentOpcode).getValue2().toString().toInt()
    }
}

class InitMethod extends Method{

    InitMethod(){
        this = initEntryBlock()
    }

    override string printClassName(){result = "Initialisation method"}

    override int getNumParameters(){
        result = 0
    }

    override int getNumReturns(){
        result = 0
    }
}

class BareMethod extends Method{
    BareMethod(){
        this = bareMethodEntryBlock()
    }

    override string printClassName(){result = "Bare method"}

    override int getNumParameters(){
        result = 0
    }

    override int getNumReturns(){
        result = 0
    }
}