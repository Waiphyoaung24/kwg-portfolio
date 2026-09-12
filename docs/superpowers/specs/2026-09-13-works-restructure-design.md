# Works Restructure — Design

Status: approved 2026-09-13. Produced through the `brainstorming` skill.
Supersedes: `docs/works-page-design.md` (written against the previous
Lamborghini-dark system; its colour, type and tab decisions no longer hold).

Reference studied: `https://stylized.cortiz.dev/` — the live site, measured in
a real browser. **Not** `github.com/cortiz2894/stylized-components`, whose
`main` is behind the deployed site (see D1).

---

## 1. Understanding Summary

- `/works` is restructured from a linear document with three tab groups into a
  scroll-driven exhibit: one full-viewport screen per chapter, each carrying a
  WebGL carousel of that chapter's projects, with a curtain transition at every
  chapter boundary.
- **Motion is ported; styling is not.** The reference's mechanics are adopted
  wholesale. Its palette, typefaces, weights and shadows are not. `DESIGN.md`
  is unamended by this work.
- Content still lives entirely in `src/data/works.ts`. Adding a project stays a
  one-file edit.
- The WebGL layer is existing infrastructure (`src/components/Canvas.astro`),
  not new capability.

## 2. Non-Goals

- No DESIGN.md amendment. No light sections, no new typeface, no shadows.
- No React, no React Three Fiber, no new npm dependency.
- No CMS, no API route, no database. The `/vault` surface is untouched.
- No restyle of Home, Services, About, or Catalog.
- No pixel-fidelity target against the reference.
- No change to `src/pages/index.astro`'s Selected Work section.

## 3. Assumptions

| # | Assumption | Basis |
|---|---|---|
| A1 | No new dependency: `gsap`, `lenis`, `curtainsjs`, `three` and `sharp` are already in `package.json` | verified |
| A2 | `vite-plugin-glsl` is configured, so `.glsl` imports resolve | `astro.config.mjs:7,47` |
| A3 | Lenis already drives `ScrollTrigger.update` on the GSAP ticker with `lagSmoothing(0)` | `src/scripts/scroll.ts` |
| A4 | `Canvas.astro` is already mounted globally and binds planes to `[data-canvas]` | `src/layouts/Layout.astro:8` |
| A5 | A WebGL failure path already exists: `onError` sets `.no-curtains`, which reveals the DOM image | `Canvas.astro`, `_base.scss:213-232` |
| A6 | `workTransition.ts` (Flip + SplitText) is shipping and reusable for the detail view | `src/pages/index.astro:914` |
| A7 | WCAG 2.2 AA is the floor; `--c-mute` is metadata only | `PRODUCT.md` |
| A8 | All motion gates on `prefers-reduced-motion` | `PRODUCT.md` |
| A9 | The exhibit currently holds 9 entries, of which **4 are real and 5 are `TODO —` placeholders** | `src/data/works.ts`, audited |
| A10 | A further 4 real, fully-mediated projects are marked `homeOnly` and excluded from the exhibit | `src/data/works.ts` |

## 4. Measured Reference Values

Read off the live site at a 1440×900 viewport via Playwright. These numbers are
the only thing carried over; every colour, face and weight below them is
replaced by our own token.

### Curtain (`PageCurtain`)

| Property | Measured |
|---|---|
| Layer | `position: fixed; inset: 0; z-index: 10040; pointer-events: none` |
| Composition | an opaque sheet **plus** its own `<canvas>` at `opacity: 0` |

The sheet covers instantly; the canvas is what animates. The sheet exists so
the transition still reads if WebGL is unavailable.

### Carousel (`HomeCarousel`)

