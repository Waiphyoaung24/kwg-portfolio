# Gold Offline First Experiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. This document is planning only. The owner will review it before implementation starts.

**Goal:** Produce one reproducible, explicitly provisional comparison between the existing gold baseline and one bounded Vibe-Trading proposal.

**Architecture:** Reuse the frozen MT5 dataset, replay, simulator and strict promotion evaluator. Add a small offline experiment manifest, an entry-only candidate filter and a comparison report. Vibe-Trading proposes structured data through the owner's existing model connection; generated code never runs against MT5.

**Tech Stack:** Existing Python standard library and unittest; native Linux research environment; pinned Vibe-Trading version subject to a capability check. No frontend, Worker or MT5 deployment in this plan.

**Spec:** `docs/superpowers/plans/2026-09-28-gold-ai-researcher.md`, the Batch 1/2 result notes, and the owner's request to plan the four offline steps before implementation. This plan permits exploratory research while live qualification is incomplete; it does not waive the earlier promotion gates.

## Global Constraints

- Planning status: **awaiting owner review; no implementation authorized by this document alone**.
- Instrument `XAUUSD-VIP`; completed M15 bars; baseline EMA20/EMA50 and ATR14.
- Keep risk 0.1% of equity, stop 2 ATR, target 3 ATR, one position, no pyramiding or martingale, no same-bar reversal, and the existing 1% daily entry pause.
- Preserve the existing next-adjacent-bar entry, adverse gap fills, stop-first ambiguity handling, volume rounding and window liquidation rules.
- No orders, Algo Trading activation, observer changes, cloud deployment, automatic promotion or recurring research job.
- Private dataset, model credentials, raw reports and broker identifiers stay outside Git. Git contains source, tests, plan and sanitized results only.
- Unknown historical fees remain unknown. Do not relabel today's fees as verified historical costs or weaken `gold_costs.validate_profile`.
- An MCP token is not proof of a compatible inference endpoint. Verify the existing Claude/Worker path without printing secrets or introducing another paid provider.

## Current evidence and limits

The offset-enabled one-shot check passed at 2026-09-28 12:34 UTC: quote age
0.204 seconds, 250 completed bars and the expected latest completed candle.
The subsequent long collector accepted 57 samples, then stopped with an MT5
connection failure; SSH reset afterward. The cause is unresolved. Continuous
two-boundary reliability did not pass and is deferred at the owner's request.

The owner reports Standard STP. Current broker documentation lists no separate
gold commission for Standard STP and VIP STP; the exact `-VIP` tier still needs
reconciliation. Current MT5 observations are swap mode POINTS, long -79.48,
short +34.41, three-day field Wednesday, contract size 100, point 0.01 and USD
profit currency. Historical rates and exact rollover timing are unavailable.

The previously simulated validation period has already been inspected and lost
money under all three old scenarios. All 10,000 bars were used in earlier signal
replay. The newest 2,000 bars were not trade-simulated but are not wholly unseen.
This experiment is exploratory, never independent confirmation of profitability.

## File map

| File | Responsibility |
| --- | --- |
| Create `ops/trading/gold_experiment.py` | Validate experiment/proposal data; freeze inputs; apply the entry filter; compare report identities and results |
| Create `ops/trading/compare-gold.py` | Offline CLI for experiment preparation and comparison; exclusive output creation |
| Create `ops/trading/test_gold_experiment.py` | Reproducibility, input rejection, filter and comparison checks |
| Modify `ops/trading/replay-gold.py` | Optional offline candidate annotation; default baseline output preserved |
| Modify `ops/trading/simulate-gold.py` | Optional candidate input; filter new entries only; complete provenance |
| Modify `ops/trading/test_replay_gold.py`, `ops/trading/test_simulate_gold.py` | Baseline parity, causality and unchanged exit/risk behavior |
| Create `docs/superpowers/plans/2026-09-28-gold-first-experiment-results.md` during execution | Sanitized outcome and outstanding blockers |
| Modify `ops/trading/README.md` during execution | Exact tested offline commands and resumption steps |

Do not modify `gold_signal.py`, `gold_costs.py`, `evaluate-gold.py`,
`evaluation-policy.json`, the observer, desktop launcher or dashboard for this experiment.

