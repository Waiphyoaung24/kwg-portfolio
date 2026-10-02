param([Parameter(Mandatory)][ValidateSet('canary', 'credentials', 'seal', 'seal-current', 'seal-gateway', 'seal-readiness')][string]$Phase)
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

function Assert-NoReparse([string]$Path) {
    $item = Get-Item -LiteralPath $Path -Force
    while ($null -ne $item) {
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Source or ancestor reparse point rejected.' }
        $item = if ($item.PSIsContainer) { $item.Parent } else { $item.Directory }
    }
}

function Copy-Verified([string]$Source, [string]$Destination) {
    Assert-NoReparse $Source
    Assert-NoReparse (Split-Path $Destination -Parent)
    if (-not ('Batch3HandlePath' -as [type])) {
        Add-Type @'
using System.Text;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;
public static class Batch3HandlePath {
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern uint GetFinalPathNameByHandle(SafeFileHandle file, StringBuilder path, uint size, uint flags);
}
'@
    }
    # ShareRead denies writes/deletion while hashing and copying this exact handle.
    $sourceStream = [IO.File]::Open($Source, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
    try {
        $actual = [Text.StringBuilder]::new(32768)
        $length = [Batch3HandlePath]::GetFinalPathNameByHandle($sourceStream.SafeFileHandle, $actual, 32768, 0)
        if ($length -eq 0 -or $length -ge 32768 -or $actual.ToString().Substring(4) -ne [IO.Path]::GetFullPath($Source)) { throw 'Opened source identity differs from expected path.' }
        Assert-NoReparse $Source
        $before = (Get-FileHash -InputStream $sourceStream -Algorithm SHA256).Hash
        $sourceStream.Position = 0
        $destinationStream = [IO.File]::Open($Destination, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        try { $sourceStream.CopyTo($destinationStream); $destinationStream.Flush($true) } finally { $destinationStream.Dispose() }
        if ($before -ne (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash) { throw 'Copy identity changed; preserve partial snapshot.' }
    } finally { $sourceStream.Dispose() }
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
    $current = $Phase -in @('seal-current', 'seal-gateway', 'seal-readiness')
    if ($Phase -eq 'seal-readiness') {
        & git -C $repo diff --quiet HEAD -- ops/trading
        if ($LASTEXITCODE) { throw 'Commit reviewed trading sources before readiness sealing.' }
        $commit = (& git -C $repo rev-parse HEAD).Trim()
        if ($LASTEXITCODE -or $commit -notmatch '^[a-f0-9]{40}$') { throw 'Committed source identity unavailable.' }
    }
    $snapshotName = switch ($Phase) { 'seal-current' { 'sealed-trusted-transport-20261002' } 'seal-gateway' { 'sealed-gateway-20261002-r2' } default { 'sealed-credential-rehearsal' } }
    if ($Phase -eq 'seal-readiness') { $snapshotName = 'sealed-gateway-readiness-' + $commit.Substring(0, 12) }
    $sealed = Join-Path $root $snapshotName
    Assert-NoReparse $root
    if (Test-Path -LiteralPath $sealed) { throw 'Snapshot already exists; preserve it.' }
    New-Item -ItemType Directory -Path $sealed | Out-Null
    # Close sandbox access before any source bytes or manifest are copied.
    Set-Boundary $sealed
    if ($Phase -eq 'seal-readiness') {
        $registry = Join-Path $root 'production-attempts'
        Assert-NoReparse $root
        if (-not (Test-Path -LiteralPath $registry)) {
            New-Item -ItemType Directory -Path $registry | Out-Null
            Set-Boundary $registry
        }
        Assert-NoReparse $registry
        $acl = Get-Acl -LiteralPath $registry
        if (-not $acl.AreAccessRulesProtected -or $acl.GetOwner([Security.Principal.SecurityIdentifier]) -ne $user) { throw 'Private registry owner/inheritance mismatch.' }
        $seen = @()
        foreach ($rule in $acl.Access) {
            $sid = $rule.IdentityReference.Translate([Security.Principal.SecurityIdentifier])
            if ($sid -notin @($user, $system) -or $rule.AccessControlType -ne 'Allow' -or $rule.FileSystemRights -ne 'FullControl') { throw 'Private registry permissions mismatch.' }
            $seen += $sid.Value
        }
        if ($user.Value -notin $seen -or $system.Value -notin $seen) { throw 'Private registry access incomplete.' }
        $readiness = Join-Path $root 'gateway-readiness'
        if (-not (Test-Path -LiteralPath $readiness)) {
            New-Item -ItemType Directory -Path $readiness | Out-Null
            Set-Boundary $readiness
        }
        Assert-NoReparse $readiness
        @{ mode='fake_readiness_only'; git_commit=$commit; production_registry=$registry;
            registry_acl_checked=$true; production_dispatch='blocked'; billing_ceiling_verified=$false;
            server_account_verified=$false; production_isolation_verified=$false } |
            ConvertTo-Json | Set-Content -LiteralPath (Join-Path $sealed 'readiness.json') -Encoding utf8
    }
    $code = New-Item -ItemType Directory -Path (Join-Path $sealed 'code')
    # Snapshot the offline tool chain, including test dependencies, not the upstream application.
    $sources = @(Get-ChildItem -LiteralPath $PSScriptRoot -File | Where-Object { $_.Extension -in @('.py', '.json', '.patch', '.ps1') })
    if ($Phase -eq 'seal-readiness') {
        foreach ($file in $sources) {
            & git -C $repo ls-files --error-unmatch -- ('ops/trading/' + $file.Name) | Out-Null
            if ($LASTEXITCODE) { throw 'Uncommitted source in readiness seal.' }
        }
    }
    foreach ($file in $sources) { Copy-Verified $file.FullName (Join-Path $code.FullName $file.Name) }
    Copy-Verified (Join-Path $root 'upstream/agent/src/providers/openai_codex.py') (Join-Path $sealed 'upstream-provider.py')
    $attempt = if ($current) { Join-Path $repo '.superpowers/sdd/batch3-auth-docker-20261002-03/refresh_success' } else { Join-Path $root 'sandbox-rehearsal-20261001-214001/attempt' }
    $inputs = New-Item -ItemType Directory -Path (Join-Path $sealed 'inputs')
    foreach ($name in @('attempt.json', 'packet.json', 'request.json', 'provider.py')) {
        Copy-Verified (Join-Path $attempt $name) (Join-Path $inputs.FullName $name)
    }
    if ($current) {
        $expected = @{
            'attempt.json' = '76bdfdc7113325bc10ca6e4cc217167794351da4bb4f38cf84aaffe0c5d66d5f'
            'packet.json' = 'ebfcaac926358b87bffa22129eba5253b2eb4872ba7012552ad49f0ab74b5539'
            'request.json' = '325d6b1fc5a45d0ae5480cf5c99f2cc67bb435c3730b41ca39498beeb0a5af90'
            'provider.py' = '64e257725e04ff0b1d8e7a56061d67aa190113d60340850b45bc821de74e867e'
        }
        foreach ($name in $expected.Keys) {
            if ((Get-FileHash -LiteralPath (Join-Path $inputs.FullName $name)).Hash.ToLowerInvariant() -ne $expected[$name]) { throw 'Frozen -03 input identity mismatch.' }
        }
        if ((Get-FileHash -LiteralPath (Join-Path $sealed 'upstream-provider.py')).Hash.ToLowerInvariant() -ne '19a23404ae7cdbe404c28b157fd2fc6766f7deec2a0db0423879601bb1fdd4f0') { throw 'Upstream provider identity mismatch.' }
        $verification = @'
import hashlib,json,pathlib,sys
p=pathlib.Path(sys.argv[1])
read=lambda n: json.loads((p/'inputs'/n).read_bytes())
digest=lambda v: hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
attempt=read('attempt.json'); request=read('request.json')
assert attempt['packet_sha256']==digest(read('packet.json'))
assert attempt['request_sha256']==digest(request)
assert request['provider_source_sha256']==hashlib.sha256((p/'inputs/provider.py').read_bytes()).hexdigest()
assert attempt['worker_source_sha256']==hashlib.sha256((p/'code/batch3_runner.py').read_bytes()).hexdigest()
'@
        $encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($verification))
        & python -I -S -B -c "import base64;exec(base64.b64decode('$encoded'))" $sealed
        if ($LASTEXITCODE) { throw 'Frozen attempt identity invalid; preserve partial snapshot.' }
        foreach ($file in $sources) {
            if ((Get-FileHash -LiteralPath $file.FullName).Hash -ne (Get-FileHash -LiteralPath (Join-Path $code.FullName $file.Name)).Hash) { throw 'Source changed during snapshot; preserve partial snapshot.' }
        }
    }
    $manifest = @(Get-ChildItem -LiteralPath $sealed -Recurse -File | ForEach-Object {
        @{ path=$_.FullName.Substring($sealed.Length + 1); sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant() }
    })
    $manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $sealed 'manifest.json') -Encoding utf8
    Set-Boundary $sealed 'ReadAndExecute'
    foreach ($item in Get-ChildItem -LiteralPath $sealed -Recurse -Force) { Set-Boundary $item.FullName 'ReadAndExecute' }
    foreach ($entry in $manifest) {
        if ((Get-FileHash -LiteralPath (Join-Path $sealed $entry.path)).Hash.ToLowerInvariant() -ne $entry.sha256) { throw 'Sealed snapshot hash mismatch.' }
    }
    Write-Output 'PASS: code and frozen input copies sealed; owner/SYSTEM full, sandbox read/execute only.'
}
