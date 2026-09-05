# Works Page — Design

Status: approved 2026-09-04. Produced through the `brainstorming` skill.
Reference studied: `https://openai.com/index/gpt-6-astra/` (layout only).

---

## 1. Understanding Summary

- Add a `Works` link to the shared header, routing to a new `/works` page.
- The page showcases three categories: **creative websites**, **ERP software**,
  and **custom website / mobile development**.
- Structure is borrowed from the OpenAI reference: narrow prose measure, a tab
  switcher that swaps a project panel, captions, meta lines.
- Visual language stays Lamborghini-dark per `DESIGN.md`: true black, gold
  accent, all-caps labels, **square corners**, Space Grotesk.
- The reference is measured for proportions only. None of its code, colour,
  typography, or copy is reused.
- Content ships as clearly-marked placeholders in one typed data file. Real
  projects are a single-file edit later.
- Audience is practicing designers and developers judging craft, per
  `PRODUCT.md`. The page is an exhibit, not a lead funnel.

## 2. Non-Goals

- No contact form, no lead capture, no CTA funnel.
- No CMS, no database, no API route. The Postgres surface behind `/vault`
  is untouched.
- No new npm dependency.
- No restyle of `index.astro`, `/vault`, or `/page-2`.
- No pixel-fidelity target against the reference.

## 3. Assumptions

| # | Assumption | Confirmed |
|---|---|---|
| A1 | No new npm dependencies; GSAP and Lenis are already bundled | yes |
| A2 | Tabs are plain DOM with the ARIA tablist pattern, no framework | yes |
| A3 | WCAG 2.2 AA is the floor; Ash `#7D7D7D` is metadata only | yes |
| A4 | Page is public and enters the sitemap (filter only excludes `/vault`) | yes |
| A5 | No forms, no API routes, no database | yes |
| A6 | ~3 projects per category, 9 total, as initial density | yes |
| A7 | All motion gates on `prefers-reduced-motion` | yes |

## 4. Measured Reference Proportions

Extracted by reconnaissance against the reference at a 1568px viewport.
These numbers are the only thing carried over from the target.

| Property | Measured | Applied as |
|---|---|---|
| Prose measure | ~730px / ~65ch | `max-width: 65ch` |
| Body size / line-height | 18px / 1.55 | `--fs-base` / `1.55` |
| Hero display | ~64px, centred | `--fs-1`, all-caps |
| Section gap | ~120px | `clamp-fluid(80, 160)` |
| Tab bar position | centred above media | left-aligned to prose column |
| Media ratio | 16:9, column-width | `aspect-ratio: 16 / 9`, capped at 64rem (see D7) |
| Caption | italic, muted, below media | all-caps label, ash, below media |

Deliberately **not** carried over: rounded pills, 16px card radius, soft
1px borders, sentence-case centred headlines, italic captions.

## 5. Decision Log

### D1 — Reference styling vs. DESIGN.md

**Decided:** borrow the reference's structure; render it in the existing
Lamborghini-dark system.

**Alternatives:** (a) match the reference closely, adopting its rounded pills
and sentence-case type; (b) amend `DESIGN.md` to permit border-radius
site-wide and let other pages drift toward it.

**Why:** (a) makes `/works` visually foreign to the rest of the site for no
gain in clarity. (b) has the largest blast radius and would eventually force a
restyle of `index.astro`, `/vault`, and `/page-2`. Structure is the part worth
borrowing; the detailing is the part that carries brand.

### D2 — Role of the `website-rebuild` skill

**Decided:** reconnaissance only. Measure the reference's proportions, then
discard the target entirely and build from scratch.

**Alternatives:** (a) run the full 1:1 pipeline — mirror, de-minify, port the
bundle verbatim, gate on pixel diffs; (b) skip the skill and design from
screenshots alone.

**Why:** (a) produces a near-copy of a copyrighted commercial page and directly
contradicts D1, whose whole point is that the page should *not* look like the
target. (b) leaves spacing and type scale to guesswork. Recon gives the useful
half of the skill without either problem.

### D3 — Content source

**Decided:** ship a typed placeholder data file at `src/data/works.ts`.

**Alternatives:** (a) collect real project copy before building; (b) wire in
screenshots from an external folder.

**Why:** no real project assets exist in the repo today. A typed data file
makes the page structurally complete now and reduces the later work to editing
one file. Empty media panels render a labelled dark-iron block, never a stock
photo, per `PRODUCT.md` anti-reference 4.

### D4 — Page structure

**Decided:** three chapters, each with its own tab switcher.

**Alternatives:** (a) one global tab bar filtering a grid of nine cards;
(b) linear editorial with nine stacked full sections and no tabs.

**Why:** three chapters is the closest analogue to the reference, which repeats
*heading → prose → tab bar → media panel → caption* per topic. (a) is the most
conventional portfolio pattern, which `PRODUCT.md` anti-reference 4 warns
against. (b) makes a very long page and drops the switcher affordance.

### D5 — Nav composition

**Decided:** remove `Page 2` from the header. Keep the `/page-2` route live and
surface it as the first real entry in the creative-websites chapter.

**Alternatives:** leave the nav as-is and add `Works` as a fifth item.

**Why:** `Page 2` reads as scaffolding in a nav. The page itself (Kage) is
genuine creative work, so it belongs in the exhibit rather than the chrome.
A client can still open it from the works panel.

### D6 — Hero treatment

**Decided:** typographic hero matching the existing homepage void hero. The
reference's full-bleed hero video slot is reserved in the data layer, not
filled.

