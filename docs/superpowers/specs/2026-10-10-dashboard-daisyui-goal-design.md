# Dashboard daisyUI redesign, goal-first — design

Date: 2026-10-10. Surface: `/vault/dashboard` (seven pages) and `dashboard/src/trading.tsx`.
Issues: closes #12, #13, #14, #15, #16 (dashboard KPI parts). Supports #17–#27.
Supersedes the design system in `2026-10-05-dashboard-shadcn-neutral-dark.md`.

## Understanding summary

- Replace shadcn/Radix/Base UI with daisyUI 5 and a custom dark `kwg` theme.
- Rebuild Today and Founder around the 2026 goal: 3-4 retainer clients
  (about $3,200/month) by 31 Dec 2026; floor 1 client by 5 Dec 2026.
- Single user, two isolated workspaces (Personal, Parallel).
- The local-vault engine is unchanged: explicit permission, content-hash
  conflict check, Web Locks, `.history`, six flat folders, 1 MiB limit.
- Non-goals: light theme, server or sync, chart library, marketing-site changes,
  drag-and-drop pipeline.

## Assumptions

1. Goal, lead, conversation and niche data are flat frontmatter read by the
   existing `properties()` parser in `shared/vault-model.js`.
2. The Base UI workspace menu becomes a daisyUI `dropdown`; the README rule to
   retain its Base UI API is retired.
3. Existing element IDs used by `browser-check.mjs` are kept where possible.
4. `trading.tsx` moves from Radix Tabs to native ARIA tabs (decision 9), so `radix-ui` can go.
5. Performance: dashboard bundle grows by no more than 15%. Scale: under 2,000
   notes, computed in memory. Privacy: no network calls, telemetry or uploads.

## Decision log

| # | Decision | Alternatives | Why |
|---|---|---|---|
| 1 | daisyUI classes on plain React elements (approach A) | Re-skin shadcn wrappers (B); `react-daisyui` (C) | Only A fully replaces the system; C lags daisyUI 5 |
| 2 | Goal-first Today and Founder | Swap styling only | Dashboard serves the 2026 goal |
| 3 | One custom dark `kwg` theme | Built-in themes; light toggle | Keeps dark-only rule; one accent |
| 4 | Frontmatter in vault folders | New storage | Local-only constraint |
| 5 | Spec, then one PR | Two PRs; spec only | Owner choice |
| 6 | `trading.tsx` in scope | Keep Radix there | Removes `radix-ui` |
| 7 | Stage change by editing the note | Drag-and-drop | Reuses save, history and conflict checks; YAGNI |
| 8 | Native `<dialog>` for New note | Keep Radix Dialog | Native focus trap, Escape and backdrop |
| 9 | `trading.tsx` uses native ARIA tabs with its existing `.pill-btn` classes, not daisyUI `tabs` | daisyUI `tabs` | `/vault/trading` is marketing-styled and does not load `dashboard.css`; daisyUI there would be unstyled and break the Dashboard Boundary Rule. Still removes `radix-ui` |
| 10 | Pin `daisyui@5.7.43` exactly | Latest 5.7.47 | Latest was 10 days old at implementation; pinned release is over 2 weeks old |
| 11 | Minimal copy: no subtitles, descriptions, hints, privacy or empty-state text; status and error messages cut to 2-4 words | Remove errors too | Silent save failures risk lost drafts |

## 1. Shell and theme

- Layout: `drawer lg:drawer-open`. `drawer-toggle` is controlled by React
  state. The opener is `<button id="pages-toggle" aria-expanded aria-controls>`.
  Escape closes the drawer and returns focus to it.
- Sidebar order: Back to vault, brand, milestone badge, page `menu`
  (`menu-active` + `aria-current`), Local vault card, workspace `dropdown`.
- Topbar: `navbar` with `breadcrumbs`, connection `badge` (text plus color),
  Quick capture.
