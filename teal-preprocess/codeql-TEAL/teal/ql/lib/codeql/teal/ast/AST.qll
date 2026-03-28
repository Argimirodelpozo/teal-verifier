import codeql.Locations
private import codeql.teal.ast.internal.TreeSitter
private import codeql.teal.cfg.BasicBlocks
private import codeql.teal.SSA.SSA
private import codeql.teal.cfg.Completion::Completion
import codeql.teal.ast.Program
import codeql.teal.ast.opcodes.Arithmetic
import codeql.teal.ast.opcodes.ByteArithmetic
import codeql.teal.ast.opcodes.Comparison
import codeql.teal.ast.opcodes.ByteComparison
import codeql.teal.ast.opcodes.Logic
import codeql.teal.ast.opcodes.Hashing
import codeql.teal.ast.opcodes.Crypto
import codeql.teal.ast.opcodes.EllipticCurve
import codeql.teal.ast.opcodes.Constants
import codeql.teal.ast.opcodes.Transaction
import codeql.teal.ast.opcodes.GlobalState
import codeql.teal.ast.opcodes.InnerTransactions
import codeql.teal.ast.opcodes.ControlFlow
import codeql.teal.ast.opcodes.StackManipulation
import codeql.teal.ast.opcodes.ScratchSpace
import codeql.teal.ast.opcodes.ByteOps
import codeql.teal.ast.opcodes.BoxStorage
import codeql.teal.ast.opcodes.Logging
import codeql.teal.ast.opcodes.Misc

