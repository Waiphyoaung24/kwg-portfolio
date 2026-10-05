# Dashboard shadcn neutral dark design brief

Status: implemented and verified on 2026-10-05; independent finish review verdict: ship.

## Purpose and decision

The owner uses `/vault/dashboard` to browse, create, edit, and explicitly save local Markdown notes. This is an Operate surface. Success is a consistent stock shadcn neutral dark interface across note pages, Settings, graph, workspace menu, and new-note dialog with existing behavior preserved.

On 2026-10-05 the owner selected **“Apply a stock shadcn neutral dark theme to the dashboard”**, explicitly authorizing a dashboard-only exception to DESIGN.md. Other routes retain KWG styling. Keep dark mode permanently enabled; no theme switcher.

## Options considered

1. **shadcn with KWG styling:** least disruption, but retains pills and regular-weight constraints rather than a stock appearance.
2. **Stock neutral dark (selected):** consistent semantic colors, rounded rectangular controls, standard component weights and overlay elevation. Requires removing conflicting host and dashboard styles.
3. **Configuration/token cleanup only:** smallest change, but leaves the visible mismatch unresolved.

## Selected direction

- Preserve desktop rail, centered content, page order, Personal/Parallel switcher, mobile Pages disclosure, six note sections, overview layouts, note list/editor, and Settings folder controls.
- Use the official neutral dark palette with existing New York-style Radix components. Keep the custom Base UI workspace menu and its API, adapting its presentation to the same theme. This is not a component-library upgrade.
- Use system sans, body weight 400, button labels 500, headings 600, sentence-case form labels, and existing compact heading sizes. Remove marketing tracking and forced mono-uppercase labels. No remote fonts or assets.
- Use component radius tokens instead of universal pills, existing button variants, readable selected rows, and neutral surfaces. Keep 44-pixel touch targets. Error color must accompany text; graph distinctions retain non-color cues.
- Preserve visible focus, reduced motion, WCAG 2.2 AA, long-content handling, and readable loading/empty/error states.

## Behavior and boundary

Preserve first-run/no-folder, loading, connected, empty results, selected note, dirty draft, saving, saved, permission denied/revoked, reconnect, conflict, write failure, unsupported browser, and modal validation states. Keep labels, IDs, URL parameters, and handlers unless presentation requires a structural wrapper.

Personal and Parallel remain isolated. Notes remain local; no uploads, telemetry, database storage, automatic permission prompts, or remote migration. Explicit saves, original-version conflict checks, write locking, and local `.history` backups stay unchanged. Keep CSP, no-store headers, unsupported-browser explanation, and noscript content.

Verify 320, 375, 768, 1024, 1440, and 2560 pixel widths, 200% zoom, keyboard operation, reduced motion, and long filenames. Save/navigation controls remain reachable.

## Evidence and implementation implications

- `dashboard/` is a React 19 / Vite 7 / Tailwind 4 package built into `public/dashboard-assets/` and hosted by Astro.
- Eight UI component files already exist. `shadcn info --json` detects Vite/TypeScript/Tailwind v4 but returns null configuration and an empty inventory because `components.json` is absent.
- Most primitives use Radix; the workspace menu uses Base UI. The unconfigured CLI defaults to Base UI documentation, which is not evidence that existing components should migrate.
- The Astro route imports the entire marketing SCSS entry point. Dashboard CSS forces pills, weight 400, no shadows, and KWG aliases.
- Legacy `--muted` is text and `--accent` is action/link foreground; shadcn uses both for backgrounds. Rename legacy consumers before introducing official semantics.
- Existing uncommitted responsive and draft/permission changes must be preserved.

The official `.agents/skills/shadcn/SKILL.md` is installed using the requested skills CLI; `skills-lock.json` records it. The skill, brainstorming, Impeccable planning guidance, and Context7 library `/shadcn-ui/ui` informed this brief.

References: [skills](https://ui.shadcn.com/docs/skills), [theming](https://ui.shadcn.com/docs/theming), [configuration](https://ui.shadcn.com/docs/components-json).

The official skill and dashboard configuration are installed. The approved theme is implemented, including semantic colors, route isolation, component radii, weights, and portaled overlays. Production build, seven unit tests, and extended browser checks pass. Existing local-file behavior is preserved. Native Windows folder-picker/save smoke verification remains manual; deployment was not requested.
