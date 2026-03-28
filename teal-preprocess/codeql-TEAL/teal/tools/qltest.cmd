@echo off

type NUL && "%CODEQL_DIST%\codeql.exe" database index-files ^
    --prune=**/*.testproj ^
    --include-extension=.teal ^
    --include-extension=.gemspec ^
    --include=**/Gemfile ^
    --size-limit=5m ^
    --language=teal ^
    --working-dir=. ^
    "%CODEQL_EXTRACTOR_TEAL_WIP_DATABASE%"

exit /b %ERRORLEVEL%
