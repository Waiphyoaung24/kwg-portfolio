# Project Workflow System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `bizz $$` money tracker with a self-hosted project-workflow tool that clones a pipeline template into each new project and surfaces who's blocking what.

**Architecture:** Hybrid Astro — portfolio pages stay static; `/vault/projects` and `/api/*` opt into on-demand rendering via `@astrojs/node`. Postgres holds the data, accessed with raw parameterized SQL through the `postgres` client (no ORM). A one-password HMAC cookie gates the API. The frontend is a vanilla-TS island that fetches `/api`.

**Tech Stack:** Astro 6, `@astrojs/node`, `postgres` (porsager), Node 24 (built-in test runner via plain `.mjs` assert files), SCSS, TypeScript.

## Global Constraints

- Node `>=24` (already in `engines`). Use the yarn package manager (`yarn add ...`).
- **Exactly two new dependencies:** `@astrojs/node`, `postgres`. No ORM, migration tool, auth lib, or validation lib.
- Every `/api/*` route and `/vault/projects` MUST set `export const prerender = false`.
- Every `/api/*` route MUST reject unauthenticated requests (401) except `/api/login` and `/api/health`.
- Pure logic lives in `.mjs` modules tested with `node <file>.test.mjs` + `node:assert` — same convention as `workout-picker.test.mjs`. No test framework.
- Env vars (server-side, read via `process.env`): `DATABASE_URL`, `APP_PASSWORD`, `APP_SECRET`.
- Reuse existing design tokens (`--c-dark`, `--c-light`, `--c-accent` `#FFC000`, `to-rem()`, `clamp-fluid()`, Space Grotesk). No restyle.
- `owner_type ∈ {internal, client, shared}`. `stage status ∈ {not_started, in_progress, waiting_on_client, blocked_internal, done, skipped}`. `project status ∈ {active, on_hold, done, cancelled}`.

---

### Task 1: Node adapter + health endpoint

**Files:**
- Modify: `package.json` (deps + scripts)
- Modify: `astro.config.mjs`
- Create: `src/pages/api/health.ts`
- Create: `.env.example`

**Interfaces:**
- Produces: a running server (`node ./dist/server/entry.mjs`) with `GET /api/health` → `{ok:true}`.

- [ ] **Step 1: Install deps**

```bash
yarn add @astrojs/node postgres
```

- [ ] **Step 2: Add the adapter to `astro.config.mjs`**

Import at top and add `adapter` to the config object. Leave `output` at its default (`static`) — per-route `prerender = false` handles on-demand rendering.

```js
import node from '@astrojs/node';
// inside defineConfig({ ... }):
adapter: node({ mode: 'standalone' }),
```

- [ ] **Step 3: Create the health endpoint**

`src/pages/api/health.ts`:

```ts
export const prerender = false;

export function GET() {
  return Response.json({ ok: true });
}
```

- [ ] **Step 4: Create `.env.example`**

```
DATABASE_URL=postgres://user:pass@localhost:5432/kwg
APP_PASSWORD=change-me
APP_SECRET=generate-a-long-random-string
```

- [ ] **Step 5: Build and smoke-test**

Run: `yarn build && node ./dist/server/entry.mjs &` then `curl -s localhost:4321/api/health`
Expected: `{"ok":true}`. Kill the server after.

- [ ] **Step 6: Commit**

```bash
git add package.json yarn.lock astro.config.mjs src/pages/api/health.ts .env.example
git commit -m "✨ add node adapter + /api/health"
```

---

### Task 2: Database schema, client, and seed

**Files:**
- Create: `db/schema.sql`
- Create: `src/server/db.ts`
- Create: `src/server/seed.ts`
- Create: `src/env.d.ts` addition for `*.sql?raw`
- Create: `src/server/db.test.mjs` (integration, gated on `DATABASE_URL`)

**Interfaces:**
- Produces: `sql` (postgres tagged-template client), `initDb(): Promise<void>` (applies schema + seeds once), from `src/server/db.ts`.

- [ ] **Step 1: Write `db/schema.sql` (DDL only — seed is in TS)**

```sql
CREATE TABLE IF NOT EXISTS project_types (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name text NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS pipeline_templates (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_type_id integer NOT NULL REFERENCES project_types(id),
  name text NOT NULL,
  version integer NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS stage_templates (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  pipeline_template_id integer NOT NULL REFERENCES pipeline_templates(id),
  ord integer NOT NULL,
  name text NOT NULL,
  owner_type text NOT NULL CHECK (owner_type IN ('internal','client','shared')),
  description text NOT NULL DEFAULT '',
  required_documents text[] NOT NULL DEFAULT '{}',
  checklist_items text[] NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS projects (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  client_name text NOT NULL,
  project_type_id integer NOT NULL REFERENCES project_types(id),
  pipeline_template_id integer NOT NULL REFERENCES pipeline_templates(id),
  created_date timestamptz NOT NULL DEFAULT now(),
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','on_hold','done','cancelled'))
);

CREATE TABLE IF NOT EXISTS project_stages (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id integer NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  stage_template_id integer REFERENCES stage_templates(id),
  ord integer NOT NULL,
  name text NOT NULL,
  owner_type text NOT NULL CHECK (owner_type IN ('internal','client','shared')),
  status text NOT NULL DEFAULT 'not_started'
    CHECK (status IN ('not_started','in_progress','waiting_on_client','blocked_internal','done','skipped')),
  notes text NOT NULL DEFAULT '',
  blocked_reason text,
  blocked_since timestamptz,
  started_at timestamptz,
  completed_at timestamptz,
  required_documents text[] NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS documents (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_stage_id integer NOT NULL REFERENCES project_stages(id) ON DELETE CASCADE,
  filename text NOT NULL,
  doc_type text NOT NULL CHECK (doc_type IN ('proposal','brs','quotation','contract','wireframe','other')),
  version_number integer,
  uploaded_by text NOT NULL DEFAULT '',
  uploaded_at timestamptz NOT NULL DEFAULT now(),
  note text NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS team_members (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name text NOT NULL,
  role text NOT NULL DEFAULT '',
  contact text NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS project_assignments (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id integer NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  team_member_id integer NOT NULL REFERENCES team_members(id) ON DELETE CASCADE,
  role_on_project text NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS activity_log (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id integer NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  actor text NOT NULL DEFAULT '',
  action text NOT NULL,
  timestamp timestamptz NOT NULL DEFAULT now(),
  note text NOT NULL DEFAULT ''
);
```

- [ ] **Step 2: Declare the `?raw` module type**

Append to `src/env.d.ts` (create if missing with the Astro reference line):

```ts
/// <reference types="astro/client" />
declare module '*.sql?raw' {
  const contents: string;
  export default contents;
}
```

