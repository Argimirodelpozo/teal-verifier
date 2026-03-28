# TealQL

TealQL is an SAST powered by GitHub Advanced Security's CodeQL, bringing the latest in Static Analysis tooling to the Algorand Virtual Machine's native language.

## Quick Start (macOS)

### 1. Clone the Repository

```bash
git clone https://github.com/Argimirodelpozo/codeql-TEAL.git
cd codeql-TEAL
```

### 2. Build the TEAL Extractor

The script handles dependency linking and permissions automatically:

```bash
cd teal/scripts
./create-extractor-pack.sh
cd ../..
```

### 3. Register Extractor for CodeQL

```bash
rm -rf .codeql-extractors
mkdir -p .codeql-extractors/teal
cp -R teal/extractor-pack/* .codeql-extractors/teal/
```

### 4. Create a CodeQL Database

```bash
codeql database create test-projects/my-db --overwrite -l teal -s test-projects/missing-fee --search-path "$(pwd)/.codeql-extractors"
```

### 5. Run a Query

**CLI:**
```bash
codeql query run teal/ql/lib/codeql/missingTxnFeeValidation.ql --database test-projects/my-db
```

**Or use the CodeQL VS Code extension** for an interactive UI experience.

---

## Running Tests

All tests require the extractor to be built and registered first (steps 2-3 above).

### Tealer Detection Tests (pytest)

The `tealer-detections/` directory contains a pytest suite that validates 12 security detections. Each detection is tested against a vulnerable contract (must produce findings) and a fixed contract (must produce zero findings).

**1. Build the test databases:**

```bash
bash tealer-detections/build_test_databases.sh
```

**2. Run the full test suite:**

```bash
pytest tealer-detections/test_tealer_detections.py -v
```

This runs 24 tests (2 per detection: vuln + fixed) covering: `is-deletable`, `is-updatable`, `unprotected-deletable`, `unprotected-updatable`, `group-size-check`, `can-close-account`, `can-close-asset`, `missing-fee-check`, `rekey-to`, `constant-gtxn`, `self-access`, `sender-access`.

**Run a single detection:**

```bash
pytest tealer-detections/test_tealer_detections.py -v -k "is-deletable"
```

> Note: If databases haven't been pre-built, the test suite will build them automatically on first run (slower).

### Running Individual Queries

You can run any `.ql` query file against a database:

```bash
codeql query run teal/ql/lib/codeql/<query>.ql --database test-projects/<db>
```

To export results to JSON:

```bash
python codeql-analysis-tools/codeql-analysis.py -d test-projects/<db> -q teal/ql/lib/codeql/<query>.ql -o results.json
```

---

## Prerequisites

- [CodeQL CLI](https://github.com/github/codeql-cli-binaries) (`codeql` on PATH)
- Rust toolchain (for building the extractor)
- Python 3 with `pytest` (for running tests)

## Features Coming Soon

## How to Contribute

## Rebuilding Extractors

When encountering parsing errors, a grammar update is probably needed.

1. Fix the appropriate rule in the grammar
2. Commit and push to main
3. Rebuild:

```bash
cd teal/scripts
./create-extractor-pack.sh
```

This will rebuild the Rust extractor, regenerate `teal.dbscheme` and `TreeSitter.qll`, and move them into the correct folders.

---

Made with love.

If you're into this kind of stuff, check out [TEALFuzz]() — a custom fuzzer for TEAL programs that uses TealQL to aid in fuzzing campaign setup.
