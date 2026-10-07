# Batch 3 Offline Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve a small, non-sensitive failure classification from transport through worker to controller receipt, verified entirely with fake inputs.

**Architecture:** Extend the existing transport and proposal controller rather than adding a logging service. Successful payloads stay unchanged; failed worker responses use a strictly validated diagnostic envelope. Existing sealed runtime and consumed experiments remain untouched.

**Tech Stack:** Python standard library, unittest/unittest.mock, existing injected fake HTTP client and subprocess fixtures.

**Spec:** `docs/superpowers/plans/2026-10-06-batch3-one-proposal-outcome.md`, especially “Approval text correction and next offline milestone.” Foundation evidence: `docs/superpowers/plans/2026-10-07-trading-e2e-foundation-review.md`.

**Status:** PLAN ONLY. Owner explicitly selected planning on October 7, 2026. This document does not authorize implementation, model requests, resealing, deployment or another account-verification round.

## Global Constraints

- Preserve `stream=true`, `store=false`, model `gpt-5.6-sol`, reasoning `medium`, one POST, zero retries/fallback, no tools and no trade authority.
- Preserve approval/receipt binding, freshness checks, exclusive reservation, cleanup verification, and blocked promotion.
- Preserve unknown request outcomes after possible transfer. A failure stage is not proof that the provider received zero requests.
- No exception messages, response bodies, headers, tokens, prompts, account identities, arbitrary provider strings or process stderr in public diagnostics.
- No access to the real `.batch3-vibe` tree; no actual Docker, account, HTTP or broker operations in candidate tests.
- Do not edit historical authorization text or consumed receipts; do not reset, rename or reseal the failed experiment.

## Options considered

1. Controller stage only: smallest change, but HTTP refusal and stream validation would remain indistinguishable.
2. Bounded stage plus optional HTTP status through all three layers: recommended. Enough information to choose the next investigation without capturing sensitive messages.
3. Detailed provider/body/stderr logging: unnecessary and outside the allowed diagnostic contract.

Owner selected option 2 on October 7: failure stage plus HTTP status. Provider-code capture is optional in the existing milestone and is deferred; do not begin reading response bodies just to obtain it. This first version distinguishes stages, not every SSE parser rejection. A later version could add fixed stream refusal categories if coarse stages prove insufficient; it would still exclude provider/body/stderr logging.

## Review Focus

1. Secret-bearing exceptions must serialize only fixed classification fields (Task 1).
2. A malicious or malformed worker envelope must never be copied into a receipt (Task 2).
3. Worker crash/import failure may produce no envelope; preserve a coarse worker-stage failure rather than guessing HTTP outcome (Task 2).
4. Cleanup failure after successful transport must prevent success and retain independent cleanup evidence (Task 3).
5. Future approval text must describe the actual tested request, including streaming; historical records stay unchanged (Task 3).

## Files and scope

Modify only `ops/trading/supported_oauth_transport.py`, `ops/trading/gold_proposal.py`, their existing `test_supported_oauth_transport.py` / `test_gold_proposal.py`, and a short future approval checklist `docs/superpowers/plans/2026-10-07-batch3-future-request-review.md`.

Compatibility review: `supported_gateway.py` catches `ValueError` from `invoke_fake`; preserve that catch contract without changing its established fake response format. `parse_stream` is also tested directly; preserve its public signature and validation behavior. No dependency, database, UI or general logging abstraction is needed.

## Task 1: Classify transport failures without disclosing content

**Interfaces:** Add `DiagnosticFailure(ValueError)` and `validate_diagnostic(value: object) -> dict` in `supported_oauth_transport.py`. The exception owns an already validated `diagnostic` dict and uses a fixed generic message. Existing `invoke_fake`, `invoke_isolated`, `_invoke` and `parse_stream` signatures remain unchanged.

**Record contract:** Required `stage`, optional `http_status`; no other keys. Worker stages: `worker_initialization`, `http_request`, `http_response`, `response_stream`. Controller stages: `controller_pre_dispatch`, `worker_exchange`, `proposal_parse`, `artifact_write`. HTTP status must have exact type int (not bool), range 100–599, and be present only on `http_response` or `response_stream`, after headers were received. Records are capped at 256 UTF-8 JSON bytes. Unknown stage/key/type is rejected before serialization. Return a new dict containing validated fields rather than retaining the caller's mutable dict.

