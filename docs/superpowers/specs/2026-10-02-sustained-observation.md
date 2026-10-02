# Sustained diagnostic retention and prospective schedule — draft

Status: preparation only. No scheduler, service, new long capture or prospective
manifest has been started. Batch 2 remains prepared_but_blocked. Gold dispatch
remains blocked by unknown OAuth cost; fixed risk and human promotion approval
are unchanged. The original smoke, private datasets and journals are preserved.

## Receipt review

Known trial: diagnostic-trial-20261002T083518Z-840efc3b, selected diagnostics hash
32b15c2054d491e217ebb5322f8e2029719414a8c960e08a5aa5fc2bfdac1b45.
Owner summary reports 12 samples, expected timeout, no gaps/rejected frames/tail,
verified receipt bytes and unchanged container state. Detailed review uses
owner-authenticated read-only output from run-diagnostic-trial.ps1 -ReviewOnly.
Review verifies actual bytes, saved source hashes, counts, sample interval,
receipt duration, receive lag, state/quote breakdown and private file permissions.
It assigns zero observed days and never changes evidence or launches a follower.

Owner supplied the detailed read-only review: 2026-10-02 08:35:18.132023–
08:36:18.138321 UTC, 60.0063 seconds. First/last source samples were
08:35:20.388859/08:36:15.394552 UTC. Twelve fresh quotes, all status duplicate;
max sample interval 5.0041 seconds, max receive lag 0.0138 seconds. No gaps,
rejected frames or trailing bytes. Bytes/source hashes and private permissions
passed. Receipt SHA-256:
c5b8755bad5bac31c64ea77bf240e51c69cf779c0dfc05f2d7e00c06243fb8ff.
This is reviewed owner-authenticated script output, not independent direct SSH
artifact access by the agent. It proves short-interval delivery of duplicate
polls, not a new candle, observed date, Algo/exposure state or full-day coverage.

## Selected retention design

Reuse the reviewed fixed-container diagnostic follower as a host operations
component. Keep it separate from Vibe-Trading, its model, broker credentials
and the existing observer. Operations' Docker access is not delegated to AI.

| Item | Proposed rule | Evidence / failure behavior |
|---|---|---|
| Segments | Unique private directory per capture, at most 24 hours and 64 MiB diagnostic bytes | Receipt and source hashes per segment; never overwrite |
| Handoff | Start next segment 5 minutes before previous bounded end | Require actual sample overlap; no presumed continuity |
| Liveness | Independent supervisor checks every 10 seconds; alert on no new selected sample for more than 30 seconds | Record gap start/end; existing observer continues untouched |
| Time | Record host UTC and source sample times; retain synchronization and applicable broker mapping | Clock jumps or nonmonotonic samples block day completeness |
| Failure | Preserve partial files, tails, rejected-frame hashes and exit reason | Restart only follower into new identity after operator review; never restart MT5 |
| Storage | Measure trial bytes/minute, reserve twice projected capture storage plus separate journal/export budget | Check free space before launch; halt new captures if budget unavailable; no evidence deletion |
| Integrity | Finalize receipts, verify bytes/counts/source hashes, preserve completed files as read-only | Missing receipt/hash mismatch invalidates segment completeness |
| Operator review | Daily selected-state/gap review and consistent SQLite/export preservation | No raw credential-bearing mixed logs printed or passed to researcher |

The follower alone is not a scheduler or watchdog. retention_supervisor.py now
implements bounded local-rehearsable supervision and segment reconciliation:
at most two followers, overlaps, a 30-second stale-writer check, explicit disk
reserve, owned process-group cleanup and source/receipt/boundary verification.
Fake-process/capture rehearsals passed. This is not a deployed service; POSIX
process-group behavior has only been exercised through mocks here. Operator
review and a supervised VPS handoff trial remain required before sustained use.
No new recurring run is authorized by this planning document. Cross-run handoff,
calendar scheduling, host recovery, alerts and storage preservation remain
operations responsibilities; the bounded supervisor does not implement them.

Capture all observer polls, including blocked/duplicate/baseline states. Preserve
separate guard/current-contract evidence to verify pinned demo, Algo Trading off
and exposure. Selected fields and hashed error text alone cannot prove every
guard, restore raw error messages, or establish uninterrupted broker delivery.
Reconcile segment overlaps by sample timestamp and source record hash: keep
original copies and deduplicate only the derived index. Conflicting records for
the same timestamp block reconciliation. Include first/last capture boundaries,
not only gaps between adjacent received samples. The 30-second diagnostic alert
threshold is an operational review trigger, not a new strategy risk limit.

## Proposed schedule, dates deliberately unset

Owner selected these stage lengths on October 2: 20 eligible development days,
three validation folds of 20 eligible observed days, and 20 untouched holdout
days. Start and calendar deadline remain unset until evidence readiness.
This approves the lengths, not collection start or evidence applicability.