cached
newtype TAstNode = 
TSource(Teal::Source op) or TLabel(Teal::Label op) or
TOpcode_b(Teal::BOpcode op) or TOpcode_bz(Teal::BzOpcode op) or
TOpcode_bnz(Teal::BnzOpcode op) or TOpcode_callsub(Teal::CallsubOpcode op) or
TOpcode_switch(Teal::SwitchOpcode op) or TOpcode_match(Teal::MatchOpcode op) or
TOpcode_retsub(Teal::ZeroArgumentOpcode op){op.getValue() = "retsub"} or
TOpcode_sha256(Teal::ZeroArgumentOpcode op){op.getValue() = "sha256"} or
TOpcode_keccak256(Teal::ZeroArgumentOpcode op){op.getValue() = "keccak256"} or
TOpcode_sha512_256(Teal::ZeroArgumentOpcode op){op.getValue() = "sha512_256"} or
TOpcode_err(Teal::ZeroArgumentOpcode op){op.getValue() = "err"} or
TOpcode_ed25519verify(Teal::ZeroArgumentOpcode op){op.getValue() = "ed25519verify"} or
TOpcode_add(Teal::ZeroArgumentOpcode op){op.getValue() = "+"} or
TOpcode_sub(Teal::ZeroArgumentOpcode op){op.getValue() = "-"} or
TOpcode_mul(Teal::ZeroArgumentOpcode op){op.getValue() = "*"} or
TOpcode_div(Teal::ZeroArgumentOpcode op){op.getValue() = "/"} or
TOpcode_mod(Teal::ZeroArgumentOpcode op){op.getValue() = "%"} or
TOpcode_lt(Teal::ZeroArgumentOpcode op){op.getValue() = "<"} or
TOpcode_lte(Teal::ZeroArgumentOpcode op){op.getValue() = "<="} or
TOpcode_gt(Teal::ZeroArgumentOpcode op){op.getValue() = ">"} or
TOpcode_gte(Teal::ZeroArgumentOpcode op){op.getValue() = ">="} or
TOpcode_and(Teal::ZeroArgumentOpcode op){op.getValue() = "&&"} or
TOpcode_or(Teal::ZeroArgumentOpcode op){op.getValue() = "||"} or
TOpcode_eq(Teal::ZeroArgumentOpcode op){op.getValue() = "=="} or
TOpcode_neq(Teal::ZeroArgumentOpcode op){op.getValue() = "!="} or
TOpcode_not(Teal::ZeroArgumentOpcode op){op.getValue() = "!"} or
TOpcode_len(Teal::ZeroArgumentOpcode op){op.getValue() = "len"} or
TOpcode_itob(Teal::ZeroArgumentOpcode op){op.getValue() = "itob"} or
TOpcode_btoi(Teal::ZeroArgumentOpcode op){op.getValue() = "btoi"} or
TOpcode_bitand(Teal::ZeroArgumentOpcode op){op.getValue() = "&"} or
TOpcode_bitor(Teal::ZeroArgumentOpcode op){op.getValue() = "|"} or
TOpcode_bitxor(Teal::ZeroArgumentOpcode op){op.getValue() = "^"} or
TOpcode_bitnot(Teal::ZeroArgumentOpcode op){op.getValue() = "~"} or
TOpcode_mulw(Teal::ZeroArgumentOpcode op){op.getValue() = "mulw"} or
TOpcode_addw(Teal::ZeroArgumentOpcode op){op.getValue() = "addw"} or
TOpcode_divmodw(Teal::ZeroArgumentOpcode op){op.getValue() = "divmodw"} or
TOpcode_intc_0(Teal::ZeroArgumentOpcode op){op.getValue() = "intc_0"} or
TOpcode_intc_1(Teal::ZeroArgumentOpcode op){op.getValue() = "intc_1"} or
TOpcode_intc_2(Teal::ZeroArgumentOpcode op){op.getValue() = "intc_2"} or
TOpcode_intc_3(Teal::ZeroArgumentOpcode op){op.getValue() = "intc_3"} or
TOpcode_bytec_0(Teal::ZeroArgumentOpcode op){op.getValue() = "bytec_0"} or
TOpcode_bytec_1(Teal::ZeroArgumentOpcode op){op.getValue() = "bytec_1"} or
TOpcode_bytec_2(Teal::ZeroArgumentOpcode op){op.getValue() = "bytec_2"} or
TOpcode_bytec_3(Teal::ZeroArgumentOpcode op){op.getValue() = "bytec_3"} or
TOpcode_arg_0(Teal::ZeroArgumentOpcode op){op.getValue() = "arg_0"} or
TOpcode_arg_1(Teal::ZeroArgumentOpcode op){op.getValue() = "arg_1"} or
TOpcode_arg_2(Teal::ZeroArgumentOpcode op){op.getValue() = "arg_2"} or
TOpcode_arg_3(Teal::ZeroArgumentOpcode op){op.getValue() = "arg_3"} or
TOpcode_gaids(Teal::ZeroArgumentOpcode op){op.getValue() = "gaids"} or
TOpcode_loads(Teal::ZeroArgumentOpcode op){op.getValue() = "loads"} or
TOpcode_stores(Teal::ZeroArgumentOpcode op){op.getValue() = "stores"} or
TOpcode_return(Teal::ZeroArgumentOpcode op){op.getValue() = "return"} or
TOpcode_assert(Teal::ZeroArgumentOpcode op){op.getValue() = "assert"} or
TOpcode_pop(Teal::ZeroArgumentOpcode op){op.getValue() = "pop"} or
TOpcode_dup(Teal::ZeroArgumentOpcode op){op.getValue() = "dup"} or
TOpcode_dup2(Teal::ZeroArgumentOpcode op){op.getValue() = "dup2"} or
TOpcode_swap(Teal::ZeroArgumentOpcode op){op.getValue() = "swap"} or
TOpcode_select(Teal::ZeroArgumentOpcode op){op.getValue() = "select"} or
TOpcode_concat(Teal::ZeroArgumentOpcode op){op.getValue() = "concat"} or
TOpcode_substring3(Teal::ZeroArgumentOpcode op){op.getValue() = "substring3"} or
TOpcode_getbit(Teal::ZeroArgumentOpcode op){op.getValue() = "getbit"} or
TOpcode_setbit(Teal::ZeroArgumentOpcode op){op.getValue() = "setbit"} or
TOpcode_getbyte(Teal::ZeroArgumentOpcode op){op.getValue() = "getbyte"} or
TOpcode_setbyte(Teal::ZeroArgumentOpcode op){op.getValue() = "setbyte"} or
TOpcode_extract_uint16(Teal::ZeroArgumentOpcode op){op.getValue() = "extract_uint16"} or
TOpcode_extract_uint32(Teal::ZeroArgumentOpcode op){op.getValue() = "extract_uint32"} or
TOpcode_extract_uint64(Teal::ZeroArgumentOpcode op){op.getValue() = "extract_uint64"} or
TOpcode_replace3(Teal::ZeroArgumentOpcode op){op.getValue() = "replace3"} or
TOpcode_extract3(Teal::ZeroArgumentOpcode op){op.getValue() = "extract3"} or
TOpcode_balance(Teal::ZeroArgumentOpcode op){op.getValue() = "balance"} or
TOpcode_app_opted_in(Teal::ZeroArgumentOpcode op){op.getValue() = "app_opted_in"} or
TOpcode_app_local_get(Teal::ZeroArgumentOpcode op){op.getValue() = "app_local_get"} or
TOpcode_app_local_get_ex(Teal::ZeroArgumentOpcode op){op.getValue() = "app_local_get_ex"} or
TOpcode_app_global_get(Teal::ZeroArgumentOpcode op){op.getValue() = "app_global_get"} or
TOpcode_app_global_get_ex(Teal::ZeroArgumentOpcode op){op.getValue() = "app_global_get_ex"} or
TOpcode_app_local_put(Teal::ZeroArgumentOpcode op){op.getValue() = "app_local_put"} or
TOpcode_app_global_put(Teal::ZeroArgumentOpcode op){op.getValue() = "app_global_put"} or
TOpcode_app_local_del(Teal::ZeroArgumentOpcode op){op.getValue() = "app_local_del"} or
TOpcode_app_global_del(Teal::ZeroArgumentOpcode op){op.getValue() = "app_global_del"} or
TOpcode_online_stake(Teal::ZeroArgumentOpcode op){op.getValue() = "online_stake"} or
TOpcode_min_balance(Teal::ZeroArgumentOpcode op){op.getValue() = "min_balance"} or
TOpcode_ed25519verify_bare(Teal::ZeroArgumentOpcode op){op.getValue() = "ed25519verify_bare"} or
TOpcode_shl(Teal::ZeroArgumentOpcode op){op.getValue() = "shl"} or
TOpcode_shr(Teal::ZeroArgumentOpcode op){op.getValue() = "shr"} or
TOpcode_sqrt(Teal::ZeroArgumentOpcode op){op.getValue() = "sqrt"} or
TOpcode_bitlen(Teal::ZeroArgumentOpcode op){op.getValue() = "bitlen"} or
TOpcode_exp(Teal::ZeroArgumentOpcode op){op.getValue() = "exp"} or
TOpcode_expw(Teal::ZeroArgumentOpcode op){op.getValue() = "expw"} or
TOpcode_bsqrt(Teal::ZeroArgumentOpcode op){op.getValue() = "bsqrt"} or
TOpcode_divw(Teal::ZeroArgumentOpcode op){op.getValue() = "divw"} or
TOpcode_sha3_256(Teal::ZeroArgumentOpcode op){op.getValue() = "sha3_256"} or
TOpcode_badd(Teal::ZeroArgumentOpcode op){op.getValue() = "b+"} or
TOpcode_bsub(Teal::ZeroArgumentOpcode op){op.getValue() = "b-"} or
TOpcode_bdiv(Teal::ZeroArgumentOpcode op){op.getValue() = "b/"} or
TOpcode_bmul(Teal::ZeroArgumentOpcode op){op.getValue() = "b*"} or
TOpcode_blt(Teal::ZeroArgumentOpcode op){op.getValue() = "b<"} or
TOpcode_bgt(Teal::ZeroArgumentOpcode op){op.getValue() = "b>"} or
TOpcode_blte(Teal::ZeroArgumentOpcode op){op.getValue() = "b<="} or
TOpcode_bgte(Teal::ZeroArgumentOpcode op){op.getValue() = "b>="} or
TOpcode_beq(Teal::ZeroArgumentOpcode op){op.getValue() = "b=="} or
TOpcode_bneq(Teal::ZeroArgumentOpcode op){op.getValue() = "b!="} or
TOpcode_bmod(Teal::ZeroArgumentOpcode op){op.getValue() = "b%"} or
TOpcode_bor(Teal::ZeroArgumentOpcode op){op.getValue() = "b|"} or
TOpcode_band(Teal::ZeroArgumentOpcode op){op.getValue() = "b&"} or
TOpcode_bxor(Teal::ZeroArgumentOpcode op){op.getValue() = "b^"} or
TOpcode_bnot(Teal::ZeroArgumentOpcode op){op.getValue() = "b~"} or
TOpcode_bzero(Teal::ZeroArgumentOpcode op){op.getValue() = "bzero"} or
TOpcode_log(Teal::ZeroArgumentOpcode op){op.getValue() = "log"} or
TOpcode_itxn_begin(Teal::ZeroArgumentOpcode op){op.getValue() = "itxn_begin"} or
TOpcode_itxn_submit(Teal::ZeroArgumentOpcode op){op.getValue() = "itxn_submit"} or
TOpcode_itxn_next(Teal::ZeroArgumentOpcode op){op.getValue() = "itxn_next"} or
TOpcode_box_create(Teal::ZeroArgumentOpcode op){op.getValue() = "box_create"} or
TOpcode_box_extract(Teal::ZeroArgumentOpcode op){op.getValue() = "box_extract"} or
TOpcode_box_replace(Teal::ZeroArgumentOpcode op){op.getValue() = "box_replace"} or
TOpcode_box_del(Teal::ZeroArgumentOpcode op){op.getValue() = "box_del"} or
TOpcode_box_len(Teal::ZeroArgumentOpcode op){op.getValue() = "box_len"} or
TOpcode_box_get(Teal::ZeroArgumentOpcode op){op.getValue() = "box_get"} or
TOpcode_box_put(Teal::ZeroArgumentOpcode op){op.getValue() = "box_put"} or
TOpcode_args(Teal::ZeroArgumentOpcode op){op.getValue() = "args"} or
TOpcode_gloadss(Teal::ZeroArgumentOpcode op){op.getValue() = "gloadss"} or
TOpcode_box_splice(Teal::ZeroArgumentOpcode op){op.getValue() = "box_splice"} or
TOpcode_box_resize(Teal::ZeroArgumentOpcode op){op.getValue() = "box_resize"} or
TOpcode_intc(Teal::IntcOpcode op) or
TOpcode_bytec(Teal::SingleNumericArgumentOpcode op){op.getOp() = "bytec"} or
TOpcode_arg(Teal::SingleNumericArgumentOpcode op){op.getOp() = "arg"} or
TOpcode_load(Teal::LoadOpcode op) or
TOpcode_store(Teal::StoreOpcode op) or
TOpcode_gloads(Teal::SingleNumericArgumentOpcode op){op.getOp() = "gloads"} or
TOpcode_bury(Teal::SingleNumericArgumentOpcode op){op.getOp() = "bury"} or
TOpcode_popn(Teal::SingleNumericArgumentOpcode op){op.getOp() = "popn"} or
TOpcode_dupn(Teal::SingleNumericArgumentOpcode op){op.getOp() = "dupn"} or
TOpcode_dig(Teal::SingleNumericArgumentOpcode op){op.getOp() = "dig"} or
TOpcode_cover(Teal::SingleNumericArgumentOpcode op){op.getOp() = "cover"} or
TOpcode_uncover(Teal::SingleNumericArgumentOpcode op){op.getOp() = "uncover"} or
TOpcode_replace2(Teal::SingleNumericArgumentOpcode op){op.getOp() = "replace2"} or
TOpcode_pushint(Teal::SingleNumericArgumentOpcode op){op.getOp() = "pushint"} or
TOpcode_frame_dig(Teal::SingleNumericArgumentOpcode op){op.getOp() = "frame_dig"} or
TOpcode_frame_bury(Teal::SingleNumericArgumentOpcode op){op.getOp() = "frame_bury"} or
TOpcode_int(Teal::SingleNumericArgumentOpcode op){op.getOp() = "int"} or
TOpcode_acct_params_get(Teal::AcctParamsGetOpcode op) or
TOpcode_app_params_get(Teal::AppParamsGetOpcode op) or
TOpcode_asset_holding_get(Teal::AssetHoldingGetOpcode op) or
TOpcode_asset_params_get(Teal::AssetParamsGetOpcode op) or
TOpcode_base64_decode(Teal::Base64DecodeOpcode op) or
TOpcode_block(Teal::BlockOpcode op) or
TOpcode_bytecblock(Teal::BytecblockOpcode op) or
TOpcode_extract(Teal::DoubleNumericArgumentOpcode op){op.getOp() = "extract"} or
TOpcode_substring(Teal::DoubleNumericArgumentOpcode op){op.getOp() = "substring"} or
TOpcode_gload(Teal::DoubleNumericArgumentOpcode op){op.getOp() = "gload"} or
TOpcode_proto(Teal::DoubleNumericArgumentOpcode op){op.getOp() = "proto"} or
TOpcode_ec_add(Teal::EcOpcode op){op.getOp() = "ec_add"} or
TOpcode_ec_mul(Teal::EcOpcode op){op.getOp() = "ec_mul"} or //TODO: ERROR IN OPCODE! FIX. IT IS ec_scalar_mul
TOpcode_ec_pairing_check(Teal::EcOpcode op){op.getOp() = "ec_pairing_check"} or
TOpcode_ec_multi_scalar_mul(Teal::EcOpcode op){op.getOp() = "ec_multi_scalar_mul"} or
TOpcode_ec_subgroup_check(Teal::EcOpcode op){op.getOp() = "ec_subgroup_check"} or
TOpcode_ec_map_to(Teal::EcOpcode op){op.getOp() = "ec_map_to"} or
TOpcode_ecdsa_verify(Teal::EcdsaOpcode op){op.getOp() = "ecdsa_verify"} or
TOpcode_ecdsa_pk_decompress(Teal::EcdsaOpcode op){op.getOp() = "ecdsa_pk_decompress"} or
TOpcode_ecdsa_pk_recover(Teal::EcdsaOpcode op){op.getOp() = "ecdsa_pk_recover"} or
TOpcode_gaid(Teal::ZeroArgumentOpcode op){op.getValue() = "gaid"} or
TOpcode_gitxn(Teal::GitxnOpcode op) or
TOpcode_gitxna(Teal::GitxnaOpcode op) or
TOpcode_gitxnas(Teal::GitxnasOpcode op) or
TOpcode_global(Teal::GlobalOpcode op) or
TOpcode_gtxn(Teal::GtxnOpcode op) or
TOpcode_gtxna(Teal::GtxnaOpcode op) or
TOpcode_gtxnas(Teal::GtxnasOpcode op) or
TOpcode_gtxns(Teal::GtxnsOpcode op) or
TOpcode_gtxnsa(Teal::GtxnsaOpcode op) or
TOpcode_gtxnsas(Teal::GtxnsasOpcode op) or
TOpcode_intcblock(Teal::IntcblockOpcode op) or
TOpcode_itxn_field(Teal::ItxnFieldOpcode op) or
TOpcode_itxna(Teal::ItxnaOpcode op) or
TOpcode_itxnas(Teal::ItxnasOpcode op) or
TOpcode_itxn(Teal::ItxnOpcode op) or
TOpcode_json_ref(Teal::JsonRefOpcode op) or
TOpcode_mimc(Teal::MimcOpcode op) or
// TPragma(Teal::Pragma p)
TOpcode_pushbytes(Teal::PushbytesOpcode op) or
TOpcode_pushbytess(Teal::PushbytessOpcode op) or
TOpcode_pushints(Teal::PushintsOpcode op) or
TOpcode_txn(Teal::TxnOpcode op) or
TOpcode_txna(Teal::TxnaOpcode op) or
TOpcode_txnas(Teal::TxnasOpcode op) or
TOpcode_voter_params_get(Teal::VoterParamsGetOpcode op) or
TOpcode_vrf_verify(Teal::VrfVerifyOpcode op) 

