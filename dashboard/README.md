# Local vault dashboard

The public page at `/vault/dashboard` runs the editor in the browser. It has no notes API, note database, telemetry, or upload path. Existing portfolio vault password UI is an obscurity gate, not authentication; the dashboard does not rely on it to protect remote notes because it stores no remote notes.

## Use

Open `/vault/dashboard?page=today&workspace=personal` or `?page=knowledge&workspace=parallel`. Open the Settings tab to choose, reconnect, or forget a folder for the selected workspace. Back to vault is at the top of the sidebar. On phones and tablets, use Pages to expand navigation; Escape closes it and returns focus to Pages. Choose a folder explicitly for each workspace. Use separate non-nested vault folders. The browser asks for read/write access. Choose only folders you trust this website to access: permissions and IndexedDB storage are origin-scoped, not route-scoped. Other trusted code on this origin shares that security boundary.

Directory handles, not note contents, are remembered in IndexedDB. Permission can expire or be revoked. Reconnect folder asks again only when clicked. Forget folder removes the saved handle, not files or browser permission; revoke permission in browser site settings. Changes to a workspace binding in another tab invalidate old bindings before the next file operation.

Reconnect folder keeps the active draft and its original file version. After restoring permission, save the draft explicitly. If another editor changed the file, the normal conflict check still applies. A permission-denied save changes the connection status to Folder not connected and keeps the draft in the tab.

The six flat folders are journal, knowledge, projects, reviews, founder, and inbox. Files must use supported Markdown names and be at most 1 MiB. Nested notes, attachments, and other filenames are skipped. Empty folders are created only when saving a new note. No sample content is created on connection.

Save is explicit. The editor compares content hashes, serializes this origin's mutations with Web Locks, and writes the prior version to the chosen vault's `.history` before replacing a note. Browser writable streams commit on close. Native Obsidian cannot participate in browser locks: a very small race remains between the final comparison and commit. Avoid editing the same file simultaneously in both apps; local history is a recovery aid, not a complete backup system. A failed first save may leave an empty newly created file; the draft stays in the tab.

## Browser support

Use current desktop Microsoft Edge or Chrome on HTTPS (localhost works for development). The folder picker is not supported everywhere. Firefox and WebKit do not have supported directory-picker coverage for this integration. Brave disables folder access by default; enable `brave://flags/#file-system-access-api`, then relaunch Brave. Unsupported browsers show the failed requirement (secure page, Brave setting, or browser) and disable connection and create actions; there is no silent browser-database fallback. The page requires a network load initially; an already open page can edit a connected local folder offline. No service worker is installed.

Official references:
- https://developer.chrome.com/docs/capabilities/web-apis/file-system-access
- https://developer.mozilla.org/en-US/docs/Web/API/Window/showDirectoryPicker
- https://developer.mozilla.org/en-US/docs/Web/API/FileSystemHandle/requestPermission

## Development

The dashboard uses daisyUI 5 with a single custom dark `kwg` theme, the
dashboard-only exception recorded in DESIGN.md. The theme lives in
`src/styles.css` (`@plugin "daisyui/theme"`; built-in themes are disabled);
`shared/tokens.css` owns layout geometry. The Astro route sets
`data-theme="kwg"` and does not import the marketing stylesheet. Dark mode is
permanent.

Use daisyUI classes on plain elements (`btn`, `input`, `select`, `menu`,
`card`, `stats`, `steps`, `badge`, `modal`). There is no component wrapper
layer. The New note dialog is a native `<dialog class="modal">`. The workspace
dropdown (`src/WorkspaceMenu.tsx`) implements the menu-radio keyboard pattern
itself; keep its arrow, Home/End and Escape handling when editing it. The rail
is a daisyUI `drawer`, open at `lg` and a Pages drawer below it.

Goal panels on Today and Founder read typed frontmatter through
`shared/goal-model.js`: `type: goals` in `founder/`, `type: lead` in
`founder/`, `type: niche` in `founder/`, and `type: conversation` anywhere.
Milestone dates match GitHub milestones M1-M4 for 2026.

Use Node 24 or later. Install the portfolio's locked dependencies with `yarn install --frozen-lockfile`, and the isolated dashboard dependencies with `npm ci --prefix dashboard --ignore-scripts`. Then run `node scripts/build-dashboard.mjs` and `node node_modules/astro/bin/astro.mjs dev --host 127.0.0.1 --port 4327`.

The dashboard bundle is generated into ignored `public/dashboard-assets`. `npm run build` builds the dashboard, checks Astro, and builds the site. Docker builds the same browser bundle before Astro; no database or credentials are needed by the dashboard. This change does not deploy or migrate any data.

## Verification

- `node --test dashboard/*.test.mjs`: isolated adapter tests, graph, Wai-G templates, and the goal model.
- `node dashboard/browser-check.mjs`: requires a local production preview at port 4327, or DASHBOARD_ORIGIN. Uses Microsoft Edge on Windows, Google Chrome on macOS, or DASHBOARD_BROWSER, a new temporary browser profile, real OPFS directory handles, and deterministic chooser/permission substitutes. It checks persistence, cancellation, permission denial, stale writes, workspace isolation, drafts, templates, graph, dark styling, all seven pages at six viewport sizes, centered desktop content, and the compact mobile Pages menu with keyboard and Escape checks, and absence of note-upload requests.
- Native Windows chooser was opened during verification, but desktop automation did not complete its confirmation. Manual check remains: choose an empty temporary folder, grant access, create/save a note, confirm the Markdown file on disk, reload and reconnect, then revoke permission and confirm a save retains the draft. Do not use a real private vault for this first check.
- Automated checks do not constitute a screen-reader audit or native Firefox/WebKit folder-access certification.

The neutral dark migration also checks rendered text contrast (4.5:1), rounded
rectangular actions, keyboard workspace-menu navigation, dialog focus entry and
restoration, search-icon clearance, selected-editor height, long titles at
320 pixels, reachable Save controls at a 200% zoom equivalent, reduced motion,
and JavaScript-disabled guidance in the first viewport. Production screenshots
use synthetic notes in temporary browser storage.

The graph regression checks confirm that titles and paths stack inside each
control without horizontal overflow, and remain readable at rest, on keyboard
focus, and on pointer hover.

The browser check also exercises create, edit, save, reopen, search, wiki links, backlinks, graph opening, dated journal entries, weekly reviews, founder actions and project notes in both temporary workspaces. It reads saved OPFS content back through browser handles. This verifies browser storage operations, not native Windows folder permission or a visible Markdown file in a user-selected directory.

No Personal/Parallel notes, history, credentials, business source documents, screenshots, or Obsidian settings are part of this integration. See THIRD_PARTY.md for code attribution.
