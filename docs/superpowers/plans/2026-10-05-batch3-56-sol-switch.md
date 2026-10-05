# 5.6 Sol switch and next owner check — 2026-10-05 Bangkok

## Current: ACL removal correction ready for owner

Owner ran the first helper. The scoped nine-file model-switch commit succeeded:
`0816548e872af0b7a4e507dc109a15375cccbd11`. Sealing then stopped in the shared
`Set-Boundary` helper with `Unexpected access removal failed.` The full native
checks did not run, and the private partial snapshot has not been inspected by
this denied coding session. Preserve it and all consumed artifacts.

The source contained an ACL removal bug: it translated each identity to a SID
for comparison but passed the identity display string to `icacls /remove`.
Numeric identities require a leading `*` under the
[Windows command contract](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/icacls).
The one-line correction passes the already translated SID as `*<SID>` in the
shared helper, covering all callers without weakening the owner/SYSTEM boundary.
The discarded private command error does not establish the exact offending
identity; native resealing is still required to confirm the original failure
is resolved.

A harmless public file check reproduced removal failure without the prefix,
then removed the ACE with the prefix. The runnable regression
`ops/trading/test-boundary-sid.ps1` extracts and executes the actual shared removal
command against a numeric SID on a harmless canary and verifies the ACE is gone;
it passed. Its initial AST traversal missed the function's nested script block;
that test-only issue was corrected before the passing run. A preliminary
unresolvable synthetic-account grant failed and was preserved; the successful
regression uses the well-known Everyone SID on a credential-free canary only.
No production ACLs, credential files, account/network requests or model requests
were accessed by these checks. Full owner-only ACL hardening was not exercised
by this narrow regression.

**Superseding owner command:**

```powershell
& 'C:\Users\wai19\Desktop\kwg-portfolio\.superpowers\sdd\gold-56-sol-acl-20261005\prepare.ps1'
```

This helper pins parent `0816548` and the five reviewed correction/checkpoint
file hashes. It requires an empty index, stages only those files and commits the
correction, then reuses the existing sealing and fake/native checks at new
commit-named paths. It never removes, overwrites or retries the failed snapshot.
Public syntax/hash checks passed; full private execution remains owner-only and
pending. Share final redacted JSON or the refusal. Stop on any failure. This
stage still excludes account acceptance, token renewal, authenticated catalog
and real inference. Arrange fresh $0/denial evidence and concrete approval only
after the new native preparation passes.

The original helper and instructions below describe the consumed first run.
**Do not rerun that helper.** The line-ending warnings were advisory; the commit
succeeded and the stop came from ACL removal.

Owner selected `gpt-5.6-sol` and authorized continuing. It is present in the
owner-reported seven-model authenticated catalog from Unix `1791197686`. This
supersedes the unavailable `gpt-6.1-sol` requirement and earlier Astra choice.
Support contact was declined; no message was sent.

## Completed source and offline verification

Only the shared `MODEL` constant in `supported_oauth_transport.py` changed from
`gpt-6-astra` to `gpt-5.6-sol`. Existing account, gateway and proposal imports
inherit it. Medium reasoning, the supported OAuth route, one POST, zero retries,
no tools/trades and all billing/isolation/approval gates stay fixed. Historical
private snapshots and consumed attempts are preserved.

Ten existing focused offline tests passed: two supported transport tests, six
proposal tests and two account request/signature-binding tests. Additional
assertions checked all four shared policies, acceptance of a 5.6 Sol catalog and
rejection of an Astra-only catalog. Requests used synthetic credentials/mocks;
no real HTTP or private credential access occurred. Official
[5.6 Sol documentation](https://developers.openai.com/api/docs/models/gpt-5.6-sol)
confirms medium reasoning and Responses streaming support; Context7 was queried
for the relevant primary documentation. Generic API-key examples do not replace
this runner's supported plan-usage OAuth contract or prove included-plan cost.

The broader earlier atomic-publication test encountered a Windows temporary-
file permission error; preserve that disclosed limitation in the
[availability review](2026-10-05-batch3-sol-availability-review.md). The previous
197-test regression, 14 fake native cases and native cleanup results certify the
historical Astra source, not this new source. New native checks remain pending.

## Next: owner runs preparation only

The ignored operational helper is
`.superpowers/sdd/gold-56-sol-20261005/prepare.ps1`. It is pinned to the committed
source bytes and parent Git identity before handoff. PowerShell syntax, synthetic
argument-array binding and public source/output contracts were checked; the
complete helper has not been executed by the agent. Git index writes failed
with permission denied both in the ordinary tool and its approved escalated
retry. No staging or commit completed. The helper therefore verifies the reviewed
file hashes, requires an empty index, stages only the nine listed source/checkpoint
files and creates the necessary local commit in the owner's context. It does not
stage unrelated dashboard, design, product or skill changes.
The active `.batch3-vibe` deny is non-escalatable, so agent tools must not run
this helper or request access around the denial. Run manually in owner PowerShell:

```powershell
& 'C:\Users\wai19\Desktop\kwg-portfolio\.superpowers\sdd\gold-56-sol-20261005\prepare.ps1'
```

It reuses `harden-batch3.ps1` to create new supported, account and proposal seals
from the reviewed commit, then runs all 14 fake transport cases and the existing
account/proposal native boundary and forced-controller-cleanup modes. It checks
the production registry before/after and prints new source/seal/intent hashes
and pass flags. Fixed interpreter and owner identity are required; it refuses
another parent HEAD, changed reviewed bytes, pre-existing staged edits, unexpected
trading edits, existing production attempts or failed checks. Snapshot creation
and native attempts are exclusive. If anything fails, stop, preserve artifacts
and share the refusal; do not delete or retry consumed paths.

This stage can make signing-key and unauthenticated boundary probes and fake
transport calls. It does **not** run account acceptance, token renewal,
authenticated catalog access or real inference. No provider setting changes.
Share only the final redacted JSON summary or error, never credential files.

## After successful preparation

Review the new exact intent and establish owner-side fresh account-bound $0
controls, actual coding-denial evidence and explicit one-proposal approval.
Coordinate these before running new account acceptance because acceptance and
dispatch evidence expire after five minutes and attempts are consumed once.
The old account receipt cannot be relabelled, repeated or reused for the new
seal. No approval or private evidence writer has been added by this model change.
Real dispatch remains blocked; no model request has run. Batch 2 qualification
remains deferred and no trade, deployment or push is part of this stage.
