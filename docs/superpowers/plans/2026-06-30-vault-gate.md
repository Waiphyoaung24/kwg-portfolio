# Vault Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a password-gated `/vault` page (client-side obscurity gate + empty tool-grid shell) to the static KWG portfolio.

**Architecture:** One standalone Astro page with two states (login form ⇄ tool grid), toggled by a `data-vault` attribute on `<html>`. A head inline script reads the `localStorage` flag before paint (no flash); a module script handles SHA-256 verification, login/logout, and focus. Hash compare uses a shared `sha256Hex` helper that has its own runnable self-check.

**Tech Stack:** Astro 6 (static output), TypeScript, Web Crypto (`crypto.subtle`), SCSS with existing design tokens, `@astrojs/sitemap`.

## Global Constraints

- Static site — `output` stays default (static); no SSR adapter, no server code.
- Obscurity gate only; never hardcode a secret the user didn't choose (ships a documented default + replace instructions).
- Styling uses existing tokens from `src/styles/` (CSS vars `--c-*`, `--fs-*`; `Space Grotesk`; square corners). Do not restyle the rest of the site.
- `/vault` is unlinked, `noindex`, and excluded from the sitemap.
- Node ≥ 24 (strips TS types natively — test runs `.mjs` importing `.ts`).

---

### Task 1: SHA-256 hex helper + self-check

**Files:**
- Create: `src/scripts/vault-hash.ts`
- Test: `src/scripts/vault-hash.test.mjs`

**Interfaces:**
- Produces: `export async function sha256Hex(text: string): Promise<string>` — lowercase 64-char hex digest. Imported by Task 2's page script.

- [ ] **Step 1: Write the failing test**

`src/scripts/vault-hash.test.mjs`:
```js
import assert from 'node:assert/strict';
import { sha256Hex } from './vault-hash.ts';

// Known vector: SHA-256("abc")
assert.equal(
  await sha256Hex('abc'),
  'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad',
);
console.log('ok: sha256Hex matches known vector');
```

- [ ] **Step 2: Run test, verify it fails**

Run: `node src/scripts/vault-hash.test.mjs`
Expected: FAIL — cannot resolve `./vault-hash.ts` (file does not exist yet).

- [ ] **Step 3: Write minimal implementation**

`src/scripts/vault-hash.ts`:
```ts
/** SHA-256 of `text` as lowercase hex. Web Crypto — runs in browser and Node 24+. */
export async function sha256Hex(text: string): Promise<string> {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');
}
```

- [ ] **Step 4: Run test, verify it passes**

Run: `node src/scripts/vault-hash.test.mjs`
Expected: PASS — prints `ok: sha256Hex matches known vector`.

- [ ] **Step 5: Commit**

```bash
git add src/scripts/vault-hash.ts src/scripts/vault-hash.test.mjs
git commit -m "✨ add sha256Hex helper with self-check"
```

---

### Task 2: The `/vault` page (gate + grid)

**Files:**
- Create: `src/pages/vault.astro`

**Interfaces:**
- Consumes: `sha256Hex` from `src/scripts/vault-hash.ts`.
- Behavior contract: `localStorage["kwg_vault"] === "1"` ⇒ unlocked. `<html data-vault="open|locked">` drives which section shows.

- [ ] **Step 1: Generate the password hash**

Pick a password and generate its hash (default below is `changeme`):
```bash
node -e "crypto.subtle.digest('SHA-256',new TextEncoder().encode('changeme')).then(b=>console.log([...new Uint8Array(b)].map(x=>x.toString(16).padStart(2,'0')).join('')))"
# changeme => 057ba03d6c44104863dc7361fe4578965d1887360f90a0895882e58a6248fc86
```

- [ ] **Step 2: Write the page**

