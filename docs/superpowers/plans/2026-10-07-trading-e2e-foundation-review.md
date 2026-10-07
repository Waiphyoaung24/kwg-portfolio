# Trading E2E Foundation Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish reproducible evidence for the offline trading pipeline and read-only learning-app browser flows without changing trading behavior.

**Architecture:** Reuse the existing Python rehearsal and boundary tests. Use TesterArmy e2e for browser assertions with no model provider; preserve the distinction between synthetic software checks, live inference, and strategy qualification.

**Tech Stack:** Python unittest, existing simulator/adapter/worker, TesterArmy e2e web engine, local Vibe-Trading UI.

**Spec:** User-selected scope: both offline pipeline and read-only browser review. Existing contracts: `docs/superpowers/specs/2026-10-01-gold-batch3-vibe-integration.md`, `docs/superpowers/plans/2026-10-02-batch2-batch3-handoff.md`, `docs/superpowers/plans/2026-10-06-batch3-one-proposal-outcome.md`.

## Global Constraints

- No product implementation or fixes in this review. New test scaffolding is a separately reviewable follow-up.
- No real model requests, broker actions, account verification, resealing, or replay of consumed attempts.
- The real `.batch3-vibe` directory is subject to a non-escalatable agent read denial. Do not copy, proxy, or relocate its contents to evade that restriction.
- Batch 2 remains closed for development, unqualified; promotion remains blocked.
- Preserve existing dirty work. Git fetch/pull have not succeeded; this is local checkout evidence.
- Browser review uses existing saved sessions only; no new chats, uploads, setting changes, or scheduled work.

## Final scoped acceptance — October 7, 2026, 15:03 Bangkok

Owner completed `trading-review-owner-02` with e2e 0.18.0. Agent read the saved `.e2e/trading-review-owner-02/report.json`: status passed, exitCode 0, two selected/executed/passed, zero failed/flaky/interrupted/skipped among selected tests, no run errors. Both passed on attempt 0 and cleanup completed. The generated example was discovered but not selected. Screenshot and trace artifact references are saved in the report; no agent/model steps are used by this suite.

Accepted scope: 34 offline foundation tests passed in the owner terminal; two deterministic browser tests verify saved arithmetic result, expanded tool trace, Reports empty state, return navigation, and zero authorized brokers/running runners. Earlier direct browser review also covered Settings and reload. No production implementation changed. Original failed reports remain preserved.

This completes the requested offline plus read-only browser foundation smoke. It does not establish fresh inference, report generation, production containment, strategy qualification, or a working autonomous improvement loop. The consumed real proposal failure remains unresolved; its next recorded milestone is offline safe diagnostics, requiring separate implementation scope. Git fetch/pull remains incomplete from the original request.

## Review Focus

1. Unavailable local server: report browser blocked, never a passing UI suite (Task 2).
2. Protected upstream source required by a synthetic test: report access blocker separately from an assertion failure (Task 1).
3. Historical successful account gates followed by failed dispatch: show both without implying current readiness (Task 3).
4. Synthetic profitability mistaken for qualification: assert explicit unqualified/blocked labels (Tasks 1 and 3).
5. Browser tooling triggering inference or sensitive actions: use deterministic locators only, no agent steps or submit actions (Task 2).

## Recorded execution — October 7, 2026 Bangkok

- Ran from `ops/trading`:
  `python -B -m unittest test_batch3_rehearsal test_real_development test_batch2_adapter test_gold_costs test_supported_oauth_transport test_gold_proposal`
- Result: 34 tests, 30 passed, 4 errors, exit 1; 32.599 seconds.
- Four errors: `test_auth_fixture_through_isolated_worker`, `test_complete_flow_is_repeatable_and_unqualified`, `test_fail_closed_limits_usage_tools_and_deadline`, `test_worker_success_usage_and_no_reuse` in `test_batch3_rehearsal.Batch3Test`.
- All four reach `batch3_runner.py:175`, where the synthetic runner reads the pinned upstream provider under the protected directory. No successful protected read occurred. No escalation or retry of these tests is permitted from this agent context.
- Browser navigation to `http://127.0.0.1:8899/` returned `net::ERR_CONNECTION_REFUSED`. No saved session or browser flow was reviewed live.
- `npx --yes e2e init --help` failed fetching the package with `ENOTFOUND registry.npmjs.org`; a bounded escalated attempt also failed. Initialization did not run and the requested package skill was not installed/read.
- Earlier same-chat saved-artifact review verified three byte hashes, the canonical manifest digest, six comparison CSV deltas/labels, and the redacted proposal outcome receipt hash. These are historical artifact checks, not a fresh full rehearsal.
- Verdict: foundation components have passing checks; complete E2E acceptance is BLOCKED, not passed. No conclusion of profitability or autonomous self-improvement.