Teal::AstNode toTreeSitter(TAstNode node){
    TSource(result) = node or
    TLabel(result) = node or
    TOpcode_b(result) = node or
    TOpcode_bz(result) = node or
    TOpcode_bnz(result) = node or
    TOpcode_callsub(result) = node or
    TOpcode_retsub(result) = node or
    TOpcode_sha256(result) = node or
    TOpcode_keccak256(result) = node or
    TOpcode_sha512_256(result) = node or
    TOpcode_err(result) = node or
    TOpcode_ed25519verify(result) = node or
    TOpcode_add(result) = node or
    TOpcode_sub(result) = node or
    TOpcode_mul(result) = node or
    TOpcode_div(result) = node or
    TOpcode_mod(result) = node or
    TOpcode_lt(result) = node or
    TOpcode_lte(result) = node or
    TOpcode_gt(result) = node or
    TOpcode_gte(result) = node or
    TOpcode_and(result) = node or
    TOpcode_or(result) = node or
    TOpcode_eq(result) = node or
    TOpcode_neq(result) = node or
    TOpcode_not(result) = node or
    TOpcode_len(result) = node or
    TOpcode_itob(result) = node or
    TOpcode_btoi(result) = node or
    TOpcode_bitand(result) = node or
    TOpcode_bitor(result) = node or
    TOpcode_bitxor(result) = node or
    TOpcode_bitnot(result) = node or
    TOpcode_mulw(result) = node or
    TOpcode_addw(result) = node or
    TOpcode_divmodw(result) = node or
    TOpcode_intc_0(result) = node or
    TOpcode_intc_1(result) = node or
    TOpcode_intc_2(result) = node or
    TOpcode_intc_3(result) = node or
    TOpcode_bytec_0(result) = node or
    TOpcode_bytec_1(result) = node or
    TOpcode_bytec_2(result) = node or
    TOpcode_bytec_3(result) = node or
    TOpcode_arg_0(result) = node or
    TOpcode_arg_1(result) = node or
    TOpcode_arg_2(result) = node or
    TOpcode_arg_3(result) = node or
    TOpcode_gaids(result) = node or
    TOpcode_loads(result) = node or
    TOpcode_stores(result) = node or
    TOpcode_return(result) = node or
    TOpcode_assert(result) = node or
    TOpcode_pop(result) = node or
    TOpcode_dup(result) = node or
    TOpcode_dup2(result) = node or
    TOpcode_swap(result) = node or
    TOpcode_select(result) = node or
    TOpcode_concat(result) = node or
    TOpcode_substring3(result) = node or
    TOpcode_getbit(result) = node or
    TOpcode_setbit(result) = node or
    TOpcode_getbyte(result) = node or
    TOpcode_setbyte(result) = node or
    TOpcode_extract_uint16(result) = node or
    TOpcode_extract_uint32(result) = node or
    TOpcode_extract_uint64(result) = node or
    TOpcode_replace3(result) = node or
    TOpcode_extract3(result) = node or
    TOpcode_balance(result) = node or
    TOpcode_app_opted_in(result) = node or
    TOpcode_app_local_get(result) = node or
    TOpcode_app_local_get_ex(result) = node or
    TOpcode_app_global_get(result) = node or
    TOpcode_app_global_get_ex(result) = node or
    TOpcode_app_local_put(result) = node or
    TOpcode_app_global_put(result) = node or
    TOpcode_app_local_del(result) = node or
    TOpcode_app_global_del(result) = node or
    TOpcode_online_stake(result) = node or
    TOpcode_min_balance(result) = node or
    TOpcode_ed25519verify_bare(result) = node or
    TOpcode_shl(result) = node or
    TOpcode_shr(result) = node or
    TOpcode_sqrt(result) = node or
    TOpcode_bitlen(result) = node or
    TOpcode_exp(result) = node or
    TOpcode_expw(result) = node or
    TOpcode_bsqrt(result) = node or
    TOpcode_divw(result) = node or
    TOpcode_sha3_256(result) = node or
    TOpcode_badd(result) = node or
    TOpcode_bsub(result) = node or
    TOpcode_bdiv(result) = node or
    TOpcode_bmul(result) = node or
    TOpcode_blt(result) = node or
    TOpcode_bgt(result) = node or
    TOpcode_blte(result) = node or
    TOpcode_bgte(result) = node or
    TOpcode_beq(result) = node or
    TOpcode_bneq(result) = node or
    TOpcode_bmod(result) = node or
    TOpcode_bor(result) = node or
    TOpcode_band(result) = node or
    TOpcode_bxor(result) = node or
    TOpcode_bnot(result) = node or
    TOpcode_bzero(result) = node or
    TOpcode_log(result) = node or
    TOpcode_itxn_begin(result) = node or
    TOpcode_itxn_submit(result) = node or
    TOpcode_itxn_next(result) = node or
    TOpcode_box_create(result) = node or
    TOpcode_box_extract(result) = node or
    TOpcode_box_replace(result) = node or
    TOpcode_box_del(result) = node or
    TOpcode_box_len(result) = node or
    TOpcode_box_get(result) = node or
    TOpcode_box_put(result) = node or
    TOpcode_args(result) = node or
    TOpcode_gloadss(result) = node or
    TOpcode_box_splice(result) = node or
    TOpcode_box_resize(result) = node or
    TOpcode_switch(result) = node or 
    TOpcode_match(result) = node or
    TOpcode_intc(result) = node or
    TOpcode_bytec(result) = node or
    TOpcode_arg(result) = node or
    TOpcode_load(result) = node or
    TOpcode_store(result) = node or
    TOpcode_gloads(result) = node or
    TOpcode_bury(result) = node or
    TOpcode_popn(result) = node or
    TOpcode_dupn(result) = node or
    TOpcode_dig(result) = node or
    TOpcode_cover(result) = node or
    TOpcode_uncover(result) = node or
    TOpcode_replace2(result) = node or
    TOpcode_pushint(result) = node or
    TOpcode_frame_dig(result) = node or
    TOpcode_frame_bury(result) = node or
    TOpcode_int(result) = node or
    TOpcode_acct_params_get(result) = node or
    TOpcode_app_params_get(result) = node or
    TOpcode_asset_holding_get(result) = node or
    TOpcode_asset_params_get(result) = node or
    TOpcode_base64_decode(result) = node or
    TOpcode_block(result) = node or
    TOpcode_bytecblock(result) = node or
    TOpcode_extract(result) = node or
    TOpcode_substring(result) = node or
    TOpcode_gload(result) = node or
    TOpcode_proto(result) = node or
    TOpcode_ec_add(result) = node or
    TOpcode_ec_mul(result) = node or
    TOpcode_ec_pairing_check(result) = node or
    TOpcode_ec_multi_scalar_mul(result) = node or
    TOpcode_ec_subgroup_check(result) = node or
    TOpcode_ec_map_to(result) = node or
    TOpcode_ecdsa_verify(result) = node or
    TOpcode_ecdsa_pk_decompress(result) = node or
    TOpcode_ecdsa_pk_recover(result) = node or
    TOpcode_gitxn(result) = node or
    TOpcode_gitxna(result) = node or
    TOpcode_gitxnas(result) = node or
    TOpcode_global(result) = node or
    TOpcode_gaid(result) = node or
    TOpcode_gtxn(result) = node or
    TOpcode_gtxna(result) = node or
    TOpcode_gtxnas(result) = node or
    TOpcode_gtxns(result) = node or
    TOpcode_gtxnsa(result) = node or
    TOpcode_gtxnsas(result) = node or
    TOpcode_intcblock(result) = node or
    TOpcode_itxn_field(result) = node or
    TOpcode_itxna(result) = node or
    TOpcode_itxnas(result) = node or
    TOpcode_itxn(result) = node or
    TOpcode_json_ref(result) = node or
    TOpcode_mimc(result) = node or
    TOpcode_pushbytes(result) = node or
    TOpcode_pushbytess(result) = node or
    TOpcode_pushints(result) = node or
    TOpcode_txn(result) = node or
    TOpcode_txna(result) = node or
    TOpcode_txnas(result) = node or
    TOpcode_voter_params_get(result) = node or
    TOpcode_vrf_verify(result) = node
}


