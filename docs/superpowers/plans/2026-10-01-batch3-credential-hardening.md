# Batch 3 credential hardening and fake-auth rehearsal

Completed on main, 2026-10-01 Bangkok. Preparation only: zero model requests,
no credential contents read, no VPS/MT5/collector/order/risk/promotion changes.
This supersedes the host-ACL findings in the credential-boundary review for
the inspected workspace paths; it does not approve a live transport.

## Windows boundary

Used native `icacls` via `ops/trading/harden-batch3.ps1`. The initial Set-Acl
approach required an unavailable security privilege and was replaced with
icacls; no audit policy was changed.

- Owner is now wai19 for `.batch3-vibe`, profile and private runtime parents.
  Sandbox Modify on editable parents omits DeleteChild. Explicit non-inherited
  sandbox Delete denial on `.batch3-vibe` and profile prevents renaming them to
  substitute a different tree. The repository remains editable.
- A harmless credential canary proved owner read access and sandbox denial of
  read, write and deletion before hardening the real files.
- The entire private `.vibe-trading` runtime, auth directory, existing OAuth/
  lock files and private config are restricted to wai19 and SYSTEM. Protecting
  the config parent also protects future atomic replacements through inherited
  permissions. Default user-level OAuth stores were not changed.
- Verified owner create/read/delete using a harmless file inside the auth
  directory. Sandbox attempts to open the OAuth and private environment files
  were denied before any bytes could be read. No token contents or hashes used.
- The already-running learning application still serves HTTP 200 at port 8899.
  No login, token refresh, model inference or service restart was used to test it.

## Sealed reviewed copies

`.batch3-vibe/sealed-credential-rehearsal` contains the offline Python/config/
patch tool chain, original pinned provider source, and copies of the previous
synthetic attempt's packet, request, reservation and prepared provider source.
It contains no OAuth/config credentials. All 48 manifest hashes verified.

Owner/SYSTEM retain FullControl; the coding sandbox has read/execute only and
does not own these files/directories. Sandbox write and deletion attempts were
denied on both the runner and frozen request. These are protected copies, not
immutable storage against the owning user, SYSTEM or an administrator. Original
development sources and earlier evidence remain editable. A future live runner
must explicitly verify and execute its approved snapshot; no live entry exists.

## Fake authentication checks

`test_batch3_auth_boundary.py` extracts pinned OAuth state-machine/header/error
definitions. It supplies memory-only fake storage, fake SDK refresh and fake HTTP
through the existing provider harness. The harness audit records counts/status
only, never headers or credentials. Checks cover:

1. Fresh fake token: zero refresh calls, one fake inference.
2. Expired fake token: one successful fake refresh, one fake inference.
3. Permanent refresh failure, timeout exception and stale returned token:
   no inference; fake cache clearing when appropriate; canaries absent from errors.
4. Fake inference HTTP 401: one inference attempt, no refresh or resend.
5. A delayed fake refresh: isolated subprocess killed by a 0.2-second parent
   deadline before the fake inference marker could be written.

Four test methods passed from development sources and again from the sealed
copies. Full trading Python suite: 137 passed. The provider helper now has a
fake-header/audit seam solely for these offline tests. Ordinary learning-provider
behavior and upstream files are unchanged.

These tests do not verify real SDK HTTP timeout behavior, file locking/rotation,
OAuth validity or endpoint token-cap compatibility. The lock in this test is a
null context and refresh traffic is mocked. A real transport still needs the
same outer deadline and a credential-owning trusted process; it must not expose
tokens to the proposal worker or automatically resend inference after 401.
Normal learning app dependencies and tools run as wai19 and can access its
credentials; this hardening separates the coding sandbox, not arbitrary code
executed under the credential owner's identity.

## Resume

Private evidence: `.batch3-vibe/canary-denial-passed.json`,
`.batch3-vibe/credential-hardening-check.json`, sealed `manifest.json`.
Hardening is staged: canary, credentials, seal. Do not rerun canary initialization
over a hardened runtime; it is an initial setup operation, not a health check.

At verification time it was 2026-10-01 15:58 UTC. Smoke collection ends at
17:00 UTC; finish capture is permitted only after 17:15 UTC, October 2 00:15
Bangkok. Preserve `/root/kwg-gold-research/evidence/smoke-20260930T164651Z` and
its collector. Review the finish capture and cost/clock/continuity evidence after
that time; no remote finish evidence was inspected in this task.

Unknown OAuth monetary cost still blocks live dispatch. Batch 2 qualification
and explicit human promotion approval remain independent gates. One-day smoke
success does not qualify Batch 2.
