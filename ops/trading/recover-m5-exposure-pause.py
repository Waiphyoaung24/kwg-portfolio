"""Recover only the reviewed dual-M5 exposure mismatch; never submit an order."""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import demo_pilot as pilot

PREVIOUS = '7831738a81a6a409105a62c5c4b2ce5c6f0bba2cf6a4429a64c5e17501de2b85'
PAUSE = 'Journal and broker exposure disagree'


def review(mt5, gold, btc, login, now, home, reviewed):
    if pilot.identity() != reviewed:
        raise ValueError('Reviewed source identity mismatch')
    risk = json.loads(gold.execute('SELECT data FROM account_limits WHERE id=1').fetchone()[0])
    records = [pilot.state(db) for db in (gold, btc)]
    if risk['code'] != PREVIOUS or risk['pause'] != PAUSE or not pilot.continuous(risk):
        raise ValueError('Expected the affected M5 shared account pause')
    for db, symbol, p in zip((gold, btc), (pilot.GOLD, pilot.BTC), records):
        if [tuple(r) for r in db.execute('SELECT login, server, symbol FROM metadata')] != [(login, pilot.SERVER, symbol)]:
            raise ValueError('Journal account identity mismatch')
        if not pilot.continuous(p) or any(p[k] != risk[k] for k in ('code', 'start', 'end', 'offset')):
            raise ValueError('Shared identity mismatch')
        if db.execute("SELECT count(*) FROM attempts WHERE state NOT IN ('closed','disarmed')").fetchone()[0]:
            raise ValueError('Unresolved attempts require review')
    for p, stem, strategy in zip(records, ('gold', 'btc'), (pilot.M5_JEV_STRATEGY, pilot.BTC_M5_JEV_STRATEGY)):
        if (p['strategy'] != strategy or p.get('jev_mode') != 'veto' or p['pause'] != PAUSE
                or p.get('pending_entry') is not None or (home / (stem + '-pilot.pause')).exists()):
            raise ValueError('Expected only the reviewed mismatch pause on both veto pilots')
        if (p.get('reporting_start') != 1792048262.9843044
                or p.get('reporting_end') != 1792221062.9843044):
            raise ValueError('Reporting window differs from the approved trial')
    pilot.account(mt5, login, enabled=True)
    positions, orders = mt5.positions_get(), mt5.orders_get()
    if positions is None or orders is None or positions or orders:
        raise ValueError('Recovery requires a verified flat account')
    checked = {**risk, 'code': reviewed, 'pause': None}
    pilot.limits(mt5, gold, json.loads(json.dumps(checked)), login, now, journals=(gold, btc))
    pilot.check_exposure(mt5, (gold, btc), login, now)
    checked['last_poll'] = now
    updated = [{**p, 'code': reviewed} for p in records]
    for p, stem in zip(updated, ('gold', 'btc')):
        if p['pause'] == PAUSE and not (home / (stem + '-pilot.pause')).exists():
            p.update(pause=None, last_bar=None, last_poll=now,
                     reason='Exposure reconciled and reviewed; waiting for candle baseline')
    return checked, updated


def recover(mt5, gold, btc, login, now, home, reviewed, backup):
    risk, records = review(mt5, gold, btc, login, now, home, reviewed)
    backup.mkdir(mode=0o700)
    for db, name in ((gold, 'gold'), (btc, 'btc')):
        if db.execute('PRAGMA journal_mode').fetchone()[0] != 'delete':
            raise ValueError('Recovery requires rollback journals')
        with closing(sqlite3.connect(backup / (name + '.sqlite3'))) as target:
            db.backup(target)
            if target.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise ValueError('Backup integrity check failed')
    gold.execute('ATTACH DATABASE ? AS btc_recovery', (btc.execute('PRAGMA database_list').fetchone()[2],))
    try:
        with gold:
            gold.execute('UPDATE account_limits SET data=? WHERE id=1', (json.dumps(risk, allow_nan=False),))
            for table, p in zip(('main.pilot', 'btc_recovery.pilot'), records):
                gold.execute('UPDATE ' + table + ' SET data=? WHERE id=1', (json.dumps(p, allow_nan=False),))
    finally:
        gold.execute('DETACH DATABASE btc_recovery')
    return dict(code=reviewed, strategy=records[0]['strategy'], jev_mode=records[0]['jev_mode'],
                gold_pause=records[0]['pause'], btc_pause=records[1]['pause'], backup=str(backup), order_sent=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reviewed-code-sha256', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if os.environ.get('MT5_RUN_MODE') != 'pilot':
        raise ValueError('Expected pilot runtime')
    import MetaTrader5 as mt5
    if not mt5.initialize(r'C:\Program Files\MetaTrader 5\terminal64.exe', timeout=10000):
        raise ValueError('MT5 unavailable')
    home = Path.home()
    mode = '?mode=rw' if args.apply else '?mode=ro'
    try:
        with closing(sqlite3.connect((home / 'gold-pilot.sqlite3').as_uri() + mode, uri=True)) as gold, \
             closing(sqlite3.connect((home / 'btc-pilot.sqlite3').as_uri() + mode, uri=True)) as btc:
            gold.row_factory = btc.row_factory = sqlite3.Row
            login = int(os.environ['MT5_DEMO_LOGIN'])
            if args.apply:
                with pilot.execution._exclusive(home / 'gold-one-shot.sqlite3'):
                    result = recover(mt5, gold, btc, login, time.time(), home, args.reviewed_code_sha256,
                                     home / ('before-m5-exposure-recovery-' + str(time.time_ns())))
                print('M5_EXPOSURE_RECOVERED', json.dumps(result), flush=True)
            else:
                review(mt5, gold, btc, login, time.time(), home, args.reviewed_code_sha256)
                print('M5_EXPOSURE_REVIEW_PASSED; order_sent=false', flush=True)
    finally:
        mt5.shutdown()


if __name__ == '__main__':
    main()
