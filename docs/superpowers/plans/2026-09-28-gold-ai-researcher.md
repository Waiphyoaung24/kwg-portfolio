# Gold AI researcher and MT5 runner — selected 2026-09-28

This section is the current direction for trading. Earlier discovery notes above
are historical; they do not expand the gold-only scope or enable orders.

## Selected architecture

Owner selected: keep the existing MT5 runner and add Vibe-Trading as a separate
researcher. TradingAgents is a possible later comparison, not a dependency of
the first version. Reuse the existing observer, SQLite journal, status sidecar,
Cloudflare Tunnel, Access, Worker and `/vault/trading` page.

- Instrument: `XAUUSD-VIP`; timeframe: completed M15 candles; demo only.
- Execution host remains the existing Ubuntu VPS with Windows MT5/Python under
  Wine. Native Linux Python runs research separately. Cloudflare serves the
  authenticated status API and UI; it does not run MT5 or research jobs.
- The researcher consumes exported market data and sanitized strategy outcomes.
  It has no MT5 credentials, broker volume, Docker socket, order tools, or write
  access to the running strategy, risk configuration, or evaluator.
- Generated research code runs in a separate constrained job with no broker
  credentials or network access. LLM calls belong to the research controller,
  not generated code. Do not treat a language-level sandbox as isolation.
- Use the existing EMA20/EMA50/ATR14 signal as a fixed comparison baseline.
  Start with bounded parameter/filter proposals, one candidate at a time.
- Pin the Vibe-Trading version after testing data import and artifact output.
  Its installed 0.1.15 runner/SL-TP limitations remain unresolved; research
  adoption does not authorize replacing the execution path or switching profiles.

## Improvement process

Collect evidence -> propose a change -> evaluate -> observe on new data ->
review promotion -> retain the prior version for rollback.

Persist each experiment's hypothesis, candidate/version hash, baseline version,
data snapshot/hash, time windows, evaluator version, model/prompt version,
cost assumptions, API cost, results and rejection/promotion reason. Record
failed experiments as well as successful ones. A reflection is a hypothesis,
not proof of improvement. Missing evidence is inconclusive.

The researcher cannot change risk limits, evaluation criteria, held-out data,
account identity, or its own promotion permissions. Initial promotions require
owner review. Automatic promotion is a later design decision, not part of v1.
No fine-tuning, multiple research frameworks, or automatic repository upgrades
are required for the first version.

## Delivery sequence and acceptance checks

1. **Qualify the current data and reporting.** Inspect raw gold tick time,
   receive time and age during an open session; establish timestamp semantics
   without guessed timezone corrections. Verify two consecutive completed M15
   transitions, subscription recovery, and restart/duplicate handling. Split
   UI evidence into status delivery, observer heartbeat, MT5 connection at last
   check, and quote readiness. Derive each from explicit checks, not reason text.
   Verify stale heartbeat and unavailable origin never appear healthy; separate
   old quotes from future timestamps. Closed-market blocking is not a failure
   of the Worker, but does not satisfy fresh-data qualification.

2. **Create reproducible data and baseline evaluation.** Export broker-specific
   candles, available bid/ask data, symbol specification and provenance without
   account credentials. Specify baseline entry/exit and fill rules once and
   reuse the signal calculation. Enter only after a completed signal candle;
   include spread, commissions, slippage, applicable overnight costs and lot
   constraints. Declare conservative treatment when stop and target fall in
   the same bar; OHLC alone cannot establish their order. Verify with a small
   known-outcome fixture and deterministic rerun. Missing costs or insufficient
   history block qualification rather than silently assuming zero.

3. **Define evaluation gates before research.** Freeze chronological development,
   validation and final holdout windows with overlap controls for holding
   periods. Run rolling out-of-sample comparisons and execution-cost stress
   tests. Measure net expectancy/return, drawdown, turnover, sample size and
   uncertainty. Count all candidate trials. Predeclare minimum evidence and
   acceptable regression thresholds before inspecting candidate results. Do
   not repeatedly select on the final holdout or use current news in past runs.

4. **Connect one Vibe-Trading research job.** Verify the pinned version can use
   the exported gold data; otherwise use it only to propose a bounded strategy
   specification for our evaluator. Do not substitute Yahoo/futures prices for
   the broker CFD silently. Owner intends to use their existing Claude/Worker
   MCP connection; no separate paid LLM provider is requested. First establish
   its supported invocation path and authentication locally: an MCP token alone
   does not establish a model inference API or unattended-job compatibility.
   Prefer the supported existing Claude-to-research-tools path if Vibe-Trading
   cannot use that connection directly. Keep tokens out of chat, Git and logs.
   Start with manually triggered jobs, per-run call/token/time limits and one
   active job. Validate a proposal, invalid-proposal rejection, timeout and
   quota exhaustion without altering the baseline. Do not add paid market data
   or a new provider subscription without an explicit owner decision.

5. **Observe a candidate on fresh data.** Run baseline and candidate against the
   same feed without orders. Persist both decisions and modeled outcomes using
   the same fill assumptions. Dashboard shows active baseline, candidate,
   observation mode, evidence period, measured results and review state; retain
   the existing restriction on account identifiers and balances. A modeled
   outcome must be labeled simulated. Passing tests does not itself promote it.

