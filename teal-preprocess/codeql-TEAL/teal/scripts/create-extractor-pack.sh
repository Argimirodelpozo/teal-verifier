#!/bin/bash
set -eux

# Detect platform (used for extractor binary directory)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
  platform="linux64"
elif [[ "$OSTYPE" == "darwin"* ]]; then
  platform="osx64"
else
  echo "Unknown OS"
  exit 1
fi

# Move to teal/ root
cd "$(dirname "$0")/.."

# Ensure tree-sitter dependency path exists
# Required for Rust extractor build
mkdir -p extractor/dep
if [ ! -e extractor/dep/tree-sitter-extractor ]; then
  ln -s ../../dep/tree-sitter-extractor extractor/dep/tree-sitter-extractor
fi

# Build Rust extractor (release mode)
(cd extractor && cargo update -p tree-sitter-teal && cargo build --release)

# Generate dbscheme + TreeSitter.qll
BIN_DIR=extractor/target/release
"$BIN_DIR/codeql-extractor-teal" generate \
  --dbscheme ql/lib/teal.dbscheme \
  --library ql/lib/codeql/teal/ast/internal/TreeSitter.qll

# Format generated QL file
codeql query format -i ql/lib/codeql/teal/ast/internal/TreeSitter.qll

# Recreate extractor-pack
rm -rf extractor-pack
mkdir -p extractor-pack

# Copy required pack files
cp -r codeql-extractor.yml tools \
      ql/lib/teal.dbscheme \
      ql/lib/teal.dbscheme.stats \
      extractor-pack/

# Copy platform-specific extractor binary
mkdir -p extractor-pack/tools/${platform}
cp "$BIN_DIR/codeql-extractor-teal" \
   extractor-pack/tools/${platform}/extractor

# Ensure extractor tool scripts are executable
chmod +x extractor-pack/tools/autobuild.sh \
         extractor-pack/tools/index-files.sh \
         extractor-pack/tools/qltest.sh 2>/dev/null || true
