# Gold M1 + Bitcoin M15 demo pilot

The owner selected one shared account runner with independent symbol views and
journals. This is an unqualified demo product pilot, not a profitability claim.

| Setting | Gold | Bitcoin |
| --- | --- | --- |
| Broker symbol | XAUUSD-VIP | BTCUSD |
| Completed candles | M1 | M15 |
| Entry rule | EMA20/EMA50 trend, three-bar EMA slope | Same |
| Spread ceiling | 25% of ATR14 | 25% of ATR14 |
| Volume / positions | 0.01 lot / one per symbol | 0.01 lot / one per symbol |
| Protection | Stop 2 ATR, target 3 ATR | Same |
| After-close cooldown | Five minutes | Five minutes |

Account equity, not separate symbol balances, drives the 0.1% entry ceiling,
1% daily pause and 5% drawdown pause. Unknown account activity, unprotected or
unowned positions, and ambiguous execution outcomes block further entries.
The single runner holds the existing account execution lock. It reconciles both
journals before checking account-wide exposure and submitting any new order.

The migration keeps Gold's existing position, receipts, latched pause, original
start/end and risk history. Shared limits live in `account_limits` in the existing
Gold database. BTC gets its own `btc-pilot.sqlite3`, `btc-pilot.pause` and
`btc.json` snapshot. BTC starts in standby and cannot enter until activated.
The original pilot expiry is not extended by adding BTC.

## Deployment sequence

1. Run the local staging review in normal PowerShell, entering the SSH passphrase
   locally:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\wai19\Desktop\kwg-portfolio\ops\trading\stage-two-symbol-pilot.ps1
   ```

   Preserve `TWO_SYMBOL_STAGE`, `TWO_SYMBOL_REVIEWED_CODE` and
   `TWO_SYMBOL_REVIEW_PASSED`. This uploads a private stage and reads broker/journal
   state; it does not stop the runner, migrate journals or place orders.

2. Publish the matching portfolio UI through the existing main/Dokploy flow and
   deploy `worker/wrangler.toml`. The research MCP Worker remains Gold-only; its
   default normalization still rejects BTC. Existing owner Access authentication
   and same-origin POST checks remain required.

3. On the VPS, use the exact reviewed stage path and code hash:

   ```sh
   python3 -B <stage>/cutover-two-symbol-pilot.py <stage> --reviewed-code-sha256 <reviewed-code>
   ```

   This verifies the previous image and every staged file, builds from that
   existing image without network access, saves host and SQLite backups, stops
   the exact runner, migrates under its lock, and restarts with
   `MT5_PILOT_SYMBOLS=XAUUSD-VIP,BTCUSD`. Success requires
   `TWO_SYMBOL_STANDBY_DEPLOYED`, a fresh BTC standby report and preserved Gold
   expiry/pause. If interrupted, preserve the backup and inspect; do not blindly
   restart the old code against migrated state.

4. Verify authenticated Gold `/api/trading/status` and Bitcoin
   `/api/trading/status?symbol=BTCUSD`, plus their dashboard views. Verify research
   credentials still cannot reach either preview or pause controls.

5. Review fresh BTC data and account state before activation. The deployed CLI
   supports `activate-btc --enable-demo-execution --reviewed-code-sha256 <hash>`.
   It must run under Wine's pseudo-terminal after deliberately stopping the
   runner supervisor, since it acquires the same account lock. It preserves the
   original expiry, requires fresh admissible BTC data and leaves Gold's pause
   unchanged. Do not use the old flat-account resume script for this migration.

## Views and controls

- `/vault/trading` shows Gold; `?symbol=BTCUSD` shows Bitcoin. Links select a view
  only. Neither link activates or pauses execution.
- Prices, trade results, position levels, pause requests and sound notifications
  are scoped to the selected symbol. A cross-symbol response clears the view.
- Each navigation starts a fresh chart/sound baseline. Historical or already-open
  entries do not trigger a catch-up sound. Synthetic Gold replay is only shown
  in the Gold view.
- BTC activation does not guarantee entries. Spread, signal, cooldown, account
  and broker checks still apply at each submission.

## Validation

Fake-broker tests cover open-position migration and backup, account-wide loss
latching, both symbols' ownership/history, standby, native BTC M15 reads,
sequential BTC entry alongside Gold, and duplicate/restart suppression. Boundary
tests reject wrong-symbol snapshots/journals and scope owner pause requests.
Browser tests exercise navigation, independent figures and stale/wrong-symbol
clearing. These tests do not place VPS orders.
