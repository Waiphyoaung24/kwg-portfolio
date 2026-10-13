"""Score Gold M5 Jev shadow decisions against demo fills read-only; never contacts MT5.

Only shadow-mode candidates count: veto rows are filtered by the veto itself.
A candidate with an empty input_sha256 had no Jev state (state build failed). It
is counted as no_state, kept out of the bad-receipt denominator, and its trade
scores as vetoed because veto mode would have failed closed. Closed P/L is the
attempt's realized_net_usd (profit + commission + swap + fee over the position's
deals); a closed attempt without it is unresolved and left out of the averages.
"""
import argparse
from contextlib import closing
import json
import math
from pathlib import Path
import sqlite3
import time

import jev_m5

MIN_CLOSED = 50
BAD_RECEIPT_MAX = .2
QUALIFICATION = 'demo fills; unqualified; not a profitability claim'


def connect(path):
    return sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)


def _receipts(path):
    if not path.exists():
        return {}  # The Worker may not have forwarded a receipt yet; never create the store.
    with closing(connect(path)) as db:
        return {stamp: raw for stamp, raw in db.execute('SELECT bar_time, payload FROM receipts')}


def _summary(values):
    return dict(trades=len(values), avg_net_usd=round(sum(values) / len(values), 4) if values else None)


def _classify(value, bar_time, digest):
    if value is None:
        return 'missing'
    try:
        jev_m5.validate_receipt(value)
    except ValueError:
        return 'invalid'
    if value['bar_time'] != bar_time or value['input_sha256'] != digest:
        return 'invalid'
    close = bar_time + jev_m5.SECONDS
    if not close <= value['completed_at'] <= close + jev_m5.DEADLINE:
        return 'late'
    return value['status']


def export(journal, receipts, now=None):
    stored = _receipts(receipts)
    with closing(connect(journal)) as db:
        db.execute('BEGIN')  # One consistent snapshot while the runner appends.
        rows = db.execute('SELECT c.bar_time, c.side, c.input_sha256, c.submitted, c.jev_mode, '
                          'a.state, a.realized_net_usd FROM jev_candidates c '
                          'LEFT JOIN attempts a ON a.id = c.attempt ORDER BY c.bar_time').fetchall()
    counts = dict.fromkeys(('ok', *jev_m5.STATUSES[1:], 'missing', 'late'), 0)
    modes, groups = {}, {'all': [], 'jev_kept': [], 'jev_vetoed': []}
    candidates = no_state = closed = unresolved = 0
    for bar_time, side, digest, submitted, mode, state, net in rows:
        modes[str(mode)] = modes.get(str(mode), 0) + 1
        if mode != 'shadow':
            continue
        candidates += 1
        value = None
        if digest:
            raw = stored.get(bar_time)
            try:
                value = None if raw is None else json.loads(raw)
            except ValueError:
                value = {}
            counts[_classify(value, bar_time, digest)] += 1
        else:
            no_state += 1
        if not (submitted and state == 'closed'):
            continue
        closed += 1
        if type(net) not in (int, float) or not math.isfinite(net):
            unresolved += 1
            continue
        clock = value.get('completed_at') if isinstance(value, dict) else bar_time
        kept, _ = jev_m5.allows(value, side=side, bar_time=bar_time, input_sha256=digest, now=clock)
        groups['all'].append(net)
        groups['jev_kept' if kept else 'jev_vetoed'].append(net)
    scored = candidates - no_state
    bad = scored - counts['ok']
    rate = round(bad / scored, 4) if scored else None
    summary = {name: _summary(values) for name, values in groups.items()}
    reasons = []
    if summary['all']['trades'] < MIN_CLOSED:
        reasons.append(f"Need {MIN_CLOSED} closed shadow trades with resolved P/L; have {summary['all']['trades']}")
    if rate is None:
        reasons.append('No shadow candidates with a Jev state to measure receipts')
    elif bad / scored >= BAD_RECEIPT_MAX:
        reasons.append(f'Bad receipts {bad}/{scored} reach the {BAD_RECEIPT_MAX:.0%} limit')
    kept, every = groups['jev_kept'], groups['all']
    if not kept or sum(kept) / len(kept) <= sum(every) / len(every):
        reasons.append('Jev-kept average net P/L does not beat all trades')
    return dict(status='ready', generated_at=time.time() if now is None else now,
                candidates=candidates, no_state=no_state, mode_counts=modes,
                closed=closed, unresolved=unresolved, receipts=counts, **summary,
                gate=dict(min_closed=MIN_CLOSED, bad_receipt_max=BAD_RECEIPT_MAX, bad_receipt_rate=rate,
                          passes=not reasons, reasons=reasons),
                qualification=QUALIFICATION)


def publish(journal, receipts, output):
    try:
        body = json.dumps(export(journal, receipts), allow_nan=False, separators=(',', ':'))
    except Exception as error:
        body = json.dumps(dict(status='unavailable', generated_at=time.time(), error=type(error).__name__))
    temporary = output.with_suffix('.tmp')
    temporary.write_text(body, encoding='utf-8')
    temporary.replace(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--journal', type=Path, required=True)
    parser.add_argument('--receipts', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    publish(args.journal, args.receipts, args.output)
