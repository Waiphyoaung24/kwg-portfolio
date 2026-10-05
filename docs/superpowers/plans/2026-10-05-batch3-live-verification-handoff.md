# Current-seal account and provider $0 verification

## Current: recovered old cleanup; guardian fix native preparation next

Owner recovery removed both empty owned networks, confirmed all owned resources
absent/saved guardian PID absent, and preserved historical metadata. Old native
proof stays failed; account acceptance/model requests zero, production empty.
Historical exact cause unknown. Public regression found an unhandled guardian
wait/handle failure path. Shared cleanup now publishes redacted class/phase
failure evidence, fails closed and batches exact names under the same budget;
both controllers expose exit/cleanup diagnostics. Seventeen tests and both
callers' real-self-handle/fake-Docker publication checks pass.

Manual next: gold-guardian-fix-20261005/prepare.ps1. Scoped functional commit,
old-evidence/current-absence preflight, new account/proposal seals and four native
fake-input/public-TLS proofs. No acceptance, renewal/catalog, approval or inference;
reuse the old supported matrix after exact source/evidence checks. Preserve old
failure and new consumed attempts; stop on failure, never repeat preparation.
Fresh account round and provider-enforced $0 checks remain next after actual
native success, then separate proposal approval. Old verify.ps1 remains obsolete.

## Current: scoped failed-native network recovery pending

Owner inspection: public TLS true, no false probe categories or saved exception
kind; cleanup receipt absent. All exact-owned containers absent, inner/outer
networks present with no unexpected matches. Engine/images healthy, production
registry empty, no acceptance/remaining native checks/model requests.
Do not run live verification or repeat consumed preparation/boundary.

Next manual owner entry is gold-native-failure-20261005/recover.ps1. It validates
source/seals/markers, saved guardian PID absent/exited, exact network ownership
and zero attachments, removes only inspected IDs and rechecks absence. Active
or unknown PID/attachments/unexpected resources refuse mutation. Historical
receipt/ownership/markers remain byte-identical; manual cleanup does not replace
native proof. Public synthetic recovery/guardian tests and 15 focused tests pass.
Runtime/seals unchanged; actual owner recovery and guardian cause are pending.
Fresh native proof, account/$0 gates and separate proposal approval follow.

## Current: native preparation failure blocks live verification

Source e93578e was committed/sealed by the owner preparation command. Its first
account.boundary failed with exit 2 and cleanup false, consuming that native
attempt. No account acceptance or model request ran. The remaining new native
checks were not reached. Do not run preparation again or any live verification.
Read-only owner diagnosis is gold-native-failure-20261005/inspect.ps1; preserve
failed attempts and seals, and share its redacted receipt/resource result.
No runtime changes are made before the saved failure is inspected. See the
[recovery task plan](2026-10-05-batch3-account-recovery/task_plan.md).

## Current: owner-selected durable recovery implemented offline

Durable round IDs and exact approved account receipt binding are implemented
in public runtime source; 15 focused offline tests pass. Owner native source
commit/sealing/proof is pending at gold-account-recovery-20261005/prepare.ps1,
which performs no acceptance or model requests. See
[recovery task plan](2026-10-05-batch3-account-recovery/task_plan.md) for scope and
checks. Previous sealed source and old verify.ps1 do not implement this recovery;
do not use them for another acceptance. Bind a fresh verification helper to
actual new source/seal/intent identities only after successful owner preparation.
No live account verification, fresh $0 gate or proposal approval has occurred.

## Current: corrected infrastructure confirmation passed

Owner supplied the corrected inspector result: Linux engine available, both
fixed image pins pass with their correct identity basis, and all exact-owned
failed-attempt containers/networks are absent with zero unexpected matches.
No credentials read, acceptance repeated, resources modified or model requests.
Historical saved cleanup false and failed consumed acceptance are preserved.

No further infrastructure diagnostic is requested at this point. The remaining
account-verification lifetime/recovery contract is documented in
[the recovery task plan](2026-10-05-batch3-account-recovery/task_plan.md).
Owner choice pending; runtime remains unchanged during brainstorming. A new
round must come from a reviewed functional controller change with legitimate
fresh sealing/native proof, not resetting/replaying this attempt or resealing
unchanged source. Account/$0 and separate proposal approval remain incomplete.

## Latest: owner recovery and image-check correction

Owner recovery returned Linux engine available; both exact-owned container and
network inventories are known absent, with zero unexpected prefix matches.
Historical saved cleanup remains false and acceptance remains failed/consumed.
No credential reads, repeated acceptance, resource changes or model requests.

