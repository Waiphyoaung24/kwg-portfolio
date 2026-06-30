# Workout Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/vault/fitness/generate` page that assembles a random workout (full-body spread or single-muscle focus) from the existing 1324-exercise dataset, client-side only.

**Architecture:** Extract the existing exercise detail `<dialog>` into a shared Astro component + TS module so both the browser and generator pages use one copy. Add a pure `pickWorkout()` selection function (unit-tested with `node:assert`). Build the generator page that wires controls → `pickWorkout()` → JS-rendered cards → shared dialog.

**Tech Stack:** Astro, TypeScript, scoped SCSS (helpers auto-injected via `vite.css.preprocessorOptions.scss.additionalData`), Node 26 (strips TS types natively — `.test.mjs` can import `.ts` directly).

## Global Constraints

- All pages under `/vault` repeat the obscurity gate `<script is:inline>` that runs `if (localStorage.getItem('kwg_vault') !== '1') location.replace('/vault');` in `<head>` before render.
- CDN base is `https://cdn.jsdelivr.net/gh/hasaneyldrm/exercises-dataset@92e2704` — single source, exported from `src/scripts/exercise-detail.ts` as `CDN`.
- Exercise images use `loading="lazy"`, `width`/`height` set, empty `alt=""` (decorative; name is in adjacent text).
- Touch targets ≥ 44px; `:focus-visible` outlines use `2px solid var(--c-accent)` offset `2px` — match existing patterns.
- SCSS uses tokens only: `to-rem()`, `clamp-fluid()`, `var(--c-*)`, `var(--fs-*)`, `var(--ease-smooth)`.
- `data-*` card attributes drive behavior; the shared dialog reads `card.dataset.id`.
- Verification baseline: `npm run build` (runs `astro check && astro build`) must pass with zero errors.

---

### Task 1: Extract the shared exercise detail dialog

Move the `<dialog>` markup + its JS out of `fitness.astro` into a reusable component and module, then re-wire `fitness.astro` to use them. Behavior must be byte-for-byte identical after this task. This is a pure refactor (no behavior change), so it is verified by `astro check` + a manual browser check rather than a unit test (the logic is DOM wiring, which the project does not unit-test).

**Files:**
- Create: `src/components/ExerciseDetail.astro`
- Create: `src/scripts/exercise-detail.ts`
- Modify: `src/pages/vault/fitness.astro` (remove inlined dialog markup at lines 76–86, the CDN const at line 5, and the detail-dialog JS at lines 117–156; import the new component + module instead)

**Interfaces:**
- Produces: `src/components/ExerciseDetail.astro` — renders `<dialog id="detail" class="detail">` with its scoped styles.
- Produces: `export const CDN: string` and `export function initDetail(grid: HTMLElement, exercises: Exercise[]): void` from `src/scripts/exercise-detail.ts`. `initDetail` attaches a click delegate to `grid`, opens `#detail`, renders name/meta/secondary/steps, and toggles poster↔GIF honoring reduced-motion.
- Produces: `export type Exercise` (the trimmed record shape) from the same module.

- [ ] **Step 1: Create the shared module `src/scripts/exercise-detail.ts`**

