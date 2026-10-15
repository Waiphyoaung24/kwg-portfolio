"""Guarded dual M5 demo veto upgrade and separate reporting-window activation.

Host: upgrade-dual-m5.py <stage> --previous-code-sha256 OLD --reviewed-code-sha256 NEW
      [--owner-approved-btc]
After live verification, repeat on the host with --start-reporting --deployment-verified.
Container: --journal is read-only; --journal --apply requires a stopped runner.
Broker reads verify the pinned demo account is flat; this helper never submits orders.
"""
import argparse
from contextlib import closing, nullcontext
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import shlex
import shutil
import sqlite3
import subprocess
import sys
import time

# Embedded Wine Python pins /opt/trading; review the staged siblings instead.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import demo_pilot as pilot

ROOT = Path('/opt/kwg-mt5-qualification')
PREFIX = 'dual-m5-review-'
UNRESOLVED = "SELECT count(*) FROM attempts WHERE state NOT IN ('closed','disarmed')"


BTC_M5 = 'btc-ema-v1-m5-trend-jev'


def review(gold, btc, home, now, reviewed, previous, owner_approved=False, reporting=False):
    if not all(re.fullmatch(r'[0-9a-f]{64}', h) for h in (reviewed, previous)):
        raise ValueError('Explicit SHA256 identities required')
    if pilot.identity() != reviewed:
        raise ValueError('Loaded code differs from reviewed source')
    if btc is None:
        raise ValueError('Both activated journals required')
    records = [pilot.state(db) for db in (gold, btc)]
    row = gold.execute('SELECT data FROM account_limits WHERE id=1').fetchone()
    if row is None:
        raise ValueError('Shared account limits required')
    risk = json.loads(row[0])
    expected = reviewed if reporting else previous
    if risk['code'] != expected or risk['pause'] is not None:
        raise ValueError('Shared risk identity mismatch or risk pause')
    metadata = []
    for db, symbol, p in zip((gold, btc), (pilot.GOLD, pilot.BTC), records):
        if p is None or p['code'] != expected:
            raise ValueError('Journal identity mismatch')
        meta = [tuple(r) for r in db.execute('SELECT login, server, symbol FROM metadata')]
        if len(meta) != 1 or meta[0][1:] != (pilot.SERVER, symbol):
            raise ValueError('Journal account identity mismatch')
        metadata.append(meta[0][0])
        if any(p[k] != risk[k] for k in ('start', 'end', 'offset')):
            raise ValueError('Shared activation identity mismatch')
        if pilot.expired(p, now):
            raise ValueError('Pilot expired')
        if db.execute(UNRESOLVED).fetchone()[0] or p.get('pending_entry') is not None:
            raise ValueError('Open, unresolved or pending entry; flat journals required')
    if metadata[0] != metadata[1]:
        raise ValueError('Journal logins differ')
    gold_p, btc_p = records
    if gold_p['strategy'] != pilot.M5_JEV_STRATEGY or gold_p.get('jev_mode') != 'veto':
        raise ValueError('Gold must already be M5 veto')
    if gold_p['pause'] is not None or (home / 'gold-pilot.pause').exists():
        raise ValueError('Gold pause requires review')
    if btc_p['pause'] not in (None, 'Paused by owner'):
        raise ValueError('BTC risk pause requires review')
    if (btc_p['pause'] or (home / 'btc-pilot.pause').exists()) and (not owner_approved or reporting):
        raise ValueError('Explicit BTC owner approval required')
    if reporting:
        if btc_p['strategy'] != BTC_M5 or btc_p.get('jev_mode') != 'veto':
            raise ValueError('Both M5 veto strategies required before reporting')
        if any(p.get('reporting_start') is not None or p.get('reporting_end') is not None for p in records):
            raise ValueError('Reporting window already exists; never reset it')
        records = [{**p, 'reporting_start': now, 'reporting_end': now + 172800} for p in records]
    else:
        if btc_p['strategy'] != pilot.BTC_SCALP_STRATEGY:
            raise ValueError('BTC must be the reviewed M1 scalp strategy')
        records = [{**gold_p, 'code': reviewed},
                   {**btc_p, 'code': reviewed, 'strategy': BTC_M5, 'jev_mode': 'veto',
                    'last_bar': None, 'pause': None,
                    'reason': 'M5 Jev veto selected; waiting for a completed candle baseline'}]
        risk = {**risk, 'code': reviewed}
    return records, risk


