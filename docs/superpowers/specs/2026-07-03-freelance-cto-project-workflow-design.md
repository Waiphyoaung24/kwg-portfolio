# Freelance CTO Project Workflow System — Design Spec

**Date:** 2026-07-03
**Status:** Approved for planning
**Replaces:** the `bizz $$` money-tracker tool at `src/pages/vault/bizz.astro`

## 1. Purpose

A self-hosted vault tool that turns the project lifecycle (Proposal → Requirement →
BRS → Quotation → Contract → Wireframe → UI/UX → Development → Launch) into a
repeatable, trackable system — so every new project starts from a known process,
and it's always visible what's on you vs. what's waiting on the client.

## 2. Architecture (decided)

One framework, one repo, one deploy. No separate backend service — Astro's own
server endpoints are the backend.

- **Rendering:** keep `output: 'static'` (Astro's default) and add the
  `@astrojs/node` adapter (standalone: `node ./dist/server/entry.mjs`). Portfolio
  pages stay prerendered. The tool pages (`/vault/projects`) and every `/api/*`
  endpoint opt into on-demand server rendering with `export const prerender = false`.
  *(Astro 6 removed `output: 'hybrid'`; per-route `prerender = false` is the replacement.)*
- **Database:** Postgres, accessed with the `postgres` (porsager) client — raw
  parameterized SQL via tagged templates. No ORM.
- **Frontend:** vanilla TS island (matching `fitness`/`bizz`), talking to `/api`
  over `fetch`. No new frontend framework.

**New dependencies — exactly two:** `@astrojs/node`, `postgres`. No ORM, no
migration tool, no auth library, no validation library.

### File layout

```
astro.config.mjs                  add @astrojs/node adapter (output stays 'static')
db/schema.sql                     tables (CREATE TABLE IF NOT EXISTS) + seed
src/server/db.ts                  postgres client (reads DATABASE_URL), runs schema.sql on boot
src/server/pipeline.ts            PURE derived views (node-tested)
src/server/auth.ts                one-password gate, HMAC signed cookie (node crypto)
src/pages/api/login.ts            POST → set cookie
src/pages/api/projects.ts         GET list · POST create-from-template
src/pages/api/projects/[id].ts    GET project + stages + rollup
src/pages/api/stages/[id].ts      PATCH status/notes/blocked/skip
src/pages/api/documents.ts        POST document record
src/pages/api/team.ts             GET list · POST member
src/pages/api/projects/[id]/assignments.ts   POST assign member
src/pages/api/activity.ts         GET ?project=:id
src/pages/vault/projects.astro    SSR shell (checks auth cookie) + vanilla-TS island
src/scripts/projects/*            island: router.ts, views/, api.ts (fetch wrappers)
```

### Deliberate simplifications (ponytail)

- **Schema** → single `db/schema.sql`, `CREATE TABLE IF NOT EXISTS`, applied on
  boot. Skipped a migration framework; add Kysely/Drizzle when the schema churns.
- **DB access** → raw SQL. Skipped an ORM for ~9 tables one person queries.
- **Session** → `crypto.createHmac` (stdlib). Skipped `jsonwebtoken`.
- **Derived views** → pure TS over fetched rows. Skipped SQL views/triggers;
  keeps the logic node-testable like `workout-picker.test.mjs`.
- **`current_stage`** → **derived, not stored**. The spec's stored
  `projects.current_stage_id` is dropped; it's computable (earliest
  non-Done/non-Skipped stage) and a stored pointer only invites drift.

## 3. Auth (the one non-lazy part)

The existing vault gate is client-side only (a hashed password in `localStorage`).
That protects nothing once data lives in Postgres — an open `/api/*` leaks data.
So the new tool is gated server-side:

- One shared password in env `APP_PASSWORD`. No accounts, no roles (matches §8/§12).
- `POST /api/login` compares it (constant-time), sets an **HMAC-signed, httpOnly,
  SameSite=Lax** cookie signed with `APP_SECRET` (`crypto.createHmac`, ~30 lines).
