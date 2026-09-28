# Gold offline experiment: implementation status

The offline experiment commands are implemented and locally tested. **No real
experiment verdict exists yet.** The frozen broker dataset and detailed reports
remain on the private VPS. The owner ran `sha256sum` there and verified the
dataset SHA-256 as
`ba4f246746d861c9f61d82c7a09d17931cd74e9dea604ea2897853369dcf8614`.
The six Python files from commit `e7f313a` were downloaded to the private
`gold-exp-001/src` directory and their hashes matched the reviewed Git blobs.
Manifest preparation passed on the real 10,000-bar dataset; private
`manifest-prepared.json` has SHA-256
`fc1c68ddc38d33cb737f8de10e746ffd6d54928fe23afeb5f4611b81649775cf`.
The two preliminary baseline runs and final freeze are pending. No dataset was
re-exported or copied into Git. Automated SSH cannot unlock the encrypted key,
so private VPS commands are run in the owner's authenticated shell.

The tools now prepare and freeze an exact 10,000-bar manifest, pin 60/20/20
indices and every evaluator source hash, replay an entry-only EMA20 slope
filter, require a registered proposal before candidate simulation, and compare
both runs against the same manifest. Source-data and report outputs use
exclusive creation. A synthetic end-to-end CLI run completed with verdict
`inconclusive` and `promotion_status=blocked`; it is a plumbing check, not a
gold result. The full local trading suite passed 47 tests. No MT5 or order
command is used by these tools.

The previous real baseline, from the same dataset under an older evaluator
revision, had only 30–31 validation trades and lost under all three hypothetical
cost scenarios; see [the prior result](2026-09-28-gold-baseline-results.md).
That run is context, **not** a reproducibility check of this revision. Given
the predeclared 100-trade threshold, a candidate compared on this dataset
would be `inconclusive` even if its simulated return improved. Historical
broker costs, raw timestamp semantics, and two-boundary live qualification
also remain unresolved. The newest 2,000 bars are reserved from trade
simulation, though earlier signal replay saw them.

The installed local `vibe-trading` is version 0.1.15. Its documented
`run -f ... --json --max-iter N` interface is present, but `provider doctor`
reported default OpenAI routing, no selected model, and no configured key.
The owner's Claude/Worker MCP token has not been shown to provide a compatible
Vibe-Trading inference endpoint. The CLI help exposes an iteration limit but
no explicit combined-token or model-request cap for this run. State:
`research_connection_blocked`; no model request or proposal was made, and no
lookback value was chosen from validation results. The upstream
[Vibe-Trading agent instructions](https://github.com/HKUDS/Vibe-Trading/blob/main/agent/SKILL.md)
describe the CLI/MCP interface and distinguish the optional model-powered
features.

The next checks are: run the preliminary baseline twice and compare bytes,
finalize the manifest, rerun baseline twice and compare bytes and metrics.
The development-only research input can then be generated.
Only a supported, bounded Vibe-Trading model route justifies one genuine
proposal; otherwise leave the result as blocked. A valid proposal must be
registered before its one candidate run. No finding from this experiment
enables orders or promotion.