// cached
// class TExpr = TArrayAccess or TAssignmentExpression or TAugmentedAssignmentExpression or
//   TBinaryExpression or TBooleanLiteral or TCallExpression or TInlineArrayExpression or
//   TMemberExpression or TMetaTypeExpression or TNewExpression or TNumberLiteral or 
//   TParenthesizedExpression or TPayableConversionExpression or TSliceAccess or 
//   TStringLiteral or TStructExpression or TTernaryExpression or TTupleExpression or
//   TTypeCastExpression or TUnaryExpression or TUpdateExpression or TUserDefinedType or 
//   TExpression
//   or
//   THexStringLiteral or TTokenIdentifier or TPrimitiveType or TUnicodeStringLiteral
//   or
//   TCallArgument
//   or
//   TStructFieldAssignment or TYulAssignment;


// cached
// class TStmt = TAssemblyStatement or TBlockStatement or TDoWhileStatement or 
//   TEmitStatement or TExpressionStatement or TForStatement or TIfStatement or
//   TReturnStatement or TRevertStatement or TBreakStatement or TContinueStatement or 
//   TTryStatement or TVariableDeclarationStatement or TWhileStatement or TStatement
//   or TFunctionBody;

// Branching opcode groups
cached
class TOpcode = TOpcode_b or TOpcode_bz or TOpcode_bnz or TOpcode_callsub or TOpcode_retsub or
TOpcode_sha256 or TOpcode_keccak256 or TOpcode_sha512_256 or TOpcode_err or TOpcode_ed25519verify or
TOpcode_add or TOpcode_sub or TOpcode_mul or TOpcode_div or TOpcode_mod or TOpcode_lt or TOpcode_lte or
TOpcode_gt or TOpcode_gte or TOpcode_and or TOpcode_or or TOpcode_eq or TOpcode_neq or TOpcode_not or
TOpcode_len or TOpcode_itob or TOpcode_btoi or TOpcode_bitand or TOpcode_bitor or TOpcode_bitxor or
TOpcode_bitnot or TOpcode_mulw or TOpcode_addw or TOpcode_divmodw or TOpcode_intc_0 or TOpcode_intc_1 or
TOpcode_intc_2 or TOpcode_intc_3 or TOpcode_bytec_0 or TOpcode_bytec_1 or TOpcode_bytec_2 or TOpcode_bytec_3 or
TOpcode_arg_0 or TOpcode_arg_1 or TOpcode_arg_2 or TOpcode_arg_3 or TOpcode_gaids or TOpcode_loads or
TOpcode_stores or TOpcode_return or TOpcode_assert or TOpcode_pop or TOpcode_dup or TOpcode_dup2 or
TOpcode_swap or TOpcode_select or TOpcode_concat or TOpcode_substring3 or TOpcode_getbit or TOpcode_setbit or
TOpcode_getbyte or TOpcode_setbyte or TOpcode_extract_uint16 or TOpcode_extract_uint32 or TOpcode_extract_uint64 or
TOpcode_replace3 or TOpcode_extract3 or TOpcode_balance or TOpcode_app_opted_in or TOpcode_app_local_get or
TOpcode_app_local_get_ex or TOpcode_app_global_get or TOpcode_app_global_get_ex or TOpcode_app_local_put or
TOpcode_app_global_put or TOpcode_app_local_del or TOpcode_app_global_del or TOpcode_online_stake or
TOpcode_min_balance or TOpcode_ed25519verify_bare or TOpcode_shl or TOpcode_shr or TOpcode_sqrt or
TOpcode_bitlen or TOpcode_exp or TOpcode_expw or TOpcode_bsqrt or TOpcode_divw or TOpcode_sha3_256 or
TOpcode_badd or TOpcode_bsub or TOpcode_bdiv or TOpcode_bmul or TOpcode_blt or TOpcode_bgt or TOpcode_blte or
TOpcode_bgte or TOpcode_beq or TOpcode_bneq or TOpcode_bmod or TOpcode_bor or TOpcode_band or TOpcode_bxor or
TOpcode_bnot or TOpcode_bzero or TOpcode_log or TOpcode_itxn_begin or TOpcode_itxn_submit or TOpcode_itxn_next or
TOpcode_box_create or TOpcode_box_extract or TOpcode_box_replace or TOpcode_box_del or TOpcode_box_len or
TOpcode_box_get or TOpcode_box_put or TOpcode_args or TOpcode_gloadss or TOpcode_box_splice or
TOpcode_box_resize or TOpcode_switch or TOpcode_match or TOpcode_intc or TOpcode_bytec or TOpcode_arg or
TOpcode_load or TOpcode_store or TOpcode_gloads or TOpcode_bury or TOpcode_popn or TOpcode_dupn or TOpcode_dig or
TOpcode_cover or TOpcode_uncover or TOpcode_replace2 or TOpcode_pushint or TOpcode_frame_dig or
TOpcode_frame_bury or TOpcode_int or TOpcode_acct_params_get or TOpcode_app_params_get or
TOpcode_asset_holding_get or TOpcode_asset_params_get or TOpcode_base64_decode or TOpcode_block or
TOpcode_bytecblock or TOpcode_extract or TOpcode_substring or TOpcode_gload or TOpcode_proto or
TOpcode_ec_add or TOpcode_ec_mul or TOpcode_ec_pairing_check or TOpcode_ec_multi_scalar_mul or
TOpcode_ec_subgroup_check or TOpcode_ec_map_to or TOpcode_ecdsa_verify or TOpcode_ecdsa_pk_decompress or
TOpcode_ecdsa_pk_recover or TOpcode_gitxn or TOpcode_gitxna or TOpcode_gitxnas or TOpcode_global or
TOpcode_gtxn or TOpcode_gtxna or TOpcode_gtxnas or TOpcode_gtxns or TOpcode_gtxnsa or TOpcode_gtxnsas or
TOpcode_intcblock or TOpcode_itxn_field or TOpcode_itxna or TOpcode_itxnas or TOpcode_json_ref or
TOpcode_mimc or TOpcode_pushbytes or TOpcode_pushbytess or TOpcode_pushints or TOpcode_txn or TOpcode_txna or
TOpcode_txnas or TOpcode_voter_params_get or TOpcode_vrf_verify or TOpcode_itxn;

