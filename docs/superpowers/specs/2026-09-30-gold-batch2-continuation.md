# Gold Batch 2 continuation specification

Status: approved by the owner for native implementation on main. Scope: desktop-origin close reconciliation and read-only qualification evidence. The implementation plans are separate because either can be reviewed independently. Live rollout and external qualification remain pending.

## Decisions and alternatives

The owner selected Batch 2 qualification and desktop closes only. A journal-only acknowledgement would hide the unresolved cause; a new operations framework would add unnecessary state and deployment work. Reuse the existing broker matching, SQLite journal, status projection and evidence probe. No new dependency, service, scheduler or execution control is required.

## Milestone A: verified desktop closes

The one-shot runner must distinguish a verified closed position from an unsupported close origin. A desktop-origin close may become `closed` with `close_reason="manual desktop"` only when:

- The pinned demo identity passes existing guards and every gold position/order query succeeds.
- No gold position or pending order remains. Another attempt's exposure still blocks reconciliation.
- Existing matching anchors bind the entry and exit deals to one position belonging to this attempt. Matching a symbol or magic number alone is insufficient.
- The journal previously observed the protected position (`opened_at` and a valid positive recorded volume). A fast desktop close before that observation remains `needs_attention`; do not relax `_historical_protection` for this milestone.
- Complete entry/exit volumes equal the last observed filled volume within `1e-8`; direction is consistent; unsupported reversals/close-by entries are rejected. Multiple exit fills are allowed only if they fully close that volume.
- Manual-close deals have positive integer unique tickets, a single position identity and only `DEAL_REASON_CLIENT` exit reasons. Mobile, web, unknown and mixed manual/protective origins remain unsupported for this new path.
- Every profit, commission, swap and fee is finite, and their cumulative sum remains finite. Net result includes both entry and exit deal amounts. Missing values are not zero. The result covers matching deal amounts, not a guarantee against later separate broker adjustments.

Existing SL/TP paths and historical timed-close reconciliation remain supported. No timer or new entry permission is added. Reconciliation is idempotent after restart and calls no `order_send` or `order_check`; journal rows and request identities are preserved. The configured current offset is used only as the existing live close-time convention, not historical DST proof.

The existing page displays `Closed`, UTC close time and net result. For `manual desktop`, its guidance must say exactly: `Closed from MT5 desktop. This is a historical result.` No layout or design-system changes. Other closed reasons retain current guidance. The standalone page is regenerated from Astro, never hand-edited.

Done means fake-SDK tests prove the positive path, failure guards and no resubmission; after separate deployment review, a read-only reconciliation of the existing journal produces a broker-supported result. A new trade is not needed for verification.

## Milestone B: evidence collection ready

Extend the existing probe with optional `--output PATH`. Persist a canonical JSON result with exclusive creation, preserve existing stdout behavior without that option, and publish only an output hash/allowlisted summary when it is supplied. Complete all samples before opening the output. Refuse overwrite; report capture/write failure without claiming success. Failed writes must not be treated as verified evidence. Owner-private permissions are required for the evidence directory and files. Capture remains read-only, with no credentials/account identifiers/tickets in its payload.

Store raw tick timestamps, host UTC and the explicitly selected current offset as already implemented. Always retain `cost_status="incomplete"` and `timestamp_status="current_spot_checks_only"`; unchanged rates around midnight do not establish a funding charge. A stale quote during a break is recorded as stale, never relabelled fresh. Record exact symbol sessions and post-reopening verifier results privately. Do not restart the desktop merely because a closed-session quote is stale.

The original raw historical snapshots stay immutable. The exporter's raw-host incomplete-bar count is not a deletion criterion. No blanket current-offset conversion, reconstructed bars or retrospective claims of pristine holdout are allowed.

Prospective collection starts at an explicitly recorded future completed-bar boundary. A private manifest records its creation time, collection start, code/policy hashes, source references, coverage intervals, clock/session evidence and blockers. Dated snapshots establish observations at those instants, not rates throughout unobserved intervals. Public current terms only remain the source constraint. Missing account applicability, rate coverage, rollover events or dated offset/DST coverage blocks qualification.

## Milestone C: qualified baseline — conditional

This is an evidence gate, not a promise that software changes will complete qualification. Before a qualified rerun, commission/funding coverage must span the exact windows, clock/session mapping must be evidenced, and the simulator-to-gate adapter must be independently specified and verified. Until then retain `prepared_but_blocked` and `simulator_provenance_unverified`. Milestone B does not lift either status.

Use the unchanged approved v1 policy: at least 100 closed trades in each strategy across 60 observed validation days, three flat folds with at least 20 observed days each, PF at least 1.10, base improvement at least 0.25 percentage points, drawdown at most 5% and baseline plus 0.25 percentage points, and the existing stress/bootstrap gates. Preserve seed 20260928, 10,000 replicates, block length 5 and slippage scenarios 0.05/0.10/0.30 per side. Historical warmup cannot count as newly observed validation. No candidate is fabricated to meet a baseline-only gate.

Once covered, run the baseline twice with identical immutable inputs and exclusive outputs; compare bytes. An inspected old baseline remains diagnostic. A separate adapter plan is required when real qualified inputs exist; do not build an unverified adapter or lower thresholds now. Batch 3 research and promotion remain conditional on the original roadmap's gates.

## Safety and scope

Keep demo-only `XAUUSD-VIP`, existing minimum-lot/risk ceilings, pinned account and one-attempt rules. Algo Trading stays off for observation. No new order, cancellation, SL/TP edit, journal reset, live-account route, automatic promotion, AI research or recurring job is authorized by this specification. Deployment requires a reviewed concrete diff and current broker-state check. Private captures, account evidence and detailed results stay outside Git; plans use synthetic examples only.

## Sources and limits

Context7 queried `/lucas-campagna/mt5linux` for `history_deals_get`: date/order/position filters, TradeDeal fields and `None` on error. This wrapper is documentation context, not a dependency proposal. Its example that conflates empty history and errors must not be copied.

Primary references: [history_deals_get](https://www.mql5.com/en/docs/python_metatrader5/mt5historydealsget_py), [deal properties and origins](https://www.mql5.com/en/docs/constants/tradingconstants/dealproperties), [broker product sessions](https://get.vtmarkets.help/hc/en-us/articles/37317499627289-What-are-the-trading-hours), [server clock](https://get.vtmarkets.help/hc/en-us/articles/37317868198297-What-is-VT-Markets-GMT-offset-or-server-time). APIs define history semantics; they do not prove this account's historical costs or timezone schedule.
