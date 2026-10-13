"""Reviewed Gold M5 Jev shadow cutover; journal-only, never contacts the broker.

Host:      switch-pilot-m5.py <stage> --reviewed-code-sha256 <hash>
Container: switch-pilot-m5.py --journal --reviewed-code-sha256 <hash> [--apply]
The container form is read-only review unless --apply; --apply runs only after
the host has stopped the runner, and holds the runner lock while it writes.
"""
import argparse
from contextlib import closing
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
PREFIX = 'm5-jev-review-'
UNRESOLVED = "SELECT count(*) FROM attempts WHERE state NOT IN ('closed','disarmed')"


def deployed_code(directory):
    # The deployed identity predates the Jev M5 module.
    return pilot.digest({name: hashlib.sha256((Path(directory) / name).read_bytes()).hexdigest()
                         for name in pilot.SOURCES if name != 'jev_m5.py'})


def review(gold, btc, home, now, reviewed, previous):
    if pilot.identity() != reviewed:
        raise ValueError('Loaded code does not match reviewed staging code: ' + str(pilot.__file__))
    p = pilot.state(gold)
    if p is None or p['strategy'] != pilot.TREND_STRATEGY:
        raise ValueError('Switch requires an activated Gold ' + pilot.TREND_STRATEGY + ' pilot')
    if p['code'] != previous:
        raise ValueError('Activated journal code does not match deployed source')
    if p['pause'] is not None:
        raise ValueError('Gold pilot is paused: ' + str(p['pause']))
    if (home / 'gold-pilot.pause').exists():
        raise ValueError('Owner pause exists')
    if pilot.expired(p, now):
        raise ValueError('Original pilot window has ended')
    if gold.execute(UNRESOLVED).fetchone()[0]:
        raise ValueError('Gold attempt is open or unresolved; switch only while flat')
    risk = other = None
    if gold.execute("SELECT name FROM sqlite_master WHERE name='account_limits'").fetchone():
        risk = json.loads(gold.execute('SELECT data FROM account_limits WHERE id=1').fetchone()[0])
        if risk['pause']:
            raise ValueError('Shared account limits pause is latched: ' + str(risk['pause']))
        if risk['code'] != previous:
            raise ValueError('Shared account limits code does not match deployed source')
        if btc is None:
            raise ValueError('Shared account limits require the BTC journal')
        other = pilot.state(btc)
        if other is not None and other['code'] != previous:
            raise ValueError('BTC journal code does not match deployed source')
        risk = {**risk, 'code': reviewed}
        # The runner requires every shared journal to carry the loaded code; only that field changes.
        other = other and {**other, 'code': reviewed}
    elif btc is not None:
        raise ValueError('BTC journal without shared account limits requires review')
    # Start/end, limits, offset and equity history are kept; the next candle is a baseline.
    updated = {**p, 'strategy': pilot.M5_JEV_STRATEGY, 'jev_mode': 'shadow', 'code': reviewed,
               'last_bar': None, 'reason': 'M5 Jev shadow selected; waiting for a new completed candle baseline'}
    updated.pop('pending_entry', None)
    return updated, risk, other


def switch(gold, btc, home, now, reviewed, previous, backup_dir):
    p, risk, other = review(gold, btc, home, now, reviewed, previous)
    backup_dir.mkdir(mode=0o700)
    for db, name in ((gold, 'gold'), (btc, 'btc')):
        if db is None:
            continue
        with closing(sqlite3.connect(backup_dir / (name + '.sqlite3'))) as target:
            db.backup(target)
            if target.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise ValueError('Backup integrity check failed')
    if other is None:
        with gold:
            if risk is not None:
                gold.execute('UPDATE account_limits SET data=? WHERE id=1', (json.dumps(risk, allow_nan=False),))
            gold.execute('UPDATE pilot SET data=? WHERE id=1', (json.dumps(p, allow_nan=False),))
    else:
        for db in (gold, btc):
            if db.execute('PRAGMA journal_mode').fetchone()[0] != 'delete':
                raise ValueError('Switch requires rollback journals')
        gold.execute('ATTACH DATABASE ? AS btc_switch', (btc.execute('PRAGMA database_list').fetchone()[2],))
        try:
            # SQLite's attached rollback-journal transaction commits both files together.
            with gold:
                gold.execute('UPDATE account_limits SET data=? WHERE id=1', (json.dumps(risk, allow_nan=False),))
                gold.execute('UPDATE main.pilot SET data=? WHERE id=1', (json.dumps(p, allow_nan=False),))
                gold.execute('UPDATE btc_switch.pilot SET data=? WHERE id=1', (json.dumps(other, allow_nan=False),))
        finally:
            gold.execute('DETACH DATABASE btc_switch')
    return dict(strategy=p['strategy'], jev_mode=p['jev_mode'], code=reviewed, ends_at=p['end'],
                btc_code_updated=other is not None, backup=str(backup_dir), order_sent=False)


