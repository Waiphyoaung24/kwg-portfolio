# Gold Batch 1 Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete or explicitly fail the outstanding live-data, recovery and dated-cost evidence gates, then hand verified evidence to Batch 2.

**Architecture:** Run the existing bounded verifier on the existing VPS; use MCP for status spot checks. Preserve private reports and publish only sanitized results. No new collector, service, dependency or trading capability is required.

**Tech Stack:** Existing Python/unittest, Windows MetaTrader5 under Wine, Docker, SQLite and read-only gold MCP.

**Spec:** `ops/trading/HANDOFF.md`, `2026-09-28-gold-ai-researcher.md`, and `2026-09-28-gold-batch-1-implementation.md`. This completion checklist supersedes their obsolete pending-code/deployment steps, not their evidence requirements.

## Global Constraints

- Keep the system read-only, demo-only, gold-only (`XAUUSD-VIP`), and Algo Trading off.
- Quote age remains between 0 and 30 seconds inclusive. Fetch 250 completed M15 bars from position 1.
- Use `--server-offset-seconds 10800` only after reconfirming the documented session offset against synchronized UTC and Market Watch. Preserve raw timestamps; do not apply this constant to historical data or across DST without evidence.
- No orders, candidate research, policy approval, automatic promotion or recurring monitoring in this plan.
- Keep credentials, account identifiers, terminal state, broker documents and full reports private. Do not print `.env` or full container configuration.
- Preserve unrelated local changes. Planning does not pull, deploy, restart or execute the collector.

## Review and selected approach

The owner selected Batch 1 completion, followed by explicit Batch 2 gates.

| Approach | Benefit | Limitation | Decision |
| --- | --- | --- | --- |
| Manual MCP snapshots | Immediate health check | Cannot prove sampled continuity or contract provenance | Preflight only |
| Existing bounded VPS verifier | Already implements the required evidence checks | Needs authorized VPS access and an uninterrupted run | Selected |
| New persistent monitor | Could accumulate future windows | Adds lifecycle work before an existing collector has qualified | Deferred |

Reviewed checkout: `ad58b58`; 48 local Python tests passed on 2026-09-28.
Current MCP sample at epoch `1790612710`: connected, quote age ~0.152 seconds,
250 bars, `duplicate`, `signal=none`. This is a spot check only. MCP normalizes
tick times; use the private verifier report for raw-versus-adjusted evidence.

The collector and cost adapter already exist. The first-experiment results
record a long collection ending after 57 accepted samples with a disconnected
terminal; its cause is unresolved. Older Batch 1 notes saying the collector
was never run are historical. The handoff records the observer rebuild with
the session offset; do not redeploy merely because older notes say otherwise.

Frozen baseline validation lost under all three hypothetical scenarios with
30–31 trades. It remains unqualified, with no candidate. A live-data pass does
not fix historical costs, the inspected validation set, or insufficient samples.

## File and artifact map

| Path | Action and responsibility |
| --- | --- |
| `ops/trading/verify-demo.py`, `mt5_data.py`, `gold_qualification.py`, `gold_signal.py` | Reuse unchanged; hash against deployed copies |
| `ops/trading/test_verify_demo.py`, `test_gold_qualification.py`, `test_observe_gold.py` | Run existing regression checks; add a regression only if a defect is reproduced |
| `/opt/kwg-gold-research/qualification/<UTC-run-id>/` on VPS | Private collector, cost-source and recovery evidence, plus hashes; directory 700/files 600 |
| `docs/superpowers/plans/2026-09-28-gold-batch-1-results.md` | Append dated outcome; preserve previous failed runs |
| `ops/trading/HANDOFF.md` | Update verified state and unresolved gates after execution |
| `task_plan.md` | Record selected direction and link this plan |

## Review Focus

1. Disconnection or sampling gap must invalidate continuity, never stitch separate runs (Tasks 1–2).
2. Fresh quote with stale/forming/malformed history must not pass (Tasks 1–2).
3. Session clock correction must not become historical timestamp qualification (Tasks 1, 3).
4. Current rates, missing fees or account-tier ambiguity must remain incomplete historical costs (Task 3).
5. Recovery must preserve journal rows and suppress duplicate/startup decisions; it cannot be counted inside uninterrupted collection (Task 4).

## Task 1: Pin the operational state

**Interfaces:** Existing `read_gold(..., server_offset_seconds=10800)` and verifier CLI. Produces a private preflight record and exact source hashes for Task 2.

