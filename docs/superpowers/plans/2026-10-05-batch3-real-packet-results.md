# Batch 3 — verified real development packet

Date: 2026-10-05, Asia/Bangkok. The original export is now accessible locally;
the current frozen manifest, reproducible baseline and real development packet
are prepared. **Gate C remains incomplete:** final real inference implementation,
isolation acceptance, runner/input seal and concrete owner authorization remain.
No model request ran.

## SSH and source data

The owner entered the existing key's passphrase directly in a visible PowerShell
SSH prompt. One authenticated read copied the retained VPS export from
`/opt/kwg-gold-research/datasets/gold-history-20260928.json` to the protected local
development directory. SSH returned exit 0. Both the remote read command and
local verification required the original recorded checksum; no SSH configuration,
agent service, VPS file, service or broker state was changed.

Local file: `.batch3-vibe/gold-development/gold-history-20260928-ssh-20261005.json`.
Size: 1,273,818 bytes. SHA256:
`ba4f246746d861c9f61d82c7a09d17931cd74e9dea604ea2897853369dcf8614`.
This is the existing frozen export, not a new capture or substituted fixture.

Private SSH receipt: `.batch3-vibe/gold-development/ssh-read-20261005.json`,
SHA256 `c53fc5c3f35d028becd1b20dbce3d71fcab355e0f480655e5534e7a89db21561`.
Passphrase/key contents were not captured in the receipt or tool output. The
SSH agent remains disabled; this successful interactive read does not establish
unlocked keys or unattended SSH access for later commands.

## Committed tools and artifact identity

Preparation reused source commit `e75e515e09a6bfa115d7e593173262d9e0deacac`.
The existing sealer produced `.batch3-vibe/sealed-supported-e75e515e09a6`,
manifest SHA256
`dd0f7abeb9dcea9eef2c230bcb11b4e348fe8c5fd9dd5db6009098be467f4ea8`.
All 77 manifest files verified and all 71 snapshotted code files matched working
sources. Its metadata remains `supported_fake_only`: this is a source snapshot
used for offline preparation, not a final real inference seal.

Existing sealed `compare-gold.py` commands prepared and froze the current
manifest. Two isolated `simulate-gold.py` processes produced byte-identical
baseline reports. The sealed adapter independently recomputed the full baseline
again before accepting the inputs and producing the packet/prompt.

Private input directory:
`.batch3-vibe/gold-development/real-inputs-e75e515e09a6`.
Private packet directory:
`.batch3-vibe/gold-development/real-packet-e75e515e09a6`.

| Artifact | File SHA256 |
| --- | --- |
| Prepared manifest | `25a2d40a9104c0cdea95ffb05a74f6dc6e3e62c37818d6c880805a8905b0e9e2` |
| Frozen manifest | `3fe09a21ceca7e4386dcb9ffb33102fe46ec139bda651e9ff41f7773622a6e81` |
| Baseline A and B | `632a33fcb6a0adac8d3a5449aeebe8751479dbf8f81a880afae99eb301078c18` |
| Packet and prompt's packet copy | `e6f2d78918772b3791b3451c70a326a3d24de2a95da3c332d44d720065e70038` |
| Adapter audit | `4a658a895c6d1d43bb9cacd4c319df1be44abfd4d9a2229a79b26032040bb7a7` |
| Prompt text | `cb4584ac365334f372a82a3b963bb806650c59ce9d84a8b23742f6145e12b9a7` |
| Prompt preparation result | `f44b7517e41a49fc5bba973877b691ffb583d4f89f1b895cc8c5a0bde52435d2` |

Private preparation receipt: `real-inputs-e75e515e09a6/preparation-receipt.json`
under the development directory, SHA256
`1c93fc050b0de511e6fa635b157720c3be74a1832c7585cec90296bc6ee7f046`.
Its readback, recorded artifact hashes and every output file's owner/SYSTEM ACL
verified. Operational orchestration scripts remain ignored under
`.superpowers/sdd/gold-development-preflight-20261005/`; they are not part of a
production inference seal. No private dataset, manifest, baseline or prompt is
committed to Git.

## Packet scope and verification

The packet summarizes the first 6,000 bars, including warmup and 66 recorded
development gaps, with development baseline metrics only. It contains no raw
validation/reserved bars, validation performance or account data. The newest
2,000 bars remain excluded from trade simulation. Baseline holdout metadata is
exactly `start_index=8000`, `bars=2000`, `evaluated=false`.

The prompt rebuilt byte-for-byte from the validated packet. The prompt's packet
copy equals the standalone packet bytes. Risk/policy pins and the proposal schema
remain unchanged: one EMA20 slope-filter lookback from 2 through 5, with no risk,
order or promotion authority. No candidate has been requested or registered.

Retained limitations: `validation_previously_inspected`,
`reserved_bars_signal_replayed`, `historical_costs_unverified`,
`broker_timestamps_unqualified`, `slippage_assumed`. Costs remain hypothetical,
the baseline and packet are unqualified and broker provenance is not promoted
by matching a checksum. The reserved period was previously signal-replayed;
it is not a newly untouched qualification holdout.

This milestone ran actual-data offline CLIs and artifact checks. The preceding
[191-test regression and native synthetic adapter checks](2026-10-05-batch3-real-development-preparation.md)
are still applicable to the unchanged source commit; they were not rerun here.
No Docker runtime acceptance test or authenticated model catalog ran today.
Direct supported dispatch still refuses, and the production registry is empty.
OAuth credentials were not renewed; no model, credit/settings, trading,
deployment or push action ran.

## Next milestone — final isolated proposal runner

The data-access blocker is resolved. Reuse this verified private packet and
baseline when preparing the smallest distinct real execution path. Existing
account/fake snapshots remain their original scopes; never remove a fake guard
or relabel that snapshot as an enabled real gateway.

Finish fixed real transport/controller binding, the credential-free parser,
durable single-attempt reservation and independent termination cleanup. Verify
the actual credential/filesystem/network boundary with fake credentials and
freeze the exact final runner plus input identity. The earlier host command
could open owner credentials, so restricted-token denial remains unproved; see
the [spending checkpoint limitation](2026-10-05-batch3-zero-spend-results.md).

Only after preparation is concrete and reviewed should the owner authorize one
`gpt-6-astra`/medium proposal. Immediately before that attempt, recheck provider
$0 settings and expired login through the reviewed same-account path. No retry,
fallback, tools, orders or automatic promotion. Batch 2 qualification stays deferred.
