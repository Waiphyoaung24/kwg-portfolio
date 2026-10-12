"""Read the frozen journal without migrations; export diagnostic outcomes, never orders."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import time

import jev_research as research


def export(path, now=None):
    with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)) as db:
        db.execute('BEGIN')  # One consistent snapshot while the collector appends.
        config = json.loads(db.execute('SELECT payload FROM config').fetchone()[0])
        if config['journal_code_sha256'] != hashlib.sha256(Path(research.__file__).read_bytes()).hexdigest():
            raise ValueError('Frozen journal code mismatch')
        samples = {stamp: json.loads(raw) for stamp, raw in db.execute('SELECT bar_time,payload FROM samples')}
        for sample in samples.values():
            if sample['input_sha256'] != research.digest({k: v for k, v in sample.items() if k != 'input_sha256'}):
                raise ValueError('Journal input hash mismatch')
        # shortcut: bounded first diagnostic run; add pagination before 200 eligible setups.
        if sum(s['eligible'] for s in samples.values()) > 200:
            raise ValueError('Scorecard requires pagination beyond 200 setups')
        result = research.report(db)
        outcomes = []
        for row in result['outcomes']:
            sample = samples[row['bar_time']]
            approved = {key: sample[key] for key in ('symbol', 'timeframe', 'captured_at', 'bars',
                        'bid', 'ask', 'signal', 'eligible', 'slope_pass', 'indicators', 'costs',
                        'specification', 'input_sha256')}
            outcomes.append(dict(bar_time=row['bar_time'], sample=approved,
                                 outcome=row['outcome'], trade=row['trade']))
        return dict(version=1, status='ready', qualification='unqualified_diagnostic',
                    generated_at=time.time() if now is None else now,
                    last_bar=max(samples, default=None), samples=result['samples'], gaps=result['gaps'],
                    journal_config_sha256=research.digest(config), outcomes=outcomes)


def publish(state, output):
    try:
        value = export(state)
        body = json.dumps(value, allow_nan=False, separators=(',', ':'))
        if len(body.encode()) > 8_000_000:
            raise ValueError('Scorecard export too large')
    except Exception as error:
        body = json.dumps(dict(status='unavailable', generated_at=time.time(), error=type(error).__name__))
    temporary = output.with_suffix('.tmp')
    temporary.write_text(body, encoding='utf-8')
    temporary.replace(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    publish(args.state, args.output)
