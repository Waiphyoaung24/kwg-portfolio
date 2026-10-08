# Autonomous demo pilot

This is a product pilot, labelled **unqualified**, for the pinned USD
VTMarkets-Demo account and XAUUSD-VIP. It does not change research qualification.
No deployment or activation is implied by merging this implementation.

## Behavior

- Fixed M15 EMA strategy with the existing three-bar slope filter; completed
  candles only. Startup and missed candles establish a baseline without entry.
- One 0.01-lot position, with broker SL/TP at two/three ATR. The existing executor
  rejects entry when estimated stop loss exceeds 0.1% of equity, quotes are stale,
  spread is excessive, or account/symbol/protection checks fail.
- A 1% UTC-day equity loss or 5% peak-equity drawdown latches a pause. These
  thresholds pause entries; they cannot guarantee a maximum realized loss.
- Separate persistent journal, one activation, at most seven days. Restart does
  not reset limits or retry uncertain submissions. Manual control is disabled
  in pilot mode, and the runner holds the manual executor's process lock.
- Owner pause stops new entries. Existing positions retain broker SL/TP. At
  expiry the runner attempts to close only its confirmed position, then
  reconciles broker deals. An uncertain close is never blindly resubmitted.
- Missing history, account activity outside the pilot, code/offset changes,
  partial fills and uncertain execution require review. Pauses do not auto-resume.
- The page shows state, broker-reconciled realized P&L, floating P&L, recent
  trades and time remaining. Stale or unauthenticated data clears current values.

## Local verification

From the repository root in PowerShell:

```powershell
python -B -m unittest discover -s ops/trading -p test_demo_pilot.py
python -B -m unittest discover -s ops/trading -p test_demo_one_shot.py
python -B -m unittest discover -s ops/trading -p test_control_server.py
python -B -m unittest discover -s ops/trading -p test_status_server.py
node --test src/scripts/trading-pilot.test.mjs src/scripts/trading-status.test.mjs ops/trading/worker/test.mjs
npm run build
node ops/trading/build-status-page.mjs
```

Run `npx --no-install e2e run tests/trading-pilot.e2e.ts tests/vault-trading.e2e.ts`.
The runner starts the development fixture server on port 8899 automatically.
Set `APP_URL` only when intentionally using an already running fixture server.
These tests intercept trading API requests; they do not submit broker orders.
The fixture flag is development-only and is passed only to the test server.

## Deployment and standby

The initial deployment from the verified foundation image is automated by
`preflight-demo-pilot.ps1` and `deploy-demo-pilot.ps1`. Run them from normal
PowerShell and enter the SSH passphrase locally. Both support `-DryRun` for
local syntax checks. The installer pins the foundation image, verifies bundle
hashes, repeats broker preflight, backs up the journal/files/environment, then
recreates the services and checks fresh standby status. It refuses an already
configured pilot; do not rerun it against the deployed pilot or use it to reset
state. `review-demo-pilot.ps1` reads the deployed activation preview without
activating it. The equivalent deployment requirements follow.

1. Record the reviewed Git revision and source hashes. Keep Algo Trading off.
   Verify the demo account has no positions or orders and the existing manual
   attempt is closed/disarmed. Preserve SQLite backups and the current image
   rollback tag; retain the persistent home and status volumes and VNC password.
2. Deploy the matching trading sources and Compose configuration. The image
   must include `demo_pilot.py`, `demo_one_shot.py`, `gold_experiment.py`,
   `gold_signal.py`, `mt5_data.py`, `control_server.py` and `desktop.sh` from the
   same reviewed revision. Build the image before recreating the desktop.
3. Deploy `status_server.py` and the generated `trading.html`/`trading-bot.html`.
   These HTML files are legacy sidecar copies. The public trading page is
   forwarded to the portfolio's Dokploy origin: commit/push the reviewed source
   to its deployment branch and run the normal portfolio deployment too. Verify
   the resulting page contains the pilot panel; an old page rejects the new
   status mode even when the status API is healthy.
   Publish the matching trading Worker; its new shared import
   `src/scripts/trading-pilot.mjs` must be in the deployment checkout. Rebuild
   the research MCP Worker if it must consume the new status mode. Preserve
   existing secrets and Cloudflare Access policies: research stays status-only.
4. Set `MT5_RUN_MODE=pilot` in the private Compose environment, preserving the
   existing login, offset and control secret. Recreate the desktop and status
   services with the reviewed image. Default mode remains `observer`.
5. Verify fresh `/status` reports `mode=autonomous-demo`, `pilot.status=standby`,
   and the page shows owner activation required. Verify unauthenticated access
   fails and the research credential cannot POST control requests.

Preview from the VPS SSH terminal while Algo Trading is off:

```bash
docker exec -it --user mt5 kwg-mt5-desktop bash -lc \
  'script -q -e -c "wine /opt/python/python.exe /opt/trading/demo_pilot.py preview" /dev/null'
```

Review the account, symbol, strategy, equity, risk limits and `code_sha256`.
Preview sends no orders. Resolve standby/authentication failures before activation.

## Explicit owner activation

Only after reviewing the preview and deployment, enable Algo Trading on the
demo terminal. Choose an explicit UTC end within seven days. Replace both
placeholders below with the reviewed values; the CLI refuses a mismatched hash.

```bash
docker exec -it --user mt5 kwg-mt5-desktop bash -lc \
  'script -q -e -c "wine /opt/python/python.exe /opt/trading/demo_pilot.py activate --enable-demo-execution --end-utc END_UTC --reviewed-code-sha256 REVIEWED_HASH" /dev/null'
```

Confirm `DEMO_PILOT_ACTIVATED`, fresh active status and the displayed end time.
Activation does not force a trade: the runner waits for the next eligible
completed-candle crossover. Demo fills and a short pilot do not establish
profitability or live-account suitability.

## Pause, expiry and recovery

Use **Pause new entries** on the authenticated page. If the page is unavailable:

```bash
docker exec --user mt5 kwg-mt5-desktop \
  touch /home/mt5/.wine/drive_c/users/mt5/gold-pilot.pause
```

Confirm the next fresh status says paused. Deleting the pause file does not
clear a persisted pause. Preserve `gold-pilot.sqlite3` and its receipts; never
delete/reset the journal to bypass an uncertain outcome or risk limit.

If expiry cannot close (for example, the market is closed or Algo Trading is
off), reconcile the actual MT5 position and history manually. Keep the runner
available for reconciliation. It cannot promise flat exposure at the deadline.
Before rolling back to observer mode, confirm all pilot exposure is flat and
the journal is resolved; retain the journal and backups for review.
