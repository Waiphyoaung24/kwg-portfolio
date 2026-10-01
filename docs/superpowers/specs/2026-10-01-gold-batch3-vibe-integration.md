# Batch 3 Vibe-Trading integration specification

Status: specification prepared; offline parser/replay preparation started after
the owner's subsequent “start”. This document does not authorize research.
The implemented replay is for synthetic fixtures only until packet/controller
review and credential quarantine are implemented. All replay output remains
explicitly unreviewed and unqualified; parsing provides no sensitive-content clearance.
Development-packet validation and deterministic prompt construction are now
implemented and tested with synthetic input. Model dispatch, real-report
provenance and credential quarantine remain pending.
Batch 2 remains `prepared_but_blocked`. Owner selected a structured proposal in
this preparation session. Work was performed on `main`, starting at
`0f31e35011b664627390386fa7c0bf24ceb139d3`.

## Milestone and decision

Prepare one manually initiated, reproducible comparison of one Vibe-Trading
proposal against the unchanged EMA20/EMA50/ATR14 baseline. Reuse the existing
offline evaluator; successful comparison can only recommend no-order shadow
observation. It never promotes or activates a strategy.

Alternatives considered with the owner:

| Approach | Benefit | Cost / decision |
| --- | --- | --- |
| Strict structured proposal | Existing validator and entry filter; no generated code | Limited to one supported filter; selected |
| Generated strategy code | Broader hypotheses | Requires hardened execution isolation; excluded |
| Manual transcription | Minimal provider integration | Weaker automatic provenance; not selected |

This preserves the roadmap's separate researcher architecture. No proposal or
lookback value was selected during preparation.

## Owner-selected product architecture — 2026-10-01

Owner selected the existing Vibe-Trading app as a separate research workspace,
rather than chat-only tools or a full trading terminal. Reuse its application;
do not build a custom research UI or general agent framework. This supersedes
the earlier assumption that no separate application would be used. It does not
authorize installation, deployment, live inference or candidate research.

The boundary is: approved development packet -> isolated Vibe app -> one
structured proposal -> existing strict validator -> existing Batch 2 simulator
and qualification gates -> explicit human review. Validation/holdout evidence
stays with the evaluator. Upstream backtests are exploratory and cannot replace
our fixed baseline, dated broker costs or qualification evidence. The app gets
no broker credentials, MT5 volume, order tools or promotion interface.

Prepare a synthetic import/export compatibility check first. Inspect installed
0.1.15 against the assessed upstream release before pinning a runtime; no
automatic upgrade. Verify provider route, isolated home, tool permissions,
background jobs, usage accounting and request limits without model requests.
An external MCP allowlist alone does not prove built-in app tools are disabled.

The existing one-model-request, zero-retry/fallback/tool-call budget remains.
The full app workflow is not assumed compatible: if the narrow proposal mode
cannot enforce it, report the mismatch and seek an explicit revised workflow
budget before real use. Thin file/API adapters may be needed; no replacement
provider framework, reporting system or evaluator is planned.

