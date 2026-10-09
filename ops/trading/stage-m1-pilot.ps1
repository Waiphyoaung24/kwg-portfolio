param([switch]$DryRun, [switch]$Trend)
$ErrorActionPreference = 'Stop'
$taskNames = @('demo_pilot.py','demo_one_shot.py','mt5_data.py','gold_signal.py','gold_experiment.py','switch-pilot-m1.py','status_server.py')
$taskBundle = @{}
foreach ($taskName in $taskNames) {
    $taskText = [IO.File]::ReadAllText((Join-Path $PSScriptRoot $taskName)).Replace("`r`n", "`n")
    $taskBundle[$taskName] = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($taskText))
}
$taskPayload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($taskBundle | ConvertTo-Json -Compress)))
$taskRemote = @'
import base64, hashlib, json, os, pathlib, subprocess, time, uuid
os.umask(0o077)
bundle = json.loads(base64.b64decode('PAYLOAD'))
name = 'm1-review-' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-' + uuid.uuid4().hex[:8]
stage = pathlib.Path('/opt/kwg-mt5-qualification') / name
stage.mkdir(mode=0o700)
for filename, data in bundle.items():
    assert pathlib.Path(filename).name == filename
    (stage / filename).write_bytes(base64.b64decode(data, validate=True))
sources = ('demo_pilot.py','demo_one_shot.py','mt5_data.py','gold_signal.py','gold_experiment.py')
hashes = {f: hashlib.sha256((stage/f).read_bytes()).hexdigest() for f in sources}
identity = hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
(stage/'manifest.json').write_text(json.dumps(dict(code_sha256=identity, sources=hashes), indent=2))
target = '/home/mt5/' + name
receiver = '''import base64, hashlib, json, os, pathlib, sys
os.umask(0o077)
target = pathlib.Path(sys.argv[1])
target.mkdir(mode=0o700)
for filename, entry in json.load(sys.stdin).items():
    assert pathlib.Path(filename).name == filename
    raw = base64.b64decode(entry['data'], validate=True)
    assert hashlib.sha256(raw).hexdigest() == entry['sha256']
    with (target / filename).open('xb') as output:
        output.write(raw)
'''
transfer = {f.name: dict(data=base64.b64encode(f.read_bytes()).decode(),
                        sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for f in stage.iterdir()}
subprocess.run(['docker','exec','-i','--user','mt5','kwg-mt5-desktop','python3','-c',receiver,target],
               input=json.dumps(transfer).encode(), check=True)
print('M1_STAGE', str(stage), flush=True)
print('M1_REVIEWED_CODE', identity, flush=True)
command = ('stty cols 4096; wine /opt/python/python.exe ' + target + '/switch-pilot-m1.py '
           '--previous-code-sha256 85fa929e80a9cb2d1bf34072df12de5ba954f186db022687ceb41f9bfcb2a08f '
           '--reviewed-code-sha256 ' + identity)
subprocess.run(['docker','exec','--user','mt5','kwg-mt5-desktop','script','-q','-e','-c',command,'/dev/null'], check=True)
print('REVIEW_ONLY; runner, journal, and deployed source unchanged', flush=True)
'@
if ($Trend) {
    $taskRemote = $taskRemote.Replace('85fa929e80a9cb2d1bf34072df12de5ba954f186db022687ceb41f9bfcb2a08f', '2495766af1cda52e60ac7b9c7fd3e0e2bb34f49c69323723c2add0a09653c19e')
    $taskRemote = $taskRemote.Replace('--reviewed-code-sha256 ', '--trend --reviewed-code-sha256 ')
}
$taskRemote = $taskRemote.Replace('PAYLOAD', $taskPayload)
if ($DryRun) {
    $taskRemote | python -B -c 'import sys; compile(sys.stdin.read(), sys.argv[1], sys.argv[2])' m1-stage exec
    if ($LASTEXITCODE -ne 0) { throw 'Staging syntax check failed' }
    Write-Output 'M1_STAGE_SYNTAX_PASSED; no SSH connection made'
} else {
    $taskRemote | ssh -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=2 root@187.52.117.116 python3 -
    if ($LASTEXITCODE -ne 0) { throw 'M1 review failed. Preserve the stage and share the output; do not replace deployed files.' }
}
