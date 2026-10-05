# Final real-development runner preparation — 2026-10-05 Bangkok

The distinct proposal runner is implemented, tested and sealed around the
verified real development packet. Native container isolation and independent
cleanup passed. **Activation remains blocked:** the actual coding command
currently runs with an unrestricted owner token and can open the private login
file. No credential contents were read during that diagnostic. Gate C is not
complete and one real proposal is not yet authorized.

## What is ready

`ops/trading/gold_proposal.py` reuses the inspected Docker/Squid topology,
watchdog, strict Responses stream core, separate network-none proposal parser
and Windows cleanup guardian. The original fake entry and legacy dispatch
refusal remain intact. Account acceptance now records the exact validated
registration hash, accepted time and account/client/host fingerprints so the
proposal runner can bind a later fresh acceptance to the same bytes.

The fixed request intent is:

| Setting | Sealed value |
| --- | --- |
| Model / reasoning | `gpt-6-astra` / `medium` |
| Route | `POST https://api.openai.com/v1/responses` |
| Calls | One; zero retries, redirects or fallback |
| Data | Existing 6,000-bar development summaries; no validation or reserved bars in prompt |
| Prompt / packet bytes | 2,267 / 1,708 |
| Proposal / stream / event limits | 16,384 / 262,144 / 65,536 bytes |
| Worker/controller deadline | 180 seconds; stream processing budget 120 seconds |
| Additional spending | $0, requiring fresh saved provider credit-prevention evidence |
| Tools / trading / promotion | Disabled; unqualified development proposal only |
| Storage / retries | `store=false`, streaming; unknown outcomes remain consumed |

The proxy permits public TLS to `api.openai.com:443` only and denies private
destinations. It does not inspect encrypted HTTP paths or enforce request count;
the sealed request core fixes the single POST. Only the trusted controller may
transfer the access token and bounded prompt through stdin. Worker mounts contain
specific read-only source files, without credentials, host home, Docker socket,
fake CA, dataset or baseline. The parser receives proposal text only and uses
`network=none`. No authentication refresh exists in this controller.

Before transfer, it requires exact input reproduction, passing native boundary
and termination receipts, fresh actual coding-token file denial, concrete owner
authorization, fresh provider UI evidence, and fresh signed account/catalog
acceptance bound to the current registration. Missing approval stops before
credential-store access, network creation or production reservation. The private
production reservation is atomic and keyed to the frozen experiment identity,
so a changed source seal or approval cannot silently retry the same experiment.
There is no approval-writing command or gate override.

## Source and input identities

Source commit: `dfb9454a81e9a301c80561de4371ffaefae25f78` on
`codex/batch3-supported-gateway`, locally committed only.

| Snapshot under `.batch3-vibe` | Manifest SHA256 | Files / code files |
| --- | --- | --- |
| `sealed-proposal-dfb9454a81e9` | `b00ee5256e16883f9bdc7866cdba1fa58d709ee114599c1cda7d8608eb6e87a5` | 84 / 73 |
| `sealed-supported-dfb9454a81e9` | `36ed1e27cd14de28fb5811da1b2d60968ddab39b96ad8ee7ccff37e6ede1986a` | 79 / 73 |
| `sealed-account-dfb9454a81e9` | `72da287687cdbd950a86c2b2c6442efb15d5c67ea74b36a7ec21ececab8591c3` | 79 / 73 |

Every listed file and all 73 working source matches were verified. The proposal
snapshot and all its children are owner/SYSTEM-only. It includes copies of the
real packet, prompt, frozen manifest and preparation receipt plus `inputs/intent.json`.
Large dataset and baseline files stay in the protected development directory;
the intent binds their exact hashes and the runner independently reproduces the
baseline and packet before use. The existing 1 MiB per sealed-file bound was not
weakened. Historical fake seals remain unchanged.

