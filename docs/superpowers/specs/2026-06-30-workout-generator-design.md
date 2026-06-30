# Workout Generator — Design

**Date:** 2026-06-30
**Status:** Approved (design), pending implementation plan
**Surface:** `/vault/fitness/generate`

## Goal

Add a workout generator to the fitness vault. Given equipment and a count, it
assembles a set of exercises from the existing 1324-record dataset — either a
full-body spread (one pick per body part) or a focused set (all hitting one
target muscle). Pure client-side filtering/sampling over data already shipped.
No new dependencies, no persistence.

## Scope

In scope:
- New page at `/vault/fitness/generate`.
- Mode toggle: **Full body** vs **Focus**.
- Equipment + count inputs; target input (Focus mode only).
- Generate + Reroll.
- Results reuse the existing exercise card + detail dialog.
- Extract the shared detail dialog so both pages use one copy.

Out of scope (YAGNI for now):
- Copy-to-clipboard / export.
- Saving or naming workouts (no persistence).
- Set/rep/weight logging.
- Re-targeting individual slots.

## Entry & routing

- New file `src/pages/vault/fitness/generate.astro` → serves `/vault/fitness/generate`.
- `src/pages/vault/fitness.astro` is unchanged as a route — Astro still serves it
  at `/vault/fitness` alongside the new nested route.
- Add one link in the fitness page header (near `.page__title`):
  `↗ generate workout` → `/vault/fitness/generate`.
- The generate page repeats the same obscurity gate `<script is:inline>` that
  bounces to `/vault` unless `kwg_vault === '1'`.

## Controls

Rendered above the result grid, reusing `.filters` row styling:

| Control | Source | Notes |
|---|---|---|
| Mode | radios `Full body` / `Focus` | `Full body` default |
| Equipment | `<select>` from `uniq('equipment')` | first option "Any equipment" (`value=""`) |
| Target | `<select>` from `uniq('target')` | shown/enabled only in Focus mode |
| Count | `<select>` `3..10` | default `6` |
| Generate | button | runs selection |
| Reroll | button | re-runs with current settings; hidden until first generate |

Switching to Full body hides/disables the Target select. Switching to Focus
reveals it.

## Selection logic

Plain client JS over the imported `exercises` array. No server work.

1. **Pool** = `exercises`, filtered by chosen equipment (skip filter if "Any").
2. **Full body:** group pool by `body_part`; shuffle group order; take one
   random exercise from each distinct part in turn until `count` is reached. If
   distinct parts < count, loop the parts again but never repeat an exercise
   already picked.
3. **Focus:** filter pool to chosen `target`; shuffle; take first `count`.
4. **Shortfall:** if the pool yields fewer than `count`, render all that matched
   and show a caption (e.g. `only 4 matched`). Never pad, never invent.
5. Shuffle = Fisher–Yates using `Math.random` (acceptable in page JS).

## Rendering

- Results render into a `.grid` of `.card` items built in JS from the picked
  subset — identical markup to `fitness.astro` cards (`data-id`, image, name,
  equipment tag).
- A caption (`role="status" aria-live="polite"`) reports the result, e.g.
  `6 exercises · full body` or `only 4 matched`.
- Clicking a card opens the shared detail dialog (steps, secondary muscles,
  play/pause GIF) — same behavior as the browser page.

## Shared detail dialog (the refactor)

Both pages need the identical `<dialog id="detail">` markup plus the
open/render/play-pause logic (~45 lines). Extract once to avoid drift:

- **`src/components/ExerciseDetail.astro`** — the `<dialog>` markup currently
  inlined in `fitness.astro` (lines 76–86), unchanged.
- **`src/scripts/exercise-detail.{ts,js}`** — exports `initDetail(exercises, CDN)`
  wiring the dialog: byId lookup, card-click delegation on a passed grid element,
  poster/GIF toggle, reduced-motion honoring, close handlers. Mirrors current
  `fitness.astro` script lines 117–156.

Both `fitness.astro` and `generate.astro`:
- render `<ExerciseDetail />`,
- call `initDetail(exercises, CDN)` against their own grid.

`fitness.astro` keeps its own filter/search JS; only the dialog block moves out.
Behavior must be identical after extraction (verified by manually opening a card
on `/vault/fitness` and confirming steps/GIF/close still work).

## Styling

- Controls row borrows `.filters` / `.filters__select` styles (same tokens).
- Result grid and cards reuse existing `.grid` / `.card` SCSS — no new card CSS.
- Only genuinely new CSS: the mode radios and the generate/reroll buttons
  (can reuse `.detail__toggle` button styling as a base).
- All values via existing tokens (`to-rem`, `clamp-fluid`, `var(--c-*)`).

## Accessibility

- Radios in a `<fieldset>` with a `<legend>` ("Workout mode").
- Generate/Reroll are real `<button type="button">`; min 44px touch target.
- Result caption is `aria-live="polite"`.
- Target select gets `hidden` (not just visually hidden) when in Full body mode
  so it's out of the tab order.

## Verification

- Full body, Dumbbell, 6 → 6 cards spanning distinct body parts.
- Focus, Chest, Dumbbell, 5 → 5 cards all with `target === 'chest'`.
- Reroll → different set, same constraints.
- Equipment with < count matches → shortfall caption, no crash.
- `/vault/fitness` detail dialog still works after the extraction.
- Both pages still bounce to `/vault` when not unlocked.
</content>
</invoke>
