# Batch 3 supported gateway — fake-only implementation results

Date: 2026-10-03, Asia/Bangkok. Completes the fake-only implementation milestone
in the [approved plan](2026-10-03-batch3-supported-gateway-plan.md).

The practice connection is implemented, locally committed, tested against a
local fake service and sealed. It can transport one synthetic response and pass
its text to the existing proposal validator without giving that validator
credentials or network access. It cannot dispatch a real request. The next work
is separate production isolation/account acceptance and provider $0 enforcement;
one real research proposal requires those gates and explicit owner authorization.

No real OAuth store was read during this continuation, no OpenAI model request
was sent, and no credits, billing settings, broker orders or deployments changed.
No branch was pushed. Batch 2 remains unqualified; qualification stays deferred.

## Implemented scope

- Reused the existing pinned worker image, Docker pipe, exclusive receipt writer,
  source verifier, synthetic packet validation and proposal parser. Added no
  Python package, custom proxy, agent framework or frontend change.
- Added a fixed public Responses fake transport: one POST, fixed model and
  reasoning, bounded SSE/text, strict completion/usage validation, verified TLS,
  explicit timeouts, no redirects, no environment-derived proxy and no retries.
  Live dispatch still raises; there is no real credential reader.
- Added a distinct supported rehearsal with exact synthetic account/client
  binding checks before input transfer, inspected container/runtime/network
  configuration, independent worker/service and parent deadlines, and cleanup.
- Used pinned Squid on two internal isolated dual-stack bridges. Only the proxy
  maps the provider hostname to the local fake TLS service. All mounts are
  explicit and read-only, including masks for image-declared volumes.
- Runs proposal evaluation in a separate stdlib container with `--network none`.
  It receives only text, with no access token, TLS key, home or credential store.
- Uses the separate owner-private `supported-readiness/attempts` registry.
  Every attempt is consumed, failed attempts remain, duplicates/concurrent
  reservations refuse, and ambiguous transmitted attempts record
  `outcome_unknown`. The legacy synthetic-only reservation guard remains.
- Added a separate supported seal using the existing stable-handle copying and
  ACL checks. Historical seals, frozen input checks and registration remain intact.

## Final source and evidence identities

Local branch: `codex/batch3-supported-gateway`.

| Evidence | Identity |
| --- | --- |
| Reviewed implementation commit | `0e6db2bf3b2294f5defce57c5ce1371558229b7c` |
| Source snapshot | `.batch3-vibe/sealed-supported-0e6db2bf3b22` |
| Manifest SHA256 | `dd143b7a5de1d0cf66e14cb947cdeb9681ad3aa07c7479e86ca22dba9667c115` |
| Aggregate receipt SHA256 | `3f4227d06c352361d8700849636ee98970491a67b1d96f68c52a99e30dac0ddb` |
| Squid configuration SHA256 | `83bbc28698c9ed16e6cf020630191b493c03c97d308d42321c9b859ee357ccad` |
| Final redacted verification SHA256 | `203971dfe5ce70e572df881af9886cac232d2b6c114cd53e03b1bc8b477a756f` |

The private aggregate is
`.batch3-vibe/supported-readiness/<manifest-sha>.receipt.json`. It binds all
14 individual case receipt hashes. Final verification checked every case hash,
all 73 sealed files and all 67 corresponding working source files. A subsequent
documentation commit does not change these implementation bytes or seal identity.

The reproducible redacted verification script and result are
`.superpowers/sdd/supported-gateway-final-20261003/verify.py` and
`verification.json`; `sandbox-boundary.json` records actual sandbox denial of
sealed source write access and both fake/production registry enumeration.
These development copies are mutable and ignored by Git; the source snapshot
and owner-private receipts remain the authoritative evidence.

## Actual runtime

| Component | Observed version / identity |
| --- | --- |
| Host Python | 3.12.0; `C:\Users\wai19\.unsloth\studio\unsloth_studio\Scripts\python.exe` |
| Host installed dependencies | HTTPX 0.28.1, PyJWT 2.12.1, cryptography 46.0.7 |
| Docker client / Engine | 29.2.1, API 1.53 |
| Desktop / WSL2 kernel | 4.65.0 (221669); 6.6.87.2-microsoft-standard-WSL2 |
| Worker image | `sha256:35b089054ac9b4257976107e71673d9e30ac17c9b50bbf8b4783f2f6d1d1981f` |
| Transport interpreter | `/usr/local/searxng/.venv/bin/python -I -B`; Python 3.14.5 |
| Transport dependencies | HTTPX 0.28.1, httpcore 1.0.9, certifi 2026.5.20 |
| Evaluator interpreter | `/usr/sbin/python3 -I -S -B`; Python 3.14.5, stdlib only |
| Proxy image | `ubuntu/squid@sha256:6a097f68bae708cedbabd6188d68c7e2e7a38cedd05a176e1cc0ba29e3bbe029` |
| Proxy executable / user | Squid 6.13, `/usr/sbin/squid`, UID/GID 13 |

Worker/evaluator UID is 65534, read-only root, dropped capabilities,
no-new-privileges, 32 PIDs, 128 MiB and one CPU. The proxy tag used for pulling
was `6.6-24.04_beta`; the executable reports 6.13, so the digest and observed
version above govern this report. No package installation or upgrade was needed.

## Fresh validation

