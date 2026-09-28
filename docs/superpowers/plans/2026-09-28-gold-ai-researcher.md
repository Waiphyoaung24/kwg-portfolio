# Gold AI researcher and MT5 runner — selected 2026-09-28

## Resume here — four delivery batches

Detailed execution plans (planning only; numeric policy awaits review):
- [Batch 1 implementation](2026-09-28-gold-batch-1-implementation.md)
- [Batch 2 implementation](2026-09-28-gold-batch-2-implementation.md)

Owner approved this batch sequence on 2026-09-28 for continuation from a
MacBook. This is the current delivery checklist; earlier milestone status
below records historical progress. No batch enables orders or auto-promotion.

### Batch 1 — qualify data and costs (next)

- Verify pinned demo identity, Algo Trading off, synchronized host clock, and
  fresh gold bid/ask quotes with ages between 0 and 30 seconds.
- Record at least three valid observations spanning two consecutive advancing
  M15 boundaries. Confirm completed bars, raw tick timestamps and host receive
  times; do not guess timezone corrections. Retain restart/recovery checks.
- Confirm the account-specific commission and swap rules, including rollover
  timing and triple-charge day, from broker evidence. Record units and dates.
- Measure observed spread during the sample; retain explicit hypothetical
  slippage until execution evidence exists. Do not assume unknown costs are zero.
- Completion: save evidence and unresolved items. Stale prices or unknown
  material costs keep qualification blocked; weekend closure is not a pass.

### Batch 2 — freeze evaluation criteria

- Define sample-size requirements, drawdown limits, cost stress scenarios,
  improvement thresholds and uncertainty handling before candidate results.
- Preserve chronological splits and record every attempted candidate. The
  newest 2,000 bars have not been trade-simulated, but earlier signal replay
  included that period; describe this limitation honestly.
- Rerun the fixed baseline with documented cost assumptions. Do not change
  risk limits or choose favorable costs after seeing results.
- Completion: versioned criteria and a reproducible baseline report. Preparing
  criteria can proceed while Batch 1 waits for the market; unresolved evidence
  must remain explicit.

### Batch 3 — one Vibe-Trading experiment

- Depends on Batches 1 and 2. Verify the pinned Vibe-Trading version, broker
  data import, artifact output and the owner's existing Claude/Worker model
  invocation path. An MCP token alone is not proof of an inference API.
- Run one manually triggered, bounded proposal with call/time limits and
  isolated evaluation. No broker credentials, order tools, strategy write
  access or risk-limit changes are granted to the researcher.
- Compare against the fixed baseline under the frozen criteria; record failed
  proposals too. Keep holdout use controlled and avoid repeated tuning on it.
- Completion: reproducible acceptance/rejection report for observation only.

### Batch 4 — parallel observation

- Only a candidate passing Batch 3 proceeds. Observe baseline and candidate
  on the same fresh feed, without orders; record decisions and clearly labeled
  simulated outcomes using the same cost/fill model.
- Show version, evidence period and review state in the authenticated dashboard.
- Completion: enough new evidence under the frozen criteria for owner review.
  Promotion and demo execution remain separate decisions and implementation.

Each batch ends with saved evidence, outstanding blockers and a committed
handoff. No recurring monitoring or future scheduled run has been created.

### MacBook continuation

1. Pull `main` in the MacBook checkout (preserve any local work first). Read
   `CLAUDE.md`, this checklist, and `2026-09-28-gold-baseline-results.md`.
2. Begin with Batch 1; inspect current state rather than assuming the market
   has reopened or the previous status is still current.
3. Dashboard: https://waiphyoaung.com/vault/trading. Sign in through existing
   Cloudflare Access. VPS management: https://dokploy.castranova.cloud.
4. MT5/Wine and the observer run on VPS `187.52.117.116`, not on either laptop.
   Use existing authorized SSH access or Dokploy. Do not install local MT5 or
   recreate containers merely because the laptop changed.
5. For the private desktop, in a Mac terminal with an already-authorized SSH key:
   `ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:6081:127.0.0.1:6081 root@187.52.117.116`
   Then open `http://127.0.0.1:6081/vnc.html?autoconnect=1&resize=scale`.
   Keep that terminal open while viewing the desktop. Do not expose port 6081.
6. From an SSH shell **on the VPS**, the read-only check is:
   `docker exec kwg-mt5-desktop wine /opt/python/python.exe /opt/trading/verify-demo.py --login 1344907`
   Account login is the existing pinned demo identifier, not a credential to
   publish in the dashboard. Passwords, private keys and tokens stay out of Git.

