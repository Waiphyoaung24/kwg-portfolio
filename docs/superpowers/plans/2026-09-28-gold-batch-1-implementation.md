# Batch 1: Gold Data and Cost Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a bounded, private evidence report proving live gold data continuity and documenting exactly which broker costs are known.

**Architecture:** Extend the existing verifier and MT5 data boundary; keep the continuous observer and authenticated dashboard unchanged. A pure reducer evaluates samples from a finite collection run. Store private JSON evidence on the VPS and commit only sanitized summaries.

**Tech Stack:** Existing Windows Python 3.12.10, MetaTrader5 5.0.6180 under Wine; Python standard library and unittest. No new packages or monitoring service.

**Spec:** `docs/superpowers/plans/2026-09-28-gold-ai-researcher.md`, “Resume here — four delivery batches”. This plan refines Batch 1; it does not authorize orders.

## Global Constraints

- Instrument: `XAUUSD-VIP`; timeframe: completed M15 candles; demo only.
- Algo Trading remains off and no order path is deployed.
- Pinned account/server guard remains mandatory; account identifiers and credentials are excluded from published evidence.
- Quote age remains between 0 and 30 seconds inclusive; no guessed timestamp offset or weakened threshold.
- Use existing helpers; no Worker, UI, Docker network or dependency changes.
- Planning decisions below are proposed until owner review; no live run or restart is scheduled by this document.

## Review Focus

- Broker display-time offset differs from Python epoch semantics: preserve raw evidence, block any inferred conversion (Tasks 1, 4).
- Polls skip a boundary, clock jumps or old ticks repeat: require continuous sampled evidence, not three arbitrary screenshots (Task 2).
- History is malformed while quote is fresh: freshness must not imply valid candles or strategy readiness (Tasks 1, 2).
- Demo fee history is absent or all zero: do not infer a commission-free contract (Task 3).
- Collector/restart touches the running observer's SQLite state: collector is read-only; restart evidence is separately controlled (Task 4).

## Design choice and file map

Alternatives: manual snapshots are simplest but weak evidence; extending the bounded verifier is recommended and fits current code; a permanent monitoring service adds lifecycle/security work with no current need. Use the verifier unless owner selects otherwise.

Modify `ops/trading/mt5_data.py` (allowlisted diagnostics), `verify-demo.py` (optional collection CLI), `test_verify_demo.py` (existing boundary tests), and `README.md` (operator steps). Create `ops/trading/gold_qualification.py` (pure reducer) and `test_gold_qualification.py`. No package scaffold. Existing Dockerfile already copies verifier and data helper; add only `gold_qualification.py` to that COPY when deploying.

Private evidence schema v1: `symbol`, `mode=read-only-qualification`, `started_at`, `ended_at`, `sdk_version`, `code_sha256`, `samples`, `contract`, `data_status`, `cost_status`, `blockers`, `spread_summary`. Never serialize entire account, terminal, symbol or deal objects.

## Task 1: Capture independently useful evidence

**Files:** Modify `ops/trading/mt5_data.py:read_gold`, `ops/trading/verify-demo.py:main`, `ops/trading/test_verify_demo.py`.

**Interfaces:** Preserve `read_gold(mt5, login: int, now: float | None, evidence: dict | None = None)`. Add allowlisted evidence keys `bid`, `ask`, `spread_price`, `point`, `spread_points`, `history_valid`, `expected_bar_time`, `strategy_signal`, `strategy_reason`. Preserve all old keys and callers. Do not change the public status API allowlist.

- [ ] Add `test_fresh_quote_invalid_history_is_not_ready`: fresh valid tick plus duplicate/malformed OHLC must yield `history_valid=False`; quote remains `fresh`; strategy cannot be ready. Add `test_spread_units`: bid 100, ask 100.2, point .01 gives spread_price approximately .2 and spread_points approximately 20. Test NaN, missing/zero point and missing tick as unknown/blocked, never fabricated zeros.
- [ ] Run `python -B -m unittest discover -s ops/trading -p 'test_verify_demo.py'`; new assertions must fail before implementation.
- [ ] Reuse `evaluate` for the 250-bar validation and strategy result. Distinguish its history block from its ATR/spread block: the latter leaves history valid. Preserve stale/future diagnostic evidence even when `read_gold` raises. Validate account before and after each SDK sample; halt on changed identity. Never include trade/account objects in diagnostic exceptions.
- [ ] Re-run focused checks and `python -B -m unittest discover -s ops/trading -p 'test_*.py'`; existing callers must pass. Test mock `order_send` raises if ever invoked.
- [ ] Commit only these files: `git commit -m "Add bounded gold qualification evidence fields"`.

