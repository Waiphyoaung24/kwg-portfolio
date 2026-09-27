# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

## 5. Website Design — DESIGN.md Is Law

`DESIGN.md` at the repo root is the single source of visual truth. It records the
project's design system: an interpretation of x.ai's web language. `PRODUCT.md`
records durable product truth. Read both before writing or changing any markup,
style, or component.

### Rules

- **Read `DESIGN.md` first.** Tokens, type ladder, component specs, and the
  Do's and Don'ts list are binding. When a request conflicts with it, say so
  and ask rather than silently splitting the difference.
- **Use the tokens, never raw values.** Colors, spacing, radii, type sizes and
  easings all live in `src/styles/_vars.scss`. A hex code or a px value in a
  component is a bug unless the file comment explains why.
- **Reuse the primitives.** `.pill-btn`, `.pill-btn--filled`, `.card`, `.label`
  and `.micro` live in `src/styles/`. Do not hand-roll a button.
- **The hard rules from `DESIGN.md`:** near-black canvas only, no light mode.
  Weight 400 everywhere; the system never bolds. Every interactive element is a
  pill. Outline pills by default, one filled white pill for the primary action
  per view. Hairline borders carry elevation; there are no shadows. Negative
  tracking on display sizes. Mono, uppercase, positively tracked for labels.
  The sunset/dusk accent colors are for illustration only, never chrome.
- **Accessibility floor is WCAG 2.2 AA**, per `PRODUCT.md`. The `--c-mute`
  neutral is metadata only; it does not meet the body-text ratio.

### Design work

For substantive design work — building a new surface, redesigning an existing
one, auditing, or polishing — use the `impeccable` skill (`/impeccable <command>`).
It reads `PRODUCT.md` and `DESIGN.md` as its context automatically. Do not
freestyle a visual direction, and do not import an aesthetic from another
design system.

### Exhibited work is exempt

Content on display is not site chrome and keeps its own styling:
`src/catalog/kage/` and any future catalog demo. The frame around an exhibit
follows the design system; the exhibit itself does not.

## Trading setup handoff — 2026-09-27

### Scope and saved work

- Continue `/vault/trading` with **gold only: `XAUUSD-VIP`**, demo account only.
- Setup source, checks, and operating instructions are in `ops/trading/README.md`.
- Commits `0cc7581` (setup) and `12f7ea3` (handoff) were pushed to `main`.
- Gold signal-only implementation plan:
  `docs/superpowers/plans/2026-09-27-gold-signal-only.md`. Local data guard,
  EMA/ATR calculation and SQLite observer are implemented and tested. Gold
  market freshness and supervised VPS observation remain pending while closed.
  Demo execution remains a separate follow-on.
- The VPS was deployed directly. A Git commit/push does not update its running
  Compose project. Preserve unrelated repository changes and existing VPS apps.
- The signal-only observer, private status sidecar, Cloudflare Tunnel, Access
  policies, read-only API Worker, and `/vault/trading` page route are deployed.
  The signed-in page showed gold blocked with no signal on a stale quote.
  Algo Trading remains off; no order execution is deployed.

### Current VPS setup

- Host: `187.52.117.116`, Ubuntu 24.04.4, 4 CPUs, approximately 15 GiB RAM.
- Dokploy: `https://dokploy.castranova.cloud/dashboard/settings/server`.
  Its authenticated server terminal works after the owner authorized Dokploy's
  existing public SSH key. Do not extract private keys or broker credentials.
- Remote project: `/opt/kwg-mt5-qualification`; container
  `kwg-mt5-desktop`; image `kwg-mt5-desktop:qualification`.
- MT5 runs under Wine 9 with Windows Python 3.12.10, MetaTrader5 5.0.6180,
  NumPy 1.26.4. This is a qualification environment; a maintained runtime still
  needs qualification. NumPy 2.5.3 failed under this Wine version.
- Dedicated Compose network and persistent `mt5-home` volume; UID 10001,
  1 CPU/2 GiB memory cap, capabilities dropped. `/tmp` is tmpfs to prevent stale
  X display locks after restart. Preserve the volume containing terminal state.
- Desktop port is **VPS loopback only** (`127.0.0.1:6081`). Never expose noVNC
  publicly. Closing the local SSH tunnel disconnects viewing, not the VPS app.

To reconnect tomorrow, run locally in PowerShell and keep the window open:

```powershell
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:6081:127.0.0.1:6081 root@187.52.117.116
```

Enter the SSH passphrase locally, then open
`http://127.0.0.1:6081/vnc.html?autoconnect=1&resize=scale`.
The owner's SSH client prompts for the existing local key
`C:\Users\wai19\.ssh\id_ed25519`. This prompt requests the key's passphrase,
not the VPS root password or MT5 password. Enter it only in PowerShell; input
is not echoed. After successful authentication, a blank waiting window is
normal because `ssh -N` runs only the tunnel. The passphrase prompt alone does
not confirm a successful connection. Never copy the private key or passphrase
into the repository or chat.
Broker credentials stay in MT5's volume, never in chat, Git, shell commands,
images, or logs. Local Vibe-Trading credentials remain outside the repo in
the owner's `.vibe-trading/mt5.json`; do not display its contents.

### Verified results and unresolved issues

