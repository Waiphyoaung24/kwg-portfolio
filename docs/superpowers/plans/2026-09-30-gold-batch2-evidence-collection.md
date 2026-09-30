# Gold Batch 2 Evidence Collection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task with the previously selected native execution method. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Make private dated evidence capture reproducible and define the remaining qualification gates without fabricating historical coverage.

**Architecture:** Extend the existing read-only probe with exclusive JSON output. Use existing verifier, exporter and cost validator for operator checks; record a private prospective collection manifest. Keep the evaluator cap until a separately verified adapter exists.

**Tech Stack:** Python stdlib/unittest, existing MT5 SDK and private JSON files; manual VPS execution. No new scheduler, service or dependency.

**Spec:** `docs/superpowers/specs/2026-09-30-gold-batch2-continuation.md`, Milestones B/C. This plan completes collection readiness, not an unconditional qualification pass.

## Global Constraints

- Algo off for observation; no new trade, cancellation, restart or research job.
- Preserve raw epochs, immutable datasets, reserved holdout and approved v1 policy.
- `cost_status="incomplete"` and `timestamp_status="current_spot_checks_only"` remain on probe output.
- Private captures stay outside Git with owner-private permissions. Current rates are not historical coverage.
- Keep `prepared_but_blocked` and `simulator_provenance_unverified` while evidence is insufficient.

## Review Focus

- Reusing an output path must refuse overwrite and preserve original bytes.
- Failed capture/write must not print a success hash or create a supposedly verified checkpoint.
- Stale closed-session quotes and error `None` must retain their distinct meanings.
- Equal snapshots around midnight are not proof of a rollover charge or interval-wide rate coverage.
- Historical warmup or inspected bars must not be counted as new prospective validation.

## File map

Modify `ops/trading/batch2-evidence.py`, `ops/trading/test_batch2_evidence.py`, `ops/trading/README.md` and `ops/trading/HANDOFF.md`. The probe is already in Docker packaging. Create no second collector or general evidence framework. Operator artifacts below are private, not repository files.

### Task 1: Exclusive private capture output

**Interfaces:** Preserve `capture(mt5, login, now, server_offset_seconds) -> dict`. Add `save_evidence(path: Path, result: dict) -> str` returning SHA-256 of canonical UTF-8 bytes, sorted keys, no NaN, trailing newline, exclusive `xb`. Add optional CLI `--output PATH`; without it, preserve existing JSON stdout. With it, print only `mode`, `cost_status`, `timestamp_status` and `output_sha256` after a successful save.

- [x] Add `test_saved_evidence_hash_matches_bytes_and_refuses_overwrite`: save a synthetic result, assert byte hash matches the return, then expect `FileExistsError` and unchanged bytes on reuse. Add `test_invalid_json_never_creates_output`: NaN input raises before the file is opened.
- [x] Add CLI tests using the existing fake-SDK technique: complete capture then write once; failed broker capture produces no output file; write failure produces no success hash; stdout with `--output` omits the sample payload; stale sample remains stale. Do not require a real terminal or credentials.
- [x] Run `python -B -m unittest discover -s ops/trading -p 'test_batch2_evidence.py'`; expect missing helper/CLI support failures.
- [x] Implement serialization before exclusive open, `os.umask(0o077)` at CLI start, optional output and explicit error handling. Operator directory ACLs still matter on Windows; do not claim umask alone enforces Windows permissions. An I/O failure can leave an incomplete artifact: report failure and require a new output filename; never count it as captured evidence.
- [x] Run focused and full Python suites. Update README with container-side environment expansion, unique Windows home output paths, SHA verification and host backup permissions. Commit only probe/tests/runbook: `git commit -m "Save dated gold evidence without overwrite"`.

### Task 2: Verify session recovery and freeze the collection protocol

**Interfaces:** Reuse `verify-demo.py --login ... --server-offset-seconds ...`, `batch2-evidence.py`, `export-gold.py`, and `gold_costs.validate_profile(profile, start, end)`. No session prediction API or automated swap-charge test is added.