- Every `/api/*` handler and `projects.astro` verify the cookie first; missing/invalid
  → 401 / redirect to a minimal login screen.
- Existing `fitness`/`bizz` tools keep their client-side gate, unchanged — only this
  tool has a server and therefore needs real auth.

## 4. Core Concepts

**Project Type** — POS or Creative Website (extensible; more types = more seed rows,
no structural change).

**Pipeline Template** — an ordered list of stages tied to a Project Type. Stored as
data (seed rows), not hardcoded logic.

**Stage Ownership** — every stage is tagged with who must move it forward:
- `internal` — you/your team produce it (Proposal, Wireframe, UI/UX, Development)
- `client` — you can't proceed until the client delivers (BRS, assets, approvals, payment)
- `shared` — both sides negotiate (Requirement discussion, Contract terms)

## 5. Data Model (Postgres)

Integer PKs via `GENERATED ALWAYS AS IDENTITY` (DB-native, no app-side counters).
`owner_type` and `status` are `text` with `CHECK` constraints. Lists use native
`text[]`. Timestamps are `timestamptz`.

- **project_types** — `id, name`
- **pipeline_templates** — `id, project_type_id→project_types, name, version`
- **stage_templates** — `id, pipeline_template_id→pipeline_templates, ord, name,
  owner_type CHECK(internal|client|shared), description, required_documents text[],
  checklist_items text[]`
- **projects** — `id, client_name, project_type_id, pipeline_template_id,
  created_date, status CHECK(active|on_hold|done|cancelled)`
  *(no `current_stage_id` — derived, see §2)*
- **project_stages** *(cloned from stage_templates at project creation, so editing a
  template never mutates live projects)* — `id, project_id→projects,
  stage_template_id, ord, name, owner_type, status CHECK(not_started|in_progress|
  waiting_on_client|blocked_internal|done|skipped), notes, blocked_reason,
  blocked_since, started_at, completed_at`
- **documents** *(records only in v1 — no file bytes)* — `id,
  project_stage_id→project_stages, filename, doc_type CHECK(proposal|brs|quotation|
  contract|wireframe|other), version_number, uploaded_by, uploaded_at, note`
- **team_members** — `id, name, role, contact`
- **project_assignments** — `id, project_id, team_member_id, role_on_project`
- **activity_log** — `id, project_id, actor, action, timestamp, note`

## 6. Stage Lifecycle

Statuses and triggers:

- **not_started** — default when a project is created
- **in_progress** — internal/shared stage actively worked
- **waiting_on_client** — distinct blocked state, auto-suggested for `client`-owned
  stages when the previous stage completes; shows a days-waiting counter
- **blocked_internal** — stuck for a non-client reason; requires `blocked_reason`
- **done** — completed, timestamped (`completed_at`)
- **skipped** — requires a typed reason + who approved it → written to `activity_log`

`blocked_reason` is **mandatory** whenever a stage enters `waiting_on_client` or
`blocked_internal`. No silent blocking.

## 7. Derived Views — the "smooth system" (pure, in `src/server/pipeline.ts`)

All pure functions over fetched rows; each gets a `node --test` case.

- `currentStage(stages)` → earliest non-Done/non-Skipped stage by `ord`.
- `blockedOnWho(stages)` → `'you' | 'client' | 'nobody'`, from the current stage's
  `owner_type` + `status`. **The single most useful signal** for a CTO running
  several projects at once.
- `daysWaiting(stage, now)` → integer days since `blocked_since` for any
  `waiting_on_client` stage.
- `preContractWarning(stages)` → true when a Development stage is active while the
  Contract stage is not Done (§10) → surfaces a warning badge.

## 8. Document & Deliverable Handling (v1: records only)

- Document records attach to a specific `project_stage`, not the project generally —
  findable by stage.
- **Revision tracking matters most for BRS.** `version_number` is required for BRS
  document records; `activity_log` records which revision both sides signed off on.
