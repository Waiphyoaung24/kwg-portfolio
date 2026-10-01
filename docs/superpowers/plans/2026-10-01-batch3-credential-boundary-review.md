# Batch 3 credential-boundary review — 2026-10-01 Bangkok

Result: the synthetic Docker worker has a credential-free boundary. The live
OAuth boundary is not complete or approved. This review does not qualify Batch 2
or authorize a model request, candidate research, orders or promotion.

## Verified

- On `main`, inspected runner, launcher, fake provider harness and pinned
  upstream file-path guards. Read Windows ACL metadata, not credential contents.
  No tokens, credential hashes, OAuth callbacks or authentication headers read.
- `.batch3-vibe` has a protected ACL allowing FullControl to `wai19`, SYSTEM
  and `CodexSandboxOffline`. Profile, runtime, auth directory, OAuth JSON,
  latest rehearsal directory and attempt files inherit these three identities.
  No Everyone or ordinary Users ACE appeared on these inspected objects.
  Inspected paths showed no reparse-point attribute.
- The normal learning launcher drops inherited API/broker variables, uses its
  own profile/runtime and disables shell tools, scheduling and channel startup.
  It retains PATH and uses the installed dependency runtime. This is configuration
  separation, not a separate Windows process identity or OS sandbox.
- Upstream default document/file/run roots are uploads, imports, runs and bundled
  skills, not the auth directory. A stdlib AST-only check of the actual path
  guard definitions rejected five auth-path cases and accepted an upload path.
  The check resolved paths only; it never opened the OAuth file. Configured roots
  and loaded-process settings were not attested by this check. Do not add the
  runtime/profile/repository root to file or run allowlists.
- The offline runner accepts only synthetic packets. Its worker has no file
  tools or generated-code execution, uses isolated/no-site Python, and filters
  environment variables. The fake provider harness compiles named request/SSE
  definitions only; auth helpers are absent and headers are replaced with an
  empty fake. No credential store is read by that execution path.
- Docker mounts only two fixed harness files, prepared provider source and two
  empty image-volume overrides, all read-only. Neither OAuth store, full repo,
  broker configuration nor Docker socket is mounted. Network is disabled.
  Previous rehearsal evidence records successful sandbox inspection, denied
  write/network probes and cleanup; this review did not rerun Docker.
- Packet/request/result metadata has the same three-principal inherited ACL.
  Runner persists structured validated output, not arbitrary stderr/exception
  bodies. The provider patch is prepared, not installed into the learning app.

## Findings and required follow-up

1. **Host credential access is broader than the desired live boundary.**
   `CodexSandboxOffline` can read and modify the workspace OAuth file and private
   environment file through inherited FullControl. No exposure was observed,
   but a private config directory is not proof of isolation from coding tools.
   Before live preparation, restrict the auth directory and credential-bearing
   configuration to the intended user and SYSTEM, retaining provider login and
   refresh access. Verify both allowed access and sandbox-identity denial using
   a harmless canary before touching real credentials. Do not change the whole
   `.batch3-vibe` tree or break the learning workspace.
2. **Host evidence is mutable.** The same identity can modify attempt files;
   repository harness files also inherit Modify permissions for sandbox
   identities. Exclusive creation, fsync and recorded hashes prevent ordinary
   reuse and aid auditing, but do not make files immutable or establish a trusted
   host-code boundary. For a live attempt, seal reviewed code and reserved
   attempt inputs against worker/coding identities before dispatch; record and
   verify all executable source identities. Read-only container mounts do not
   prevent an authorized host writer from changing the underlying files.
3. **Live authentication is still a design/verification gate.** The offline
   container cannot contact OpenAI or access OAuth by design. Do not mount the
   profile or copy tokens into its packet, environment, artifacts or tool-visible
   files to make it work. Define a narrowly trusted authentication/transport
   boundary and test it with fake credentials first. Token refresh may require
   separate authentication HTTP requests; the cap is one inference request.
   Real endpoint output-cap compatibility and provider refresh/error behavior
   remain untested. The general learning agent is not the bounded proposal runner.

No ACLs, credentials, running services or VPS artifacts changed. Only this report
and the handoff were updated. Unknown OAuth monetary cost continues to block live
dispatch; actual Batch 2 cost/clock/prospective evidence and explicit human
promotion approval remain independent gates. A completed one-day smoke capture
would not complete Batch 2 qualification.