cached
class TUnconditionalBranches = TOpcode_b or TOpcode_callsub or TOpcode_retsub;

cached
class TSimpleConditionalBranches = TOpcode_bnz or TOpcode_bz;

cached
class TMultiTargetConditionalBranch = TOpcode_switch or TOpcode_match;

cached
class TBranchOpcodes = TUnconditionalBranches or TSimpleConditionalBranches or
    TMultiTargetConditionalBranch;

cached
class TContractExitOpcode = TOpcode_assert or TOpcode_err or TOpcode_return;


class AstNode instanceof TAstNode{
    AstNode getParent(){
        toTreeSitter(result) = toTreeSitter(this).getParent()}
  
    int getParentIndex(){result = toTreeSitter(this).getParentIndex()}
    
    string toString(){toTreeSitter(this).toString() = result}
    
    string getAPrimaryQlClass(){result = toTreeSitter(this).getAPrimaryQlClass()}

  
    /** Gets the primary file where this element occurs. */
    File getFile() { result = toTreeSitter(this).getLocation().getFile() }

    L::Location getLocation(){result = toTreeSitter(this).getLocation()}


    
    int getLineNumber(){
        exists(int i | this.getProgram().getChild(i) = this | result = i)
    }

    int getLineNumberInFile(){
        result = this.getLocation().getStartLine()
    }

    // Get opcode immediately next to this one in the code (not accounting for branches)
    AstNode getNextLine(){
        exists(int i | this.getProgram().getChild(i) = this
        | result = this.getProgram().getChild(i+1))
    }

    // Get opcode immediately before this one in the code (not accounting for branches)
    AstNode getPreviousLine(){
        exists(int i | this.getProgram().getChild(i+1) = this 
        | result = this.getProgram().getChild(i))
    }


    //Starts a codeblock
    predicate startsACodeblock(){
        this instanceof Label or
        this.getPreviousLine().endsACodeblock() or
        this.getLineNumber() = 0
    }

    //Ends a codeblock
    predicate endsACodeblock(){
        this instanceof UnconditionalBranches or
        this instanceof SimpleConditionalBranches or
        this instanceof MultiTargetConditionalBranch or
        this instanceof ContractExitOpcode or
        this.getNextLine() instanceof Label
    }

    cached
    AstNode getCodeblockStart(){
        this.startsACodeblock() and result = this
        or
        not this.startsACodeblock() and
        result = this.getPreviousLine().getCodeblockStart()
    }

    cached
    AstNode getCodeblockEnd(){
        this.endsACodeblock() and result = this
        or
        not this.endsACodeblock() and
        result = this.getNextLine().getCodeblockEnd()
    }

    predicate isInSameCodeblock(AstNode node){
        this.getCodeblockStart() = node.getCodeblockStart()
    }

    Program getProgram(){
        if this instanceof Program then result = this
        else result = this.getParent().getProgram()
    }



    cached
    BasicBlock getBasicBlock(){
        exists(BasicBlock bb | bb.getANode().getAstNode() = this and result = bb)
    }

    int getIndexInBasicBlock(){
        exists(int i | this.getBasicBlock().getNode(i).getAstNode() = this and result = i)
    }

    AstNode getPrevElementInBasicBlock(){
        exists(int i | i >= 0 and i < this.getIndexInBasicBlock() and 
            result = this.getBasicBlock().getNode(i).getAstNode())
    }

    AstNode getNextElementInBasicBlock(){
        exists(int i | i >= 0 and i > this.getIndexInBasicBlock() and 
            result = this.getBasicBlock().getNode(i).getAstNode())
    }

    predicate reaches(AstNode target){
        this.getBasicBlock() = target.getBasicBlock() and 
            this.getIndexInBasicBlock() <= target.getIndexInBasicBlock() 
        or

        //experimental. This branch checks for if we are ALREADY inside a subroutine
        //when the call to reaches starts, and therefore we cant do the trick of exploring
        //the whole subroutine independantly. This might cause problems in some parts.
        //TODO: test thoroughly
        exists(Subroutine sub | sub.mayReachNode(this) and 
            this.getBasicBlock().getLastNode().getAstNode() instanceof RetsubOpcode and
            sub.getRetsubOpcode() =  this.getBasicBlock().getLastNode().getAstNode() and
            sub.getCallingOpcode().getNextLine().reaches(target)
            )
        or


        exists(BasicBlock succ|
            succ = this.getBasicBlock().getASuccessor() and
            not this.getBasicBlock().getLastNode().getAstNode() instanceof RetsubOpcode and
            not this.getBasicBlock().getLastNode().getAstNode() instanceof CallsubOpcode and
            succ.getFirstNode().getAstNode().reaches(target)
        )
        or
        exists(BasicBlock succ|
            succ = this.getBasicBlock().getASuccessor() and
            this.getBasicBlock().getLastNode().getAstNode() instanceof CallsubOpcode and
            (
                this.getBasicBlock().getLastNode().getAstNode().(CallsubOpcode).getSubroutine().mayReachNode(target)
                or
                exists(this.getBasicBlock().getLastNode().getAstNode().(CallsubOpcode).getSubroutine().getRetsubOpcode())
                and this.getBasicBlock().getLastNode().getAstNode().getNextLine().reaches(target)
            )
        )
    }

    // this function is ONLY concerned with the delta (not the actual values)
    // unlike consumption/output, this one is useful to know the SIZE of a given stack,
    // without caring about the dataflow pattern of said stack through the opcode
    int getStackDelta(){
        result = 0
    }

