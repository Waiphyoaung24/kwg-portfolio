# Gold M15 diagnostic scorecard

Primary metric: average net modeled USD outcome across resolved selected
opportunities. Selection coverage is selected / all eligible baseline setups;
timely matched response coverage is separate. First review is at 50 resolved
baseline opportunities, never an automatic promotion or a proof-of-edge threshold.

`jev_scorecard.py` opens the existing journal in SQLite read-only mode with a
consistent transaction. It verifies the frozen journal/evaluator source and
sample hashes, reuses `jev_research.report`, and atomically exports approved
market/setup fields and outcomes. No schema changes or response imports occur.
The current frozen collector, strategy, model and provider question remain intact.

The private status server serves `/jev-scorecard`. Owner-authenticated GET
`/api/trading/jev-scorecard` joins that report with the existing Durable Object's
immutable per-candle receipts. Matching requires the same completed candles,
indicators, prices, eligibility, slope decision, specification, costs, risk,
capture time, model and exact live question. Only the fresh transport heartbeat
is excluded. JSON key order is normalized after both payloads are parsed in JS.
The UI displays hashes of the projected input and live question separately from
the original journal input/config hashes; these are different schemas, not
interchangeable identifiers. The old journal prompt is not attributed to Jev.

A response must be requested after capture and completed within 15 seconds of
capture to enter Jev selection. The `review_setup` label means positive modeled
outcome. `insufficient_data` is abstention. Missing, failed, interrupted, late and
mismatched receipts remain in the eligible denominator. No-setup manual clicks
never enter it. Manual eligible responses use the same exact-input/deadline rules.

All three selections use the same frozen opportunity outcomes. Unresolved
window-end exits stay pending, gaps are censored, and unavailable reports show
dashes. Neither overlapping opportunity means nor sample counts are portfolio
returns or confidence intervals. Next-open fills do not model response latency;
spread proxies and cost scenarios are unverified. Promotion remains blocked.

## Rollout

1. Run `stage-jev-scorecard.ps1` with the existing unlocked SSH agent. It installs
   only the new exporter alongside the frozen bundle and a one-minute systemd
   timer, validates a read-only live export, and adds the private route with a
   backup. It restarts only the status server, not MT5 or the collector.
2. Deploy `ops/trading/worker` using `wrangler deploy --keep-vars`. Preserve the
   `gold-preview-v1` Durable Object and the existing $5 ledger. Scorecard reads
   never contact TypeSafe or reserve spend.
3. Publish the frontend through the normal portfolio pipeline. The owner retains
   control of the Dokploy Compose deployment. Production fixture routes return
   404; the Worker owns the authenticated scorecard API.
4. Verify live empty/populated results and the exporter timer. The source cap of
   200 eligible setups and 8 MB fails visibly; add pagination before that limit.

Stop only `kwg-jev-scorecard.timer` to stop exporting. Existing Jev observation
continues. A stopped exporter becomes unavailable after 120 seconds. The outcome
cutoff is displayed independently; a fresh export does not imply fresh candles.

The React Bits AnimatedContent entrance is adapted to the existing Astro/GSAP
stack; no new React runtime is added. Motion respects reduced-motion preferences
and does not animate the displayed financial values. Local preview data is
explicitly synthetic and cannot call the provider.

## Activation evidence — 2026-10-13 Bangkok

Read-only exporter timer and existing collector both verified active. Live export
reported 4 captured candles and 0 eligible setups at verification. Worker version
6194e107-8f36-4def-ab15-134763ae3c7c includes the scorecard route. No paid request
was initiated by these checks. Frontend publication and owner-authenticated live
scorecard rendering remain pending the owner's Dokploy deployment.

Validation: 36 JavaScript tests and 23 Python tests; Astro type check and production
build passed. Desktop/mobile UI preview uses explicitly synthetic outcomes.
