# Workout Presets — Design

**Date:** 2026-06-30
**Status:** Approved (design), pending implementation plan
**Surface:** `/vault/fitness/generate` (adds preset buttons to the existing generator page)

## Goal

Add three named, fixed workout routines (the user's actual training splits) as
one-click presets on the generator page. Clicking a preset renders its
exercises, in a fixed author-defined order, into the existing result grid —
distinct from the random generator already on the page.

## Scope

In scope:
- A `workout-presets.ts` module holding the three routines as ordered id lists.
- A test asserting every preset id resolves in the dataset.
- A `MY ROUTINES` button row on the generator page.
- Clicking a preset renders its exercises (no shuffle) into the existing grid.
- Extract a shared `showExercises()` render helper so the random generator and
  the presets share one render path (no duplication).

Out of scope (YAGNI / per user decision):
- Set counts / reps / rest (the routines list "3 set" etc.; deliberately not shown).
- Persistence (no localStorage).
- Editing presets in the UI — they live in the module; edit the file to change a routine.
- Adding presets to the `/vault/fitness` browser page (generator page only).

## Preset data (source of truth)

Each preset is `{ name: string; ids: string[] }`. Ids are dataset record ids;
order is the display order. Verified against `src/data/fitness-exercises.json`.

**Upper Body A** (6)
| id | exercise | requested as |
|----|----------|--------------|
| 1350 | lever seated row | Machine back row |
| 0577 | lever chest press | Chest press |
| 0579 | lever front pulldown | Lat pulldown |
| 0603 | lever shoulder press | Shoulder press |
| 0602 | lever seated reverse fly | Rear delt fly |
| 0584 | lever lateral raise | Lateral raise |

**Lower Body A** (5)
| id | exercise | requested as |
|----|----------|--------------|
| 2138 | stationary bike run v. 3 | Cycling (10 mins) |
| 2287 | lever alternate leg press | Leg Press |
| 0585 | lever leg extension | Leg Extension |
| 0599 | lever seated leg curl | Leg Curl |
| 0739 | sled 45° leg press | Plate Loaded |

**Upper Body B** (8)
| id | exercise | requested as |
|----|----------|--------------|
| 0314 | dumbbell incline bench press | Incline bench press |
| 1350 | lever seated row | Row |
| 0579 | lever front pulldown | Lat Pull Down |
| 0603 | lever shoulder press | Shoulder Press |
| 0577 | lever chest press | Chest Press |
| 0596 | lever seated fly | Deltoid Fly (pec deck) |
| 0584 | lever lateral raise | Lateral Raise |
| 0607 | lever triceps extension | Triceps Press |

## Architecture

**`src/scripts/workout-presets.ts`** — exports
`export const PRESETS: { name: string; ids: string[] }[]` in display order
(Upper Body A, Lower Body A, Upper Body B). Pure data, no logic.

**`src/scripts/workout-presets.test.mjs`** — imports `PRESETS` and the dataset,
asserts: at least 3 presets; every preset has a non-empty `name` and `ids`;
every id resolves to a record in `fitness-exercises.json`. This is the runnable
check that fails if a pinned id is mistyped or removed from the data.

**`src/pages/vault/fitness/generate.astro`** — additive change plus one refactor:
- Add a `MY ROUTINES` row of buttons above the generator `<form>`, one button
  per preset (label = preset name), styled with the existing `.gen__btn`.
- Build a `byId` lookup in the page script: `Object.fromEntries(exercises.map(e => [e.id, e]))`.
- Extract the card-rendering tail of the existing `render()` into
  `showExercises(list, captionText)`: `grid.replaceChildren(...list.map(cardEl))`
  then set the caption. The random `render()` calls it with
  `(picks, "N exercises · label")`; preset clicks call it with the resolved
  ordered list and `"<name> · N exercises"`.
- Preset click resolves `ids.map(id => byId[id]).filter(Boolean)` (defensive: a
  missing id is skipped, not crash) and calls `showExercises`, then hides the
  `Reroll` button (reroll is meaningless for a fixed list).

## Data flow

Preset button click → look up `PRESETS[i]` → resolve ordered ids via `byId` →
`showExercises(list, caption)` → cards render into `#grid` → existing
`initDetail` delegate opens the shared dialog on card click (unchanged).

## Error handling

- A preset id absent from the dataset is filtered out at render time, so the
  routine still renders its remaining exercises rather than crashing. The test
  prevents this from shipping in the first place.

## Styling

- Preset buttons reuse `.gen__btn` (touch target, focus-visible ring already
  defined). The `MY ROUTINES` row reuses the `.gen` flex row pattern / label
  styling from the controls. No new tokens.

## Verification

- `npm run test:picker` style: `node src/scripts/workout-presets.test.mjs` →
  prints an `ok:` line; fails loudly if any id is bad.
- `npm run build` → 0 errors.
- Manual: open `/vault/fitness/generate`, click each preset → correct exercises
  in the listed order; caption shows the routine name + count; clicking a card
  opens the dialog; Reroll hides under a preset and the random Generate path
  still works.
</content>