## Task 2: Bounded collection and two-transition proof

**Files:** Create `ops/trading/gold_qualification.py`, `ops/trading/test_gold_qualification.py`; modify verifier and Dockerfile COPY.

**Interfaces:** `qualify_samples(samples: list[dict]) -> dict` returns `data_status` (`passed|inconclusive`), `blockers`, `transition_bar_times`, `accepted_sample_count`, and `spread_summary`. Extend verifier CLI with `--collect-seconds 3600 --output PATH`; omit both to retain existing one-shot behavior. Permit collection durations 60–3600 seconds; fixed 5-second polling; no default daemon or scheduled job.

- [ ] Add `test_two_transitions_need_continuity`: fixture uses 5-second host timestamps, advancing ticks aged 1 second, valid 250-bar histories and bar_times 90000→90900→91800 at their proper UTC completion boundaries. Require >=1,800 elapsed seconds, >=361 accepted samples, at least two consecutive +900 transitions and >=3 distinct valid completed bars. Three isolated samples must be inconclusive.
- [ ] Add cases: age -0.001 or 30.001, host sample interval >10 seconds, backward host time, tick rollback, history regression or skipped +1800 bar reset the contiguous qualifying segment. Repeated ticks are allowed only while age <=30; every accepted segment must contain advancing tick timestamps. Account guard failure halts, not retries. Wide spread affects strategy eligibility, not basic data continuity.
- [ ] Run focused tests; confirm failure. Implement the pure reducer with strict types/finite values; track the most recent uninterrupted segment. Require each accepted latest bar equal `floor(sampled_at/900)*900-900`; no forming-bar input. Stop collection early only when the segment passes; otherwise hard-stop at monotonic deadline and save an inconclusive result.
- [ ] Implement collector using a monotonic deadline, 5-second sampling and the existing SDK initialization/shutdown lifecycle. Output path must be a new file under persistent MT5 home; exclusive creation, JSON `allow_nan=False`, bounded <=721 samples. On Ctrl+C save partial evidence as inconclusive. Do not open observer state or write the live snapshot. CLI exit 0=data passed, 2=inconclusive, 1=guard/runtime failure; costs remain independently unknown.
- [ ] Test output collision, outside-home path, interruption, serialization redaction and shutdown on failure. Verify p50/p95/max spread via sorted finite sampled spreads (nearest-rank percentiles); include units, timestamps, count, sample interval and eligible sample count. Label this sampled spread, not tick-complete market distribution.
- [ ] Run full Python suite; commit `git commit -m "Collect finite gold freshness and M15 transition evidence"`.

## Task 3: Establish cost evidence without trading

**Files:** Modify verifier and `test_verify_demo.py`; document private cost evidence in `ops/trading/README.md`. No broker-account export or automatic deal-history ingestion required.

**Interfaces:** `read_contract(mt5) -> dict` in `mt5_data.py` allowlists symbol name, `chart_mode`, `digits`, `point`, tick size/value, contract size, profit/margin currency, volume min/max/step, calculation mode, swap mode/long/short/rollover3days. Missing properties remain null. Private `cost-evidence.json` schema is consumed by Batch 2.

- [ ] Add `test_contract_allowlist_and_unknown_cost`: arbitrary extra secret fields do not appear; absent commission stays null; raw swap units stay attached to `swap_mode`; zero is not used as a missing-value sentinel. Run failing test, implement allowlist, rerun.
- [ ] Record current terminal specification with capture time and source. Inspect the exact demo symbol's Specification and account-specific broker fee schedule. Log source URL/document hash, effective dates, account category (redacted), commission currency/basis/per-side-or-round-trip, minimum fees, swap mode/direction/rates, rollover timezone and weekday multipliers. Do not use another entity/account's advertised fees as proof.
- [ ] Save private schema: `schema_version=1`, `symbol`, `captured_at`, `commission={status,value,currency,basis,minimum,source,effective_from,effective_to}`, `swap={status,mode,long,short,units,rollover_timezone,rollover_local_time,weekday_multipliers,source,effective_from,effective_to}`, `contract`, `slippage={status:"assumed",price_per_side:[0.05,0.10,0.30]}`, `blockers`. Status is `verified_current|verified_historical|unknown`; historical requires coverage of evaluated dates. Unsupported schedule shapes are unknown for simulation rather than approximated silently.
- [ ] If source unavailable, record unknown and ask owner for the account-specific schedule. No support message is sent and no fee-generating trade is placed. Existing demo statements may corroborate with owner's access, but zero/absent charges alone are not proof of general rules. Preserve documents privately.
- [ ] Commit sanitized collection instructions and tests, never the private evidence file. Completion can be partial: `data_status=passed` while `cost_status=incomplete`.

