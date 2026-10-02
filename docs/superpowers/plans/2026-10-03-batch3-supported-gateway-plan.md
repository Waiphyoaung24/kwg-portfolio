# Batch 3 — supported OAuth gateway and isolation plan

Date: 2026-10-03, Asia/Bangkok. Status: proposed implementation plan; no implementation or live dispatch authorized by this document.

Continuation: the [fake-only milestone is complete](2026-10-03-batch3-supported-gateway-results.md).
The owner subsequently authorized account acceptance. Its
[local preflight](2026-10-03-batch3-account-preflight.md) found expired access and
identity tokens; gate A remains incomplete pending reviewed renewal and the real
credential/Internet boundary. Real dispatch remains disabled. Historical starting
evidence below describes the earlier plan-writing checkpoint.

## Outcome and scope

Build and seal the smallest supported ChatGPT plan-usage transport that can pass realistic isolation tests using fake credentials. Keep real model dispatch disabled. Completion means the production boundary is ready for a separate account and billing acceptance review; it does not mean Batch 2 is qualified or Batch 3 is allowed to spend.

The owner selected the supported OAuth route and accepted replacing the provider-enforced 2,048-token ceiling with local byte and time bounds. The mandatory ceiling remains **$0 additional spend**. The latest operational authorization was OAuth registration only, with no credits. This planning request does not expand that authorization to account-setting changes or inference.

Use the existing runner, strict proposal validator, simulator, comparison, report review, private registry, seal verification and watchdog. Do not build a new agent framework, broker integration, dashboard, scheduler, credential manager or generalized provider layer.

## Starting evidence

| Area | Current position | Consequence |
| --- | --- | --- |
| Batch 2 | Development complete; qualification explicitly deferred | Do not reopen development or count smoke tests as qualification |
| Batch 3 offline flow | Structured proposal → validation → simulator → comparison → report review works; production pages connected | Reuse this flow; no website changes |
| Earlier gateway readiness | Historical 65-file seal, five fake Docker cases and 176 Python checks recorded in HANDOFF | Preserve those receipts; they do not validate a new transport |
| Separate gold OAuth | KWG Gold Research registration completed; signed identity verified; separate owner/SYSTEM credential storage; callback helper exited | Do not repeat registration or overwrite Vibe credentials |
| Registration result | Zero model requests; dispatch blocked; billing verification false | Registration is identity evidence, not spending authorization |
| Current gateway | Fake HTTP in network-disabled containers; live dispatch deliberately refuses calls | Networking alone cannot enable a safe real gateway |
| Existing transport | Private backend route, legacy token binding and token-cap assumptions | Add a narrowly scoped public-route implementation; preserve historical behavior |
| Latest local checks | 49 targeted existing checks and three registration tests passed in the preceding work | These are separate historical runs, not a fresh full-suite result |
| Unsealed work | Registration helper, launcher and tests are not in the earlier committed seal | Review and include them in a new eligible source snapshot before claiming a final seal |

Token freshness has not been rechecked for this planning milestone. Registration does not implement renewal. An expired token must fail closed; never silently rerun registration, replace the saved record or assume refresh works.

## Approaches considered

| Approach | Benefit | Limitation | Decision |
| --- | --- | --- | --- |
| Host-only HTTPX transport | Fewest moving parts | Client flags do not isolate credentials or enforce OS-level egress | Insufficient for the stated production boundary |
| Existing Docker controller plus a constrained public transport and fixed egress boundary | Reuses the audited runner and existing cleanup/registry mechanisms | Requires actual Windows/Docker isolation proof and a runtime dependency check | Recommended, subject to Phase 1 feasibility |
| Full Vibe or app-server agent integration | Broad existing agent functionality | Introduces unnecessary tools, retries and authority for one structured proposal | Defer; no present need |

The recommended topology is a design proposal, not a statement that the current host already supports every required control. Use a native enforceable egress policy if it satisfies the tests. Otherwise use one established, narrowly configured egress proxy; do not write a custom proxy service.

