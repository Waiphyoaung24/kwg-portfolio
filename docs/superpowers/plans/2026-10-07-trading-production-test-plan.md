# Trading production test plan — October 7, 2026

Owner acceptance for the current Batch 1 feed/control UI, Batch 2 comparison software and Batch 3 offline diagnostics. A website release does not update the separately deployed VPS desktop/control service, change sealed research snapshots, qualify a strategy or authorize an AI request.

## Current acceptance boundaries

| Batch | What can pass now | What remains outside this test |
| --- | --- | --- |
| 1 | Fresh demo observations, protected pages, level diagram and a no-order preview | Continuous trading; any new order needs a deliberate owner action |
| 2 | Synthetic reports load, reconcile and clear; fixed risk/qualification facts remain visible | Real-market qualification is deferred, not passed |
| 3 | Fake transport → worker → receipt diagnostics and saved local learning checks | A successful real proposal, reproducible real comparison and the self-improvement loop remain incomplete |

The October 6 real proposal attempt is consumed with unknown request outcome and verified cleanup; proposal/usage artifacts are absent. Do not retry it, reset its reservation, rename it into a new experiment or reseal it. The October 7 diagnostic code is a candidate source change, not a change to that old snapshot.

## Before you begin — 5 minutes

1. Confirm the production deployment reports the new `main` commit. A pushed commit alone does not prove deployment succeeded. If the website is served from the separate VPS `trading.html`/`trading-bot.html` copies, their existing packaging/deployment path must also be updated; do not replace the desktop or control service for this visual release.
2. Open https://waiphyoaung.com/vault/trading-bot and https://waiphyoaung.com/vault/trading. Sign in through the existing Cloudflare Access flow yourself.
3. Confirm the KWG mark appears in navigation; the demo page has **Prepare one trade**, **Set prices / Preview / Place once**, and **Entry / stop / target**. If these are absent, stop: the new frontend is not deployed.
4. Keep MT5 **Algo Trading off** for observation and preview. Use the pinned demo account. Inspect MT5 for existing gold positions/pending orders; do not cancel or restart anything merely to make a test pass.
5. Record commit, deployment time, browser/device, test time in Bangkok and each case as `PASS`, `FAIL`, `BLOCKED` or `NOT RUN`. Keep broker/account details, cookies, tokens and full network payloads out of shared screenshots/logs.

## Batch 1 — feed and supervised preparation, 15–25 minutes

| ID | Steps | Expected result |
| --- | --- | --- |
| B1-01 | Open both pages in an already signed-in browser. In a private/signed-out browser, open the page and `/api/trading/status`. Do not submit an unauthenticated order POST. | Signed-in pages load. Signed-out protected content requires Access; no broker data is exposed. |
| B1-02 | On Overview, inspect connection, quote freshness, history and signal. On Supervised demo, expand **Technical details**. Wait across two 10-second updates during an open session. | Current heartbeat/check time advances. A healthy feed says connected/fresh/observing, orders off. **No setup yet** is acceptable. Market-closed/stale data stays waiting/paused rather than becoming a false pass. |
| B1-03 | Briefly use browser DevTools offline mode, wait over 30 seconds, inspect the state, then restore networking and refresh. Do this before any preview or order. | Unavailable/expired observations are explicit; another order is not enabled on old status. Recovery requires a new successful response. Never stop MT5 or the VPS to simulate this. |
| B1-04 | Compare the latest displayed attempt, its state, direction/size, prices, close time and net result with MT5's history. | They agree with the recorded attempt. A closed result is labeled historical; it is not presented as strategy return or proof that no other broker exposure exists. Missing data stays unknown. |
| B1-05 | Enter your own demo test prices without submitting. Test Buy (`stop < entry < target`), then Sell (`target < entry < stop`). | Diagram uses your exact levels, places higher prices above lower prices, and says **Draft levels · not broker checked**. It is explicitly not a market chart/forecast. No order or AI request is sent by editing fields. |
| B1-06 | Clear one price; reverse stop/target ordering; enter zero, an out-of-range price or an invalid decimal step. Then restore valid prices. | Invalid/incomplete input hides the diagram and explains the ordering. Valid input restores it. No stale historical diagram is mislabeled as your draft. |
| B1-07 | With healthy feed, resolved prior attempt, correct demo account and Algo off, click **Preview pending order** once using your reviewed prices. Inspect MT5 before and after. | Preview returns exact direction/order kind, 0.01 lot, entry/SL/TP and modeled stop loss. It states no order was placed. MT5 positions/orders and the execution journal do not gain a new attempt from preview. A broker guard refusal is a valid blocked result. |
| B1-08 | After a successful preview, edit a price. For expiry, optionally make another no-order preview and wait beyond 10 minutes without placing it. | Editing invalidates the previous confirmation and requires another preview. An expired preview must not authorize an order; do not click Place just to probe expiry. Backend expiry enforcement is also checked offline in `test_control_server`. |