```ts
export type Exercise = {
  id: string;
  name: string;
  body_part: string;
  equipment: string;
  target: string;
  secondary_muscles: string[];
  image: string;
  gif_url: string;
  steps: string[];
};

export const CDN = 'https://cdn.jsdelivr.net/gh/hasaneyldrm/exercises-dataset@92e2704';

// Wire the shared <dialog id="detail"> to a grid of .card elements.
export function initDetail(grid: HTMLElement, exercises: Exercise[]) {
  const byId = Object.fromEntries(exercises.map((e) => [e.id, e]));
  const dlg = document.getElementById('detail') as HTMLDialogElement;
  const gif = dlg.querySelector('.detail__gif') as HTMLImageElement;
  const name = dlg.querySelector('.detail__name')!;
  const meta = dlg.querySelector('.detail__meta')!;
  const secondary = dlg.querySelector('.detail__secondary')!;
  const steps = dlg.querySelector('.detail__steps')!;
  const toggle = dlg.querySelector('.detail__toggle')!;

  let posterSrc = '';
  let gifSrc = '';
  function renderMedia(playing: boolean) {
    gif.src = playing ? gifSrc : posterSrc; // GIF only requested when playing
    toggle.textContent = playing ? 'Pause' : 'Play';
    toggle.setAttribute('aria-pressed', String(playing));
  }
  toggle.addEventListener('click', () =>
    renderMedia(toggle.getAttribute('aria-pressed') !== 'true'),
  );

  grid.addEventListener('click', (ev) => {
    const card = (ev.target as HTMLElement).closest('.card') as HTMLElement | null;
    if (!card) return;
    const e = byId[card.dataset.id!];
    name.textContent = e.name;
    meta.textContent = [e.target, e.equipment, e.body_part].filter(Boolean).join(' · ');
    secondary.textContent = e.secondary_muscles?.length
      ? 'Also targets: ' + e.secondary_muscles.join(', ')
      : '';
    steps.replaceChildren();
    for (const s of e.steps || []) {
      const li = document.createElement('li');
      li.textContent = s;
      steps.appendChild(li);
    }
    posterSrc = `${CDN}/${e.image}`;
    gifSrc = `${CDN}/${e.gif_url}`;
    gif.alt = e.name;
    // Honor reduced-motion: start on the static poster; otherwise autoplay the GIF.
    renderMedia(!window.matchMedia('(prefers-reduced-motion: reduce)').matches);
    dlg.showModal();
  });

  dlg.querySelector('.detail__close')!.addEventListener('click', () => dlg.close());
  dlg.addEventListener('click', (ev) => {
    if (ev.target === dlg) dlg.close();
  });
  dlg.addEventListener('close', () => {
    gif.removeAttribute('src');
  });
}
```

- [ ] **Step 2: Create `src/components/ExerciseDetail.astro`** (dialog markup + the `.detail*` styles moved verbatim out of `fitness.astro`)

```astro
---
---
<dialog id="detail" class="detail" aria-labelledby="detail-name">
  <button class="detail__close" type="button" aria-label="Close">✕</button>
  <div class="detail__media">
    <img class="detail__gif" alt="" width="360" height="360" />
    <button class="detail__toggle" type="button" aria-pressed="false">Play</button>
  </div>
  <h2 id="detail-name" class="detail__name"></h2>
  <p class="detail__meta"></p>
  <p class="detail__secondary"></p>
  <ol class="detail__steps"></ol>
</dialog>

<style lang="scss">
  .detail {
    width: 100%;
    max-width: min(92vw, to-rem(480));
    max-height: 90svh;
    overflow-y: auto;
    margin: auto; // center within the viewport
    color: var(--c-light);
    background: var(--c-surface-1);
    border: 1px solid var(--c-on-surface-muted);
    padding: clamp-fluid(16, 28);

    &::backdrop { background: rgb(0 0 0 / 0.7); }
  }
  .detail__close {
    position: absolute;
    top: to-rem(4);
    right: to-rem(4);
    z-index: 1;
    display: grid;
    place-items: center;
    min-width: to-rem(44);
    min-height: to-rem(44); // touch target
    font-size: var(--fs-6);
    color: var(--c-on-surface-muted);
    background: var(--c-surface-1);
    border: 0;
    cursor: pointer;

    &:hover { color: var(--c-accent); }
    &:focus-visible { outline: 2px solid var(--c-accent); outline-offset: 2px; }
  }
  .detail__media { position: relative; }
  .detail__gif {
    width: 100%;
    height: auto;
    aspect-ratio: 1;
    object-fit: contain;
    background: #111;
  }
  .detail__toggle {
    position: absolute;
    right: to-rem(8);
    bottom: to-rem(8);
    min-height: to-rem(44); // touch target
    padding: to-rem(6) to-rem(14);
    font-size: var(--fs-label);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--c-light);
    background: var(--c-dark);
    border: 1px solid var(--c-on-surface-muted);
    cursor: pointer;
    transition: color 0.2s var(--ease-smooth), border-color 0.2s var(--ease-smooth);

    &:hover { color: var(--c-accent); border-color: var(--c-accent); }
    &:focus-visible { outline: 2px solid var(--c-accent); outline-offset: 2px; }
  }
  .detail__name { margin: to-rem(12) 0 to-rem(4); text-transform: capitalize; }
  .detail__meta {
    margin: 0 0 to-rem(12);
    font-size: var(--fs-label);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--c-on-surface-muted);
  }
  .detail__secondary { margin: 0 0 to-rem(12); font-size: var(--fs-label); color: var(--c-on-surface-muted); text-transform: capitalize; }
  .detail__steps { margin: 0; padding-left: 1.2em; display: grid; gap: to-rem(6); }
</style>
```

