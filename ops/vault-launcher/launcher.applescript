-- macOS delivers custom URL events here; Rust validates and opens the app.
on open location appURL
    set launcherPath to (POSIX path of (path to me)) & "Contents/MacOS/vault-launcher"
    try
        do shell script (quoted form of launcherPath) & " " & (quoted form of appURL)
    on error errorMessage
        display alert "Vault could not open this app" message errorMessage
    end try
end open location
