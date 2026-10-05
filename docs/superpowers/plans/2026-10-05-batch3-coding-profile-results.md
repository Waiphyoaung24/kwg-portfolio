# Coding-session profile prepared — 2026-10-05 Bangkok

## Current result: actual chat file denial passed at 17:34 Bangkok

After the owner's permissions selection, the active managed policy explicitly
denies `.batch3-vibe` under both workspace roots. The same open-only probe ran
through the ordinary command tool, without a nested CLI or escalation, and
exited 0 at Unix `1791196453` (2026-10-05 17:34:13 Bangkok):

```json
{"mode":"coding-boundary-open-only","dispatch_status":"blocked","credential_contents_read":false,"registration_open_denied":true,"canary_open_denied":true,"source_open_allowed":true,"workspace_write_allowed":true,"token_restricted":false,"executing_owner":true,"checked_at":1791196453,"model_requests":0}
```

This is genuine file-access denial in the actual coding command context. The
Windows token remains unrestricted and executes as owner, so this result does
not establish the separate restricted-token property seen in the native CLI
validation. No credential bytes were read. Project config still names
`gold-research-coding`; the owner's reported UI label was `gold-research-config`.
The verified effective policy and probe, rather than that label, establish
the observed boundary. Prior ordinary-tool probes failed until this selection;
restart alone had not resolved it. No further restart is required by this check.

The deny is non-escalatable. Do not request exceptions to read private runtime
data, authorizations or credentials. This step changed documentation only and
did not reread private seals, ACLs or registries after selection. Their last
owner-context verification remains historical. No private production proof or
approval was written, and no renewal, authenticated catalog or model request
ran. This public diagnostic is not a private gate receipt and must not be
presented as fresh dispatch evidence later.

Next review the unchanged sealed intent, obtain applicable account-renewal and
one-proposal authorization, and establish legitimate owner-side execution
outside this coding profile. Before any real dispatch, that execution must
verify the sealed source/inputs and same account, refresh saved provider $0
controls, and record a fresh actual-chat denial bound to the proposal seal.
The runner's denial, billing and account evidence must be within five minutes;
its concrete approval has a separate maximum thirty-minute lifetime. Keep
dispatch blocked until all gates pass. See the
[final runner intent](2026-10-05-batch3-final-runner-results.md).

## Historical validation before the active permissions selection

The stronger project-only profile is implemented and passed a real native
Windows sandbox check. **This running chat has not adopted it:** its ordinary
command tool still runs as the owner and can open both private files. Real
dispatch remains blocked. No credential bytes or model requests were read/sent.

## Change and proof

`.codex/config.toml` selects `gold-research-coding`, extending the built-in
`:workspace` profile with one narrower rule: `.batch3-vibe` is denied under
workspace roots. This protects the entire private runtime, including auth,
development data, real input snapshots, approval/evidence and production attempts.
It keeps normal project editing and the existing elevated Windows sandbox.
The user/global config, legitimate owner's private ACLs, proposal code/input
seals, provider settings and SSH configuration were not changed.