- [ ] **Step 3: Re-wire `src/pages/vault/fitness.astro`**

In the frontmatter (`---` block), replace the local `CDN` const (line 5) with imports:

```astro
---
import '../../styles/index.scss';
import exercises from '../../data/fitness-exercises.json';
import ExerciseDetail from '../../components/ExerciseDetail.astro';
import { CDN } from '../../scripts/exercise-detail';

type ExKey = keyof (typeof exercises)[0];
const uniq = (k: ExKey) => [...new Set(exercises.map((e) => e[k]).filter(Boolean))].sort();
const bodyParts = uniq('body_part');
const equipments = uniq('equipment');
const targets = uniq('target');
---
```

Replace the inlined `<dialog>...</dialog>` block (lines 76–86) with:

```astro
      <ExerciseDetail />
```

Replace the entire `<script is:inline define:vars={{ exercises, CDN }}> ... </script>` block (lines 89–157) with a bundled module that keeps the filter/search logic and delegates the dialog to `initDetail`:

```astro
    <script>
      import { initDetail } from '../../scripts/exercise-detail';
      import exercises from '../../data/fitness-exercises.json';

      const grid = document.getElementById('grid')!;
      const cards = [...grid.children] as HTMLElement[];
      const q = document.getElementById('q') as HTMLInputElement;
      const fBody = document.getElementById('f-body') as HTMLSelectElement;
      const fEquip = document.getElementById('f-equip') as HTMLSelectElement;
      const fTarget = document.getElementById('f-target') as HTMLSelectElement;
      const count = document.getElementById('count')!;

      function apply() {
        const term = q.value.trim().toLowerCase();
        const b = fBody.value, eq = fEquip.value, t = fTarget.value;
        let n = 0;
        for (const card of cards) {
          const ok =
            (!term || card.dataset.name!.includes(term)) &&
            (!b || card.dataset.body === b) &&
            (!eq || card.dataset.equip === eq) &&
            (!t || card.dataset.target === t);
          card.hidden = !ok;
          if (ok) n++;
        }
        count.textContent = `${n} exercise${n === 1 ? '' : 's'}`;
      }
      [q, fBody, fEquip, fTarget].forEach((el) => el.addEventListener('input', apply));
      apply();

      initDetail(grid, exercises);
    </script>
```

Then delete the `.detail*` style rules (lines 269–335 of the original) from `fitness.astro`'s `<style>` block — they now live in `ExerciseDetail.astro`. Leave all other styles (`.page`, `.filters`, `.grid`, `.card`) untouched.

- [ ] **Step 4: Run the build to typecheck the refactor**

Run: `npm run build`
Expected: PASS — `astro check` reports 0 errors, build completes. (If `astro check` flags the non-null assertions, they are valid since the elements exist in the markup.)

- [ ] **Step 5: Manual behavior check**

Run: `npm run dev`, open `http://localhost:4321/vault` and unlock, then go to `/vault/fitness`. Click any card. Confirm: dialog opens, shows name/meta/secondary/steps, GIF autoplays (or shows poster under reduced-motion), Play/Pause toggles, ✕ and backdrop-click close it. Behavior must match pre-refactor exactly.

- [ ] **Step 6: Commit**

```bash
git add src/components/ExerciseDetail.astro src/scripts/exercise-detail.ts src/pages/vault/fitness.astro
git commit -m "♻️ extract shared exercise detail dialog into component + module"
```

---