- [ ] In the execution checkout run `git status --short` and `git log -1 --oneline`. If using the other terminal, preserve its changes before `git pull --ff-only origin main`; stop on divergence rather than reset. Record the resulting revision.
- [ ] Run `python -B -m unittest discover -s ops/trading -p 'test_*.py'`. Current expectation: 48 passing tests. Existing qualification tests reject isolated snapshots, stale/future ticks, invalid history, disconnects and skipped polling. Passing tests establish software behavior only.
- [ ] Use the existing authorized VPS SSH/Dokploy session. If access fails, retain an access blocker and the prepared commands; do not replace keys or install a new access service.
- [ ] On VPS run `timedatectl show -p NTPSynchronized -p Timezone`. Reconfirm pinned demo, Algo off and current Market Watch/UTC offset. Privately inspect bounded logs and container restart/OOM state for the earlier disconnection; record unknown if its cause cannot be established.
- [ ] Compare SHA-256 for the four verifier source files against the chosen commit and running `/opt/trading/` copies. Copy only mismatches after tests, preserving originals; no MT5 restart to install diagnostics. Record persistence/image differences if any.
- [ ] From VPS run the one-shot command below. Replace the uppercase placeholder locally with the existing pinned login; never put the identifier in the sanitized report. Expect `reason=ready`, fresh quote and the expected completed bar. Stop on guard failure or clock inconsistency; wide spread can block strategy readiness without proving a data outage.

```sh
docker exec -it kwg-mt5-desktop wine /opt/python/python.exe /opt/trading/verify-demo.py --login YOUR_DEMO_ACCOUNT_NUMBER --server-offset-seconds 10800
```

**Done when:** Source identity, runtime safety and session timestamp basis are recorded, or a specific blocker is retained.

## Task 2: Capture a new two-boundary window

**Interfaces:** Existing `collect(mt5, login, seconds, server_offset_seconds=0) -> dict` and `qualify_samples(samples: list[dict]) -> dict`. Produces schema-v1 private JSON and a sanitized data verdict; costs remain independently incomplete.

- [ ] During a confirmed open gold session, choose a new UTC-stamped filename under the persistent MT5 home. Run the existing command from VPS; use a supervised session that will remain connected. Do not start a second observer.

```sh
docker exec -it kwg-mt5-desktop wine /opt/python/python.exe /opt/trading/verify-demo.py --login YOUR_DEMO_ACCOUNT_NUMBER --server-offset-seconds 10800 --collect-seconds 3600 --output 'C:\users\mt5\gold-qualification-YYYYMMDD-HHMMSS.json'
```

- [ ] Observe the finite run through completion. The collector normally stops early on pass or after its one-hour deadline. Its SDK calls are synchronous: a hung SDK call can exceed that deadline. If stalled, stop only the diagnostic process, preserve available evidence, and record failure rather than claim a completed report. Do not kill MT5 to force collector completion.
- [ ] Require the ending contiguous segment to contain at least 361 accepted samples over at least 1,800 seconds, advancing ticks, and at least two consecutive +900-second completed-bar transitions. Each accepted bar must equal `floor(sampled_at/900)*900-900`; history must be valid with at least 250 bars; quote age must be 0–30 seconds. A polling interval over 10 seconds resets the segment.
- [ ] Treat CLI exit 0 as data-only pass, exit 2 as inconclusive; inspect JSON blockers in either case. Current collector account-guard failures also return inconclusive/exit 2, so do not rely on an older planned exit-1 distinction. A runtime crash without a valid report is a failure, never a pass.
- [ ] Recompute `qualify_samples(report['samples'])` using the pinned reducer and compare its count/transitions/spread fields. A top-level interruption/guard blocker still overrides any reducer-only result. Preserve all samples, raw clock fields, code hashes, SDK version and offset. Record accepted-segment UTC start/end separately from whole-run start/end.
- [ ] Copy the exact report into the private qualification directory and compare SHA-256. Record p50/p95/max spread in price units, count and five-second sampling cadence; these are sampled spreads, not measured slippage or tick-complete statistics.
- [ ] On failure, retain that run and diagnose the explicit failure before a separately named retry. Never join pre/post-disconnection samples, relax thresholds, or retry indefinitely without a new decision.

**Done when:** One reproducible data pass or a documented inconclusive attempt exists. An old pass does not certify future health.

## Task 3: Establish dated, account-specific costs

**Interfaces:** Existing `read_contract(mt5) -> dict`; cost evidence schema in Batch 1 Task 3; downstream `gold_costs.validate_profile(profile, start, end)`. Produces private provenance, not a newly approved simulator profile.

