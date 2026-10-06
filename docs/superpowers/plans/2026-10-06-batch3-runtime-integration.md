# Batch 3 diagnostic runtime integration implementation plan

> **For agentic workers:** Use superpowers:executing-plans only after the owner separately authorizes the relevant implementation phase. Checkboxes and future steps below provide no dispatch authorization.

**Goal:** Integrate the pinned diagnostic contract with the supported gold runtime while preserving seals, consumed attempts, request limits and human approval.

**Architecture:** Apply the existing patch to reviewed public source in a separate clean worktree. Treat the account and proposal source families as a matched pair; preserve existing sealed copies. Reuse the current worker, parser, guardian, manifest verifier and experiment registry.

**Tech Stack:** Windows, Python 3.12+, Git, existing standard-library unittest checks. The prospective runtime keeps its existing images and HTTPX 0.28.1/httpcore 1.0.9/certifi 2026.5.20 pins; no installation or service change is part of preparation.

**Spec:** [Batch 3 specification](../specs/2026-10-01-gold-batch3-vibe-integration.md).
**Prior review:** [Pinned diagnostic candidate](2026-10-06-batch3-diagnostic-review.md).

## Current result and authorization

Prepared on `codex/batch3-preparation-reconcile`, starting at
`2d44eb988e219eb8b396e8d28a34ab4d19b443ab`. Runtime patch application is confined
to disposable public-source exports. **19 fake checks pass**, including five new
compatibility checks. Reverse application restores every exported file byte and
removes the added diagnostic test. No sealed runtime, private tree, production registry, collector or VPS service
was inspected or changed. Original checkout access was read-only.

This plan and added verification are ready for review. Source integration,
creation of any new private snapshot and any native/account verification require
separate authorization. No current approval authorizes a model request. Batch 2
remains closed for development and unqualified; its evidence program is deferred.

## Global constraints

- Preserve the consumed attempt, its experiment identity, approvals, seals,
  started/finished/cleanup markers and all absent/unknown outcome facts. Never
  rename, reset, reseal or retime that experiment to permit another attempt.
- One POST to public Responses; gpt-5.6-sol, medium, stream=true/store=false;
  zero retries/fallback/tools, USD0 additional spend and blocked promotion.
- Keep proposal 16,384 bytes, stream 262,144 bytes, event 65,536 bytes, stream
  processing 120 seconds and controller deadline 180 seconds. Local closure
  is not proof of backend cancellation, zero requests or bounded billed usage.
- XAUUSD-VIP completed M15; EMA20/EMA50/ATR14; entry risk 0.1% equity,
  stop 2 ATR, target 3 ATR, 1% daily entry pause, one position, no same-bar reversal.
- Risk hash `865e46d493db5939e9e3d98375ce727664d57c03bc42a06e548cace61a8e6ce7`;
  policy hash `39eb8759133ac1ca50308e0aa053c761a53b24e94be9ebc3f8c13ff73413873d`.
- No merge, inference, scheduler, order, MT5 restart, journal reset or VPS operation.
  Preserve the smoke collector and `/root/kwg-gold-research/evidence/smoke-20260930T164651Z`.

## Integration decision and exact source changes

| Approach | Consequence | Decision |
| --- | --- | --- |
| Edit an existing seal | Manifest/source identity fails; overwrites historical evidence | Rejected |
| Import the whole supported branch into main | Includes unrelated runtime work and dirty-checkout risk | Excluded from this task |
| Apply pinned diff to separate public source, then review matched snapshot families | Small existing change; preserves old evidence; still needs later owner gates | Selected for planning and fake rehearsal |

The source base is `18620b96eb05eeef86dcea52acf3e00cb1c09e6c`. The exact
[patch](../../../ops/trading/patches/2026-10-06-proposal-diagnostics.patch) is already
published in preparation commit `2d44eb9`; it is unchanged by this review.
Patch SHA-256: `0a7958e1043ca4d077e0dd8a9c263336e137d64e2d80cf316e9d8791b8de59ad`.
Different source bytes require a new reviewed diff; do not force or fuzz this one.