def run(args, **kwargs):
    return subprocess.check_output(args, timeout=kwargs.pop('timeout', 60), **kwargs).decode().strip()


def deploy(stage, reviewed):
    if stage.parent != ROOT or not stage.name.startswith(PREFIX) or stage.is_symlink():
        raise ValueError('Expected a private M5 Jev review stage')
    manifest = json.loads((stage / 'manifest.json').read_text())
    if manifest['code_sha256'] != reviewed or 'jev_m5.py' not in manifest['sources']:
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
    compose = ['docker', 'compose', '--project-directory', str(ROOT), '-f', str(ROOT / 'compose.yml')]
    desktop = json.loads(run(compose + ['config', '--format', 'json']))['services']['desktop']
    if desktop['image'] != 'kwg-mt5-desktop:qualification' or desktop['environment']['MT5_RUN_MODE'] != 'pilot':
        raise ValueError('Existing pilot deployment does not match')
    # Run the host-reviewed helper via stdin; do not trust an older container stage copy.
    import base64
    receiver = 'import base64,json,pathlib,sys; root=pathlib.Path(sys.argv[1]); root.mkdir(mode=0o700, exist_ok=True); [ (root/n).write_bytes(base64.b64decode(v)) for n,v in json.load(sys.stdin).items() ]'
    target = '/home/mt5/' + stage.name
    bundle = {n: base64.b64encode((stage / n).read_bytes()).decode() for n in manifest['files']}
    run(['docker', 'exec', '-i', '--user', 'mt5', 'kwg-mt5-desktop', 'python3', '-c', receiver, target],
        input=json.dumps(bundle).encode())
    helper = ['wine', '/opt/python/python.exe', target + '/switch-pilot-m5.py', '--journal', '--reviewed-code-sha256', reviewed]
    # Read-only review while the runner still runs: any refusal aborts before anything is stopped or built.
    try:
        reviewed_output = run(['docker', 'exec', '--user', 'mt5', 'kwg-mt5-desktop', 'script', '-q', '-e', '-c',
                               'stty cols 4096; ' + shlex.join(helper), '/dev/null'])
    except subprocess.CalledProcessError as exc:
        raise ValueError('Journal review refused; runner untouched: ' + (exc.output or b'').decode(errors='replace')[-300:]) from exc
    print(reviewed_output, flush=True)
    if 'M5_JEV_REVIEW_PASSED' not in reviewed_output:
        raise ValueError('Journal review receipt missing; runner untouched')
    backup = ROOT / ('m5-jev-backup-' + str(time.time_ns()))
    backup.mkdir(mode=0o700)
    shutil.copy2(ROOT / 'status_server.py', backup / 'status_server.py')
    (backup / 'image.txt').write_text(current['Image'] + '\n')
    print('M5_JEV_BACKUP', backup, flush=True)
    base = 'kwg-mt5-desktop:m5-jev-base-' + backup.name.removeprefix('m5-jev-backup-')
    run(['docker', 'tag', current['Image'], base])
    if run(['docker', 'image', 'inspect', base, '--format', '{{.Id}}']) != current['Image']:
        raise ValueError('Local base image identity mismatch')
    image = 'kwg-mt5-desktop:m5-jev-' + reviewed[:12]
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
    match = re.search(r'M5_JEV_JOURNAL_SWITCHED (\{[^\r\n]*\})', receipt)
    if match is None:
        raise ValueError('Switch receipt missing; leave runner stopped')
    switched = json.loads(match.group(1))
    if (switched.get('strategy') != pilot.M5_JEV_STRATEGY or switched.get('jev_mode') != 'shadow'
            or switched.get('code') != reviewed or switched.get('order_sent') is not False):
        raise ValueError('Unexpected switch result; leave runner stopped')
    shutil.copyfile(stage / 'status_server.py', ROOT / 'status_server.py')
    (ROOT / 'status_server.py').chmod(0o644)
    run(['docker', 'tag', image, 'kwg-mt5-desktop:qualification'])
    run(compose + ['up', '-d', '--no-build', '--pull', 'never', '--no-deps', '--force-recreate', 'desktop', 'status'], timeout=120)
    seen = None
    for _ in range(18):
        try:
            read = 'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8000/status",timeout=5).read().decode())'
            report = json.loads(run(['docker', 'exec', 'kwg-trading-status', 'python', '-c', read], stderr=subprocess.DEVNULL))
            p = report.get('pilot') or {}
            if report.get('checked_at', 0) >= time.time() - 30 and p.get('strategy') == pilot.M5_JEV_STRATEGY:
                if p.get('jev_mode') != 'shadow' or p.get('ends_at') != switched['ends_at']:
                    raise RuntimeError('M5 status mismatch; preserve backup and inspect')
                if p.get('status') != 'active':
                    # A pause latched at startup (identity, clock, limits) shows here; the switch refused all earlier pauses.
                    raise RuntimeError('M5 runner not active after restart: ' + str(p.get('status')) + ': ' + str(p.get('reason')))
                # Require two consecutive active polls, so a pause latched on the second poll is not missed.
                if seen is None or report['checked_at'] == seen:
                    seen = report['checked_at']
                    time.sleep(5)
                    continue
                print('M5_JEV_SHADOW_DEPLOYED', json.dumps(dict(gold=report, order_sent=False)), flush=True)
                return
        except (subprocess.SubprocessError, ValueError, KeyError):
            pass
        time.sleep(5)
    raise RuntimeError('Fresh M5 status not verified; preserve backup and inspect')


