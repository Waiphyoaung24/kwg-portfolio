# Works Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild `/works` as a scroll-driven exhibit — one full-viewport screen per chapter, each a WebGL carousel of that chapter's projects, with a curtain transition at every chapter boundary.

**Architecture:** Astro page + per-chapter component, no framework runtime. A pure TypeScript module owns slide state; DOM wiring reads from it; a curtains.js plane layer textures the active slide and warps on drag/scroll velocity; GSAP ScrollTrigger drives the curtain at boundaries. Every layer degrades independently: no JS gives a linear stack, no WebGL gives a plain image carousel.

**Tech Stack:** Astro 6, TypeScript, SCSS, GSAP 3.15 (+ ScrollTrigger, Flip, SplitText), Lenis, curtains.js 8, GLSL via `vite-plugin-glsl`. **No new dependency is added.**

**Spec:** `docs/superpowers/specs/2026-09-13-works-restructure-design.md`

## Global Constraints

- **`DESIGN.md` is law and is unamended by this work.** Near-black canvas only, no light sections. Weight 400 everywhere — never bold. Hairline borders carry elevation; no shadows. Every interactive element is a pill.
- **Use tokens, never raw values.** Colours, spacing, radii, type sizes and easings come from `src/styles/_vars.scss`. A hex code or px literal in a component is a bug unless a comment explains why.
- **Reuse the primitives.** `.pill-btn`, `.pill-btn--filled`, `.card`, `.label`, `.micro` in `src/styles/`. Do not hand-roll a button. Mixins: `has-hover()`, `has-motion()`, `liquid-glass($radius, $frost)`.
- **No new npm dependency.** Everything needed is installed.
- **WCAG 2.2 AA is the floor.** `--c-mute` (#7d8187, ~3.5:1) is metadata only — never primary copy or an interactive label. Use `--c-body` (#dadbdf) for secondary copy. Focus indicators are never removed.
- **All motion gates on `prefers-reduced-motion: reduce`.** Motion is never load-bearing for comprehension.
- **Two independent fallbacks.** No-JS (slides ship visible, script collapses them) and no-WebGL (`.no-curtains` on `<body>` reveals the DOM `<img>`). A device can have one without the other.
- **Texture budget:** plane textures cap at **1600×900**. Planes exist only for the in-view chapter plus one lookahead. Films never become WebGL textures.
- Commit after every task. Run `yarn build` (which is `astro check && astro build`) before each commit.

---

## File Structure

```
src/data/works.ts                    modified  roster (D9a); homeOnly retired
src/data/works.test.mjs              modified  assertions follow the roster
src/styles/_vars.scss                modified  + two reference easings
src/components/ActionPill.astro      create    .pill-btn + two-icon badge
src/scripts/works/slides.ts          create    pure slide-index maths
src/scripts/works/slides.test.mjs    create    node assert, no framework
src/components/WorkCarousel.astro    create    one chapter; replaces WorkChapter
src/scripts/works/carousel.ts        create    DOM wiring: arrows, thumbs, drag, keys
src/scripts/works/lineReveal.ts      create    SplitText line-mask reveal
src/shader/carousel.vert.glsl        create    plane bulge driven by velocity
src/shader/carousel.frag.glsl        create    texture sample + directional smear
src/components/Canvas.astro          modified  scoped containers + plane registry
src/components/PageCurtain.astro     create    fixed sheet + canvas
src/scripts/works/curtain.ts         create    boundary ScrollTriggers
src/components/WorkDetail.astro      create    overlay extracted from index.astro
src/pages/index.astro                modified  overlay markup+styles → component
src/pages/works.astro                rewritten hero, 3 carousels, closing
src/components/WorkChapter.astro     delete    superseded
docs/works-page-design.md            modified  marked superseded
```

**One deviation from spec §2, deliberate.** The spec says "no change to `src/pages/index.astro`'s Selected Work section". Task 9 does modify `index.astro` — but it extracts the `work-detail` overlay into a shared component without altering its markup, styles, or behaviour. Selected Work itself is untouched. The alternative is duplicating ~85 lines of markup and ~230 lines of SCSS onto `/works`, which is worse. If the extraction produces any visual change, it has gone wrong.

---

## Task 1: Roster — D9(a)

Free the four real projects from `homeOnly`, delete the five `TODO —` stubs, and retire the now-unused flag.

**Files:**
- Modify: `src/data/works.ts`
- Test: `src/data/works.test.mjs`

**Interfaces:**
- Consumes: nothing.
- Produces: `worksFor(category: Category): Work[]` — unchanged signature, now returning only real work. The `Work` interface no longer has `homeOnly`. Chapter rosters become: `creative-web` 4, `erp` 2, `custom-build` 2.

- [ ] **Step 1: Write the failing assertions**

In `src/data/works.test.mjs`, replace the two `homeOnly` blocks. Delete this block entirely:

```js
  // Home-only work is reachable ONLY through Selected Work, so without both a
  // caption and a poster it renders in neither place.
  if (w.homeOnly) {
    assert.ok(w.featured, `${w.id}: homeOnly needs featured`);
    assert.ok(w.media, `${w.id}: homeOnly needs media`);
  }
```

Replace the orphan loop:

```js
// No project may be orphaned from a chapter — it would never render. Home-only
// work is the deliberate exception: it renders in Selected Work instead, and
// `worksFor` keeps it out of the exhibit.
for (const w of works) {
  if (w.homeOnly) continue;
  assert.ok(seen.has(w.category), `${w.id}: category has no chapter`);
}
```

with:

```js
// Every project renders in a chapter. The home-only exception is gone: the
// exhibit and Selected Work now draw from the same set, filtered differently
// (index.astro selects on `featured && media`).
for (const w of works) {
  assert.ok(seen.has(w.category), `${w.id}: category has no chapter`);
}

// The exhibit is a carousel of full-viewport slides, so a placeholder costs a
// whole screen. Nothing ships with TODO copy (spec D9).
for (const w of works) {
  const copy = [w.title, w.client, w.summary, ...w.stack].join(' ');
  assert.ok(!copy.includes('TODO'), `${w.id}: placeholder copy in the exhibit`);
}

// A slide is textured from its poster. Kage is the one permitted gap and
// renders the labelled empty panel instead.
const ALLOWED_EMPTY = new Set(['kage']);
for (const w of works) {
  assert.ok(
    w.media !== null || ALLOWED_EMPTY.has(w.id),
    `${w.id}: needs media, or an entry in ALLOWED_EMPTY`,
  );
}
```

Replace the final log line:

```js
const homeOnly = works.filter((w) => w.homeOnly).length;
console.log(
  `ok: ${works.length} works across ${chapters.length} chapters ` +
    `(${homeOnly} home-only)`,
);
```

with:

```js
const perChapter = chapters
  .map((c) => `${c.index}:${worksFor(c.category).length}`)
  .join(' ');
console.log(`ok: ${works.length} works across ${chapters.length} chapters (${perChapter})`);
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node src/data/works.test.mjs`
Expected: FAIL — `placeholder-creative-03: placeholder copy in the exhibit`

- [ ] **Step 3: Make the roster change**

In `src/data/works.ts`:

1. Delete these five entries whole: `placeholder-creative-03`, `placeholder-erp-03`, `placeholder-custom-01`, `placeholder-custom-02`, `placeholder-custom-03`.
2. Delete the line `homeOnly: true,` from `parallel`, `redhorse-group`, `mrspinel-staff`, `gaigai`.
3. Delete the `// ---- Home page only ----` comment banner above `parallel` and the paragraph under it, replacing it with nothing — those four entries now sit in their category's section. Move them so file order matches chapter order: `parallel` and `redhorse-group` after `kage`; `mrspinel-staff` and `gaigai` under a `// ---- Custom web & mobile ----` banner.
4. Delete the `homeOnly` field and its doc comment from the `Work` interface:

```ts
  /**
   * Show in Selected Work on the home page but keep out of the /works
   * exhibit. `worksFor` skips these, so they never reach a chapter panel —
   * which also means their category is inert, and that nothing deep-links to
   * `/works#panel-<id>` for them.
   */
  homeOnly?: true;
```

5. Simplify `worksFor`:

```ts
/** Projects for one chapter, in file order. */
export const worksFor = (category: Category): Work[] =>
  works.filter((w) => w.category === category);
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `node src/data/works.test.mjs`
Expected: `ok: 8 works across 3 chapters (02:4 03:2 04:2)`

- [ ] **Step 5: Confirm the home page is unaffected**

`src/pages/index.astro:20` selects on `featured && media`, and `index.astro:778` destructures `homeOnly` from each gallery entry to choose a CTA target. That destructure now yields `undefined` for every entry, which is the same value it yielded for non-home-only work before — so the CTA logic is unchanged. Verify by reading `src/pages/index.astro:775-790` and confirming `homeOnly` is only used as a truthiness check.

Run: `yarn build`
Expected: PASS. `astro check` reports 0 errors.

- [ ] **Step 6: Commit**

```bash
git add src/data/works.ts src/data/works.test.mjs
git commit -m "✨ works: the exhibit ships eight real projects, no placeholders"
```

---

## Task 2: Easing tokens and the ActionPill

The reference's pill mechanic is a 36px circular badge holding two stacked icons: on hover the first slides out right and its clone arrives from the left. It is CSS only — a hover state that needs a JS runtime is a hover state that breaks.

**Files:**
- Modify: `src/styles/_vars.scss`
- Create: `src/components/ActionPill.astro`

**Interfaces:**
- Consumes: `.pill-btn` / `.pill-btn--filled` from `src/styles/_base.scss`; `Icon.astro` and `src/data/icons.ts`.
- Produces: `<ActionPill href label icon variant? external? />` where `variant` is `'outline' | 'filled'` (default `'outline'`). Renders an `<a>` when `href` is set, a `<button type="button">` otherwise.

- [ ] **Step 1: Add the two easings**

In `src/styles/_vars.scss`, in the `// animations` block after `--ease-out-expo`:

```scss
  // Pill motion, measured off stylized.cortiz.dev (spec §4). The overshoot
  // variant is what makes the icon swap read as mechanical rather than soft;
  // the two are a pair and are not interchangeable.
  --ease-pill: cubic-bezier(0.22, 0.68, 0, 1);
  --ease-pill-icon: cubic-bezier(0.22, 0.68, 0, 1.5);
```

- [ ] **Step 2: Write the component**

Create `src/components/ActionPill.astro`:

```astro
---
// The site's action pill: the shared `.pill-btn` shape, plus a badge that
// swaps its icon on hover. Mechanism ported from stylized.cortiz.dev (spec
// §4, §7.4); every colour, face and weight is ours.
//
// The icon is rendered twice on purpose. Both copies sit in the same grid
// cell inside an overflow-hidden badge: one leaves to the right while the
// clone arrives from the left, so the badge never shows an empty frame.
import Icon from '@components/Icon.astro';

interface Props {
  /** Renders an <a> when present, a <button> when not. */
  href?: string;
  label: string;
  /** Key from src/data/icons.ts */
  icon: string;
  variant?: 'outline' | 'filled';
  /** Opens in a new tab and appends the offsite affordance. */
  external?: boolean;
}

const { href, label, icon, variant = 'outline', external = false } = Astro.props;

const Tag = href ? 'a' : 'button';
const classes = ['action-pill', 'pill-btn', variant === 'filled' && 'pill-btn--filled']
  .filter(Boolean)
  .join(' ');
---

<Tag
  class={classes}
  href={href}
  type={href ? undefined : 'button'}
  target={external ? '_blank' : undefined}
  rel={external ? 'noopener noreferrer' : undefined}
>
  <span class="action-pill__label label">{label}</span>
  <span class="action-pill__badge" aria-hidden="true">
    <span class="action-pill__icon"><Icon name={icon} /></span>
    <span class="action-pill__icon action-pill__icon--clone"><Icon name={icon} /></span>
  </span>
  {external && <span class="visually-hidden">(opens in a new tab)</span>}
</Tag>

<style lang="scss">
  .action-pill {
    // Asymmetric padding: the label needs breathing room on the left, the
    // badge sits almost flush right. Measured 0 5px 0 22px; ours rounds to
    // the 4px scale.
    padding: var(--sp-xs) var(--sp-xs) var(--sp-xs) var(--sp-xl);
    gap: var(--sp-md);
    transition:
      background-color 0.5s var(--ease-pill),
      border-color 0.5s var(--ease-pill),
      color 0.5s var(--ease-pill),
      transform 0.5s var(--ease-pill);

    @include has-hover {
      // The reference lifts to 1.1. At our pill sizes that reads as a jump,
      // and DESIGN.md has no shadow to anchor it — so the scale is halved.
      &:hover {
        transform: scale(1.04);
      }
    }
  }

  .action-pill__label {
    color: inherit;
  }

  .action-pill__badge {
    flex: 0 0 auto;
    display: grid;
    place-items: center;
    width: to-rem(36);
    height: to-rem(36);
    border-radius: var(--r-pill);
    background-color: rgba(255, 255, 255, 0.14);
    // The swap only reads because the badge clips it.
    overflow: hidden;
    transition: background-color 0.5s var(--ease-pill);
  }

  .pill-btn--filled .action-pill__badge {
    background-color: rgba(10, 10, 10, 0.12);
  }

  .action-pill__icon {
    // Both icons occupy one cell, so neither reserves layout for the other.
    grid-area: 1 / 1;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: transform 0.5s var(--ease-pill-icon);
  }

  .action-pill__icon--clone {
    transform: translateX(-250%);
  }

  @include has-hover {
    .action-pill:hover {
      .action-pill__badge {
        background-color: rgba(255, 255, 255, 0.22);
      }

      .action-pill__icon {
        transform: translateX(250%);
      }

      .action-pill__icon--clone {
        transform: translateX(0);
      }
    }

    .pill-btn--filled:hover .action-pill__badge {
      background-color: rgba(10, 10, 10, 0.2);
    }
  }

  // The clone stays parked and nothing travels, matching the reference's own
  // reduced-motion block. The pill still reports hover through its border.
  @media (prefers-reduced-motion: reduce) {
    .action-pill,
    .action-pill__badge,
    .action-pill__icon {
      transition: none;
    }

    .action-pill:hover {
      transform: none;

      .action-pill__icon {
        transform: none;
      }

      .action-pill__icon--clone {
        transform: translateX(-250%);
      }
    }
  }
</style>
```

- [ ] **Step 3: Add the arrow glyph**

`src/data/icons.ts` holds 32 Feather glyphs and **none of them is an arrow**. `Icon.astro:19` throws on an unknown name, so using `arrow-up-right` without adding it fails the build rather than rendering an empty box.

The file's header says "add a name to the list and regenerate", but no generator is checked in and `feather-icons` is not a dependency — so add the entry by hand, matching its neighbours exactly: the inner markup of the upstream 24×24 glyph, no stroke or fill attributes (those live on the wrapper in `Icon.astro`). Insert in alphabetical order, above `activity`:

```ts
  'arrow-up-right':
    '<line x1="7" y1="17" x2="17" y2="7"></line><polyline points="7 7 17 7 17 17"></polyline>',
```

Then correct the stale header comment, since the next person will hit the same wall. Replace:

```ts
// Generated from feather-icons 4.29.2 — do not hand-edit; add a name to the
// list and regenerate.
```

with:

```ts
// Transcribed from feather-icons 4.29.2. No generator is checked in, so new
// glyphs are added by hand: copy the inner markup of the upstream 24x24 SVG
// verbatim and keep the list alphabetical.
```

- [ ] **Step 4: Build**

Run: `yarn build`
Expected: PASS, 0 `astro check` errors.

- [ ] **Step 5: Commit**

```bash
git add src/styles/_vars.scss src/components/ActionPill.astro src/data/icons.ts
git commit -m "✨ ui: action pill swaps its icon on hover"
```

---

## Task 3: Slide state

Pure index maths, no DOM. Extracted so the awkward cases — a two-slide carousel, a drag that does not commit — are testable without a browser.

**Files:**
- Create: `src/scripts/works/slides.ts`
- Test: `src/scripts/works/slides.test.mjs`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `clampIndex(index: number, count: number): number`
  - `canGo(index: number, count: number, dir: -1 | 1): boolean`
  - `indexAfterDrag(index: number, count: number, dx: number, width: number, threshold?: number): number`

- [ ] **Step 1: Write the failing test**

Create `src/scripts/works/slides.test.mjs`:

```js
import assert from 'node:assert/strict';
import { clampIndex, canGo, indexAfterDrag } from './slides.ts';

// The rail does NOT wrap. With two slides a wrapping carousel reads as a
// flicker between the same two frames, and the arrows stop meaning anything.
assert.equal(clampIndex(-1, 4), 0, 'clamps below zero');
assert.equal(clampIndex(4, 4), 3, 'clamps above the last');
assert.equal(clampIndex(2, 4), 2, 'leaves an in-range index alone');
assert.equal(clampIndex(0, 0), 0, 'survives an empty carousel');

assert.equal(canGo(0, 2, -1), false, 'no previous at the first slide');
assert.equal(canGo(0, 2, 1), true, 'next exists at the first slide');
assert.equal(canGo(1, 2, 1), false, 'no next at the last slide');
assert.equal(canGo(0, 1, 1), false, 'a single slide goes nowhere');

// A drag shorter than the threshold snaps back rather than committing.
assert.equal(indexAfterDrag(1, 4, -60, 1000), 1, 'short drag does not commit');
assert.equal(indexAfterDrag(1, 4, -300, 1000), 2, 'drag left advances');
assert.equal(indexAfterDrag(1, 4, 300, 1000), 0, 'drag right retreats');

// One drag is one slide however far it travels: a flick must not skip work.
assert.equal(indexAfterDrag(0, 4, -3000, 1000), 1, 'a long drag still moves one');
assert.equal(indexAfterDrag(3, 4, -3000, 1000), 3, 'cannot drag past the last');
assert.equal(indexAfterDrag(0, 4, -300, 0), 0, 'zero width is a no-op, not NaN');

console.log('ok: slides');
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node src/scripts/works/slides.test.mjs`
Expected: FAIL — cannot find module `./slides.ts`

- [ ] **Step 3: Write the implementation**

Create `src/scripts/works/slides.ts`:

```ts
// Slide index maths for the /works carousels. Pure: no DOM, no GSAP, no
// curtains. Everything that moves reads its target from here.

/**
 * Hold an index inside the carousel. The rail deliberately does not wrap —
 * two of the three chapters carry only two projects (spec D9), and a
 * wrapping carousel of two reads as a flicker rather than as navigation.
 */
export const clampIndex = (index: number, count: number): number =>
  count <= 0 ? 0 : Math.min(Math.max(index, 0), count - 1);

/** Whether an arrow in `dir` would actually move. Drives the disabled state. */
export const canGo = (index: number, count: number, dir: -1 | 1): boolean =>
  clampIndex(index + dir, count) !== index;

/**
 * Where a pointer drag lands. `dx` is total travel in px (positive = right),
 * `width` one slide's width. A drag shorter than `threshold` of a slide snaps
 * back; a longer one moves exactly one slide however far it travelled, so a
 * flick cannot skip past a project.
 */
export const indexAfterDrag = (
  index: number,
  count: number,
  dx: number,
  width: number,
  threshold = 0.2,
): number => {
  if (width <= 0) return index;
  const moved = -dx / width;
  const step = Math.abs(moved) < threshold ? 0 : Math.sign(moved);
  return clampIndex(index + step, count);
};
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `node src/scripts/works/slides.test.mjs`
Expected: `ok: slides`

- [ ] **Step 5: Register the test**

In `package.json` `scripts`, after `"test:services"`:

```json
    "test:slides": "node src/scripts/works/slides.test.mjs",
```

- [ ] **Step 6: Commit**

```bash
git add src/scripts/works/slides.ts src/scripts/works/slides.test.mjs package.json
git commit -m "✨ works: slide index maths, and a rail that refuses to wrap"
```

---

## Task 4: Static carousel markup and the page

The page renders and reads correctly with no JavaScript and no WebGL. No motion yet. This is a shippable milestone: `/works` is better than it was before any script loads.

**Files:**
- Create: `src/components/WorkCarousel.astro`
- Rewrite: `src/pages/works.astro`
- Delete: `src/components/WorkChapter.astro`

**Interfaces:**
- Consumes: `worksFor`, `chapters`, `Chapter`, `Work` from Task 1; `ActionPill` from Task 2.
- Produces: DOM contract the later tasks bind to, per chapter root `.carousel[data-carousel]`:
  - `[data-carousel-slide]` — one per project, in order
  - `[data-carousel-plane]` — the `[data-canvas]` element inside a slide
  - `[data-carousel-thumb]` — one per project, in order
  - `[data-carousel-prev]`, `[data-carousel-next]` — the arrows
  - `[data-carousel-status]` — the `aria-live` region
  - `[data-carousel-hint]` — the drag hint

- [ ] **Step 1: Write the component**

Create `src/components/WorkCarousel.astro`. One chapter: label, heading, a stack of slides, arrows, thumb rail.

Slides ship **visible**. `src/scripts/works/carousel.ts` performs the initial collapse in Task 5, exactly as the old tab script did — so with JS off the chapter is a readable linear stack. Slides therefore carry **no** `data-inview`, which hides its element until a script adds `.inview`.

```astro
---
import type { Chapter, Work } from '../data/works';
import ActionPill from '@components/ActionPill.astro';

interface Props {
  chapter: Chapter;
  items: Work[];
}

const { chapter, items } = Astro.props;
const { index, category, heading, intro } = chapter;
---

<section
  class="carousel"
  data-carousel
  aria-labelledby={`ch-${category}`}
  aria-roledescription="carousel"
  role="group"
>
  <header class="carousel__head">
    <p class="label carousel__index">{index} &mdash; {heading}</p>
    <h2 id={`ch-${category}`} class="carousel__heading" data-line-reveal>{heading}</h2>
    <p class="carousel__intro">{intro}</p>
  </header>

  <div class="carousel__stage">
    {
      items.map((w, i) => (
        <article class="slide" data-carousel-slide data-index={i} id={`slide-${w.id}`}>
          {/*
            Deliberately NOT data-canvas. `_base.scss:213` hides the children
            of any [data-canvas] element and relies on `.no-curtains` to put
            them back — so the image starts invisible and WebGL is required to
            reveal it. That inverts the failure mode: reduced motion, a
            skipped plane, a context loss all land on a blank box. Here the
            image is visible by default and planes.ts hides it only once a
            plane is actually drawing. Every failure lands on a visible image.
          */}
          {w.media ? (
            <div class="slide__plane" data-carousel-plane>
              <img
                src={w.media.poster}
                width={w.media.posterWidth}
                height={w.media.posterHeight}
                alt={w.media.alt}
                loading={i === 0 ? 'eager' : 'lazy'}
                decoding="async"
              />
            </div>
          ) : (
            <div class="slide__plane slide__plane--empty">
              <span class="micro">No media yet</span>
            </div>
          )}

          <div class="slide__copy">
            <h3 class="slide__title">{w.title}</h3>
            <p class="slide__summary">{w.summary}</p>
            <p class="slide__meta micro">
              {w.client} &middot; {w.year} &middot; {w.stack.join(', ')}
            </p>
            <div class="slide__actions">
              {w.url && (
                <ActionPill
                  href={w.url}
                  label="View live"
                  icon="arrow-up-right"
                  variant="filled"
                  external={!w.url.startsWith('/')}
                />
              )}
            </div>
          </div>
        </article>
      ))
    }
  </div>

  <!-- Arrows are hidden from the no-JS document: with the script absent every
       slide is already on screen, so there is nothing to page through. -->
  <div class="carousel__arrows" hidden data-carousel-arrows>
    <button class="carousel__arrow pill-btn" type="button" data-carousel-prev>
      <span aria-hidden="true">&larr;</span>
      <span class="visually-hidden">Previous project</span>
    </button>
    <button class="carousel__arrow pill-btn" type="button" data-carousel-next>
      <span aria-hidden="true">&rarr;</span>
      <span class="visually-hidden">Next project</span>
    </button>
  </div>

  <div class="carousel__thumbs" hidden data-carousel-thumbs>
    {
      items.map((w, i) => (
        <button
          class="thumb"
          type="button"
          data-carousel-thumb
          data-index={i}
          aria-current={i === 0 ? 'true' : 'false'}
        >
          {w.media ? (
            <img class="thumb__img" src={w.media.poster} alt="" width="112" height="64" loading="lazy" />
          ) : (
            <span class="thumb__img thumb__img--empty" />
          )}
          <span class="thumb__label micro">{w.title}</span>
        </button>
      ))
    }
  </div>

  <p class="carousel__hint micro" hidden data-carousel-hint>Drag to explore</p>
  <p class="visually-hidden" aria-live="polite" data-carousel-status></p>
</section>

<style lang="scss">
  .carousel {
    position: relative;
    display: flex;
    flex-direction: column;
    gap: clamp-fluid(24, 40);
    max-width: var(--container-max-width);
    margin-inline: auto;
    padding: clamp-fluid(72, 96) var(--grid-margin) clamp-fluid(48, 64);
  }

  .carousel__head {
    display: flex;
    flex-direction: column;
    gap: to-rem(12);
  }

  .carousel__index {
    color: var(--c-mute);
  }

  .carousel__heading {
    margin: 0;
    color: var(--c-ink);
    font-size: var(--fs-3);
    line-height: 1.02;
    letter-spacing: var(--ls-3);
  }

  .carousel__intro {
    max-width: 58ch;
    margin: 0;
    color: var(--c-body);
    line-height: 1.55;
  }

  // No-JS: every slide stacked and readable. The script turns this into a
  // single-slide viewport in Task 5.
  .carousel__stage {
    display: flex;
    flex-direction: column;
    gap: clamp-fluid(48, 72);
  }

  .slide {
    display: grid;
    gap: clamp-fluid(20, 32);
    grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
    align-items: center;

    @media (max-width: 900px) {
      grid-template-columns: 1fr;
    }
  }

  .slide__plane {
    position: relative;
    overflow: hidden;
    aspect-ratio: 16 / 9;
    border-radius: var(--r-sm);
    background-color: var(--c-canvas-card);

    > img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
  }

  // Set by planes.ts only once a plane is confirmed drawing this element.
  // Until then — and forever, if WebGL never comes up — the image is what
  // the visitor sees.
  .slide__plane.is-planed > img {
    opacity: 0;
    visibility: hidden;
  }

  .slide__plane--empty {
    display: grid;
    place-items: center;
    border: 1px solid var(--c-hairline);
    color: var(--c-mute);
  }

  .slide__copy {
    display: flex;
    flex-direction: column;
    gap: to-rem(12);
  }

  .slide__title {
    margin: 0;
    color: var(--c-ink);
    font-size: var(--fs-4);
    line-height: 1.1;
    letter-spacing: var(--ls-4);
  }

  .slide__summary {
    max-width: 52ch;
    margin: 0;
    color: var(--c-body);
    line-height: 1.55;
  }

  .slide__meta {
    margin: 0;
    color: var(--c-mute);
  }

  .slide__actions {
    display: flex;
    flex-wrap: wrap;
    gap: to-rem(8);
    margin-top: to-rem(4);
  }

  .carousel__arrows {
    display: flex;
    gap: to-rem(8);
  }

  .carousel__arrow {
    min-width: to-rem(44);
    padding-inline: var(--sp-lg);

    &[disabled] {
      opacity: 0.35;
      cursor: not-allowed;
    }
  }

  .carousel__thumbs {
    display: flex;
    flex-wrap: wrap;
    gap: to-rem(10);
  }

  .thumb {
    position: relative;
    overflow: hidden;
    width: to-rem(112);
    height: to-rem(64);
    padding: 0;
    cursor: pointer;
    border: 1px solid var(--c-hairline);
    border-radius: var(--r-sm);
    background-color: var(--c-canvas-card);
    // Rest state is dim; the active thumb is full strength AND carries the
    // progress fill AND aria-current — never opacity alone (PRODUCT.md).
    opacity: 0.42;
    transition:
      opacity 0.22s var(--ease-smooth),
      border-color 0.22s var(--ease-smooth);

    &[aria-current='true'] {
      opacity: 1;
      border-color: var(--c-hairline-bright);
    }

    @include has-hover {
      &:hover {
        opacity: 0.8;
      }
    }
  }

  // The reference fills this bar as an autoplay timer elapses. This carousel
  // has no autoplay — it advances only when someone asks it to — so a
  // creeping fill would be animating a number that means nothing. It becomes
  // a plain active rule instead: the second, non-colour carrier of selected
  // state that PRODUCT.md requires alongside opacity.
  .thumb[aria-current='true']::after {
    content: '';
    position: absolute;
    inset: auto 0 0 0;
    z-index: 1;
    height: to-rem(2);
    background-color: var(--c-ink);
  }

  .thumb__img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .thumb__img--empty {
    background-color: var(--c-canvas-soft);
  }

  // The reference sets these at 8px. That fails AA at any contrast, so ours
  // uses --fs-micro and the rail is sized to fit it.
  .thumb__label {
    position: absolute;
    inset: auto 0 0 0;
    padding: to-rem(12) to-rem(6) to-rem(4);
    color: var(--c-ink);
    text-align: left;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    background: linear-gradient(rgba(10, 10, 10, 0), rgba(10, 10, 10, 0.8));
  }

  // The drag hint sways until first interaction, then carousel.ts hides it
  // for good. ±35px over 1.7s, measured off the reference (spec §4).
  .carousel__hint {
    width: fit-content;
    margin: 0;
    color: var(--c-mute);
  }

  @include has-motion {
    .carousel__hint {
      animation: carousel-sway 1.7s var(--ease-smooth) infinite;
    }
  }

  @keyframes carousel-sway {
    0%,
    100% {
      transform: translateX(#{to-rem(-35)});
    }
    50% {
      transform: translateX(#{to-rem(35)});
    }
  }
</style>
```

- [ ] **Step 2: Rewrite the page**

Replace `src/pages/works.astro` entirely. The standalone intro section is folded into the hero (spec §6): with chapters now one screen each, two paragraphs of preamble delay the first exhibit by a full screen. The tab script goes with `WorkChapter`.

```astro
---
import Layout from '@layouts/Layout.astro';
import WorkCarousel from '@components/WorkCarousel.astro';

import { chapters, worksFor } from '../data/works';

// Content lives entirely in src/data/works.ts.
// See docs/superpowers/specs/2026-09-13-works-restructure-design.md.
const sections = chapters.map((chapter) => ({
  chapter,
  items: worksFor(chapter.category),
}));
---

<Layout>
  <main>
    <section class="hero" aria-labelledby="works-mark">
      <p class="hero__index label" data-inview-manual>01 &mdash; Works</p>

      <div class="hero__center">
        <h1 id="works-mark" class="hero__mark" data-inview-manual>Works</h1>
        <p class="hero__tagline" data-inview-manual>
          Creative websites, ERP systems,<br />
          and custom builds. Evidence, not claims.
        </p>
        <p class="hero__body" data-inview-manual>
          Three kinds of work sit here. Sites where the interface carries the
          argument, internal systems built for people who live in them all day,
          and commissioned builds shaped to one operation rather than a
          template.
        </p>
      </div>

      <p class="hero__cue label" data-inview-manual>
        Scroll <span aria-hidden="true">&darr;</span> 2026
      </p>
    </section>

    {
      sections.map(({ chapter, items }) => (
        <WorkCarousel chapter={chapter} items={items} />
      ))
    }

    <section class="container closing" aria-labelledby="closing-heading">
      <h2 id="closing-heading" class="visually-hidden">Contact</h2>
      <p class="closing__body" data-inview>
        More detail on any of these is available on request.
      </p>
      <a class="closing__link label" href="mailto:waiphyoag.cs34@gmail.com" data-inview>
        Get in touch <span aria-hidden="true">&#8599;&#65038;</span>
      </a>
    </section>
  </main>
</Layout>

<style lang="scss">
  // 4rem subtracts the Header's footprint.
  .hero {
    position: relative;
    display: grid;
    grid-template-rows: auto 1fr auto;
    min-height: calc(100svh - 4rem);
    max-width: var(--container-max-width);
    margin-inline: auto;
    padding: to-rem(24) var(--grid-margin) to-rem(40);
  }

  .hero__index {
    color: var(--c-mute);
  }

  .hero__center {
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: clamp-fluid(20, 32);
  }

  .hero__mark {
    margin: 0;
    color: var(--c-ink);
    letter-spacing: -0.02em;
  }

  .hero__tagline {
    max-width: 32ch;
    margin: 0;
    color: var(--c-ink);
    font-size: clamp-fluid(16, 18);
    line-height: 1.56;
    letter-spacing: 0;
  }

  .hero__body {
    max-width: 58ch;
    margin: 0;
    color: var(--c-body);
    line-height: 1.55;
  }

  .hero__cue {
    justify-self: end;
    align-self: end;
    display: inline-flex;
    align-items: center;
    gap: to-rem(8);
    color: var(--c-body);
  }

  .closing {
    margin-block: clamp-fluid(80, 160);
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: to-rem(20);
  }

  .closing__body {
    max-width: 65ch;
    margin: 0;
    color: var(--c-mute);
    line-height: 1.55;
  }

  .closing__link {
    color: var(--c-ink);
    text-decoration: none;
    border-bottom: 1px solid transparent;
    transition: border-color 0.2s var(--ease-smooth);

    @include has-hover {
      &:hover {
        border-bottom-color: var(--c-ink);
      }
    }
  }
</style>
```

- [ ] **Step 3: Delete the superseded component**

```bash
git rm src/components/WorkChapter.astro
```

- [ ] **Step 4: Build**

Run: `yarn build`
Expected: PASS, 0 errors. If `astro check` reports `WorkChapter` still imported, the page rewrite in Step 2 was incomplete.

- [ ] **Step 5: Verify by eye**

Run: `yarn dev`, open `/works`.
Expected: hero, then three chapters, each a vertical stack of every project with poster, title, summary, meta and a View live pill. Arrows, thumbs and hint are absent (they are `hidden`). Nothing moves. This is exactly the no-JS document.

- [ ] **Step 6: Commit**

```bash
git add -A src/components src/pages/works.astro
git commit -m "✨ works: chapters become carousels, starting from the no-JS document"
```

---

## Task 5: Carousel wiring

Turn the stack into a one-slide viewport driven by arrows, thumbs, keyboard and drag. Still no WebGL.

**Files:**
- Create: `src/scripts/works/carousel.ts`
- Modify: `src/pages/works.astro` (add the mounting `<script>`)

**Interfaces:**
- Consumes: `clampIndex`, `canGo`, `indexAfterDrag` from Task 3; the DOM contract from Task 4.
- Produces: `class WorkCarouselController` with `readonly root: HTMLElement`, `readonly slides: HTMLElement[]`, `get index(): number`, `go(next: number): void`, and `onChange(fn: (index: number, slide: HTMLElement) => void): void`. Task 7 subscribes via `onChange` to drive the planes.

- [ ] **Step 1: Write the controller**

Create `src/scripts/works/carousel.ts`:

```ts
// One chapter's carousel. Owns the slide index and nothing else: the plane
// layer (works/planes.ts) subscribes through onChange rather than reading the
// DOM itself, so WebGL can fail without taking navigation with it.
import { clampIndex, canGo, indexAfterDrag } from './slides';

type ChangeFn = (index: number, slide: HTMLElement) => void;

const DRAG_COMMIT = 8; // px before a pointer press counts as a drag, not a click

export class WorkCarouselController {
  readonly root: HTMLElement;
  readonly slides: HTMLElement[];
  private thumbs: HTMLElement[];
  private prev: HTMLButtonElement | null;
  private next: HTMLButtonElement | null;
  private status: HTMLElement | null;
  private hint: HTMLElement | null;
  private listeners: ChangeFn[] = [];
  private i = 0;
  private dragging = false;
  private startX = 0;

  constructor(root: HTMLElement) {
    this.root = root;
    this.slides = Array.from(root.querySelectorAll<HTMLElement>('[data-carousel-slide]'));
    this.thumbs = Array.from(root.querySelectorAll<HTMLElement>('[data-carousel-thumb]'));
    this.prev = root.querySelector('[data-carousel-prev]');
    this.next = root.querySelector('[data-carousel-next]');
    this.status = root.querySelector('[data-carousel-status]');
    this.hint = root.querySelector('[data-carousel-hint]');

    if (this.slides.length === 0) return;

    // The markup ships every slide visible so the page reads without JS.
    // Revealing the controls and collapsing the stack is this script's first
    // act, which means the controls never appear without something to drive.
    this.root.classList.add('is-live');
    root.querySelector('[data-carousel-arrows]')?.removeAttribute('hidden');
    root.querySelector('[data-carousel-thumbs]')?.removeAttribute('hidden');
    // A carousel of one has nothing to drag or page through.
    if (this.slides.length < 2) {
      root.querySelector('[data-carousel-arrows]')?.setAttribute('hidden', '');
      root.querySelector('[data-carousel-thumbs]')?.setAttribute('hidden', '');
    } else {
      this.hint?.removeAttribute('hidden');
    }

    this.bind();
    this.render(true);
  }

  get index() {
    return this.i;
  }

  onChange(fn: ChangeFn) {
    this.listeners.push(fn);
  }

  go(next: number) {
    const target = clampIndex(next, this.slides.length);
    if (target === this.i) return;
    this.i = target;
    this.render(false);
  }

  private bind() {
    this.prev?.addEventListener('click', () => this.go(this.i - 1));
    this.next?.addEventListener('click', () => this.go(this.i + 1));

    this.thumbs.forEach((thumb, i) => {
      thumb.addEventListener('click', () => this.go(i));
    });

    // Arrow keys page the carousel only while focus is inside it, so they
    // never steal the keys from the page.
    this.root.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        this.go(this.i - 1);
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        this.go(this.i + 1);
      }
    });

    // Focus landing on an off-screen slide advances to it, rather than
    // leaving the user tabbing through content they cannot see.
    this.root.addEventListener('focusin', (e) => {
      const slide = (e.target as HTMLElement).closest<HTMLElement>('[data-carousel-slide]');
      if (!slide) return;
      const at = this.slides.indexOf(slide);
      if (at !== -1) this.go(at);
    });

    const stage = this.root.querySelector<HTMLElement>('.carousel__stage');
    if (!stage) return;

    stage.addEventListener('pointerdown', (e) => {
      if (e.pointerType === 'mouse' && e.button !== 0) return;
      this.dragging = true;
      this.startX = e.clientX;
      this.hint?.setAttribute('hidden', '');
    });

    stage.addEventListener('pointerup', (e) => {
      if (!this.dragging) return;
      this.dragging = false;
      const dx = e.clientX - this.startX;
      if (Math.abs(dx) < DRAG_COMMIT) return; // a click, not a drag
      this.go(indexAfterDrag(this.i, this.slides.length, dx, stage.clientWidth));
    });

    stage.addEventListener('pointercancel', () => {
      this.dragging = false;
    });
  }

  private render(initial: boolean) {
    this.slides.forEach((slide, i) => {
      const on = i === this.i;
      slide.classList.toggle('is-active', on);
      // inert keeps off-screen slides out of the tab order without hiding
      // them from the layout the plane layer measures against.
      slide.toggleAttribute('inert', !on);
    });

    this.thumbs.forEach((thumb, i) => {
      thumb.setAttribute('aria-current', String(i === this.i));
    });

    if (this.prev) this.prev.disabled = !canGo(this.i, this.slides.length, -1);
    if (this.next) this.next.disabled = !canGo(this.i, this.slides.length, 1);

    // Silent on first render: announcing "Project 1 of 4" the moment the page
    // loads is noise, not navigation.
    if (!initial && this.status) {
      this.status.textContent = `Project ${this.i + 1} of ${this.slides.length}`;
    }

    this.listeners.forEach((fn) => fn(this.i, this.slides[this.i]));
  }
}

