# Batch 3 Vibe-Trading Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for any later authorized implementation. Checkboxes record scope and evidence, not authorization to launch research.

**Goal:** Prepare one reproducible comparison of one structured proposal against
the fixed gold baseline, with unchanged qualification gates and human approval.

**Architecture:** Reuse the existing packet/parser, simulator, adapters and
comparison code. Keep the learning app and read-only gold MCP separate from
the credential-owning gold controller. Reconcile newer execution history as
evidence; do not import the newer gateway branch or restart its consumed attempt.

**Tech Stack:** Existing Python standard-library offline tests and existing MCP
Worker. No dependency installation, provider request, scheduler or VPS operation
is needed for this reconciliation.

**Spec:** [Batch 3 specification](../specs/2026-10-01-gold-batch3-vibe-integration.md).
**Evidence:** [October 6 reconciliation](2026-10-06-batch3-preparation-reconciliation.md).

## Current milestone and source boundary

Prepared in a separate worktree on `codex/batch3-preparation-reconcile`,
based on local main `1881e77656c3e26c7ec2bd248e309ec7698e20dd`.
The Desktop checkout remains on `codex/batch3-supported-gateway` at
`18620b96eb05eeef86dcea52acf3e00cb1c09e6c`, including its uncommitted records.
No merge, cherry-pick, stash, branch switch or deployment is part of this task.

Batch 2 is closed for development and unqualified. Its observation program is
deferred, not passed. Offline integration exists; do not recreate the parser,
runner or adapter described as new in the superseded October 1 plan.
The October 2 smoke review is complete with a partial pipeline verdict.

Newer records document one approved development-only proposal attempt as
consumed with unknown request outcome, verified cleanup, and no proposal/usage
artifacts. There is no accepted candidate to compare. Neither absence of output
nor this worktree provides permission to retry. Preserve all seals, registries,
receipts, approvals and failed inspections.

This plan replaces the outdated pending-task list. Earlier plan text remains
available in Git at the main base above. Historical successful provider/account/
isolation checks must not be treated as fresh gates.

## Global constraints

- Current authorization: reconciliation, fake-only diagnostic patch, offline checks,
  review, commit and push of the preparation branch. No merge.
- No real model/account/browser refresh, owner helper, production registry read,
  scheduler enablement, candidate research, trade, journal reset or VPS change.
- No retry, fallback, reset, rename, reseal or retiming of the consumed attempt.
- XAUUSD-VIP, completed M15; EMA20/EMA50/ATR14; 0.1% equity entry risk,
  2 ATR stop, 3 ATR target, 1% UTC day-start loss entry pause, one position,
  no pyramiding/martingale or same-candle reversal.
- Risk SHA-256: `865e46d493db5939e9e3d98375ce727664d57c03bc42a06e548cace61a8e6ce7`.
- Policy SHA-256: `39eb8759133ac1ca50308e0aa053c761a53b24e94be9ebc3f8c13ff73413873d`.
- Proposal: exactly kind=ema20_slope_filter, integer lookback_bars=2..5
  (not boolean), nonblank hypothesis of at most 2,000 characters.
- Later supported route: gpt-5.6-sol/medium, one POST, stream=true/store=false,
  zero retries/fallback/tools, USD0 additional spend. Local bounds are 16,384
  proposal bytes, 262,144 stream bytes, 65,536 event bytes, 120-second stream
  processing and 180-second controller deadline. No provider-enforced 2,048-token
  cap is claimed; that original requirement was replaced by owner decision.
- Private evidence stays private and exclusive. Unknown request/usage outcomes
  remain unknown. Qualification and promotion never follow from test success.

## Review focus

1. Old branch/main or historical/current claims mixed together: pin source
   revisions and document hashes; verify only scoped documentation changes (Task 1).
2. Generic failures lose stage information or expose secrets: fake-only negative
   tests must preserve uncertainty and omit arbitrary content (Task 2).
3. Approval describes a different payload: assert stream/store, model, effort,
   request count and no tools against the actual request fixture (Task 2).
4. Hypothetical or synthetic evidence masquerades as qualification: preserve
   provenance cap, zero eligible days and cost/clock blockers (Tasks 1 and 3).
