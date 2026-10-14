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

## Self-hosted Vault apps

Fitness launches **openGym 1.4.1** with its own UI and profile login.
`/vault/figcraft` retains the unmodified **FigCraft 0.5.1 browser release** as a
fallback; the Vault dock opens the desktop app (see below). Neither app is ported
into Astro. The old workout generator remains at `/vault/fitness/generate`.

For local use, copy `.env.example` to `.env` if you haven't configured it yet,
then start just the new services:

```bash
docker compose up -d --build opengym figcraft
yarn dev
```

Open the Vault and choose Fitness, or visit `/vault/figcraft` for the web editor. Direct local URLs are
`http://localhost:8091` and `http://localhost:8092`. Create your own openGym
profile on first use; the first profile is the administrator. openGym's API is
only reachable through its web container. Its exercise media ships in the
official image. FigCraft's Docker build downloads the release ZIP, verifies its
SHA-256, and keeps the bundled licences and notices.

### Production (Dokploy / existing tunnel)

Set these variables in Dokploy's environment, using your actual HTTPS domains:

```dotenv
PUBLIC_OPENGYM_URL=https://fitness.waiphyoaung.com
OPENGYM_RP_ID=fitness.waiphyoaung.com
PUBLIC_FIGCRAFT_URL=https://figcraft.waiphyoaung.com
BIND_HOST=172.17.0.1
```

Route the Fitness hostname to host port **8091**, and FigCraft to **8092**, using
the existing tunnel convention (for example `http://172.17.0.1:8091`). If using
Dokploy service routing instead, target services `opengym:80` and `figcraft:80`.
Redeploy the Compose stack, including `app`, so the Vault reads its new runtime
URLs. openGym's URL is also its API's allowed origin: use an origin only, with
no path or trailing slash. Configure the final hostname before creating
passkeys; passkeys are bound to `OPENGYM_RP_ID`. HTTPS is required outside
localhost. The Vault's client-side gate is obscurity, not authentication;
openGym uses its own login.

Back up the Compose **opengym_data** volume: it holds profiles, workout history,
settings, session secrets, and uploaded media. The apps do not share the site's
Postgres. Do not use `docker compose down -v` when retaining workout data.

FigCraft runs on the visitor's device, requiring WebGPU or WebGL2. It has no
server file storage or cross-device sync in this setup; its upstream browser
build is alpha and native file dialogs are not wired up. Use the desktop app
for file workflows the browser build does not support. Optional online sharing
is an upstream feature and may contact FigCraft's public server; this setup
does not run a collaboration server. Upgrades are deliberate: change openGym's
two image tags together; for FigCraft update the release URL, checksum, and
extracted directory in `ops/figcraft/Dockerfile` together.

## Desktop Vault apps (macOS)

The FigCraft and Sagar dock entries say **Open on Mac**. They open installed
apps through `kwg-vault://figcraft` and `kwg-vault://sagar`, with the browser's
normal external-app confirmation. Install both apps in `/Applications` first,
then install the local Rust launcher:

```bash
bash ops/vault-launcher/install.sh
```

The installer needs Rust (`rustup`, minimal stable profile) and macOS developer
tools. Rust validates two exact links and calls `/usr/bin/open` with fixed app
paths. A tiny AppleScript adapter receives macOS URL events. There is no daemon,
open port, document upload, or cross-device sync. A second Mac needs its own
installation. To uninstall, move `KWG Vault Launcher.app` to Trash; this does
not delete app documents. To update, move the old launcher aside and rerun.

FigCraft uses the official **0.5.1 universal macOS release**. The five upstream
example files are downloaded locally under `downloads/figcraft-examples/` and
opened as native editor tabs; these downloads are not deployed or committed.

Sagar **0.1.0** is built from upstream commit
`b7b5fb062d5010b274b5410e04424b2ea7729689` with `bun install --frozen-lockfile`
and `bun tauri build --bundles app`, then copied from
`src-tauri/target/release/bundle/macos/Sagar.app` into `/Applications`.
It keeps its upstream UI and Rust backend. It translates DRM-free EPUB books;
it is not a general text translation page. Local translations live under
`~/Library/Application Support/app.myanmars.sagar`; back up that folder.
AI provider setup and actual translation are separate from installation.

## Brand rules at a glance

The full system is in [`DESIGN.md`](./DESIGN.md). For quick reference when editing:

- Surface is `#0a0a0a`, near-black, edge to edge. There is no light mode.
- Type is white on that canvas at weight 400. The system never bolds; size and
  negative tracking carry the emphasis.
- Display faces are Inter (substituting the proprietary Universal Sans) and
  JetBrains Mono for uppercase, positively tracked labels.
- Every interactive element is a pill. Outline by default; one filled white
  pill per view marks the primary action.
- Hairline borders carry elevation. The system uses no shadows.
- The sunset and dusk accents are for illustration only, never for chrome.
- Anti-references (see [`PRODUCT.md`](./PRODUCT.md)): no neon, no glassmorphism, no gradient text, no hero-metric template.

## Credits

Built on the [astro-creative-base](https://github.com/jankohlbach/astro-creative-base) starter by Jan Kohlbach. Brand direction and content are original.