## Review Focus

1. A modified dataset or report must fail identity checks rather than produce a comparison (Tasks 1 and 4).
2. Current costs or a constant three-hour offset must never become historical facts (Tasks 1 and 2).
3. A candidate must not access future bars or suppress protective/opposite-signal exits (Task 3).
4. A malformed proposal, unavailable model route or timeout must not trigger an unrecorded second experiment (Task 3).
5. Better-looking returns with missing evidence, too few trades or reused validation must not imply promotion (Task 4).

## Task 1 — Freeze the existing data and experiment inputs

**Files:** Create `gold_experiment.py`, `compare-gold.py`, `test_gold_experiment.py` in `ops/trading/`.

**Interfaces:**
- `prepare_experiment(data: dict, dataset_sha256: str, code_sha256: dict) -> dict` returns a JSON-safe manifest.
- CLI: `compare-gold.py prepare --dataset PATH --sha256 HASH --output PATH` verifies bytes before parsing and writes once using exclusive creation.
- Manifest fields: `schema_version=1`, `status="prepared"`, `mode="provisional-offline"`, `dataset_sha256`, `code_sha256`, `windows`, `reserved_start_index`, `scenarios`, `risk`, `cost_evidence`, `timestamp_basis`, `prior_exposure`, `live_qualification`. Task 3 finalizes the shared evaluator revision before any proposal is requested.

- [ ] Confirm the private VPS file exists at `/opt/kwg-gold-research/datasets/gold-history-20260928.json`. Verify SHA-256 `ba4f246746d861c9f61d82c7a09d17931cd74e9dea604ea2897853369dcf8614`. Stop on mismatch; never overwrite or re-export to make it match.
- [ ] Add failing tests: reject wrong hash, schema/symbol/timeframe/start position, nonfinite prices, duplicate/unordered timestamps and invalid OHLC/spread. Count gaps without filling them. Reject an existing output path.
- [ ] Implement manifest preparation using the existing completed-bar validation and explicit whole-dataset structure checks. Inspect reserved bars only for integrity, not strategy outcomes.
- [ ] Freeze zero-based indices: 0–248 warmup, 249–5999 development, 6000–7999 validation, 8000–9999 reserved. Require the expected 10,000 bars for this experiment; derive each window's exact start/end timestamps from the dataset. Preserve raw timestamps, labeled `raw_broker_epoch_unqualified`; do not subtract today's offset from historical data.
- [ ] Copy the unchanged `SCENARIOS` and risk rules into the manifest; hash canonical JSON (`sort_keys=True`, compact separators, `allow_nan=False`). Record complete evaluator source hashes, including imported replay/signal/cost/experiment modules. Record prior exposure and `live_qualification="inconclusive_disconnect"`.
- [ ] Verify repeated preparation is byte-identical. Store the prepared manifest privately under `/opt/kwg-gold-research/experiments/gold-exp-001/manifest-prepared.json`; keep directories owner-only. Commit only source/tests after the new and existing offline tests pass.

**Done when:** Dataset identity, windows, costs, risks and evaluator version are frozen before the proposal or candidate results.

## Task 2 — Reproduce the baseline with explicit cost assumptions

**Files:** Reuse `simulate-gold.py`, `replay-gold.py`, `test_simulate_gold.py`; extend provenance only as needed. Save the sanitized result document.

**Interfaces:** Existing `run(data, *, windows=None, cost_profile=None)` remains valid. The manifest's `windows` uses existing `development` and `validation` objects, each containing inclusive integer `start`/`end` timestamps.

The first comparison deliberately uses the existing hypothetical scenarios:

| Scenario | Commission USD/lot round trip | Slippage price/side | Overnight USD/lot/raw calendar day | Recorded spread multiplier |
| --- | ---: | ---: | ---: | ---: |
| lower | 3.5 | 0.05 | 5 | 1 |
| middle | 7 | 0.10 | 15 | 1.5 |
| stress | 14 | 0.30 | 30 | 2 |

