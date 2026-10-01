# Batch 3 Vibe-Trading Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. This is a preparation deliverable, not authorization to execute the plan.

## Implementation checkpoint — owner requested start

Latest preparation checkpoint: `validate_packet(packet: dict) -> dict` and
`build_prompt(packet: dict) -> str` are implemented in `research-gold.py`.
They enforce the spec's nested field shapes, fixed risk/policy hashes, finite
numbers and limitation codes; prompt JSON is canonical and undefined metrics
stay null. Unknown fields and unsupported values raise a safe generic error
before rendering. Input remains unreviewed; source hashes are not yet verified
against raw reports. Seven research tests and all 120 trading tests passed.
Fresh review found fixed-risk drift and oversized integer gaps; regression
checks failed first and then passed after fixes, with no remaining scoped finding.

Owner's subsequent “start” is interpreted as authorization for preparation
implementation on main, within the original prohibition on candidate research.
The offline portion of Task 2 is implemented in `research-gold.py`:
`parse_proposal(raw: bytes) -> dict` and
`replay_response(raw: bytes, output_dir: Path) -> dict`. Initial synthetic
tests failed before implementation and then passed. Final verification passed
four new checks and the full 117-test trading Python suite.

The CLI takes `--response` and `--output` and only reads already-saved bytes.
It preserves a bounded response, emits a canonical proposal if valid and a
safe result summary, refuses any existing output directory, and reports zero
model requests, no candidate registration and promotion blocked. Oversized
responses produce a failure summary without copying the payload. Use a private
parent directory; Windows permissions inherit its ACL rather than a POSIX mode.
Every result is explicitly unreviewed and unqualified. This parser cannot
identify arbitrary credentials in freeform text and provides no credential
clearance; credential quarantine/review is deferred to the controller boundary.
Until that boundary is implemented, use synthetic responses only. Parsed
`proposal.json` is a decoding artifact, not an approved or registered candidate.

Ruling: split Task 2 at the unverified provider dependency. Packet validation,
prompt generation, model dispatch/deadlines, isolation and usage/cost accounting
remain pending. No placeholder transport or launch command was added; Task 2
is partial. Tasks 3/4 remain gated. Synthetic fixtures choose a lookback solely
to exercise parsing; they are not registered research candidates.

The subsequent owner request to go next completed packet validation and prompt
generation from that pending list. Dispatch, isolation, credential clearance,
usage/cost accounting and qualified report provenance are still pending.

Task 1 source inspection identified
`src.providers.llm.build_llm(*, model_name=None, callbacks=None)` in installed
0.1.15. It loads discovered dotenv files, mutates provider environment and can
select provider-specific adapters and fallback behavior. It was not imported
or invoked; the owner's actual model route, response/usage interface and
one-request guarantee remain unverified. Environment presence alone is not a
complete route check.

Frozen dependency restoration completed with lifecycle scripts disabled and
package/lockfile unchanged. The four MCP tests passed with access to the pnpm
store; the sandbox's package-store permissions caused the earlier module-load
failure. No MCP source change or deployment was needed.

**Goal:** Produce one reproducible, human-reviewed comparison of a bounded structured Vibe-Trading proposal against the fixed gold baseline.

**Architecture:** Reuse the existing Vibe-Trading app as a separate isolated research workspace, as selected by the owner on 2026-10-01. Reuse our candidate schema, parser/replay, simulator and approved evaluator. Add only the file/API boundary needed after synthetic product compatibility and enforceable request limits are verified; consume the separately verified Batch 2 prospective contract and raw-report adapter. Keep the research MCP unchanged. Do not build another research application.

**Tech Stack:** Existing Vibe-Trading application, Python standard-library boundary helpers and existing Node MCP tests. Installed 0.1.15 is inspection evidence, not a deployment pin. Product version and dependencies must be assessed before adoption; no automatic upgrade or installation is authorized here.

**Next preparation milestone:** A synthetic product compatibility record covering
development-data import, structured response export, isolated configuration,
built-in and MCP tool permissions, background jobs, provider route and actual
request accounting. No model request is needed for this milestone. Retain the
one-request budget; if the app cannot enforce it, stop at the documented mismatch
instead of silently enabling its general agent loop. Task 1/2 transport details
below are provisional until this product boundary is verified. Reuse existing
parser/prompt checks; do not implement a competing provider or agent framework.

**Spec:** [Batch 3 specification](../specs/2026-10-01-gold-batch3-vibe-integration.md).

