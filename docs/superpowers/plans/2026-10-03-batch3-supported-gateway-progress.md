# Batch 3 supported gateway — implementation checkpoint

**Historical initial checkpoint.** The fake-only controller, 14-case native
matrix, private registry and committed source seal have since completed. See
[final implementation results](2026-10-03-batch3-supported-gateway-results.md)
for the current status, exact seal and fresh checks. The partial status and
source hashes below describe the earlier checkpoint and are preserved as history.

Date: 2026-10-03, Asia/Bangkok. Local fake-only continuation of the
[milestone plan](2026-10-03-batch3-supported-gateway-plan.md).

Runtime feasibility and an initial real Docker/Squid topology have been
demonstrated. The public transport has a tested fake-only core. This is **not
the final implementation seal or production isolation acceptance**. Phase 2's
controller binding/watchdog integration, Phase 3's complete isolation/failure
matrix and Phase 4's registry/seal work remain open. Account acceptance, credit
settings and inference remain separate later gates. Batch 2 stays unqualified
with qualification deferred.

## Reuse and change map

| Existing source | Reuse / finding |
| --- | --- |
| `batch3_runner.py` | Existing fixed local Docker pipe, pinned image, proposal byte bound and exclusive receipt writer; source unchanged |
| `trusted_gateway.py` | Existing seal verification, synthetic reservation, fixed production/readiness registries, pre-input inspect, parent deadline and cleanup; source unchanged |
| `trusted_oauth_transport.py` | Reuse duplicate-key/nonfinite JSON rejection; legacy URL, binding and token-cap behavior remain intact; live dispatch still raises before file/network access |
| `research-gold.py`, `gold_experiment.py`, `gold_signal.py` | Existing proposal validation; all three are required in the worker's minimal code mounts |
| `harden-batch3.ps1` | Owner-only stable-handle copying and historical input checks remain intact; a supported-route seal must be added later |
| Registration helper/launcher/tests | Traced without running registration or opening its private store; launcher uses installed HTTPX/PyJWT/cryptography; still outside the historical seal |
| `supported_oauth_transport.py` (new) | Narrow fixed public Responses core; accepts only synthetic `FAKE_CANARY_` tokens and injected fake HTTP; no credential-store reader or live CLI |
| `test_supported_oauth_transport.py` (new) | Focused request/stream/usage/failure checks; no installed HTTP dependency required |

The existing Docker runner remains the selected approach. Host-only HTTP flags
cannot establish OS containment; a full app-server integration introduces tools
and authority unnecessary for one proposal. Reusing the image's existing
virtualenv avoids adding Python packages. A standard Squid process supplies the
CONNECT boundary; no custom proxy or agent framework was built.

## Runtime inventory

| Component | Observed value |
| --- | --- |
| Host Python | 3.12.0; `C:\Users\wai19\.unsloth\studio\unsloth_studio\Scripts\python.exe` |
| Host dependency-bearing invocation | HTTPX 0.28.1, PyJWT 2.12.1, cryptography 46.0.7 |
| Docker client / Linux Engine | 29.2.1 / API 1.53 |
| Desktop / kernel | Docker Desktop 4.65.0 (221669); 6.6.87.2-microsoft-standard-WSL2 |
| Existing worker image | `sha256:35b089054ac9b4257976107e71673d9e30ac17c9b50bbf8b4783f2f6d1d1981f` |
| `/usr/sbin/python3 -I -S -B` | Python 3.14.5; HTTPX/JWT/cryptography unavailable; system CA bundle present |
| `/usr/local/searxng/.venv/bin/python -I -B` | Python 3.14.5; HTTPX 0.28.1, httpcore 1.0.9, certifi 2026.5.20; JWT/cryptography unavailable |
| New proxy image | `ubuntu/squid@sha256:6a097f68bae708cedbabd6188d68c7e2e7a38cedd05a176e1cc0ba29e3bbe029` |
| Proxy executable/user | `/usr/sbin/squid`; Squid 6.13; UID/GID 13 |

The proxy image was pulled via the documented `6.6-24.04_beta` tag, but its
executable reports **6.13**. The recorded digest and observed executable version,
not the tag's apparent version, are the identities for subsequent review.
The existing worker image is reused at its existing digest. Crypto remains a
host-side fake-certificate/test dependency; it has not been added to the worker.

The coding sandbox cannot open the Docker engine pipe. Owner-context tool
execution was used for these bounded local probes. No owner credential directory
was opened. Existing stdlib checks retain `-S`; dependency-bearing checks use
`-I -B` separately. No package upgrades or frontend changes were made.

## Current transport behavior

The fake core makes one POST to the fixed public Responses URL using array input,
`store=false`, `stream=true`, gpt-6.1-sol and medium reasoning. It omits tools,
private-route fields and `max_output_tokens`. HTTPX uses explicit connect/read/
write/pool limits, `trust_env=false`, no redirects and verified TLS.

The parser bounds the raw stream to 262,144 bytes, an SSE event to 65,536 bytes,
proposal text to 16,384 bytes and local stream processing to 120 seconds. It
requires completed status, a consistent response ID/model, completed output
matching the deltas and valid usage. It refuses duplicate terminal events,
truncation, malformed data, tools and failure/usage-limit events after partial
text. Usage above 2,048 output tokens can pass; no server token-cap claim is made.
Unknown usage fields are rejected rather than copied to receipts.

