# Gold trading handoff — 2026-09-28

Resume here from another terminal or machine. This page records the latest
verified state; older plan and result files are historical evidence. Keep the
system read-only, demo-only, gold-only (`XAUUSD-VIP`), and Algo Trading off.

## Verified now

- VPS `187.52.117.116`: `/opt/kwg-mt5-qualification`, container
  `kwg-mt5-desktop`. The observer image was rebuilt with the verified
  `10800`-second MT5 server-clock offset. The running observer file matched
  commit `c3ffb2c` by SHA-256 after rebuild.
- The authenticated gold MCP returned `status=baseline`, `signal=none`, a
  connected demo terminal, and a quote 0.187 seconds old at one check. A later
  Codex tool call returned `status=duplicate` with a fresh quote about 0.23
  seconds old. These are spot checks, not continuous qualification.
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

1. **Batch 1: qualify live data.** Check current MCP status, then capture
   uninterrupted fresh quotes and at least two consecutive advancing M15
   boundaries with the existing bounded verifier and
   `--server-offset-seconds 10800`. Verify restart/recovery separately. A
   fresh spot quote does not pass this gate.
2. **Batch 1: qualify costs.** Reconcile the reported Standard STP account
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

Private datasets and reports remain under `/opt/kwg-gold-research/` on the VPS.
The dashboard is `https://waiphyoaung.com/vault/trading`. Never commit the
VPS `.env`, MCP tokens, broker password, SSH key, or private reports. Local
unrelated changes to `skills-lock.json`, `.agents/skills/`, and
`CLIProxyAPI-Codex-Claude-Guide.md` predate this handoff; leave them alone.
