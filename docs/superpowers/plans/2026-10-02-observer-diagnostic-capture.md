# Observer Diagnostic Capture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prepare a bounded, read-only follower of existing Docker observer output.

**Architecture:** Python stdlib, existing wrapped JSON parser, exclusive private
directory, fsynced JSONL and a final byte-hash receipt. Capture selected numeric
health fields and categorical states; free text becomes a hash. Never retain
mixed container logs, credentials or arbitrary fields. No collector changes.

**Scope:** Local implementation and fake-input checks only. No VPS deployment or
capture start. Capture earns zero observed days and never qualifies a strategy.

## Task 1: Bounded diagnostic capture

- [x] Test wrapped blocked/duplicate samples, secret exclusion, gaps and limits.
- [x] Watch missing implementation fail; implement capture-observer.py with
  synthetic file mode and a fixed docker logs --follow --since route.
- [x] Bound runtime, input frames and output bytes; record disconnect/timeout,
  ignored frames and sample gaps. No retries or silent resume. Exclusive writes
  with private POSIX modes, flush/fsync and failure preservation.
- [x] Run focused/full checks, fake CLI rehearsal and fresh scoped review.
- [x] Document source/container checks, local-file transfer and future supervised
  start commands without executing them. Update handoff and ledger.

Selected-field diagnostics support gap review, not complete raw-log retention.
Fatal non-JSON observer errors remain unknown text hashes and stream termination;
capture limits or malformed frames invalidate completeness. Existing journals
and source exports still need independent preservation. Future manifest records
the actual capture start; late attachment cannot recover already rotated logs.
