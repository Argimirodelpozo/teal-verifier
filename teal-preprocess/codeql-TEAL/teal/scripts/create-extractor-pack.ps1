# Enable strict mode and exit on error
$ErrorActionPreference = "Stop"

# Build the extractor using cargo
Push-Location "extractor"
Invoke-Expression "cargo build --release"
Pop-Location

# Set binary directory path
$BIN_DIR = "extractor/target/release"

# Generate with the codeql-extractor-teal
& "$BIN_DIR/codeql-extractor-teal.exe" generate --dbscheme "ql/lib/teal.dbscheme" --library "ql/lib/codeql/teal/ast/internal/TreeSitter.qll"

# Format the query file
codeql query format -i "ql/lib/codeql/teal/ast/internal/TreeSitter.qll"

# Prepare extractor-pack directory
Remove-Item -Recurse -Force "extractor-pack" -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path "extractor-pack"
Copy-Item -Recurse -Force -Path "codeql-extractor.yml", "tools", "ql/lib/teal.dbscheme", "ql/lib/teal.dbscheme.stats" -Destination "extractor-pack/"

# Create platform-specific tools directory and copy the binary
$platformToolsDir = "extractor-pack/tools/win64"
New-Item -ItemType Directory -Path $platformToolsDir -Force
Copy-Item "$BIN_DIR/codeql-extractor-teal.exe" -Destination "$platformToolsDir/extractor.exe"
