# Gold Operations Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Build `/vault/trading-bot` as a read-only gold demo operations workspace, without enabling research or autonomous orders.

**Architecture:** Reuse the protected Worker/status-sidecar path and existing status/one-shot execution formatters. Add an Astro page and standalone HTML packaging, preserving the supervised trading page. Research/qualification sections show explicitly dated preparation information until a verified live report API exists.

**Tech Stack:** Astro, existing SCSS tokens/primitives, browser fetch, stdlib Python status service, existing Worker tests and installed esbuild for standalone modules.

**Spec:** [Autonomous gold workspace](../specs/2026-10-01-autonomous-gold-workspace-brainstorm.md); owner accepted implementation of the recommended gold dashboard.

## Global Constraints

- Work on main and preserve unrelated changes; no push/deployment or VPS changes.
- Gold demo only; keep fixed risk and all Batch 2 qualification/promotion gates.
- No order, arming, strategy promotion, model dispatch or research action from this page.
- No made-up prices/charts/performance, live qualification claim or private credential exposure.
- Reuse DESIGN.md tokens, weight 400, pill controls, hairline borders and accessible mobile layout.
- Preserve the smoke collector and its artifacts.

## Review Focus

- New page requests must require the same exact Access identity as the existing page.
- New path must map only to its own fixed sidecar HTML; reject unknown paths and POST.
- Fetch failure or expired status must clear current signal/execution claims.
- One-shot trade results must not appear as autonomous portfolio or strategy returns.
- Static preparation notes must not masquerade as live research/qualification state.

### Task 1: Protected route and standalone packaging

**Files:** `ops/trading/worker/src/index.js`, `ops/trading/worker/test.mjs`, `ops/trading/status_server.py`, `ops/trading/test_status_server.py`, `ops/trading/build-status-page.mjs`, `ops/trading/compose.yml`.

**Interfaces:** GET `/vault/trading-bot` and trailing slash -> `/vault/trading-bot` at status origin -> `/app/trading-bot.html`. Existing API/actions unchanged.

- [x] Add Worker regression: no/mismatched identity yields 403 with zero origin calls; correct identity maps exact path and no-store HTML; POST yields 404.
- [x] Add sidecar integration check: correct dashboard bytes, unknown route 404 and no-cache headers. Run tests and observe missing-route failures.
- [x] Extend fixed page routes, mount new HTML read-only and package both Astro pages. Use installed esbuild to inline extracted module dependencies when Astro shares chunks.
- [x] Run Worker/status tests and inspect standalone output; expect passing tests and no external script/style assets.

### Task 2: Operations surface and verification

**Files:** `src/pages/vault/trading-bot.astro`, `src/pages/vault/trading.astro` (navigation only), generated `ops/trading/trading-bot.html`, `ops/trading/trading.html`; handoff/README and this plan.

**Interfaces:** read-only GET `/api/trading/status`; `statusFields(data, now)` and `executionFields(data.execution, now)` from existing formatter. No new API contract.

- [x] Build desktop two-column/mobile single-column workspace with operating state, feed, signal, last supervised result, fixed-risk rules and dated workflow/gate notes. Keep runner unavailable and research disconnected explicit.
- [x] Add refresh/sign-in handling, bounded fetch, expired-state rendering and safe text-only updates. No browser-stored credentials or mutation endpoint.
- [x] Run Astro check/build, standalone packaging, Worker tests and full trading Python suite.
- [x] Inspect desktop/mobile and synthetic fresh/stale/error states in browser; verify keyboard controls and no horizontal overflow. Fix findings in one batch.
- [x] Obtain one fresh code review, address material findings and save verification/handoff. Do not deploy or commit unrelated changes.
