# Jev Gold M5 Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Put Jev (TypeSafe `jev-1.13.0`) into the Gold demo pilot as a decision
layer on M5 candles: shadow-journal first, owner-gated veto later. Jev never
originates, sizes or closes a trade.

**Architecture:** The VPS runner computes the EMA trend signal and categorical
features in code and publishes a candidate feed. The Cloudflare Worker (the only
TypeSafe key holder) calls Jev from its existing per-minute cron. It stores a
per-candle receipt in the existing Durable Object and forwards the receipt over
the existing private control path to the runner. Shadow mode only journals it.
Veto mode defers the entry and submits only on a valid allowing receipt within
90 s of candle close.

**Tech Stack:** Python 3.12 (Windows Python under Wine for the runner), SQLite,
MetaTrader5 SDK, Cloudflare Worker + Durable Objects (JS, `node --test`), Astro +
desk theme for `/vault/trading`, Playwright e2e.

**Design:** `docs/superpowers/specs/2026-10-13-jev-gold-m5-integration.md` (read
first: decision log, frozen veto threshold, non-goals).

**Ground rules for the implementer**

- Demo only. Never touch BTC, the M15 observer (`jev_live.py`, `jev_research.py`,
  `jev-m15.js`) or the M15 scorecard except where a task says so.
- Run Python tests from `ops/trading/`: `python3 -B -m pytest -q <file>`.
  Several pre-existing suites fail on macOS (Windows-only `msvcrt`,
  `CREATE_NO_WINDOW`, missing `.batch3-vibe`, missing `jwt`). Ignore those. Only
  the files named in each task must pass.
- Worker tests: `cd ops/trading/worker && node --test`.
- Frontend script tests: `node --test src/scripts/`.
- Every pilot source file is part of `demo_pilot.identity()`. Changing any of them
  changes the activated code hash. That is expected; the cutover (Task 12) rehashes.
