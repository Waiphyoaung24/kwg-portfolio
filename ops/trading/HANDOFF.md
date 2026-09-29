# Gold trading handoff — 2026-09-28

Resume here from another terminal or machine. This page records the latest
verified state; older plan and result files are historical evidence. Keep the
system read-only, demo-only, gold-only (`XAUUSD-VIP`), and Algo Trading off.

## Updated owner direction — 2026-09-29

The immediate engineering milestone is one supervised, operator-armed,
minimum-lot demo smoke trade that opens with broker-held protection, closes,
reconciles and disarms. The [selected design](../../docs/superpowers/plans/2026-09-29-gold-agent-design.md)
and [implementation plan](../../docs/superpowers/plans/2026-09-29-gold-one-shot-demo-execution.md)
separate that machinery test from Batch 2/3 strategy qualification and later
continuous demo execution. The runner is installed on the private VPS but is
disarmed; the existing observer stays read-only with Algo Trading off.

## Implementation update — 2026-09-29

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

## Remaining one-shot to-do

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

The planning branch is `codex/gold-demo-one-shot-plan`, built on
`codex/gold-batch2-review` (draft PR #1), not on `main`. In another
checkout, fetch and switch to the planning branch before continuing.

> Read `AGENTS.md`, `ops/trading/HANDOFF.md`,
> `docs/superpowers/plans/2026-09-29-gold-agent-design.md` and
> `docs/superpowers/plans/2026-09-29-gold-one-shot-demo-execution.md`.
> Implement the one-shot demo runner with native execution, task by task:
> preflight, durable reconciliation, then read-only dashboard status.
> Keep the existing observer signal-only and the pinned demo/Algo-off guard
> intact. Run the plan's fake-MT5, Python, Worker and site checks. Prepare
> the private dry-run preview for owner review before any order is sent.
> Do not place a trade, enable continuous entry, run Vibe-Trading, change
> risk policy or expose account data during this handoff.

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
