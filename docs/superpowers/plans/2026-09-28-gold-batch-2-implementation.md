# Batch 2: Gold Evaluation Rules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze prospective research acceptance criteria and rerun the fixed baseline using explicit, traceable cost profiles before one candidate is proposed.

**Architecture:** Keep the existing pure-Python simulator and immutable dataset. Add a narrow cost adapter and a deterministic evidence gate; separate result calculation from acceptance. Baseline diagnostics already seen cannot be retroactively called preregistered; new criteria apply prospectively to candidate testing.

**Tech Stack:** Python standard library/unittest; Linux Python on VPS for offline replay; JSON evidence/configuration, SHA-256, Git. No inference calls, trading SDK or new dependencies in this batch.

**Spec:** `docs/superpowers/plans/2026-09-28-gold-ai-researcher.md`; Batch 1 implementation plan and `2026-09-28-gold-baseline-results.md`.

## Global Constraints

- Use the existing EMA20/EMA50/ATR14 signal as a fixed comparison baseline.
- Initial equity is a hypothetical USD 100,000 per window, unrelated to the demo account balance.
- Preserve risk 0.1%, stop 2 ATR, target 3 ATR, one position, opposite-signal close without same-bar reversal, daily 1% entry pause sampled at bar open/close.
- No risk, account, dataset or evaluator changes by future researcher proposals.
- Missing costs or insufficient history block qualification rather than silently assuming zero.
- No automatic promotion, live orders, parameter search, UI expansion or Vibe-Trading installation in Batch 2.
- Numerical gates below are proposed research policy, not established guarantees or broker rules. Freeze after owner review and before the first candidate; revisions create a new policy version and invalidate prior candidate acceptance.

## Review Focus

- Round-trip/per-side fees, signed swap credits, rollover/DST and triple charges have different units: exact fixtures or reject unsupported mode (Task 1).
- Portfolio equity falls across midnight/weekend gap: do not reset day-start reference to an already-lowered new opening mark (Task 2).
- Candidate changes holding periods or time coverage: compare equal windows with flat boundaries, never unequal aggregate reports (Tasks 2, 3).
- Zero trades, tiny sample, NaN or inspected holdout: must be inconclusive/rejected, not an accidental pass (Task 3).
- Changed dataset/criteria/code, omitted failed trials or nondeterministic rerun: invalidate comparison and preserve audit trail (Tasks 3, 4).

## Known state and design choice

Manual report review is small but easy to apply inconsistently. Recommended: one JSON policy and one pure gate beside the existing simulator. A full optimization/experiment platform is deferred to demonstrated need. Existing 60/20/20 diagnostic used 10,000 bars and only ~30 validation trades; validation losses under all costs are retained, not tuned away. The last 2,000 bars were excluded from trade simulation but earlier signal counts included them.

File map: create `ops/trading/gold_costs.py`, `test_gold_costs.py`, `evaluation-policy.json`, `evaluate-gold.py`, `test_evaluate_gold.py`; modify `simulate-gold.py`, `test_simulate_gold.py`, `README.md`. Keep data, broker documents and detailed reports private outside Git. Do not extract an application framework from these scripts.

## Task 1: Explicit supported cost profiles

**Interfaces:** In `gold_costs.py`, `validate_profile(profile: dict, start: int, end: int) -> dict` returns normalized values and `historical_coverage`/`blockers`; invalid units/nonfinite inputs raise ValueError, unknown evidence stays incomplete. `commission_usd(profile: dict, lots: float, side: str) -> float` returns a nonnegative debit. `rollover_cashflow_usd(profile: dict, direction: int, lots: float, spec: dict, start: int, end: int) -> float` returns signed credit/debit over `(start,end]`.

**Files:** New cost module/tests; modify simulator CLI and README.

