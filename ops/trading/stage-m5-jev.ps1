param([switch]$DryRun)
$ErrorActionPreference = 'Stop'
# Uploads the exact reviewed files, runs the read-only journal review and installs the
# read-only M5 scorecard publisher. Runner, journal and deployed source stay unchanged.
$taskNames = @('demo_pilot.py','demo_one_shot.py','mt5_data.py','gold_signal.py','gold_experiment.py','instruments.py','jev_m5.py','control_server.py','status_server.py','cutover-m1-pilot.py','switch-pilot-m5.py','promote-jev-veto.py','jev_m5_scorecard.py')
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
root = pathlib.Path('/opt/kwg-mt5-qualification')
name = 'm5-jev-review-' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-' + uuid.uuid4().hex[:8]
stage = root / name
stage.mkdir(mode=0o700)
for filename, data in bundle.items():
    assert pathlib.Path(filename).name == filename
    (stage / filename).write_bytes(base64.b64decode(data, validate=True))
sources = ('demo_pilot.py','demo_one_shot.py','mt5_data.py','gold_signal.py','gold_experiment.py','instruments.py','jev_m5.py')
hashes = {f: hashlib.sha256((stage/f).read_bytes()).hexdigest() for f in sources}
identity = hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
image = json.loads(subprocess.check_output(['docker','inspect','kwg-mt5-desktop']))[0]['Image']
manifest = dict(code_sha256=identity, sources=hashes, previous_image=image,
                files={f:hashlib.sha256((stage/f).read_bytes()).hexdigest() for f in bundle})
(stage/'manifest.json').write_text(json.dumps(manifest, indent=2))
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
print('M5_JEV_STAGE', str(stage), flush=True)
print('M5_JEV_REVIEWED_CODE', identity, flush=True)
command = ('stty cols 4096; wine /opt/python/python.exe ' + target + '/switch-pilot-m5.py '
           '--journal --reviewed-code-sha256 ' + identity)
subprocess.run(['docker','exec','--user','mt5','kwg-mt5-desktop','script','-q','-e','-c',command,'/dev/null'], check=True)
print('REVIEW_ONLY; runner, journal, and deployed source unchanged', flush=True)

# Read-only scorecard publisher: root-owned copies on the host, never the container-writable volume.
volume = pathlib.Path('/var/lib/docker/volumes/kwg-mt5-qualification_mt5-home/_data/.wine/drive_c/users/mt5')
journal = volume / 'gold-pilot.sqlite3'
receipts = volume / 'jev-m5-receipts.sqlite3'
output = pathlib.Path('/var/lib/docker/volumes/kwg-mt5-qualification_status-snapshot/_data/jev-m5-scorecard.json')
publisher = root / 'jev-m5-scorecard'
assert journal.is_file() and output.parent.is_dir()
def units(command, writable):
    return {
     'kwg-jev-m5-scorecard.service': '[Unit]\nDescription=Read-only Gold M5 Jev shadow scorecard export\n[Service]\nType=oneshot\n'
         'ExecStart=' + ' '.join(command) + '\nNoNewPrivileges=yes\nPrivateNetwork=yes\nProtectSystem=strict\n'
         'ReadWritePaths=' + writable + '\n',
     'kwg-jev-m5-scorecard.timer': '[Unit]\nDescription=Refresh the Gold M5 Jev shadow scorecard every minute\n[Timer]\n'
         'OnBootSec=15\nOnUnitActiveSec=60\nAccuracySec=5\n[Install]\nWantedBy=timers.target\n',
    }
publisher.mkdir(mode=0o700, exist_ok=True)
for filename in ('jev_m5_scorecard.py', 'jev_m5.py'):
    raw = (stage / filename).read_bytes()
    path = publisher / filename
    if path.exists() and path.read_bytes() != raw: raise RuntimeError('Existing publisher differs; review before replacement: ' + filename)
    path.write_bytes(raw)
command = ['/usr/bin/python3', str(publisher / 'jev_m5_scorecard.py'), '--journal', str(journal),
           '--receipts', str(receipts), '--output', str(output)]
for unit, body in units(command, str(output.parent)).items():
    path = pathlib.Path('/etc/systemd/system') / unit
    if path.exists() and path.read_text() != body: raise RuntimeError('Existing unit differs: ' + unit)
    path.write_text(body)
subprocess.run(['systemctl','daemon-reload'], check=True)
subprocess.run(['systemctl','enable','--now','kwg-jev-m5-scorecard.timer'], check=True)
subprocess.run(['systemctl','start','kwg-jev-m5-scorecard.service'], check=True)
value = json.loads(output.read_text())
# Before the switch the journal has no M5 candidates yet, so 'unavailable' is expected here.
print('M5_JEV_SCORECARD_PUBLISHER_INSTALLED', json.dumps({'status': value.get('status')}), flush=True)
'@
$taskRemote = $taskRemote.Replace('PAYLOAD', $taskPayload)
if ($DryRun) {
    $taskRemote | python -B -c 'import sys; compile(sys.stdin.read(), sys.argv[1], sys.argv[2])' m5-jev-stage exec
    if ($LASTEXITCODE -ne 0) { throw 'Staging syntax check failed' }
    Write-Output 'M5_JEV_STAGE_SYNTAX_PASSED; no SSH connection made'
} else {
    $taskRemote | ssh -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=2 root@187.52.117.116 python3 -
    if ($LASTEXITCODE -ne 0) { throw 'M5 Jev review failed. Preserve the stage and share the output; do not replace deployed files.' }
}