| Public source path under ops/trading | Exact change | Patched SHA-256 |
| --- | --- | --- |
| supported_oauth_transport.py | ProposalFailure/checked_failure, shared request_body, safe stream/HTTP classification | `bd2ca3f1c2952003a1ab1c9ba84fc1bef2699f375f28bfe1ec6b0a6bf19bf73e` |
| gold_proposal.py | Worker envelope, strict decoder, safe receipt and separate cleanup failure, request_review hash approval gate | `8195b6ae0e6ad01a3790e901a042cdc0d039629087df981b90ba0de7a700ee85` |
| test_supported_oauth_transport.py | Existing limit assertion follows fixed diagnostic label | `dbee602a8dc6101e75505d096136fa57048eae1cd360b3c314c27f947582e023` |
| test_gold_proposal.py | Valid fake approvals include request_review_sha256 | `c557da3abb7a5b580c22ff5852af2275a9d39870f5cb8e2232218a2d79a8569c` |
| test_proposal_diagnostics.py | New fake HTTP/worker/controller/approval checks | `5a9b1afb829228fb4eec7a2d052af592dbd9870a4fe46fbd2c11303d3962aac4` |

All hashes describe Git-exported LF bytes, not console output or a converted copy.
No changes to gold_account.py, supported_gateway.py, harden-batch3.ps1, risk,
policy, evaluator, images, proxy ACLs, billing limits or registration are needed
by the pinned diff. Neither FILES nor PARSER_FILES needs a new runtime module.

## Runtime dependency and approval review

`gold_proposal.FILES` includes `gold_account.FILES`; both include the transport.
`supported_gateway.CODE_FILES` and its credential-free `PARSER_FILES` also include
that transport. Proposal workers therefore need both changed source modules;
supported fake workers and account workers pick up the new transport while their
request routes, policies and no-inference boundaries stay unchanged. ProposalFailure
is a ValueError subclass, so the existing supported fake worker's failure handling
continues to refuse. Its fake receipt remains generic; production diagnostics
travel through gold_proposal's new envelope instead.

`dispatch_prerequisites` locates `sealed-account-<same suffix as proposal>` and
compares every ACCOUNT_FILES byte with the proposal copy. A patched proposal
paired with an old account copy refuses before reading the account receipt.
The fixture test executes this real verifier and comparison. Matching copies
demonstrate source compatibility only: its fake billing/native records establish
no production acceptance. Billing is checked before shared-source comparison;
signed account acceptance and request transfer happen later in run().

`verify_seal` binds manifest bytes, every listed source hash and the exact file set.
Changing an old code file fails its existing seal hash; merely regenerating its
manifest still fails the old expected hash. Extra review/test files cannot be
inserted into a seal after creation. A future approved integration therefore
requires separate new matching snapshots from the same reviewed source commit,
with new manifest hashes. It must preserve every old snapshot.

The current sealer names supported/account/proposal snapshots by that source
commit's first 12 characters. It copies all tracked top-level .py/.json/.patch/.ps1
files, frozen legacy fixtures and an upstream-provider copy. The proposal phase
also calls prepare_inputs, which binds the existing private development packet.
The helper changes ACLs and accesses private inputs; it is not an offline checker.
Do not run it here, transplant its outputs or replace missing frozen inputs.
Its broad copy rules mean tests/tooling also influence manifest hashes.

The pinned patch deliberately does **not** change PREPARATION_SHA, PACKET_SHA,
PROMPT_SHA, baseline or experiment hashes. The old packet's production reservation
therefore remains consumed even under a different source/seal. This plan does not
make that packet launchable. Preparing a genuinely distinct future experiment
requires its own scope, input/provenance review and authorization; changing an ID
solely to evade reservation is forbidden.

### Exact future approval contract

`request_review()` derives the displayed request fields from `request_body('')`,
removing only input. UTF-8 encoding without BOM, LF newlines and one trailing LF
has SHA-256 `1358b7a8531287bb196d0ccccf44d31fad68040be924e0d1da4577178bc808c3`.
That hash covers method/URL, model/effort, stream/store, local bounds, one POST,
zero retries/tools/trade authority and USD0. Existing intent/seal hashes continue
to bind the actual prompt/packet; the review hash is not a replacement for them.

