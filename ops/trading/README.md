# MT5 compatibility probe

## Current scope and next steps

The first strategy is gold only (`XAUUSD-VIP`) on the demo account. Bitcoin
results below document earlier compatibility checks; Bitcoin is excluded from
the first strategy. The current diagnostic script checks gold only.

The M15 EMA20/EMA50 strategy is implemented in signal-only mode. It uses
250 completed candles, SMA-seeded EMAs, Wilder ATR14, and a 10%-of-ATR
spread limit. It records one observation per new candle in SQLite; the first
candle after startup or a missed interval is a baseline. No order API is called.
The updated image was deployed on 2026-09-27. The pinned demo and Algo-off
guard passed, but the gold quote was stale during market closure, so both the
diagnostic and one-shot observer blocked as intended. The VPS now runs the
signal-only observer continuously. Live candle transitions, restart persistence,
and advancing tick freshness still need qualification during an open gold session.
Review live signals and risk checks before a separate demo-order implementation.
Keep Algo Trading off.

## Read-only Vault status

The observer now publishes a small JSON snapshot to a **separate** Docker
volume. `kwg-trading-status` serves that snapshot and the prebuilt trading page
on `dokploy-network` with no host port; it cannot read MT5's home volume.
Cloudflare routes `/vault/trading` and `/api/trading/status` to the same Worker,
without moving the rest of the portfolio from its current origin. The Worker requires
Cloudflare Access identity, checks the exact approved viewer email, and fetches
the status origin through the existing Cloudflare Tunnel. It exposes no broker
login, balance, password, or order operation. A missing heartbeat becomes
`offline`; a stale gold quote remains `blocked`.

On the VPS only, set `MT5_DEMO_LOGIN` in this Compose project's private `.env`.
For the verified three-hour lead on this demo, also set
`MT5_SERVER_OFFSET_SECONDS=10800`; the default is zero and fails closed when
the broker clock is ahead. Then deploy the observer and private status service:

```sh
docker compose --profile status up -d --build
```

Keep `.env` outside Git. The desktop process starts the signal-only observer
when the login is set; it never calls an order API. Confirm the private service
is reachable from `dokploy-network` and has **no host port** before adding its
Cloudflare Tunnel public hostname. In Cloudflare Zero Trust, protect that
hostname with an Access **Service Auth** policy for a dedicated service token.
The Worker receives the token as `STATUS_ACCESS_CLIENT_ID` and
`STATUS_ACCESS_CLIENT_SECRET` secrets; set `STATUS_ORIGIN_URL` to the protected
`https://.../status` origin and `ALLOWED_VIEWER_EMAIL` to the exact owner email
as secrets too. Protect the Worker itself with Access for that email across all
routes, leave `workers.dev` disabled, then deploy from `ops/trading/worker` with
Wrangler. No secret values belong in source, commands, logs, or chat.

After changing `src/pages/vault/trading.astro`, build Astro and regenerate the
self-contained page served by the private status service:

```sh
npm run build
node ops/trading/build-status-page.mjs
```

Commit `ops/trading/trading.html` with the source change, copy it and
`status_server.py` to the VPS Compose directory, then restart only the status
sidecar. Deploy the Worker routes with Wrangler afterward. The page and API
both require the one-email Worker Access policy; the origin accepts only its
dedicated service token.

The VPS status sidecar and Cloudflare Tunnel, Access policies, API Worker,
and trading page route were deployed by 2026-09-28. The sidecar returned HTTP
200 from `dokploy-network` and exposes no host port. The authenticated page at
`https://waiphyoaung.com/vault/trading` showed `XAUUSD-VIP` blocked with no
signal because the gold quote was stale. An unauthenticated page request
redirected to Access; direct access to `status.waiphyoaung.com` returned 403.
The status service runs as UID 10001, so a manually copied `status_server.py`
must be readable by that user (`chmod 644`).

The existing Vault password only hides links in the browser. Cloudflare Access
is the authorization boundary for this status API. Do not expose the MT5 desktop
or mount its home volume into the status service or portfolio app. Live M15
transitions are still unqualified; the dashboard must not label the observer
as trading autonomously.

