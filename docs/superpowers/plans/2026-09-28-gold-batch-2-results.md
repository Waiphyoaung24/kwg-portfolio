# Batch 2 implementation state

The offline simulator now accepts fixed timestamp windows and a dated,
historically covered cost profile. The previous hypothetical scenarios remain
available. The daily entry pause uses the previous sampled equity when a new
UTC day begins, preserving adverse overnight gaps. An offline evaluator and
draft policy contain candidate gates and a deterministic paired bootstrap.
All of this remains diagnostic; the draft policy cannot make a candidate
eligible for shadow observation.

Local checks: 53 Python tests passed on 2026-09-29. The original frozen
dataset is private on the VPS, so a new baseline rerun was not completed from
this workspace. Batch 1 continuity and container-restart recovery now passed
for their observed session, while dated commission/swap coverage, an approved
prospective policy, a registered candidate and sufficient validation
observations remain missing. State: **prepared_but_blocked**.
Prior baseline losses and 30–31 validation trades remain the only observed
results; they do not satisfy the proposed 100-trade gate. No Vibe-Trading job,
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
The policy remains `draft`; these synthetic tests do not qualify a candidate.

The authenticated read-only baseline summary still reports dataset SHA-256
`ba4f246746d861c9f61d82c7a09d17931cd74e9dea604ea2897853369dcf8614`,
hypothetical costs, 30/31/30 validation trades and net P&L of
-$305.195/-$445.94/-$186.87 (lower/middle/stress). No candidate is registered
or compared. Its older `live qualification incomplete` limitation does not
reflect the subsequent bounded Batch 1 session; neither result establishes
historical cost or timestamp coverage. The real simulator report still lacks
the daily-return/fold adapter required by the prospective evaluator, so a
synthetic gate pass cannot be treated as end-to-end Batch 2 readiness.

The owner chose current public broker terms only. Those terms cannot fill the
historical cost profile, so no dated-cost baseline rerun, candidate experiment
or policy approval was attempted. The 2,000-bar holdout remains reserved.
