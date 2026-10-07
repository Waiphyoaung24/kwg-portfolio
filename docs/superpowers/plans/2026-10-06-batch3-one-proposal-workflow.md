# One development proposal — owner approval and fresh evidence

Status: consumed on 2026-10-06. Fresh verification passed; the approved controller
returned `consumed_outcome_unknown`, `model_requests=outcome_unknown`, cleanup
verified. **Do not rerun this workflow.** Follow the
[saved-outcome diagnostic](2026-10-06-batch3-one-proposal-outcome.md).
The preparation/operator sequence below is historical; it does not authorize retry.
Correction after source review: the actual sealed request used stream=true and
store=false. The original owner prompt incorrectly said both false. Preserve that
original prompt/approval; future approval reviews must describe the tested payload.

The [completed combined verification](2026-10-06-batch3-combined-verification-results.md)
remains preserved. Its five-minute evidence is historical; do not rerun or retime it.

## Concrete approval scope

- Exactly one `gpt-5.6-sol` / `medium` development proposal from the existing
  sealed 6,000-bar summaries, constrained to an EMA20 slope filter.
- Supported OAuth `/v1/responses`, one POST, zero retries/fallback/tools,
  `stream=true`, `store=false`, and **$0 additional spending** (corrected description
  of actual transport; original owner prompt was inaccurate). Provider included
  plan usage must remain enabled; app credit usage and auto reload must remain off.
- One new logged same-account/model verification, with token renewal if needed,
  then fresh browser/provider and actual restricted CLI file-denial evidence.
- Research stays unqualified. No trading, promotion, deployment or Batch 2 qualification.

The manual owner terminal shows this scope and requires exact `APPROVE` via
`Read-Host`. This is the separate human authorization required by the sealed
`gold_proposal.py` approval gate. The coordinator takes its actual timestamp in
memory; a public marker or chat acknowledgement cannot supply approval. Any
other response stops before account verification. After approval, passing all
fresh checks authorizes this coordinator to send the single request automatically.

## Operator sequence

1. In the existing restricted Codex CLI, paste the contents of
   `.superpowers/sdd/gold-one-proposal-20261006/cli-prompt.txt`. The CLI submits the
   reviewed literal public holding command and reports `waiting.json`. It never
   runs the owner/account/dispatch helpers or probes private files.
2. After that marker is reported, run in a separate **owner PowerShell** terminal:

   ```powershell
   & 'C:\Users\wai19\Desktop\kwg-portfolio\.superpowers\sdd\gold-one-proposal-20261006\start.ps1'
   ```

3. Read the review printed there. Type `APPROVE` only if approving that exact
   scope. Keep the owner terminal and CLI open. Report **Owner ready** once the
   terminal says **Owner waiting for fresh browser evidence**.
4. This desktop chat genuinely rechecks the browser account, follows Gold's
   connected-app Manage usage link, and captures saved provider controls. Its
   public-only release helper publishes the matching observation descriptor.
5. The approved owner workflow performs its single new account verification,
   independently observes the actual held CLI token/ancestry/file denial, audits
   all bindings, creates the three private canonical gates once (approval last),
   and calls the existing sealed proposal controller exactly once.
6. Share the redacted terminal result. A successful request still needs offline
   proposal/evaluator review and development classification. Never infer trading
   authority or qualification from a successful model response.

The owner step is manual because this desktop chat is forbidden to read the real
`.batch3-vibe` tree. No permission profile, ACL, execution policy or replay guard
is changed. If the existing CLI is unavailable, use its previously reviewed owner
launcher; do not start a nested CLI from an agent command.

## Fixed bindings and refusal rules

- Source commit: `18620b96eb05eeef86dcea52acf3e00cb1c09e6c` (unchanged).
- Account seal: `e67f2b7f38d4d1458ae70dc5a8c86c311794caa338ecb0f731c025e52ffbe5ea`.
- Proposal seal: `a8ad5f4919cd020b71e6c8da408b08a94d2689f095c68fe510faef32b0f3ca2f`.
- Intent: `19de161c8f04a83d9ba66150274df268d1b3f66942deec087fca5a2ea5d01e4c`.
- New account ID: `bda965d0f493416c8fffa374f8964a44` (unstarted).
- New CLI nonce: `3a74a60ed4a24560ba41a9be3297d6b8` (unstarted).
- Approval is valid for at most 1,800 seconds. Browser release requires actual
  evidence within 10 seconds; account launch within 30 seconds. Final account,
  browser/provider and coding evidence must each be within 300 seconds.
- The canonical approval binds this exact new account ID and exact receipt SHA.
  Existing canonical gates, production experiments or round markers stop the flow.
- Preserve partial gates, attempts, results and old rounds. No automatic retry,
  deletion, reset, resealing or retiming after any failure or unknown outcome.
- Controller timeout after launch is reported as `outcome_unknown`, never zero
  requests. The existing durable production reservation and independent guardian
  remain responsible for request limits and cleanup.

## Validation

All checks use public files, synthetic temporary trees and mocked private/native
boundaries; none executes a real owner helper or reads credentials.

- `dispatch-check.py`: expired/missing approval stops before source/private flow;
  wrong receipt/provider/coding bindings refused; exact controller invoked once;
  replay and timeout preserve consumed records. Full synthetic continuation writes
  exact gates once; stale CLI, wrong receipt and existing gate stop before writes.
- `account-check.py`: exact round/seal/account/model/freshness, safe redaction,
  failed native proof before launch, one account-only invocation and replay refusal.
- `coordinated-check.py`: stale/unsafe provider controls, wrong release and live
  challenge bindings, atomic public release and replay refusal.
- `check.ps1`: public source pins, PowerShell syntax, exact versioned runner,
  live kernel self-binding and negative challenge/unrestricted-token checks.
- `preflight-check.ps1`: exact PowerShell stdin-to-Python transport with a
  synthetic Linux Docker result; no real Docker or network call.

Existing native preparation and fourteen fake cases are reused. Runtime source,
seals, original hook warning and Batch 2 qualification remain unchanged. Do not
repeat checks after this round's live markers are published.