| Property | Measured |
|---|---|
| Root | `height: 100dvh; overflow: hidden`, with `--footer-h: 58px` (54 below 720px) |
| Mast | `top: 34px; left: 40px` — 22/22 below 900px |
| Title | `clamp(30px, 4.4vw, 58px)`, `line-height: 1`, `letter-spacing: -0.005em` |
| Description | mono 12px, `line-height: 1.65`, `letter-spacing: 0.02em`, `max-width: 58ch` |
| Info block | `bottom: calc(var(--footer-h) + 40px)`, `width: min(680px, 100vw - 48px)` |
| Arrows | `right: 40px; top: 50%`, column, `gap: 12px`, `opacity: .8` |
| Thumbs | `right: 40px`, `gap: 10px`; each `112×64`, `border-radius: 10px`, 1px border |
| Thumb opacity | `.42` rest → `.8` hover → `1` active |
| Thumb progress | `::after { width: calc(var(--slide-progress) * 100%); opacity: .3 }` |
| Thumb label | mono **8px**, `letter-spacing: .1em`, on a transparent→black gradient |
| Line mask | `.hcLine { padding-bottom: .08em; overflow: hidden }` |
| Drag hint | `±35px` sway, `1.7s ease-out` infinite |
| Mobile ≤900px | thumbs centre (`right: 50%; transform: translate(50%)`), shrink to `78×46`, labels hidden |

### Section kit (`SectionType`)

| Property | Measured |
|---|---|
| Eyebrow | mono 10px, `letter-spacing: .22em`, uppercase, on a solid chip `padding: 7px 14px 6px` |
| Title | `clamp(38px, 6.4vw, 88px)`, `line-height: .94`, `letter-spacing: -0.01em`, uppercase |
| Line mask | `.sectionTitleLine { padding-bottom: .09em; overflow: hidden }`, wrapping per-character `<div>`s |
| Body | mono 13px, `line-height: 1.8`, `letter-spacing: .015em` |
| Spec grid | 3 columns, `gap: clamp(20px, 3vw, 44px)`; 1 column ≤900px |
| Spec rule | 1px `linear-gradient(90deg, ink 0, ink 26px, ink/.16 26px)` — a hairline with a ticked head |

### Pill (`ActionButton`)

| Property | Measured |
|---|---|
| Shape | `height: 46px`, `border-radius: 999px`, `padding: 0 5px 0 22px`, `gap: 14px` |
| Label | mono 11px, `letter-spacing: .12em`, uppercase |
| Badge | `36×36`, circular, `overflow: hidden`, `display: grid; place-items: center` |
| Icons | **two**, both at `grid-area: 1/1`; clone parks at `translate(-250%)` |
| Hover | first icon → `translate(250%)`, clone → `translate(0)`; button → `scale(1.1)` |
| Easings | `--btn-ease: cubic-bezier(.22,.68,0,1)`, `--btn-icon-ease: cubic-bezier(.22,.68,0,1.5)` |
| Duration | `.5s` on every channel |
| Reduced motion | every transition and transform nulled; clone stays parked |

## 5. Decision Log

### D1 — Which reference

**Decided:** measure the live site. Ignore the public repo's landing page.

**Finding:** `cortiz2894/stylized-components` `main` is at `c0c02c4`
(2026-08-20); its three other remote branches are all shader feature branches.
The repo's `src/app/page.tsx` is a static CSS card grid, and `gsap` sits in
`package.json` **unimported anywhere in `src/`**. The redesign at
`stylized.cortiz.dev` has never been pushed.

**Consequence:** "exact style from the repo" would have delivered the previous
design. The owner confirmed the live site is the target.

**Also noted:** the React / R3F stack is not why the motion could not be
copied. R3F powers the *demos* (grass, water, Kuwahara post-processing), not
the site chrome. The chrome is CSS modules plus WebGL canvases, and every
mechanism in it has a vanilla equivalent already installed here.

### D2 — How far the port goes

**Decided:** motion and layout mechanics only, rendered in our own system.

**Alternatives:** (a) adopt the reference's visual language on `/works` alone;
(b) rewrite `DESIGN.md` around it site-wide.

**Why:** the reference breaks four explicit `DESIGN.md` Don'ts — three of its
four screens are cream (`Don't introduce a light-mode counterpart`), its
display face is a single ultra-bold condensed and its mono runs at 600
(`Weight 400 is the entire scale`), its pills carry
`box-shadow: 0 10px 26px` (`Hairline borders carry elevation`), and
Anton-uppercase-on-cream is a poster register against PRODUCT.md's
"research lab announcing its work". (a) makes `/works` foreign to every other
page; (b) is a separate project with a blast radius across five surfaces.