| Input | SHA256 |
| --- | --- |
| Sealed intent | `6f41f118325687093072eb72989d370d03c2dfdf25106d7dd2973207125750e1` |
| Real packet | `e6f2d78918772b3791b3451c70a326a3d24de2a95da3c332d44d720065e70038` |
| Real prompt | `cb4584ac365334f372a82a3b963bb806650c59ce9d84a8b23742f6145e12b9a7` |
| Frozen manifest file | `3fe09a21ceca7e4386dcb9ffb33102fe46ec139bda651e9ff41f7773622a6e81` |
| Dataset | `ba4f246746d861c9f61d82c7a09d17931cd74e9dea604ea2897853369dcf8614` |
| Baseline | `632a33fcb6a0adac8d3a5449aeebe8751479dbf8f81a880afae99eb301078c18` |
| Original offline preparation receipt | `1c93fc050b0de511e6fa635b157720c3be74a1832c7585cec90296bc6ee7f046` |
| Frozen experiment / durable production key | `216d3cdb2debbb67d748688225e55a3a4e346bffeb725c65abc86adbddcda62b` |

The prior inspection, reserved-period signal replay, unverified historical costs,
unqualified broker timestamps and assumed slippage limitations remain in the
packet and prompt. No qualification credit, candidate registration or promotion
was earned. See [real packet results](2026-10-05-batch3-real-packet-results.md).

## Verification and preserved failures

Six new proposal tests cover concrete approval and expiry, provider controls,
early refusal, signed-account receipt binding, experiment-wide reservation/replay
and host/live entry refusal. The 197-test workspace stdlib regression passed;
15 focused runner/account/transport checks passed. Four separate existing
signature and registration checks passed with fake keys.

All 14 native fake transport cases passed, including one-post success, 401,
malformed/truncated streams, bad usage, redirect refusal, identity/client/expiry
refusal, crash, watchdog timeout/trickle and pre-transmission interruption.
Every case refused replay and verified cleanup.

The final proposal worker passed native read-only/missing-mount probes,
host/peer isolation, direct IPv4/IPv6 Internet and DNS denial, proxy domain,
address, port and plaintext denial, and rejection of an untrusted TLS context.
Unrestricted controls reached the host service, Internet and both peer address
families. The isolated worker's default-CA, unauthenticated model-route GET
returned 401; no body or credentials were read. Account defaults also passed
native boundary checks using public signing keys, without renewal or catalog
authentication. Both controllers were then forcibly terminated after synthetic
input transfer, and independent guardians removed owned containers/networks.
These are container proofs, not proof of the coding process's Windows isolation.
Global IPv6 Internet reachability was not separately established by a positive
control; the dual-stack peer controls and absent IPv6 default route were tested.

A direct `-I` invocation of the older fake harness failed before importing its
dependencies or reserving an attempt. Its existing isolated bootstrap then ran
the full matrix successfully. A wholesale full-suite run from the source-only
seal also failed: 193 tests ran with five errors and one failure because older
tests expect the repository-relative upstream provider and `desktop.sh`. This
layout limitation is preserved; the full suite is verified in its intended
workspace layout and focused runner checks use the sealed source. No legacy
test/runner paths were refactored to hide it.

The fresh default-tool open-only probe found `token_restricted=false`,
`registration_open_denied=false` and `canary_open_denied=false`. Handles were
closed without reading bytes. The failed diagnostic is retained separately;
the passing coding-denial evidence path is absent. Owner/SYSTEM ACLs passed,
but they cannot deny the owner token currently used by this session. Do not
change credential ACLs to deny their legitimate owner or treat container
isolation as a substitute for this missing host proof.

Private receipts under `.batch3-vibe`:

