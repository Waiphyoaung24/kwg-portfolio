# MT5 compatibility probe

## Current scope and next steps

The first strategy is gold only (`XAUUSD-VIP`) on the demo account. Bitcoin
results below document earlier compatibility checks; Bitcoin is excluded from
the first strategy. The existing diagnostic script still checks both symbols.

Next: qualify fresh gold quotes and timestamp handling when the market is
available, then implement the M15 EMA20/EMA50 strategy in signal-only mode.
Review signals and risk checks before enabling demo orders, then connect status
to `/vault/trading`. Keep Algo Trading off during qualification.

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

This verifies account identity, demo mode, Algo Trading off, both exact symbols,
bid/ask quotes, and 250 completed M15 bars. Quote age is reported; a returned
quote may be old while a market is closed. Repeat the check after a container
restart to qualify persistence and reconnection. No order functions are used.

VPS qualification passed on 2026-09-27: the pinned VTMarkets-Demo account,
Algo Trading off, BTCUSD and XAUUSD-VIP prices, and 250 completed M15 bars
per symbol were verified before and after a container restart. Newly selected
symbols initially returned empty quotes; subsequent checks succeeded after
subscription synchronization. `/tmp` uses tmpfs so stale display locks do not
prevent restarts.

Freshness is not qualified: BTCUSD timestamps were approximately three hours
ahead of the VPS clock and the gold quote was approximately 22 hours old.
Investigate timestamp semantics and clock synchronization before enabling
entries; do not treat a negative quote age as fresh or silently subtract an
assumed timezone offset. Autonomous orders remain disabled.

Local verification:

```sh
python -B ops/trading/test_verify_demo.py
bash -n ops/trading/desktop.sh
docker compose -f ops/trading/compose.yml config --quiet
```

Python 3.12.10 and Wine 9 remain a qualification environment, not a completed
autonomous trading deployment. Keep the desktop private and qualify a maintained
runtime before production use. The MT5 installer is downloaded from MetaQuotes;
its version can change independently of this image.
