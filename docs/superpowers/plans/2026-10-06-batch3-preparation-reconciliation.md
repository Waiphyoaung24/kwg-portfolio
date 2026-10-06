# Batch 3 preparation reconciliation — 2026-10-06

**Milestone:** specification and implementation plan reconciled with newer
records; 39 baseline checks and 14 fake diagnostic tests pass. **Batch 2: closed for development,
unqualified. Batch 3: no accepted proposal; further dispatch blocked.
Promotion: blocked.**

This reconciliation includes a pinned, unapplied fake-only diagnostic patch
and offline checker in the user-approved separate
worktree `C:\Users\wai19\.codex\worktrees\gold-batch3-reconcile\kwg-portfolio`,
branch `codex/batch3-preparation-reconcile`, based on local main
`1881e77656c3e26c7ec2bd248e309ec7698e20dd`. Main was not advanced.
The original Desktop checkout at `18620b96eb05eeef86dcea52acf3e00cb1c09e6c`
on `codex/batch3-supported-gateway` remains the source of newer records.
Neither its commits nor uncommitted work were imported as executable runtime
code. The [diagnostic review](2026-10-06-batch3-diagnostic-review.md) documents
the patch artifact, exact hook failure and request/approval consistency check.

## Reconciled decisions

| Earlier wording | Current interpretation |
| --- | --- |
| Batch 2 prepared_but_blocked, development pending | October 2 owner close-out accepted development, while qualification remains deferred |
| Parser/controller/adapter still to build | Main already contains offline helpers and the preparation adapter; reuse them |
| Smoke collector still in its scheduled interval | October 2 review records completed capture, preserved artifacts and a partial pipeline result; no qualifying-day credit |
| Learning-app OAuth is the gold route | Later branch uses separate gold registration and supported Responses transport; MCP remains observation-only |
| 2,048 provider output-token cap | October 3 owner decision replaced it with local byte/time bounds; USD0 additional-spend ceiling remains |
| Account/provider/CLI gates unverified forever | Newer records report historical passes; those expiring proofs are not current dispatch authorization |
| One proposal is ready to start | It was consumed; request outcome unknown, cleanup verified, no proposal/usage artifacts; never rerun |
| stream=false/store=false | Actual recorded request is stream=true/store=false; preserve original approval and its documented correction |

Keep the unchanged EMA20/EMA50/ATR14 baseline, 0.1% equity risk, 2 ATR stop,
3 ATR target, 1% daily entry pause and one-position/no-same-bar-reversal rules.
The unchanged numeric policy and hash-bound human approval are in the
[specification](../specs/2026-10-01-gold-batch3-vibe-integration.md).

## Provenance and evidence limits

The following public source files were read from the original Desktop checkout.
They are working-copy evidence, not claims that main contains them or that
private receipts were independently revalidated during this reconciliation.

| Source relative to original checkout | SHA-256 at review |
| --- | --- |
| CLAUDE.md | `44259ee5b42ed3c9e3eabb949a4b887e3dacbc40f728016ec43693c202d3c8b7` |
| ops/trading/HANDOFF.md | `5554e42608539b8866f1a846f523fcf015ac8ca288bd11e856a0227ee3c94786` |
| docs/superpowers/plans/2026-10-03-batch3-supported-gateway-plan.md | `3ce6f3940cdaf719215cab759061db8e9f81c9cbbb06513e9aff66c3d5727c93` |
| docs/superpowers/plans/2026-10-06-batch3-one-proposal-outcome.md | `2c7eff3e5fd5b265fa4acb831f7329ad250e280ef5f25f76cf8fc7ff4b6ecea2` |
| docs/superpowers/plans/2026-10-06-batch3-one-proposal-workflow.md | `83acf013301eaf748fcdc09446b7e68c6c5e2932254f2f0cdbe2de6db2ec53ae` |
| docs/superpowers/plans/2026-10-06-batch3-combined-verification-results.md | `e0aa9fd9215a2b2094a35bb3155b16b5bef1a48898038502af0f2621261104be` |

