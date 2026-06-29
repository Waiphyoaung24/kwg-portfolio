# Fitness Reference Browser Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the empty `/vault/fitness` placeholder with a client-side, searchable/filterable reference browser for 1,324 exercises.

**Architecture:** A one-time Node script trims the dataset's `exercises.json` (English-only, needed fields) into a committed `src/data/fitness-exercises.json`. The Astro page imports that JSON at build time, renders a filterable card grid (static thumbnails), and opens a native `<dialog>` that lazy-loads the animated GIF + steps on click. All media is hotlinked from jsDelivr pinned to commit `92e2704`. No new dependencies.

**Tech Stack:** Astro, SCSS (existing `index.scss` tokens), vanilla JS (`is:inline` + `define:vars`), Node ESM scripts with `node:assert/strict`.

## Global Constraints

- Keep the existing vault gate verbatim: `<script is:inline>` in `<head>` that does `if (localStorage.getItem('kwg_vault') !== '1') location.replace('/vault');`
- Keep `<meta name="robots" content="noindex" />`.
- jsDelivr CDN prefix, pinned: `https://cdn.jsdelivr.net/gh/hasaneyldrm/exercises-dataset@92e2704`
- No new npm dependencies. The dataset repo is NOT added to `package.json`.
- Reuse existing SCSS tokens (`--c-accent`, `--c-on-surface-muted`, `clamp-fluid`, `to-rem`, `--grid-max-width`, `--grid-margin`, `--ease-smooth`). No new design system.
- Tests are standalone `.mjs` files using `node:assert/strict`, run with `node` (match `src/scripts/vault-hash.test.mjs`).
- English only. No i18n.

---

### Task 1: Data trim script + committed JSON

Generates `src/data/fitness-exercises.json` from a local clone of the dataset. The script's built-in asserts ARE the self-check (a one-shot generator doesn't need a separate test file — same spirit as the repo's existing assert scripts).

**Files:**
- Create: `src/scripts/build-fitness-data.mjs`
- Create (generated, committed): `src/data/fitness-exercises.json`

**Interfaces:**
- Produces: `src/data/fitness-exercises.json` — a JSON array of records with shape:
  `{ id: string, name: string, category: string, body_part: string, equipment: string, target: string, secondary_muscles: string[], muscle_group: string, image: string, gif_url: string, steps: string[] }`
  where `image` / `gif_url` are repo-relative paths like `"images/0001-2gPfomN.jpg"` / `"videos/0001-2gPfomN.gif"` (CDN prefix applied later by the page, NOT stored here).

- [ ] **Step 1: Clone the dataset to a temp dir**

```bash
git clone --depth 1 https://github.com/hasaneyldrm/exercises-dataset.git /tmp/exercises-dataset
git -C /tmp/exercises-dataset rev-parse --short HEAD   # sanity: expect 92e2704
```
Expected: clone succeeds; short SHA prints `92e2704` (if it differs, the pin in the page must be updated to match — flag it).

- [ ] **Step 2: Write the script**

Create `src/scripts/build-fitness-data.mjs`:

```js
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import assert from 'node:assert/strict';

const src = process.argv[2];
assert(src, 'usage: node build-fitness-data.mjs <path-to-exercises.json>');

const raw = JSON.parse(await readFile(src, 'utf8'));
assert(Array.isArray(raw), 'expected an array of exercises');

const out = raw.map((e) => ({
  id: e.id,
  name: e.name,
  category: e.category,
  body_part: e.body_part,
  equipment: e.equipment,
  target: e.target,
  secondary_muscles: e.secondary_muscles ?? [],
  muscle_group: e.muscle_group,
  image: e.image,
  gif_url: e.gif_url,
  steps: e.instruction_steps?.en ?? [],
}));

// Self-check: this is the runnable check for this task.
assert(out.length > 1300, `expected >1300 exercises, got ${out.length}`);
for (const e of out) {
  assert(e.name, `missing name for id ${e.id}`);
  assert(e.image, `missing image for ${e.name}`);
}

const destDir = new URL('../data/', import.meta.url);
await mkdir(destDir, { recursive: true });
await writeFile(new URL('fitness-exercises.json', destDir), JSON.stringify(out));
console.log(`ok: wrote ${out.length} exercises to src/data/fitness-exercises.json`);
```

- [ ] **Step 3: Run it (this both generates the file and runs the self-check)**

Run: `node src/scripts/build-fitness-data.mjs /tmp/exercises-dataset/data/exercises.json`
Expected: prints `ok: wrote 1324 exercises to src/data/fitness-exercises.json` (count may differ by a few if the dataset updated; any assert failure means STOP and inspect).

- [ ] **Step 4: Sanity-check the output**

