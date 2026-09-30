# Gold Batch 3 preparation — session checkpoint, 2026-10-01 Bangkok

Owner is stopping here and intends to resume tomorrow, October 2 Bangkok time.
Work remains on `main`; preparation commits are `fb80e49` and `8883439`.
They are local commits, not pushed or deployed. Preserve unrelated local changes.

## Saved preparation

- [Specification](../specs/2026-10-01-gold-batch3-vibe-integration.md) and
  [implementation plan](2026-10-01-gold-batch3-vibe-integration.md).
- Strict offline response parsing/replay, development-packet validation and
  deterministic prompt construction in `ops/trading/research-gold.py`.
- Synthetic tests and fresh scoped reviews; last complete trading Python suite
  passed 120 tests, including seven research tests. Four local MCP tests passed
  with package-store access after frozen dependency restoration.
- Read-only MCP connectivity verified; anonymous access denied with HTTP 401.
  Installed Vibe-Trading metadata is 0.1.15. MCP supplies observation tools;
  the actual model inference route remains unverified.

All parser/prompt artifacts remain unreviewed and unqualified. Use synthetic
input only until controller isolation and sensitive-content clearance are
implemented. No real proposal, candidate registration, research job, strategy
evaluation, promotion, order, MT5 restart or journal reset occurred here.

## Running one-day smoke test — owner-reported

- Directory: `/root/kwg-gold-research/evidence/smoke-20260930T164651Z`.
- Interval: 2026-09-30 17:00 UTC to 2026-10-01 17:00 UTC.
- Finish capture only after 2026-10-01 17:15 UTC, which is
  **October 2, 00:15 Bangkok**.
- Start checks passed: Algo Trading off, no gold positions or pending orders.
- Cost status remains incomplete. No end capture or final pipeline verdict has
  been confirmed. Preserve collector, raw exports, journals and all artifacts.

No reminder, automation or end capture was scheduled by this session.
The existing VPS collector continues independently of this chat.

## Remaining gates

Batch 2 remains `prepared_but_blocked`. A successful one-day pipeline check does
not qualify a strategy or unlock Batch 3 research. The unchanged policy requires
60 observed validation days, three flat folds of at least 20 days and 100 closed
trades per strategy, plus the approved performance/stress/bootstrap criteria.
These are evidence requirements, not a countdown from this checkpoint.

Dated applicable commission/swap/rollover and clock/calendar coverage, a frozen
prospective protocol, adequate covered observations, verified simulator-to-gate
provenance and repeatable immutable baseline outputs remain outstanding. The
legacy candidate manifest still rejects qualified dated costs/explicit windows;
prospective contract support must be verified before a real comparison.

Preparation can continue with read-only model-route identification, synthetic
controller isolation, one-request/no-retry/deadline checks and usage/cost
accounting. A model request or real proposal is not authorized by this checkpoint.
Risk limits remain fixed; promotion requires explicit human approval tied to
the exact evidence and candidate hashes.

## Resume tomorrow

1. Read `AGENTS.md`, `CLAUDE.md`, `ops/trading/HANDOFF.md`, this checkpoint,
   the linked specification/plan and the
   [Batch 2 wrap-up](2026-09-30-gold-batch2-wrap-up.md).
2. Verify the smoke-test finish time has passed before any end capture. If
   continuing that operational work, use the existing
   [one-day runbook](2026-09-30-gold-one-day-smoke-test.md), preserve exclusive
   outputs and report pipeline checks separately from qualification. Do not
   infer success from elapsed time or overwrite existing artifacts.
3. Next independent Batch 3 preparation step: identify the owner's existing
   Claude/Worker inference route with secret-safe read-only checks. Establish
   the pinned provider interface and enforceable bounds before implementing
   dispatch. Never reuse the research-MCP bearer token as inference credentials.
4. Continue synthetic controller work only within the unchanged gates. Keep
   Algo Trading off for observation and leave the collector running untouched.

Suggested resume instruction:

> Continue on main from
> `docs/superpowers/plans/2026-10-01-gold-batch3-session-checkpoint.md`.
> Preserve the one-day smoke collector and artifacts. Review its finish evidence
> separately from Batch 2 qualification, then continue read-only model-route
> verification and synthetic controller preparation. No candidate research,
> orders, restarts, journal resets, risk changes or promotion.
