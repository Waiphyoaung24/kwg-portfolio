# Gold offline experiment: verified baseline, research pending

The frozen 10,000-bar `XAUUSD-VIP` dataset was replayed on the private VPS.
The baseline is reproducible, but it lost money in the validation window under
all three hypothetical cost scenarios. No Vibe-Trading proposal or candidate
comparison exists. This is an **exploratory, unqualified** result; no orders or
promotion are enabled.

| Scenario | Development trades / net P&L | Validation trades | Validation net P&L | Validation return | Validation profit factor |
| --- | ---: | ---: | ---: | ---: | ---: |
| Lower | 82 / +$410.97 | 30 | -$305.19 | -0.305% | 0.811 |
| Middle | 83 / +$6.43 | 31 | -$445.94 | -0.446% | 0.746 |
| Stress | 78 / +$63.33 | 30 | -$186.87 | -0.187% | 0.882 |

The dataset, manifest, reports, and research input remain private under
`/opt/kwg-gold-research/experiments/gold-exp-001/`; they were not committed to
Git. Their SHA-256 hashes are:

| Artifact | SHA-256 |
| --- | --- |
| Dataset (`gold-history-20260928.json`) | `ba4f246746d861c9f61d82c7a09d17931cd74e9dea604ea2897853369dcf8614` |
| Prepared manifest | `fc1c68ddc38d33cb737f8de10e746ffd6d54928fe23afeb5f4611b81649775cf` |
| Frozen manifest | `01f7c2c698e28474af9fd4398004e2a50331934a6df32b4b03e63ec8c3708291` |
| Preliminary baseline, both runs | `b76038559c176339f1caa9e73be2cca4d3f21ea5d0b5ae7608155b6d473aaa7e` |
| Final baseline, both runs | `50de8aa4c4fbeaa4a5c4e825faaf78aeb0b13c7996e261d61eecc7d9f08c31ef` |
| Development-only research input, both copies | `91006f70968b1c8d6641f6175f4111fb245f91246e466953934c99a49bea891f` |

The two preliminary reports matched byte-for-byte; the two final reports also
matched byte-for-byte. Preliminary and final `runs` were equal. Final reports
state `qualification="unqualified"`, `cost_profile_status="hypothetical"`, and
reserve the newest 2,000 bars without trade simulation. The research input
contains development information only. Its existing file matched a freshly
generated copy byte-for-byte; the first attempt to recreate it raised
`FileExistsError` because outputs deliberately refuse overwrites.

The six evaluator source hashes on the VPS matched the reviewed files from
commit `e7f313a`. The full local trading suite passed 47 tests. Earlier
validation trade results had already been inspected, so this is not an
independent holdout. Historical broker costs and raw broker timestamp semantics
remain unverified; the long live collector ended after 57 accepted samples
with a disconnected MT5 terminal. The hypothetical scenario named “stress” is
not a verified upper bound on actual costs.

**Research state: `research_connection_blocked`.** Vibe-Trading is not installed
on the VPS. The local Windows `vibe-trading` 0.1.15 has no verified Claude/Worker
inference route or enforceable two-request/8,000-token cap. No model request,
proposal, candidate run, or comparison was made. Installing the CLI alone would
not satisfy the model-route gate. Even if a proposal is later compared on this
same dataset, the predeclared 100-validation-trade minimum cannot be met by
this baseline's 30–31 trades; the exploratory verdict would be inconclusive.

Next, verify a supported bounded model route before running one research job.
For any claim beyond exploratory research, collect independent data and dated
broker costs, and complete live quote/candle qualification. None of these steps
authorizes trading.