**Translation table** — what each measured value becomes here:

| Reference | Ours |
|---|---|
| Anton, uppercase, ultra-bold | `--ff-primary` (Inter) weight 400, sentence case, `--ls-*` negative tracking |
| IBM Plex Mono 600 | `--ff-mono` (JetBrains Mono) weight 400 via `.label` / `.micro` |
| Cream sections `#efeae2` | `--c-canvas` throughout; there is one surface |
| Eyebrow on a solid chip | the existing `.label` primitive, plain, `--c-mute` |
| `box-shadow` on pill hover | `.pill-btn`'s existing border + frost lift |
| `scale(1.1)` on hover | `scale(1.04)`; `.pill-btn`'s existing `scale(.97)` press is kept |
| `border-radius: 10px` thumbs | `--r-sm` (8px) |
| Their icon-swap badge | kept verbatim — it is mechanism, not styling |
| Their line-mask reveal | kept verbatim |
| Their spec-rule gradient | kept, drawn in `--c-ink` / `--c-hairline` |

The two custom easings are kept as-is and added to `_vars.scss` beside the
existing ones; they are curves, not colours.

### D3 — Page structure

**Decided:** chapter-as-carousel. One `100dvh` screen per chapter, each
holding a carousel of that chapter's projects, curtain between chapters.

**Alternatives:** (a) literal port — one hero carousel of featured work, with
chapter sections below; (b) a single carousel of all eight with the chapters
reduced to filter pills.

**Why:** (a) duplicates content, because our featured work and our chapter work
are the same projects; the reference avoids this only because its hero items
*are* all its items. (b) discards the three-kinds-of-work argument that
`PRODUCT.md` positioning rests on. Chapter-as-carousel keeps that argument,
gives the curtain a real job at the chapter boundary, and lands at 2–4 items
per carousel — the same density the reference runs at four.

**Dependency:** this structure assumes each chapter has real work in it. It
does not today. See D9, which must be settled before implementation starts.

### D9 — The exhibit is majority placeholder

**Finding, from auditing `src/data/works.ts`:** of the 9 entries `worksFor`
exhibits, only **4 are real** — `miracle-cutting-machine`, `kage`,
`castranova-pos`, `parallel-hrm`. The other 5 are `TODO —` stubs.
**Chapter 04 (Custom Web & Mobile) is 100% placeholder**: all three of its
entries are stubs with no title, no client and no media.

This did not matter under the previous design, where a stub was one panel in a
scrollable document. It matters enormously now: a full-viewport carousel gives
every stub an entire screen, and one chapter in three becomes three screens of
"TODO — Build name".

**Meanwhile** four real, fully-mediated projects are excluded from the exhibit
by `homeOnly: true` — `parallel` and `redhorse-group` (creative-web),
`mrspinel-staff` and `gaigai` (custom-build).

**Options, for the owner to decide:**

| | Move | Result |
|---|---|---|
| **a** | Drop `homeOnly` from all four and delete the 5 stubs | 02: 4 real · 03: 2 real · 04: 2 real. **Zero placeholders.** Recommended. |
| **b** | Drop `homeOnly` from the two `custom-build` entries only | Rescues chapter 04; chapters 02 and 03 keep stubs. |
| **c** | Hide any chapter whose entries are all stubs | Exhibit shrinks to two chapters; the three-kinds-of-work argument breaks. |
| **d** | Ship the stubs | Three screens of "TODO". Not viable. |

Option (a) is what the mockup was built against and what §6 below assumes.
It reverses `works-page-design.md` D5's home-only split, which was a decision
made when `/works` and the home page showed the same work in the same way —
no longer true once `/works` is an exhibit and the home page is an index.

**Effect on the home page: none.** Selected Work is driven by `featured`, not
by `homeOnly` — `worksFor` is the only consumer of `homeOnly`. Dropping the
flag adds those four to `/works` without removing them from home, which is the
intended end state: home is an index, `/works` is the exhibit, and the same
project legitimately appears in both. `src/pages/index.astro` is not edited.

**This is a content decision, not an implementation one.** Nothing in §7
changes whichever way it goes; only the per-chapter counts in §6 do.

