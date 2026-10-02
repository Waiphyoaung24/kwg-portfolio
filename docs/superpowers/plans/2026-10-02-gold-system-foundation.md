# Gold system foundation checkpoint — October 2, 2026

The owner wants to finish the foundation for an eventual self-improving XAUUSD
system. The pasted architecture is reference material, not authorization to
install frameworks, execute generated code, change qualification policy or trade.
Current authority remains the [Batch 2/3 handoff](2026-10-02-batch2-batch3-handoff.md).

Batch 2 is closed for development and unqualified. Batch 3's offline integration
is verified; real gold dispatch and promotion are blocked. Deferring the sample
does not qualify the baseline or a candidate. The baseline is a comparison
reference, not an accepted profitable production strategy.

## Existing components and boundaries

| Responsibility | Existing component | Current limit |
| --- | --- | --- |
| Broker observation | VPS observer and `/api/trading/status` | Health/signals, not qualifying performance or autonomous execution |
| Research workspace | Separate local Vibe-Trading application | Learning app is not the bounded gold runner |
| Evidence packet | `batch2_adapter.py`, `batch3_adapter.py` | Real-format reconciliation and synthetic integration; coverage still incomplete |
| One structured proposal | `batch3_runner.py`, proposal validator | Fixed model/medium; real inference disabled; no generated code execution |
| Trusted credential boundary | `trusted_oauth_transport.py`, `trusted_gateway.py` | Fake gateway tested; real permitted egress/account acceptance and USD0 enforcement unverified |
| Independent evaluation | Existing gold simulator and evaluation policy | Fixed risk, costs/scenarios and windows; synthetic pass is not qualification |
| Experiment record | Exclusive attempt artifacts, manifests and hashes | Rehearsal reservation is per registry; fixed production registry still required |
| Owner review | Comparison outputs, explicit human promotion requirement | No working promotion service or continuous autonomous runner |
| Operations view | `/vault/trading-bot` | Hosted protected feed; loopback preview for fictional practice comparison only; qualification and promotion remain blocked |

## Smallest useful increment — accepted and completed

The owner confirmed local offline comparison, evidence gaps and blocked promotion.
Gold operations now makes one synthetic experiment inspectable using existing
rehearsal reports. No research framework, broker connector, model request,
scheduler or promotion endpoint was added.

1. Updated stale preparation copy to distinguish development closure,
   unqualified evidence, offline rehearsal and blocked production dispatch.
2. Local selection accepts comparison.json, baseline.json and candidate.json
   together, limited to 8 MiB each. The parser requires the synthetic,
   unqualified, promotion-blocked rehearsal format and unchanged risk/policy.
   It checks baseline/candidate SHA-256 hashes against selected file bytes and
   reconciles numeric summaries across lower/middle/stress scenarios and
   development/validation windows before displaying six Original/Proposed rows.
   Practice comparison explicitly identifies fictional data and distinguishes
   these amounts from MT5 account profits/losses. How to read the results explains
   terms; a computed plain-language explanation identifies underperformance.
3. Files remain in the browser tab. Clear or reload removes the review. There
   is no upload or report publishing. Allowlisted display fields omit private
   paths, credentials and raw broker records; report values render as text.
4. Engineering stages, strategy/risk, qualification requirements and evidence
   gaps are available behind disclosures. Baseline/candidate hashes are checked locally;
   manifest, proposal, risk, policy, cost and clock identities are declarations
   in the comparison, not verification of their source files. Local consistency
   is not authenticity, broker provenance or qualification. No dispatch, order
   or promotion action is available.
5. Parser rejection/reconciliation checks and a real rehearsal artifact check
   passed. Browser verification at 390 and 1440 pixels found no page overflow;
   clear removed the review, and an incorrect-file selection was rejected while
   clearing old results. Astro build and standalone bundling succeeded, with
   no external Astro script/style imports in `ops/trading/trading-bot.html`.
   The earlier offline-review disposition was ship, no material fixes. The
   subsequent clarity revision has passed tests/build/bundling and browser checks
   for zero loopback API requests, one filled primary and no page overflow;
   its fresh finish review returned ship with no material fixes. Latest captures are
   `.superpowers/trading-clarity-desktop.png` and
   `.superpowers/trading-clarity-mobile.png`. Global Astro check remains blocked
   by 616 unrelated dashboard/dependency errors; it reported no trading diagnostics.
6. Loopback preview (localhost, 127.0.0.1 or ::1) makes no status API requests,
   displays Not connected here, hides local refresh/sign-in and links to the
   hosted MT5 dashboard. Choose reports is its single filled primary action.
   Hosted mode retains the same protected `/api/trading/status` boundary and
   distinguishes access redirects/401/403 from other feed failures. A desktop
   MT5 tunnel does not connect the preview to this API. No new live connection,
   proxy, credentials or deployment was added; live integration is not completed
   by this local review increment.

Success achieved: the owner can inspect declared packet/proposal identity,
baseline-versus-candidate results and evidence gaps for one reproducible offline
experiment, without confusing software completion with strategy qualification.
This completes the accepted foundation increment; the self-improvement loop
still requires the separate later increments below. The surface extends the
incumbent design system; root DESIGN.md and its sidecar remain unchanged.

## Separate later increments

- Production transport: reviewed credential process, fixed private reservation
  registry, permitted provider egress, verified server account binding, new seal
  of final committed sources and demonstrable USD0 enforcement before dispatch.
- Qualification: dated costs/clock/session coverage, prospective windows and
  previously approved samples, untouched holdout and repeatable real provenance.
  No retrospective sample credit or relaxed policy.
- Repeated research: record all attempts and data exposure, impose a search
  budget, and prevent feedback from repeatedly turning a holdout into development
  data. Even pass/fail feedback can leak information across repeated trials.
- Shadow execution and promotion: separate reviewed protocol and exact-artifact
  human approval. Existing one-shot supervised demo is not this service.

OpenShell, Qlib, RD-Agent, generated-code agents, additional macro feeds and GPU
workloads remain optional future proposals. Their external capability claims in
the pasted text have not been verified in this checkpoint; no installation or
replacement is justified by the current one-filter comparison scope.
