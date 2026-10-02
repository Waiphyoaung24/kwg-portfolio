$ErrorActionPreference = 'Stop'
$repo = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$root = Join-Path $repo '.batch3-vibe/gold-plan-auth'
$owner = [Security.Principal.NTAccount]::new('KWG-Beast', 'wai19').Translate([Security.Principal.SecurityIdentifier])
$system = [Security.Principal.SecurityIdentifier]::new('S-1-5-18')
if ([Security.Principal.WindowsIdentity]::GetCurrent().User -ne $owner) { throw 'Run as the workspace owner.' }
$taskPython = (Get-Command python.exe).Source
& $taskPython -I -c 'import httpx,jwt,cryptography'
if ($LASTEXITCODE) { throw 'Existing OAuth dependencies unavailable.' }
foreach ($path in @($repo, (Join-Path $repo '.batch3-vibe'), $root)) {
    if ((Test-Path -LiteralPath $path) -and ((Get-Item -LiteralPath $path -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Reparse path refused.' }
}
if (-not (Test-Path -LiteralPath $root)) {
    New-Item -ItemType Directory -Path $root | Out-Null
    $acl = [Security.AccessControl.DirectorySecurity]::new()
    $acl.SetOwner($owner)
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($sid in @($owner, $system)) {
        $rule = [Security.AccessControl.FileSystemAccessRule]::new($sid, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
        $acl.AddAccessRule($rule)
    }
    Set-Acl -LiteralPath $root -AclObject $acl
}
$actual = Get-Acl -LiteralPath $root
if (-not $actual.AreAccessRulesProtected) { throw 'Private auth directory inherits access.' }
foreach ($rule in $actual.Access) {
    if ($rule.AccessControlType -ne 'Allow' -or $rule.IdentityReference.Translate([Security.Principal.SecurityIdentifier]) -notin @($owner, $system)) { throw 'Unexpected auth directory access.' }
}
if (Test-Path -LiteralPath (Join-Path $root 'registration.json')) { Write-Output 'Already registered; no request or overwrite.'; exit 0 }
$source = Join-Path $PSScriptRoot 'register_gold_oauth.py'
$snapshot = Join-Path $root 'register_gold_oauth.py'
if (-not (Test-Path -LiteralPath $snapshot)) { [IO.File]::Copy($source, $snapshot, $false) }
if ((Get-FileHash -LiteralPath $source).Hash -ne (Get-FileHash -LiteralPath $snapshot).Hash) { throw 'Private source differs; review before replacing.' }
# An exclusive lock avoids concurrent callback listeners without touching prior credentials.
$lock = [IO.File]::Open((Join-Path $root 'registration.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
try {
    & $taskPython -I -B $snapshot
    exit $LASTEXITCODE
} finally { $lock.Dispose() }