## Proposed boundary

1. The existing owner controller verifies the sealed source, fixed registry, policy and packet before any credential transfer. It owns lifecycle and receipts.
2. A short-lived transport worker receives only the required access token through a private input channel. Do not mount the registration directory, refresh token, ID token, user home, Vibe credentials, Docker socket or repository into the worker.
3. The worker has a read-only pinned runtime, an unprivileged user, dropped capabilities, resource limits and no writable host mounts. The proposal parser/simulator remains credential-free.
4. The worker has no general outbound route. The candidate Docker design uses an internal isolated network and a separate egress boundary that permits only TLS connections to `api.openai.com:443`. The boundary has no OAuth credentials. The actual Docker engine must support and enforce this topology.
5. Keep end-to-end TLS verification. A CONNECT proxy restricts destination, not encrypted HTTP paths or request counts. The sealed transport must enforce method/path, request count and redirects independently; do not claim the proxy proves those properties.
6. Deny direct IPv4/IPv6 egress, unrelated destinations, host services and arbitrary DNS from the worker. Any necessary resolution belongs at the fixed egress boundary and must be tested for bypasses.
7. Fake endpoint configuration is a separately sealed test configuration. Production must not accept an arbitrary endpoint, proxy, model or credential path through command-line arguments or environment variables.

`--internal` alone is insufficient: Docker documents possible access to host services via an internal bridge. Check isolated gateway support and probe actual host reachability. If the required denial cannot be proved on this Windows/Docker installation, stop before introducing real credentials and document the missing platform control. Do not fall back silently to host networking.

## Phase 1 — map reuse and prove runtime feasibility

**Work**

- Trace `trusted_gateway.py`, `trusted_oauth_transport.py`, `batch3_runner.py`, `harden-batch3.ps1`, registration helpers and their tests end to end.
- Record existing image digest, Docker engine/network capabilities, mount policy, watchdog behavior, dependency availability and current production dispatch refusal.
- Reuse existing HTTPX/JWT dependencies where the sealed runtime can support them. The host's installed Python packages do not prove they exist in the container.
- Choose the smallest reproducible runtime: retain the image if it can satisfy the requirements; otherwise pin only the required runtime/dependencies and CA trust. No blanket package upgrades.
- Check import isolation explicitly. Existing `-I -S -B` test invocations disable site packages, while the registration tests require installed crypto/HTTP packages. Preserve isolated tests where applicable and document a separate locked-dependency invocation; do not silently remove `-S` everywhere.
- Probe the proposed network topology with fake credentials and inert requests only. Record observed behavior and platform versions.

**Deliverables**: reuse/file-change map, runtime/dependency inventory, network decision with probe evidence, list of unsupported controls if any.

**Exit criteria**: a reproducible runtime and enforceable topology are demonstrated without opening the real credential store or sending provider requests. Otherwise record a blocked platform gate and stop dependent work.

## Phase 2 — implement the public transport with fake HTTP

**Likely files**: one small adjacent public-route transport module and its focused tests; minimal shared-gateway changes only where reuse is safe. Keep `trusted_oauth_transport.py` legacy semantics intact unless a shared defect requires a surgical fix.

**Request contract**

- Fixed public Responses endpoint, one POST, no automatic retries, redirects, fallback provider, tools or agent loop.
- Use `store: false`, `stream: true`, array-form input and supported instructions/developer-message fields. Do not send the unsupported `max_output_tokens` field or copy incompatible private-route fields.
- Require the selected account's exact model availability before a later live attempt. Do not substitute a different model when unavailable.
- Set `trust_env=False`, preserve certificate validation and configure any deliberate approved proxy explicitly. Environment proxy suppression is not OS isolation.
- Apply explicit connect/read/write/pool timeouts plus the existing independent wall-clock watchdog. A read timeout only limits inactivity between reads.

