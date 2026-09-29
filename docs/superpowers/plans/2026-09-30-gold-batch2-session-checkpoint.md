# Gold Batch 2 — sign-off checkpoint, 2026-09-30

## Status

Batch 2 remains **prepared_but_blocked**. The owner selected qualification as the next milestone. The evidence probe and evaluator preparation are implemented; current spot checks, a historical export and public current terms do not constitute a qualification pass.

Session work reviewed the read-only observation guard, private dated contract/clock captures, immutable export coverage, public holiday schedules and existing one-shot reconciliation logic. Detailed runtime observations, deal results, contract rates and dataset hashes are kept in the private session record outside Git. No new strategy, model job, order, deployment or promotion was started by the agent during qualification.

## Findings to preserve

- Observation requires Algo Trading off. A healthy heartbeat can coexist with a blocked observer; inspect the explicit reason rather than treating delivery as feed health.
- Broker-held pending orders and protective exits are separate from new Python entry permission. Turning Algo off does not cancel a pending order.
- Public holiday schedules can explain longer candle gaps. Schedule consistency is not proof of exact demo-account sessions or historical UTC mapping. Preserve frozen bytes; do not interpolate or silently delete bars.
- Export metadata compares raw broker epochs with host UTC when counting incomplete bars. A raw-clock count must not be used to discard candles before timestamp semantics are established.
- The current pending-entry runner accepts SL/TP close evidence during its entry phase. A matched desktop-origin exit can leave `needs_attention` despite no remaining broker exposure. Repeating `resume` does not change that rule. Do not edit the SQLite journal by hand or call it a protective exit.
- A quote-age failure during a scheduled session break is distinct from a connection failure. Verify exact symbol sessions and recovery after reopening.
- Current public commission/swap rules and current snapshots cannot be backdated over the historical evaluation interval. `commission: null` is unavailable data, not an evidenced zero fee.

## Remaining tasks, in order

1. **Read-only recovery check:** after the expected gold reopening, verify pinned-demo identity, Algo off, fresh quotes and valid completed M15 history. Confirm exact `XAUUSD-VIP` sessions in MT5 Specification. Record the dated result privately; do not restart or submit another attempt to test recovery.
2. **Close reconciliation follow-up:** design a narrow supported path for a broker-verified desktop-origin close. Require the existing attempt's matched position identity, full exit volume and reconciled deal amounts; label the actual close origin. Retain fail-closed handling for ambiguous history, partial exits and unmatched exposure. Add a regression check before implementation is deployed. This operational follow-up is not authorization for new trading.
3. **Dated costs and clock coverage:** preserve prospective contract/host-clock captures and public source retrieval dates. Establish account applicability, exact rollover clock, dated funding rates/events and DST interpretation. With current public terms only, uncovered historical periods remain unqualified. Do not open a position just to generate a swap charge.
4. **Prospective evaluation:** freeze a new manifest before candidate research; establish three flat validation folds and simulator-to-gate provenance. Keep the approved 100 closed trades, 60 observed validation days and at least 20 observed days per fold. Historical warmup is not newly observed validation. Preserve the original holdout and `simulator_provenance_unverified` cap.
5. **Reproducible baseline:** once inputs are covered, run the existing baseline twice with explicit code/data/cost/policy hashes and exclusive private output files. Compare bytes and report remaining limitations. Batch 3 stays conditional on the required evidence gates; no candidate research or automatic promotion yet.

## Resume prompt

> Read `ops/trading/HANDOFF.md`, this checkpoint, and the linked Batch 2 plan/results. Continue Batch 2 qualification, starting with read-only session recovery and the unsupported desktop-origin close reconciliation design. Inspect the private session record with the owner; do not publish its broker data. Keep MT5 demo-only, no new orders, and Algo Trading off for observation. Preserve the current pending-entry implementation and immutable datasets. Do not reset the journal, lower evaluation gates, or enable Batch 3 prematurely.

## Where to resume

Code and documentation: branch `codex/gold-batch2-evidence`, existing [PR #4](https://github.com/Waiphyoaung24/kwg-portfolio/pull/4). No merge is part of this checkpoint.

Private Windows session record: `gold-batch2-private-evidence-20260930.md` under the Codex visualization directory for this chat. VPS captures remain under `/root/kwg-gold-research/evidence/`; the MT5 journal and exported snapshot remain in its persistent home volume. No credentials or runtime reports belong in Git.

The primary checkout has an unresolved merge and unrelated local changes. Continue in the existing Batch 2 worktree; do not resolve or overwrite the primary checkout as part of resuming this session.

## Public references

- [Broker server clock](https://get.vtmarkets.help/hc/en-us/articles/37317868198297-What-is-VT-Markets-GMT-offset-or-server-time)
- [Current settlement rules](https://get.vtmarkets.help/hc/en-us/articles/37354714409625-What-does-PNL-Weekend-Swap-mean)
- [Exact product session lookup](https://get.vtmarkets.help/hc/en-us/articles/37317499627289-What-are-the-trading-hours)
- [Generic XAUUSD public hours](https://www.vtmarkets.com/en-ca/precious-metals/xauusd/)
- [MetaQuotes deal entry and reason definitions](https://www.mql5.com/en/docs/constants/tradingconstants/dealproperties)

This checkpoint changes documentation only. Earlier 104-test validation applies to the evidence-probe implementation; it does not establish live qualification or test a future reconciliation fix.
