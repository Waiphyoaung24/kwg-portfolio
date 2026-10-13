# Balance/history pause investigation â€” 2026-10-13

Both pilots use the same account limit record, so one account reconciliation
failure pauses both symbols. Jev does not control this guard.

The earlier audit reconciled the broker balance and all deal costs exactly:
$74,714.64 starting balance minus $275.88 net activity = $74,438.76.
The pause remained latched as designed. Its original trigger cannot be proven:
the runner keeps only two 2 MB console logs, and the original check had already
rotated out. MT5 retained the Gold close at 03:37:57 UTC, but neither the old
runner nor the journal recorded the two reconciliation amounts at failure.

## Captured live recurrence

At 08:44:56 UTC the terminal reconnected and declared synchronization complete,
but the guard received only 378 deals while the balance was already current.
Persisted evidence: before/after balance $74,435.91, history-derived expected
balance $74,467.31, difference -$31.40, latest deal time_msc 1791816421103.
A subsequent read returned 824 deals and reconciled to $74,435.77 exactly
(another BTC close had since settled). This proves a successful history response
can be incomplete during terminal startup. It does not prove the cause of the
earlier, unlogged incident.

## Reproduced defects and correction

`limits()` read account balance before fetching history. A settlement between
those calls produced old balance + new deals and permanently latched a false
discrepancy. A deterministic test reproduces this through `SharedAccount.check`.

The guard now reads the pinned demo account again after validating deal history
and costs. It rechecks the latest equity against the existing loss thresholds.
If balance changed between reads or history disagrees, it immediately blocks
entry with `BrokerUnavailable` so the continuous runner retries reconciliation
on its next poll. A persisted `balance_pending_since` permits at most 30 seconds
of confirmation; restarting or re-creating the shared guard cannot reset it.
Only a consistent account/history snapshot within the original $0.02 tolerance
clears the pending state. A discrepancy still present after 30 seconds permanently
latches the original pause. Existing latched pauses are never automatically cleared.

For a changed balance or discrepancy, `account_limits.data.balance_check` retains
the timestamp, before/after balances, expected balance, difference, deal count,
and latest deal timestamp. This evidence survives console rotation. History that
does not reconcile within the bounded window still stops the pilots; investigate
the stored evidence rather than extending the deadline without evidence.

## Verification and rollout

`python -m unittest test_balance_snapshot test_continuous_pilot test_two_symbol_pilot test_btc_scalp test_demo_pilot`
passed 110 tests. Coverage includes both mixed-read directions, partial successful
history responses, entry blocking and recovery for both pilots, persistent
mismatch latching across guard reconstruction, latest-read loss limits, and
migration preservation of risk and trades.

Reviewed runtime: `3cd6afee01fc37c4c579843ad2a77456d0fe5cb708e8d8e05b1daf9209f789e8`.
Only the snapshot guard block differs from the previous deployed trading sources.
Stage: `/opt/kwg-mt5-qualification/two-symbol-review-20261013T084934Z-36d0fcb8`.
Deployment backup: `/opt/kwg-mt5-qualification/two-symbol-backup-1791881429333123532`.
Journal backups: `C:\users\mt5\before-btc-scalp-1791881432616180500` in the MT5 home volume.
The existing migration preserved continuous operation, both strategies, risk
thresholds, acknowledged receipts, and positions; it sent no orders itself.

After the final restart, the new guard captured another incomplete response:
823 deals, expected $74,435.91 versus current balance $74,435.77 (the missing
BTC close was -$0.14). It blocked entries during synchronization and recovered
without a permanent pause when history caught up. Fresh post-restart snapshots
confirmed both pilots active, no pending balance check, and Jev feed/scorecard
ready. The historical `balance_check` record remains available after recovery.