export const mountCarousels = (): WorkCarouselController[] =>
  Array.from(document.querySelectorAll<HTMLElement>('[data-carousel]')).map(
    (root) => new WorkCarouselController(root),
  );
```

- [ ] **Step 2: Add the live-mode styles**

Append to the `<style>` block in `src/components/WorkCarousel.astro`:

```scss
  // Live mode: the script has run, so the stack becomes a one-slide viewport.
  // Everything in this block is scoped to .is-live, which means the no-JS
  // document above is untouched by it.
  .carousel.is-live {
    .carousel__stage {
      display: grid;
      gap: 0;
    }

    .slide {
      // All slides share one cell; only the active one is visible. Laying
      // them out rather than display:none keeps the plane layer able to
      // measure a slide before it is shown.
      grid-area: 1 / 1;
      opacity: 0;
      visibility: hidden;
      transition:
        opacity 0.5s var(--ease-out-expo),
        visibility 0s linear 0.5s;
    }

    .slide.is-active {
      opacity: 1;
      visibility: visible;
      transition:
        opacity 0.5s var(--ease-out-expo),
        visibility 0s;
    }

    .carousel__stage {
      touch-action: pan-y;
      cursor: grab;
    }

    .carousel__stage:active {
      cursor: grabbing;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .carousel.is-live .slide {
      transition: none;
    }
  }
```

- [ ] **Step 3: Mount it**

Append to `src/pages/works.astro`, after the `</Layout>` tag and before the `<style>` block:

```astro
<script>
  import { mountCarousels } from '../scripts/works/carousel';

  mountCarousels();
</script>
```

- [ ] **Step 4: Build**

Run: `yarn build`
Expected: PASS, 0 errors.

- [ ] **Step 5: Verify by hand**

Run: `yarn dev`, open `/works`. Check every one of these:

- Arrows page through each chapter; the Previous arrow is disabled on slide 1 and Next on the last.
- Thumbs jump to their slide and the active one shows full-strength with a border.
- Tab into a chapter, then Left/Right arrow keys page it.
- Tabbing forward from the last control of slide 1 advances the carousel rather than reaching an invisible slide.
- Drag left/right on the stage commits at roughly a fifth of the width and snaps back below it.
- A short click on the stage does not change slide.
- With DevTools emulating reduced motion, slides swap instantly.
- Disable JavaScript and reload: the linear stack returns, with no arrows or thumbs.

- [ ] **Step 6: Commit**

```bash
git add src/scripts/works/carousel.ts src/components/WorkCarousel.astro src/pages/works.astro
git commit -m "✨ works: arrows, thumbs, keys and drag page each chapter"
```

---

## Task 6: Line reveal

Chapter headings arrive line by line from behind a mask.

**Files:**
- Create: `src/scripts/works/lineReveal.ts`
- Modify: `src/pages/works.astro` (mount), `src/components/WorkCarousel.astro` (mask styles)

**Interfaces:**
- Consumes: `[data-line-reveal]` from Task 4's markup.
- Produces: `mountLineReveals(): void`.

- [ ] **Step 1: Write the module**

Create `src/scripts/works/lineReveal.ts`:

```ts
// Heading reveal: split to lines, mask each, translate them up on a stagger.
// Mechanism from stylized.cortiz.dev (spec §7.3), which wraps each line in an
// overflow-hidden box with a little bottom padding so descenders are not
// clipped by the mask.
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { SplitText } from 'gsap/SplitText';

gsap.registerPlugin(ScrollTrigger, SplitText);

export const mountLineReveals = () => {
  // Reduced motion keeps the text exactly as the server rendered it: no
  // split, no mask, no trigger. Splitting and then not animating would still
  // rewrite the DOM for a reader who asked for none of it.
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  const targets = gsap.utils.toArray<HTMLElement>('[data-line-reveal]');

  targets.forEach((el) => {
    const split = new SplitText(el, {
      type: 'lines',
      linesClass: 'reveal-line',
      // Each line gets its own mask element, which is what we translate
      // against. Without this the lines slide over one another.
      mask: 'lines',
    });

    gsap.from(split.lines, {
      yPercent: 110,
      duration: 0.9,
      ease: 'expo.out',
      stagger: 0.08,
      scrollTrigger: {
        trigger: el,
        start: 'top 85%',
        once: true,
      },
    });
  });
};
```

- [ ] **Step 2: Add the mask padding**

Append to the `<style>` block in `src/components/WorkCarousel.astro`. It must not be scoped to `.is-live`: `SplitText` injects these elements at runtime, and Astro's scoped styles need the class present in the component's own stylesheet to emit it.

```scss
  // SplitText's mask wrapper. The bottom padding stops the mask clipping
  // descenders on the final line (spec §4: the reference uses .09em).
  :global(.reveal-line) {
    padding-bottom: 0.09em;
  }
```

- [ ] **Step 3: Mount it**

In the `<script>` block of `src/pages/works.astro`:

```astro
<script>
  import { mountCarousels } from '../scripts/works/carousel';
  import { mountLineReveals } from '../scripts/works/lineReveal';

  mountCarousels();
  mountLineReveals();
</script>
```

- [ ] **Step 4: Build**

Run: `yarn build`
Expected: PASS, 0 errors. If `astro check` cannot resolve `gsap/SplitText`, confirm the import path matches the one already used in `src/scripts/workTransition.ts`.

- [ ] **Step 5: Verify**

Run: `yarn dev`, open `/works`, scroll to each chapter.
Expected: the heading rises line by line from a hard edge; no descender is clipped; it fires once and does not replay on scroll back. Under emulated reduced motion the heading is simply present, and inspecting it shows no `.reveal-line` wrappers in the DOM at all.

- [ ] **Step 6: Commit**

```bash
git add src/scripts/works/lineReveal.ts src/components/WorkCarousel.astro src/pages/works.astro
git commit -m "✨ works: chapter headings rise from behind a mask"
```

---

## Task 7: Plane layer

Texture the active slide onto a curtains.js plane that bulges under drag and scroll velocity.

`src/components/Canvas.astro` currently creates one global full-screen instance, binds every `[data-canvas]` on the page at load, and never disposes anything. That is wrong for this page on two counts: planes must be created per chapter (spec D7's texture budget) and disposed at boundaries. This task refactors it to expose a registry rather than doing the binding itself.

**Files:**
- Create: `src/shader/carousel.vert.glsl`, `src/shader/carousel.frag.glsl`
- Create: `src/scripts/works/planes.ts`
- Modify: `src/components/Canvas.astro`
- Modify: `src/pages/works.astro` (mount)

**Interfaces:**
- Consumes: `WorkCarouselController.onChange` from Task 5; `[data-carousel-plane]` from Task 4.
- Produces:
  - From `Canvas.astro`: `window.__curtains` typed as `Curtains | null`, set once the context is live and left `null` on `onError`.
  - From `planes.ts`: `mountPlanes(controllers: WorkCarouselController[]): void`, and `disposeChapter(root: HTMLElement): void` which Task 8 calls at boundaries.

- [ ] **Step 1: Write the shaders**

Create `src/shader/carousel.vert.glsl`:

```glsl
precision mediump float;

#define PI 3.14159265359

attribute vec3 aVertexPosition;
attribute vec2 aTextureCoord;

uniform mat4 uMVMatrix;
uniform mat4 uPMatrix;
uniform mat4 uTextureMatrix0;

uniform float uTime;
// Signed travel, roughly -1..1. Drag and scroll both write it.
uniform float uVelocity;

varying vec3 vVertexPosition;
varying vec2 vTextureCoord;

void main() {
  vec3 p = aVertexPosition;

  // A centre-weighted bulge that relaxes to nothing at the edges, so the
  // plane never tears away from the rectangle the DOM reserved for it.
  float falloff = cos(p.x * PI * 0.5) * cos(p.y * PI * 0.5);

  // At rest the plane breathes almost imperceptibly; under travel it leans.
  p.z += falloff * (0.012 * sin(uTime * 0.01) + uVelocity * 0.28);
  p.x += falloff * uVelocity * 0.06;

  gl_Position = uPMatrix * uMVMatrix * vec4(p, 1.0);

  vVertexPosition = p;
  vTextureCoord = (uTextureMatrix0 * vec4(aTextureCoord, 0.0, 1.0)).xy;
}
```

Create `src/shader/carousel.frag.glsl`:

```glsl
precision mediump float;

uniform sampler2D uSampler0;
uniform float uVelocity;

varying vec3 vVertexPosition;
varying vec2 vTextureCoord;

void main() {
  // A slight horizontal smear in the direction of travel. Three taps, not a
  // loop: this runs per pixel on every frame of a drag.
  float smear = uVelocity * 0.012;
  vec4 a = texture2D(uSampler0, vTextureCoord + vec2(smear, 0.0));
  vec4 b = texture2D(uSampler0, vTextureCoord);
  vec4 c = texture2D(uSampler0, vTextureCoord - vec2(smear, 0.0));

  gl_FragColor = (a + b + c) / 3.0;
}
```

- [ ] **Step 2: Publish the curtains instance**

`Canvas.astro` keeps creating the global context and binding its background planes. Its `[data-canvas]` query needs no change — Task 4's slides deliberately do not carry that attribute, so the global pass never sees them. The only change is publishing the instance so the carousel layer can attach to the same context rather than standing up a second WebGL canvas.

Inside the `load` handler, after the `onError`/`onContextLost` chain:

```ts
    // Published so the carousel plane layer can attach to the same context
    // rather than standing up a second WebGL canvas. Stays null if the
    // context never came up, which is the same signal as .no-curtains.
    window.__curtains = curtains;
```

And declare it. Add to `src/env.d.ts`:

```ts
import type { Curtains } from 'curtainsjs';

declare global {
  interface Window {
    __curtains: Curtains | null;
  }
}
```

- [ ] **Step 3: Write the plane layer**

Create `src/scripts/works/planes.ts`:

```ts
// Curtains planes for the /works carousels.
//
// Budget (spec D7): textures cap at 1600x900 and planes exist only for the
// chapter in view plus one lookahead. Eight simultaneous 2048x1152 RGBA
// textures is ~75MB of VRAM, which is not safe on mid-range mobile.
//
// Films are never textured. A video texture re-uploads every frame and costs
// more than the effect returns; the plane carries the poster and the film
// plays in a DOM <video> above the canvas.
import { Plane } from 'curtainsjs';
import type { PlaneParams } from 'curtainsjs';
import { gsap } from 'gsap';
import { lenis } from '../scroll';
import type { WorkCarouselController } from './carousel';
import vertexShader from '../../shader/carousel.vert.glsl';
import fragmentShader from '../../shader/carousel.frag.glsl';

const params: PlaneParams = {
  vertexShader,
  fragmentShader,
  // The bulge needs vertices to bend. 40x40 is enough for a smooth curve at
  // this size; Canvas.astro's background plane runs 100x100 because it is
  // full-screen.
  widthSegments: 40,
  heightSegments: 40,
  transparent: true,
  uniforms: {
    time: { name: 'uTime', type: '1f', value: 0 },
    velocity: { name: 'uVelocity', type: '1f', value: 0 },
  },
};

const chapters = new Map<HTMLElement, Plane[]>();
let velocity = 0;

export const disposeChapter = (root: HTMLElement) => {
  const planes = chapters.get(root);
  if (!planes) return;
  planes.forEach((plane) => plane.remove());
  chapters.delete(root);
  // Hand the element back to its <img>. Disposing without this leaves a blank
  // box where a poster should be.
  root
    .querySelectorAll<HTMLElement>('[data-carousel-plane]')
    .forEach((el) => el.classList.remove('is-planed'));
};

const createChapter = (root: HTMLElement) => {
  const curtains = window.__curtains;
  if (!curtains || chapters.has(root)) return;

  const planes = Array.from(root.querySelectorAll<HTMLElement>('[data-carousel-plane]')).map(
    (el) => {
      const plane = new Plane(curtains, el, params);
      plane.onRender(() => {
        plane.uniforms.time.value = (plane.uniforms.time.value as number) + 1;
        plane.uniforms.velocity.value = velocity;
      });
      // Hide the <img> only once its plane is confirmed ready. Before this
      // fires — and if it never fires — the poster is what shows.
      plane.onReady(() => el.classList.add('is-planed'));
      return plane;
    },
  );

  chapters.set(root, planes);
};

export const mountPlanes = (controllers: WorkCarouselController[]) => {
  if (!window.__curtains) return; // no WebGL: .no-curtains already showed the imgs
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  // Scroll velocity, normalised and decayed. Lenis reports px/frame; 60 is
  // about the fastest a real scroll goes, so it maps to roughly -1..1.
  lenis.on('scroll', ({ velocity: v }: { velocity: number }) => {
    velocity = gsap.utils.clamp(-1, 1, v / 60);
  });

  gsap.ticker.add(() => {
    // Relax toward rest every frame, so the plane settles when nothing moves.
    velocity *= 0.92;
  });

  controllers.forEach((controller, i) => {
    // Budget (D7): only the first chapter is planed at mount. The curtain's
    // boundary triggers create and dispose the rest as they come into view,
    // so the resident set never exceeds two chapters.
    if (i === 0) createChapter(controller.root);

    controller.onChange(() => {
      // A slide change re-measures: curtains positions a plane from its
      // element's box, and the outgoing slide's box is about to change.
      chapters.get(controller.root)?.forEach((plane) => plane.updatePosition());
    });
  });
};

export const createChapterPlanes = createChapter;
```

- [ ] **Step 4: Mount it**

In `src/pages/works.astro`'s `<script>`:

```astro
<script>
  import { mountCarousels } from '../scripts/works/carousel';
  import { mountLineReveals } from '../scripts/works/lineReveal';
  import { mountPlanes } from '../scripts/works/planes';

  const carousels = mountCarousels();
  mountLineReveals();
  // Planes attach to the context Canvas.astro publishes on load, so this
  // waits for that same event rather than racing it.
  window.addEventListener('load', () => mountPlanes(carousels));
</script>
```

- [ ] **Step 5: Build**

Run: `yarn build`
Expected: PASS, 0 errors. If `astro check` cannot resolve the `.glsl` imports, confirm `src/env.d.ts` has a `*.glsl` module declaration — `vite-plugin-glsl` needs one for TypeScript. Add it if missing:

```ts
declare module '*.glsl' {
  const value: string;
  export default value;
}
```

- [ ] **Step 6: Verify**

Run: `yarn dev`, open `/works`.

- Chapter 02's active slide renders through the canvas and bulges slightly while scrolling, settling when still.
- Drag a carousel: the plane leans into the direction of travel and relaxes.
- Chapters 03 and 04 show plain `<img>` posters at this point — their planes are the curtain's job in Task 8, and they must look correct without them.
- In DevTools, run `window.__curtains = null` then reload: every poster renders as a flat image and the carousels still page correctly.
- Under emulated reduced motion, no plane is created and every poster renders as a flat image. **This is the case `_base.scss:213` would have broken** — confirm no slide is a blank box.
- Open the Memory tab, page through all three chapters twice, and confirm the plane count is not growing.

- [ ] **Step 7: Commit**

```bash
git add src/shader src/scripts/works/planes.ts src/components/Canvas.astro src/env.d.ts src/pages/works.astro
git commit -m "✨ works: slides ride a curtains plane that leans into the drag"
```

---

## Task 8: The curtain

A wipe at each chapter boundary, and the plane lifecycle that hangs off it.

**Files:**
- Create: `src/components/PageCurtain.astro`, `src/scripts/works/curtain.ts`
- Modify: `src/pages/works.astro`

**Interfaces:**
- Consumes: `disposeChapter`, `createChapterPlanes` from Task 7.
- Produces: `mountCurtain(roots: HTMLElement[]): void`.

- [ ] **Step 1: Write the component**

Create `src/components/PageCurtain.astro`.

**Deliberate simplification against spec §4/§7.1.** The reference's curtain is a sheet *plus* its own WebGL canvas, and the spec records it that way. This ships the sheet alone. The sheet is what actually carries the transition — the reference puts it there precisely so the wipe still reads without WebGL — and the canvas is a shader flourish on top of a mechanism that has to work first. Proving the boundary lifecycle (Step 2's plane create/dispose) is the hard part and the canvas would obscure whether it is correct. Add the shader pass afterwards if the plain sweep reads flat; the layer is already in place for it.

```astro
---
// The chapter-boundary curtain. Purely decorative and never interactive:
// pointer-events are off and the whole layer is hidden from assistive tech.
---

<div class="curtain" aria-hidden="true" data-curtain>
  <div class="curtain__sheet" data-curtain-sheet></div>
</div>

<style lang="scss">
  .curtain {
    position: fixed;
    inset: 0;
    // Above the page, below the sticky header (10) so the header never
    // disappears mid-transition.
    z-index: 9;
    pointer-events: none;
  }

  .curtain__sheet {
    position: absolute;
    inset: 0;
    background-color: var(--c-canvas);
    // Parked below the fold; the timeline drives it up and away.
    transform: translateY(100%);
    will-change: transform;
  }
</style>
```

- [ ] **Step 2: Write the controller**

Create `src/scripts/works/curtain.ts`:

```ts
// Chapter-boundary curtain.
//
// Positions are computed off the chapter stack, not off a chapter's own box.
// A pinned or sticky element moves under ScrollTrigger and its
// getBoundingClientRect cannot be trusted as a trigger reference.
//
// ScrollTriggers are attached to top-level animations only, never nested in a
// parent timeline — that is unsupported and silently misbehaves.
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { disposeChapter, createChapterPlanes } from './planes';

gsap.registerPlugin(ScrollTrigger);

export const mountCurtain = (roots: HTMLElement[]) => {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  if (roots.length < 2) return;

  const sheet = document.querySelector<HTMLElement>('[data-curtain-sheet]');
  if (!sheet) return;

  roots.forEach((root, i) => {
    if (i === 0) return;

    const prev = roots[i - 1];

    gsap
      .timeline({
        scrollTrigger: {
          trigger: root,
          start: 'top bottom',
          end: 'top top',
          scrub: true,
          invalidateOnRefresh: true,

          // Teardown hangs off onLeave/onLeaveBack, never onUpdate. A scrub
          // trigger has no onComplete: progress is scroll-bound, so there is
          // no natural end to hang it on. Disposing on update would tear the
          // outgoing chapter mid-wipe.
          onLeave: () => {
            disposeChapter(prev);
            createChapterPlanes(root);
          },
          onLeaveBack: () => {
            disposeChapter(root);
            createChapterPlanes(prev);
          },
          onEnter: () => createChapterPlanes(root),
          onEnterBack: () => createChapterPlanes(prev),
        },
      })
      // The sheet sweeps up across the boundary and off the top, so one
      // chapter is replaced rather than cross-faded.
      .fromTo(
        sheet,
        { yPercent: 100 },
        { yPercent: 0, ease: 'none', duration: 0.5 },
      )
      .to(sheet, { yPercent: -100, ease: 'none', duration: 0.5 });
  });

  // dvh changes when the mobile URL bar collapses, which moves every
  // boundary. Refresh on resize, debounced — never on scroll.
  let timer = 0;
  window.addEventListener('resize', () => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => ScrollTrigger.refresh(), 200);
  });
};
```

- [ ] **Step 3: Mount it**

In `src/pages/works.astro`, import the component and render it as the last child of `<main>`:

```astro
import PageCurtain from '@components/PageCurtain.astro';
```

```astro
    <PageCurtain />
  </main>
