"""One fixed, time-bounded autonomous demo pilot; owner activation is required."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import time

import demo_one_shot as execution
from gold_experiment import digest, entry_allowed
from gold_signal import evaluate
from mt5_data import SERVER, SYMBOL, read_gold, validate_account, validate_tick

STRATEGY = 'gold-ema-v1-slope-3'
M1_STRATEGY = 'gold-ema-v1-m1-slope-3'
TREND_STRATEGY = 'gold-ema-v1-m1-trend-3'
SNAPSHOT = Path(r'Z:\opt\status\latest.json')
SOURCES = ('demo_pilot.py', 'demo_one_shot.py', 'mt5_data.py', 'gold_signal.py', 'gold_experiment.py')


def identity():
    return digest({name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                   for name in SOURCES})


def open_state(path, login):
    db = execution.open_journal(path, login)
    with db:
        db.execute('CREATE TABLE IF NOT EXISTS pilot (id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL)')
    return db


def state(db):
    row = db.execute('SELECT data FROM pilot WHERE id=1').fetchone()
    return json.loads(row[0]) if row else None


def candle_seconds(p):
    if p is None or p['strategy'] == STRATEGY:
        return 900
    if p['strategy'] in (M1_STRATEGY, TREND_STRATEGY):
        return 60
    raise ValueError('Unknown pilot strategy')


def assess(bars, tick, now, p):
    result = evaluate(bars, float(tick.bid), float(tick.ask), now, bar_seconds=candle_seconds(p))
    if p and p['strategy'] == TREND_STRATEGY and result['signal'] != 'blocked':
        fast, slow = result['ema20'], result['ema50']
        result['signal'] = 'long' if fast > slow else 'short' if fast < slow else 'none'
    return result


def cooldown_remaining(db, p, now):
    if p['strategy'] != TREND_STRATEGY:
        return 0
    closed = db.execute("SELECT MAX(closed_at) FROM attempts WHERE state='closed'").fetchone()[0]
    if closed is None:
        return 0
    if type(closed) not in (int, float) or not math.isfinite(closed) or not 0 < closed <= now:
        raise ValueError('Invalid close time for cooldown')
    return max(0, math.ceil(closed + 300 - now))


def save(db, value):
    with db:
        db.execute('UPDATE pilot SET data=? WHERE id=1', (json.dumps(value, allow_nan=False),))


def account(mt5, login, *, enabled=False):
    value = mt5.account_info()
    terminal = mt5.terminal_info()
    if (value is None or terminal is None or not terminal.connected
            or value.trade_mode != 0 or value.login != login or value.server != SERVER
            or value.currency != 'USD'):
        raise ValueError('Pinned USD demo account unavailable')
    if enabled:
        validate_account(value, terminal, login, execution=True)
    execution._positive(value.equity, 'equity')
    execution._positive(value.balance, 'balance')
    return value


def activate(mt5, db, login, now, end, pause_path):
    if type(end) is not int or not now < end <= now + 7 * 86400:
        raise ValueError('End must be a future UTC time within seven days')
    if pause_path.exists():
        raise ValueError('A pause request exists; review it before activation')
    value = account(mt5, login, enabled=True)
    positions, orders = mt5.positions_get(), mt5.orders_get()
    if positions is None or orders is None or positions or orders:
        raise ValueError('Activation requires an empty demo account')
    read_gold(mt5, login, None, server_offset_seconds=execution._server_offset(), execution=True)
    record = dict(start=now, end=end, strategy=STRATEGY, code=identity(),
                  offset=execution._server_offset(), initial_equity=value.equity,
                  initial_balance=value.balance, peak=value.equity, day=int(now // 86400),
                  day_equity=value.equity, last_poll=now, last_bar=None,
                  pause=None, reason='Waiting for a new completed candle')
    with db:
        # One activation per journal; neither restart nor another command resets limits.
        db.execute('INSERT INTO pilot VALUES (1, ?)', (json.dumps(record, allow_nan=False),))
    return record


def limits(mt5, db, p, login, now):
    candle_seconds(p)
    value = account(mt5, login)
    if now < p['last_poll']:
        raise ValueError('Host clock moved backward')
    if p['code'] != identity() or p['offset'] != execution._server_offset():
        raise ValueError('Activated code or clock configuration changed')
    # A mid-day restart cannot invent the missing midnight equity observation.
    if int(now // 86400) != p['day']:
        if now - p['last_poll'] > 30 or now % 86400 > 30:
            raise ValueError('UTC day boundary equity was not observed')
        p.update(day=int(now // 86400), day_equity=value.equity)
    p['peak'] = max(p['peak'], value.equity)
    if value.equity <= p['peak'] * .95:
        raise ValueError('Pilot drawdown limit reached')
    if value.equity <= p['day_equity'] * .99:
        raise ValueError('Daily equity loss limit reached')
    offset = execution._server_offset()
    deals = mt5.history_deals_get(datetime.fromtimestamp(p['start'] + offset, timezone.utc),
                                 datetime.fromtimestamp(now + offset + 60, timezone.utc))
    if deals is None:
        raise ValueError('Account history unavailable')
    attempts = db.execute('SELECT request_json, position_ticket FROM attempts WHERE request_json IS NOT NULL').fetchall()
    comments = {json.loads(row['request_json'])['comment'] for row in attempts}
    tickets = {row['position_ticket'] for row in attempts if row['position_ticket']}
    for deal in deals:
        if (getattr(deal, 'type', None) not in (0, 1)
                or getattr(deal, 'symbol', None) != SYMBOL
                or not (getattr(deal, 'position_id', None) in tickets
                        or getattr(deal, 'comment', None) in comments)):
            raise ValueError('Unrelated account activity requires review')
    total = p['initial_balance']
    for deal in deals:
        for name in ('profit', 'commission', 'swap', 'fee'):
            amount = getattr(deal, name, None)
            if type(amount) not in (int, float) or not math.isfinite(amount):
                raise ValueError('Deal costs unavailable')
            total += amount
    if not math.isclose(total, value.balance, rel_tol=0, abs_tol=.02):
        raise ValueError('Account balance and deal history disagree')
    return value


def close_at_expiry(mt5, db, login, now):
    row = execution._attempt(db)
    if row is None or row['state'] in ('closed', 'disarmed') or row['phase'] == 'close':
        return
    positions, all_positions, orders, _ = execution._broker_state(mt5, row, now, login)
    if len(positions) != 1 or len(all_positions) != 1 or orders:
        raise ValueError('Expiry exposure needs owner reconciliation')
    account(mt5, login, enabled=True)
    position = positions[0]
    original = json.loads(row['request_json'])
    execution._protected(mt5, position, original, row['entry_equity'])
    tick = mt5.symbol_info_tick(SYMBOL)
    validate_tick(tick, now, server_offset_seconds=execution._server_offset())
    side = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
    request = dict(action=mt5.TRADE_ACTION_DEAL, symbol=SYMBOL, position=position.ticket,
                   volume=position.volume, type=side, price=tick.bid if side == mt5.ORDER_TYPE_SELL else tick.ask,
                   deviation=10, magic=execution.MAGIC, comment=original['comment'],
                   type_time=mt5.ORDER_TIME_GTC, type_filling=original['type_filling'])
    checked = mt5.order_check(request)
    if checked is None or checked.retcode != 0:
        raise ValueError('Expiry close check rejected; owner action required')
    account(mt5, login, enabled=True)
    execution._update(db, phase='close', state='closing')
    try:
        result = mt5.order_send(request)
    except Exception:
        result = None
    execution._update(db, close_order_id=getattr(result, 'order', None),
                      close_deal_id=getattr(result, 'deal', None))
    execution.process_once(mt5, db, now, allow_entry=False)


def poll_once(mt5, db, login, now, pause_path, *, bootstrap=False):
    p = state(db)
    seconds = candle_seconds(p)
    health = {}
    report = dict(mode='autonomous-demo', symbol=SYMBOL, checked_at=int(now),
                  status='blocked', signal='none', bar_time=None, health=health,
                  reason='Pilot not activated')
    status = execution.process_once(mt5, db, now, allow_entry=False)
    if p:
        row = execution._attempt(db)
        if status['status'] == 'open' and row and status['volume'] != json.loads(row['request_json'])['volume']:
            p['pause'] = p['pause'] or 'Partial fill requires review'
        try:
            if pause_path.exists():
                p['pause'] = p['pause'] or 'Paused by owner'
            value = limits(mt5, db, p, login, now)
        except (ValueError, TypeError, OverflowError) as exc:
            p['pause'] = p['pause'] or str(exc)
        if status['status'] in ('needs_attention', 'submitting', 'closing'):
            p['pause'] = p['pause'] or 'Broker outcome requires review'
        if now >= p['end']:
            p['pause'] = p['pause'] or 'Pilot expired'
            if status['status'] not in ('closed', 'disarmed'):
                try:
                    close_at_expiry(mt5, db, login, now)
                except (ValueError, TypeError, OverflowError) as exc:
                    p['pause'] = str(exc)
                status = execution._status(db, now)
        p['last_poll'] = max(now, p['last_poll'])
        save(db, p)
    try:
        tick, bars = read_gold(mt5, login, now, health,
                              server_offset_seconds=execution._server_offset(), execution=bool(p), bar_seconds=seconds)
        result = assess(bars, tick, now, p)
        health.update(strategy_signal=result['signal'], strategy_reason=result['reason'])
        report.update(bar_time=result['bar_time'], status='observed', reason=result['reason'])
        if p:
            new_bar = p['last_bar'] is None or result['bar_time'] > p['last_bar']
            baseline = bootstrap or p['last_bar'] is None or (new_bar and result['bar_time'] - p['last_bar'] != seconds)
            cooldown = cooldown_remaining(db, p, now)
            if new_bar:
                p['last_bar'] = result['bar_time']
                save(db, p)
            if result['signal'] == 'blocked':
                report.update(status='blocked', reason=result['reason'])
            elif p['pause']:
                report.update(status='blocked', reason=p['pause'])
            elif baseline:
                report.update(status='baseline', reason='Startup or missed candle baseline')
            elif cooldown:
                report.update(reason=f'Cooldown after close: {cooldown} seconds remaining')
            elif new_bar and result['signal'] in ('long', 'short') and entry_allowed(bars, result['signal'], 3):
                report['signal'] = result['signal']
                if status['status'] in ('closed', 'disarmed'):
                    positions, orders = mt5.positions_get(), mt5.orders_get()
                    if positions is None or orders is None or positions or orders:
                        raise ValueError('Account exposure blocks another entry')
                    execution.arm_once(db, 'buy' if result['signal'] == 'long' else 'sell', int(now))
                    def guard(request):
                        if pause_path.exists() or time.time() >= p['end']:
                            raise ValueError('Pause or expiry before submission')
                        fresh_tick, fresh_bars = read_gold(mt5, login, None,
                            server_offset_seconds=execution._server_offset(), execution=True, bar_seconds=seconds)
                        fresh = assess(fresh_bars, fresh_tick, time.time(), p)
                        if cooldown_remaining(db, p, time.time()):
                            raise ValueError('Cooldown before submission')
                        if (fresh['bar_time'] != result['bar_time'] or fresh['signal'] != result['signal']
                                or not entry_allowed(fresh_bars, fresh['signal'], 3)):
                            raise ValueError('Signal changed before submission')
                        try:
                            limits(mt5, db, p, login, time.time())
                        except ValueError as exc:
                            p['pause'] = str(exc)
                            raise
                        request['comment'] = 'kwg-pilot-' + execution._attempt(db)['id']
                    status = execution.process_once(mt5, db, now, before_submit=guard, bar_seconds=seconds)
                    if status['status'] in ('needs_attention', 'submitting', 'closing'):
                        p['pause'] = 'Broker outcome requires review'
                    if status['status'] == 'open' and status['volume'] != .01:
                        p['pause'] = 'Partial fill requires review'
                    report['reason'] = status.get('close_reason') or 'Demo signal processed'
            else:
                report['reason'] = 'Waiting for the next eligible crossover'
    except (ValueError, TypeError, OverflowError) as exc:
        report.update(status='blocked', reason=str(exc)[:160])
    if health.get('tick_time') is not None:
        health['tick_time'] -= execution._server_offset()
    if health.get('tick_time_msc') is not None:
        health['tick_time_msc'] -= execution._server_offset() * 1000
    if not health:
        report['health'] = None
    if p:
        p['reason'] = report['reason']
        save(db, p)
    report['execution'] = status
    report['pilot'] = snapshot(mt5, db, p, status, now, login)
    return report


def snapshot(mt5, db, p, status, now, login):
    recent = [dict(row) for row in db.execute(
        "SELECT side, opened_at, closed_at, realized_net_usd FROM attempts WHERE state='closed' ORDER BY rowid DESC LIMIT 10")]
    closed = db.execute("SELECT count(*), coalesce(sum(realized_net_usd),0) FROM attempts WHERE state='closed'").fetchone()
    floating = None
    try:
        account(mt5, login)
        positions = mt5.positions_get(symbol=SYMBOL)
        if status['status'] in ('closed', 'disarmed') and positions == ():
            floating = 0
        elif status['status'] == 'open':
            row = execution._attempt(db)
            own, _, _, _ = execution._broker_state(mt5, row, now, login)
            if len(own) == 1 and type(own[0].profit) in (int, float) and math.isfinite(own[0].profit):
                floating = own[0].profit
    except (ValueError, TypeError, AttributeError):
        pass
    label = ('standby' if not p else 'expired' if now >= p['end'] and status['status'] in ('closed', 'disarmed')
             else 'needs_attention' if now >= p['end'] or status['status'] in ('needs_attention', 'closing', 'submitting')
             else 'paused' if p['pause'] else 'active')
    return dict(status=label, strategy=p['strategy'] if p else STRATEGY, qualification='unqualified', updated_at=now,
                started_at=p['start'] if p else None, ends_at=p['end'] if p else None,
                reason=p['pause'] or p['reason'] if p else 'Owner activation required',
                completed_trades=closed[0], realized_net_usd=closed[1], floating_usd=floating,
                recent_trades=recent)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('run', 'preview', 'activate'))
    parser.add_argument('--end-utc', help='ISO UTC timestamp; at most seven days from activation')
    parser.add_argument('--enable-demo-execution', action='store_true')
    parser.add_argument('--reviewed-code-sha256')
    args = parser.parse_args()
    if os.environ.get('MT5_RUN_MODE', 'observer') != 'pilot':
        parser.error('MT5_RUN_MODE=pilot must be explicitly configured')
    login = int(os.environ['MT5_DEMO_LOGIN'])
    path = Path.home() / 'gold-pilot.sqlite3'
    pause_path = Path.home() / 'gold-pilot.pause'
    os.umask(0o077)
    import MetaTrader5 as mt5
    if not mt5.initialize(r'C:\Program Files\MetaTrader 5\terminal64.exe', timeout=10000):
        raise SystemExit('MT5 connection unavailable')
    db = open_state(path, login)
    try:
        if args.command == 'preview':
            value = account(mt5, login)
            read_gold(mt5, login, None, server_offset_seconds=execution._server_offset(), execution=False)
            if state(db) is not None:
                raise ValueError('This pilot journal has already been activated')
            print(json.dumps(dict(mode='autonomous-demo-preview', account=login, server=SERVER,
                symbol=SYMBOL, strategy=STRATEGY, code_sha256=identity(), equity=value.equity,
                entry_risk_pct=.1, daily_pause_pct=1, drawdown_pause_pct=5,
                max_positions=1, max_days=7, stop_atr=2, target_atr=3, order_sent=False)))
            return
        if args.command == 'activate':
            if not args.enable_demo_execution or not args.end_utc:
                parser.error('Activation requires explicit execution flag and UTC end')
            if args.reviewed_code_sha256 != identity():
                parser.error('Activation requires the unchanged code hash from the reviewed preview')
            end = datetime.fromisoformat(args.end_utc.replace('Z', '+00:00'))
            if end.utcoffset() != timezone.utc.utcoffset(None):
                parser.error('End must include UTC timezone')
            # The runner owns the manual execution lock; activation writes only configuration.
            activate(mt5, db, login, time.time(), int(end.timestamp()), pause_path)
            print('DEMO_PILOT_ACTIVATED')
            return
        with execution._exclusive(Path.home() / 'gold-one-shot.sqlite3'):
            manual = Path.home() / 'gold-one-shot.sqlite3'
            if manual.exists():
                previous = execution.open_journal(manual, login)
                try:
                    row = execution._attempt(previous)
                    if row and row['state'] not in ('closed', 'disarmed'):
                        raise ValueError('Resolve the manual attempt before pilot startup')
                finally:
                    previous.close()
            bootstrap = True
            while True:
                report = poll_once(mt5, db, login, time.time(), pause_path, bootstrap=bootstrap)
                temporary = SNAPSHOT.with_suffix('.tmp')
                temporary.write_text(json.dumps(report, allow_nan=False), encoding='utf-8')
                temporary.replace(SNAPSHOT)
                print(json.dumps(report, allow_nan=False), flush=True)
                bootstrap = False
                time.sleep(5)
    finally:
        db.close()
        mt5.shutdown()


if __name__ == '__main__':
    main()
