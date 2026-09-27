# Gold baseline: hypothetical cost scenarios

The baseline lost money in the chronological validation window in all three
scenarios. This is an unqualified diagnostic, not evidence supporting execution
or an estimate of future returns. No orders were placed or strategy promoted.

Code: `1874bff`. Dataset SHA-256:
`ba4f246746d861c9f61d82c7a09d17931cd74e9dea604ea2897853369dcf8614`.
Two VPS runs produced byte-identical reports, SHA-256:
`f580e2e59e4619f3f4d8018e8103351e62a71419b6885290c5c9e3f9a6be4dd5`.
Twenty-two Python tests passed, including gap fills, stop/target ambiguity,
short ask-side exits, entry timing, sizing, costs, daily pause and holdout isolation.

Hypothetical capital: USD 100,000, reset for each window. Fixed EMA20/50, ATR14,
0.1% entry risk, 2 ATR stop, 3 ATR target. No parameter optimization.

| Scenario | Development trades | Development net USD | Validation trades | Validation net USD | Validation return | Validation profit factor |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Lower costs | 82 | +410.97 | 30 | -305.19 | -0.305% | 0.811 |
| Middle costs | 83 | +6.43 | 31 | -445.94 | -0.446% | 0.746 |
| Stress costs | 78 | +63.33 | 30 | -186.87 | -0.187% | 0.882 |

Validation close-sampled maximum drawdowns were 0.732%, 0.865%, and 0.673%
respectively. These exclude unobserved intrabar drawdown. Trade counts change
across scenarios because stressed spreads reject entries and changed fill
prices alter exits; higher costs need not monotonically lower aggregate P&L.
Do not choose a cost scenario because it has a better outcome.

Development indices: 249–5999, raw timestamps rendered UTC April 30 11:00 to
July 28 10:00. Validation: 6000–7999, July 28 10:15 to August 27 04:00.
First 249 bars provide warmup. Positions are liquidated at each window end;
validation uses past bars for indicators but resets positions and capital.
Indices 8000–9999 (2,000 bars) were not trade-simulated. The earlier signal-only
replay did include their signal counts; do not describe them as wholly unseen.

Costs were frozen before running, in the researcher plan: USD 3.5/7/14 per lot
round-trip commission, price slippage 0.05/0.10/0.30 per side, daily overnight
debits USD 5/15/30 per lot, spread multipliers 1/1.5/2. They are hypothetical
stress inputs, not verified VT Markets charges. OHLC is assumed bid, with
constant spread inside each bar and current contract specification applied
historically. Stop-first handles ambiguous bars conservatively. Missing broker
margin/rejection behavior, actual ask path, cost history and timestamp semantics
prevent trading qualification. Thirty or thirty-one validation trades do not
establish statistical confidence.

Private ledgers/equity curves remain on the VPS under
`/opt/kwg-gold-research/simulation-1874bff/run-1.json` and `run-2.json`, created
with umask 077. The dataset and detailed reports were not published.

Next: verify fresh live data and two advancing M15 transitions when available,
verify actual broker costs and contract semantics, then predeclare evidence
and comparison gates before trying one bounded research proposal. Retain this
baseline as a comparator; do not enable orders or repeatedly tune on validation.