- [ ] Add `test_failure_diagnostics_are_bounded_and_redacted`: fake client construction/stream-open error -> `http_request`; non-200 or unacceptable content headers -> `http_response`; invalid/truncated/mismatched stream -> `response_stream`. Status is retained only after an actual fake response exposes a valid status.
- [ ] Include secret canaries in fake exceptions, body/header fields and invalid diagnostic values. Assert neither exception string nor serialized diagnostic contains the canaries; malformed records raise ValueError.
- [ ] Run the new test and confirm failure before implementing classification.
- [ ] In `_invoke`, track the fixed current stage and optional validated HTTP status, then raise `DiagnosticFailure` from None. Do not parse error bodies or exception text. Existing parser refusals are classified by stage, not by matching their message strings.
- [ ] Include fake connect, write and read timeout exceptions carrying canary request URLs. Record only the active stage/status; no timeout class establishes provider receipt, and none may change request counts. A status of 200 can accompany a stream failure and must not imply proposal success.
- [ ] Run `python -B -m unittest test_supported_oauth_transport` from `ops/trading`. Require existing exact request/one-POST tests and the new diagnostic tests to pass, with no network operations.

## Task 2: Carry the record through the worker boundary

**Interfaces:** Add `worker_entry() -> None` and `decode_worker_result(operation: str, returncode: int, stdout: bytes) -> dict` to `gold_proposal.py`. `worker_entry` calls the existing worker and is used by the fixed worker bootstrap. Successful output remains the current result object. Classified failure output is exactly `{"diagnostic": <validated record>}` with exit code 2. `decode_worker_result` returns a successful object or raises `DiagnosticFailure`; it never reads stderr. Apply this decoder to the existing `proposal` and `probes` exchanges; retain the separate `hold` termination protocol.

- [ ] Add `test_worker_failure_envelope_is_strict`: exercise worker initialization refusal and injected transport failure using fake stdin/stdout and patched dependencies. Require exit 2, valid bounded envelope, no exception text, and unchanged success shape.
- [ ] Add `test_worker_exchange_rejects_untrusted_diagnostics`: reject unknown fields/stages, bool/out-of-range statuses, oversized output, malformed JSON, diagnostic envelope paired with exit 0, success payload paired with nonzero exit, and empty crash output. Each becomes fixed `worker_exchange`, never copied raw.
- [ ] For a failure envelope, accept only worker-owned stages; reject controller stages forged by worker output. Accept HTTP stages only for the proposal operation; probe failures without an applicable proposal transport classification remain coarse worker failures.
- [ ] For exit-0 proposal results, require exactly `text`, `usage`, `model`, `reasoning_effort`, `promotion_status`; text is a bounded string, usage follows the existing parser's finite integer/total/details rules, model/effort/status match the pinned contract. Require an object of named true booleans for probes and retain the existing caller verification. Reject `[]`, `{}`, scalars, injected keys or a diagnostic-only object before counting a completed exchange. Reuse existing validation where possible; do not introduce a second parser or deserialize the strategy proposal in this credential-owning process.
- [ ] Run new tests to observe failure, then implement the two boundary functions. The existing nested `exchange` calls the decoder. Imports failing before `worker_entry` remain classifiable only as `worker_exchange`; do not promise unavailable initialization detail.
- [ ] Keep the existing output-size bound on all responses and enforce the smaller bound on diagnostic envelopes. Wrap unexpected worker exceptions as `worker_initialization` without retaining text.
- [ ] Run `python -B -m unittest test_gold_proposal test_supported_oauth_transport`. Existing approval, account binding, host refusal and replay tests must still pass. Use mocked subprocesses only.

## Task 3: Preserve receipt semantics and review the request contract

**Interfaces:** Existing `run(seal_sha, mode)` may add `failure_diagnostic` to a failed receipt after strict validation. Retain `failure_kind` (class only) and all existing outcome/cleanup fields; document the new `DiagnosticFailure` class if it appears there. Controller fallback stage is a local fixed variable: begin `controller_pre_dispatch`, move to `worker_exchange` immediately before proposal exchange, `proposal_parse` before parser creation and `artifact_write` before artifact saving. Never infer a stage from arbitrary exception text. Guardian cleanup fields retain their current producer contract and are not replaced by transport diagnostics.