The exact approval fields are mode, seal_sha256, intent_sha256, approved_at,
expires_at, one_proposal_authorized, additional_spend_usd, account_seal_sha256,
account_verification_id, account_receipt_sha256 and **request_review_sha256**.
No extras, inferred consent, migrated timestamps or default review hashes are valid.
Freshness remains at most 1,800 seconds, with the existing future-time tolerance;
account/billing/coding proofs remain governed by their existing checks.

The historical owner coordinator lives in
`.superpowers/sdd/gold-one-proposal-20261006/start.ps1`, outside the pinned source
commit. Its public workflow record describes an old-schema writer. Its source was
not opened or executed in this review. It cannot be certified compatible here.
A future separately reviewed coordinator must render the runtime-generated review,
require explicit human approval of those bytes, record the existing human timestamp,
hash the exact UTF-8 review bytes and write the eleven-field approval once, last,
bound to the new seal/intent and exact fresh account receipt. It must stop on old,
missing or mismatched fields; never auto-fill an old approval or rewrite the original.
Do not hash a Windows console transcript: print/PowerShell may change newlines or BOM.
No new executable owner helper or real approval file is prepared in this task.

## Review focus

1. Old/new source mixtures: fake matching and mismatching account copies exercise the real manifest verifier and source equality gate.
2. Old/wrong approval schema: refusal occurs after only the approval read, before follow-up private IO, verification or reservation.
3. Failure patch breaks successful parsing: fake transport success passes worker decoding into the real credential-free parser.
4. Policy/authority drift: compare proposal/account/gateway policies before and after patch in isolated imports; test import-file closure and blocked flags.
5. Rollback changes bytes or leaves an added file: reverse-check/apply and compare the entire exported tree byte-for-byte, including removal of the added test.

## Task 1: Public-source integration rehearsal - complete

**Files:** the five-file pinned patch; [checker](../../../ops/trading/check-proposal-diagnostic-patch.py);
[compatibility tests](../../../ops/trading/diagnostic-tests/test_proposal_runtime_integration.py).
**Interfaces:** consumes the pinned local Git commit and diff; produces fake
verification only. Existing APIs are checked_failure(value), request_body(prompt),
request_review(), decode_worker_response(returncode, raw), approval_gate(...),
dispatch_prerequisites(...), verify_seal(root, expected) and reserve_production(...).

- [x] Export the pinned public source, record its bytes/policies, check and apply
  exactly the five-file patch in the disposable export.
- [x] Exercise the five review-focus cases above alongside the existing 14 tests.
- [x] Reverse-check and reverse-apply the patch; require equality of all exported
  file bytes and paths with the before snapshot. A failure stops the checker.

From the preparation repository root:

```powershell
python -B ops/trading/check-proposal-diagnostic-patch.py
```

Expected: 19 unittest cases pass, exact reverse restoration passes. Requires the
base commit locally; no fetch/install. The checker creates a disposable Git
repository so ops/trading/.gitattributes enforces LF; the first attempt outside
a Git repository passed 19 tests but failed exact reversal due to LF->CRLF
conversion in four files. The corrected check passed without configuration,
hook or whitespace-check overrides. This is concrete rollback evidence, not a
claim that unapproved native/runtime operations were exercised.

Tests use real manifest/source/schema/parser/reservation logic where applicable;
private/native/HTTP boundaries are fake. Audit guards refuse sockets, real child
processes and .batch3-vibe opens in the test process. Parent-process Git commands
are limited to export/init/apply in the disposable tree. Guards are not production
containment proof. The prior 39 baseline checks and risk/policy hashes remain
historical evidence from the preceding review; they were not rerun in this task.

## Task 2: Future integration - requires separate approval

**Files:** both changed runtime modules and the patch tests in a new clean public
source worktree; any newly reviewed owner coordinator outside the consumed workflow.
**Interfaces:** produces one reviewed source commit, exact prospective snapshot
hashes and an eleven-field human approval contract; consumes no old authorization.

- [ ] Obtain approval for public-source integration; verify base/patch/file hashes
  and clean scope. Apply both runtime files together; review the resulting source
  and rerun Task 1. Commit with normal hooks. Do not merge under this plan.