Commit this directory's source and documentation only. Broker passwords,
`mt5.json`, SSH keys, and the terminal's persistent volume stay outside Git.
The VPS setup was deployed directly; committing or pushing this repository
does not update that running Compose project automatically.

## SDK probe

Run `bash ops/trading/check-wine.sh` on the Ubuntu Docker host. The probe uses
one CPU and at most 2 GiB RAM. It opens no ports, mounts no host files, and
does not load credentials, connect to a broker, or submit orders.

Inspect it with:

```sh
docker logs --tail 30 kwg-mt5-probe
docker inspect --format '{{.State.Status}} exit={{.State.ExitCode}}' kwg-mt5-probe
```

Success requires `SDK_IMPORT_OK` in the log and exit code `0`. This only proves
that Windows Python can import the MT5 SDK under Wine. It does **not** prove
MT5 terminal installation, terminal IPC, broker login, or unattended operation.
Those are separate checks before any trading deployment.

The container is retained for diagnostics. Do not place account credentials in
the image, this directory, browser commands, or logs. Python 3.12.10 is pinned
for this disposable compatibility probe; select a maintained runtime for the
deployed service after compatibility is established.

## VPS test result

On the supplied Ubuntu 24.04.4 VPS, Windows Python 3.12.10 successfully imported
MetaTrader5 5.0.6180 with NumPy 1.26.4 under Ubuntu Wine 9. The test printed
`SDK_IMPORT_OK 5.0.6180 3.12.10`.

NumPy 2.5.3 crashed on Wine's unimplemented `ucrtbase.crealf`; the probe pins
1.26.4 accordingly. An interactive console was also required for the retry
to avoid invalid Windows standard-stream handles. The script allocates a TTY
and bounds Wine commands with timeouts. Its shell syntax passes `bash -n`;
the clean, time-bounded probe also passed from a fresh Ubuntu container with
the same SDK marker and exit code 0 (`kwg-mt5-probe-clean`).

Remote diagnostic containers: `kwg-mt5-probe` (initial browser input formatting
failure) and `kwg-mt5-probe-v2` (successful manual retry). Retained container
files contain no broker credentials. This is an SDK import result only.

## Private desktop qualification

The Compose project is separate from the portfolio and existing Dokploy apps.
It runs as UID 10001, with one CPU/2 GiB limits, no Linux capabilities, and a
persistent `mt5-home` volume. The desktop uses a dedicated Compose network;
only `127.0.0.1:6081` on the VPS is published. Do not change this binding to
`0.0.0.0` or add a public proxy: desktop access relies on the SSH tunnel.

```sh
docker compose -f ops/trading/compose.yml up -d --build
```

From your own computer, keep this SSH connection open:

```powershell
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:6081:127.0.0.1:6081 root@187.52.117.116
```

Open `http://127.0.0.1:6081/vnc.html?autoconnect=1&resize=scale` in your browser.
Complete the official installer, review its terms yourself, and sign in to
your existing VTMarkets-Demo account inside the remote desktop. Leave Algo
Trading off. Credentials stay in MT5's persistent volume; do not paste them
into chat or a shell command.

After login, the following read-only check requires your expected demo account
number. It attaches to the terminal's saved session without taking a password:

```sh
docker exec -it kwg-mt5-desktop wine /opt/python/python.exe /opt/trading/verify-demo.py --login YOUR_DEMO_ACCOUNT_NUMBER
```

This verifies account identity, demo mode, Algo Trading off, the exact gold
symbol, fresh bid/ask quotes, and 250 completed M15 bars. It exits nonzero if
the gold quote is old or its timestamp is in the future. A closed-market quote
cannot pass. No order functions are used.

The diagnostic also emits sanitized JSON when blocked: raw `tick_time` and
`tick_time_msc`, the UTC sampling epoch, exact `quote_age_seconds`, terminal
check state and fetched history count/time. Positive ages over 30 seconds mean
stale; negative ages mean a future timestamp. Do not correct these by guessing
a broker timezone. The readiness check also evaluates completed-bar timing and
spread guards; receiving 250 bars alone is not a readiness pass.