- Commit after every task with the message given. End each commit message with:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`

---

### Task 1: M5 support in the signal evaluator

**Files:**
- Modify: `ops/trading/gold_signal.py:39-44`
- Test: `ops/trading/test_gold_signal.py`

**Step 1: Write the failing test** (append to `GoldSignalTest`)

```python
    def test_gold_m5_trend_demo_uses_quarter_atr_spread(self):
        sample = [{**bar, 'time': bar['time'] // 3} for bar in bars(101)]
        now = NOW // 3
        self.assertEqual(evaluate(sample, 100, 100.5, now, bar_seconds=300, trend_demo=True)['signal'], 'long')
        self.assertEqual(evaluate(sample, 100, 100.5001, now, bar_seconds=300, trend_demo=True)['signal'], 'blocked')
        self.assertEqual(evaluate(sample, 100, 100.5, now + 300, bar_seconds=300, trend_demo=True)['signal'], 'blocked')
        # M5 without the trend policy keeps the strict 10% ceiling.
        self.assertEqual(evaluate(sample, 100, 100.5, now, bar_seconds=300)['signal'], 'blocked')
```

**Step 2: Run it to verify it fails**

Run: `python3 -B -m pytest -q test_gold_signal.py -k m5`
Expected: FAIL with `ValueError: Only M1 and M15 candles are supported`

**Step 3: Minimal implementation** in `evaluate`:

```python
    if type(bar_seconds) is not int or bar_seconds not in (60, 300, 900):
        raise ValueError('Only M1, M5 and M15 candles are supported')
    if type(trend_demo) is not bool or trend_demo and symbol != BTC and bar_seconds not in (60, 300):
        raise ValueError('Trend demo spread policy requires M1 or M5 candles')
```

Keep `validate_market` unchanged: BTC still accepts only 60/900.

**Step 4: Run the whole file**

Run: `python3 -B -m pytest -q test_gold_signal.py`
Expected: all pass. The existing `test_trend_demo_spread_boundary_is_m1_only`
still passes because it uses 60 and 900.

**Step 5: Commit**

```bash
git add ops/trading/gold_signal.py ops/trading/test_gold_signal.py
git commit -m "feat(trading): allow Gold M5 candles in the trend evaluator"
```

---

### Task 2: Pure Jev M5 module — features, hash, question, veto rule

**Files:**
- Create: `ops/trading/jev_m5.py`
- Test: `ops/trading/test_jev_m5.py`

The module is pure: no MT5, no network. The runner, control server, scorecard and
promotion script all import it, so the frozen question and veto rule exist once.

**Step 1: Write the failing tests**

```python
import math
import unittest

import jev_m5


def bars(n=250, start=300, close=lambda i: 100 + i * .01):
    return [dict(time=start + i * 300, open=close(i) - .005, high=close(i) + .02,
                 low=close(i) - .02, close=close(i)) for i in range(n)]


class FeatureTest(unittest.TestCase):
    def test_features_are_categorical_and_deterministic(self):
        b = bars()
        indicators = dict(ema20=102.4, ema50=102.2, atr14=.05)
        stamp = b[-1]['time']
        state = jev_m5.state(b, 102.48, 102.49, indicators, captured_at=stamp + 302)
        self.assertEqual(state['features']['trend'], 'up')
        self.assertIn(state['features']['session'], {'asia', 'london', 'new_york', 'overlap'})
        self.assertEqual(len(state['bars']), 50)
        self.assertNotIn('side', state)            # code side never shown to Jev
        self.assertNotIn('account', state)
        again = jev_m5.state(b, 102.48, 102.49, indicators, captured_at=stamp + 302)
        self.assertEqual(jev_m5.input_sha256(state), jev_m5.input_sha256(again))

    def test_rejects_non_m5_or_short_history(self):
        with self.assertRaises(ValueError):
            jev_m5.state(bars(49), 1, 1.1, dict(ema20=1, ema50=1, atr14=1), captured_at=10**9)
        bad = bars()
        bad[-1]['time'] += 60
        with self.assertRaises(ValueError):
            jev_m5.state(bad, 1, 1.1, dict(ema20=1, ema50=1, atr14=1), captured_at=10**9)


class VetoRuleTest(unittest.TestCase):
    def receipt(self, choice='buy', confidence=.8, status='ok', completed=930, **extra):
        probabilities = {'buy': .1, 'hold': .1, 'sell': .1}
        probabilities[choice] = .8
        return dict(bar_time=600, input_sha256='a' * 64, model=jev_m5.MODEL,
                    question_sha256=jev_m5.QUESTION_SHA256, status=status, choice=choice,
                    confidence=confidence, probabilities=probabilities, completed_at=completed, **extra)

    def test_frozen_rule_table(self):
        allow = lambda r, side='long': jev_m5.allows(r, side=side, bar_time=600,
                                                     input_sha256='a' * 64, now=930)
        self.assertEqual(allow(self.receipt('buy')), (True, 'Jev agreed'))
        self.assertEqual(allow(self.receipt('sell'), 'short'), (True, 'Jev agreed'))
        self.assertFalse(allow(self.receipt('hold'))[0])
        self.assertFalse(allow(self.receipt('sell'))[0])
        self.assertFalse(allow(self.receipt('buy', confidence=.49))[0])
        self.assertFalse(allow(self.receipt(status='timeout'))[0])
        self.assertFalse(allow(None)[0])
        self.assertFalse(allow(self.receipt(completed=600 + 300 + 91))[0])  # after T+90 s
        self.assertFalse(jev_m5.allows(self.receipt(), side='long', bar_time=600,
                                       input_sha256='b' * 64, now=930)[0])
        self.assertFalse(jev_m5.allows(self.receipt(), side='long', bar_time=600,
                                       input_sha256='a' * 64, now=600 + 300 + 91)[0])

    def test_validate_rejects_malformed(self):
        for mutate in (lambda r: r.update(model='jev-latest'),
                       lambda r: r.update(question_sha256='0' * 64),
                       lambda r: r['probabilities'].update(buy=.9),
                       lambda r: r.update(confidence=math.nan),
                       lambda r: r.update(choice='review_setup'),
                       lambda r: r.update(extra='x')):
            value = self.receipt()
            mutate(value)
            with self.assertRaises(ValueError):
                jev_m5.validate_receipt(value)
        self.assertEqual(jev_m5.validate_receipt(self.receipt(status='timeout', choice=None,
            confidence=None, probabilities=None))['status'], 'timeout')
```

**Step 2: Run to verify failure**

Run: `python3 -B -m pytest -q test_jev_m5.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'jev_m5'`

**Step 3: Implement `ops/trading/jev_m5.py`**

```python
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
```

**Step 4: Run the tests**

Run: `python3 -B -m pytest -q test_jev_m5.py`
Expected: PASS. If the `trend == 'up'` assertion fails, fix the fixture, not the
rule (`ema20 > ema50` means up).

**Step 5: Commit**

```bash
git add ops/trading/jev_m5.py ops/trading/test_jev_m5.py
git commit -m "feat(trading): add frozen Gold M5 Jev state, question and veto rule"
```

---

### Task 3: Insert-only receipt store

**Files:**
- Modify: `ops/trading/jev_m5.py` (append)
- Test: `ops/trading/test_jev_m5.py` (append)

**Step 1: Failing test**

```python
import sqlite3, tempfile
from pathlib import Path


class StoreTest(unittest.TestCase):
    def test_first_receipt_wins_and_reads_back(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'r.sqlite3'
            first = VetoRuleTest.receipt(VetoRuleTest(), 'buy')
            self.assertTrue(jev_m5.store_receipt(path, first, received=1031))
            self.assertFalse(jev_m5.store_receipt(path, {**first, 'choice': 'sell'}, received=1032))
            self.assertEqual(jev_m5.load_receipt(path, 600)['choice'], 'buy')
            self.assertIsNone(jev_m5.load_receipt(path, 1200))
            with self.assertRaises(ValueError):
                jev_m5.store_receipt(path, {**first, 'bar_time': 1200, 'model': 'x'}, received=1)
```

**Step 2:** Run `python3 -B -m pytest -q test_jev_m5.py -k Store`. Expected: FAIL
(`AttributeError: store_receipt`).

**Step 3: Implement**

```python
import sqlite3
from contextlib import closing


def _receipts(path):
    db = sqlite3.connect(path)
    with db:
        db.execute('CREATE TABLE IF NOT EXISTS receipts (bar_time INTEGER PRIMARY KEY, '
                   'received REAL NOT NULL, payload TEXT NOT NULL)')
    return db


def store_receipt(path, value, *, received):
    validate_receipt(value)
    with closing(_receipts(path)) as db, db:
        # Insert-only: a later or duplicate receipt never replaces the first one.
        cursor = db.execute('INSERT OR IGNORE INTO receipts VALUES (?, ?, ?)',
                            (value['bar_time'], received, json.dumps(value, sort_keys=True, allow_nan=False)))
        return cursor.rowcount == 1


def load_receipt(path, bar_time):
    if not path.exists():
        return None
    with closing(sqlite3.connect(f'file:{path}?mode=ro', uri=True)) as db:
        row = db.execute('SELECT payload FROM receipts WHERE bar_time=?', (bar_time,)).fetchone()
    return json.loads(row[0]) if row else None
```

**Step 4:** Run `python3 -B -m pytest -q test_jev_m5.py`. Expected: all PASS.

**Step 5: Commit**

```bash
git add ops/trading/jev_m5.py ops/trading/test_jev_m5.py
git commit -m "feat(trading): store Jev M5 receipts insert-only"
```

---

### Task 4: Control server accepts receipts

**Files:**
- Modify: `ops/trading/control_server.py` (the `do_POST` path allowlist near line 40; `run_action`)
- Test: `ops/trading/test_control_server.py`

First, read how existing tests drive `run_action` and the secret check in
`test_control_server.py`, and copy that harness.

**Step 1: Failing tests**

```python
    def test_jev_receipt_requires_pilot_and_stores_once(self):
        receipt = dict(bar_time=600, input_sha256='a' * 64, model='jev-1.13.0',
                       question_sha256=jev_m5.QUESTION_SHA256, status='timeout',
                       choice=None, confidence=None, probabilities=None, completed_at=1030)
        with patch.dict(os.environ, {'MT5_RUN_MODE': 'observer'}):
            self.assertEqual(control.run_action('jev-receipt', receipt)[0], 409)
        with patch.dict(os.environ, {'MT5_RUN_MODE': 'pilot'}), \
                patch.object(control, 'RECEIPTS', self.folder / 'jev-m5-receipts.sqlite3'):
            self.assertEqual(control.run_action('jev-receipt', receipt), (202, {'status': 'stored'}))
            self.assertEqual(control.run_action('jev-receipt', receipt), (200, {'status': 'duplicate'}))
            self.assertEqual(control.run_action('jev-receipt', {**receipt, 'model': 'x'})[0], 400)
```

Import `jev_m5` at the top of the test. `self.folder` is a `TemporaryDirectory`
path. Add it in `setUp` if the harness has none.

**Step 2:** Run `python3 -B -m pytest -q test_control_server.py -k jev`. Expected: FAIL.

**Step 3: Implement**

At module top:

```python
import jev_m5
RECEIPTS = STATE.parent / "jev-m5-receipts.sqlite3"
```

`control_server.py` runs as Linux Python, not Wine Python. It needs `jev_m5.py`
on its path. Check the desktop `Dockerfile`/`desktop.sh` for how
`control_server.py` is copied to `/opt/trading`, and copy `jev_m5.py` the same way
(Task 12 stages it).

At the start of `run_action`, before the `pilot-pause` branch:

```python
    if action == 'jev-receipt':
        if os.environ.get('MT5_RUN_MODE', 'observer') != 'pilot':
            return 409, {'error': 'Pilot mode is not available.'}
        try:
            stored = jev_m5.store_receipt(RECEIPTS, payload, received=time.time())
        except (ValueError, TypeError, KeyError):
            return 400, {'error': 'Invalid Jev receipt.'}
        return (202, {'status': 'stored'}) if stored else (200, {'status': 'duplicate'})
```

Add `"/jev-receipt"` to the `do_POST` path tuple. Then find the body-length limit
in that handler. If it is below 1024 bytes, allow up to 1024 for this path only.

**Step 4:** Run `python3 -B -m pytest -q test_control_server.py`. Expected: PASS.

**Step 5: Commit**

```bash
git add ops/trading/control_server.py ops/trading/test_control_server.py
git commit -m "feat(trading): accept Jev M5 receipts on the private control path"
```

---

### Task 5: Status sidecar routes

**Files:**
- Modify: `ops/trading/status_server.py:177-190` (POST allowlist) and `do_GET` (beside `/jev-m15`)
- Test: `ops/trading/test_status_server.py`

**Step 1: Failing tests**, following the existing `/jev-m15` test style in
`test_status_server.py`:

- `GET /jev-m5` → 200 with the file body when `jev-m5.json` has `status: ready` and
  `checked_at` ≤15 s old. Otherwise 503. Files over 100,000 bytes → 503.
- `POST /control/jev-receipt` is forwarded to `http://desktop:8001/jev-receipt`
  with the `X-KWG-Control-Secret` header. Bodies of 1 to 1024 bytes are accepted
  on this path, and other paths keep the 256-byte limit.

**Step 2:** Run `python3 -B -m pytest -q test_status_server.py -k jev_m5`. Expected: FAIL.

**Step 3: Implement**

- POST: add `"/control/jev-receipt"` to the tuple. Replace
  `if not 0 < length <= 256` with
  `if not 0 < length <= (1024 if self.path == "/control/jev-receipt" else 256)`.
- GET: copy the `/jev-m15` block as `/jev-m5`, reading `SNAPSHOT.with_name('jev-m5.json')`.
  Use the same 100,000-byte and 15-second limits. Do not refactor the M15 block.

**Step 4:** Run `python3 -B -m pytest -q test_status_server.py`. Expected: PASS.

**Step 5: Commit**

```bash
git add ops/trading/status_server.py ops/trading/test_status_server.py
git commit -m "feat(trading): expose Gold M5 Jev feed and receipt route privately"
```

---

### Task 6: M5 strategy in the runner (shadow mode)

**Files:**
- Modify: `ops/trading/demo_pilot.py` (constants ~L17-21, `SOURCES`, `candle_seconds`, `assess`, `cooldown_remaining`, `poll_once`)
- Test: `ops/trading/test_jev_m5_pilot.py` (new; reuse `PilotTest` helpers from `test_demo_pilot.py`)

**Behaviour:**

- `M5_JEV_STRATEGY = 'gold-ema-v1-m5-trend-jev'`. `candle_seconds` → 300.
  `assess` treats it as a trend strategy: signal = EMA20 vs EMA50 side.
  `trend_demo=True`. Cooldown 300 s.
- Add `'jev_m5.py'` to `SOURCES`.
- `TREND_STRATEGY` checks appear in about eight places. Introduce one helper and
  use it at each place:
  `def trending(p): return bool(p and p['strategy'] in (TREND_STRATEGY, M5_JEV_STRATEGY, BTC_STRATEGY, BTC_SCALP_STRATEGY))`.
  This is the only refactor allowed in this task.
- On every new completed candle that is an entry candidate (signal long/short,
  `entry_allowed`, not paused, not baseline, not in cooldown, flat), publish
  `Z:\opt\status\jev-m5.json` atomically (tmp + replace). Contents:
  `{"status":"ready","checked_at":now,"candidate":true,"state":<jev_m5.state(...)>,"input_sha256":...,"bid":...,"ask":...}`.
  When there is no candidate, publish `{"status":"ready","checked_at":now,"candidate":false,"bar_time":...}`.
  The Worker only spends on `candidate: true`.
- Shadow (`p.get('jev_mode') == 'shadow'`): submit exactly as the trend strategy
  does today. Record the candidate in a new table
  `jev_candidates(bar_time PK, side, input_sha256, submitted INTEGER, reason TEXT)`.
  Create it in `open_state` with `CREATE TABLE IF NOT EXISTS`.

**Step 1: Failing tests** (shape; use the existing `tick()` helper with `seconds=300`)

```python
class JevM5PilotTest(PilotTest):          # import PilotTest from test_demo_pilot
    def activate_m5(self, mode='shadow'):
        self.start()
        p = pilot.state(self.db)
        p.update(strategy=pilot.M5_JEV_STRATEGY, jev_mode=mode, code=pilot.identity())
        pilot.save(self.db, p)

    def test_m5_candle_and_cooldown(self):
        self.activate_m5()
        self.assertEqual(pilot.candle_seconds(pilot.state(self.db)), 300)

    def test_shadow_trades_like_trend_and_journals_candidate(self):
        self.activate_m5()
        feed = Path(self.temp.name) / 'jev-m5.json'
        with patch.object(pilot, 'JEV_FEED', feed), patch('demo_pilot.jev_m5.state',
                return_value={'bar_time': 0}):
            self.tick(NOW + 300)                 # baseline candle
            report = self.tick(NOW + 600)        # candidate
        self.assertEqual(report['execution']['status'], 'open')   # shadow never blocks
        self.assertTrue(json.loads(feed.read_text())['candidate'])
        row = self.db.execute('SELECT side, submitted FROM jev_candidates').fetchone()
        self.assertEqual(tuple(row), ('long', 1))
```

Adjust the clock values to the M5 grid used by `tick()`. `bar_time` is derived as
`stamp // 300 * 300 - 300`. Add `JEV_FEED = SNAPSHOT.with_name('jev-m5.json')` to
`demo_pilot.py` so tests can patch it.

**Step 2:** Run `python3 -B -m pytest -q test_jev_m5_pilot.py`. Expected: FAIL
(`AttributeError: M5_JEV_STRATEGY`).

**Step 3: Implement** the behaviour above. Keep the M1 and BTC paths
byte-for-byte equivalent in behaviour.

**Step 4: Regression run**

Run: `python3 -B -m pytest -q test_jev_m5_pilot.py test_demo_pilot.py test_continuous_pilot.py test_two_symbol_pilot.py test_btc_scalp.py`
Expected: all PASS. Existing tests may pin `identity()` hashes; if so, update the
pinned values only, never behaviour.

**Step 5: Commit**

```bash
git add ops/trading/demo_pilot.py ops/trading/test_jev_m5_pilot.py
git commit -m "feat(trading): add Gold M5 trend strategy with Jev shadow journal"
```

---

### Task 7: Veto mode — deferred, fail-closed entry

**Files:**
- Modify: `ops/trading/demo_pilot.py` (`poll_once` entry branch)
- Test: `ops/trading/test_jev_m5_pilot.py`

**Behaviour (veto mode only):**

1. A candidate candle does **not** arm. It stores
   `p['pending_entry'] = {bar_time, side, input_sha256}`, saves it, publishes the
   feed and reports `reason='Waiting for Jev'`.
2. Each later poll with a `pending_entry`:
   `receipt = jev_m5.load_receipt(RECEIPTS, bar_time)`, where
   `RECEIPTS = Path.home() / 'jev-m5-receipts.sqlite3'` (patchable).
   Then call `jev_m5.allows(receipt, side, bar_time, input_sha256, now)`.
   - Allowed → arm and submit through the **existing** `guard`. The guard still
     requires the same `bar_time`, the same side, `entry_allowed`, limits and the
     cooldown. Record `submitted=1`.
   - Not allowed and the deadline has passed, or the receipt is final and
     disagrees → drop `pending_entry`. Record `submitted=0, reason`.
   - Not allowed and no receipt yet, before the deadline → keep waiting.
3. A pause, an expiry, a new candle or a restart clears `pending_entry`. It is
   never replayed into a later candle.
4. Shadow mode also writes the receipt verdict into `jev_candidates.reason` when
   the receipt exists, but never changes submission.

**Step 1: Failing tests**, one per row:

- Veto + agreeing receipt within deadline → order submitted on the next poll.
- Veto + `hold` receipt → no order. Reason contains `Jev chose hold`.
- Veto + no receipt by T+91 s → no order. Reason `No Jev receipt`.
- Veto + receipt with another `input_sha256` → no order.
- Veto + pending entry, then a new candle → pending dropped, no order.
- Veto + pending, then the pause file appears → no order.
- Veto never arms when the code signal is `none`, even if the receipt says `buy`.
  Jev never originates.
- Shadow + `sell` receipt on a long candidate → order still submitted.

Build each receipt with the `VetoRuleTest.receipt` helper and write it with
`jev_m5.store_receipt` into the patched `RECEIPTS` path.

**Step 2:** Run `python3 -B -m pytest -q test_jev_m5_pilot.py`. Expected: new tests FAIL.

**Step 3: Implement** the branch. Keep the existing immediate path for every
non-veto strategy.

**Step 4:** Rerun the Task 6 regression command plus `test_jev_m5.py`. Expected: all PASS.

**Step 5: Commit**

```bash
git add ops/trading/demo_pilot.py ops/trading/test_jev_m5_pilot.py
git commit -m "feat(trading): defer Gold M5 entries for a fail-closed Jev veto"
```

---

### Task 8: Worker M5 snapshot, request and parser

**Files:**
- Create: `ops/trading/worker/src/jev-m5.js`
- Test: `ops/trading/worker/m5.test.mjs`

The JS must reproduce the Python frozen question byte-for-byte, so the
`question_sha256` matches. A test pins the Python digest.

**Step 1: Get the pinned hash**

Run: `cd ops/trading && python3 -B -c "import jev_m5; print(jev_m5.QUESTION_SHA256)"`
Copy the printed value into the test below as `PY_QUESTION_SHA256`.

**Step 2: Failing tests**

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import {m5Snapshot, m5Request, parseM5, QUESTION_SHA256, sha256Canonical} from './src/jev-m5.js';
const PY_QUESTION_SHA256 = '<paste>';
const now = Math.floor(Date.now()/300)*300+20;
const feed = () => ({status:'ready',checked_at:now,candidate:true,input_sha256:'x',bid:4000,ask:4000.1,
  state:{symbol:'XAUUSD-VIP',timeframe:'M5',bar_time:now-20-300,captured_at:now,
    features:{trend:'up',slope_3:'rising',price_vs_ema20:'above',volatility:'normal',spread:'tight',session:'london',last_5:['up','up','down','up','up']},
    bars:Array.from({length:50},(_,i)=>({time:now-20-(50-i)*300,open:4000,high:4001,low:3999,close:4000})),
    account:'omit'}});
test('question hash matches Python', async ()=>assert.equal(await QUESTION_SHA256, PY_QUESTION_SHA256));
test('snapshot recomputes input hash and strips extras', async ()=>{
  const f=feed(); f.input_sha256 = await sha256Canonical({...f.state, account:undefined});
  const s = await m5Snapshot(f, now);
  assert.equal(s.state.account, undefined);
  for (const mutate of [x=>x.checked_at=now-16, x=>x.candidate=false, x=>x.state.timeframe='M15',
      x=>x.state.features.trend='sideways', x=>x.state.bars.at(-1).time+=300, x=>x.input_sha256='0'.repeat(64)]) {
    const g=feed(); g.input_sha256=f.input_sha256; mutate(g); await assert.rejects(m5Snapshot(g, now));
  }
});
test('parser enforces model, choices and probability sum', ()=>{
  const ok={model:'jev-1.13.0',usage:{input_tokens:900},answers:{decision:{type:'choice',choice:'buy',confidence:.7,
    probabilities:{buy:.7,hold:.2,sell:.1}}}};
  assert.equal(parseM5(ok).choice,'buy');
  assert.throws(()=>parseM5({...ok,model:'jev-latest'}));
  assert.throws(()=>parseM5({...ok,answers:{decision:{...ok.answers.decision,probabilities:{buy:.9,hold:.2,sell:.1}}}}));
});
```

Canonical JSON must match Python's `json.dumps(sort_keys=True, separators=(',',':'))`:
sort keys recursively and use no spaces. Numbers must serialise identically. The
features and bars only hold strings and broker prices, and both languages print
those as shortest round-trip floats. Still, add one cross-language fixture test:
hash a small fixture with the Python script and assert the same digest in JS.

**Step 3: Implement `src/jev-m5.js`**

- `canonical(value)`: recursive key-sorted JSON.
- `sha256Canonical(value)`: `crypto.subtle.digest('SHA-256', ...)` → hex.
- `QUESTION`: identical object to Python. `QUESTION_SHA256 = sha256Canonical(QUESTION)` (a Promise).
- `m5Snapshot(feed, now)`: requires `status:'ready'`, `candidate:true`,
  `0 <= now-checked_at <= 15`, symbol/timeframe, `bar_time === floor(now/300)*300-300`,
  `captured_at >= bar_time+300`, and `now - captured_at <= 90`. Requires 50
  strictly increasing, int-timed M5-grid bars with valid OHLC (gaps allowed;
  `features.gap_in_window` is a boolean), and every feature value in its allowed
  enum. A stale `candidate:true` feed (old `bar_time`/`checked_at`) must be rejected. Rebuilds `state` from allowlisted keys only, recomputes `input_sha256` and
  rejects a mismatch. Returns `{bar_time, input_sha256, state}`.
- `m5Request(snapshot)` → `{model:'jev-1.13.0', state:snapshot.state, questions:{decision:QUESTION}}`.
- `parseM5(value)`: like `parseJev`, with keys `buy|hold|sell`, the question key
  `decision`, and `input_tokens` 1..65536.

**Step 4:** Run `cd ops/trading/worker && node --test m5.test.mjs`. Expected: PASS.

**Step 5: Commit**

```bash
git add ops/trading/worker/src/jev-m5.js ops/trading/worker/m5.test.mjs
git commit -m "feat(trading): validate Gold M5 Jev snapshots in the Worker"
```

---

### Task 9: Worker cron, Durable Object receipt and forward

**Files:**
- Modify: `ops/trading/worker/src/jev.js` (`JevObserver.fetch`: add path `/m5`)
- Modify: `ops/trading/worker/src/index.js` (`scheduled`)
- Modify: `ops/trading/worker/wrangler.toml` (`[vars] JEV_M5_LIVE = "false"`; the owner flips it at rollout)
- Test: `ops/trading/worker/m5.test.mjs` (append)

**Behaviour:**

- `scheduled` keeps the M15 branch exactly as it is. Add an independent M5 branch
  that runs when `jevEnabled(env) && env.JEV_M5_LIVE === 'true'`:
  1. Read `/jev-m5` from `STATUS_ORIGIN_URL`, like `readM15` (CF Access service
     token, `redirect:'manual'`, 5 s timeout). Retry up to 5 times, 1 s apart,
     read-only.
  2. If the feed is not a valid candidate (`m5Snapshot` throws), log and stop.
     Spend nothing.
  3. POST to the observer at `https://jev.internal/m5`.
- `JevObserver` `/m5` POST: in one transaction, skip if `m5:<bar_time>` exists
  (one paid call per candle). Otherwise reserve `RESERVE` from the **same**
  `record.charged` ledger, refuse when `charged + RESERVE > LIMIT`, and write
  `m5:<bar_time>` = running. Call TypeSafe with a 15 s timeout. Store the final
  receipt with `status` ∈ ok|timeout|unavailable|budget_exhausted|invalid, then
  refund unused reservation exactly as M15 does. Return the receipt in the
  Python `validate_receipt` shape, with `completed_at` in **seconds**.
- After the observer returns (including on failure statuses), the cron forwards
  the receipt to `${STATUS_ORIGIN_URL}/control/jev-receipt`. Send the CF Access
  service token and `X-KWG-Control-Secret: env.TRADING_CONTROL_SECRET`, with a
  `Content-Type: application/json` body ≤1024 bytes, `redirect:'manual'` and a
  5 s timeout. No retry is needed: the runner fails closed.
- The forwarded body carries only the receipt fields: no key, usage, cost or
  snapshot.

**Step 1: Failing tests**

- No-candidate feed → zero TypeSafe calls, ledger unchanged.
- Candidate → one TypeSafe call. Then a second cron for the same candle → still
  one call total.
- Ledger near `LIMIT` → `budget_exhausted` receipt forwarded, zero TypeSafe calls.
- TypeSafe timeout → `timeout` receipt forwarded; the reservation is kept.
- Forward request: path `/control/jev-receipt`, has the control secret header,
  the body parses, its keys exactly equal the Python receipt keys, and it does
  not contain `TYPESAFE_API_KEY`.
- `JEV_M5_LIVE` unset → M5 branch inert, and the M15 branch behaves as before
  (existing tests stay green).

Mock `globalThis.fetch` by URL, as `m15.test.mjs` does.

**Step 2:** Run `node --test`. Expected: new tests FAIL.

**Step 3: Implement.**

**Step 4:** Run `cd ops/trading/worker && node --test`. Expected: all PASS (30 existing + new).

**Step 5: Commit**

```bash
git add ops/trading/worker/src/jev.js ops/trading/worker/src/index.js ops/trading/worker/wrangler.toml ops/trading/worker/m5.test.mjs
git commit -m "feat(trading): call Jev once per Gold M5 candidate and forward receipts"
```

---

### Task 10: M5 scorecard (feedback loop)

**Files:**
- Create: `ops/trading/jev_m5_scorecard.py`
- Test: `ops/trading/test_jev_m5_scorecard.py`

**Behaviour:** Open the Gold runner journal and the receipts DB read-only
(`file:...?mode=ro`). For each `jev_candidates` row with `submitted=1` and a
closed attempt, read realised net P/L from the existing closed-attempt fields.
Look up which columns `demo_one_shot` stores for closed P/L. If profit, commission
and swap are not all journalled, report P/L as `null` and exclude the row from
averages with an explicit `unresolved` count. **Do not** fetch from MT5.

Output (`jev-m5-scorecard.json`, atomic write):

```json
{"status":"ready","generated_at":0,"candidates":0,"closed":0,
 "receipts":{"ok":0,"timeout":0,"unavailable":0,"budget_exhausted":0,"invalid":0,"missing":0,"late":0},
 "all":{"trades":0,"avg_net_usd":null},
 "jev_kept":{"trades":0,"avg_net_usd":null},
 "jev_vetoed":{"trades":0,"avg_net_usd":null},
 "gate":{"min_closed":50,"bad_receipt_max":0.2,"passes":false,"reasons":["..."]},
 "qualification":"demo fills; unqualified; not a profitability claim"}
```

Compute `jev_kept` with `jev_m5.allows(...)` evaluated at receipt time
(`now=receipt.completed_at`), so shadow trades are scored by the same frozen rule
veto mode will use. `gate.passes` is true only when closed ≥50, bad receipts
(non-ok + missing + late) / candidates < 0.2, and
`jev_kept.avg_net_usd > all.avg_net_usd`. The gate's `reasons` list every failed
condition.

**Step 1: Failing tests:** an empty journal gives `passes: false` with three
reasons; 50 synthetic closed trades with a kept-subset advantage gives `passes: true`;
a 20% bad-receipt rate gives `passes: false`; unresolved P/L is excluded and
counted; the DB is opened read-only (writes raise).

**Step 2:** `python3 -B -m pytest -q test_jev_m5_scorecard.py` → FAIL.

**Step 3: Implement.**

**Step 4:** → PASS.

**Step 5: Commit**

```bash
git add ops/trading/jev_m5_scorecard.py ops/trading/test_jev_m5_scorecard.py
git commit -m "feat(trading): score Gold M5 Jev shadow decisions against demo fills"
```

---

### Task 11: Scorecard API and dashboard panel

**Files:**
- Modify: `ops/trading/status_server.py` (`GET /jev-m5-scorecard`, a copy of the `/jev-scorecard` block with a 120 s freshness check)
- Modify: `ops/trading/worker/src/index.js` (owner-authenticated `GET /api/trading/jev-m5-scorecard`, passthrough with no-store)
- Create: `src/pages/api/trading/jev-m5-scorecard.ts` (copy `jev-scorecard.ts`: dev fixture only, 404 in production)
- Create: `src/scripts/trading-jev-m5.mjs` + `src/scripts/trading-jev-m5.test.mjs`
- Create: `src/components/JevM5Panel.astro`; include it in `src/pages/vault/trading.astro`
- Test: `tests/trading-jev-m5.e2e.ts`

Read `DESIGN.md` → "Trading exception" and copy the patterns of
`JevScorecard.astro`, `trading-jev-scorecard.mjs` and `src/styles/desk.scss`. Use
desk tokens only: no raw colours or px.

**Panel content:**
- Mode badge (Shadow / Veto).
- Last receipt: choice, confidence, age.
- Kept vs all avg net (sign plus arrow, never colour alone).
- Gate checklist with each reason.
- Receipt-health counts.
- Budget remaining.
- Footer text: "Demo only. Jev can block an entry; it never opens one."

**Steps:**
1. Write `trading-jev-m5.test.mjs`: the state-mapping function turns the JSON into
   view text for the empty, populated, gate-passing and unavailable cases. Run
   `node --test src/scripts/` → FAIL.
2. Implement the mapping → PASS.
3. Build the panel. Run `npx astro check && npm run build` → no errors.
4. Write the e2e test against the dev fixture, at desktop and 375 px mobile
   widths, checking keyboard focus is visible. Run it with the repo's existing
   e2e command from `e2e.config.ts` / `package.json`.
5. Worker test: route requires Access identity; non-owner → 403.
6. Commit:

```bash
git add ops/trading/status_server.py ops/trading/worker/src/index.js src/pages/api/trading/jev-m5-scorecard.ts src/scripts/trading-jev-m5.mjs src/scripts/trading-jev-m5.test.mjs src/components/JevM5Panel.astro src/pages/vault/trading.astro tests/trading-jev-m5.e2e.ts
git commit -m "feat(trading): show Gold M5 Jev shadow scorecard on the vault desk"
```

---

### Task 11b: Accept the M5 strategy in status allowlists and labels

Added during execution (Task 6 review). Without it, M5 pilot snapshots are
rejected as `Invalid pilot state`.

**Files:**
- Modify: `ops/trading/status_server.py` (`sanitize_pilot` gold strategy tuple; pass
  through `jev_mode` only when it is `shadow` or `veto`)
- Modify: `src/scripts/trading-pilot.mjs` (`normalizePilot`, same rules) + its test
- Modify: `src/pages/vault/trading.astro` (strategy description and timeframe labels for
  `gold-ema-v1-m5-trend-jev`: "M5 trend · Jev shadow/veto")
- Modify: `ops/trading/fixtures/status-contract.json` if the shared contract lists strategies
- Test: `test_status_server.py`, `src/scripts/trading-pilot.test.mjs`, `ops/trading/worker/test.mjs`

TDD each. Commit: `feat(trading): accept Gold M5 Jev strategy in status contract`.

---

### Task 12: Staged cutover to M5 shadow, and owner-gated promotion

**Files:**
- Create: `ops/trading/switch-pilot-m5.py`, `ops/trading/stage-m5-jev.ps1`
- Create: `ops/trading/promote-jev-veto.py`
- Test: `ops/trading/test_switch_m5.py`, `ops/trading/test_promote_jev.py`

Every staging list, manifest and generated Dockerfile that ships `demo_pilot.py`
or `control_server.py` must also ship `jev_m5.py`. That includes `Dockerfile`,
`deploy-demo-pilot.py`, `deploy-demo-pilot.ps1`, `stage-m1-pilot.ps1`,
`stage-two-symbol-pilot.ps1`, `migrate-two-symbol-pilot.py` and the new
`stage-m5-jev.ps1`. Add a test that fails if one ships without the other.

Model both on `switch-pilot-m1.py`, `stage-m1-pilot.ps1`,
`cutover-two-symbol-pilot.py` and their tests. Read them fully first.

**`switch-pilot-m5.py <stage> --reviewed-code-sha256 <hash>`:**
- Verifies the staged file hashes, including `jev_m5.py`.
- Refuses if Gold is open, pending or `needs_attention`. Refuses if paused, or
  if the owner pause file exists.
- Backs up the journal (SQLite backup API plus integrity check).
- Under the runner lock, sets `strategy=M5_JEV_STRATEGY`, `jev_mode='shadow'` and
  `code=<reviewed>`, preserving start/end, limits, receipts and `last_bar=None`.
  The next candle is a baseline.
- Never touches the BTC journal. Never sends a broker request.
- Prints `M5_JEV_SHADOW_DEPLOYED`.

**`promote-jev-veto.py --owner-approved`:**
- Runs `jev_m5_scorecard` read-only and refuses unless `gate.passes`.
- Refuses without `--owner-approved`.
- Under the lock, flips only `jev_mode` to `veto` and appends an audit row
  `jev_mode_changes(at, from, to, scorecard_sha256)`.
- Never flips back automatically. Demotion to shadow is allowed any time with
  `--demote`, also audited.

**Tests:** refusals (open position, pause, hash mismatch, failing gate, missing
flag), success paths preserving limits/receipts, BTC journal byte-identical, and
an audit row written.

Commit:

```bash
git add ops/trading/switch-pilot-m5.py ops/trading/stage-m5-jev.ps1 ops/trading/promote-jev-veto.py ops/trading/test_switch_m5.py ops/trading/test_promote_jev.py
git commit -m "feat(trading): stage Gold M5 Jev shadow cutover and owner-gated veto promotion"
```

---

### Task 13: Runbook and handoff

**Files:**
- Create: `ops/trading/JEV-M5.md` (deployment order, verification, stop/rollback, what each status means)
- Modify: `ops/trading/HANDOFF.md` (replace the stale "Now / Running / Next" block)
- Modify: `CLAUDE.md` trading section: fix the stale "no automatic or agent-initiated
  order path" line to describe the autonomous demo pilot and the Jev shadow/veto.

**Deployment order for the runbook (owner-run):**
1. `stage-m5-jev.ps1` (local PowerShell, SSH passphrase entered locally). Keep the
   printed stage path and reviewed hash.
2. Deploy the Worker with `wrangler deploy --keep-vars` and `JEV_M5_LIVE="false"`.
   Publish the frontend through Dokploy.
3. On the VPS: `python3 -B <stage>/switch-pilot-m5.py <stage> --reviewed-code-sha256 <hash>`.
   Expect `M5_JEV_SHADOW_DEPLOYED`.
4. Set `JEV_M5_LIVE="true"` and redeploy the Worker. Verify the first receipt in
   `/api/trading/jev-m5-scorecard` and in Worker logs.
5. Shadow until the gate passes. Then the owner reviews and runs
   `promote-jev-veto.py --owner-approved`.
- **Stop Jev spend:** set `JEV_M5_LIVE="false"`. Shadow trading continues without
  receipts; veto mode then skips every entry (fail-closed).

**Verification before marking done:**

```bash
cd ops/trading && python3 -B -m pytest -q test_gold_signal.py test_jev_m5.py test_jev_m5_pilot.py test_jev_m5_scorecard.py test_switch_m5.py test_promote_jev.py test_control_server.py test_status_server.py test_demo_pilot.py test_continuous_pilot.py test_two_symbol_pilot.py test_btc_scalp.py
```

```bash
cd ops/trading/worker && node --test
```

```bash
node --test src/scripts/ && npx astro check && npm run build
```

All must pass. Commit:

```bash
git add ops/trading/JEV-M5.md ops/trading/HANDOFF.md CLAUDE.md
git commit -m "docs(trading): add Gold M5 Jev runbook and refresh handoff"
```

---

## Out of scope (do not build)

- Live account, BTC with Jev, Jev-originated entries, Jev exits or sizing.
- Automatic promotion, threshold tuning, budget increases.
- Retraining or "learning"; the feedback loop is the scorecard.
- Any change to the M15 observer, the M15 scorecard or the manual demo controls.