5. Passing metrics or stale approval enables activation: bind human review to
   exact hashes and retain report-only blocked promotion (Task 4).

## File map

| Files | Role / source |
| --- | --- |
| This plan, companion spec, reconciliation checkpoint, diagnostic review, ops/trading/HANDOFF.md | Current evidence and scope |
| ops/trading/patches/2026-10-06-proposal-diagnostics.patch; check-proposal-diagnostic-patch.py | Unapplied pinned patch and disposable offline verifier |
| ops/trading/research-gold.py; test_research_gold.py | Existing packet/prompt/parser and exclusive replay on main |
| ops/trading/gold_experiment.py; compare-gold.py; test_gold_experiment.py | Existing schema, filter, legacy registration and provisional comparison |
| ops/trading/batch2_adapter.py; test_batch2_adapter.py | Existing baseline preparation adapter; cannot qualify real evidence |
| ops/trading/batch3_adapter.py; batch3_runner.py | Existing synthetic integration on main; newer real-development adapter is branch work |
| ops/trading/simulate-gold.py; evaluate-gold.py; evaluation-policy.json | Fixed simulator and approved policy; unchanged |
| ops/trading/supported_oauth_transport.py; gold_proposal.py; their tests | Newer supported-gateway branch only; not brought into this worktree |

### Task 1: Reconcile status and verify the offline baseline — complete

**Interfaces:** existing `validate_packet(packet)`, `build_prompt(packet)`,
`parse_proposal(raw)`, `replay_response(raw, output_dir)`,
`validate_candidate(proposal)`, `compare_reports(...)`,
`adapt_baseline(...)` and `evaluate_reports(...)`. No new interface.

- [x] Preserve the original checkout and create the approved main-based worktree.
- [x] Read the roadmap, wrap-up, development close-out, smoke review and newer
  saved-outcome records. Record provenance without private-file access.
- [x] Update the spec, this plan and handoff to distinguish development closure,
  deferred qualification and consumed proposal history.
- [x] Run the five focused modules below: 39 tests passed. They exercise strict
  packet/schema rejection, fixed identities, exclusive attempts, replay,
  cost coverage, real-format fixture reconciliation and qualification refusal.
- [x] Independently recompute canonical risk/policy hashes; both match the spec.

From the worktree's `ops/trading` directory:

```powershell
python -B -m unittest test_research_gold test_gold_experiment test_evaluate_gold test_gold_costs test_batch2_adapter
```

Expected: 39 tests, OK, no live model or broker calls. Fixtures create temporary
files only; this is not the complete trading suite or a production containment test.
No Node dependencies are present in the fresh worktree; the MCP Node suite was
not rerun or installed for this documentation change.

### Task 2: Prepare a fake-only diagnostic patch — implemented as an unapplied artifact

**Source dependency:** review the supported-gateway branch separately before
porting any code to main. Keep the consumed runtime and all source seals intact.

**Files:** on that reviewed source snapshot, use
`ops/trading/supported_oauth_transport.py` (`_invoke`, `parse_stream`),
`ops/trading/gold_proposal.py` (`worker`, `run`) and existing
`test_supported_oauth_transport.py` / `test_gold_proposal.py`.
Do not build a new transport or general error framework.

- [x] Pin the proposed safe receipt contract before editing: bounded enumerated
  failure stage, optional numeric HTTP status and an explicit allowlist of
  provider failure codes. Unknown strings become a fixed unknown code; no raw
  message/body/header/token/prompt/account value may cross the boundary.
- [x] Add fake HTTP/worker tests for refusal, truncated stream, identity and usage
  rejection, worker initialization and cleanup failure. Assert request count
  remains unknown after possible transfer, replay stays refused and no fallback
  or second POST occurs.
- [x] Add an approval-text/request fixture check for gpt-5.6-sol/medium,
  stream=true/store=false, one POST, no tools and the reviewed bounds. Preserve
  the original inaccurate approval text as historical evidence.
- [x] Implement only safe classification propagation into the worker/controller
  receipt; run those focused fake suites, with private/native/network calls
  mocked. Present the diff for review before any future live plan.

