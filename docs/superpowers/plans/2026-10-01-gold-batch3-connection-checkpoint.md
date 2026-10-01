# Batch 2 → Batch 3 connection checkpoint

Owner requested usable connection preparation on main. This record covers local
preparation, not permission for inference, candidate evaluation or deployment.

## Latest continuation — bounded offline rehearsal

Subsequent continuation verified the worker plus real pinned request/SSE parser
using fake HTTP in a no-network read-only Docker sandbox. All 133 Python tests
pass, as do actual isolation/timeout/cleanup probes. Existing Vibe server is
unchanged. See the rehearsal plan's latest section: live credential/HTTP
integration and real token-cap compatibility still require review, and unknown
OAuth monetary cost plus Batch 2 qualification continue to block dispatch.

Successful learning CSV run verified OAuth model `gpt-6.1-sol`, medium. The
subsequent [bounded rehearsal](2026-10-01-batch3-bounded-rehearsal.md) implements
a synthetic worker, hash/coverage/repeatability adapter and complete offline
comparison through the existing simulator/evaluator. Actual model requests zero;
qualification remains inconclusive, promotion blocked. Prepared provider guard
now includes token/stream/response/timeout bounds but remains unapplied.
Owner confirmed unknown OAuth monetary cost must block live dispatch. No live
controller or OS sandbox is claimed. Older setup notes below are historical.

## Verified 2026-10-01

Subsequent owner scope: normal AI learning demos after interactive OAuth login
are authorized separately from the bounded gold experiment. See
[local learning guide](../../../ops/trading/VIBE-LEARNING.md). Launcher and login
help verified, source guard repaired after fresh review, model explicitly
selected as `openai-codex/gpt-5.4` from upstream metadata; 128 tests pass.
Login terminal opened without capturing auth output. OAuth file remains absent
at latest check, so model availability and learning replies are still unverified.
Normal learning may make multiple requests; it does not relax gold experiment
bounds or qualify Batch 2. No model request was sent during setup.

- Existing Vibe UI and settings GET return HTTP 200. The listener binds only
  `127.0.0.1:8899`, PID 18048. Upstream v0.1.15 checkout has no source changes.
- Separate OAuth store is absent. Provider selected; model not configured.
  No authentication bytes were read. No model request was made.
- Authenticated `get_gold_status` responded with connected terminal, fresh
  quote (0.644 seconds at that check), 250 history bars and duplicate/no signal.
  This is a spot check, not collector completion or qualification evidence.
- `get_baseline_summary` responded: provisional/offline, unqualified,
  hypothetical costs, 30–31 validation trades, research/promotion blocked.
- Synthetic CLI prompt export passed, with exclusive output, deterministic
  bytes and hashes, zero inference, unreviewed/unqualified, promotion blocked.
  Private evidence: `.batch3-vibe/synthetic-prompt-handoff/`.
- Eight research tests and all 122 trading Python tests passed. Fresh scoped
  review found no material issue. No VPS write, restart or order occurred.

## Connection boundaries

```text
Batch 2 qualified frozen reports
  → verified development-only packet adapter [pending]
  → research-gold.py --packet [implemented offline]
  → private packet.json + prompt.txt + result.json
  → bounded Codex proposal invocation [pending]
  → research-gold.py --response [implemented offline]
  → existing simulator/evaluator [qualification gated]
  → exact-artifact human approval [required; no runtime activation]
```

The dashboard link opens the existing Vibe workspace; it does not synchronize
Batch 2 data or make the general chat loop a bounded experiment controller.
The private app currently has no MCP servers configured. Do not add the baseline
MCP to the proposal agent: that tool exposes validation results. Observation
tools remain separate from model-visible development input.

`gold_experiment.research_input` already extracts the old diagnostic development
summary, but its identity fields/limitations differ from the new strict packet.
It is not a prospective qualified adapter. Do not rename fields and drop the
historical limitations to make that output appear qualified. Raw-report identity,
qualified window and cost/clock provenance must be verified before real export.

## Offline command

From the repository root, using a private ACL-restricted parent directory:

```powershell
python -B ops/trading/research-gold.py --packet <private-development-packet.json> --output <new-private-handoff-directory>
```

Input is bounded to 16 KiB; unknown/nested validation fields, duplicate JSON keys,
changed risk/policy hashes and invalid values reject before output. An existing
output directory is never overwritten. Prompt preparation does not prove packet
provenance or credential clearance. Use synthetic inputs until those boundaries
are verified. Do not paste/send the prompt into Vibe chat while research is gated.

## Configuration still required

### Durable attempt rehearsal — subsequent continuation

`research-gold.py` now has `run_synthetic_attempt(packet, output_dir, request)`
for a trusted fake callback only. It accepts only the strict packet with the
single `synthetic_fixture` limitation; it is not exposed through the CLI or app.
An exclusive directory and fsynced `attempt.json` reserve the attempt before
the callback. Failure/interruption never authorizes reuse of that directory;
failed marker flush prevents callback invocation. Never delete the reservation
to retry. File fsync covers ordinary process interruption, not a certified
host-power-loss/filesystem recovery guarantee or protection from external edits.

