# Windows receives kwg-vault:// links here. Only exact links open fixed app paths;
# the URL is compared as text and never becomes a command.
param([string]$Url)

function Show-VaultError([string]$Message) {
    (New-Object -ComObject WScript.Shell).Popup($Message, 0, 'Vault could not open this app', 16) | Out-Null
    exit 1
}

switch ($Url) {
    { $_ -cin 'kwg-vault://sagar', 'kwg-vault://sagar/' } {
        # setup.exe installs per user; the .msi installs for all users.
        $candidates = @(
            (Join-Path $env:LOCALAPPDATA 'Sagar\sagar.exe'),
            (Join-Path $env:ProgramFiles 'Sagar\sagar.exe')
        )
        $app = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
        if (-not $app) { Show-VaultError 'Install Sagar for Windows from its official repository first.' }
        Start-Process -FilePath $app
        exit 0
    }
    { $_ -cin 'kwg-vault://figcraft', 'kwg-vault://figcraft/' } {
        Show-VaultError 'FigCraft is set up on the Mac only.'
    }
    default { Show-VaultError 'Unsupported Vault app link.' }
}
