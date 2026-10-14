# Vault: self-hosted openGym and FigCraft

Approved by the owner on 2026-10-14: self-host both apps, keep their own UI,
and use the simplest setup. This approval covers implementation.

## Approach

Keep upstream apps independent from Astro. Add openGym's official web/API images
and a static nginx container for FigCraft's published browser ZIP to compose.yml.
Pin openGym to 1.4.1 and FigCraft to 0.5.1; verify the FigCraft download against
the release SHA-256. Preserve bundled notices and licences. No source forks,
Rust builds, extra database, AI coach, or FigCraft collaboration server.

## Vault integration

Fitness remains `/vault/fitness`, which redirects to the self-hosted openGym URL.
Add a FigCraft entry at `/vault/figcraft`, redirecting to its self-hosted URL.
Launch full pages: openGym denies iframe embedding, and full pages give FigCraft
all available space. URLs are runtime environment variables, following the
existing Notes/Finance deployment pattern. Local defaults use ports 8091 and 8092.
The existing workout generator is retained for old bookmarks, with no migration
or deletion of existing data. Site navigation keeps its current styling.
The owner explicitly approved upstream app interfaces retaining their own UI.

## Hosting and data

openGym's API has no host port; its web container proxies `/api` on the same
origin. A named volume holds all openGym data and must be backed up. Its own
profile login protects workout data; the Vault's client gate is only obscurity.
Configure its origin and passkey hostname to match its HTTPS production domain.
The owner selected `fitness.waiphyoaung.com` and `figcraft.waiphyoaung.com`
for production on the existing Dokploy server.
New host ports follow the existing loopback/tunnel BIND_HOST convention.

FigCraft is an unmodified static browser app, requiring WebGPU or WebGL2.
nginx serves correct WASM MIME types, compression, hashed-asset caching, and
no-cache HTML. Files remain on the user's device; this integration adds no
server file storage or cross-device sync. Browser file-saving limitations must
be reported from verification rather than assuming desktop capability parity.

## Verification

Check Compose interpolation and service wiring; verify the downloaded release
checksum and static asset response types; exercise both runtime redirects and
Vault entries; load FigCraft in a real browser; run Astro checks/build and the
existing workout picker/preset tests. Run containers if the local Docker engine
is available. Report production deployment or runtime checks that cannot run.
