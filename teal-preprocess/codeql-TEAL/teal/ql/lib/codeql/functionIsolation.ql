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
private import codeql.teal.ast.BinaryComparison
private import codeql.teal.ast.RoutingHelpers
private import codeql.teal.ast.Transaction

// For some reason this is not what regular toString() from the Location class does
// so we had to redo it
string locationToString(Location loc) {
    exists(string filepath, int startline, int startcolumn, int endline, int endcolumn |
      loc.hasLocationInfo(filepath, startline, startcolumn, endline, endcolumn) and
      result = filepath + "@" + startline + ":" + startcolumn + ":" + endline + ":" + endcolumn
    )
  }

from Method method
select method, method.printClassName() as type, method.getName() as name, locationToString(method.getLocation()) as location


//TODO: last page has a method that is both ABI and subroutine
// it is called vote
// this should NOT happen like this (even tho it is possible to callsub ABI methods)
// so the criteria por subroutines should be "...and they are not an ABI method"
// HOWEVER, we need to check b.c. it seems like a bug in dataflow
// ApplicationArgs 0 should NOT be flowing into vote