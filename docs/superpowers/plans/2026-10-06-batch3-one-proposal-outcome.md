# Approved proposal attempt — consumed outcome unknown

Current status: stop dispatch and preserve this experiment. The single approved
owner workflow ran; account/provider/actual CLI checks passed, then the sealed
proposal controller returned `passed=false`, `dispatch_status=consumed_outcome_unknown`,
`model_requests=outcome_unknown`, and **`cleanup_verified=true`**. This does not
prove zero requests or a successful proposal. No retry, fallback, reset or retiming.

## Saved metadata review completed

Owner gold-proposal-metadata-20261006 review passed exact consumed approval/receipt
bindings. Actual approval timestamp is `1791282363`; controller receipt SHA is
`158b155e4b8c70420a84f435002ae0cf1ca7c08f38db8041b50d2baf28cc8896`.
Public review-result SHA independently checked:
`4c2ad83b25364036a1c2c9307e60cc9684acd941a1c93217dfffc67fb5faca38`.
Saved receipt has `failure_kind=ValueError`, unknown request count, cleanup true,
guardian exit0. Saved independent cleanup confirms cleanup true. started/finished/
cleanup markers exist; **proposal.json and usage.json do not exist**. No request
was repeated, resources modified or credential contents read by this diagnostic.
Preserve its review-result.json; do not run either inspector again.

Public controller code sets the unknown marker before entering the proposal worker
exchange and changes it to1 only after a successful exchange. Thus the saved
receipt places failure before a validated worker response returned; it does not
prove whether the POST reached the provider. The separate credential-free proposal
parser follows that successful exchange and was not reached according to this
counter path. Container configuration refusal, worker input/runtime checks, HTTP
failure and response-stream validation can all cause this broad failure. Do not
select a cause without evidence.

The transport wraps exceptions in generic ValueError, the worker exits2 without
exception details, and the controller saves only exception class. HTTP status,
safe provider failure code and precise worker stage were not retained. Further
read-only inspection cannot reconstruct those absent details; do not request
another account/browser/CLI cycle to investigate this consumed outcome.

### Approval text correction and next offline milestone

The owner review text prepared by the assistant incorrectly said stream/store
false. The actual unchanged sealed request and its fixture are **stream=true,
store=false**, using SSE. Original start.ps1 and authorization records remain
preserved; this correction does not retroactively rewrite the approved scope.
There is no evidence that this documentation error caused the ValueError.

One existing fake-only request test was run to verify the exact request payload,
one-POST/no-retry behavior and generic failures; it passed. No live API, Docker,
account or private-file operation ran in that test. Runtime source/seals remain
unchanged. No further model request is authorized.

Next milestone is an **offline diagnostic candidate**, before any future live plan:

1. Reuse the fake HTTP harness to retain bounded, allowlisted failure stage and
   optional HTTP status/provider code. Keep exception messages, response bodies,
   headers, tokens, prompts, account identities and arbitrary provider strings out
   of output. Unknown request outcome must stay unknown after possible transfer.
2. Carry that safe classification through worker/controller receipts. Test HTTP
   refusal, stream truncation/identity/usage refusal, worker initialization failure,
   and cleanup failure without live requests. Preserve one-POST, no retry/fallback,
   credential/network isolation and existing replay guards.
3. Check future human approval text against the tested actual request contract,
   including stream=true/store=false. Prepare a concrete patch for review, not a
   change to this consumed snapshot.

Do not reseal, rename, delete or reset this consumed experiment to permit retry.
Any future live work requires a separately reviewed plan and explicit approval;
neither a diagnostic patch nor this checkpoint authorizes it.

## Verified public evidence

All files remain in `.superpowers/sdd/gold-one-proposal-20261006`:

- Fresh browser account was visibly `nexuslab.dev.mm@gmail.com`; owner correlated
  its email hash with the same signed registration.
- Provider controls genuinely observed `2026-10-06T10:27:26.577Z`: Gold plan usage
  on at 100%, app credit usage off, auto reload off, Save disabled; followed
  Manage usage from the Gold connection. No setting was changed.
