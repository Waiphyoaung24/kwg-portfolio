# Works — the rest of stylized.cortiz.dev

Status: built 2026-09-15, uncommitted. Verified in a browser at 1440 and 400.
Open: the section copy and the four perks in §3 await the owner; the rail's
bend was tuned by eye (0.05 card heights) because the reference's own value
reads far stronger in this implementation. Builds on the hero ring
(`src/scripts/works/ring.ts`, decision D6 in `2026-09-15-works-card-grid.md`).

Reference: `https://stylized.cortiz.dev/`, measured in a browser at 1440×900
and read off its deployed CSS and bundle defaults. Numbers below are its
values. Code is ours.

---

## 1. What the live page is, top to bottom

| # | Section | Height | Layout | Moving part |
|---|---|---|---|---|
| 0 | Hero `HomeCarousel` | 100dvh | ring of curved cards | done |
| 1 | Intro `#about` | 100dvh | centred chip, 2-line Anton title, 3 spec columns | cards streaming toward the camera |
| 2 | Breakdowns `#breakdowns` | min 100dvh | head grid 1.25fr / .75fr: chip + title left, body + black pill right; full-width rail below | draggable, drifting rail of cards that bends with speed |
| 3 | Support `#support` | min 100dvh | grid 1.05fr / .95fr: curved 16:9 video left, chip + title + body + perks + black pill right | the video panel |
| — | Footer strip | fixed | "Created by" left, socials right | colour follows the page |

Page-level: one backdrop behind everything — a noise wash with a faint grid
lattice — that hands over from the dark hero to paper `#efeae2` as the intro
scrolls in (`whiten .92` from scroll `.08` to `.87` of the hero).

## 2. Decisions (owner, 2026-09-15)

| # | Decision | Rejected |
|---|---|---|
| S1 | Faithful: each section's motion in three.js, plus the page hand-over | Hybrid (WebGL strip only); CSS only |
| S2 | Claude drafts portfolio copy per section; owner edits after | Cortiz's copy as placeholder; empty slots |
| S3 | Rail shows the 18 captures in `public/works/capabilities` | the 8 work posters again; services sectors |
| S4 | Live-site fixed strip for the whole page; the KWG footer is hidden on /works | both |
| S9 | The site footer returns to /works and the fixed "Created by KWG" strip is removed, reversing S4. The contact section stays above the footer. Layout's `footer` prop goes with it, since nothing turns the footer off any more | keep the strip and fade it at the footer; strip in the hero only; drop the contact section |
| S8 | The screens strip becomes a brands strip: one card per work (seven), each its logo on a dark gradient tinted to the brand, no label, 16:9 like the reference. Built by `build-work-cards.mjs` into `public/works/strip/<id>.webp`. The Nexus captures drop out, the rail returns to the reference's height, and the copy is rewritten for logos | all 17 captures as logo cards; Nexus projects with cut-down logos; one neutral gradient; a caption per card |
| S7 | Kage leaves /works entirely: the hero ring, its thumbnails, the intro stream and the screens strip. It is exhibited under Catalog only, so its works.ts entry, its card and its strip capture are removed | keep Kage in the ring |
| S6 | Hero cards show a background and a logo, never a screenshot. All eight are rebuilt by `src/scripts/build-work-cards.mjs` into `public/works/cards/<id>.webp`: the project's own capture, blurred and darkened, with its logo keyed out of its existing poster and centred (Parallel HRM uses the Parallel wordmark with "HRM" beneath). The ring stops swapping in films, since a film would cover the logo; the contact panel keeps its film. Home keeps its posters | project name as the logo; owner-supplied logo files; only Parallel HRM and Kage; plain dark gradient behind the logo |
| S5 | Later the same night: dark theme. The hand-over runs to the site's black `#0a0a0a` instead of paper; section type turns cream; chips and pills are cream-filled with dark text; the lattice stays light. The header override and `--page-paper` go, since nothing flips any more | no hand-over, slate throughout; black with a card tint; warm black `#0e0d0c`; dark outline pills |

## 3. Copy drafts (S2) — owner to confirm

