# Using the local Vibe-Trading workspace

This is the existing upstream product, v0.1.15, running at
[Local Vibe-Trading](http://127.0.0.1:8899/). KWG Gold operations remains the
read-only operating frame and links to it. The upstream app keeps its own UI;
we do not duplicate its researcher, reports or strategy editor in Astro.

Owner authorized normal AI learning demos after OAuth login. These may make
multiple model requests and use upstream tools; they are separate from the
one-request Batch 3 gold comparison. No gold candidate, real broker import,
orders, risk changes or promotion are authorized by learning tests.

## 1. Sign in locally

An interactive PowerShell login terminal was opened for this step. If it was
closed, run these commands in your own PowerShell window:

```powershell
Set-Location -LiteralPath 'C:\Users\wai19\Desktop\kwg-portfolio'
python -B ops/trading/vibe-workspace.py login
```

This calls upstream `provider login openai-codex` using the prepared source and
the existing dependency runtime. The child environment excludes inherited API,
MCP and broker credentials and uses `.batch3-vibe/profile` as its home. Follow
the browser sign-in and paste any requested callback URL into that terminal
only. Never send callback URLs, token files or authentication screenshots to chat.
No `OPENAI_API_KEY` is required.

If login succeeds but Agent still says **not logged in**, check which command
was used. A bare `vibe-trading provider login openai-codex` from the ordinary
Windows profile saves to `C:\Users\wai19\.vibe-trading\auth\openai-codex.json`.
Our running app uses
`C:\Users\wai19\Desktop\kwg-portfolio\.batch3-vibe\profile\.vibe-trading\auth\openai-codex.json`.
Those are distinct sessions. Use the launcher above (or its absolute path
from any directory) to sign in for this app. Do not copy rotating tokens between
stores. Refresh Settings after the workspace login succeeds; restart is not
required. Keep the failed chat and test again in a new learning chat.

After login, refresh **Settings** at `http://127.0.0.1:8899/settings`.
Provider should be **OpenAI Codex (ChatGPT OAuth)**. The selected learning model
is **openai-codex/gpt-6.1-sol**, explicitly requested by the owner, with
**medium** reasoning, outer
retries 0 and timeout 120 seconds. Selection is verified; account availability
is not verified until a successful reply. OAuth model discovery is unsupported
in this product; an empty discovery list does not prove access is absent.
If that model is unavailable, preserve the error and choose an available model
explicitly in Settings; do not silently fall back or change the Batch 3 model.

## 2. Test one simple reply

Open **Agent**, start a new chat and send:

> This is a learning test, not trading research. Reply exactly: Vibe learning workspace ready. Do not call tools, fetch data, generate or execute code, or place orders.

Expected: one plain text reply. Check the tool/activity trace; a tool call or
provider error means this test did not meet that expectation. Do not repeatedly
resubmit a stalled message; inspect **Runtime** and the existing session first.
These prompt instructions are not an enforced tool sandbox or HTTP budget.

Before sending, confirm Settings and the new Agent session show GPT-6.1 Sol
and medium reasoning. Use a **new** chat after changing models; an already
running session can retain its existing model instance. Where Runtime/session
metadata includes the returned model, check `gpt-6.1-sol` there. Do not ask the
assistant which model it is as verification: its text is not backend evidence.
If the backend returns model-unavailable/access-denied, the learning test has
failed; preserve the error and do not silently switch models. Settings and
synthetic request-shape checks prove selection, not account entitlement.

The requested identifier and medium reasoning support were checked against
[OpenAI's GPT-6.1 Sol documentation](https://developers.openai.com/api/docs/models/gpt-6.1-sol).

## 3. Practice a synthetic upload

Create another learning chat. Attach:

`C:\Users\wai19\Desktop\kwg-portfolio\ops\trading\fixtures\vibe-learning-trades.csv`

Then send:

> Using only the attached CSV, calculate row count, sum of net_pnl_usd, count of positive values and arithmetic mean. Return only JSON with keys row_count, sum, positive_count, mean. Round mean to two decimals. Do not include dates, instrument names or additional commentary. No external data is needed.

Expected: **6 rows**, **USD 130 total**, **3 positive rows**, **USD 21.67 mean**
(rounded). The fixture is synthetic and insufficient to establish strategy
quality. There is no real account, gold dataset or performance claim.
Live upload-to-answer test passed on 2026-10-01 with provider-response model
`gpt-6.1-sol` and medium reasoning. Reopen the verified
[synthetic CSV session](http://127.0.0.1:8899/?session=0edab1e6d735).
Its trace includes two recovered path errors before successful document reading
and arithmetic; final numbers match the fixture. A fresh chat must have its own
attachment before sending this prompt.
Use a fresh chat for this arithmetic test. Observed v0.1.15 behavior rejects a
CSV-derived “win rate” as unsupported analysis evidence; recovery messages then
cause repeated refusals. The trace confirms the attachment was read and values
computed, but the final figures were blocked. The plain JSON arithmetic answer
avoids that misclassification; no grounding safeguard is disabled.
Use the built-in history to reopen the chat and inspect the response/tool trace.
If a report artifact was actually produced, inspect it in **Reports**; do not
assume every reply creates one. **Runtime** shows the product's run state, not
our Batch 2 qualification verdict.

## 4. Learn the remaining product surfaces

### Inspect the Batch 2 / Batch 3 synthetic comparison

The existing `rehearse-batch3.py` now also exports `comparison.csv`: six rows
from the actual synthetic baseline/comparison reports, with explicit
synthetic/unqualified/blocked labels. Its byte hash is in `comparison.json`.
No broker data, credentials, generated code or live model request is used to
produce the file. The fixed fixture proposal is plumbing, not research.

In a new Vibe-Trading learning chat, upload that CSV from your latest private
rehearsal directory. Use this arithmetic-only prompt:

> Use only the attached fictional CSV. For rows whose window is validation,
> return one JSON object with row_count and a differences_by_scenario object
> mapping each scenario to candidate_net_pnl_usd minus baseline_net_pnl_usd.
> Also return qualification and promotion_status exactly as written in the
> CSV. Do not fetch market data, resolve instruments, generate a proposal,
> run backtests or place orders. These are synthetic arithmetic fixtures.

Expect three validation rows, the saved per-scenario differences, qualification
unqualified and promotion_status blocked. A correct reply verifies learning-app
file reading/arithmetic only. This manual chat can make multiple model calls;
it is separate from the bounded one-request gold experiment. Use the configured
gpt-6.1-sol / medium settings and inspect Runtime for actual provider metadata.
If a tool tries unrelated market-data recovery, preserve the trace and stop
that learning test; do not relax tool permissions or feed it real broker data.

Broker-support confirmation may be deferred for these learning demos as the
owner requested. Batch 2 is closed for development with qualification deferred.
Real report provenance, production credential/network isolation, backend USD0
enforcement for gold dispatch and human promotion approval remain gated.

- **Agent:** questions, attachments and session history. Begin with synthetic
  examples; retain failed runs and their trace.
- **Reports / Runtime:** inspect generated evidence and progress. Product
  backtests are exploratory and do not substitute for our fixed evaluator.
- **Alpha Zoo / Options Lab:** browse the existing catalog. Starting analysis,
  sweeps or backtests is separate from these first learning tests.
- **Portfolio / broker connectors:** leave unconfigured. Do not attach MT5,
  import real account histories, submit orders or enable live execution.
- **Scheduled:** leave off. Scheduler, shell tools and automatic channels remain
  disabled in the launcher. Do not create scheduled work during these tests.

The upstream README includes research and backtest examples. We reuse that
product, but its normal agent loop is not the qualified gold pipeline. Once
Batch 2 is ready, gold input goes through our verified development-only adapter,
bounded one-proposal controller and existing simulator/evaluator. Human approval
is required for exact candidate artifacts before later observation/promotion.

## Restart and status

The current app is already running. Do not start a second server on port 8899.
After it has exited, start it in a terminal with:

```powershell
python -B ops/trading/vibe-workspace.py serve
```

Use Ctrl+C in that server terminal to stop this local app. This command does
not touch MT5 or the VPS. Saved model settings load from the private workspace;
the launcher does not inherit another model from your shell.

```powershell
python -B ops/trading/vibe-workspace.py status
```

Status verifies tracked agent files and rejects extra Python/native modules,
including ignored ones. It does not attest dependency or built-frontend
integrity. It reports OAuth **file presence**, not token validity,
model access or live server health. Do not open or print the credential file.
The private profile is configuration isolation, not an OS security sandbox;
normal product tools are not a qualified Batch 3 execution environment.

## Verified setup and remaining project gates

Verified: upstream CLI help in the isolated environment, loopback product UI,
settings save with the explicit model, clean-environment/source-guard checks and 128
trading Python tests. Login completion and successful learning replies require
the owner's interaction; neither is claimed yet. No model request was made by
the setup work. All private state remains Git-ignored.

Batch 2 costs/clock, prospective sample/folds and real-report provenance remain
unqualified. The adapter request-limit patch and durable synthetic attempt
checks are preparation, not a connected production controller. The running app
still uses its ordinary upstream behavior. Smoke completion does not waive any
of those gates. See the
[connection checkpoint](../../docs/superpowers/plans/2026-10-01-gold-batch3-connection-checkpoint.md).

Reference: [upstream README](https://github.com/HKUDS/Vibe-Trading/blob/main/README.md)
and the local pinned v0.1.15 source. Current-main instructions can differ from
the installed release; the launcher explicitly binds 127.0.0.1.