- Theme `kwg` via `@plugin "daisyui/theme"`: `default: true`,
  `prefersdark: true`, `color-scheme: dark`.
  - Base: `base-100 oklch(14.5% 0 0)`, `base-200 oklch(20.5% 0 0)`,
    `base-300 oklch(26.9% 0 0)`, `base-content oklch(98.5% 0 0)`.
  - `primary oklch(78% 0.16 75)` (amber), `primary-content oklch(20% 0.03 75)`.
    Amber is reserved for goal progress and primary actions.
  - `success`, `warning`, `error` for pipeline and connection states.
  - `--radius-box .75rem; --radius-field .5rem; --radius-selector 1rem;
    --border 1px; --depth 0; --noise 0; --size-field .275rem` (44 px fields).
- Every `*-content` pair must reach 4.5:1 contrast.

## 2. Goal model and pages

`shared/goal-model.js` (pure, unit-tested):

- `goals(notes)`: `founder/goals-2026.md` with `type: goals`, `target_clients`,
  `floor_clients`, `floor_date`, `target_mrr`, `deadline`. Missing note: `null`.
- `milestones(today)`: M1 Niche 2026-10-24, M2 Offer 2026-11-07,
  M3 First clients 2026-12-05, M4 Retainers + systems 2026-12-31. Returns the
  list, the current index and days left; after the last date, `ended: true`.
- `pipeline(notes, today, week)`: `type: lead` notes grouped by `stage`
  (`lead|contacted|call|proposal|won|lost`). Unknown stage goes to `lead` with
  a warning. Returns stages, `won`, `mrr` (sum of valid `mrr` where won),
  `overdue` (valid `next_date` before today, not won or lost),
  `contactedThisWeek`, and per-lead `warnings`.
- `conversations(notes)`: `type: conversation` count, by `niche`, by `would_pay`.
- `niches(notes)`: `type: niche` with `verdict` and checks `c1`..`c5`.

New templates in `templateChoices` and `makeTemplate`: `niche` (founder),
`conversation` (inbox), `lead` (founder), `goals` (founder).

Today: milestone `steps`; `stats` (clients with `radial-progress`, MRR,
conversations of 20, weeks left); cards for Daily entry and Next actions
(overdue leads + due tasks); week strip. Founder: pipeline columns (horizontal
scroll on mobile), niche `table`, conversation `progress`, existing Open actions
and Decisions. Review: KPI prompts in the weekly template. Journal, Knowledge,
Projects: re-skin only.

## 3. Components, accessibility, errors

| Current | daisyUI |
|---|---|
| Button default/outline/ghost | `btn btn-primary` / `btn-outline` / `btn-ghost` |
| Input, Textarea, Label, NativeSelect | `input`, `textarea`, `label`, `select` |
| Dialog | `<dialog class="modal">` with `showModal()`; focus returns to opener |
| DropdownMenu | `dropdown` + `menu`, `menuitemradio`, arrow/Home/End/Escape handler |
| NavigationMenu | `menu` + `menu-active` |
| Radix Tabs (trading) | Native ARIA tabs with existing `.pill-btn` styles; arrow, Home, End keys |
| Feedback | `alert` with live `role=status` |

- Keep visible focus, reduced motion, 44 px targets, noscript guidance.
- Status never relies on color alone.
- No goals note: stats show "Set your 2026 goal" with a create action.
- Bad `mrr` or `next_date`: ignored in totals; card shows "Check fields".
- After 31 Dec: "Goal period ended" with a link to the review page.
- Existing folder, permission, conflict and unsupported-browser flows keep
  their wording.

## 4. Testing and docs

- Unit: `goal-model.test.mjs`; template round-trip in `vault-model.test.mjs`;
  existing tests unchanged.
- Browser: update selectors; add goal panel, lead won updates stats,
  conversation counter, modal focus, dropdown keys, drawer Escape, trading tabs.
- Bundle size compared before and after.
- Update `DESIGN.md` dashboard exception, `dashboard/ui-spec.yaml`,
  `dashboard/README.md`, `.impeccable/design.json`, `THIRD_PARTY.md`.

## Risks

- Native dialog and dropdown accessibility regressions; covered by browser check.
- Amber contrast; verified before merge.
- Branch base differs from `chore/new-logo`; check icon overlap before the PR.
