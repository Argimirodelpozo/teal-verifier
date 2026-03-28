use std::env;
use std::path::PathBuf;

use clap::Args;

use codeql_extractor::autobuilder;

#[derive(Args)]
// The autobuilder takes no command-line options, but this may change in the future.
pub struct Options {}

pub fn run(_: Options) -> std::io::Result<()> {
    let database = env::var("CODEQL_EXTRACTOR_TEAL_WIP_DATABASE")
        .expect("CODEQL_EXTRACTOR_TEAL_WIP_DATABASE not set");

    autobuilder::Autobuilder::new("teal", PathBuf::from(database))
        .include_extensions(&[".teal"])
        .exclude_globs(&["**/.git"])
        .size_limit("5m")
        .run()
}