The official [permission profile documentation](https://learn.chatgpt.com/docs/permissions)
describes `default_permissions`, extending `:workspace`, and exact deny rules
that override a wider workspace grant. The [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
documents the same keys; native [Windows sandbox modes](https://learn.chatgpt.com/docs/windows/windows-sandbox)
distinguish the preferred elevated implementation from its fallback. The profile
uses the existing stronger mode; no fallback or weaker setting was selected.

The installed user CLI is 0.157.1, while the app's cached runtime used for this
test is 0.160.0 at
`C:/Users/wai19/AppData/Local/OpenAI/Codex/bin/f544b3844e0f14e9/codex.exe`.
The existing user config already had `windows.sandbox="elevated"`; no named
default profile or project config existed. The current chat's supplied managed
policy allows reads from the filesystem root. Thus workspace write restriction
alone does not establish the required private-file read denial.

The real native test used:

```powershell
# $encodedProbe is the UTF-16LE base64 of the reviewed open-only probe script.
& C:/Users/wai19/AppData/Local/OpenAI/Codex/bin/f544b3844e0f14e9/codex.exe sandbox `
  -C C:/Users/wai19/Desktop/kwg-portfolio -P gold-research-coding -- `
  C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe `
  -NoProfile -NonInteractive -EncodedCommand $encodedProbe
```

The operational probe is preserved at
`.superpowers/sdd/gold-coding-isolation-20261005/probe.ps1`. It opens and closes
handles without reading bytes, checks the actual Windows token, opens a public
source file as a positive control, and creates/removes its own empty workspace
write canary. The native launcher uses Codex's real sandbox rather than a mocked
token. Its setup log records one deny-read ACL applied and successful setup.

| Result | Native explicit profile | Current ordinary command tool |
| --- | --- | --- |
| Restricted token | true | false |
| Executing as owner | false | true |
| Registration open denied | true | false |
| Private canary open denied | true | false |
| Public source open allowed | true | true |
| Workspace write allowed | true | true |
| Credential contents read | false | false |

Native check exited 0; the active-tool probe exited 2 as required for failure.
Both outputs and native stderr are retained under that operational directory.
Private auth/canary/development/registry/snapshot ACLs still passed owner/SYSTEM
checks afterward; the 84-file proposal seal is unchanged and production registry
empty. This is **profile validation**, not a passing active-chat proof. No
`<proposal seal>.coding-denial.json` or approval was created.

Private receipt: `.batch3-vibe/proposal-readiness/b00ee5256e16883f9bdc7866cdba1fa58d709ee114599c1cda7d8608eb6e87a5.profile-validation-20261005.json`.
SHA256: `49ef28dd0244e80c17d51e2165a585f42793fd81bd301def15312efb5a8e210c`.
It explicitly records `actual_coding_token=false` and
`active_chat_boundary_verified=false` for the nested validation's scope.
Configuration SHA256:
`316297359e9ec57ef37882f0b4b7346c54636caedac1b2f5d63f821a05916d06`;
probe SHA256: `fa5721b1f6e909a0d14336b050c86f8c80d83e51e8e834564995bb01c6492a34`.

Two launch diagnostics are preserved in this report: using the older
`sandbox windows --help` syntax caused the flat CLI to attempt setup and fail
before its child launched; using `-File` then hit the sandbox user's existing
script execution policy. The reviewed inline `-EncodedCommand` probe succeeded.
No machine or user script execution policy was modified. No helper cache,
sandbox account or setup state was deleted or manually repaired.

## Resume

1. Fully exit and reopen Codex, then return to this chat so the project
   permission configuration can reload. This is a required user action because
   the agent cannot replace the running chat's execution context from its shell.
2. Verify that the active chat uses `gold-research-coding`. If an existing chat
   retains its previous permission selection, select this named profile where
   available. Configuration alone is not proof; run the same open-only probe
   through the ordinary command tool and require genuine denial there.
3. Only then capture fresh owner-private production-bound evidence, review the
   existing sealed one-proposal intent and recheck account/provider $0 controls
   under the applicable owner authorization. Keep the final runner's gates and
   durable attempt discipline. Do not count the nested CLI probe as the actual
   active-chat proof or renew login merely to resume.

The [final runner checkpoint](2026-10-05-batch3-final-runner-results.md) supplies
the unchanged source, input and receipt identities. Account login remains expired;
concrete one-proposal authorization is pending and qualification deferred.
No OAuth renewal, authenticated catalog, inference, credit/provider/SSH setting
change, trade, deployment or push ran. Native sandbox setup applied its own
restricted-process deny boundary as part of the authorized profile validation.

Ponytail remains active: reuse the native permission system and one exact deny
rule instead of adding a custom launcher, changing private owner ACLs or
rewriting the sealed proposal controller.