```

And in the `<script>`:

```astro
<script>
  import { mountCarousels } from '../scripts/works/carousel';
  import { mountLineReveals } from '../scripts/works/lineReveal';
  import { mountPlanes } from '../scripts/works/planes';
  import { mountCurtain } from '../scripts/works/curtain';

  const carousels = mountCarousels();
  mountLineReveals();
  window.addEventListener('load', () => {
    mountPlanes(carousels);
    mountCurtain(carousels.map((c) => c.root));
  });
</script>
```

- [ ] **Step 4: Build**

Run: `yarn build`
Expected: PASS, 0 errors.

- [ ] **Step 5: Verify**

Run: `yarn dev`, open `/works`.

- Scrolling from chapter 02 into 03 sweeps a solid panel up across the viewport and off the top; the same in reverse scrolling back.
- The sticky header stays visible throughout.
- Emulate a mobile device and scroll so the URL bar collapses; boundaries stay aligned with the chapters.
- Open DevTools Performance, record a boundary crossing at 1440×900, and confirm it holds 60fps. If it does not, drop `widthSegments`/`heightSegments` in `planes.ts` from 40 to 20 and re-record.
- Under emulated reduced motion, no curtain appears and chapters follow one another as a plain stack.

- [ ] **Step 6: Commit**

```bash
git add src/components/PageCurtain.astro src/scripts/works/curtain.ts src/pages/works.astro
git commit -m "✨ works: a curtain sweeps each chapter boundary"
```

---

## Task 9: Detail overlay

Clicking a slide opens the same overlay Selected Work uses. Extracted to a component so both pages share one copy.

**Files:**
- Create: `src/components/WorkDetail.astro`
- Modify: `src/pages/index.astro`, `src/pages/works.astro`, `src/components/WorkCarousel.astro`

**Interfaces:**
- Consumes: `WorkTransition` from `src/scripts/workTransition.ts`, whose constructor takes `{ items: HTMLElement[]; img: string; overlay: HTMLElement }`.
- Produces: `<WorkDetail items={Work[]} />`, rendering the existing `.work-detail` markup unchanged.

- [ ] **Step 1: Extract the component**

Create `src/components/WorkDetail.astro`. Move, **verbatim and without edits**:

- the markup at `src/pages/index.astro:749-835` (the comment block through the closing `</div>` of `.work-detail`)
- every `.work-detail*` rule and the `@keyframes work-detail-screen-in` block from `src/pages/index.astro:1885-2120`

Give it this frontmatter, replacing the page's local `gallery` reference with a prop:

```astro
---
// The overlay a work card expands into (src/scripts/workTransition.ts).
// Shared by Selected Work on the home page and by the /works carousels.
//
// Must sit outside any element that transforms on exit — a transformed
// ancestor becomes the containing block for a fixed child and traps it.
// data-lenis-prevent lets the column scroll natively while Lenis is frozen.
import type { Work } from '../data/works';

