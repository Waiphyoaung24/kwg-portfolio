# Batch 3 production isolation and OAuth budget review

Review date: October 2, 2026 Bangkok. No inference, token/config contents,
broker access, service restart or ACL modification performed.

## Owner-approved budget

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