def switch(gold, btc, home, now, reviewed, previous, backup_dir, owner_approved=False, reporting=False):
    records, risk = review(gold, btc, home, now, reviewed, previous, owner_approved, reporting)
    for db in (gold, btc):
        if db.execute('PRAGMA journal_mode').fetchone()[0] != 'delete':
            raise ValueError('Atomic migration requires rollback journals')
    backup_dir.mkdir(mode=0o700)
    for db, name in ((gold, 'gold'), (btc, 'btc')):
        with closing(sqlite3.connect(backup_dir / (name + '.sqlite3'))) as target:
            db.backup(target)
            if target.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise ValueError('Backup integrity check failed')
    pause = home / 'btc-pilot.pause'
    if pause.exists():
        shutil.copy2(pause, backup_dir / pause.name)
    gold.execute('ATTACH DATABASE ? AS btc_upgrade', (btc.execute('PRAGMA database_list').fetchone()[2],))
    try:
        with gold:
            gold.execute('UPDATE main.account_limits SET data=? WHERE id=1', (json.dumps(risk, allow_nan=False),))
            for table, p in zip(('main.pilot', 'btc_upgrade.pilot'), records):
                gold.execute('UPDATE ' + table + ' SET data=? WHERE id=1', (json.dumps(p, allow_nan=False),))
    finally:
        gold.execute('DETACH DATABASE btc_upgrade')
    # Failure here keeps the owner pause on disk and therefore fails closed on restart.
    if owner_approved and not reporting and pause.exists():
        pause.unlink()
    return dict(gold_strategy=records[0]['strategy'], btc_strategy=records[1]['strategy'],
                jev_mode='veto', code=reviewed, reporting_start=records[0].get('reporting_start'),
                reporting_end=records[0].get('reporting_end'), backup=str(backup_dir), order_sent=False)


def run(args, **kwargs):
    return subprocess.check_output(args, timeout=kwargs.pop('timeout', 60), **kwargs).decode().strip()