interface Props {
  /** Groups render in this order; WorkTransition matches them by index. */
  items: Work[];
}

const { items } = Astro.props;
---
```

Then in the moved markup, change `gallery.map(` to `items.map(`. Nothing else changes.

- [ ] **Step 2: Use it on the home page**

In `src/pages/index.astro`, delete the markup and styles you moved, then import and render in their place:

```astro
import WorkDetail from '@components/WorkDetail.astro';
```

```astro
    <WorkDetail items={gallery} />
```

Leave the `<script>` that constructs `WorkTransition` exactly where it is — it queries `.work-detail` from the document and does not care which component rendered it.

- [ ] **Step 3: Verify the extraction changed nothing**

Run: `yarn build`
Expected: PASS, 0 errors.

Run: `yarn dev`, open `/`. Click a Selected Work card.
Expected: the overlay behaves exactly as before — image morphs, copy reveals, Back and Esc reverse it, the screens strip scrolls. **Any visual difference means the move was not verbatim.** Compare against `git stash` if unsure.

- [ ] **Step 4: Commit the extraction on its own**

Committing separately keeps the pure move reviewable apart from the new wiring.

```bash
git add src/components/WorkDetail.astro src/pages/index.astro
git commit -m "♻️ work-detail: extract the overlay so /works can share it"
```

- [ ] **Step 5: Make slides open it**

In `src/components/WorkCarousel.astro`, add the trigger inside `.slide__actions`, before the `View live` pill:

```astro
              <button class="slide__open pill-btn" type="button" data-work-open>
                Details
              </button>
```

And give the plane the class `WorkTransition` morphs from. Change the media wrapper's `<img>` to carry it:

```astro
              <img
                class="slide__img"
                src={w.media.poster}
```

- [ ] **Step 6: Wire it on the page**

In `src/pages/works.astro`, render the overlay after the chapters and before `<PageCurtain />`:

```astro
    <WorkDetail items={sections.flatMap(({ items }) => items)} />
    <PageCurtain />
```

with `import WorkDetail from '@components/WorkDetail.astro';` at the top. Then in the `<script>`:

```astro
  import { WorkTransition } from '../scripts/workTransition';

  const overlay = document.querySelector<HTMLElement>('.work-detail');
  if (overlay) {
    new WorkTransition({
      // Order must match the order WorkDetail rendered its groups in, which
      // is the flattened chapter order above — WorkTransition pairs them by
      // index, not by id.
      items: Array.from(document.querySelectorAll<HTMLElement>('[data-carousel-slide]')),
      img: '.slide__img',
      overlay,
    });
  }
```

- [ ] **Step 7: Build**

Run: `yarn build`
Expected: PASS, 0 errors.

- [ ] **Step 8: Verify**

Run: `yarn dev`, open `/works`.

- Clicking Details on any slide morphs its poster into the overlay preview and reveals the copy.
- Back and Esc reverse it, and focus returns to the slide.
- Kage, which has no media, does not break the overlay — it opens with the empty panel.
- Dragging a slide does not trigger the overlay (Task 5's `DRAG_COMMIT` guard).
- Tab to Details and press Enter: the same transition runs.

- [ ] **Step 9: Commit**

```bash
git add src/pages/works.astro src/components/WorkCarousel.astro
git commit -m "✨ works: a slide expands into the detail overlay"
```

---

## Task 10: Documentation and final verification

**Files:**
- Modify: `docs/works-page-design.md`, `package.json`

- [ ] **Step 1: Mark the old design doc superseded**

Replace the header of `docs/works-page-design.md`:

```markdown
# Works Page — Design

Status: approved 2026-09-04. Produced through the `brainstorming` skill.
Reference studied: `https://openai.com/index/gpt-6-astra/` (layout only).
```

with:

```markdown
# Works Page — Design (SUPERSEDED)

> **Superseded 2026-09-13** by
> `docs/superpowers/specs/2026-09-13-works-restructure-design.md`.
>
> Kept for its decision log, which records why the page was built the way it
> was. Everything below describes a page that no longer exists: the tab
> switcher is gone (that spec's D5), the home-only split is gone (D9), and the
> colour, type and square-corner decisions were written against a previous
> `DESIGN.md` — the system is now the near-black / Inter 400 / pill
> interpretation recorded there.

Status: superseded. Originally approved 2026-09-04.
Reference studied: `https://openai.com/index/gpt-6-astra/` (layout only).
```

- [ ] **Step 2: Run every test**

```bash
node src/data/works.test.mjs
node src/scripts/works/slides.test.mjs
yarn build
```

Expected: all pass, `astro check` reports 0 errors.

- [ ] **Step 3: Run the spec's verification checklist**

From spec §11, per chapter:

- Keyboard through every slide; focus never lands off-screen.
- JavaScript disabled: every project readable as a linear stack.
- `document.body.classList.add('no-curtains')`: every project readable as images.
- `prefers-reduced-motion: reduce`: no curtain, no warp, no split.
- Throttled mobile profile: no VRAM growth across all three boundaries.

Record any failure as a fix before committing, not as a follow-up.

- [ ] **Step 4: Commit**

```bash
git add docs/works-page-design.md package.json
git commit -m "📝 works: retire the superseded design doc"
```

---

## Open, deliberately

Two items the spec records as content problems rather than implementation ones. Neither blocks this plan; both change what the finished page looks like.

1. **Posters are 16:9 web captures**, sized for the previous design's bounded 1024px column. On a full-viewport plane they read as screenshots. The fix is the spec's D8 intake, not code.
2. **Chapters 03 and 04 carry two projects each.** Task 5 makes the chrome degrade honestly at n=2 — arrows disable at the ends, the rail shows exactly two. A third project in each would do more for the page than anything in Tasks 6–8.
