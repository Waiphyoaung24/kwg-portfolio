# Trading Agent Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Meet the five foundation criteria from the 2026-10-08 `ops/trading` review so a self-improving gold research agent can be built on evidence instead of ceremony.

**Architecture:** Keep the existing MT5 runner, status server, Worker and page. Add one shared status contract fixture that all three test suites read, one browser test of `/vault/trading`, two security preconditions, an owner-run live data check, and a deterministic development-only grid plus a pre-registered prospective holdout that replaces the LLM proposal path until data can support it.

**Tech Stack:** Python 3.12 stdlib (`unittest`, `runpy`), Node `node:test`, Cloudflare Worker, Astro 6 (node adapter), repo `e2e` runner, Docker Compose on the VPS, MetaTrader5 Python package under Wine.

**Spec:** The 2026-10-08 review (multi-agent: skeptic, constraint guardian, user advocate; arbiter disposition REVISE). The five criteria it set:

1. Status data is confirmed fresh across two live M15 boundaries.
2. One shared status fixture is used by the Python, Worker and frontend tests.
3. One read-only end-to-end test covers `/vault/trading`.
4. The research loop runs on one supported machine against new data the agent never sees.
5. The agent can only output parameters within a fixed schema, never holds control secrets, and promotion stays manual.

## Global Constraints

- Gold only: `XAUUSD-VIP`, VT Markets **demo** account only. No live account, ever, in this plan.
- No task enables Algo Trading, places an order, or adds an agent-callable order path.
- Do not shift timestamps, guess a broker offset, or relax the 30-second freshness limit to make a check pass.
- Never put broker credentials, SSH keys, Access tokens or `TRADING_CONTROL_SECRET` in Git, chat, shell history, images or logs.
- Do not change `evaluation-policy.json` or the risk constants; `research-gold.py` pins their SHA-256 (`POLICY_SHA256`, `RISK_SHA256`).
- The reserved newest 20% of the frozen dataset and the already-inspected validation window stay out of any new selection step.
- The VPS is deployed directly; a Git push does not update it. Preserve the `mt5-home` volume and existing Dokploy apps.
- Site chrome follows `DESIGN.md`: weight 400, pills, no raw hex/px in components. Copy changes only use existing primitives.
- Python tests run with `python3 -m pytest -q -p no:cacheprovider` from `ops/trading`. Node tests run with `node --test`.

## Review Focus

- **Status JSON drift between layers** (e.g. a new field like `bid`/`ask` added in Python but dropped by the Worker): expected to fail one shared contract test. Pinned in Task 3.
- **Manual demo order open while the observer reports "orders off"**: the page must not claim orders are off. Pinned in Task 4.
- **Signed-out or 302 response from `/api/trading/status`** in the browser: the page must show the sign-in link, not stale numbers. Pinned in Task 5.
- **Broker clock offset change at the late-October daylight-saving switch**: the qualification must be rerun after the switch rather than trusted across it. Pinned in Task 8.
- **Grid step reading validation or reserved bars**: must be impossible by construction. Pinned in Task 10.

---

## Phase A — Truth and housekeeping

### Task 1: Decide the unmerged receipt reliability fix

The branch `origin/codex/batch3-receipt-reliability` (commit `68b7850`) moves proposal setup and guardian start-up inside the receipt lifetime and fails closed on missing or malformed `cleanup.json`. On `main`, a setup failure can leave a consumed attempt with no `receipt.json`.

**Files:**
- Modify (via merge): `ops/trading/gold_proposal.py`, `ops/trading/test_gold_proposal.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `main` either contains `68b7850` or `HANDOFF.md` records why not.

- [ ] **Step 1: Read the diff**

Run: `git diff main...origin/codex/batch3-receipt-reliability -- ops/trading/gold_proposal.py ops/trading/test_gold_proposal.py`
Expected: changes confined to the two files (126 insertions, 50 deletions).

- [ ] **Step 2: Run the proposal tests on the owner's Windows machine**

These tests import `msvcrt` and cannot run on macOS or Linux.
Run (Windows, repo root): `git checkout origin/codex/batch3-receipt-reliability -- ops/trading/gold_proposal.py ops/trading/test_gold_proposal.py; cd ops/trading; python -m pytest -q test_gold_proposal.py`
Expected: all pass (commit message says 43 fake-only tests).

- [ ] **Step 3: Merge or record rejection**

If Step 2 passed:
```bash
git checkout main
git merge --no-ff origin/codex/batch3-receipt-reliability -m "Merge receipt reliability fix for proposal setup failures"
```
If it failed, discard the checkout (`git checkout main -- ops/trading`) and add one line under "Now" in Task 2's block: `Receipt fix 68b7850 not merged: <failing test name>`.

---

### Task 2: Make the docs match what is deployed

`CLAUDE.md` says "no order execution is deployed" and "Order execution stays off", but manual demo pending orders have been deployed since 2026-09-29 (`ops/trading/README.md:336`, `src/pages/vault/trading.astro:69-104`). `HANDOFF.md` is 2,203 lines with 19 "Current/Latest" headings and does not mention PR #9.

**Files:**
- Modify: `CLAUDE.md` (trading handoff section only)
- Modify: `ops/trading/HANDOFF.md` (prepend one block; rename one heading)

**Interfaces:**
- Consumes: Task 1 outcome.
- Produces: a single `## Now / Running / Next` block at the top of `HANDOFF.md` that later tasks append to.