On 2026-09-28, Market Watch displayed about 15:26 while synchronized VPS UTC
was about 12:26. The same three-hour lead appeared in raw tick and M15 bar
epochs. For this pinned demo only, the verifier accepts an explicit diagnostic
`--server-offset-seconds 10800`; it retains raw timestamps and checks adjusted
quote age and completed bars independently. Its default is zero offset, and
the running observer uses the same offset only when explicitly configured in
the private Compose `.env`. Confirm the Market Watch difference again after a
server DST change before reusing this option. This is evidence
collection, not proof that all MT5 Python timestamps use broker time.

### Bounded Batch 1 collection (read only)

The verifier can sample the pinned gold demo for at most one hour. A pass
requires 361 continuous five-second samples, fresh quotes, valid 250-bar
history and two consecutive completed M15 transitions. A weekend, missed
poll, stale quote or changed demo identity produces an inconclusive report.
The report contains sampled spread and allowlisted current contract fields,
but no account number, credentials or verified fee claim.

After copying the tested `verify-demo.py`, `mt5_data.py`,
`gold_qualification.py` and `gold_signal.py` into the existing desktop
container, run this on the VPS during the symbol's open session:

```sh
docker exec -it kwg-mt5-desktop wine /opt/python/python.exe /opt/trading/verify-demo.py --login YOUR_DEMO_ACCOUNT_NUMBER --collect-seconds 3600 --output 'C:\users\mt5\gold-qualification-YYYYMMDD.json'
```

For the observed three-hour server clock, add `--server-offset-seconds 10800`
to that command after rechecking Market Watch against UTC. A one-shot verifier
with the same option should pass first; the command without it should still
block on the raw future timestamp. Neither command changes the observer.

Choose a new filename on rerun; output creation is exclusive. Keep the JSON
private in MT5 home. Exit 0 means data continuity passed, not that strategy
or costs passed. Exit 2 means inconclusive. Do not commit the report.
Commission and swap rules require this exact demo account's dated broker
schedule; an absent or zero charge in deal history is insufficient evidence.

### Batch 2 offline comparison

`gold_costs.py` accepts only sourced, dated USD commission and supported
swap events. `simulate-gold.py --cost-profile PROFILE.json --windows
WINDOWS.json` is optional; without them the old three scenarios remain
hypothetical. A profile with unknown or uncovered costs is rejected. Window
JSON specifies fixed `development` and `validation` objects, each with
integer `start` and `end` bar timestamps. Keep profiles and detailed
reports private. `evaluation-policy.json` is **draft** and the offline
`evaluate-gold.py` cannot produce shadow eligibility from it. No candidate
or order path is installed.

Once deployed with the offset, the observer normalizes the displayed quote
timestamp; the one-shot verifier still retains raw broker timestamps. The
health-enabled dashboard separates API delivery, observer heartbeat, MT5
demo checks, quote freshness, fetched M15 history and strategy readiness.
It refreshes every 10 seconds while visible, bounds fetches to 8 seconds and
expires observer checks after 30 seconds. Old snapshots without explicit health
fields show unknown MT5/quote health until the observer and Worker are upgraded.
"Bars fetched" is a data count, not a claim that history passed strategy checks.
Quote failures retain history diagnostics; no orders are enabled by this view.

Once the market is open and freshness passes, run one bounded observation:

```sh
docker exec -it kwg-mt5-desktop wine /opt/python/python.exe /opt/trading/observe-gold.py --login YOUR_DEMO_ACCOUNT_NUMBER --state 'C:\users\mt5\gold-observer.sqlite3' --server-offset-seconds 10800 --once
```

The state path is the verified Windows home inside the persistent `mt5-home`
volume. Omit `--once` only while supervised; stop with Ctrl+C. On restart, run
`--once` again to confirm duplicate/baseline handling. Output is signal-only
JSON and contains no login or password. The SQLite file is the durable journal
and is ignored by Git. A fresh 30-second quote and a current, completed M15 bar
are both required; weekends, feed gaps, and future timestamps block signals.