Both pinned image lookups exited zero. Worker ID matched, but proxy availability
false was an inspector bug: SQUID_IMAGE is a repository@digest, whereas Docker
image Id is a configuration digest. Corrected the ignored inspector to inspect
only Id and RepoDigests, comparing ID pins to Id and repository pins to exact
RepoDigests (also accepting its explicit docker.io prefix). No image pull or
sealed runtime change is needed for this diagnostic correction. Regression
checks cover correct/different/missing repository pins, wrong IDs, invalid IDs,
redaction and exact ownership. Wrapper pins were updated and syntax verified.

Next manual read-only entry is gold-accept-failure-20261005/inspect.ps1 to confirm
the corrected proxy pin. This does not retry acceptance or make an expired/
failed receipt valid. Fresh account acceptance recovery remains unresolved; do
not delete/reset/replay this attempt or reseal unchanged code to bypass it.
Provider $0 evidence must be freshly checked after that recovery is legitimately
prepared, and a proposal still requires separate explicit approval. Earlier
recovery-pending entries below are historical; dispatch remains blocked.

## Latest: native account acceptance failed and is consumed

The owner read-only inspector returned Docker Linux engine unavailable, native
exit 1, stderr SHA `e9133cf10b02b0b91c8b119848513db0ac541e7c3c19681266939e4b9952f7cc`.
It skipped pinned-image/resource inventories, so cleanup/resource absence is
still unverified. Guard-ready and finished markers exist; both credential
renewal snapshot markers are absent. These were presence checks, not credential
reads. Saved receipt and cleanup remain unchanged and false.

Hidden Desktop startup was attempted under the earlier explicit startup
authorization. Agent-side public Docker info using an empty public configuration
returns permission denied; that result does not prove the owner's engine is
ready or stopped. Next manual owner entry is
`.superpowers/sdd/gold-accept-failure-20261005/recover.ps1`. It checks the owner
identity and inspector hash, starts Desktop hidden only if neither Desktop nor
backend is running, waits 20 seconds after a start, then runs the read-only
inspector. The inspector adds finite safe stderr categories without disclosing
raw errors. Synthetic classification/redaction/ownership tests and PowerShell
syntax checks pass. Actual owner recovery is pending. No restart, reset, pull,
resource removal, acceptance retry, credentials or model requests. Preserve the
consumed attempt; do not use verify.ps1 again for this acceptance.

Owner reported the existing current account seal's `accept` receipt: passed
false, failure `CalledProcessError`, cleanup false, accepted timestamp/catalog/
renewal fields null, account/isolation unverified, model requests zero and
dispatch blocked. The helper stopped at `one_unused_sealed_account_acceptance`.
This failure occurs after acceptance was created; preserve it and do not run
verification again. No proposal approval or dispatch occurred. Earlier
unused-acceptance resumption instructions below are now historical.

The public controller's checked subprocess commands are Docker operations, so
the failure is in a Docker command. The exact failing command/stderr was
discarded by its existing exception handler and is not recoverable from this
receipt alone. Do not assume engine downtime, an image problem, credential
rejection or resource leakage without evidence. Cleanup false means the
guardian did not verify absence; it does not establish presence.

Next manual owner entry:
`.superpowers/sdd/gold-accept-failure-20261005/inspect.ps1`. The hash-pinned
inspector reads only the exact receipt/cleanup/ownership metadata, checks guard/
finished and credential-snapshot file presence without opening credentials,
and queries current Docker engine/pinned images/exact-owned resource presence.
It requires an empty attempt-local Docker configuration and outputs allowlisted
values/statuses and error fingerprints, never raw Docker errors or credentials.
It does not start, stop, remove, pull or alter resources, retry acceptance,
contact the provider, approve inference or change permissions/seals. Synthetic
redaction and resource-prefix checks passed, including refusal of unrelated or
mixed resource names; wrapper syntax passed. Initial owner diagnosis completed
as recorded above. Agent tools did not read the denied saved attempt. Share the
recovery result. Dispatch stays blocked and Batch 2 deferred.

## Owner pre-acceptance refusal corrected

The owner reported `ValueError` at `source_and_existing_seals`. Public source
inspection found an incorrect owner-only ACL call on the account snapshot.
`harden-batch3.ps1` intentionally grants account code/fake inputs sandbox RX;
the account controller verifies its seal rather than requiring a private code
ACL. The real proposal snapshot and credential store remain owner-only.

Only the ignored owner helper was corrected: apply the private snapshot ACL
check to the proposal, while fully verifying both pinned manifests and code
identities. Credential/receipt/registry privacy checks are unchanged. No
permissions, runtime sources or seals were changed. A regression using the
actual helper loop and in-memory paths reproduced the old refusal, then passed
afterward. Invalid account manifest/private proposal ACL cases still refuse.
The wrapper's helper hash was updated; diagnostic phases now separate each
seal, native receipts, registry and real inputs.

The reported phase occurs before the account acceptance subprocess, so this
run did not create or consume acceptance or send a model request. Do not
repeat any separately consumed attempts. Refresh actual UI/denial observations
before resuming the corrected verification-only command. Full owner execution
is pending; the denied private snapshots were not read by agent tools.

