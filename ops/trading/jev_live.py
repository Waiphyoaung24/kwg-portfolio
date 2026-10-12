"""Read market data alongside the existing demo runner; no order API or trading configuration writes."""
import json
import os
from pathlib import Path
import time
import sys

# The embedded Wine Python uses an isolated ._pth; explicitly load this reviewed bundle.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from gold_signal import evaluate
from gold_experiment import entry_allowed
from mt5_data import read_gold, read_contract
from jev_research import open_journal, capture


def publish(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, allow_nan=False), encoding='utf-8')
    temporary.replace(path)


def run(mt5, home, output, once=False):
    login = int(os.environ['MT5_DEMO_LOGIN'])
    offset = int(os.environ['MT5_SERVER_OFFSET_SECONDS'])
    db = None
    bootstrap = True
    previous = None
    try:
        while True:
            try:
                health = {}
                # Existing execution=True validates the already-enabled pinned demo;
                # it only selects account/data guards and never calls an order API.
                tick, bars = read_gold(mt5, login, None, health, server_offset_seconds=offset, execution=True)
                now = health['sampled_at']
                if db is None:
                    db = open_journal(home / 'jev-m15-live-v1.sqlite3', read_contract(mt5))
                result = evaluate(bars, float(tick.bid), float(tick.ask), now)
                stamp = result['bar_time']
                latest = db.execute('SELECT max(bar_time) FROM samples').fetchone()[0]
                status = 'blocked' if result['signal'] == 'blocked' else 'baseline' if bootstrap or latest is None or stamp-latest != 900 else 'observed'
                if stamp != previous and 0 <= now-stamp-900 <= 30:
                    capture(db, bars, float(tick.bid), float(tick.ask), now, status)
                    previous = stamp
                    bootstrap = status == 'blocked'
                row = db.execute('SELECT payload FROM samples WHERE bar_time=?', (stamp,)).fetchone()
                if row:
                    sample = json.loads(row[0])
                else:
                    # A mid-candle startup can be reviewed manually but never enters the experiment.
                    config = json.loads(db.execute('SELECT payload FROM config').fetchone()[0])
                    sample = dict(symbol='XAUUSD-VIP',timeframe='M15',captured_at=now,bars=bars,
                        bid=float(tick.bid),ask=float(tick.ask),signal='none',eligible=False,slope_pass=False,
                        indicators={k:result[k] for k in ('ema20','ema50','atr14')},
                        costs=config['costs'],specification=config['specification'])
                publish(output,dict(status='ready',checked_at=now,sample=sample))
            except Exception as error:
                bootstrap = True
                publish(output,dict(status='unavailable',checked_at=time.time(),error=type(error).__name__))
            if once:
                return
            time.sleep(2)
    finally:
        if db is not None:
            db.close()


if __name__ == '__main__':
    import MetaTrader5 as mt5
    if not mt5.initialize(r'C:\Program Files\MetaTrader 5\terminal64.exe', timeout=10000):
        raise SystemExit('MT5 attach unavailable')
    try:
        run(mt5, Path.home(), Path(r'Z:\opt\status\jev-m15.json'))
    finally:
        mt5.shutdown()
