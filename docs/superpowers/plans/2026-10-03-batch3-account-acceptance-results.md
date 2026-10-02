# Batch 3 — account acceptance completed

Date: 2026-10-03, Asia/Bangkok. Gate A passed for the separate gold research
account and the owner-selected `gpt-6-astra`. The expired login was renewed once;
the provider's authenticated catalog includes this model. The account worker's
Internet isolation and cleanup checks passed. **Inference remains disabled.**
The next milestone is gate B: verify provider-enforced **$0 additional spend**.
Batch 2 stays development-complete, unqualified, with qualification deferred.

## Authorization and result

The owner authorized continuing account acceptance and the reviewed same-account
renewal after the [expired-login preflight](2026-10-03-batch3-account-preflight.md).
The renewed account's catalog lacked `gpt-6.1-sol`. The owner explicitly selected
`gpt-6-astra`; there was no automatic model substitution.

| Final account receipt | Result |
| --- | --- |
| Account acceptance | Passed |
| Signed identity/account/client binding | Validated during renewal |
| Same issued client, account and stable host | Preserved |
| Required model | `gpt-6-astra`, present in seven-model catalog |
| Account-worker production isolation | Verified within the limits below |
| Cleanup, including forced controller termination | Passed |
| Inference/model generation requests | 0 |
| Production attempt registry | Empty |
| Provider $0 ceiling | Unverified |
| Real dispatch | Blocked |

There was one actual refresh POST and five separate authenticated catalog GET
attempts across reviewed source versions. The first two catalog attempts failed
in local response handling; the next two verified the catalog but found the old
model absent; the final attempt passed with the owner's selected model. These
were separate consumed attempts, not HTTP retries inside a request. Anonymous
public signing-key requests also ran. No credit purchase, payment change,
spending-setting change, strategy request, broker action, deployment or push ran.

## Implementation

`gold_account.py` reuses the pinned Docker runtime, existing HTTPX installation,
Squid, seal verification, exclusive receipt helpers and container inspection.
It permits only signing-key GET, the documented refresh grant and model-catalog
GET at fixed provider endpoints. It has no inference operation, endpoint/model
override, redirect, fallback or HTTP retry. `supported_oauth_transport.MODEL`
now supplies the shared fixed `gpt-6-astra` selection; legacy trusted transport
and historical baseline fixtures retain their original model identity.

The owner controller verifies signatures using the installed PyJWT/cryptography
packages and published keys. It checks issuer, audience, subject, client,
expiry, scopes and renewed nonce when present against the original signed nonce.
It does not invent a nonce or treat an expired retained identity as fresh.

A Windows lock serializes access to the original registration. A durable marker
consumes a rotation attempt before transmission. The complete validated token set
is published through a private same-directory pending file, flush/fsync and
atomic replacement, with ACL checks. An unknown rotation remains consumed;
there is no automatic retry, rollback, re-registration or alternate account.
The previous registration and unvalidated renewal response remain credential
material in owner/SYSTEM-only evidence files. They are excluded from Git and
reports. The Vibe store is outside this path.

Credential workers receive only the data needed for their operation through
stdin, never command arguments. No auth directory, home, repository, Docker
socket or fake trust store is mounted. Containers use an unprivileged UID,
read-only mounts/filesystem, dropped capabilities, no new privileges, fixed
resource limits, no restart and Docker logging `none`. Sensitive stdout remains
in captured process pipes; failure output is reduced to bounded redacted classes.

Workers have only an internal dual-stack bridge with isolated gateway modes.
A separate pinned Squid process has the Internet route and permits CONNECT only
to `auth.openai.com` or `api.openai.com`, port 443. Public certificate validation
remains enabled; environment proxies/trust injection are ignored. Squid has no
credentials, cache or access log. CONNECT restricts destinations, not encrypted
HTTP paths; the sealed worker enforces the fixed operations independently.

Catalog handling follows the OAuth route's `models` array and `slug` schema.
Auth responses are capped at 262,144 bytes and catalog responses at 2,097,152
bytes, on both wire and decoded content. Identity and bounded gzip are supported;
truncated, trailing or over-limit content is refused. Raw catalog metadata does
not leave the worker; only bounded model names, count, canonical digest and
availability result are returned.