VPS qualification passed on 2026-09-27: the pinned VTMarkets-Demo account,
Algo Trading off, BTCUSD and XAUUSD-VIP prices, and 250 completed M15 bars
per symbol were verified before and after a container restart. Newly selected
symbols initially returned empty quotes; subsequent checks succeeded after
subscription synchronization. `/tmp` uses tmpfs so stale display locks do not
prevent restarts.

Freshness is not qualified: BTCUSD timestamps were approximately three hours
ahead of the VPS clock and the gold quote was approximately 22 hours old in the
earlier check. On 2026-09-27, `timedatectl` reported a synchronized UTC clock,
while the gold tick was approximately 34.5 hours old during market closure.
Investigate timestamp semantics and clock synchronization before enabling
entries; do not treat a negative quote age as fresh or silently subtract an
assumed timezone offset. Autonomous orders remain disabled.

Local verification:

```sh
python -B ops/trading/test_verify_demo.py
python -B -m unittest discover -s ops/trading -p 'test_*.py'
bash -n ops/trading/desktop.sh
docker compose -f ops/trading/compose.yml config --quiet
```

Python 3.12.10 and Wine 9 remain a qualification environment, not a completed
autonomous trading deployment. Keep the desktop private and qualify a maintained
runtime before production use. The MT5 installer is downloaded from MetaQuotes;
its version can change independently of this image.

## Frozen gold history for baseline research

`export-gold.py` attaches to the same pinned demo with Algo Trading off. It
exports only gold OHLC, volume/spread fields, current contract specifications
and data provenance. It neither reads trade history nor sends orders. Bar
position 0 is excluded as the current bar, following the
[MetaQuotes API documentation](https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesfrompos_py).
Available history is limited by the terminal's chart history settings; partial
exports are labeled. Closed-market history can be captured without passing live
quote freshness, but the export always remains unqualified for strategy promotion.

Run on the VPS after the exporter is installed in the desktop image:

```sh
docker exec -it kwg-mt5-desktop wine /opt/python/python.exe /opt/trading/export-gold.py --login YOUR_DEMO_ACCOUNT_NUMBER --bars 10000 --output 'C:\users\mt5\gold-history-YYYYMMDD.json'
```

Use a new filename for each dataset; existing files are never overwritten.
The output stays in the persistent MT5 home and is not published by the Worker.
The JSON summary gives the exact byte-level SHA-256 and coverage. Preserve the
file and hash together for later evaluation. Contract fields describe the capture
date, not past contract terms. Commission, slippage and historical overnight
costs remain explicitly unknown; a recorded bar spread is not a bid/ask tick
path. Do not label any backtest qualified until those assumptions, timestamp
semantics, history gaps and chronological evaluation windows are resolved.

### Offline baseline signal replay

`replay-gold.py` consumes an exported dataset and required SHA-256. It reuses
`gold_signal.evaluate` on each completed 250-bar window, suppressing startup
and recovery signals. It substitutes bar close plus recorded spread for the
unavailable historical live quote; reports remain unqualified. It computes no
fills, trading returns or performance claims. No MT5 SDK or credentials needed.

```sh
python3 replay-gold.py --dataset gold-history-20260928.json --sha256 <verified-dataset-sha256> --output replay.json
```

Output is created exclusively (never overwritten). Keep datasets and reports
private outside Git. Run twice with different output filenames and compare
bytes to check determinism. Cost/fill evaluation remains a separate next step.

### Hypothetical trade simulation

`simulate-gold.py` uses the fixed baseline and three explicit cost scenarios;
see the researcher plan for frozen assumptions. It evaluates chronological
60% development / 20% validation windows, leaving newest 20% untouched.
Reports contain synthetic trade ledgers, costs, equity curves, source hashes
and limitations. Capital is hypothetical USD 100,000 per window. No MT5 calls.

```sh
python3 -B simulate-gold.py --dataset gold-history-20260928.json --sha256 <verified-dataset-sha256> --output simulation.json
```

All runs remain unqualified. Historical bid/ask paths, contract changes, actual
broker costs and live data qualification are unresolved. No result enables orders.

### One provisional offline comparison