### Task 2: Pure workout selection logic + test

**Files:**
- Create: `src/scripts/workout-picker.ts`
- Test: `src/scripts/workout-picker.test.mjs`

**Interfaces:**
- Consumes: `Exercise` type from `src/scripts/exercise-detail.ts`.
- Produces: `export function pickWorkout(exercises: Exercise[], opts: PickOpts): Exercise[]` and `export type PickMode = 'full' | 'focus'`, `export interface PickOpts { mode: PickMode; equipment?: string; target?: string; count: number; rng?: () => number }`. Returns up to `count` exercises; deterministic given a fixed `rng`.

- [ ] **Step 1: Write the failing test `src/scripts/workout-picker.test.mjs`**

```js
import assert from 'node:assert/strict';
import { pickWorkout } from './workout-picker.ts';

// Deterministic PRNG (mulberry32) so picks are reproducible across runs.
function rng32(seed) {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const ex = (id, body_part, equipment, target) => ({
  id,
  name: 'ex' + id,
  body_part,
  equipment,
  target,
  secondary_muscles: [],
  image: '',
  gif_url: '',
  steps: [],
});

const data = [
  ex('1', 'chest', 'dumbbell', 'pectorals'),
  ex('2', 'chest', 'dumbbell', 'pectorals'),
  ex('3', 'back', 'dumbbell', 'lats'),
  ex('4', 'legs', 'dumbbell', 'quads'),
  ex('5', 'legs', 'barbell', 'quads'),
  ex('6', 'waist', 'dumbbell', 'abs'),
];

// focus: filters to target, respects count, never exceeds available
const focus = pickWorkout(data, { mode: 'focus', target: 'quads', count: 5, rng: rng32(1) });
assert.equal(focus.length, 2, 'only 2 quads exercises exist');
assert.ok(focus.every((e) => e.target === 'quads'), 'all focus picks match target');

// focus + equipment narrows the pool
const focusEq = pickWorkout(data, {
  mode: 'focus', target: 'quads', equipment: 'dumbbell', count: 5, rng: rng32(1),
});
assert.equal(focusEq.length, 1, 'only 1 dumbbell quads exercise');

// full body: spans distinct body parts, no dupes, respects count
const full = pickWorkout(data, { mode: 'full', count: 4, rng: rng32(2) });
assert.equal(full.length, 4, 'returns count');
assert.equal(new Set(full.map((e) => e.body_part)).size, 4, 'four distinct body parts');
assert.equal(new Set(full.map((e) => e.id)).size, 4, 'no repeated exercise');

// full body wraps when count > distinct parts, still no repeats, caps at pool size
const wrap = pickWorkout(data, { mode: 'full', equipment: 'dumbbell', count: 10, rng: rng32(3) });
assert.equal(wrap.length, 5, 'capped at the 5 available dumbbell exercises');
assert.equal(new Set(wrap.map((e) => e.id)).size, 5, 'no repeats when wrapping parts');

console.log('ok: pickWorkout focus + full-body behavior');
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node src/scripts/workout-picker.test.mjs`
Expected: FAIL — `Cannot find module './workout-picker.ts'` (or `pickWorkout is not a function`).

- [ ] **Step 3: Write `src/scripts/workout-picker.ts`**