`src/pages/vault.astro`:
```astro
---
import '../styles/index.scss';

// ── Vault password (obscurity gate, client-side only) ──────────────────
// SHA-256 hex of the password. Default password is "changeme" — REPLACE IT:
//   node -e "crypto.subtle.digest('SHA-256',new TextEncoder().encode('YOUR_PW')).then(b=>console.log([...new Uint8Array(b)].map(x=>x.toString(16).padStart(2,'0')).join('')))"
const VAULT_HASH = '057ba03d6c44104863dc7361fe4578965d1887360f90a0895882e58a6248fc86';

const placeholders = Array.from({ length: 6 });
---

<!doctype html>
<html lang="en" data-vault="locked">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="theme-color" content="#000000" />
    <meta name="robots" content="noindex" />
    <title>Vault — KWG</title>
    <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      rel="stylesheet"
      href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300..700&display=swap"
    />
    <!-- Decide state before paint → no flash of the wrong section. -->
    <script is:inline>
      document.documentElement.dataset.vault =
        localStorage.getItem('kwg_vault') === '1' ? 'open' : 'locked';
    </script>
  </head>

  <body data-vault-hash={VAULT_HASH}>
    <main class="vault">
      <!-- ── Login ─────────────────────────────────────────────── -->
      <section class="gate" id="gate" aria-labelledby="gate-title">
        <form class="gate__form" id="gate-form" novalidate>
          <p class="gate__eyebrow">KWG</p>
          <h1 class="gate__title" id="gate-title">Vault</h1>
          <label class="gate__label" for="gate-pw">Password</label>
          <input
            class="gate__input"
            id="gate-pw"
            name="password"
            type="password"
            autocomplete="current-password"
            autocapitalize="off"
            autocorrect="off"
            spellcheck="false"
            aria-describedby="gate-error"
            required
          />
          <p class="gate__error" id="gate-error" role="alert" aria-live="assertive" hidden>
            Incorrect password.
          </p>
          <button class="gate__submit" type="submit">Enter</button>
        </form>
      </section>

      <!-- ── Vault ─────────────────────────────────────────────── -->
      <section class="grid-wrap" id="vault" aria-labelledby="vault-title">
        <header class="grid-wrap__head">
          <h1 class="grid-wrap__title" id="vault-title" tabindex="-1">Vault</h1>
          <button class="grid-wrap__lock" type="button" id="logout">Lock</button>
        </header>
        <p class="grid-wrap__caption">Your handy tools live here.</p>
        <ul class="tools" role="list">
          {placeholders.map(() => (
            <li class="tool" aria-hidden="true">
              <span class="tool__plus">+</span>
              <span class="tool__hint">Add a tool</span>
            </li>
          ))}
        </ul>
      </section>
    </main>

    <script>
      import { sha256Hex } from '../scripts/vault-hash';

      const form = document.querySelector<HTMLFormElement>('#gate-form')!;
      const pw = document.querySelector<HTMLInputElement>('#gate-pw')!;
      const err = document.querySelector<HTMLParagraphElement>('#gate-error')!;
      const title = document.querySelector<HTMLHeadingElement>('#vault-title')!;
      const logout = document.querySelector<HTMLButtonElement>('#logout')!;
      const expected = document.body.dataset.vaultHash!;

      const setState = (s: 'open' | 'locked') => {
        document.documentElement.dataset.vault = s;
      };

      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        if ((await sha256Hex(pw.value)) === expected) {
          localStorage.setItem('kwg_vault', '1');
          err.hidden = true;
          pw.removeAttribute('aria-invalid');
          setState('open');
          title.focus();
        } else {
          err.hidden = false;
          pw.setAttribute('aria-invalid', 'true');
          pw.value = '';
          pw.focus();
        }
      });

      logout.addEventListener('click', () => {
        localStorage.removeItem('kwg_vault');
        setState('locked');
        pw.value = '';
        pw.focus();
      });

      // Focus the field when arriving locked.
      if (document.documentElement.dataset.vault !== 'open') pw.focus();
    </script>

    <style lang="scss">
      // States: head script sets html[data-vault]; CSS reveals one section.
      #gate,
      #vault {
        display: none;
      }
      :global(html[data-vault='locked']) #gate {
        display: grid;
      }
      :global(html[data-vault='open']) #vault {
        display: block;
      }

      .vault {
        min-height: 100svh;
        background: var(--c-dark);
        color: var(--c-light);
        font-family: var(--ff-primary);
      }

      // ── Login ──────────────────────────────────────────────
      .gate {
        min-height: 100svh;
        place-items: center;
        padding: to-rem(24);
      }
      .gate__form {
        display: grid;
        gap: to-rem(12);
        width: min(100%, to-rem(360));
      }
      .gate__eyebrow {
        margin: 0;
        font-size: var(--fs-label);
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: var(--c-on-surface-muted);
      }
      .gate__title {
        margin: 0 0 to-rem(8);
        font-size: var(--fs-3);
        line-height: 0.95;
        text-transform: uppercase;
      }
      .gate__label {
        font-size: var(--fs-label);
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--c-on-surface-muted);
      }
      .gate__input {
        appearance: none;
        width: 100%;
        padding: to-rem(14) to-rem(16);
        background: var(--c-surface-1);
        border: 1px solid var(--c-surface-2);
        color: var(--c-light);
        font: inherit;
        transition: border-color 0.2s var(--ease-smooth);

        &:hover {
          border-color: var(--c-on-surface-muted);
        }
        &:focus-visible {
          outline: 2px solid var(--c-accent);
          outline-offset: 2px;
          border-color: var(--c-accent);
        }
        &[aria-invalid='true'] {
          border-color: var(--c-accent);
        }
      }
      .gate__error {
        margin: 0;
        font-size: var(--fs-label);
        letter-spacing: 0.04em;
        color: var(--c-accent);
      }
      .gate__submit {
        margin-top: to-rem(4);
        padding: to-rem(14) to-rem(20);
        background: var(--c-accent);
        color: var(--c-dark);
        border: none;
        font: inherit;
        font-weight: var(--fw-medium);
        letter-spacing: 0.08em;
        text-transform: uppercase;
        cursor: pointer;
        transition: background 0.2s var(--ease-smooth);

        &:hover {
          background: var(--c-accent-hover);
        }
        &:focus-visible {
          outline: 2px solid var(--c-light);
          outline-offset: 2px;
        }
      }

      // ── Vault grid ─────────────────────────────────────────
      .grid-wrap {
        max-width: var(--grid-max-width);
        margin-inline: auto;
        padding: clamp-fluid(24, 56) var(--grid-margin);
      }
      .grid-wrap__head {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: to-rem(16);
      }
      .grid-wrap__title {
        margin: 0;
        font-size: var(--fs-2);
        line-height: 0.95;
        text-transform: uppercase;

        &:focus-visible {
          outline: 2px solid var(--c-accent);
          outline-offset: 4px;
        }
      }
      .grid-wrap__lock {
        background: transparent;
        border: 1px solid var(--c-surface-2);
        color: var(--c-light);
        padding: to-rem(8) to-rem(16);
        font: inherit;
        font-size: var(--fs-label);
        letter-spacing: 0.12em;
        text-transform: uppercase;
        cursor: pointer;
        transition:
          border-color 0.2s var(--ease-smooth),
          color 0.2s var(--ease-smooth);

        &:hover {
          border-color: var(--c-accent);
          color: var(--c-accent);
        }
        &:focus-visible {
          outline: 2px solid var(--c-accent);
          outline-offset: 2px;
        }
      }
      .grid-wrap__caption {
        margin: to-rem(8) 0 clamp-fluid(24, 40);
        color: var(--c-on-surface-muted);
      }
      .tools {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(to-rem(220), 1fr));
        gap: clamp-fluid(12, 20);
        margin: 0;
        padding: 0;
        list-style: none;
      }
      .tool {
        display: grid;
        place-content: center;
        gap: to-rem(8);
        aspect-ratio: 4 / 3;
        background: var(--c-surface-1);
        border: 1px dashed var(--c-surface-2);
        color: var(--c-on-surface-muted);
        text-align: center;
      }
      .tool__plus {
        font-size: var(--fs-4);
        line-height: 1;
        color: var(--c-surface-2);
      }
      .tool__hint {
        font-size: var(--fs-label);
        letter-spacing: 0.12em;
        text-transform: uppercase;
      }
    </style>
  </body>
</html>
```