- [ ] Review the future coordinator's actual source. Add fake tests showing absent
  human approval invokes nothing; exact runtime review bytes and hash are used;
  wrong/old schema refuses; receipts/IDs/time are bound and files are exclusive.
  Watch those tests fail before implementing that coordinator change.
- [ ] Only after explicit private-snapshot authorization, prepare separately named
  matching source snapshots with blocked readiness flags. Confirm code closure,
  new manifests and byte equality. Preserve partial failure outputs; never repair
  a consumed snapshot in place. The current packet remains unlaunchable.
- [ ] Separately approve and verify native isolation, forced cleanup, real coding
  credential denial, account/model acceptance and saved applicable USD0 controls
  for the prospective exact runtime. Fake tests or old receipts cannot satisfy them.
- [ ] Any inference needs its own approved distinct experiment plan and fresh
  exact approval. No launch command, new experiment ID or launch date is supplied here.

Expected: each missing gate refuses before its prohibited operation; a source
integration commit or new manifest alone never changes promotion/dispatch authority.

## Rollback procedure

**Preparation rollback:** no runtime was changed. Keep this review and the pinned
artifact for audit; simply decline integration. A reversal rehearsal is already
available through Task 1 and only mutates its own disposable public export.

**Public-source rollback after a future approved application:** stop that integration
before snapshot selection. In its separate clean source worktree, review and revert
the dedicated application commit with normal Git hooks, rather than resetting a
branch or overwriting uncommitted work. Require the previous committed source/file
hashes and rerun the fake checker on the pinned candidate separately. Use the
repository's LF attributes; semantic similarity or CRLF conversion is insufficient
for a hash-bound source restoration. Do not reverse-apply into any sealed code tree.

**If new snapshots have been created:** retain them and all partial/failed proof
files; record the candidate as retired/blocked in a separate reviewed decision
record. Stop using the candidate selector/launcher under a separately authorized
owner procedure. Do not rename/delete/edit seals or create an executable switch to
the old runtime here. Reverting public source does not roll back private snapshots,
provider settings, renewed credentials, receipts or an experiment reservation.

**After any possible request transfer:** preserve unknown request/usage outcome
and the exclusive marker. Stop. Cleanup uses the existing independently owned
resources and guardian; an unverified cleanup requires separate owner investigation.
Rollback never authorizes a replay, fresh timestamp, renewed old approval, automatic
old-runtime activation, service restart or backend retry. Retained old snapshots
are evidence, not a preapproved live fallback.

## Ready versus remaining gates

| Work | Status / approval or evidence needed |
| --- | --- |
| Exact five-file diagnostic diff and compatibility/rollback checks | Ready; 19 fake cases and byte restoration pass |
| Public-source integration and future coordinator compatibility | Plan ready; explicit application approval and source review still required |
| New paired snapshots and native containment | Not performed; explicit private/runtime-operation approval and new seal-bound evidence required |
| Distinct future development inference | Not authorized; reviewed experiment plus fresh owner/account/model/USD0/isolation/cleanup gates |
| Batch 2 qualification | Deferred: dated costs/clock/sessions, prospective freeze and untouched holdout, reviewed real provenance/registration adapter |
| Qualified comparison | 60 eligible validation days, three folds >=20 days, 100 closed trades per strategy plus all unchanged performance/stress/bootstrap gates |
| No-order observation and execution promotion | Qualified comparison and explicit hash-bound human observation approval; execution is a separate approval/implementation |

The diagnostic/source review can proceed without completing Batch 2 qualification.
A development-only result would remain unqualified. Native credential/billing
gates and Batch 2 evidence are independent; neither substitutes for the other.

## Documentation references and evidence limits