- [ ] Write fixtures: USD7/lot round-trip gives USD3.5 per side for one lot; a per-side USD7 source gives USD7 each side. Explicit zero with source is valid; null or an empty deal history is not zero. Reject unknown currency, negative commission, nonfinite numbers, missing required keys and unimplemented minimum/tiered fee schedules.
- [ ] Swap fixtures: POINTS mode with long=-2, point=.01, contract100, lots=.5 gives -1 USD for a single rollover and -3 for multiplier3. Signed positive rate is a credit. Currency-symbol/deposit/profit modes require evidenced USD currency semantics; accept only USD cash-per-lot or POINTS with USD linear CFD formula verified from spec. Reject interest/reopen/unsupported modes rather than approximating. Disabled swaps require explicit source evidence.
- [ ] Test `(start,end]` rollover event boundaries, multiple events over a weekend, zero-charge weekdays, triple day, entry exactly at rollover and dated rate changes. Dates outside source coverage stay hypothetical. Test the broker-confirmed timezone conversion across both DST changes; never replace a timezone with the current GMT offset.
- [ ] Run `python -B -m unittest discover -s ops/trading -p 'test_gold_costs.py'`; expect failing imports/assertions. Implement the exact interfaces. Profile schema v1 contains source hashes/effective intervals from Batch 1, commission basis, signed directional swap rates and explicit sorted UTC `rollover_events=[{at,multiplier,rate_long,rate_short}]` for the evaluated range. Generate these events from verified timezone/local schedule with stdlib zoneinfo as an operator preparation step; persist timezone, schedule and conversion version. If no verified timezone exists, profile remains hypothetical.
- [ ] Extend `simulate-gold.py` to accept optional `--cost-profile PATH`; retain current default hypothetical scenarios unchanged for reproducibility. Capture profile SHA and classification in the report. Missing historical fee evidence permits a diagnostic run but cannot yield candidate acceptance. Slippage remains `assumed`, tested at .05/.10/.30 price units per side; never relabel observed spread as measured slippage.
- [ ] Pass fixtures and full suite, commit `git commit -m "Add explicit dated gold cost profiles"`. Current broker rates do not rewrite the old frozen dataset or old results.

## Task 2: Correct simulator evidence limits before using gates

**Interfaces:** Keep `simulate(bars, signals, spec, costs, initial=100000)` callable by old tests. Add optional keyword `cost_profile=None`, dispatched through Task 1 helpers. `run(data)` retains diagnostic compatibility; add keyword `windows=None, cost_profile=None`. Windows specify explicit frozen start/end bar timestamps, not percentages recomputed after new bars are appended.

**Files:** Modify simulator and its existing tests; no change to live strategy/risk constants.

- [ ] Add `test_midnight_gap_keeps_previous_equity_reference`: previous close equity100000, first new-day mark98000 means entry pause is true. Prior end mark supplies the day-start proxy before new gap costs/P&L; report it as sampled/proxy equity, never exact midnight valuation.
- [ ] Add `test_rollover_costs_reconcile_trade_and_cash`: all signed funding flows and two commissions reconcile final cash minus initial with sum of closed net P&L. Ineligible/nonpositive equity cannot produce entries; reject nonfinite report metrics. Retain cost changes from Task 1, stop-first ambiguity, tick-size rounding and lot-step sizing.
- [ ] Add `test_splits_are_frozen_and_flat`: appending future bars does not move existing windows; no position/signal intent crosses a split; indicators use only earlier completed candles. Required 250-bar warmup is available before each window. Both compared strategies share exact timestamps, costs and initial capital.
- [ ] Run focused simulator tests, confirm new failures; implement the corrections. Current bar-average spread remains an execution proxy (not known-at-open data); label that limitation. Spread stress is applied to entry gating and synthetic exits consistently. Do not claim margin/rejections are simulated. Preserve original scenario run artifacts/version.
- [ ] Report mark-to-market daily returns, peak-to-trough sampled drawdown, realized net P&L, turnover, per-trade entry risk and `net_r=net_pnl/entry_risk_usd`, gaps, resets and rejects. Use close-sampled drawdown naming. Add exact tests for aggregation and denominator units; cash plus marked P&L must reconcile.
- [ ] Run full suite and one fixture twice (byte equality); commit `git commit -m "Make gold comparison windows and equity accounting explicit"`.

