#!/bin/bash
# Build all CodeQL databases for tealer detection test contracts.
# Run from the repository root.

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SEARCH_PATH="$REPO_ROOT/.codeql-extractors"
CONTRACTS_DIR="$REPO_ROOT/tealer-detections/test-contracts"

DETECTIONS=(
  is-deletable is-updatable
  unprotected-deletable unprotected-updatable
  group-size-check
  can-close-account can-close-asset
  missing-fee-check
  rekey-to
  constant-gtxn self-access sender-access
)

for dir in "${DETECTIONS[@]}"; do
  for variant in vuln fixed; do
    src="$CONTRACTS_DIR/$dir/${variant}-src"
    db="$CONTRACTS_DIR/$dir/${variant}-db"
    echo "Building $dir/$variant..."
    codeql database create "$db" --overwrite -l teal -s "$src" \
      --search-path "$SEARCH_PATH" 2>&1 | grep -E "Successfully|Error" | head -1
  done
done

echo "All databases built."