**Selected provider:** OpenAI Codex via ChatGPT OAuth, using
`LANGCHAIN_PROVIDER=openai-codex` and `vibe-trading provider login openai-codex`.
This supersedes the earlier intended Claude/Worker route. Installed 0.1.15
metadata/source and upstream README confirm provider support; login and actual
connectivity remain unverified. No `OPENAI_API_KEY` is required for this route.
Keep OAuth storage private and isolated from broker configuration; never reuse
the research-MCP token. Verify model availability instead of accepting a default.
Synthetic checks must exercise the adapter's built-in 401 refresh/resend, which
currently conflicts with our one-request/no-retry contract. No live probe or
implicit budget relaxation is authorized by this provider selection.

## Global Constraints

- Work on `main`; preserve unrelated local changes.
- Preparation only now: no real proposal, candidate registration/evaluation, order, MT5 restart, journal reset or promotion.
- Batch 2 remains `prepared_but_blocked`; keep `simulator_provenance_unverified` until separately verified raw-report provenance permits removal.
- `XAUUSD-VIP`, completed M15, EMA20/EMA50/ATR14; risk 0.1%, stop 2 ATR, target 3 ATR, daily entry pause 1%, one position and no same-bar reversal remain unchanged.
- Policy canonical hash remains `39eb8759133ac1ca50308e0aa053c761a53b24e94be9ebc3f8c13ff73413873d`.
- Strict proposal: exactly `kind=ema20_slope_filter`, integer `lookback_bars` 2..5 and nonblank `hypothesis` at most 2,000 characters.
- One model request, zero retries/fallbacks/tool calls, 120-second request deadline, 180-second controller deadline, 2,048 output tokens and 16 KiB response maximum; owner-approved cost ceiling required before launch.
- No generated code, default broker profile, broker credential access or mutation tool access.
- Private outputs are exclusive; failed attempts remain recorded. No tokens or raw private datasets enter Git.
- Retain the running smoke-test directory and collector. Finish capture is after 2026-10-01 17:15 UTC; smoke success is not qualification.

## Review Focus

1. Provider SDK retries/fallbacks can exceed one request: fake transport counts actual requests, including failures (Task 2).
2. A secret or validation/holdout field can enter a prompt through inherited configuration: strict input allowlist and isolated home tests (Task 2).
3. Old hypothetical registration can appear compatible with a new cost profile: require prospective contract identity and reject legacy qualification (Task 3).
4. Crash after dispatch can cause a second proposal: exclusive attempt marker precedes dispatch; resume only from stored response (Task 2).
5. A passing report or stale approval can activate a strategy: report-only outputs and hash-bound approval checks, with no activation interface (Task 4).

## File map and dependency boundary

| File | Responsibility |
| --- | --- |
| This plan and companion spec | Preparation evidence, chosen contract and remaining gates |
| `ops/trading/research-gold.py` (new, later) | One bounded request, strict parsing, durable private artifacts; no agent loop |
| `ops/trading/test_research_gold.py` (new, later) | Synthetic transport, limits, failure/replay and redaction checks |
| `ops/trading/gold_experiment.py` | Reuse validator/filter/digest; prospective support is a Batch 2 dependency |
| `ops/trading/compare-gold.py` | Reuse exclusive writes; later final report assembly with verified prospective identities |
| `ops/trading/test_gold_experiment.py` | Regression protection for strict schema and unchanged filter behavior |
| `ops/trading/research-mcp/README.md` | Add only verified local test recovery notes if needed |

Batch 2 owns the separate real-report adapter specification, dated UTC/cost
mapping and prospective manifest/registration support in `gold_experiment.py`,
`simulate-gold.py`, `compare-gold.py` and `evaluate-gold.py`. Do not implement
an improvised second adapter inside this integration. The current candidate CLI
rejects dated profiles/windows with its legacy manifest; that must be resolved
and tested under the Batch 2 contract before Task 3. Keep this dependency
explicit rather than inventing a runnable qualified command today.

### Task 1: Verify the pinned runtime without research

**Files:** update this plan's evidence section and, only if useful,
`ops/trading/research-mcp/README.md`. No production code change.

**Interfaces:** consumes installed package metadata/source and the owner's
existing model route; produces a private route record with provider/model,
endpoint protocol, auth reference (never value), package/source hashes,
supported request bounds and artifact/import results.

- [ ] On a separately authorized implementation turn, restore existing MCP
  dependencies with `pnpm install --frozen-lockfile` in `ops/trading/research-mcp`;
  run `pnpm test`. Expect four tests passing; stop and record lock/install
  mismatch rather than changing versions to force success.
