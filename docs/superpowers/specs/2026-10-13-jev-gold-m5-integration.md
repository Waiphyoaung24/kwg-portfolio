# Jev decision layer for the Gold M5 demo pilot — design

Date: 2026-10-13 (Bangkok). Branch: `jev-integration`. Status: design accepted by
the owner; implementation plan in
`docs/superpowers/plans/2026-10-13-jev-gold-m5-integration.md`.

Reference vision: the owner's "Jev trading loop" carousel — market state → Jev
structured BUY/HOLD/SELL decision → code risk engine → execution → feedback loop.
This design keeps that loop but restricts Jev to the part it is documented to do
well (typed classification over supplied state) and leaves every number in code.

## Understanding summary

- **What:** Jev (TypeSafe System One, pinned `jev-1.13.0`) becomes a decision
  layer for **Gold only** (`XAUUSD-VIP`) on the pinned **demo** account, on a new
  **M5** pilot strategy.
- **Phase 1 — shadow:** the existing EMA20/EMA50 trend + three-bar slope + ATR
  code decides and trades every entry. For each candidate entry candle Jev returns
  BUY/HOLD/SELL with probabilities and confidence; the receipt is journalled next
  to the actual demo trade. Jev has zero effect on orders.
- **Phase 2 — veto:** Jev may block a code-signalled entry; it can never originate,
  size, place, modify or close a trade. Stop 2 ATR, target 3 ATR, 0.1% equity entry
  ceiling, 1% daily and 5% drawdown pauses and one position per symbol stay in code.
- **Gate to Phase 2:** ≥50 closed M5 code trades with timely receipts; the subset
  Jev would have kept has a higher average net realised demo P/L than all trades;
  missing/late/invalid receipts <20% of candidates; then explicit owner approval.
  Never automatic.
- **Feedback loop:** an M5 scorecard. Jev is not retrained or fine-tuned.
- **Why:** test the carousel's idea against real demo fills without trusting Jev
  with arithmetic. TypeSafe documents that Jev "cannot count, do math, or compare
  dates" reliably; those stay in code.
- **Non-goals:** live account; BTC; Jev originating trades; Jev changing risk
  rules, evaluator or its own promotion; automatic promotion; changes to the M15
  observer or M15 scorecard; the VPS ever holding the TypeSafe key.

## Assumptions (confirmed by owner 2026-10-13)

1. The TypeSafe key stays only in the Cloudflare Worker; its existing per-minute
   cron performs M5 calls.
2. Veto mode is fail-closed: missing, late, invalid, mismatched or low-confidence
   receipts skip the entry.
3. The runner waits at most 90 seconds after candle close for a receipt.
4. The existing $5 Jev ledger stays (shared with the M15 observer). Raising it
   requires owner approval.
5. The Gold runner switches from M1 to M5 at the start of Phase 1 via the existing
   staged, reviewed-hash cutover pattern, preserving position, receipts, latched
   pause and account limits. BTC is untouched.
6. ~20k input tokens per call is an estimate; actual usage is measured and shown.
   Calls happen only on candidate-entry candles, not every candle, so real spend
   is well below the 288-calls/day ceiling (~$0.24/day worst case).

## Decision log

| # | Decision | Alternatives | Why |
|---|---|---|---|
| 1 | Shadow first, then veto-only | Veto now; Jev decides; shadow forever | Zero evidence exists (M15 scorecard: 0 eligible setups); docs say Jev is unreliable on numbers; veto can only reduce trading. |
| 2 | M5 timeframe | M15 (reuse observer); M1 with bigger budget; both | Owner choice. M5 fits a ≤90 s receipt wait and the $5 budget; M1 does neither. |
| 3 | Veto gate = 50 closed trades + better kept-subset average + <20% bad receipts + owner OK | Owner-only; time-based | Minimum sample, explicit comparison and reliability check; promotion stays human. |
| 4 | Worker calls Jev (approach A) | Runner calls TypeSafe directly; VPS sidecar holds key | Key never on VPS; reuses ledger, receipts, budget reservation and snapshot allowlisting. Rejected B: key beside broker state plus duplicated ledger. Rejected C: second secret and ledger. |
| 5 | Receipt returns via existing private control path (Worker → status origin `/control/jev-receipt` → `desktop:8001`) | Runner polls Worker; status sidecar writes a file | No new credential or outbound route in MT5 container; status sidecar stays read-only. |
| 6 | Code supplies categorical features; Jev classifies | Raw numbers only | Follows TypeSafe guidance: computation in code, classification in Jev. Raw last bars are still included for context. |
| 7 | Jev is asked independently; the code's proposed side is **not** in the state | Include code side | Avoids anchoring Jev to agree; veto = Jev choice differs from code side or confidence below threshold. |
| 8 | Veto threshold frozen before shadow: veto if choice ≠ code side or confidence < 0.5 | Tune after shadow | Pre-registration; tuning on shadow data would overfit the gate. |
| 9 | Call Jev only on candidate-entry candles | Every candle | Jev never originates, so only candidates need a decision; saves budget. |
| 10 | Scorecard uses realised demo P/L from the runner journal | Modeled outcomes | The bot really trades in shadow; real demo fills are better evidence than a cost scenario. Still demo, still unqualified. |