- `required_documents` on a stage template drives a checklist ("expected: BRS, signed
  proposal") so it's visible what's missing before anything is recorded.
- Actual file bytes are deferred to v2 (see §12) — the dispute-evidence value is in
  *which revision, when, who* (metadata), which v1 captures fully.

## 9. Default Pipeline Templates (seeded in `db/schema.sql`)

**Shared early stages (both pipelines):**
1. Proposal — `internal`
2. Requirement Discussion — `shared`
3. BRS — `client` (version-tracked, §8)
4. Quotation — `internal` (blocks on client approval before project officially starts)
5. Contract — `shared`

**POS Pipeline (diverges after Contract):**
6. System/Hardware Requirement Confirmation — `client`
7. Wireframe — `internal`
8. UI/UX — `internal`
9. Development — `internal`
10. Client Testing/Feedback — `client`
11. Launch/Deployment — `shared`
12. Handover & Resource Assignment — `internal`

**Creative Website Pipeline (diverges after Contract):**
6. Content/Brand Assets Collection — `client`
7. Wireframe — `internal`
8. UI/UX — `internal`
9. Development — `internal`
10. Client Review/Revisions — `client`
11. Launch — `shared`
12. Handover — `internal`

## 10. Edge Cases & Business Rules

- **Work started before contract signed:** Development stage active while Contract ≠
  Done → `preContractWarning` badge on the project (§7).
- **Scope disputes:** versioned, stage-tied document records + `activity_log` preserve
  the evidence (which BRS revision, when). The system preserves evidence; it doesn't
  resolve disputes.
- **Stage skipping:** typed reason + approver, logged in `activity_log` — distinguishes
  "we agreed to skip" from "we forgot."

## 11. Screens (vanilla-TS island)

Hash-routed: `#/` project list · `#/p/:id` project detail · `#/team`.

- **List** — projects with status, current stage, blocked-on-who chip, days-waiting,
  pre-contract warning badge. This is the daily driver.
- **New project** — pick client name + project type → clones the template's stages.
- **Project detail** — the stage checklist: change status, add notes, enter
  blocked/skip reasons, add document records against a stage, see required-docs
  checklist, view the activity log.
- **Team** — flat list of members; assign members to a project with a role label.

Visual language reuses the existing vault tokens (dark, Space Grotesk, `#FFC000`
accent). No restyle.

## 12. Out of Scope for V1 (deliberate deferrals)

- Actual file uploads / byte storage (records only in v1 — smaller lift once the DB exists)
- Template-editor CRUD (v1 ships the 2 seeded pipelines; the daily loop delivers value
  without editing them). Editing later is a small add since templates are already data.
- Dashboard analytics beyond the "blocked on who" rollup
- PDF generation (proposals/quotations/contracts)
- Invoicing / payment tracking
- Client-facing portal or client login
- Notifications/reminders on stale waiting stages
- Full drag-and-drop template builder
- Per-stage task assignment / sub-tasks (assignment is project-level in v1)
- Multi-user auth/roles (one shared password only)

## 13. Testing

- `node --test` files for `pipeline.ts` (all four derived views) and `auth.ts`
  (sign/verify round-trip, tamper rejection) — same convention as
  `workout-picker.test.mjs`. Wire into `package.json` scripts.
- `astro check && astro build` green.

## 14. Infra / Deploy (changes for the operator)

1. **Deploy moves from static-host → Node-host** — something must run
   `node ./dist/server/entry.mjs`.
2. **A Postgres is required** — set `DATABASE_URL` (managed free tier like Neon/Supabase,
   or self-hosted). The app reads the env var and applies `schema.sql` on boot; it does
   not provision the database.
3. **Env vars:** `DATABASE_URL`, `APP_PASSWORD`, `APP_SECRET`.

## 15. Assumptions

- Single user / small trusted team; one shared password, no roles in v1.
- The vault is a self-hosted app you run; hosting/Postgres provisioning is yours.
- Two project types (POS, Creative Website) cover current needs; the model extends to
  more types by adding seed rows, no structural change.
- The `bizz $$` money-tracker code is uncommitted and will be replaced. If it should be
  kept, commit it or move it to a separate tile before implementation.
