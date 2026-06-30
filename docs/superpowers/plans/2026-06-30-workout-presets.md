# Workout Presets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three fixed, named workout routines as one-click presets on `/vault/fitness/generate` that render their exercises in author-defined order.

**Architecture:** A pure data module (`workout-presets.ts`) holds the routines as ordered id lists, validated by a `node:assert` test. The generator page gains a `MY ROUTINES` button row; clicking a preset resolves its ids and renders them through a shared `showExercises()` helper extracted from the existing random-generator `render()`.

**Tech Stack:** Astro, TypeScript, Node 26 (strips TS types natively; supports JSON import attributes `with { type: 'json' }`).

## Global Constraints

- Preset ids are exact dataset record ids; the spec's id tables are the source of truth. Order = display order. The three presets, in order: **Upper Body A** `['1350','0577','0579','0603','0602','0584']`; **Lower Body A** `['2138','2287','0585','0599','0739']`; **Upper Body B** `['0314','1350','0579','0603','0577','0596','0584','0607']`.
- No set counts, no persistence, no in-UI editing (presets live in the module).
- Presets render in author order — NO shuffle.
- Reuse the existing `.gen__btn` / `.gen` styling and the existing `cardEl` + `initDetail` (shared dialog). Only ADD; the one refactor is extracting `showExercises()`.
- Touch targets ≥44px and `:focus-visible` rings already come from `.gen__btn` — preset buttons inherit them.
- A preset id missing from the dataset must be skipped at render (`.filter(Boolean)`), not crash; the test prevents shipping a bad id.
- Verification baseline: `npm run build` (= `astro check && astro build`) passes with 0 errors.

---

### Task 1: Presets data module + validation test

**Files:**
- Create: `src/scripts/workout-presets.ts`
- Test: `src/scripts/workout-presets.test.mjs`
- Modify: `package.json` (add a `test:presets` script)

**Interfaces:**
- Produces: `export const PRESETS: { name: string; ids: string[] }[]` from `src/scripts/workout-presets.ts`, in display order (Upper Body A, Lower Body A, Upper Body B).

- [ ] **Step 1: Write the failing test `src/scripts/workout-presets.test.mjs`**

```js
import assert from 'node:assert/strict';
import { PRESETS } from './workout-presets.ts';
import exercises from '../data/fitness-exercises.json' with { type: 'json' };

const ids = new Set(exercises.map((e) => e.id));

assert.ok(PRESETS.length >= 3, 'expected at least 3 presets');
for (const p of PRESETS) {
  assert.ok(p.name && p.name.trim(), 'preset must have a name');
  assert.ok(Array.isArray(p.ids) && p.ids.length > 0, `${p.name} must have ids`);
  for (const id of p.ids) {
    assert.ok(ids.has(id), `${p.name}: id ${id} not found in dataset`);
  }
}

// Spot-check the three routines are present and the right size.
const byName = Object.fromEntries(PRESETS.map((p) => [p.name, p.ids.length]));
assert.equal(byName['Upper Body A'], 6, 'Upper Body A has 6 exercises');
assert.equal(byName['Lower Body A'], 5, 'Lower Body A has 5 exercises');
assert.equal(byName['Upper Body B'], 8, 'Upper Body B has 8 exercises');

console.log('ok: all preset ids resolve in the dataset');
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node src/scripts/workout-presets.test.mjs`
Expected: FAIL — `Cannot find module './workout-presets.ts'`.

- [ ] **Step 3: Write `src/scripts/workout-presets.ts`**

```ts
// Fixed training routines, rendered in this order on the generator page.
// ids are record ids in fitness-exercises.json; the .test.mjs verifies they resolve.
export const PRESETS: { name: string; ids: string[] }[] = [
  { name: 'Upper Body A', ids: ['1350', '0577', '0579', '0603', '0602', '0584'] },
  { name: 'Lower Body A', ids: ['2138', '2287', '0585', '0599', '0739'] },
  { name: 'Upper Body B', ids: ['0314', '1350', '0579', '0603', '0577', '0596', '0584', '0607'] },
];
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `node src/scripts/workout-presets.test.mjs`
Expected: PASS — prints `ok: all preset ids resolve in the dataset`.

- [ ] **Step 5: Add the npm script**

In `package.json`, in the `"scripts"` block, add a line after the existing `"test:picker"` line:

```json
    "test:presets": "node src/scripts/workout-presets.test.mjs",
