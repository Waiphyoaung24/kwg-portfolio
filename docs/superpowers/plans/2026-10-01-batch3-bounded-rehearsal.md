# Batch 3 bounded runner and offline rehearsal

Owner authorized local preparation on main, synthetic adapter checks and offline
rehearsal. Unknown OAuth monetary cost must keep live dispatch blocked.

## Latest continuation: integrated provider and Docker rehearsal

The worker now executes the pinned adapter's actual request builder, stream loop,
message conversion and SSE/usage parser. Only an allowlisted set of definitions
is compiled from verified source; auth/config/token functions are excluded and
the HTTP client is fake. The prepared source hash is bound to the reservation
and checked in the worker. No OAuth files or headers are loaded.

Docker Desktop's local Linux engine is available through its explicit local
named pipe; the first default-pipe probe was inconclusive. No service/container
restart or image download was needed. Reused the cached image with immutable ID
`sha256:35b089054ac9b4257976107e71673d9e30ac17c9b50bbf8b4783f2f6d1d1981f`.
Its application entrypoint is replaced with isolated Python (`-I -S -B`), so
the SearXNG application/packages are not started or imported.

`--sandbox` runs with network none, read-only root, user 65534, all capabilities
dropped, no-new-privileges, 128 MiB RAM, one CPU and 32 processes. Only the two
fixed harness files and prepared provider source are mounted read-only. The
image's two declared config/cache volumes are overridden with empty read-only
directories; initial verification correctly refused their writable defaults.
No repository, Docker socket, OAuth store, broker files or dataset volume is
mounted. The approved synthetic prompt/response fixture arrives on stdin.

Verified actual container configuration, denied filesystem write and denied
external-network probe, one fake POST with parsed usage, complete repeatable
comparison, timeout cleanup and refusal to reuse the attempt. Containers are
force-removed with anonymous-volume cleanup in a finally block; failed attempts
remain on disk. Two event-linked volumes from the earlier failed probes were
identified and removed without an unscoped prune. All 133 Python tests and the
standalone provider guard checks pass. Actual model requests remain zero.

```powershell
python -B ops/trading/rehearse-batch3.py --sandbox --output .batch3-vibe/my-new-sandbox-rehearsal
```

Run in an authorized local terminal with access to Docker Desktop. There is no
automatic pull/start or fallback from Docker to a weaker host worker. The default
host rehearsal still explicitly reports `os_sandbox=false`.

This establishes the **offline fixture's OS boundary**, not a live OAuth runner.
Real HTTP/auth integration, endpoint acceptance of the output-token parameter,
credential/host-artifact ACL review, qualified Batch 2 provenance and an approved
observable monetary ceiling remain gates. Image/runtime hashes provide identity,
not an independent supply-chain attestation. A host crash can leave the named
container; its name is saved in attempt.json for recovery without redispatch.
Older implementation notes below describe the earlier host-only milestone.

Reuse the strict structured proposal and existing simulator. General agent loops
cannot enforce this experiment's request budget; generated code adds an
unnecessary execution boundary. Neither is used for this rehearsal.

1. Prepare the one-request provider guard with token, stream and response bounds;
   verify pinned provider class with fake transport, never OAuth credentials.
2. Run a fixed synthetic response in a separate clean-environment worker with
   exclusive durable reservation, wall deadline, bounded output and usage audit.
   Worker has no provider, tools or credential imports. This is not an OS sandbox
   for arbitrary code. Live entry remains absent until verified isolation,
   cost clearance and Batch 2 qualification.
3. Adapt synthetic baseline reports against immutable dataset/source/window/
   risk/policy/cost/clock identities. Preserve raw evidence separately and expose
   only development statistics. Reproduce the baseline before accepting it.
4. Replay one structured fixture proposal through the validator and existing
   simulator with identical windows/costs; save comparison and verify repeatability.
   Synthetic registration is local audit only; no strategy registry or promotion.

Checks: tampered identities/costs/clock, validation leakage, tools, oversized
output, missing usage, timeout, refusal to reuse attempts, unchanged risk/policy,
identical repeated comparison bytes. No VPS, collector or MT5 changes.

## Implemented and exercised

- `batch3_runner.py`: fixed fake transport in a separate `-I -S -B` Python
  process, cleared environment, attempt-local home/temp/cwd, exclusive fsynced
  reservation before launch, 180-second wall deadline with kill/wait, no retry,
  validated 16 KiB proposal and 2,048-token synthetic usage bound. Invalid worker
  outputs and exception bodies are not persisted. Usage is explicitly synthetic;
  actual model requests are zero and monetary cost is unknown, never zero.
- Prepared provider patch: one inference POST per invocation, no tools/401
  resend/redirect/proxy inheritance, timeout at most 120 seconds, request body
  `max_output_tokens=2048`, response 16 KiB and wire stream 256 KiB. Fake HTTP
  checks exercise pinned upstream class. Patch remains unapplied; its token
  parameter has not been accepted by the real OAuth endpoint in this experiment.
- `batch3_adapter.py`: rejects real data; binds exact raw dataset/baseline bytes,
  source/window/risk/policy/cost/clock hashes, interval coverage and reproduced
  baseline. Cost/clock evidence stays in the audit, development statistics alone
  go into the prompt. Synthetic UTC daily returns derive from equity curves;
  raw broker daily buckets are not simply renamed UTC. Real dated/DST mapping,
  raw evidence authenticity and qualified report adapter review remain pending.
- `rehearse-batch3.py`: artificial noisy bars, dated fictional cost/clock records,
  three flat validation folds and an untouched holdout. Reads the validated
  proposal artifact, records synthetic audit registration before simulation,
  runs existing simulator for baseline and candidate, reruns both and writes
  comparison plus gate inputs. Existing evaluator returns `inconclusive` /
  `evidence_incomplete`; no qualification or numeric gate is relaxed.

Run from repository root, choosing a new output directory each time:

```powershell
python -B ops/trading/rehearse-batch3.py --output .batch3-vibe/my-new-rehearsal
python -B -m unittest discover -s ops/trading -p test_batch3_rehearsal.py
python -B ops/trading/check-vibe-codex-guard.py --source .batch3-vibe/upstream/agent/src/providers/openai_codex.py
```

Saved private evidence is indexed by `.batch3-vibe/latest-rehearsal.txt`.
Verification: all 132 trading Python tests passed, plus pinned provider fake-
transport checks. Self-review covered attempt reuse/interruption, fixed worker
imports/environment, development-only packet, raw report binding and holdout.
The synthetic lookback of 3 is a plumbing fixture, not a selected research
candidate. Normal Vibe learning UI and OAuth session remain unchanged.

## Live runner is not finished or enabled

This is a runnable offline supervisor plus a prepared provider guard, not a
connected production runner. The two have not been exercised together against
real HTTP. Unknown OAuth monetary cost is an owner-confirmed dispatch blocker.
The fixed worker has no file/code tools or credential imports; environment and
directory separation are not an OS sandbox or verified private NTFS ACLs.
Before live dispatch: qualified Batch 2 inputs/report provenance, reviewed OS
isolation/credential boundary, approved measurable cost ceiling, provider token-
limit compatibility, and integrated accounting/deadline checks. No credential
files were read/copied and no live gold request was made.
