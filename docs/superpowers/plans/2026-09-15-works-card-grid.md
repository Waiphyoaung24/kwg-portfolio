# Works Page — Card Grid

Status: brainstormed and built 2026-09-15.
Reference studied: `https://github.com/cortiz2894/stylized-components`, the `/`
landing only (`src/app/page.tsx`, `src/app/home.module.css`). Layout only.
None of its type, colour, radius or code is reused.

Supersedes the tab-switcher layout in `docs/works-page-design.md`. The data
rules there (§7, `src/data/works.ts` is the only content source) still hold.

---

## 1. Understanding

- Replace `/works` completely: hero + intro + three tabbed chapters become
  one compact header and one grid of video-backed cards.
- The reference's shape: eyebrow (rule + mono caption), display title with a
  dim second line, one short lead, then an `auto-fit minmax(320px, 1fr)` grid.
  Each card plays its demo muted behind the copy, desaturated and dim (~0.22
  opacity), and "wakes" on hover (colour back, ~0.55 opacity, scale 1.04).
  A scrim keeps copy legible. A ghost index number sits top-right. Actions
  are pushed to the card's bottom edge so uneven copy still lines up.
- Rendered in the `DESIGN.md` system: near-black canvas, hairline borders,
  `.pill-btn` actions, `.label` / `.micro` mono captions, weight 400, tokens
  only. One filled pill per view at most.
- Pure Astro + SCSS. No React, no new dependency. The reference's landing
  needs none of its R3F / Tailwind stack; only its demo pages do.

## 2. Why this is not the shelved rebuild

The 2026-09-13 restructure (see memory `works-restructure-shelved`) ported the
same author's demo-page scroll mechanics and failed on assets: 16:9 posters
stretched over full-viewport WebGL planes. This ports the *index* page instead.
Posters sit at card size behind a scrim, which is the size they were made for.

## 3. Decisions (owner, 2026-09-15)

| # | Decision | Rejected |
|---|---|---|
| D1 | Layout only, DESIGN.md skin | Faithful port as a scoped exception; cards + per-project workspace view |
| D2 | One grid with filter pills: All / Creative Websites / ERP Software / Custom Web & Mobile | Three sections each with a grid; flat grid without filter |
| D3 | Placeholders (`TODO —` entries) do not render | Empty-state cards |
| D4 | Compact header replaces the full-height hero and the intro prose | Keep hero, grid below |
| D6 | Superseded D5 that evening. The target is the deployed site stylized.cortiz.dev, not the repo landing. `/works` is one full-screen three.js ring of all eight works (`src/scripts/works/ring.ts`), measured off the live site's settings defaults, in its own look. The shelved `origin/wip` build was the starting point, but its flat curtains panels do not fit a ring, so little of its code carries over | Rebuild from scratch; keep the card grid; one carousel per category |
| D5 | Later the same day: reverses D1 and D2. `/works` becomes a 1:1 port of the reference landing, its own fonts, palette, radii and square buttons, as a DESIGN.md exception. No filter row. One "View live" action per card | Keep the DESIGN.md skin; copy the owner's own home page |

## 4. Home-only work — resolved: included

`homeOnly: true` keeps Parallel, Red Horse Group, Mr Spinel and GaiGai out of
`/works`. The recorded reason is that nothing should deep-link to a tab panel
for them. Tab panels no longer exist. With D3, honouring the flag leaves a
**4-card grid** (Miracle Cutting Machine, Kage, CastraNova POS, Parallel HRM);
lifting it gives **8**, all with posters.

Recommendation: include them (`worksFor` stops filtering on `homeOnly`, the
flag stays as a Selected-Work marker or is removed). Confirm before step 2.

## 5. Non-goals

- No detail view, no routing per project, no modal.
- No WebGL, no scroll-driven motion, no GSAP on this page.
- No changes to the home page's Selected Work overlay.
- No copy rewrite beyond the header lead.

## 6. Steps