### Optional supervised demo order — owner only, separate from release acceptance

Skip this for the read-only release review. If you deliberately choose one new demo order, first review the current account, quote, exact prices, modeled risk and empty gold exposure in MT5. Enable Algo Trading yourself only after those checks; click the reviewed **Place one … order** once. Watch MT5 and the website for pending/open/closed or needs-attention state. Cancel an unwanted pending order manually in MT5 and wait for reconciliation. Turn Algo off afterward.

If the response is uncertain, an order is duplicated, protections are absent or the state says needs attention, stop further submissions and inspect broker exposure/journal. Do not repeat Place or reload to obtain another entry. This optional mechanics check provides no Batch 2 qualification credit.

## Responsive and accessibility checks — both pages, 5–10 minutes

1. Check 320/390-pixel phones, 768-pixel tablet, the screenshot width of 1122 pixels and 1440-pixel desktop; also check 200% browser zoom.
2. Overview: **What is ready?** and **Practice comparison** have readable paragraph/button spacing. Narrow content stacks the strategy sidebar below the primary sections. **Fictional results** wraps below the heading on phones. No page content is clipped sideways; only the results table may scroll within its own region.
3. Supervised demo: fields and the diagram stack on narrow screens; all three levels and labels remain readable. Draft and historical labels remain distinct. No horizontal page overflow.
4. Use Tab/Shift+Tab and Enter/Space for navigation, disclosures and buttons. Focus must remain visible. Test **Development stages**, **Observation details**, **Trade details** and the report explanations. No status relies on color alone.

## Batch 2 — fictional comparison, 10–15 minutes

Use the existing local synthetic folder `.superpowers/sdd/batch3-development-handoff-20261002-01/`. It is preserved local evidence, excluded from Git and not downloaded from production. If unavailable, mark the import prerequisite blocked; do not invent real broker reports.

| ID | Steps | Expected result |
| --- | --- | --- |
| B2-01 | On production Overview, click **Choose three reports**. Select `comparison.json`, `baseline.json` and `candidate.json` together from that same folder. | Six rows appear: lower/middle/stress × development/validation. Results remain explicitly fictional, unqualified and promotion blocked. |
| B2-02 | Read the explanation and **How to read the results**. Compare the numbers to the selected files. | Difference is proposed minus original. This fixture's development differences are 0; validation differences are −413.10, −412.35 and −409.35 USD respectively. Explanation says the proposed filter underperformed under all three cost assumptions. These are not MT5 P&L. |
| B2-03 | Expand **Technical file checks** and **What remains before trading**. | Selected baseline/candidate hashes are checked; other identities are declarations whose source files were not loaded. Evidence gaps and exact-artifact human approval remain visible. |
| B2-04 | Click **Clear review**. Reimport, then reload; reimport again, navigate away and return. | Review returns to empty after clear/reload/leaving. No persistent account result is implied. |
| B2-05 | Select only two files. In a new disposable folder, copy the three originals and corrupt JSON or alter a baseline byte; select those copies. Preserve originals. | Missing files, malformed JSON or hash mismatch produces an error and no accepted table. A subsequent correct selection recovers. |
| B2-06 | Optionally copy reports again and change only a comparison delta, `qualification`, `promotion_status` or a policy/risk hash. | Inconsistent summaries or unsupported claims are refused. The UI cannot promote a candidate through imported claims. |
| B2-07 | Inspect Strategy and qualification. | EMA20/EMA50, fixed risk rules and **Evidence still incomplete** remain present. The deferred requirements remain 60 eligible validation days, three flat folds of at least 20 days and 100 closed trades per strategy, plus existing cost/provenance/performance/stress gates. None is passed by this upload. |

