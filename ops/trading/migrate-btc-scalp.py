"""Review/migrate continuous BTC to M1 with timed exits; sends no orders."""
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import demo_pilot as pilot
from instruments import GOLD, BTC, BTC_STRATEGY, BTC_SCALP_STRATEGY

PREVIOUS_CODE = '7338be40752337c8ce10bb0e65ac6ac58e3d3c83bc94e395caf56fe3445feb7d'


def review(mt5, gold, btc, login, now, reviewed, previous):
    if reviewed != pilot.identity() or previous != PREVIOUS_CODE:
        raise ValueError('Reviewed code identity mismatch')
    risk = json.loads(gold.execute('SELECT data FROM account_limits WHERE id=1').fetchone()[0])
    records = [pilot.state(db) for db in (gold, btc)]
    if not pilot.continuous(risk) or risk['code'] != previous or risk['pause']:
        raise ValueError('Expected the reviewed continuous deployment without account pause')
    for db, symbol, p in zip((gold, btc), (GOLD, BTC), records):
        if [tuple(r) for r in db.execute('SELECT login, server, symbol FROM metadata')] != [(login, pilot.SERVER, symbol)]:
            raise ValueError('Journal identity mismatch')
        if not pilot.continuous(p) or any(p[k] != risk[k] for k in ('code', 'start', 'end', 'offset')):
            raise ValueError('Continuous journal identity mismatch')
    if records[1]['strategy'] != BTC_STRATEGY or records[1]['pause']:
        raise ValueError('Expected active BTC M15 without pause')
    pilot.account(mt5, login, enabled=True)
    checked = {**risk, 'code': reviewed}
    pilot.limits(mt5, gold, checked, login, now, journals=(gold, btc))
    pilot.check_exposure(mt5, (gold, btc), login, now)
    checked['last_poll'] = now
    updated = [{**p, 'code': reviewed, 'last_poll': now, 'last_bar': None} for p in records]
    updated[1].update(strategy=BTC_SCALP_STRATEGY, reason='M1 timed demo selected; waiting for candle baseline')
    return checked, updated


def migrate(mt5, gold, btc, login, now, reviewed, previous, backup_dir):
    risk, records = review(mt5, gold, btc, login, now, reviewed, previous)
    backup_dir.mkdir(mode=0o700)
    for db, name in ((gold, 'gold'), (btc, 'btc')):
        with closing(sqlite3.connect(backup_dir / (name + '.sqlite3'))) as target:
            db.backup(target)
            if target.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise ValueError('Backup integrity check failed')
        if db.execute('PRAGMA journal_mode').fetchone()[0] != 'delete':
            raise ValueError('Migration requires rollback journals')
    gold.execute('ATTACH DATABASE ? AS btc_migration', (btc.execute('PRAGMA database_list').fetchone()[2],))
    try:
        with gold:
            gold.execute('UPDATE account_limits SET data=? WHERE id=1', (json.dumps(risk, allow_nan=False),))
            for table, p in zip(('main.pilot', 'btc_migration.pilot'), records):
                gold.execute('UPDATE ' + table + ' SET data=? WHERE id=1', (json.dumps(p, allow_nan=False),))
    finally:
        gold.execute('DETACH DATABASE btc_migration')
    return dict(run_policy='continuous', ends_at=None, backup=str(backup_dir),
                gold_pause=records[0]['pause'], btc_pause=records[1]['pause'],
                strategy=BTC_SCALP_STRATEGY, order_sent=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reviewed-code-sha256', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    # The reviewed deployed identity predates the Jev M5 module.
    old = pilot.digest({n: hashlib.sha256((Path(r'Z:\opt\trading') / n).read_bytes()).hexdigest()
                        for n in pilot.SOURCES if n != 'jev_m5.py'})
    if old != PREVIOUS_CODE or os.environ.get('MT5_PILOT_SYMBOLS') != GOLD + ',' + BTC:
        raise ValueError('Deployed source/symbols differ from reviewed version')
    import MetaTrader5 as mt5
    if not mt5.initialize(r'C:\Program Files\MetaTrader 5\terminal64.exe', timeout=10000):
        raise ValueError('MT5 unavailable')
    home, login = Path.home(), int(os.environ['MT5_DEMO_LOGIN'])
    databases = []
    try:
        for name in ('gold', 'btc'):
            path = home / (name + '-pilot.sqlite3')
            db = sqlite3.connect(path.as_uri() + ('?mode=rw' if args.apply else '?mode=ro'), uri=True)
            db.row_factory = sqlite3.Row
            databases.append(db)
        inputs = (mt5, *databases, login, time.time(), args.reviewed_code_sha256, old)
        if args.apply:
            with pilot.execution._exclusive(home / 'gold-one-shot.sqlite3'):
                receipt = migrate(*inputs, home / ('before-btc-scalp-' + str(time.time_ns())))
            print('BTC_SCALP_MIGRATED', json.dumps(receipt))
        else:
            review(*inputs)
            print('BTC_SCALP_REVIEW_PASSED', json.dumps(dict(code=pilot.identity(),
                strategy=BTC_SCALP_STRATEGY, cooldown_seconds=60, exit_seconds=60,
                existing_btc_position_inherits_timer=True, order_sent=False)))
    finally:
        for db in databases:
            db.close()
        mt5.shutdown()


if __name__ == '__main__':
    main()