- [ ] **Step 1: Correct the order-execution statements in `CLAUDE.md`**

Replace the sentence `Algo Trading remains off; no order execution is deployed.` with:
```markdown
Algo Trading stays off for observation. Manual, owner-confirmed demo pending
orders (preview → single-use token → arm) have been deployed since 2026-09-29;
there is no automatic or agent-initiated order path.
```
Replace `Order execution stays off.` with `Automatic order execution stays off.`

- [ ] **Step 2: Prepend the status block to `HANDOFF.md`**

Insert directly under the `# Gold trading handoff — 2026-09-28` title:
```markdown
## Now / Running / Next — updated 2026-10-08

**Now:** `main` at `2d031cc` (PR #9: demo monitor, validated bid/ask, synthetic replay).
Foundation plan: [2026-10-08-trading-agent-foundation.md](../../docs/superpowers/plans/2026-10-08-trading-agent-foundation.md).
**Running on VPS:** MT5 desktop (demo), signal-only observer, status sidecar, Worker, manual demo pending-order controls. Algo Trading off.
**Next:** foundation plan Phase B (shared status fixture, page e2e test).
**Blocked:** live freshness (needs an open session), Batch 3 proposals (paused by the foundation plan).

Everything below this block is history. Read it only for a specific record.
```

- [ ] **Step 3: Mark the old top section as history**

Change the heading `## Current candidate — October 7: diagnostics reviewed; frontend acceptance next` to `## Historical: October 7 candidate — diagnostics reviewed`.

- [ ] **Step 4: Verify**

Run: `grep -c "^## Current" ops/trading/HANDOFF.md; grep -n "no order execution is deployed" CLAUDE.md`
Expected: the second command prints nothing. Remaining "Current" headings are deep history and stay as written.

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md ops/trading/HANDOFF.md
git commit -m "docs(trading): state deployed manual demo orders and add Now/Running/Next"
```

---

## Phase B — Criteria 2 and 3: one contract, one browser test

### Task 3: Shared status contract fixture (criterion 2)

Today `test_status_server.py`, `worker/test.mjs` and `src/scripts/trading-status.test.mjs` each hand-write their own JSON. One fixture file, read by all three, makes drift between layers fail a test.

**Files:**
- Create: `ops/trading/fixtures/status-contract.json`
- Modify: `ops/trading/test_status_server.py` (add one test)
- Modify: `ops/trading/worker/test.mjs` (add one test)
- Modify: `src/scripts/trading-status.test.mjs` (append assertions)

**Interfaces:**
- Consumes: `read_status(path, now, *, execution_path)` from `status_server.py`; `normalizeStatus(value, now)` from `ops/trading/worker/src/index.js`; `statusFields(data, now)` and `executionFields(execution, now)` from `src/scripts/trading-status.mjs`.
- Produces: `fixtures/status-contract.json` with shape `{"now": number, "cases": [{"name", "observer", "execution"|null, "payload", "ui"}]}`. Task 4 adds a case; Task 5 reuses `cases[0].payload`.

- [ ] **Step 1: Write the fixture**

`ops/trading/fixtures/status-contract.json`:
```json
{
  "now": 1000,
  "cases": [
    {
      "name": "fresh priced observation, no execution",
      "observer": {"mode": "signal-only", "symbol": "XAUUSD-VIP", "status": "observed", "signal": "long",
        "reason": "Completed candle evaluated", "checked_at": 995, "bar_time": 900,
        "health": {"terminal": "connected", "quote": "fresh", "sampled_at": 995, "tick_time": 994,
          "tick_time_msc": 994500, "quote_age_seconds": 0.5, "history_bar_time": 900, "history_count": 250,
          "bid": 4100.25, "ask": 4100.5}},
      "execution": null,
      "payload": {"mode": "signal-only", "symbol": "XAUUSD-VIP", "status": "observed", "signal": "long",
        "reason": "Completed candle evaluated", "checked_at": 995, "bar_time": 900,
        "health": {"terminal": "connected", "quote": "fresh", "sampled_at": 995, "tick_time": 994,
          "tick_time_msc": 994500, "quote_age_seconds": 0.5, "history_bar_time": 900, "history_count": 250,
          "bid": 4100.25, "ask": 4100.5}},
      "ui": {"state": "Observing", "price": "4100.25 / 4100.50", "signal": "Long setup"}
    },
    {
      "name": "stale weekend quote is blocked and unpriced",
      "observer": {"mode": "signal-only", "symbol": "XAUUSD-VIP", "status": "blocked", "signal": "long",
        "reason": "Gold quote is old", "checked_at": 995, "bar_time": 900,
        "health": {"terminal": "connected", "quote": "stale", "sampled_at": 995, "tick_time": 10,
          "tick_time_msc": 10000, "quote_age_seconds": 985, "history_bar_time": 900, "history_count": 250,
          "bid": 4100.25, "ask": 4100.5}},
      "execution": null,
      "payload": {"mode": "signal-only", "symbol": "XAUUSD-VIP", "status": "blocked", "signal": "none",
        "reason": "Gold quote is old", "checked_at": 995, "bar_time": 900,
        "health": {"terminal": "connected", "quote": "stale", "sampled_at": 995, "tick_time": 10,
          "tick_time_msc": 10000, "quote_age_seconds": 985, "history_bar_time": 900, "history_count": 250,
          "bid": 4100.25, "ask": 4100.5}},
      "ui": {"state": "Waiting for price", "price": "—", "signal": "Paused"}
    },
    {
      "name": "inverted bid/ask is dropped in every layer",
      "observer": {"mode": "signal-only", "symbol": "XAUUSD-VIP", "status": "observed", "signal": "none",
        "reason": "Completed candle evaluated", "checked_at": 995, "bar_time": 900,
        "health": {"terminal": "connected", "quote": "fresh", "sampled_at": 995, "tick_time": 994,
          "tick_time_msc": 994500, "quote_age_seconds": 0.5, "history_bar_time": 900, "history_count": 250,
          "bid": 4100.5, "ask": 4100.25}},
      "execution": null,
      "payload": {"mode": "signal-only", "symbol": "XAUUSD-VIP", "status": "observed", "signal": "none",
        "reason": "Completed candle evaluated", "checked_at": 995, "bar_time": 900,
        "health": {"terminal": "connected", "quote": "fresh", "sampled_at": 995, "tick_time": 994,
          "tick_time_msc": 994500, "quote_age_seconds": 0.5, "history_bar_time": 900, "history_count": 250,
          "bid": null, "ask": null}},
      "ui": {"state": "Observing", "price": "—", "signal": "No setup yet"}
    }
  ]
}
```

- [ ] **Step 2: Python layer test**

Append to `ops/trading/test_status_server.py` inside `StatusServerTest`:
```python
    def test_shared_status_contract(self):
        contract = json.loads((Path(__file__).parent / "fixtures" / "status-contract.json").read_text())
        for case in contract["cases"]:
            with self.subTest(case["name"]), tempfile.TemporaryDirectory() as root:
                observer = Path(root) / "latest.json"
                observer.write_text(json.dumps(case["observer"]))
                execution = Path(root) / "execution.json"
                if case["execution"] is not None:
                    execution.write_text(json.dumps(case["execution"]))
                status, payload = read_status(observer, contract["now"], execution_path=execution)
                self.assertEqual(status, 200)
                self.assertEqual(payload, case["payload"])
