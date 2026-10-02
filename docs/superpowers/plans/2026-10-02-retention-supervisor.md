# Retention Supervisor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for task execution.

**Goal:** Implement a bounded local-rehearsable supervisor and segment integrity/overlap review.

**Spec:** ../specs/2026-10-02-sustained-observation.md

**Architecture:** One Python stdlib module and fake-process tests. Reuse the
capture CLI unchanged. At most two overlapping followers; a fixed total deadline
and explicit disk reserve; no service installation, retries, broker calls or
collector changes. Evidence remains unqualified regardless of software success.

## Task 1

- [x] Write failing checks for healthy overlap, conflicts, boundary gaps,
  tampered receipts, stale writer, process failure and low disk refusal.
- [x] Implement segment review and bounded supervision with injectable fake
  launch/clock/space functions; fsynced private event log and exclusive outputs.
- [x] Run focused/full tests and offline two/three-segment rehearsals.
- [x] Fresh scoped review; fix findings and update runbook/handoff.

No actual VPS supervisor or capture starts. Keep schedule dates unset. Disjoint
segments or failed capture boundaries must never be silently treated as complete.
Limits bound retained output; preserve partial artifacts, stop only owned follower
processes, and never install automatic restart or delete evidence.
