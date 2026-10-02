# Prospective observation preflight — prepared, not started

Continue the approved offline-first sequence on main. Reuse the existing VPS
observer and SQLite journal. This preflight neither launches a collector nor
changes its logging, journals, risk configuration or services.

## Current findings

- Baseline report reconciliation is implemented and fixture-tested. It still
  assigns zero verified observed days; numerical reproduction is not provenance.
- The protocol draft has no start, windows or holdout. No prospective run is
  registered or collecting under that draft.
- Local compose.yml specifies Docker log rotation at 2m x 2. Prior smoke review
  recovered only a late retained tail; full-interval diagnostics are missing.
  Verify deployed configuration instead of assuming it matches local source.
- Current contract and screenshots establish current values only. Dated
  commission, swap events, settlement timezone and broker-clock/session coverage
  remain unverified. Broker confirmation was deferred for unqualified learning,
  not waived for qualification.
- Non-interactive VPS SSH on this continuation rejected publickey authentication.
  No current remote health, source identity, disk space or retention check passed.
- Unknown OAuth monetary cost continues to block gold model dispatch. Model
  authentication or a successful learning conversation does not clear that gate.

### Owner-authenticated VPS results — 2026-10-02 08:11:35 UTC

Read directly from the connected Codex terminal after owner ran the checks:

| Check | Observed result | Scope |
|---|---|---|
| Host clock | Etc/UTC; NTP=yes; NTPSynchronized=yes | Current synchronization only |
| Desktop container | running; started 2026-09-30T11:40:37.553873291Z; restarts=0 | Container state, not MT5 health |
| Docker logging | json-file; max-size=2m; max-file=2 | Full prospective diagnostics not retained by this configuration alone |
| Evidence filesystem | 193G total; 15G used; 178G available; 8% used | Current space, not a retention guarantee |
| Current contract bytes | SHA-256 matches expected hash below | Saved-byte integrity only |

Read-only preflight passed for these selected fields. Current broker connection,
Algo-off/exposure checks, deployed source identity and full-period capture still
need verification. No collector/service/journal changes made. Batch 2 stays
prepared_but_blocked; no observed-day or historical cost credit assigned.

## Read-only VPS checks

Connect interactively from PowerShell; enter any key passphrase locally:

```powershell
ssh root@187.52.117.116
```

Then run these normal Linux commands at the root@... prompt. Print only selected
Docker fields; never print full docker inspect, .env, broker credentials or tokens.

```sh
date -u +%Y-%m-%dT%H:%M:%SZ
timedatectl show -p Timezone -p NTPSynchronized -p NTP
docker inspect --format '{{.Name}} status={{.State.Status}} running={{.State.Running}} started={{.State.StartedAt}} restarts={{.RestartCount}}' kwg-mt5-desktop
docker inspect --format 'log_driver={{.HostConfig.LogConfig.Type}} log_options={{json .HostConfig.LogConfig.Config}}' kwg-mt5-desktop
df -h /root/kwg-gold-research/evidence
sha256sum /root/kwg-gold-research/evidence/broker-intake-S7u11LUf/current-contract.json
```

Expected contract hash:
e693d61fe075444ee9ed8d6ec0b9e839fd15bcf620396b07f33652ccf0ebe05f.
A hash match establishes saved bytes only, not historical applicability.
Clock synchronization and running=true establish current status only; neither
proves MT5 connectivity, exposure, historical coverage or uninterrupted collection.
Missing paths or failed commands remain blockers; do not restart to force a pass.
These commands do not change the existing smoke directory or collector.

## Decisions before prospective collection

### Bounded follower trial — owner output received

Private run: diagnostic-trial-20261002T083518Z-840efc3b under the VPS evidence
directory. Expected timeout after the 60-second invocation; 12 samples, zero
detected gaps/rejected frames/trailing bytes, verified receipt hash and unchanged
container state reported by the launcher. Diagnostics SHA-256:
32b15c2054d491e217ebb5322f8e2029719414a8c960e08a5aa5fc2bfdac1b45.
No model request. This is owner-pasted evidence, not independent artifact review.
The trial finished and remains unqualified; no prospective collection began.
Longer capture scheduling, liveness/gap supervision and handoff between bounded
captures still require review. A minute of delivery does not clear retention.

Detailed -ReviewOnly output received: byte and source hashes matched, root-owned
0600 artifacts, elapsed 60.0063s; all 12 samples were fresh-quote duplicate polls.
Maximum interval 5.0041s and receive lag 0.0138s. Receipt SHA-256:
c5b8755bad5bac31c64ea77bf240e51c69cf779c0dfc05f2d7e00c06243fb8ff.
No new candle or observed-day credit. Sustained design and proposed stage rules
are in ../specs/2026-10-02-sustained-observation.md, dates/deadline unset and no
supervisor/scheduler installed. The design draft does not complete readiness.

1. **Diagnostic retention.** Specify a separate, owner-private append-only capture
   of every observer poll, including blocked reads, alongside the existing
   journal. Document timestamps, writer liveness, gap detection, byte receipts,
   bounded storage and failure handling. Reuse existing output where possible.
   A log-rotation increase alone cannot prove retention. A new capture process
   is a separate implementation/start step; none is installed here.
2. **Preregistered schedule.** Choose future UTC completed-bar collection start
   after manifest creation. Record development, three ordered flat validation
   folds and a separate untouched holdout, or fixed selection rules that cannot
   choose favorable days after results. Minimum 60 observed validation days,
   at least 20 per fold, at least 100 closed simulated trades per strategy.
   Calendar duration and fetched history alone do not satisfy these minimums.
3. **Evidence coverage.** Establish exact-account cost and clock/session evidence
   over those windows. Preserve unknowns and all source hashes. Historical
   rates cannot be inferred from today's screenshot. Missing observations do
   not become observed days by backfilling broker candles.
4. **Manifest review.** Verify current baseline/source/policy/risk identities and
   source applicability. Record diagnostics and reserved holdout before start.
   Changing a draft into collecting status is not evidence that a process ran.
5. **After collection.** Verify gaps and coverage, export/reconcile the baseline
   to distinct exclusive reports, verify provenance and the evaluator adapter.
   Keep the existing evaluator qualification cap until that review is complete.

No costs or dates are invented. The one-day smoke remains a partial pipeline
check, earns no new qualification credit and is never rerun or overwritten here.
Promotion always requires explicit human approval under unchanged risk limits.

## Verification / checkpoint

- [x] Read current handoff, roadmap, Batch 2 result and collection runbook.
- [x] Inspect local retention configuration and previous smoke limitations.
- [x] Attempt read-only SSH; record authentication failure honestly.
- [x] Review owner-authenticated VPS output from the checks above.
- [ ] Review a concrete retention design and prospective schedule before start.
- [ ] Verify dated coverage and sufficient observed sample; complete Batch 2.

Related implementation: [report adapter plan](2026-10-02-batch2-report-adapter.md).