- [ ] **Step 3: Write `src/server/seed.ts` (idempotent — only seeds when empty)**

```ts
import type { Sql } from 'postgres';

// The two default pipelines from the spec (§9). Shared early stages, then a divergent tail.
const SHARED = [
  { name: 'Proposal', owner: 'internal', docs: ['signed proposal'] },
  { name: 'Requirement Discussion', owner: 'shared', docs: [] },
  { name: 'BRS', owner: 'client', docs: ['BRS'] },
  { name: 'Quotation', owner: 'internal', docs: ['quotation'] },
  { name: 'Contract', owner: 'shared', docs: ['signed contract'] },
] as const;

const POS_TAIL = [
  { name: 'System/Hardware Requirement Confirmation', owner: 'client', docs: [] },
  { name: 'Wireframe', owner: 'internal', docs: [] },
  { name: 'UI/UX', owner: 'internal', docs: [] },
  { name: 'Development', owner: 'internal', docs: [] },
  { name: 'Client Testing/Feedback', owner: 'client', docs: [] },
  { name: 'Launch/Deployment', owner: 'shared', docs: [] },
  { name: 'Handover & Resource Assignment', owner: 'internal', docs: [] },
] as const;

const WEB_TAIL = [
  { name: 'Content/Brand Assets Collection', owner: 'client', docs: ['brand assets'] },
  { name: 'Wireframe', owner: 'internal', docs: [] },
  { name: 'UI/UX', owner: 'internal', docs: [] },
  { name: 'Development', owner: 'internal', docs: [] },
  { name: 'Client Review/Revisions', owner: 'client', docs: [] },
  { name: 'Launch', owner: 'shared', docs: [] },
  { name: 'Handover', owner: 'internal', docs: [] },
] as const;

export async function seedIfEmpty(sql: Sql) {
  const [{ count }] = await sql`SELECT count(*)::int AS count FROM project_types`;
  if (count > 0) return;

  for (const [typeName, tail] of [['POS', POS_TAIL], ['Creative Website', WEB_TAIL]] as const) {
    const [type] = await sql`INSERT INTO project_types (name) VALUES (${typeName}) RETURNING id`;
    const [tpl] = await sql`
      INSERT INTO pipeline_templates (project_type_id, name)
      VALUES (${type.id}, ${typeName + ' Pipeline'}) RETURNING id`;
    const stages = [...SHARED, ...tail];
    for (let i = 0; i < stages.length; i++) {
      const s = stages[i];
      await sql`
        INSERT INTO stage_templates (pipeline_template_id, ord, name, owner_type, required_documents)
        VALUES (${tpl.id}, ${i + 1}, ${s.name}, ${s.owner}, ${sql.array([...s.docs])})`;
    }
  }
}
```

- [ ] **Step 4: Write `src/server/db.ts`**

```ts
import postgres from 'postgres';
import schema from '../../db/schema.sql?raw';
import { seedIfEmpty } from './seed';

export const sql = postgres(process.env.DATABASE_URL!);

let ready: Promise<void> | undefined;
export function initDb(): Promise<void> {
  // ponytail: apply schema + seed once per process; add a migration tool when the schema churns.
  return (ready ??= (async () => {
    await sql.unsafe(schema);
    await seedIfEmpty(sql);
  })());
}
```

- [ ] **Step 5: Write the gated integration test `src/server/db.test.mjs`**

```js
import assert from 'node:assert';

if (!process.env.DATABASE_URL) {
  console.log('SKIP db.test — no DATABASE_URL');
  process.exit(0);
}
const { sql, initDb } = await import('./db.ts');
await initDb();
const types = await sql`SELECT name FROM project_types ORDER BY name`;
assert.deepStrictEqual(types.map((t) => t.name), ['Creative Website', 'POS']);
const stages = await sql`SELECT count(*)::int c FROM stage_templates`;
assert.strictEqual(stages[0].c, 24); // 12 per pipeline
await initDb(); // idempotent — second call must not double-seed
const again = await sql`SELECT count(*)::int c FROM project_types`;
assert.strictEqual(again[0].c, 2);
console.log('db.test OK');
await sql.end();
```

- [ ] **Step 6: Run it (with a Postgres available)**

Run: `DATABASE_URL=postgres://... node src/server/db.test.mjs`
Expected: `db.test OK` (or `SKIP` if no DB). Node 24 strips the `.ts` import types automatically.

- [ ] **Step 7: Commit**

```bash
git add db/schema.sql src/env.d.ts src/server/seed.ts src/server/db.ts src/server/db.test.mjs
git commit -m "✨ postgres schema, client, idempotent seed"
```

---

### Task 3: Auth module (one-password HMAC cookie) — TDD

**Files:**
- Create: `src/server/auth.mjs`
- Create: `src/server/auth.test.mjs`
- Modify: `package.json` (add `test:auth` script)

**Interfaces:**
- Produces (from `auth.mjs`):
  - `checkPassword(input: string): boolean`
  - `sessionCookie(): string` — a `Set-Cookie` value
  - `clearCookie(): string`
  - `isAuthed(request: Request): boolean`

- [ ] **Step 1: Write the failing test `src/server/auth.test.mjs`**

```js
import assert from 'node:assert';
process.env.APP_SECRET = 'test-secret';
process.env.APP_PASSWORD = 'hunter2';
const { checkPassword, sessionCookie, isAuthed } = await import('./auth.mjs');

// password check
assert.strictEqual(checkPassword('hunter2'), true);
assert.strictEqual(checkPassword('wrong'), false);
assert.strictEqual(checkPassword(''), false);

// a valid cookie authenticates; a tampered one does not
const setCookie = sessionCookie();
const value = setCookie.split(';')[0].split('=').slice(1).join('=');
const authed = new Request('http://x', { headers: { cookie: `kwg_pw=${value}` } });
assert.strictEqual(isAuthed(authed), true);

const tampered = new Request('http://x', { headers: { cookie: `kwg_pw=${value}x` } });
assert.strictEqual(isAuthed(tampered), false);
assert.strictEqual(isAuthed(new Request('http://x')), false);
console.log('auth.test OK');
```

- [ ] **Step 2: Run to verify it fails**

Run: `node src/server/auth.test.mjs`
Expected: FAIL — `Cannot find module './auth.mjs'`.

- [ ] **Step 3: Implement `src/server/auth.mjs`**