## Owner follow-up and direct browser review — October 7, 2026 Bangkok

Supersedes the unavailable-server and owner-test blockers above; preserves their historical results.

- Owner supplied PowerShell output for the identical six-module command: all 34 tests passed in 47.269 seconds. This is owner-reported execution evidence, not a second agent-run test suite. Expected negative-path refusal messages appeared before the final OK.
- Owner `npm ping` returned PONG in 377 ms. Owner networking works; agent npm access has not been restored or reverified.
- Owner started the existing launcher on loopback port 8899. Startup reported 5/7 services ready; OKX DNS failed and optional Tushare was unconfigured. These do not prevent saved-session review, but crypto data-dependent E2E remains unverified.
- Agent directly verified browser root rendering and saved session `0edab1e6d735`. Saved response exactly matches 6 rows, sum 130, positive count 3, mean 21.67. Expanded trace showed four steps: Read document, Read file, Read document, Verify financial analysis.
- Reports navigation passed and showed 0 reports / No reports yet. No report-generation test was performed.
- Runtime navigation passed and showed 0 authorized brokers, 0 running runners. These are UI observations, not an independent broker/account audit. The Futu card displayed a Longbridge service error message: observed diagnostic-label inconsistency; cause unverified, no fix made.
- Settings navigation passed: OpenAI Codex, openai-codex/gpt-6.1-sol, medium reasoning, timeout 120, retries 0. Paid QVeris route was unchecked; channels were stopped. No settings changed and no model availability inferred from these settings alone.
- Browser back returned to Runtime, forward returned to Settings, and reloading the saved session preserved its exact answer. Browser interactions used the built-in browser automation, not TesterArmy e2e.
- Current verdict: selected offline foundation checks PASS by owner output; scoped read-only browser smoke PASS by direct observation. TesterArmy initializer/test suite remains pending. Real inference, fresh report generation, production containment and strategy qualification remain outside this completed smoke scope.

## Task 1: Complete offline foundation evidence in an authorized environment

### TesterArmy setup follow-up

Owner run `trading-review-owner-01` installed Chromium successfully and executed both tests; both failed. Review of saved trace and screenshot established two test defects: the trace toggle was already `aria-expanded=true` before the unconditional click, which collapsed it, and the runtime renders `AUTHORIZED` uppercase while the assertion expected `Authorized`. Corrected the test to open the trace only when collapsed, assert expanded state, and match the rendered uppercase authorization count with numeric boundaries. Product source remains unchanged.

Agent attempts `trading-review-20261007-02` and `-03` used the installed browser but both stopped at navigation with `ERR_NETWORK_ACCESS_DENIED`, including the escalated attempt. Those infrastructure failures do not validate the corrected assertions. Preserve all reports; next owner run uses a new output directory `trading-review-owner-02`.

Owner completed initialization/dependency installation. Installed runner is e2e 0.18.0; Node is 24.11.0. Read the generated project skill and setup/writing/running references. The generated config selected an OpenAI-compatible local endpoint; removed its model configuration for this no-inference review and changed the default app URL to port 8899. Added only `tests/trading-readonly.e2e.ts`, with two deterministic checks for the saved arithmetic session/trace/Reports/back navigation and Runtime's unauthorized/stopped state. No product source changed; initializer dependency/lockfile changes remain owner-generated.

Attempted `npx --no-install e2e run tests/trading-readonly.e2e.ts --workers 1 --retries 0 --output .e2e/trading-review-20261007-01` with telemetry disabled. Runner failed before test execution with `BROWSER_INSTALL_FAILED`: missing Chromium download could not resolve cdn.playwright.dev from the agent environment. No test assertions executed and no report was written. The earlier direct browser smoke and owner Python results remain valid within their respective scopes; the new automated suite is not yet verified. Owner can install Chromium using `npx @e2e-dev/web install chromium` and run the same focused command from repository root while the app remains running.