## Task 3: Freeze prospective gates and experiment identity

**Interfaces:** `evaluate_reports(baseline: dict, candidate: dict, policy: dict) -> dict` in `evaluate-gold.py` returns `decision=eligible_for_shadow|rejected|inconclusive`, `reasons`, and matching hashes. CLI: `--baseline PATH --candidate PATH --policy PATH --output PATH`; exclusive JSON output. It never calls model/broker APIs or promotes a strategy.

**Files:** New policy, evaluator and tests.

Proposed policy v1 (owner reviews before candidate work):

| Gate | Exact requirement |
| --- | --- |
| Evidence | Batch 1 recorded data continuity/recovery; matching code/dataset/cost policy; historically covered commission/funding for tested dates; explicit assumed slippage; no unresolved timestamp/contract blockers |
| Scope | Exactly one predeclared candidate and one change; unchanged risk constants and baseline; all failed attempts counted |
| Sample | At least 100 closed trades in both baseline and candidate across at least 60 distinct observed UTC trading days in validation; insufficient means inconclusive |
| Base cost | Candidate net return >0, profit factor >=1.10 and return improvement >=0.25 percentage points versus baseline on the identical window |
| Stress costs | Candidate net return >0 and not below baseline in every fixed stress scenario |
| Drawdown | Candidate close-sampled max drawdown <=5% and <=baseline drawdown+0.25 percentage points in every scenario; not a claim about true intrabar drawdown |
| Stability | Three fixed consecutive validation subwindows, each >=20 observed days; candidate improves over baseline in at least two and no subwindow underperforms by >0.25 percentage points; flat positions at each fold boundary |
| Uncertainty | Seed20260928, 10,000 paired moving-block bootstrap replicates of matching net daily returns, block length5 observed days, sample length original day count; lower nearest-rank 2.5th percentile of mean candidate-minus-baseline daily return must exceed0. Report full 95% interval and assumptions; uncertainty check is not proof under regime change |
| Final holdout | Never open during this batch or candidate selection; owner-reviewed one-time protocol only after shadow eligibility |

The existing 30-trade validation period cannot pass the sample gate. Do not lower it to fit known results. Collect additional data and freeze a new prospective evaluation manifest before a proposal; old reviewed validation is diagnostic, not unseen confirmation. Drawdown and sample thresholds are research policy, not guaranteed safety bounds.

- [ ] Write boundary tests for PF1.10, improvement .25pp, drawdown5%, day/trade minimums and fold limits; values just outside fail. Negative base net or one failing stress case must reject regardless of headline return.
- [ ] Test missing cost provenance, assumed historical rates, zero trades, missing baseline, mismatched dates/hash, nonfinite values, insufficient days/trades -> inconclusive (schema corruption -> ValueError). Fake candidate risk changes -> rejected. No-loss profit_factor=null must not pass by truthiness; require sufficient losing/winning evidence or mark inconclusive. Bootstrap all-zero differences fails; strictly positive constant differences passes; deterministic seed reproduces interval.
- [ ] Run focused tests to fail, then implement one pure gate with explicit reason codes. Precedence: reject scope/integrity violations; otherwise incomplete evidence -> inconclusive; complete evidence missing any numerical gate -> rejected; all gates -> eligible_for_shadow only.
- [ ] Save policy with `status=draft`, version and exact values; freeze to `approved` only after owner review. Tests ensure a draft cannot produce eligibility. Append private `experiments.jsonl` entries with trial id, hypothesis, declared single change, baseline/candidate/data/code/cost/policy hashes, windows, model/prompt version (null before research), status, failure/rejection reasons. Do not include tokens. Gate requires a frozen registration predating candidate execution; no retroactive registration.
- [ ] Pass full suite; commit `git commit -m "Freeze prospective gold research acceptance gates"`.

## Task 4: Rerun baseline and publish Batch 2 evidence

**Files:** README and CLAUDE handoff; create sanitized `docs/superpowers/plans/2026-09-28-gold-batch-2-results.md` during execution.