Context7 was queried for HTTPX 0.28.1. Its primary
[streaming documentation](https://github.com/encode/httpx/blob/0.28.1/docs/quickstart.md#streaming-responses)
and [timeout documentation](https://github.com/encode/httpx/blob/0.28.1/docs/advanced/timeouts.md)
support the existing streamed raw-byte/context-manager and phase-timeout usage.
They do not prove local dependency availability, backend cancellation or billing.
No provider/account connectivity was rechecked. The consumed inference failure
remains unknown; the separately diagnosed Codex notification hook was unchanged.

## Review, configuration difference and preservation

The reviewed preparation scope consists of this plan, the spec/handoff links,
the expanded offline checker and its five compatibility tests. The pinned
runtime patch is unchanged; no runtime modules or real approval records are edited.
Review corrected the prerequisite-order description: billing is checked before
shared-source equality, while signed account acceptance occurs later in run().

The broken historical HANDOFF link to `docs/superpowers/plans/task_plan.md` is
replaced with the existing Batch 3 preparation plan. That plan retains the Batch 2
qualification gates and links the current specification/evidence. No placeholder
task_plan.md or unrelated historical rewrite is introduced.

Read-only configuration checks compare raw file bytes, without printing contents:

| Observation | SHA-256 / result |
| --- | --- |
| Prior-task Codex config checkpoint | `51a5fe9ce3582a4fc271d67db252b8c5d046996780f1b04ff93060368ff5a5dd` |
| Previous integration review and current review | `4776696bba5f806aec8d8122328e8f189e61bab0aaa5344a74592a807ee93aa8` |
| Hook file, prior checkpoint and current review | `429a78006123b200440e73fffdd55a4d54f16afadac54e4d28e0fa8f13be5a60` |
| legacy_notify command and arguments | Exact match with the earlier two-element notification entry |

The whole config file differed between the earlier checkpoint and integration
review, and is stable across the last two review observations. A hash difference
establishes changed bytes, not changed keys, semantic impact, author or cause.
The old config contents were not retained, so no key-level diff or attribution is
claimed. Neither this task nor the preceding integration review wrote configuration.
No config/token contents were printed; no notification hook was edited, rerun,
disabled or bypassed. The old failing preservation comparison remains evidence;
its expected hash was not reset to conceal the difference.

The original checkout HEAD/branch/status and 95 inventoried uncommitted file hashes
are verified separately against their original snapshot. Those checks do not
depend on treating the newer global config hash as equal to the old one. The
preparation patch hash, fake checks, exact rollback, full HANDOFF/local plan/spec
links, code fences, syntax and scoped whitespace are checked before commit.
Only these five preparation files are selected for the commit/push; main and the
original supported-gateway branch/worktree remain untouched.

## Exact next approval scope

The next approval would authorize **public-source integration and fake-only
coordinator preparation**, limited to:

1. Create a new clean source worktree/branch based on supported-gateway commit
   `18620b96eb05eeef86dcea52acf3e00cb1c09e6c`. Apply only the unchanged five-file
   patch identified above to public source, verify the two runtime-file hashes,
   review the diff and commit it with normal hooks. Preserve the original dirty
   checkout and the main-based preparation branch. Any rebase or extra source
   change needs a newly reviewed diff; no merge is included.
2. Review the public source of the historical owner coordinator read-only and
   record its identity. Prepare a separate future source candidate plus synthetic
   tests for runtime-generated review text, exact UTF-8 hash, eleven-field schema,
   explicit human consent/freshness and exclusive writes. Do not edit or execute
   the consumed coordinator, write real approvals, access credentials or invoke
   account/dispatch helpers. A future helper is a candidate for review, not a
   newly authorized launcher.
3. Rerun fake-only request/worker/parser/manifest/approval/replay/rollback checks
   and report the reviewed source commit and remaining gates. Approval of this
   phase does not approve any owner acceptance prompt or model request.

This approval excludes private snapshot creation or resealing, ACL changes,
native/Docker containment operations, real account/model/browser/billing checks,
credential renewal, real approval-record writes, inference, retries, scheduling,
orders, promotion, merge and VPS changes. New matched snapshots/native proofs
need a separate later approval. A distinct future inference needs its own reviewed
experiment and fresh exact owner authorization; the consumed identity stays blocked.
Batch 2 evidence and human observation/promotion decisions remain separate as
listed above. No further approval is needed to publish this preparation commit.

Current-task verification: all 19 fake cases and exact reverse restoration pass;
all 50 local HANDOFF/plan/spec links resolve; fences, syntax and whitespace pass.
Original HEAD/branch/status and all 95 inventoried file hashes match; current
configuration bytes, notification entry and hook file are unchanged during this
review. The historical configuration-hash difference above remains documented.
