$ErrorActionPreference = 'Stop'
# Adds a read-only exporter beside the frozen bundle; never replaces its evaluator or collector.
$taskSource = [Convert]::ToBase64String([IO.File]::ReadAllBytes((Join-Path $PSScriptRoot 'jev_scorecard.py')))
$taskServer = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'status_server.py'))
$taskStart = $taskServer.IndexOf("        if self.path == '/jev-scorecard':")
$taskEnd = $taskServer.IndexOf("        if self.path == '/jev-m15':", $taskStart)
if ($taskStart -lt 0 -or $taskEnd -lt $taskStart) { throw 'Scorecard route missing' }
$taskRoute = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($taskServer.Substring($taskStart, $taskEnd-$taskStart)))
$taskRemote = @'
import base64,pathlib,subprocess
home=pathlib.Path('/var/lib/docker/volumes/kwg-mt5-qualification_mt5-home/_data')
bundle=home/'jev-observer-v1'
state=home/'.wine/drive_c/users/mt5/jev-m15-live-v1.sqlite3'
output=pathlib.Path('/var/lib/docker/volumes/kwg-mt5-qualification_status-snapshot/_data/jev-scorecard.json')
assert bundle.is_dir() and state.is_file() and output.parent.is_dir()
script=bundle/'jev_scorecard.py'
raw=base64.b64decode('SOURCE')
compile(raw,str(script),'exec')
if script.exists() and script.read_bytes()!=raw: raise RuntimeError('Existing exporter differs; review before replacement')
script.write_bytes(raw)
command=['/usr/bin/python3',str(script),'--state',str(state),'--output',str(output)]
subprocess.run(command,check=True)
import json
value=json.loads(output.read_text())
assert value['status']=='ready', 'Exporter failed frozen journal checks'
source=pathlib.Path('/opt/kwg-mt5-qualification/status_server.py')
text=source.read_text()
route=base64.b64decode('ROUTE').decode().replace('\r\n','\n')
if "self.path == '/jev-scorecard'" not in text:
 assert text.count('    def do_GET(self):\n')==1
 replacement=text.replace('    def do_GET(self):\n','    def do_GET(self):\n'+route)
 compile(replacement,str(source),'exec')
 with source.with_name('status_server.before-scorecard.py').open('xb') as backup: backup.write(source.read_bytes())
 source.write_text(replacement)
 subprocess.run(['docker','restart','kwg-trading-status'],check=True)
units={
 'kwg-jev-scorecard.service':'[Unit]\nDescription=Read-only Gold M15 diagnostic outcome export\n[Service]\nType=oneshot\nExecStart='+ ' '.join(command)+'\n',
 'kwg-jev-scorecard.timer':'[Unit]\nDescription=Refresh Gold M15 diagnostic outcomes\n[Timer]\nOnBootSec=15\nOnUnitActiveSec=60\n[Install]\nWantedBy=timers.target\n'
}
for name,body in units.items():
 path=pathlib.Path('/etc/systemd/system')/name
 if path.exists() and path.read_text()!=body: raise RuntimeError('Existing unit differs: '+name)
 path.write_text(body)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','enable','--now','kwg-jev-scorecard.timer'],check=True)
print(json.dumps({'status':value['status'],'samples':value['samples'],'eligible':len(value['outcomes'])}))
print('Read-only exporter installed; collector, trading runner, journal and provider budget unchanged')
'@
$taskRemote = $taskRemote.Replace('SOURCE', $taskSource).Replace('ROUTE', $taskRoute)
$taskRemote | & 'C:/Program Files/Git/usr/bin/ssh.exe' -o BatchMode=yes -o ConnectTimeout=10 root@187.52.117.116 python3 -
if ($LASTEXITCODE -ne 0) { throw 'Scorecard staging failed; preserve files for diagnosis.' }
