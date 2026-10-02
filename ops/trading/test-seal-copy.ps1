param([string]$Output = '.superpowers/sdd/seal-copy-canary-20261002')
$ErrorActionPreference = 'Stop'
$scriptPath = Join-Path $PSScriptRoot 'harden-batch3.ps1'
$ast = [Management.Automation.Language.Parser]::ParseFile($scriptPath, [ref]$null, [ref]$null)
foreach ($node in $ast.FindAll({ param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -in @('Assert-NoReparse','Copy-Verified') }, $false)) {
    Invoke-Expression $node.Extent.Text
}
$folder = [IO.Path]::GetFullPath($Output)
if (Test-Path -LiteralPath $folder) { throw 'Canary already exists; preserve it.' }
New-Item -ItemType Directory -Path $folder | Out-Null
$source = Join-Path $folder 'source.txt'
[IO.File]::WriteAllText($source, 'harmless sealing canary')
$copy = Join-Path $folder 'copy.txt'
Copy-Verified $source $copy
if ([IO.File]::ReadAllText($copy) -ne 'harmless sealing canary') { throw 'Copy bytes differ.' }
try { Copy-Verified $source $copy; throw 'Existing destination overwritten.' } catch {
    if ($_.Exception.Message -eq 'Existing destination overwritten.') { throw }
}
$writer = [IO.File]::Open($source, 'Open', 'ReadWrite', 'ReadWrite')
try {
    try { Copy-Verified $source (Join-Path $folder 'writer-copy.txt'); throw 'Active writer accepted.' } catch {
        if ($_.Exception.Message -eq 'Active writer accepted.') { throw }
    }
} finally { $writer.Dispose() }
if (Test-Path -LiteralPath (Join-Path $folder 'writer-copy.txt')) { throw 'Failed copy published.' }
$target = New-Item -ItemType Directory -Path (Join-Path $folder 'target')
[IO.File]::WriteAllText((Join-Path $target.FullName 'source.txt'), 'harmless junction canary')
$link = New-Item -ItemType Junction -Path (Join-Path $folder 'link') -Target $target.FullName
try { Copy-Verified (Join-Path $link.FullName 'source.txt') (Join-Path $folder 'junction-copy.txt'); throw 'Junction accepted.' } catch {
    if ($_.Exception.Message -eq 'Junction accepted.') { throw }
}
if (Test-Path -LiteralPath (Join-Path $folder 'junction-copy.txt')) { throw 'Junction copy published.' }
'PASS: stable canary copy, exclusive destination, active-writer and reparse rejection; no credentials read.'