```ts
import type { Exercise } from './exercise-detail';

export type PickMode = 'full' | 'focus';

export interface PickOpts {
  mode: PickMode;
  equipment?: string;
  target?: string;
  count: number;
  rng?: () => number;
}

function shuffle<T>(arr: T[], rng: () => number): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// Pick up to `count` exercises. Pure: same inputs + rng => same output.
export function pickWorkout(exercises: Exercise[], opts: PickOpts): Exercise[] {
  const { mode, equipment = '', target = '', count, rng = Math.random } = opts;
  const pool = equipment ? exercises.filter((e) => e.equipment === equipment) : exercises;

  if (mode === 'focus') {
    const filtered = target ? pool.filter((e) => e.target === target) : pool;
    return shuffle(filtered, rng).slice(0, count);
  }

  // full body: group by body part, then round-robin one random pick per part
  // until count is reached. Wraps through parts again but never repeats an exercise.
  const groups = new Map<string, Exercise[]>();
  for (const e of shuffle(pool, rng)) {
    const g = groups.get(e.body_part);
    if (g) g.push(e);
    else groups.set(e.body_part, [e]);
  }
  const parts = shuffle([...groups.keys()], rng);
  const picked: Exercise[] = [];
  let added = true;
  while (picked.length < count && added) {
    added = false;
    for (const p of parts) {
      if (picked.length >= count) break;
      const next = groups.get(p)!.shift();
      if (next) {
        picked.push(next);
        added = true;
      }
    }
  }
  return picked;
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `node src/scripts/workout-picker.test.mjs`
Expected: PASS — prints `ok: pickWorkout focus + full-body behavior`.

- [ ] **Step 5: Commit**

```bash
git add src/scripts/workout-picker.ts src/scripts/workout-picker.test.mjs
git commit -m "✨ add pure workout selection logic + test"
```

---

### Task 3: Generator page + header link

**Files:**
- Create: `src/pages/vault/fitness/generate.astro`
- Modify: `src/pages/vault/fitness.astro` (add one header link to the generator)

**Interfaces:**
- Consumes: `pickWorkout` from `src/scripts/workout-picker.ts`; `initDetail`, `CDN`, `Exercise` from `src/scripts/exercise-detail.ts`; `ExerciseDetail.astro` component; `fitness-exercises.json`.
- Produces: route `/vault/fitness/generate`.

Note on styling: Astro scopes `<style>` per page, so this page carries its own copy of `.grid`/`.card` rules (≈35 lines, duplicated from `fitness.astro`) plus its own controls styles. This keeps the working fitness page untouched. Acceptable duplication; globalize later only if a third consumer appears.

- [ ] **Step 1: Create `src/pages/vault/fitness/generate.astro`**

```astro
---
import '../../../styles/index.scss';
import exercises from '../../../data/fitness-exercises.json';
import ExerciseDetail from '../../../components/ExerciseDetail.astro';

type ExKey = keyof (typeof exercises)[0];
const uniq = (k: ExKey) => [...new Set(exercises.map((e) => e[k]).filter(Boolean))].sort();
const equipments = uniq('equipment');
const targets = uniq('target');
const counts = [3, 4, 5, 6, 7, 8, 9, 10];
---

