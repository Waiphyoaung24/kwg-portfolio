# Batch 2 Real Report Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Reconcile real-format baseline CLI reports offline and create an honest prospective protocol draft.

**Architecture:** Reuse simulator, canonical hashes, cost validation and exclusive output. One stdlib adapter module; existing qualification cap remains intact.

**Tech Stack:** Python stdlib/unittest; no broker, provider, service or new dependency.

**Spec:** ../specs/2026-10-02-batch2-report-adapter.md

## Global constraints

Main; preserve unrelated work/private artifacts and current VPS collector.
No model request, real candidate, orders, restart, deployment or promotion.
Keep existing risk/policy hashes and unknown OAuth cost gate. UTC declaration
is not historical clock proof. Never count fixture days as observed days.

## Review focus

Changed report plus changed checksum must still fail recomputation.
Raw-epoch input must fail; no double offset subtraction on UTC curves.
Window/cost bytes and full baseline report metadata must match exactly.
Draft or stale source identities must never imply a frozen qualifying run.
Failures and existing output paths must preserve original bytes.

## Task 1: Protocol draft and baseline adapter

- [x] Add test for draft null dates/windows/holdout and blocked status.
- [x] Add fixture tests for CLI metadata, report tampering, UTC declaration,
  profile/window/hash mismatch, observed-day zero, UTC daily accounting and
  exclusive output.
- [x] Watch tests fail; implement ops/trading/batch2_adapter.py with
  protocol_draft(created_at), adapt_baseline(dataset_raw, windows_raw,
  costs_raw, report_raw, clock_raw, protocol), and safe offline CLI draft/adapt modes.
- [x] Rerun focused/full tests; create private synthetic-schema rehearsal.
- [x] Fresh review of scoped implementation; update HANDOFF and runbook.

Fresh review identified root-shape, boolean/number equality and overflowing
JSON-number gaps. Regressions failed before fixes and passed after; scoped
re-review found no remaining blockers. Actual simulator and adapter CLIs passed
against private synthetic inputs. No qualification, collector or dispatch began.

Ruling: prepare numerical reconciliation now because owner explicitly requested
it. Keep qualifying evidence/candidate adapter and evaluator-cap removal deferred;
source authenticity, normalized data provenance and observed-day completeness
cannot be established from a report hash or a current Specification screenshot.
