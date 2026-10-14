# Vault self-hosted apps implementation plan

> **For agentic workers:** Implement inline, following executing-plans. The owner
> approved implementation in this chat; no further design approval is needed.

**Goal:** Launch self-hosted openGym and FigCraft from the existing Vault.

**Architecture:** Keep upstream applications independent. Compose runs openGym's
official web/API images and nginx serving the verified FigCraft release ZIP.
Astro routes redirect to runtime URLs, retaining upstream UI.

**Tech Stack:** Astro 6 / Node, Docker Compose, official openGym images, nginx.

**Spec:** `docs/superpowers/specs/2026-10-14-vault-self-hosted-apps-design.md`

## Global constraints

- openGym 1.4.1; FigCraft 0.5.1, SHA-256 checked; no new npm dependencies.
- Preserve existing workout generator, workout data, and unrelated trading work.
- Upstream UI stays unmodified; retain licences and notices.
- Bind new ports through the existing BIND_HOST convention, default loopback.
- No FigCraft collaboration server, AI coach, or extra database.

## Task 1: Hosting

Files: `compose.yml`, `.env.example`, `ops/figcraft/Dockerfile`,
`ops/figcraft/nginx.conf`, `README.md`.

- [x] Add openGym API/web services with private API, persistent volume, runtime
  origin/passkey configuration, and web port 8091.
- [x] Add FigCraft Docker build: fetch published ZIP, verify SHA-256, unzip only
  into static web root, and serve via nginx at port 8092. Preserve all notices.
- [x] Configure WASM MIME, gzip, hashed-file caching and no-cache HTML.
- [x] Document local startup, production URL/origin settings, tunnel targets,
  openGym backup, and FigCraft's browser limitations.
- [x] Validate Compose and container build/startup when Docker is available.

## Task 2: Vault integration

Files: `src/pages/vault.astro`, `src/pages/vault/fitness.astro`,
`src/pages/vault/figcraft.astro`, `PRODUCT.md`, `DESIGN.md`.

- [x] Before edits, verify current Fitness returns the old browser and FigCraft
  is absent; use HTTP checks against Astro dev.
- [x] Replace Fitness with an on-demand redirect to PUBLIC_OPENGYM_URL,
  default `http://localhost:8091`.
- [x] Add FigCraft on-demand redirect to PUBLIC_FIGCRAFT_URL,
  default `http://localhost:8092`, and its Vault dock entry.
- [x] Record product behavior and the approved upstream UI exception.
- [x] Verify routes redirect to configured URLs, Vault includes both tools,
  FigCraft renders in-browser, and existing workout checks plus build pass.

## Finish

- [x] Review only the scoped diff; report validation and any deployment limits.

## Production deployment

- [x] Save the approved fitness.waiphyoaung.com and figcraft.waiphyoaung.com runtime URLs in the existing Dokploy service, preserving other settings.
- [ ] Add the two public hostnames to the existing Cloudflare tunnel.
- [ ] Publish the reviewed changes and verify the Dokploy deployment and live app responses.

Local checks passed: build, Astro diagnostics (only two existing trading hints),
workout picker/presets, production-runtime redirects, Compose interpolation,
FigCraft checksum, nginx syntax/headers, and Chrome rendering. The local Docker
engine is unresponsive; container runtime validation moves to Dokploy.