| Receipt | SHA256 |
| --- | --- |
| `proposal-readiness/<proposal seal>.preparation.json` | `5ac92694ab4e555e929984318c9ff05c66c562a574f37116d9feac1d32df738b` |
| `proposal-readiness/<proposal seal>.boundary/receipt.json` | `cc1c4aa858683cf66d30dc8c34ff01771f6df9e5b29bcdf3e7ee64dcfac3ff7a` |
| `proposal-readiness/<proposal seal>.termination/receipt.json` | `894918e7f09f0e3f46b72ff170a3107d41f0e6297cfa836f79691a352252eb5e` |
| `proposal-readiness/<proposal seal>.coding-denial.failed-20261005.json` | `1eeac2055d9c8340cf3a11c166b486d2b1e9d90f18d3481894b9381254c6cdd5` |
| `supported-readiness/<supported seal>.receipt.json` | `a8e371fff505a5b934ca0b5bb5fe844e927af6326e5c360c679f5a76eb6bab7d` |
| `account-readiness/<account seal>.boundary/receipt.json` | `a722bbcb0bd9963de9e6bdc83f33316acdfaf82c3760fcb0810a820845b0ba90` |
| `account-readiness/<account seal>.termination/receipt.json` | `a127408967ee34d7386df796f449c1f015fb43c4f84b2cdb4fef5d8e28daddad` |
| `proposal-readiness/<proposal seal>.tests.json` | `a86ba24a6053819d824024baa5549ea29a6b5a7b643723e33200d2856b46137c` |
| `proposal-readiness/<proposal seal>.relocated-suite.failed.json` | `fed59c24679d36fbcb0176c6d02275c3e0becc95cf2834bf0915cbb4196522de` |

`<proposal seal>`, `<supported seal>` and `<account seal>` mean the full manifest
hashes above. An owner-context verifier reread ACLs, all three seals and input
reproduction, checked receipts and owned resources, and exercised the actual
sealed dispatch CLI with approval absent. It exited 2 and left the production
registry empty. Failed checks, synthetic attempts and receipts are preserved.
The separate test receipt confirms a fresh final-source 197-test workspace pass
and 15-test sealed pass, with private captured logs; it preserves the relocated
full-suite failure separately in `<proposal seal>.relocated-suite.failed.json`.

## Resume order

1. Restore/use an actual restricted coding session and run the open-only canary
   and registration probes there. Capture fresh real denial evidence; do not
   read or paste credentials. This environment is currently the blocker.
2. Keep this source/input seal and the evidence above. If executable sources
   change, commit and create new snapshots, then rerun affected native checks;
   do not overwrite consumed attempts or seals.
3. Review the concrete intent above with the owner. Before any separately
   authorized account acceptance/request, recheck the saved provider $0 controls
   and same-account/client/host identity. The current token is expired; no
   renewal was performed in this preparation milestone. Final account boundary
   and termination tests are ready, but its authenticated acceptance receipt
   has not been created.
4. Only after all prerequisites and explicit one-proposal authorization are
   satisfied may the owner-private, short-lived approval and fresh UI/denial
   evidence be recorded and the durable single attempt dispatched. The runner
   cannot fix the host execution policy or renew auth by itself. Unknown or
   failed production outcomes stay consumed.
5. After a valid proposal, separately run the existing fixed-baseline comparison
   and retain diagnostics for human review. A favorable development result
   still grants no qualification, promotion or trade authority.

This milestone made zero real model requests, OAuth renewals or authenticated
catalog requests. It changed no credit/provider/SSH settings, broker state or
orders, and made no deployment or push. Existing Docker Desktop was started
hidden for the native tests; cached pinned images were used with `--pull never`.
All production acceptance flags remain false and the production registry is
empty. Batch 2 qualification remains deferred; unrelated working changes remain.

Ponytail and the earlier converged brainstorming plan supplied the reuse-first
scope. Context7 reconfirmed primary HTTPX documentation on
[`trust_env=False`](https://github.com/encode/httpx/blob/master/docs/environment_variables.md),
[per-operation timeouts](https://github.com/encode/httpx/blob/master/docs/advanced/timeouts.md)
and [transport retries](https://github.com/encode/httpx/blob/master/docs/advanced/transports.md).
These describe client behavior and do not replace native isolation or the
[provider's credit controls](https://help.openai.com/en/articles/20001542-using-your-chatgpt-plan-in-other-apps-and-sites).
