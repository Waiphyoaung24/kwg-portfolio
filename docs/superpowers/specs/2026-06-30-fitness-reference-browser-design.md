# Fitness Exercise Reference Browser — Design

**Date:** 2026-06-30
**Status:** Approved
**Page:** `src/pages/vault/fitness.astro` (behind existing vault gate + `noindex`)

## Goal

Turn the empty `/vault/fitness` placeholder into a searchable, filterable
reference browser for the [exercises-dataset](https://github.com/hasaneyldrm/exercises-dataset)
(1,324 exercises with instructions, target muscles, equipment, image + animated GIF).

Read-only reference. No logging, no routines, no persistence.

## Decisions

| Question | Decision | Why |
|---|---|---|
| Tool type | Reference browser (read-only) | Simplest thing that's actually useful |
| Media hosting | Hotlink via jsDelivr CDN | 0 MB added to repo, no build cost |
| jsDelivr ref | Pinned commit `92e2704` | Media can't change under us; deletion risk accepted |
| Data | Trimmed English-only JSON committed to repo | 6.5 MB → ~1 MB; dataset repo is not a dependency |
| Detail view | Native `<dialog>` modal | Keyboard/escape/focus handling for free; no per-exercise routes |
| Filters | search + body part + equipment + target muscle | Covers the real lookup paths |

## Architecture

All client-side. One page, one committed data file, one build-time script.

```
src/scripts/build-fitness-data.mjs   (run once, output committed)
        │ reads (from a local clone of the dataset)
        ▼
src/data/fitness-exercises.json      (~1 MB, committed)
        │ imported at build time
        ▼
src/pages/vault/fitness.astro        (gate + filter UI + grid + <dialog>)
        │ media URLs prefixed at render
        ▼
cdn.jsdelivr.net/gh/hasaneyldrm/exercises-dataset@92e2704/images|videos/...
```

### Data pipeline — `src/scripts/build-fitness-data.mjs`

- Reads `exercises.json` from a local clone of the dataset (path passed as arg).
- For each record, keep:
  `{ id, name, category, body_part, equipment, target, secondary_muscles, muscle_group, image, gif_url, steps }`
  where `steps = instruction_steps.en`.
- Drop: `instructions` (redundant full strings), all non-English language data, `created_at`.
- Write `src/data/fitness-exercises.json`.
- **Self-check (assert-based):** output length is within a few of 1,324, and every
  record has a non-empty `name` and `image`. Throw if not.
- The dataset repo is NOT added to `package.json`. The script is a one-time
  generator; only its committed output ships.

### Page — `src/pages/vault/fitness.astro`

Keep existing: vault `localStorage` gate, `noindex`, fonts, `index.scss` import,
`.page` / `.page__back` / `.page__title` styling.

- **Build time:** `import exercises from '../../data/fitness-exercises.json'`.
  Derive distinct filter option lists (body parts, equipment, targets) from the data.
- **Render:** filter bar + results grid of cards.
- **Client script (`is:inline` or a small island):**
  - Filter state: text query + 3 selects. Filtering runs client-side over the
    full array. Case-insensitive substring match on `name`; exact match on selects.
  - Card click → open `<dialog>` populated with that exercise's GIF (lazy
    `loading="lazy"`, src set on open so the 125 MB of GIFs never load for the grid),
    numbered `steps`, and metadata (target, secondary muscles, equipment, body part).
  - `<dialog>` closes on Escape / backdrop / close button (native).
- **Media URL helper:** `CDN = "https://cdn.jsdelivr.net/gh/hasaneyldrm/exercises-dataset@92e2704"`;
  image src = `${CDN}/${exercise.image}`, gif src = `${CDN}/${exercise.gif_url}`.

### Grid performance

Grid shows **static JPG thumbnails only** (`loading="lazy"`). GIFs load only when a
detail dialog opens. 1,324 cards render fine as a plain CSS grid; if it ever feels
heavy, cap visible results to the current filter (filters narrow it in practice).
No virtualization unless measured to be needed.

## Styling

Reuse existing SCSS tokens already in the page (`--c-accent`, `--c-on-surface-muted`,
`clamp-fluid`, `to-rem`, `--grid-max-width`, `--grid-margin`, `--ease-smooth`).
Lamborghini-dark / brutalist direction per `DESIGN.md`. No new dependencies.

## Out of scope (YAGNI)

Workout logging, routine building, set/rep history, multi-language, per-exercise
routes, backend, search ranking, virtualization. Each is a separate spec if wanted.

## Risks

- **Dataset repo deletion** → media 404s. Accepted. Mitigation if it matters later:
  switch the CDN prefix to committed `public/` images (11 MB stills).
- **jsDelivr availability** → standard CDN risk, acceptable for a personal gated page.
