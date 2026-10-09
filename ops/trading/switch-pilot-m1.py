"""Explicit, flat-account M1 or trend migration; default is read-only review."""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import sys
import time

# Embedded Wine Python pins /opt/trading; review the staged siblings instead.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import demo_pilot as pilot


def review(mt5, db, login, now, pause_path, previous_code, reviewed_code, *, trend=False):
    p = pilot.state(db)
    source = pilot.M1_STRATEGY if trend else pilot.STRATEGY
    if not p or p['strategy'] != source or p['pause'] is not None:
        raise ValueError('Switch requires an active, unpaused ' + source + ' pilot')
    if p['code'] != previous_code:
        raise ValueError('Activated journal code does not match previous reviewed code')
    if pilot.identity() != reviewed_code:
        raise ValueError('Loaded code does not match reviewed staging code: ' + str(pilot.__file__))
    if not p['start'] <= now < p['end'] or p['end'] - p['start'] > 604800:
        raise ValueError('Original pilot window invalid or expired')
    if pause_path.exists():
        raise ValueError('Owner pause exists')
    pilot.account(mt5, login, enabled=True)
    positions, orders = mt5.positions_get(), mt5.orders_get()
    if positions is None or orders is None or positions or orders:
        raise ValueError('Switch requires an empty account')
    if db.execute("SELECT count(*) FROM attempts WHERE state NOT IN ('closed','disarmed')").fetchone()[0]:
        raise ValueError('Unresolved attempt requires review')
    # Accept only this explicitly reviewed code transition; all other limits still apply.
    p['code'] = reviewed_code
    pilot.limits(mt5, db, p, login, now)
    reason = 'M1 selected; waiting for a new completed candle baseline'
    try:
        pilot.read_gold(mt5, login, now, execution=True, bar_seconds=60,
                        server_offset_seconds=pilot.execution._server_offset())
    except ValueError as exc:
        # Switching while flat sends no order; the runner still enforces this entry gate.
        if str(exc) != 'ATR or spread outside allowed range':
            raise
        reason = 'M1 selected; entry blocked by ATR or spread outside allowed range'
    p.update(strategy=pilot.TREND_STRATEGY if trend else pilot.M1_STRATEGY, last_bar=None,
             reason=reason)
    return p


def switch(mt5, db, login, now, pause_path, previous_code, reviewed_code, backup_path, *, trend=False):
    p = review(mt5, db, login, now, pause_path, previous_code, reviewed_code, trend=trend)
    with backup_path.open('xb'):
        pass
    with closing(sqlite3.connect(backup_path)) as backup:
        db.backup(backup)
        if backup.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
            raise ValueError('Backup integrity check failed')
    pilot.save(db, p)
    return p


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous-code-sha256', required=True)
    parser.add_argument('--reviewed-code-sha256', required=True)
    parser.add_argument('--enable-demo-execution', action='store_true')
    parser.add_argument('--trend', action='store_true', help='Switch an existing M1 crossover pilot to M1 trend with a 300-second close cooldown')
    args = parser.parse_args()
    if os.environ.get('MT5_RUN_MODE') != 'pilot':
        parser.error('MT5_RUN_MODE must be pilot')
    import MetaTrader5 as mt5
    if not mt5.initialize(r'C:\Program Files\MetaTrader 5\terminal64.exe', timeout=10000):
        raise SystemExit('MT5 unavailable')
    os.umask(0o077)
    home = Path.home()
    path = home / 'gold-pilot.sqlite3'
    try:
        with closing(sqlite3.connect(path.as_uri() + '?mode=' + ('rw' if args.enable_demo_execution else 'ro'), uri=True)) as db:
            db.row_factory = sqlite3.Row
            inputs = (mt5, db, int(os.environ['MT5_DEMO_LOGIN']), time.time(), home / 'gold-pilot.pause',
                      args.previous_code_sha256, args.reviewed_code_sha256)
            if args.enable_demo_execution:
                with pilot.execution._exclusive(home / 'gold-one-shot.sqlite3'):
                    backup = home / ('gold-pilot-before-m1-' + str(time.time_ns()) + '.sqlite3')
                    p = switch(*inputs, backup, trend=args.trend)
                    print('M1_SWITCH_SAVED', json.dumps(dict(strategy=p['strategy'], ends_at=p['end'], backup=str(backup), order_sent=False)))
            else:
                p = review(*inputs, trend=args.trend)
                print('M1_REVIEW_PASSED', json.dumps(dict(strategy=p['strategy'], ends_at=p['end'], code=p['code'], reason=p['reason'], order_sent=False)))
    finally:
        mt5.shutdown()


if __name__ == '__main__':
    main()
