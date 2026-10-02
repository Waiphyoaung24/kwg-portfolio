# Batch 3 production isolation and OAuth budget review

Review date: October 2, 2026 Bangkok. No inference, token/config contents,
broker access, service restart or ACL modification performed.

## Follow-up after sealed gateway readiness — October 2

The earlier checks table below is historical. Docker is now available and the
committed-code fake readiness review passed, as recorded in HANDOFF.md. This
does not turn its network-none, fake-credential worker into a live transport.

The existing `check_binding` helper was run in owner context after comparing
its source and runner bytes with the final f7bb8f058903 seal. It returned local
account binding=true and token_fresh=true; signature verification, server
account verification and billing verification remained false. Only sanitized
metadata was printed. No token contents, refresh or network requests occurred.
Freshness is a point-in-time check, not a guarantee for a future attempt.

Current official [pricing](https://learn.chatgpt.com/docs/pricing) distinguishes
included allowance, additional credits and API-key usage. The documented
[app-server account methods](https://learn.chatgpt.com/docs/app-server#authentication-endpoints)
include `account/read` with `refreshToken:false`, `account/rateLimits/read` and
`account/usage/read`. These expose account/usage information; this review found
no documented per-request USD0 or included-only enforcement for the pinned
Vibe private inference endpoint. A balance snapshot is not an enforced ceiling.
Context7's `/openai/codex` documentation confirms the separate account and
rate-limit methods. No Codex CLI account was substituted for the Vibe account,
and no externally managed token was supplied to an app-server process.

### Remaining production acceptance checks

- Bind any server-side read-only verification to the exact Vibe account hash;
  reject a different account, missing evidence or expired token. Keep local JWT
  claim consistency distinct from server acceptance.
- Establish a provider-supported USD0 boundary for this route. Owner-reported
  Pro/no paid credits/no top-ups and the approved budget remain recorded facts,
  not backend enforcement. No API-key or paid/model fallback.
- Review and seal the actual credential-owning transport separately from the
  credential-free proposal worker. Its OS boundary must exclude unrelated
  files and enforce only approved provider egress; Python isolation flags and
  HTTP URL checks alone do not establish either boundary.
- Before real credentials, verify denied filesystem/network access, fixed
  request destination, no redirect/proxy/retry, one POST, deadline and owned
  process cleanup using harmless credentials. The production attempt registry
  must remain separate from the fake readiness registry.

Do not enable `dispatch` or reserve a production attempt while these gates
remain unresolved. Existing fake receipts and the production registry are
unchanged; Batch 2 remains unqualified and human promotion approval required.

## Owner-approved budget

### Supported plan-usage route compatibility review

Official [models and inference documentation](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
specifies OAuth-authorized public Responses inference and a read-only model
catalog for the same account. It explicitly excludes ChatGPT backend-api
endpoints from that flow. This is a different integration from the pinned Vibe
Codex provider, not evidence that its existing login authorizes the public API.

The [registration documentation](https://developers.openai.com/siwc/token-sharing-open-source/sign-in)
requires an issued client registration, plan-usage scopes, and signed ID-token
validation. Reusing the existing account claim or changing the request URL is
insufficient. A future migration needs separate reviewed OAuth handling and
must preserve the current working learning workspace and credential store.

The [preview limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)
reject `max_output_tokens`. Therefore the documented route cannot currently
prove the required provider-enforced 2048-token ceiling. A byte limit, streaming
disconnect or timeout bounds local handling but does not prove stopped backend
generation or zero additional billing. Do not silently replace the token cap
with a prompt instruction or label a client cutoff as a provider guarantee.

Result: supported-route migration is not an unblock under current requirements.
Keep the existing dispatch guard. Before transport implementation, obtain a
documented applicable USD0 control and provider output cap, or an explicit owner
revision of the constraints with its practical limits recorded. No new OAuth
registration, model catalog request, credential refresh or inference was run.

Included ChatGPT subscription only; maximum additional spend USD 0; paid
fallback forbidden. This is the owner's approved ceiling, not verified backend
billing behavior. Do not substitute API token prices or record actual OAuth
cost as zero without applicable evidence. Included allowance consumption is
still usage and must be recorded separately from additional monetary spend.

Official [pricing documentation](https://learn.chatgpt.com/docs/pricing)
distinguishes included usage, purchased credits and API-key billing. Available
credits can fund eligible usage beyond included limits; rates alone do not
establish the account's included allowance. The pinned Vibe provider uses
chatgpt.com/backend-api/codex/responses. Its request has no verified
included-usage-only billing switch. New public plan-usage integration guidance
does not prove a billing control for that existing private endpoint.

## Checks completed

| Boundary | Evidence | Verdict |
|---|---|---|
| Private OAuth/config ACL | Read-only owner-context Get-Acl: auth directory, OAuth file, config parent and .env protected; only owner/SYSTEM FullControl | Passed at review time; no token/config contents read |
| Coding sandbox exclusion | Current sandbox access to private auth directory and harmless canary denied | Passed narrowly; does not exclude arbitrary owner-account processes |
| Sealed snapshot | 48 actual files matched saved manifest hashes; sandbox ReadAndExecute ACL on sealed root | Archived snapshot integrity passed; not a seal of all current development sources |
| Provider request guards | Pinned-source guard passed HTTP/error/tool/token/stream/response bounds with fake HTTP | Passed offline; zero real network requests |
| Fake authentication | Four tests passed: refresh failure/timeout/stale token blocks inference; 401 does not resend; outer deadline | Passed offline; real refresh locks/timeouts not verified |
| Fixture runner | Five rehearsal tests passed, fixed proposal worker and durable attempts | Passed for synthetic mode only |
| OS container boundary | Current Docker Linux engine pipe absent; no engine startup attempted | Current production verification unavailable |
| Live trusted transport | batch3_runner.run_fixture accepts only synthetic packets; no credential-owning production transport entry | Not implemented/verified |
| USD 0 enforcement | Owner ceiling recorded; provider/account fallback behavior not verified | Dispatch blocked |

The normal Vibe Agent remains a separate learning workspace. It can execute
multiple requests/tools as the credential owner and is not the bounded gold
proposal controller. Do not apply the research patch to that app to pretend
its whole agent is isolated.

## Work required before one real gold proposal

1. Verify account-level paid-usage controls or a documented included-only
   allowance applies to the actual request route. If that cannot enforce USD 0,
   keep dispatch blocked rather than estimating cost or assuming subscription
   means free. No automatic credit purchase, top-up, API fallback or model fallback.
2. Reuse the reviewed provider in a dedicated trusted credential-owning process.
   Keep proposal worker credential-free; require a durable single-attempt
   reservation, one inference POST, no tools, no redirects/proxies/retries,
   bounded input/output, 120-second HTTP timeout and 180-second outer deadline.
   Refresh before inference may use separate auth traffic; never resend a 401.
3. Verify real credential-store locking/refresh failure and returned model,
   usage/token-cap compatibility at the production boundary after budget is
   enforceable. Seal the exact current controller/provider/input identities.
4. Verify a supported OS boundary and owned-process cleanup with fake credentials
   before supplying real auth to the trusted process. A clean environment and
   Python -I/-S flags alone do not isolate the filesystem/network.
5. Prepare a real-data development-only packet with explicit unqualified status,
   provenance and cost/clock limitations under the owner's deferred-validation
   scope. No validation/holdout outcomes in model input. No synthetic assumptions
   may be promoted to verified broker evidence.

Batch 2 development is complete, qualification deferred. Risk limits and human
promotion approval stay unchanged. Real gold dispatch remains blocked by the
unverified production and billing boundaries, not by a new observation schedule.