Run: `node -e "const a=require('./src/data/fitness-exercises.json'); console.log(a.length, a[0].name, a[0].steps.length, a[0].image)"`
Expected: a count (~1324), a name string, a steps count ≥ 1, and an `images/...jpg` path. Confirm NO `instructions` / `it`/`tr`/`es` keys exist: `node -e "const a=require('./src/data/fitness-exercises.json'); console.log(Object.keys(a[0]))"` should print exactly `id,name,category,body_part,equipment,target,secondary_muscles,muscle_group,image,gif_url,steps`.

- [ ] **Step 5: Commit**

```bash
git add src/scripts/build-fitness-data.mjs src/data/fitness-exercises.json
git commit -m "✨ add fitness dataset trim script + generated data"
```

---

### Task 2: Fitness browser page

Replaces the placeholder body of `src/pages/vault/fitness.astro` with the filter UI, card grid, and detail dialog. Keeps the existing head (gate, noindex, fonts, title) unchanged.

**Files:**
- Modify: `src/pages/vault/fitness.astro` (replace `<main>` body + `<style>`; add a `<script>`; keep `<head>` as-is)

**Interfaces:**
- Consumes: `src/data/fitness-exercises.json` (shape from Task 1).

- [ ] **Step 1: Replace the frontmatter to import data + derive filters**

Replace the frontmatter block (currently just `import '../../styles/index.scss';`) with:

```astro
---
import '../../styles/index.scss';
import exercises from '../../data/fitness-exercises.json';

const CDN = 'https://cdn.jsdelivr.net/gh/hasaneyldrm/exercises-dataset@92e2704';
const uniq = (k) => [...new Set(exercises.map((e) => e[k]).filter(Boolean))].sort();
const bodyParts = uniq('body_part');
const equipments = uniq('equipment');
const targets = uniq('target');
---
```

Leave the entire `<head>` (gate script, noindex, fonts, title) exactly as it is.

- [ ] **Step 2: Replace the `<main>` body**

Replace the existing `<main class="page">…</main>` with:

```astro
<main class="page">
  <a class="page__back" href="/vault">← Vault</a>
  <h1 class="page__title">Fitness</h1>

  <div class="filters">
    <input id="q" class="filters__search" type="search" placeholder="Search exercises…" autocomplete="off" />
    <select id="f-body" class="filters__select">
      <option value="">All body parts</option>
      {bodyParts.map((v) => <option value={v}>{v}</option>)}
    </select>
    <select id="f-equip" class="filters__select">
      <option value="">All equipment</option>
      {equipments.map((v) => <option value={v}>{v}</option>)}
    </select>
    <select id="f-target" class="filters__select">
      <option value="">All targets</option>
      {targets.map((v) => <option value={v}>{v}</option>)}
    </select>
  </div>

  <p id="count" class="page__caption"></p>

  <ul class="grid" id="grid">
    {exercises.map((e) => (
      <li
        class="card"
        data-id={e.id}
        data-name={e.name.toLowerCase()}
        data-body={e.body_part}
        data-equip={e.equipment}
        data-target={e.target}
      >
        <button class="card__btn" type="button">
          <img class="card__img" src={`${CDN}/${e.image}`} alt={e.name} loading="lazy" width="160" height="160" />
          <span class="card__name">{e.name}</span>
          <span class="card__tag">{e.equipment}</span>
        </button>
      </li>
    ))}
  </ul>

  <dialog id="detail" class="detail">
    <button class="detail__close" type="button" aria-label="Close">✕</button>
    <img class="detail__gif" alt="" width="360" height="360" loading="lazy" />
    <h2 class="detail__name"></h2>
    <p class="detail__meta"></p>
    <ol class="detail__steps"></ol>
  </dialog>
</main>
```

- [ ] **Step 3: Add the client script (after `</main>`, before the `<style>`)**

```astro
<script is:inline define:vars={{ exercises, CDN }}>
  const byId = Object.fromEntries(exercises.map((e) => [e.id, e]));
  const grid = document.getElementById('grid');
  const cards = [...grid.children];
  const q = document.getElementById('q');
  const fBody = document.getElementById('f-body');
  const fEquip = document.getElementById('f-equip');
  const fTarget = document.getElementById('f-target');
  const count = document.getElementById('count');

  function apply() {
    const term = q.value.trim().toLowerCase();
    const b = fBody.value, eq = fEquip.value, t = fTarget.value;
    let n = 0;
    for (const card of cards) {
      const ok =
        (!term || card.dataset.name.includes(term)) &&
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

  const dlg = document.getElementById('detail');
  const gif = dlg.querySelector('.detail__gif');
  const name = dlg.querySelector('.detail__name');
  const meta = dlg.querySelector('.detail__meta');
  const steps = dlg.querySelector('.detail__steps');

  grid.addEventListener('click', (ev) => {
    const card = ev.target.closest('.card');
    if (!card) return;
    const e = byId[card.dataset.id];
    name.textContent = e.name;
    meta.textContent = [e.target, e.equipment, e.body_part].filter(Boolean).join(' · ');
    steps.replaceChildren();
    for (const s of e.steps || []) {
      const li = document.createElement('li');
      li.textContent = s;
      steps.appendChild(li);
    }
    gif.src = `${CDN}/${e.gif_url}`;   // GIF loads only now, never for the grid
    gif.alt = e.name;
    dlg.showModal();
  });

  dlg.querySelector('.detail__close').addEventListener('click', () => dlg.close());
  dlg.addEventListener('click', (ev) => { if (ev.target === dlg) dlg.close(); });
  dlg.addEventListener('close', () => { gif.removeAttribute('src'); });
</script>
```

