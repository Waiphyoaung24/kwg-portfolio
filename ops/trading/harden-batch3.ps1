param([Parameter(Mandatory)][ValidateSet('canary', 'credentials', 'seal')][string]$Phase)
$ErrorActionPreference = 'Stop'
$repo = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$root = Join-Path $repo '.batch3-vibe'
$user = [Security.Principal.NTAccount]::new('KWG-Beast', 'wai19').Translate([Security.Principal.SecurityIdentifier])
$system = [Security.Principal.SecurityIdentifier]::new('S-1-5-18')
$sandbox = [Security.Principal.NTAccount]::new('KWG-Beast', 'CodexSandboxOffline').Translate([Security.Principal.SecurityIdentifier])
if ([Security.Principal.WindowsIdentity]::GetCurrent().User -ne $user) { throw 'Run as the owning user, not the coding sandbox.' }

function Set-Boundary([string]$Path, [string]$SandboxRights = '') {
    $item = Get-Item -LiteralPath $Path -Force
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Reparse point rejected.' }
    if (-not $item.FullName.StartsWith($root + '\', [StringComparison]::OrdinalIgnoreCase) -and $item.FullName -ne $root) { throw 'Outside workspace boundary.' }
    $old = Get-Acl -LiteralPath $Path
    $inherit = if ($item.PSIsContainer) { '(OI)(CI)' } else { '' }
    & icacls.exe $Path /setowner "*$user" | Out-Null
    if ($LASTEXITCODE) { throw 'Owner change failed.' }
    & icacls.exe $Path /inheritance:r /grant:r "*${user}:${inherit}F" "*${system}:${inherit}F" | Out-Null
    if ($LASTEXITCODE) { throw 'Owner/SYSTEM boundary failed.' }
    foreach ($rule in $old.Access) {
        $sid = $rule.IdentityReference.Translate([Security.Principal.SecurityIdentifier])
        if ($sid -ne $user -and $sid -ne $system) {
            & icacls.exe $Path /remove "$($rule.IdentityReference)" | Out-Null
            if ($LASTEXITCODE) { throw 'Unexpected access removal failed.' }
        }
    }
    if ($SandboxRights) {
        $rights = if ($SandboxRights -eq 'Modify') { 'M' } else { 'RX' }
        & icacls.exe $Path /grant:r "*${sandbox}:${inherit}$rights" | Out-Null
        if ($LASTEXITCODE) { throw 'Sandbox boundary failed.' }
        if ($item.PSIsContainer -and $SandboxRights -eq 'Modify') {
            # Non-inherited deny prevents renaming the boundary's parent to substitute a new tree.
            & icacls.exe $Path /deny "*${sandbox}:(D)" | Out-Null
            if ($LASTEXITCODE) { throw 'Boundary rename protection failed.' }
        }
    }
}

$canary = Join-Path $root 'credential-boundary-canary'
if ($Phase -eq 'canary') {
    if (Test-Path -LiteralPath $canary) { throw 'Canary already initialized; do not reopen a hardened runtime.' }
    # Modify omits DeleteChild: a parent FullControl ACE would bypass child deletion protection.
    Set-Boundary $root 'Modify'
    foreach ($p in @('profile', 'profile/.vibe-trading')) { Set-Boundary (Join-Path $root $p) 'Modify' }
    New-Item -ItemType Directory -Path $canary | Out-Null
    Set-Boundary $canary
    [IO.File]::WriteAllText((Join-Path $canary 'canary.txt'), 'harmless credential-boundary canary')
    Set-Boundary (Join-Path $canary 'canary.txt')
    if ([IO.File]::ReadAllText((Join-Path $canary 'canary.txt')) -ne 'harmless credential-boundary canary') { throw 'Owner access failed.' }
    Write-Output 'PASS: owner can read canary; verify sandbox denial before credential phase.'
} elseif ($Phase -eq 'credentials') {
    if (-not (Test-Path -LiteralPath (Join-Path $root 'canary-denial-passed.json'))) { throw 'Canary denial evidence required.' }
    $auth = Join-Path $root 'profile/.vibe-trading/auth'
    Set-Boundary $auth
    foreach ($item in Get-ChildItem -LiteralPath $auth -Force) {
        if ($item.PSIsContainer) { throw 'Unexpected auth subdirectory; inspect metadata first.' }
        Set-Boundary $item.FullName
    }
    foreach ($p in @('profile/.vibe-trading/.env', 'profile/.vibe-trading/settings.json')) {
        $path = Join-Path $root $p
        if (Test-Path -LiteralPath $path) { Set-Boundary $path }
    }
    # Config APIs may replace files atomically: protect their parent so replacements stay private.
    Set-Boundary (Join-Path $root 'profile/.vibe-trading')
    Write-Output 'PASS: auth directory and private config restricted to owner and SYSTEM; contents not read.'
} else {
    $sealed = Join-Path $root 'sealed-credential-rehearsal'
    New-Item -ItemType Directory -Path $sealed | Out-Null
    $code = New-Item -ItemType Directory -Path (Join-Path $sealed 'code')
    # Snapshot the offline tool chain, including test dependencies, not the upstream application.
    $sources = @(Get-ChildItem -LiteralPath $PSScriptRoot -File | Where-Object { $_.Extension -in @('.py', '.json', '.patch') })
    foreach ($file in $sources) { Copy-Item -LiteralPath $file.FullName -Destination $code.FullName }
    Copy-Item -LiteralPath (Join-Path $root 'upstream/agent/src/providers/openai_codex.py') -Destination (Join-Path $sealed 'upstream-provider.py')
    $attempt = Join-Path $root 'sandbox-rehearsal-20261001-214001/attempt'
    $inputs = New-Item -ItemType Directory -Path (Join-Path $sealed 'inputs')
    foreach ($name in @('attempt.json', 'packet.json', 'request.json', 'provider.py')) {
        Copy-Item -LiteralPath (Join-Path $attempt $name) -Destination $inputs.FullName
    }
    $manifest = @(Get-ChildItem -LiteralPath $sealed -Recurse -File | ForEach-Object {
        @{ path=$_.FullName.Substring($sealed.Length + 1); sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant() }
    })
    $manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $sealed 'manifest.json') -Encoding utf8
    Set-Boundary $sealed 'ReadAndExecute'
    foreach ($item in Get-ChildItem -LiteralPath $sealed -Recurse -Force) { Set-Boundary $item.FullName 'ReadAndExecute' }
    Write-Output 'PASS: code and frozen input copies sealed; owner/SYSTEM full, sandbox read/execute only.'
}
