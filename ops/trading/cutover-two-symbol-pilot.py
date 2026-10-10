"""Deploy a reviewed two-symbol stage in BTC standby; keep gold state intact."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import shlex
import shutil
import subprocess
import time

ROOT = Path('/opt/kwg-mt5-qualification')


def run(args, **kwargs):
    return subprocess.check_output(args, timeout=kwargs.pop('timeout', 60), **kwargs).decode().strip()


def deploy(stage, reviewed):
    if stage.parent != ROOT or not stage.name.startswith('two-symbol-review-') or stage.is_symlink():
        raise ValueError('Expected a private two-symbol review stage')
    manifest = json.loads((stage / 'manifest.json').read_text())
    if manifest['code_sha256'] != reviewed:
        raise ValueError('Reviewed code differs from stage')
    for name, expected in manifest['files'].items():
        if Path(name).name != name or hashlib.sha256((stage/name).read_bytes()).hexdigest() != expected:
            raise ValueError('Stage file identity mismatch')
    current = json.loads(run(['docker', 'inspect', 'kwg-mt5-desktop']))[0]
    if current['Image'] != manifest['previous_image']:
        raise ValueError('Deployment changed since review')
    compose = ['docker', 'compose', '--project-directory', str(ROOT), '-f', str(ROOT/'compose.yml')]
    config = json.loads(run(compose + ['config', '--format', 'json']))
    desktop = config['services']['desktop']
    if (desktop['image'] != 'kwg-mt5-desktop:qualification'
            or desktop['environment']['MT5_RUN_MODE'] != 'pilot'
            or desktop['environment'].get('MT5_PILOT_SYMBOLS', 'XAUUSD-VIP') != 'XAUUSD-VIP'):
        raise ValueError('Expected the existing single-symbol pilot deployment')
    # Render a private override without copying resolved secrets into a new Compose file.
    compose_text = (ROOT/'compose.yml').read_text()
    if compose_text.count('      MT5_RUN_MODE:') != 1:
        raise ValueError('Compose layout changed; review before editing')
    if 'MT5_PILOT_SYMBOLS:' in compose_text:
        raise ValueError('Existing symbol configuration requires review')
    updated = compose_text.replace('      MT5_RUN_MODE:', '      MT5_PILOT_SYMBOLS: "XAUUSD-VIP,BTCUSD"\n      MT5_RUN_MODE:')
    backup = ROOT / ('two-symbol-backup-' + str(time.time_ns()))
    backup.mkdir(mode=0o700)
    for name in ('compose.yml', 'status_server.py'):
        shutil.copy2(ROOT/name, backup/name)
    (backup/'image.txt').write_text(current['Image'] + '\n')
    print('TWO_SYMBOL_BACKUP', backup, flush=True)
    image = 'kwg-mt5-desktop:two-symbol-' + reviewed[:12]
    base = 'kwg-mt5-desktop:two-symbol-base-' + backup.name.removeprefix('two-symbol-backup-')
    run(['docker', 'tag', current['Image'], base])
    if run(['docker', 'image', 'inspect', base, '--format', '{{.Id}}']) != current['Image']:
        raise ValueError('Local base image identity mismatch')
    names = [*manifest['sources'], 'control_server.py']
    (stage/'Dockerfile').write_text('FROM ' + base + '\nCOPY --chmod=0644 ' + ' '.join(names) + ' /opt/trading/\n')
    (stage/'.dockerignore').write_text('*\n!Dockerfile\n' + ''.join('!'+n+'\n' for n in names))
    run(['docker', 'build', '--pull=false', '--network=none', '-t', image, str(stage)], timeout=300)
    expected = {n:manifest['files'][n] for n in names}
    inspect = 'import hashlib,json,pathlib,sys; print(json.dumps({n:hashlib.sha256((pathlib.Path("/opt/trading")/n).read_bytes()).hexdigest() for n in json.loads(sys.argv[1])}))'
    actual = json.loads(run(['docker', 'run', '--rm', '--network', 'none', '--entrypoint', 'python3', image,
                             '-c', inspect, json.dumps(names)]))
    if actual != expected:
        raise ValueError('Built image differs from reviewed sources')
    shared = runpy.run_path(str(stage/'cutover-m1-pilot.py'))
    print('RUNNER_STOPPED', shared['stop_runner'](), flush=True)
    # Run the host-reviewed helper via stdin; do not trust an older container stage copy.
    receiver = 'import base64,json,pathlib,sys; root=pathlib.Path(sys.argv[1]); [ (root/n).write_bytes(base64.b64decode(v)) for n,v in json.load(sys.stdin).items() ]'
    import base64
    target = '/home/mt5/' + stage.name
    bundle = {n:base64.b64encode((stage/n).read_bytes()).decode() for n in manifest['files']}
    run(['docker','exec','-i','--user','mt5','kwg-mt5-desktop','python3','-c',receiver,target], input=json.dumps(bundle).encode())
    command = 'stty cols 4096; ' + shlex.join(['wine', '/opt/python/python.exe', target+'/migrate-two-symbol-pilot.py',
                                             '--reviewed-code-sha256', reviewed, '--apply'])
    receipt = run(['docker','exec','--user','mt5','kwg-mt5-desktop','script','-q','-e','-c',command,'/dev/null'])
    print(receipt, flush=True)
    match = re.search(r'TWO_SYMBOL_MIGRATED (\{[^\r\n]*\})', receipt)
    if match is None:
        raise ValueError('Migration receipt missing; leave runner stopped')
    migrated = json.loads(match.group(1))
    if migrated.get('btc_status') != 'standby' or migrated.get('order_sent') is not False:
        raise ValueError('Unexpected migration result; leave runner stopped')
    shutil.copyfile(stage/'status_server.py', ROOT/'status_server.py')
    (ROOT/'status_server.py').chmod(0o644)
    (ROOT/'compose.yml').write_text(updated)
    run(['docker', 'tag', image, 'kwg-mt5-desktop:qualification'])
    run(compose + ['up','-d','--no-build','--pull','never','--no-deps','--force-recreate','desktop','status'], timeout=120)
    for _ in range(18):
        try:
            read = 'import json,urllib.request; print(json.dumps([json.load(urllib.request.urlopen("http://127.0.0.1:8000/status"+q,timeout=5)) for q in ("","?symbol=BTCUSD")]))'
            gold, btc = json.loads(run(['docker','exec','kwg-trading-status','python','-c',read], stderr=subprocess.DEVNULL))
            if all(r['checked_at'] >= time.time()-30 for r in (gold,btc)) and btc.get('pilot',{}).get('status') == 'standby':
                if (gold['symbol'] != 'XAUUSD-VIP' or btc['symbol'] != 'BTCUSD'
                        or gold['pilot']['ends_at'] != migrated['ends_at']
                        or migrated['gold_pause'] and gold['pilot']['reason'] != migrated['gold_pause']):
                    raise ValueError('Cross-symbol status mismatch')
                print('TWO_SYMBOL_STANDBY_DEPLOYED', json.dumps(dict(gold=gold, btc=btc, btc_activation_performed=False)), flush=True)
                return
        except (subprocess.SubprocessError, ValueError, KeyError):
            pass
        time.sleep(5)
    raise RuntimeError('Fresh two-symbol status not verified; preserve backup and inspect')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', type=Path)
    parser.add_argument('--reviewed-code-sha256', required=True)
    args = parser.parse_args()
    os.umask(0o077)
    try:
        deploy(args.stage.resolve(), args.reviewed_code_sha256)
    except Exception:
        print('CUTOVER_INCOMPLETE; preserve backups and inspect before retrying or restoring the old runner', flush=True)
        raise