These are sensitivity inputs, **not estimates or bounds on actual broker costs**.
Today's long swap observation exceeds these flat overnight debits; the scenario
called stress is not guaranteed conservative. Preserve all three for comparison
with prior runs. Today's zero-commission indication, current directional swap
and sampled spread 0.27–0.28 belong in `cost_evidence` as current observations;
do not replace historical spread or fabricate a historical rollover calendar.

- [ ] Test that missing historical cost coverage still fails the existing verified-profile path. Assert manifest scenarios equal the simulator's unchanged `SCENARIOS`.
- [ ] Run the baseline using the exact manifest windows and no verified `--cost-profile`. Save exclusive private outputs `baseline-preliminary-a.json` and `baseline-preliminary-b.json`. Task 3 repeats this with the final shared evaluator revision before research begins.
- [ ] Verify byte-identical results and expected source/window/dataset hashes. Report per-window trade count, net return/P&L, profit factor (undefined when appropriate), expectancy, close-sampled drawdown and scenario sensitivity.
- [ ] Mark results `qualification="unqualified"`, `cost_profile_status="hypothetical"`. Record the disconnect, raw-time ambiguity, historical-cost gap and previously inspected validation. Do not call raw day grouping verified UTC funding.
- [ ] Commit necessary provenance changes and sanitized baseline summary after focused tests pass. If bytes differ from the previous baseline, explain the cause before candidate execution.

**Done when:** The frozen baseline is reproducible and its limitations are visible. Verified historical costs are a future qualification gate, not a precondition for this explicitly hypothetical run.

## Task 3 — Obtain and register exactly one research proposal

**Files:** Extend `gold_experiment.py`, `replay-gold.py`, `simulate-gold.py` and their tests. Store researcher artifacts privately; record sanitized provenance in the result document.

**Interfaces:**
- `validate_candidate(proposal: dict) -> dict` accepts only `kind="ema20_slope_filter"`, integer `lookback_bars` from 2 through 5, and a nonempty `hypothesis` of at most 2,000 characters. Reject extra keys, booleans as integers and every risk/cost/code field.
- `entry_allowed(bars: list[dict], signal: str, lookback_bars: int) -> bool` compares the existing SMA-seeded EMA20 at the last completed bar with its value N bars earlier, using only that same trailing 250-bar window. Long requires a strictly positive slope; short requires a strictly negative slope; a flat slope rejects entry.
- `replay(data, *, candidate=None)` preserves default results exactly. Candidate replay annotates each decision with `entry_allowed`; it retains the original crossover `signal` and ATR.
- `run(data, *, windows=None, cost_profile=None, candidate=None)` passes the candidate to replay. `simulate` checks `pending.get("entry_allowed", True)` only before opening a new position. Opposite-cross closing, protection, sizing and pause logic remain unchanged.

- [ ] Inspect the installed Vibe-Trading package/revision and its documented research interface. Pin the tested version and record the exact supported invocation. Consult upstream at `https://github.com/HKUDS/Vibe-Trading`; do not assume the current upstream matches the installed package or invent a CLI command.
- [ ] Verify the existing Claude/Worker model path with a bounded connectivity check. No token values in reports. If that path is unsupported, record `research_connection_blocked` and stop the actual job; do not silently replace Vibe-Trading with a locally invented proposal.
- [ ] Add regression tests for invalid/extra proposal fields, future-bar mutation leaving earlier decisions unchanged, baseline byte parity, and a filtered opposite crossover still closing an existing position. Assert all frozen risk settings are identical for baseline and candidate.
- [ ] Implement the interfaces above with the existing EMA helper. Record candidate filtering in skips/report labels without presenting filtered entries as blocked data. No generated Python execution or new plugin architecture.
- [ ] Finalize shared evaluator code and run the focused tests before research. Create exclusive `manifest.json` with `status="frozen"` and updated code hashes; require dataset/windows/scenarios/risk to equal the prepared manifest. Run baseline twice again as `baseline-a.json` and `baseline-b.json`, verify byte identity and metric parity with Task 2. Any unexplained difference blocks the job. Do not change evaluator code after this freeze; a necessary correction requires a new recorded experiment.
- [ ] Prepare researcher inputs using development bars/results only. No validation or reserved data mounts, broker volume, Docker socket, account credentials or executable strategy/evaluator write access. Provide the allowed JSON shape and the fixed risk/cost rules.
- [ ] Run one manually triggered job: maximum 10 minutes, at most two model requests including the connectivity check, maximum 8,000 combined input/output tokens where the supported route can enforce them. If limits cannot be enforced, stop for a supported bounded invocation; do not start an unattended job. No proposal-repair loop or parameter sweep.
- [ ] Record prompt/model/version, request outcome, timestamps and failure reasons. Validate and register the single proposal, with manifest/proposal hashes and registration time, **before** any candidate simulation. A refusal, malformed response or timeout ends this experiment as inconclusive.
- [ ] Run focused tests and commit the offline candidate support separately from private proposal artifacts.

