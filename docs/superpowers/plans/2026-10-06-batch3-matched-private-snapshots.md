# Matched Batch 3 private snapshots implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:executing-plans after explicit owner approval, task by task. This document authorizes no execution.

**Goal:** Prepare three new, matched, blocked snapshots from the reviewed public source while preserving every existing runtime and consumed record.

**Architecture:** Use the existing sealer at its exact reviewed commit, in a new clean worktree at the pinned source commit. Stage only its enumerated inputs into a new owner-controlled preparation root after separate authorization. Preserve historical evidence; the proposal snapshot is diagnostic preparation for an already-consumed packet, never a launchable experiment.

**Tech stack:** Windows owner PowerShell, Git, Python 3.12+, NTFS ACLs; no Docker, provider API, MT5 or VPS operation.

**Spec:** [reviewed integration specification](https://github.com/Waiphyoaung24/kwg-portfolio/blob/29a096e34cb46b0692f46b09d00ac09bde3748bb/docs/superpowers/specs/2026-10-01-gold-batch3-vibe-integration.md), [source review](https://github.com/Waiphyoaung24/kwg-portfolio/blob/f2ae1a2e92bf0e2c5fcf34e23c868e63c69e8bb3/docs/superpowers/plans/2026-10-06-batch3-public-source-integration.md).

## Global constraints and evidence limits

- Planning only. No snapshot, private-input read, ACL change, real approval, sealed-runtime modification or inference was performed in this task.
- Exact source commit: **`f2ae1a2e92bf0e2c5fcf34e23c868e63c69e8bb3`**. No cherry-pick, dirty source or later HEAD substitution. The runtime patch commit is `13fd377ef5dcb9dffd24aeac907745237f5331ba`.
- `ops/trading/harden-batch3.ps1` SHA-256: `4baae773c5826d8f1013710da979ae6b764e7d7b706ba2cac422387ebafd385d`.
- Public-source checker SHA-256: `90b4e1ca55c64d830c7425f33161817733a11c98c3be8553d785b3ac06b97141`; it checks all five patched file hashes. Policies, risk, evaluator, packet and experiment identity stay unchanged.
- Availability, ACLs, byte identity and freshness of private inputs are **unverified**. Paths/hashes below come from public code, not inspection of private state. New manifest/intent hashes cannot be known before exact staging; record actual results, never invent them.
- Preserve the original dirty checkout, all old snapshots and registries, and the smoke collector/artifacts. No old helper, acceptance prompt, scheduler or dispatch command appears in this plan.

## Review focus

1. A missing or changed frozen input must stop before snapshot creation; preserve any partial output if a later check fails.
2. A shared account/proposal module mismatch must refuse, even when both manifests individually verify.
3. A substituted path, reparse point, unexpected ACE or existing destination must refuse without repair.
4. A new preparation root's empty registry must never be treated as permission to repeat the consumed experiment.
5. Synthetic tests must retain source identity checks, network/private IO guards and their evidence limits; fake deadlines do not prove native termination.

## Exact locations

For the future authorized owner session only (the SourceRoot below does not get created by this task):

```powershell
$SourceCommit = 'f2ae1a2e92bf0e2c5fcf34e23c868e63c69e8bb3'
$CoverageRoot = 'C:\Users\wai19\.codex\worktrees\gold-batch3-public-diagnostics\kwg-portfolio'
$SourceRoot = 'C:\Users\wai19\.codex\worktrees\gold-batch3-snapshots-f2ae1a2e92bf\kwg-portfolio'
$PreparationRoot = Join-Path $SourceRoot '.batch3-vibe'
$HistoricalRoot = 'C:\Users\wai19\Desktop\kwg-portfolio'
```

| New destination relative to SourceRoot | Purpose |
| --- | --- |
| `.batch3-vibe/sealed-supported-f2ae1a2e92bf` | Supported fake-only code/policy plus frozen legacy fixture copies |
| `.batch3-vibe/sealed-account-f2ae1a2e92bf` | Account code/policy with identical shared modules |
| `.batch3-vibe/sealed-proposal-f2ae1a2e92bf` | Proposal code/policy, same shared modules, pinned historical development inputs; approval pending |
| `.batch3-vibe/production-attempts` | Sealer-required private preparation registry; not a replacement for the historical consumed registry |
| `.batch3-vibe/supported-readiness`, `account-readiness`, `proposal-readiness` | Sealer-required private directories; no acceptance or approval record written |
| `.superpowers/sdd/batch3-auth-docker-20261002-03/refresh_success` | New restricted staging copy of the four frozen historical fixture files |
| `.batch3-vibe/snapshot-preparation-f2ae1a2e92bf/verification.json` | New owner-only, exclusive preparation receipt with source/manifest/input hashes and blocked status; not an approval |
| same receipt directory: `failure.json` or `retirement.json` | New exclusive failure/retirement decision; preserve the successful/partial verification record rather than replacing it |

All destinations are beneath the explicit SourceRoot above. If the preparation
root or staging fixture destination already exists, stop for an owner-reviewed
inventory; do not assume emptiness or reuse it. Do not move/rename an old tree to
make a path available. The helper has no alternate-root parameter and derives
paths from its own repository; do not run it from the original dirty checkout.

## Task 1: Approve and stage exact inputs; blocked pending owner authorization

**Files:** the pinned public source; only new staging destinations listed above.
**Interfaces:** consumes exact existing bytes; produces owner-controlled copies with recorded hashes, not model/account readiness.

### Required read/copy allowlist

For each row, the source is under HistoricalRoot and the staging destination
under SourceRoot uses the **same relative path**. These copies are absent from
Git. No auth profile, registration token, issued client, broker file or approval
file belongs in the allowlist.

| Required source relative path | Required identity / use |
| --- | --- |
| `.batch3-vibe/upstream/agent/src/providers/openai_codex.py` | Raw SHA `19a23404ae7cdbe404c28b157fd2fc6766f7deec2a0db0423879601bb1fdd4f0`; all three phases copy it as upstream-provider.py |
| `.superpowers/sdd/batch3-auth-docker-20261002-03/refresh_success/attempt.json` | `76bdfdc7113325bc10ca6e4cc217167794351da4bb4f38cf84aaffe0c5d66d5f` |
| same fixture directory: `packet.json` | `ebfcaac926358b87bffa22129eba5253b2eb4872ba7012552ad49f0ab74b5539` |
| same fixture directory: `request.json` | `325d6b1fc5a45d0ae5480cf5c99f2cc67bb435c3730b41ca39498beeb0a5af90` |
| same fixture directory: `provider.py` | Patched SHA `64e257725e04ff0b1d8e7a56061d67aa190113d60340850b45bc821de74e867e` |
| `.batch3-vibe/gold-development/real-inputs-e75e515e09a6/preparation-receipt.json` | `1c93fc050b0de511e6fa635b157720c3be74a1832c7585cec90296bc6ee7f046` |
| `.batch3-vibe/gold-development/real-packet-e75e515e09a6/packet.json` | `e6f2d78918772b3791b3451c70a326a3d24de2a95da3c332d44d720065e70038` |
| same packet directory: `prompt/prompt.txt` | `cb4584ac365334f372a82a3b963bb806650c59ce9d84a8b23742f6145e12b9a7` |
| `.batch3-vibe/gold-development/real-inputs-e75e515e09a6/manifest.json` | `3fe09a21ceca7e4386dcb9ffb33102fe46ec139bda651e9ff41f7773622a6e81`; evaluator hash map must match gold_experiment.source_hashes() |
| `.batch3-vibe/gold-plan-auth/billing-settings-20261005.json` | Read only for `client_id_sha256`/`subject_sha256` in prepare_inputs; no full-file SHA pin in code; owner must approve and record exact staging bytes. Not fresh billing proof |
| `.batch3-vibe/gold-plan-auth/host.json` | Read only for `id` hashed into intent; no full-file SHA pin in code; owner must approve and record exact staging bytes. Not native identity proof |
| `.batch3-vibe/gold-development/gold-history-20260928-ssh-20261005.json` | Needed only for optional later reproducibility verification, not sealer copying; SHA must equal dataset_sha256 in the pinned manifest, value not independently read here |
| `.batch3-vibe/gold-development/real-inputs-e75e515e09a6/baseline-a.json` | Needed only for optional later reproducibility verification; `632a33fcb6a0adac8d3a5449aeebe8751479dbf8f81a880afae99eb301078c18` |

The last two large inputs need a separately enumerated read/copy authorization
if `verify_inputs` is approved. Basic snapshot/hash verification does not need them.
Do not treat unknown identity of the unpinned billing/host bytes as validated;
review them in the owner session, record hashes without printing contents, and
stop if the intended binding is unavailable or inconsistent.

- [ ] After separate approval, create the new public worktree with `git -C $CoverageRoot worktree add --detach $SourceRoot $SourceCommit` only if its path is absent. This freezes f2ae1a2 even though the coverage branch has advanced. Do not reset or repurpose the coverage worktree. Verify clean pinned source before any private staging:

```powershell
git -C $SourceRoot rev-parse HEAD
git -C $SourceRoot status --porcelain
Get-FileHash -LiteralPath (Join-Path $SourceRoot 'ops/trading/harden-batch3.ps1') -Algorithm SHA256
python -I -B "$SourceRoot/ops/trading/diagnostic-tests/check_public_source.py"
```

Expected: exact source commit, empty status, exact sealer hash, 40 fake cases pass.
Any later public-source fixture/helper change needs a new reviewed source commit
and new snapshot names; do not silently keep this plan's f2ae1a2e92bf suffix.

- [ ] Before creating each staging file, reject existing targets and source/destination ancestor reparses; use the sealer's reviewed Copy-Verified handle/hash/CreateNew procedure. Preserve original ACLs and bytes. Validate the nine fixed small-file pins, fixture packet/request/provider/worker-source relationships, and evaluator map **before** invoking a phase. No synthetic replacement is valid for these historical exact-byte pins.

### Proposed ACL operations (not performed)

Owner is `KWG-Beast\wai19`, SYSTEM is `S-1-5-18`; the sandbox account is
`KWG-Beast\CodexSandboxOffline`. Resolve their SIDs at execution time and stop
if unavailable. Never use a guessed owner SID.

1. For the **new** preparation root and every staged private input directory/file,
   set owner to the owner SID, remove inherited ACEs, grant only owner and SYSTEM
   FullControl. Directory grants use `(OI)(CI)F`; file grants use `F`. Verify no
   other explicit ACE remains. Do not invoke `canary` or `credentials` phases:
   they touch profile/auth boundaries outside this staging allowlist.
2. For the **new** historical fixture staging subtree, apply the same owner/SYSTEM
   boundary to that subtree/files only; do not recursively alter existing
   `.superpowers` parents or sibling workflows.
3. Existing sealer phases create/harden new production/readiness directories with
   owner/SYSTEM only, validate their ACLs, and initially close every new seal.
   Final supported/account seals grant sandbox ReadAndExecute as well as
   owner/SYSTEM FullControl on each item. Proposal seal remains owner/SYSTEM only.
   This existing behavior must be explicitly approved, not mislabeled all-private.
4. No old seal, registry, profile, token/config file or historical input gets an
   ACL change. Existing destination/ACL mismatch is a stop, not a repair branch.

Exact native ACL operations used by Set-Boundary are `icacls /setowner`,
`/inheritance:r /grant:r`, removal of other ACEs, then optional sandbox `/grant:r`.
For new root/input directories use the same first two operations, then **refuse**
unexpected explicit ACEs; do not remove permissions on an existing tree. No
inherited Modify grant or sandbox Delete/FullControl is requested for this plan.

Concrete directory ACL command form, **only for a newly created allowlisted
staging directory**, not an existing runtime:

```powershell
$OwnerSid = ([Security.Principal.NTAccount]::new('KWG-Beast','wai19').Translate([Security.Principal.SecurityIdentifier])).Value
$SystemSid = 'S-1-5-18'
$NewDirectory = $PreparationRoot # Only after approved new-path creation/reparse checks
icacls.exe $NewDirectory /setowner "*$OwnerSid"
if ($LASTEXITCODE) { throw 'Stop; owner operation failed' }
icacls.exe $NewDirectory /inheritance:r /grant:r "*${OwnerSid}:(OI)(CI)F" "*${SystemSid}:(OI)(CI)F"
if ($LASTEXITCODE) { throw 'Stop; staging boundary failed' }
Get-Acl -LiteralPath $NewDirectory # Check exact ACEs; do not print private file contents
```

For each new file omit `(OI)(CI)` from the grants. Check each command's result
and the final exact ACE set. The sealer's final per-item supported/account grant
is `*<resolved-sandbox-SID>:(OI)(CI)RX` for directories and `RX` for files; no
sandbox grant is added to the proposal seal. Do not dot-source the sealer to
borrow a function: its phase body would execute. A path-scoped staging procedure
must be reviewed before execution; this plan does not provide an executable helper.

## Task 2: Create and verify three new snapshots; not authorized

**Files:** exactly the three new destinations. **Interfaces:** sealer phases
consume staged inputs and public code; produce new code/input copies, readiness
metadata and manifests. There is no dispatch or approval writer in this task.

- [ ] After Task 1's separate approval/evidence, run in owner PowerShell, stopping
  on any failure. These commands are a future runbook, **not executed here**:

```powershell
& "$SourceRoot/ops/trading/harden-batch3.ps1" -Phase seal-supported
if ($LASTEXITCODE) { throw 'Stop; preserve partial supported snapshot' }
& "$SourceRoot/ops/trading/harden-batch3.ps1" -Phase seal-account
if ($LASTEXITCODE) { throw 'Stop; preserve partial account snapshot' }
& "$SourceRoot/ops/trading/harden-batch3.ps1" -Phase seal-proposal
if ($LASTEXITCODE) { throw 'Stop; preserve partial proposal snapshot' }
```

Set `$ErrorActionPreference='Stop'` first. Script terminating errors stop the
sequence too. Each phase copies **all tracked top-level** .py/.json/.patch/.ps1
files under ops/trading, plus upstream provider and the four frozen fixtures;
proposal adds four real-* files and intent.json. The nested diagnostic-tests
candidate/checker is not copied and remains outside runtime FILES closures.
Readiness must say exact git_commit, production_dispatch=blocked and false
billing/server-account/production-isolation flags; proposal intent stays
unqualified, promotion blocked, owner_authorization pending.

- [ ] Record each new manifest hash and verify it against the real verifier:

```powershell
$Family = 'supported' # Repeat for account, proposal; only these three new paths
$NewSeal = Join-Path $PreparationRoot ('sealed-'+$Family+'-f2ae1a2e92bf')
$ManifestSha = (Get-FileHash -LiteralPath (Join-Path $NewSeal 'manifest.json') -Algorithm SHA256).Hash.ToLowerInvariant()
python -I -S -B -c "import pathlib,sys;sys.path.insert(0,sys.argv[1]);from trusted_gateway import verify_seal;verify_seal(pathlib.Path(sys.argv[2]),sys.argv[3]);print('Manifest and exact file set verified')" "$SourceRoot/ops/trading" $NewSeal $ManifestSha
if ($LASTEXITCODE) { throw 'Stop; new snapshot verification failed' }
```

The manifest hash must be saved in a **new owner-only verification receipt** for
this preparation (not an approval). On later reads compare with that recorded
hash, not a newly calculated expected hash. The first self-hash establishes a
candidate identity only; it does not replace source-byte/path/readiness checks.
The verifier enforces manifest <=65,536 bytes, each file <=1,048,576 bytes, no
reparse/path traversal, listed hashes and exact file set. Failures are preserved.

- [ ] Compare every copied code file byte-for-byte to the pinned source, not just
  the five patched files. For every `gold_account.FILES` name compare account and
  proposal copies to each other; compare supported CODE_FILES with source too.
  Independently check staged/copy input pins and metadata fields above.

Exact future read-only source/metadata comparison command (after new seals exist):

```powershell
@'
import json, pathlib, sys
source = pathlib.Path(sys.argv[1]); root = source/'.batch3-vibe'
sys.path.insert(0, str(source/'ops/trading'))
import gold_account, gold_proposal, supported_gateway
families = {'supported': supported_gateway.POLICY, 'account': gold_account.POLICY, 'proposal': gold_proposal.POLICY}
suffix = 'f2ae1a2e92bf'
files = {p.name: p.read_bytes() for p in (source/'ops/trading').iterdir() if p.is_file() and p.suffix in ('.py','.json','.patch','.ps1')}
for family, policy in families.items():
    seal = root/('sealed-'+family+'-'+suffix)
    assert all(p.is_file() for p in (seal/'code').iterdir()), 'Unexpected code subdirectory'
    copied = {p.name: p.read_bytes() for p in (seal/'code').iterdir() if p.is_file()}
    assert copied == files, 'Source copy differs'
    meta = json.loads((seal/'readiness.json').read_bytes())
    assert meta['git_commit'] == 'f2ae1a2e92bf0e2c5fcf34e23c868e63c69e8bb3'
    assert meta['mode'] == policy['mode'] and meta['policy'] == policy
    assert meta['production_registry'] == str(root/'production-attempts')
    assert meta['registry_acl_checked'] is True and meta['production_dispatch'] == 'blocked'
    assert all(meta[k] is False for k in ('billing_ceiling_verified','server_account_verified','production_isolation_verified'))
for name in gold_account.FILES:
    assert (root/('sealed-account-'+suffix)/'code'/name).read_bytes() == (root/('sealed-proposal-'+suffix)/'code'/name).read_bytes()
intent = json.loads((root/('sealed-proposal-'+suffix)/'inputs/intent.json').read_bytes())
assert intent['qualification'] == 'unqualified' and intent['promotion_status'] == 'blocked'
assert intent['owner_authorization'] == 'pending' and intent['policy'] == gold_proposal.POLICY
print('Exact source copies, shared closure and blocked metadata verified')
'@ | python -I -S -B - $SourceRoot
if ($LASTEXITCODE) { throw 'Stop; source/metadata verification failed' }
```

This runs only after hash-pinned manifest verification, reads only the three new
seals and pinned public source, and writes nothing. It does not prove registry
history or account/native acceptance. Source commit/cleanliness is checked again
before and after the sequence; `code` must contain no additional nested items,
as independently enforced by source inventory and exact manifest/file-set checks.
- [ ] Verify ACLs using `Get-Acl -LiteralPath $NewSeal` and every enumerated
  descendant, reporting only pass/fail. Require expected owner, protected
  inheritance and exact ACE allowlist/rights from Task 1. Proposal/private staged
  inputs use `gold_account.private_acl(path)`; do **not** use that owner-only
  checker on supported/account seals because their sandbox RX is intentional.
- [ ] If separately approved, call `gold_proposal.verify_inputs(PreparationRoot,
  proposalSeal)` in owner Python with `-I -S -B`, importing only the pinned public
  ops/trading source. It reads the two large private files and returns the intent
  identity; save only safe hashes/blocked status. No run(), dispatch_prerequisites,
  controller CLI, native probe, registration/account acceptance or Docker command.

**Critical activation block:** this new preparation root has a different registry
path. Its empty production-attempts directory is not proof of an unused identity.
Preserve the canonical historical consumed marker at the original root. Do not
copy/reset/migrate that registry here. Before any future activation, a separately
reviewed mechanism must enforce consumed identity across roots; this plan supplies
none. All three snapshots remain unselected; the current packet is unusable for
inference regardless of manifest or source changes.

## Task 3: Legacy-check coverage assessment and future fake-only work

**Files:** public legacy tests/fixture helpers. The synthetic coverage publication below implements only logic tests; snapshot Tasks 1 and 2 remain unexecuted. Any future runtime/provider fixture plumbing change needs its own reviewed diff.

Seven recorded errors were **seven error entries, not seven total test cases**:
the auth class setUpClass failure prevented all its methods from running.

| Blocked entry | Immediate dependency | Additional blocker / synthetic coverage |
| --- | --- | --- |
| trusted_gateway: test_unsafe_container_never_receives_input_and_errors_are_not_saved | Missing `ops/inputs/provider.py`; falls back to private `sealed-trusted-transport-20261002/inputs/provider.py` | Real rehearse verifies exact patched provider hash before container checks. Fake container failures can be covered with genuine hash-matching public provider bytes and mocked Docker; arbitrary synthetic source cannot pass this gate |
| trusted_oauth_transport: test_bound_headers_single_post_and_fail_closed_responses | Same frozen file missing; fallback calls prepare_source on private upstream provider | prepare_source also launches git apply, forbidden under test audit guard. With preprocessed exact public bytes, fake HTTP/canary credentials can cover real invoke_bound unchanged |
| batch3_auth_boundary: setUpClass | Unconditional private upstream SOURCE and prepare_source | Public pinned auth definitions plus fake memory storage/refresh can cover logic. Parent-deadline method later launches a real child; current no-subprocess guard would also refuse it |
| batch3_rehearsal: test_auth_fixture_through_isolated_worker | run_fixture unconditionally prepares private upstream source | Then launches real worker child; fake protocol/controller response handling can be covered, not actual isolated-worker/forced-deadline proof |
| batch3_rehearsal: test_worker_success_usage_and_no_reuse | Same run_fixture dependency | Synthetic packet, usage, reservation and no-reuse logic can be covered with fake child results; no OS-isolation claim |
| batch3_rehearsal: test_fail_closed_limits_usage_tools_and_deadline | Same run_fixture dependency | Fake error/TimeoutExpired and direct worker parsing cover refusal/redaction/receipt logic; mocked clock/process cannot prove real cancellation or termination |
| batch3_rehearsal: test_complete_flow_is_repeatable_and_unqualified | rehearsal -> run_fixture -> private upstream source | Existing synthetic evaluator inputs and fake transport can cover deterministic reports, unchanged risk/qualification, exclusive outputs; not full worker containment |

### Decision: cover semantics without replacing identity/containment proof

- **Implemented by the subsequently authorized public-source test task:** explicit
  synthetic fixture injection at test boundaries, canary-only credentials,
  in-memory fake HTTP and subprocess **mocks** (no real Popen), and temporary
  synthetic manifests/receipts. Keep sockets/real subprocess/private opens
  forbidden. Reject all fallback paths rather than silently probing private state.
  Such equivalent tests get separate names and evidence; do not claim the old
  isolated-worker/deadline tests passed unchanged.
- **Possible for exact provider logic only if authentic public bytes are obtained:**
  historical public record names upstream v0.1.15 commit
  `cc54832cb50de29d14bb10097b18e08f0a843650`. Public retrieval/reconstruction was
  not attempted here. Verify raw SHA `19a23404...`, apply the existing patch in
  a disposable public export before the guarded test process, and require patched
  SHA `64e25772...`. Hash mismatch remains a stop. Do not lower/hash-mock a
  PROVIDER_SHA, use fabricated definitions as the pinned provider, or import a
  live app/storage provider. Audit guarded tests may receive the verified public
  bytes directly; their guards stay unchanged. This needs reviewed test plumbing.
- **Not reproducible from arbitrary synthetic bytes:** the four frozen historical
  fixture SHA pins, trusted provider authenticity, private signed acceptance,
  native ACL denial, container isolation, real deadline termination and billing.
  Synthetic counterparts prove only logic. No source was fetched, private fixture
  read, provider hash patched or guard relaxed for this assessment.

Future RED/GREEN cases should prove missing fixture refuses without fallback;
wrong public fixture hash refuses; unchanged real provider consumes exactly one
fake request; malformed/tool/usage/completion replies refuse; fake child timeout
preserves consumption; reports are byte-repeatable and remain unqualified; and
the audit guard still rejects real sockets/Popen/private paths. Native deadline
testing belongs to a separate explicitly approved containment phase.

## Rollback and approval boundary

Before creation, rollback is simply declining this plan. After staging/creation,
stop selection and leave all new copies, manifests, failed receipts and partial
outputs intact. Record the preparation as blocked/retired in a separate owner-only
decision receipt. Do not delete/reset production journals, rename a partial seal,
restore broad ACLs, reseal an old tree or automatically select an old runtime.
No service, provider, credential, request or production selector is changed here,
so there is no live switchback command. Cleanup/deletion of new private staging
or ACL restoration requires a later explicit path-scoped approval and preserved
evidence; public-source rollback remains normal reviewed Git revert only.

**Next approval would cover:** only exact new root/fixture staging creation,
allowlisted small-file private reads/copies, stated new-path ACL changes, three
sealer phases, hash/source/metadata/ACL verification and a new verification/retirement
receipt. Optional large-input reproducibility reads must be named separately.
No real approvals, account/model/billing/native checks, private registry migration,
source changes, inference, retries, selection, scheduler, merge or VPS operation.

Known blockers: owner approval; private input availability/hash/ACL evidence;
approved identities for unpinned host/billing bytes; safe new-path bootstrap;
canonical consumed-identity enforcement before any later activation; and genuine
public provider source/test plumbing for legacy compatibility. Batch 2 evidence
and human observation/promotion approval remain independent and outstanding.

Planning validation checks source commit/hash references, relative links, fenced
command syntax, input names against prepare_inputs/verify_inputs, sealer phases,
shared file closures and legacy call paths. It does not run any private command.
The six future PowerShell blocks were parsed without execution; embedded Python
syntax, source/helper hash references, three snapshot suffixes, seven recorded
error entries and whitespace were checked from public source. At the original planning checkpoint, the public-source
worktree was clean at f2ae1a2 and the original checkout remained at 18620b96.
This document is now published with tests; none of its private operations is applied.


## Published synthetic coverage and remaining proof limits

The owner subsequently authorized synthetic coverage and publication only.
[test_legacy_synthetic_logic.py](../../../ops/trading/diagnostic-tests/test_legacy_synthetic_logic.py)
adds nine separately named logic tests. It uses real public controller/parser/
evaluator/manifest/refusal logic, with dependency fakes for provider preparation
and child results. It never supplies synthetic bytes to a patched identity guard:
the actual upstream/trusted provider guards reject those bytes. Real runtime
source, hash constants and the audit guard function remain unchanged.

| Historical error entry | New logic coverage | Still unverified |
| --- | --- | --- |
| trusted_gateway unsafe container | Real provider/manifest refusal before reservation or child call; real supported-route inspector rejects unsafe network/mount/runtime metadata | Trusted legacy branch after authentic provider hash; actual Docker configuration/cleanup |
| trusted transport bound headers/replies | Real legacy source pin rejects synthetic bytes; supported fake HTTP single POST, refusal/redaction and zero retries | Legacy provider conversion, exact legacy headers/SSE against authentic pinned bytes |
| auth-boundary class setup | Real fixture/audit schema validation, no provider/child call for invalid fixture, acceptance/refusal of fake audit replies | Real pinned refresh/storage/401 state machine; parent termination deadline |
| auth isolated worker | Real controller consumes fake successful auth-audit response and refuses invalid audit counts; zero model requests, os_sandbox=false | Authentication execution, actual worker isolation and helper provenance |
| worker success/no reuse | Real controller validates fake successful reply, writes validated proposal, refuses output reuse and preserves reservation bytes | Child process execution and environment isolation |
| fail-closed limits/deadline | Direct real worker checks bound synthetic source/usage; controller rejects invalid/oversized proposal replies, redacts fake child failure and preserves consumption on mocked TimeoutExpired | Provider-side tool/usage handling; real timeout kills/waits or cancellation |
| repeatable comparison | Real controller with fake child, real validator/simulator/gates: two JSON/CSV/baseline/candidate outputs identical, unqualified and blocked | Full provider-to-isolated-process flow; real broker inputs/qualification |

The guard test deliberately calls DNS/connect/bind/Popen/os.system and a private
open; each is refused before its prohibited operation. Every filesystem write
is confined to synthetic temporary fixtures; no private snapshot or production
registry is created. No hash guard, sys.flags value or native acceptance is mocked.
Direct worker tests run with actual isolated/no-site flags, fake provider dependency,
empty allowed environment and sandbox_expected=false, not fabricated isolation proof.

Run these two **current public coverage** commands from CoverageRoot:

```powershell
python -I -B ops/trading/diagnostic-tests/check_public_source.py
python -I -S -B ops/trading/diagnostic-tests/check_public_source.py --legacy-only
```

Expected: 40 existing checks and nine new logic checks pass separately. The same
unchanged audit function is installed in both modes. The separate -S invocation
is necessary for direct worker flag checks; -S hides the installed JWT dependency
needed by the existing crypto test, so do not run that module in this mode.
An initial combined -S attempt found the missing JWT import and an incorrect test
assertion about a transport request-count field; these were test setup/assertion
errors, corrected without a dependency install, runtime change or guard relaxation.

The checker tooling on the coverage branch has changed to select these suites;
its older hash at the beginning of this plan refers only to the frozen f2ae1a2
snapshot source. Publication does not change the selected snapshot source commit,
private operation approval, provider identity, native isolation, canonical consumed
identity requirement or any Batch 2/promotion gate. The seven historical error
entries remain unresolved as exact legacy/integration checks; these equivalents
are partial logic evidence, never renamed passes for those checks.


Publication verification: all 40 existing checks and nine new synthetic logic
checks passed in their separate guarded modes. Seven fenced PowerShell blocks
were parsed without execution; embedded Python, local links, whitespace, exact
four-file scope and unchanged runtime/guard were verified. Independent read-only
review found no Critical, Important or Minor issues. Private input identities,
ACL/native proofs, actual provider/auth behavior, consumed registry contents and
live acceptance remain outside certification. Original HEAD/branch/status match
the retained checkpoint; no private inputs were opened for preservation checks.
