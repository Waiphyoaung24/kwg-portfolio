"""Local M15 shadow journal. No provider requests, broker orders or promotion."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import runpy
import sqlite3
import time

from gold_experiment import SCENARIOS, RISK, digest, entry_allowed, source_hashes
from gold_signal import evaluate

MODEL = 'jev-1.13.0'
PROMPT = ('Estimate whether this baseline Gold M15 setup will finish positive after the '
          'supplied modeled costs. Use only the supplied completed candles and snapshot. '
          'Choose positive, nonpositive, or abstain. This is research, never an order.')
simulate = runpy.run_path(str(Path(__file__).with_name('simulate-gold.py')))['simulate']


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def open_journal(path, specification):
    specification = {k: specification[k] for k in ('point', 'trade_contract_size', 'trade_tick_size',
                       'volume_min', 'volume_max', 'volume_step', 'currency_profit')}
    # Reuse the frozen simulator's contract validation without producing trades.
    simulate([], {}, specification, SCENARIOS['middle'])
    config = dict(version=1, symbol='XAUUSD-VIP', timeframe='M15', model=MODEL,
                  prompt_sha256=digest(PROMPT), costs=SCENARIOS['middle'], risk=RISK,
                  specification=specification, evaluator=source_hashes(), slope_bars=3)
    config['journal_code_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    db = sqlite3.connect(path)
    try:
        with db:
            db.execute('CREATE TABLE IF NOT EXISTS config (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS samples (bar_time INTEGER PRIMARY KEY, captured REAL NOT NULL, payload TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS responses (bar_time INTEGER PRIMARY KEY REFERENCES samples(bar_time), received REAL NOT NULL, payload TEXT NOT NULL)')
            db.execute('INSERT OR IGNORE INTO config VALUES (1, ?)', (encoded(config),))
        if db.execute('SELECT payload FROM config').fetchone()[0] != encoded(config):
            raise ValueError('Research configuration/code changed; start a separately versioned journal')
        return db
    except BaseException:
        db.close()
        raise


def capture(db, bars, bid, ask, captured, status):
    if status not in ('baseline', 'observed', 'blocked', 'duplicate'):
        raise ValueError('Invalid observer status')
    if len(bars) != 250:
        raise ValueError('Exactly 250 completed bars required')
    clean = [{k: b[k] for k in ('time', 'open', 'high', 'low', 'close')} for b in bars]
    result = evaluate(clean, bid, ask, captured)
    stamp = result['bar_time']
    if not stamp + 900 <= captured <= stamp + 930:
        raise ValueError('Capture must be within 30 seconds of candle close; no backfill')
    if status == 'duplicate':
        return False
    eligible = status == 'observed' and result['signal'] in ('long', 'short')
    config = json.loads(db.execute('SELECT payload FROM config').fetchone()[0])
    point = config['specification']['point']
    sample = dict(symbol='XAUUSD-VIP', timeframe='M15', captured_at=captured,
                  bars=clean, bid=bid, ask=ask, indicators={k: result[k] for k in ('ema20', 'ema50', 'atr14')},
                  signal=result['signal'] if eligible else 'none', eligible=eligible,
                  observer_status=status, slope_pass=entry_allowed(clean, result['signal'], 3) if eligible else False,
                  costs=config['costs'], risk=config['risk'], specification=config['specification'],
                  spread_points=math.ceil((ask-bid) / point),
                  cost_evidence='unverified_scenario', spread_source='capture_quote_proxy',
                  proposed_trade={'side': result['signal'], 'entry_reference': ask if result['signal'] == 'long' else bid,
                                  'stop_atr': 2, 'target_atr': 3} if eligible else None)
    sample['input_sha256'] = digest(sample)
    with db:
        latest = db.execute('SELECT max(bar_time) FROM samples').fetchone()[0]
        if latest is not None and stamp <= latest:
            return False
        if latest is not None:
            previous = json.loads(db.execute('SELECT payload FROM samples WHERE bar_time=?', (latest,)).fetchone()[0])
            history = {b['time']: b for b in previous['bars']}
            if any(b['time'] in history and b != history[b['time']] for b in clean):
                raise ValueError('Previously captured candles changed')
        db.execute('INSERT INTO samples VALUES (?, ?, ?)', (stamp, captured, encoded(sample)))
    return True


def pending(db, now=None):
    now = time.time() if now is None else now
    requests = []
    for stamp, captured, raw in db.execute('SELECT bar_time,captured,payload FROM samples WHERE bar_time NOT IN (SELECT bar_time FROM responses)'):
        sample = json.loads(raw)
        if sample['eligible'] and captured <= now <= captured + 15:
            requests.append(dict(bar_time=stamp, input_sha256=sample['input_sha256'], model=MODEL,
                                 prompt_sha256=digest(PROMPT), state=sample,
                                 questions={'outcome': {'type': 'choice', 'instructions': PROMPT,
                                   'criteria': {'positive': 'Net modeled outcome above zero',
                                                'nonpositive': 'Net modeled outcome zero or below',
                                                'abstain': 'Evidence insufficient'}}}))
    return requests


def record_response(db, stamp, response, received=None):
    received = time.time() if received is None else received
    row = db.execute('SELECT captured,payload FROM samples WHERE bar_time=?', (stamp,)).fetchone()
    if row is None or not json.loads(row[1])['eligible']:
        raise ValueError('Unknown or ineligible setup')
    sample = json.loads(row[1])
    if response.get('input_sha256') != sample['input_sha256'] or response.get('model') != MODEL or response.get('prompt_sha256') != digest(PROMPT):
        raise ValueError('Response does not match the frozen request')
    status = response.get('status')
    if status not in ('ok', 'timeout', 'unavailable', 'budget_exhausted', 'not_connected'):
        raise ValueError('Invalid response status')
    if not math.isfinite(received) or received < row[0]:
        raise ValueError('Invalid receipt time')
    value = dict(status=status, model=MODEL, input_sha256=sample['input_sha256'], prompt_sha256=digest(PROMPT),
                 provenance='imported_unverified')
    if status == 'ok':
        probabilities = response.get('probabilities', {})
        if (set(probabilities) != {'positive', 'nonpositive', 'abstain'} or
                any(type(p) not in (float, int) or not math.isfinite(p) or not 0 <= p <= 1 for p in probabilities.values()) or
                abs(sum(probabilities.values())-1) > .001 or response.get('decision') not in probabilities):
            raise ValueError('Invalid probabilities')
        value.update(decision=response['decision'], probabilities=probabilities)
    value['timely'] = received <= row[0] + 15
    with db:
        # Duplicate outcomes/responses are never overwritten, including after a timeout.
        db.execute('INSERT INTO responses VALUES (?, ?, ?)', (stamp, received, encoded(value)))


def report(db):
    config = json.loads(db.execute('SELECT payload FROM config').fetchone()[0])
    if config['evaluator'] != source_hashes():
        raise ValueError('Evaluator changed since journal creation')
    rows = [(stamp, json.loads(raw)) for stamp, raw in db.execute('SELECT bar_time,payload FROM samples ORDER BY bar_time')]
    replies = {stamp: json.loads(raw) for stamp, raw in db.execute('SELECT bar_time,payload FROM responses')}
    bars = [{**s['bars'][-1], 'spread': s['spread_points']} for _, s in rows]
    setups = {stamp: s for stamp, s in rows if s['eligible']}
    signals = {stamp: dict(bar_time=stamp, signal=s['signal'], atr14=s['indicators']['atr14']) for stamp, s in setups.items()}
    gaps = sum(b['time'] - a['time'] != 900 for a, b in zip(bars, bars[1:]))
    outcomes = []
    for stamp, sample in setups.items():
        reply = replies.get(stamp, {'status': 'missing', 'timely': False})
        # Independent opportunity labels include slope/Jev rejects. They are not portfolio P/L.
        path = [b for b in bars if b['time'] >= stamp - 900]
        local = {t: {**s, 'entry_allowed': t == stamp} for t, s in signals.items() if t >= stamp}
        result = simulate(path, local, config['specification'], config['costs'])
        trade = next((t for t in result['trades'] if t['signal_bar'] == stamp), None)
        state = 'pending' if not path or path[-1]['time'] <= stamp else 'no_fill'
        if trade:
            state = 'pending' if trade['exit_reason'] == 'window_end' else 'resolved'
        if any(b['time']-a['time'] != 900 for a,b in zip(path,path[1:]) if not trade or b['time'] <= trade['exit_bar']):
            state = 'censored_gap'
        if not path or path[0]['time'] != stamp - 900:
            state = 'censored_missing_predecessor'
        outcomes.append(dict(bar_time=stamp, slope_pass=sample['slope_pass'], jev=reply,
                             outcome=state, trade=trade if state == 'resolved' else None))
    arms = {}
    for name in ('baseline', 'slope', 'jev'):
        selected = [o for o in outcomes if name == 'baseline' or
                    (name == 'slope' and o['slope_pass']) or
                    (name == 'jev' and o['jev']['status'] == 'ok' and o['jev']['timely'] and o['jev']['decision'] == 'positive')]
        resolved = [o['trade']['net_pnl'] for o in selected if o['outcome'] == 'resolved']
        arms[name] = dict(selected=len(selected), resolved=len(resolved),
                          coverage=len(selected)/len(outcomes) if outcomes else None,
                          expectancy_usd=sum(resolved)/len(resolved) if resolved else None)
    return dict(qualification='unqualified_diagnostic', promotion='blocked', samples=len(rows),
                eligible=len(setups), gaps=gaps, missing_responses=sum(t not in replies for t in setups),
                arms=arms, outcomes=outcomes,
                limitations=['Independent opportunity labels are not additive portfolio returns or drawdown.',
                             'Response imports are unverified; missing and late responses remain in the denominator.',
                             'Costs and capture-quote spread proxies are unverified.',
                             'Next-open simulation does not model Jev response latency; no tradable-edge claim.',
                             'No holdout registration, confidence intervals or automatic promotion.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--spec', type=Path, required=True)
    parser.add_argument('action', choices=('pending', 'report', 'response'))
    parser.add_argument('--response', type=Path)
    args = parser.parse_args()
    db = open_journal(args.state, json.loads(args.spec.read_text()))
    try:
        if args.action == 'response':
            value = json.loads(args.response.read_text())
            record_response(db, value['bar_time'], value)
        else:
            print(encoded(pending(db) if args.action == 'pending' else report(db)))
    finally:
        db.close()


if __name__ == '__main__':
    main()