- Account ID `bda965d0f493416c8fffa374f8964a44` consumed successful; accepted
  `1791282475` (17:27:55 Bangkok), `gpt-5.6-sol` present, same signed account/
  client/host and cleanup verified; no renewal needed. Exact account receipt SHA:
  `49db5f028acbb830e65556acc31236831b576b23ce429b17300295288590d3ba`.
- Actual CLI proof checked `1791282480` (17:28:00 Bangkok), PID27448/TID25012,
  exact native runner PID18240 and Codex PID23084. Effective restricted token;
  registration/canary opens denied, source open and workspace write allowed.
  Coding receipt SHA `0f30c66ab78dd8b22bb774b1e41348f01d0df948f3b28d901bde76db39ae368a`.
- `combined-result.json` passed exact fresh account/provider/coding bindings and
  billing ceiling. This audit itself has zero model requests and no gate writes.
- Owner continuation then wrote the exact canonical gates and launched the
  controller, as shown by `dispatch-started.json` and the matching sealed dispatch
  receipt in `dispatch-result.json`. The outer wrapper's redacted result omits
  the private controller failure type. Do not guess the cause from that omission.

HEAD `18620b96eb05eeef86dcea52acf3e00cb1c09e6c`, account/proposal seals and intent
remain unchanged. All historical receipts and earlier refusals are preserved.
The agent never read the real private tree or credential bytes. Proposal success,
usage metadata and exact failure type are not yet independently reviewed.

## Historical: manual saved-metadata review (now complete)

Current diagnostic: `.superpowers/sdd/gold-proposal-metadata-20261006/inspect.ps1`.
Run in owner PowerShell:

```powershell
& 'C:\Users\wai19\Desktop\kwg-portfolio\.superpowers\sdd\gold-proposal-metadata-20261006\inspect.ps1'
```

It checks unchanged source and exact intent/consumed approval bindings, reads only
saved intent/receipt/cleanup/approval metadata, and checks artifact presence. It
prints safe failure/cleanup fields and saves a public redacted `review-result.json`.
No account verification, token renewal, network/model request, Docker operation,
proposal contents, credential contents or modification of historical records.

Pure redaction and full synthetic continuation tests pass: unknown counts stay
unknown, secrets/messages are omitted, all attempt bytes preserved, and only the
mocked git source check runs. Owner diagnostic main has not been run by the agent.
The manual step is required by the non-escalatable denial of real `.batch3-vibe`
reads. Share its redacted result; do not rerun `start.ps1` or account verification.

### Original metadata inspector refused; producer contract corrected

Owner ran gold-proposal-outcome-20261006/inspect.ps1. It refused with ValueError
in the broad `exact_consumed_experiment` phase, without requests or resource
changes. Original source/pins remain unchanged; the supplied refusal is saved as
`owner-refusal.json` in that original folder. No successful review result exists.

Public source reveals an inspector mismatch: `reserve_production` verifies the
protected production registry and creates its child with mkdir. The original
inspector applied `private_acl` to that child, requiring directory inheritance
protection the producer does not establish. A synthetic inherited-child regression
reproduced this refusal before the fix and passes after it. This explains a real
inspector defect; the owner's broad phase alone does not confirm its precise
native failure or the separate model-request failure.

The new diagnostic applies the unchanged strict directory ACL validator to the
protected registry, rejects reparse points at the child, and retains unchanged
strict private-file ACL validation for each metadata read. No ACL is modified,
no inference guard relaxed, and no sealed/runtime code changed. A negative unsafe-
registry test still stops before receipt/approval reads. Narrow phases now identify
intent read/digest, experiment ID, registry ACL, child reparse, receipt read/binding,
approval read/binding or cleanup/presence failure without exposing exception text.
The new diagnostic was prepared/tested and has now completed the owner review
reported above; it only reviewed the existing consumed attempt and does not
authorize another request. The original failed inspector source remains preserved.

Batch 2 qualification and trading/promotion remain deferred and blocked. The
original hook warning remains unconfirmed; no hooks or MCP credentials changed.