The owner authorized this milestone on October 5, 2026: fresh account and
provider-enforced $0 checks, followed by separate explicit approval for one
development proposal. That instruction does not authorize inference.

## Read-only checks completed

The agent opened the unique **KWG Gold Research** login connection, confirmed
its October 3 connection date and ChatGPT plan permission, and followed its
**Manage usage** button. Saved controls showed included plan use allowed,
app limit 100%, global app credit use **off**, automatic reload **off**, and
Save disabled. The browser account email fingerprint matched the previous
public observation. Owner-side correlation to the current signed registration
is still required; the private registration was not read by agent tools.

The existing actual-chat open-only probe passed again: registration and canary
opens denied, public source open and workspace write positive, no credential
bytes read, model requests zero. `token_restricted=false` and executing-owner
true remain accurately reported: the effective filesystem denial is verified;
no claim of a restricted Windows token is made. No escalation or private
permission exception was requested. Exact fresh observations and timestamps
are in the public helper folder and must not be retimed.

[OpenAI's current provider policy](https://help.openai.com/en/articles/20001542-using-your-chatgpt-plan-in-other-apps-and-sites)
states that apps stop using plan usage at the overall limit unless app credit
use is allowed. An app limit of 100% alone does not enable credits. Credit-use
permission and automatic credit purchases are separate controls. The $0 scope
here is additional provider usage spending through this OAuth connection;
existing subscription charges are outside that scope. No settings changed,
credits bought, API key or paid fallback added. Context7 was consulted for
current authentication/account documentation; provider policy above governs
the spending conclusion.

## Prepared owner workflow

Ignored public helpers live in
`.superpowers/sdd/gold-live-verification-20261005/`. `verify.ps1` is the
verification-only entry. It pins the reviewed helper and observation hashes;
`owner.py --mode verify` validates exact source/seals, completed native
receipts, empty production registry, existing input/intent identity, fresh UI
and actual-chat evidence, and browser/account identity correlation. It then
runs the **unused** sealed account acceptance once and checks the durable
receipt, signed binding, current catalog containing `gpt-5.6-sol`, isolation,
cleanup and exact registration bytes. It writes a private verification audit
only and prints allowlisted results. It creates no approval or canonical
dispatch-gate record and sends zero inference requests. Same-account supported
renewal may occur through the existing sealed runner if needed.

The current account/proposal seals, runtime commit and intent remain unchanged:

| Identity | Value |
| --- | --- |
| Source | `a6eecea6c3f0fb19bd68ff9a436a47947ce81538` |
| Account seal | `91322fb34a145c10b04d357694bca6a75bca09ecfc7fd2c38145be2a88bfb56f` |
| Proposal seal | `b0efe908822a464829ab1c7427d3541d2486bd8d6d2b00b6d7560582a7eef503` |
| Intent | `19de161c8f04a83d9ba66150274df268d1b3f66942deec087fca5a2ea5d01e4c` |

Fresh public evidence must be at most **five minutes old before acceptance**;
stale evidence refuses before consuming that attempt. At dispatch, account,
billing and denial evidence must all be within **five minutes**, while separate
explicit approval is limited to thirty minutes. Do not start owner verification
unless ready to share its result promptly and review the approval next. A
stale refusal before acceptance needs new genuine observations, never a new
timestamp on old observations. A consumed acceptance/production attempt must
not be rerun, removed or reset. If an acceptance expires before approval or
dispatch, stop and review the blocking state instead of bypassing it.
If UI/denial evidence expires during the native account check, refresh genuine
observations and use `owner.py --mode review` for an audit of the existing
acceptance without another network request. It still requires the account
acceptance itself to be within five minutes; it cannot extend its timestamp.

`owner.py --mode dispatch` is prepared but **not authorized or executed**.
It refuses without the exact separate owner approval phrase and its actual
timestamp before accessing the private runtime. It rechecks all evidence and
current acceptance, writes exclusive account-bound billing/denial/approval
records using the original observation times, reuses the sealed gates and
invokes the existing one-request controller. This preserves one request,
zero retries, `$0` additional spend, no tools/trades and blocked promotion.
Do not invoke this mode based on the milestone instruction alone. The exact
request remains the [prepared Sol intent](2026-10-05-batch3-56-sol-switch.md).

## Validation and current limit

Offline helper checks passed a valid observation and refused thirteen unsafe
or stale evidence cases plus four missing/vague/stale/future approvals. An
unauthorized dispatch CLI invocation refused at `authorization_check` before
private access. PowerShell wrapper syntax is checked independently without
executing owner verification. These tests use no credentials, private files,
provider requests or model requests. Actual owner verification is **pending**;
private receipts were not independently reread. No new account acceptance,
renewal, approval, model call, commit or replacement seal was performed by
agent tools. Batch 2 qualification remains deferred.
