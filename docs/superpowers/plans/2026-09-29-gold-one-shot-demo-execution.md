# Gold One-Shot Demo Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove one supervised `XAUUSD-VIP` demo order can be opened with broker-held protection, reconciled, automatically closed and durably disarmed.

**Architecture:** Keep the current signal observer read-only. A separate Wine/Python runner owns one operator-armed smoke-test intent in a private SQLite journal, uses the existing MT5 data checks, and publishes only a sanitized execution state through the existing status path. A missing or ambiguous broker response freezes new orders until reconciliation.

**Tech Stack:** Existing MetaTrader5 5.0.6180 under Wine, Python 3.12 standard library/SQLite/unittest, Docker Compose, existing Cloudflare Worker and Astro status page. No model or new paid dependency.

**Spec:** `docs/superpowers/plans/2026-09-29-gold-agent-design.md`; existing `docs/superpowers/plans/2026-09-28-gold-ai-researcher.md` for pinned demo, symbol and baseline risk limits.

## Global Constraints

- Pinned `VTMarkets-Demo` login and `XAUUSD-VIP` only; `account.trade_mode == 0`. Never accept a live account.
- One explicitly armed attempt, operator-specified `buy` or `sell`, minimum broker lot only. The arm expires after 900 seconds; no new entry after a process/container restart. The runner reads pinned login and current verified offset from the private Compose environment.
- Planned stop-distance exposure at minimum lot must be at most 0.1% of current equity. Use the current broker `order_calc_profit`; unknown fees, gaps and slippage mean this is not a guaranteed total-loss cap.
- Stop = 2 × current ATR14 and target = 3 × ATR14, rounded adversely to the broker tick and checked against stop-distance rules. Entry request includes both server-held SL and TP.
- Quote age 0–30 seconds using the explicitly verified current server offset; 250 completed valid M15 bars and existing 10%-of-ATR spread gate. A past offset is not automatically valid after a DST change.
- No existing gold position or active gold order before entry; no pyramiding, strategy signal, model call, browser arm endpoint, auto-promotion or continuous entry loop. The future continuous runner still needs its separate persisted 1% UTC daily entry pause.
- Successful entry confirmation starts a 60-second hold. Close early if broker SL/TP has already closed it; otherwise send one ticket-specific close request, reconcile and disarm. A close failure/unknown response leaves a protected position in `needs_attention`, never a fabricated closed state.
- The read-only observer keeps its existing Algo-Trading-off guard. The operator may enable Algo Trading only for the supervised test and must turn it off after broker reconciliation. The runner's own arm and one-attempt journal enforce its execution limit even if the terminal toggle remains on.
- All private journal rows, account details, broker tickets and full trade reports remain in the persistent MT5 home, outside Git and the web API. The page remains Cloudflare Access protected and read-only.
- This test does not unblock Batch 2/3 strategy qualification. Do not run it merely because software tests pass: activation is a separate reviewed step.

## Review Focus

1. Wrong account, server, live mode, disabled trading, changed symbol or stale/future tick must block before `order_send` (Task 1 tests).
2. Broker minimum lot above the planned risk ceiling, unsupported fill mode, stop distance or occupied gold symbol must block before `order_send` (Task 1 tests).
3. A timeout/lost entry reply must be reconciled through positions, orders and deals without a second entry (Task 2 tests).
4. Restart after a submitted entry must never create another entry; an existing protected position must still reach the close/recovery path (Task 2 tests).
5. A successful `order_check` or `order_send` alone must not mark a protected open/closed trade; position/deal evidence and sanitized status must agree (Tasks 2–3 tests). MetaQuotes documents that an order check is not execution confirmation.

## File map

| File | Responsibility |
| --- | --- |
| `ops/trading/mt5_data.py`, `test_verify_demo.py` | Share pinned demo/market checks while preserving the observer's off guard |
| `ops/trading/demo_one_shot.py`, `test_demo_one_shot.py` | One-shot preflight, order lifecycle and persistent journal |
| `ops/trading/Dockerfile`, `desktop.sh` | Ship a resume-only boot hook; no background entry loop |
| `ops/trading/status_server.py`, `test_status_server.py` | Allowlist a separate execution snapshot |
| `ops/trading/worker/src/index.js`, `worker/test.mjs` | Pass through only sanitized execution fields under Access |
| `src/pages/vault/trading.astro`, `src/scripts/trading-status.mjs`, `src/scripts/trading-status.test.mjs`, generated `ops/trading/trading.html` | Read-only execution state on the existing authenticated page |
| `ops/trading/README.md`, `HANDOFF.md` | Operator runbook, evidence and rollback state |

## Task 1: Preflight and protected entry request

**Files:** Modify `ops/trading/mt5_data.py`, `test_verify_demo.py`; create `ops/trading/demo_one_shot.py`, `test_demo_one_shot.py`.

