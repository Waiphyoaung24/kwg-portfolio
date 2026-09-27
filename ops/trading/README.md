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
diagnostic and one-shot observer blocked as intended. Live candle transitions,
restart persistence, and advancing tick freshness still need qualification
during an open gold session. No observer is running unattended.
Review live signals and risk checks before a separate demo-order implementation.
Keep Algo Trading off.

## Read-only Vault status

The observer now publishes a small JSON snapshot to a **separate** Docker
volume. `kwg-trading-status` serves that snapshot on `dokploy-network` with no
host port; it cannot read MT5's home volume. `/vault/trading` requests a
same-origin Cloudflare Worker route at `/api/trading/status`. The Worker requires
Cloudflare Access identity, checks the exact approved viewer email, and fetches
the status origin through the existing Cloudflare Tunnel. It exposes no broker
login, balance, password, or order operation. A missing heartbeat becomes
`offline`; a stale gold quote remains `blocked`.

On the VPS only, set `MT5_DEMO_LOGIN` in this Compose project's private `.env`,
then deploy the observer and private status service:

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

Once the market is open and freshness passes, run one bounded observation:

```sh
docker exec -it kwg-mt5-desktop wine /opt/python/python.exe /opt/trading/observe-gold.py --login YOUR_DEMO_ACCOUNT_NUMBER --state 'C:\users\mt5\gold-observer.sqlite3' --once
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
