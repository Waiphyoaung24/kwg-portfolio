$ErrorActionPreference = 'Stop'
$taskNames = @('jev_live.py','jev_research.py','gold_signal.py','gold_experiment.py','gold_costs.py','simulate-gold.py','replay-gold.py','compare-gold.py','instruments.py','mt5_data.py')
$taskBundle = @{}
foreach ($taskName in $taskNames) {
  $taskBundle[$taskName] = [Convert]::ToBase64String([IO.File]::ReadAllBytes((Join-Path $PSScriptRoot $taskName)))
}
$taskPayload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($taskBundle | ConvertTo-Json -Compress)))
$taskRoute = @'
        if self.path == '/jev-m15':
            try:
                path = SNAPSHOT.with_name('jev-m15.json')
                if path.stat().st_size > 100000:
                    raise ValueError('Oversized M15 snapshot')
                body = path.read_bytes()
                value = json.loads(body)
                if value.get('status') != 'ready' or not 0 <= time.time()-value['checked_at'] <= 15:
                    raise ValueError('M15 feed unavailable')
            except (OSError, ValueError, KeyError, TypeError):
                self.send_error(503)
                return
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
'@
$taskRoute64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($taskRoute))
$taskRemote = @'
import base64,json,pathlib,subprocess,hashlib
bundle=json.loads(base64.b64decode('PAYLOAD'))
target=pathlib.Path('/var/lib/docker/volumes/kwg-mt5-qualification_mt5-home/_data/jev-observer-v1')
target.mkdir(mode=0o700,exist_ok=True)
for name,data in bundle.items():
 assert pathlib.Path(name).name==name
 raw=base64.b64decode(data)
 compile(raw,name,'exec')
 path=target/name
 if path.exists() and path.read_bytes()!=raw: raise RuntimeError('Existing stage differs: '+name)
 path.write_bytes(raw)
subprocess.run(['chown','-R','10001:10001',str(target)],check=True)
source=pathlib.Path('/opt/kwg-mt5-qualification/status_server.py')
text=source.read_text()
if "self.path == '/jev-m15'" not in text:
 assert text.count('    def do_GET(self):\n')==1
 backup=source.with_name('status_server.before-jev.py')
 with backup.open('xb') as f: f.write(source.read_bytes())
 replacement=text.replace('    def do_GET(self):\n','    def do_GET(self):\n'+base64.b64decode('ROUTE').decode()+'\n')
 compile(replacement,'status_server.py','exec')
 source.write_text(replacement)
 subprocess.run(['docker','restart','kwg-trading-status'],check=True)
unit=pathlib.Path('/etc/systemd/system/kwg-jev-observer.service')
body='''[Unit]
Description=Gold M15 read-only Jev market collector
After=docker.service
Requires=docker.service
[Service]
ExecStart=/usr/bin/docker exec --user mt5 kwg-mt5-desktop script -q -e -c "wine /opt/python/python.exe /home/mt5/jev-observer-v1/jev_live.py" /dev/null
Restart=on-failure
RestartSec=10
[Install]
WantedBy=multi-user.target
'''
if unit.exists() and unit.read_text()!=body: raise RuntimeError('Existing service differs')
unit.write_text(body)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','enable','--now','kwg-jev-observer.service'],check=True)
print('JEV_COLLECTOR_STARTED; trading runner was not restarted')
'@
$taskRemote = $taskRemote.Replace('PAYLOAD',$taskPayload).Replace('ROUTE',$taskRoute64)
$taskRemote | & 'C:/Program Files/Git/usr/bin/ssh.exe' -o BatchMode=yes -o ConnectTimeout=10 root@187.52.117.116 python3 -
if ($LASTEXITCODE -ne 0) { throw 'Jev staging failed; preserve the stage for diagnosis.' }
