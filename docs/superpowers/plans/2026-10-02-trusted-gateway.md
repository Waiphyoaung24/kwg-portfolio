# Trusted gateway controller — fake transport rehearsal

Implement a controller around the reviewed trusted OAuth core. The runnable
entry is synthetic-only; real dispatch retains its unconditional billing gate.

1. Validate the development packet and sealed code manifest. Reserve one directory
   keyed by the experiment manifest identity, using exclusive creation and fsynced
   metadata. Keep it after every outcome; retry, altered packet and concurrent
   invocation for that identity must fail before a worker is started.
2. Create the fixed Docker container, inspect its image, entrypoint, mounts,
   read-only/network-none/resource/user settings before supplying stdin. Start
   only the reviewed worker, with fake credentials generated inside it. Reuse
   invoke_bound; no SDK/token store, real HTTP, generated code or tools.
3. Enforce an overall parent deadline up to 180 seconds, bounded protocol, child
   watchdog, owned-container removal and verified absence. Persist safe status,
   usage, proposal and exact identities; never persist arbitrary error bodies.
4. Test reservation/no-retry, bad seals, response/account/usage checks and real
   fake-Docker success/401/account mismatch/timeout. Review, seal a new snapshot
   without changing earlier snapshots, and record the receipts.

Actual OAuth input, permitted production egress and USD0 backend enforcement
remain unimplemented/unverified. The fake controller is not permission to read
credentials or dispatch one real proposal. Batch2 remains development-complete,
unqualified; fixed risk limits and human promotion approval remain.

## Completed rehearsal

Current protected snapshot: .batch3-vibe/sealed-gateway-20261002-r2.
Manifest SHA256: 1fa75e9093140a8263cff5170bfc772a1e050a85fea31bc8498da4390103f4e6.
Success, 401, account mismatch, bad usage and timeout passed in real Docker with
fake-only HTTP and credentials. Replay refused. All owned containers removed.
Fresh scoped review found no Critical/Important issues. Oversized worker frame
regression fixed before parsing (RED to GREEN).

The first gateway snapshot exposed ignored default SIGALRM in a direct PID1
reproduction. Explicit signal handler fixed it; scaled one-second sealed-worker
check now exits2 with no output, independently of the parent deadline. Both
snapshots/receipts preserved. Docker documents PID1 default signal behavior in
[attach](https://github.com/docker/cli/blob/master/docs/reference/commandline/container_attach.md).
Context7 also verified network-none and read-only bind mount semantics.

Execution deadline excludes up to 30s cleanup. stdout capture assumes the fixed
sealed worker's output guard, not arbitrary executable output. Production flags
remain false; no real credential input or network egress was enabled.
