use std::{env, process::{Command, ExitCode}};

fn application(url: &str) -> Option<&'static str> {
    match url {
        "kwg-vault://figcraft" | "kwg-vault://figcraft/" => Some("/Applications/FigCraft.app"),
        "kwg-vault://sagar" | "kwg-vault://sagar/" => Some("/Applications/Sagar.app"),
        _ => None,
    }
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().skip(1).collect();
    let [url] = args.as_slice() else {
        eprintln!("Expected one Vault app link.");
        return ExitCode::FAILURE;
    };
    let Some(app) = application(url) else {
        eprintln!("Unsupported Vault app link.");
        return ExitCode::FAILURE;
    };
    // Only fixed application paths reach open; URLs never become shell commands.
    match Command::new("/usr/bin/open").args(["-a", app]).status() {
        Ok(status) if status.success() => ExitCode::SUCCESS,
        _ => {
            eprintln!("Could not open {app}. Install the app in Applications first.");
            ExitCode::FAILURE
        }
    }
}

#[cfg(test)]
mod tests {
    use super::application;

    #[test]
    fn opens_only_the_two_installed_apps() {
        for suffix in ["", "/"] {
            assert_eq!(application(&format!("kwg-vault://figcraft{suffix}")), Some("/Applications/FigCraft.app"));
            assert_eq!(application(&format!("kwg-vault://sagar{suffix}")), Some("/Applications/Sagar.app"));
        }
    }

    #[test]
    fn rejects_paths_queries_and_commands() {
        for url in ["", "https://sagar", "kwg-vault://terminal", "kwg-vault://sagar/file",
            "kwg-vault://sagar?command=rm", "kwg-vault://sagar#file", "kwg-vault://sagar//",
            "kwg-vault://sagar;touch /tmp/anything", "kwg-vault://sagar\n", "kwg-vault://user@sagar",
            "kwg-vault://%73agar", "kwg-vault://sagar:80", "file:///Applications/Sagar.app"] {
            assert_eq!(application(url), None, "accepted {url:?}");
        }
    }
}
