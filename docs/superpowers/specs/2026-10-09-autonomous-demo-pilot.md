# Autonomous MT5 demo product pilot

Date: 2026-10-09 (Asia/Bangkok)
Status: implemented and tested; VPS deployed in standby; public portfolio UI deployment pending.

## Outcome

Within the owner's one-week budget, demonstrate automatic demo entries, protected
positions, broker-confirmed exits and a useful trading dashboard. Report the
result as an unqualified demo pilot. The existing prospective qualification
policy is not a prerequisite for this separately labelled product experiment
and is not weakened by it. No further hour-long baseline capture is required
before implementation.

The owner selected autonomous MT5 demo orders. Compared with live-price simulated
trades, this exercises broker behavior but requires a tested order lifecycle.
Compared with manually approved trades, it demonstrates autonomy but needs
persistent limits and restart handling.

## Smallest architecture

Reuse Python, Wine MT5, SQLite, the protected status/control service and the
existing trading page. Add no dependency, model agent or messaging platform.
A native MQL5 EA would require another implementation/deployment stack. An LLM
executor would introduce decision variability and additional permissions; neither
is needed for this fixed-strategy product trial.

One persistent pilot runner owns evaluation, execution and reconciliation. Do not
loop the manual arm CLI: it has operator-selected sides, arm expiry, fixed journal
paths and one-attempt semantics. Extract a shared helper only where required to
reuse existing validation without changing manual behavior.

The observer requires Algo Trading off. Desktop startup must select exactly one
signal publisher: existing read-only observation or the explicit pilot mode.
The pilot uses the execution-aware account/data checks. Do not remove the
observer's guard to make the new mode work. Manual controls must refuse new arms
while the pilot owns execution, including concurrent requests and restarts.

## Strategy and order rules

- Exact pinned demo account/server, USD account currency and XAUUSD-VIP. Read
  account identity before submission; any mismatch blocks trading.
- Completed M15 EMA20/EMA50 crossover plus the existing lookback-3 EMA20 slope
  filter. Use the existing signal/filter implementation and freeze its version.
- Market entries only for this pilot, with broker-supported filling and attached
  SL/TP. No new pending-order entry flow or same-bar reversal.
- Broker minimum lot, modeled stop exposure at most 0.1% of current equity,
  stop distance 2 ATR and target distance 3 ATR. Skip if minimum volume, price
  rounding, spread, filling or stop-distance checks cannot meet the contract.
- One open position; block new entries if any gold exposure or pending order is
  unknown or belongs to another flow. Do not alter unrelated exposure.
- Persist the last evaluated completed candle before any submission. Startup
  establishes a baseline; no catch-up entries for missed candles. Restarts cannot
  create another entry for an already evaluated candle.
- Journal intent before submission. A timeout/unknown result requires broker
  reconciliation using recorded identity and tickets. No blind resubmission.
- Partial fills and uncertain ownership pause new entries and remain visible.
  Confirm actual fill volume and broker-held SL/TP rather than treating a
  successful preflight check as an executed/protected order.

## Limits and lifecycle

Owner activation binds code/config identity, account, start time and an end time
no more than seven days later. Build/test time is included in the overall week;
the actual run uses the remaining budget. Do not start this timer during design.

Persist activation equity, UTC-day starting equity, peak pilot equity and pause
state. Daily loss of 1% from the recorded UTC-day start, or drawdown of 5% from
the recorded peak, blocks new entries. Include floating loss in equity checks.
Restart cannot reset limits. Unexplained deposits/withdrawals or missing required
history block new entries until reconciled; they cannot create extra allowance.

Owner pause stops entries and keeps reconciliation active. Risk/uncertainty stops
are latched for review. A new day does not clear an owner or attention stop.

At expiry, refuse entries and close only confirmed pilot-owned exposure. Persist
close intent and reconcile before retrying an ambiguous close. Closed sessions,
disconnections or rejected closes may prevent immediate flattening; keep broker
protection and expose the unresolved position. Never claim expired means flat
without broker evidence. The runner must continue managing unresolved exposure.

## Product and evidence

Extend /vault/trading using the current design system and shared contract:
pilot mode, strategy, heartbeat, entry/block reason, position and SL/TP, realized
and floating P&L, recent completed trades, time remaining and owner pause.
Account/login details and secrets stay private. Stale or unauthorized responses
must not leave apparently current prices or active controls on screen.

Use actual broker deals for profit, commission, swap and fees. The public zero
commission schedule and current swap snapshot are assumptions until matched to
actual evidence. Unknown values stay unknown. A slow week may have no natural
signals; show that honestly. Synthetic UI fixtures stay labelled and isolated.

## Change surface

- New pilot runner and fake-broker tests in ops/trading.
- Existing demo_one_shot.py validation/reconciliation helpers only where reuse is
  necessary, with its existing tests preserved; pilot gets separate journal and
  order identity and a shared execution exclusion mechanism.
- desktop.sh, Dockerfile and compose.yml for opt-in pilot startup.
- control_server.py, status_server.py and worker/src/index.js for owner-only
  activation/pause and a sanitized pilot status contract.
- src/scripts/trading-status.mjs, its tests, status-contract fixtures and
  src/pages/vault/trading.astro; regenerate the served trading.html using the
  existing build-status-page.mjs route rather than independently editing copies.
- Python status/control tests, Worker tests and vault-trading E2E scenarios.
- Deployment instructions, rollback and HANDOFF.md.

## Acceptance checks

1. Deterministic fake broker tests cover both signal directions, no-signal/filter
   rejection, wrong/real accounts, stale inputs, duplicate candle/restart,
   submission timeout, rejection/partial fill, missing protection, daily and
   drawdown stops, concurrent manual entry, pause and expiry with unresolved exit.
2. Protected control/status integration preserves research status-only access and
   credential redaction; no model can arm the pilot through research credentials.
3. Dashboard checks cover waiting, open, closed, paused, stale, attention and
   expiry states. Build and affected suites pass.
4. Deploy disabled; retain rollback image and consistent journal backup. Inspect
   the concrete preview and runtime account/config before owner activation.
5. Capture broker receipts and operational results during the remaining week.
   Product success means truthful state, bounded execution and correct recovery;
   profit is not an acceptance requirement or a guarantee.

## Documentation check

Context7 was invoked for MetaTrader5/Python documentation. Its official-book index
returned no matching content for the execution queries, so the primary Python
references were checked directly:

- https://www.mql5.com/en/docs/python_metatrader5/mt5ordercheck_py
- https://www.mql5.com/en/docs/python_metatrader5/mt5ordersend_py

A successful check/request is insufficient evidence of successful execution.
Record returned broker results and reconcile actual orders, positions and deals.
