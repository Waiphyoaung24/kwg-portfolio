# Dashboard shadcn neutral dark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Apply stock shadcn neutral dark styling exclusively to `/vault/dashboard`, preserving local-file workflows and responsive layout.

**Architecture:** Configure the nested Vite app for shadcn discovery, isolate its CSS from the Astro marketing theme, then migrate existing presentation to semantic roles. Preserve Radix primitives and the custom Base UI menu; no data-layer rewrite or bulk component reinstall.

**Tech Stack:** Astro, React 19, TypeScript, Vite 7, Tailwind CSS 4, Radix UI, Base UI, Lucide.

**Spec:** `docs/superpowers/specs/2026-10-05-dashboard-shadcn-neutral-dark.md`

## Global Constraints

- Other routes retain KWG styling.
- Keep dark mode permanently enabled; no theme switcher.
- Accessibility remains WCAG 2.2 AA.
- Notes remain local; no uploads, telemetry, database storage, automatic permission prompts, or remote migration.
- Keep CSP, no-store headers, unsupported-browser explanation, and noscript content.
- Preserve the existing dirty working tree. Stage only migration hunks if commits are requested.
- Record the owner-approved dashboard exception; dashboard theme values belong in dashboard CSS, while `_vars.scss` remains authoritative elsewhere.

## Review Focus

1. Legacy foreground variables becoming dark backgrounds: check muted text and selected navigation contrast in Task 2.
2. Portaled menus/dialogs outside `#root`: verify theme inheritance and focus restoration in Task 3.
3. Removal of marketing SCSS: verify reset, focus, typography, and noscript readability in Task 2.
4. Revoked permission/cancelled workspace switch with a dirty draft: rerun existing preservation scenarios in Task 3.
5. Long titles, small viewports, and zoom: verify overflow and reachable Save/Pages controls in Task 3.

## Task 1: Configure shadcn discovery

**Files:** Create `dashboard/components.json`; modify `dashboard/tsconfig.json`, `dashboard/vite.config.ts`, `dashboard/README.md`.

**Interfaces:** Consumes `dashboard/src/components/ui/` and `dashboard/src/lib/utils.ts`. Produces CLI-resolvable `@/* -> dashboard/src/*` aliases and configuration pointing to `src/styles.css`.

- [x] Record starting `git status --short` and diff. Run `npm --prefix dashboard run typecheck` and `npm run test:dashboard`; distinguish pre-existing failures.
- [x] From `dashboard/`, run `npx --yes shadcn@latest info --json`. Pre-change evidence: null config/CSS path and an empty component inventory despite eight source files.
- [x] Add official-schema configuration: `style: "new-york"`, `rsc: false`, `tsx: true`, `iconLibrary: "lucide"`; Tailwind `config: ""`, `css: "src/styles.css"`, `baseColor: "neutral"`, `cssVariables: true`, `prefix: ""`. Aliases: components `@/components`, ui `@/components/ui`, utils `@/lib/utils`, lib `@/lib`, hooks `@/hooks`. Validate with the current CLI rather than inventing schema fields.
- [x] Set TypeScript paths `@/*: ["./src/*"]`; add the Vite equivalent using `fileURLToPath(new URL('./src', import.meta.url))`. Retain all current build entry/output/plugin settings.
- [x] Document the existing Radix component family and deliberate Base UI dropdown exception. Do not migrate primitive APIs based on unconfigured CLI defaults.
- [x] Rerun CLI info and typecheck. Verify resolved CSS, aliases, style, and component inventory. Do not run force-init, preset application, or component overwrites.

## Task 2: Isolate and migrate the theme

**Files:** Modify `src/pages/vault/dashboard.astro`, `dashboard/src/styles.css`, `dashboard/shared/tokens.css`, `dashboard/shared/workspace.css`, `DESIGN.md`, `PRODUCT.md`, `dashboard/ui-spec.yaml`.

**Interfaces:** Consumes Task 1 configuration and current geometry tokens. Produces semantic theme variables on `html.dark`, inherited by React and body portals without marketing SCSS.

- [x] Capture baseline route styles/screenshots for page background, heading, primary/outline buttons, muted copy, selected navigation, dialog, and workspace menu. Confirm the forced pills/weights reproduce the mismatch. Use visual checks rather than CSS source-text tests.
- [x] Add a narrowly scoped dashboard exception to DESIGN.md. Update only the dashboard statement in PRODUCT.md and relevant visual fields in `dashboard/ui-spec.yaml`: neutral dark, component radius/weight/elevation, dashboard token ownership, unchanged interactions. Do not replace the site's design system.
- [x] Remove the route's `../../styles/index.scss` import and add `class="dark"` to `<html>`. Preserve route validation, headers, metadata, scripts, and noscript content. Supply dashboard-owned body/noscript styles.
- [x] Define the official neutral dark palette in `dashboard/src/styles.css`, with `--radius: 0.625rem` and Tailwind v4 mappings for background/foreground, card, popover, primary, secondary, muted, accent, destructive, border, input, ring, sidebar, and radii. Add the class-based dark variant. Take exact palette values from the official theme documentation at execution time and record the source. No light theme/provider.
- [x] Before changing variable definitions, migrate legacy text uses of `--muted` to `--muted-foreground`; migrate legacy link/action uses of `--accent` to foreground/primary as appropriate. Keep surface/foreground pairs distinct. Map retained geometry-era aliases (`--bg`, `--surface`, `--text`, `--rail-*`, graph/status roles) without circular references. Remove obsolete blue/light palette fallbacks used by the dashboard.
- [x] Remove KWG alias blocks and forced pill/weight/shadow rules. Preserve centering, responsive media queries, `[hidden]`, focus rules, reduced motion, and draft-related visibility. Put foundational CSS in the base layer and legacy component presentation in the components layer so unlayered rules cannot defeat Tailwind utilities. Verify layout after this precedence change.
- [x] Apply system sans, body 400, actions 500, headings 600, current compact heading sizes, and sentence-case labels. Remove marketing tracking/mono-uppercase rules. Use theme radius/elevation; remove the old raised blue-button presentation.
- [x] Run `npm --prefix dashboard run build`. Inspect actual rendered text contrast and selection colors, theme resolution in body portals, visible keyboard focus, and JavaScript-disabled readability. Compare a public route before/after to prove isolation.