**Interfaces:** Extend `validate_account(account, terminal, login, server=SERVER, *, execution=False)` and `read_gold(mt5, login, now, evidence=None, *, server_offset_seconds=0, execution=False)`. The default retains current observer behavior. Add `build_entry_request(mt5, login: int, side: str, now: float, server_offset_seconds: int, *, execution: bool) -> dict` in `demo_one_shot.py`; it returns a locally checked request, never sends it. `execution=False` previews under the observer guard; `execution=True` requires trading enabled and is rechecked before `order_check`.

- [ ] **Step 1: Write failing tests.** Default `read_gold` still rejects Algo Trading on; execution mode rejects off, wrong demo identity, `account.trade_allowed=False`, `account.trade_expert=False`, `terminal.tradeapi_disabled=True`, stale/future ticks and invalid bars. A valid current session reaches preflight.
- [ ] **Step 2: Write failing request tests.** Fake MT5 reports an existing gold position/order, unsupported `filling_mode`, excessive minimum-lot stop exposure, invalid stop/freeze level or `order_calc_profit=None`; each raises before any `order_send`. Valid fake yields exactly `TRADE_ACTION_DEAL`, the chosen side, `volume_min`, broker-supported filling, dedicated magic and unique short comment, and nonzero SL/TP on the correct sides of bid/ask. Preview mode has Algo Trading off and calls no `order_send`.
- [ ] **Step 3: Run** `python -B -m unittest ops/trading/test_verify_demo.py ops/trading/test_demo_one_shot.py`; expect the new cases to fail.
- [ ] **Step 4: Implement the two interfaces.** Reuse `read_gold` and `gold_signal.evaluate` for ATR/spread/history, ignore its directional signal. Recheck demo identity immediately before building the request. Use the current symbol's tick size, volume step, stop/freeze distances and allowed execution/filling modes; `order_calc_profit` estimates minimum-lot stop exposure. Reject missing metadata and unsupported cases rather than guessing. The operator supplies side; no default side.
- [ ] **Step 5: Run the focused tests and** `python -B -m unittest discover -s ops/trading -p test_*.py`; expect all pass. Commit only Task 1 files.

## Task 2: One durable attempt and reconciliation

**Files:** Modify `ops/trading/demo_one_shot.py`, `test_demo_one_shot.py`; later ship through `Dockerfile` and `desktop.sh`.

**Interfaces:** `open_journal(path: Path, login: int) -> sqlite3.Connection` pins account/server/symbol and stores one attempt. `arm_once(db, side: str, now: int) -> str` records a unique arm ID and `expires_at=now+900`; it refuses any unfinished attempt. `process_once(mt5, db, now: float) -> dict` advances one state without accepting a second entry. CLI has `preview --side buy|sell --state PATH`, `arm --side buy|sell --state PATH --enable-demo-execution` and `resume --state PATH`. `arm` journals and runs its one attempt in the same supervised process; `resume` never enters and only reconciles a submitted attempt.

- [ ] **Step 1: Write failing journal tests.** Arm is exclusive; preview makes no journal entry; expired arm makes zero sends; reopening the SQLite file preserves account binding, attempt count and state; read-only observer journal is untouched.
- [ ] **Step 2: Write failing broker tests using a fake MT5 boundary.** `order_check` rejection makes zero sends. Before `order_send`, commit `submitting`; a timeout/None reply or process crash then uses `positions_get`, `orders_get` and `history_deals_get` to reconcile. Unknown state never resends. A successful return still needs matching position ticket, symbol, actual filled volume, magic and SL/TP. Partial fills are reconciled; a missing stop/target or stop exposure above 0.1% at the actual fill triggers ticket-specific emergency close or `needs_attention`.
- [ ] **Step 3: Write failing close/restart tests.** Confirmed position closes after 60 seconds or is recognized as broker-closed earlier. A close request names the confirmed position ticket and reverse side; lost close reply reconciles deals/position before any retry. Restart of an armed-but-unsubmitted attempt disarms; restart of a submitted attempt reconciles without another entry. No ambiguous result is labeled closed.
- [ ] **Step 4: Run** `python -B ops/trading/test_demo_one_shot.py`; expect the new cases to fail.
- [ ] **Step 5: Implement the state machine and CLI.** Keep the journal in persistent MT5 home with owner-only permissions. Store UTC timestamps, exact request/result codes and broker identifiers privately. A definite rejection disarms; an unresolved response freezes new orders. Use one process/lock for the journal; no retry loop that can issue duplicate entries. On normal closure record realized deal evidence and disarm.
- [ ] **Step 6: Run focused and full Python tests; repeat deterministic fake execution after reopening the journal.** Commit Task 2 files.

## Task 3: Safe boot behavior and visible read-only result

**Files:** Modify `ops/trading/Dockerfile`, `desktop.sh`, `status_server.py`, `test_status_server.py`, `worker/src/index.js`, `worker/test.mjs`, `src/pages/vault/trading.astro`, `src/scripts/trading-status.mjs`, `src/scripts/trading-status.test.mjs`; regenerate `ops/trading/trading.html`.