```js
import crypto from 'node:crypto';

const SECRET = process.env.APP_SECRET || 'dev-insecure-secret';
const COOKIE = 'kwg_pw';
const PAYLOAD = 'ok';

const hmac = (v) => crypto.createHmac('sha256', SECRET).update(v).digest('hex');

function sign(v) {
  return `${v}.${hmac(v)}`;
}
function verify(signed) {
  if (!signed) return null;
  const i = signed.lastIndexOf('.');
  if (i < 0) return null;
  const v = signed.slice(0, i);
  const want = Buffer.from(sign(v));
  const got = Buffer.from(signed);
  if (want.length !== got.length) return null;
  return crypto.timingSafeEqual(want, got) ? v : null;
}

export function checkPassword(input) {
  const a = Buffer.from(String(input));
  const b = Buffer.from(process.env.APP_PASSWORD || '');
  return a.length === b.length && a.length > 0 && crypto.timingSafeEqual(a, b);
}

export function sessionCookie() {
  return `${COOKIE}=${sign(PAYLOAD)}; HttpOnly; SameSite=Lax; Path=/; Max-Age=2592000`;
}
export function clearCookie() {
  return `${COOKIE}=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0`;
}
export function isAuthed(request) {
  const cookie = request.headers.get('cookie') || '';
  const match = cookie.split(';').map((c) => c.trim()).find((c) => c.startsWith(COOKIE + '='));
  if (!match) return false;
  return verify(match.slice(COOKIE.length + 1)) === PAYLOAD;
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `node src/server/auth.test.mjs`
Expected: `auth.test OK`.

- [ ] **Step 5: Add script + commit**

Add to `package.json` scripts: `"test:auth": "node src/server/auth.test.mjs"`.

```bash
git add src/server/auth.mjs src/server/auth.test.mjs package.json
git commit -m "✨ one-password HMAC session (tdd)"
```

---

### Task 4: Pipeline derived views (pure) — TDD

**Files:**
- Create: `src/server/pipeline.mjs`
- Create: `src/server/pipeline.test.mjs`
- Modify: `package.json` (add `test:pipeline` script)

**Interfaces:**
- Produces (from `pipeline.mjs`), where a stage is `{ord, name, owner_type, status, blocked_since}`:
  - `currentStage(stages): stage | null` — earliest `ord` whose status ∉ {done, skipped}
  - `blockedOnWho(stages): 'you' | 'client' | 'nobody'`
  - `daysWaiting(blockedSince: string|null, now: Date): number`
  - `preContractWarning(stages): boolean`

- [ ] **Step 1: Write the failing test `src/server/pipeline.test.mjs`**

```js
import assert from 'node:assert';
const { currentStage, blockedOnWho, daysWaiting, preContractWarning } = await import('./pipeline.mjs');

const S = (ord, name, owner_type, status, blocked_since = null) => ({ ord, name, owner_type, status, blocked_since });

// currentStage: earliest non-done/non-skipped
const a = [S(1, 'Proposal', 'internal', 'done'), S(2, 'BRS', 'client', 'waiting_on_client'), S(3, 'Dev', 'internal', 'not_started')];
assert.strictEqual(currentStage(a).ord, 2);
assert.strictEqual(currentStage([S(1, 'x', 'internal', 'done')]), null);
// skipped is treated as passed
assert.strictEqual(currentStage([S(1, 'x', 'internal', 'skipped'), S(2, 'y', 'internal', 'in_progress')]).ord, 2);

// blockedOnWho
assert.strictEqual(blockedOnWho(a), 'client');                       // current is waiting_on_client
assert.strictEqual(blockedOnWho([S(1, 'x', 'internal', 'in_progress')]), 'you');
assert.strictEqual(blockedOnWho([S(1, 'x', 'client', 'not_started')]), 'client'); // client-owned = waiting on them
assert.strictEqual(blockedOnWho([S(1, 'x', 'internal', 'done')]), 'nobody');

// daysWaiting
const now = new Date('2026-07-10T00:00:00Z');
assert.strictEqual(daysWaiting('2026-07-01T00:00:00Z', now), 9);
assert.strictEqual(daysWaiting(null, now), 0);

// preContractWarning: Development active while Contract not done
const risky = [S(5, 'Contract', 'shared', 'in_progress'), S(9, 'Development', 'internal', 'in_progress')];
assert.strictEqual(preContractWarning(risky), true);
const safe = [S(5, 'Contract', 'shared', 'done'), S(9, 'Development', 'internal', 'in_progress')];
assert.strictEqual(preContractWarning(safe), false);
console.log('pipeline.test OK');
```

- [ ] **Step 2: Run to verify it fails**

Run: `node src/server/pipeline.test.mjs`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `src/server/pipeline.mjs`**

```js
const PASSED = new Set(['done', 'skipped']);

export function currentStage(stages) {
  return [...stages].sort((a, b) => a.ord - b.ord).find((s) => !PASSED.has(s.status)) ?? null;
}

export function blockedOnWho(stages) {
  const cs = currentStage(stages);
  if (!cs) return 'nobody';
  if (cs.status === 'waiting_on_client') return 'client';
  if (cs.owner_type === 'client') return 'client';
  return 'you';
}

export function daysWaiting(blockedSince, now) {
  if (!blockedSince) return 0;
  return Math.max(0, Math.floor((now.getTime() - new Date(blockedSince).getTime()) / 86400000));
}

