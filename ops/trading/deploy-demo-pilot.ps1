param([switch]$DryRun)
$ErrorActionPreference = 'Stop'
$taskNames = @('desktop.sh','demo_pilot.py','demo_one_shot.py','gold_experiment.py','instruments.py','gold_signal.py','mt5_data.py','control_server.py','status_server.py','trading.html','trading-bot.html','compose.yml','preflight-demo-pilot.py','deploy-demo-pilot.py')
$taskBundle = @{}
foreach ($taskName in $taskNames) {
    $taskText = [IO.File]::ReadAllText((Join-Path $PSScriptRoot $taskName)).Replace("`r`n", "`n")
    $taskBytes = [Text.Encoding]::UTF8.GetBytes($taskText)
    $taskHash = [Security.Cryptography.SHA256]::Create()
    try { $taskDigest = [BitConverter]::ToString($taskHash.ComputeHash($taskBytes)).Replace('-', '').ToLowerInvariant() }
    finally { $taskHash.Dispose() }
    $taskBundle[$taskName] = @{data=[Convert]::ToBase64String($taskBytes); sha256=$taskDigest}
}
$taskPayload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($taskBundle | ConvertTo-Json -Depth 4 -Compress)))
$taskRemote = @'
import base64, hashlib, json, os, pathlib, runpy, sys, time, uuid
os.umask(0o077)
bundle = json.loads(base64.b64decode('PAYLOAD'))
root = pathlib.Path('/opt/kwg-mt5-qualification')
assert root.is_dir() and not root.is_symlink(), 'Deployment root unavailable'
stage = root / ('pilot-standby-' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-' + uuid.uuid4().hex[:8])
stage.mkdir(mode=0o700)
manifest = {}
for name, entry in bundle.items():
    assert pathlib.Path(name).name == name
    raw = base64.b64decode(entry['data'], validate=True)
    assert hashlib.sha256(raw).hexdigest() == entry['sha256']
    (stage / name).write_bytes(raw)
    manifest[name] = entry['sha256']
(stage / 'manifest.json').write_text(json.dumps(manifest, indent=2))
print('DEPLOYMENT_STAGE ' + str(stage), flush=True)
sys.argv = ['deploy-demo-pilot.py', str(stage)]
runpy.run_path(str(stage / 'deploy-demo-pilot.py'), run_name='__main__')
'@
$taskRemote = $taskRemote.Replace('PAYLOAD', $taskPayload)
if ($DryRun) {
    $taskRemote | python -B -c 'import sys; compile(sys.stdin.read(), sys.argv[1], sys.argv[2])' pilot-transfer exec
    if ($LASTEXITCODE -ne 0) { throw 'Transfer syntax check failed' }
    foreach ($taskName in $taskNames | Where-Object { $_.EndsWith('.py') }) {
        python -B -c 'import pathlib, sys; compile(pathlib.Path(sys.argv[1]).read_bytes(), sys.argv[1], sys.argv[2])' (Join-Path $PSScriptRoot $taskName) exec
        if ($LASTEXITCODE -ne 0) { throw "Source syntax check failed: $taskName" }
    }
    Write-Output 'STANDBY_DEPLOYMENT_SYNTAX_PASSED; no SSH connection or deployment performed'
} else {
    $taskRemote | ssh -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=2 root@187.52.117.116 python3 -
    if ($LASTEXITCODE -ne 0) { throw 'Standby deployment incomplete. Preserve the printed deployment directory and share the output; do not activate trading.' }
}
