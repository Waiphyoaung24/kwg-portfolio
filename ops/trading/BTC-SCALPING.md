# BTC timed demo policy

BTC only: completed M1 EMA trend with three-bar slope, 0.01 lot, one position.
Request a close once the journal's observed open time is at least 60 seconds old,
even when losing or entries are paused. The runner polls about every five seconds;
broker latency, unavailable quotes, disabled execution, or disconnection can delay
closure. SL 2 ATR and TP 3 ATR remain broker-side. Reconcile an uncertain close;
never blindly repeat it. An existing BTC position inherits this timer at cutover.

Cooldown is 60 seconds from confirmed close. A new completed candle, trend/slope,
fresh quotes, spread <= 25% ATR, and all account checks are still required.
M1 spread checks may block most entries; this change does not promise frequency
or profitability. Gold strategy, account loss baselines, daily 1% / drawdown 5%
limits, and entry risk ceiling 0.1% are preserved.

## Deployment

1. Run locally:
   powershell -NoProfile -ExecutionPolicy Bypass -File ops/trading/stage-two-symbol-pilot.ps1 -BtcScalp
   Enter SSH passphrase locally. Require BTC_SCALP_REVIEW_PASSED.
2. Publish matching status Worker and dashboard before the runner cutover, so the
   new strategy identifier is accepted and accurately labeled. Existing M15 is
   still supported while waiting.
3. On the VPS, use the exact stage path and reviewed hash from step 1:
   python3 -B "$stage/cutover-two-symbol-pilot.py" "$stage" --reviewed-code-sha256 "$reviewed"
   This backs up files and both journals, verifies the current image and code,
   stops the single runner, migrates atomically and recreates the services.
4. Verify BTC strategy btc-ema-v1-m1-scalp-60 and Gold strategy unchanged using
   /status?symbol=BTCUSD and /status. Confirm close receipts in broker history.

The migration only accepts the reviewed continuous code
7338be40752337c8ce10bb0e65ac6ac58e3d3c83bc94e395caf56fe3445feb7d.
It refuses paused BTC/account state rather than resetting loss or owner pauses.
If cutover fails, preserve backups and inspect; do not restore an old runner over
new journals. No new broker request is sent by staging or migration itself.