def journal(args):
    if os.environ.get('MT5_RUN_MODE') != 'pilot':
        raise SystemExit('MT5_RUN_MODE must be pilot')
    home = Path.home()
    previous = deployed_code(r'Z:\opt\trading')
    mode = '?mode=rw' if args.apply else '?mode=ro'
    paths = [home / 'gold-pilot.sqlite3', home / 'btc-pilot.sqlite3']
    databases = []
    try:
        for path in paths:
            if path.exists():
                db = sqlite3.connect(path.as_uri() + mode, uri=True)
                db.row_factory = sqlite3.Row
                databases.append(db)
            else:
                databases.append(None)
        gold, btc = databases
        if gold is None:
            raise ValueError('Gold pilot journal missing')
        if args.apply:
            with pilot.execution._exclusive(home / 'gold-one-shot.sqlite3'):
                result = switch(gold, btc, home, time.time(), args.reviewed_code_sha256, previous,
                                home / ('before-m5-jev-' + str(time.time_ns())))
            print('M5_JEV_JOURNAL_SWITCHED', json.dumps(result))
        else:
            p, risk, other = review(gold, btc, home, time.time(), args.reviewed_code_sha256, previous)
            print('M5_JEV_REVIEW_PASSED', json.dumps(dict(strategy=p['strategy'], jev_mode=p['jev_mode'], code=p['code'],
                  ends_at=p['end'], btc_code_updated=other is not None, order_sent=False)))
    finally:
        for db in databases:
            if db is not None:
                db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('stage', nargs='?', type=Path)
    parser.add_argument('--reviewed-code-sha256', required=True)
    parser.add_argument('--journal', action='store_true', help='Run the journal step inside the MT5 container')
    parser.add_argument('--apply', action='store_true', help='With --journal: write under the runner lock')
    args = parser.parse_args()
    if args.journal == (args.stage is not None) or args.apply and not args.journal:
        parser.error('Use either <stage> on the host or --journal inside the container')
    os.umask(0o077)
    if args.journal:
        journal(args)
        return
    try:
        deploy(args.stage.resolve(), args.reviewed_code_sha256)
    except Exception:
        print('CUTOVER_INCOMPLETE; preserve backups and inspect before retrying or restoring the old runner', flush=True)
        raise


if __name__ == '__main__':
    main()
