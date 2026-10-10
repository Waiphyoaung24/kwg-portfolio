$ErrorActionPreference = 'Stop'
$taskSource = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'review-btc-readiness.py')).Replace("`r`n", "`n")
$taskPayload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($taskSource))
$taskRemote = @'
import shlex, subprocess
code = "exec(__import__('base64').b64decode('PAYLOAD'))"
command = 'stty cols 4096; wine /opt/python/python.exe -B -c ' + shlex.quote(code)
try:
    result = subprocess.run(['docker','exec','--user','mt5','kwg-mt5-desktop','script','-q','-e','-c',command,'/dev/null'], timeout=45)
except subprocess.TimeoutExpired:
    raise SystemExit('BTC readiness timed out; no orders requested')
raise SystemExit(result.returncode)
'@
$taskRemote.Replace('PAYLOAD', $taskPayload) | ssh -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=2 root@187.52.117.116 python3 -
if ($LASTEXITCODE -ne 0) { throw 'BTC readiness check failed; no orders or journal changes were requested.' }
