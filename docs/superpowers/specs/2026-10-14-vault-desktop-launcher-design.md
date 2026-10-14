# Vault desktop apps

Approved by the owner on 2026-10-14: finish FigCraft and open its five downloaded
examples, then install Sagar and launch both desktop apps from Vault. Use Rust
and the smallest setup; keep both upstream interfaces.

## Design

Install FigCraft's official macOS release and build Sagar's existing Tauri/Rust
app from its pinned upstream source. Keep documents on this Mac. The existing
FigCraft browser deployment remains available at its subdomain.

A small local KWG Vault Launcher app handles exactly `kwg-vault://figcraft`
and `kwg-vault://sagar`. Its Rust executable matches the entire URL and launches
only the corresponding installed application with fixed arguments. Reject all
other input, including paths, queries and extra arguments. It has no listener,
network access, document access or background service. A minimal macOS
AppleScript event adapter passes the URL to the Rust executable using shell
quoting; Rust owns all validation and process launching.

Reuse Vault's existing dock: FigCraft and Sagar link to the local handler and
say “Open on Mac”. Existing `/vault/figcraft` bookmarks retain browser access;
the dock is the approved desktop entry point. No new visual surface or redesign.

## Verification

Verify all five example tabs and rendered content in FigCraft. Build and open
Sagar. Test the Rust allowlist with valid URLs and malicious/unsupported values,
then test the installed handler from browser links. Run the portfolio build and
verify deployed Vault links. Document that other devices require local app and
launcher installation; no cross-device sync is promised.