## Exact final source and evidence

Source commit: `ea5c7d5cd1f47bbe76a6d8256ad616bed5cf55f7`.
Both independent final snapshots contain **76 verified files**, including
**70 code files matching working sources**. Subsequent documentation commits
do not replace these immutable source identities.

| Snapshot / receipt | SHA256 |
| --- | --- |
| `.batch3-vibe/sealed-account-ea5c7d5cd1f4/manifest.json` | `f7c80f73fee847a264d869fa8197ba5358cd049f685a5f5a47b362e93c0a643b` |
| Account boundary receipt | `9b840ad2dc355868e75cfe3c00592f81123c4f164d69126441de88317c50f153` |
| Account termination receipt | `0b3dfc42c607a2f2105e65c20b13b2e86bb59dea321b9aa1c19d61723eac5edc` |
| Account acceptance receipt | `84b95a695304ed7458600ad35dad4b213cf022f3df7160ceba67b339a604645f` |
| `.batch3-vibe/sealed-supported-ea5c7d5cd1f4/manifest.json` | `4021aa9120235e6a224682c6e270985f7288c80e2a37e243f232d4225e9afed0` |
| Supported fake readiness receipt | `cc753e1e24629f8c7bb0588d7b77cd629c234a2cbd61686c1c8791d216f08c5c` |

Account receipts reside under `.batch3-vibe/account-readiness/<account-seal>.<mode>/receipt.json`
for `boundary`, `termination` and `accept`. The separate fake summary resides at
`.batch3-vibe/supported-readiness/<supported-seal>.receipt.json`.
All 14 individual fake receipt hashes were read back and verified.

The redacted operational proof is
`.superpowers/sdd/gold-account-selected-model-20261003/verification.json`, produced
by its adjacent `verify.py`. It confirms one completed rotation, fresh access,
validated token publication, preserved binding, private ACLs, final source and
receipt hashes, wrong-seal refusal, account replay refusal before Docker,
unchanged consumed receipts, empty production registry and absent owned resources.
`sandbox-denials.json` separately records denied credential reads, denied private
registry enumeration and denied sealed-source write access. These ignored
development proof artifacts are mutable; they are not additional source seals.

## Fresh verification

- **185 workspace stdlib tests passed**, 41.750 seconds. Registration and crypto
  dependency tests were excluded from this `-I -S -B` invocation.
- **15 final sealed focused stdlib tests passed**, 0.428 seconds: account,
  supported gateway/transport and existing trusted gateway tests.
- **4 separate final sealed dependency tests passed**, 0.176 seconds: three
  registration tests and the actual RSA signature/binding matrix. These use
  `-I -B` with installed packages, not `-S`.
- **14 final native Docker/Squid/fake-TLS cases passed** with `gpt-6-astra`:
  success, 401, account/client mismatch, missing/expired binding, bad usage,
  malformed/truncated streams, redirect, crash, interruption, timeout and trickle.
  Success observed one fake POST and a credential-free proposal parser. Every
  attempt was consumed, refused replay and cleaned up. Fake verification grants
  no real dispatch, account or billing flag.
- **Final native account boundary, forced termination and account acceptance
  passed**. A normal bridge provided positive host, peer and IPv4 Internet
  controls; isolated workers denied direct host/peer/Internet paths, DNS/UDP DNS,
  unrelated/suffix/literal destinations, alternate ports, plain HTTP and untrusted
  TLS. Fixed approved public TLS worked. Read-only filesystem and absent sensitive
  mounts/socket were probed.

The forced-termination check transferred a synthetic canary, used native Windows
termination on the controller without its `finally` block, and verified detached
guardian cleanup. This is not a power-loss or Docker-engine-failure guarantee.
IPv6 Internet denial was observed without a working IPv6 Internet positive
control. Private-destination ACLs are configured; forced DNS rebinding was not
tested. `production_isolation_verified` applies to this narrow account/JWKS/
renewal/catalog worker, not an enabled real inference entry point. Catalog
availability does not prove inference success, remaining quota or zero cost.

