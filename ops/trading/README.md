# MT5 compatibility probe

## Current development milestone — 2026-10-02

Owner chose to close Batch 2 for development and defer the 60-day/trade-count
qualification program. Batch 2 is **closed for development, unqualified**.
Batch 3's existing synthetic offline integration and separate Vibe learning app
are the next workflow; see the [current handoff](../../docs/superpowers/plans/2026-10-02-batch2-batch3-handoff.md).
The qualification policy and risk limits stay fixed. Unknown OAuth cost still
blocks gold dispatch; human approval remains required for promotion. Historical
evidence checkpoints below do not override this current development scope.
Account-worker credential/network isolation and catalog acceptance have now
passed; provider USD0 enforcement and the final real inference boundary remain
Batch 3 activation gates. They do not reopen Batch 2 development. Current
close-out evidence and acceptance boundaries are in the linked handoff.

### Batch 3 local readiness and fake-auth isolation

Run the read-only readiness check as the owner:

```powershell
python -B ops/trading/batch3_runner.py --preflight
```

It checks the fixed local Linux Docker engine and cached pinned image without
loading Docker credentials, starting services, pulling images or invoking AI.
Exit 2 is intentional while production/billing gates remain blocked. Engine
availability is separate from successful sandbox probes and real transport.

After explicit Docker startup authorization, the existing credential-free
rehearsal can run at a new exclusive output path:

```powershell
python -B ops/trading/rehearse-auth-isolation.py --output .superpowers/sdd/auth-isolation-UNIQUE
```

It checks fake refresh/401/deadline behavior and removal of only its own
containers. No network or credentials are mounted; no broker or model called.
First failure halts the rehearsal; preserve its artifacts rather than retrying
at the same path. Timeout cleanup does not imply its configuration was inspected.
Successful fixtures do not grant real OAuth or USD0 billing approval.

### Gold account acceptance (inference disabled)

The owner-selected supported model is fixed to `gpt-6-astra`. Same-account
renewal, signed binding, authenticated catalog access, isolated Internet worker
and forced-controller-termination cleanup passed. See the
[account results](../../docs/superpowers/plans/2026-10-03-batch3-account-acceptance-results.md)
for source/receipt identities, commands and scope limits. Provider $0 enforcement
remains unverified; real dispatch is blocked.

The owner seals committed sources with `harden-batch3.ps1 -Phase seal-account`.
Run that snapshot's `code/gold_account.py --seal-sha256 <manifest hash>` with
`python -I -B`, first `--mode boundary`, then `--mode verify-termination`, and
only after both pass `--mode accept`. These permit authentication/catalog checks,
never inference. Attempts are exclusive and consumed; existing final attempts
refuse repetition. Preserve failed/unknown attempts and private credential
evidence. Do not rerun registration or overwrite the Vibe store.

### Trusted OAuth transport (dispatch disabled)

The supported public-route rehearsal has a separate committed-source seal.
Run `harden-batch3.ps1 -Phase seal-supported` as the workspace owner, then use
that snapshot's `code/supported_gateway.py --seal-sha256 <manifest hash>`.
Load the sealed code directory explicitly with isolated Python, as in the
readiness command below. It accepts no endpoint, model, credential or registry
override. Its fixed registry is `.batch3-vibe/supported-readiness/attempts`;
production reservations and dispatch remain disabled. The bundled TLS fixture
is synthetic test material, never a production trust store. Repeating an
attempt or the whole seal review is refused; preserve failed receipts.

`trusted_oauth_transport.py` reuses the pinned provider request/stream guards
with account-bound headers, fixed gpt-6.1-sol/medium and validated proposal/usage.
The internal core is tested with fake HTTP. Its public dispatch refuses before
reading credentials or making requests; production containment, source sealing
and backend USD0 billing enforcement remain pending.

The owner can inspect local account consistency without a model request:

```powershell
python -E -S -B ops/trading/trusted_oauth_transport.py --check-binding --output .batch3-vibe/profile/.vibe-trading/auth/binding-UNIQUE.json
```

This reads only the fixed private Vibe store, checks the stored account against
the unverified JWT claim and records a fingerprint plus freshness. It does not
verify JWT signature, server authentication, subscription or billing. No token
refresh, CLI-store import, raw account ID or token output. Keep the receipt private.

The current transport code and recorded synthetic inputs are separately sealed
at `.batch3-vibe/sealed-trusted-transport-20261002` (62 verified files).
Sealed-core tests and Docker read-only/no-network/timeout cleanup checks passed;
see the [seal checkpoint](../../docs/superpowers/plans/2026-10-02-current-transport-seal.md).
This offline check does not verify a production credential process with network
egress or backend billing, and cannot enable gold dispatch.

### Durable gateway rehearsal

