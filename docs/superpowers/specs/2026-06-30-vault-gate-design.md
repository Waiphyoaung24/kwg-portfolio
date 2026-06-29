# Vault Gate — Design Spec

**Date:** 2026-06-30
**Status:** Approved direction, pending spec review

## Goal

Add a password-gated `/vault` page to the static KWG portfolio — a private home
for "handy tools." This release ships the **gate + empty tool-grid shell**; no
real tools yet.

## Protection model (read this first)

The site is **fully static** (`serve dist`, no SSR/API). Therefore the gate is
an **obscurity gate**, not real security: the password hash and page content
ship in the browser bundle and a technical user can bypass it. This is an
accepted, explicit choice for personal-but-not-sensitive tools.

- Anything genuinely sensitive must NOT live in the vault.
- If real privacy is ever needed, upgrade path = Astro SSR + middleware, or an
  auth proxy in front. Out of scope here.

## Architecture

**One page, two states.** `src/pages/vault.astro` is a single self-contained
document holding both the login form and the tool grid. A client script toggles
visibility. No separate `/login` route, no redirect, no flash of vault content
(grid starts hidden; script reveals it only after the unlock check).

The page is **standalone** — it does NOT use `Layout.astro` (which pulls in the
3D `Canvas`, `Splash`, and scroll chrome — wrong for a focused utility screen).
It imports `../styles/index.scss` for the design tokens/fonts and defines its
own scoped styles. `Header`/`Footer` are omitted for a clean, focused gate.

### Auth flow (inline client script)

1. **On load:** if `localStorage["kwg_vault"] === "1"` → show grid, hide login.
   Else → show login form, autofocus the password field.
2. **On submit:** `crypto.subtle.digest('SHA-256', <entered>)` → hex string →
   compare to stored `VAULT_HASH` constant.
   - Match → `localStorage["kwg_vault"]="1"`, hide login, show grid, move focus
     to the grid heading.
   - No match → show inline error via `aria-live="assertive"`, clear + refocus
     the field. No lockout/rate-limit (meaningless client-side).
3. **Logout** button in the grid → remove the flag, show login again.

### Password setup

`VAULT_HASH` is seeded with a **placeholder hash** and a `// replace this`
comment. The user generates their own with a one-liner (documented in the page
comment), e.g.:

```bash
node -e "crypto.subtle.digest('SHA-256',new TextEncoder().encode('YOUR_PW')).then(b=>console.log([...new Uint8Array(b)].map(x=>x.toString(16).padStart(2,'0')).join('')))"
```

No secret the user didn't choose is ever hardcoded.

## The empty grid

- A heading (e.g. "VAULT") + short caption.
- Responsive card grid of "add your tools here" placeholder cards — the slot for
  future tools.
- A logout control.
- Styled in the existing Lamborghini-dark system: true-black canvas, white text,
  `#FFC000` gold accent on the primary action, square corners (`rounded.none`),
  `Space Grotesk` via the global tokens.

## Accessibility (frontend-a11y)

- Real `<form>` with a visible `<label>` bound to the password `<input
  type="password">`.
- Submit via a real `<button type="submit">` — Enter works natively.
- Error region: `role="alert"` / `aria-live="assertive"`, text-based (not
  color-only); input gets `aria-invalid="true"` on failure.
- Focus management: autofocus password on load; on unlock move focus to the grid
  heading (`tabindex="-1"`); on logout return focus to the password field.
- Visible focus rings; sufficient contrast (white/gold on black already passes).

## Discoverability

- **Unlinked secret URL** — nothing in nav/header/footer links to `/vault`.
- `<meta name="robots" content="noindex">` on the page.
- Exclude `/vault` from the sitemap via the `@astrojs/sitemap` `filter` option in
  `astro.config.mjs`.

## Verification

- Build passes: `yarn build` (runs `astro check`).
- Manual: wrong password → error, no reveal; correct password → grid + flag set;
  reload → straight to grid; logout → back to login.
- One runnable check: a tiny self-check asserting the SHA-256 hex helper matches
  a known vector (e.g. hash of `"abc"`), so the compare logic can't silently rot.

## Explicitly out of scope (YAGNI)

Real auth/SSR, session expiry, rate-limiting, password reset, multiple users,
and any actual tools. None requested; none meaningful in an obscurity gate.

## Files touched

- `src/pages/vault.astro` — new (gate + grid + inline script + scoped styles).
- `astro.config.mjs` — add sitemap `filter` excluding `/vault`.
- (optional) a tiny test for the hex-hash helper.
