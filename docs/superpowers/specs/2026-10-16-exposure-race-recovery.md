# Dual M5 exposure reconciliation repair

Owner authorized main, tests, deployment and clearing only the verified mismatch pauses. No exit-policy change was approved; the suggested 15-minute cap is a separate demo experiment. Demo veto, sizing, risk limits, shared budget and reporting window remain unchanged.

Read-only investigation found both journals fully reconciled and MT5 flat; direct exposure validation passed while shared and symbol mismatch pauses remained latched. The historical triggering interval was not available in retained container logs. A local regression reproduced the timing gap when a stop/target closes after reconciliation but before exposure validation.

Fix: after either ownership-mismatch error, reconcile open journal attempts once using the existing deal/protection evidence validator, then repeat the complete exposure check. Other errors propagate immediately. Missing close evidence and unrelated positions still refuse entry. No reconciliation retry submits orders or automatically clears existing pauses. MetaQuotes documents separate position/history calls and None on API errors: https://www.mql5.com/en/docs/python_metatrader5/mt5positionsget_py and https://www.mql5.com/en/docs/python_metatrader5/mt5historydealsget_py. Context7 was also consulted for the API contracts.

141 targeted tests passed across dual-symbol, execution, Jev, and guarded recovery. The new close-race regression failed on the original code and passed after the fix. Existing test fixture ResourceWarnings remain.

Implementation commit: aed897e.
Reviewed code identity: 159868398bf04b4708b4821024c3d48f4ee50d83d6995bef1b9c9415894bd638.
Image: sha256:ca1a41bd5f79b4394f37a337aaf82a4afbc0f19b6960ebac270e92425c846039.
Stage: /opt/kwg-mt5-qualification/m5-exposure-159868398bf0.
Host backup: /opt/kwg-mt5-qualification/before-exposure-fix-1792135833621626543.
Previous image retained as kwg-mt5-desktop:exposure-base-1792135834514763288.
Journal backup: Wine user home/before-m5-exposure-recovery-1792135843898928300.

The reviewed helper required both exact mismatch pauses, correct pinned demo identity, both M5 veto strategies, no owner pause files/pending entries/unresolved attempts, unchanged exact reporting window, flat broker, and passing risk/exposure validation. It backed up both journals and atomically changed code identity plus mismatch pauses, resetting candle baselines. The recovery sent no order. Only the reviewed new runner image was started.

Verified post-start: both active/veto, fresh reports about 5.6 seconds old, quote ages Gold 0.50 seconds and BTC 1.38 seconds. Full attempt-table contents matched recovery backups. Shared risk differences were code, last_poll and pause only. Window remains 2026-10-15T07:11:02.984Z through 2026-10-17T07:11:02.984Z. Gold: 5 closed, +$2.17; BTC: 4 closed, +$0.94. No Worker deployment, budget-ledger reset or exit-policy change occurred. No forced trade was used to verify the repair; future stop/target closures remain subject to monitoring.