- [ ] Assess installed 0.1.15 and the chosen upstream app release, then pin the
  verified isolated runtime and record distribution and dependency hashes.
  Inspect its application startup and provider construction before import:
  prove no automatic connection, global-home mutation or broker access.
- [ ] Identify the owner's intended inference route from allowlisted configuration.
  Record its exact installed callable and response/usage shape here before
  implementing the transport. Do not guess from current-main Context7 docs.
- [ ] Prove with fake transport and synthetic development data that the pinned
  callable accepts the limits, writes private artifacts and makes no background
  requests. No market data import or live inference is needed for this check.
- [ ] If no usable route exists, record `model_route_unverified`; do not buy a
  provider, reuse the MCP bearer token or launch the general Vibe agent.
- [ ] Review and commit only the verified documentation changes.

**Completion:** runtime contract identified or a concrete blocking result saved.
A live inference probe is deferred to Task 3 and needs a frozen cost ceiling.

### Task 2: Prepare one bounded request controller with synthetic tests

**Files:** create `ops/trading/research-gold.py` and
`ops/trading/test_research_gold.py`. Reuse `validate_candidate` and `digest`.

**Interfaces:**
- `parse_proposal(raw: bytes) -> dict`: strict UTF-8 JSON object; reject duplicate
  keys, nonfinite values, oversized response and anything outside existing schema.
- `run_proposal(packet: dict, output_dir: Path, request: Callable[[dict], dict]) -> dict`:
  consumes an approved development-only packet; request returns
  `{response_bytes: bytes, model: str, usage: dict, cost: dict}`. Production
  callable is the single verified pinned-runtime adapter from Task 1.
- Produces exclusive `attempt.json`, `response.json`, `proposal.json` and
  `result.json` in a new private directory. Result references byte hashes,
  timestamps and safe error codes; never dumps environment, request headers or
  provider exception bodies. No registration or evaluation occurs here.

- [ ] Write failing `test_strict_response`: accept the exact three-key schema;
  reject bool/1/6 lookbacks, unknown risk fields, duplicate JSON keys, blank or
  2,001-character hypothesis, NaN, invalid UTF-8 and 16,385-byte responses.
- [ ] Write failing `test_one_attempt`: fake transport call count equals one on
  success/error; second invocation with the same directory makes zero calls;
  interrupted dispatch cannot be retried. Invalid response remains a failed attempt.
- [ ] Write failing `test_packet_boundary`: reject validation, holdout, credential
  or unknown fields before transport; assert generated prompt only contains
  approved development summary, schema and immutable identifiers. Isolated
  environment/home must exclude default broker config and inherited tools.
  Use the exact packet fields in the spec; reject unknown nested fields and
  nonfinite metrics, preserve explicit nulls and reject prose/code-fenced output.
- [ ] Write failing `test_bounds_and_replay`: fake slow/oversized/tool-call responses
  fail closed; request settings enforce limits; stored response reconstructs the
  same proposal hash offline. Transport spies cover retry and fallback paths.
- [ ] Run `python -B -m unittest discover -s ops/trading -p test_research_gold.py`;
  expect failure because controller is absent.
- [ ] Implement those interfaces using stdlib JSON, hashing, exclusive writes
  and a bounded process for the pinned provider callable. Create the attempt
  marker before dispatch and terminal result separately so a crash never
  authorizes another call. No full agent loop, shell tools or provider abstraction.
- [ ] Run the same tests; expect all pass with fake transport and no network.
  Run existing experiment/evaluator suites and verify no tracked policy/risk diff.
- [ ] Review and commit controller plus its synthetic tests only.

### Task 3: Gate and run the single experiment — blocked now

**Files:** private evidence only after authorization; this plan receives a
sanitized outcome. Batch 2 code/interface changes require its separate review.

**Interfaces:** consumes signed Batch 2 readiness, verified prospective
manifest/registration and raw-report adapter, fixed baseline artifacts,
Task 2 controller, owner-approved model route/cost ceiling and run authorization.
Produces one immutable registered proposal and repeated simulator outputs.

- [ ] Require dated costs/clock evidence, frozen future protocol and covered
  baseline sample/folds under the unchanged policy. Require verified adapter
  and prospective candidate CLI support; keep real launch blocked otherwise.
  Save the spec's launch-readiness record with source artifact paths/hashes and
  individual gate outcomes. Candidate sample sufficiency is evaluated later.
- [ ] Add/verify regression assertions under the Batch 2 contract: legacy
  hypothetical manifest cannot qualify; cost/window/risk/source/policy mismatch,
  late registration, overlapping folds and unsupported UTC conversion cannot pass.
  A synthetic numeric gate pass must not bypass raw-report provenance.
