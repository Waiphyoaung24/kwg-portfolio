# Vault Desktop Launcher Implementation Plan

**Goal:** Open FigCraft and Sagar from Vault on this Mac, with all five FigCraft examples loaded.

**Architecture:** Keep upstream desktop apps intact. Two exact custom URLs are
handled by a Rust executable inside a small macOS app bundle. Reuse the Vault dock.

**Tech Stack:** Rust standard library, macOS URL events, Astro, Sagar's Tauri 2 build.

**Spec:** `docs/superpowers/specs/2026-10-14-vault-desktop-launcher-design.md`

## Constraints

- No web port, background server, arbitrary file opener or shell command endpoint.
- Native apps keep their original UI; dock keeps the existing design.
- Finish FigCraft first. Build unmodified Sagar from a recorded commit.
- Explicit user approval above covers installation and the launcher integration.

## Tasks

- [x] Install official FigCraft v0.5.1, verify SHA-256 and Gatekeeper assessment,
  open five `.figcraft` examples through its supported file arguments, inspect tabs/render.
- [x] Build Sagar using `bun install --frozen-lockfile` and
  `bun tauri build --bundles app`; install and inspect its library screen.
- [x] Add `ops/vault-launcher/main.rs`, native URL event adapter and installer.
  Tests assert only `kwg-vault://figcraft` and `kwg-vault://sagar` (with optional
  terminal slash) resolve; paths, queries, fragments, shell text and other schemes fail.
  Run `rustc --test` and the resulting test executable before installing.
- [x] Point the existing FigCraft dock item at `kwg-vault://figcraft`; add
  Sagar with `kwg-vault://sagar` and “Open on Mac” hints. Update PRODUCT and README.
- [x] Run portfolio build, test both browser links against installed apps,
  review the diff, deploy and verify both production link targets.

## Evidence / decisions

- FigCraft's official release checksum matched; Gatekeeper accepted the app as
  Notarized Developer ID. Strict codesign reported upstream resource/signature
  issues even on the mounted source; no signature or security setting was changed.
- All five examples are visible as native editor tabs, with the dashboard rendered.
- Sagar has no published GitHub release, so a local source build is required.
- Sagar's release build succeeded from commit `b7b5fb062d5010b274b5410e04424b2ea7729689`;
  installed `/Applications/Sagar.app` and verified its Library / Import EPUB screen.
- Rust allowlist tests passed (2); portfolio build passed (0 errors/warnings,
  2 existing trading hints). Independent code review found no actionable issues.
- Browser automation forbids custom app URL navigation. The owner manually
  clicked both exact URLs on a local verification page and confirmed each app opens.
- Reopened FigCraft examples with absolute paths so Recent Files works from
  subsequent desktop launches. No example contents were changed.
- Deployed `0aa2ac3` through Dokploy; log finished with `Docker Compose Deployed: ✅`.
  Fetched production `/vault` and asserted both exact desktop URLs and both
  “Open on Mac” hints. Temporary local verification servers were stopped.
