param([string]$Output = '.superpowers/sdd/boundary-sid-canary-20261005')
$ErrorActionPreference = 'Stop'
$parseErrors = $null
$ast = [Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'harden-batch3.ps1'), [ref]$null, [ref]$parseErrors)
if ($parseErrors.Count) { throw 'Hardener syntax invalid.' }
$boundary = $ast.Find({ param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Set-Boundary' }, $false)
$removal = @($boundary.FindAll({ param($node) $node -is [Management.Automation.Language.CommandAst] -and $node.GetCommandName() -eq 'icacls.exe' -and '/remove' -in @($node.CommandElements | ForEach-Object { $_.Extent.Text }) }, $true))
if ($removal.Count -ne 1) { throw 'One shared ACL removal command required.' }
$folder = [IO.Path]::GetFullPath($Output)
if (Test-Path -LiteralPath $folder) { throw 'Canary already exists; preserve it.' }
New-Item -ItemType Directory -Path $folder | Out-Null
$Path = Join-Path $folder 'canary.txt'
[IO.File]::WriteAllText($Path, 'harmless numeric SID removal canary')
$sid = [Security.Principal.SecurityIdentifier]::new('S-1-1-0')
# Force numeric identity, as returned for an ACL identity without a friendly name.
$rule = [pscustomobject]@{ IdentityReference = $sid }
& icacls.exe $Path /grant "*${sid}:R" | Out-Null
if ($LASTEXITCODE) { throw 'Synthetic ACL grant failed.' }
if (-not @( (Get-Acl -LiteralPath $Path).Access | Where-Object { $_.IdentityReference.Translate([Security.Principal.SecurityIdentifier]) -eq $sid }).Count) { throw 'Synthetic grant missing.' }
Invoke-Expression $removal[0].Extent.Text | Out-Null
if ($LASTEXITCODE) { throw 'Shared numeric SID removal failed.' }
if (@( (Get-Acl -LiteralPath $Path).Access | Where-Object { $_.IdentityReference.Translate([Security.Principal.SecurityIdentifier]) -eq $sid }).Count) { throw 'Unexpected ACE remains.' }
# Exercise the complete shared function with the observed inherited/removed SID
# sequence. Mock only ACL reads and native writes; no real owner-only ACL rewrite.
Invoke-Expression $boundary.Extent.Text
$root = $folder
$user = [Security.Principal.WindowsIdentity]::GetCurrent().User
$system = [Security.Principal.SecurityIdentifier]::new('S-1-5-18')
$unmapped = [Security.Principal.SecurityIdentifier]::new('S-1-5-21-111111111-222222222-333333333-9876')
$script:inheritanceRemoved = $false
$script:explicitUnmapped = $false
$script:removedCurrent = $false
$script:staleRemovalAttempted = $false
function Get-Acl([string]$LiteralPath) {
    $identities = @($user, $system)
    if (-not $script:inheritanceRemoved -or $script:explicitUnmapped) { $identities += $unmapped } else { $identities += $sid }
    return [pscustomobject]@{ Access = @($identities | ForEach-Object { [pscustomobject]@{ IdentityReference = $_ } }) }
}
function icacls.exe {
    $global:LASTEXITCODE = 0
    if ($args[1] -eq '/inheritance:r') { $script:inheritanceRemoved = $true }
    if ($args[1] -eq '/remove') {
        if ($args[2] -eq "*$unmapped") { $script:staleRemovalAttempted = $true; $global:LASTEXITCODE = 1332 }
        elseif ($args[2] -eq "*$sid") { $script:removedCurrent = $true }
        else { throw 'Unexpected synthetic removal target.' }
    }
}
Set-Boundary $folder
if (-not $script:inheritanceRemoved -or -not $script:removedCurrent -or $script:staleRemovalAttempted) { throw 'Current ACL was not used after inheritance removal.' }
# A still-present unmapped explicit entry must continue to fail closed.
$script:explicitUnmapped = $true
$refused = $false
try { Set-Boundary $folder } catch {
    if ($_.Exception.Message -ne 'Unexpected access removal failed.') { throw }
    $refused = $true
}
if (-not $refused) { throw 'Failed explicit ACL removal was ignored.' }
$global:LASTEXITCODE = 0
'PASS: native numeric SID removal; current ACL after inheritance cleanup; explicit removal failure refused; no private runtime access or model requests.'