- [ ] With Algo off, read exact `XAUUSD-VIP` sessions from MT5 Specification and preserve the dated source privately. Record host UTC, terminal wall-clock convention and current offset. Generic public XAU hours are supporting context only.
- [x] Capture evidence before a documented close and after the documented reopening using distinct filenames. Run the verifier after reopening. Verify connected pinned demo, fresh quote and expected completed M15 bar. Record a failed result as a blocker; do not restart or trade to force a pass.
- [ ] Preserve probe/verifier outputs and SHA-256 values privately. A break-period stale quote is expected only when documented session evidence supports it. This check proves bounded session recovery, not historical DST or an actual funding settlement.
- [ ] Before future collection begins, create private `prospective-collection-manifest.json` with `schema_version=1`, `status="collecting_unqualified"`, creation UTC, future completed-bar start, baseline/code/policy hashes, exact symbol/timeframe, private source references/hashes, observed offset intervals, cost coverage intervals, and an explicit blockers list. Fields with missing evidence remain null or absent as documented, never guessed.
- [ ] Reserve a separate future holdout without reading its strategy results. Record missing observations and covered dates; use existing historical data only for labelled warmup/diagnostics. Boundary observations do not prove uninterrupted collection between them.
- [ ] Check that manifest creation precedes collection start, referenced hashes match saved bytes, and no current-rate interval extends beyond evidence. Commit only a sanitized protocol/checklist update, never the manifest or runtime payload: `git commit -m "Document prospective gold qualification protocol"`.

### Task 3: Evaluate evidence readiness and hand off the conditional baseline

**Interfaces:** Existing cost validator returns `{historical_coverage: bool, blockers: list}`. Existing simulator accepts `--cost-profile` and `--windows`; existing gate CLI retains its provenance cap. `compare-gold.py`'s old percentage manifest is not automatically a qualified prospective manifest.

- [x] Run `python -B -m unittest discover -s ops/trading -p 'test_gold_costs.py'`. Expected PASS; this checks software units, not broker coverage.
- [ ] Validate commission and swap profiles over each exact proposed window. Require sourced account applicability, effective intervals, verified rollover clock/event conversion and dated rates. Preserve `historical_coverage=False` if anything is uncovered. Do not manufacture a `verified_historical` status from daily snapshots or reuse another account's fee schedule.
- [ ] Confirm dated clock/session interpretation, 250-bar prior warmup and a pristine future validation protocol. Freeze three consecutive flat folds only when there are sufficient covered observed days; do not invent 60 days or 100 trades. Record policy minimum failures as inconclusive rather than weakening thresholds.
- [ ] If coverage is incomplete, append named blockers to the private manifest and sanitized handoff, retaining `prepared_but_blocked`; Task 3 ends with an honest readiness report, not a baseline qualification claim.
- [ ] If coverage is complete, specify a separate simulator-to-gate adapter plan using the real raw report schema, hash identities, UTC daily aggregation and exact folds. Preserve `simulator_provenance_unverified` until that implementation and its tamper/reconciliation tests pass. This deferred plan is required before using a real eligibility result.
- [ ] Only after that follow-up, rerun the fixed baseline twice with identical immutable inputs and distinct exclusive filenames, compare bytes and report code/data/cost/policy/window hashes. Keep previously inspected results diagnostic. Do not fabricate a candidate report or call Vibe-Trading in this plan.
- [x] Update `HANDOFF.md` with completed collection steps and remaining blockers; commit sanitized docs with `git commit -m "Record gold evidence readiness and remaining gates"`.

## Completion and self-review

Task 1 covers safe capture; Task 2 covers session recovery and prospective provenance; Task 3 covers honest evidence gates. Actual qualification depends on external evidence and adequate observations. A passing capture test or matched holiday gap never promotes a strategy. No private runtime data is embedded in these plans.

Execution note: Task 1 implementation and sanitized protocol are committed on main. Tasks 2/3 external evidence and qualification remain pending; documentation is preparation, not evidence of completion.

Wrap-up: the owner verified deployed exclusive output bytes and supplied a
current session specification crop, preserved privately. Cost validation still
returns uncovered. A private prospective draft is prepared, not started; no
start, validation windows or holdout was invented. See the [wrap-up verdict](2026-09-30-gold-batch2-wrap-up.md).

The owner subsequently supplied a saved passing M15 verifier summary. Bounded
recovery is complete for the observed before/after pair; reopening latency,
historical clock/cost coverage and uninterrupted collection are not inferred.
