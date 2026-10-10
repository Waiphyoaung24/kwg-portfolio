"""Review or clear only a recovered account pause; never place an order."""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import time

import demo_pilot as pilot

ACCOUNT_PAUSE = 'Pinned USD demo account unavailable'


def review(mt5, db, login, now, pause_path, reviewed_code):
    p = pilot.state(db)
    if not p or p['pause'] != ACCOUNT_PAUSE:
        raise ValueError('Only the pinned-account pause can be resumed')
    if not p['start'] <= now < p['end'] or p['end'] - p['start'] > 7 * 86400:
        raise ValueError('Original pilot window is invalid or expired')
    if p['code'] != reviewed_code or pilot.identity() != reviewed_code:
        raise ValueError('Reviewed trading code does not match activated code')
    if pause_path.exists():
        raise ValueError('Owner pause request exists')
    pilot.account(mt5, login, enabled=True)
    positions, orders = mt5.positions_get(), mt5.orders_get()
    if positions is None or orders is None or positions or orders:
        raise ValueError('Resume requires an empty demo account')
    if db.execute("SELECT count(*) FROM attempts WHERE state NOT IN ('closed','disarmed')").fetchone()[0]:
        raise ValueError('Unresolved journal attempts require review')
    pilot.limits(mt5, db, p, login, now)
    try:
        pilot.read_gold(mt5, login, now, server_offset_seconds=pilot.execution._server_offset(), execution=True,
                        bar_seconds=pilot.candle_seconds(p), trend_demo=p['strategy'] == pilot.TREND_STRATEGY)
    except ValueError as exc:
        # Flat-account recovery resumes monitoring; the runner still enforces entry eligibility.
        if str(exc) != 'ATR or spread outside allowed range':
            raise
    return p


def resume(mt5, db, login, now, pause_path, reviewed_code, backup_path):
    p = review(mt5, db, login, now, pause_path, reviewed_code)
    # Caller holds the same OS lock as the runner for the entire recovery.
    with backup_path.open('xb'):
        pass
    with closing(sqlite3.connect(backup_path)) as backup:
        db.backup(backup)
        if backup.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
            raise ValueError('Backup integrity check failed')
    p.update(pause=None, last_bar=None, reason='Account recovered; waiting for a new candle baseline')
    pilot.save(db, p)
    return p


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reviewed-code-sha256', required=True)
    parser.add_argument('--enable-demo-execution', action='store_true', help='Clear the pause; default is review only')
    args = parser.parse_args()
    if os.environ.get('MT5_RUN_MODE') != 'pilot':
        parser.error('MT5_RUN_MODE must be pilot')
    import MetaTrader5 as mt5
    if not mt5.initialize(r'C:\Program Files\MetaTrader 5\terminal64.exe', timeout=10000):
        raise SystemExit('MT5 connection unavailable')
    home = Path.home()
    path = home / 'gold-pilot.sqlite3'
    os.umask(0o077)
    db = sqlite3.connect(path.as_uri() + '?mode=' + ('rw' if args.enable_demo_execution else 'ro'), uri=True)
    db.row_factory = sqlite3.Row
    try:
        login = int(os.environ['MT5_DEMO_LOGIN'])
        if args.enable_demo_execution:
            with pilot.execution._exclusive(home / 'gold-one-shot.sqlite3'):
                backup = home / ('gold-pilot-before-resume-' + str(time.time_ns()) + '.sqlite3')
                p = resume(mt5, db, login, time.time(), home / 'gold-pilot.pause', args.reviewed_code_sha256, backup)
                print('RESUME_SAVED', json.dumps(dict(ends_at=p['end'], backup=str(backup), order_sent=False)))
        else:
            p = review(mt5, db, login, time.time(), home / 'gold-pilot.pause', args.reviewed_code_sha256)
            print('RESUME_REVIEW_PASSED', json.dumps(dict(ends_at=p['end'], pause=p['pause'], order_sent=False)))
    finally:
        db.close()
        mt5.shutdown()


if __name__ == '__main__':
    main()