For current committed-code readiness, run as the owning Windows user:
`powershell -NoProfile -ExecutionPolicy Bypass -File ops/trading/harden-batch3.ps1 -Phase seal-readiness`.
This requires clean, committed trading sources, creates a new commit-named seal,
and prepares `.batch3-vibe/production-attempts` with owner/SYSTEM-only access.
It never reads OAuth contents or reserves a production attempt.

Hash the new seal's `manifest.json`, then run its `code/trusted_gateway.py`
with `--readiness --seal-sha256 <manifest hash>`. For isolated host Python,
explicitly load the sealed code directory (PowerShell, with `$sealed` set to
the new snapshot's absolute path):

```powershell
$hash = (Get-FileHash (Join-Path $sealed 'manifest.json') -Algorithm SHA256).Hash.ToLowerInvariant()
python -I -S -B -c "import runpy,sys; p=sys.argv.pop(1); sys.path.insert(0,p); runpy.run_path(p+'/trusted_gateway.py',run_name='__main__')" (Join-Path $sealed 'code') --readiness --seal-sha256 $hash
```

The fixed fake registry is
`.batch3-vibe/gateway-readiness/attempts`; no registry/case/deadline override
is accepted in readiness mode. It exercises success, 401, account mismatch,
bad usage and timeout, checks cleanup/replay refusal, and saves an exclusive
private receipt. Repeating the same seal is refused; preserve failed attempts.
Failed readiness checks return a nonzero exit status even when a receipt is saved.
Readiness receipts always say model_requests=0, dispatch/promotion blocked,
and production isolation, server account acceptance and billing unverified.
The existing pinned Docker image must already be present; nothing is pulled.

The current synthetic-only controller is sealed at
`.batch3-vibe/sealed-gateway-20261002-r2/code/trusted_gateway.py`.
It reserves a manifest identity before starting work, inspects the container before
sending stdin, and preserves failed attempts. The worker creates fake credentials
internally; the controller has no live OAuth entry. Its parent deadline and explicit
PID1 watchdog both have offline checks. Cleanup has a separate maximum 30s budget.

Five Docker cases and same-registry replay refusal passed. See the
[gateway checkpoint](../../docs/superpowers/plans/2026-10-02-trusted-gateway.md).
Separate test registries allow independent fixtures only; they are not permission
to retry a real proposal. Live dispatch remains blocked by production credential
containment, permitted egress and backend billing enforcement.

## Batch 2 evidence checkpoint — 2026-09-30

The owner reports the pending-entry update deployed and an existing gold pending
order. The preparation notes below are historical. Batch 2 qualification is the
next milestone; current public fees and terminal swaps do not qualify historical
cost coverage. Use the [read-only evidence runbook](../../docs/superpowers/plans/2026-09-30-gold-batch2-evidence.md)
for broker counts, current contract values and clock samples. The standalone
probe requires no desktop restart and cannot send, modify or cancel orders.

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
and advancing tick freshness passed the 2026-09-28 Batch 1 session; see
[HANDOFF.md](HANDOFF.md). Later sessions still require fresh preflight checks.
On 2026-09-29 the owner authorized one supervised minimum-lot demo buy. It
opened at 09:11:16 UTC, closed at 09:12:17 UTC, and reconciled to -$0.24 net.
The first close reconciliation missed broker deals because MT5 reports their
timestamps three hours ahead of UTC. Commit `5225fce` fixes the history window
and UTC close timestamp; the VPS source, running container and rebuilt image
matched SHA-256 `ac4f67888ac4a3e327948719869c47ae01fd16e3286572179c17bb5fee58217b`.
The patched desktop was recreated after closure. The original journal row
remains closed; the supervised web control below can append a new attempt only
after fresh checks and an explicit Start click. Keep Algo Trading off between
supervised attempts. This smoke test proves execution mechanics only; Batch 2
strategy qualification remains blocked.

## Supervised web control (deployed 2026-09-29)

### Pending-entry update (prepared locally; deploy after review)

The next version removes the 60-second forced close. The owner enters a buy or
sell **Entry price**, **Stop loss**, and **Take profit** on `/vault/trading` and
previews the exact 0.01-lot request. An entry below the current ask for a buy
or above the current bid for a sell is a limit order; the other direction is a
stop order. The preview does not place an order. Start sends one broker-held
GTC pending order after a fresh demo, quote, contract, occupancy and risk
check. An unfilled order remains pending until the owner cancels it in MT5.
After a fill, the position remains open until broker SL or TP. The page shows
the pending/open state and reviewed levels. Broker-side stops can slip or gap.
The runner never promotes the strategy or submits another entry on its own.

Before updating the VPS, verify no gold position or pending order remains,
back up the SQLite journal, and keep Algo Trading off. Deploy the matching
desktop image, status sidecar, standalone `trading.html`, and Worker together;
the old 60-second page and new request format cannot be mixed. Confirm the
historical closed row survives restart. Do a no-order preview and inspect its
exact levels and modeled stop loss. Only then enable Algo Trading and click
the one-order Start button. If a pending order is unwanted, cancel it in MT5
and wait for the page to show DISARMED. If the status becomes NEEDS ATTENTION,
inspect the broker order/position and journal; do not click Start again.

The private CLI equivalent uses all three prices:

```sh
docker exec -it kwg-mt5-desktop wine /opt/python/python.exe /opt/trading/demo_one_shot.py preview --side buy --entry ENTRY_PRICE --sl STOP_PRICE --tp TARGET_PRICE --state 'C:\users\mt5\gold-one-shot.sqlite3'
```

Replace the placeholder prices with current reviewed prices. The CLI arm command
requires the same `--entry`, `--sl`, and `--tp` values plus
`--enable-demo-execution`; use the web preview and Start flow for the owner
instead of arming from a second shell.

The new Vault page shows the latest attempt, the live price-feed state and a
link to the SSH-protected MT5 desktop at
`http://127.0.0.1:6081/vnc.html?autoconnect=1&resize=scale`.
Its **Preview demo trade** button runs the existing no-order preflight with
Algo Trading off. A 10-minute, single-use confirmation token then permits
one explicit **Start one demo BUY/SELL** click. The runner rebuilds the request,
checks the broker again and writes a new attempt row to the private journal;
older rows, including the 2026-09-29 -$0.24 result, remain unchanged. An
unresolved attempt, occupied gold symbol, stale feed or failed broker guard
blocks another entry. The runner supervises the attempt independently of the
browser; its broker-held stop/target and resume-only recovery still apply.

This code does not enable continuous strategy trading or AI promotion. The
controller, private network, shared secret, status sidecar, page and Worker
were deployed on 2026-09-29. The original -$0.24 attempt remained closed
after the desktop restart. An authenticated page preview succeeded with
`order_sent: false`; a fresh unauthenticated GET and POST both redirected to
Cloudflare Access. No new demo trade was placed, and Algo Trading remained off.
The control endpoint must be reachable only on a private Compose network
shared by `desktop` and `status`; retain `desktop` on its existing Compose
default network for broker connectivity. Its `gw_priority: 1` keeps that
network as the default route, so the VPS needs Docker Compose 2.33.1 or later
and Docker Engine 28 or later. Check both versions before rebuilding.
Publish no control host port. A
32-character-or-longer `TRADING_CONTROL_SECRET` must be stored privately in
the VPS Compose `.env` and as a Worker secret with the same value. Never put it
in Git, browser code, commands shown in chat, or logs. Keep Cloudflare Access
restricted to the owner and the status origin restricted to the existing
service token. A POST from another browser origin is rejected.

Before replacing the desktop image, back up the SQLite journal with SQLite's
backup API and verify the backup. Keep Algo Trading off. Build the image,
regenerate `trading.html` from Astro, then deploy the desktop and status
sidecar. Confirm the old closed result survives restart, the observer is
fresh, no gold position/order exists, and unauthenticated page/API requests
remain behind Access. Deploy the Worker last. A page preview is read-only;
the user must inspect its new prices, enable Algo Trading in the private MT5
desktop and click Start to authorize a new attempt. Watch MT5 until it is
closed or needs attention, then turn Algo Trading off. Do not repeat Start
after an uncertain response; inspect the journal and broker state first.

## Vault status and Access boundary

The observer now publishes a small JSON snapshot to a **separate** Docker
volume. `kwg-trading-status` serves that snapshot and legacy standalone page
copies on `dokploy-network` with no host port; it cannot read MT5's home volume.
Cloudflare routes `/vault/trading*` and `/api/trading/*` to the same Worker,
without moving the rest of the portfolio from its current origin. The Worker requires
Cloudflare Access identity, checks the exact approved viewer email, and fetches
the status origin through the existing Cloudflare Tunnel. Approved page GETs
are forwarded to the existing portfolio origin instead: the normal Dokploy
Astro build owns both trading pages and their assets. Every portfolio redeploy
therefore updates the trading UI without SCP or status-service restarts.
The Worker remains deployed separately when its routing/API code changes.
The status payload
exposes no broker login, balance, password or order request. The prepared
control POST path additionally requires the private shared secret. A missing heartbeat becomes
`offline`; a stale gold quote remains `blocked`.

On the VPS only, set `MT5_DEMO_LOGIN` in this Compose project's private `.env`.
For the verified three-hour lead on this demo, also set
`MT5_SERVER_OFFSET_SECONDS=10800`; the default is zero and fails closed when
the broker clock is ahead. Then deploy the observer and private status service:

```sh
docker compose --profile status up -d --build
```

Keep `.env` outside Git. The desktop process starts the signal-only observer
when the login is set; that observer never calls an order API. The separate
resume-only hook may close an already submitted one-shot position. Confirm the
private service is reachable from `dokploy-network` and has **no host port** before adding its
Cloudflare Tunnel public hostname. In Cloudflare Zero Trust, protect that
hostname with an Access **Service Auth** policy for a dedicated service token.
The Worker receives the token as `STATUS_ACCESS_CLIENT_ID` and
`STATUS_ACCESS_CLIENT_SECRET` secrets; set `STATUS_ORIGIN_URL` to the protected
`https://.../status` origin and `ALLOWED_VIEWER_EMAIL` to the exact owner email
as secrets too. Protect the Worker itself with Access for that email across all
routes, leave `workers.dev` disabled, then deploy from `ops/trading/worker` with
Wrangler. No secret values belong in source, commands, logs, or chat.

After changing `src/pages/vault/trading.astro` or `trading-bot.astro`, commit and
push the source, then redeploy the portfolio in Dokploy. Its existing Dockerfile
builds both pages. No VPS file copy or Worker redeploy is needed for UI-only
changes after activating the origin-forwarding Worker.

For the legacy sidecar copies only, build Astro and regenerate the self-contained pages:

```sh
npm run build
node ops/trading/build-status-page.mjs
```

Commit `ops/trading/trading.html` and `trading-bot.html` with source changes.

Both trading pages share navigation with a current-page indicator and a
keyboard skip link. **Overview** (`/vault/trading-bot`) contains the feed and
practice comparison. **Supervised demo** (`/vault/trading`) shows feed health
before the existing manual order preview. Leaving Overview clears its
in-memory practice review.

Gold operations now includes a local offline experiment review. Open
`/vault/trading-bot`, choose **Choose three reports**, and select
`comparison.json`, `baseline.json` and `candidate.json` together from one
synthetic `rehearse-batch3.py` output directory. The existing private example is
`.superpowers/sdd/batch3-development-handoff-20261002-01/`. Files are read only
in the browser tab; they are not uploaded or persisted. The review checks
baseline/candidate byte hashes, fixed risk/policy and summary differences,
then shows six scenario/window rows and blocked promotion. Other identities
remain declarations, not verified provenance. Unsupported, mismatched or
oversized reports are rejected and remove previous results. **Clear review**
or reload removes the local review. This accepts only the current synthetic
format, never qualification or a real model/order request.

Runnable check: `node src/scripts/trading-review.test.mjs`.

The interface calls this **Practice comparison** and labels the results
fictional. **Original** means baseline; **Proposed** means candidate. The
result explanation describes a validation shortfall without implying account
losses. Development, cost scenarios, risk and qualification details remain
available through disclosures. On localhost/127.0.0.1/IPv6 loopback, the page
does not poll the absent Worker API or offer local status sign-in. It shows
**Not connected here** and links to the protected hosted MT5 dashboard.
This is an honest local preview state, not a newly implemented live proxy.
Hosted pages continue to use the same protected status API. Only an access
redirect or 401/403 offers sign-in; a generic API failure does not presume
authentication is the cause.

For a separately authorized legacy sidecar deployment, copy both pages, `status_server.py`
and the updated read-only HTML mount in `compose.yml` to the VPS Compose
directory, then restart only the status
sidecar. Deploy the Worker routes with Wrangler afterward. The page and API
both require the one-email Worker Access policy; the origin accepts only its
dedicated service token.

One-time activation of automatic UI deployment: push the origin-forwarding
Worker, redeploy the portfolio on that commit in Dokploy, then run
`npx wrangler deploy` from `ops/trading/worker` using the existing account.
Verify both protected pages show the current navigation and that the status
API remains protected and returns sanitized observer data. Existing Access
policies, Worker secrets, MT5 and collectors need no changes. To roll back,
redeploy the previous Worker version; it reads the preserved sidecar copies.

`/vault/trading-bot` is the read-only gold operations workspace. It reuses
`/api/trading/status` and shows one-shot results separately from the unavailable
autonomous runner. Research and qualification sections are dated preparation
notes, not live evidence. The exact Access-viewer check covers both page routes;
unknown subpaths and dashboard POSTs are rejected. The existing Worker route
pattern already covers the new URL. This source change does not deploy it,
connect Vibe/Codex inference or enable orders. Verify the dashboard's protected
route end-to-end before exposing a new deployment; Vault obscurity is not auth.

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

## Initial one-shot demo dry-run and recovery

The one-shot runner is separate from `observe-gold.py`. Initially, its only
entry path was the private Wine CLI `arm` command. The deployed web control
adds an owner-only preview and explicit Start path. Its persistent journal in
the MT5 home allows a new attempt only after the previous one is resolved.
Boot invokes `resume`, which can reconcile an existing submitted
attempt but cannot send a new entry. `execution.json` on the status volume
contains display fields only; tickets, account details, request bodies and
deal history stay private.

Before deploying the new image, verify the source hashes on the VPS and in the
image, take a consistent SQLite backup of `gold-observer.sqlite3`, and retain
the running container until the replacement is verified. Build without arming,
confirm `resume` with no journal sends no orders, then recheck the pinned demo,
Algo Trading off, MT5 SDK/build, synchronized UTC against Market Watch, fresh
gold quote and 250 completed M15 bars. Reconfirm the server offset after a DST
change. Inspect current symbol trading, minimum lot, stop/freeze and filling
rules, and confirm there is no gold position or active gold order. Keep the
desktop bound to SSH loopback and the page behind Cloudflare Access.

Run a private **no-order preview** only after those checks, with Algo Trading
off. Replace `buy` with `sell` only if that is the owner's chosen side:

```sh
docker exec -it kwg-mt5-desktop wine /opt/python/python.exe /opt/trading/demo_one_shot.py preview --side buy --entry ENTRY_PRICE --sl STOP_PRICE --tp TARGET_PRICE --state 'C:\users\mt5\gold-one-shot.sqlite3'
```

The preview prints the current minimum lot, pending order type, reviewed broker
SL/TP, modeled stop exposure and timestamp. It does not
create a journal, call `order_check` or call `order_send`. Store its full JSON
privately in the persistent MT5 home or another private VPS directory, record
its SHA-256 hash, and review it promptly: its quote and contract checks are
time-limited. `arm` rebuilds and rechecks the request; the preview never grants
permission to submit it. Unknown fees, gaps and slippage are outside the
modeled stop exposure.

Only after the owner reviews that concrete preview should the operator enable
Algo Trading on the private desktop and run a single `arm` with the explicit
flag, using the reviewed side:

```sh
docker exec -it kwg-mt5-desktop wine /opt/python/python.exe /opt/trading/demo_one_shot.py arm --side buy --entry ENTRY_PRICE --sl STOP_PRICE --tp TARGET_PRICE --state 'C:\users\mt5\gold-one-shot.sqlite3' --enable-demo-execution
```

The operator watches the journal, broker position and orders until the
pending order is canceled, the protected position closes, or a `needs_attention`
state is resolved. Do not
repeat `arm`, create another journal, or treat a missing reply as a failed
order. If reconciliation is uncertain, preserve the journal and broker-held
protection for ticket-specific recovery. After confirmed closure, ensure no
gold position/order remains, turn Algo Trading off, and verify the observer's
read-only guard again. The smoke result does not qualify the strategy or
enable continuous entry.

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
reports private. `evaluation-policy.json` is **approved for prospective
evaluation** after owner review on 2026-09-29. Historical costs, sufficient
validation observations and real evaluator inputs remain unavailable. No
candidate or order path is installed.
For an approved policy, both evaluator input reports must carry the SHA-256
of its canonical JSON (`sort_keys=True`, compact separators, finite numbers)
in `identity.policy_sha256`; changing a threshold invalidates the comparison.
Simulation reports now include `entry_risk_usd` and `net_r` per trade,
`notional_turnover_usd`, and close-sampled `raw_epoch_daily_returns`. The
last field uses raw broker epochs, **not verified UTC dates**, so it must not
be copied into the evaluator's `daily_returns`. The frozen provisional
manifest rejects `--cost-profile` and cannot supply the required three
prospective folds. A new covered dataset and manifest are needed before
building real gate inputs.
Until that adapter verifies raw simulator hashes, UTC dates, dated costs and
folds, the `evaluate-gold.py` CLI caps any otherwise eligible result at
`inconclusive` with `simulator_provenance_unverified`. Pure gate fixtures are
software checks, not candidate qualification.
For prospective windows, `folds` may contain exactly three ordered
`{start,end}` timestamp pairs partitioning validation. Each fold runs from
flat initial capital and cannot include the reserved holdout. The current
frozen manifest has no such folds; adding them to it would invalidate its
identity and would not create missing observed days.

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

### Desktop-close reconciliation rollout

The continuation supports an MT5 desktop close (`manual desktop`) only after
this journal observed the protected position and matching unique broker deals
prove the full recorded volume closed. Mobile/web/mixed closes, incomplete
history and fast unobserved manual exits remain `needs_attention`. Net result
includes matching entry and exit profit, commission, swap and fee; later separate
broker adjustments are outside this result. No new order is needed to verify it.

Before separately authorized deployment:

1. Confirm current pinned demo identity and no unresolved gold position/order.
   Do not restart the desktop while exposure is unresolved.
2. Back up the journal using SQLite's backup API, check `PRAGMA integrity_check`,
   preserve private permissions and verify source/backup hashes. File copying a
   live SQLite database is not the backup procedure.
3. Review the runner and generated page diff and source hashes. Update the image
   build source as well as runtime files; runtime-only copying is not durable.
4. Coordinate the existing controller journal lock before any bounded read-only
   `resume`. Do not start another long-lived resume while the control loop owns
   the lock. Do not reset the journal or arm another attempt to test this change.
5. Verify the existing attempt's private snapshot and authenticated page agree:
   Closed, UTC close time, net result and desktop-close guidance. Software tests
   alone do not establish a live broker reconciliation.

### Dated private Batch 2 captures

After the updated probe is deployed, use a new output filename each time. Expand
`MT5_DEMO_LOGIN` inside the container, not the host shell. Keep Algo Trading off.
The Windows home evidence directory must already exist with private permissions.

```sh
docker exec kwg-mt5-desktop bash -lc 'wine /opt/python/python.exe /opt/trading/batch2-evidence.py --login "$MT5_DEMO_LOGIN" --server-offset-seconds 10800 --output "C:\users\mt5\contract-UNIQUE-UTC-TIMESTAMP.json"'
```

Replace `UNIQUE-UTC-TIMESTAMP` before running. Output is exclusive canonical
UTF-8 JSON, sorted keys, no NaN, ending in a newline. Stdout prints only mode,
unqualified cost/time status and the saved SHA-256; without `--output`, existing
full JSON stdout remains available. Compare that hash with the actual saved bytes:

```sh
docker exec kwg-mt5-desktop sha256sum /home/mt5/.wine/drive_c/users/mt5/contract-UNIQUE-UTC-TIMESTAMP.json
umask 077
mkdir -p /root/kwg-gold-research/evidence
chmod 700 /root/kwg-gold-research/evidence
docker cp kwg-mt5-desktop:/home/mt5/.wine/drive_c/users/mt5/contract-UNIQUE-UTC-TIMESTAMP.json /root/kwg-gold-research/evidence/
chmod 600 /root/kwg-gold-research/evidence/contract-UNIQUE-UTC-TIMESTAMP.json
sha256sum /root/kwg-gold-research/evidence/contract-UNIQUE-UTC-TIMESTAMP.json
```

Never overwrite a capture. An I/O error can leave an incomplete file: preserve
it as failed, do not count it as verified evidence, and retry with a new filename.
The CLI sets umask 077; native Windows still requires private directory ACLs.
Keep captures and account-specific evidence outside Git.

### Prospective qualification protocol — external evidence pending

#### Prepared diagnostic follower — not deployed

`capture-observer.py` follows only `docker logs` from the fixed desktop container.
It never attaches to MT5 or writes the observer journal. It retains selected
numeric health fields, categorical states and received timestamps; arbitrary
fields and free text are replaced by hashes. Wrapped JSON uses the existing
log parser. Rejected frames and incomplete tails retain counts/hashes. Receipt
includes code and output hashes, gaps, stop reason and zero qualification credit.
This is selected-field evidence, not a claim that complete raw logs were saved.

The Linux live mode has a 1–86400-second limit, 1 MiB frame limit and 64 MiB
diagnostic-file limit per invocation. Each accepted event is flushed/fsynced.
It creates a new 0700 directory and 0600 files under umask 077. Existing paths
are refused. Disconnect, interrupted input, limits and silence require review;
there are no automatic retries. A disk/write failure may leave partial files
without a receipt: preserve them as a failed attempt. Docker client termination
does not stop the container or observer. Fixture mode is local/offline only.

**Future supervised trial, after transfer/source verification:** transfer only
these two reviewed source files from a separate local PowerShell terminal:

```powershell
scp ops/trading/capture-observer.py ops/trading/review_observer_log.py root@187.52.117.116:/root/kwg-gold-research/
Get-FileHash ops/trading/capture-observer.py,ops/trading/review_observer_log.py -Algorithm SHA256
```

The transfer is a separate deployment step and has not been executed. Check
destination files first; do not overwrite any pre-existing version. Compare
local hashes to `sha256sum` on the VPS. Confirm current reviewed desktop launcher
identity and that its observer still emits signal-only JSON on stdout before
using this follower. Do not print full container environment or raw mixed logs.
Then a **new 60-second diagnostic trial**, distinct from the original smoke,
can be run in the SSH terminal:

```sh
sha256sum /root/kwg-gold-research/capture-observer.py /root/kwg-gold-research/review_observer_log.py
umask 077
python3 -B /root/kwg-gold-research/capture-observer.py --seconds 60 --output /root/kwg-gold-research/evidence/diagnostic-trial-UNIQUE-UTC
```

Replace UNIQUE-UTC with a fresh run ID. `timeout` is the expected bounded stop,
not a qualification pass. Review receipt, last received sample, rejected frames,
tail count/hash and gaps. A nonzero sample count proves only that selected
observer output arrived during that trial. Start/end live account/Algo-off/
exposure checks remain separate. Zero samples, nonmonotonic times, unexplained
silence or a failed receipt keep readiness blocked. Full prospective retention
still requires a reviewed schedule, handoff between captures, independent
writer-liveness/gap checks, disk monitoring and preserved journals/exports.
No follower or recurring service has been installed or started by this work.

For a single owner-authenticated transfer-and-trial invocation, use local
PowerShell from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ops/trading/run-diagnostic-trial.ps1
```

ExecutionPolicy applies only to this new process; persistent policy is not
changed. Enter your SSH key passphrase locally if prompted. This launcher checks
the deployed desktop source hash, transfers reviewed files into an exclusive
UTC/UUID run directory, runs 60 seconds, then verifies receipt bytes and container
state. It prints only selected counts/status/hashes. A failed launch preserves
partial evidence and never retries or restarts MT5. `-DryRun` compiles the
generated remote script locally and performs no SSH connection.

Read the saved 60-second trial without starting a new capture:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ops/trading/run-diagnostic-trial.ps1 -ReviewOnly
```

This review mode is pinned to diagnostic-trial-20261002T083518Z-840efc3b and its
known diagnostic byte hash. It checks source identities, receipt counts and
unqualified/zero-day/blocked-promotion metadata before printing selected timing,
state and permission results. Sustained retention and the proposed observation
schedule remain a [draft](../../docs/superpowers/specs/2026-10-02-sustained-observation.md).

For the next bounded 110-second overlapping-follower handoff trial:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ops/trading/run-diagnostic-trial.ps1 -RetentionTrial
```

This transfers the three reviewed stdlib source files into a fresh private
UTC/UUID directory, checks desktop/source identity, runs 60-second segments with
a 10-second overlap and a 1 GiB disk reserve, then prints blockers, unique sample
count, receipt hash and container-state comparison. It exits 2 on blockers or
changed container state. ReviewOnly and RetentionTrial are mutually exclusive.
This trial installs no service and grants no qualification or observed-day credit.

Read-only verification of both completed October 2 handoff attempts:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ops/trading/run-diagnostic-trial.ps1 -RetentionReview
```

Enter the SSH key passphrase locally. This route reads the two pinned private
directories, verifies their reported supervisor hashes and reviewed source bytes,
reconciles actual segment bytes/overlaps/boundaries, and checks root ownership
and private permissions. It creates no files or processes on the VPS beyond the
read-only Python review. A mismatch exits unsuccessfully; preserve both attempts.
The attempts remain separate, unqualified and earn zero observed-day credit.
ReviewOnly, RetentionReview and RetentionTrial are mutually exclusive.

#### Retention supervisor — local implementation only

`retention_supervisor.py` reuses the fixed diagnostic capture CLI. It starts at
most two overlapping owned follower process groups, checks every ten seconds,
records stale writers/early exits/disk refusal and stops only its own processes.
No retries, service installation, MT5 calls, journal changes or order tools.
Run identity and outputs are exclusive; partial attempts stay intact. Final
review verifies receipts, source/byte identities, sample/receive clocks,
start/end boundaries, real overlap and conflicting source hashes. A gap or
failed receipt remains a blocker. Original samples are never deleted to dedupe.
All results retain unqualified status, zero observed days and blocked promotion.

The CLI bounds a single supervision run to two days and at most four planned
segments, each at most 24 hours/64 MiB diagnostic output. It requires an explicit
disk reserve of at least twice the projected bounded diagnostic budget; include
additional journal/export/storage needs. It does not provide calendar scheduling,
off-host alerts, independent host-recovery proof or handoff between supervisor
runs. Failed I/O can prevent a final receipt: preserve partial evidence.

Future supervised Linux trial, after verifying transferred sources and reviewing
current demo/Algo-off/exposure and disk readiness (not executed here):

```sh
python3 -B retention_supervisor.py --run --seconds 110 --segment-seconds 60 --overlap-seconds 10 --reserve-bytes 1073741824 --output /root/kwg-gold-research/evidence/retention-handoff-UNIQUE-UTC
```

This is a short two-follower handoff trial, not prospective qualification. For
longer bounded segments the proposed defaults are 86400 seconds with a 300-second
overlap; freeze total duration/reserve separately before starting. No sustained
run starts just because its command is documented. Source transfer includes
retention_supervisor.py, capture-observer.py and review_observer_log.py; verify exact versions
in a new private tools directory rather than overwriting deployed source.
Completed capture/receipt preservation and consistent SQLite exports remain
operator tasks. Supervisor summary must report no blockers for software readiness;
it still grants no strategy qualification. The CLI exits 2 on blockers.

Read-only offline segment review, with explicit UTC epoch bounds and unique output:

```sh
python3 -B retention_supervisor.py --review SEGMENT_A SEGMENT_B --start START_UTC_EPOCH --end END_UTC_EPOCH --output REVIEW_UNIQUE.json
```

Fixture review additionally requires `--mode synthetic_fixture`. Local tests
exercise overlap conflicts, clock/receive silence, missing boundaries/receipts,
writer failure, disk refusal and owned-group cleanup without Docker/broker use.

#### Offline report adapter preparation (2026-10-02)

`batch2_adapter.py` reconciles the existing baseline simulator CLI report by
recomputing it, including exact dataset/window/cost file hashes. This prepares
real-format integration; it does not authenticate broker evidence or qualify
Batch 2. It requires explicitly UTC data and a clock evidence object declaring
`timestamp_basis: "utc"`, `status: "unreviewed"`; include mapping/source evidence
in that object for later review. Its byte hash is retained without treating the
declaration as proof. Raw broker epochs must be normalized and independently
reviewed before this interface is used. Daily returns group existing equity
marks by their UTC bar-open date, without another offset adjustment.

Run locally from the repository root, with private existing directories and
unique output names (PowerShell):

```powershell
python -B ops/trading/batch2_adapter.py --draft --output .batch3-vibe/protocol-UNIQUE.json
python -B ops/trading/batch2_adapter.py --dataset .batch3-vibe/dataset.json --windows .batch3-vibe/windows.json --costs .batch3-vibe/costs.json --report .batch3-vibe/baseline.json --clock .batch3-vibe/clock.json --protocol .batch3-vibe/protocol-UNIQUE.json --output .batch3-vibe/adapted-UNIQUE.json
```

The baseline report must come from `simulate-gold.py` using explicit `--windows`
and `--cost-profile`, without a candidate. Costs must structurally cover those
windows; fictional profiles are only suitable for labelled offline rehearsals.
All output creation is exclusive. The protocol must match current fixed source,
risk and policy identities. This adapter accepts only `prepared_not_started`
drafts and always emits unqualified evidence, zero verified observed days and
blocked dispatch/promotion. It creates no Batch 3 dispatch packet.

Before starting a separate prospective collection, review and record:

1. A future UTC completed-bar start after manifest creation, an ordered future
   development/validation schedule and three flat folds, plus a reserved
   untouched holdout. Pre-register window selection rules before inspecting
   results; do not choose successful days after collection.
2. Dated exact-account commission, swap-rate and holiday rollover coverage,
   settlement timezone, broker-to-UTC mapping and exact-symbol sessions.
   Missing evidence remains a named blocker, including for demo accounts.
3. Full diagnostics and data retention for the entire interval, saved byte
   hashes, gaps and closure/reopening checks; existing artifacts stay intact.
4. Independent provenance review and the unchanged 60-day/three-fold/100-trade
   gates below. Confirm coverage after collection before assigning observed
   days. Calendar marks alone earn no qualification credit.

The prepared draft starts no collector. A collecting manifest requires separate
review and is not accepted by this preparation adapter. Unknown OAuth monetary
cost still blocks gold model dispatch; human promotion approval remains required.

Record exact `XAUUSD-VIP` sessions from MT5 Specification with dated source
references. Capture before documented closure and after documented reopening,
then run `verify-demo.py` with Algo off. Require connected pinned demo, a fresh
quote and the expected completed M15 bar. Preserve failed checks as blockers;
do not restart or trade to force a pass. Public generic gold hours support a
hypothesis, not exact-symbol session proof. Current UTC offset checks are not
historical DST coverage or evidence of a funding settlement.

Before collecting future validation, create an owner-private
`prospective-collection-manifest.json` containing:

- schema_version 1, status `collecting_unqualified`, creation UTC and a future
  completed-bar collection start; creation must precede that start.
- Exact symbol/timeframe and fixed baseline, source-code and approved policy hashes.
- Private dated session/cost/clock source references with hashes; missing fields
  stay null or absent and are named in `blockers`.
- Observed offset and cost coverage intervals supported by those sources.
- A separate future reserved holdout, uninspected for strategy outcomes; warmup
  bars and old inspected snapshots labelled diagnostic rather than validation.
- Covered dates, missing observations and explicit blockers. Two boundary
  observations do not prove uninterrupted data or cost coverage between them.

Verify referenced hashes against actual bytes. Validate commission, swap rates,
account applicability and rollover timezone/events over each exact window with
`gold_costs.validate_profile`. Current public terms and current contract snapshots
must not be stretched into `verified_historical` coverage.

The original gates remain: 60 observed validation days across three flat folds
of at least 20 days, and at least 100 closed trades per strategy, plus unchanged
risk, stress and bootstrap thresholds. Freeze folds only when covered observations
exist. Minimum-evidence failures are inconclusive, not permission to relax policy.

Retain `prepared_but_blocked` and `simulator_provenance_unverified`. When qualified
real inputs exist, specify and test a separate simulator-to-gate adapter against
actual report schemas and hash identities. Only then run the immutable baseline
twice to distinct exclusive outputs and compare bytes. No fabricated candidate,
Batch 3 research call or continuous trading is part of this collection protocol.