## Design

### 1. Components and changes

- `gold_signal.py`: accept `bar_seconds=300`; trend-demo spread ceiling (25% ATR)
  allowed for Gold M5. M1/M15 behaviour unchanged.
- `demo_pilot.py`: new strategy `gold-ema-v1-m5-trend-jev` with pilot field
  `jev_mode: "shadow" | "veto"`. `candle_seconds` → 300, cooldown 300 s.
  Candidate entries write a feature payload (`jev-m5.json`) for the Worker. In
  veto mode the entry is deferred into a `pending_entry` record and executed on a
  later poll only when a valid allowing receipt for that exact `bar_time` and
  `input_sha256` exists, within 90 s of candle close, and the existing
  `before_submit` guard still passes (same bar, same side, slope, limits).
- `jev_m5.py` (new, pure): builds the feature state, its `input_sha256`, the
  frozen question, receipt validation, and the veto rule. Shared by runner,
  scorecard and tests.
- `control_server.py`: new `POST /jev-receipt` (secret-checked like existing
  actions, ≤1 KiB, schema-validated); appends to `jev-m5-receipts.sqlite3`
  (insert-only, one row per `bar_time`).
- `status_server.py`: allowlist `/control/jev-receipt` (1 KiB body) and
  `GET /jev-m5` (freshness ≤15 s, like `/jev-m15`).
- Worker: `src/jev-m5.js` (snapshot allowlist + validation), cron branch gated by
  `JEV_M5_LIVE=true`, per-candle Durable Object receipt key `m5:<bar_time>`,
  then forward the receipt to `/control/jev-receipt`.
- `jev_m5_scorecard.py` + `/api/trading/jev-m5-scorecard` + a panel on
  `/vault/trading` (desk theme per DESIGN.md trading exception).
- `promote-jev-veto.py`: owner-run; recomputes the gate read-only, refuses unless
  it passes, requires `--owner-approved`, flips `jev_mode` under the runner lock.

### 2. Data flow (one M5 candle)

1. Candle closes at T. Runner (≤5 s poll) evaluates code signal. In shadow mode a
   candidate trades immediately as today; in veto mode it becomes `pending_entry`.
   Either way the runner publishes `jev-m5.json` with `bar_time`, features,
   last 50 bars, bid/ask, `input_sha256`, `candidate: true`.
2. Worker cron (≤60 s) reads `/jev-m5`, validates, reserves budget, calls
   TypeSafe (15 s timeout), stores the receipt under `m5:T`.
3. Worker POSTs `{bar_time, input_sha256, model, question_sha256, choice,
   probabilities, confidence, status, completed_at}` to `/control/jev-receipt`.
4. Runner reads the receipt. Shadow: journal only. Veto: allow → submit through the
   existing guard; veto/invalid/late (> T+90 s) → skip with a recorded reason.

### 3. Jev question (frozen; hashed into receipts)

State: categorical features computed in code — `trend` (up/down/flat),
`slope_3` (rising/falling/mixed), `price_vs_ema20` (above/below/at), volatility
regime (low/normal/high vs 50-bar ATR median), spread bucket (tight/normal/wide
vs ATR), session (asia/london/new_york/overlap), last-5-candle body pattern — plus
the last 50 OHLC bars. No account, P/L, position, code side or credentials.

Question `decision` (choice): `buy` — conditions favour a long entry now;
`hold` — no clear edge or conflicting evidence; `sell` — conditions favour a
short entry now. Instructions forbid inferring missing data and state that code
owns all risk and execution.

### 4. Error handling

- Feed stale/invalid → Worker sends nothing; runner (veto) skips at T+90 s.
- Provider timeout/error/budget exhausted → receipt with that status; veto skips;
  no automatic retry (existing reservation semantics keep spend capped).
- Receipt for wrong `bar_time`/hash/model/question → rejected, logged, counted as
  bad receipt.
- Duplicate receipt → insert-only; first wins.
- Runner restart with `pending_entry` → expires if past T+90 s; never replayed.
- Control path down → same as missing receipt.

### 5. Testing

- Python unit: M5 evaluate; feature builder determinism and hash; veto rule table;
  receipt validation; pending-entry deadline and restart; shadow never blocks;
  veto never originates; cutover preserves state; promotion refuses failing gate.
- Worker: M5 snapshot validation; cron gating; budget reservation; receipt forward
  with control secret; no key in forwarded payload.
- Frontend: scorecard state rendering with synthetic data; Playwright fixture
  checks desktop/mobile.
- VPS acceptance (owner): staged cutover, first live receipts, shadow journal.

## Risks acknowledged

- Jev may simply have no edge on Gold M5; the gate is designed to show that, not
  to hide it. 50 trades is a minimum review sample, not proof of edge.
- Cron latency (≤75 s) can make veto-mode entries later than shadow entries; the
  scorecard reports entry delay so the comparison is not silently biased.
- Shared $5 ledger can be exhausted; budget state is visible and veto fails closed.
- Demo fills differ from live; nothing here qualifies live trading.
