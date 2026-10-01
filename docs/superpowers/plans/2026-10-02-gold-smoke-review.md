# One-day smoke finish review — 2026-10-02 Bangkok

Final review: **smoke evidence capture complete; artifact preservation passed;
continuous observation not established. Overall pipeline result is partial,
not a clean pass. Batch 2 remains `prepared_but_blocked`.** Finish artifacts and
a consistent observer backup were preserved through the owner's connected SSH
terminal. Two exported candles have no observation. Four elapsed slots still
need exact-symbol session review.

## Verified finish checks

Read the command results directly through Codex's terminal snapshot. The owner
executed the supplied runbook commands; the agent cannot type into that terminal.
End-contract, verifier and export receipt parsed. Five deployed source hashes
matched the start freeze. Both exact raw export copies matched their receipt
SHA-256 hashes before being saved exclusively. Backup used SQLite read-only
source connection and `Connection.backup`; integrity check passed. Collector
and original database were not stopped or reset.

| Check | Result |
| --- | --- |
| Interval rows | 90: 87 observed, 3 baseline |
| Duplicate bar times | 0 |
| Recorded before candle completion | 0 |
| Observations without matching raw timestamp | 0 |
| Raw interval candles without observation | 2 |
| Elapsed M15 slots absent from raw export | 4, session interpretation pending |
| Start/end Algo Trading and exposure | Off; zero gold positions/pending orders |
| Start/end quote states | Fresh |
| Source hashes | Unchanged |

Private artifacts include `start-raw-export.json`, `end-raw-export.json`,
`observer-finish.sqlite3` and exclusive `smoke-report.json` with artifact hashes.
The report deliberately retains `pipeline_verdict=pending_review`. Candle
matching is timestamp correspondence conditional on the configured 10800-second
offset, not full historical clock qualification or OHLC replay verification.
Missing observations cannot be filled from retrospective exports. Baseline rows
are not counted as normal observed rows. Exact missing/baseline times, session
closure applicability and blocked polling periods still require review.

## Gap and retained-log review

Every artifact hash in the saved smoke report was recomputed and verified in a
separate read-only command after capture. The preserved observer backup shows:

| Item | UTC bar-open timestamps |
| --- | --- |
| Raw candles without observer rows | September 30 20:45 and 22:00 |
| Elapsed slots without raw candles | September 30 21:00, 21:15, 21:30, 21:45 |
| Baseline rows | September 30 22:15 and 23:00; October 1 06:45 |

The one-hour raw gap is consistent with a session break, not proof of its
exact-symbol applicability. No dated session evidence was added by this review.
The deployed observer requires a fresh quote and consecutive latest completed
candles. Those guards plausibly explain the two candles around the gap, but
their actual blocking reasons are not established by the saved observations.
The observer also resets bootstrap after a blocked poll, so baseline rows alone
do not establish restarts. No restart or root cause is inferred from these times.

Owner preserved `observer-interval-stdout.log`, `observer-interval-stderr.log`
and `observer-log-review.json` using the supplied bounded Docker-log command.
The initial line parser found zero observer samples. Subsequent read-only
inspection established that stdout is nonempty (1,294,994 bytes, 34,926 lines,
2,328 opening-brace markers); stderr is empty. Parsing complete JSON from the
timestamped/terminal-wrapped stream recovered the records below. The initial
zero result was a parsing limitation, not proof of absent observer logs.

| Retained diagnostic check | Result |
| --- | --- |
| Unique recovered samples | 1,164 |
| First sample UTC | October 1 15:38:00.526043 |
| Last sample UTC | October 1 17:14:56.546670 |
| Blocked reasons in recovered portion | None |
| Docker logging | json-file, max-size 2m, max-file 2 |
| Container restarts | 0; started September 30 11:40:37 UTC |
| Deployed desktop launcher | SHA-256 matched current local reviewed file |

The retained portion covers only the end of the smoke interval plus the allowed
finish-capture margin. It does not cover the September 30 closure/reopening
gaps or the October 1 06:45 baseline. No blocked samples near the end do not
establish absence of blocking earlier. Logging is bounded and the observed
coverage is limited; exact rotation events were not inspected. Zero container
restarts does not establish absence of observer-process restarts or blocked
bootstrap resets.