6. **Implement and qualify demo execution separately.** Preserve the proposed
   baseline limits: 0.1% current-equity entry risk, 2 ATR stop, 3 ATR target,
   one strategy-owned gold position, no pyramiding/martingale, opposite-cross
   close by ticket without same-candle reversal, and pause new entries at 1%
   loss from persisted UTC day-start equity. This is not a guaranteed loss cap.
   Require broker-held protection, volume-step sizing, fresh quotes, valid
   spread, pinned demo identity, persistent pause and reconciliation of uncertain
   submissions. Test restart, duplicate intent, rejected protection, lost reply
   and account mismatch before reviewing activation with the owner. Until then
   Algo Trading remains off and no order path is deployed.

## Current acceptance status and next action

- Selected architecture: complete; implementation of research/evaluation: pending.
- Existing status delivery and demo observer reporting: previously verified.
- Fresh gold ticks and completed live M15 transitions: still unqualified.
- Owner supplied inference preference: existing Claude/Worker MCP connection;
  integration method and unattended-job compatibility remain unverified.
- Next implementation milestone: step 1, explicit health evidence and data
  qualification, followed by step 2's reproducible baseline evaluator.
- This plan does not schedule monitoring, deploy services, or enable orders.

Documentation consulted on 2026-09-28 through Context7 and upstream sources:
- https://github.com/HKUDS/Vibe-Trading (MT5 profiles and research capabilities)
- https://github.com/TauricResearch/TradingAgents (memory and reproducibility)
Upstream capabilities must be checked against the pinned installed version.

## Milestone 1 refinement — 2026-09-28

Live browser inspection at 2026-09-27 18:22 UTC returned a current observer
report with the quote-age failure. Delivery is verified at that check; gold
freshness is not. This is evidence of the running path, not a completed
open-market qualification.

Alternatives: terminal diagnostics alone are fastest but do not satisfy the
requested page visibility; explicit health fields on the existing page fit the
selected scope; a full infrastructure monitoring stack adds maintenance without
being necessary for this milestone. Continue with explicit in-page health.

Code findings:
- `verify-demo.py` emits timestamp evidence only after `read_gold` succeeds;
  a stale/future tick currently loses its numeric diagnostic details.
- `read_gold` validates tick age before requesting history, so blocked quotes
  prevent independent history diagnostics. Signal gates must remain strict.
- The observer stops on account-guard failure; a missing heartbeat cannot by
  itself distinguish stopped Python, disconnected MT5 or the wrong account.
- The UI maps all blocked states to unqualified quotes, even history or spread
  failures, and only refreshes on load/click. Displayed health can grow stale.

Proposed evidence contract (sanitized, no account identifiers):
- Delivery: last successful end-to-end API response; authentication required,
  unreachable and origin failure are separate states. Do not invent independent
  Worker/Tunnel/container probes from one response.
- Observer: snapshot time and calculated age; expire health when heartbeat
  exceeds the existing 30-second origin limit. Old MT5 observations become
  unknown, never a current connected/disconnected claim.
- MT5: explicit connection/account-guard check outcome with its observation
  time. Preserve fail-closed account behavior and publish only safe categories.
- Quote: raw tick epoch and milliseconds when available, checked/received time,
  measured age, and fresh/stale/future/missing/invalid status. Timestamp failures
  retain their evidence; no timezone correction by assumption.
- History: latest fetched completed M15 bar opening time, expected completed
  bar opening time, count and readiness independent of signal eligibility.
  Label any last successfully evaluated bar separately from fetched history.
- Strategy: ready/blocked with a specific reason and latest signal. Fresh
  quotes do not imply a tradable signal; a valid no-cross result is ready/none.

UI uses existing site primitives. Show "System reporting / Gold data blocked"
when those are the actual observations. Refresh every 10 seconds while visible,
refresh on return to the tab, prevent overlapping requests and bound request
time. Recalculate expiry in the browser so failed polling cannot leave an old
healthy state visible. An old quote alone must not be labeled "market closed";
that requires verified broker-session evidence.

Acceptance evidence:
1. Host clock synchronization plus documented tick/bar timestamp interpretation.
2. Fresh valid two-sided gold quotes measured across at least two consecutive
   completed M15 transitions; record timestamps and signal decisions.
3. At least 250 valid ordered completed bars and no forming-bar inputs. Latest
   history advances at each transition; a duplicate poll adds no decision.
4. Supervised restart retains state, resumes the correct demo session and does
   not replay an entry. Qualify connection recovery separately from fresh data.
5. Focused local checks cover stale/future/missing ticks, stale heartbeat,
   account-guard failure, invalid history, fresh quotes with blocked spread,
   unavailable origin and browser health expiry. Browser checks verify the
   displayed distinctions and authenticated delivery after deployment.

Next operational diagnostic: run the existing `verify-demo.py` in the VPS
container (not local Docker), capture its readiness output and host clock status.
If blocked, retain blocked status; collecting full failed-tick evidence requires
the planned diagnostic change. Implementation and deployment of these changes
have not yet occurred.

