# Batch 3 Vibe Application Initialization Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare a separate existing Vibe-Trading application with Codex OAuth, without inference, research or changes to Batch 2.

**Architecture:** Reuse the product locally first. Keep application state separate from the existing installation and broker profile; retain our parser and evaluator as the proposal/qualification boundary. No custom UI or provider framework.

**Tech Stack:** Existing Vibe-Trading 0.1.15 inspection source, Windows PowerShell, existing Python tests; select a clean product runtime only after isolation checks.

**Spec:** [Selected product/provider specification](../specs/2026-10-01-gold-batch3-vibe-integration.md).

## Global Constraints

- Owner authorized starting initialization on main; this supersedes the earlier preparation note prohibiting installation solely because product selection was not launch authorization. It does not authorize inference or research.
- Local-first initialization is the reversible default. Do not install the app on the VPS or touch its collector.
- Provider `openai-codex`, ChatGPT OAuth, no `OPENAI_API_KEY`; interactive login stays local and no auth bytes enter chat/Git.
- One model request, zero retries/fallbacks/tool calls remain the eventual proposal budget. No model request during initialization.
- No real gold imports, candidate generation/evaluation/registration, orders, risk changes, MT5 restart, journal reset or promotion.
- Preserve the one-day smoke collector and artifacts. Finish capture after October 2, 00:15 Bangkok; that is not Batch 2 qualification.

## Review Focus

- Runtime-root override does not isolate every settings path: verify settings writes resolve inside the new workspace.
- Startup migration can move old installed histories: use a clean runtime, never start the shared installation.
- OAuth 401 recovery resends inference: fake transport must count actual POST attempts before any research permission.
- Shell/scheduler/channel defaults may be inherited: explicitly disable them and test effective configuration.
- A CLI install may omit the UI: require the existing product's built frontend, not a custom replacement.

## Task 1: Initialize state and verify source paths

**Files:** `.gitignore`, private `.batch3-vibe/.env`, `.batch3-vibe/agent.json`, `.batch3-vibe/initialization.json`; this plan and `ops/trading/HANDOFF.md`.

**Interfaces:** private state only; initialization record has package version, provider and boolean check outcomes, never credentials. No launch script or provider transport is introduced.

- [x] Create the exclusive workspace with owner/System access and add its Git ignore rule before writing files. Refuse to overwrite any existing workspace.
- [x] Write provider selection and explicit shell/scheduler/channel-off settings, and an empty MCP/channel config. Leave model unset until availability is verified.
- [x] Run only the stdlib path-helper source with a synthetic root; assert runtime/session/run/upload paths remain beneath it. Do not import server, provider or migration modules.
- [x] Verify JSON parsing, Git exclusion, absence of OAuth/broker artifacts and existing synthetic research tests. Record configuration prepared; application not running.
- [x] Save source-inspection blockers and sanitized verification results. Do not claim full isolation from path-helper checks alone.

Task 1 result: `.batch3-vibe/` initialized, Git exclusion confirmed for all
three files, no auth directory or broker profile, seven existing research tests
passed. Source-only installed path-helper assertions passed for config, sessions,
runs, uploads and swarm paths; no provider/server was imported. ACL grants the
owner, SYSTEM and the executing Codex sandbox account; broader inherited access
is removed. Initial path check failed because the workspace initially granted
only the sandbox account and SYSTEM; owner access was added and the check passed.
Full application isolation remains unverified. No login, model call, research,
app server, installation upgrade or VPS operation occurred.

## Task 2: Qualify a clean application runtime

**Files:** isolated upstream application checkout/runtime under `.batch3-vibe/`; update this record only. No changes to installed product source.

**Interfaces:** produces a verified product version/source identity and local startup command. Consumes the unchanged proposal budget from the spec.

- [x] Select and pin an upstream release with existing built frontend. Verify UI artifact availability and source identity before installation; never upgrade the shared tool.
- [x] Resolve home-based settings/dotenv paths using the product's supported configuration or a separate OS/container home. Verify no broker/auth/history import or migration from existing directories.
- [ ] Test startup with synthetic fixtures and network inference denied: no scheduled/channel work, no shell capability and no provider dispatch. Verify loopback binding explicitly.
- [ ] Verify synthetic data import and structured proposal export without invoking a model. Reuse our parser; app backtests remain exploratory.
- [x] Verify retry/401 bounds using fake transport. If the product cannot enforce one request, report the mismatch for a separate owner budget decision; no implicit relaxation.
- [ ] Start only the qualified local UI, then perform interactive Codex OAuth login locally. Login is not a research run; record status only and never callback/token values.

