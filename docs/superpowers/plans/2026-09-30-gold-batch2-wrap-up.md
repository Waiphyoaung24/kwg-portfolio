# Batch 2 wrap-up — 2026-09-30

## Current status — October 2 owner scope decision

Batch 2 is **closed for development, unqualified**. The owner deferred the
qualifying sample; real OAuth isolation and backend billing are remaining
Batch 3 activation work. See the [final development handoff](2026-10-02-batch2-batch3-handoff.md).
The September 30 evidence record below is preserved as history, not the active
development completion gate.

## Historical verdict — September 30

**Qualification: `prepared_but_blocked`. Development was still open at this checkpoint.** The deployed
desktop-close fix and exclusive evidence capture are working. Their success
does not qualify the baseline or unlock Batch 3 research.

## Completed and verified

- Native implementation and independent review of desktop-only reconciliation;
  complete observed volume, unique deals, finite net amounts and no resubmission.
- Owner rollout after consistent SQLite backup and exposure-free Algo-off check;
  image hashes matched and startup reconciled the existing attempt.
- Exclusive dated probe output, followed by owner verification of the saved byte
  hash and fresh, exposure-free read-only state. Detailed payload stays private.
- Owner-supplied current session specification preserved with a verified local
  image hash. The crop omits the symbol header, so applicability remains owner
  attributed. This is current session evidence, not historical coverage.
- Owner-saved post-reopening verifier passed fresh quotes and expected completed
  M15 history. Together with earlier boundary captures this closes the bounded
  recovery check. It does not measure immediate reopening latency or prove
  uninterrupted feed, historical dates or rate coverage.
- Three cost-validator and ten evaluator tests rerun successfully during this
  wrap-up. Earlier implementation verification passed 113 Python tests,
  JavaScript tests, Astro check/build and standalone page regeneration.

## What public current sources establish

The broker's current [commission guide](https://get.vtmarkets.help/hc/en-us/articles/37317570987545-What-fees-commissions-are-charged-for-trading)
lists zero separate gold commission for Standard STP and VIP STP. Its
[swap settlement guide](https://get.vtmarkets.help/hc/en-us/articles/37354714409625-What-does-PNL-Weekend-Swap-mean)
describes midnight settlement and possible later weekend adjustments. Its
[clock guide](https://get.vtmarkets.help/hc/en-us/articles/37317868198297-What-is-VT-Markets-GMT-offset-or-server-time)
describes GMT+2/GMT+3. These are current public statements, not dated rate or
offset coverage over the frozen evaluation range. No profile was promoted to
`verified_historical`; the actual cost validator still returns
`historical_coverage=False`, with commission and swap unverified.

## Remaining gates

| Gate | Required evidence | Status |
| --- | --- | --- |
| Session recovery | Bounded before-close/after-reopening captures plus expected completed M15 history; preserve failures | Passed for the observed boundary pair; limitations above |
| Historical costs | Applicable sourced commission, directional swap rates and rollover events covering exact windows | Uncovered |
| Historical clock | Dated offset/DST mapping and calendar interpretation across those windows | Uncovered |
| Prospective protocol | Freeze a future completed-bar start, source/policy hashes, flat folds and separate uninspected holdout before collection | Draft only; not started |
| Adequate evaluation | Covered observations under the unchanged approved policy; historical warmup stays diagnostic | Not established |
| Real-report provenance | Separately specified/tested simulator-to-gate adapter, then repeatable immutable baseline outputs | Deferred until qualified inputs |

The existing policy requires 60 observed validation days, three flat folds of
at least 20 days and 100 closed trades per strategy, alongside the unchanged
performance, drawdown, stress and bootstrap gates. A one-shot order is not a
strategy evaluation trade. No count or threshold was relaxed.

Private readiness and prospective-manifest drafts were saved outside Git.
The draft is `prepared_not_started`: collection start, windows and holdout are
unset, coverage intervals empty, blockers explicit. It is not a registered
collection run, and no new observed days have been claimed.

## Resume in order

1. Confirm the authenticated page projects the reconciled result correctly.
2. Preserve the completed bounded recovery evidence; no further arbitrary spot
   checks are needed for this item.
3. Establish sourced dated costs and clock coverage for the proposed interval.
   Preserve uncovered status if public current terms cannot provide history.
4. Freeze the prospective protocol before collecting qualifying future data.
5. Once inputs are covered, specify/verify the adapter and rerun the fixed
   baseline twice to distinct exclusive private outputs; compare bytes.

Keep Algo Trading off for observation. No new order, recurring job, candidate
research, promotion or journal reset was started as part of this wrap-up.
