use std::{
    fs,
    io::{self, Read},
    process::ExitCode,
};

use clap::{Parser, Subcommand};

#[derive(Debug, Parser)]
#[command(
    name = "wellmanifest-native",
    version,
    about = "Native JSON/YAML WellManifest runtime"
)]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Debug, Subcommand)]
enum Command {
    Convert {
        file: String,
        #[arg(long = "from")]
        from: String,
        #[arg(long = "to")]
        to: String,
        #[arg(long)]
        compact: bool,
    },
}

fn read_source(path: &str) -> io::Result<String> {
    if path == "-" {
        let mut source = String::new();
        io::stdin().read_to_string(&mut source)?;
        Ok(source)
    } else {
        fs::read_to_string(path)
    }
}

fn main() -> ExitCode {
    let cli = Cli::parse();
    match cli.command {
        Command::Convert {
            file,
            from,
            to,
            compact,
        } => {
            let source = match read_source(&file) {
                Ok(value) => value,
                Err(error) => {
                    eprintln!("ERROR WM-IO-001: {error}");
                    return ExitCode::from(2);
                }
            };
            match wellmanifest_core::convert(&source, &from, &to, !compact) {
                Ok(output) => {
                    print!("{output}");
                    ExitCode::SUCCESS
                }
                Err(error) => {
                    eprintln!("ERROR WM-CONVERT-001: {error}");
                    ExitCode::from(1)
                }
            }
        }
    }
}