**Alternatives:** render `public/video.mp4` in the hero immediately.

**Why:** no purpose-made hero asset exists. A generic clip in a hero is
`PRODUCT.md` anti-reference 4 (corporate agency polish).

### D7 — Media panel width (amended during implementation)

**Decided:** cap the tab row and media panels at a 64rem (1024px) content
column, left-aligned with the prose.

**Superseded:** the original plan said "16:9 full-bleed".

**Why:** at container width a 16:9 panel is ~880px tall on a 1568px viewport
and visually swamps the 65ch prose. The reference constrains its section media
to the article column rather than bleeding it. 64rem is wider than the text
measure, because this is an exhibit rather than an article, but it is a bounded
step rather than full bleed. Implemented as `--work-col` on `.chapter`.

## 6. Architecture

```
src/components/Header.astro     modified — drop Page 2, add Works
src/data/works.ts               new — typed content, single source of truth
src/data/works.test.mjs         new — data integrity assertions
src/components/WorkChapter.astro new — one category chapter, ×3 instances
src/pages/works.astro           new — hero, intro, 3 chapters, closing
```

`works.astro` owns page-level layout and the tab script. `WorkChapter.astro`
owns one chapter's markup and styles. Nothing else is touched.

### Page order

1. **Hero** — `01 — Works` label, giant all-caps mark, one-line statement,
   scroll cue. Full viewport height minus header.
2. **Intro** — two paragraphs at the 65ch measure.
3. **Chapter 01 — Creative Websites**
4. **Chapter 02 — ERP Software**
5. **Chapter 03 — Custom Web & Mobile**
6. **Closing** — one line and a mail link.

### Chapter anatomy

```
02 — ERP SOFTWARE                  label, ash, --fs-label
ERP Software                       h2, all-caps, white
One prose paragraph.               65ch measure, ash-light

[ TAB ][ TAB ][ TAB ]              square tabs, gold rule when active
┌───────────────────────────┐
│  16:9 media panel         │      square corners, surface-1 when empty
└───────────────────────────┘
TITLE · CLIENT · 2026 · STACK      meta line, label style, ash
One prose paragraph.               65ch measure
VIEW LIVE ↗                        gold, only when url is present
```

## 7. Data Model

```ts
type Category = 'creative-web' | 'erp' | 'custom-build';

interface Work {
  id: string;          // unique, kebab-case
  category: Category;
  title: string;
  client: string;      // or 'Personal'
  year: number;
  stack: string[];
  summary: string;
  media: string | null; // path under /works/, null renders empty state
  url: string | null;   // live link, null hides the CTA
}
```

Kage (`/page-2`) is the one real entry. Eight siblings are marked `TODO —`.

## 8. Behaviour

- **Tabs** — one delegated click handler covers all three groups. Full ARIA
  tablist: `role="tablist"`, `role="tab"`, `aria-selected`, `aria-controls`,
  `role="tabpanel"`, `aria-labelledby`. Roving tabindex. Arrow Left/Right
  move selection, Home/End jump to the ends.
- **No JavaScript** — panels render visible in the markup and are hidden on
  init. Without JS the page degrades to the linear editorial layout, which is
  the alternative considered in D4. Tab panels therefore carry **no**
  `data-inview` attribute, since that attribute hides its element until a
  script adds `.inview`.
- **Motion** — entrance reveals reuse the existing `data-inview` attribute,
  already gated on `prefers-reduced-motion` in `src/styles/_base.scss`. No new
  GSAP timeline, no new dependency.

## 9. Accessibility

- Active vs. inactive tab state is carried by **fill and a gold bottom rule**,
  not colour alone (`PRODUCT.md`: colour is never the sole carrier of meaning).
- Tab labels use `--c-light`, never Ash. Ash `#7D7D7D` measures 5.1:1 on black,
  which passes AA, but `PRODUCT.md` reserves it for non-essential metadata.
- Focus indicators are never removed.
- Every interactive element is keyboard reachable and operable.
- Media panels carry real `alt` text; empty states are `aria-hidden` decorative
  blocks with a visible `TODO` label.

## 10. Non-Functional Requirements

| Concern | Target |
|---|---|
| Performance | Static page. No new dependency. Images lazy-loaded with explicit ratio, so no layout shift. |
| Scale | 9 static projects. No CMS, no DB, no pagination. |
| Security | No forms, no user input, no new API route. Nothing touches the vault surface. |
| Reliability | Content fully readable with JavaScript disabled. |
| Maintenance | One data file owns all content. Adding a project is a data edit, never a markup edit. |

## 11. Risks

1. **Placeholder media makes the page read as unfinished** until real assets
   land. Mitigated by labelled empty states rather than stock imagery, but the
   page is not launch-ready until `works.ts` is filled in.
2. **Category overlap with the homepage.** `index.astro`'s Capabilities section
   advertises Websites & Landing Pages / Brand & Identity / Product & UI, which
   disagree with the Works categories. Left unresolved by explicit choice;
   flagged for a later pass.
3. **`data-inview` requires JavaScript to reveal.** Pre-existing project-wide
   behaviour, not introduced here. Contained by keeping the attribute off tab
   panels.

## 12. Verification

```
yarn build              # astro check && astro build must pass
node src/data/works.test.mjs
```

The data test asserts: unique ids, every `category` is a valid union member,
every required field is present and non-empty, and each category has at least
one entry. Manual checks: keyboard through each tab group, and load with
JavaScript disabled.