    cached
    int getNumberOfConsumedArgs(){
        //TODO: finish
        if this instanceof TOpcode_bytecblock or
        this instanceof TOpcode_intcblock or
        this instanceof TOpcode_err or
        this instanceof TOpcode_return or

        // not strictly an opcode but included for completeness
        this instanceof TLabel or
        this instanceof TSource or

        // a pseudo-opcode
        this instanceof TOpcode_int or

        this instanceof TOpcode_intc or
        this instanceof TOpcode_intc_0 or
        this instanceof TOpcode_intc_1 or
        this instanceof TOpcode_intc_2 or
        this instanceof TOpcode_intc_3 or
        this instanceof TOpcode_bytec or
        this instanceof TOpcode_bytec_0 or
        this instanceof TOpcode_bytec_1 or
        this instanceof TOpcode_bytec_2 or
        this instanceof TOpcode_bytec_3 or
        this instanceof TOpcode_arg or
        this instanceof TOpcode_arg_0 or
        this instanceof TOpcode_arg_1 or
        this instanceof TOpcode_arg_2 or
        this instanceof TOpcode_arg_3 or
        this instanceof TOpcode_txn or
        this instanceof TOpcode_global or
        this instanceof TOpcode_gtxn or
        this instanceof TOpcode_load or
        this instanceof TOpcode_txna or
        this instanceof TOpcode_gtxna or
        this instanceof TOpcode_gload or
        this instanceof TOpcode_callsub or
        this instanceof TOpcode_pushint or
        this instanceof TOpcode_pushbytes or
        this instanceof TOpcode_itxn_begin or
        this instanceof TOpcode_itxn_submit or
        this instanceof TOpcode_gaid or
        this instanceof TOpcode_itxn_next or
        this instanceof TOpcode_pushbytess or
        this instanceof TOpcode_pushints or
        this instanceof TOpcode_gtxn or
        this instanceof TOpcode_proto or
        this instanceof TOpcode_frame_dig or // TODO: REVIEW!
        this instanceof TOpcode_online_stake or
        this instanceof TOpcode_gitxn or
        this instanceof TOpcode_gitxna or
        this instanceof TOpcode_itxn or
        this instanceof TOpcode_itxna or
        this instanceof TOpcode_retsub or  //TODO: this should consume whole stack at that point
                                           // if there is a proto affecting it
        this instanceof TOpcode_b then result = 0

        else if this instanceof TOpcode_keccak256 or
        this instanceof TOpcode_sha256 or
        this instanceof TOpcode_sha512_256 or
        this instanceof TOpcode_ecdsa_pk_decompress or
        this instanceof TOpcode_not or
        this instanceof TOpcode_len or
        this instanceof TOpcode_itob or
        this instanceof TOpcode_btoi or
        this instanceof TOpcode_store or
        this instanceof TOpcode_gtxns or
        this instanceof TOpcode_gtxnsa or
        this instanceof TOpcode_gloads or
        this instanceof TOpcode_gaids or
        this instanceof TOpcode_loads or
        this instanceof TOpcode_bnz or
        this instanceof TOpcode_bz or
        this instanceof TOpcode_assert or
        this instanceof TOpcode_pop or
        this instanceof TOpcode_dup or
        this instanceof TOpcode_substring or
        this instanceof TOpcode_extract or
        this instanceof TOpcode_itxn_field or
        this instanceof TOpcode_app_global_get or
        this instanceof TOpcode_app_global_del or
        this instanceof TOpcode_log or
        this instanceof TOpcode_bzero or
        this instanceof TOpcode_asset_params_get or
        this instanceof TOpcode_acct_params_get or
        this instanceof TOpcode_app_params_get or
        this instanceof TOpcode_balance or
        this instanceof TOpcode_min_balance or
        this instanceof TOpcode_bitnot or
        this instanceof TOpcode_bnot or
        this instanceof TOpcode_frame_bury or // TODO: REVIEW!
        this instanceof TOpcode_sqrt or
        this instanceof TOpcode_bitlen or
        this instanceof TOpcode_bsqrt or
        this instanceof TOpcode_sha3_256 or
        this instanceof TOpcode_box_del or
        this instanceof TOpcode_box_len or
        this instanceof TOpcode_box_get or
        this instanceof TOpcode_base64_decode or
        this instanceof TOpcode_block or
        this instanceof TOpcode_ec_subgroup_check or
        this instanceof TOpcode_ec_map_to or
        this instanceof TOpcode_gitxnas or
        this instanceof TOpcode_gtxnas or
        this instanceof TOpcode_itxnas or
        this instanceof TOpcode_txnas or
        this instanceof TOpcode_mimc or
        this instanceof TOpcode_voter_params_get or
        this instanceof TOpcode_switch or
        this instanceof TOpcode_args then result = 1

        else if this instanceof TOpcode_add or 
        this instanceof TOpcode_sub or
        this instanceof TOpcode_mul or
        this instanceof TOpcode_lt or
        this instanceof TOpcode_gt or 
        this instanceof TOpcode_lte or 
        this instanceof TOpcode_gte or 
        this instanceof TOpcode_and or
        this instanceof TOpcode_or or
        this instanceof TOpcode_eq or
        this instanceof TOpcode_neq or
        this instanceof TOpcode_mod or
        this instanceof TOpcode_bor or
        this instanceof TOpcode_band or
        this instanceof TOpcode_bxor or
        this instanceof TOpcode_mulw or
        this instanceof TOpcode_addw or
        this instanceof TOpcode_stores or
        this instanceof TOpcode_dup2 or
        this instanceof TOpcode_swap or
        this instanceof TOpcode_concat or
        this instanceof TOpcode_getbit or
        this instanceof TOpcode_getbyte or
        this instanceof TOpcode_app_global_get_ex or
        this instanceof TOpcode_app_global_put or
        this instanceof TOpcode_app_local_get or
        this instanceof TOpcode_app_local_del or
        this instanceof TOpcode_exp or
        this instanceof TOpcode_bitand or
        this instanceof TOpcode_bitor or
        this instanceof TOpcode_bitxor or
        this instanceof TOpcode_shr or
        this instanceof TOpcode_shl or
        this instanceof TOpcode_asset_holding_get or
        this instanceof TOpcode_div or
        this instanceof TOpcode_replace2 or
        this instanceof TOpcode_extract_uint16 or
        this instanceof TOpcode_extract_uint32 or
        this instanceof TOpcode_extract_uint64 or
        this instanceof TOpcode_app_opted_in or
        this instanceof TOpcode_expw or
        this instanceof TOpcode_badd or
        this instanceof TOpcode_bsub or
        this instanceof TOpcode_bdiv or
        this instanceof TOpcode_bmul or
        this instanceof TOpcode_blt or
        this instanceof TOpcode_bgt or
        this instanceof TOpcode_blte or
        this instanceof TOpcode_bgte or
        this instanceof TOpcode_beq or
        this instanceof TOpcode_bneq or
        this instanceof TOpcode_bmod or
        this instanceof TOpcode_box_create or
        this instanceof TOpcode_box_put or
        this instanceof TOpcode_box_resize or
        this instanceof TOpcode_gloadss or
        this instanceof TOpcode_ec_add or
        // this instanceof TOpcode_ec_mul or // TODO: REVIEW! TODO: FIX ERROR IN GRAMMAR!
        this instanceof TOpcode_ec_pairing_check or
        this instanceof TOpcode_ec_multi_scalar_mul or
        this instanceof TOpcode_json_ref or
        this instanceof TOpcode_gtxnsas then result = 2

        else if this instanceof TOpcode_ed25519verify or
        this instanceof TOpcode_substring3 or
        this instanceof TOpcode_setbit or
        this instanceof TOpcode_setbyte or
        this instanceof TOpcode_extract3 or
        this instanceof TOpcode_app_local_get_ex or
        this instanceof TOpcode_app_local_put or
        this instanceof TOpcode_select or
        this instanceof TOpcode_replace3 or
        this instanceof TOpcode_ed25519verify_bare or
        this instanceof TOpcode_divw or
        this instanceof TOpcode_box_extract or
        this instanceof TOpcode_box_replace or
        this instanceof TOpcode_vrf_verify then result = 3

        else if this instanceof TOpcode_ecdsa_pk_recover or
        this instanceof TOpcode_divmodw or
        this instanceof TOpcode_box_splice then result = 4

        else if this instanceof TOpcode_ecdsa_verify then result = 5

        else if this instanceof TOpcode_cover then
            result = toTreeSitter(this).(Teal::SingleNumericArgumentOpcode).getValue().toString().toInt() + 1

        else if this instanceof TOpcode_uncover then
            result = toTreeSitter(this).(Teal::SingleNumericArgumentOpcode).getValue().toString().toInt() + 1

        else if this instanceof TOpcode_popn then
            result = toTreeSitter(this).(Teal::SingleNumericArgumentOpcode).getValue().toString().toInt()

        else if this instanceof TOpcode_dupn then
            result = 1
        
        else if this instanceof TOpcode_match then
            result = count(toTreeSitter(this).(Teal::MatchOpcode).getChild(_)) + 1
        
        else if this instanceof TOpcode_dig then
            result = toTreeSitter(this).(Teal::SingleNumericArgumentOpcode).getValue().getValue().toInt() + 1
        
        else if this instanceof TOpcode_bury then
            result = toTreeSitter(this).(Teal::SingleNumericArgumentOpcode).getValue().getValue().toInt() + 1

        // else if this instanceof TOpcode_retsub then
            // this.(RetsubOpcode).getAffectingProto() and consumefullstack() or
            // result = 0
        //         result = this.(RetsubOpcode).getAffectingProto().getNumberOfInputArgs()
        
        else result = -1
    }