Current foundation: private status path and continuous observer deployed;
signal replay and hypothetical trade simulator implemented and tested. All
three simulated validation cost scenarios lost money. Vibe-Trading research
integration, live qualification and actual costs remain pending. Detailed
private datasets and ledgers remain on the VPS; Git contains code and summaries.

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
the diagnostic change described above.

Implementation update: commit `f0e00d3` implements and deploys the health fields,
failed-tick evidence, automatic refresh and browser expiry. Verified on the VPS
at 2026-09-27 18:40 UTC: connected demo, 250 fetched bars and a stale quote aged
approximately 153829 seconds. Unit checks, build and signed-in live UI passed;
unauthenticated edge/origin checks remain denied. Fresh-data and M15-transition
qualification are still pending. See `CLAUDE.md` for deployment/rollback details.

## Milestone 2 data capture — 2026-09-28

Completed read-only exporter and froze 10,000 broker M15 bars on the VPS in
`/opt/kwg-gold-research/datasets/gold-history-20260928.json`. The complete
requested sample spans raw timestamps April 27 through September 25, 2026;
109 gaps are recorded. SHA-256 and current contract observations are recorded
in `CLAUDE.md`. Sixteen Python tests pass. The file is kept private outside Git.

This completes initial data capture, not baseline evaluation. The next work is
the deterministic evaluator, chronological split and explicit execution-cost
assumptions. Unqualified raw times, historical costs and gap handling must not
be silently converted into qualified profitability results. Live freshness and
two advancing M15 transitions remain an independent outstanding gate.


## Signal replay refinement — 2026-09-28

Proceed with a live verifier spot check and a deterministic historical signal
replay before building a trade simulator. Reuse the existing rolling 250-bar
signal evaluator, suppress startup/recovery signals, record code/data hashes
and blocked reasons. Bar close and spread are only quote proxies; replay does
not qualify live data or estimate profits. No holdout optimization occurs in
this diagnostic. Profit/loss evaluation still requires explicit cost/fill rules.

Replay result: commit `23966ec`, 17 Python checks passed. Two private VPS runs
on the frozen dataset were byte-identical: 90 long, 88 short, 9,360 none,
106 blocked, 107 startup/recovery resets. This is a signal-logic diagnostic,
not a cost-aware backtest or qualification. Live recheck at 19:05 UTC still
found a 155301-second-old quote and no new candle. Two live M15 transitions,
restart/recovery evidence and cost-aware evaluation remain outstanding.

## Hypothetical trade simulation — frozen before first run

User approved continuing offline work during the weekend. Use the fixed
baseline without parameter search: risk 0.1%, stop 2 ATR, target 3 ATR, one
position, opposite-signal close without same-bar reversal, daily 1% entry pause
sampled at bar open/close. Initial equity is a hypothetical USD 100,000 per
window, unrelated to the demo account balance.

Freeze chronological index splits at 60% development / 20% validation / 20%
reserved holdout. First 249 bars are indicator warmup. Reuse trailing history
for validation indicators, but reset capital/positions and suppress first-bar
entry intent. Close open positions at window ends. Do not evaluate holdout.
This diagnostic is not a promotion gate; no candidate search is authorized.

Cost scenarios are deliberately hypothetical, not broker fee estimates:

| Scenario | Commission USD/lot round trip | Slippage USD price/side | Overnight USD/lot/calendar day | Spread multiplier |
| --- | --- | --- | --- | --- |
| Lower | 3.5 | 0.05 | 5 | 1 |
| Middle | 7 | 0.10 | 15 | 1.5 |
| Stress | 14 | 0.30 | 30 | 2 |

Assume bid OHLC and constant bar spread; short exits use synthetic ask.
Evaluate a completed bar, enter only at the next adjacent bar opening, reject
wide entry spreads, and cancel entry intents across gaps. Round price and lots
to current symbol increments, including modeled exit costs in entry sizing.
Use stop-first for ambiguous intrabar touches, adverse opening-gap stop fills,
no favorable target gap improvement, and adverse slippage on exits.
Daily pause and drawdown use discrete observations; they cannot guarantee an
intrabar loss cap. Overnight debit per raw calendar day is a stress model, not
historical swaps. Margin availability/rejections and timestamp semantics remain
unqualified. No profitability or automatic promotion claim follows from a run.