- [ ] **Step 3: Build & verify it compiles**

Run: `yarn build`
Expected: PASS — `astro check` clean, `dist/vault/index.html` emitted.

- [ ] **Step 4: Manual verification**

Run: `yarn dev`, open `/vault`.
- Locked on first visit; password field focused.
- Wrong password → "Incorrect password." announced, field cleared/refocused, grid stays hidden.
- Correct password (`changeme`) → grid shows, focus on "Vault" heading, no login flash.
- Reload → straight to grid (flag persisted).
- "Lock" → back to login, field focused; reload stays locked.
- Keyboard-only: Tab reaches input → submit; Enter submits; focus rings visible.

- [ ] **Step 5: Commit**

```bash
git add src/pages/vault.astro
git commit -m "✨ add password-gated /vault page with tool-grid shell"
```

---

### Task 3: Hide `/vault` from the sitemap

**Files:**
- Modify: `astro.config.mjs` (sitemap integration call)

- [ ] **Step 1: Add the filter**

In `astro.config.mjs`, change the `sitemap({ … })` call to exclude `/vault`:
```js
    sitemap({
      filter: (page) => !page.includes('/vault'),
      lastmod: new Date(),
      xslURL: '/sitemap.xsl',
    }),
```

- [ ] **Step 2: Build & verify exclusion**

Run: `yarn build && grep -rl vault dist/sitemap*.xml; echo "exit: $?"`
Expected: no sitemap file lists `/vault` (grep finds nothing).

- [ ] **Step 3: Commit**

```bash
git add astro.config.mjs
git commit -m "🔒 exclude /vault from sitemap"
```

---

## Self-Review

**Spec coverage:**
- Obscurity model, one-page two-state, standalone (no Layout) → Task 2. ✓
- localStorage stay-logged-in + logout → Task 2 script. ✓
- SHA-256 compare + helper self-check → Tasks 1–2. ✓
- Empty tool grid in Lambo-dark styling → Task 2 markup + styles. ✓
- A11y (label, alert region, focus management, focus rings) → Task 2. ✓
- noindex meta → Task 2 head; sitemap exclusion → Task 3; unlinked → no nav edits anywhere. ✓
- Password-setup command + replaceable default → Task 2 Step 1 + frontmatter comment. ✓

**Placeholder scan:** None. The `changeme` default + `// REPLACE IT` is an intended, documented config value, not a plan gap.

**Type consistency:** `sha256Hex(text: string): Promise<string>` defined in Task 1, consumed identically in Task 2. `data-vault` values `open`/`locked` and `localStorage` key `kwg_vault` used consistently across head script, module script, and CSS.
