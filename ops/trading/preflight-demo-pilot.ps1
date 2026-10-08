param([switch]$DryRun)
$ErrorActionPreference = 'Stop'
$taskRemote = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'preflight-demo-pilot.py'))
if ($DryRun) {
    $taskRemote | python -B -c 'import sys; compile(sys.stdin.read(), sys.argv[1], sys.argv[2])' pilot-preflight exec
    if ($LASTEXITCODE -ne 0) { throw 'Preflight syntax check failed' }
    Write-Output 'PREFLIGHT_SYNTAX_PASSED; no SSH connection made'
} else {
    $taskRemote | ssh -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=2 root@187.52.117.116 python3 -
    if ($LASTEXITCODE -ne 0) { throw 'Standby preflight failed. Preserve the current deployment and share the diagnostic.' }
}