## Preserved failures and history

All earlier seals and consumed receipts remain intact. Initial isolated CLI
sibling-import and native PowerShell inherited-module-path failures occurred
before credential transfer. A later boundary passed its probes but recorded
cleanup false because a peer-name filter also matched its control; resources
were removed and the exact-name filter was corrected before account use.

The first actual refresh succeeded on source `24b24c1f4cff…`, account manifest
`f2ed7c4786ad110bef9a058b93402a437754a05b228cf99cf959185661a456bf`.
Its validated publication was preserved despite a subsequent catalog handling
failure. Later sources added redacted diagnostics, bounded gzip/catalog handling
and bounded model-name reporting. They reused the fresh access token and did
not repeat renewal. Final source selected the owner's model and repeated all
applicable boundary/cleanup/fake checks. The original preflight and fake-only
results remain historical evidence, not current blockers.

## Owner commands and runtime

The following is the command sequence already executed for the final account
seal. **These attempts are consumed; repeating them refuses execution.** Any
later review needs a newly reviewed source identity, not deleted receipts.

```powershell
& ./ops/trading/harden-batch3.ps1 -Phase seal-account
$sealed = Join-Path (Get-Location) '.batch3-vibe/sealed-account-ea5c7d5cd1f4'
$hash = (Get-FileHash (Join-Path $sealed 'manifest.json')).Hash.ToLowerInvariant()
python -I -B (Join-Path $sealed 'code/gold_account.py') --seal-sha256 $hash --mode boundary
python -I -B (Join-Path $sealed 'code/gold_account.py') --seal-sha256 $hash --mode verify-termination
python -I -B (Join-Path $sealed 'code/gold_account.py') --seal-sha256 $hash --mode accept
```

For the separate supported fake seal, load the sealed sibling imports explicitly:

```powershell
$sealed = Join-Path (Get-Location) '.batch3-vibe/sealed-supported-ea5c7d5cd1f4'
$hash = (Get-FileHash (Join-Path $sealed 'manifest.json')).Hash.ToLowerInvariant()
python -I -B -c "import sys,json;sys.path.insert(0,sys.argv[1]);from supported_gateway import readiness;r=readiness(sys.argv[2]);print(json.dumps(r,sort_keys=True));sys.exit(not r['offline_checks_passed'])" (Join-Path $sealed 'code') $hash
```

Runtime: host Python 3.12.0, HTTPX 0.28.1, PyJWT 2.12.1, cryptography 46.0.7;
Docker 29.2.1/API 1.53, Desktop 4.65.0 (221669), WSL2 kernel 6.6.87.2.
Worker image `sha256:35b089054ac9b4257976107e71673d9e30ac17c9b50bbf8b4783f2f6d1d1981f`
contains Python 3.14.5, HTTPX 0.28.1, httpcore 1.0.9 and certifi 2026.5.20.
HTTP workers use `/usr/local/searxng/.venv/bin/python -I -B`; the proposal parser
uses `/usr/sbin/python3 -I -S -B`. Proxy image
`ubuntu/squid@sha256:6a097f68bae708cedbabd6188d68c7e2e7a38cedd05a176e1cc0ba29e3bbe029`
runs Squid 6.13 as UID 13. No packages were added or upgraded.

Ponytail and brainstorming supplied the reuse/converged design workflow.
Context7 supplied Docker/network/logging documentation; route-specific renewal
and catalog rules came from the official provider sources documented in the
[preflight](2026-10-03-batch3-account-preflight.md). Documentation informed the
implementation; native tests and private receipts establish the observed result.

## Next milestone

Verify gate B's actual saved provider controls for this exact gold integration.
OAuth success, subscription access, catalog availability and a local flag do not
enforce $0 additional spend. Setting changes remain separately authorized work.
Until applicable saved enforcement is verified, billing remains false and real
dispatch remains blocked. Gate C still requires its own concrete authorized
single proposal after account/billing checks, real-data preparation and a final
runner seal. No strategy promotion or qualification credit follows from gate A.
