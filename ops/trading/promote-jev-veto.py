"""Owner-approved Gold M5 Jev mode change; never automatic and never contacts the broker.

Host:      promote-jev-veto.py <stage> --owner-approved [--demote | --demo-test]
Container: promote-jev-veto.py --journal --owner-approved [--demote | --demo-test]
Normal promotion requires a passing read-only scorecard gate. An explicit
--demo-test records an unqualified demo override without changing risk limits. Demotion
(veto -> shadow) is allowed at any time. Both are audited in jev_mode_changes.
"""
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import sqlite3
import subprocess
import sys
import time

# Embedded Wine Python pins /opt/trading; load the reviewed staged siblings instead.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import demo_pilot as pilot
import jev_m5_scorecard as scorecard

ROOT = Path('/opt/kwg-mt5-qualification')
PREFIX = 'm5-jev-review-'
VOLUME = Path('/var/lib/docker/volumes/kwg-mt5-qualification_mt5-home/_data/.wine/drive_c/users/mt5')


def card(journal, receipts, now, *, demote, demo_test=False):
    try:
        value = scorecard.export(journal, receipts, now)
    except Exception:
        if demote:
            return None  # Demotion never waits on the scorecard.
        raise
    if not demote and not demo_test and not value['gate']['passes']:
        raise ValueError('Scorecard gate does not pass: ' + '; '.join(value['gate']['reasons']))
    return value


def expect(p, code, *, demote):
    if p is None or p['strategy'] != pilot.M5_JEV_STRATEGY:
        raise ValueError('Mode change requires the Gold ' + pilot.M5_JEV_STRATEGY + ' pilot')
    if p['code'] != code:
        raise ValueError('Journal code does not match the staged code')
    source, target = ('veto', 'shadow') if demote else ('shadow', 'veto')
    if p.get('jev_mode') != source:
        raise ValueError('Jev mode is ' + str(p.get('jev_mode')) + ', expected ' + source)
    return source, target


def check_demo_test(db, p, value, *, demote):
    if demote or value is None or value.get('status') != 'ready':
        raise ValueError('Demo test requires promotion and a ready scorecard')
    metadata = db.execute('SELECT server, symbol FROM metadata').fetchall()
    if [tuple(r) for r in metadata] != [(pilot.SERVER, pilot.GOLD)]:
        raise ValueError('Demo test requires the pinned Gold demo journal')
    risk = json.loads(db.execute('SELECT data FROM account_limits WHERE id=1').fetchone()[0])
    if p.get('pause') or risk.get('pause'):
        raise ValueError('Demo test cannot clear or bypass a pause')
    if db.execute("SELECT count(*) FROM attempts WHERE state NOT IN ('closed','disarmed')").fetchone()[0]:
        raise ValueError('Demo test requires Gold flat with no unresolved attempts')


def change(db, now, value, *, owner_approved, demote, backup, demo_test=False):
    if owner_approved is not True:
        raise ValueError('Explicit owner approval is required')
    p = pilot.state(db)
    source, target = expect(p, pilot.identity(), demote=demote)
    if demo_test:
        check_demo_test(db, p, value, demote=demote)
    if not demote and not demo_test and (value is None or value['gate']['passes'] is not True):
        raise ValueError('Scorecard gate does not pass')
    digest = value and hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                                 allow_nan=False).encode()).hexdigest()
    with backup.open('xb'):
        pass
    with closing(sqlite3.connect(backup)) as saved:
        db.backup(saved)
        if saved.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
            raise ValueError('Backup integrity check failed')
    with db:
        db.execute('CREATE TABLE IF NOT EXISTS jev_mode_changes (at REAL NOT NULL, from_mode TEXT NOT NULL, '
                   'to_mode TEXT NOT NULL, scorecard_sha256 TEXT)')
        db.execute('INSERT INTO jev_mode_changes VALUES (?, ?, ?, ?)', (now, source, target, digest))
        if demo_test:
            db.execute('CREATE TABLE IF NOT EXISTS jev_demo_tests (at REAL NOT NULL, scorecard_json TEXT NOT NULL)')
            db.execute('INSERT INTO jev_demo_tests VALUES (?, ?)',
                       (now, json.dumps(value, sort_keys=True, allow_nan=False)))
        # Only jev_mode changes; any deferred veto entry is dropped by the runner on restart.
        db.execute('UPDATE pilot SET data=? WHERE id=1', (json.dumps({**p, 'jev_mode': target}, allow_nan=False),))
    return dict(from_mode=source, to_mode=target, scorecard_sha256=digest, backup=str(backup), order_sent=False, demo_test=demo_test)


def journal(args):
    if os.environ.get('MT5_RUN_MODE') != 'pilot':
        raise SystemExit('MT5_RUN_MODE must be pilot')
    home = Path.home()
    if args.demo_test and (home / 'gold-pilot.pause').exists():
        raise ValueError('Owner pause exists')
    path = home / 'gold-pilot.sqlite3'
    if not path.is_file():
        raise ValueError('Gold pilot journal missing')
    with pilot.execution._exclusive(home / 'gold-one-shot.sqlite3'):
        db = sqlite3.connect(path.as_uri() + '?mode=rw', uri=True)
        db.row_factory = sqlite3.Row
        try:
            now = time.time()
            value = card(path, home / 'jev-m5-receipts.sqlite3', now, demote=args.demote, demo_test=args.demo_test)
            result = change(db, now, value, owner_approved=args.owner_approved, demote=args.demote, demo_test=args.demo_test,
                            backup=home / ('gold-pilot-before-jev-mode-' + str(time.time_ns()) + '.sqlite3'))
        finally:
            db.close()
    print('JEV_MODE_CHANGED', json.dumps(result))