export function preContractWarning(stages) {
  const contract = stages.find((s) => /contract/i.test(s.name));
  const dev = stages.find((s) => /development/i.test(s.name));
  return (
    !!dev && (dev.status === 'in_progress' || dev.status === 'done') &&
    !!contract && contract.status !== 'done' && contract.status !== 'skipped'
  );
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `node src/server/pipeline.test.mjs`
Expected: `pipeline.test OK`.

- [ ] **Step 5: Add script + commit**

Add to `package.json` scripts: `"test:pipeline": "node src/server/pipeline.test.mjs"`.

```bash
git add src/server/pipeline.mjs src/server/pipeline.test.mjs package.json
git commit -m "✨ pipeline derived views (tdd)"
```

---

### Task 5: Login endpoint + auth guard helper

**Files:**
- Create: `src/server/guard.ts`
- Create: `src/pages/api/login.ts`

**Interfaces:**
- Consumes: `checkPassword`, `sessionCookie`, `isAuthed` from `auth.mjs`.
- Produces: `guard(request): Response | null` from `guard.ts` — returns a 401 Response if unauthenticated, else `null`.

- [ ] **Step 1: Write `src/server/guard.ts`**

```ts
import { isAuthed } from './auth.mjs';

export function guard(request: Request): Response | null {
  return isAuthed(request) ? null : new Response('unauthorized', { status: 401 });
}
```

- [ ] **Step 2: Write `src/pages/api/login.ts`**

```ts
import type { APIContext } from 'astro';
import { checkPassword, sessionCookie } from '../../server/auth.mjs';

export const prerender = false;

export async function POST({ request }: APIContext) {
  const { password } = await request.json().catch(() => ({ password: '' }));
  if (!checkPassword(password)) return new Response('nope', { status: 401 });
  return new Response(null, { status: 204, headers: { 'set-cookie': sessionCookie() } });
}
```

- [ ] **Step 3: Smoke-test against the dev server**

Run (dev server started with env set): 
`curl -si localhost:4321/api/login -d '{"password":"<APP_PASSWORD>"}' | grep -i set-cookie`
Expected: a `set-cookie: kwg_pw=...` header. Wrong password → HTTP 401.

- [ ] **Step 4: Commit**

```bash
git add src/server/guard.ts src/pages/api/login.ts
git commit -m "✨ /api/login + auth guard"
```

---

### Task 6: Projects endpoints (list with rollup, create-from-template)

**Files:**
- Create: `src/pages/api/projects.ts`

**Interfaces:**
- Consumes: `sql`, `initDb` (db.ts); `guard` (guard.ts); `currentStage`, `blockedOnWho`, `daysWaiting`, `preContractWarning` (pipeline.mjs).
- Produces:
  - `GET /api/projects` → `[{...project, current_stage, blocked_on, days_waiting, warn}]`
  - `POST /api/projects {client_name, project_type_id}` → `{id}` (201). Clones the type's pipeline stages.

- [ ] **Step 1: Write `src/pages/api/projects.ts`**

```ts
import type { APIContext } from 'astro';
import { sql, initDb } from '../../server/db';
import { guard } from '../../server/guard';
import { currentStage, blockedOnWho, daysWaiting, preContractWarning } from '../../server/pipeline.mjs';

export const prerender = false;

export async function GET({ request }: APIContext) {
  const denied = guard(request);
  if (denied) return denied;
  await initDb();

  const projects = await sql`SELECT * FROM projects ORDER BY created_date DESC`;
  const stages = await sql`SELECT project_id, ord, name, owner_type, status, blocked_since FROM project_stages ORDER BY ord`;
  const byProject = new Map<number, any[]>();
  for (const s of stages) (byProject.get(s.project_id) ?? byProject.set(s.project_id, []).get(s.project_id))!.push(s);

  const now = new Date();
  const rows = projects.map((p) => {
    const ss = byProject.get(p.id) ?? [];
    const cs = currentStage(ss);
    return {
      ...p,
      current_stage: cs?.name ?? null,
      blocked_on: blockedOnWho(ss),
      days_waiting: cs ? daysWaiting(cs.blocked_since, now) : 0,
      warn: preContractWarning(ss),
    };
  });
  return Response.json(rows);
}

export async function POST({ request }: APIContext) {
  const denied = guard(request);
  if (denied) return denied;
  await initDb();

  const { client_name, project_type_id } = await request.json();
  if (!client_name || !project_type_id) return new Response('bad request', { status: 400 });

  const [tpl] = await sql`
    SELECT id FROM pipeline_templates WHERE project_type_id = ${project_type_id} ORDER BY version DESC LIMIT 1`;
  if (!tpl) return new Response('no pipeline for type', { status: 400 });

  const id = await sql.begin(async (tx) => {
    const [proj] = await tx`
      INSERT INTO projects (client_name, project_type_id, pipeline_template_id)
      VALUES (${client_name}, ${project_type_id}, ${tpl.id}) RETURNING id`;
    // ponytail: clone stage_templates → project_stages so template edits never touch live projects.
    await tx`
      INSERT INTO project_stages (project_id, stage_template_id, ord, name, owner_type, required_documents)
      SELECT ${proj.id}, id, ord, name, owner_type, required_documents
      FROM stage_templates WHERE pipeline_template_id = ${tpl.id} ORDER BY ord`;
    await tx`INSERT INTO activity_log (project_id, action) VALUES (${proj.id}, 'project created')`;
    return proj.id;
  });
  return Response.json({ id }, { status: 201 });
}
```

- [ ] **Step 2: Smoke-test (dev server + valid cookie in `$C`)**

Run: `curl -s -H "cookie: $C" localhost:4321/api/projects -d '{"client_name":"Acme","project_type_id":1}'`
Expected: `{"id":1}`. Then `curl -s -H "cookie: $C" localhost:4321/api/projects` shows Acme with `blocked_on` set and 12 cloned stages in the DB.

- [ ] **Step 3: Commit**

```bash
git add src/pages/api/projects.ts
git commit -m "✨ /api/projects list+create-from-template"
```

---

### Task 7: Project detail + stage update endpoints

**Files:**
- Create: `src/pages/api/projects/[id].ts`
- Create: `src/pages/api/stages/[id].ts`

**Interfaces:**
- Produces:
  - `GET /api/projects/:id` → `{project, stages:[...], documents:[...], activity:[...], rollup:{blocked_on, warn}}`
  - `PATCH /api/stages/:id {status?, notes?, blocked_reason?, skip_reason?, approved_by?}` → `{ok:true}`.
    Sets `blocked_since` on entering `waiting_on_client`; `started_at` on first `in_progress`; `completed_at` on `done`. Requires `blocked_reason` for `waiting_on_client`/`blocked_internal`; requires `skip_reason`+`approved_by` for `skipped`. Writes `activity_log`.

- [ ] **Step 1: Write `src/pages/api/projects/[id].ts`**

```ts
import type { APIContext } from 'astro';
import { sql, initDb } from '../../../server/db';
import { guard } from '../../../server/guard';
import { blockedOnWho, preContractWarning } from '../../../server/pipeline.mjs';

export const prerender = false;

export async function GET({ request, params }: APIContext) {
  const denied = guard(request);
  if (denied) return denied;
  await initDb();
  const id = Number(params.id);

  const [project] = await sql`SELECT * FROM projects WHERE id = ${id}`;
  if (!project) return new Response('not found', { status: 404 });
  const stages = await sql`SELECT * FROM project_stages WHERE project_id = ${id} ORDER BY ord`;
  const documents = await sql`
    SELECT d.* FROM documents d JOIN project_stages s ON s.id = d.project_stage_id
    WHERE s.project_id = ${id} ORDER BY d.uploaded_at DESC`;
  const activity = await sql`SELECT * FROM activity_log WHERE project_id = ${id} ORDER BY timestamp DESC`;

  return Response.json({
    project,
    stages,
    documents,
    activity,
    rollup: { blocked_on: blockedOnWho(stages), warn: preContractWarning(stages) },
  });
}
```

- [ ] **Step 2: Write `src/pages/api/stages/[id].ts`**

```ts
import type { APIContext } from 'astro';
import { sql, initDb } from '../../../server/db';
import { guard } from '../../../server/guard';

export const prerender = false;

export async function PATCH({ request, params }: APIContext) {
  const denied = guard(request);
  if (denied) return denied;
  await initDb();
  const id = Number(params.id);
  const body = await request.json();

  const [stage] = await sql`SELECT * FROM project_stages WHERE id = ${id}`;
  if (!stage) return new Response('not found', { status: 404 });

  const status: string = body.status ?? stage.status;
  if ((status === 'waiting_on_client' || status === 'blocked_internal') && !body.blocked_reason)
    return new Response('blocked_reason required', { status: 400 });
  if (status === 'skipped' && (!body.skip_reason || !body.approved_by))
    return new Response('skip_reason and approved_by required', { status: 400 });

  const now = new Date();
  await sql.begin(async (tx) => {
    await tx`
      UPDATE project_stages SET
        status = ${status},
        notes = ${body.notes ?? stage.notes},
        blocked_reason = ${status === 'waiting_on_client' || status === 'blocked_internal' ? body.blocked_reason : null},
        blocked_since = ${status === 'waiting_on_client' ? (stage.blocked_since ?? now) : null},
        started_at = ${stage.started_at ?? (status === 'in_progress' ? now : null)},
        completed_at = ${status === 'done' ? (stage.completed_at ?? now) : stage.completed_at}
      WHERE id = ${id}`;

    const action =
      status === 'skipped'
        ? `skipped "${stage.name}" — ${body.skip_reason} (approved by ${body.approved_by})`
        : `"${stage.name}" → ${status}${body.blocked_reason ? ' — ' + body.blocked_reason : ''}`;
    await tx`INSERT INTO activity_log (project_id, action) VALUES (${stage.project_id}, ${action})`;
  });
  return Response.json({ ok: true });
}
```

- [ ] **Step 3: Smoke-test**

Run: `curl -s -X PATCH -H "cookie: $C" localhost:4321/api/stages/2 -d '{"status":"waiting_on_client"}'`
Expected: HTTP 400 `blocked_reason required`. Retry with `-d '{"status":"waiting_on_client","blocked_reason":"awaiting BRS"}'` → `{"ok":true}`; GET the project and confirm `blocked_since` is set and an activity row appended.

- [ ] **Step 4: Commit**

```bash
git add src/pages/api/projects/[id].ts src/pages/api/stages/[id].ts
git commit -m "✨ project detail + stage update endpoints"
```

---

### Task 8: Documents, team, assignments, activity endpoints

**Files:**
- Create: `src/pages/api/documents.ts`
- Create: `src/pages/api/team.ts`
- Create: `src/pages/api/projects/[id]/assignments.ts`
- Create: `src/pages/api/types.ts`

**Interfaces:**
- Produces:
  - `GET /api/types` → project types (for the new-project form)
  - `POST /api/documents {project_stage_id, filename, doc_type, version_number?, uploaded_by?, note?}` → `{id}`. `version_number` required when `doc_type='brs'`.
  - `GET /api/team` → members; `POST /api/team {name, role?, contact?}` → `{id}`
  - `POST /api/projects/:id/assignments {team_member_id, role_on_project?}` → `{id}`

- [ ] **Step 1: Write `src/pages/api/types.ts`**

```ts
import type { APIContext } from 'astro';
import { sql, initDb } from '../../server/db';
import { guard } from '../../server/guard';

export const prerender = false;

export async function GET({ request }: APIContext) {
  const denied = guard(request);
  if (denied) return denied;
  await initDb();
  return Response.json(await sql`SELECT id, name FROM project_types ORDER BY name`);
}
```

- [ ] **Step 2: Write `src/pages/api/documents.ts`**

```ts
import type { APIContext } from 'astro';
import { sql, initDb } from '../../server/db';
import { guard } from '../../server/guard';

export const prerender = false;

export async function POST({ request }: APIContext) {
  const denied = guard(request);
  if (denied) return denied;
  await initDb();
  const b = await request.json();
  if (!b.project_stage_id || !b.filename || !b.doc_type) return new Response('bad request', { status: 400 });
  if (b.doc_type === 'brs' && !b.version_number) return new Response('version_number required for BRS', { status: 400 });

  const [row] = await sql`
    INSERT INTO documents (project_stage_id, filename, doc_type, version_number, uploaded_by, note)
    VALUES (${b.project_stage_id}, ${b.filename}, ${b.doc_type}, ${b.version_number ?? null}, ${b.uploaded_by ?? ''}, ${b.note ?? ''})
    RETURNING id`;
  const [{ project_id }] = await sql`SELECT project_id FROM project_stages WHERE id = ${b.project_stage_id}`;
  await sql`INSERT INTO activity_log (project_id, action) VALUES (${project_id}, ${'document: ' + b.filename + (b.version_number ? ' r' + b.version_number : '')})`;
  return Response.json({ id: row.id }, { status: 201 });
}
```

- [ ] **Step 3: Write `src/pages/api/team.ts`**

```ts
import type { APIContext } from 'astro';
import { sql, initDb } from '../../server/db';
import { guard } from '../../server/guard';

export const prerender = false;

export async function GET({ request }: APIContext) {
  const denied = guard(request);
  if (denied) return denied;
  await initDb();
  return Response.json(await sql`SELECT * FROM team_members ORDER BY name`);
}

export async function POST({ request }: APIContext) {
  const denied = guard(request);
  if (denied) return denied;
  await initDb();
  const b = await request.json();
  if (!b.name) return new Response('name required', { status: 400 });
  const [row] = await sql`
    INSERT INTO team_members (name, role, contact) VALUES (${b.name}, ${b.role ?? ''}, ${b.contact ?? ''}) RETURNING id`;
  return Response.json({ id: row.id }, { status: 201 });
}
```

- [ ] **Step 4: Write `src/pages/api/projects/[id]/assignments.ts`**

```ts
import type { APIContext } from 'astro';
import { sql, initDb } from '../../../../server/db';
import { guard } from '../../../../server/guard';

export const prerender = false;

export async function POST({ request, params }: APIContext) {
  const denied = guard(request);
  if (denied) return denied;
  await initDb();
  const b = await request.json();
  if (!b.team_member_id) return new Response('team_member_id required', { status: 400 });
  const [row] = await sql`
    INSERT INTO project_assignments (project_id, team_member_id, role_on_project)
    VALUES (${Number(params.id)}, ${b.team_member_id}, ${b.role_on_project ?? ''}) RETURNING id`;
  return Response.json({ id: row.id }, { status: 201 });
}
```

- [ ] **Step 5: Smoke-test each** (with cookie `$C`): create a team member, assign to project 1, add a BRS document without `version_number` (expect 400) then with it (expect 201). `GET /api/types` returns POS + Creative Website.

- [ ] **Step 6: Commit**

```bash
git add src/pages/api/documents.ts src/pages/api/team.ts src/pages/api/projects/[id]/assignments.ts src/pages/api/types.ts
git commit -m "✨ documents, team, assignments, types endpoints"
```

---

### Task 9: Page shell, server auth gate, login screen, API client

**Files:**
- Create: `src/pages/vault/projects.astro`
- Create: `src/scripts/projects/api.ts`
- Create: `src/scripts/projects/app.ts`

**Interfaces:**
- Consumes: all `/api/*` endpoints.
- Produces: `api` object in `api.ts` (`get`, `post`, `patch` helpers, credentials included); `mount()` in `app.ts` that renders the login screen when `GET /api/projects` returns 401, else boots the router (Task 10).

- [ ] **Step 1: Write `src/scripts/projects/api.ts`**

```ts
const j = async (r: Response) => {
  if (r.status === 401) throw { unauth: true };
  if (!r.ok) throw new Error((await r.text()) || r.statusText);
  return r.status === 204 ? null : r.json();
};

export const api = {
  get: (p: string) => fetch('/api' + p).then(j),
  post: (p: string, body: unknown) =>
    fetch('/api' + p, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) }).then(j),
  patch: (p: string, body: unknown) =>
    fetch('/api' + p, { method: 'PATCH', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) }).then(j),
};
```

- [ ] **Step 2: Write `src/scripts/projects/app.ts` (login gate + boot)**

```ts
import { api } from './api';
import { startRouter } from './router';

const app = document.getElementById('app')!;

function loginScreen() {
  app.innerHTML = `
    <form class="gate__form" id="login">
      <p class="gate__eyebrow">KWG</p>
      <h1 class="gate__title">Projects</h1>
      <label class="gate__label" for="pw">Password</label>
      <input class="gate__input" id="pw" type="password" autocomplete="current-password" />
      <p class="gate__error" id="err" role="alert"></p>
      <button class="gate__submit" type="submit">Enter</button>
    </form>`;
  app.querySelector('#login')!.addEventListener('submit', async (e) => {
    e.preventDefault();
    const pw = (app.querySelector('#pw') as HTMLInputElement).value;
    const res = await fetch('/api/login', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ password: pw }) });
    if (res.ok) boot();
    else app.querySelector('#err')!.textContent = 'Incorrect password.';
  });
}

export async function boot() {
  try {
    await api.get('/projects'); // 401 → show login
    startRouter(app);
  } catch (e: any) {
    if (e?.unauth) loginScreen();
    else app.innerHTML = `<p class="page__caption">Error: ${e?.message ?? e}</p>`;
  }
}

boot();
```

- [ ] **Step 3: Write `src/pages/vault/projects.astro`** (SSR shell — reuses the vault gate styles)

```astro
---
import '../../styles/index.scss';
export const prerender = false;
---

<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="theme-color" content="#000000" />
    <meta name="robots" content="noindex" />
    <title>Projects — Vault — KWG</title>
    <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300..700&display=swap" />
  </head>
  <body>
    <main class="page">
      <a class="page__back" href="/vault">← Vault</a>
      <div id="app"></div>
    </main>
    <script>
      import '../../scripts/projects/app';
    </script>
    <style lang="scss" is:global>
      // Reuses the .gate__* / .page__* patterns from vault.astro + fitness.astro.
      // Full component styles land with each view task; this shell just centers #app.
      .page { max-width: var(--grid-max-width); margin-inline: auto; padding: clamp-fluid(24, 56) var(--grid-margin); min-height: 100svh; }
    </style>
  </body>
</html>
```

- [ ] **Step 4: Browser smoke-test**

Build + run server with env. Visit `/vault/projects` in a browser: the login screen shows; wrong password shows the error; correct password swaps to the (empty) router view without a full reload. `astro check && astro build` green.

- [ ] **Step 5: Commit**

```bash
git add src/pages/vault/projects.astro src/scripts/projects/api.ts src/scripts/projects/app.ts
git commit -m "✨ projects page shell + login gate + api client"
```

---

### Task 10: Router + project list view

**Files:**
- Create: `src/scripts/projects/router.ts`
- Create: `src/scripts/projects/views/list.ts`
- Create: `src/scripts/projects/format.ts`

**Interfaces:**
- Consumes: `api` (api.ts).
- Produces: `startRouter(root: HTMLElement): void` — hash routes `#/` (list), `#/p/:id` (detail, Task 12), `#/team` (Task 13); `renderList(root)` in `views/list.ts`; `esc(s)` HTML-escape + `chip(blockedOn)` in `format.ts`.

- [ ] **Step 1: Write `src/scripts/projects/format.ts`**

```ts
export const esc = (s: unknown) =>
  String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!);

export const chip = (blockedOn: string) =>
  blockedOn === 'client' ? 'Waiting on client' : blockedOn === 'you' ? 'On you' : 'Clear';
```

- [ ] **Step 2: Write `src/scripts/projects/router.ts`**

```ts
import { renderList } from './views/list';
import { renderProject } from './views/project';
import { renderTeam } from './views/team';

export function startRouter(root: HTMLElement) {
  const route = async () => {
    const hash = location.hash || '#/';
    const m = hash.match(/^#\/p\/(\d+)$/);
    if (m) return renderProject(root, Number(m[1]));
    if (hash === '#/team') return renderTeam(root);
    return renderList(root);
  };
  window.addEventListener('hashchange', route);
  route();
}
```

- [ ] **Step 3: Write `src/scripts/projects/views/list.ts`**

```ts
import { api } from '../api';
import { esc, chip } from '../format';

export async function renderList(root: HTMLElement) {
  const projects = await api.get('/projects');
  root.innerHTML = `
    <header class="pv__head">
      <h1 class="page__title">Projects</h1>
      <nav class="pv__nav">
        <a href="#/team">Team</a>
        <button id="new" type="button">+ New project</button>
      </nav>
    </header>
    <ul class="pv__list" role="list">
      ${projects.length ? projects.map((p: any) => `
        <li class="pcard pcard--${p.blocked_on}">
          <a class="pcard__link" href="#/p/${p.id}">
            <span class="pcard__name">${esc(p.client_name)}${p.warn ? ' <span class="pcard__warn" title="Work started before contract signed">⚠</span>' : ''}</span>
            <span class="pcard__stage">${esc(p.current_stage ?? 'Complete')}</span>
            <span class="pcard__chip">${chip(p.blocked_on)}${p.days_waiting ? ` · ${p.days_waiting}d` : ''}</span>
          </a>
        </li>`).join('') : `<li class="page__caption">No projects yet. Create your first one.</li>`}
    </ul>`;
  root.querySelector('#new')!.addEventListener('click', () => (location.hash = '#/new'));
}
```

Note: `#/new` is handled by Task 11 (add its branch to the router there).

- [ ] **Step 4: Add styles** — append to `projects.astro`'s `is:global` style block: `.pv__head`, `.pv__nav`, `.pcard` (dark card, left-accent bar colored by `--c-accent` when `pcard--you`, muted when `pcard--client`), `.pcard__warn` in `--c-accent`. (Reuse the `.row`/`.tool` visual language from `bizz.astro`/`vault.astro`.)

- [ ] **Step 5: Browser smoke-test**

Log in, confirm the list renders the project created via curl in Task 6, shows its current stage + blocked-on chip, and clicking a card sets the hash to `#/p/:id` (detail view lands in Task 12).

- [ ] **Step 6: Commit**

```bash
git add src/scripts/projects/router.ts src/scripts/projects/views/list.ts src/scripts/projects/format.ts src/pages/vault/projects.astro
git commit -m "✨ router + project list view"
```

---

### Task 11: New-project view

**Files:**
- Create: `src/scripts/projects/views/new.ts`
- Modify: `src/scripts/projects/router.ts` (add `#/new` branch)

**Interfaces:**
- Consumes: `api`. Produces: `renderNew(root)`.

- [ ] **Step 1: Write `src/scripts/projects/views/new.ts`**

```ts
import { api } from '../api';
import { esc } from '../format';

export async function renderNew(root: HTMLElement) {
  const types = await api.get('/types');
  root.innerHTML = `
    <a class="pv__back" href="#/">← Projects</a>
    <h1 class="page__title">New project</h1>
    <form id="np" class="np">
      <label class="gate__label">Client name<input class="entry__label" name="client_name" required /></label>
      <label class="gate__label">Project type
        <select class="filters__select" name="project_type_id" required>
          ${types.map((t: any) => `<option value="${t.id}">${esc(t.name)}</option>`).join('')}
        </select>
      </label>
      <button class="entry__add" type="submit">Create</button>
      <p class="gate__error" id="err" role="alert"></p>
    </form>`;
  root.querySelector('#np')!.addEventListener('submit', async (e) => {
    e.preventDefault();
    const f = e.target as HTMLFormElement;
    try {
      const { id } = await api.post('/projects', {
        client_name: (f.elements.namedItem('client_name') as HTMLInputElement).value.trim(),
        project_type_id: Number((f.elements.namedItem('project_type_id') as HTMLSelectElement).value),
      });
      location.hash = `#/p/${id}`;
    } catch (err: any) {
      root.querySelector('#err')!.textContent = err?.message ?? 'Failed';
    }
  });
}
```

- [ ] **Step 2: Wire the route** — in `router.ts` add before the list fallback:

```ts
if (hash === '#/new') return renderNew(root);
```

and `import { renderNew } from './views/new';` at the top.

- [ ] **Step 3: Browser smoke-test** — click **+ New project**, create "Beta Corp" as Creative Website, land on its detail hash, and confirm via `GET /api/projects` it has 12 cloned stages.

- [ ] **Step 4: Commit**

```bash
git add src/scripts/projects/views/new.ts src/scripts/projects/router.ts
git commit -m "✨ new-project view"
```

---

### Task 12: Project detail view (stage checklist, status, docs, activity)

**Files:**
- Create: `src/scripts/projects/views/project.ts`

**Interfaces:**
- Consumes: `api`, `esc`, `chip`. Produces: `renderProject(root, id)`.

- [ ] **Step 1: Write `src/scripts/projects/views/project.ts`**

```ts
import { api } from '../api';
import { esc, chip } from '../format';

