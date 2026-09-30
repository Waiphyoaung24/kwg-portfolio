# Gold trading handoff — 2026-09-28

## Current checkpoint — Batch 2 evidence, 2026-09-30

### Owner-selected next step — one-day pipeline smoke test

The owner approved a one-day pipeline test while retaining qualification
thresholds. Use the [one-day smoke-test runbook](../../docs/superpowers/plans/2026-09-30-gold-one-day-smoke-test.md).
It reuses the running observer, dated probe and raw exporter with a future
M15 start and private artifacts. All five owner-reported observer/export source
hashes matched published Git bytes. The observer journal retains signals and
health, so raw OHLC exports must also be preserved. Setup is prepared locally;
no VPS smoke-test start is confirmed yet. No new order or scheduler is part
of this test. A pipeline pass does not complete Batch 2 or unlock Batch 3.

### Wrap-up verdict — qualification still blocked

Read the [current wrap-up and exact remaining gates](../../docs/superpowers/plans/2026-09-30-gold-batch2-wrap-up.md)
first. The owner verified exclusive capture bytes and fresh exposure-free state;
the current session specification was preserved privately. The subsequent
saved verifier passed expected completed M15 history and fresh quotes, closing
the bounded recovery check. These do not establish interval qualification or
immediate reopening latency.
Current cost validation still rejects historical commission and swap coverage.
A private prospective draft is prepared but has no start/windows/holdout and
does not represent an active collection run. Batch 3 remains gated.

### Continuation implementation — owner rollout verified, page check pending

