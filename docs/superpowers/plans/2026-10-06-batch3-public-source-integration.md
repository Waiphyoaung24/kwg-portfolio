# Batch 3 public-source integration and coordinator review

## Authorized scope and result

The owner authorized the pinned public-source application, historical coordinator
source review and synthetic request/approval consistency tests. Work is isolated
on `codex/batch3-public-diagnostics`, based on supported-gateway commit
`18620b96eb05eeef86dcea52acf3e00cb1c09e6c`. The original checkout and preparation
branch are preserved. This is public source only; no sealed runtime was modified.

The [reviewed integration plan](https://github.com/Waiphyoaung24/kwg-portfolio/blob/29a096e34cb46b0692f46b09d00ac09bde3748bb/docs/superpowers/plans/2026-10-06-batch3-runtime-integration.md)
and [specification](https://github.com/Waiphyoaung24/kwg-portfolio/blob/29a096e34cb46b0692f46b09d00ac09bde3748bb/docs/superpowers/specs/2026-10-01-gold-batch3-vibe-integration.md)
remain the requirements. No main merge or preparation-history rewrite is included.

## Exact patch identity

Patch SHA-256: `0a7958e1043ca4d077e0dd8a9c263336e137d64e2d80cf316e9d8791b8de59ad`.
Before application, the local commit identity, patch hash, clean worktree and all
four existing target files' exact Git-exported bytes were checked; the fifth
target was absent. `git apply --check` preceded application. All five resulting
hashes matched the published plan:

| File under ops/trading | SHA-256 |
| --- | --- |
| gold_proposal.py | `8195b6ae0e6ad01a3790e901a042cdc0d039629087df981b90ba0de7a700ee85` |
| supported_oauth_transport.py | `bd2ca3f1c2952003a1ab1c9ba84fc1bef2699f375f28bfe1ec6b0a6bf19bf73e` |
| test_gold_proposal.py | `c557da3abb7a5b580c22ff5852af2275a9d39870f5cb8e2232218a2d79a8569c` |
| test_supported_oauth_transport.py | `dbee602a8dc6101e75505d096136fa57048eae1cd360b3c314c27f947582e023` |
| test_proposal_diagnostics.py | `5a9b1afb829228fb4eec7a2d052af592dbd9870a4fe46fbd2c11303d3962aac4` |

The pinned five-file diff is unchanged. No policy, risk, evaluator, input or
experiment identity changed. Shared account/proposal transport dependencies still
require separately approved new matching snapshots. The consumed experiment
remains consumed even under a new source commit; source integration cannot retry it.
The dedicated application commit is `13fd377ef5dcb9dffd24aeac907745237f5331ba`.

## Historical coordinator review (read-only)

Public source reviewed without executing or importing its operational helpers:

| Historical file under .superpowers/sdd/gold-one-proposal-20261006 | SHA-256 |
| --- | --- |
| start.ps1 | `2d3357a413188a8564705bc6a0ce98394b4952a6baca42ddbefa9e1996566755` |
| dispatch.py | `60c6d29c03cef810200a4904cdd02a71c62d1bf7ad4c4f33e2145841883074cb` |

`start.ps1` prints a hard-coded `stream/store false` description, while the
patched request body actually has `stream=true, store=false`. Its prompt does
require the exact answer `APPROVE`, preserves the human timestamp, and stops on
consumed workflow markers. After approval it invokes real account, coding, audit
and dispatch helpers; it is unsuitable for fake-only use and was never run here.

`dispatch.py:consent` constructs the old ten-field approval without
`request_review_sha256`; the patched runtime therefore refuses it. Its original
timestamp and freshness checks, exact receipt hash/verification binding,
exclusive writes with approval last, and consumed-registry refusal are useful
patterns. They do not fix the mismatched displayed request or missing review hash.
Neither file was edited; no old approval was migrated or renewed.

## Separate future candidate and synthetic verification

The [candidate](../../../ops/trading/diagnostic-tests/proposal_approval_candidate.py)
is an in-memory function, outside the tracked top-level runtime file closures.
It has no CLI, private IO, writer, subprocess or launch function. `review_bytes()`
uses runtime-generated UTF-8 bytes, LF and one trailing LF, no BOM. The exact
review hash is `1358b7a8531287bb196d0ccccf44d31fad68040be924e0d1da4577178bc808c3`.

`prepare_approval` refuses absent/incorrect human consent before parsing receipts,
requires the original fresh human timestamp and exact displayed review bytes,
and checks the synthetic receipt's identity/freshness/flags. It returns the exact
eleven-field object and passes the real runtime approval gate. It never writes it.
Caller-supplied receipt flags are not signed identity, billing or native proof;
the existing downstream gates must still verify those separately in any future
authorized workflow. Returning an object is not permission to dispatch.

The six [tests](../../../ops/trading/diagnostic-tests/test_proposal_approval_candidate.py)
cover exact review/schema, absent consent with no helper invocation, BOM/CRLF or
request drift, timestamp/receipt identity failures, old/wrong runtime approvals,
and exclusive writes using the existing writer only in a temporary fake fixture.
They first failed on absent candidate functions, then passed after implementation.
Approval output stays in memory except that synthetic temporary fixture.

The [public checker](../../../ops/trading/diagnostic-tests/check_public_source.py)
checks all five pinned hashes before imports. Its audit guard blocks network,
real child processes and private-tree opens. Existing tests' synthetic
`.batch3-vibe` fixtures are allowed only under a temporary root owned by this
checker; no real runtime read is allowed. Guards are test defense, not production
containment proof. No dependency installation or account connectivity is needed.

```powershell
python -I -B ops/trading/diagnostic-tests/check_public_source.py
```

The standalone scope includes patched transport/proposal diagnostics, supported
gateway, account/crypto, real-development offline preparation and six new tests.
All 40 standalone checks passed. The six new tests were observed failing on the
missing candidate before implementation; the initial 33-case scope then passed.
The preparation branch's `check-proposal-diagnostic-patch.py` separately verifies
19 compatibility cases and exact reverse restoration in its disposable export;
both were rerun successfully after public-source application.

A broader guarded attempt ran 58 cases and encountered seven errors because
legacy tests require absent frozen provider source and fall back to `.batch3-vibe`.
Blocked: `test_trusted_gateway.test_unsafe_container_never_receives_input_and_errors_are_not_saved`,
`test_trusted_oauth_transport.test_bound_headers_single_post_and_fail_closed_responses`,
`test_batch3_auth_boundary.setUpClass`, and `test_batch3_rehearsal` cases
`test_auth_fixture_through_isolated_worker`, `test_complete_flow_is_repeatable_and_unqualified`,
`test_fail_closed_limits_usage_tools_and_deadline`, `test_worker_success_usage_and_no_reuse`.
Those modules are excluded from the standalone checker; no guard was bypassed,
private fixture copied or legacy test rewritten. No full legacy-suite pass is claimed.

## Rollback and remaining approvals

Stop before snapshot selection. Revert the dedicated public-source integration
commit `13fd377ef5dcb9dffd24aeac907745237f5331ba` with normal hooks in this clean worktree; verify the previous four target
hashes against the pinned base and absence of the added diagnostic test. Revert
the separate candidate/preparation commit if its preparation is also declined.
Never reverse-apply inside an existing seal or reset the original dirty checkout.
The disposable checker proves exact patch reversal, not native/runtime rollback.

The next approval is **new matched private snapshot preparation**, tied to this
reviewed source commit: separately named account/proposal/supported snapshots,
new manifests, exact shared-source equality and blocked readiness flags, with
old snapshots and failed/partial evidence preserved. It must explicitly cover
the sealer's private input reads and ACL changes. This phase has not authorized
those actions or any real owner prompt/approval-record write.

Native isolation/cleanup and real account/model/coding/billing acceptance need
separate operation approval and fresh exact evidence. The candidate still needs
a reviewed future owner UI/writer workflow with approval last and exclusive
canonical writes before any real approval can be considered. A distinct future
experiment needs its own reviewed inputs and fresh explicit authorization;
the consumed identity cannot be renamed, retimed or renewed to evade its marker.

Batch 2 stays closed for development, unqualified: dated cost/clock/session
coverage, prospective freeze/untouched holdout, real provenance/registration,
60 validation days, three folds of at least 20 days, 100 closed trades per
strategy and unchanged performance/stress/bootstrap gates remain outstanding.
Qualified observation and promotion require explicit human approval; execution
is a separate implementation and decision. No scheduling, merge or VPS change
is authorized by this source commit.

Independent read-only review matched the pinned artifact/output hashes and
historical coordinator hashes, checked the candidate and dependency/rollback
boundaries, and found no Critical or Important source issues. A malformed new
handoff link was corrected and checked. Live provider behavior, native isolation,
private evidence, real approval/dispatch and excluded legacy compatibility are
not certified by this review. Original HEAD/branch/status, all 95 inventoried
uncommitted file hashes, current configuration bytes and notification/hooks were
checked without changing configuration. No source application hook was bypassed.