const STATUSES = ['not_started', 'in_progress', 'waiting_on_client', 'blocked_internal', 'done', 'skipped'];

export async function renderProject(root: HTMLElement, id: number) {
  const data = await api.get(`/projects/${id}`);
  const { project, stages, documents, activity, rollup } = data;

  root.innerHTML = `
    <a class="pv__back" href="#/">← Projects</a>
    <h1 class="page__title">${esc(project.client_name)}</h1>
    <p class="page__caption">${chip(rollup.blocked_on)}${rollup.warn ? ' · ⚠ work started before contract signed' : ''}</p>
    <ul class="stages" role="list">
      ${stages.map((s: any) => stageRow(s, documents.filter((d: any) => d.project_stage_id === s.id))).join('')}
    </ul>
    <h2 class="pv__subhead">Activity</h2>
    <ul class="activity" role="list">
      ${activity.map((a: any) => `<li><span>${esc(a.action)}</span><time>${new Date(a.timestamp).toLocaleDateString()}</time></li>`).join('') || '<li class="page__caption">No activity yet.</li>'}
    </ul>`;

  root.querySelectorAll<HTMLSelectElement>('.stage__status').forEach((sel) => {
    sel.addEventListener('change', () => onStatus(id, Number(sel.dataset.stage), sel.value, root));
  });
  root.querySelectorAll<HTMLFormElement>('.docform').forEach((f) => {
    f.addEventListener('submit', (e) => onDoc(e, id, root));
  });
}