```
Note: when `execution` is null the file is absent, so `read_status` omits the `execution` key, matching the payload.

- [ ] **Step 3: Run it**

Run: `cd ops/trading && python3 -m pytest -q -p no:cacheprovider test_status_server.py -k shared_status_contract`
Expected: PASS for all three subtests. If a subtest fails, the fixture or `status_server.py` disagrees: fix the fixture only if `status_server.py` behavior is the intended one, and say which in the commit message.

- [ ] **Step 4: Worker layer test**

Append to `ops/trading/worker/test.mjs`:
```js
import { readFileSync } from 'node:fs';

test('shared status contract survives Worker normalization unchanged', () => {
  const contract = JSON.parse(readFileSync(new URL('../fixtures/status-contract.json', import.meta.url)));
  for (const item of contract.cases) {
    assert.deepEqual(normalizeStatus(item.payload, contract.now), item.payload, item.name);
  }
});
```
Move the `import { readFileSync }` line to the top of the file with the other imports.

- [ ] **Step 5: Frontend layer test**

Append to `src/scripts/trading-status.test.mjs`:
```js
import { readFileSync } from 'node:fs';
import { normalizeStatus } from '../../ops/trading/worker/src/index.js';

const contract = JSON.parse(readFileSync(new URL('../../ops/trading/fixtures/status-contract.json', import.meta.url)));
for (const item of contract.cases) {
  const fields = statusFields(normalizeStatus(item.payload, contract.now), contract.now);
  for (const [key, expected] of Object.entries(item.ui)) assert.equal(fields[key], expected, `${item.name}: ${key}`);
}
console.log('Trading status: shared contract passes Python → Worker → page fields');
```
Move both imports to the top of the file.

- [ ] **Step 6: Run all three suites**

Run: `node --test ops/trading/worker/test.mjs src/scripts/*.test.mjs && (cd ops/trading && python3 -m pytest -q -p no:cacheprovider test_status_server.py)`
Expected: all pass.

- [ ] **Step 7: Prove the contract catches drift**

Temporarily delete `'bid', 'ask'` from the key list in `normalizeStatus` (`worker/src/index.js`), rerun `node --test ops/trading/worker/test.mjs`.
Expected: FAIL on "shared status contract". Restore the line; rerun; PASS.

- [ ] **Step 8: Commit**

```bash
git add ops/trading/fixtures/status-contract.json ops/trading/test_status_server.py ops/trading/worker/test.mjs src/scripts/trading-status.test.mjs
git commit -m "test(trading): share one status contract across Python, Worker and page"
```

---

### Task 4: Stop the page claiming "orders off" while a demo order is active

`statusFields` returns `strategy: 'Observing · orders off'` (`src/scripts/trading-status.mjs:38`) even when `data.execution.status` is `pending` or `open`.

**Files:**
- Modify: `src/scripts/trading-status.mjs:38`
- Modify: `ops/trading/fixtures/status-contract.json` (add one case)
- Test: covered by Task 3's loops

**Interfaces:**
- Consumes: Task 3 fixture and loops.
- Produces: `statusFields(...).strategy` values: `'Paused — no current observer report'`, `'Blocked — see reason below'`, `'Signals only · manual demo order active'`, `'Observing · signals place no orders'`.

- [ ] **Step 1: Add the failing contract case**

Append to `cases` in the fixture:
```json
{
  "name": "manual demo order pending while observing",
  "observer": {"mode": "signal-only", "symbol": "XAUUSD-VIP", "status": "observed", "signal": "none",
    "reason": "Completed candle evaluated", "checked_at": 995, "bar_time": 900,
    "health": {"terminal": "connected", "quote": "fresh", "sampled_at": 995, "tick_time": 994,
      "tick_time_msc": 994500, "quote_age_seconds": 0.5, "history_bar_time": 900, "history_count": 250,
      "bid": 4100.25, "ask": 4100.5}},
  "execution": {"mode": "one-shot-demo", "status": "pending", "updated_at": 990, "side": "buy",
    "volume": 0.01, "opened_at": null, "closed_at": null, "realized_net_usd": null,
    "entry_price": 4095.0, "sl": 4085.0, "tp": 4110.0, "close_reason": null},
  "payload": {"mode": "signal-only", "symbol": "XAUUSD-VIP", "status": "observed", "signal": "none",
    "reason": "Completed candle evaluated", "checked_at": 995, "bar_time": 900,
    "health": {"terminal": "connected", "quote": "fresh", "sampled_at": 995, "tick_time": 994,
      "tick_time_msc": 994500, "quote_age_seconds": 0.5, "history_bar_time": 900, "history_count": 250,
      "bid": 4100.25, "ask": 4100.5},
    "execution": {"mode": "one-shot-demo", "status": "pending", "updated_at": 990, "side": "buy",
      "volume": 0.01, "opened_at": null, "closed_at": null, "realized_net_usd": null,
      "entry_price": 4095.0, "sl": 4085.0, "tp": 4110.0, "close_reason": null}},
  "ui": {"state": "Observing", "strategy": "Signals only · manual demo order active"}
}
```
Also add `"strategy": "Observing · signals place no orders"` to the `ui` of the first case.

- [ ] **Step 2: Run to see it fail**

Run: `node --test src/scripts/trading-status.test.mjs`
Expected: FAIL on `strategy` for both edited cases. Python and Worker suites still pass (they check payload only).

- [ ] **Step 3: Implement**

In `src/scripts/trading-status.mjs`, replace line 38:
```js
    strategy: !alive ? 'Paused — no current observer report' : data.status === 'blocked' ? 'Blocked — see reason below'
      : ['armed', 'submitting', 'pending', 'open', 'closing', 'needs_attention'].includes(data.execution?.status)
        ? 'Signals only · manual demo order active' : 'Observing · signals place no orders',
```

- [ ] **Step 4: Run all three suites**

Run: `node --test ops/trading/worker/test.mjs src/scripts/*.test.mjs && (cd ops/trading && python3 -m pytest -q -p no:cacheprovider test_status_server.py)`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/scripts/trading-status.mjs ops/trading/fixtures/status-contract.json
git commit -m "fix(trading): show when a manual demo order is active instead of 'orders off'"
```

---

### Task 5: Read-only browser test of `/vault/trading` (criterion 3)

The only existing browser test (`tests/trading-readonly.e2e.ts`) targets the Vibe-Trading app on port 8899. `/vault/trading` fetches `/api/trading/status`, which in production is served by the Worker. In dev, a small route serves the shared fixture so the real page renders real fixture data.

**Files:**
- Create: `src/pages/api/trading/status.ts`
- Create: `tests/vault-trading.e2e.ts`
- Modify: `e2e.config.ts` (no change needed if `APP_URL` is passed; see Step 4)

**Interfaces:**
- Consumes: `ops/trading/fixtures/status-contract.json` `cases[0].payload` (Task 3); `normalizeStatus` is not used here because the fixture payload is already normalized.
- Produces: `npm run test:e2e` covers `/vault/trading` when `APP_URL=http://127.0.0.1:4321`.

- [ ] **Step 1: Install the declared dependencies**

Run: `npm install`
Expected: `node_modules/e2e` and `node_modules/@e2e-dev/web` exist. If `@e2e-dev/web` is not in `package.json`, add it at the version the existing test was written against: `npm view @e2e-dev/web versions --json | tail -3`, then `npm install -D @e2e-dev/web@<latest 0.x>`.

- [ ] **Step 2: Dev-only fixture route**

`src/pages/api/trading/status.ts`:
```ts
import type { APIRoute } from 'astro';
import contract from '../../../../ops/trading/fixtures/status-contract.json';

export const prerender = false;

// Dev only: production /api/trading/status is served by the Access-gated Worker.
export const GET: APIRoute = () => {
  if (!import.meta.env.DEV) return new Response(null, { status: 404 });
  const now = Math.floor(Date.now() / 1000);
  const shift = now - contract.now;
  const payload = structuredClone(contract.cases[0].payload);
  payload.checked_at += shift;
  payload.health.sampled_at += shift;
  return Response.json(payload, { headers: { 'Cache-Control': 'no-store' } });
};
```
The time shift keeps the fixture inside the page's 30-second freshness window.

- [ ] **Step 3: Write the test**

`tests/vault-trading.e2e.ts`:
```ts
import { test } from '@e2e-dev/web';
import { expect } from 'e2e';

test('vault trading page renders the shared fresh-status contract', async ({ app, screen }) => {
  await app.open('/vault/trading');
  await expect(screen.getByRole('heading', 'Live demo feed')).toBeVisible();
  await expect(screen.getByText('4100.25 / 4100.50')).toBeVisible();
  await expect(screen.getByText('Connected to demo')).toBeVisible();
  await expect(screen.getByText('Long setup')).toBeVisible();
  await expect(screen.getByText('Signals do not place orders', { exact: false })).toBeVisible();
  await app.screenshot('vault-trading-fresh');
});
```
If `getByText` in this runner has no `{ exact: false }` option, use `screen.getByRole('main')` with `toContainText(/Signals do not place orders/)` as the existing test does.

- [ ] **Step 4: Run it against the dev server**

Terminal 1: `npm run dev`
Terminal 2: `APP_URL=http://127.0.0.1:4321 npm run test:e2e -- tests/vault-trading.e2e.ts`
Expected: PASS. If the Vault requires sign-in in dev (check `src/middleware*`), note which env var disables it locally and pass it in Terminal 1; do not weaken production auth.

- [ ] **Step 5: Prove a production build returns 404**

Run: `npx astro build && (node ./dist/server/entry.mjs & sleep 3; curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:4321/api/trading/status; kill %1)`
Expected: `404`. In production the Worker also owns this path before the origin.

- [ ] **Step 6: Commit**

```bash
git add src/pages/api/trading/status.ts tests/vault-trading.e2e.ts package.json package-lock.json
git commit -m "test(trading): browser test /vault/trading against the shared status contract"
```

---

## Phase C — Criterion 5 security preconditions

### Task 6: Password-protect VNC inside Docker

`desktop.sh:15` runs `x11vnc ... -nopw`. `x11vnc` itself is `-localhost`, but `websockify` on container port 6080 is reachable from every container on the `trading-control` network, including `status`, which is also on the shared `dokploy-network`. Anyone who compromises `status` gets the MT5 desktop.

**Files:**
- Modify: `ops/trading/desktop.sh:15`

**Interfaces:**
- Consumes: nothing.
- Produces: VNC requires the password stored at `/home/mt5/.vnc/passwd` (inside the persistent `mt5-home` volume).

- [ ] **Step 1: Owner creates the password file on the VPS first**

Run on the VPS (interactive; the password is typed, not echoed into history):
```bash
docker exec -it kwg-mt5-desktop sh -c 'mkdir -p "$HOME/.vnc" && x11vnc -storepasswd "$HOME/.vnc/passwd" && chmod 600 "$HOME/.vnc/passwd"'
```
Expected: `stored passwd in file: /home/mt5/.vnc/passwd`. Do this **before** Step 3's redeploy, or the desktop will refuse to start VNC.

- [ ] **Step 2: Change the start line**

In `ops/trading/desktop.sh`, replace:
```bash
x11vnc -display "$DISPLAY" -localhost -rfbport 5900 -forever -shared -nopw &
```
with:
```bash
# VNC password lives in the persistent mt5-home volume; never in Git or env.
x11vnc -display "$DISPLAY" -localhost -rfbport 5900 -forever -shared -rfbauth "$HOME/.vnc/passwd" &
```

- [ ] **Step 3: Verify locally then deploy**

Run: `bash -n ops/trading/desktop.sh`
Expected: no output. Copy only `desktop.sh` to the VPS compose folder, rebuild the image layer and recreate `desktop` per README's rollback-preserving procedure. Then open `http://127.0.0.1:6081/vnc.html` through the SSH tunnel.
Expected: noVNC prompts for a password; the correct password shows MT5.

- [ ] **Step 4: Commit**

```bash
git add ops/trading/desktop.sh
git commit -m "fix(trading): require a VNC password inside the desktop container"
```

---

### Task 7: Give the research tool its own read-only service token

`research-mcp/src/index.js:25-35` and `worker/src/index.js:98,129-130,170-171` both read `STATUS_ACCESS_CLIENT_ID/SECRET`. If they hold the same Cloudflare Access service token, the research Worker's credentials can reach `/control/*`. Criterion 5 requires the agent side to never hold a credential accepted on `/control/*`.

**Files:**
- None in Git. Cloudflare Zero Trust dashboard and `wrangler secret` only.

**Interfaces:**
- Consumes: nothing.
- Produces: two Access service tokens: `trading-worker` (allowed on `/status` and `/control/*`) and `research-readonly` (allowed on `/status` only).

- [ ] **Step 1: Owner checks whether the tokens are shared**

In Cloudflare Zero Trust → Access → Service Auth → Service Tokens, note which token names exist. In each Worker's settings → Variables, compare the `STATUS_ACCESS_CLIENT_ID` values (IDs are not secret).
Expected outcome recorded in `HANDOFF.md` "Now": `research-mcp token: shared | separate`.

- [ ] **Step 2: If shared, create `research-readonly`**

Create a new service token named `research-readonly`. Set it on the research Worker only:
```bash
cd ops/trading/research-mcp
npx wrangler secret put STATUS_ACCESS_CLIENT_ID
npx wrangler secret put STATUS_ACCESS_CLIENT_SECRET
```
Paste values only into the wrangler prompt.

- [ ] **Step 3: Split the Access application by path**

On the status origin hostname, add a separate Access application for path `/control/*` whose only Allow (Service Auth) policy includes `trading-worker`. Keep the existing `/status` application allowing both tokens.

- [ ] **Step 4: Verify**

From the owner's machine, with the research token in environment variables set for this shell only:
```bash
curl -s -o /dev/null -w '%{http_code}\n' -X POST -H "CF-Access-Client-Id: $RID" -H "CF-Access-Client-Secret: $RSECRET" -H 'Content-Type: application/json' --data '{}' https://<status-origin>/control/preview
```
Expected: `403`. The same token on `GET /status` returns `200`. Then `unset RID RSECRET`.

- [ ] **Step 5: Record**

Add to `HANDOFF.md` "Now": `Research token is status-only; /control/* accepts trading-worker token only (verified <date>).` Commit:
```bash
git add ops/trading/HANDOFF.md
git commit -m "docs(trading): record status-only research service token"
```

---

## Phase D — Criterion 1: live data confirmed

### Task 8: Owner-run live freshness qualification across two M15 boundaries

The collector already exists: `verify-demo.py --collect-seconds` feeds `gold_qualification.qualify_samples`, which passes only with ≥361 samples, ≥1,800 continuous seconds, ≥2 M15 transitions and advancing ticks. The handoff records a pass on 2026-09-28. Repeat qualification for current deployment health; preserve that historical evidence.

**Files:**
- Modify: `ops/trading/HANDOFF.md` ("Now" block only)

**Interfaces:**
- Consumes: deployed `verify-demo.py`, `gold_qualification.py`, `mt5_data.py` (check they match `main` first).
- Produces: a private JSON on the VPS with `data_status: passed`, and its SHA-256 in `HANDOFF.md`.

- [ ] **Step 1: Confirm the deployed files match `main`**

Run on the VPS: `docker exec kwg-mt5-desktop sha256sum /opt/trading/verify-demo.py /opt/trading/gold_qualification.py /opt/trading/mt5_data.py`
Run locally: `cd ops/trading && shasum -a 256 verify-demo.py gold_qualification.py mt5_data.py`
Expected: identical. If not, copy the `main` versions with `docker cp` as the README describes, without restarting MT5.

- [ ] **Step 2: Run during a liquid open session**

Pick a weekday between 08:00 and 16:00 UTC (London/New York overlap). Algo Trading off. On the VPS:
```bash
docker exec -it kwg-mt5-desktop wine /opt/python/python.exe /opt/trading/verify-demo.py --login YOUR_DEMO_ACCOUNT_NUMBER --collect-seconds 3600 --output 'C:\users\mt5\gold-qualification-YYYYMMDD.json'
```
Expected: exits after `data_status: passed` or at 3,600 s.

- [ ] **Step 3: Read the result**

Run: `docker exec kwg-mt5-desktop sh -c 'cat "$HOME/.wine/drive_c/users/mt5/gold-qualification-YYYYMMDD.json"' | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('data_status'), d.get('transition_bar_times'), d.get('blockers'))"`
Expected: `passed [<bar1>, <bar2>, ...] []`. If `inconclusive`, record the blocker and rerun on another session. Do not adjust thresholds or offsets.

- [ ] **Step 4: Rerun after the daylight-saving switch**

European clocks change on 2026-10-25 and US clocks on 2026-11-01. Repeat Step 2 on a weekday after 2026-11-01.
Expected: passes again with the same `MT5_SERVER_OFFSET_SECONDS`. If it fails with `future` or a bar-time mismatch, the broker offset changed: stop and record it; changing the offset is a separate reviewed decision.

- [ ] **Step 5: Record**

Add to `HANDOFF.md` "Now": `Live freshness: passed <date> (pre-DST) and <date> (post-DST); sha256 <hash>.` Commit `ops/trading/HANDOFF.md`.

---

## Phase E — Criterion 4 and 5: a research loop that can learn

### Task 9: Owner decision — where the research loop runs

The Batch 3 proposal path depends on Windows (`npipe` Docker, `msvcrt`). The owner now works on a MacBook; the VPS is Linux and already holds the frozen dataset.

**Files:**
- Modify: `ops/trading/HANDOFF.md` ("Now" block)

- [ ] **Step 1: Choose and record one host**

Options:
- **VPS Linux (recommended):** the dataset is already there, Docker is native, and Tasks 10–11 use only stdlib Python. No credentials needed beyond existing SSH.
- **MacBook:** needs the dataset copied (private file, checksum-verified) and stays offline-only.
- **Windows:** keeps the existing Batch 3 harness but ties research to one machine the owner no longer uses daily.

Record: `Research host: <choice>. Batch 3 LLM proposal path paused until Task 11 gates can be met.`

---

### Task 10: Deterministic development-only grid

The bounded agent can only choose `lookback_bars` in 2..5 (`gold_experiment.validate_candidate`). A plain loop over those four values plus the baseline gives the same answer with no model, and is the comparison any future agent must beat. It reads only development bars by construction.

**Files:**
- Create: `ops/trading/grid-gold.py`
- Create: `ops/trading/test_grid_gold.py`

**Interfaces:**
- Consumes: `replay(data, *, candidate=None)` from `replay-gold.py` (returns `{'decisions': [{'bar_time', ...}]}`); `simulate(bars, signals, spec, costs, initial=100000, *, cost_profile=None)` from `simulate-gold.py` (returns `{'summary': {'trades', 'net_pnl_usd', 'close_sampled_drawdown_pct', ...}, ...}`); `SCENARIOS` from `gold_experiment.py`.
- Produces: `grid(data, *, dev_start=249, dev_end=6000) -> {'mode': 'development-only-grid', 'scenario': 'middle', 'dev_end_index': int, 'rows': [{'lookback_bars': int|None, 'trades': int, 'net_pnl_usd': float, 'drawdown_pct': float}], 'selected': int|None}`. Task 11 consumes `selected`.

- [ ] **Step 1: Write the failing test**

`ops/trading/test_grid_gold.py`:
```python
import math
from pathlib import Path
import runpy
import unittest

grid = runpy.run_path(str(Path(__file__).with_name('grid-gold.py')))['grid']
SPEC = dict(point=.01, trade_contract_size=100, trade_tick_size=.01,
            volume_min=.01, volume_max=100, volume_step=.01, currency_profit='USD')


def dataset(n):
    bars = [dict(time=(i + 1) * 900, open=2000 + 20 * math.sin(i / 15),
                 high=2001 + 20 * math.sin(i / 15), low=1999 + 20 * math.sin(i / 15),
                 close=2000 + 20 * math.sin((i + 1) / 15), spread=20) for i in range(n)]
    for bar in bars:
        bar['high'] = max(bar['high'], bar['open'], bar['close'])
        bar['low'] = min(bar['low'], bar['open'], bar['close'])
    return {'schema_version': 1, 'symbol': 'XAUUSD-VIP', 'timeframe': 'M15',
            'source': {'start_pos': 1}, 'captured_at': (n + 2) * 900,
            'current_contract_specification': SPEC, 'bars': bars}


class GridTest(unittest.TestCase):
    def test_grid_never_reads_past_development_and_is_deterministic(self):
        data = dataset(700)
        data['bars'] += [None] * 300  # validation/reserved stand-ins: any read raises
        first = grid(data, dev_end=700)
        self.assertEqual([r['lookback_bars'] for r in first['rows']], [None, 2, 3, 4, 5])
        self.assertIn(first['selected'], (None, 2, 3, 4, 5))
        self.assertEqual(first, grid(data, dev_end=700))

    def test_rejects_development_end_inside_warmup(self):
        with self.assertRaises(ValueError):
            grid(dataset(700), dev_end=300)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run to see it fail**

Run: `cd ops/trading && python3 -m pytest -q -p no:cacheprovider test_grid_gold.py`
Expected: FAIL — `grid-gold.py` does not exist.

- [ ] **Step 3: Implement**

`ops/trading/grid-gold.py`:
```python
"""Deterministic development-only grid over the bounded EMA20 slope-filter candidates."""
import argparse
import json
from pathlib import Path
import runpy

from gold_experiment import SCENARIOS

HERE = Path(__file__).parent
simulate = runpy.run_path(str(HERE / 'simulate-gold.py'))['simulate']
replay = runpy.run_path(str(HERE / 'replay-gold.py'))['replay']


def grid(data, *, dev_start=249, dev_end=6000):
    # Development window matches gold_experiment.prepare_experiment; nothing at or after dev_end is read.
    if dev_end < dev_start + 251:
        raise ValueError('Development window shorter than the 250-bar warm-up')
    dev = {**data, 'bars': data['bars'][:dev_end]}
    spec = data['current_contract_specification']
    rows = []
    for lookback in (None, 2, 3, 4, 5):
        candidate = None if lookback is None else {
            'kind': 'ema20_slope_filter', 'lookback_bars': lookback, 'hypothesis': 'deterministic grid'}
        signals = {d['bar_time']: d for d in replay(dev, candidate=candidate)['decisions']}
        summary = simulate(dev['bars'][dev_start:], signals, spec, SCENARIOS['middle'])['summary']
        rows.append({'lookback_bars': lookback, 'trades': summary['trades'],
                     'net_pnl_usd': summary['net_pnl_usd'],
                     'drawdown_pct': summary['close_sampled_drawdown_pct']})
    # Pre-registered rule: highest development net under 'middle' costs; ties go to the baseline, then shorter lookback.
    best = max(rows, key=lambda r: (r['net_pnl_usd'], -(r['lookback_bars'] or 0)))
    return {'mode': 'development-only-grid', 'scenario': 'middle', 'dev_end_index': dev_end,
            'rows': rows, 'selected': best['lookback_bars']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = grid(json.loads(args.dataset.read_text()))
    with args.output.open('x') as output:
        json.dump(report, output, indent=2)


if __name__ == '__main__':
    main()
```

- [ ] **Step 4: Run tests**

Run: `cd ops/trading && python3 -m pytest -q -p no:cacheprovider test_grid_gold.py test_replay_gold.py test_simulate_gold.py`
Expected: all pass. If `replay` raises on the synthetic data (e.g. a gap check), adjust only the test's `dataset()` generator, not `replay-gold.py`.

- [ ] **Step 5: Run once on the frozen dataset (research host from Task 9)**

```bash
python3 grid-gold.py --dataset /opt/kwg-gold-research/datasets/gold-history-20260928.json --output /opt/kwg-gold-research/grid-<commit>/grid.json
```
Expected: one file with five rows and `selected`. Record `selected` and the file's SHA-256 in `HANDOFF.md`. These are development numbers only; they are not evidence of an edge.

- [ ] **Step 6: Commit**

```bash
git add ops/trading/grid-gold.py ops/trading/test_grid_gold.py
git commit -m "feat(trading): deterministic development-only grid for slope-filter candidates"
```

---

### Task 11: Pre-register a prospective holdout the agent never sees

The existing validation window is already inspected and only yields about 30 trades over about 21 days, against `min_trades` 100 and `min_observed_days` 60 in `evaluation-policy.json`. New data collected **after** a committed start date is the only window no one has seen.

**Files:**
- Create: `ops/trading/prospective-holdout.json`
- Create: `ops/trading/test_prospective_holdout.py`

**Interfaces:**
- Consumes: Task 10 `selected` value; `evaluation-policy.json` thresholds (read, not modified).
- Produces: a committed, immutable registration: start epoch, the one candidate to evaluate, and the evaluation rule. A remotely recorded registration published before collection must bind the candidate, development report, dataset, evaluator, policy and risk hashes. Local Git timestamps alone are not proof. The holdout must be collected under an owner-controlled identity inaccessible to the research process; JSON declarations alone do not enforce access.

- [ ] **Step 1: Write the registration**

`ops/trading/prospective-holdout.json` (fill `selected_lookback_bars` from Task 10 Step 5; `null` means the baseline; set `start_utc` to the first Monday 00:00 UTC after the commit):
```json
{
  "schema_version": 1,
  "symbol": "XAUUSD-VIP",
  "timeframe": "M15",
  "start_utc": "<future Monday 00:00 UTC after registration>",
  "selected_lookback_bars": null,
  "selection_rule": "grid-gold.py development-only, scenario middle, highest net; ties to baseline then shorter lookback",
  "compare_against": "baseline EMA20/EMA50 crossover",
  "one_candidate_only": true,
  "evaluate_when": "trades >= 100 and observed_days >= 60 per evaluation-policy.json",
  "agent_access": "none until evaluate_when is met",
  "promotion": "owner review only"
}
```

- [ ] **Step 2: Test that it stays consistent**

`ops/trading/test_prospective_holdout.py`:
```python
import json
from datetime import datetime
from pathlib import Path
import unittest

HERE = Path(__file__).parent


class HoldoutTest(unittest.TestCase):
    def test_registration_is_single_candidate_and_matches_policy(self):
        holdout = json.loads((HERE / 'prospective-holdout.json').read_text())
        policy = json.loads((HERE / 'evaluation-policy.json').read_text())
        self.assertTrue(holdout['one_candidate_only'])
        self.assertIn(holdout['selected_lookback_bars'], (None, 2, 3, 4, 5))
        self.assertEqual(holdout['promotion'], 'owner review only')
        self.assertIn(str(policy['min_trades']), holdout['evaluate_when'])
        self.assertIn(str(policy['min_observed_days']), holdout['evaluate_when'])
        start = datetime.fromisoformat(holdout['start_utc'].replace('Z', '+00:00'))
        self.assertEqual((start.weekday(), start.hour, start.minute), (0, 0, 0))


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 3: Run**

Run: `cd ops/trading && python3 -m pytest -q -p no:cacheprovider test_prospective_holdout.py`
Expected: PASS.

- [ ] **Step 4: Commit before the start date**

```bash
git add ops/trading/prospective-holdout.json ops/trading/test_prospective_holdout.py
git commit -m "feat(trading): pre-register one-candidate prospective gold holdout"
git push origin main
```
The pushed commit must predate `start_utc`. If it does not, move `start_utc` to the next Monday and recommit; never backdate.

- [ ] **Step 5: Record and stop**

Add to `HANDOFF.md` "Now": `Prospective holdout registered <commit>, starts <start_utc>; evaluation only after the policy sample minimums and all cost, provenance and fold gates pass. Agent research resumes only after that evaluation, with owner review.` Commit.

---

## Not in this plan

- **Pending-order expiry** (`pending_until_cancelled` in `worker/src/index.js:153`): accepted in the review, but it changes order behavior and needs its own reviewed plan using MT5 `ORDER_TIME_SPECIFIED`.
- **Pinning Docker downloads by checksum/digest:** deferred to the next image rebuild.
- **Restarting Batch 3 LLM proposals:** paused until Task 11's holdout is evaluated.
- **Fixing the macOS path-comparison test failures** in `trusted_gateway.py`/`gold_account.py`: only matters if Batch 3 resumes on a symlinked host.


## Approved execution corrections — 2026-10-08

- Execute natively in `codex/trading-agent-foundation`, with one final independent review.
- Task 1 remains pending Windows evidence; do not merge or imply rejection without it.
- Task 5 must cover fresh status, active manual execution, and expired sign-in (401/302), including clearing previously displayed prices. Enable fixtures only with an explicit dev-test environment flag; preserve normal localhost preview. Production must return 404 even with that flag set.
- Task 6 may prepare source locally; deploy only after owner password provisioning and a safe desktop restart window.
- Task 10 must bind to the existing frozen manifest and its exact 6,000-bar development boundary, record provenance, and reject invalid boundaries instead of allowing configurable access to validation bars.
- Task 11 is blocked until the owner chooses the research host, runs the development grid, and establishes holdout storage inaccessible to the research identity. Preserve all existing policy gates; minimum sample size alone does not qualify a candidate. If baseline wins, retain baseline rather than inventing a new candidate.
- TradingAgents is a future reference; no dependency or LLM proposal path is added by this foundation.
