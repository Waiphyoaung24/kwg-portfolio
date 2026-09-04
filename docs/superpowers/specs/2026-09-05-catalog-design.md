# Catalog — design

Date: 2026-09-05. Status: approved in chat.

## Goal

A "Catalog" nav item and page where components, page sections and pages
can be viewed live and their source copied. First entry: the Codrops
shape-aware ASCII renderer (MIT, Edoardo Lunardi).

## Style

Nothing design system (github.com/dominikmartn/nothing-design-skill), dark
mode. Monochrome, Space Grotesk body, Space Mono labels (ALL CAPS), Doto
for the one hero moment. No shadows, gradients, cards or bounce easing.
Three-layer hierarchy per screen.

## Structure

- `Header.astro`: add `Catalog` link → `/catalog`.
- `src/catalog/entries.ts`: array of `{ slug, title, kind, description,
  stack, credit: { name, url }, source }`. `kind` ∈ Component | Section | Page.
- `src/catalog/<slug>/`: vendored source files, verbatim.
- `src/pages/catalog/index.astro`: Doto headline + count, then one divider
  row per entry (index, title, kind, stack).
- `src/components/CatalogEntry.astro`: shared shell. Slot = live demo in a
  viewport-height stage. Below: meta row, then every source file under
  `src/catalog/<slug>/` (read at build via `import.meta.glob(..., {
  query: '?raw' })`) as path label, byte count, `<pre>`, Copy button that
  flips to `[COPIED]` inline.
- `src/pages/catalog/ascii-logo.astro`: uses the shell, mounts
  `<ascii-logo>`.

## Dependencies

three 0.149 → 0.185 (nothing in `src/` imports the old one). Space Mono
and Doto added to the existing Google Fonts link.

## Out of scope

Syntax highlighting, search/filter, light mode toggle, KWG-specific mark.

## Page-kind entries (added same day)

A whole page cannot be inlined into the shell, so it gets three files:

- `src/catalog/<slug>/index.html`: the page, verbatim, asset paths absolute.
- `src/pages/catalog/<slug>/live.ts`: endpoint that serves that file as HTML.
- `src/pages/catalog/<slug>.astro`: shell with an iframe of `/catalog/<slug>/live`.

First one: Kage, moved from `/page-2`. The Page 2 nav link is gone.