function stageRow(s: any, docs: any[]) {
  const req = (s.required_documents ?? []) as string[];
  return `
    <li class="stage stage--${s.owner_type} stage--${s.status}">
      <div class="stage__head">
        <span class="stage__name">${s.ord}. ${esc(s.name)}</span>
        <span class="stage__owner">${s.owner_type}</span>
        <select class="stage__status" data-stage="${s.id}">
          ${STATUSES.map((st) => `<option value="${st}" ${st === s.status ? 'selected' : ''}>${st.replace(/_/g, ' ')}</option>`).join('')}
        </select>
      </div>
      ${s.blocked_reason ? `<p class="stage__blocked">⛔ ${esc(s.blocked_reason)}</p>` : ''}
      ${req.length ? `<p class="stage__req">Expected: ${req.map(esc).join(', ')}</p>` : ''}
      ${docs.length ? `<ul class="stage__docs">${docs.map((d: any) => `<li>${esc(d.filename)}${d.version_number ? ' r' + d.version_number : ''} <em>${esc(d.doc_type)}</em></li>`).join('')}</ul>` : ''}
      <form class="docform" data-stage="${s.id}">
        <input name="filename" placeholder="Document name" class="entry__label" />
        <select name="doc_type" class="filters__select">
          ${['proposal', 'brs', 'quotation', 'contract', 'wireframe', 'other'].map((t) => `<option>${t}</option>`).join('')}
        </select>
        <input name="version_number" type="number" min="1" placeholder="rev" class="entry__amount" />
        <button class="row__del" type="submit" title="Add document record">+</button>
      </form>
    </li>`;
}

