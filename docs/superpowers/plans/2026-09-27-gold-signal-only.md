# Gold Signal-Only Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Qualify gold data and record restart-safe EMA crossover observations on the existing demo VPS, without submitting orders.

**Architecture:** Reuse the MT5 desktop and Python SDK already qualified on the VPS. Extract its account guard into an importable module, add a small pure strategy module and one CLI observer using standard-library SQLite for candle deduplication. No HTTP server, new package, AI agent, or Worker is needed for this milestone.

**Tech Stack:** Existing Windows Python 3.12.10 under Wine 9, MetaTrader5 5.0.6180, NumPy 1.26.4, Python unittest/sqlite3, existing Docker Compose.

**Spec:** `CLAUDE.md`, sections “Trading setup handoff” and “Resume sequence and strategy baseline”; `ops/trading/README.md`, “Current scope and next steps.”

## Global Constraints

- Gold only: `XAUUSD-VIP`; expected server `VTMarkets-Demo`; explicitly supplied demo login; Algo Trading off.
- Completed M15 candles only; at least 250 history bars; SMA-seeded EMA20/EMA50 and Wilder ATR14.
- Quote age at most 30 seconds; negative age is invalid. No inferred timezone correction.
- Valid finite positive bid/ask and OHLC; spread at most 10% ATR; fail closed on invalid data.
- Never call order submission, modify positions, enable Algo Trading, or implement an execution toggle in this milestone.
- Keep credentials, account identifiers in output, runtime databases, and terminal state out of Git. Retain loopback-only desktop access.
- Preserve the existing VPS volume and unrelated apps. The current runtime remains qualification-only.
- Tests use stdlib unittest; no new dependencies. No UI changes in this plan.

## Review Focus

- Future timestamps, including the observed three-hour discrepancy, must block observations (Task 1).
- NaN/Infinity, duplicate/out-of-order bars and malformed OHLC must never generate a signal (Task 2).
- Weekend gaps are allowed in historical data, but an old latest candle must not generate a current signal (Tasks 1–2).
- Restart, missed polls and repeated candles must not replay historical signals (Task 3).
- Disconnects, account switches and unwritable/corrupt state must fail closed without silently recreating state (Task 3).

## Documentation checked