## Task 3: Align controls and verify workflows

**Files:** Modify presentation as needed in `dashboard/src/components/ui/button.tsx`, `dashboard/src/components/ui/dropdown-menu.tsx`, `dashboard/src/App.tsx`, `dashboard/src/NewNote.tsx`, `dashboard/src/Overview.tsx`, `dashboard/src/NoteGraph.tsx`, and `dashboard/src/styles.css`. Inspect existing input, textarea, native-select, label, navigation-menu, and dialog component files; change only demonstrated conflicts. Extend `dashboard/browser-check.mjs`. Build `public/dashboard-assets/dashboard.js` and `public/dashboard-assets/dashboard.css`.

**Interfaces:** Retain Button props/variants, `NewNote({request, notes, onClose, onCreate})`, menu exports, IDs, and handlers. Storage/model modules stay outside this migration.

- [x] After configuration, run `shadcn docs` for changed primitives and read the returned documentation, selecting Radix docs for Radix files and Base UI menu docs for the local menu. Use CLI dry-run/diff for any upstream comparison; never blindly reinstall customized components.
- [x] Remove `.pill-btn` injection from Button. Let variants own visual styling; remove conflicting `.primary-press`/`.face` presentation and obsolete wrappers. Preserve IDs, disabled/saving states, and handlers. Save/Create use primary; secondary actions use outline/ghost. Keep 44-pixel touch targets.
- [x] Style the Base UI menu with popover/accent/foreground tokens and component radii while retaining portal, positioning, radio semantics, and trigger composition. Preserve Radix dialog title/description, outside-click handling, validation, and focus behavior. Keep the current form structure unless necessary; newly introduced form groups use Field/FieldGroup per the skill.
- [x] Align existing overview panels, note rows, navigation, graph controls, and empty/error states through semantic roles and existing components. Preserve content and layout; add no charts, metric cards, sidebar package, or synthetic notes.
- [x] Extend browser scenarios for keyboard menu selection/dismissal, dialog focus entry/restoration, long note titles at 320 pixels, and reachable Save controls at 200% zoom. Assert cancel returns focus to the opener, creation focuses the editor, and the document does not overflow horizontally. Keep all existing permission/draft/conflict/no-upload checks.
- [x] Run `npm run test:dashboard`, `npm --prefix dashboard run typecheck`, and `npm run build`. Start `npm run dev -- --port 4327` and run `node dashboard/browser-check.mjs`. All must pass; identify baseline failures before touching unrelated code.
- [x] Inspect connected/disconnected note pages and Settings at 320, 375, 768, 1024, 1440, and 2560 pixels, plus overlays, zoom, and reduced motion. Measure rendered normal-text contrast at 4.5:1 minimum; verify focus and non-color status cues. Native Windows picker/save smoke checks remain a separate manual check; automated tests use synthetic OPFS folders and chooser/permission substitutes.
- [x] Apply Impeccable's bounded visual verification: one batched desktop/mobile inspection, material fixes together, then one confirmation. Run its detector on changed UI files and obtain its required finish review at implementation time.
- [x] Update README/ui-spec with verified behavior and mixed-base maintenance guidance. Review the diff for unexpected marketing, data, dependency, or generated-asset changes. Commit only migration hunks if requested.

## Review and execution handoff

Implemented on 2026-10-05 in the existing checkout, preserving pre-existing work. Production build, dashboard typecheck, seven unit tests, and the extended production browser suite pass. Independent finish review verdict: ship, with both graph-list findings resolved. Native Windows folder-picker/save smoke verification remains manual; no deployment or commits were requested.

Self-review: every brief requirement maps to a task. Variable collisions, portal inheritance, CSS precedence, dirty-tree preservation, route isolation, and file-safety regressions have explicit checks. Execution evidence is recorded in `.superpowers/sdd/2026-10-05-dashboard-shadcn-neutral-dark/progress.md`; synthetic production captures are in `.impeccable/review/dashboard-neutral/`. Graph list regression checks additionally cover contrast in normal/focus/hover states, stacked text containment, and internal overflow at 320, 375, 720, and 1440 pixels.
