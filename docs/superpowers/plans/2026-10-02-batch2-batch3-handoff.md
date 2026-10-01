# Batch 2 to Batch 3 handoff checkpoint — October 2, 2026 Bangkok

**Batch 2: prepared_but_blocked. Batch 3: synthetic integration verified;
real-data integration and research dispatch blocked.**

## Verification completed now

Reused the existing adapter, bounded runner, proposal validator, simulator and
evaluator. No additional service, dependency or broker connector was needed.
All 137 Python tests passed. Fresh offline end-to-end artifacts are private at
`.batch3-vibe/batch2-handoff-rehearsal-20261002-02/`.

The rehearsal used synthetic candles/costs/clock and one fake inference request,
not the broker export or OAuth credentials. The pinned cached Docker image ran
with no network, read-only files and no credentials; isolation probes and
container cleanup passed. Baseline and synthetic comparison reports reproduced
identically. The evaluator returned `inconclusive: evidence_incomplete`.
Model requests were zero, monetary cost unknown and promotion blocked.

The first attempt, `batch2-handoff-rehearsal-20261002-01/`, remains preserved as
failed. The coding sandbox could not access the Docker pipe; owner execution of
the same command at a new exclusive path passed. Its `sandbox_cleanup_failed`
status does not prove a container was created or that cleanup was verified.

The reviewed one-day smoke is separately complete with a partial pipeline
verdict. Its two missing observation candles and limited retained diagnostics
remain limitations. Do not insert retrospective observations or assign
qualification credit to synthetic fixtures or the smoke.

## Finish in this order

### Local cost-boundary correction

Continuation review found that `gold_costs.validate_profile` checked dates and
source hashes but could claim coverage with missing/nonfinite commission,
unsupported currencies or malformed swap events. Seven regression cases first
failed, then passed after sharing swap-event validation with cashflow accounting
and reusing the existing commission validator. Both directional rates must be
finite, including the direction not used by a particular simulated position.

All 138 Python tests passed. Revised-source Docker rehearsal at
`.batch3-vibe/batch2-handoff-rehearsal-20261002-03/` passed, with zero model
requests, repeatable reports and blocked promotion. Earlier attempts remain
unchanged. This checks schema usability, not source authenticity, account
applicability or completeness of the broker rollover calendar.

The local `gold_costs.py` source hash changed. The deployed collector, smoke
source freeze and sealed credential-rehearsal snapshot were not changed. Any
future qualifying protocol must explicitly freeze its reviewed code identities;
do not substitute revised code into an already frozen run or describe the old
sealed snapshot as containing this correction.

| Step | Acceptance evidence | Current gate |
| --- | --- | --- |
| Exact symbol/account applicability | Private dated source showing XAUUSD-VIP, applicable demo account type and sessions; source byte hashes | Prior session crop omitted symbol header; applicability insufficient |
| Cost coverage | Sourced commission basis/currency and long/short swap rates, effective intervals and rollover events; existing cost validator passes every frozen window | Uncovered; current public rates cannot be backdated |
| Clock coverage | Dated broker offset intervals, DST/session interpretation and verified UTC conversion spanning the frozen windows | Current spot checks only |
| Future protocol | Private manifest saved before its future completed-bar start, frozen code/baseline/risk/policy identities, windows and separate untouched holdout | Draft prepared, not started |
| Diagnostic retention | Preserve the existing observer output across the future interval; verify first/last samples and gaps without depending on bounded Docker history | One-day logs retained only their tail |
| Adequate observations | 60 observed validation days, three flat folds >=20 days and 100 closed trades per strategy, with evidence coverage | Not established |
| Real-report provenance | Separately reviewed adapter: raw report identities, UTC daily accounting, exact folds, tamper rejection and reconciliation; fixed baseline repeated to distinct files with identical bytes | Synthetic adapter is not this evidence |
| Batch 3 dispatch | Qualified Batch 2 packet restricted to development data; approved known cost ceiling, pinned model/medium effort and verified production credential/transport boundary | Blocked independently of learning-app OAuth |
| Promotion | Explicit human approval after the unchanged evaluation gates | Always required; never automatic |

No collection start date, rate, source interval or qualification status is
invented. Existing observer and all smoke artifacts remain intact. A future
diagnostic-preservation procedure must be reviewed before operation; this
checkpoint starts no follow process, scheduler or second market-data collector.

## Integration boundary

Batch 2 owns immutable evidence and the fixed baseline. Its qualified adapter
will create the restricted development packet. The separate bounded Batch 3
runner may return one allowlisted parameter/filter proposal; it has no broker
tools or generated-code execution. The existing simulator evaluates it under
the same frozen limits and costs. Comparison and human approval remain outside
the learning application's general Agent workflow.

Normal Vibe-Trading learning demos are usable separately. A successful OAuth
greeting or synthetic CSV analysis does not authorize reading broker data,
running gold research, enabling MT5 or promoting a strategy.

References: [smoke review](2026-10-02-gold-smoke-review.md),
[Batch 2 wrap-up](2026-09-30-gold-batch2-wrap-up.md),
[evidence collection](2026-09-30-gold-batch2-evidence-collection.md),
[Batch 3 specification](../specs/2026-10-01-gold-batch3-vibe-integration.md).