    cached
    int getNumberOfOutputArgs(){
        //TODO: finish
        if this instanceof TOpcode_bytecblock or
        this instanceof TOpcode_intcblock or

        // not strictly an opcode but included for completeness
        this instanceof TLabel or
        this instanceof TSource or

        this instanceof TBranchOpcodes or this instanceof TContractExitOpcode or
        this instanceof TOpcode_pop or this instanceof TOpcode_popn or
        this instanceof TOpcode_callsub or
        this instanceof TOpcode_itxn_begin or
        this instanceof TOpcode_itxn_field or
        this instanceof TOpcode_itxn_submit or
        this instanceof TOpcode_itxn_next or
        this instanceof TOpcode_app_global_put or
        this instanceof TOpcode_app_local_put or
        this instanceof TOpcode_app_local_del or
        this instanceof TOpcode_app_global_del or
        this instanceof TOpcode_store or
        this instanceof TOpcode_log or
        this instanceof TOpcode_match or
        this instanceof TOpcode_retsub or
        this instanceof TOpcode_proto or
        this instanceof TOpcode_frame_bury or // TODO: REVIEW!
        this instanceof TOpcode_stores or
        this instanceof TOpcode_box_replace or
        this instanceof TOpcode_box_put or
        this instanceof TOpcode_box_splice or
        this instanceof TOpcode_box_resize then result = 0

        else if this instanceof TOpcode_add or 
        this instanceof TOpcode_sub or
        this instanceof TOpcode_mul or
        this instanceof TOpcode_lt or
        this instanceof TOpcode_gt or 
        this instanceof TOpcode_lte or 
        this instanceof TOpcode_gte or 
        this instanceof TOpcode_and or
        this instanceof TOpcode_or or
        this instanceof TOpcode_eq or
        this instanceof TOpcode_neq or
        this instanceof TOpcode_mod or
        this instanceof TOpcode_pushint or
        this instanceof TOpcode_extract or
        this instanceof TOpcode_txn or
        this instanceof TOpcode_gtxnsa or
        this instanceof TOpcode_txna or
        this instanceof TOpcode_load or

        //a pseudo-opcode
        this instanceof TOpcode_int or
        
        this instanceof TOpcode_intc or
        this instanceof TOpcode_intc_0 or
        this instanceof TOpcode_intc_1 or
        this instanceof TOpcode_intc_2 or
        this instanceof TOpcode_intc_3 or
        this instanceof TOpcode_bytec or
        this instanceof TOpcode_bytec_0 or
        this instanceof TOpcode_bytec_1 or
        this instanceof TOpcode_bytec_2 or
        this instanceof TOpcode_bytec_3 or
        this instanceof TOpcode_extract3 or
        this instanceof TOpcode_getbit or
        this instanceof TOpcode_setbit or
        this instanceof TOpcode_app_global_get or
        this instanceof TOpcode_len or
        this instanceof TOpcode_shr or
        this instanceof TOpcode_shl or
        this instanceof TOpcode_concat or
        this instanceof TOpcode_bitand or
        this instanceof TOpcode_bitor or
        this instanceof TOpcode_bitxor or
        this instanceof TOpcode_bitnot or
        this instanceof TOpcode_bzero or
        this instanceof TOpcode_itob or
        this instanceof TOpcode_btoi or
        this instanceof TOpcode_div or
        this instanceof TOpcode_global or
        this instanceof TOpcode_exp or
        this instanceof TOpcode_gtxns or
        this instanceof TOpcode_app_local_get or
        this instanceof TOpcode_substring3 or
        this instanceof TOpcode_sha256 or
        this instanceof TOpcode_sha512_256 or
        this instanceof TOpcode_keccak256 or
        this instanceof TOpcode_getbyte or
        this instanceof TOpcode_setbyte or
        this instanceof TOpcode_ecdsa_verify or
        this instanceof TOpcode_not or
        this instanceof TOpcode_extract_uint16 or
        this instanceof TOpcode_balance or
        this instanceof TOpcode_min_balance or
        this instanceof TOpcode_gtxn or
        this instanceof TOpcode_select or
        this instanceof TOpcode_bnot or
        this instanceof TOpcode_pushbytes or
        this instanceof TOpcode_arg_0 or
        this instanceof TOpcode_arg_1 or
        this instanceof TOpcode_arg_2 or
        this instanceof TOpcode_arg_3 or
        this instanceof TOpcode_arg or
        this instanceof TOpcode_gaids or
        this instanceof TOpcode_loads or
        this instanceof TOpcode_args or
        this instanceof TOpcode_gloads or
        this instanceof TOpcode_gload or
        this instanceof TOpcode_gaid or
        this instanceof TOpcode_gtxna or
        this instanceof TOpcode_bor or
        this instanceof TOpcode_band or
        this instanceof TOpcode_bxor or
        this instanceof TOpcode_replace2 or
        this instanceof TOpcode_replace3 or
        this instanceof TOpcode_extract_uint32 or
        this instanceof TOpcode_extract_uint64 or
        this instanceof TOpcode_app_opted_in or
        this instanceof TOpcode_online_stake or
        this instanceof TOpcode_ed25519verify_bare or
        this instanceof TOpcode_sqrt or
        this instanceof TOpcode_bitlen or
        this instanceof TOpcode_bsqrt or
        this instanceof TOpcode_divw or
        this instanceof TOpcode_sha3_256 or
        this instanceof TOpcode_badd or
        this instanceof TOpcode_bsub or
        this instanceof TOpcode_bdiv or
        this instanceof TOpcode_bmul or
        this instanceof TOpcode_blt or
        this instanceof TOpcode_bgt or
        this instanceof TOpcode_blte or
        this instanceof TOpcode_bgte or
        this instanceof TOpcode_beq or
        this instanceof TOpcode_bneq or
        this instanceof TOpcode_bmod or
        this instanceof TOpcode_box_create or
        this instanceof TOpcode_box_extract or
        this instanceof TOpcode_box_del or
        this instanceof TOpcode_gloadss or
        this instanceof TOpcode_base64_decode or
        this instanceof TOpcode_block or
        this instanceof TOpcode_ec_add or
        // this instanceof TOpcode_ec_mul or // TODO: REVIEW! TODO: FIX OPCODE ERROR 
        this instanceof TOpcode_ec_pairing_check or
        this instanceof TOpcode_ec_multi_scalar_mul or
        this instanceof TOpcode_ec_subgroup_check or
        this instanceof TOpcode_ec_map_to or
        this instanceof TOpcode_gitxn or
        this instanceof TOpcode_gitxna or
        this instanceof TOpcode_gitxnas or
        this instanceof TOpcode_gtxnas or
        this instanceof TOpcode_gtxnsas or
        this instanceof TOpcode_itxn or
        this instanceof TOpcode_itxna or
        this instanceof TOpcode_itxnas or
        this instanceof TOpcode_txnas or
        this instanceof TOpcode_json_ref or
        this instanceof TOpcode_mimc or
        this instanceof TOpcode_frame_dig then result = 1 // TODO: REVIEW!

        else if this instanceof TOpcode_addw or
        this instanceof TOpcode_asset_holding_get or
        this instanceof TOpcode_acct_params_get or
        this instanceof TOpcode_asset_params_get or
        this instanceof TOpcode_app_params_get or
        this instanceof TOpcode_mulw or
        this instanceof TOpcode_dupn or
        this instanceof TOpcode_app_global_get_ex or
        this instanceof TOpcode_expw or
        this instanceof TOpcode_ecdsa_pk_recover or
        this instanceof TOpcode_swap or
        this instanceof TOpcode_dup or
        this instanceof TOpcode_ecdsa_pk_decompress or
        this instanceof TOpcode_app_local_get_ex or
        this instanceof TOpcode_box_len or
        this instanceof TOpcode_box_get or
        this instanceof TOpcode_voter_params_get or
        this instanceof TOpcode_vrf_verify then result = 2

        else if this instanceof TOpcode_dup2 or
        this instanceof TOpcode_divmodw then result = 4

        else if this instanceof TOpcode_cover then
            result = toTreeSitter(this).(Teal::SingleNumericArgumentOpcode).getValue().toString().toInt() + 1

        else if this instanceof TOpcode_uncover then
            result = toTreeSitter(this).(Teal::SingleNumericArgumentOpcode).getValue().toString().toInt() + 1

        else if this instanceof TOpcode_dupn then
            result = toTreeSitter(this).(Teal::SingleNumericArgumentOpcode).getValue().toString().toInt() + 1

        else if this instanceof TOpcode_pushints then
            result = strictcount(toTreeSitter(this).(Teal::PushintsOpcode).getValue(_))
        
        else if this instanceof TOpcode_pushbytess then
            result = strictcount(toTreeSitter(this).(Teal::PushbytessOpcode).getChild(_))
        
        else if this instanceof TOpcode_dig then
            result = toTreeSitter(this).(Teal::SingleNumericArgumentOpcode).getValue().getValue().toInt() + 2

        else if this instanceof TOpcode_bury then
            result = toTreeSitter(this).(Teal::SingleNumericArgumentOpcode).getValue().getValue().toInt()

        // else if this instanceof TOpcode_frame_bury then
        //     if toTreeSitter(this).(Teal::SingleNumericArgumentOpcode).getValue().getValue().toInt() < 0
        //     then result = 

        else result  = -1
    }