Responses must have exactly `response_bytes` and empty `tool_calls`; extra fields,
tool requests and oversized payloads reject. Bounded invalid bytes remain private
for review; canonical parsed fixtures remain unreviewed/unqualified with no
registration or promotion. Exception bodies never enter the saved result.
`request_invocations=1` counts only the callback. `model_requests=null` means
HTTP/inference use is not measured by this helper; a callable is not a sandbox.
Our tests use only local fake callbacks and make zero actual model requests.

Four new checks passed after initial failures: reservation/no retry, exceptions
and interruption/input rejection, marker flush failure, and response/tool bounds.
The complete trading suite passed 126 tests. No provider was connected, no source
patch applied and no OAuth login attempted. Timeout/termination, stream acquisition
bounds, output-token cap, usage/cost, real credential quarantine and OS isolation
are not implemented by this synthetic helper. Do not connect it to Vibe chat.

### Prepared adapter guard — subsequent continuation

`ops/trading/vibe-codex-one-request.patch` adds explicit `max_requests=1` to the
pinned upstream Codex adapter. In that mode it rejects bound tools, makes no
401 refresh/resend, disables redirects and inherited HTTP proxy configuration.
`bind_tools` preserves the mode. Default behavior remains two attempts for
ordinary product use. A future approved controller must select mode 1 directly;
an outer retry setting is not a substitute, and the mode does not constrain
multiple independent adapter invocations or the general chat loop.

The patch is **prepared only**, not applied to the checkout/running server or
shared installation. Its checker verifies the exact original provider SHA-256
`19a23404ae7cdbe404c28b157fd2fc6766f7deec2a0db0423879601bb1fdd4f0`, applies the
patch only in a disposable directory, and executes the actual patched class
with fake HTTP clients/headers/body. It does not import provider auth/config
modules, load credentials or access the network.

```powershell
python -B ops/trading/check-vibe-codex-guard.py --source .batch3-vibe/upstream/agent/src/providers/openai_codex.py
```

Verified one POST each for 200/401/302/429/500, no forced-refresh header call,
tool rejection before POST, strict integer budgets and unchanged default 401
recovery. This is a class-level synthetic check, not full HTTP integration,
login/model availability or a qualified request controller. The full 122-test
trading suite remains green. Do not mark the existing `oauth_401_resend` runtime
blocker resolved: the actual app still uses unchanged upstream source.

Still required before dispatch: durable exclusive attempt record before the
first POST, process deadline/termination, verified output-token/byte limits,
usage/cost accounting, safe exception capture/credential quarantine and OS
isolation. The upstream adapter's body currently does not set the experiment's
2,048 output-token limit; this patch does not claim to enforce that limit.
The general chat workflow remains disconnected from qualified Batch 2 research.

Fresh scoped review found no material defect in the per-invocation inference
POST bound. OAuth header preparation may still refresh a token before that POST;
this is not a one-total-HTTP-request guarantee. Tool rejection covers configured
tools, not historical messages or returned tool calls. The future controller
must supply only the approved prompt and reject any tool-call output.

1. Prepare an isolated, no-tool invocation using the existing provider, with an
   enforced one-inference-POST budget, no retry/fallback, 120/180-second deadlines,
   2,048 output tokens, 16 KiB response bound and an owner-approved cost ceiling.
   Fake transport currently proves that upstream OAuth 401 recovery resends,
   producing two POSTs despite outer retries zero. Configuration alone is
   insufficient; keep actual dispatch disabled until the bound is enforceable.
2. Verify filesystem/tool/network isolation and credential quarantine. Separate
   USERPROFILE is configuration isolation, not an OS sandbox; shell-off does not
   by itself prove all product file/code/backtest tools are unavailable.
3. Perform interactive Vibe-owned Codex OAuth login locally, then verify and pin
   an available model without research dispatch. Do not use a shared installation
   login command: it would target a different home. Do not copy Codex auth files.
4. Complete the qualified Batch 2 prospective input/report adapter and immutable
   repeatable baseline. Dated costs/clock, 60 observed validation days, three flat
   folds ≥20 days and 100 closed trades per strategy remain unchanged gates.
5. Dashboard deployment/live API verification is separate from this local app
   setup. The prepared new page/Worker/sidecar changes are not deployed.

Smoke finish capture after 2026-10-01 17:15 UTC (October 2 00:15 Bangkok) is a
pipeline evidence milestone. No completion is claimed here, and it supplies none
of the missing strategy qualification gates. Preserve collector/artifacts.

Provider workflow reference: upstream
[Vibe-Trading README](https://github.com/HKUDS/Vibe-Trading/blob/main/README.md),
checked through Context7. Local pinned source and fake transport determine actual
compatibility. No new agent framework or trading engine was introduced.
