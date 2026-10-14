# M5 acknowledgement regression recovery — 2026-10-14

The first M5 shadow cutover switched the journals but latched `Unrelated account
activity requires review`. The deployed M1 source supported exact, previously
reviewed manual deal receipts; the merged M5 source omitted that support.
The shared journal retained `acknowledged_manual_deals` during cutover.

Read-only broker inspection found exactly two rejected deals: BTC tickets
591104897 and 591104975, the open and close of position 805998317. Every receipt
field matched the existing acknowledgement. All 1,226 deals reconciled exactly:
initial balance $74,714.64 to current balance $74,423.33. No positions or orders
were open. These are historical receipts, not permission for new manual trades.

`demo_pilot.py` restores the previous exact-receipt check. Missing or changed
acknowledged receipts and any new unrelated deal still refuse. Acknowledged
deals remain included in balance and loss calculations.

`recover-m5-account-pause.py` accepts only the affected M5 code identity, continuous
M5 shadow, the specific regression pause, existing acknowledgements, a flat
account, resolved journal attempts and passing account/loss/history checks.
It backs up both journals, updates their code identity atomically, and clears
only this pause. It preserves BTC's separate `Paused by owner` state and owner
pause files. It must run under Wine Python with the runner stopped for `--apply`;
without that option it performs read-only review. It is a one-time recovery,
not a general unpause command.

## Preserved artifacts

Original stage: `/opt/kwg-mt5-qualification/m5-jev-review-20261013T222052Z-e73ca13d`.
Original host backup: `/opt/kwg-mt5-qualification/m5-jev-backup-1791931148529438806`.
Original journals: `C:\users\mt5\before-m5-jev-1791931151212299300`.
The original M1 base image was absent from Docker at investigation time; do not
assume the historical image tag is available for rollback. Both original journal
backup files were verified present. No old M1 runner was started.

Recovery stage: `/opt/kwg-mt5-qualification/m5-account-recovery-1791935953222834975`.
Corrected source identity:
`0084f2b63b256ef528a95d067e18fba031b0e3b3f31cd26ff0eb2e02f8f1b03c`.
Pre-recovery M5 image: `kwg-mt5-desktop:before-account-recovery-1791935953222834975`.
Recovery journal backups: `C:\users\mt5\before-m5-account-recovery-1791935985492082500`.
Corrected image: `kwg-mt5-desktop:m5-recovered-0084f2b63b25`.

The recovery operation reported `order_sent: false`. M5 provider calls remain
disabled (`JEV_M5_LIVE=false`); this recovery does not authorize enabling them.

## Verification

175 targeted tests passed, including the reproduced acknowledgement regression,
strict rejection of changed/missing receipts and new manual activity, recovery
backup/owner-pause preservation, shared limits, balance reconciliation and M5.
Two distinct fresh reports confirmed M5 shadow active after restart. Subsequent
quotes and M5 history were fresh/valid; shared pause was null. The ready scorecard
reported zero candidates and an unmet veto gate. Worker version
`2bc6b99f-fdaa-4667-acc6-136155466fc8` still has `JEV_M5_LIVE=false`.

## Subsequent owner-approved step 6

After recovery verification, the owner explicitly approved the last 50 M5 candles
and trend labels/categorical features to TypeSafe within the shared $5 budget.
Commit `8848f5b` enabled M5 calls; both it and recovery commit `010840d` were pushed
to main. Worker version `6f5f282a-601b-4a65-9cef-74773eb88484` is deployed with
`JEV_M5_LIVE=true`. Gold remains shadow; BTC remains paused by owner.

First receipt: bar_time `1791936000` (2026-10-14 00:00 UTC), model `jev-1.13.0`,
status `ok`, choice `sell`, confidence `0.52`, completed_at `1791936316.198`,
received `1791936316.7798202`. The input hash matches the shadow candidate:
`3eba3ed7387972573c857a6eadd6fcbb1d89f8824b1ac8093fd79528843bb60d`.
Arrival was 16.780 seconds after candle close, within the 90-second deadline.
The strategy disarmed this candidate for checked-entry price deviation; it did
not submit an order. Thirty Worker tests passed before enablement.
