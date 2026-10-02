# Dashboard unsupported-browser guidance — design

Date: 2026-10-02. Surface: `/vault/dashboard` (all six pages, reported on Knowledge).

## Problem

In Brave the dashboard shows "This browser cannot edit local folders here" and a
disabled Choose folder button. Cause: Brave disables the File System Access API
(`showDirectoryPicker`) by default, so `supported()` in
`dashboard/src/local-vault.mjs` is false. The vault code works: the repo browser
check passes in Chromium. The unsupported screen is confusing:

1. It does not say which requirement failed or how to fix it.
2. The overview says "Choose a folder above, or reconnect its saved permission",
   but both actions are unavailable.
3. New note, Quick capture and Create a note look usable but only report
   "Connect a folder before creating a note."

## Decision (approach A)

Explain the exact cause, remove the contradiction, disable actions that cannot
work. No storage fallback (the approved spec forbids a silent browser-database
fallback). No change to permission, save, lock or history behavior.

### 1. Support reason — `local-vault.mjs`

Add `unsupportedReason()` next to `supported()`. It returns, first match wins:

| Return | Condition |
| --- | --- |
| `null` | `supported()` is true |
| `'insecure'` | `isSecureContext` is false |
| `'brave'` | picker missing and `navigator.brave` exists |
| `'browser'` | anything else (picker, IndexedDB or Web Locks missing) |

`supported()` stays as is; `unsupportedReason()` is derived from the same checks.
Brave detection only selects help text; it never enables or blocks access.

### 2. Folder panel copy — `App.tsx`

Replace the single unsupported sentence with one per reason:

- `insecure`: "Folder access needs a secure page. Open this dashboard over
  HTTPS, or on localhost for development. No notes have been read."
- `brave`: "Brave turns off folder access by default. To use this dashboard in
  Brave, open brave://flags/#file-system-access-api, set it to Enabled, then
  relaunch Brave. Or use a current desktop Edge or Chrome. No notes have been
  read." The flag address is rendered as `<code>` text; web pages cannot link
  to `brave://` URLs.
- `browser`: existing sentence, kept.

### 3. Overview empty state — `App.tsx`

When unsupported, the "No folder connected" panel reads "Folder access is not
available in this browser. See the steps above." Otherwise unchanged.

### 4. Create actions — `App.tsx`

`#capture`, `#create` and `#empty-create` are `disabled` while `connected` is
false. The existing guard in `openNew` stays as a backstop.

### 5. Docs

Add the Brave flag to the Browser support section of `dashboard/README.md`.

## Styling

Reuse existing classes and tokens. One rule, `.folder-panel code
{font-family:var(--ff-mono)}`, sets the flag address in the existing mono
token. It stays lowercase because it is an address the user must type exactly. No
new raw values. Disabled buttons use the existing disabled opacity.

## Testing

- Unit (`dashboard/local-vault.test.mjs`): `unsupportedReason()` returns each of
  the four values with stubbed `globalThis` properties.
- Browser (`dashboard/browser-check.mjs`, unsupported block): also stub
  `navigator.brave`; assert the Brave text and flag address, the new overview
  text, and that the three create buttons are disabled.
- Run `node --test dashboard/*.test.mjs`, the dashboard build (`tsc` + Vite) and
  the browser check in Chromium. Manual: reload in Brave without the flag and
  confirm the guidance.

## Out of scope

Storage fallbacks, import/export, Firefox/Safari support, enabling the flag for
the user, and existing Brave Shields settings.
