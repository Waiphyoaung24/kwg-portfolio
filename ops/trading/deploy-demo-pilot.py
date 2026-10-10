"""Install the reviewed bundle into standby; never activate demo execution."""
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys
import time


def run(args, **kwargs):
    return subprocess.check_output(args, timeout=kwargs.pop('timeout', 60), **kwargs).decode().strip()


def deploy(stage):
    os.umask(0o077)
    root = Path('/opt/kwg-mt5-qualification')
    manifest = json.loads((stage / 'manifest.json').read_text())
    for name, expected in manifest.items():
        assert Path(name).name == name and not (stage / name).is_symlink(), 'Invalid bundle path'
        assert hashlib.sha256((stage / name).read_bytes()).hexdigest() == expected, 'Bundle hash mismatch: ' + name
    checked = runpy.run_path(str(stage / 'preflight-demo-pilot.py'))
    desktop, env = checked['desktop'], checked['env']
    assert desktop['Image'] == 'sha256:ddaddceb01ab450a9a14f229550307db2c2e2d990f034044af4658b169e14ddc', 'Base image changed; review required'
    compose = ['docker', 'compose', '--project-directory', str(root), '-f', str(root / 'compose.yml')]
    config = json.loads(run(compose + ['config', '--format', 'json']))
    for key in ('MT5_DEMO_LOGIN', 'MT5_SERVER_OFFSET_SECONDS', 'TRADING_CONTROL_SECRET'):
        assert config['services']['desktop']['environment'].get(key) == env.get(key), 'Persisted Compose environment differs: ' + key
    envfile = root / '.env'
    assert envfile.is_file() and not envfile.is_symlink(), 'Expected private Compose .env missing'
    assert config['services']['desktop']['image'] == 'kwg-mt5-desktop:qualification', 'Unexpected image tag'
    backup = stage / 'backup'
    backup.mkdir(mode=0o700)
    files = ('compose.yml', 'desktop.sh', 'status_server.py', 'trading.html', 'trading-bot.html')
    for name in files + ('.env',):
        shutil.copy2(root / name, backup / name)
        (backup / name).chmod(0o600)
    stamp = stage.name.removeprefix('pilot-standby-')
    rollback = 'kwg-mt5-desktop:rollback-pilot-' + stamp
    image = 'kwg-mt5-desktop:pilot-' + stamp
    run(['docker', 'tag', desktop['Image'], rollback])
    (backup / 'image.txt').write_text(desktop['Image'] + '\n' + rollback + '\n')
    journal_code = r'''
import json, sqlite3, sys
from pathlib import Path
source = Path('/home/mt5/.wine/drive_c/users/mt5/gold-one-shot.sqlite3')
target = Path('/home/mt5/backups') / sys.argv[1]
target.parent.mkdir(exist_ok=True)
assert not target.exists()
if source.exists():
    src = sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)
    dst = sqlite3.connect(target)
    try:
        src.backup(dst)
        assert dst.execute('PRAGMA integrity_check').fetchall() == [('ok',)]
    finally:
        dst.close()
        src.close()
    print('JOURNAL_BACKUP_READY')
else:
    print('JOURNAL_ABSENT')
'''
    journal_name = 'before-pilot-' + stamp + '.sqlite3'
    result = run(['docker', 'exec', '--user', 'mt5', 'kwg-mt5-desktop', 'python3', '-c', journal_code, journal_name])
    if result == 'JOURNAL_BACKUP_READY':
        source = '/home/mt5/backups/' + journal_name
        expected = run(['docker', 'exec', 'kwg-mt5-desktop', 'sha256sum', source]).split()[0]
        run(['docker', 'cp', 'kwg-mt5-desktop:' + source, str(backup / journal_name)])
        assert hashlib.sha256((backup / journal_name).read_bytes()).hexdigest() == expected, 'Journal backup mismatch'
    else:
        assert result == 'JOURNAL_ABSENT'
    print(result, flush=True)
    sources = ('desktop.sh', 'demo_pilot.py', 'demo_one_shot.py', 'gold_experiment.py','instruments.py',
               'gold_signal.py', 'mt5_data.py', 'control_server.py')
    (stage / 'Dockerfile').write_text('FROM ' + rollback + '\nCOPY --chmod=0644 ' + ' '.join(sources) + ' /opt/trading/\n')
    (stage / '.dockerignore').write_text('*\n!Dockerfile\n' + ''.join('!' + name + '\n' for name in sources))
    subprocess.run(['docker', 'build', '--pull=false', '--network=none', '-t', image, str(stage)], check=True, timeout=300)
    run(['docker', 'run', '--rm', '--network', 'none', '--entrypoint', 'bash', image, '-n', '/opt/trading/desktop.sh'])
    # Recheck the real terminal immediately before replacing the running services.
    runpy.run_path(str(stage / 'preflight-demo-pilot.py'))
    print('ROLLBACK_DIRECTORY ' + str(backup), flush=True)
    try:
        for name in files:
            shutil.copyfile(stage / name, root / name)
            (root / name).chmod(0o600 if name == 'compose.yml' else 0o644)
        content = envfile.read_text()
        content = re.sub(r'(?m)^(?:export\s+)?MT5_RUN_MODE=.*\n?', '', content)
        envfile.write_text(content.rstrip('\n') + '\nMT5_RUN_MODE=pilot\n')
        envfile.chmod(0o600)
        run(compose + ['config', '--quiet'])
        run(['docker', 'tag', image, 'kwg-mt5-desktop:qualification'])
        subprocess.run(compose + ['up', '-d', '--no-build', '--pull', 'never', '--no-deps', '--force-recreate', 'desktop', 'status'], check=True, timeout=120)
        snapshot = None
        for attempt in range(24):
            try:
                snapshot = json.loads(run(['docker', 'exec', 'kwg-trading-status', 'python', '-c',
                    'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8000/status", timeout=5).read().decode())']))
                p = snapshot.get('pilot') or {}
                if snapshot.get('mode') == 'autonomous-demo' and p.get('status') == 'standby':
                    assert p.get('started_at') is None and p.get('ends_at') is None, 'Unexpected activated pilot'
                    assert snapshot.get('execution', {}).get('status') == 'disarmed', 'Unexpected execution state'
                    health = snapshot.get('health') or {}
                    if health.get('terminal') == 'connected' and health.get('quote') == 'fresh':
                        break
            except (subprocess.SubprocessError, ValueError):
                pass
            time.sleep(5)
        else:
            raise RuntimeError('Standby did not produce a fresh connected report; inspect private logs')
        current = json.loads(run(['docker', 'inspect', 'kwg-mt5-desktop']))[0]
        assert current['Image'] == run(['docker', 'image', 'inspect', image, '--format', '{{.Id}}'])
        assert sorted(current['Mounts'], key=lambda m: m['Destination']) == sorted(desktop['Mounts'], key=lambda m: m['Destination']), 'Persistent mounts changed'
        (stage / 'standby-status.json').write_text(json.dumps(snapshot, indent=2))
        print('STANDBY_DEPLOYED ' + json.dumps(dict(image=current['Image'], pilot=p,
              terminal=health['terminal'], quote=health['quote'], activation_performed=False)), flush=True)
    except BaseException:
        print('DEPLOYMENT_INCOMPLETE; preserve journals and inspect ' + str(backup) + ' before recovery', flush=True)
        raise


if __name__ == '__main__':
    deploy(Path(sys.argv[1]).resolve())
