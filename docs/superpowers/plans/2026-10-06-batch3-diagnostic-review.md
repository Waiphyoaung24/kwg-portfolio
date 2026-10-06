# Batch 3 fake-only diagnostic and hook review - 2026-10-06

The diagnostic candidate is an **unapplied patch**, tested against supported-gateway
commit `18620b96eb05eeef86dcea52acf3e00cb1c09e6c`. The preparation branch remains
based on main `1881e77656c3e26c7ec2bd248e309ec7698e20dd`; it does not import that
branch's executable controller or change any sealed source. No production
readiness, new authorization or qualification follows from these checks.

## Failed hook: exact observed cause

Codex's local log records `hook_name=legacy_notify` and
`The filename or extension is too long. (os error 206)` during `after_agent`.
The observed failing operation is process creation, before the notification
handler can run. The configured command is `codex-computer-use.exe turn-ended`.
The executable path is 137 characters; the fixed argument is 10 characters.

Read-only SQLite inspection found the same failure at 2026-10-06 10:51:39,
10:58:14 and 11:17:42 UTC (local log IDs 2331844, 2335214 and 2339435).
Only the relevant error suffix and notification configuration were extracted;
no full turn payload, token, credential store or provider error body was printed.

The [Codex legacy notification implementation](https://raw.githubusercontent.com/openai/codex/rust-v0.160.0/codex-rs/hooks/src/legacy_notify.rs)
serializes the notification as JSON, appends it as one command-line argument,
then spawns the configured command. A synthetic 40,000-character argument to
an inert Python process reproduced Windows error 206 on this machine.
This identifies the notification command-line length failure; the exact failed
argument length was not retained and cannot be recovered from these logs.
The upstream source explains the mechanism; it is not a byte-for-byte audit
of the installed binary. No notification command was manually retried.

This is separate from the Impeccable stdin-based Stop hook and from Git hooks.
The earlier passing empty Stop fixture did not reproduce this failure. Git has
no configured `core.hooksPath` and only sample hook files in the common hooks
directory. No hook, notification configuration, executable or Git safety check
was disabled, edited or bypassed. The notification defect remains unfixed.

## Patch and request/approval consistency

[Patch](../../../ops/trading/patches/2026-10-06-proposal-diagnostics.patch)
changes only the transport, proposal controller and three focused test files
on the pinned public source. Main lacks those newer runtime modules, so importing
the whole gateway implementation merely to fix diagnostics would broaden this
task. The patch artifact preserves the source boundary and is directly testable.

- Transport failures expose only enumerated stage/code pairs, bounded numeric
  HTTP status, or two approved provider error codes. Other provider codes become
  `unknown`. No arbitrary error message, body, headers, account, prompt or token
  is propagated. HTTP refusal bodies are never read.
- Worker failures emit a small strict JSON envelope. The controller validates
  it even on a nonzero exit; malformed, extra-field and oversized replies become
  `worker/reply`. Stderr remains excluded from receipts.
- A possible request transfer remains `outcome_unknown`; the exclusive marker
  survives, replay refuses, and no fallback or second POST is added. Cleanup
  failure is separate and cannot overwrite the request diagnostic or pass state.
- Future review text is generated from the same request builder as the actual
  fake HTTP call: POST, public Responses, gpt-5.6-sol/medium, stream=true,
  store=false, no tools, one POST, zero retry and USD0 additional spend. It also
  lists the unchanged local byte/time bounds. No provider token cap is asserted.
- The candidate approval schema requires `request_review_sha256` for that exact
  UTF-8 review text, in addition to the existing seal, intent, account receipt
  and fresh-owner requirements. Missing or mismatched review hashes refuse.
  This is a future schema change, not a migration or approval writer. Existing
  approval text, source seals and the consumed experiment remain untouched.

The original review's stream=false statement was inaccurate. That is a confirmed
consistency defect, not evidence that it caused the consumed attempt's failure.
The old worker discarded its details, so that inference failure remains unknown.
Local time/byte limits still do not establish backend cancellation or billed usage.

## Reproduce the offline verification

From this branch's repository root, with Windows and Python 3.12+:

```powershell
python -B ops/trading/check-proposal-diagnostic-patch.py
```

The [checker](../../../ops/trading/check-proposal-diagnostic-patch.py) exports the
pinned local commit into a disposable temporary directory, checks/applies the
patch there, and runs only the three reviewed fake suites. It never fetches.
The pinned commit must already be in the local Git object database. Python audit
guards reject socket activity, real subprocess creation and private runtime
opens during the test process; these guards are not production isolation proof.

TDD evidence: the new diagnostic tests first failed on missing diagnostics,
decoder, worker envelope and review generation. The real-controller/fake-boundary
test failed on discarded failure details in both cleanup outcomes. The bounds
review test separately failed with `KeyError: local_bounds` before implementation.
After implementation, all **14 focused tests pass**. They exercise real request
construction, stream parsing, envelope handling, approval gates, temporary-file
reservation/receipt logic and replay refusal with fake external/private boundaries.
The existing five baseline/evaluation/cost modules passed all 39 checks on the
main-based preparation worktree. Both canonical risk/policy hashes still match;
18 local document links and code fences validate. Original HEAD, branch, status
and all 95 previously inventoried uncommitted file hashes match the pre-task
snapshot. Codex hook/config hashes also match; nothing was bypassed.

## Execution rulings and remaining gates

Task 1 reconciliation is retained. Task 2 is delivered as a pinned patch plus
offline checker, not a gateway merge. This is the smallest implementation that
preserves the approved main-based worktree and the consumed runtime. Tasks 3
and 4 remain deferred; no acceptance requirement was removed.

Further gates remain: separate runtime integration review; a distinct explicitly
approved future development plan with fresh account/model/billing/isolation and
cleanup evidence; Batch 2 dated costs, clock/session coverage, frozen prospective
protocol and untouched holdout; 60 eligible days, three folds of at least 20 days,
100 trades per strategy, and all existing numeric/stress/bootstrap gates.
A qualified comparison still needs explicit hash-bound human no-order observation
approval; execution promotion is separate. Neither a new ID nor changed review
text permits retrying the consumed experiment.

No real inference, owner helper, inspector, scheduler, trade, MT5 restart, journal
reset, collector change or VPS service operation was used. The smoke collector
and artifacts remain preserved. Original checkout/uncommitted work is retained.

## Independent final review

A fresh read-only reviewer inspected the full patched controller, transport,
three focused test files and reconciled documentation. It independently ran the
packaged checker (14 tests passed) and `git diff --check` (passed), and reported
no Critical, Important or Minor findings: ready to commit/push this preparation
branch, not a statement of runtime readiness. No additional fix pass was needed.

Reviewer exclusions accepted: live inference, native isolation/owner helpers,
private receipt inspection, consumed-attempt retry, deployment and gateway import
are outside the authorized task. Historical private evidence was not revalidated.
There are no deferred review findings. The pinned-patch ruling above is the only
implementation deviation; no new transport, dependency or approval writer was added.

The staged check additionally found 11 space-only blank context lines in the
patch artifact. Those were normalized to empty context lines; patched source
behavior is unchanged. Git patch application and all 14 fake tests were rerun
after this formatting correction, with no checks disabled.
