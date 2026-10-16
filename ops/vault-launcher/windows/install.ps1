# Registers kwg-vault:// for the current Windows user only. No admin rights needed.
$ErrorActionPreference = 'Stop'

$destination = Join-Path $env:LOCALAPPDATA 'KWG Vault Launcher'
$key = 'HKCU:\Software\Classes\kwg-vault'
if (Test-Path $key) {
    throw "Already installed: $key. Remove it before reinstalling."
}

New-Item -ItemType Directory -Force -Path $destination | Out-Null
$launcher = Join-Path $destination 'launcher.ps1'
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'launcher.ps1') -Destination $launcher -Force

$powershell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$command = "`"$powershell`" -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$launcher`" -Url `"%1`""
New-Item -Path $key -Value 'URL:KWG Vault desktop apps' | Out-Null
New-ItemProperty -Path $key -Name 'URL Protocol' -Value '' | Out-Null
New-Item -Path "$key\shell\open\command" -Force -Value $command | Out-Null
Write-Output "Installed $launcher"
