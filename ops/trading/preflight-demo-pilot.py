import json, os, pathlib, re, shlex, subprocess

def run(args):
    return subprocess.check_output(args, timeout=60).decode().strip()

desktop = json.loads(run(['docker', 'inspect', 'kwg-mt5-desktop']))[0]
env = dict(item.split('=', 1) for item in desktop['Config']['Env'] if '=' in item)
labels = desktop['Config'].get('Labels') or {}
assert desktop['State']['Running'], 'Desktop is not running'
assert labels.get('com.docker.compose.project.working_dir') == '/opt/kwg-mt5-qualification', 'Unexpected Compose directory'
assert labels.get('com.docker.compose.project.config_files') == '/opt/kwg-mt5-qualification/compose.yml', 'Unexpected Compose files'
assert env.get('MT5_RUN_MODE', 'observer') == 'observer', 'Pilot mode already configured; inspect before redeploying'
assert env.get('MT5_DEMO_LOGIN') == '1344907', 'Unexpected demo login'
assert env.get('MT5_SERVER_OFFSET_SECONDS') == '10800', 'Server offset requires review'
assert len(env.get('TRADING_CONTROL_SECRET', '')) >= 32, 'Control secret missing'
print('DOCKER', json.dumps({'image': desktop['Image'], 'mode': env.get('MT5_RUN_MODE', 'observer'),
    'compose_folder': labels['com.docker.compose.project.working_dir'],
    'mounts': [{'type': m['Type'], 'destination': m['Destination'], 'name': m.get('Name')} for m in desktop['Mounts']]}), flush=True)
run(['docker', 'exec', '--user', 'mt5', 'kwg-mt5-desktop', 'sh', '-c',
     'test -s /home/mt5/.vnc/passwd && test -r /home/mt5/.vnc/passwd'])
print('VNC_PASSWORD_READY', flush=True)

broker = r'''
import json, os, sqlite3
from pathlib import Path
import MetaTrader5 as mt5
assert mt5.initialize(r'C:\Program Files\MetaTrader 5\terminal64.exe', timeout=10000), 'MT5 unavailable'
try:
    a, t = mt5.account_info(), mt5.terminal_info()
    assert a and t and t.connected, 'Demo disconnected'
    assert a.login == int(os.environ['MT5_DEMO_LOGIN']) and a.trade_mode == 0 and a.server == 'VTMarkets-Demo' and a.currency == 'USD', 'Pinned USD demo account required'
    assert not t.trade_allowed, 'Turn Algo Trading off before standby deployment'
    positions, orders = mt5.positions_get(), mt5.orders_get()
    assert positions is not None and orders is not None and not positions and not orders, 'Account must be flat with no pending orders'
    journals = {}
    for name in ('gold-one-shot.sqlite3', 'gold-pilot.sqlite3'):
        path = Path.home() / name
        if not path.exists():
            journals[name] = 'absent'
            continue
        db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
        try:
            assert db.execute('PRAGMA quick_check').fetchone()[0] == 'ok', 'Journal integrity failed'
            row = db.execute('SELECT state FROM attempts ORDER BY rowid DESC LIMIT 1').fetchone()
            assert row is None or row[0] in ('closed', 'disarmed'), 'Resolve existing journal attempt first'
            if name == 'gold-pilot.sqlite3':
                assert db.execute('SELECT count(*) FROM pilot').fetchone()[0] == 0, 'Previously activated pilot requires review'
            journals[name] = row[0] if row else 'empty'
        finally:
            db.close()
    print('BROKER_PREFLIGHT ' + json.dumps(dict(account_match=True, server=a.server, currency=a.currency,
        equity=a.equity, balance=a.balance, algo_trading=False, positions=len(positions), orders=len(orders), journals=journals)))
finally:
    mt5.shutdown()
'''
command = 'stty cols 4096; ' + shlex.join(['wine', '/opt/python/python.exe', '-c', 'exec(bytes.fromhex(' + repr(broker.encode().hex()) + '))'])
output = run(['docker', 'exec', '--user', 'mt5', 'kwg-mt5-desktop',
              'script', '-q', '-e', '-c', command, '/dev/null'])
clean = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', output)
marker = 'BROKER_PREFLIGHT '
if marker not in clean:
    print('BROKER_DIAGNOSTIC', repr(output[-6000:]), flush=True)
    raise SystemExit('Broker preflight receipt missing')
receipt, _ = json.JSONDecoder().raw_decode(clean.split(marker, 1)[1].lstrip())
assert receipt['account_match'] is True and receipt['algo_trading'] is False and receipt['positions'] == receipt['orders'] == 0
print(marker + json.dumps(receipt), flush=True)
for name in ('compose.yml', 'desktop.sh', 'status_server.py', 'trading.html', 'trading-bot.html'):
    path = pathlib.Path('/opt/kwg-mt5-qualification') / name
    assert path.is_file() and not path.is_symlink(), 'Missing or symlinked deployment file: ' + name
run(['docker', 'compose', '-f', '/opt/kwg-mt5-qualification/compose.yml', 'config', '--quiet'])
print('STANDBY_PREFLIGHT_PASSED; no deployment or activation performed', flush=True)
