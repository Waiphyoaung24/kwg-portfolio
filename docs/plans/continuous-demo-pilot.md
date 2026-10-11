# Continuous sequential demo pilot

Owner selected continuous sequential demo trading: one position per symbol,
automatic recovery after verified temporary disconnections, until owner pause.
Keep entry sizing, spread filters, cooldown, stops and account loss limits.

1. Add an explicit continuous run policy; existing bounded journals retain expiry.
2. Retry unavailable broker data without clearing owner or risk pauses. Reconcile
   both journals and verify account, history, protection and limits before entry;
   establish a new candle baseline after recovery.
3. Preserve risk thresholds when midnight equity was missed; never invent equity.
4. Migrate existing journals with backups and reviewed source identity, without
   submitting orders or resetting balances, history or loss thresholds.
5. Extend status validation and show monitoring separately from entry permission.
6. Verify disconnect/recovery, open position monitoring, sequential entries,
   owner/risk stops, migration, status contracts and desktop/mobile UI.

Deployment requires the matching status service, Worker and website. Stage and
review on the trading VPS before switching the runner; preserve rollback data.

Deployment order:

1. Run `stage-two-symbol-pilot.ps1 -Continuous` in normal PowerShell. This is
   read-only against the journals and requires the owner's SSH passphrase.
2. Publish the matching Worker and website before the backend migration; older
   validators reject a started pilot with a null end time.
3. Run the staged `cutover-two-symbol-pilot.py` with the returned code hash. It
   builds and verifies the image before stopping the runner, backs up both
   journals, then updates their policy in one rollback-journal transaction.
4. Verify `CONTINUOUS_DEPLOYED`, both symbol policies and preserved positions.
   If cutover fails, preserve receipts/backups and inspect before restarting;
   the old code cannot interpret the new continuous journals.

Verified locally: disconnect recovery, sequential re-entry after cooldown,
owner-paused position reconciliation, permanent identity/loss pauses, atomic
migration rollback, status contracts, and seven fixture browser tests.
The production review and cutover remain pending. This changes operation,
not strategy qualification or expected profitability.

The first VPS review preserved the old combined exposure-unavailable/pending-order
pause. The migration now clears that exact legacy pause only after current account,
history, balances, owned protected positions and absence of pending orders pass
verification. It repeats these checks during apply; all other pauses survive.
Restage the helper before cutover. The core code hash is unchanged by this helper fix.
