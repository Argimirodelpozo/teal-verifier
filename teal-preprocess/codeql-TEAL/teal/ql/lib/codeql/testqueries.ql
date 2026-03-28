// To create db, from root folder do:
// codeql database create --overwrite --search-path codeql/teal/extractor-pack -l teal test-projects/db1 -s test-projects/

private import codeql.teal.ast.internal.TreeSitter
private import codeql.teal.ast.AST
private import codeql.teal.SSA.SSA
private import codeql.teal.cfg.BasicBlocks
private import codeql.teal.cfg.CFG::CfgImpl
private import codeql.teal.cfg.CFG
private import codeql.teal.ast.InnerTransactions
private import codeql.teal.dataflow.Dataflow

private import codeql.teal.ast.Transaction
// private import codeql.teal.ast.IntegerConstants


//given an err statement, trace the values that make it happen


// from Definition def
// select def, getGenerator(def)

// from AstNode n
// select n.getLineNumber(), n, n.getNumberOfConsumedArgs(), n.getNumberOfOutputArgs()

// from Dataflow::OpcodeNode op, Dataflow::OpcodeNode n
// // where n instanceof TOpcode_len
// where op.getCfgNode().getAstNode().(TxnaOpcode).getField() = "ApplicationArgs" and 
// LocalFlow::localFlow(op, n)
// // select n, n.getConsumedVars()
// select op.getCfgNode().getAstNode(), n.getCfgNode().getAstNode()





// from SSAWriteDef def
// select def.getRHS().getLineNumber(), def.getVar(), def.getRHS()

// from Definition def, AstNode n, SSAVar orig
// where 
//     n.getConsumedValues() = def and(
//         def instanceof DirectPhi and orig=def.(DirectPhi).getOriginatingInput()
//         or
//         def instanceof IndirectPhi and orig=def.(IndirectPhi).getGenerator().getOriginatingInput()
//     )
// select def.getLocation(), def.getOrd(), n, def, orig


// from Definition def1, Definition def2, AstNode op
// where LocalFlow::defSSAFlowThroughOp(def1, op, def2)
// select def1, def2, op, op.getStackOrderByDef(def1), def2.(SSAWriteDef).getVar().getInternalOutputIndex(),

// from Definition def1, AstNode op, AstNode n
// where
// def1 = rank[1](SSAVar v | op = n.getConsumedBy(v) |
//             v.toDef() order by ((op.getLineNumber() - n.getLineNumber())*10 + v.getInternalOutputIndex()) 
//         )
// select n, op, def1

// from AstNode n, int h
// select n, h, n.getStackInputByOrder(h)


// class TComparison = TOpcode_eq or TOpcode_lte or TOpcode_lt;

// AstNode lengthExtraction(StackVar var){
//     result instanceof TOpcode_len and 
//     exists(Dataflow::Node src, Dataflow::Node sink | 
//         src.(Dataflow::SsaDefinitionNode).asDefinition().(SSAWriteDef).getVar() = var
//         and sink.getUnderlyingASTNode() = result and
//         LocalFlow::localFlow(src, sink)
//     )
// }

// predicate lengthCheckForVar(StackVar var, AssertOpcode assertion, AstNode comp){
//     comp instanceof TComparison and
//     assertion.getConsumedValues().(SSAWriteDef).getRHS() = comp
//     and
//     comp.getConsumedValues() = var.toDef() and
//     exists(StackVar v | v != var and
//         comp.getConsumedValues() = v.toDef()
//         and exists(v.tryCastToInt()) and 
//         count(comp.getConsumedValues()) = 2
//     )
// }


// from Dataflow::Node op, Dataflow::Node n
// where op.getUnderlyingASTNode().(TxnaOpcode).getField() = "ApplicationArgs" and
// op != n and LocalFlow::localFlow(op, n)
// select op.getUnderlyingASTNode().getLineNumber()*1000 + n.getUnderlyingASTNode().getLineNumber(), op.getUnderlyingASTNode().getFile(), op, n


// from StackVar v
// select v.getDeclarationNode().getLineNumber(), v, v.inferType()

from TOpcode_dup b, AstNode b1
where b1 = b
select b1, b1.getStackInputByOrder(_), b1.getStackInputByOrder(_).(DirectPhi).getOriginatingInput()

// from StackVar v
// where v.getDeclarationNode() instanceof TOpcode_uncover
//     // and v.getDeclarationNode().getLineNumber() = 88
//     // and v.getDeclarationNode().getLineNumber() = 83
//     and v.getDeclarationNode().getLineNumber() = 90
    
//       and v.getInternalOutputIndex() != v.getDeclarationNode().getNumberOfOutputArgs()
//       and v.getInternalOutputIndex() in [1 .. v.getDeclarationNode().getNumberOfOutputArgs()-1]
// select getGenerator(v.getDeclarationNode().getStackInputByOrder(
//         v.getDeclarationNode().getNumberOfConsumedArgs() - v.getInternalOutputIndex()
//       )),
//       v.getDeclarationNode().getStackInputByOrder(
//         v.getDeclarationNode().getNumberOfConsumedArgs() - v.getInternalOutputIndex()
//       ),
//       v.getDeclarationNode(),
//       v.getDeclarationNode().getNumberOfConsumedArgs() - v.getInternalOutputIndex(),
//       v.getDeclarationNode().getLineNumber()
      
//       ,
//       getGenerator(v.getDeclarationNode().getStackInputByOrder(
//         v.getDeclarationNode().getNumberOfConsumedArgs() - v.getInternalOutputIndex()
//       )).inferType()




// Is there global storage?

// Is global storage gated by app creation?

// Is there local storage?

// If there is, give me dominator blocks of their writes


// Are there any itxns to contracts?

// What is the highest number of application arguments used?