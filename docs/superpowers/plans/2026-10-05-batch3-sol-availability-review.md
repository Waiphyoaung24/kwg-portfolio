# Sol availability review — 2026-10-05 Bangkok

**Superseded model requirement:** owner subsequently selected `gpt-5.6-sol`,
which the returned catalog includes, and authorized continuing. See the
[current model-switch checkpoint](2026-10-05-batch3-56-sol-switch.md). This report
preserves the investigation of unavailable `gpt-6.1-sol`; its old activation
blocker does not apply to the new selection. Support contact was declined.

The owner requires `gpt-6.1-sol`. The owner-reported authenticated catalog at
17:54:46 Bangkok contains seven other model slugs and no Sol. No parser
filtering of Sol was found. The exact provider-side reason is unknown; the
available evidence does not establish Sol entitlement for this connection.
Keep the existing Astra intent blocked. No runtime model constant or historical
private seal was changed, and no inference or new credential request ran.

## Source and contract checks

`gold_account.catalog_matches` iterates every entry in the provider's `models`
array. It validates each `slug` and rejects duplicates; it does not filter by
visibility, a local model list or the configured required model. The worker's
`available_models` output includes every returned slug. The configured model
affects only `required_model_present`. Thus the reported seven-model list is
not an Astra-only selection or a cached Codex picker list.

The official [plan-usage catalog contract](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
requires discovery using the selected account's OAuth access token and selection
of an available model. Its inference example explicitly uses `gpt-6.1-sol`;
Sol is not generally excluded from the documented route. That example does not
establish availability to this particular account/app. OpenAI's
[model-selection guidance](https://developers.openai.com/api/docs/guides/model-selection)
also distinguishes availability by product. No documented setting to force Sol
into this connection's catalog was found in the reviewed sources. Do not infer
that reconnecting, changing credits or switching authentication will fix it.

Context7 was queried for the plan-usage availability rules. It returned generic
API-key catalog examples and product-boundary guidance; those generic examples
do not replace the OAuth-specific contract above. Ponytail's reuse-first scope
keeps the existing parser and boundary rather than adding another transport.

The synthetic diagnostic is runnable without credentials or network access:

```powershell
python -I -S -B .superpowers/sdd/gold-sol-catalog-20261005/catalog_check.py
```

It passed: the supplied seven-model catalog fails a Sol requirement, and a
synthetic Sol entry with hidden visibility is recognized. Two existing fake-only
request/signature-binding tests also passed. A broader three-test run failed in
the synthetic atomic-file publication test with Windows `PermissionError` during
temporary-file replacement. An approved escalated rerun encountered the same
error in the command environment's temporary directory. No private trading
file was accessed; no runtime source was changed to hide that failure. A shell
quoting error in the initial focused invocation was corrected with the saved
diagnostic above. These checks are not new native isolation or dispatch acceptance.

## Prepared support question — not sent

The owner subsequently declined sending this question and asked about another
model. Do not submit it. The temporary support page was closed without a message.
`gpt-6-astra` was recommended because the existing seals target it; the owner
subsequently selected `gpt-5.6-sol` as recorded in the superseding checkpoint.

OpenAI documents [contacting support through its Help Center](https://help.openai.com/en/articles/6614161-how-can-i-contact-support).
The owner can submit this draft through the authenticated support flow:

> My personal ChatGPT Pro connection, KWG Gold Research, uses the documented
> Sign in with ChatGPT plan-usage OAuth flow. On October 5, 2026 at 17:54:46
> Asia/Bangkok, the authenticated GET to https://api.openai.com/v1/models
> returned these seven slugs: gpt-6-astra, gpt-reserve, gpt-5.6-sol,
> gpt-5.6-terra, gpt-5.6-luna, gpt-5.5, codex-auto-review.
>
> I want gpt-6.1-sol. It appears in my Codex picker and in your plan-usage
> inference documentation, but is absent from this connection's catalog.
> Is it available to this connection? If so, what supported entitlement or
> model-discovery step is needed? If not, is there a published rollout timeline?
> I need included-plan usage only, with app credit use and automatic reload off.

No message was sent and no account identifiers or credentials were included.
The next external step is resolving this catalog discrepancy with the provider.
If Sol becomes available, prepare a new exact Sol intent and source seals, rerun
affected validation, and obtain fresh account/$0/coding evidence and concrete
proposal approval. Preserve the completed account attempt; do not rerun it or
relabel its old acceptance time. Real dispatch stays blocked and Batch 2 remains
unqualified with qualification deferred.
