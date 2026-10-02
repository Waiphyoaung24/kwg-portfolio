# Local Docker readiness and credential-free isolation

Owner authorized starting local Docker Desktop and rerunning the offline
isolation rehearsal. VPS/MT5 and all original evidence remain untouched.

1. Add read-only batch3_runner --preflight: fixed local engine/pinned image,
   no owner Docker config or inherited context, bounded inspection calls.
   Availability alone must never grant production or billing approval.
2. Start Docker Desktop as authorized; do not pull images or change other
   containers. Reuse run_fixture for fake refresh success/failure, HTTP401,
   timeout and cleanup in the credential-free sandbox.
3. Preserve exclusive case outputs/summary. Halt on first failed gate; no
   automatic retry. Verify focused/full checks and obtain fresh scoped review.

Verification: preflight test failed before implementation then passed. Initial
sandbox preflight could not access runtime; owner-context read-only preflight
verified Linux engine and existing pinned image. Rehearsal passed at
`.superpowers/sdd/batch3-auth-docker-20261002-01/summary.json`.
Success case verified write/network denial; refresh failure made zero fake
inference posts, HTTP401 made one with no refresh. All cases verified removal of
their own containers. Timeout case reports os_sandbox false because its config
was not inspected before timeout; cleanup passed, no stronger claim made.

No real credential transport or additional-spend enforcement verified. USD0
budget and no paid fallback remain approved; gold dispatch/promotion blocked.

Fresh review found a future false-PASS gate: only inference_posts was checked,
not refreshes/clears. Regression failed, then passed after checking all expected
counts. Corrected live Docker fixture rehearsal passed at separate preserved
`batch3-auth-docker-20261002-02/summary.json`; -01 remains intact and already
contained correct counts. No real model requests.

Owner billing facts: Vibe uses ChatGPT Pro, no paid credits available, automatic
purchases/top-ups disabled. This is owner-reported evidence supporting the USD0
budget, not direct provider/account inspection or proof of a per-request billing
control. Trusted real transport must bind the correct account, stop at quota
failure and never purchase/fallback/retry. Backend monetary enforcement remains
unverified; no request is enabled by this readiness report.