```
1. Data       → src/data/works.ts: `worksFor()` becomes `exhibited()`:
                 drops `TODO —` placeholders (id starts with `placeholder-`),
                 and per §4 either keeps or drops the homeOnly filter.
                 Delete the five placeholder entries outright (D3 makes them
                 dead data). Keep `chapters` — the pill row reads its
                 headings. Update works.test.mjs: chapter test no longer
                 requires ≥1 project per chapter via worksFor if filtered;
                 assert no `placeholder-` ids remain.
                 verify: `yarn test:works` passes (add script if missing;
                 today it is run directly with node).

2. Card       → src/components/WorkCard.astro (replaces WorkChapter.astro,
                 which is deleted). Props: one Work. Markup:
                 <article class="work-card" data-category=…>
                   media: <video muted loop playsinline autoplay
                          preload="metadata" poster> when kind=video, <img>
                          when kind=image, nothing when null (card keeps the
                          hairline and a `.micro` "No media yet").
                   scrim span
                   ghost index (two-digit, from grid position)
                   .micro meta line: client · year
                   h2 title (display-xs / --fs-5)
                   summary (body-sm, ~42ch)
                   .micro stack line
                   actions: one `.pill-btn` "View live ↗" when url, else
                   nothing. No filled pill on cards.
                 verify: page renders one card per exhibited work; no
                 hex/px literals in the component (grep).

3. Page       → src/pages/works.astro rewritten:
                 header: .label eyebrow "02 — Works" with a hairline rule,
                 h1 "Works" + dim second line (--c-mute is metadata-only,
                 so the dim line uses --c-body-mid… check contrast ≥ 4.5:1
                 on canvas; else use --c-body), one lead ≤ 60ch.
                 filter row: role="group" of `.pill-btn` buttons with
                 aria-pressed; "All" pressed by default.
                 grid: repeat(auto-fit, minmax(20rem, 1fr)), gap
                 var(--grid-gutter).
                 script: one delegated click handler toggles aria-pressed
                 and sets `hidden` on cards whose data-category ≠ choice.
                 Cards ship visible; no-JS = all cards, no filter.
                 Motion: hover wake gated by has-hover and
                 prefers-reduced-motion (no scale under reduce). Videos
                 autoplay only when `prefers-reduced-motion: no-preference`;
                 otherwise the poster shows and the video does not load
                 (set `autoplay` from a matchMedia check, or use
                 `preload="none"` + poster and start playback in script).
                 verify: `yarn build` passes astro check; keyboard: Tab
                 reaches every pill and every live link; filter works with
                 Enter/Space; screen-reader announces pressed state.

4. Cleanup    → delete WorkChapter.astro; update the comment in works.astro
                 that points at works-page-design.md; add a two-line
                 "superseded by" note at the top of that doc.
                 verify: `grep -rn WorkChapter src` is empty; lint clean.

5. Visual     → run dev, screenshot /works at 400px, 768px, 1280px.
                 verify: no horizontal scroll at 400px; cards stack to one
                 column; copy readable over the busiest video frame; ghost
                 index does not collide with the title on narrow cards.
```

## 7. Files

| File | Change |
|---|---|
| `src/pages/works.astro` | rewrite |
| `src/components/WorkCard.astro` | new |
| `src/components/WorkChapter.astro` | delete |
| `src/data/works.ts` | drop placeholders, rename/adjust `worksFor` |
| `src/data/works.test.mjs` | adjust assertions |
| `docs/works-page-design.md` | superseded note |

## 8. Risks

- Four autoplaying videos on one page is fine; if the grid grows past ~8 with
  film, switch to IntersectionObserver play/pause. Not needed now.
- `liquid-glass` on `.card` uses a backdrop filter; over a video that is a
  per-frame filter pass. The card uses a plain hairline border and
  `--c-canvas-card`, not `.card`, for that reason. Note it in the SCSS.
- Kage's live link is an internal route (`/catalog/kage/live`); the pill must
  not force `target=_blank` for internal hrefs.