- [ ] **Step 4: Replace the `<style lang="scss">` block**

Keep the existing `.page`, `.page__back`, `.page__title`, `.page__caption` rules, and append these to the same block:

```scss
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: to-rem(8);
  margin-top: to-rem(8);
}
.filters__search,
.filters__select {
  font: inherit;
  color: var(--c-on-surface);
  background: transparent;
  border: 1px solid var(--c-on-surface-muted);
  padding: to-rem(8) to-rem(12);
  border-radius: 0;

  &:focus-visible {
    outline: 2px solid var(--c-accent);
    outline-offset: 2px;
  }
}
.filters__search { flex: 1 1 16rem; }

.grid {
  list-style: none;
  margin: to-rem(16) 0 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(to-rem(140), 1fr));
  gap: to-rem(12);
}
.card[hidden] { display: none; }
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
.card__name { font-size: var(--fs-body); text-transform: capitalize; }
.card__tag {
  font-size: var(--fs-label);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--c-on-surface-muted);
}

.detail {
  max-width: min(92vw, to-rem(480));
  color: var(--c-on-surface);
  background: var(--c-surface);
  border: 1px solid var(--c-on-surface-muted);
  padding: clamp-fluid(16, 28);

  &::backdrop { background: rgb(0 0 0 / 0.7); }
}
.detail__close {
  position: absolute;
  top: to-rem(8);
  right: to-rem(8);
  font: inherit;
  color: var(--c-on-surface-muted);
  background: transparent;
  border: 0;
  cursor: pointer;

  &:hover { color: var(--c-accent); }
}
.detail__gif {
  width: 100%;
  height: auto;
  aspect-ratio: 1;
  object-fit: contain;
  background: #111;
}
.detail__name { margin: to-rem(12) 0 to-rem(4); text-transform: capitalize; }
.detail__meta {
  margin: 0 0 to-rem(12);
  font-size: var(--fs-label);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--c-on-surface-muted);
}
.detail__steps { margin: 0; padding-left: 1.2em; display: grid; gap: to-rem(6); }
```

Note: if any referenced token (e.g. `--c-surface`, `--c-on-surface`, `--fs-body`) does not exist in `src/styles`, substitute the nearest existing token rather than inventing one — grep `src/styles` for the actual token names before finalizing this step.

- [ ] **Step 5: Type-check + build**

Run: `npm run build`
Expected: `astro check` passes with 0 errors, build completes. (Astro types JSON imports automatically, so the `import exercises` line should not error.)

- [ ] **Step 6: Verify in the browser**

Run: `npm run dev`, then in the browser:
1. Open `/vault`, unlock with the password (sets `kwg_vault=1`).
2. Navigate to `/vault/fitness`.
3. Confirm: grid of thumbnails renders, count shows ~1324, typing in search narrows the grid, each select narrows it, combined filters AND together.
4. Click a card → dialog opens with an animated GIF, name, meta line, numbered steps. Escape / backdrop / ✕ all close it. Open a second card → GIF updates.
5. Open DevTools Network, filter to `gif` → confirm NO gif requests fire until a card is clicked (grid loads only `.jpg`).

- [ ] **Step 7: Commit**

```bash
git add src/pages/vault/fitness.astro
git commit -m "✨ build fitness exercise reference browser"
```

---

## Self-Review

**Spec coverage:**
- Reference browser (read-only) → Task 2 ✓
- jsDelivr hotlink, pinned `92e2704` → Global Constraints + Task 2 CDN const ✓
- Trimmed English JSON, dataset not a dependency → Task 1 ✓
- `<dialog>` modal, lazy GIF, no per-exercise routes → Task 2 Steps 2–3 ✓
- Filters: search + body part + equipment + target → Task 2 Steps 1–3 ✓
- Static thumbnails in grid, GIF only on open → Task 2 Step 3 + verify Step 6.5 ✓
- Reuse existing SCSS tokens, no new deps → Global Constraints + Task 2 Step 4 ✓
- Build self-check → Task 1 Step 2 asserts ✓
- Keep gate + noindex → Global Constraints + Task 2 Step 1 ✓

**Placeholder scan:** No TBD/TODO; all code blocks complete. The Step 4 token note is a real instruction (verify token names), not a placeholder.

**Type consistency:** Record shape (Task 1 Produces) matches every field read in Task 2 (`id, name, body_part, equipment, target, image, gif_url, steps`). `CDN` const identical in both places. `byId` keyed by `e.id` matches `data-id`.