Primary product reference: [Vibe-Trading](https://github.com/HKUDS/Vibe-Trading).
Batch 2 gates, fixed risk hashes and human promotion approval remain unchanged.

### Selected inference provider: OpenAI Codex with ChatGPT OAuth

Owner selected `LANGCHAIN_PROVIDER=openai-codex` and the product's
`vibe-trading provider login openai-codex` browser login flow. This replaces the
earlier intended Claude/Worker inference route for this integration. The gold
research MCP remains a separate read-only observation service; its bearer token
must never be used as inference authentication.

Read-only inspection of installed 0.1.15 provider metadata confirms
`api_key_required=false`, `auth_type=oauth`, no API-key environment field and
the stated login command. The upstream README documents the same flow and
OAuth credential storage outside `agent/.env`. No credential store was read,
login executed, provider configuration changed or model request made here.
The metadata default model is not an approved model pin; verify the account's
supported model and record the selected identity before use.

Installed `src/providers/openai_codex.py` automatically refreshes on the first
HTTP 401 and resends the inference POST (two-attempt stream loop). Therefore
the provider choice is verified, but the one-request/no-retry contract is not.
Synthetic transport checks must cover this recovery path as well as outer
provider retries. Do not claim ordinary app configuration enforces one request
without proof. Any budget revision requires explicit owner approval.

For later local setup, set the provider in the isolated app's configuration
and run its login command in an interactive terminal. Complete browser login
locally; never paste callback URLs, codes or tokens into chat or Git. Login is
not evidence of inference connectivity, tool isolation or Batch 2 qualification.
OAuth usage accounting must record observable usage and unavailable cost data
explicitly rather than inventing API-key billing values.

## Read-only verification evidence

Document date is the client date, 2026-10-01 Asia/Bangkok. The tool clock during
inspection reported 2026-09-30 17:01:49 UTC; retain raw observation timestamps
rather than inferring elapsed smoke-test time from the document date.

| Check | Observed result | Meaning / limit |
| --- | --- | --- |
| Available gold MCP tools | `get_gold_status`, `get_baseline_summary` | Exactly the two tools registered by repository source; no inference, data export or job tool |
| Authenticated baseline call | Unqualified, hypothetical costs, no candidate, promotion blocked | Frozen historical summary, not live Batch 2 readiness |
| Authenticated status call | `duplicate` / `none`; terminal connected; quote fresh; 250 bars | Snapshot `checked_at=1790787681`, age 0.139784 seconds at source check; no continuous-health or exposure claim |
| Anonymous remote `tools/list` | HTTP 401 | Access denied as intended |
| Codex local configuration | Expected endpoint and `KWG_GOLD_MCP_TOKEN` reference present; process/user variable present | Boolean-only inspection; no values printed or changed |
| Installed package metadata | `vibe-trading-ai` 0.1.15 | Local install only; no VPS research-runtime pin verified |
| Provider environment presence | Inspected `LANGCHAIN_PROVIDER`, `LANGCHAIN_MODEL_NAME`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_BASE`: absent in process/user scope | Not an exhaustive configuration audit; file-based or other auth could exist; inference remains unverified |
| Existing Python tests | 7 experiment + 10 evaluator tests passed | Synthetic/offline checks, not qualification |
| MCP Node tests | Failed to load `@modelcontextprotocol/server/index.js` | Local dependency-resolution blocker before tests ran; live connectivity passed independently |

Subsequent implementation verification restored the frozen dependencies and
passed all four MCP tests with package-store access. The original failure was
the sandbox's inability to read those packages, not evidence of a broken
deployed Worker. Package and lockfile versions were unchanged.

The endpoint is
`https://kwg-gold-research-mcp.nexuslab-dev-mm.workers.dev/mcp`.
Source uses a 64-hex bearer secret, HTTPS origin, five-second origin timeout,
sanitized status allowlist and 30-second heartbeat expiry. Worker package pins
are SDK 1.29.0, server 2.0.0-beta.5, agents 0.20.0, zod 4.5.4 and Wrangler
4.115.0. No dependency install, deployment or secret change was made.

Context7 resolved `/hkuds/vibe-trading` and returned upstream
[README](https://github.com/HKUDS/Vibe-Trading/blob/main/README.md) material on
MCP configuration and custom data loaders. Those are current-main references,
not proof of 0.1.15 compatibility. Installed source confirms separate provider
configuration, `TIMEOUT_SECONDS` default 120, `MAX_RETRIES` default 2, an agent
loop default of 50 iterations, and `VIBE_TRADING_HOME` support. These defaults
do not satisfy this experiment's bounds. No agent, provider doctor, inference
request or research command was run. MCP credentials are not model credentials.

## Existing code and missing integration

- `gold_experiment.py`: `validate_candidate`, `entry_allowed`, canonical
  `digest`, registration, research-input and provisional comparison helpers.
- `replay-gold.py`: candidate filter changes entry eligibility only. Opposite
  signals still reach the simulator to close an existing position.
- `simulate-gold.py`: cost-aware simulation, explicit windows and three flat
  folds; exclusive output creation. Candidate CLI requires a manifest and
  registration. Its old manifest path rejects `--cost-profile` and `--windows`.
- `compare-gold.py`: immutable provisional preparation/registration/reporting.
  Its contract is fixed to the old 10,000-bar diagnostic, hypothetical costs,
  development indices and prior exposure. Do not relabel it as qualified.
- `evaluate-gold.py`: approved numeric gates, paired bootstrap and an explicit
  CLI cap `simulator_provenance_unverified`. Leave that cap until the separate
  Batch 2 adapter is specified, tested and reviewed against real evidence.

A prospective manifest/registration path must bind dated costs, qualified clock
mapping, windows/folds, policy, simulator source and immutable raw outputs.
The old helpers cannot be used unchanged to claim a qualified candidate run.
This is a prerequisite, not permission to weaken the old validators.

## Frozen comparison contract

The only accepted proposal is an object with exactly:

- `kind`: literal `ema20_slope_filter`.
- `lookback_bars`: integer 2 through 5 inclusive (booleans forbidden).
- `hypothesis`: nonblank string, at most 2,000 characters.

One proposal chooses one value; no sweep, ranking of four alternatives, repair
prompt or automatic retry. Long entries require positive EMA20 slope over that
lookback; short entries require negative slope. Zero slope rejects entry.
Reuse the existing rolling 250-bar indicator seeds. The filter must not suppress
opposite-cross exits or alter ATR, sizing, price rounding, fills or gap handling.

Unchanged constraints for both baseline and candidate:

- `XAUUSD-VIP`, completed M15 candles, demo-only scope.
- EMA20/EMA50, ATR14, 0.1% current-equity entry risk, stop 2 ATR, target 3 ATR.
- One strategy-owned position; no pyramiding/martingale; opposite-cross close
  with no same-candle reversal; floor volume step and skip excessive minimum lot.
- Persisted UTC day-start 1% equity-loss entry pause; not a guaranteed loss cap.
- Valid bid/ask, spread at most 10% ATR, qualified quote age 0–30 seconds,
  pinned demo identity, broker protection and uncertain-intent reconciliation
  remain execution requirements. This offline work cannot authorize execution.
- Same qualified dataset, dates, flat folds, warmup, initial simulated USD
  100,000 per window, costs, assumed stress, evaluator and risk hashes.

Approved policy canonical SHA-256:
`39eb8759133ac1ca50308e0aa053c761a53b24e94be9ebc3f8c13ff73413873d`.
Use `evaluation-policy.json` without edits: 100 closed trades per strategy,
60 observed validation days, three folds of at least 20 days, lower-scenario
profit factor at least 1.1, improvement at least 0.25 percentage points,
drawdown at most 5%, drawdown increase at most 0.25 points, no fold worse by
more than 0.25 points and at least two improved folds. All scenarios need
positive candidate net P&L; middle/stress return must be positive and no worse
than baseline. Paired 95% bootstrap lower bound must exceed zero, using seed
20260928, 10,000 replicates and five-day blocks. Slippage assumptions remain
0.05/0.10/0.30 price units per side. Missing evidence is inconclusive.

## Information and runtime boundaries

1. Batch 2 freezes future collection protocol, dated cost/clock coverage and
   development/validation/fold/holdout boundaries before qualifying collection.
   Freeze the candidate before candidate validation execution or inspection.
2. Research sees only an allowlisted development summary and schema. Exclude
   validation results/bars and all holdout contents. Record prior exposure:
   original validation was inspected and reserved bars were signal-replayed.
   Preserve the old reserved 2,000 bars; new holdout stays separately uninspected.
3. Use one isolated Vibe-Trading 0.1.15 controller invocation through the owner's
   existing route, only after a bounded route check. No default trading profile,
   global home, broker secrets, MT5 volume, Docker socket, shell tools, order
   tools or write access to evaluator/risk/runtime strategy. Mount sanitized
   input read-only; only a new private experiment directory is writable.
4. Draft run bounds: one model request, zero retries/fallbacks/tool calls,
   120-second request deadline, 180-second controller deadline, at most 2,048
   output tokens and 16 KiB response. Enforce at transport/process boundaries;
   an agent iteration setting alone is insufficient. Unknown route, pricing,
   usage accounting or unenforceable bounds blocks launch. Freeze the owner's
   approved cost ceiling before the route check; none is assumed here.
5. Model egress is limited to the verified provider; evaluation has no network.
   Inspect pinned runtime with synthetic input to prove limits, import and
   artifact output. Do not introduce a custom market loader when a development
   summary suffices. No generated code is executed.
6. Persist request/prompt hash, exact response bytes and parsed proposal before
   evaluation. Invalid output, timeout or lost response consumes the attempt;
   record failure, never silently ask again. Replaying frozen response bytes
   must work without a model call. Model generation itself is not claimed to be
   deterministic.

## Reproducible evidence and decision

Private exclusive artifacts bind experiment ID, registration UTC time, source
commit and hashes, installed package/dependency provenance, model/provider and
settings, prompt/input/response/proposal hashes, data/cost/clock/policy/risk
hashes, windows/folds, prior exposure, start/end times, limits, usage and cost.
Never save credentials in prompts, output summaries, errors or Git. Keep a
durable attempt record even for failed or invalid proposals.

Run the fixed baseline twice to distinct private outputs before candidate
evaluation; compare canonical report bytes. Run the single registered candidate
twice from the frozen proposal and identical inputs. No second model request.
Exclude wall-clock envelope metadata from deterministic report bytes; retain it
separately. Any hash or repeatability mismatch is inconclusive, never repaired
by overwriting evidence. Use the verified Batch 2 adapter to derive gate inputs
from raw outputs, not hand-shaped metrics. Recompute identities from bytes.

The final report contains verdict/reasons, scenario and fold comparisons,
trade/day counts, returns, net P&L, profit factor, drawdown, expectancy, turnover,
risk-normalized trade evidence, bootstrap interval, limitations and all evidence
references. `eligible_for_shadow` is a recommendation only. The comparison
always emits `promotion_status=blocked`. A separate human record identifies the exact
candidate, baseline, comparison and policy hashes, approved observation scope,
approver and UTC time. A matching approval sets only `review_status=observation_approved`.
Reject missing/stale/mismatched approval. Approval for Batch 4 observation
authorizes no orders; execution promotion needs a separate review and implementation.

## Development packet and attempt artifacts

Use a strict top-level packet with exactly `schema_version=1`, `experiment_id`,
`identity`, `development`, `baseline_development`, `proposal_schema` and
`limitations`. `identity` contains hashes of the prospective manifest, source,
development input, fixed risk rules and approved policy. These identify inputs;
they do not convey validation metrics or holdout contents.

Exact identity keys are `manifest_sha256`, `source_sha256`,
`development_input_sha256`, `risk_sha256` and `policy_sha256`; each is a lowercase
64-hex SHA-256. Risk must match both the local unchanged `RISK` object and fixed
digest `865e46d493db5939e9e3d98375ce727664d57c03bc42a06e548cace61a8e6ce7`.
Policy must match the approved digest above. The other hashes are references;
the future adapter must verify their source bytes before launch.
`experiment_id` is 1–64 ASCII letters, digits, underscores or hyphens, starting
with a letter or digit. Schema version is integer 1, never a boolean.

For `development`, reuse the existing research summary fields:
`bars_including_warmup`, `first_bar`, `last_bar`, `first_close`, `last_close`,
`minimum_close`, `maximum_close`, `median_recorded_spread_points` and `gap_count`.
For `baseline_development`, include `lower`, `middle` and `stress`, each with
`trades`, `return_pct`, `net_pnl_usd`, `profit_factor`,
`expectancy_usd_per_trade` and `close_sampled_drawdown_pct`. Nonfinite numbers
are rejected; undefined metrics remain explicit nulls and never become zero.
Bind each summary to its raw development report through the verified adapter.
Warmup-inclusive bar count must be an integer at least 250; first/last epochs
must be positive, ordered and aligned to M15. The count cannot exceed the
available M15 slots. Gap count is an integer from zero to bar count minus one.
Prices are finite and positive, first/last close lie within minimum/maximum,
and median spread is finite and nonnegative. Trades are a finite nonnegative
integer; drawdown is finite from zero to 100 percent. Profit factor is null or
finite nonnegative; expectancy is null or finite. Return and net P&L are finite
and required. These structural checks do not qualify timestamps or accounting.

`proposal_schema` has exactly the existing three entries: `kind` is
`ema20_slope_filter`, `lookback_bars` is the literal `integer 2..5`, and
`hypothesis` is the literal `nonempty string, at most 2000 characters`.
Limitations are a nonempty, duplicate-free list drawn only from
`synthetic_fixture`, `validation_previously_inspected`,
`reserved_bars_signal_replayed`, `historical_costs_unverified`,
`broker_timestamps_unqualified` and `slippage_assumed`. These codes replace
freeform text at the prompt boundary; new evidence limitations require a
reviewed schema update rather than arbitrary text injection.
The original `research_input` helper is a field-layout reference, not a
qualified-input producer: its legacy identity and hypothetical assumptions
must not be copied into the prospective packet.

Render the prompt from these allowlisted fields and fixed instructions; reject
unknown fields recursively. Do not feed raw files, logs, MCP status payloads,
previous validation summaries or provider errors to the model. The model must
return the proposal JSON only; code fences, prose and tool calls fail parsing.

| Private artifact | Written when | Contents |
| --- | --- | --- |
| `attempt.json` | Exclusively before any model dispatch | Experiment ID, input/prompt hashes, frozen bounds, approved route reference and start time |
| `response.json` | After a response arrives | Exact UTF-8 proposal response bytes; no parse-and-reserialize step |
| `proposal.json` | Only after strict validation | Canonical proposal and its hash |
| `result.json` | At terminal success/failure | Safe outcome code, response/proposal hashes when available, finish time, usage/cost or explicit unknown |

An attempt marker without a terminal result means interrupted/uncertain, not
permission to dispatch again. Preserve returned bytes even if invalid; bound
capture size and record truncation as failure. Never render provider response
or error bodies in public summaries. A credential-bearing response is
quarantined privately and cannot become a proposal. Offline replay consumes
saved response bytes and does not rewrite original artifacts.

## Launch-readiness record

Before a future launch, save one private readiness record listing every gate
below, its evidence path and SHA-256, outcome, reviewer and review UTC time.
Only verified evidence may receive `passed`; missing evidence stays `blocked`.
This record does not replace the source artifacts or the owner's run approval.

| Gate | Required pass condition |
| --- | --- |
| Data and clock | Exact-symbol completed bars, dated offset/calendar mapping, coverage and failures preserved |
| Costs | Applicable dated commission, directional swap and rollover coverage for all comparison windows |
| Prospective protocol | Precollection source/policy freeze, declared development/validation/folds and separate untouched holdout |
| Baseline evidence | Adequate covered baseline days/trades/folds; unchanged policy and risk; two identical report outputs |
| Adapter | Raw hashes, real daily returns/folds, cost/date identity and accounting independently reproduced; CLI provenance cap lifted only through its reviewed implementation |
| Candidate contract | Prospective manifest accepts qualified costs/windows and rejects mismatches; registration precedes candidate execution |
| Runtime | Pinned package/dependencies, isolated home, no broker/tool access, synthetic import/output checks pass |
| Model route | Owner's existing route, bounded synthetic probe, request accounting and approved cost ceiling verified |
| Launch authorization | Owner explicitly authorizes this single experiment ID and frozen bounds |

Candidate trade/day minimums and performance gates are outcomes of the single
comparison, not evidence that can exist before the proposal. Baseline readiness
does not require profitable baseline results. If the candidate fails sufficiency,
save `inconclusive`; do not reinterpret the launch approval as permission for
another proposal. Human observation approval is a subsequent separate gate.

## Prepare now versus gated work

| Work | Gate |
| --- | --- |
| This specification, plan, source review and read-only MCP checks | Completed now |
| Synthetic adapter/controller design and tests, local dependency repair, isolated package pin | Preparation implementation requested; offline parser/replay implemented, full controller and route still pending |
| Dated commission/swap/rollover and historical offset/DST coverage | Outstanding Batch 2 evidence |
| Frozen future protocol, 60 covered days, three 20-day folds, 100 trades per strategy | Outstanding; candidate sufficiency is checked after its one gated run |
| Verified real-report adapter, prospective candidate contract and repeatable fixed baseline | Required before research launch; numeric profitability of baseline is not a launch requirement |
| Bounded existing model route, owner cost ceiling, synthetic import/artifact isolation checks | Required before research launch; no inference verified here |
| Real Vibe proposal, registration and candidate evaluation | Only after Batch 2 prerequisites are signed off and owner authorizes the bounded run |
| Batch 4 observation / promotion | Passing comparison plus explicit human approval; separate implementation |

## Running smoke test: preserve

Owner reports active collector directory
`/root/kwg-gold-research/evidence/smoke-20260930T164651Z`.
Interval: 2026-09-30 17:00 UTC through 2026-10-01 17:00 UTC.
Finish capture only after 2026-10-01 17:15 UTC (2026-10-02 00:15 Bangkok).
Owner-reported start checks: Algo Trading off; no gold positions or pending
orders. Cost status remains incomplete. This session did not independently
inspect collector files or change any VPS state. Preserve collector, raw OHLC,
journals and all artifacts. No finish capture or follow-up was scheduled.
Pipeline success does not satisfy Batch 2 or unlock Batch 3.

References: [roadmap](../plans/2026-09-28-gold-ai-researcher.md),
[Batch 2 wrap-up](../plans/2026-09-30-gold-batch2-wrap-up.md),
[implementation plan](../plans/2026-10-01-gold-batch3-vibe-integration.md),
[MCP setup](../../../ops/trading/research-mcp/README.md).