- [ ] Freeze private experiment directory, all input hashes, prompt, actual
  provider/model/version, exact route and owner-approved cost ceiling. Record
  all previous validation exposure and keep both holdouts out of research input.
- [ ] With explicit run authorization, make one separately recorded bounded
  synthetic route probe before research; verify usage/cost, deadlines and no tools.
  If probe fails, stop. The proposal itself still has a one-request budget;
  the probe is disclosed separately in total usage/cost accounting.
- [ ] Run fixed baseline twice through the qualified Batch 2 path to distinct
  exclusive outputs. Require identical canonical bytes and provenance. Hash
  comparison commands operate only on approved private paths, never raw content.
- [ ] Invoke Task 2 once on the development packet. Preserve failures. Validate
  and register the returned proposal before candidate execution/results access.
  Do not manually repair it or select a different lookback.
- [ ] Run that candidate twice under identical frozen conditions, with network
  disabled. Verify equal report bytes and shared baseline identities; no second
  model call. Preserve mismatches as inconclusive evidence.
- [ ] Derive gate inputs from verified raw reports and evaluate with the unchanged
  policy. Candidate insufficient trades/days or missing evidence is inconclusive;
  do not extend/tune windows after seeing results to manufacture a pass.

**Completion:** reproducible acceptance/rejection/inconclusive evidence for one
attempt. It does not promote a strategy or enable observation automatically.

### Task 4: Assemble the comparison and human approval packet

**Files:** later modify `ops/trading/compare-gold.py` and its existing tests in
`ops/trading/test_gold_experiment.py`; save private final report and sanitized
summary under a dated result document.

**Interfaces:** `build_review_packet(comparison: dict, artifacts: dict,
approval: dict | None) -> dict`. Consumes verified identities and metrics from
Task 3; produces report-only review status, reasons, evidence references and
`promotion_status=blocked`. A matching human approval can mark
`observation_approved`, never change that promotion field or touch runtime files.

- [ ] Write failing tests for the review packet: include scenario/fold metrics,
  sample counts, bootstrap interval and limitations; no approval defaults to
  `awaiting_human_review`; failing/inconclusive comparisons are not approvable.
- [ ] Test missing approver/time/scope and mismatched candidate, baseline,
  comparison or policy hashes: each rejects approval. Assert no broker/runtime
  write or model call occurs for any verdict, including eligible.
- [ ] Run `python -B -m unittest discover -s ops/trading -p test_gold_experiment.py`;
  expect the new interface tests to fail, then implement minimal packet assembly
  with exclusive artifact output and run again to pass.
- [ ] Produce the human packet. Request separate explicit approval for exact
  candidate hashes and Batch 4 no-order observation. Preserve a refusal or
  absence of approval; never synthesize an approval from this plan or a gate pass.
- [ ] Commit only source/tests and sanitized findings. Execution promotion remains
  a separate future decision and implementation.

## Preparation verification and handoff

Completed in this session: owner choice, repository and pinned-package source
review, Context7 lookup, both authenticated MCP tools, anonymous HTTP 401,
secret-safe local configuration presence checks, 17 passing Python checks.
Local MCP tests were attempted but blocked by dependency resolution before test
execution. No code/config/risk policy was changed and no research was launched.

Self-review: schema and filter already exist; the plan reuses them. Prospective
contract/adapter and model invocation are explicit dependencies, not claimed
implemented interfaces. Task 2 covers failure accounting and information limits;
Task 3 covers identical evidence and qualification; Task 4 covers human approval.
Implementation is deliberately deferred by the user's preparation-only scope.

## Next-session handoff

Begin with Task 1's local dependency/runtime checks and Task 2's synthetic
controller only when implementation is requested. Read the companion spec's
packet, artifact and launch-readiness contracts before choosing interfaces.
Resolve the Batch 2 adapter and prospective manifest dependency separately;
do not bypass it with the existing provisional comparison helpers.

At the smoke-test finish time, use the existing
[one-day runbook](2026-09-30-gold-one-day-smoke-test.md) to preserve and review
pipeline artifacts when that operational work is requested. Keep its result
separate from the readiness record. A pipeline pass supplies no missing dated
cost coverage, qualifying sample size or candidate approval.

The next Batch 3 report should state one of: preparation still blocked,
bounded proposal failed, comparison rejected, comparison inconclusive, or
eligible awaiting human observation review. Include the exact remaining gate
and private evidence references; never report “Batch 3 passed” from connectivity
alone or “promoted” from a numerical gate result.