async function onStatus(projectId: number, stageId: number, status: string, root: HTMLElement) {
  const body: any = { status };
  if (status === 'waiting_on_client' || status === 'blocked_internal') {
    const reason = prompt('Reason for blocking?'); // ponytail: native prompt; replace with inline field if it grates.
    if (!reason) return renderProject(root, projectId);
    body.blocked_reason = reason;
  }
  if (status === 'skipped') {
    body.skip_reason = prompt('Why skip this stage?');
    body.approved_by = prompt('Who approved skipping it?');
    if (!body.skip_reason || !body.approved_by) return renderProject(root, projectId);
  }
  try {
    await api.patch(`/stages/${stageId}`, body);
  } catch (e: any) {
    alert(e?.message ?? 'Update failed');
  }
  renderProject(root, projectId);
}

async function onDoc(e: Event, projectId: number, root: HTMLElement) {
  e.preventDefault();
  const f = e.target as HTMLFormElement;
  const filename = (f.elements.namedItem('filename') as HTMLInputElement).value.trim();
  if (!filename) return;
  const v = (f.elements.namedItem('version_number') as HTMLInputElement).value;
  try {
    await api.post('/documents', {
      project_stage_id: Number(f.dataset.stage),
      filename,
      doc_type: (f.elements.namedItem('doc_type') as HTMLSelectElement).value,
      version_number: v ? Number(v) : null,
    });
  } catch (err: any) {
    alert(err?.message ?? 'Failed');
  }
  renderProject(root, projectId);
}
```

- [ ] **Step 2: Add styles** — append `.stages`, `.stage` (dark card, left-accent bar by `owner_type`, dim when `stage--done`/`stage--skipped`), `.stage__blocked` in `--c-accent`, `.activity` list, `.docform` inline row, to the `projects.astro` global style block, reusing existing tokens.

- [ ] **Step 3: Browser smoke-test (the core loop)**

On a project: change BRS to **waiting_on_client** → prompted for a reason → card shows ⛔ reason, list chip becomes "Waiting on client" with a day counter. Add a BRS document without a rev → rejected (alert); with a rev → appears under the stage and in Activity. Set Development to in_progress while Contract ≠ done → the ⚠ warning shows on the list and detail.

- [ ] **Step 4: Commit**

```bash
git add src/scripts/projects/views/project.ts src/pages/vault/projects.astro
git commit -m "✨ project detail: stage checklist, docs, activity"
```

---

### Task 13: Team view

**Files:**
- Create: `src/scripts/projects/views/team.ts`

**Interfaces:**
- Consumes: `api`, `esc`. Produces: `renderTeam(root)`.

- [ ] **Step 1: Write `src/scripts/projects/views/team.ts`**

```ts
import { api } from '../api';
import { esc } from '../format';