**Response contract**

- Bound total received bytes, event size, assembled proposal bytes and elapsed time. Define transport framing allowance separately from the existing 16,384-byte proposal limit, with a fixed reviewed ceiling.
- Require a valid terminal completion event before accepting a proposal. Reject truncated streams, malformed or duplicate terminal events, provider failure events, missing usage, identity/model inconsistencies and invalid structured output.
- Explicitly reject plan-sharing usage-limit/unavailable failures even if partial text arrived first. Partial text never becomes an accepted proposal.
- Validate reported usage shape and consistency, but do not reintroduce a claimed server-enforced 2,048-token cap. Preserve legacy fake tests that depend on that old cap in their original mode.
- Local cutoff means consumption and backend completion may be unknown. Do not claim backend cancellation, zero usage or zero cost from a timeout.
- Never log tokens, authorization headers, callback codes or raw sensitive account responses. Use private binding metadata and redacted receipts.

**Exit criteria**: fake success and each failure path have deterministic tests, one POST is proved by the fake server, and production dispatch still rejects every invocation.

## Phase 3 — enforce isolation and cleanup

**Likely files**: existing gateway and hardening launcher, with the smallest necessary fixed network/runtime configuration.

**Work**

- Add a distinct fake supported-route test mode; retain existing readiness mode and historical fixture identities.
- Use only synthetic credentials and the separate readiness registry. Do not read the real OAuth record during these tests.
- Probe credential and filesystem isolation: no host home, unrelated credentials, repository writes, Docker control socket or access from a credential-free parser.
- Probe network isolation: permitted fake route succeeds; direct provider/Internet access, unrelated hostnames, host gateway/services, alternate ports, environment proxies, IPv6 and arbitrary DNS fail.
- Test redirects and alternate endpoint injection at the application boundary as well as network denial at the OS boundary.
- Exercise timeout, worker crash, malformed output and interrupted controller cleanup. Remove only resources owned by the recorded attempt, including its worker, proxy and network.
- Confirm cleanup never deletes attempt records or permits a retry under the same attempt identity.

**Exit criteria**: actual Docker probes pass, configuration is captured in a redacted receipt, owned resources terminate on every tested failure and no real credential/provider call was used.

## Phase 4 — integrate registry, receipts and a new seal

**Work**

- Reuse the fixed private production registry and durable exclusive reservation. Keep fake and production identities/registries separate.
- Do not relax the current synthetic-only `reserve` guard globally. Add an explicit reviewed live-packet path only in the later activation milestone; this milestone leaves it unreachable.
- Define attempt states conservatively: reserved, started, completed, failed and outcome-unknown. Once request transmission might have occurred, ambiguity consumes the attempt. No automated retry or alternate model fallback.
- Bind receipts to packet/source/policy hashes, runtime/image digest, network configuration, model, account/client binding hash and source seal. Keep identity data private.
- Keep separate facts for registration verified, server acceptance verified, isolation verified and billing ceiling verified. Fake success cannot set real verification flags.
- Review and commit the exact intended sources before producing a new clean-source seal during implementation. Include dependency/runtime and network-policy identities in the review; the old 65-file seal does not cover the new route.
- Adapt sealing narrowly: existing hardening checks historical worker/fixture hashes, so preserve those historical mode assertions and add a distinct supported-route seal rather than rewriting old receipts.
- Verify every new sealed hash, mutation refusal and replay refusal. Re-run relevant focused checks against the sealed runtime, then required regression checks once.

**Exit criteria**: reproducible new seal and private redacted receipts exist; no production attempt was reserved; live dispatch and billing verification remain blocked/false.

## Test matrix for the implementation milestone