def run(args, **kwargs):
    return subprocess.check_output(args, timeout=kwargs.pop('timeout', 60), **kwargs).decode().strip()


def deploy(stage, *, demote, demo_test=False):
    if stage.parent != ROOT or not stage.name.startswith(PREFIX) or stage.is_symlink():
        raise ValueError('Expected a private M5 Jev review stage')
    manifest = json.loads((stage / 'manifest.json').read_text())
    for name, expected in manifest['files'].items():
        if Path(name).name != name or hashlib.sha256((stage / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Stage file identity mismatch')
    # Refuse before stopping the runner; the container step rechecks everything under the lock.
    with closing(sqlite3.connect((VOLUME / 'gold-pilot.sqlite3').resolve().as_uri() + '?mode=ro', uri=True)) as db:
        expect(pilot.state(db), manifest['code_sha256'], demote=demote)
    if not demote:
        value = card(VOLUME / 'gold-pilot.sqlite3', VOLUME / 'jev-m5-receipts.sqlite3', time.time(), demote=False, demo_test=demo_test)
        if demo_test:
            if (VOLUME / 'gold-pilot.pause').exists():
                raise ValueError('Owner pause exists')
            with closing(sqlite3.connect((VOLUME / 'gold-pilot.sqlite3').resolve().as_uri() + '?mode=ro', uri=True)) as db:
                check_demo_test(db, pilot.state(db), value, demote=False)
    import runpy
    import base64
    print('RUNNER_STOPPED', runpy.run_path(str(stage / 'cutover-m1-pilot.py'))['stop_runner'](), flush=True)
    receiver = 'import base64,json,pathlib,sys; root=pathlib.Path(sys.argv[1]); root.mkdir(mode=0o700, exist_ok=True); [ (root/n).write_bytes(base64.b64decode(v)) for n,v in json.load(sys.stdin).items() ]'
    target = '/home/mt5/' + stage.name
    bundle = {n: base64.b64encode((stage / n).read_bytes()).decode() for n in manifest['files']}
    run(['docker', 'exec', '-i', '--user', 'mt5', 'kwg-mt5-desktop', 'python3', '-c', receiver, target],
        input=json.dumps(bundle).encode())
    command = 'stty cols 4096; ' + shlex.join(['wine', '/opt/python/python.exe', target + '/promote-jev-veto.py',
                                             '--journal', '--owner-approved', *(['--demote'] if demote else []),
                                             *(['--demo-test'] if demo_test else [])])
    receipt = run(['docker', 'exec', '--user', 'mt5', 'kwg-mt5-desktop', 'script', '-q', '-e', '-c', command, '/dev/null'])
    print(receipt, flush=True)
    match = re.search(r'JEV_MODE_CHANGED (\{[^\r\n]*\})', receipt)
    expected = 'shadow' if demote else 'veto'
    if match is None or json.loads(match.group(1)).get('to_mode') != expected:
        raise ValueError('Mode change receipt missing; leave runner stopped')
    compose = ['docker', 'compose', '--project-directory', str(ROOT), '-f', str(ROOT / 'compose.yml')]
    run(compose + ['up', '-d', '--no-build', '--pull', 'never', '--no-deps', '--force-recreate', 'desktop'], timeout=120)
    for _ in range(18):
        try:
            read = 'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8000/status",timeout=5).read().decode())'
            report = json.loads(run(['docker', 'exec', 'kwg-trading-status', 'python', '-c', read], stderr=subprocess.DEVNULL))
            p = report.get('pilot') or {}
            if report.get('checked_at', 0) >= time.time() - 30 and p.get('jev_mode') == expected:
                print('JEV_SHADOW_DEMOTED' if demote else 'JEV_VETO_PROMOTED', json.dumps(dict(gold=report, order_sent=False)), flush=True)
                return
        except (subprocess.SubprocessError, ValueError, KeyError):
            pass
        time.sleep(5)
    raise RuntimeError('Fresh Jev mode status not verified; inspect before any retry')


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('stage', nargs='?', type=Path)
    parser.add_argument('--owner-approved', action='store_true')
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--demo-test', action='store_true', help='Explicit unqualified demo veto test; audit the unmet gate')
    modes.add_argument('--demote', action='store_true', help='Return veto to shadow; allowed at any time')
    parser.add_argument('--journal', action='store_true', help='Run the journal step inside the MT5 container')
    args = parser.parse_args()
    if not args.owner_approved:
        parser.error('--owner-approved is required; Jev mode never changes automatically')
    if args.journal == (args.stage is not None):
        parser.error('Use either <stage> on the host or --journal inside the container')
    os.umask(0o077)
    if args.journal:
        journal(args)
        return
    try:
        deploy(args.stage.resolve(), demote=args.demote, demo_test=args.demo_test)
    except Exception:
        print('MODE_CHANGE_INCOMPLETE; if RUNNER_STOPPED was printed, inspect before restarting the desktop', flush=True)
        raise


if __name__ == '__main__':
    main()
