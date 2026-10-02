# Current trusted transport seal

Reuse harden-batch3.ps1 with a separate fixed seal-current phase. Preserve the
earlier snapshot and OAuth/config files. Snapshot current offline tools and the
already-recorded synthetic -03 success packet/request/provider/attempt. These
are rehearsal inputs, not a real gold proposal authorization.

Verify copied source hashes before sealing and all manifest hashes afterward;
owner/SYSTEM full access, coding sandbox read/execute only. Run trusted transport
fake tests from that exact snapshot, using the frozen prepared provider.
Recheck coding-sandbox write denial without modifying bytes.

This prepares a current code seal. It does not prove Windows owner-process
credential containment or a production outer deadline, server authentication,
backend billing or eligibility for live dispatch. Production stays disabled.

Completed: 62-file snapshot verified, three sealed transport tests passed,
coding sandbox write denied. Fresh review's three Important findings fixed:
private staging before copy, stable source handles/full reparse checks, pinned
input/upstream identities and attempt cross-checks. Harmless writer/junction/
exclusive-copy checks passed. Exact sealed fake core passed Docker read-only
and no-network probes; inspected fixed UID/resources/mounts/image, timeout and
cleanup verified. Both cases model_requests=0. Production assertions remain false.
Receipts: .superpowers/sdd/current-transport-seal-20261002/.
