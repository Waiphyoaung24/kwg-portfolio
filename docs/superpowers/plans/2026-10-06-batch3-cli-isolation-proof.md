# Actual CLI isolation: fresh owner proof

**Consumed round: do not rerun these operator commands.** Owner result at
1791230681 passed live kernel/effective-token binding, then refused at
pinned_native_runner_ancestry because the actual runner has a versioned filename.
No private probes ran. The sandbox copy's hash matches the approved cached
binary. The [fresh replacement](2026-10-06-batch3-cli-runner-binding.md) recognizes
the exact observed name/path/hash and preserves this round's sources and markers.

Owner selected the actual restricted CLI route and authorized completing its
live-process/file-denial verification. The ordinary CLI self-query succeeded
at 1791228696: restricted process token, expected CodexSandboxOffline SID hash.
That process ended. The new round uses nonce 3e2fbf0491cd4b6d912a6ac305fbbe2e.
Nothing from the old process, attempts or historical account audits is replayed.

## Steps and verification

1. The existing actual CLI executes the reviewed literal public holder input.
   Verify: offline identity/workspace, pinned native source, restricted token,
   atomic new waiting/ready/challenge markers. No agent private-path access.
2. The manual owner observes that live process/thread and effective token.
   Verify: kernel creation times/image, SID and token ID/authentication/modified
   fingerprint, pinned codex-command-runner.exe followed by pinned codex.exe in
   the live ancestry. Unknown or changed ancestry refuses before private checks.
3. Only the manual owner duplicates that verified restricted token into an
   impersonation token. Verify: same account/authentication and retained
   restriction; successful impersonation before any token-scoped file request.
   Public source open and empty workspace write must work. Owner existence/open
   controls establish that registration/canary exist; reparse points refuse.
   Both restricted open requests must return exactly Win32 ACCESS_DENIED (5).
   No file bytes are read. Failed impersonation causes no fallback owner probe;
   failed RevertToSelf terminates the helper. Recheck the live target afterward.

The token-based denial is conservative for the verified native restricted-token
backend: duplication preserves its security context, while additional sandbox
restrictions could only prevent more access. An unrestricted token or unknown
backend cannot pass this proof. Configuration or a nested sandbox is insufficient.
The public result remains dispatch_status=blocked, model_requests=0, and writes
no canonical coding-denial gate. Fresh combined gates are a separate milestone.

## Operator sequence

In the existing CLI `Verify CLI command context`, submit the prepared
`.superpowers/sdd/gold-cli-isolation-proof-20261006/cli-prompt.txt` prompt.
Use the already open CLI terminal: the desktop app reports this chat as notLoaded,
so an app message cannot be assumed to reach the existing native CLI runtime.
No app message was sent. The earlier permission question does not start this round.
The CLI must read the holding input and submit literal statements through its
ordinary command tool. No script-policy changes, dynamic file evaluation,
escalation or nested process. Keep its command session alive until the owner
result or expiry; yielding the tool must not terminate the held command.

After waiting.json is published, run in a separate manual owner PowerShell:

```powershell
& 'C:\Users\wai19\Desktop\kwg-portfolio\.superpowers\sdd\gold-cli-isolation-proof-20261006\inspect.ps1'
```

Owner readiness starts a new, unchanged five-minute challenge. Before readiness,
the CLI waits at most thirty minutes. Preserve all markers/results on refusal or
timeout; do not rerun/reset this round. Impersonation or owner process inspection
may be refused by Windows; retain the redacted phase/native_error instead of
changing ACLs, privileges, profile or sealed guards automatically.

Separately, in the owner's launch terminal, run the empty hook fixture:

```powershell
& 'C:\Users\wai19\Desktop\kwg-portfolio\.superpowers\sdd\gold-cli-isolation-proof-20261006\hook-check.ps1'
```

This captures node_path, exit/stdout/stderr from the configured Stop command with
fixed synthetic stdin and empty cwd. It does not rerun the original project event
or establish the original CLI environment. The configured hook and permissions
remain unchanged. The F2 GitHub/nexapex warnings are unrelated to this check.

## Hook evidence and references

Configured global Stop: Impeccable Design deep pass. Windows command uses node;
exact cmd /C empty-fixture test passes with an audit record, exit 0 and empty
stdout/stderr. Desktop node resolves to the bundled kwg-dev-packages node.exe.
Original failing hook/cause is unconfirmed. No credential, PAT or MCP repair is
needed to obtain this isolation proof.

Installed CLI version 0.160.0 supports commandWindows and runs Windows hooks via
cmd /C. Its Stop parser emits only a generic failure for exit 1, omitting stderr:
[command runner](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/hooks/src/engine/command_runner.rs),
[hook config](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/config/src/hook_config.rs),
[Stop parser](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/hooks/src/events/stop.rs).
Win32 contracts:
[DuplicateTokenEx](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-duplicatetokenex),
[ImpersonateLoggedOnUser](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-impersonateloggedonuser),
[RevertToSelf](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-reverttoself).

## Validation and checkpoint

Public check.ps1 passes native self-binding, four kernel mismatch refusals,
eleven malformed/stale/context challenge refusals, unrestricted-token refusal,
syntax and helper source pins. Windows PowerShell 5.1 parses the inputs and
compiles/queries the native helper through literal commands without a policy
change. These are compatibility checks, not actual CLI isolation evidence.
The empty hook fixture and completed-fixture replay refusal pass in a separate
public test copy. No owner helper or holder was run through desktop tools.

Complete isolation proof and owner-terminal hook fixture are pending. No account round,
renewal, canonical gate or model request is approved. Sealed trading Python and
PowerShell match HEAD 18620b96; account/proposal seals and freshness guards remain
unchanged. Batch 2 qualification deferred; trading model gpt-5.6-sol.