Voice per PRODUCT.md: declarative, short, no claims that are not evidenced.

**01 — The Work**
- Title: "Three kinds of work. / All of it shipped."
- Specs, one line each, cut from the retired chapter intros:
  - Creative Websites — Sites where the interface is the argument.
  - ERP Software — Internal systems for people who live in them all day.
  - Custom Web & Mobile — Builds shaped to one operation, not a template.
- Stream cards: the eight work posters.

**02 — The Screens**
- Title: "Evidence, / not claims." (the site's own line, from the retired hero)
- Body 1: "Every frame in this strip is a capture of shipped work, taken from the running product rather than drawn for the portfolio."
- Body 2: "Each one belongs to a sector on the services page, with what was built there and why."
- Pill (black): "Browse services" → `/services`
- Rail: 18 captures, labelled by project. Not links; the pill is the door.

**03 — Work with me**
- Title: "One email, / then the work."
- Body: "There is no form and no call to book. Write with what you run and what is broken in it. The reply comes from the person who builds it, usually within a day."
- Perks (owner to verify each is true before launch):
  - Design, build and deployment by one person, not a relay
  - The data model settled before the interface is drawn
  - One codebase for web and mobile where the product allows it
  - Source and deployment handed over at the end
- Pill (black): "Start a project" → `mailto:` with the Footer's subject line
- Media: the Miracle Cutting Machine film on the curved panel.

## 4. Build

Reference values per piece, then what changes here.

**Backdrop** (`src/scripts/works/backdrop.ts`, new). Moves the wash out of
ring.ts into one fixed full-screen canvas behind the page. Scroll progress
through the hero drives `whiten` 0→.92 toward paper; grid ink swaps light→dark
with it and writes `--page-paper` on `<html>` for the DOM (strip colour,
section ink). The ring canvas becomes transparent and reports its tones.

**Intro stream** (`intro-stream.ts`, new). 10 cards, width 2.8, aspect 1.6,
corner .05, opacity .73, tint .45 toward paper. Spawn depth 34, speed 5.8,
spread 1.6–6.5, scale .55–1.2, roll ±12°, spin ±3°, tilt ±22°, fade-in over 12,
scroll boost 1.5. Camera distance 8.7, fov 42, pointer parallax 5.25 with tilt
.6. DPR .7. Canvas bleeds 30% above and below with a masked fade. The
reference's per-card motion blur and chromatic spread are left out; cards are
drawn sharp at the reference opacity.

**Rail** (`rail.ts`, new). Card height .66 of the rail, gap .09, corner .055.
Auto drift .05, drag sensitivity .65, decay 3.6, flick cap 10. Bend .16 of
horizontal travel, full at speed 10.9. Hovered card keeps colour, others go
56% grey. Rail height `clamp(210px, 25vw, 360px)`. Deviation: card aspect
follows the captures (portrait, ~.77) instead of the reference's 16:9, so a
screen is shown whole rather than cropped to a band.

**Support panel** (`panel.ts`, new). Orthographic canvas, 16:9, inset -10%
vertically; the video on a rounded plane bowed by the page curve (.23).

**Reveals** (GSAP, already installed). Titles split to chars, rise 115% with a
.012 stagger when the section reaches 78% of the viewport; spec rules scale in
from the left; `[data-reveal]` items fade up 14px. None of it under reduced
motion.

**Chrome.** `Layout.astro` gains a `footer` prop, default true; /works passes
false. The hero's own strip moves to a page-level fixed strip.

**Budget.** Every canvas renders only while its section is on screen. No new
dependency.

## 5. Steps

```
1. Sections in DOM  → layout, type, copy, fixed strip, Layout prop, reveals
                      verify: screenshots beside the live site at 1440 and 400
2. Backdrop         → wash out of ring.ts, scroll hand-over to paper
                      verify: colour at hero, mid-intro, breakdowns
3. Intro stream     → verify: cards pass the camera, pause off screen
4. Rail             → verify: drift, drag, bend, hover grey
5. Support panel    → verify: film plays on screen, pauses off screen
6. Close            → build, lint, tests, reduced motion, mobile
```