### D4 — Where the detail lives

**Decided:** clicking a slide opens the existing `WorkTransition` overlay.

**Alternative:** a per-project route at `/works/[id]`.

**Why:** `workTransition.ts` already handles the Flip morph, the SplitText
reveal, the Lenis freeze, focus management and a reduced-motion path. A route
would need all of that rebuilt plus a curtain hand-off across a navigation.
Deferred, not rejected — if project write-ups grow past a screen, routes are
the right answer and the data layer already keys on `id`.

### D5 — Tabs are retired

**Decided:** the ARIA tablist in `works.astro` and `WorkChapter.astro` is
replaced by the carousel's thumb rail.

**Why:** the tab row and the thumb rail are the same control — pick one of N
projects within a chapter. Keeping both would be two affordances for one job.
The thumb rail carries media, which the tabs did not.

**Cost:** the no-JavaScript fallback changes shape. See D6.

### D6 — No-JavaScript and no-WebGL behaviour

**Decided:** two independent fallbacks, neither of which loses content.

- **No JS:** every slide ships visible in the markup as a linear stack. The
  carousel script performs the initial collapse, exactly as the tab script does
  today. Slides therefore carry no `data-inview` (that attribute hides its
  element until a script adds `.inview`).
- **No WebGL:** `Canvas.astro`'s `onError` already sets `.no-curtains` on
  `<body>`, and `_base.scss:224` already reveals the DOM `<img>` inside
  `[data-canvas]`. The carousel degrades to a plain image carousel with no
  further work.

These are separate failures and must be handled separately; a device can have
JS and no WebGL.

### D7 — Texture budget

**Decided:** plane textures cap at 1600×900, and planes are created per
chapter rather than per page.

**Why:** eight simultaneous 2048×1152 RGBA textures is roughly 75 MB of VRAM,
which is not safe on mid-range mobile. At 1600×900 each texture is ~5.8 MB, and
holding only the in-view chapter's planes keeps the resident set at three.

**Video:** the plane is textured from the poster image. A film plays only for
the active slide, in a DOM `<video>` layered above the canvas, never as a
WebGL texture. Video textures re-upload every frame and would cost more than
the effect returns.

### D8 — Asset intake format

**Decided:** raw masters in, derived sizes out. One folder per project `id`.

```
incoming/<id>/
  hero.png          16:9, largest available (≥2560×1440 preferred)
  film.mov          master edit, only where one exists (≥1920×1080)
  screens/01.png    raw UI captures at native resolution, in listing order
```

- Largest, least-compressed source. Downscaling is lossless in intent;
  upscaling is not.
- No pre-made thumbnails: the 112×64 rail thumb is cropped from `hero.png`.
- No pre-scaling, pre-cropping or device framing on UI captures —
  `DeviceMock.astro` frames them and `sharp` does the encoding.
- Nothing carrying a client's real customer data. `castranova-pos` sets the
  precedent: captured against an isolated seeded database.

**Placeholders until real assets land:** the project's own existing media in
`public/works/`, not the reference's demo footage. Borrowed footage inside a
portfolio exhibit misrepresents the work on display, which is `PRODUCT.md`
anti-reference 4 — and the reference's clips carry licensed characters that
are not ours to redistribute.

**Under D9 option (a)**, seven of the eight exhibited projects already have a
real poster in `public/works/`. The single gap is `kage` (`media: null`),
which renders the labelled empty panel the data layer already supports, and
`parallel-hrm`, which has a still but no film — acceptable, since D7 textures
planes from stills regardless.

## 6. Architecture

