"""Score M5 Jev shadow decisions against demo fills read-only; never contacts MT5.

Only shadow-mode candidates count: veto rows are filtered by the veto itself.
A candidate still inside its Jev deadline is pending and not scored yet.
A candidate with an empty input_sha256 had no Jev state (state build failed). It
is reported as no_state, counts as a bad receipt, and its trade scores as vetoed
because veto mode would have failed closed. A receipt is late when it completed
or reached the runner's store after the deadline, since veto would have missed it. Closed P/L is the
attempt's realized_net_usd (profit + commission + swap + fee over the position's
deals); a closed attempt without it is unresolved and left out of the averages.
"""
import argparse
from contextlib import closing
import json
import math
import os
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
        return {stamp: (received, raw) for stamp, received, raw in
                db.execute('SELECT bar_time, received, payload FROM receipts')}


def _summary(values):
    return dict(trades=len(values), avg_net_usd=round(sum(values) / len(values), 4) if values else None)


def _classify(value, received, bar_time, digest, symbol):
    if value is None:
        return 'missing'
    try:
        jev_m5.validate_receipt(value, symbol=symbol)
    except ValueError:
        return 'invalid'
    if value['bar_time'] != bar_time or value['input_sha256'] != digest:
        return 'invalid'
    close = bar_time + jev_m5.SECONDS
    if not close <= value['completed_at'] <= close + jev_m5.DEADLINE or received > close + jev_m5.DEADLINE:
        return 'late'
    return value['status']


def veto_activity(db, stored, symbol):
    """Actual veto outcomes; never use these selected trades in the shadow gate."""
    record = db.execute('SELECT data FROM pilot WHERE id=1').fetchone()
    pilot = json.loads(record[0]) if record else {}
    start, end = pilot.get('reporting_start'), pilot.get('reporting_end')
    if start is not None or end is not None:
        if type(start) not in (int, float) or type(end) not in (int, float) or not math.isfinite(start) or not math.isfinite(end) or start <= 0 or end - start != 172800:
            raise ValueError('Invalid reporting window')
    rows = db.execute('SELECT c.bar_time, c.side, c.input_sha256, c.submitted, c.reason, '
                      'a.state, a.realized_net_usd, a.opened_at FROM jev_candidates c '
                      "LEFT JOIN attempts a ON a.id=c.attempt WHERE c.jev_mode='veto' ORDER BY c.bar_time DESC").fetchall()
    if start is not None:
        rows = [row for row in rows if start <= row[0] + jev_m5.SECONDS < end]
    counts = dict.fromkeys(('ok', *jev_m5.STATUSES[1:], 'missing', 'late'), 0)
    recent, nets = [], []
    submitted_count = no_state = unresolved = 0
    for bar, side, digest, submitted, reason, state, net, opened in rows:
        received, raw = stored.get(bar, (None, None))
        try:
            value = json.loads(raw) if raw is not None else None
        except ValueError:
            value = {}
        status = _classify(value, received, bar, digest, symbol) if digest else 'no_state'
        if status == 'no_state':
            no_state += 1
        else:
            counts[status] += 1
        submitted_count += bool(submitted)
        in_window = start is None or (type(opened) in (int, float) and start <= opened < end)
        resolved = in_window and submitted and state == 'closed' and type(net) in (int, float) and math.isfinite(net)
        if resolved:
            nets.append(net)
        elif in_window and submitted and state == 'closed':
            unresolved += 1
        if len(recent) < 20:
            recent.append(dict(bar_time=bar, side=side, receipt=status,
                               choice=value['choice'] if status == 'ok' else None,
                               confidence=value['confidence'] if status == 'ok' else None,
                               submitted=bool(submitted), state=state,
                               net_usd=net if resolved else None, reason=reason))
    pending = int(pilot.get('jev_mode') == 'veto' and bool(pilot.get('pending_entry')))
    if pending and start is not None:
        pending = int(start <= pilot['pending_entry']['bar_time'] + jev_m5.SECONDS < end)
    return dict(**(dict(reporting_start=start, reporting_end=end) if start is not None else {}), candidates=len(rows), submitted=submitted_count, blocked=len(rows)-submitted_count,
                pending=pending, no_state=no_state, unresolved=unresolved, receipts=counts,
                results={**_summary(nets), 'net_usd': round(sum(nets), 4) if nets else None}, recent=recent)