## Task 4: Operational qualification and handoff

**Files:** Update `README.md`, `CLAUDE.md`; sanitized Batch 1 result under `docs/superpowers/plans/2026-09-28-gold-batch-1-results.md` during execution.

- [ ] Before deployment record Git state, SDK/runtime versions and `timedatectl show -p NTPSynchronized -p Timezone` on VPS. Re-run one-shot verifier. Stop if identity differs or Algo Trading is on; do not toggle it automatically.
- [ ] Commit/push tested files, fetch exact commit on VPS and verify SHA-256. Back up current scripts. Copy only the verifier/helper files into running container for initial collection; do not recreate MT5 just to install a diagnostic. Also update host sources/Dockerfile for future persistence; record whether image rebuild remains pending.
- [ ] Start finite collection from a VPS SSH session during the exact symbol's confirmed open session:
  `docker exec kwg-mt5-desktop wine /opt/python/python.exe /opt/trading/verify-demo.py --login 1344907 --collect-seconds 3600 --output 'C:\users\mt5\gold-qualification-YYYYMMDD-HHMM.json'`
  This command is a future interface, not runnable until Task 2 is deployed. MacBook only provides SSH; it does not run Wine locally.
- [ ] Verify two-transition evidence and UTC interpretation from raw tick/bar epochs plus host clock and terminal display; broker GMT+2/+3 display alone is not a conversion rule. If inconsistent, preserve failure and investigate before changing shared freshness logic.
- [ ] After a successful collection, copy observer SQLite with its SQLite backup API (never copy a live DB file blindly) and record row counts/max bar. Supervise one desktop-container restart retaining existing volumes, then verify pinned demo, renewed heartbeat and unchanged historical rows with no duplicate bar primary keys. Startup suppression is expected. Record downtime and return to current observation. Restart qualifies recovery only, not uninterrupted market continuity; do not merge pre/post restart samples.
- [ ] Subscription recovery: test SDK `symbol_select` failure→success with mocks; confirm subscription and reconnect after the supervised restart. Do not remove a symbol from a running observer's Market Watch merely for a test. Label real network-disconnect recovery untested if not exercised.
- [ ] Copy private reports into `/opt/kwg-gold-research/qualification/` with directory700/file600; compare hashes. Save sanitized report with data/cost/recovery outcomes and timestamp scope. A passed window is historical evidence, not a permanent health badge. Run Python suite and existing Worker/status checks if shared fields changed; no UI redesign.
- [ ] Commit sanitized handoff; leave orders disabled. Batch 2 may consume verified evidence or continue as explicitly hypothetical if costs remain incomplete; Batch 3 stays blocked on required evidence.

## Documentation checked on 2026-09-28

Context7 `/lucas-campagna/mt5linux` confirms SDK data structures; it is a secondary wrapper reference, not a dependency to install. Primary verification:
- https://www.mql5.com/en/docs/python_metatrader5/mt5symbolinfo_py — symbol metadata including swap fields.
- https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesfrompos_py — index zero is current; retain start_pos=1.
- https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesrange_py — documented UTC epoch handling.
- https://get.vtmarkets.help/hc/en-us/articles/37317868198297-What-is-VT-Markets-GMT-offset-or-server-time — broker display timezone varies; not historical fee evidence.

Self-review: all five review risks assigned tests/actions; no order API, timezone correction, new service or cost invention. Data collection can finish inconclusive; no promise that an hour guarantees qualification.

## Runnable assertion examples for Task 2

Use a test helper `contiguous_samples()` producing the 361-sample, 1,800-second
fixture specified in Task 2. Keep it in the test file, not runtime code.

```python
def test_two_transitions_need_continuity(self):
    samples = contiguous_samples()
    self.assertEqual(qualify_samples(samples)['data_status'], 'passed')
    self.assertEqual(qualify_samples([samples[0], samples[180], samples[-1]])['data_status'], 'inconclusive')
    samples[-1]['quote_age_seconds'] = 30.001
    self.assertEqual(qualify_samples(samples)['data_status'], 'inconclusive')
```

A later failed sample invalidates the current qualifying segment even if an
earlier segment once passed. Finished reports explicitly identify their ending
sample; future health must not be inferred from an old passed file.