- Context7 `/python/cpython`, queried 2026-09-27: SQLite connection contexts commit/rollback transactions but do not close connections. Use parameter binding and explicit close. [Python SQLite reference](https://docs.python.org/3.12/library/sqlite3.html).
- Context7's MetaTrader search returned wrappers and mirrors, not the official SDK reference. Use MetaQuotes directly for SDK decisions; do not add a wrapper.
- [copy_rates_from_pos](https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesfrompos_py): position zero is the current bar; request position 1 and 250 bars; a failed request returns None. Available history depends on terminal settings.
- [copy_ticks_from](https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksfrom_py): tick/bar times are documented as UTC. Treat the observed mismatch as unresolved evidence, not proof of a fixed broker offset.

## File map

| File | Responsibility |
| --- | --- |
| `ops/trading/mt5_data.py` (new) | Shared account guard, bounded gold subscription/read, timestamp validation |
| `ops/trading/verify-demo.py` (modify) | Gold-only diagnostic using the shared module |
| `ops/trading/test_verify_demo.py` (modify) | Existing guard coverage plus fake-SDK data checks |
| `ops/trading/gold_signal.py` (new) | Pure EMA, ATR and crossover evaluation |
| `ops/trading/test_gold_signal.py` (new) | Hand-calculated indicators and malformed-input checks |
| `ops/trading/observe-gold.py` (new) | CLI, SQLite candle ledger, polling and structured output |
| `ops/trading/test_observe_gold.py` (new) | Temporary SQLite database and fake-SDK lifecycle checks |
| `ops/trading/Dockerfile`, `.dockerignore` (modify) | Include the new runtime modules in the existing image |
| `ops/trading/.gitignore`, `README.md`, `CLAUDE.md` (modify) | Exclude databases; operator instructions and verified status |

## Task 1: Gold-only data qualification

**Files:** `mt5_data.py`, `verify-demo.py`, `test_verify_demo.py` under `ops/trading/`.

**Interfaces:**
- Move existing `validate_account(account, terminal, login, server) -> None` unchanged into `mt5_data.py`; caller imports it normally.
- `validate_tick(tick, now: float) -> float`: returns age seconds, raises ValueError for nonfinite/invalid prices or timestamp, crossed quotes, or age outside `[0, 30]`. Use `time_msc / 1000` where positive, otherwise `time`.
- `read_gold(mt5, login: int, now: float) -> tuple[object, list[dict]]`: validates identity on every call, selects exact gold symbol, returns tick and 250 bars requested at M15 position 1. No hidden clock correction or order operations.
- Bars have `time`, `open`, `high`, `low`, `close`; preserve integer epoch timestamps and convert NumPy scalars to native values at the boundary.

- [ ] **1. Write failing tests.** Extend the existing unittest file with fake SDK objects. Assert tick ages 0 and 30 pass; -0.001 and 30.001 fail; zero/NaN/Infinity/crossed prices fail. Assert exact SDK request `('XAUUSD-VIP', TIMEFRAME_M15, 1, 250)`, and wrong/live account, disconnected terminal, missing tick or 249 bars fail. Retain all existing account guard cases.
- [ ] **2. Run:** `python -B -m unittest discover -s ops/trading -p test_verify_demo.py`. Expected: new tests fail because shared data functions do not exist.
- [ ] **3. Implement the interfaces.** Keep `read_gold` a single attempt. In the diagnostic CLI, retry missing subscription data once per second for at most 15 seconds using monotonic time; account mismatch/Algo-on errors terminate immediately. Print only whitelisted diagnostic fields: symbol, UTC host time, raw tick time, age, history count, latest bar time and reason. A failed freshness check must exit nonzero, not report overall readiness.
- [ ] **4. Run the test command again.** Expected: all pass, with no installed MT5 SDK needed for pure/fake tests. Verify `--help` works without connecting to MT5.
- [ ] **5. Commit only these files:** `git add ops/trading/mt5_data.py ops/trading/verify-demo.py ops/trading/test_verify_demo.py`; `git commit -m "Validate gold demo market data"`.

## Task 2: Deterministic signal calculation

**Files:** `ops/trading/gold_signal.py`, `ops/trading/test_gold_signal.py`.

**Interfaces:**
- `ema(values: list[float], period: int) -> list[float | None]`: same-length output; first value at index period-1 is the SMA; subsequent alpha `2/(period+1)`.
- `atr(bars: list[dict], period: int = 14) -> list[float | None]`: TR starts at index 1 using previous close; SMA of TR indices 1..14 seeds ATR at index 14; Wilder recurrence thereafter.
- `evaluate(bars: list[dict], bid: float, ask: float, now: float) -> dict`: returns `bar_time`, `signal` (`long`, `short`, `none`, `blocked`), `reason`, `ema20`, `ema50`, `atr14`. Indicators may be null for blocked invalid inputs.

- [ ] **1. Write failing tests.** Assert `ema([1,2,3,4],3) == [None,None,2,3]`; constant close 100 with highs 101/lows 99 yields ATR14=2 and no cross. Use 249 constant closes of 100 then close 101 (valid enclosing OHLC) to assert long; final close 99 asserts short. Equality on both last bars gives none. Spread 0.2 with ATR2 passes; 0.2001 blocks. Reject nonfinite data, invalid OHLC enclosure, nonpositive prices, fewer than 250 bars, duplicate/reversed timestamps. Allow older session gaps, but require the last two candles to be 900 seconds apart and latest opening time to equal `floor(now/900)*900-900`; stale/future latest bars block.
- [ ] **2. Run:** `python -B -m unittest discover -s ops/trading -p test_gold_signal.py`. Expected: fail before implementation.
- [ ] **3. Implement the interfaces.** Cross long when previous EMA20 <= EMA50 and latest EMA20 > EMA50; reverse comparisons for short. Require positive ATR. Use a fixed 250-bar rolling input for reproducibility and record that seed convention. No sizing, virtual fills, P&L or execution logic yet; these are observations only.
- [ ] **4. Run the tests.** Expected: all pass. Re-run Task 1's test file to confirm the data contract still agrees.
- [ ] **5. Commit:** `git add ops/trading/gold_signal.py ops/trading/test_gold_signal.py`; `git commit -m "Add pure gold EMA crossover signals"`.

## Task 3: Persistent signal-only observer

**Files:** `ops/trading/observe-gold.py`, `ops/trading/test_observe_gold.py`, `ops/trading/.gitignore`.

**Interfaces:**
- CLI `observe-gold.py --login EXPECTED_DEMO_LOGIN --state PATH [--once]`; require an explicit state path verified to reside inside the persistent Wine home. Do not guess a Wine home path during implementation.
- `record_observation(db: sqlite3.Connection, result: dict, observed_at: float, bootstrap: bool) -> bool`: parameterized insert; returns true only for a new candle. Ledger primary key is `bar_time` for this one-symbol, one-strategy DB; metadata pins expected login/server/symbol and strategy version `gold-ema-v1`. Mismatched metadata is a hard failure.
- `poll_once(mt5, db, login: int, now: float, bootstrap: bool) -> dict`: consumes Tasks 1–2, returns a signal-only status. Never submits orders.

- [ ] **1. Write failing tests.** Using stdlib tempfile and a fake SDK whose `order_send` raises AssertionError, assert first valid startup candle is stored as `baseline` without a long/short emission; duplicate polls and restart on the same candle add no row; the next adjacent valid candle adds exactly one row. A jump over missed candles stores the latest as a new baseline without replay. Repeat after closing/reopening SQLite. Simulate disconnected/wrong account, stale tick and invalid bars: output blocked and no signal row. Corrupt DB, metadata mismatch and write failure must terminate rather than reset. Assert persisted JSON has `mode=signal-only`, no login/password, and status from Task 2.
- [ ] **2. Run:** `python -B -m unittest discover -s ops/trading -p test_observe_gold.py`. Expected: fail before implementation.
- [ ] **3. Implement the CLI and interfaces.** Poll every 5 seconds using monotonic scheduling; revalidate account every poll. Persist baseline and observations transactionally before emitting JSON. On startup or reconnection, establish a fresh baseline; never replay offline candles. SQLite is the authoritative journal, stdout is informational and may be missed on a crash. Roll back on failure and explicitly close connections. On data failures emit blocked status without logging secrets; on identity/Algo-on/state failures exit nonzero. Use SDK shutdown in finally and handle Ctrl+C. Add `*.sqlite3`, `*.sqlite3-*` to the local ignore file. No daemon framework or restart-on-error loop for fatal failures.
- [ ] **4. Run:** `python -B -m unittest discover -s ops/trading -p 'test_*.py'`. Expected: all three test files pass without contacting a broker. Verify unknown CLI arguments fail and `--once` performs one poll only.
- [ ] **5. Commit only the Task 3 files:** `git commit -m "Persist signal-only gold observations"` after explicit staging.

## Task 4: Package and qualify on the existing VPS

**Files:** `ops/trading/Dockerfile`, `.dockerignore`, `README.md`, `CLAUDE.md`.

**Interfaces:** Existing desktop/container and persistent volume remain the deployment boundary; observer runs through `docker exec` with Windows Python, not a second MT5 session.

- [ ] **1. Extend Docker COPY/build allowlist for the three new runtime files.** Keep tests, credentials and databases out of build context. Confirm the embedded Python can import sqlite3 inside Wine before declaring the persistence design qualified; if absent, use the official full Python installer in a separate tested image revision, not a new database service.
- [ ] **2. Validate locally:** run all Python tests, `bash -n ops/trading/desktop.sh`, `bash -n ops/trading/check-wine.sh`, `docker compose -f ops/trading/compose.yml config --quiet`, and `git diff --check`. Expected: zero exits. No Astro build is needed because no application files change.
- [ ] **3. Record clock evidence through authenticated VPS access:** `date -u`, `timedatectl status`, and Windows Python UTC/epoch alongside raw gold ticks. Run the gold diagnostic during a gold session and compare multiple advancing ticks over at least 60 seconds. If future timestamps persist, leave observation blocked and record the exact finding; seek broker/platform clarification before any normalization. Closed-market data is not a passing freshness test. Offline Tasks 2–3 may still finish while this external gate is pending.
- [ ] **4. Deploy only this Compose project after taking an owner-only backup of its persistent volume.** Keep backups outside Git and never print terminal configuration. Preserve the previous image tag for rollback. Copy only reviewed source, build, recreate only the desktop service and verify loopback binding plus saved demo login. Document rollback to the preserved image without deleting volumes.
- [ ] **5. Run observer `--once` with an explicit state path inside the persistent home, then a bounded foreground observation across two completed M15 transitions.** Expected: baseline first, one record per new valid candle, no duplicates; a crossover is not required to pass. Stop it deliberately, restart the container, and repeat to verify SQLite persistence and baseline suppression. Recheck Algo Trading off. Do not leave an unattended process running as part of this qualification.
- [ ] **6. Update README and handoff with commands, data evidence, test results and remaining blockers.** Report what was actually observed, not predicted. Commit only these packaging/docs files with `git commit -m "Package and document gold observer qualification"` after explicit staging.

## Completion and follow-on plans

This milestone completes when offline tests pass and the VPS demonstrates valid gold observations, persistence and restart behavior with zero order calls. If gold is closed or timestamps unresolved, label it **implemented, runtime qualification pending**.

Next, write a separate demo-execution plan covering 0.1% sizing, one gold position, broker-held 2ATR stop/3ATR target, 1% persisted UTC daily-loss pause, position ownership, opposite-cross exits, uncertain-order reconciliation and broker stop/fill constraints. Signal-only results do not validate these controls or demonstrate profitability.

Write the dashboard/Worker plan separately after the observation contract is proven. Read DESIGN.md and PRODUCT.md and use the required design skill then. Preserve existing Astro authentication; never expose broker credentials or the desktop through the Worker. No UI or public endpoint is authorized by this plan's execution tasks.

## Self-review

- Data/strategy/ledger interfaces align; all five Review Focus cases have named tests.
- Execution risk rules and dashboard requirements are explicitly deferred, not silently omitted or represented as implemented.
- No new dependencies or speculative order abstraction; four independently reviewable tasks.
- This document is a plan only. Review it and choose Native or Subagent-driven execution before implementation, as required by the writing-plans skill.

## Execution progress — 2026-09-27

- Tasks 1–3 implemented and locally tested: 9 unittest cases pass. Local commits:
  `70bcc44`, `c257b16`, `0b322ee`.
- Task 4 packaging and local checks pass. Wine Python imported SQLite 3.49.1.
- The VPS clock reports synchronized UTC. Gold's last tick was roughly 34.5 hours
  old during market closure, so fresh advancing ticks and two completed live
  transitions cannot be qualified yet.
- A root-only, mode-600 backup of the existing MT5 volume was made on the VPS at
  `/opt/kwg-mt5-qualification/backups/mt5-home-20260927.tar.gz`; the prior image
  is tagged `kwg-mt5-desktop:pre-gold-20260927`. No credentials entered Git.
- Reviewer found no Critical/Important code issue; corrected stale documentation
  that claimed the current diagnostic checked Bitcoin too.
- Ruling: future or stale gold timestamps block observations. Market-closed
  runtime qualification remains pending; the cost is delayed live observation.