The [diagnostic review](2026-10-06-batch3-diagnostic-review.md) records the patch,
request-review hash binding, hook cause and red/green evidence. The offline checker
applies the patch only to a disposable export of commit
`18620b96eb05eeef86dcea52acf3e00cb1c09e6c`; all 14 focused fake tests pass.
No supported-gateway code is installed on main or into any sealed runtime.

Completion means a reviewed diagnostic candidate, not another inference attempt.
Do not rerun either saved inspector: it cannot recover discarded failure details.

### Task 3: Establish qualified comparison inputs — deferred Batch 2 gate

**Files:** future separately reviewed work in `batch2_adapter.py`,
`gold_experiment.py`, `simulate-gold.py`, `compare-gold.py` and their tests;
private dated evidence and protocol. Do not start collection now.

- [ ] Obtain applicable dated commission, directional swap, rollover, exact-symbol
  session and UTC/DST mapping coverage for every frozen window.
- [ ] Freeze future collection boundaries, code/risk/policy/cost/clock identities,
  development/validation, three flat folds and a separate untouched holdout
  before qualifying collection. Preserve the original reserved 2,000 bars and
  disclose prior validation inspection/signal replay.
- [ ] Specify and test the qualified manifest/registration and raw-report adapter
  against real provenance. Reject missing coverage, hash drift, overlap, late
  registration, invented dates and synthetic eligibility. The existing
  preparation adapter's unqualified output is not sufficient.
- [ ] Meet unchanged baseline sample requirements; freeze exact inputs and run
  the baseline twice to distinct private outputs with equal canonical report
  bytes. Baseline profitability is not required to start a fair comparison.

The approved minimums remain 100 closed trades per strategy, 60 eligible
validation days and three folds of at least 20 days, plus all fixed performance,
drawdown, stress and bootstrap gates. Candidate sufficiency is an outcome of
Task 4, not a prerequisite that can be assumed before it runs.
Do not remove `simulator_provenance_unverified` without separate review.

### Task 4: One future comparison and human review — blocked

**Inputs:** Task 3 evidence, reviewed controller/runtime, current account/model/
billing/isolation proofs, and explicit authorization for a distinct future
experiment after Task 2 review. This plan provides none of that authorization.

- [ ] Prepare a separate concrete run plan and exact human approval. A new ID
  must never be used merely to bypass the consumed attempt's replay guard.
  No live connectivity probe is implicitly included in a one-request budget.
- [ ] Supply only the allowlisted development summary and proposal schema.
  Reserve once before dispatch; retain failures and unknown outcomes. Accept
  one strict proposal, without repair, parameter sweep or another model request.
- [ ] Register its byte hash before candidate validation execution or inspection.
  Reuse unchanged entries/exits, sizing, costs, timestamps, windows, folds and
  initial simulated USD100,000 per window for baseline and candidate.
- [ ] Evaluate the saved candidate twice offline to exclusive paths; require
  identical canonical report bytes and all shared identities. Report mismatch
  or incomplete evidence as inconclusive, without overwriting or tuning.
- [ ] Derive gate metrics from verified raw outputs. Report per-scenario/fold
  counts, returns, net P&L, profit factor, drawdown, expectancy, turnover,
  risk-normalized results, paired bootstrap interval and limitations.
- [ ] Keep `promotion_status=blocked`. Only a passing qualified comparison can
  be presented for human Batch 4 no-order observation approval, bound to exact
  candidate/baseline/comparison/policy hashes, approver, UTC time and scope.
  Missing, stale or mismatched approval does not authorize observation.
  Execution promotion needs its own explicit approval and implementation.

An independently authorized unqualified development comparison can use the
October 2 deferred-qualification scope, but can never yield shadow eligibility
or replace Task 3. No such proposal or comparison is authorized now.

## Verification and handoff

The checkpoint records fresh checks separately from historical evidence.
Self-review: all fixed comparison/risk requirements are retained; implemented
helpers are reused; the supported-gateway source boundary is explicit; smoke
and synthetic checks earn no qualification credit; human promotion stays separate.
No future implementation or live execution method is selected by this document.