**Files:** Read existing `ops/trading/test_batch3_rehearsal.py`, `batch3_runner.py`, `test_real_development.py`, `test_batch2_adapter.py`, `test_gold_costs.py`, `test_supported_oauth_transport.py`, `test_gold_proposal.py`. Modify none.

**Interfaces:** Existing unittest modules consume synthetic fixtures; the rehearsal produces baseline/candidate/comparison JSON and CSV in exclusive temporary directories.

- [x] Run the selected six modules and classify all failures.
- [x] Identify the shared blocked dependency in `run_fixture`; retain the four errors as blocked coverage.
- [ ] Owner runs the same command in an independently authorized environment. This is not permission for this agent to read the protected directory.
- [ ] Require all 34 tests to pass, including repeatable complete flow, output reuse refusal, auth failure handling, tool/deadline limits, zero real model requests, and unqualified/blocked results.
- [ ] Preserve dated output and exact source revision. Do not substitute old successful receipts for the new result.

## Task 2: Initialize and run read-only browser E2E

**Files:** Future tool-generated test configuration and dependency changes must be inspected before acceptance. Intended test: `tests/trading-readonly.e2e.ts`; config: `e2e.config.ts`. No such files were created in this review.

**Interfaces:** Browser opens existing loopback app and saved synthetic session; assertions inspect visible content only. No trading or inference interface is called by a test action.

- [x] Identify `npx e2e init` as TesterArmy's framework initializer, not an existing local skill.
- [x] Attempt initializer help; record npm DNS failure.
- [ ] Once npm access is working, inspect the resolved package version/help and run the requested initializer. Choose web and no model provider. Review all generated dependency, skill, MCP and ignore-file changes; do not overwrite existing configuration blindly.
- [ ] Read the installed `.agents/skills/e2e/SKILL.md` before writing tests. Pin the reviewed version; do not assume current-main docs match it.
- [ ] Owner starts the existing app through its documented launcher outside this agent's denied private tree. Do not start duplicate servers or change its model configuration.
- [ ] Verify root UI renders and navigation to Agent/history, Reports, Runtime and Settings works without submitting forms.
- [ ] Open existing session `0edab1e6d735`; inspect the saved synthetic arithmetic answer and its trace. Expected arithmetic: 6 rows, sum 130, positive count 3, mean 21.67. Missing session is a failed prerequisite, not reason to create a replacement inference.
- [ ] Check back/forward navigation and reload preserve access to the saved session. Report any unavailable artifact rather than inventing one.
- [ ] Save sanitized browser results and screenshots; exclude credentials/account settings details. No claim of browser success until assertions actually execute.

## Task 3: Reconcile evidence and issue the foundation verdict

**Files:** Read `.superpowers/sdd/batch3-development-handoff-20261002-01/comparison.json`, `comparison.csv`, and `.superpowers/sdd/gold-proposal-metadata-20261006/review-result.json`; update only this review document if new evidence arrives.

**Interfaces:** Saved public receipts plus fresh test results produce a matrix of pass/fail/blocked checks with scope and date.

- [x] Keep synthetic validation P&L deltas distinct from strategy improvement: lower -413.10, middle -412.35, stress -409.35 USD versus baseline.
- [x] Preserve real proposal outcome: failed, request count unknown, cleanup verified, proposal/usage artifacts absent.
- [ ] Reconcile fresh offline and browser evidence without converting a historical account check into present authorization.
- [ ] Report separate verdicts for software foundation, production containment, real inference, strategy qualification and self-improvement. No overall green verdict while required E2E coverage remains blocked.

## Self-review

Both requested surfaces are covered; no new provider, service, trading behavior or qualification shortcut is proposed. Task 1 depends on an existing protected upstream installation; Task 2 depends on npm reachability and a running app. Those are explicit blockers, not implementation defects established by this run. Browser test APIs/locators must be grounded in installed docs and actual UI before implementation.

References: https://github.com/tester-army/e2e ; local `ops/trading/VIBE-LEARNING.md`.