| Boundary | Required cases | Pass condition |
| --- | --- | --- |
| Request | Supported fields, unsupported fields, URL/model override, redirect, proxy environment | Exact fixed request; invalid input fails before dispatch |
| Streaming | Completed, partial then failed, EOF, malformed SSE, oversized frame/output, missing usage | Only complete valid structured output passes |
| Limits | Slow connection, stalled reads, endless trickle, worker crash | Independent deadline and bounded memory; owned cleanup |
| Identity | Wrong client/account binding, expired registration, missing record | Fail closed; no automatic registration/refresh |
| Isolation | Host files/services, other containers, direct egress, DNS, IPv6, alternate destination | Denied by the actual runtime boundary |
| Attempt accounting | Duplicate, concurrent reservation, timeout/unknown outcome | Exclusive durable attempt; no reuse or retry |
| Seal | Modified source/config/runtime identity, missing file | Refused before credential transfer |
| Regression | Existing fake gateway, registration, proposal validation and offline comparison | Existing behavior preserved |

The implementation report must include exact commands, runtime versions and results. Separate stdlib-only checks from dependency-bearing checks. Do not label historical checks as fresh, or sum separate runs into a full-suite count. No frontend build is required unless frontend files actually change.

## Later gate A — account acceptance, without inference

This is a separate execution scope after fake-only acceptance. Do not run it as part of this plan-writing task.

- Recheck the exact private registration's ACLs, expected issuer/client/subject binding and freshness without printing credentials. The registration helper verified the original nonce at registration; do not invent a replacement nonce for later token checks.
- If expired, stop. Design/review a minimal supported renewal path separately if needed, with atomic private persistence; no automatic overwrite or re-registration.
- Through the verified production boundary, perform only the documented authenticated model-catalog GET using the same gold access token. Correlate authorization acceptance with the already verified signed identity; a models listing alone is not a fresh identity attestation.
- Confirm the required model is present. Missing account/model evidence remains blocked; no substitute credentials or models.
- Produce a private redacted account-acceptance receipt. Do not reserve or send an inference attempt.

## Later gate B — verify the $0 additional-spend control

This remains deferred by the owner's “no credit for now” instruction. Reading applicable evidence can be planned; do not enable credits, purchase credits, add payment methods or change settings implicitly.

- Locate the exact new gold integration in the account's current app-usage controls and verify account/client correspondence.
- Establish the provider's documented prevention of credit usage for this exact route. The proposed conservative configuration is app credit use disabled and a nonzero per-app limit below 100%, if those controls are available and applicable to this account.
- Any needed setting change requires its own owner authorization. Capture saved-state evidence and recheck it immediately before any eventual live dispatch.
- Keep auto-reload, credit balance and per-app credit access distinct. A displayed zero balance, account subscription, local dollar counter or OAuth success is not an enforceable additional-spend ceiling.
- If the exact account lacks a verifiable provider-side control, or the documentation/UI cannot establish applicability, leave real dispatch blocked. Do not replace the $0 requirement with a local estimate.

**Gate result**: verified included-usage-only enforcement, or an explicit unresolved blocker. A locally maintained boolean is only a receipt of evidence, never the control itself.

## Later gate C — one real development-only proposal

Only consider this after gates A and B pass and the owner explicitly authorizes the concrete attempt.

1. Prepare a real-data development packet using existing Batch 2 reconciliation/provenance helpers where possible. The current Batch 3 adapter is synthetic-only; do not relabel a synthetic fixture as real. Add only the minimum real-data adapter path needed at that time.
2. Freeze packet, baseline, allowed proposal schema, limits, account/model binding and final runner seal. Exclude untouched holdout data and preserve all unqualified/provenance limitation labels.
3. Recheck freshness, isolation and provider credit prevention. Reserve exactly one durable production attempt immediately before the approved request, using the final sealed identity.
4. Make one request with no retries, fallback, tools or trade authority. Failed or unknown outcomes stay consumed.
5. Run the existing validator, simulator and fixed-baseline comparison; retain all diagnostics and review the report. A proposal or favorable comparison does not promote a strategy.

Do not weaken risk limits, qualification requirements, human promotion approval or order controls in any phase.

