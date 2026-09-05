# Vault — scroll-driven dock

Replaces the Vault's static tool grid with a vertical, scroll-driven dock in the
spirit of the macOS/iOS dock: tiles magnify as they reach the focal point and
recede either side of it. Pure CSS scroll-driven animation, no JavaScript.

Reference: jh3y, "iOS style scrolling dock with scroll-driven animation"
(https://codepen.io/jh3y/pen/xxmRyJO), via freefrontend.com/css-animations.

## Understanding summary

- **What.** `#vault`'s 4-column `.tools` grid becomes a one-column dock inside
  its own bounded scroller. Each tile scales up, brightens and takes the accent
  border as it crosses the scroller's centre.
- **Why.** The grid was inert. Selection should feel physical, and the page
  should have a reason to scroll.
- **Who.** One authenticated user. ~4-7 tools. `noindex`, private.
- **Scope.** `src/pages/vault.astro` only — the `#vault` section's markup and
  styles. Gate, hash check, logout and tool URLs untouched.
- **Non-goals.** No icon assets, no glassmorphism, no `filter: blur()`, no JS
  fallback, no new dependencies, no changes to `/vault/*` subpages.

## Assumptions

1. Tiles stay square and brutalist — existing `--c-surface-1`, 1px border,
   uppercase Space Grotesk. Only the *motion* is borrowed from the reference,
   not its rounded-glass skin, which would fight the site's design direction.
2. Magnification is `scale` + `opacity` + `border-color`. `blur()` is the
   expensive part and reads as mush on text-only tiles.
3. The three `aria-hidden` "Add a tool" placeholders are dropped. In a
   one-column dock they would be three empty screens of scrolling.
4. Browsers without `animation-timeline` get a plain, readable vertical list.
   That is Firefox and Safari < 26. Acceptable on a page only the owner sees.
5. `prefers-reduced-motion: reduce` disables magnification and snap.

## Decision log

| Decision | Alternatives | Why |
|---|---|---|
| Vertical dock, tiles magnify at centre | Horizontal bottom dock; horizontal centred strip | Uses the page's own scroll axis; closest to the reference; no extra chrome. |
| Per-tile `animation-timeline: view(block)` | `scroll()` timeline on the container with per-item ranges; JS IntersectionObserver | `view()` gives each tile its own progress for free. `scroll()` needs manual per-index range maths. JS costs ~40 lines and a rAF loop for a private page. |
| Bounded scroller under a static header | Let the whole page scroll | Keeping "VAULT" and LOCK in place is what makes it read as a dock rather than a long list. Costs four lines. |
| `padding-block: calc((--dock-h - --tile-h) / 2)` | Spacer `::before`/`::after`; container queries with `cqh` | Lets the first and last tile reach the focal point with one line of arithmetic instead of pseudo-elements. |
| Square tiles, accent border at focus | Rounded macOS-style tiles | Preserves the brutalist direction; the motion alone carries the reference. |
| No blur | `filter: blur()` off-focus | Cheapest thing to cut, and text tiles blur badly. |
| Placeholders removed | Keep as dashed empty tiles | They were decorative filler; in one column they are dead scroll distance. |
| Bounded-scroller layout scoped to `@supports` | Apply unconditionally | Without magnification, a fixed-height snap scroller showing one lonely centred tile is worse than a plain list. |
| `mask-image` gradient on the scroller | Let tiles clip at the edges; fade further via keyframe opacity alone | The scroller's hard edge sliced receding tiles mid-word. One gradient line fixes it; opacity alone cannot, because the tile is still geometrically clipped. |
| Tile 152px inside a 340px scroller | Tiles short enough that all four fit at once | First attempt let four tiles sit in view, so two were near peak simultaneously and there was no focal point. Tiles must overflow the scroller substantially. |

## Final design

Markup: `ul.dock` is itself the scroll container; `li.tool` snap-centre; the
`a.tool__link` inside carries the animation, so snap positions stay fixed while
the visual scales.

```
.dock   height: var(--dock-h); overflow-y: auto;
        scroll-snap-type: y mandatory;
        padding-block: calc((var(--dock-h) - var(--tile-h)) / 2);
.tool   scroll-snap-align: center; height: var(--tile-h);

@keyframes magnify {
  0%, 100%  scale .72, opacity .3, border-color --c-surface-2
  50%       scale 1,   opacity 1,  border-color --c-accent
}
.tool__link  animation: magnify linear both; animation-timeline: view(block);
```

### Sass gotcha

`--tile-h: to-rem(152)` does **not** work: Sass passes custom-property values
through verbatim, so `to-rem()` reaches the browser unevaluated, the value is
invalid, and every `calc()` and `height` depending on it silently falls back.
Custom properties holding Sass function results must be interpolated:
`--tile-h: #{to-rem(152)}`.

### Notes

`view()`'s default `cover` range runs 0% as the tile begins entering the
scrollport to 100% as it finishes leaving, so 50% is exactly where the tile is
centred — the focal point, with no explicit `animation-range` needed.

Keyboard: tiles are links; tabbing scrolls each into view, which drives the
same animation. Focus ring is unchanged.

---

# Revision — Nothing design language

The dock layout above is unchanged. Its skin was rebuilt on the design system in
`github.com/dominikmartn/nothing-design-skill`, and each tile gained an icon.

## Fonts

Loaded on this page only, via the existing Google Fonts link:
**Doto** (variable dot-matrix, wordmark only), **Space Grotesk** (already
present, body/UI), **Space Mono** (all labels).

## The three layers

| Layer | Element | Treatment |
|---|---|---|
| Primary | `VAULT` wordmark | Doto 700, `clamp-fluid(48, 88)`, `#FFF` |
| Secondary | Tool names in the dock | Space Grotesk 300, 24px |
| Tertiary | Caption, `OPEN`, `LOCK`, form labels | Space Mono 11px, ALL CAPS, 0.08em, `#999` |

The Doto wordmark is the screen's single "moment of surprise"; everything else
is deliberately plain so that break reads as intentional rather than as noise.

## Decision log — revision

| Decision | Alternatives | Why |
|---|---|---|
| Monochrome focal state (`#FFF` border + `#111` fill) | Keep KWG yellow `#FFC000`; adopt Nothing red `#D71921` | The skill treats red as an interrupt, not decoration: "if nothing is urgent, no red on the screen." Nothing in a vault is urgent. Brightness alone marks the focal tile. |
| Red kept for the failed-password state only | Monochrome error text | The skill is explicit that errors *are* the accent moment. This is the one urgent state on the page. |
| Icons as `d` strings in a `tools` array | Four literal SVG blocks in markup | Each icon is a single path, so the array plus one loop is shorter than four near-identical blocks and matches how `works.astro` already handles lists. |
| Asymmetric tile: icon top-left, name bottom-left, action bottom-right | Centred stack (the previous design) | "Centred layouts feel generic" — the skill favours deliberately unbalanced composition. |
| Underlined password input, pill buttons | Bordered input, square buttons | Straight from the components reference: underline is the lighter container; primary = inverted pill, secondary = outlined pill. |
| Magnification eased to `0.82`-`1.0` | Keep `0.72`-`1.0` | The skill asks for percussive restraint over theatrics. Opacity and border now carry more of the state change than scale does. |
| No dot-grid background | Add the dot-matrix motif behind the dock | Two expressive breaks compete. The Doto wordmark is the one break; the rest stays empty. |

## Anti-patterns observed

No gradients in chrome, no shadows, no blur, no filled or multi-colour icons,
no toasts (the error is inline text), no spring easing — transitions are
`cubic-bezier(0.25, 0.1, 0.25, 1)` at 200ms. Tile radius is 8px (technical).