<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="theme-color" content="#000000" />
    <meta name="robots" content="noindex" />
    <title>Generate Workout — Fitness — KWG</title>
    <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      rel="stylesheet"
      href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300..700&display=swap"
    />
    <!-- Obscurity gate: bounce to /vault unless already unlocked. -->
    <script is:inline>
      if (localStorage.getItem('kwg_vault') !== '1') location.replace('/vault');
    </script>
  </head>

  <body>
    <main class="page">
      <a class="page__back" href="/vault/fitness">← Fitness</a>
      <h1 class="page__title">Generate</h1>

      <form class="gen" id="gen">
        <fieldset class="gen__modes">
          <legend>Workout mode</legend>
          <label class="gen__mode"><input type="radio" name="mode" value="full" checked /> Full body</label>
          <label class="gen__mode"><input type="radio" name="mode" value="focus" /> Focus</label>
        </fieldset>
        <select id="g-equip" class="gen__select" aria-label="Equipment">
          <option value="">Any equipment</option>
          {equipments.map((v) => <option value={v}>{v}</option>)}
        </select>
        <select id="g-target" class="gen__select" aria-label="Target muscle" hidden>
          <option value="">Any target</option>
          {targets.map((v) => <option value={v}>{v}</option>)}
        </select>
        <select id="g-count" class="gen__select" aria-label="Number of exercises">
          {counts.map((n) => <option value={n} selected={n === 6}>{n} exercises</option>)}
        </select>
        <button class="gen__btn" type="submit">Generate</button>
        <button class="gen__btn" id="g-reroll" type="button" hidden>↻ Reroll</button>
      </form>

      <p id="count" class="page__caption" role="status" aria-live="polite"></p>

      <ul class="grid" id="grid"></ul>

      <ExerciseDetail />
    </main>

    <script>
      import { initDetail, CDN } from '../../../scripts/exercise-detail';
      import { pickWorkout } from '../../../scripts/workout-picker';
      import exercises from '../../../data/fitness-exercises.json';

      const form = document.getElementById('gen') as HTMLFormElement;
      const equip = document.getElementById('g-equip') as HTMLSelectElement;
      const target = document.getElementById('g-target') as HTMLSelectElement;
      const countSel = document.getElementById('g-count') as HTMLSelectElement;
      const reroll = document.getElementById('g-reroll') as HTMLButtonElement;
      const grid = document.getElementById('grid')!;
      const caption = document.getElementById('count')!;

      function mode() {
        return (form.querySelector('input[name="mode"]:checked') as HTMLInputElement).value as
          | 'full'
          | 'focus';
      }
      function syncTarget() {
        target.hidden = mode() !== 'focus'; // hidden also removes it from tab order
      }
      form.querySelectorAll('input[name="mode"]').forEach((r) =>
        r.addEventListener('change', syncTarget),
      );
      syncTarget();

      function cardEl(e: (typeof exercises)[number]) {
        const li = document.createElement('li');
        li.className = 'card';
        li.dataset.id = e.id;
        const btn = document.createElement('button');
        btn.className = 'card__btn';
        btn.type = 'button';
        const img = document.createElement('img');
        img.className = 'card__img';
        img.src = `${CDN}/${e.image}`;
        img.alt = '';
        img.loading = 'lazy';
        img.width = 160;
        img.height = 160;
        const nm = document.createElement('span');
        nm.className = 'card__name';
        nm.textContent = e.name;
        const tag = document.createElement('span');
        tag.className = 'card__tag';
        tag.textContent = e.equipment;
        btn.append(img, nm, tag);
        li.append(btn);
        return li;
      }

      function render() {
        const picks = pickWorkout(exercises, {
          mode: mode(),
          equipment: equip.value,
          target: target.hidden ? '' : target.value,
          count: Number(countSel.value),
        });
        grid.replaceChildren(...picks.map(cardEl));
        const label = mode() === 'full' ? 'full body' : target.value || 'all targets';
        caption.textContent = picks.length
          ? `${picks.length} exercise${picks.length === 1 ? '' : 's'} · ${label}`
          : 'no matches — try different filters';
        reroll.hidden = false;
      }

      form.addEventListener('submit', (ev) => {
        ev.preventDefault();
        render();
      });
      reroll.addEventListener('click', render);

      initDetail(grid, exercises);
    </script>

    <style lang="scss">
      .page {
        display: grid;
        align-content: start;
        gap: to-rem(16);
        min-height: 100svh;
        max-width: var(--grid-max-width);
        margin-inline: auto;
        padding: clamp-fluid(24, 56) var(--grid-margin);
      }
      .page__back {
        justify-self: start;
        font-size: var(--fs-label);
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--c-on-surface-muted);
        text-decoration: none;
        transition: color 0.2s var(--ease-smooth);

        &:hover { color: var(--c-accent); }
        &:focus-visible { outline: 2px solid var(--c-accent); outline-offset: 2px; }
      }
      .page__title {
        margin: to-rem(8) 0 0;
        font-size: var(--fs-2);
        line-height: 0.95;
        text-transform: uppercase;
      }
      .page__caption { color: var(--c-on-surface-muted); }

      .gen {
        display: flex;
        flex-wrap: wrap;
        align-items: stretch;
        gap: to-rem(8);
        margin-top: to-rem(8);
      }
      .gen__modes {
        display: flex;
        gap: to-rem(16);
        align-items: center;
        margin: 0;
        padding: 0 to-rem(12);
        border: 1px solid var(--c-on-surface-muted);

        legend { padding: 0 to-rem(6); font-size: var(--fs-label); letter-spacing: 0.08em; text-transform: uppercase; color: var(--c-on-surface-muted); }
      }
      .gen__mode { display: inline-flex; gap: to-rem(6); align-items: center; min-height: to-rem(44); cursor: pointer; }
      .gen__select {
        font: inherit;
        color: var(--c-light);
        background: var(--c-dark);
        border: 1px solid var(--c-on-surface-muted);
        padding: to-rem(8) to-rem(12);
        min-height: to-rem(44);
        border-radius: 0;
        flex: 1 1 to-rem(150);

        &:focus-visible { outline: 2px solid var(--c-accent); outline-offset: 2px; }
        &[hidden] { display: none; }
      }
      .gen__btn {
        font: inherit;
        min-height: to-rem(44);
        padding: to-rem(8) to-rem(18);
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--c-light);
        background: var(--c-dark);
        border: 1px solid var(--c-on-surface-muted);
        cursor: pointer;
        transition: color 0.2s var(--ease-smooth), border-color 0.2s var(--ease-smooth);

        &:hover { color: var(--c-accent); border-color: var(--c-accent); }
        &:focus-visible { outline: 2px solid var(--c-accent); outline-offset: 2px; }
        &[hidden] { display: none; }
      }

      @media (max-width: 40rem) {
        .gen { flex-direction: column; align-items: stretch; }
      }

      .grid {
        list-style: none;
        margin: to-rem(16) 0 0;
        padding: 0;
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(min(to-rem(140), 100%), 1fr));
        gap: to-rem(12);
      }
      .card { list-style: none; }
      .card__btn {
        display: grid;
        gap: to-rem(6);
        width: 100%;
        padding: to-rem(8);
        text-align: left;
        color: inherit;
        background: transparent;
        border: 1px solid transparent;
        cursor: pointer;
        transition: border-color 0.2s var(--ease-smooth);

        &:hover { border-color: var(--c-accent); }
        &:focus-visible { outline: 2px solid var(--c-accent); outline-offset: 2px; }
      }
      .card__img {
        width: 100%;
        height: auto;
        aspect-ratio: 1;
        object-fit: cover;
        background: #111;
      }
      .card__name { font-size: var(--fs-base); text-transform: capitalize; overflow-wrap: anywhere; }
      .card__tag {
        font-size: var(--fs-label);
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--c-on-surface-muted);
      }
    </style>
  </body>