```
src/components/Canvas.astro          modified — accept scoped containers, expose plane registry
src/shader/carousel.vert.glsl        new — plane warp driven by drag + scroll velocity
src/shader/carousel.frag.glsl        new — texture sample + edge falloff
src/shader/curtain.frag.glsl         new — the boundary wipe
src/components/WorkCarousel.astro    new — one chapter's carousel; replaces WorkChapter
src/components/PageCurtain.astro     new — the fixed sheet + canvas layer
src/components/ActionPill.astro      new — .pill-btn plus the two-icon badge
src/scripts/works/carousel.ts        new — slide state, drag, arrows, thumbs, progress
src/scripts/works/curtain.ts         new — boundary ScrollTriggers, curtain timeline
src/scripts/works/lineReveal.ts      new — SplitText line/char mask reveal
src/styles/_vars.scss                modified — add the two reference easings
src/pages/works.astro                rewritten — hero, three carousels, closing
src/components/WorkChapter.astro     deleted — superseded by WorkCarousel
src/data/works.ts                    unchanged
src/data/works.test.mjs              extended — assert every exhibited work has a thumb source
docs/works-page-design.md            marked superseded, pointing here
```

Nothing outside this list is touched.

### Page order

1. **Hero** — `01 — Works`, the existing typographic void. Unchanged.
2. **Chapter 02 — Creative Websites** — carousel, 4 projects.
3. **Chapter 03 — ERP Software** — carousel, 2 projects.
4. **Chapter 04 — Custom Web & Mobile** — carousel, 2 projects.

Counts assume **D9 option (a)**. Any other option changes only these numbers.
5. **Closing** — one line and the mail link. Unchanged.

The standalone intro section is folded into the hero: with chapters now one
screen each, two paragraphs of preamble sit between the mark and the first
exhibit and delay it by a full screen.

### Chapter anatomy

```
┌─ 100dvh ──────────────────────────────────────────────┐
│  02 — CREATIVE WEBSITES          .label, --c-mute     │
│  Creative Websites               h2, line-mask reveal │
│                                                       │
│      ╭────────────────────────────╮          ╭─╮      │
│      │   warped plane (curtains)  │          │‹│      │
│      │   active project media     │          ╰─╯      │
│      ╰────────────────────────────╯          ╭─╮      │
│                                              │›│      │
│  Miracle Cutting Machine         title       ╰─╯      │
│  Two sentences of summary.       mono 12/1.65         │
│  [View live ↗] [Details]         ActionPill  ▭ ▭ ▭    │
└───────────────────────────────────────────────────────┘
                    ↑ curtain fires here
```

## 7. Motion System

Four mechanisms. Each is independent and independently disabled.

### 7.1 Curtain (chapter boundary)

A `ScrollTrigger` per boundary, anchored to the chapter stack rather than to a
chapter's own box, because a pinned or sticky element moves under ScrollTrigger
and its `getBoundingClientRect` cannot be trusted:

```
start: () => 'top top-=' + (i - 1) * window.innerHeight
end:   () => 'top top-=' + i * window.innerHeight
scrub: true
invalidateOnRefresh: true
```

The sheet covers, the canvas wipes, the outgoing chapter's planes are disposed
and the incoming chapter's are created. `ScrollTrigger.refresh()` runs after
plane creation, since creating planes changes layout.

Per the GSAP guidance: ScrollTriggers are applied to top-level animations only,
never nested inside a parent timeline.

### 7.2 Carousel (within a chapter)

Slide index is the single source of truth. Arrows, thumb clicks, keyboard
arrows and pointer drag all write to it; everything else reads from it.

- Plane `uTime` advances in `onRender`, as `Canvas.astro` already does.
- A `uVelocity` uniform carries pointer-drag delta and Lenis scroll velocity,
  so the plane deforms in the direction of travel and relaxes at rest.
- `--slide-progress` on the active thumb is written from the same state.
- The drag hint's ±35px sway runs until first interaction, then is removed.

### 7.3 Line reveal (headings)

`SplitText` into lines, each line wrapped in an `overflow: hidden` mask with
`padding-bottom: .09em` so descenders are not clipped. Lines translate up from
100% on a stagger. `SplitText` is already imported by `workTransition.ts`.

### 7.4 Pill icon swap

CSS only, no GSAP. Two icons stacked at `grid-area: 1/1` inside a
`overflow: hidden` badge; hover translates one out and the clone in. This
belongs in CSS because it is a hover state, and a hover state that depends on
a JS runtime is a hover state that breaks.

### 7.5 Reduced motion