    //TODO: TEST THOROUGHLY! We assume its correct for now
    // get definitions that get consumed by this opcode, ordered from closest to furthest
    //to order in ssawrites (first branch), we use 1000 because its the maximum height of the stack
    // (therefore, no op could push more than 1000 elems to stack)
    Definition getStackInputByOrder(int ord){
        ord <= count(this.getConsumedValues()) and
        ord > 0 and
        result = 
        rank[ord](SSAVar var, AstNode n | this = n.getConsumedBy(var) | 
            var.toDef() order by ((this.getLineNumber() - n.getLineNumber())*1000 + var.getInternalOutputIndex()) 
        )
        or
        (
            result = rank[ord](Definition def | 
                (def instanceof DirectPhi or def instanceof IndirectPhi) and 
                this.getConsumedValues() = def | def order by 
                def.getOrd() desc)
        )
    }

    int getStackInputOrderByDef(Definition def){
        this.getStackInputByOrder(result) = def
    }


    Definition getConsumedValues(){
        result.(DirectPhi).getConsumedBy() = this 
        or
        result.(IndirectPhi).getConsumedBy() = this or
        exists(SSAVar v |
        v.getDeclarationNode().getBasicBlock() = this.getBasicBlock() and
        v.getDeclarationNode().getConsumedBy(v) = this and
        result = v.toDef()
        )
    }

    SSAVar getConsumedVars(){
        result = getGenerator(this.getConsumedValues()) 
        and result.reaches(this)  //TODO: why this? Might be wrong
    }

    // string getConsumedVars_str(){
    //     result = this.getConsumedVars().getIdentifier()
    // }


    //True if the input nodes to this AstNode may be predicted with certanity.
    // Note that this does not imply that the input is a constant, just
    // that we know exactly what opcode the values come from, and this choice
    // is unique. We also include PhiNodes in this, even tho their value
    // may or may not be dependant on multiple values.
    predicate inputIsPredictable(){
        count(this.getConsumedValues()) = this.getNumberOfConsumedArgs()
    }


    cached
    AstNode getConsumedBy(SSAVar var){
        this.getAnOutputVar() = var and
        result = rank[1](AstNode end |
            end.getBasicBlock() = this.getBasicBlock() and
            var.getInternalOutputIndex() + getPartialStackSizeBeforeOutput(this.getNextLine(), end) <= 0
            | end order by end.getLineNumber()
        )
    }

    SSAVar getOutputVar(int i){
        this.getNumberOfOutputArgs() > 0 and
        exists(SSAVar v | v.getDeclarationNode() = this and v.getInternalOutputIndex() = i
            | result = v)
    }

    SSAVar getAnOutputVar(){result = this.getOutputVar(_)}
}




// AstNode isinAPathBetween(AstNode start, AstNode end){
//     start.reaches(end) and
//     start.reaches(result)
//     and result.reaches(end)
// }

// predicate isInAllPathsBetween(AstNode start, AstNode end){
//     start = end
// }

// AstNode test(InnerTransactionStart s, InnerTransactionEnd e, int i){
//     result = rank[i](AstNode mid | 
//     mid = isinAPathBetween(s, e) | mid order by mid.getLineNumber())
// }



int getPartialStackSizeBeforeOutput(AstNode begin, AstNode end){
    begin = end and result = -begin.getNumberOfConsumedArgs() 
    or
    begin != end and
    begin.getCodeblockStart() = end.getCodeblockStart() and
    // begin.getBasicBlock() = end.getBasicBlock() and
    begin.getLineNumber() < end.getLineNumber() and
    result = sum(int h | h = [begin.getLineNumber() .. end.getLineNumber()-1] | 
        begin.getProgram().getChild(h).getNumberOfOutputArgs() -
        begin.getProgram().getChild(h).getNumberOfConsumedArgs()) -
        end.getNumberOfConsumedArgs()
}

class Codeblock extends AstNode{
    Codeblock(){this.startsACodeblock()}

    AstNode getChild(int i){
        i in [0 .. this.getCodeblockEnd().getLineNumber() - this.getLineNumber()]
        // i >= 0 and this.getLineNumber()+i <= this.getCodeblockEnd().getLineNumber()
        and result = this.getProgram().getChild(this.getLineNumber()+i)
    }

    int numberOfLines(){
        result = count(this.getChild(_))
    }
}


class Subroutine extends AstNode{
    private CallsubOpcode originalCall;

    Subroutine(){
        this = originalCall.getTargetLabel() 
    }

    CallsubOpcode getCallingOpcode(){
        result = originalCall
    }

    cached
    RetsubOpcode getRetsubOpcode(){
        exists(RetsubOpcode ret | ret.getBasicBlock() = this.getBasicBlock() or 
            this.getBasicBlock().reaches(ret.getBasicBlock()) | result = ret)
    }

    AstNode getSubroutineStart(){
        result = this.getCallingOpcode().getTargetLabel()
    }

    predicate mayReachNode(AstNode n){
        n = getNextNode_subroutineAux*(this) or 
        exists(CallsubOpcode h, AstNode j | 
            h = getNextNode_subroutineAux*(this) and h.getSubroutine().mayReachNode(j)
            | n=j)
    }
}

AstNode getNextNode_subroutineAux(AstNode prev){
    not (prev instanceof ReturnOpcode or 
        prev instanceof ErrOpcode or 
        prev instanceof RetsubOpcode) and (
        result = prev.(BOpcode).getTargetLabel() or
        result = prev.(BzOpcode).getNextNode(_) or
        result = prev.(BnzOpcode).getNextNode(_) or
        result = prev.(CallsubOpcode).getNextLine() //we ignore going into new subroutines
        or not (prev instanceof BOpcode or prev instanceof BzOpcode or prev instanceof BnzOpcode
            or prev instanceof CallsubOpcode) and result = prev.getNextLine()
    )
}


class Label extends AstNode instanceof TLabel{
    Label(){toTreeSitter(this) instanceof Teal::Label}

    string getName(){
        result = toTreeSitter(this).(Teal::Label).getName().getValue()
    }

    CallsubOpcode getCallsubToLabel(){
        exists(CallsubOpcode op | op.getTargetLabel() = this and result = op)
    }

    AstNode getReferenceToLabel(){
        any() //TODO: implement
    }
}


class Opcode extends AstNode instanceof TOpcode {
    override int getStackDelta() { result = this.getNumberOfOutputArgs() - this.getNumberOfConsumedArgs() }
}




