# Gold M5 Jev decision layer — runbook

Demo account only. Gold only (`XAUUSD-VIP`). Jev (TypeSafe `jev-1.13.0`) can
block a code-signalled entry in veto mode. It never opens, sizes, modifies or
closes a trade. Design and decision log:
`docs/superpowers/specs/2026-10-13-jev-gold-m5-integration.md`.

## How it works

1. On each completed M5 candle, the runner (`demo_pilot.py`, strategy
   `gold-ema-v1-m5-trend-jev`) evaluates the EMA20/EMA50 trend with a three-bar
   slope. Entry candidates are the candles where the trend strategy would arm.
2. For each candidate it publishes `jev-m5.json` with `state_json`, the exact
   canonical text of the categorical features and last 50 bars, plus its
   SHA-256. The text never contains the code's side, account data or
   credentials. The feed is refreshed until the candle close + 90 s.
3. The Worker cron (`JEV_M5_LIVE=true`) reads `/jev-m5`, verifies the hash,
   reserves budget from the shared $5 ledger, calls Jev once per candle and
   stores the receipt under `m5:<bar_time>`. It does not call Jev after
   close + 70 s.
4. The Worker forwards the receipt to `/control/jev-receipt`. The status sidecar
   passes it to `desktop:8001`, which stores it insert-only in
   `C:\users\mt5\jev-m5-receipts.sqlite3`.
5. **Shadow:** the code trades as normal, and every candidate is journalled in
   `jev_candidates`.
   **Veto:** the entry waits for a receipt and submits only if Jev chose the
   same side with confidence ≥ 0.5, the receipt is on time (≤ close + 90 s,
   re-checked at submission) and the hash matches. Every other outcome skips
   the entry.
6. `jev_m5_scorecard.py` runs every minute on the host as a read-only systemd
   timer and publishes `jev-m5-scorecard.json`. `/vault/trading` shows it in the
   Jev M5 panel.

## Veto gate (frozen)

Normal veto promotion requires all of these, and explicit owner approval:

- ≥ 50 closed **shadow** trades with resolved net P/L (`realized_net_usd`, net of
  profit, commission, swap and fee);
- bad receipts < 20% of due shadow candidates. Bad = not an on-time valid `ok`;
  missing, late (by completion time or arrival), invalid, failed and no-state
  rows all count;
- the average net P/L of the trades Jev would have kept is strictly greater
  than the average across all shadow trades.

These are demo fills on an unqualified strategy. Passing the gate is a minimum
review sample, not evidence of edge, and never automatic.

## Explicit unqualified demo veto test

The owner may separately approve a demo-only functional test before the frozen
qualification gate passes. Use the current reviewed source stage, then:

```sh
python3 -B "$stage/promote-jev-veto.py" "$stage" --owner-approved --demo-test
```

This opt-in bypasses only the qualification gate. It requires a ready scorecard,
the pinned Gold demo journal, no Gold/shared pause, and no unresolved Gold
attempt. Verify the actual pinned demo account and flat Gold exposure before
running it. It backs up the journal, records the mode change and the unmodified
scorecard in `jev_demo_tests`, then runs the existing veto behavior. Risk limits,
trade sizing, receipt validation and the shared $5 budget do not change. The UI
shows VETO; this is not a claim that the qualification gate passed. It persists
until owner-directed demotion with `--owner-approved --demote`. Test-mode trades
are veto trades, not closed shadow trades toward the 50-trade gate.

## Deployment (owner-run, in this order)

