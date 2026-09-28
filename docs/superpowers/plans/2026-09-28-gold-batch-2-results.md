# Batch 2 implementation state

The offline simulator now accepts fixed timestamp windows and a dated,
historically covered cost profile. The previous hypothetical scenarios remain
available. The daily entry pause uses the previous sampled equity when a new
UTC day begins, preserving adverse overnight gaps. An offline evaluator and
approved prospective policy contain candidate gates and a deterministic paired
bootstrap. The real baseline remains diagnostic and ineligible for shadow
observation.

Local checks: 56 Python tests passed on 2026-09-29. The original frozen
dataset is private on the VPS, so a new baseline rerun was not completed from
this workspace. Batch 1 continuity and container-restart recovery now passed
for their observed session, while dated commission/swap coverage, a registered
candidate and sufficient validation observations remain missing. State:
**prepared_but_blocked**.
Prior baseline losses and 30–31 validation trades remain the only observed
results; they do not satisfy the approved 100-trade gate. No Vibe-Trading job,
candidate selection, shadow promotion or orders were started.

The 2026-09-28 live verifier showed both tick and bar raw timestamps roughly
three hours ahead of synchronized VPS UTC. The frozen historical dataset
retains raw MT5 epochs and is explicitly unqualified; calendar-day funding,
daily-pause and date labels must not be interpreted as broker-accurate until
the timestamp basis is established. The old hypothetical outcomes remain
diagnostics only.

Thirteen private live samples over one minute showed raw tick timestamps
advancing 59.78 seconds with a stable apparent UTC lead of about three hours.
This confirms feed movement but does not validate UTC date labels or the
historical dataset's calendar semantics. No prior backtest result was
reclassified.

The owner reported Standard STP pricing for the pinned demo. VT Markets'
current commission guide lists no separate gold commission for Standard STP
or VIP STP, but this is not dated historical coverage for the frozen dataset.
Its symbol-suffix guide associates `-VIP` with an account tier, so the
reported account type and exact suffix should be reconciled before treating
the fee as account-specific history. Sources:
[commission guide](https://get.vtmarkets.help/hc/en-us/articles/37317570987545-What-fees-commissions-are-charged-for-trading),
[symbol suffixes](https://get.vtmarkets.help/hc/en-us/articles/42847655982105-Why-am-I-unable-to-trade-certain-products-on-the-MT4-5-App).

A guarded, read-only MT5 query on 2026-09-28 returned current `XAUUSD-VIP`
properties: swap mode 1 (points), long -79.48 points, short +34.41 points,
three-day rollover field 3 (Wednesday), contract size 100, profit currency
USD and point 0.01. This implies a current per-lot nominal overnight cash
flow of -$79.48 long or +$34.41 short before any account-specific adjustments.
The exact rollover time and historical rate changes are not established.
[MetaQuotes swap-mode reference](https://www.mql5.com/en/docs/constants/environment_state/marketinfoconstants).
No historical cost profile was approved or populated; status remains
**prepared_but_blocked**.

The 2026-09-29 offline gate review found that matching policy hash strings in
two reports did not establish that either matched the policy actually being
evaluated. The gate now checks the approved policy's canonical SHA-256 and
rejects changed criteria. Nonfinite report/policy values, arithmetic overflow
and a zero-length bootstrap block are inconclusive rather than an eligibility
result or crash.
These synthetic tests do not qualify a candidate.
Boundary fixtures now cover trade/day minimums, profit factor, return
improvement, drawdown and fold underperformance. A positive headline return
with nonpositive candidate net P&L is rejected; undefined profit factor and
zero paired daily improvement cannot pass.

The authenticated read-only baseline summary still reports dataset SHA-256
`ba4f246746d861c9f61d82c7a09d17931cd74e9dea604ea2897853369dcf8614`,
hypothetical costs, 30/31/30 validation trades and net P&L of
-$305.195/-$445.94/-$186.87 (lower/middle/stress). No candidate is registered
or compared. Its older `live qualification incomplete` limitation does not
reflect the subsequent bounded Batch 1 session; neither result establishes
historical cost or timestamp coverage. The simulator now records per-trade
entry risk/net R, notional turnover and close-sampled raw-epoch daily returns.
A synthetic test reconciles trade risk and daily marks. These are diagnostics:
the raw days are not verified UTC dates, and the provisional manifest rejects
dated cost profiles and has no three prospective folds. The simulator now
accepts three explicit folds that exactly partition validation, resets each
fold flat and leaves the holdout untouched; a synthetic boundary test passes.
No real report adapter can meet the approved evaluator's evidence contract yet;
a synthetic gate pass is not end-to-end Batch 2 readiness.

On 2026-09-29 (Asia/Bangkok), the owner explicitly approved the exact v1
thresholds in `evaluation-policy.json` for future candidate tests. Its status
is now `approved`; no numerical threshold changed. The canonical policy
SHA-256 used by the evaluator is
`39eb8759133ac1ca50308e0aa053c761a53b24e94be9ebc3f8c13ff73413873d`.
This approval is prospective and does not reclassify the previously inspected
baseline or substitute for dated broker costs. The owner chose current public
terms only; those terms cannot fill the historical cost profile. No dated-cost
baseline rerun or candidate experiment was attempted. The 2,000-bar holdout
remains reserved.