The owner approved native execution on main and desktop closes only. Read the
[continuation specification](../../docs/superpowers/specs/2026-09-30-gold-batch2-continuation.md),
[desktop-close plan](../../docs/superpowers/plans/2026-09-30-gold-desktop-close-reconciliation.md)
and [evidence-collection plan](../../docs/superpowers/plans/2026-09-30-gold-batch2-evidence-collection.md).
Local implementation adds strict observed-volume desktop-close reconciliation,
its page guidance and exclusive dated probe output. The owner verified image
source hashes, a consistent journal backup and an exposure-free Algo-off check,
then recreated the desktop and status services. Startup reconciled the existing
attempt as a verified desktop close. The owner subsequently verified exclusive
capture bytes. Authenticated page projection remains pending. No new order was
used for this check.
The VPS Dockerfile and `.dockerignore` both needed the existing repository's
`batch2-evidence.py` inclusion; updating only the runner files was insufficient.
Qualification remains `prepared_but_blocked`; `simulator_provenance_unverified`
remains in place. See the [rollout and prospective protocol](README.md#desktop-close-reconciliation-rollout).

Five planned tasks precede the Batch 3 gate; the first three code tasks are
implemented. Remaining owner evidence is exact-symbol session recovery,
sourced commission/swap/rollover and offset coverage, a future private collection
manifest and sufficient covered observations under the unchanged policy.
No current-rate snapshot qualifies a historical interval. A verified real-report
adapter and repeatable baseline are still required before eligibility. Batch 3
is not unlocked by the implementation tests.

**Resume from the [session sign-off checkpoint](../../docs/superpowers/plans/2026-09-30-gold-batch2-session-checkpoint.md).**
It supersedes the initial probe-preparation status below. Qualification remains
`prepared_but_blocked`; detailed runtime evidence stays private outside Git.
Next work is read-only session recovery, supported desktop-origin close
reconciliation, and dated cost/clock coverage before prospective evaluation.
No new attempt, desktop restart, journal reset or Batch 3 job is authorized by
this handoff. Keep Algo Trading off for observation.

### Initial probe preparation — historical

The owner reports the editable pending-entry version deployed to the VPS and
Worker and a gold pending order currently in MT5. The preparation notes below
are historical. Do not restart the desktop, cancel that order, or resubmit it
as part of qualification. The owner selected Batch 2 qualification next.
The MCP baseline remains unqualified; its historical costs are hypothetical.
The observer currently blocks because Algo Trading is on.

Use the new read-only `batch2-evidence.py` probe to capture current broker counts,
contract costs and clock samples without changing the observer's Algo-off guard.
See the [Batch 2 checkpoint and VPS runbook](../../docs/superpowers/plans/2026-09-30-gold-batch2-evidence.md).
Local validation: 104 Python tests passed. Live probe output, dated cost coverage
and historical timestamp evidence are still pending. This is not a qualification
pass or authorization for another demo order.

## Pending-entry update — prepared, not deployed

The owner requested removing the 60-second timed close and editing Entry,
SL and TP in the Vault page. The chosen Entry creates a broker-held GTC
pending order; the owner cancels an unfilled order manually in MT5. A filled
position stays open until broker SL or TP. The local branch implements this
across the runner, private controller, status sidecar, Worker, and standalone
page. The previous timed-close trades below are historical. Do not use the
new UI with the old runner or the old UI with the new controller. See the
[README deployment note](README.md#pending-entry-update-prepared-locally-deploy-after-review)
before any supervised attempt. No order was placed by this code change.

Resume here from another terminal or machine. This page records the latest
verified state; older plan and result files are historical evidence. Keep the
signal observer read-only, all execution demo-only and gold-only
(`XAUUSD-VIP`), and Algo Trading off between supervised attempts.

## Supervised web control — deployed 2026-09-29

The owner approved a simpler `/vault/trading` flow: view the gold feed and
latest attempt, open the MT5 desktop through the SSH tunnel, preview a
protected minimum-lot buy or sell with **no order**, then explicitly start
one supervised demo attempt. The new code keeps the previous closed row and
appends a new journal row only after the prior attempt is resolved. A
single-use 10-minute preview token, fresh broker preflight, owner-only
Cloudflare Access check, same-origin POST check and a private shared secret
guard the entry path. The status sidecar still cannot read the MT5 home. It
proxies control requests over an internal-only Compose network; the desktop
retains its broker-connected default network and loopback-only noVNC port.

Source is on `codex/gold-demo-one-shot-plan` (`aa6caab`, including the
`.dockerignore` build fix) and deployed to the VPS and existing Worker. The
owner approved the two-network connection; the VPS has Docker Compose 5.5.0
and Engine 28.5.0. The journal was backed up with SQLite's backup API, checked
as intact with one closed row, and copied outside the Docker volume at
`/root/kwg-trading-backups/gold-one-shot-pre-web-control-20260929.sqlite3`
(SHA-256 `e197777ff21279addc07c8d2d911614dd750d6c49fbe0bdf98f55137b1c1abe0`).
The rebuilt desktop image contains the reviewed runner and controller; after
recreation, `resume` republished the same closed -$0.24 result and the verifier
reported `ready` with a fresh quote and Algo Trading off. The sidecar reaches
the controller only on the internal Compose network; the desktop retains the
default broker network and loopback-only noVNC port. The private preview path
returned HTTP 200, 0.01 lot, and `order_sent: false`. The Worker has the
matching secret; the authenticated page showed CLOSED, the MT5 link and a
successful no-order preview. Unauthenticated page GET and preview POST both
redirected to Cloudflare Access. The unused preview was cleared from the page.
No new demo trade was placed. See [README.md](README.md#supervised-web-control-deployed-2026-09-29)
for operation and recovery. Automatic strategy execution, Batch 2
qualification and AI promotion remain separate and inactive.

## Latest one-shot result — 2026-09-29

The owner authorized one supervised minimum-lot demo **buy**. A fresh verifier
reported `ready` with 250 completed M15 bars and a 0.222-second gold quote.
The operator armed once; the broker showed a protected 0.01-lot position.
The timed close left no gold position or order, but the journal initially
reported `needs_attention`: MT5's deal timestamps and history search window
were three hours ahead of UTC. A read-only probe found one entry and one exit
in the UTC+3 window and no gold deals in the UTC window.

Commit `5225fce` applies the verified broker offset to deal-history queries and
normalizes recorded close time to UTC. After a consistent private SQLite backup
and source backup, the patched runner was installed in the VPS source and
running container (SHA-256
`ac4f67888ac4a3e327948719869c47ae01fd16e3286572179c17bb5fee58217b`).
`resume` reconciled the existing attempt to `closed`: buy 0.01 lot, opened
09:11:16 UTC, closed 09:12:17 UTC, `timed`, realized **-$0.24 net**. It sent
no second entry. The post-trade verifier reported `ready` with Algo Trading
off; the authenticated Vault page displayed the same closed result. This is
an execution-mechanics smoke test, not strategy qualification. Batch 2 remains
`prepared_but_blocked`; no continuous trading or model order path is enabled.

The older activation checklist below is historical. Preserve the private
one-shot journal and backups; use only a fresh reviewed web preview for any
new attempt, and do not repeat Start after an uncertain response. The patched Docker
image was built, verified against the same hash and used to recreate only the
desktop after the trade closed. Post-restart checks passed: the boot snapshot
remained `closed`, the verifier returned `ready` with Algo Trading off, and the
authenticated Vault page showed the same 0.01-lot, -$0.24 result.

## Earlier owner direction — 2026-09-29 (historical)

The immediate engineering milestone is one supervised, operator-armed,
minimum-lot demo smoke trade that opens with broker-held protection, closes,
reconciles and disarms. The [selected design](../../docs/superpowers/plans/2026-09-29-gold-agent-design.md)
and [implementation plan](../../docs/superpowers/plans/2026-09-29-gold-one-shot-demo-execution.md)
separate that machinery test from Batch 2/3 strategy qualification and later
continuous demo execution. The runner is installed on the private VPS but is
disarmed; the existing observer stays read-only with Algo Trading off.

## Earlier implementation update — 2026-09-29 (historical)

The one-shot preflight, durable journal/reconciliation, resume-only boot hook,
and sanitized read-only dashboard status are implemented on this branch in
commits `3284c29`, `9ea0ba4`, `566e0af`, `35ff3d5`, and `e3dce03`.
The 90-test Python suite, Worker/browser tests, shell syntax, Astro build,
generated private page and Compose configuration pass locally. Independent
code review found no remaining critical or important issue. `public/ref/`
remains unrelated and untouched. The observer still defaults to its
Algo-Trading-off guard.

**Activation is pending.** The owner authorized this Mac's SSH public key. On
2026-09-28 UTC the private VPS built image
`sha256:13aaeeaa6481d0f59147f1e9aace18d3d0c370ce17f35f9430e4b813f1eb0064`,
and only `kwg-mt5-desktop` was recreated from it. The runner's image and
running-container SHA-256 matched local source
`d250194a96df839f327458c7e0ea7666f968254214485772a7756b436a87a265`.
The prior image remains tagged `kwg-mt5-desktop:before-one-shot-35ff3d5`.
The observer journal was backed up consistently in the VPS private `backups/`
directory as `gold-observer-before-one-shot-20260928-205050.sqlite3`; its
integrity check passed. A private source rollback archive is also retained.

Before restart, the pinned demo was connected, Algo Trading was off, and gold
had zero positions and orders. The first no-order preview exposed a pinned
Python SDK omission of `SYMBOL_FILLING_FOK`/`IOC`; `e3dce03` fixes this using
the documented `1`/`2` symbol filling flags, and the repaired image was built
and hash-verified. The resume-only boot published `disarmed` without creating
a one-shot journal. The observer verifier then blocked because the gold quote
stopped updating around server midnight. The operator reran it at 07:01 UTC
on 2026-09-29: it reported `ready`, a fresh quote, and 250 completed M15 bars.
The subsequent private no-order buy preview produced the minimum-lot request,
proposed stop/target, and modeled stop exposure below the 0.1% equity limit.
Its full JSON was transcribed from the operator's terminal into a private
review packet outside Git; the local transcription hash is not a VPS-origin
hash. The preview is time-limited and requires a new preflight before arm.
The status sidecar and Worker still need the read-only execution-field update.
This Mac's Wrangler OAuth token belongs
to a different Cloudflare account than the existing Worker, so a read-only
deployment lookup returned authentication error 10000; do not change the
Worker's account ID to bypass that mismatch. No `order_check` or `order_send` was run,
Algo Trading was not enabled, and no order was sent. Batch 2 stays
`prepared_but_blocked` and continuous execution stays disabled.

## Earlier one-shot activation checklist (completed)

1. **Review the private preview.** Confirm the chosen side and time-specific
   stop, target, volume, and modeled exposure with the owner. Preserve the
   original VPS output privately if a VPS-origin report hash is required.
   Preview success does not authorize an order.
2. **Deploy the read-only status update.** Copy the generated page and status
   sidecar to the VPS, restart only that service, then deploy the Worker using
   credentials for its existing Cloudflare account. Verify Access, sanitized
   execution fields, and that no arm/order route is exposed.
3. **Only after separate owner authorization, supervise one demo attempt.**
   Recheck demo identity, Algo Trading state, clock offset, fresh quote, valid
   bars, symbol conditions, and empty gold positions/orders. Enable Algo
   Trading only for the supervised `arm`; inspect `order_check`, the single
   entry, broker-held SL/TP, ticket-specific close, and durable reconciliation.
   Freeze and recover through the journal if the result is uncertain.
4. **Return to read-only mode.** Confirm no remaining gold position/order,
   disable Algo Trading, verify the observer guard and status page, and record
   only sanitized evidence in Git. Keep Batch 2/3 qualification and continuous
   execution blocked on their separate gates.

## Handover instruction

The deployment branch is `codex/gold-demo-one-shot-plan` (draft PR #2), built
on `codex/gold-batch2-review` (draft PR #1), not on `main`. In another checkout,
fetch and switch to the deployment branch before continuing.

> Read `AGENTS.md`, `ops/trading/HANDOFF.md`,
> `docs/superpowers/plans/2026-09-29-gold-agent-design.md` and
> `docs/superpowers/plans/2026-09-29-gold-one-shot-demo-execution.md`.
> The one-shot demo smoke trade is closed and the supervised web control is
> deployed. The historical journal row remains intact; no new trade was placed.
> Keep Algo Trading off. For a new attempt, require a fresh no-order preview,
> inspect its price and risk, then explicitly Start once and supervise closure.
> Never repeat Start after an uncertain response. Continue the Batch 2 evidence
> gates (dated broker costs and the remaining strategy validation) before
> Batch 3 research or continuous demo execution. Keep the observer read-only,
> the pinned demo account, and private broker data outside Git and the web API.

Batch 2 remains `prepared_but_blocked`; the one-shot smoke test is an
independent execution-machinery milestone, not strategy qualification.

## Verified now

- **Batch 1 live-data continuity passed on 2026-09-28.** The private bounded
  collector report `C:\users\mt5\gold-qualification-20260928-1633.json` has
  361 accepted samples over 1,800.609 seconds, two consecutive advancing M15
  boundaries, and no blockers. The pinned reducer independently reproduced
  its verdict; SHA-256 is
  `2c3f112e3c566be45a200883b33adcb2807ad2fb177b7767d7a096ce89c27119`.
  Sampled spread p50/p95/max was 0.28/0.32/0.32 price units. The report stays
  private in the persistent MT5 home volume. This passes that session's data
  gate using the explicit 10,800-second offset corroborated by same-day 11:31
  UTC host NTP and approximately 12:26 UTC Market Watch checks. Immediate
  pre-run clock reconfirmation was unavailable, leaving a limited clock-basis
  risk. It does not certify later feed health or historical timestamps.
- **Container-restart recovery passed; costs remain incomplete.** A regression
  fix preserved the startup baseline after a same-candle `duplicate`. The owner
  hash-checked the fixed observer at both VPS source and container paths,
  backed up the live SQLite journal, and restarted only `kwg-mt5-desktop`.
  Integrity passed; all 8 prior rows remained identical and the first new bar
  (1790617500) was `baseline`/`none`. A post-restart one-shot verifier passed
  at 18:02:20 UTC with the pinned demo, Algo Trading off, a 0.222-second fresh
  quote, and 250 valid completed bars. Network-disconnect recovery is untested.
  Current public VT Markets terms suggest no separate gold commission for
  Standard/VIP STP and a Wednesday
  triple swap, but do not cover this account's dated historical rates,
  rollover events or the Standard STP versus `-VIP` mismatch. Batch 2 remains
  `prepared_but_blocked`.
- The observer fix in `5dfb463` is deployed to the running container and VPS
  Compose source (SHA-256 `9523ebb74d3c701fc41428bfcf04548079d7a3c03d13f0e69ddec05766b4a422`).
  The owner rebuilt `kwg-mt5-desktop:qualification` from that source and
  independently verified the same hash inside the new image. The running
  container was not recreated from the image; its verified overlay still has
  the fix. A future recreation can use the rebuilt image.
- VPS `187.52.117.116`: `/opt/kwg-mt5-qualification`, container
  `kwg-mt5-desktop`. The observer image was rebuilt with the verified
  `10800`-second MT5 server-clock offset. The running observer file matched
  commit `c3ffb2c` by SHA-256 after rebuild.
- The authenticated gold MCP returned `status=duplicate`, `signal=none`, a
  connected demo terminal and a 0.150-second quote age after collection.
  MCP calls are health spot checks; the private collector establishes the
  separate continuous-window result above.
- `https://kwg-gold-research-mcp.nexuslab-dev-mm.workers.dev/mcp` exposes only
  `get_gold_status` and `get_baseline_summary`. Both completed in an ephemeral
  Codex read-only check; anonymous access returned HTTP 401. Claude Code and
  Codex are configured locally on the owner's Windows profile. Restart an
  already-running Codex desktop app to load its new MCP entry and token
  environment variable. Secrets stay outside Git and chat.
- The frozen baseline is reproducible but **unqualified**. Validation lost
  money in all three hypothetical cost scenarios; 30–31 validation trades
  cannot meet the approved 100-trade gate. No Vibe-Trading proposal, candidate,
  research job, promotion, or order path has been enabled.
- A 2026-09-29 Batch 2 gate review fixed approved-policy hash binding and
  fail-closed nonfinite/overflow/zero-bootstrap handling; 57 Python tests
  pass. The owner approved exact v1 thresholds on 2026-09-29; the policy is
  approved prospectively. The simulator now reports raw-epoch daily returns,
  trade risk/net R and notional turnover, but raw dates and three prospective
  folds cannot yet be adapted into real gate inputs. The simulator can execute
  three explicitly frozen, flat-reset folds once qualified windows exist.
  The evaluator CLI caps synthetic eligibility at `inconclusive` until raw
  simulator provenance is verified.
  Public broker terms cannot supply dated cost coverage.
  See the [Batch 2 result](../../docs/superpowers/plans/2026-09-28-gold-batch-2-results.md).

## Next tasks, in order

1. **Batch 1: qualify dated costs.** Reconcile the reported Standard STP account
   with the `-VIP` symbol; obtain dated, account-specific commission and swap
   rules, rollover time, and historical coverage. Keep measured spread and
   assumed slippage distinct. Unknown costs remain incomplete.
2. **Operations: extend recovery evidence if needed.** Test an actual network
   disconnection separately if that gate is required; a container restart
   proves a narrower recovery path. After any future image-based recreation,
   recheck the fixed source hash and read-only demo guard.
3. **Batch 2: complete the remaining evidence.** Rerun the original frozen
   baseline as a diagnostic only when dated costs are verified. For candidate
   evaluation, collect adequately covered prospective data, establish UTC
   dates, freeze three flat folds in a new manifest, and verify the
   simulator-to-gate adapter. Preserve the original reserved 2,000-bar
   holdout. While evidence is incomplete, retain `prepared_but_blocked` and
   the hypothetical result.
4. **Batch 3 only after those gates:** verify a bounded model route and run one
   isolated Vibe-Trading research proposal. This read-only MCP is an
   observation tool, not a model API or research-job trigger. Batch 4 is
   parallel no-order observation only if a candidate passes.

## Where the work lives

- [Four-batch roadmap](../../docs/superpowers/plans/2026-09-28-gold-ai-researcher.md)
- [Batch 1 tasks](../../docs/superpowers/plans/2026-09-28-gold-batch-1-implementation.md) and [current result](../../docs/superpowers/plans/2026-09-28-gold-batch-1-results.md)
- [Batch 2 tasks](../../docs/superpowers/plans/2026-09-28-gold-batch-2-implementation.md) and [current result](../../docs/superpowers/plans/2026-09-28-gold-batch-2-results.md)
- [Offline experiment plan](../../docs/superpowers/plans/2026-09-28-gold-offline-first-experiment.md) and [baseline result](../../docs/superpowers/plans/2026-09-28-gold-first-experiment-results.md)
- [MT5 operations](README.md) and [MCP deployment/connection](research-mcp/README.md)

Private datasets remain under `/opt/kwg-gold-research/` on the VPS; the new
qualification report and SQLite backup are in the persistent MT5 home volume.
The dashboard is `https://waiphyoaung.com/vault/trading`. Never commit the
VPS `.env`, MCP tokens, broker password, SSH key, or private reports. Local
unrelated changes to `skills-lock.json`, `.agents/skills/`, and
`CLIProxyAPI-Codex-Claude-Guide.md` predate this handoff; leave them alone.
