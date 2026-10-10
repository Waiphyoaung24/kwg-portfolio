"""Review or migrate the existing gold journal; never submit an order."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import time

# Embedded Wine Python pins /opt/trading; load the reviewed staged siblings.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import demo_pilot as pilot
from instruments import GOLD

PREVIOUS_CODE = '4e00c3fa04b2f130a26fc46f754b1380e2a4891c5b23eba3b2c56f71ef955eb1'


def review(mt5, gold, login, now, reviewed_code, previous_code):
    p = pilot.state(gold)
    if (p is None or p['code'] != previous_code or reviewed_code != pilot.identity()
            or p['strategy'] != pilot.TREND_STRATEGY):
        raise ValueError('Previous or reviewed code identity mismatch')
    if gold.execute("SELECT name FROM sqlite_master WHERE name='account_limits'").fetchone():
        raise ValueError('Two-symbol migration already exists; inspect before retrying')
    if not p['start'] <= now < p['end']:
        raise ValueError('Original pilot window has ended')
    if p['pause'] not in (None, 'Pinned USD demo account unavailable', 'Paused by owner'):
        raise ValueError('Existing pause requires separate reconciliation')
    pilot.account(mt5, login, enabled=True)
    risk = {**p, 'code': reviewed_code, 'pause': None}
    pilot.limits(mt5, gold, risk, login, now, journals=(gold,))
    # Check the existing protected position without requiring fresh weekend gold ticks.
    pilot.check_exposure(mt5, (gold,), login, now)
    risk['last_poll'] = now
    return p, risk


def migrate(mt5, gold, login, now, reviewed_code, previous_code, backup):
    p, risk = review(mt5, gold, login, now, reviewed_code, previous_code)
    with backup.open('xb'):
        pass
    saved = sqlite3.connect(backup)
    try:
        gold.backup(saved)
        if saved.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
            raise ValueError('Journal backup failed verification')
    finally:
        saved.close()
    with gold:
        gold.execute('CREATE TABLE account_limits (id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL)')
        gold.execute('INSERT INTO account_limits VALUES (1, ?)', (json.dumps(risk, allow_nan=False),))
        # Existing trade receipts, pause, risk history and expiry are retained.
        gold.execute('UPDATE pilot SET data=? WHERE id=1',
                     (json.dumps({**p, 'code': reviewed_code, 'last_bar': None}, allow_nan=False),))
    return dict(gold_pause=p['pause'], ends_at=p['end'], btc_status='standby',
                backup=str(backup), order_sent=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reviewed-code-sha256', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    # The deployed five-file identity predates the instrument allowlist module.
    old = pilot.digest({name: hashlib.sha256((Path(r'Z:\opt\trading') / name).read_bytes()).hexdigest()
                        for name in pilot.SOURCES if name != 'instruments.py'})
    if old != PREVIOUS_CODE:
        raise ValueError('Deployed source differs from the reviewed starting version')
    import MetaTrader5 as mt5
    if not mt5.initialize(r'C:\Program Files\MetaTrader 5\terminal64.exe', timeout=10000):
        raise ValueError('MT5 unavailable')
    login = int(os.environ['MT5_DEMO_LOGIN'])
    path = Path.home() / 'gold-pilot.sqlite3'
    if not path.is_file() or (Path.home() / 'btc-pilot.sqlite3').exists():
        raise ValueError('Expected gold journal only; inspect existing BTC state')
    db = sqlite3.connect(path if args.apply else path.as_uri() + '?mode=ro', uri=not args.apply)
    db.row_factory = sqlite3.Row
    try:
        if [tuple(row) for row in db.execute('SELECT login, server, symbol FROM metadata')] != [(login, pilot.SERVER, GOLD)]:
            raise ValueError('Journal identity mismatch')
        if args.apply:
            with pilot.execution._exclusive(Path.home() / 'gold-one-shot.sqlite3'):
                result = migrate(mt5, db, login, time.time(), args.reviewed_code_sha256, old,
                                 path.with_name('gold-pilot-before-two-symbol-' + str(time.time_ns()) + '.sqlite3'))
            print('TWO_SYMBOL_MIGRATED', json.dumps(result))
        else:
            p, _ = review(mt5, db, login, time.time(), args.reviewed_code_sha256, old)
            print('TWO_SYMBOL_REVIEW_PASSED', json.dumps(dict(code=pilot.identity(),
                gold_pause=p['pause'], ends_at=p['end'], btc_status='standby', order_sent=False)))
    finally:
        db.close()
        mt5.shutdown()


if __name__ == '__main__':
    main()