## Batch 2 — deferred qualification workstream

Batch 2 needs evidence accumulation and a reproducible qualification run, not another development close-out.

- Obtain dated applicable broker commission/swap costs and clock/DST/session evidence. Resolve provenance gaps before treating data as qualified.
- Preregister the future qualification run and retain every required diagnostic, including failures. Keep the fixed baseline and untouched holdout discipline.
- Accumulate the required 60 observed validation days, three flat folds of at least 20 days, and 100 closed simulated trades per strategy, according to the existing qualification policy.
- Reproduce real-data results against the fixed baseline and apply the unchanged evaluation, risk, performance, stress and bootstrap gates.
- Require the existing human promotion decision. Smoke runs, fictional comparisons and prior inspected data earn no invented qualifying-day credit.

This workstream stays deferred unless separately resumed. Gateway completion is not Batch 2 qualification, and passing a development proposal comparison is not a shortcut to it.

## Definition of done and handoff

- [x] Public transport request/stream contract passes fake tests.
- [x] Real runtime credential/filesystem/network isolation probes pass with fake credentials.
- [x] Watchdog, cleanup, durable reservation and replay refusal pass.
- [x] New exact sources/configuration/runtime are reviewed and sealed; relevant regression checks pass.
- [x] Redacted evidence records what was tested and what remains unverified.
- [x] Real dispatch is still disabled; production registry unchanged; real model requests zero.
- [x] Account acceptance and $0 billing verification remain explicitly pending unless separately authorized and actually completed.
- [x] HANDOFF and task plan reference the new receipts and remaining gate, without altering historical receipts.

Completed for the fake-only implementation scope on 2026-10-03. See
[final results](2026-10-03-batch3-supported-gateway-results.md) for the exact seal,
fresh checks and limits. Isolation checks used synthetic credentials and two
internal fake-service networks. Caught SIGINT before transmission was tested;
forced termination cleanup and production credential/Internet isolation remain
unverified. Later gates A–C are not completed by this checklist.

On failure, disable the new entry point, terminate owned transient resources and preserve all attempts/receipts. Do not roll back credential state automatically or delete failed attempts. The existing offline pipeline remains the usable baseline.

## Research and source limitations

Skills applied: Ponytail (reuse before adding infrastructure) and brainstorming (compare approaches, converge on the already selected route, write a reviewable plan before implementation).

Context7 was queried for OpenAI developer documentation, Docker documentation and HTTPX. Its OpenAI results did not establish the plan-sharing-specific request contract or account billing guarantee; direct official plan-sharing pages supplied those details. Context7 is documentation evidence, not verification of this account or machine.

- [OpenAI preview limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations): supported request shape and unsupported output-cap field.
- [OpenAI models and inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference): public Responses route, authenticated model catalog and terminal stream handling.
- [ChatGPT plan use in other apps](https://help.openai.com/en/articles/20001542-using-your-chatgpt-plan-in-other-apps-and-sites): app usage and credit controls; actual saved account state still needs verification.
- [Docker port publishing and gateway modes](https://github.com/docker/docs/blob/main/content/manuals/engine/network/port-publishing.md): internal bridge host access and isolated mode caveats.
- [Docker bridge networking](https://github.com/docker/docs/blob/main/content/manuals/engine/network/drivers/bridge.md): bridge connectivity behavior.
- [Docker network routing](https://github.com/docker/docs/blob/main/content/manuals/engine/network/_index.md): multi-network gateway selection.
- [HTTPX environment variables](https://github.com/encode/httpx/blob/master/docs/environment_variables.md): `trust_env=False` behavior.
- [HTTPX timeouts](https://github.com/encode/httpx/blob/master/docs/advanced/timeouts.md): separate connection/read/write/pool timeouts; no implied overall deadline.

Revalidate these preview contracts before implementation/activation. No documentation source replaces the fake OS probes or the later exact-account acceptance gates.
