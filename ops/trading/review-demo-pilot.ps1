param([switch]$DryRun)
$ErrorActionPreference = 'Stop'
$taskRemote = @'
import json, re, subprocess
command = 'stty cols 4096; wine /opt/python/python.exe /opt/trading/demo_pilot.py preview'
output = subprocess.check_output(['docker', 'exec', '--user', 'mt5', 'kwg-mt5-desktop',
    'script', '-q', '-e', '-c', command, '/dev/null'], timeout=60).decode()
clean = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', output)
marker = '{"mode": "autonomous-demo-preview"'
assert marker in clean, 'Preview receipt missing: ' + repr(output[-2000:])
preview, _ = json.JSONDecoder().raw_decode(clean[clean.index(marker):])
assert preview['order_sent'] is False and preview['max_days'] == 7 and preview['max_positions'] == 1
assert preview['server'] == 'VTMarkets-Demo' and preview['symbol'] == 'XAUUSD-VIP'
print('ACTIVATION_REVIEW', json.dumps(preview), flush=True)
print('REVIEW_ONLY; no activation or orders performed', flush=True)
'@
if ($DryRun) {
    $taskRemote | python -B -c 'import sys; compile(sys.stdin.read(), sys.argv[1], sys.argv[2])' pilot-review exec
    if ($LASTEXITCODE -ne 0) { throw 'Review syntax check failed' }
    Write-Output 'REVIEW_SYNTAX_PASSED; no SSH connection made'
} else {
    $taskRemote | ssh -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=2 root@187.52.117.116 python3 -
    if ($LASTEXITCODE -ne 0) { throw 'Activation review incomplete. Keep Algo Trading off and share the diagnostic.' }
}
