# Gold trading handoff — 2026-09-28

Resume here from another terminal or machine. This page records the latest
verified state; older plan and result files are historical evidence. Keep the
system read-only, demo-only, gold-only (`XAUUSD-VIP`), and Algo Trading off.

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
- **Costs incomplete; recovery untested.** Current public VT Markets terms
  suggest no separate gold commission for Standard/VIP STP and a Wednesday
  triple swap, but do not cover this account's dated historical rates,
  rollover events or the Standard STP versus `-VIP` mismatch. A consistent
  backup of the six-row observer SQLite journal passed integrity checks.
  No supervised restart was possible through the authenticated Dokploy UI;
  this workspace's SSH key was rejected. The post-collection MCP showed a
  fresh quote and `duplicate`/`none`, which is not restart evidence. Batch 2
  remains `prepared_but_blocked`.
- A local observer fix now preserves the startup baseline after a same-candle
  `duplicate`; its regression test passes. This change is **not deployed** to
  the VPS. Deploy and hash-check the updated `observe-gold.py` before using a
  container restart to qualify recovery.
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
  cannot meet the draft 100-trade gate. No Vibe-Trading proposal, candidate,
  research job, promotion, or order path has been enabled.

## Next tasks, in order

1. **Batch 1: verify restart recovery.** First deploy and hash-check the local
   observer startup fix. From an authorized VPS host session, supervise one
   `docker restart kwg-mt5-desktop` outside any collector run.
   Compare the observer journal with the consistent private pre-restart backup;
   verify prior rows, startup baseline suppression, demo pinning, Algo off and
   a fresh read-only MCP heartbeat. A network-disconnect recovery check is
   separate. Do not infer recovery from a fresh spot quote.
2. **Batch 1: qualify dated costs.** Reconcile the reported Standard STP account
   with the `-VIP` symbol; obtain dated, account-specific commission and swap
   rules, rollover time, and historical coverage. Keep measured spread and
   assumed slippage distinct. Unknown costs remain incomplete.
3. **Batch 2: review the draft pass/fail policy** and rerun the frozen baseline
   only with verified dated costs. Preserve chronological windows and the
   reserved 2,000-bar holdout. If evidence is incomplete, retain
   `prepared_but_blocked` and the hypothetical result.
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