The core's time checks do **not** replace the independent process watchdog.
HTTPX read timeouts bound inactivity, and buffered reads can delay delivery to
the parser. Integrating the existing parent and PID1 watchdogs is still required.
Timeout or local disconnect cannot establish backend cancellation, zero usage
or zero cost.

## Actual probes and receipts

Evidence is under `.superpowers/sdd/supported-gateway-phase1-20261003/`, ignored
by Git. It contains only fake TLS material, synthetic input and local runtime
metadata. It is a mutable development artifact, not an owner-private source seal.

1. `probe.py`: an internal dual-stack bridge with both gateway modes `isolated`,
   explicit worker DNS upstream `127.0.0.1`, read-only root/mounts, UID 65534,
   dropped capabilities and resource limits. A normal bridge control reached a
   temporary inert Windows host listener and resolved `example.com`; the
   isolated worker did neither, reached its fake peer, and had no default IPv4
   route. IPv4/IPv6 documentation-address connection probes failed. These
   reserved-address failures alone do not prove an Internet firewall. Cleanup
   was verified. Receipt SHA256:
   `c4bd2561c0fc4ef4e0f03d0ce3e25aa1bcc0cfa2eff51e2ad7fbbd107171db5f`.
2. `proxy_probe.py`, final `proxy-r5/receipt.json`: real pinned Squid on two
   isolated internal bridges, with the provider name mapped **only in the proxy**
   to a local fake TLS server. The worker reached that server through CONNECT,
   retained certificate validation with a test-only trust context, and the fake
   server observed exactly one POST. Unrelated domain, suffix-domain spoof,
   alternate port, literal destination IP, host-name destination and plain HTTP
   were refused. Untrusted TLS and direct access to the fake server were refused.
   Every host bind mount was inspected read-only before start; all owned
   containers, automatic volumes and networks were removed. Receipt SHA256:
   `9ffd598fc915b5b7f7c756ede78bf7cbc0361096f95a5d0138d94dd7fa0ef285`.

Earlier `proxy/` and `proxy-r2/` receipts preserve missing mount-depth/dependency
failures. `proxy-r3/` was a functional pass but had automatic writable image
volumes, so it is **not mount acceptance evidence**. `proxy-r4/` refused the
remaining automatic Squid volumes. Final r5 masks both runtimes' declared volumes
read-only and passes. All recorded probe attempts verified owned cleanup.

No proxy was attached to an Internet-facing network in the TLS probe. The fake
CA and provider hosts override are test configuration only. The future sealed
production configuration must never inherit either override. Host access by
explicit resolved addresses, arbitrary DNS packets/bypasses, other-container
access, production proxy DNS/destination policy, interruption/crash/timeout
cleanup, credential-free parser separation and durable replay must still be
covered by the Phase 3 matrix. The public transport has not been wired into the
production registry or a live credential channel.

## Fresh checks and exact commands

Twenty checks passed in **one focused stdlib run** (public core, existing trusted
core/gateway and Batch 3 rehearsal). Three registration tests passed in a
**separate dependency-bearing run**. These are not a full trading-suite result
or qualification evidence. `git diff --check` passed.

```powershell
python -I -S -B -c "import sys,unittest; sys.path.insert(0,'ops/trading'); result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromNames(['test_supported_oauth_transport','test_trusted_oauth_transport','test_trusted_gateway','test_batch3_rehearsal'])); sys.exit(not result.wasSuccessful())"
python -I -B -c "import sys,unittest; sys.path.insert(0,'ops/trading'); result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromName('test_register_gold_oauth')); sys.exit(not result.wasSuccessful())"
python -I -S -B .superpowers/sdd/supported-gateway-phase1-20261003/probe.py
python -I -B .superpowers/sdd/supported-gateway-phase1-20261003/proxy_probe.py
```

Probe output directories are exclusive and preserved; repeating those commands
at the same paths refuses creation. Use reviewed copies at new output paths for
future probes; do not delete receipts to retry. Dependency checks do not launch
the registration helper's `main()` or contact authentication endpoints.

Current transport/test source SHA256 values, respectively:
`671b7f24f30ff81f4c4f91134c139266acc83695ddb7f3310e3e753740931961`,
`2731fd9912ffe655a136944f8e05cbc6912c90e983429f43c70f54409276fbb8`.
These are checkpoint identities, not a final committed-code seal. No commit,
production reservation, credential transfer, billing change, provider request,
broker action or qualification run occurred.

## Next implementation gate

Finish the existing controller's distinct supported fake mode: verify the
synthetic account/client binding, fixed runtime/configuration and exact minimal
mounts before transferring input, install its independent watchdog, retain
exclusive attempt records and exercise all failure/cleanup paths. Then integrate
the separate fake registry, review/commit eligible sources (including registration)
and create a distinct supported-route seal. Preserve legacy seals and the
synthetic-only production-reservation guard. Real verification flags remain false.

Documentation was checked with Context7 for Docker/HTTPX and direct primary
sources for the preview-specific contract:

- [Docker gateway modes](https://docs.docker.com/engine/network/port-publishing/)
- [HTTPX timeouts](https://github.com/encode/httpx/blob/master/docs/advanced/timeouts.md)
- [HTTPX raw streaming](https://github.com/encode/httpx/blob/master/docs/quickstart.md)
- [OpenAI public model/inference route](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
- [OpenAI preview request limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)
- [Canonical Squid image](https://hub.docker.com/r/ubuntu/squid)
- [Squid ACL lookup suppression](https://www.squid-cache.org/Doc/config/acl/)
- [Squid access rules](https://www.squid-cache.org/Doc/config/http_access/)
