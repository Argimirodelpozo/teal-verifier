// AVM Formal Verification Harness Template
// Used with CBMC (C Bounded Model Checker) to verify properties of TEAL contracts.
//
// Uses CBMC-specific bounded data structures (no STL containers).
// Compile: goto-cc -std=c++17 -DCBMC_VERIFICATION -I <project_root> -o out.goto <this>
//    then: cbmc out.goto --unwind N --unwinding-assertions

// Override bounds for verification (keep small for CBMC performance)
#define CBMC_STACK_MAX 16
#define CBMC_BYTES_MAX 32
#define CBMC_MAX_GLOBALS 4
#define CBMC_MAX_LOGS 4
#define CBMC_MAX_LOG_LEN 32
#define CBMC_SCRATCH_SLOTS 16
#define CBMC_MAX_APP_ARGS 4

#include "cbmc_avm.h"
#include "cbmc_opcodes.h"
#include "properties.h"
#include "bs_builder.h"

// ---------------------------------------------------------------------------
// CBMC nondet helpers
// ---------------------------------------------------------------------------

extern "C" {
    uint64_t nondet_uint64();
    uint8_t nondet_uint8();
    bool nondet_bool();
}

// ---------------------------------------------------------------------------
// Contract function type and registry
// ---------------------------------------------------------------------------

typedef void (*ContractFn)(Stack& s, BlockchainState& BS, EvalContext& ctx,
                           Txn* TxnGroup, uint8_t currentTxn);

//Function prototypes

// ---------------------------------------------------------------------------
// Verification context
// ---------------------------------------------------------------------------

struct VerifyContext {
    BlockchainState bs_before;
    BlockchainState bs_after;
    ExecResult result;
};

// ---------------------------------------------------------------------------
// User-defined properties (injected by transpiler)
// ---------------------------------------------------------------------------
//PROPERTIES_PLACEHOLDER

// ---------------------------------------------------------------------------
// main() — CBMC entry point
// ---------------------------------------------------------------------------

int main() {
    // 1. Symbolic initial state with sane Algorand defaults
    BlockchainState BS;
    bs_valid_initial_state(BS);

    uint64_t app_id = 1;

    // 2. Symbolic transaction (lean — no sender loop for default unwind compat)
    // Use txg_init for zero-init, then set up fields manually to keep loops
    // within default unwind bounds (max loop = 8 iterations for arg bytes).
    // For full symbolic sender, use txg_symbolic_appcall in setup_code with
    // unwind >= 33.
    Txn TxnGroup[1];
    txg_init(TxnGroup, 1);
    TxnGroup[0].TypeEnum = 6;  // appl
    TxnGroup[0].ApplicationID = app_id;

    // Symbolic on-completion
    uint8_t oc = nondet_uint8();
    __CPROVER_assume(oc <= 5);
    TxnGroup[0].apan = oc;

    // Symbolic app args: 2 args of 8 bytes each (loop bound = 8)
    TxnGroup[0].NumAppArgs = 2;
    TxnGroup[0].AppArgLens[0] = 8;
    TxnGroup[0].AppArgLens[1] = 8;
    for (uint8_t j = 0; j < 8; j++) {
        TxnGroup[0].AppArgs[0][j] = nondet_uint8();
        TxnGroup[0].AppArgs[1][j] = nondet_uint8();
    }

    TxnGroup[0].Fee = nondet_uint64();
    __CPROVER_assume(TxnGroup[0].Fee >= 1000);
    TxnGroup[0].Amount = nondet_uint64();

    //METHOD_CONSTRAINT_PLACEHOLDER

    uint8_t currentTxn = 0;

    // 3. Snapshot pre-state
    BlockchainState bs_before = BS;

    // 4. Execute contract
    Stack s;
    stack_init(s);
    EvalContext ctx;
    ctx_init(ctx);
    ctx.CurrentApplicationID = app_id;

    __avm_panicked = false;

    //CONTRACT_CALL_PLACEHOLDER

_contract_end: ;
    // 5. Determine result
    VerifyContext vctx;
    vctx.bs_before = bs_before;
    vctx.bs_after = BS;

    if (__avm_panicked) {
        vctx.result = PANIC;
    } else if (s.currentSize == 0) {
        vctx.result = REJECT;
    } else if (!s.stack[s.currentSize - 1]._is_bytes && s.stack[s.currentSize - 1].value != 0) {
        vctx.result = ACCEPT;
    } else {
        vctx.result = REJECT;
    }

    // 6. Check properties
    // In this scope, 'ctx' refers to VerifyContext so that property
    // expressions like 'ctx.result == ACCEPT' resolve correctly.
    {
        VerifyContext& ctx = vctx;
        (void)ctx;
        //PROPERTY_CHECKS_PLACEHOLDER
    }

    return 0;
}
