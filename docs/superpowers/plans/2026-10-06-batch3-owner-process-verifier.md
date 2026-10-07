# Owner-observed actual coding process

The owner selected this approach on 2026-10-06. Keep the trading runner, seals,
permissions, renewal/attempt guards and $0 gates unchanged. No inference approval.

The account and provider-controls audits passed, but their timed observations are
historical. Before refreshing them again, resolve actual coding-context evidence.

## Findings

- Installed Codex CLI is 0.160.0. Local protocol schemas were generated without
  starting a thread, server or model turn, under the ignored isolation-review folder.
- `windowsSandbox/readiness` reports setup status, not actual file denial.
  `permissionProfile/list` reports available profiles, not execution results.
  `attestation/generate` returns an upstream client token, not filesystem proof.
- Actual command-token-only inspection at 1791225052 reported unrestricted token,
  executing owner true. No private paths were accessed. This does not establish
  whether other filesystem/namespace protections deny reads.
- WMI process metadata is unavailable in this context. Toolhelp found the current
  PowerShell process but not its reported parent; the attempted chain is incomplete.
  Do not use those repeated partial rows as verified ancestry.
- No broad shell-prefix allow was identified in the inspected user rules. Two
  PowerShell allow entries end with specific command text; their contents were not
  printed or changed. The actual executable is the bundled primary-runtime pwsh.

## Options and decision

1. Owner observer of the actual live coding process (selected): no agent private
   reads and no separate sandbox presented as this chat; requires kernel identity
   checks and an independent manual owner inspection.
2. Repair desktop sandbox execution first: avoids new trading logic, but restart/
   configuration alone cannot demonstrate access denial or explain this backend.
3. Move coding into a real restricted CLI session: supported native execution,
   but requires moving the actual work, not relabeling a nested diagnostic.

## First concrete step: live process identity and effective token

Keep one ordinary tool PowerShell process alive briefly. It publishes only its
PID, native thread ID, process/thread creation times, image path, token SID hash,
restriction state, reviewed script/native-source hashes and a fixed challenge.
The holding script accesses public files only and creates its marker once.

The owner manually runs a hash-pinned inspector. It opens that exact process and
thread with query/synchronize rights, verifies their kernel identity and liveness,
and queries the effective thread token. Fall back to the process token only for
ERROR_NO_TOKEN; any other error refuses. Compare the SID hash/restriction state
with the published capture. It cannot select a different PID, launch a replacement
sandbox, modify token/ACL/profile, inspect credential contents or dispatch.

This first inspection has **no private-file probes**. This is deliberate: token
impersonation alone does not recreate a process's filesystem namespace or broker
policy. First identify the actual host-observed context, including its parent.
An unrestricted token or unknown binding remains inconclusive/blocked, not proof
that credentials are readable and not successful isolation evidence.

Record a public write-once result and release the holder. Keep actual_coding_token,
coding_isolation_verified and combined gates false. Only after kernel binding,
parent/backend review and a valid restricted target can an owner open-only verifier
be reviewed to prove the specific access property. Never adapt the sealed runner
to accept this diagnostic as the required denial receipt.

## Validation and exit criteria

Prepared public helpers under
`.superpowers/sdd/gold-owner-process-verifier-20261006/`: native.cs, hold.ps1,
owner.ps1, inspect.ps1 and check.ps1. Manual owner entry is inspect.ps1.
Focused check passes: native self binding, four kernel mismatch refusals,
native/JSON fresh challenges, seven challenge refusals, PowerShell syntax and
wrapper hash pins. No owner entry or private probes ran through agent tools.

Use real Windows self-process/thread handles on public inputs to test binding and
reject mismatched PID/thread/creation/image fields. Test expired challenge and
identity mismatch refusals without private files. Parse both wrappers and verify
their hash pins. Manual owner run must independently bind the currently held
process or produce a redacted refusal; neither result authorizes inference.

References: [native Windows sandbox](https://learn.chatgpt.com/docs/windows/windows-sandbox),
[Codex rules](https://learn.chatgpt.com/docs/agent-configuration/rules),
[OpenThreadToken](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openthreadtoken).

Live challenge created at 1791226184, expiry 1791226484 (Bangkok 2026-10-06).
Target PID 24676 / native TID 36932; source hashes match the reviewed pins.
Self-reported token_restricted=false is diagnostic metadata, not file-denial proof.
Owner inspection refused at 1791227314, 830 seconds after expiry. Saved result
matches the console, phase live_public_challenge; kernel binding false. Holder
exited normally. Preserve the failed diagnostic and its expired challenge.

## Replacement after expired first round

Prepared `.superpowers/sdd/gold-owner-process-ready-20261006/inspect.ps1` with
new nonce 494d628377c2438ab149802364a9762f. No first-round markers/source changed.
The ordinary holder publishes waiting.json and waits at most 30 minutes. Manual
owner wrapper validates pinned sources/owner identity/wait deadline, writes one
ready.json, and waits at most 30 seconds for the actual live capture. Holder
validates readiness nonce/age, captures the current native identity, and starts
the unchanged 300-second evidence window. Then the owner inspector runs normally.
This avoids spending the evidence window while the user reads the instructions.

Waiting/readiness/challenge publication uses create-new staging and rename
without overwrite; failed or consumed markers stay preserved. Duplicate owner
runs/holders refuse. No timer is retimed and no old PID/receipt is reused.
Existing self-binding/refusal/hash checks and new readiness age/nonce checks pass.
Replacement owner inspection passed at 1791227749, one second after live capture.
Saved result matches the owner's console; PID 37408 / TID 18096 and source hashes
correlate with the challenge. Target kernel binding verified; process token
unrestricted. Immediate parent metadata identifies cached codex.exe 0.160.0;
complete ancestry and active native backend remain unverified. Holder exited.
Scope remains diagnostic metadata: no private probes, canonical gates, acceptance
renewal or model requests. passed/actual_coding_token/coding_isolation_verified
remain false. Preserve the completed round; never replay either owner inspector.
Challenge SHA 17e2242935947f476605ddd29413cf95ae8619ca968041590d17b6d34343a596.
Result SHA 1d5df3da80d67c79c276750a9ca2c9f98724a11318e338583b3197bbc02b261d.

Replacement holder originally waited until 1791229327; actual challenge created
at 1791227748 and expired at 1791228048. That completed capture must not be retimed.

After reviewing the installed CLI help and local schemas, no supported equivalent
actual-chat file-denial attestation was established. Upstream Context7 sources
describe separate Windows backends; their current main branch does not identify
the backend used by this installed command. Do not infer unsandboxed execution
or credential readability solely from this token/parent metadata.

Owner selected moving the actual work into restricted Codex CLI. See the
[refined migration handoff](2026-10-06-batch3-cli-handoff.md). No further desktop
token-only rounds or private probes are needed. CLI flags/pins are checked, but
actual CLI isolation and fresh combined dispatch evidence remain pending.