| Mechanism | Under `prefers-reduced-motion: reduce` |
|---|---|
| Curtain | chapters become a plain stack; no sticky, no clip |
| Carousel | no plane warp, no drag inertia; slides cross-fade at 0s |
| Line reveal | text renders at rest, no split |
| Pill | transitions nulled; clone stays parked (matches the reference) |

## 8. Accessibility

- The carousel is a **group**, not a tablist and not a listbox:
  `role="group"` with `aria-roledescription="carousel"`. Thumbs are plain
  `<button>`s carrying `aria-current="true"` on the active one, and a
  `aria-live="polite"` region announces "Project 2 of 4" on each change.
  Retiring the tablist (D5) means the ARIA tab pattern goes with it — a thumb
  rail is not a tab row and must not claim to be one.
- Arrow buttons carry real labels ("Previous project" / "Next project"), never
  a bare glyph.
- Slide state is carried by thumb opacity **and** the progress fill **and**
  `aria-current` — never by opacity alone (`PRODUCT.md`: colour is never the
  sole carrier of meaning).
- Thumb labels are mono 8px in the reference. Ours use `--fs-micro` (12px);
  8px fails AA at any contrast and is not adopted.
- Drag is an enhancement. Arrows and keyboard reach every slide.
- Focus indicators are never removed. Focus moving to an off-screen slide must
  advance the carousel to it.
- The curtain layer is `pointer-events: none` and `aria-hidden`.
- `--c-mute` stays on metadata only. Summaries use `--c-body`.

## 9. Non-Functional Requirements

| Concern | Target |
|---|---|
| Dependencies | No new package. `gsap`, `lenis`, `curtainsjs`, `sharp` already present. |
| VRAM | ≤3 chapters' planes resident; textures ≤1600×900 (D7). |
| Frames | 60fps on the curtain wipe at 1440×900. Plane segment count tuned down from `Canvas.astro`'s current 100×100 if it does not hold. |
| Payload | Poster textures only on first paint. Films load on activation, never on scroll into view. |
| Degradation | Full content with no JS (D6) and with no WebGL (D6), independently. |
| Maintenance | Adding a project stays an edit to `src/data/works.ts` alone. |

## 10. Risks

1. **Plane lifecycle across the curtain.** Creating and disposing planes at a
   scrub boundary is the hardest part of this build: dispose too early and the
   outgoing chapter tears, too late and VRAM spikes. Mitigation: dispose from
   the boundary trigger's `onLeave` / `onLeaveBack`, never from `onUpdate`, and
   hold a one-chapter lookahead. (A `scrub` trigger has no meaningful
   `onComplete` — progress is scroll-bound, so there is no natural end to hang
   teardown on.)
2. **`100dvh` on mobile.** The URL bar resize changes `dvh` mid-scroll and will
   shift every boundary. Mitigation: `invalidateOnRefresh` on every trigger, and
   `ScrollTrigger.refresh()` debounced on `resize` — not on `scroll`.
3. **D9 is unresolved and blocks the layout.** Until the owner picks an option,
   the per-chapter counts in §6 are provisional. Highest-priority open item;
   nothing in §7 depends on it, so implementation of the motion system can
   start in parallel.
4. **Carousels of two read thin** next to a carousel of four. Under D9 option
   (a), chapters 03 and 04 both hold two. Accepted: the alternative is padding
   the exhibit, and `PRODUCT.md` chose a portfolio selection over a career
   total on purpose.
5. **Most posters are 16:9 web captures**, not purpose-shot hero frames. They
   will read as screenshots on a full-viewport plane, where the previous design
   showed them at a bounded 1024px column. Mitigation is content, not code:
   D8's intake.
6. **`docs/works-page-design.md` is stale** and describes a system that no
   longer exists. Marked superseded rather than deleted, so its decision log
   stays readable.

## 11. Verification

```
yarn build                      # astro check && astro build
node src/data/works.test.mjs    # extended per §6
```

Manual, per chapter:

- Keyboard through every slide; confirm focus never lands off-screen.
- Load with JavaScript disabled: every project readable as a linear stack.
- Force `.no-curtains` on `<body>`: every project readable as images.
- `prefers-reduced-motion: reduce`: no pin, no warp, no split.
- Throttled mobile profile: confirm no VRAM growth across all three boundaries.
