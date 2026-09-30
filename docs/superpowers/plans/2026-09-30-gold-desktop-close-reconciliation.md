# Gold Desktop Close Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task with the previously selected native execution method. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Reconcile a fully verified desktop-origin close without treating it as an SL/TP exit or sending another order.

**Architecture:** Keep the existing journal and broker identity matching. Add one close-origin classifier at the shared reconciliation boundary; reuse the current status projection and generated standalone page.

**Tech Stack:** Python stdlib/unittest, existing SQLite and MT5 SDK; existing Astro/JavaScript tests. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-30-gold-batch2-continuation.md`, Milestone A.

## Global Constraints

- Demo-only `XAUUSD-VIP`; no new order, cancellation, protection edit or timer.
- Desktop closes only; `close_reason="manual desktop"`; volume tolerance `1e-8`.
- Fast manual exits before a protected position was observed remain `needs_attention`.
- Private runtime reports stay outside Git. Existing policy, holdout, risks and qualification status remain unchanged.
- Read `DESIGN.md` and `PRODUCT.md` before any page markup/style work; this plan changes guidance only.

## Review Focus

- A matching desktop exit with magic 0 must be accepted through position identity, not rejected by exit magic.
- Missing history (`None`), another gold exposure or mixed close origins must never become a successful close.
- Partial/duplicate deals must not masquerade as complete volume closure.
- Finite individual amounts can overflow in aggregate; reject a nonfinite total.
- Restart reconciliation must preserve prior rows and never resend an entry.

## File map

Modify `ops/trading/demo_one_shot.py`, `ops/trading/test_demo_one_shot.py`, `src/scripts/trading-status.mjs`, `src/scripts/trading-status.test.mjs`, generated `ops/trading/trading.html`, and `ops/trading/README.md`. No schema migration, controller/Worker API change, new button or service.

### Task 1: Match and classify the complete close

**Interfaces:** Consume `_broker_state(mt5, row, now, login)` and `_close_evidence(deals, ticket, request, mt5)` unchanged at call sites. Add `_observed_exit_reason(mt5, deals, ticket, expected_volume) -> str | None`: preserve protective classification, otherwise allow only the spec's verified desktop close. `_reconcile(mt5, db, row, now)` calls it only in the already-observed entry-phase branch. `_historical_protection` stays protective-only.

- [x] Update `fake_mt5` to declare `DEAL_REASON_CLIENT=0`. Replace `test_manual_early_close_after_observed_position_needs_attention` with a realistic unique-ticket fixture and `test_manual_desktop_close_after_observed_position_is_reconciled`.
- [x] Assert `status == "closed"`, `close_reason == "manual desktop"`, complete `.01` volume, correctly offset UTC close time, and net `-.70` for synthetic profit `-.20` plus entry commission `-.10`, exit commission `-.20`, swap `-.15`, fee `-.05`. Assert repeated `process_once(..., allow_entry=False)` gives identical close fields and does not increase `order_send` call count.
- [x] Add focused failure cases using the existing fixture: partial exit `.005` of `.01`, duplicate positive deal tickets, missing ticket, mobile/web/unknown or mixed CLIENT/SL exit reasons, history `None`, wrong position identity, another gold position/order, missing amount, NaN and cumulative overflow. Each must assert `needs_attention` and zero additional sends. Fully closing multiple unique CLIENT exit fills must pass.
- [x] Run `python -B -m unittest discover -s ops/trading -p 'test_demo_one_shot.py'`. Expect the new positive desktop case to fail under the existing rejection rule.
- [x] Implement the classifier with existing matching anchors; require desktop evidence to match the recorded observed volume and unique deal identities. Do not require manual exit magic to equal entry magic. Add a finite-total check in `_close_evidence`; do not introduce another state machine.
- [x] Rerun focused tests. Existing SL/TP, timed-history, fast-unobserved-close, wrong-account, no-resend and unrelated-position tests must still pass.
- [x] Run `python -B -m unittest discover -s ops/trading -p 'test_*.py'` and `git diff --check`. Commit only the runner/test changes: `git commit -m "Reconcile verified MT5 desktop closes"`.

### Task 2: Project the reason and prepare deployment

**Interfaces:** Consume the existing snapshot's `status`, `close_reason`, `closed_at` and `realized_net_usd`. Preserve `executionFields(execution, now)` return shape. Do not expose tickets, account identity or raw history.

- [x] In `src/scripts/trading-status.test.mjs`, assert the desktop closed fixture gives `state === "Closed"`, the expected net result and exact guidance `Closed from MT5 desktop. This is a historical result.` Assert ordinary SL/TP closed guidance remains unchanged and expired active reports remain Unknown.
- [x] Run `node src/scripts/trading-status.test.mjs`; expect the exact desktop guidance assertion to fail.
- [x] Add the single desktop-close guidance branch in `executionFields`; leave layout, status delivery, entry controls and Worker routes unchanged.
- [x] Run the Node test, `npm run build`, and `node ops/trading/build-status-page.mjs`. Review the generated HTML diff; it must contain the new guidance without unrelated page changes. Do not edit generated HTML manually.
- [x] Update README with the new supported close origin and a rollout checklist: backup the journal using SQLite backup, verify no unresolved gold exposure, review source hashes, coordinate the controller's existing journal lock before a bounded `resume`, and validate the existing attempt without arming a new one. Never run a second long-lived resume while the control loop holds its lock.
- [ ] Keep source and image in sync after separately authorized deployment; verify the authenticated page and private snapshot agree. Do not restart the desktop during an unresolved position. If only runtime copies were updated, mark image/source synchronization pending rather than claiming durable rollout.
- [x] Verify `git diff --check`; commit the projection, generated artifact and runbook with `git commit -m "Display verified desktop close results"`. A deployed runtime check is pending until the owner runs it; tests alone do not prove broker reconciliation.

## Completion and self-review

Every Milestone A rule maps to Task 1 guards or Task 2 projection/deployment. The native implementation is complete only after tests pass; live rollout is a separate reviewed step. Reconciliation does not complete Batch 2 qualification or authorize another attempt.

Execution note: native implementation committed on main. Tests, Astro check/build and generated artifact verified; live rollout remains pending. Related changes were grouped in two commits rather than the suggested per-task messages.
