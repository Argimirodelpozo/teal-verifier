/**
 * CodeQL library for Teal
 * Automatically generated from the tree-sitter grammar; do not edit
 */

import codeql.Locations as L

module Teal {
  /** The base class for all AST nodes */
  class AstNode extends @teal_ast_node {
    /** Gets a string representation of this element. */
    string toString() { result = this.getAPrimaryQlClass() }

    /** Gets the location of this element. */
    final L::Location getLocation() { teal_ast_node_location(this, result) }

    /** Gets the parent of this element. */
    final AstNode getParent() { teal_ast_node_parent(this, result, _) }

    /** Gets the index of this node among the children of its parent. */
    final int getParentIndex() { teal_ast_node_parent(this, _, result) }

    /** Gets a field or child node of this node. */
    AstNode getAFieldOrChild() { none() }

    /** Gets the name of the primary QL class for this element. */
    string getAPrimaryQlClass() { result = "???" }

    /** Gets a comma-separated list of the names of the primary CodeQL classes to which this element belongs. */
    string getPrimaryQlClasses() { result = concat(this.getAPrimaryQlClass(), ",") }
  }

  /** A token. */
  class Token extends @teal_token, AstNode {
    /** Gets the value of this token. */
    final string getValue() { teal_tokeninfo(this, _, result) }

    /** Gets a string representation of this element. */
    final override string toString() { result = this.getValue() }

    /** Gets the name of the primary QL class for this element. */
    override string getAPrimaryQlClass() { result = "Token" }
  }