- [ ] Verify Batch 1 report hashes/cost coverage. If incomplete, finish evaluator tests and diagnostic baseline only; report blocked dependencies without fabricating evidence. Do not run candidate research yet.
- [ ] Use original dataset SHA `ba4f246746d861c9f61d82c7a09d17931cd74e9dea604ea2897853369dcf8614`. Freeze existing development/validation timestamps from prior result report. Last 2,000 bars stay excluded from trade simulation; acknowledge earlier signal-only access. Define three prospective folds only once sufficient dates exist; do not invent extra independent days.
- [ ] Deploy only offline Python files to a new versioned private research directory; verify code/data/profile hashes. Never mount broker state or change MT5. Run baseline twice using new filenames and compare report bytes; save private profile and ledgers with owner-only permissions.
- [ ] Run `python -B -m unittest discover -s ops/trading -p 'test_*.py'`; all tests must pass. Test gate with known-good and rejection synthetic reports only. Confirm real baseline has no candidate eligibility report: there is no candidate yet.
- [ ] Save sanitized result with actual/hypothetical cost distinction, exact windows, metrics/limitations, policy review status and outstanding data needs. If remaining unknowns persist, label `prepared_but_blocked`, not “Batch 2 qualified”.
- [ ] Commit/push only code, policy and sanitized summaries. Handoff Batch 3 remains conditional on Batches 1/2 evidence and approved policy. No Vibe-Trading job, order path or recurring monitoring starts automatically.

## Documentation and self-review

Context7 `/lucas-campagna/mt5linux` was checked for symbol/deal field semantics. Primary: https://www.mql5.com/en/docs/constants/environment_state/marketinfoconstants (swap modes, point/contract size, volume increments), https://www.mql5.com/en/docs/python_metatrader5/mt5symbolinfo_py (available metadata). Neither establishes this account's fee history. Proposed statistical/risk thresholds are design choices, not claims sourced from these APIs.

Self-review: Tasks 1–4 cover every review risk and expose exact interfaces. No confidence or profitability claim is inferred from the prior 22 passing software tests. Old outcomes stay immutable; current policy cannot be presented as preregistered before those old outcomes.

## Runnable assertion examples for Tasks 1 and 3

Use in-file fixtures `usd_round_trip_profile(value)` and `matching_reports()`;
the former supplies the complete evidenced schema from Task 1, the latter
supplies identical metadata plus all numeric gate fields from Task 3.

```python
def test_round_trip_commission(self):
    profile = usd_round_trip_profile(7)
    self.assertEqual(commission_usd(profile, 1, 'entry'), 3.5)
    self.assertEqual(commission_usd(profile, 1, 'exit'), 3.5)

def test_small_sample_never_passes(self):
    baseline, candidate, policy = matching_reports()
    candidate['validation']['trades'] = 30
    self.assertEqual(evaluate_reports(baseline, candidate, policy)['decision'], 'inconclusive')
```

Report adapter contract for the second fixture: evaluator inputs have
`validation={trades,observed_days,scenarios,folds,daily_returns}` plus
`identity={dataset_sha256,evaluator_sha256,cost_profile_sha256,policy_sha256,
window_start,window_end,risk_sha256}` and `evidence={batch1_status,cost_status,
registration_at,execution_started_at}`. Each scenario has the summary metrics
already produced by `simulate`; daily_returns maps UTC day to fractional net
return. `evaluate-gold.py` builds this adapter from immutable simulator reports;
missing fields are invalid, never silently defaulted. Registration metadata
adds candidate/baseline hashes without requiring their hashes to be identical.

Bootstrap algorithm: pair same-day returns first; form all overlapping blocks
of five observations within the same fold (never across a flat reset boundary).
Sample blocks with replacement using `random.Random(20260928)` until original
length, truncate excess, calculate mean paired difference; repeat10,000 times.
Use sorted nearest-rank 2.5th/97.5th percentiles. Reject a fold shorter than five
observations. This is an exploratory uncertainty model under dependence, not a
multiple-testing correction; one registered candidate remains the trial limit.
