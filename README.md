# kwg-portfolio

Personal portfolio. An exhibit, not a funnel. Brand strategy lives in [`PRODUCT.md`](./PRODUCT.md), visual system in [`DESIGN.md`](./DESIGN.md). Read those before touching styles or copy.

## Stack

- [Astro 6](https://astro.build)
- SCSS with a custom reset, mixins, and fluid sizing utilities
- [GSAP](https://gsap.com/docs/v3/) for orchestrated animation
- [Lenis](https://github.com/darkroomengineering/lenis) for smooth scroll
- [curtains.js](https://www.curtainsjs.com/documentation.html) for WebGL on media
- Custom cursor, inview triggers, splash screen

## Local development

Requires Node 24+ and Yarn.

```bash
yarn install
yarn dev      # http://localhost:4321
yarn build    # runs astro check, then builds for production
yarn preview  # serves the production build locally
```

## Project layout

```
src/
  components/   Header, Footer, Cursor, Canvas, Splash
  layouts/      shared shell
  pages/        /, /page-2, /my-portfolio, /about
  scripts/      scroll, inview, console credits
  styles/       _vars, _base, _typography, mixins, fonts
PRODUCT.md      register, audience, brand personality, anti-references, design principles, accessibility floor
DESIGN.md       color, typography, components, motion, breakpoints
```

## Brand rules at a glance

The full system is in [`DESIGN.md`](./DESIGN.md). For quick reference when editing:

- Surface is `#000000`. Not dark gray. Not near-black.
- Type is white on black, weight 400, uppercase at display sizes.
- The only chromatic color is Lamborghini Gold (`#FFC000`), reserved for primary CTAs.
- Border-radius is 0 on buttons and cards. Sharp angles are non-negotiable.
- Motion is color and opacity, never scale or translate on hover.
- Anti-references (see [`PRODUCT.md`](./PRODUCT.md)): no neon, no glassmorphism, no gradient text, no hero-metric template.

## Credits

Built on the [astro-creative-base](https://github.com/jankohlbach/astro-creative-base) starter by Jan Kohlbach. Brand direction and content are original.