def export(journal, receipts, now=None):
    now = time.time() if now is None else now
    with closing(connect(journal)) as db:
        symbol = db.execute('SELECT symbol FROM metadata').fetchone()[0]
        if symbol not in ('XAUUSD-VIP', 'BTCUSD'):
            raise ValueError('Unsupported symbol')
        rows = db.execute('SELECT c.bar_time, c.side, c.input_sha256, c.submitted, c.jev_mode, '
                          'a.state, a.realized_net_usd FROM jev_candidates c '
                          'LEFT JOIN attempts a ON a.id = c.attempt ORDER BY c.bar_time').fetchall()
    stored = _receipts(receipts)  # Read after the journal, so every due candidate's receipt has had its chance.
    counts = dict.fromkeys(('ok', *jev_m5.STATUSES[1:], 'missing', 'late'), 0)
    modes, groups = {}, {'all': [], 'jev_kept': [], 'jev_vetoed': []}
    candidates = pending = no_state = closed = unresolved = 0
    for bar_time, side, digest, submitted, mode, state, net in rows:
        modes[str(mode)] = modes.get(str(mode), 0) + 1
        if mode != 'shadow':
            continue
        if now < bar_time + jev_m5.SECONDS + jev_m5.DEADLINE:
            pending += 1
            continue
        candidates += 1
        value = received = None
        if digest:
            received, raw = stored.get(bar_time, (None, None))
            try:
                value = None if raw is None else json.loads(raw)
            except ValueError:
                value = {}
            counts[_classify(value, received, bar_time, digest, symbol)] += 1
        else:
            no_state += 1
        if not (submitted and state == 'closed'):
            continue
        closed += 1
        if type(net) not in (int, float) or not math.isfinite(net):
            unresolved += 1
            continue
        # Scored as veto would have seen it: when the receipt completed and reached the runner.
        clock = value.get('completed_at') if isinstance(value, dict) else bar_time
        if type(clock) in (int, float) and type(received) in (int, float):
            clock = max(clock, received)
        kept, _ = jev_m5.allows(value, side=side, bar_time=bar_time, input_sha256=digest, now=clock, symbol=symbol)
        groups['all'].append(net)
        groups['jev_kept' if kept else 'jev_vetoed'].append(net)
    with closing(connect(journal)) as db:
        veto = veto_activity(db, stored, symbol)
    bad = candidates - counts['ok']
    rate = round(bad / candidates, 4) if candidates else None
    summary = {name: _summary(values) for name, values in groups.items()}
    reasons = []
    if summary['all']['trades'] < MIN_CLOSED:
        reasons.append(f"Need {MIN_CLOSED} closed shadow trades with resolved P/L; have {summary['all']['trades']}")
    if rate is None:
        reasons.append('No due shadow candidates to measure receipts')
    elif bad / candidates >= BAD_RECEIPT_MAX:
        reasons.append(f'Bad receipts {bad}/{candidates} reach the {BAD_RECEIPT_MAX:.0%} limit')
    kept, every = groups['jev_kept'], groups['all']
    if not kept or sum(kept) / len(kept) <= sum(every) / len(every):
        reasons.append('Jev-kept average net P/L does not beat all trades')
    return dict(**(dict(symbol=symbol) if symbol == 'BTCUSD' else {}), status='ready', generated_at=now,
                candidates=candidates, pending=pending, no_state=no_state, mode_counts=modes,
                closed=closed, unresolved=unresolved, receipts=counts, veto=veto, **summary,
                gate=dict(min_closed=MIN_CLOSED, bad_receipt_max=BAD_RECEIPT_MAX, bad_receipt_rate=rate,
                          passes=not reasons, reasons=reasons),
                qualification=QUALIFICATION)


def publish(journal, receipts, output):
    try:
        body = json.dumps(export(journal, receipts), allow_nan=False, separators=(',', ':'))
    except Exception as error:
        body = json.dumps(dict(status='unavailable', generated_at=time.time(), error=type(error).__name__))
    # Root writes into a container-writable volume: never follow a planted symlink at the temp path.
    temporary = output.with_name(f'.{output.name}.{os.getpid()}.tmp')
    try:
        os.unlink(temporary)  # unlink removes a symlink itself, not its target.
    except FileNotFoundError:
        pass
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o644)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
        os.fchmod(handle.fileno(), 0o644)
        handle.write(body)
    os.replace(temporary, output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--journal', type=Path, required=True)
    parser.add_argument('--receipts', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    publish(args.journal, args.receipts, args.output)