**Done when:** One genuine, auditable proposal is registered, or its integration failure is recorded honestly. No candidate is selected by trying several lookbacks on validation.

## Task 4 — Compare once and write the decision report

**Files:** Extend `compare-gold.py`, `gold_experiment.py`, `test_gold_experiment.py`; update result notes and README. Keep `evaluate-gold.py` and the draft policy unchanged.

**Interfaces:**
- `compare_reports(baseline: dict, candidate: dict, manifest: dict, proposal: dict) -> dict` verifies identical dataset, windows, cost scenarios, risk and evaluator hashes. It returns per-scenario/window deltas and an exploratory verdict, always with `promotion_status="blocked"`.
- CLI: `compare-gold.py compare --baseline PATH --candidate PATH --manifest PATH --proposal PATH --output PATH`. Outputs use exclusive creation and deterministic JSON.
- Both raw simulation reports include candidate identity separately from their shared evaluator identity. Hash every executed source dependency; reject missing/mismatched provenance rather than comparing unlike runs.

Predeclared exploratory verdicts (not the strict promotion evaluator):
- `inconclusive`: missing/invalid metrics, undefined profit factor, or fewer than 100 validation trades for either strategy.
- `promising_for_further_research`: candidate validation returns are positive in all three scenarios; lower-scenario return improves at least 0.25 percentage points with profit factor at least 1.1; middle/stress returns are no worse than baseline; drawdown is at most 5% and increases by no more than 0.25 percentage points in any scenario.
- `rejected`: sufficient data but the stated exploratory numerical criteria fail.

All verdicts retain unresolved data/cost/time/reused-validation limitations.
None grants shadow eligibility. The existing stricter evaluator additionally
requires approved policy, historical cost coverage, live qualification, folds
and uncertainty evidence; this experiment does not manufacture those inputs.

- [ ] Test hash/risk/window mismatch rejection, identical-strategy zero deltas, undefined profit factor and insufficient trades producing inconclusive, and an otherwise better candidate still having promotion blocked.
- [ ] Simulate the registered candidate twice using the same manifest and private dataset; verify deterministic outputs. Preserve separate output names and all unsuccessful results.
- [ ] Compare development and validation once. Do not run the reserved newest 2,000 bars, tune after seeing validation, or register another proposal in this experiment.
- [ ] Write the private comparison JSON and a sanitized Markdown table: baseline/candidate metrics, deltas, assumptions, evidence gaps and explicit disposition. Include code/data/manifest/proposal hashes, researcher provenance and prior-exposure statement.
- [ ] Run `python -B -m unittest discover -s ops/trading -p 'test_*.py'` and `git diff --check`. Review that production files, risk limits and the draft policy are unchanged. Commit only named source/test/docs files; preserve unrelated workspace changes.
- [ ] Hand the owner the report. Rejected candidates stay rejected; inconclusive candidates need evidence; promising candidates need the earlier qualification and review gates before any live shadow implementation.

**Done when:** The owner can reproduce what was compared, see whether the one proposal helped under declared assumptions, and distinguish exploratory improvement from deployable trading performance.

## Execution handoff

Expected deliverables: private frozen manifest, reproducible baseline, one
registered Vibe-Trading proposal or explicit integration failure, and one
comparison/decision report. There is no promise of profitability or a successful
proposal. No long live test is required to run this offline experiment.

This plan has been checked against existing replay/simulator interfaces and the
recorded evidence gaps. **Stop here for owner review. Implementation, research
calls, deployment and experiment execution have not begun.**