During report selection, inspect request URLs if desired: file bytes must stay in the tab. The hosted page's unrelated 10-second status GETs may continue; there must be no report-file upload, AI request, order POST or promotion call caused by the import.

## Batch 3 — offline diagnostics and separate local learning, 10–15 minutes

These cannot be accepted by clicking production Overview alone. Production correctly says the learning workspace is local and automatic trading is unavailable. The website importer currently accepts synthetic rehearsal reports, not real Batch 3 receipts/proposals.

From the repository root, run fake-only checks in your local owner terminal:

```powershell
node src/scripts/trading-levels.test.mjs
node src/scripts/trading-status.test.mjs
node src/scripts/trading-review.test.mjs
python -B -m unittest discover -s ops/trading -p test_control_server.py
python -B -m unittest discover -s ops/trading -p test_demo_one_shot.py
Push-Location ops/trading
python -B -m unittest test_gold_account test_gold_proposal test_supported_oauth_transport test_supported_gateway test_real_development test_batch2_adapter test_gold_costs
Pop-Location
```

Expected: all assertions pass; the final seven-module suite currently has **42 tests**. It uses fake HTTP/subprocess/Docker boundaries and temporary synthetic files. It does not run the real protected runtime. A setup/permission failure is blocked coverage, not permission to loosen an ACL or run a live controller.

Check the diagnostic test outcomes: only an allowlisted stage and optional HTTP status survive failures; secret canaries/messages/bodies/headers do not. Worker crashes and malformed success/failure envelopes fail closed. Possible-transfer failures retain unknown request counts; cleanup failures cannot pass; consumed reservations cannot replay. HTTP 200 alone is not proposal success.

If your separate local Vibe app is already running on 8899 with saved session `0edab1e6d735`, run:

```powershell
$env:E2E_TELEMETRY_DISABLED='1'
npx e2e run tests/trading-readonly.e2e.ts --workers 1 --retries 0 --output .e2e/owner-production-review-UNIQUE
```

Replace `UNIQUE` with a fresh timestamp/run name. Expected **2 passed**, no model calls. They inspect the saved six-row arithmetic answer (sum 130, positive count 3, mean 21.67), its trace, Reports/back navigation and Runtime's zero-authorized/zero-running display. Keep the app running. Missing saved state is a blocked prerequisite; do not submit another prompt to recreate it. These tests do not target the hosted trading pages; do not set `APP_URL` to production for them.

## Evidence and acceptance

Save a short row for each case: `ID | PASS/FAIL/BLOCKED/NOT RUN | time | observed result | sanitized screenshot/report path`. Keep reports outside Git and use fresh filenames. Do not paste authentication headers, account identifiers, private receipts or broker data into public issues.

Accept the frontend release when the deployed commit is confirmed, access/feed states are truthful, diagrams and responsive controls work, the no-order preview preserves exposure, and report imports reject bad files and clear correctly. Record Batch 2 qualification as deferred and Batch 3 live research as incomplete even if all software checks pass. A bug should name the failing case and actual behavior; do not repair it by starting a trade, AI request, old helper, reseal or qualification run.

Earlier scoped evidence: 42 offline tests, two owner-run local browser tests and diagnostic patch review passed on October 7. Local responsive checks passed at 320, 390, 768, 1122 and 1440 pixels. These are pre-release evidence; production checks above remain yours to run.

Release snapshot checks: the 42-test diagnostic suite, three control-server tests, 41 demo tests and all three trading JavaScript checks passed against current `main` plus the scoped trading files. Astro check reported zero errors/warnings and two existing hints. Dashboard and Astro builds completed with temporary `preserveSymlinks` settings because standard Vite realpath resolution is denied by this Windows execution environment. Those temporary configs are excluded from the commit; the normal production build/deployment still needs confirmation.