**Interfaces:** The runner atomically writes `Z:\opt\status\execution.json` with `{mode:"one-shot-demo",status,updated_at,side,volume,opened_at,closed_at,close_reason,realized_net_usd}`; `status` is `disarmed|armed|submitting|open|closing|closed|needs_attention`; no login, ticket, order/deal IDs or request body. `status_server.read_status` adds optional `execution`; Worker `normalizeStatus` validates and preserves only this allowlist. An expired nonterminal execution heartbeat renders `Unknown`; a reconciled `closed` result remains visible as timestamped history.

- [ ] **Step 1: Write failing status tests.** Private identifiers and extra fields never reach the HTTP JSON; stale open/closing or malformed execution snapshot becomes `Unknown`, while a reconciled closed result stays labeled with its historical close time. Worker rejects invalid execution states and preserves the existing observer schema when execution is absent. Browser tests distinguish disarmed, open, closed and needs-attention without a control button.
- [ ] **Step 2: Run** `python -B ops/trading/test_status_server.py`, `node --test ops/trading/worker/test.mjs src/scripts/trading-status.test.mjs`; expect new cases to fail.
- [ ] **Step 3: Implement allowlists and boot resume.** Dockerfile copies the runner. `desktop.sh` invokes `resume` after terminal startup; it exits immediately without an active journal and never enters. The observer keeps its own read-only guard. Add a small execution section to the existing page, following `DESIGN.md`, `PRODUCT.md`, site tokens and primitives. Browser remains observation-only.
- [ ] **Step 4: Run focused tests, full Python suite, `node --test` for the named JS tests, `yarn build`, and `node ops/trading/build-status-page.mjs`.** Confirm generated HTML contains the sanitized section. Commit Task 3 files.

## Task 4: Dry run, supervised demo attempt and handoff

**Files:** Modify `ops/trading/README.md`, `HANDOFF.md`; save private VPS evidence outside Git.

**Interfaces:** Dry-run uses the same preflight/request builder but never calls `order_send`. The supervised attempt uses the existing private MT5 desktop and persistent volume; no public port or new MCP tool.

- [ ] **Step 1: Test deployment without arming.** Build the image, verify source hashes, preserve a consistent backup of the observer journal, exercise the resume-only boot hook with no arm and confirm zero orders after restart. Recheck the pinned demo, terminal build/SDK, current UTC/Market Watch offset, fresh M15 feed, symbol trading conditions, empty gold positions/orders and dashboard access. If any check fails, leave Algo Trading off.
- [ ] **Step 2: Run `preview` with Algo Trading off.** Show the operator side, current minimum lot, quote reference, proposed SL/TP, modeled stop exposure and 60-second close rule. Record that the preview is time-limited and has not passed `order_check`; preserve a private report hash. No journal arm or order send occurs.
- [ ] **Step 3: After owner review of that concrete dry-run, supervise one armed demo attempt.** Operator enables Algo Trading in the private MT5 desktop, arms via the private VPS CLI, and watches the journal/terminal. `arm` rechecks current data and calls `order_check` before the single send. Require exactly one entry attempt, a matching protected position, a confirmed close or protective exit, no remaining gold position/order, durable disarm, and a sanitized result in `/vault/trading`. On an unresolved state, keep the journal and broker protection intact, freeze new orders and perform ticket-specific recovery; do not claim completion.
- [ ] **Step 4: Turn Algo Trading off and verify the read-only observer resumes.** Record sanitized timestamps, code/image hashes, request/result categories, stop/target presence, entry/close/deal reconciliation, restart-simulation results, dashboard state and any manual recovery. Keep actual tickets, login and full deal data private. Commit/push only code and sanitized handoff; continuous execution remains disabled.

## Source checks and self-review

MetaQuotes' Python references distinguish [`order_check`](https://www.mql5.com/en/docs/python_metatrader5/mt5ordercheck_py), [`order_send`](https://www.mql5.com/en/docs/python_metatrader5/mt5ordersend_py), [`positions_get`](https://www.mql5.com/en/docs/python_metatrader5/mt5positionsget_py), and [`history_deals_get`](https://www.mql5.com/en/docs/python_metatrader5/mt5historydealsget_py); checking or sending is not sufficient proof of a protected position or closed deal. The current [`symbol_info`](https://www.mql5.com/en/docs/python_metatrader5/mt5symbolinfo_py) exposes stop/freeze, filling and volume properties; [`order_calc_profit`](https://www.mql5.com/en/docs/python_metatrader5/mt5ordercalcprofit_py) estimates stop exposure in account currency. These API capabilities do not prove this broker accepts a given request.

Spec coverage: one-shot arm, protected open, close, stop/disarm, restart and uncertain replies are Tasks 1–4; page visibility is Task 3. Batch 2/3/4 and continuous strategy execution remain separate plans in `docs/superpowers/plans/2026-09-29-gold-agent-design.md`. No task grants AI an order path or treats this smoke trade as acceptance of the losing baseline.