- [ ] Add `test_controller_diagnostics_preserve_outcome_and_cleanup` with a fake filesystem root and mocked seal/ACL/auth/Docker/process/clock operations. Assert no real subprocess or socket call can escape the fixture.
- [ ] Cover classified worker failure, worker creation/crash without envelope, invalid stream, parser refusal after completed transport, artifact write refusal, and a valid negative cleanup receipt after success. Add a pre-dispatch configuration refusal: it keeps count 0 and reports `controller_pre_dispatch`. Assert that possible-transfer failures retain `model_requests='outcome_unknown'`; only a decoded, validated completed exchange can advance the existing counter to 1; cleanup failure always prevents a pass. Dispatch failure remains consumed; no second exchange or reservation reset.
- [ ] Inject missing/malformed cleanup metadata and failures before the existing receipt/try block. Require no success claim, preserve any partial artifacts, and report these as existing receipt-availability limitations. Adding diagnostics must not silently refactor reservation/guardian lifetime or promise a receipt on every I/O failure. A separate cleanup/reservation fix requires its own scope if the tests establish one.
- [ ] Run the new controller cases before adding the receipt field, then implement the minimal propagation. Preserve all original saved-attempt behavior, request counting and independent cleanup handling.
- [ ] Reuse the existing exact-request test, which already asserts model, reasoning, `stream=true`, `store=false`, one POST and absence of tool fields. Add only missing failure cases needed to prove no retry/fallback; do not add a test that merely compares two hard-coded approval strings or an automatic approval-text subsystem. Historical approval scripts remain unchanged.
- [ ] Write the short future-request checklist naming those exact fields and requiring comparison against the exact candidate snapshot's passing fixture before any future approval is drafted. This checklist is not a live authorization or a claim of automatic approval-text enforcement.
- [ ] Run the focused tests from Tasks 1–3 plus the existing compatible gateway tests after inspecting them for external operations. Any suite requiring protected source or live Docker remains owner-only or deferred, explicitly reported.
- [ ] Review the final diff for fixed allowlists, unchanged transport bounds/guards and no secret output. Preserve fake test outputs separately from historical production records. Stop at a reviewable candidate; no commit, deployment or resealing is required by this plan.

## Acceptance and handoff

Accept the diagnostic candidate only when fake failures remain useful across transport -> worker -> controller, secret canaries never appear, success payloads and request limits remain unchanged, unknown stays unknown, and cleanup failure cannot pass. This cannot recover missing details from the October 6 attempt or prove its cause.

After owner review of this plan, implementation can be authorized separately. Recommended execution approach: native, because the two source files share one small record contract and the existing fixtures provide focused checks. No agents or implementation started during planning.

## Self-review

All three source checkpoints are covered. HTTP/provider messages remain excluded; optional provider-code support is deliberately omitted. Startup failures before the worker wrapper retain a coarse classification. Approval wording is checked against future candidate fixtures, not retroactively changed. Existing production attempt, policy, qualification status and private access restrictions remain intact.

## Plan review — October 7, 2026

Reviewed all direct `invoke_fake` / `invoke_isolated` callers and the controller's `exchange` paths. Corrected ambiguous success decoding, status availability, per-producer stages and controller timing. Explicitly covered exit-0 diagnostic forgery and malformed successful output before request-count advancement. Reused the exact-request fixture rather than inventing a separate approval-string test. No code, tests, runtime or saved production artifacts changed during this review.

Context7 resolved the pinned HTTPX 0.28.1 documentation. Its streaming interface exposes response headers/status separately from raw body iteration, and its request exceptions carry request objects; neither exception text nor request attributes belong in this public record. Timeout type does not establish the provider's request outcome; preserving unknown remains a project rule.

Sources: [HTTPX 0.28.1 quickstart](https://github.com/encode/httpx/blob/0.28.1/docs/quickstart.md), [HTTPX 0.28.1 timeouts](https://github.com/encode/httpx/blob/0.28.1/docs/advanced/timeouts.md).