```

Verify: `npm run test:presets` prints the `ok:` line.

- [ ] **Step 6: Commit**

```bash
git add src/scripts/workout-presets.ts src/scripts/workout-presets.test.mjs package.json
git commit -m "✨ add workout preset definitions + validation test"
```

---

### Task 2: Preset buttons on the generator page

**Files:**
- Modify: `src/pages/vault/fitness/generate.astro`

**Interfaces:**
- Consumes: `PRESETS` from `src/scripts/workout-presets.ts`; existing `cardEl`, `initDetail`, `CDN`, `pickWorkout`, and the `exercises` JSON already imported on this page.

This task is verified by `npm run build` + a manual browser check (DOM wiring; the project does not unit-test DOM). There is no new unit test.

- [ ] **Step 1: Import `PRESETS` in the frontmatter**

In the `---` frontmatter block of `src/pages/vault/fitness/generate.astro`, add this import alongside the existing imports:

```astro
import { PRESETS } from '../../../scripts/workout-presets';
```

- [ ] **Step 2: Add the `MY ROUTINES` button row in the markup**

Insert this block immediately BEFORE the `<form class="gen" id="gen">` line (currently line 39):

```astro
      <div class="gen gen--presets" role="group" aria-label="My routines">
        <span class="gen__label">My routines</span>
        {PRESETS.map((p, i) => (
          <button class="gen__btn" type="button" data-preset={i}>{p.name}</button>
        ))}
      </div>
```

- [ ] **Step 3: Wire presets in the page `<script>` and extract the shared render helper**

In the `<script>` block, after the line `const caption = document.getElementById('count')!;` (line 78), add a `byId` lookup:

```ts
      const byId: Record<string, (typeof exercises)[number]> = Object.fromEntries(
        exercises.map((e) => [e.id, e]),
      );
```

Replace the existing `render()` function (currently lines 118–131):

```ts
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
```

with this — a shared `showExercises()` helper plus a slimmed `render()`:

```ts
      function showExercises(list: (typeof exercises)[number][], captionText: string) {
        grid.replaceChildren(...list.map(cardEl));
        caption.textContent = captionText;
      }

      function render() {
        const picks = pickWorkout(exercises, {
          mode: mode(),
          equipment: equip.value,
          target: target.hidden ? '' : target.value,
          count: Number(countSel.value),
        });
        const label = mode() === 'full' ? 'full body' : target.value || 'all targets';
        showExercises(
          picks,
          picks.length
            ? `${picks.length} exercise${picks.length === 1 ? '' : 's'} · ${label}`
            : 'no matches — try different filters',
        );
        reroll.hidden = false;
      }
```

Then, immediately after the line `reroll.addEventListener('click', render);` (currently line 137), add the preset wiring:

```ts
      for (const btn of document.querySelectorAll<HTMLButtonElement>('[data-preset]')) {
        btn.addEventListener('click', () => {
          const p = PRESETS[Number(btn.dataset.preset)];
          const list = p.ids.map((id) => byId[id]).filter(Boolean);
          showExercises(
            list,
            `${p.name} · ${list.length} exercise${list.length === 1 ? '' : 's'}`,
          );
          reroll.hidden = true; // reroll is meaningless for a fixed routine
        });
      }
```

- [ ] **Step 4: Add the `.gen__label` style**

In the page `<style lang="scss">` block, add this rule next to the `.gen` rules (e.g. after the `.gen__modes` block):

```scss
      .gen__label {
        display: inline-flex;
        align-items: center;
        min-height: to-rem(44);
        font-size: var(--fs-label);
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--c-on-surface-muted);
      }
```

- [ ] **Step 5: Build to typecheck**

Run: `npm run build`
Expected: PASS — `astro check` 0 errors, build completes.

- [ ] **Step 6: Manual behavior check**

Run: `npm run dev`, unlock at `/vault`, open `/vault/fitness/generate`. Confirm:
- A `MY ROUTINES` row shows three buttons: Upper Body A, Lower Body A, Upper Body B.
- Clicking **Upper Body A** → 6 cards in order: lever seated row, lever chest press, lever front pulldown, lever shoulder press, lever seated reverse fly, lever lateral raise; caption `Upper Body A · 6 exercises`; Reroll hidden.
- Clicking **Lower Body A** → 5 cards starting with stationary bike, ending with sled 45° leg press.
- Clicking **Upper Body B** → 8 cards starting with dumbbell incline bench press.
- Clicking any result card opens the shared detail dialog.
- The random **Generate** path still works (and shows Reroll again).

- [ ] **Step 7: Commit**

```bash
git add src/pages/vault/fitness/generate.astro
git commit -m "✨ add workout preset buttons to generator page"
```

---

## Notes

- `showExercises()` is the only refactor; it removes duplication between the random generator and presets.
- Presets are data; to change a routine, edit `workout-presets.ts` and the test re-validates the ids.
</content>