  /** A reserved word. */
  class ReservedWord extends @teal_reserved_word, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "ReservedWord" }
  }

  /** A class representing `acct_params_get_opcode` tokens. */
  class AcctParamsGetOpcode extends @teal_token_acct_params_get_opcode, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "AcctParamsGetOpcode" }
  }

  /** A class representing `app_params_get_opcode` tokens. */
  class AppParamsGetOpcode extends @teal_token_app_params_get_opcode, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "AppParamsGetOpcode" }
  }

  /** A class representing `asset_holding_get_opcode` tokens. */
  class AssetHoldingGetOpcode extends @teal_token_asset_holding_get_opcode, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "AssetHoldingGetOpcode" }
  }

  /** A class representing `asset_params_get_opcode` tokens. */
  class AssetParamsGetOpcode extends @teal_token_asset_params_get_opcode, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "AssetParamsGetOpcode" }
  }

  /** A class representing `b_opcode` nodes. */
  class BOpcode extends @teal_b_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "BOpcode" }

    /** Gets the child of this node. */
    final LabelIdentifier getChild() { teal_b_opcode_def(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { teal_b_opcode_def(this, result) }
  }

  /** A class representing `base64_decode_opcode` tokens. */
  class Base64DecodeOpcode extends @teal_token_base64_decode_opcode, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "Base64DecodeOpcode" }
  }

  /** A class representing `block_opcode` nodes. */
  class BlockOpcode extends @teal_block_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "BlockOpcode" }

    /** Gets the node corresponding to the field `block_field`. */
    final string getBlockField() {
      exists(int value | teal_block_opcode_def(this, value) |
        result = "BlkBonus" and value = 0
        or
        result = "BlkBranch" and value = 1
        or
        result = "BlkFeeSink" and value = 2
        or
        result = "BlkFeesCollected" and value = 3
        or
        result = "BlkProposer" and value = 4
        or
        result = "BlkProposerPayout" and value = 5
        or
        result = "BlkProtocol" and value = 6
        or
        result = "BlkSeed" and value = 7
        or
        result = "BlkTimestamp" and value = 8
        or
        result = "BlkTxnCounter" and value = 9
      )
    }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { none() }
  }

  /** A class representing `bnz_opcode` nodes. */
  class BnzOpcode extends @teal_bnz_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "BnzOpcode" }

    /** Gets the child of this node. */
    final LabelIdentifier getChild() { teal_bnz_opcode_def(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { teal_bnz_opcode_def(this, result) }
  }

  /** A class representing `bytecblock_opcode` nodes. */
  class BytecblockOpcode extends @teal_bytecblock_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "BytecblockOpcode" }

    /** Gets the `i`th child of this node. */
    final AstNode getChild(int i) { teal_bytecblock_opcode_child(this, i, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { teal_bytecblock_opcode_child(this, _, result) }
  }

  /** A class representing `bz_opcode` nodes. */
  class BzOpcode extends @teal_bz_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "BzOpcode" }

    /** Gets the child of this node. */
    final LabelIdentifier getChild() { teal_bz_opcode_def(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { teal_bz_opcode_def(this, result) }
  }

  /** A class representing `callsub_opcode` nodes. */
  class CallsubOpcode extends @teal_callsub_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "CallsubOpcode" }

    /** Gets the child of this node. */
    final LabelIdentifier getChild() { teal_callsub_opcode_def(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { teal_callsub_opcode_def(this, result) }
  }

  /** A class representing `comment` tokens. */
  class Comment extends @teal_token_comment, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "Comment" }
  }

  /** A class representing `double_numeric_argument_opcode` nodes. */
  class DoubleNumericArgumentOpcode extends @teal_double_numeric_argument_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "DoubleNumericArgumentOpcode" }

    /** Gets the node corresponding to the field `op`. */
    final string getOp() {
      exists(int value | teal_double_numeric_argument_opcode_def(this, value, _, _) |
        result = "extract" and value = 0
        or
        result = "gload" and value = 1
        or
        result = "proto" and value = 2
        or
        result = "substring" and value = 3
      )
    }

    /** Gets the node corresponding to the field `value_1`. */
    final NumericArgument getValue1() {
      teal_double_numeric_argument_opcode_def(this, _, result, _)
    }

    /** Gets the node corresponding to the field `value_2`. */
    final NumericArgument getValue2() {
      teal_double_numeric_argument_opcode_def(this, _, _, result)
    }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      teal_double_numeric_argument_opcode_def(this, _, result, _) or
      teal_double_numeric_argument_opcode_def(this, _, _, result)
    }
  }

  /** A class representing `ec_opcode` nodes. */
  class EcOpcode extends @teal_ec_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "EcOpcode" }

    /** Gets the node corresponding to the field `op`. */
    final string getOp() {
      exists(int value | teal_ec_opcode_def(this, value) |
        result = "ec_add" and value = 0
        or
        result = "ec_map_to" and value = 1
        or
        result = "ec_multi_scalar_mul" and value = 2
        or
        result = "ec_pairing_check" and value = 3
        or
        result = "ec_scalar_mul" and value = 4
        or
        result = "ec_subgroup_check" and value = 5
      )
    }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { none() }
  }

  /** A class representing `ecdsa_opcode` nodes. */
  class EcdsaOpcode extends @teal_ecdsa_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "EcdsaOpcode" }

    /** Gets the node corresponding to the field `op`. */
    final string getOp() {
      exists(int value | teal_ecdsa_opcode_def(this, value) |
        result = "ecdsa_pk_decompress" and value = 0
        or
        result = "ecdsa_pk_recover" and value = 1
        or
        result = "ecdsa_verify" and value = 2
      )
    }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { none() }
  }

  /** A class representing `gitxn_opcode` nodes. */
  class GitxnOpcode extends @teal_gitxn_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "GitxnOpcode" }

    /** Gets the node corresponding to the field `txn_field`. */
    final string getTxnField() {
      exists(int value | teal_gitxn_opcode_def(this, value, _) |
        result = "Amount" and value = 0
        or
        result = "ApplicationID" and value = 1
        or
        result = "ApprovalProgram" and value = 2
        or
        result = "AssetAmount" and value = 3
        or
        result = "AssetCloseTo" and value = 4
        or
        result = "AssetReceiver" and value = 5
        or
        result = "AssetSender" and value = 6
        or
        result = "ClearStateProgram" and value = 7
        or
        result = "CloseRemainderTo" and value = 8
        or
        result = "ConfigAsset" and value = 9
        or
        result = "ConfigAssetClawback" and value = 10
        or
        result = "ConfigAssetDecimals" and value = 11
        or
        result = "ConfigAssetDefaultFrozen" and value = 12
        or
        result = "ConfigAssetFreeze" and value = 13
        or
        result = "ConfigAssetManager" and value = 14
        or
        result = "ConfigAssetMetadataHash" and value = 15
        or
        result = "ConfigAssetName" and value = 16
        or
        result = "ConfigAssetReserve" and value = 17
        or
        result = "ConfigAssetTotal" and value = 18
        or
        result = "ConfigAssetURL" and value = 19
        or
        result = "ConfigAssetUnitName" and value = 20
        or
        result = "CreatedApplicationID" and value = 21
        or
        result = "CreatedAssetID" and value = 22
        or
        result = "ExtraProgramPages" and value = 23
        or
        result = "Fee" and value = 24
        or
        result = "FirstValid" and value = 25
        or
        result = "FirstValidTime" and value = 26
        or
        result = "FreezeAsset" and value = 27
        or
        result = "FreezeAssetAccount" and value = 28
        or
        result = "FreezeAssetFrozen" and value = 29
        or
        result = "GlobalNumByteSlice" and value = 30
        or
        result = "GlobalNumUint" and value = 31
        or
        result = "GroupIndex" and value = 32
        or
        result = "LastLog" and value = 33
        or
        result = "LastValid" and value = 34
        or
        result = "Lease" and value = 35
        or
        result = "LocalNumByteSlice" and value = 36
        or
        result = "LocalNumUint" and value = 37
        or
        result = "Nonparticipation" and value = 38
        or
        result = "Note" and value = 39
        or
        result = "NumAccounts" and value = 40
        or
        result = "NumAppArgs" and value = 41
        or
        result = "NumApplications" and value = 42
        or
        result = "NumApprovalProgramPages" and value = 43
        or
        result = "NumAssets" and value = 44
        or
        result = "NumClearStateProgramPages" and value = 45
        or
        result = "NumLogs" and value = 46
        or
        result = "OnCompletion" and value = 47
        or
        result = "Receiver" and value = 48
        or
        result = "RekeyTo" and value = 49
        or
        result = "SelectionPK" and value = 50
        or
        result = "Sender" and value = 51
        or
        result = "StateProofPK" and value = 52
        or
        result = "TxID" and value = 53
        or
        result = "Type" and value = 54
        or
        result = "TypeEnum" and value = 55
        or
        result = "VoteFirst" and value = 56
        or
        result = "VoteKeyDilution" and value = 57
        or
        result = "VoteLast" and value = 58
        or
        result = "VotePK" and value = 59
        or
        result = "XferAsset" and value = 60
      )
    }

    /** Gets the node corresponding to the field `txn_group_index`. */
    final NumericArgument getTxnGroupIndex() { teal_gitxn_opcode_def(this, _, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { teal_gitxn_opcode_def(this, _, result) }
  }

  /** A class representing `gitxna_opcode` nodes. */
  class GitxnaOpcode extends @teal_gitxna_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "GitxnaOpcode" }

    /** Gets the node corresponding to the field `array_index`. */
    final NumericArgument getArrayIndex() { teal_gitxna_opcode_def(this, result, _, _) }

    /** Gets the node corresponding to the field `txn_array_field`. */
    final string getTxnArrayField() {
      exists(int value | teal_gitxna_opcode_def(this, _, value, _) |
        result = "Accounts" and value = 0
        or
        result = "ApplicationArgs" and value = 1
        or
        result = "Applications" and value = 2
        or
        result = "ApprovalProgramPages" and value = 3
        or
        result = "Assets" and value = 4
        or
        result = "ClearStateProgramPages" and value = 5
        or
        result = "Logs" and value = 6
      )
    }

    /** Gets the node corresponding to the field `txn_group_index`. */
    final NumericArgument getTxnGroupIndex() { teal_gitxna_opcode_def(this, _, _, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      teal_gitxna_opcode_def(this, result, _, _) or teal_gitxna_opcode_def(this, _, _, result)
    }
  }

  /** A class representing `gitxnas_opcode` nodes. */
  class GitxnasOpcode extends @teal_gitxnas_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "GitxnasOpcode" }

    /** Gets the node corresponding to the field `txn_array_field`. */
    final string getTxnArrayField() {
      exists(int value | teal_gitxnas_opcode_def(this, value, _) |
        result = "Accounts" and value = 0
        or
        result = "ApplicationArgs" and value = 1
        or
        result = "Applications" and value = 2
        or
        result = "ApprovalProgramPages" and value = 3
        or
        result = "Assets" and value = 4
        or
        result = "ClearStateProgramPages" and value = 5
        or
        result = "Logs" and value = 6
      )
    }

    /** Gets the node corresponding to the field `txn_group_index`. */
    final NumericArgument getTxnGroupIndex() { teal_gitxnas_opcode_def(this, _, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { teal_gitxnas_opcode_def(this, _, result) }
  }

  /** A class representing `global_opcode` nodes. */
  class GlobalOpcode extends @teal_global_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "GlobalOpcode" }

    /** Gets the node corresponding to the field `global_field`. */
    final string getGlobalField() {
      exists(int value | teal_global_opcode_def(this, value) |
        result = "AssetCreateMinBalance" and value = 0
        or
        result = "AssetOptInMinBalance" and value = 1
        or
        result = "CallerApplicationAddress" and value = 2
        or
        result = "CallerApplicationID" and value = 3
        or
        result = "CreatorAddress" and value = 4
        or
        result = "CurrentApplicationAddress" and value = 5
        or
        result = "CurrentApplicationID" and value = 6
        or
        result = "GenesisHash" and value = 7
        or
        result = "GroupID" and value = 8
        or
        result = "GroupSize" and value = 9
        or
        result = "LatestTimestamp" and value = 10
        or
        result = "LogicSigVersion" and value = 11
        or
        result = "MaxTxnLife" and value = 12
        or
        result = "MinBalance" and value = 13
        or
        result = "MinTxnFee" and value = 14
        or
        result = "OpcodeBudget" and value = 15
        or
        result = "PayoutsEnabled" and value = 16
        or
        result = "PayoutsGoOnlineFee" and value = 17
        or
        result = "PayoutsMaxBalance" and value = 18
        or
        result = "PayoutsMinBalance" and value = 19
        or
        result = "PayoutsPercent" and value = 20
        or
        result = "Round" and value = 21
        or
        result = "ZeroAddress" and value = 22
      )
    }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { none() }
  }

  /** A class representing `gtxn_opcode` nodes. */
  class GtxnOpcode extends @teal_gtxn_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "GtxnOpcode" }

    /** Gets the node corresponding to the field `index`. */
    final NumericArgument getIndex() { teal_gtxn_opcode_index(this, result) }

    /** Gets the node corresponding to the field `txn_array_field`. */
    final AstNode getTxnArrayField() { teal_gtxn_opcode_txn_array_field(this, result) }

    /** Gets the node corresponding to the field `txn_field`. */
    final AstNode getTxnField() { teal_gtxn_opcode_txn_field(this, result) }

    /** Gets the child of this node. */
    final NumericArgument getChild() { teal_gtxn_opcode_def(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      teal_gtxn_opcode_index(this, result) or
      teal_gtxn_opcode_txn_array_field(this, result) or
      teal_gtxn_opcode_txn_field(this, result) or
      teal_gtxn_opcode_def(this, result)
    }
  }

  /** A class representing `gtxna_opcode` nodes. */
  class GtxnaOpcode extends @teal_gtxna_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "GtxnaOpcode" }

    /** Gets the node corresponding to the field `index`. */
    final NumericArgument getIndex() { teal_gtxna_opcode_def(this, result, _, _) }

    /** Gets the node corresponding to the field `txn_array_field`. */
    final string getTxnArrayField() {
      exists(int value | teal_gtxna_opcode_def(this, _, value, _) |
        result = "Accounts" and value = 0
        or
        result = "ApplicationArgs" and value = 1
        or
        result = "Applications" and value = 2
        or
        result = "ApprovalProgramPages" and value = 3
        or
        result = "Assets" and value = 4
        or
        result = "ClearStateProgramPages" and value = 5
        or
        result = "Logs" and value = 6
      )
    }

    /** Gets the child of this node. */
    final NumericArgument getChild() { teal_gtxna_opcode_def(this, _, _, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      teal_gtxna_opcode_def(this, result, _, _) or teal_gtxna_opcode_def(this, _, _, result)
    }
  }

  /** A class representing `gtxnas_opcode` nodes. */
  class GtxnasOpcode extends @teal_gtxnas_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "GtxnasOpcode" }

    /** Gets the node corresponding to the field `txn_array_field`. */
    final string getTxnArrayField() {
      exists(int value | teal_gtxnas_opcode_def(this, value, _) |
        result = "Accounts" and value = 0
        or
        result = "ApplicationArgs" and value = 1
        or
        result = "Applications" and value = 2
        or
        result = "ApprovalProgramPages" and value = 3
        or
        result = "Assets" and value = 4
        or
        result = "ClearStateProgramPages" and value = 5
        or
        result = "Logs" and value = 6
      )
    }

    /** Gets the node corresponding to the field `txn_group_index`. */
    final NumericArgument getTxnGroupIndex() { teal_gtxnas_opcode_def(this, _, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { teal_gtxnas_opcode_def(this, _, result) }
  }

  /** A class representing `gtxns_opcode` nodes. */
  class GtxnsOpcode extends @teal_gtxns_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "GtxnsOpcode" }

    /** Gets the node corresponding to the field `index`. */
    final NumericArgument getIndex() { teal_gtxns_opcode_index(this, result) }

    /** Gets the node corresponding to the field `txn_array_field`. */
    final AstNode getTxnArrayField() { teal_gtxns_opcode_txn_array_field(this, result) }

    /** Gets the node corresponding to the field `txn_field`. */
    final AstNode getTxnField() { teal_gtxns_opcode_txn_field(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      teal_gtxns_opcode_index(this, result) or
      teal_gtxns_opcode_txn_array_field(this, result) or
      teal_gtxns_opcode_txn_field(this, result)
    }
  }

  /** A class representing `gtxnsa_opcode` nodes. */
  class GtxnsaOpcode extends @teal_gtxnsa_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "GtxnsaOpcode" }

    /** Gets the node corresponding to the field `index`. */
    final NumericArgument getIndex() { teal_gtxnsa_opcode_def(this, result, _) }

    /** Gets the node corresponding to the field `txn_array_field`. */
    final string getTxnArrayField() {
      exists(int value | teal_gtxnsa_opcode_def(this, _, value) |
        result = "Accounts" and value = 0
        or
        result = "ApplicationArgs" and value = 1
        or
        result = "Applications" and value = 2
        or
        result = "ApprovalProgramPages" and value = 3
        or
        result = "Assets" and value = 4
        or
        result = "ClearStateProgramPages" and value = 5
        or
        result = "Logs" and value = 6
      )
    }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { teal_gtxnsa_opcode_def(this, result, _) }
  }

  /** A class representing `gtxnsas_opcode` nodes. */
  class GtxnsasOpcode extends @teal_gtxnsas_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "GtxnsasOpcode" }

    /** Gets the node corresponding to the field `txn_array_field`. */
    final string getTxnArrayField() {
      exists(int value | teal_gtxnsas_opcode_def(this, value) |
        result = "Accounts" and value = 0
        or
        result = "ApplicationArgs" and value = 1
        or
        result = "Applications" and value = 2
        or
        result = "ApprovalProgramPages" and value = 3
        or
        result = "Assets" and value = 4
        or
        result = "ClearStateProgramPages" and value = 5
        or
        result = "Logs" and value = 6
      )
    }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { none() }
  }

  /** A class representing `hexbytes_argument` tokens. */
  class HexbytesArgument extends @teal_token_hexbytes_argument, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "HexbytesArgument" }
  }

  /** A class representing `intc_opcode` nodes. */
  class IntcOpcode extends @teal_intc_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "IntcOpcode" }

    /** Gets the node corresponding to the field `value`. */
    final NumericArgument getValue() { teal_intc_opcode_def(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { teal_intc_opcode_def(this, result) }
  }

  /** A class representing `intcblock_opcode` nodes. */
  class IntcblockOpcode extends @teal_intcblock_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "IntcblockOpcode" }

    /** Gets the node corresponding to the field `value`. */
    final NumericArgument getValue(int i) { teal_intcblock_opcode_value(this, i, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { teal_intcblock_opcode_value(this, _, result) }
  }

  /** A class representing `itxn_field_opcode` nodes. */
  class ItxnFieldOpcode extends @teal_itxn_field_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "ItxnFieldOpcode" }

    /** Gets the node corresponding to the field `txn_array_field`. */
    final AstNode getTxnArrayField() { teal_itxn_field_opcode_txn_array_field(this, result) }

    /** Gets the node corresponding to the field `txn_field`. */
    final AstNode getTxnField() { teal_itxn_field_opcode_txn_field(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      teal_itxn_field_opcode_txn_array_field(this, result) or
      teal_itxn_field_opcode_txn_field(this, result)
    }
  }

  /** A class representing `itxn_opcode` nodes. */
  class ItxnOpcode extends @teal_itxn_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "ItxnOpcode" }

    /** Gets the node corresponding to the field `txn_field`. */
    final string getTxnField() {
      exists(int value | teal_itxn_opcode_def(this, value) |
        result = "Amount" and value = 0
        or
        result = "ApplicationID" and value = 1
        or
        result = "ApprovalProgram" and value = 2
        or
        result = "AssetAmount" and value = 3
        or
        result = "AssetCloseTo" and value = 4
        or
        result = "AssetReceiver" and value = 5
        or
        result = "AssetSender" and value = 6
        or
        result = "ClearStateProgram" and value = 7
        or
        result = "CloseRemainderTo" and value = 8
        or
        result = "ConfigAsset" and value = 9
        or
        result = "ConfigAssetClawback" and value = 10
        or
        result = "ConfigAssetDecimals" and value = 11
        or
        result = "ConfigAssetDefaultFrozen" and value = 12
        or
        result = "ConfigAssetFreeze" and value = 13
        or
        result = "ConfigAssetManager" and value = 14
        or
        result = "ConfigAssetMetadataHash" and value = 15
        or
        result = "ConfigAssetName" and value = 16
        or
        result = "ConfigAssetReserve" and value = 17
        or
        result = "ConfigAssetTotal" and value = 18
        or
        result = "ConfigAssetURL" and value = 19
        or
        result = "ConfigAssetUnitName" and value = 20
        or
        result = "CreatedApplicationID" and value = 21
        or
        result = "CreatedAssetID" and value = 22
        or
        result = "ExtraProgramPages" and value = 23
        or
        result = "Fee" and value = 24
        or
        result = "FirstValid" and value = 25
        or
        result = "FirstValidTime" and value = 26
        or
        result = "FreezeAsset" and value = 27
        or
        result = "FreezeAssetAccount" and value = 28
        or
        result = "FreezeAssetFrozen" and value = 29
        or
        result = "GlobalNumByteSlice" and value = 30
        or
        result = "GlobalNumUint" and value = 31
        or
        result = "GroupIndex" and value = 32
        or
        result = "LastLog" and value = 33
        or
        result = "LastValid" and value = 34
        or
        result = "Lease" and value = 35
        or
        result = "LocalNumByteSlice" and value = 36
        or
        result = "LocalNumUint" and value = 37
        or
        result = "Nonparticipation" and value = 38
        or
        result = "Note" and value = 39
        or
        result = "NumAccounts" and value = 40
        or
        result = "NumAppArgs" and value = 41
        or
        result = "NumApplications" and value = 42
        or
        result = "NumApprovalProgramPages" and value = 43
        or
        result = "NumAssets" and value = 44
        or
        result = "NumClearStateProgramPages" and value = 45
        or
        result = "NumLogs" and value = 46
        or
        result = "OnCompletion" and value = 47
        or
        result = "Receiver" and value = 48
        or
        result = "RekeyTo" and value = 49
        or
        result = "SelectionPK" and value = 50
        or
        result = "Sender" and value = 51
        or
        result = "StateProofPK" and value = 52
        or
        result = "TxID" and value = 53
        or
        result = "Type" and value = 54
        or
        result = "TypeEnum" and value = 55
        or
        result = "VoteFirst" and value = 56
        or
        result = "VoteKeyDilution" and value = 57
        or
        result = "VoteLast" and value = 58
        or
        result = "VotePK" and value = 59
        or
        result = "XferAsset" and value = 60
      )
    }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { none() }
  }

  /** A class representing `itxna_opcode` nodes. */
  class ItxnaOpcode extends @teal_itxna_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "ItxnaOpcode" }

    /** Gets the node corresponding to the field `txn_array_field`. */
    final string getTxnArrayField() {
      exists(int value | teal_itxna_opcode_def(this, value) |
        result = "Accounts" and value = 0
        or
        result = "ApplicationArgs" and value = 1
        or
        result = "Applications" and value = 2
        or
        result = "ApprovalProgramPages" and value = 3
        or
        result = "Assets" and value = 4
        or
        result = "ClearStateProgramPages" and value = 5
        or
        result = "Logs" and value = 6
      )
    }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { none() }
  }

  /** A class representing `itxnas_opcode` nodes. */
  class ItxnasOpcode extends @teal_itxnas_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "ItxnasOpcode" }

    /** Gets the node corresponding to the field `txn_array_field`. */
    final string getTxnArrayField() {
      exists(int value | teal_itxnas_opcode_def(this, value) |
        result = "Accounts" and value = 0
        or
        result = "ApplicationArgs" and value = 1
        or
        result = "Applications" and value = 2
        or
        result = "ApprovalProgramPages" and value = 3
        or
        result = "Assets" and value = 4
        or
        result = "ClearStateProgramPages" and value = 5
        or
        result = "Logs" and value = 6
      )
    }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { none() }
  }

  /** A class representing `json_ref_opcode` tokens. */
  class JsonRefOpcode extends @teal_token_json_ref_opcode, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "JsonRefOpcode" }
  }

  /** A class representing `label` nodes. */
  class Label extends @teal_label, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "Label" }

    /** Gets the node corresponding to the field `name`. */
    final LabelIdentifier getName() { teal_label_def(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { teal_label_def(this, result) }
  }

  /** A class representing `label_identifier` tokens. */
  class LabelIdentifier extends @teal_token_label_identifier, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "LabelIdentifier" }
  }

  /** A class representing `load_opcode` nodes. */
  class LoadOpcode extends @teal_load_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "LoadOpcode" }

    /** Gets the node corresponding to the field `value`. */
    final NumericArgument getValue() { teal_load_opcode_def(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { teal_load_opcode_def(this, result) }
  }

  /** A class representing `match_opcode` nodes. */
  class MatchOpcode extends @teal_match_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "MatchOpcode" }

    /** Gets the `i`th child of this node. */
    final LabelIdentifier getChild(int i) { teal_match_opcode_child(this, i, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { teal_match_opcode_child(this, _, result) }
  }

  /** A class representing `mimc_opcode` tokens. */
  class MimcOpcode extends @teal_token_mimc_opcode, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "MimcOpcode" }
  }

  /** A class representing `numeric_argument` tokens. */
  class NumericArgument extends @teal_token_numeric_argument, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "NumericArgument" }
  }

  /** A class representing `pragma_typetrack` tokens. */
  class PragmaTypetrack extends @teal_token_pragma_typetrack, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "PragmaTypetrack" }
  }

  /** A class representing `pragma_version` tokens. */
  class PragmaVersion extends @teal_token_pragma_version, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "PragmaVersion" }
  }

  /** A class representing `pushbytes_opcode` nodes. */
  class PushbytesOpcode extends @teal_pushbytes_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "PushbytesOpcode" }

    /** Gets the node corresponding to the field `value`. */
    final AstNode getValue() { teal_pushbytes_opcode_def(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { teal_pushbytes_opcode_def(this, result) }
  }

  /** A class representing `pushbytess_opcode` nodes. */
  class PushbytessOpcode extends @teal_pushbytess_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "PushbytessOpcode" }

    /** Gets the `i`th child of this node. */
    final AstNode getChild(int i) { teal_pushbytess_opcode_child(this, i, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { teal_pushbytess_opcode_child(this, _, result) }
  }

  /** A class representing `pushints_opcode` nodes. */
  class PushintsOpcode extends @teal_pushints_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "PushintsOpcode" }

    /** Gets the node corresponding to the field `value`. */
    final NumericArgument getValue(int i) { teal_pushints_opcode_value(this, i, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { teal_pushints_opcode_value(this, _, result) }
  }

  /** A class representing `single_numeric_argument_opcode` nodes. */
  class SingleNumericArgumentOpcode extends @teal_single_numeric_argument_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "SingleNumericArgumentOpcode" }

    /** Gets the node corresponding to the field `op`. */
    final string getOp() {
      exists(int value | teal_single_numeric_argument_opcode_def(this, value, _) |
        result = "arg" and value = 0
        or
        result = "bury" and value = 1
        or
        result = "bytec" and value = 2
        or
        result = "cover" and value = 3
        or
        result = "dig" and value = 4
        or
        result = "dupn" and value = 5
        or
        result = "frame_bury" and value = 6
        or
        result = "frame_dig" and value = 7
        or
        result = "gloads" and value = 8
        or
        result = "int" and value = 9
        or
        result = "popn" and value = 10
        or
        result = "pushint" and value = 11
        or
        result = "replace2" and value = 12
        or
        result = "uncover" and value = 13
      )
    }

    /** Gets the node corresponding to the field `value`. */
    final NumericArgument getValue() { teal_single_numeric_argument_opcode_def(this, _, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      teal_single_numeric_argument_opcode_def(this, _, result)
    }
  }

  /** A class representing `source` nodes. */
  class Source extends @teal_source, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "Source" }

    /** Gets the `i`th child of this node. */
    final AstNode getChild(int i) { teal_source_child(this, i, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { teal_source_child(this, _, result) }
  }

  /** A class representing `store_opcode` nodes. */
  class StoreOpcode extends @teal_store_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "StoreOpcode" }

    /** Gets the node corresponding to the field `value`. */
    final NumericArgument getValue() { teal_store_opcode_def(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { teal_store_opcode_def(this, result) }
  }

  /** A class representing `string_argument` tokens. */
  class StringArgument extends @teal_token_string_argument, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "StringArgument" }
  }

  /** A class representing `switch_opcode` nodes. */
  class SwitchOpcode extends @teal_switch_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "SwitchOpcode" }

    /** Gets the `i`th child of this node. */
    final LabelIdentifier getChild(int i) { teal_switch_opcode_child(this, i, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { teal_switch_opcode_child(this, _, result) }
  }

  /** A class representing `txn_opcode` nodes. */
  class TxnOpcode extends @teal_txn_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "TxnOpcode" }

    /** Gets the node corresponding to the field `index`. */
    final NumericArgument getIndex() { teal_txn_opcode_index(this, result) }

    /** Gets the node corresponding to the field `txn_array_field`. */
    final AstNode getTxnArrayField() { teal_txn_opcode_txn_array_field(this, result) }

    /** Gets the node corresponding to the field `txn_field`. */
    final AstNode getTxnField() { teal_txn_opcode_txn_field(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      teal_txn_opcode_index(this, result) or
      teal_txn_opcode_txn_array_field(this, result) or
      teal_txn_opcode_txn_field(this, result)
    }
  }

  /** A class representing `txna_opcode` nodes. */
  class TxnaOpcode extends @teal_txna_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "TxnaOpcode" }

    /** Gets the node corresponding to the field `index`. */
    final NumericArgument getIndex() { teal_txna_opcode_def(this, result, _) }

    /** Gets the node corresponding to the field `txn_array_field`. */
    final string getTxnArrayField() {
      exists(int value | teal_txna_opcode_def(this, _, value) |
        result = "Accounts" and value = 0
        or
        result = "ApplicationArgs" and value = 1
        or
        result = "Applications" and value = 2
        or
        result = "ApprovalProgramPages" and value = 3
        or
        result = "Assets" and value = 4
        or
        result = "ClearStateProgramPages" and value = 5
        or
        result = "Logs" and value = 6
      )
    }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { teal_txna_opcode_def(this, result, _) }
  }

  /** A class representing `txnas_opcode` nodes. */
  class TxnasOpcode extends @teal_txnas_opcode, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "TxnasOpcode" }

    /** Gets the node corresponding to the field `txn_array_field`. */
    final string getTxnArrayField() {
      exists(int value | teal_txnas_opcode_def(this, value) |
        result = "Accounts" and value = 0
        or
        result = "ApplicationArgs" and value = 1
        or
        result = "Applications" and value = 2
        or
        result = "ApprovalProgramPages" and value = 3
        or
        result = "Assets" and value = 4
        or
        result = "ClearStateProgramPages" and value = 5
        or
        result = "Logs" and value = 6
      )
    }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { none() }
  }

  /** A class representing `voter_params_get_opcode` tokens. */
  class VoterParamsGetOpcode extends @teal_token_voter_params_get_opcode, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "VoterParamsGetOpcode" }
  }

  /** A class representing `vrf_verify_opcode` tokens. */
  class VrfVerifyOpcode extends @teal_token_vrf_verify_opcode, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "VrfVerifyOpcode" }
  }

  /** A class representing `zero_argument_opcode` tokens. */
  class ZeroArgumentOpcode extends @teal_token_zero_argument_opcode, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "ZeroArgumentOpcode" }
  }
}