</html>
```

- [ ] **Step 2: Add the header link in `src/pages/vault/fitness.astro`**

Find the title line (`<h1 class="page__title">Fitness</h1>`) and add a link right after it:

```astro
      <h1 class="page__title">Fitness</h1>
      <a class="page__gen" href="/vault/fitness/generate">↗ Generate workout</a>
```

Add the matching style inside `fitness.astro`'s `<style>` block (next to `.page__back`):

```scss
      .page__gen {
        justify-self: start;
        font-size: var(--fs-label);
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--c-accent);
        text-decoration: none;

        &:hover { text-decoration: underline; }
        &:focus-visible { outline: 2px solid var(--c-accent); outline-offset: 2px; }
      }
```

- [ ] **Step 3: Build to typecheck the new page**

Run: `npm run build`
Expected: PASS — `astro check` 0 errors, build emits `/vault/fitness/generate`.

- [ ] **Step 4: Manual behavior check**

Run: `npm run dev`, unlock at `/vault`, open `/vault/fitness`, click **↗ Generate workout**. On `/vault/fitness/generate`:
- Full body + Any equipment + 6 → Generate → 6 cards across distinct body parts; caption `6 exercises · full body`.
- Switch to Focus → target select appears; pick Dumbbell + a target → Generate → cards all match that target.
- Reroll → different set, same constraints.
- Pick an equipment with few matches (e.g. focus on a rare target) → shortfall caption, no crash.
- Click any result card → shared dialog opens with steps/GIF.
- Reload while locked out (clear `kwg_vault`) → bounces to `/vault`.

- [ ] **Step 5: Commit**

```bash
git add src/pages/vault/fitness/generate.astro src/pages/vault/fitness.astro
git commit -m "✨ add fitness workout generator page"
```

---

## Notes

- No persistence, no copy/export — out of scope by design.
- `pickWorkout` is the only branchy logic and carries the one runnable test. The page wiring and dialog are DOM glue, verified manually (consistent with the project, which has no DOM test harness).
</content>