### Supervised short handoff trials received

Owner ran the reviewed 110-second launcher twice on October 2 UTC:
retention-handoff-20261002T092809Z-d1e5fda8 and
retention-handoff-20261002T093048Z-df5db154. Each reports two segments,
22 unique samples, no reconciliation/supervision blockers and unchanged
container state. Both remain unqualified, zero observed days/model requests.
Supervisor receipt hashes respectively:
e9f299d55b5c81f6d47456cac44a3a799c066bc946947277bd7e479eb1da7636 and
6bb0dc77240f6e125c7e185f193147d034828b12d9b9960cb2646ee633c53772.
This is owner-pasted launcher evidence; full artifacts have not been read directly
by the agent. Preserve both independent attempts. Their gap is not covered by
these trials; they cannot be stitched into continuous prospective retention.
No sustained deployment or scheduled collection follows from short-trial success.

Corrected owner-authenticated -RetentionReview output subsequently verified both
pinned receipt hashes, actual segment bytes/source hashes, overlap reconciliation
and private permissions, with no blockers. First interval 09:28:09.755922–
09:29:59.873127 UTC (110.1172s); second 09:30:48.979761–09:32:39.045577 UTC
(110.0658s), October 2. Each has two segments and 22 unique samples. This closes
the detailed short-trial review gate; it does not cover the intervening gap or
prove sustained retention. Zero observed days/model requests and unqualified
status remain explicit. No direct agent SSH artifact inspection is claimed.

Approve selection rules and freeze their hash before results are inspected.
Set T0 to a future UTC midnight after manifest creation, operator review, source
checks, retention readiness and applicable dated-evidence coverage. Record it
explicitly; this document does not select a calendar date or start collection.

| Stage | Draft selection rule | Qualification treatment |
|---|---|---|
| Warmup | First 249 completed, covered M15 bars after T0 | No observed-day or validation-trade credit |
| Development | First 20 eligible observed UTC dates after warmup | Proposal input may use development only; length owner-selected |
| Validation fold 1 | Next 20 eligible observed UTC dates | Flat initial capital; fixed baseline and cost scenarios |
| Validation fold 2 | Next 20 eligible observed UTC dates | Flat initial capital; chronological and disjoint |
| Validation fold 3 | Next 20 eligible observed UTC dates | Flat initial capital; chronological and disjoint |
| Future holdout | Next 20 eligible observed UTC dates, reserved before the run | No strategy-outcome inspection; length owner-selected |

Validation is one continuous timestamp window partitioned into three contiguous
fold windows, including intervening closures and failed/incomplete dates. Each
fold ends at the close of its twentieth eligible UTC date. Do not omit failed
bars/dates from the simulator dataset to improve performance. Eligibility is
determined from completeness evidence alone, with outcomes hidden. Warmup and
partial stage-boundary dates receive no observed-day credit. Keep the original
reserved holdout separate; never replace it or count old inspected snapshots.

An eligible UTC date has documented open-session slots, all required completed
M15 observations, explicit closure boundaries, continuous reviewed diagnostics,
correct time mapping and applicable dated cost coverage. Entirely closed dates
are not observed trading days. Raw fetched history, a pair of fresh checks,
calendar duration and reconstructed missed candles do not establish eligibility.
Daily evidence review must not see strategy P&L while determining eligibility.
Cost and clock/session coverage must cover the entire simulator timestamp
window, including intervening ineligible dates; skipping their day credit does
not permit gaps in cost coverage or deletion of their bars.

Freeze a calendar deadline before T0 as well as these selection rules. At that
deadline, missing days or fewer than 100 closed simulated validation trades per
strategy yield inconclusive evidence. Do not extend a completed run or change
folds after seeing outcomes. A later experiment needs a new preregistration.
The 60/20/100 minima are approved policy; owner-selected development/holdout
lengths are scheduling decisions. Calendar deadline remains unset.
No deadline or start is invented here. This can take longer than 60 calendar days.

## Gates to enact this draft

1. Detailed 60-second receipt/source/permission/time review received as above;
   repeat checks against the immutable saved artifacts before prospective start.
2. Local supervisor/fake overlap/failure checks passed; review deployment and
   verify an actual supervised VPS handoff without touching the collector.
3. Obtain dated commission/swap/rollover and clock/session evidence covering
   the proposed dates. Missing coverage stays a blocker even on demo.
4. Owner approves development/holdout length, T0, calendar deadline and frozen
   stage rules; verify current source/risk/policy identities in private manifest.
5. Start supervised collection separately; verify sample/coverage/provenance
   before Batch 2 gate inputs or any Batch 3 candidate comparison.

Unknown OAuth cost must be resolved separately before gold model dispatch.
No strategy promotion or order placement follows automatically from this plan.
