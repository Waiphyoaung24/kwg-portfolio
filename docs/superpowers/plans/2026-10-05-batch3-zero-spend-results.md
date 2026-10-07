# Batch 3 — $0 additional-spend verification

Date: 2026-10-05, Asia/Bangkok. Gate B passed for the saved provider settings
observed today. Real inference remains disabled; gate C is unfinished.

## Saved provider controls

The account's unique `KWG Gold Research` connection, dated October 3, was opened
and its own **Manage usage** link followed to the provider's Usage page.
The saved state was observed at 14:19 Bangkok and recorded at 14:21 Bangkok.

| Control | Observed saved state |
| --- | --- |
| Gold app can use included plan allowance | Enabled |
| Gold app plan limit | 100% |
| Apps can use credits | Disabled (`aria-checked=false`) |
| Automatic credit reload | Disabled (`aria-checked=false`) |
| Save button | Disabled; no pending edits |

OpenAI documents that participating apps stop at the included usage limit unless
the owner enables app credit use and credits are available. The global preference
applies across participating apps. An app limit of 100% alone does not enable
credit use. These saved settings therefore establish included-usage-only
enforcement; a request would still consume included allowance.
Source: [Using your ChatGPT plan in other apps and sites](https://help.openai.com/en/articles/20001542-using-your-chatgpt-plan-in-other-apps-and-sites).

The original plan proposed a nonzero limit below 100% as an additional
conservative configuration. The documented disabled credit preference already
enforces the required $0 additional spending, so no limit change was needed.
Automatic purchases and permission to consume existing credits are separate
controls; both relevant switches were observed disabled.
See also [Sign in with ChatGPT usage settings](https://learn.chatgpt.com/docs/sign-in-with-chatgpt).

## Account correspondence and private evidence

The visible account email fingerprint matched the saved gold identity. Issued
client, token audience, subject and host binding matched retained registration
evidence. Current token bytes matched the previously validated renewal response.
The unique connection's name, date and its linked usage page correlated the UI
observation with the existing gold registration.

The UI did not expose a numeric OAuth client ID. This is account and connection
correlation using historical signed identity evidence, not a new signature check
or fresh server identity attestation. The saved access token is expired; no
refresh or authenticated catalog request ran today. The global credit preference
covers participating apps on the verified account.

Owner-private receipt:
`.batch3-vibe/gold-plan-auth/billing-settings-20261005.json`.

SHA256:
`1c0fb6f0878bbef70425478832c4651a9f4caaa31d1dbe5d223370def63809fe`.

The receipt records observations, correlation method and limitations,
`billing_ceiling_verified=true`, `must_recheck_before_dispatch=true`,
`access_token_fresh=false` and `dispatch_status=blocked`. Its local billing flag
records evidence; the provider setting supplies enforcement. The earlier
registration's historical billing flag was not rewritten.

Evidence persistence reused helpers from account source commit
`ea5c7d5cd1f47bbe76a6d8256ad616bed5cf55f7`, after verifying account seal
`f7c80f73fee847a264d869fa8197ba5358cd049f685a5f5a47b362e93c0a643b`.
The observation file and one-shot persistence script are ignored operational
artifacts in `.superpowers/sdd/gold-spend-preflight-20261005/`; they are not a new
sealed inference implementation.

Checks passed: private owner/SYSTEM ACLs, exclusive receipt creation, receipt
readback, unchanged registration/client/host bytes and empty production attempt
registry. No settings changed, credentials renewed, model requests sent, trades
placed, deployment performed or push run. Browser settings reads are distinct
from authenticated credential-worker requests; the latter count is zero today.

## Isolation limitation observed today

An open-only host probe could open the registration and billing receipt without
reading their contents. Follow-up native checks established that the command
tool ran as the auth owner with an unrestricted token. The directory still had
inheritance disabled and exactly the owner/SYSTEM ACL entries.

This did not reproduce the restricted coding-token denial tested on October 3.
Do not claim that denial was freshly verified, or treat owner-readable credentials
as proof of a restricted worker boundary. Before real inference, reproduce the
required restricted credential and network boundary on the actual execution path.
Do not weaken or replace the owner ACL to make this check appear to pass.

Context7 documentation about app-server usage and Platform budgets did not
establish this OAuth route's spending control. The applicable provider policy
and observed saved app settings above are the basis of gate B's result.
October 3 regression and Docker test totals remain historical; this milestone
made no runtime source changes and did not rerun those suites.

## Next milestone — prepare one real development proposal

1. Locate and verify the existing real gold export and its provenance/hash.
   A tracked-file name search did not locate a current dataset or real packet;
   that search does not establish absence from ignored or external storage.
   Preserve prior inspection, unqualified broker-clock/cost assumptions and
   reserved-data restrictions. Do not use untouched holdout data as research input.
2. Add only the minimum real development adapter needed. The current adapter is
   synthetic-only: do not relabel its fixture. Reuse packet validation, simulator,
   baseline comparison and report review; keep the existing risk policy fixed.
3. Prepare and verify the real inference path, credential/network isolation,
   termination cleanup and final committed-source seal. Current account and fake
   supported seals do not enable inference. Preserve existing fake/legacy behavior.
4. Freeze a concrete packet, baseline, schema, bounds and account/model binding
   for owner review. Target `gpt-6-astra`, medium reasoning, with the existing
   `ema20_slope_filter` proposal schema and lookback range 2–5. Obtain the owner's
   authorization for that concrete attempt after preparation is complete.
5. Immediately before an authorized attempt, recheck saved spending controls,
   login freshness and isolation. Use the reviewed same-account renewal path if
   necessary, never repeat registration. Reserve exactly one durable production
   attempt and make one request without retry, fallback, tools or order authority.
   Preserve failed/unknown attempts; only complete validated output can enter
   offline simulation and comparison.

This checkpoint authorizes no live request. Batch 2 remains development-complete
and unqualified; its qualification workstream stays deferred. No proposal or
favorable simulation promotes a strategy or authorizes trading.