`compare-gold.py` locks the private 10,000-bar dataset, evaluation source
hashes, windows, fixed hypothetical costs and risk rules before a proposal.
Run it with Python 3.12 and the sibling trading scripts in one private source
directory. Keep `/opt/kwg-gold-research/experiments/gold-exp-001/` owner-only,
and never commit its manifests, reports, prompt or proposal. Replace `TOOLS`
below with the directory containing the reviewed `ops/trading/*.py` files;
the directory must not be changed after `finalize`.

```sh
DATA=/opt/kwg-gold-research/datasets/gold-history-20260928.json
EXP=/opt/kwg-gold-research/experiments/gold-exp-001
TOOLS=/opt/kwg-gold-research/src
HASH=ba4f246746d861c9f61d82c7a09d17931cd74e9dea604ea2897853369dcf8614
umask 077
mkdir -p "$EXP"
chmod 700 "$EXP"
sha256sum "$DATA"
python3 -B "$TOOLS/compare-gold.py" prepare --dataset "$DATA" --sha256 "$HASH" --output "$EXP/manifest-prepared.json"
python3 -B "$TOOLS/simulate-gold.py" --dataset "$DATA" --sha256 "$HASH" --manifest "$EXP/manifest-prepared.json" --output "$EXP/baseline-preliminary-a.json"
python3 -B "$TOOLS/simulate-gold.py" --dataset "$DATA" --sha256 "$HASH" --manifest "$EXP/manifest-prepared.json" --output "$EXP/baseline-preliminary-b.json"
cmp "$EXP/baseline-preliminary-a.json" "$EXP/baseline-preliminary-b.json"
python3 -B "$TOOLS/compare-gold.py" finalize --dataset "$DATA" --sha256 "$HASH" --prepared "$EXP/manifest-prepared.json" --output "$EXP/manifest.json"
python3 -B "$TOOLS/simulate-gold.py" --dataset "$DATA" --sha256 "$HASH" --manifest "$EXP/manifest.json" --output "$EXP/baseline-a.json"
python3 -B "$TOOLS/simulate-gold.py" --dataset "$DATA" --sha256 "$HASH" --manifest "$EXP/manifest.json" --output "$EXP/baseline-b.json"
cmp "$EXP/baseline-a.json" "$EXP/baseline-b.json"
python3 -B "$TOOLS/compare-gold.py" research-input --dataset "$DATA" --sha256 "$HASH" --manifest "$EXP/manifest.json" --baseline "$EXP/baseline-a.json" --output "$EXP/research-input.json"
```

The research input contains development-only summary statistics and baseline
metrics; it excludes validation and reserved bars, volumes, account details
and credentials. There is no automatic Vibe-Trading model call. If its
provider and run limits are verified, save **one genuine proposal** as
`$EXP/proposal.json` with only `kind="ema20_slope_filter"`, integer
`lookback_bars` from 2 to 5 and a nonempty `hypothesis`. Then register it
before candidate simulation:

```sh
python3 -B "$TOOLS/compare-gold.py" register --manifest "$EXP/manifest.json" --proposal "$EXP/proposal.json" --output "$EXP/registration.json"
python3 -B "$TOOLS/simulate-gold.py" --dataset "$DATA" --sha256 "$HASH" --manifest "$EXP/manifest.json" --candidate "$EXP/proposal.json" --registration "$EXP/registration.json" --output "$EXP/candidate-a.json"
python3 -B "$TOOLS/simulate-gold.py" --dataset "$DATA" --sha256 "$HASH" --manifest "$EXP/manifest.json" --candidate "$EXP/proposal.json" --registration "$EXP/registration.json" --output "$EXP/candidate-b.json"
cmp "$EXP/candidate-a.json" "$EXP/candidate-b.json"
python3 -B "$TOOLS/compare-gold.py" compare --baseline "$EXP/baseline-a.json" --candidate "$EXP/candidate-a.json" --manifest "$EXP/manifest.json" --proposal "$EXP/proposal.json" --registration "$EXP/registration.json" --output "$EXP/comparison.json"
```

See the [experiment status](../../docs/superpowers/plans/2026-09-28-gold-first-experiment-results.md)
for the current blockers. An exploratory comparison never enables orders.
