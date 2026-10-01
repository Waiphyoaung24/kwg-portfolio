# Autonomous gold workspace — brainstorming draft

Status: owner accepted the recommended gold demo operations dashboard and
requested implementation. UI/read-only integration is authorized; execution
activation, real research and deployment remain outside this request.

## Owner intent and reference

The owner wants autonomous trading operated from the existing app, not only
an external research tool. Keep the chosen Vibe-Trading application and Codex
OAuth integration as the research component. A new private app page can expose
the complete operating workflow while reusing the existing MT5 foundation.

The reference directory `C:/Users/wai19/Downloads/ai-trading-bot/trading`
contains eight presentation screenshots, not executable source. Their workflow
is scan -> technical analysis -> research -> risk assessment -> trade plan.
Their displayed returns, win rates and confidence scores are illustrative
reference content, not evidence or requirements for this implementation.

## Options put to the owner

1. Gold demo operations dashboard: market health, strategy state, research,
   qualification, positions and journal; future runner controls. Recommended
   because it matches the autonomous operating goal and current foundation.
2. Research cockpit: proposals, baseline comparisons and human approval first;
   less execution interface, narrower deliverable.
3. Broader terminal: multi-market charts, scanners and portfolios; larger scope
   and new data/execution integrations beyond the current gold foundation.

## Recommended architecture, pending scope choice

Proposed page `/vault/trading-bot`; retain the supervised single-trade page.
The new route must have verified authentication, not merely Vault obscurity.
Astro renders the operating surface; protected APIs expose sanitized evidence
and later audited controls. OAuth tokens and broker credentials stay server-side.
No browser-to-broker or browser-to-provider connection is planned.

Existing observation/evidence -> approved development packet -> separate Vibe
research app with Codex OAuth -> strict candidate schema -> our deterministic
simulator/qualification -> human strategy approval -> later autonomous demo
runner -> broker and reconciliation journal -> protected page status.

Autonomous execution means a qualified, approved strategy can decide and manage
eligible trades without asking for every entry. The LLM proposes research
candidates; it does not invent risk limits or directly submit orders. Strategy
promotion approval and run authorization are separate from per-trade decisions.
The existing one-request research budget remains unresolved for full app use.

The single-attempt demo controller is not an autonomous runner. Continuous
execution requires its own design and verification: persisted candle decisions,
risk sizing, broker-held protection, loss pause, position ownership, uncertain
submission reconciliation, recovery and operator stop behavior. An attractive
page does not implement these guarantees.

## First-page information hierarchy

- Operating state and the exact reason entries are blocked; data timestamp.
- Gold M15 feed and EMA20/EMA50/ATR14 context, when a qualified chart feed exists.
- Active strategy identity and unchanged approved risk rules.
- Research/proposal history, baseline comparison and qualification evidence.
- Positions, broker-confirmed fills, costs and journal; absent data remains absent.
- Operator actions only when their backend and authorization are implemented;
  initial page has no functional order/arming/promotion controls.

Keep the existing dark canvas, tokens, weight 400 typography, hairline borders
and pill interactions from DESIGN.md. Use the reference's workflow, not its
light theme, invented metrics or stock-specific financial panels. AI confidence
is not a calibrated win probability; do not present it as one.

## Preparation versus activation

Prepare page design and read-only integration while Batch 2 evidence accumulates.
Preserve collector and smoke artifacts. The October 2, 00:15 Bangkok capture
deadline ends a pipeline check, not Batch 2 qualification. Fixed risk, dated costs,
clock coverage, prospective protocol/sample/folds, verified report provenance,
repeatable baseline and explicit human promotion approval remain unchanged.
No real research, orders, MT5 restart, journal reset or activation occurs in
this brainstorming session. Current account scope remains gold demo; real-money
or additional-market execution needs a separate explicit decision.