- [ ] Save the current allowlisted contract snapshot with capture time and source hash. Reconcile reported Standard STP versus `XAUUSD-VIP` using the exact broker entity/account category and symbol specification. Missing fields remain unknown.
- [ ] Obtain dated account-specific broker evidence for commission currency, per-side/round-trip basis, minimum fees, signed long/short swap, units, rollover time/timezone, weekday multipliers, effective intervals and contract changes. Record document URL/hash and covered dates privately. Do not send a broker message without explicit instruction.
- [ ] If evidence is unavailable, request those exact documents from the owner during execution; record `unknown` and uncovered dates. Public current pricing, zero demo charges and current swap fields cannot establish historical coverage.
- [ ] Keep `verified_current`, `verified_historical` and `unknown` distinct in the existing cost-evidence schema. Historical classification requires coverage of the actual evaluation dates and supported units/schedules; retain slippage as assumed at 0.05/0.10/0.30 price units per side.
- [ ] Run `python -B -m unittest discover -s ops/trading -p 'test_gold_costs.py'`. Require the existing unknown/uncovered profile rejection checks to pass. Do not manufacture a profile just to pass validation.
- [ ] Record historical timestamp/DST semantics as a separate blocker if unresolved. Today's 10800-second offset must not silently shift the immutable April–September dataset or generate a historical funding calendar.

**Done when:** Each material cost has sourced coverage or an explicit missing-evidence entry. Incomplete evidence leaves `cost_status=incomplete`.

## Task 4: Verify recovery separately and hand off

**Interfaces:** Existing observer SQLite `observations` keyed by `bar_time`; read-only MCP status; sanitized Batch 1 results. Produces separate data, cost and recovery dispositions.

- [ ] After the collector finishes, run `python -B -m unittest discover -s ops/trading -p 'test_observe_gold.py'`. Before a supervised restart, create a private consistent SQLite backup using `Connection.backup`, not a raw copy of the live database. Record integrity, row count and maximum bar time; do not publish metadata/account fields.
- [ ] Supervise one `docker restart kwg-mt5-desktop` in the execution session, preserving its volumes and configuration. Record start/end times. Do not overlap it with collection or start another writer against the observer journal.
- [ ] Recheck pinned demo, Algo off, one-shot readiness, fresh MCP heartbeat and subscription recovery. Compare a new consistent database snapshot with the backup: prior rows remain identical, bar keys remain unique, and the first new post-startup observation is suppressed as a baseline. Same-bar polls may correctly report duplicate.
- [ ] If recovery fails, preserve diagnostics and leave recovery blocked. Do not restore an old database over newer rows or repeatedly restart blindly. Label actual network-disconnect recovery untested unless directly exercised; restart recovery is a narrower result.
- [ ] Append sanitized timestamps, evidence hashes, accepted window/count/transitions, cost coverage, recovery results and unresolved blockers to the Batch 1 results. Update `ops/trading/HANDOFF.md` so older notes cannot be mistaken for current state.
- [ ] Run `git diff --check`; inspect only the named documentation changes for secrets. Commit the results and handoff together with `git commit -m "Record gold Batch 1 qualification evidence"` after explicitly staging those two paths. Push only as part of the agreed execution handoff.

**Batch 2 gates:** Data continuity and recovery evidence; reconciled contract and timestamp basis; historically covered commission/funding; owner-reviewed prospective policy; immutable chronological windows and reproducible baseline rerun. Keep `prepared_but_blocked` while any prerequisite is missing. The newest 2,000 bars remain excluded from trade simulation and are acknowledged as previously signal-inspected. Do not lower the draft 100-trade/60-day requirement to fit existing results. Batch 3 and 4 do not start under this plan.

## Documentation and self-review

Context7 `/lucas-campagna/mt5linux` consulted on 2026-09-28 for position-based
bar retrieval and timestamp semantics; no wrapper installation is needed.
[MetaQuotes position reference](https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesfrompos_py)
confirms position zero is current. The
[MetaQuotes UTC note](https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksfrom_py)
documents UTC; the observed server lead is a deployment-specific discrepancy,
not a universal reinterpretation of that API. Neither source proves broker fees.

Self-review: all five review risks map to existing tests plus operational checks.
No runtime change is planned; if execution exposes a defect, reproduce it with
one focused failing test before the smallest fix. Existing research artifacts
and unsuccessful runs stay immutable. Completion may honestly be blocked.

Plan prepared only: no collector, deployment, restart or broker-cost verification
was performed while writing it. Recommended execution is native/sequential:
one shared terminal and one evidence window do not benefit from parallel agents.
