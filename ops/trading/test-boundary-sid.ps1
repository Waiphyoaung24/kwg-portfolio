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
'PASS: shared hardener command removed numeric SID from harmless canary; no private runtime access or model requests.'