def deploy(stage, reviewed, previous, owner_approved=False):
    if stage.parent != ROOT or not stage.name.startswith(PREFIX) or stage.is_symlink():
        raise ValueError('Expected a private M5 Jev review stage')
    manifest = json.loads((stage / 'manifest.json').read_text())
    if manifest.get('previous_code_sha256') != previous or manifest['code_sha256'] != reviewed or 'jev_m5.py' not in manifest['sources']:
        raise ValueError('Reviewed code differs from stage')
    for name, expected in manifest['files'].items():
        if Path(name).name != name or hashlib.sha256((stage / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Stage file identity mismatch')
    if (set(manifest['sources']) != set(pilot.SOURCES) or pilot.digest(manifest['sources']) != reviewed
            or any(manifest['files'][n] != h for n, h in manifest['sources'].items())):
        raise ValueError('Stage source identity mismatch')
    current = json.loads(run(['docker', 'inspect', 'kwg-mt5-desktop']))[0]
    if current['Image'] != manifest['previous_image']:
        raise ValueError('Deployment changed since review')
    inspect_previous = 'import hashlib,json,pathlib,sys; print(json.dumps({n:hashlib.sha256((pathlib.Path("/opt/trading")/n).read_bytes()).hexdigest() for n in json.loads(sys.argv[1])}))'
    deployed = json.loads(run(['docker', 'exec', 'kwg-mt5-desktop', 'python3', '-c', inspect_previous, json.dumps(list(pilot.SOURCES))]))
    if pilot.digest(deployed) != previous:
        raise ValueError('Current container code differs from explicitly reviewed previous identity')
    compose = ['docker', 'compose', '--project-directory', str(ROOT), '-f', str(ROOT / 'compose.yml')]
    desktop = json.loads(run(compose + ['config', '--format', 'json']))['services']['desktop']
    if desktop['image'] != 'kwg-mt5-desktop:qualification' or desktop['environment']['MT5_RUN_MODE'] != 'pilot' or desktop['environment'].get('MT5_PILOT_SYMBOLS') != 'XAUUSD-VIP,BTCUSD':
        raise ValueError('Existing pilot deployment does not match')
    # Run the host-reviewed helper via stdin; do not trust an older container stage copy.
    import base64
    receiver = 'import base64,json,pathlib,sys; root=pathlib.Path(sys.argv[1]); root.mkdir(mode=0o700, exist_ok=True); [ (root/n).write_bytes(base64.b64decode(v)) for n,v in json.load(sys.stdin).items() ]'
    target = '/home/mt5/' + stage.name
    bundle = {n: base64.b64encode((stage / n).read_bytes()).decode() for n in manifest['files']}
    run(['docker', 'exec', '-i', '--user', 'mt5', 'kwg-mt5-desktop', 'python3', '-c', receiver, target],
        input=json.dumps(bundle).encode())
    helper = ['wine', '/opt/python/python.exe', target + '/upgrade-dual-m5.py', '--journal', '--reviewed-code-sha256', reviewed, '--previous-code-sha256', previous]
    if owner_approved:
        helper.append('--owner-approved-btc')
    # Read-only review while the runner still runs: any refusal aborts before anything is stopped or built.
    try:
        reviewed_output = run(['docker', 'exec', '--user', 'mt5', 'kwg-mt5-desktop', 'script', '-q', '-e', '-c',
                               'stty cols 4096; ' + shlex.join(helper), '/dev/null'])
    except subprocess.CalledProcessError as exc:
        raise ValueError('Journal review refused; runner untouched: ' + (exc.output or b'').decode(errors='replace')[-300:]) from exc
    print(reviewed_output, flush=True)
    if 'DUAL_M5_REVIEW_PASSED' not in reviewed_output:
        raise ValueError('Journal review receipt missing; runner untouched')
    backup = ROOT / ('dual-m5-backup-' + str(time.time_ns()))
    backup.mkdir(mode=0o700)
    for name in ('status_server.py', 'compose.yml'):
        shutil.copy2(ROOT / name, backup / name)
    run(['docker', 'cp', 'kwg-mt5-desktop:/opt/trading', str(backup / 'trading')])
    (backup / 'image.txt').write_text(current['Image'] + '\n')
    print('DUAL_M5_BACKUP', backup, flush=True)
    base = 'kwg-mt5-desktop:dual-m5-base-' + backup.name.removeprefix('dual-m5-backup-')
    run(['docker', 'tag', current['Image'], base])
    if run(['docker', 'image', 'inspect', base, '--format', '{{.Id}}']) != current['Image']:
        raise ValueError('Local base image identity mismatch')
    image = 'kwg-mt5-desktop:dual-m5-' + reviewed[:12]
    names = [*pilot.SOURCES, 'control_server.py']
    (stage / 'Dockerfile').write_text('FROM ' + base + '\nCOPY --chmod=0644 ' + ' '.join(names) + ' /opt/trading/\n')
    (stage / '.dockerignore').write_text('*\n!Dockerfile\n' + ''.join('!' + n + '\n' for n in names))
    run(['docker', 'build', '--pull=false', '--network=none', '-t', image, str(stage)], timeout=300)
    inspect = 'import hashlib,json,pathlib,sys; print(json.dumps({n:hashlib.sha256((pathlib.Path("/opt/trading")/n).read_bytes()).hexdigest() for n in json.loads(sys.argv[1])}))'
    actual = json.loads(run(['docker', 'run', '--rm', '--network', 'none', '--entrypoint', 'python3', image,
                             '-c', inspect, json.dumps(names)]))
    if actual != {n: manifest['files'][n] for n in names}:
        raise ValueError('Built image differs from reviewed sources')
    shared = runpy.run_path(str(stage / 'cutover-m1-pilot.py'))
    print('RUNNER_STOPPED', shared['stop_runner'](), flush=True)
    command = 'stty cols 4096; ' + shlex.join([*helper, '--apply'])
    receipt = run(['docker', 'exec', '--user', 'mt5', 'kwg-mt5-desktop', 'script', '-q', '-e', '-c', command, '/dev/null'])
    print(receipt, flush=True)
    match = re.search(r'DUAL_M5_JOURNAL_SWITCHED (\{[^\r\n]*\})', receipt)
    if match is None:
        raise ValueError('Switch receipt missing; leave runner stopped')
    switched = json.loads(match.group(1))
    if (switched.get('gold_strategy') != pilot.M5_JEV_STRATEGY or switched.get('btc_strategy') != BTC_M5
            or switched.get('jev_mode') != 'veto' or switched.get('code') != reviewed
            or switched.get('order_sent') is not False):
        raise ValueError('Unexpected switch result; leave runner stopped')
    shutil.copyfile(stage / 'status_server.py', ROOT / 'status_server.py')
    (ROOT / 'status_server.py').chmod(0o644)
    run(['docker', 'tag', image, 'kwg-mt5-desktop:qualification'])
    run(compose + ['up', '-d', '--no-build', '--pull', 'never', '--no-deps', '--force-recreate', 'desktop', 'status'], timeout=120)
    print('DUAL_M5_RECREATED; verify both live statuses and flatness before starting reporting', flush=True)


def start_reporting(stage, reviewed):
    if stage.parent != ROOT or not stage.name.startswith(PREFIX) or stage.is_symlink():
        raise ValueError('Expected private dual M5 review stage')
    manifest = json.loads((stage / 'manifest.json').read_text())
    if manifest['code_sha256'] != reviewed or pilot.identity() != reviewed:
        raise ValueError('Reporting source identity mismatch')
    for name, expected in manifest['files'].items():
        if Path(name).name != name or hashlib.sha256((stage / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Reporting stage identity mismatch')
    current = json.loads(run(['docker', 'inspect', 'kwg-mt5-desktop']))[0]
    environment = dict(value.split('=', 1) for value in current['Config']['Env'] if '=' in value)
    if environment.get('MT5_RUN_MODE') != 'pilot' or environment.get('MT5_PILOT_SYMBOLS') != 'XAUUSD-VIP,BTCUSD':
        raise ValueError('Reporting requires both configured pilot symbols')
    image = 'kwg-mt5-desktop:dual-m5-' + reviewed[:12]
    if run(['docker', 'image', 'inspect', image, '--format', '{{.Id}}']) != current['Image']:
        raise ValueError('Reporting requires the reviewed deployed image')
    inspect = 'import hashlib,json,pathlib,sys; print(json.dumps({n:hashlib.sha256((pathlib.Path("/opt/trading")/n).read_bytes()).hexdigest() for n in json.loads(sys.argv[1])}))'
    actual = json.loads(run(['docker', 'exec', 'kwg-mt5-desktop', 'python3', '-c', inspect, json.dumps(list(pilot.SOURCES))]))
    if pilot.digest(actual) != reviewed:
        raise ValueError('Current reporting code identity mismatch')
    helper = ['wine', '/opt/python/python.exe', '/home/mt5/' + stage.name + '/upgrade-dual-m5.py',
              '--journal', '--reviewed-code-sha256', reviewed, '--previous-code-sha256', reviewed,
              '--start-reporting', '--deployment-verified']

    def invoke(apply=False):
        command = 'stty cols 4096; ' + shlex.join(helper + (['--apply'] if apply else []))
        return run(['docker', 'exec', '--user', 'mt5', 'kwg-mt5-desktop', 'script', '-q', '-e', '-c', command, '/dev/null'])

    if 'DUAL_M5_REVIEW_PASSED' not in invoke():
        raise ValueError('Reporting flat review refused; runner untouched')
    shared = runpy.run_path(str(stage / 'cutover-m1-pilot.py'))
    print('RUNNER_STOPPED', shared['stop_runner'](), flush=True)
    receipt = invoke(True)
    print(receipt, flush=True)
    match = re.search(r'DUAL_M5_REPORTING_STARTED (\{[^\r\n]*\})', receipt)
    if match is None:
        raise ValueError('Reporting receipt missing; leave runner stopped')
    result = json.loads(match.group(1))
    if (result.get('code') != reviewed or result.get('order_sent') is not False
            or result.get('reporting_end', 0) - result.get('reporting_start', 0) != 172800):
        raise ValueError('Reporting receipt mismatch; leave runner stopped')
    # Restart the same container and immutable image, without rebuilding or changing journals.
    run(['docker', 'restart', 'kwg-mt5-desktop'], timeout=120)
    if json.loads(run(['docker', 'inspect', 'kwg-mt5-desktop']))[0]['Image'] != current['Image']:
        raise ValueError('Container image changed during reporting restart')
    print('DUAL_M5_REPORTING_RESTARTED; verify both fresh live statuses', flush=True)


def journal(args):
    if os.environ.get('MT5_RUN_MODE') != 'pilot' or os.environ.get('MT5_PILOT_SYMBOLS') != 'XAUUSD-VIP,BTCUSD':
        raise ValueError('Pilot runtime requires exactly XAUUSD-VIP,BTCUSD')
    import MetaTrader5 as mt5
    if not mt5.initialize(r'C:\Program Files\MetaTrader 5\terminal64.exe', timeout=10000):
        raise ValueError('MT5 unavailable')
    home = Path.home()
    mode = '?mode=rw' if args.apply else '?mode=ro'
    try:
        with closing(sqlite3.connect((home / 'gold-pilot.sqlite3').as_uri() + mode, uri=True)) as gold, \
             closing(sqlite3.connect((home / 'btc-pilot.sqlite3').as_uri() + mode, uri=True)) as btc:
            gold.row_factory = btc.row_factory = sqlite3.Row
            # Runner owns this lock for its lifetime; only the stopped-runner apply takes it.
            lock = pilot.execution._exclusive(home / 'gold-one-shot.sqlite3') if args.apply else nullcontext()
            with lock:
                login = int(os.environ['MT5_DEMO_LOGIN'])
                pilot.account(mt5, login, enabled=True)
                for db in (gold, btc):
                    if db.execute('SELECT login FROM metadata').fetchone()[0] != login:
                        raise ValueError('Journal differs from pinned account')
                positions, orders = mt5.positions_get(), mt5.orders_get()
                if positions is None or orders is None or positions or orders:
                    raise ValueError('Verified flat broker account required')
                values = (gold, btc, home, time.time(), args.reviewed_code_sha256, args.previous_code_sha256)
                options = dict(owner_approved=args.owner_approved_btc, reporting=args.start_reporting)
                if args.apply:
                    result = switch(*values, home / ('before-dual-m5-' + str(time.time_ns())), **options)
                    marker = 'DUAL_M5_REPORTING_STARTED' if args.start_reporting else 'DUAL_M5_JOURNAL_SWITCHED'
                    print(marker, json.dumps(result), flush=True)
                else:
                    review(*values, **options)
                    print('DUAL_M5_REVIEW_PASSED; order_sent=false', flush=True)
    finally:
        mt5.shutdown()


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('stage', nargs='?', type=Path)
    parser.add_argument('--reviewed-code-sha256', required=True)
    parser.add_argument('--previous-code-sha256', required=True)
    parser.add_argument('--journal', action='store_true')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--owner-approved-btc', action='store_true')
    parser.add_argument('--start-reporting', action='store_true')
    parser.add_argument('--deployment-verified', action='store_true', help='Operator attests both deployed feeds and identities verified')
    args = parser.parse_args()
    if args.journal == (args.stage is not None) or args.apply and not args.journal:
        parser.error('Use <stage> on host or --journal [--apply] inside container')
    if args.start_reporting and not args.deployment_verified:
        parser.error('Reporting requires --deployment-verified after live deployment verification')
    os.umask(0o077)
    if args.journal:
        journal(args)
    else:
        try:
            if args.start_reporting:
                start_reporting(args.stage.resolve(), args.reviewed_code_sha256)
            else:
                deploy(args.stage.resolve(), args.reviewed_code_sha256, args.previous_code_sha256, args.owner_approved_btc)
        except Exception:
            print('CUTOVER_INCOMPLETE; preserve backups; never restore M1 over migrated journals', flush=True)
            raise


if __name__ == '__main__':
    main()
