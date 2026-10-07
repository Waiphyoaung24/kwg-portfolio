"""Reproduce the browser's synthetic replay; no provider or MT5 calls."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy

from batch3_adapter import encode, simulator


def build():
    fixtures = runpy.run_path(str(Path(__file__).with_name('rehearse-batch3.py')))['fixtures']
    data, windows, costs, _ = fixtures()
    baseline = simulator()(data, windows=windows, cost_profile=costs)
    trade = baseline['runs']['lower']['windows']['development']['trades'][1]
    bars = [{'time': bar['time'], 'close': round(bar['close'], 2)} for bar in data['bars']
            if trade['signal_bar'] - 900 * 5 <= bar['time'] <= trade['exit_bar'] + 900 * 2]
    return {'mode': 'synthetic-replay', 'source_sha256': hashlib.sha256(encode(baseline)).hexdigest(),
        'description': 'Saved artificial-data simulation; lower-cost baseline, second development trade. Illustrates a target exit, not representative performance.',
        'bars': bars, 'trade': trade}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    target = Path(__file__).resolve().parents[2] / 'src/data/trading-replay.json'
    result = build()
    if args.check:
        assert json.loads(target.read_bytes()) == result, 'Replay differs from the simulator'
        print('PASS: browser replay matches the existing simulator.')
    else:
        target.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
