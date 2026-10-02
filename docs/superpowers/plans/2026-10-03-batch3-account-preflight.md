# Batch 3 account acceptance — local preflight

Historical expired-login checkpoint. Subsequent owner-authorized renewal and
account acceptance [passed with `gpt-6-astra`](2026-10-03-batch3-account-acceptance-results.md).
The original preflight and its unchanged receipt remain recorded below.

Date: 2026-10-03, Asia/Bangkok. Owner authorized the account-connection milestone
after completion of the fake gateway. **Account acceptance is incomplete:**
the saved gold access token is expired. The real model-catalog check did not run.

## Verified now

At `2026-10-02T19:46:34.809455+00:00` (October 3, 02:46 Bangkok), the read-only
owner-context check confirmed:

- The separate gold auth directory and registration/client/host/receipt/helper
  files permit only the owner and SYSTEM; the directory disables ACL inheritance.
  Paths were checked for reparse points. The coding sandbox was separately
  denied reading both the registration and the new preflight receipt.
- Local issuer, subject, issued client, audience and host mappings are consistent.
  Required scopes are present, and the original receipt records signed identity
  validation at registration. This check does not establish a fresh signature
  attestation or server account acceptance.
- Both access and retained identity tokens are expired. A separate five-minute
  freshness guard also fails. No token or identity contents were printed.
- The saved registration helper matches the final supported source snapshot.
  All 73 snapshot files passed existing manifest verification before this check.
- Original registration, issued-client, host, registration receipt and helper
  bytes remained unchanged. No refresh, reauthorization or model request ran.

The exclusive redacted private receipt is
`.batch3-vibe/gold-plan-auth/account-preflight-20261003.json`, SHA256
`658422c44e5fd746b226d0b9547bab13c52f50ed4b9a7badbcb3c69aa4099ca8`.
Its ACL was checked after creation and its saved bytes were read back and compared.
It contains booleans and source identity, not credentials or account identifiers.

The operational probe is
`.superpowers/sdd/gold-account-preflight-20261003/preflight.ps1`, run from the repo
root as the owner with:

```powershell
& ./.superpowers/sdd/gold-account-preflight-20261003/preflight.ps1
```

It uses sealed existing `verify_seal`, `strict_json` and `write_once` helpers;
Python remains `-I -S -B`. It has no HTTP or renewal implementation. Its receipt
creation is exclusive, so repeating this command will refuse rather than replace
the evidence. The probe and sandbox-denial record are mutable development
artifacts ignored by Git. No application source changed or regression rerun was
needed; historical test totals are not labelled fresh here.

## Why the authenticated check stopped

The [approved plan, gate A](2026-10-03-batch3-supported-gateway-plan.md)
explicitly says: “If expired, stop.” It calls for separately reviewing a minimal
renewal path with atomic private persistence. The current registration helper is
one-time and intentionally refuses an existing registration. Running that helper
again cannot renew it. Do not delete the registration or switch to another login.

The production credential/Internet boundary also remains unverified. The prior
fake gateway used two isolated internal networks and a fake CA/host mapping;
it cannot be relabelled as an Internet-ready model-catalog transport. No real
credential was supplied to a container during this preflight.

## Smallest reviewed renewal scope

This is a proposed next implementation scope, not an executed refresh:

1. Reuse the same issued client, selected gold account and stable host mapping.
   Keep the Vibe login untouched. Establish an exclusive per-registration lock
   and a durable started marker before any renewal request.
2. Build and seal a narrow authentication-only worker using existing pinned
   Docker/HTTPX and Squid components. Permit only the documented auth destinations
   and verified public TLS, with no fake CA, arbitrary endpoints, redirects,
   retries or general worker egress. Exercise failures, isolation and forced
   controller termination with synthetic credentials before transferring secrets.
3. Use one documented refresh grant, with the saved issued client, refresh token
   and resource. Validate returned bearer type, required scopes, expiry and exact
   account/client binding. Verify any renewed ID token against published signing
   keys; do not fabricate a nonce or label retained expired identity as fresh.
4. Publish the complete validated token set together under the lock using a
   private same-directory pending file, flush/fsync and atomic replacement.
   Verify ACLs before publication. Preserve evidence privately; never copy
   credentials into the repository, a report, logs or a command argument.
5. A timeout or interruption after transmission can leave rotation unknown.
   Keep the started attempt consumed and refuse automatic retry. Failed or
   unvalidated responses cannot replace the saved record. If recovery needs
   interactive sign-in, use the same issued client and a separately reviewed
   returning-account flow; never repeat dynamic client registration implicitly.
6. Recheck freshness and account binding, then resume the reviewed model-catalog
   boundary. Only the fixed authenticated catalog GET is in account acceptance;
   strategy generation, spending-control changes and trades remain excluded.

This renewal approach follows the provider's
[account/session documentation](https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions),
[token reference](https://developers.openai.com/siwc/token-sharing-open-source/token-reference)
and [registration identity rules](https://developers.openai.com/siwc/token-sharing-open-source/sign-in).
The future catalog must parse the documented `models` array and model `slug`,
as specified in [models and inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference);
generic API-key catalog examples are insufficient evidence for this route.
Context7 was queried; it supplied general API examples rather than this preview's
renewal/account contract, so direct official pages supplied the specific rules.

Final state: credential network requests zero, model requests zero, dispatch
blocked, production isolation/server account/$0 billing verification false.
The $0 gate and one explicitly authorized real proposal remain separate later
work. Batch 2 qualification stays deferred.
