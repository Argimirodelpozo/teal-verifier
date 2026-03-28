/**
 * @name Scratch space inference report
 * @description Reports inferred types, bounds, values, and origins for scratch space store/load opcodes.
 * @id teal/scratch-space-report
 */

import codeql.teal.ast.AST
import codeql.teal.ast.ScratchSpaceInference
import codeql.teal.ast.opcodes.ScratchSpace

from
  AstNode n, string file, int line, int col, string opcode, int slot, string type, int lo, int hi,
  string value, string origin
where
  (
    exists(StoreOpcode store |
      store = n and
      scratchStoreInfo(store, slot, type, lo, hi, value, origin) and
      opcode = "store"
    )
    or
    exists(LoadOpcode load |
      load = n and
      scratchLoadInfo(load, slot, type, lo, hi, value, origin) and
      opcode = "load"
    )
  ) and
  file = n.getLocation().getFile().getRelativePath() and
  line = n.getLocation().getStartLine() and
  col = n.getLocation().getStartColumn()
select file, line, col, opcode, slot, type, lo, hi, value, origin