Their newest status takes precedence over embedded historical operator steps.
The recorded controller receipt hash is
`158b155e4b8c70420a84f435002ae0cf1ca7c08f38db8041b50d2baf28cc8896`.
The saved review reports ValueError, unknown request count, cleanup true,
guardian exit0, and absent proposal.json/usage.json. Precise worker/HTTP
failure details were discarded. Do not claim a recovered cause, zero requests,
or failed backend execution from absent outputs. No private tree or inspector
was opened or executed here.

Main's [development handoff](2026-10-02-batch2-batch3-handoff.md),
[wrap-up](2026-09-30-gold-batch2-wrap-up.md) and
[smoke review](2026-10-02-gold-smoke-review.md) support the qualification limits.
The original smoke directory remains
`/root/kwg-gold-research/evidence/smoke-20260930T164651Z`.
This reconciliation did not connect to the VPS or verify its current processes.

## Checks performed in this conversation

| Check | Result / limit |
| --- | --- |
| Gold MCP tool inventory and Worker source | Exactly get_gold_status and get_baseline_summary; no inference/job/order tool |
| Authenticated tool calls, preceding read-only review | Both succeeded. Status snapshot checked_at=1791284077, duplicate/none, connected/fresh, 250 bars; not continuous health or a current exposure check |
| Baseline tool | Frozen unqualified hypothetical result, 30/31/30 validation trades, candidate_compared=false, promotion blocked; hard-coded summary is not newer workflow status |
| Anonymous tools/list, preceding review | HTTP 401 after sandbox's no-response failure; no token supplied |
| Repository configuration | Worker name/path, package pins, HTTPS origin and secret-reference behavior reviewed; no secret/config change or secret-store read |
| Focused tests in new main-based worktree | 39 passed: research parser/packet/attempt, experiment, evaluator, costs and baseline adapter |
| Risk canonical hash | `865e46d493db5939e9e3d98375ce727664d57c03bc42a06e548cace61a8e6ce7` |
| Policy canonical hash | `39eb8759133ac1ca50308e0aa053c761a53b24e94be9ebc3f8c13ff73413873d` |
| MCP Node suite | Not rerun: fresh worktree has no node_modules; no install needed for documentation |
| Newer production gateway | Pinned patch tested in disposable source export: 14 fake tests pass; no native containment test, owner helper or model request |

Focused offline command, from `ops/trading`:

```powershell
python -B -m unittest test_research_gold test_gold_experiment test_evaluate_gold test_gold_costs test_batch2_adapter
```

These are synthetic software checks, not 39 trading observations or a complete
gateway/trading suite. The two successful read-only MCP calls establish the
observation route only; they do not establish inference connectivity.

Context7 was used in the preceding review for
[the MCP tool protocol](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/server/tools.mdx)
and [Vibe-Trading integration documentation](https://github.com/HKUDS/Vibe-Trading/blob/main/README.md).
Current upstream documentation is not proof that an installed historical runtime
supports the same behavior. No suggested wildcard tool access, scheduler,
login, provider configuration or upstream upgrade was applied.

## Remaining gates

1. **Runtime integration:** the fake-only diagnostic patch and exact future
   approval/request tests are prepared against a pinned supported-gateway
   snapshot. Separate integration review remains; no runtime or seal was changed.
2. **Any further development inference:** separately reviewed plan and explicit
   new approval after diagnostics, with fresh same-account/model, applicable
   USD0 billing, credential/egress isolation and cleanup evidence. Historical
   receipts and the consumed attempt cannot be replayed.
3. **Qualification:** applicable dated cost/clock/session coverage, a prospectively
   frozen collection protocol and untouched holdout, sufficient baseline and
   candidate samples, and a reviewed real-provenance adapter/registration path.
   Keep 60 eligible days, three folds of at least 20 days and 100 trades per
   strategy, plus all approved performance/stress/bootstrap gates.
4. **Observation/promotion:** one reproducible qualified comparison and explicit
   hash-bound human approval for no-order observation; execution promotion is a
   separate approval and implementation.

Work we can prepare without those qualification gates is documentation,
credential-free synthetic checks and a reviewed fake-only diagnostic candidate.
A learning result stays unqualified. No collector/service change, scheduler,
trade, journal reset, consumed-attempt retry or new research was performed.
