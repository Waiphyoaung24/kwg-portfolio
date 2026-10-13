"""Frozen Gold M5 Jev state, question and veto rule; pure code, no broker or network."""
from datetime import datetime, timezone
import hashlib
import json
import math

MODEL = 'jev-1.13.0'
SECONDS = 300
DEADLINE = 90          # seconds after candle close
THRESHOLD = .5         # frozen before shadow; see design decision 8
CHOICES = ('buy', 'hold', 'sell')
STATUSES = ('ok', 'timeout', 'unavailable', 'budget_exhausted', 'invalid')
QUESTION = {'type': 'choice',
    'instructions': ('Using only the supplied Gold M5 state at captured_at, choose whether conditions '
                     'favour a long entry, a short entry, or no entry now. Do not infer missing data. '
                     'Ordinary code owns all risk, sizing and execution; this is a demo assessment.'),
    'criteria': {'buy': 'Conditions favour a long entry now.',
                 'hold': 'No clear edge, or the evidence conflicts.',
                 'sell': 'Conditions favour a short entry now.'}}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


QUESTION_SHA256 = digest(QUESTION)


def _bucket(value, low, high, names):
    return names[0] if value < low else names[2] if value > high else names[1]


def _session(stamp):
    hour = datetime.fromtimestamp(stamp, timezone.utc).hour
    if 12 <= hour < 16:
        return 'overlap'
    return 'london' if 7 <= hour < 12 else 'new_york' if 16 <= hour < 21 else 'asia'


def state(bars, bid, ask, indicators, *, captured_at):
    if len(bars) < 50 or any(b['time'] % SECONDS for b in bars[-50:]):
        raise ValueError('Need 50 completed M5 bars')
    if any(bars[i]['time'] - bars[i - 1]['time'] != SECONDS for i in range(len(bars) - 49, len(bars))):
        raise ValueError('M5 bars must be contiguous')
    numbers = [bid, ask, captured_at, *(indicators[k] for k in ('ema20', 'ema50', 'atr14'))]
    if not all(type(x) in (int, float) and math.isfinite(x) for x in numbers) or ask < bid or indicators['atr14'] <= 0:
        raise ValueError('Invalid market numbers')
    recent = [{k: b[k] for k in ('time', 'open', 'high', 'low', 'close')} for b in bars[-50:]]
    close, atr = recent[-1]['close'], indicators['atr14']
    ranges = sorted(b['high'] - b['low'] for b in recent)
    median = ranges[len(ranges) // 2] or atr
    closes = [b['close'] for b in recent]
    slope = [closes[-1] - closes[-2], closes[-2] - closes[-3], closes[-3] - closes[-4]]
    features = dict(
        trend='up' if indicators['ema20'] > indicators['ema50'] else 'down' if indicators['ema20'] < indicators['ema50'] else 'flat',
        slope_3='rising' if all(x > 0 for x in slope) else 'falling' if all(x < 0 for x in slope) else 'mixed',
        price_vs_ema20=_bucket(close - indicators['ema20'], -.1 * atr, .1 * atr, ('below', 'at', 'above')),
        volatility=_bucket(atr / median, .75, 1.25, ('low', 'normal', 'high')),
        spread=_bucket((ask - bid) / atr, .05, .15, ('tight', 'normal', 'wide')),
        session=_session(recent[-1]['time'] + SECONDS),
        last_5=['up' if b['close'] > b['open'] else 'down' if b['close'] < b['open'] else 'flat' for b in recent[-5:]])
    return dict(symbol='XAUUSD-VIP', timeframe='M5', bar_time=recent[-1]['time'],
                captured_at=captured_at, features=features, bars=recent)


def input_sha256(value):
    return digest(value)


def validate_receipt(value):
    keys = {'bar_time', 'input_sha256', 'model', 'question_sha256', 'status', 'choice',
            'confidence', 'probabilities', 'completed_at'}
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError('Invalid receipt fields')
    if (type(value['bar_time']) is not int or value['bar_time'] % SECONDS or value['model'] != MODEL
            or value['question_sha256'] != QUESTION_SHA256 or value['status'] not in STATUSES
            or not isinstance(value['input_sha256'], str) or len(value['input_sha256']) != 64
            or type(value['completed_at']) not in (int, float) or not math.isfinite(value['completed_at'])):
        raise ValueError('Receipt does not match the frozen request')
    if value['status'] != 'ok':
        if any(value[k] is not None for k in ('choice', 'confidence', 'probabilities')):
            raise ValueError('Failed receipt carries a decision')
        return value
    p, c = value['probabilities'], value['confidence']
    if (value['choice'] not in CHOICES or not isinstance(p, dict) or set(p) != set(CHOICES)
            or not all(type(x) in (int, float) and math.isfinite(x) and 0 <= x <= 1 for x in [c, *p.values()])
            or abs(sum(p.values()) - 1) > .001 or max(p, key=p.get) != value['choice']):
        raise ValueError('Invalid Jev decision')
    return value


def allows(receipt, *, side, bar_time, input_sha256, now):
    """Veto rule: allow only an on-time, matching, confident, agreeing decision."""
    deadline = bar_time + SECONDS + DEADLINE
    if receipt is None:
        return False, 'No Jev receipt'
    try:
        validate_receipt(receipt)
    except ValueError as error:
        return False, str(error)
    if receipt['bar_time'] != bar_time or receipt['input_sha256'] != input_sha256:
        return False, 'Receipt is for another candle'
    if now > deadline or receipt['completed_at'] > deadline:
        return False, 'Jev receipt missed the 90-second deadline'
    if receipt['status'] != 'ok':
        return False, f"Jev {receipt['status']}"
    if receipt['choice'] != {'long': 'buy', 'short': 'sell'}[side]:
        return False, f"Jev chose {receipt['choice']}"
    if receipt['confidence'] < THRESHOLD:
        return False, 'Jev confidence below 0.5'
    return True, 'Jev agreed'