### Task 2 checkpoint — local product UI running; inference unqualified

Owner's “continue” authorized this next preparation step. Separate upstream
checkout pinned to v0.1.15, commit `cc54832cb50de29d14bb10097b18e08f0a843650`.
Frontend lockfile installed with lifecycle scripts disabled; upstream TypeScript
and Vite production builds passed. A verification rebuild used bundled Node
24.19.0 to satisfy the jsdom test dependency's engine requirement. Upstream
chunk-size warnings remain; no product source or dependency version was changed.

The clean source reuses dependencies from the existing tool's Python runtime.
It does not upgrade that tool. The child environment is cleared, retaining only
Windows runtime/path/temp variables and assigning a separate USERPROFILE,
APPDATA/LOCALAPPDATA and VIBE_TRADING_HOME under ignored `.batch3-vibe/profile`.
This is process configuration isolation, not an OS security sandbox. A stdlib
checker proves the actual settings, dotenv candidates, migration root and Codex
credential path point inside this workspace; it confirms no inherited provider,
MCP or broker variables, model unset and scheduler/shell/channels off.

Native local app now serves the upstream built UI at `http://127.0.0.1:8899/`.
HTML and read-only settings API returned 200; UI reports Codex OAuth and unknown
model. Startup performed the product's public data-service preflight probes
(yfinance available; OKX DNS check failed); these are not gold qualification.
No actual model request, OAuth login, broker connection or research occurred.
The first direct `api_server.py` invocation failed because route registration
requires an imported module. The local seven-line launcher imports its existing
`serve_main` entry point instead; upstream source remains unchanged.

Synthetic CSV upload preserved exact bytes under the isolated upload directory.
The product's CSV reader loaded two synthetic OHLCV rows. Existing offline
proposal replay accepted a manually supplied synthetic fixture and reported
zero model requests, no registration, unreviewed/unqualified, promotion blocked.
This checks upload/reader/parser boundaries; it does not prove real data import,
model-produced structured export or a full research workflow. Those remain gated.

Fake Codex transport observed exactly two POST attempts on 401 then 200, despite
outer `MAX_RETRIES=0`. One-request compatibility is false; keep real dispatch
blocked. Full agent-loop budget/controller isolation, model pin and OAuth login
remain pending. Do not treat a running UI as a qualified inference runtime.
No app authentication artifact or broker profile was copied, and no histories
were migrated from the shared installation. The existing collector/VPS is untouched.

Private source/build/check artifacts and process IDs are in `.batch3-vibe/`.
Gold operations now links to this local app explicitly as a separate workspace;
the link makes no authentication, qualification or live-connectivity claim.

## Inspection evidence and remaining gates

Subsequent connection preparation: local listener/UI/settings and both gold MCP
tools verified read-only; strict packet-to-prompt CLI export implemented with
synthetic inputs. Eight research checks and all 122 trading Python tests pass;
fresh scoped review found no material issue. See
[connection checkpoint](2026-10-01-gold-batch3-connection-checkpoint.md).
The prospective Batch 2 adapter and bounded proposal invocation are still
missing; the observation MCP's validation results must remain outside proposal
input. No OAuth login, inference or real data import was performed.

Context7 `/hkuds/vibe-trading` documents `vibe-trading serve`, Codex OAuth and scheduler opt-in. Installed source is authoritative for this initialization: CLI/server bind defaults are `127.0.0.1`; `src.config.paths` respects `VIBE_TRADING_HOME`; `src.api.helpers.ENV_PATH` still uses `Path.home()/.vibe-trading/.env`; server startup calls `migrate_legacy_state()`; the expected installed `frontend/dist/index.html` is absent. Therefore a shared-install server launch is not the next safe step.

Primary reference: [Vibe-Trading README](https://github.com/HKUDS/Vibe-Trading/blob/main/README.md). No arbitrary generated code execution or app installation is needed to prepare Task 1.

Batch 2 remains blocked on dated costs/clock, prospective evidence, qualified sample/folds, verified report provenance and reproducible fixed baseline. Application initialization can proceed independently; real research cannot.