export async function renderTeam(root: HTMLElement) {
  const members = await api.get('/team');
  root.innerHTML = `
    <a class="pv__back" href="#/">← Projects</a>
    <h1 class="page__title">Team</h1>
    <ul class="pv__list" role="list">
      ${members.map((m: any) => `<li class="pcard"><span class="pcard__name">${esc(m.name)}</span><span class="pcard__stage">${esc(m.role)}</span><span class="pcard__chip">${esc(m.contact)}</span></li>`).join('') || '<li class="page__caption">No team members yet.</li>'}
    </ul>
    <form id="tm" class="np">
      <input class="entry__label" name="name" placeholder="Name" required />
      <input class="entry__label" name="role" placeholder="Role (dev/designer/…)" />
      <input class="entry__label" name="contact" placeholder="Contact" />
      <button class="entry__add" type="submit">Add member</button>
    </form>`;
  root.querySelector('#tm')!.addEventListener('submit', async (e) => {
    e.preventDefault();
    const f = e.target as HTMLFormElement;
    await api.post('/team', {
      name: (f.elements.namedItem('name') as HTMLInputElement).value.trim(),
      role: (f.elements.namedItem('role') as HTMLInputElement).value.trim(),
      contact: (f.elements.namedItem('contact') as HTMLInputElement).value.trim(),
    });
    renderTeam(root);
  });
}
```

- [ ] **Step 2: Browser smoke-test** — navigate to Team, add a member, confirm it appears and persists across reload.

- [ ] **Step 3: Commit**

```bash
git add src/scripts/projects/views/team.ts
git commit -m "✨ team view"
```

---

### Task 14: Swap the vault tile; retire the money tracker

**Files:**
- Modify: `src/pages/vault.astro`
- Delete: `src/pages/vault/bizz.astro`

**Interfaces:** none (navigation only).

- [ ] **Step 1: Repoint the tile** in `src/pages/vault.astro` — replace the `bizz $$` active tool `<li>`:

```astro
<li class="tool tool--active">
  <a class="tool__link" href="/vault/projects">
    <span class="tool__name">Projects</span>
    <span class="tool__hint">Open</span>
  </a>
</li>
```

- [ ] **Step 2: Delete the money tracker**

```bash
git rm src/pages/vault/bizz.astro
```

(Its code is preserved in this branch's history if ever needed.)

- [ ] **Step 3: Verify**

Run: `astro check && astro build`. Visit `/vault` → the tile reads **Projects** and links to the tool. `/vault/bizz` 404s.

- [ ] **Step 4: Commit**

```bash
git add src/pages/vault.astro
git commit -m "♻️ vault tile bizz $$ → Projects; retire money tracker"
```

---

## Self-Review

**Spec coverage:**
- §2 architecture (hybrid Astro + node + postgres, no ORM) → Tasks 1, 2, 6–8.
- §3 auth (one-password server gate) → Tasks 3, 5, 9.
- §5 data model (all 9 tables, `current_stage` derived) → Task 2; derivation Task 4/6.
- §6 stage lifecycle (statuses, mandatory blocked_reason, skip reason+approver) → Task 7.
- §7 derived views (currentStage, blockedOnWho, daysWaiting, preContractWarning) → Task 4, surfaced Tasks 6/7/10/12.
- §8 documents (records, BRS version required, required_documents checklist) → Tasks 2, 8, 12.
- §9 seeded pipelines (POS + Creative Website, 12 stages each) → Task 2.
- §10 edge cases (pre-contract warning, skip logging, dispute evidence) → Tasks 4, 7, 12.
- §11 screens (list, new, detail, team) → Tasks 10–13.
- §12 deferrals (file bytes, template editor, etc.) → not built, by design.
- §13 testing (node assert files) → Tasks 3, 4 (+ gated db test Task 2).
- §14 infra (env vars, node host) → Task 1 `.env.example`, README note optional.

**Placeholder scan:** the two `prompt()`/`alert()` calls in Task 12 are deliberate (marked `ponytail:`), not placeholders — inline fields are the noted upgrade. No TBD/TODO.

**Type consistency:** `blocked_on` values `you|client|nobody` consistent across pipeline.mjs, projects.ts, format.ts, list.ts. Status set identical in schema CHECK, stages endpoint, and detail view `STATUSES`. `api.get/post/patch` signatures consistent across all views.

## Execution Handoff

See the closing message.