| Run | Result |
| --- | --- |
| Final sealed native Docker/Squid/TLS review | All 14 cases passed |
| Final sealed focused stdlib checks | 15 tests passed, 0.491 seconds |
| Final sealed registration crypto checks, separate dependency-bearing run | 3 tests passed, 0.102 seconds |
| Final workspace trading stdlib regression | 182 tests passed, 35.072 seconds |
| Final receipt/source verification | 73 sealed hashes, 67 working source matches, all 14 case hashes passed |
| Whole-review replay | Refused before Docker invocation; saved marker/receipt bytes unchanged |
| Final independent cleanup check | No `kwg-supported-` containers or networks remained |
| Production registry | Empty, unchanged; zero production reservations |
| Wrong manifest hash / sandbox write and registry access | Refused |
| Patch hygiene / PowerShell syntax | `git diff --check` and script syntax checks passed |

Separate runs are not combined into a fictitious full-suite count. No frontend
build was required because no frontend source changed.

| Native case | Expected observed state |
| --- | --- |
| success | completed; exactly one fake POST; credential-free parser |
| account_mismatch, client_mismatch, expired, missing | binding_refused before transmission |
| 401, bad_usage, redirect, truncated, malformed | transport_failed |
| timeout, trickle | watchdog_exit; outcome_unknown, attempt consumed |
| crash | worker_failed; attempt consumed |
| interrupt | interrupted before transmission; cleanup passed |

Every case verified cleanup and replay refusal. The success case exercised
actual host/service, peer, direct Internet, DNS, UDP DNS, IPv6, forbidden proxy
destination/port, plain HTTP, untrusted TLS, ambient environment, file/socket
absence and read-only write probes. A normal bridge positive control reached
an inert Windows listener and TCP `1.1.1.1:443`; an outer-network control reached
the fake server over IPv4 and IPv6. The isolated worker was denied those direct
connections. The Internet IPv6 denial did not have a corresponding Internet IPv6
positive control, so it is not standalone proof of universal IPv6 containment.

### Commands used

Run from the repository root. Owner-context execution was required for the
Docker pipe, seal creation, private synthetic receipts and registry checks.
It did not involve the OAuth credential store.

```powershell
# This source was committed before sealing; preserve the existing snapshot.
& ./ops/trading/harden-batch3.ps1 -Phase seal-supported
$taskCodePath = Join-Path (Get-Location) '.batch3-vibe/sealed-supported-0e6db2bf3b22/code'
python -I -B (Join-Path $taskCodePath 'supported_gateway.py') --seal-sha256 dd143b7a5de1d0cf66e14cb947cdeb9681ad3aa07c7479e86ca22dba9667c115
python -I -S -B -c "import sys,unittest;sys.path.insert(0,sys.argv[1]);r=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromNames(['test_supported_gateway','test_supported_oauth_transport','test_trusted_gateway','test_trusted_oauth_transport']));sys.exit(not r.wasSuccessful())" $taskCodePath
python -I -B -c "import sys,unittest;sys.path.insert(0,sys.argv[1]);r=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromName('test_register_gold_oauth'));sys.exit(not r.wasSuccessful())" $taskCodePath
python -I -S -B -c "from pathlib import Path;import sys,unittest;sys.path.insert(0,'ops/trading');names=sorted(p.stem for p in Path('ops/trading').glob('test_*.py') if p.stem!='test_register_gold_oauth');r=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromNames(names));sys.exit(not r.wasSuccessful())"
python -I -S -B .superpowers/sdd/supported-gateway-final-20261003/verify.py
git diff --check
```

Seals, review reservations and verification outputs are exclusive: repeating
their creation refuses. Do not delete or rename consumed attempts to retry.
Creating a later seal must follow a new review of its exact committed sources.

## Preserved failures and limits

Earlier development probes remain in the
[initial implementation checkpoint](2026-10-03-batch3-supported-gateway-progress.md).
The initial committed seal `06589bdd4e92` failed its first 401 setup before
transmission; its receipt and consumed attempt remain, with cleanup/replay
verified. Docker assigns usable fake server addresses after start, and its
inspection output can contain nullable network fields. Those causes were fixed
in subsequent commits; the passing `06a292389471` snapshot and all historical
snapshots remain. The final `0e6db2bf3b22` snapshot also records consumed attempts
and conservative unknown outcomes. No failed receipt was rewritten.

The interruption case exercises a caught SIGINT before sending input. It does
not establish cleanup after forced controller termination, SIGKILL, machine
shutdown or power loss. Process watchdogs bound child execution, but cannot
guarantee removal of all Docker resources after those events. Review that
failure mode before production activation if required by its boundary policy.

The fake CA, certificate/key and proxy hostname mapping are test fixtures only.
Both proxy networks are internal and isolated; there is no Internet-facing proxy
or live credential channel. Production egress/DNS policy and actual credential
process containment need their own reviewed acceptance evidence. Fake success
does not set `production_isolation_verified`.

Local 180-second process and 120-second stream processing limits, byte limits
and disconnects do not establish backend cancellation or a monetary ceiling.
The timeout/trickle native cases use a fixed three-second worker alarm to test
that watchdog path; production default is 180 seconds. Output usage above 2,048
tokens is deliberately accepted when valid; no provider token-cap claim is made.

Final real flags remain: `production_isolation_verified=false`,
`server_account_verified=false`, `billing_ceiling_verified=false`,
`model_requests=0`, dispatch blocked, qualification unqualified and promotion
blocked. Registration was already completed in the prior scope; do not repeat
it or overwrite existing credentials. Account acceptance, saved provider $0
enforcement and one explicitly authorized real proposal remain later gates.