1. Locally, in PowerShell, with the SSH passphrase entered there:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File ops/trading/stage-m5-jev.ps1
   ```

   Keep `M5_JEV_STAGE`, `M5_JEV_REVIEWED_CODE` and `M5_JEV_REVIEW_PASSED`, and
   confirm `M5_JEV_SCORECARD_PUBLISHER_INSTALLED`. This
   uploads files, runs the read-only journal review and installs the scorecard
   publisher (`kwg-jev-m5-scorecard.timer`). It does not stop the runner or
   change the journal. `-DryRun` checks syntax without SSH.
2. Deploy the Worker with `JEV_M5_LIVE="false"` (`wrangler deploy --keep-vars`)
   and publish the frontend through Dokploy. Both must accept the new strategy
   string before the cutover.
3. On the VPS:

   ```sh
   python3 -B "$stage/switch-pilot-m5.py" "$stage" --reviewed-code-sha256 "$reviewed"
   ```

   The script refuses **before stopping the runner** if Gold has an unresolved
   attempt, any pause, the owner pause file, a latched shared pause, an expired
   window, a non-M1-trend strategy or a code mismatch. On success it backs up
   both journals and prints `M5_JEV_SHADOW_DEPLOYED` only after two fresh
   `active` M5 shadow reports.
4. Set `JEV_M5_LIVE = "true"` in `ops/trading/worker/wrangler.toml` and redeploy
   the Worker. Then confirm the first receipt in the Worker logs
   (`Jev M5 ...`) and that the panel's counts start moving.
5. Run shadow until the panel shows the gate met. Review the scorecard, then:

   ```sh
   python3 -B "$stage/promote-jev-veto.py" "$stage" --owner-approved
   ```

   Promotion re-checks the gate on the host and inside the container, backs
   up the journal and writes an audit row in `jev_mode_changes`. Return to
   shadow at any time with `--owner-approved --demote`.

## Stop, pause and recovery

- **Stop Jev spend:** set `JEV_M5_LIVE="false"` and redeploy the Worker. Shadow
  keeps trading without receipts. Veto then skips every entry (fail-closed).
- **Pause entries:** use the existing pilot pause control. A pending veto entry
  is dropped on pause and is never replayed.
- **Stop exporting the scorecard:** stop `kwg-jev-m5-scorecard.timer`. The panel
  shows "unavailable" after 120 s. Trading is unaffected.
- **Cutover failed after the runner stopped** (`CUTOVER_INCOMPLETE`): keep the
  backups (`before-m5-jev-*` in the MT5 home, the host backup directory and
  the `kwg-mt5-desktop:m5-jev-base-*` image tag). If the journal was switched
  but the restart failed, retag the built image and `docker compose up -d
  desktop status`. Never restart the old M1 runner on a switched journal; it
  refuses and may latch a pause. Restoring means restoring both backups and
  the base image together.
- **Mode change failed** (`MODE_CHANGE_INCOMPLETE`): if `RUNNER_STOPPED` was
  printed, inspect the journal and the `gold-pilot-before-jev-mode-*` backup
  before recreating the desktop.

## Known limits and owner decisions

- **BTC journal:** when BTC is active, the cutover rewrites only the BTC pilot
  `code` field in the same transaction, because the runner refuses mismatched
  shared identities. All other BTC data stays byte-identical, and the BTC code
  is verified against the deployed code first.
- **Refuse, don't preserve:** the cutover refuses an open Gold position or a
  latched pause instead of carrying them over. Run the cutover while flat.
- **Last receipt (waived):** the panel does not show the latest receipt's
  choice, confidence or age. Use Worker logs and the scorecard counts.
- **No receipt re-forward:** if a forward fails, that candle has no receipt and
  veto skips it.
- **Coverage gaps:** candidates within a few hours of the daily gold break can
  still be sampled (`gap_in_window` is true), but a state build failure records
  `no_state`, which counts as a bad receipt.
- **Costs:** about 288 calls/day at most on M5. Calls happen only on candidate
  candles, from the shared $5 ledger with the M15 observer.

## Veto dashboard reporting — 2026-10-14

The read-only publisher now exports `veto` separately from the frozen shadow
qualification fields. It joins veto candidates to their actual order attempts
and stored receipts. Counts cover all recorded veto decisions; the latest 20
show receipt status, validated choice/confidence, submission/outcome, recorded
block reason and resolved net P/L. A submitted request is not necessarily a fill.
Blocked means no submission, including non-Jev safeguards; missing P/L is never
zero. Pending entries come from the pilot journal. Veto results never contribute
to the shadow gate. This reporting makes no paid requests and changes no limits.

Deployment requires both the website and the host publisher update. After
restoring SSH access, inspect `systemctl cat kwg-jev-m5-scorecard.service` and
back up its current root-owned publisher file before replacing only
`/opt/kwg-mt5-qualification/jev-m5-scorecard/jev_m5_scorecard.py` with the reviewed
version. Run the existing scorecard service and verify the JSON's `veto` section
and fresh timestamp, then check the dashboard. Do not rerun bot cutover or
restart the trading container for this reporting update. The Worker already
passes the scorecard through; its budget/configuration need no changes. An older
publisher remains compatible, but the new panel explicitly marks veto activity
unavailable. Publisher deployment initially required restoring SSH access; deployment
evidence is recorded below.

## Clock warning investigation — 2026-10-14

`poll_once` receives a timestamp captured at the beginning of the poll. It does
broker reconciliation and guard reads before passing that same timestamp to
`read_gold`. A newer tick can therefore legitimately have a timestamp later
than that supplied checking time. The regression in `test_verify_demo.py`
reproduces a tick arriving 200 ms after poll start: the explicit old timestamp
fails, while the existing `read_gold(..., now=None)` path samples after the tick
read and correctly accepts it. A genuinely future tick still fails.

This establishes a local timing defect mechanism, not proof that every VPS
warning has that cause. SSH was unavailable, so VPS NTP synchronization and
actual tick/host skew could not be checked. Runtime files and the strict
future/stale guards remain unchanged. Before a runner fix, capture host NTP
status and tick receipt timing, then review how post-read time affects candle
boundaries and pending-entry deadlines. Deploying runner source also requires
its pinned code-identity migration; do not hot-edit the running container or
clear its safety pause.


### Publisher deployment and live clock evidence — 2026-10-14

At 08:50:50 UTC (15:50 Bangkok), deployed the publisher from `e058686`;
SHA-256 `289fc021c81cbde2d42fb0036ec203eceba83a65a4323eb2cec81f6263094450`.
Preserved backup:
`/opt/kwg-mt5-qualification/jev-m5-scorecard/jev_m5_scorecard.before-e058686-1791967849874602729.py`.
The timer remains active; a subsequent automatic report at 08:52:59 UTC was
ready. It reported 33 veto decisions, 6 submitted, 27 blocked; 24 OK receipts,
9 missing; 5 closed trades net -$3.37 and one open trade. Block reasons were
18 clock warnings (including two disarmed attempts), 5 Jev hold choices and
4 confidence-below-0.5 decisions. No runner restart, journal edit, risk limit
change or budget change was performed. The website still served the old panel
at verification and requires deployment of main's reporting UI.

Host `timedatectl` reported `NTPSynchronized=yes`. A live runner warning had
sampled_at 1791967872.563731 versus normalized tick time 1791967872.596:
quote age -0.032269 seconds. The immediately following samples were fresh.
A separate read-only MT5 probe applied the existing 10800-second server offset:
40 quotes, 2–7 ms read latency, 157–920 ms post-read quote age, no future ticks.
This supports the early poll timestamp mechanism reproduced by the regression,
but does not rule out intermittent broker skew outside the sample. A runtime
fix still needs candle-boundary/deadline tests and a reviewed code-identity
migration; strict future/stale guards remain unchanged.

### Clock sampling fix on main — 2026-10-14

The pilot now calls the existing post-read clock path in `read_gold` and uses
that sampled time for candle assessment and subsequent entry decisions. Pending
Jev receipts are evaluated after the quote read, against the refreshed time;
a slow read cannot extend the 90-second deadline. The final submission deadline
check remains in place. Negative quote ages and quotes older than 30 seconds
are still rejected without tolerance. Risk limits, sizing and budget are unchanged.
Regression tests cover a quote arriving after poll start, a read crossing a
candle boundary and a read crossing the Jev deadline.

This is a source fix, not a live runner upgrade. The desktop runs a pinned
source identity; deploying this change needs a reviewed migration of the
existing M5 journals and preserved backups. Do not copy the file into the live
container or restart with mismatched journal hashes. The website deployment
and read-only publisher do not replace the trading runner.