Private `observer-wrapped-log-review.json` preserves the corrected summary and
source-log byte hashes; the original log review/report remains unchanged.
`ops/trading/review_observer_log.py` contains the read-only parser and a runnable
synthetic wrapping/plain/truncated-record check, which passed. No log content is
executed or used to change qualification. Originals and the pending-review
private smoke report remain unchanged; this document records the reviewed
verdict.

The read-only evidence-name search located the two prior dated session-recovery
JSON files. This does not establish new historical session/cost/clock coverage.
Current official broker guidance was rechecked: [trading hours](https://get.vtmarkets.help/hc/en-us/articles/37317499627289-What-are-the-trading-hours)
directs users to exact product Specification; [server time](https://get.vtmarkets.help/hc/en-us/articles/37317868198297-What-is-VT-Markets-GMT-offset-or-server-time)
describes GMT+2/+3; [commission](https://get.vtmarkets.help/hc/en-us/articles/37317570987545-What-fees-commissions-are-charged-for-trading)
depends on account type. These current statements do not backdate applicability,
effective rates, rollover events or offset changes over evaluation windows.

## Batch 2 decision and next work

The one-day smoke delivery item is closed with the limitations above. The
qualification milestone is not complete and Batch 3 dispatch stays gated.

Before qualifying a future run, establish dated exact-symbol session/clock
evidence, sourced effective costs and a frozen prospective protocol. Docker
receives the deployed observer output, but its current bounded
retention does not preserve a complete one-day diagnostic trace. Prepare a
reviewed means of preserving that existing output for a future run; do not
restart the current collector, create a second collector or expand retention
without a concrete reviewed change. Investigate the two boundary omissions
without repairing this run retrospectively. Then
collect the unchanged 60 observed validation days / three >=20-day flat folds /
100 closed trades per strategy and verify the real-report adapter and repeatable
fixed baseline. No threshold reductions or qualification credit are assigned
to this smoke interval. The existing synthetic adapter is not real-report
qualification evidence.

This captures pipeline evidence; it does not complete Batch 2. No model request,
candidate research, orders, risk changes, promotion or MT5 restart occurred.

## Initial access check

At the initial check, clock was 2026-10-01 17:34 UTC / October 2 00:34 Bangkok,
after the 17:15 UTC capture threshold. Target is the existing private directory
`/root/kwg-gold-research/evidence/smoke-20260930T164651Z`.
Its declared interval is September 30 17:00 UTC through October 1 17:00 UTC.

Both default and explicit existing Windows SSH identity attempts were rejected
with `Permission denied (publickey)`. No usable SSH agent was present. The
existing Dokploy management URL presents Sign in in the in-app browser; owner
login requested. No credentials were opened or supplied. No remote command
ran, finish capture was made or collector/service was changed.

## Review protocol

1. Inventory existing artifacts first. Do not overwrite a finish capture/report
   if one already exists; preserve originals and failures.
2. Verify manifest timing, start evidence, pinned deployed hashes and exact
   export receipt targets. If finish artifacts are absent, perform the existing
   authorized runbook's exclusive end capture and read-only-source SQLite backup.
3. Check JSON and saved-byte hashes, SQLite integrity, observed versus bootstrap
   rows, interval membership, duplicates, gaps, blocked periods and raw candle
   correspondence. Retrospective export bars cannot replace missing observations.
4. Report endpoint demo/Algo-off/exposure/quote state and dated clock/cost limits.
   Preserve private runtime payloads outside Git; publish only sanitized verdicts.
5. Record individual pipeline checks and the independent qualification verdict.

The unchanged policy still requires 60 observed validation days, three flat
folds of at least 20 days, 100 closed trades per strategy, historical cost/clock
coverage, prospective protocol and verified repeatable real-report provenance.
The prior wrap-up records these gates as unmet. A one-day elapsed interval or
passing pipeline cannot complete them. No threshold change, candidate, trade or
promotion is authorized by this review.