- SDK attached to the expected **VTMarkets-Demo** account, verified demo mode
  and Algo Trading off, and returned quotes plus 250 completed M15 candles for
  `XAUUSD-VIP` and `BTCUSD`. Repeated successfully after a container restart.
- Bitcoin was part of earlier diagnostics only; exclude it from the first
  strategy. The current diagnostic script checks gold only.
- Newly selected symbols initially returned empty quotes; checks succeeded
  after subscription synchronization. Do not confuse this with account failure.
- **Freshness is unresolved:** gold's last quote was about 22 hours old;
  Bitcoin timestamps were about 3 hours ahead of the VPS clock. Investigate
  broker timestamp semantics and clock synchronization. Do not silently subtract
  a guessed offset or accept negative quote ages as fresh.
- Run `verify-demo.py` as documented in the README using the owner's expected
  demo account number; it takes no password and calls no order functions.
- The 2026-09-27 gold-only signal image is deployed. Its account/Algo guard
  passed; both the diagnostic and one-shot observer blocked on the stale
  weekend gold tick. The signal-only observer now runs continuously. Live freshness,
  M15 transitions, and restart persistence still require an open session.
- Account-guard test, shell syntax, Compose validation, and whitespace checks
  passed. Restart recovery and saved demo login were verified on the VPS.
- Local Vibe-Trading 0.1.15 `mt5-paper-sdk` checks previously passed. Its managed
  live runner does not support the MT5 broker SDK profile; its MT5 order method
  lacks SL/TP arguments. Do not assume switching profiles produces a safe bot.

### Resume sequence and strategy baseline

1. Qualify fresh **gold** quotes when the market is available, including clock
   handling and subscription readiness. Keep order execution disabled.
2. Review the implemented **signal-only** EMA20/EMA50 crossover observations
   across live completed M15 candles. The 250-bar SMA-seeded EMA and Wilder
   ATR14 logic passed offline tests; live transitions remain unqualified.
3. Planned demo execution limits: stop 2 ATR and take-profit 3 ATR, broker-held
   protection accepted with entry; risk 0.1% current equity using broker profit
   calculation, floor volume step, skip if minimum volume exceeds risk budget.
   One strategy-owned gold position, no pyramiding or martingale; opposite cross
   closes by ticket with no same-candle reversal. Never modify unrelated trades.
4. Persist UTC day-start equity; pause new entries at 1% daily equity loss
   (realized plus floating). This is not a guaranteed loss cap. Require valid
   bid/ask, spread at most 10% ATR, qualified quote age at most 30 seconds, market
   availability, and pinned demo identity. Persist candle decisions/order intents
   and reconcile uncertain submissions before retry; never replay old entries.
5. Review the protected `/vault/trading` status while qualifying fresh gold
   quotes and completed M15 transitions. The public site continues through
   the NexApex tunnel; only `/vault/trading` and `/api/trading/status` route to
   the Worker and CastraNova status origin. Review signal-only results and risk
   checks before any demo-order work.

The user previously requested brainstorming, Ponytail, and Context7. Continue
with minimal changes and current documentation. No overnight monitoring or
scheduled work has been configured.

### Selected AI research direction — 2026-09-28

- Owner selected **existing MT5 runner + separate Vibe-Trading researcher**.
- The current design and ordered acceptance gates are in
  `docs/superpowers/plans/2026-09-28-gold-ai-researcher.md` (also recorded in the
  Git-ignored `task_plan.md`). It supersedes earlier trading discovery notes;
  gold-only demo scope continues.
- Next: explicit health evidence and open-session data qualification, then a
  reproducible baseline evaluator. Research and demo-order execution are not
  implemented. Owner intends to use their existing Claude/Worker MCP connection;
  verify its supported invocation path before research integration. No separate
  paid provider is requested. Never request or commit the token.
- AI proposes bounded candidates; it cannot modify risk rules, the evaluator,
  broker credentials, or promote itself. Initial promotion requires owner review.

### Explicit health deployment — 2026-09-28 Bangkok

- Commit `f0e00d3` is pushed to main and deployed to the VPS and Worker.
  Worker version: `1b87a3d8-9ea8-4795-9a2f-032b8cb1cb22`; existing variables,
  secrets and protected routes preserved. API unauthenticated check returned
  302; direct status origin returned 403.
- Updated diagnostic keeps raw tick epochs and signed quote age on failure.
  Dashboard separates delivery, heartbeat, MT5 checks, quote/history and
  strategy readiness; it auto-refreshes and expires old observations.
- VPS diagnostic at 2026-09-27 18:40:48 UTC: demo connected, 250 bars fetched,
  gold tick epoch `1790380619`, milliseconds `1790380619894`, measured age
  `153828.805` seconds. This failure is stale, not future-dated. Raw epoch
  renders as 2026-09-25 23:56:59 UTC; broker timestamp semantics during an
  open session still require qualification. No guessed timezone adjustment.
- Both containers were recreated successfully preserving MT5 home/state.
  Runtime update is a small image layer over the existing qualification image;
  tag `kwg-mt5-desktop:before-health-f0e00d3` and files under remote
  `/opt/kwg-mt5-qualification/before-health-f0e00d3` preserve rollback state.
- 14 Python tests, 5 Worker tests, frontend state checks, Astro check/build,
  desktop/mobile preview and signed-in live page checks passed. Fresh gold
  ticks across two M15 transitions remain pending. Order execution stays off.
