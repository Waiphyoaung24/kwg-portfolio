"""Owner-run cutover for the reviewed M1 stage; failures require explicit recovery."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path('/opt/kwg-mt5-qualification')
STAGE = ROOT / 'm1-review-20261009T123727Z-2918ba5f'
CODE = '2495766af1cda52e60ac7b9c7fd3e0e2bb34f49c69323723c2add0a09653c19e'
OLD_CODE = '85fa929e80a9cb2d1bf34072df12de5ba954f186db022687ceb41f9bfcb2a08f'
OLD_IMAGE = 'sha256:9e45c8bb453ca492fb05758b8a7765f11630db81abad6df52694490b80ff2cac'
IMAGE = 'sha256:d43ae354f76bbfb2e3a4e2c39edff8bfd1e7deabd55be95873ea19c3e4d06cfe'
IMAGE_TAG = 'kwg-mt5-desktop:m1-20261009'
TARGET_STRATEGY = 'gold-ema-v1-m1-slope-3'
MIGRATION_FLAGS = ''


def run(args, **kwargs):
    return subprocess.check_output(args, timeout=kwargs.pop('timeout', 60), **kwargs).decode().strip()


def main():
    if sys.argv[1:] != ['--enable-demo-execution']:
        raise SystemExit('Explicit --enable-demo-execution is required; deploy the matching dashboard first')
    os.umask(0o077)
    manifest = json.loads((STAGE / 'manifest.json').read_text())
    assert manifest['code_sha256'] == CODE
    for name, expected in manifest['sources'].items():
        assert Path(name).name == name
        assert hashlib.sha256((STAGE / name).read_bytes()).hexdigest() == expected
    current = json.loads(run(['docker', 'inspect', 'kwg-mt5-desktop']))[0]
    assert current['Image'] == OLD_IMAGE, 'Current deployment changed'
    compose = ['docker', 'compose', '--project-directory', str(ROOT), '-f', str(ROOT / 'compose.yml')]
    config = json.loads(run(compose + ['config', '--format', 'json']))
    assert config['services']['desktop']['image'] == 'kwg-mt5-desktop:qualification'
    assert config['services']['desktop']['environment']['MT5_RUN_MODE'] == 'pilot'
    assert run(['docker', 'image', 'inspect', IMAGE_TAG, '--format', '{{.Id}}']) == IMAGE
    inspect_code = "import hashlib,json,pathlib; names=json.loads(__import__('sys').argv[1]); print(json.dumps({n:hashlib.sha256((pathlib.Path('/opt/trading')/n).read_bytes()).hexdigest() for n in names}))"
    hashes = json.loads(run(['docker', 'run', '--rm', '--network', 'none', '--entrypoint', 'python3', IMAGE,
                             '-c', inspect_code, json.dumps(list(manifest['sources']))]))
    assert hashes == manifest['sources'], 'Image source does not match reviewed stage'
    backup = ROOT / ('m1-cutover-backup-' + str(time.time_ns()))
    backup.mkdir(mode=0o700)
    for name in ('compose.yml', 'status_server.py'):
        shutil.copy2(ROOT / name, backup / name)
    (backup / 'image.txt').write_text(OLD_IMAGE + '\n')
    print('CUTOVER_BACKUP', backup, flush=True)
    # Discover the exact runner ancestry, then stop only it and its restart supervisor.
    stop = '''import os,pathlib,signal,time,json
def args(pid):
    return (pathlib.Path('/proc')/str(pid)/'cmdline').read_bytes().rstrip(b'\\0').split(b'\\0')
def parent(pid):
    return int(next(line.split()[1] for line in (pathlib.Path('/proc')/str(pid)/'status').read_text().splitlines() if line.startswith('PPid:')))
matches=[]
for path in pathlib.Path('/proc').iterdir():
    if path.name.isdigit():
        try:
            if args(path.name)[-2:] == [b'/opt/trading/demo_pilot.py',b'run']: matches.append(int(path.name))
        except (FileNotFoundError,ProcessLookupError,PermissionError): pass
assert len(matches)==1, 'Expected exactly one pilot runner'
runner=matches[0]; shell=parent(runner); script=parent(shell); supervisor=parent(script)
assert args(supervisor)==[b'bash',b'/opt/trading/desktop.sh']
assert args(parent(supervisor))==[b'bash',b'/opt/trading/desktop.sh']
os.kill(supervisor,signal.SIGSTOP)
os.kill(runner,signal.SIGTERM)
for _ in range(100):
    if not (pathlib.Path('/proc')/str(runner)).exists(): break
    time.sleep(.1)
assert not (pathlib.Path('/proc')/str(runner)).exists(), 'Runner did not stop'
print(json.dumps(dict(supervisor=supervisor,runner=runner)))
'''
    stopped = run(['docker', 'exec', '--user', 'mt5', 'kwg-mt5-desktop', 'python3', '-c', stop])
    print('RUNNER_STOPPED', stopped, flush=True)
    target = '/home/mt5/' + STAGE.name
    command = ('stty cols 4096; wine /opt/python/python.exe ' + target + '/switch-pilot-m1.py '
               '--previous-code-sha256 ' + OLD_CODE + ' --reviewed-code-sha256 ' + CODE + ' --enable-demo-execution' + MIGRATION_FLAGS)
    receipt = run(['docker', 'exec', '--user', 'mt5', 'kwg-mt5-desktop', 'script', '-q', '-e', '-c', command, '/dev/null'])
    print(receipt, flush=True)
    assert 'M1_SWITCH_SAVED' in receipt, 'Migration receipt missing; leave runner stopped'
    # The migration creates its SQLite backup in the persistent home volume.
    shutil.copyfile(STAGE / 'status_server.py', ROOT / 'status_server.py')
    (ROOT / 'status_server.py').chmod(0o644)
    run(['docker', 'tag', IMAGE, 'kwg-mt5-desktop:qualification'])
    run(compose + ['up', '-d', '--no-build', '--pull', 'never', '--no-deps', '--force-recreate', 'desktop', 'status'], timeout=120)
    for _ in range(18):
        try:
            report = json.loads(run(['docker', 'exec', 'kwg-trading-status', 'python', '-c',
                "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/status',timeout=5).read().decode())"], stderr=subprocess.DEVNULL))
            p = report.get('pilot') or {}
            if p.get('strategy') == TARGET_STRATEGY and p.get('updated_at', 0) >= time.time()-30:
                assert p['ends_at'] == 1792096151, 'Expiry changed'
                assert run(['docker', 'inspect', 'kwg-mt5-desktop', '--format', '{{.Image}}']) == IMAGE
                print('M1_CUTOVER_STATUS', json.dumps(report), flush=True)
                return
        except (subprocess.SubprocessError, ValueError):
            pass
        time.sleep(5)
    raise RuntimeError('Fresh M1 status not verified; inspect containers before any retry')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('CUTOVER_INCOMPLETE: preserve backups; do not rerun or resume the old supervisor blindly', flush=True)
        raise
