#!/bin/bash
set -euo pipefail

source_dir="$(cd "$(dirname "$0")" && pwd)"
rust_compiler="${RUSTC:-$HOME/.cargo/bin/rustc}"
destination="/Applications/KWG Vault Launcher.app"
build_dir="$(mktemp -d)"
trap 'rm -rf "$build_dir"' EXIT
bundle="$build_dir/KWG Vault Launcher.app"

"$rust_compiler" --edition=2024 --test "$source_dir/main.rs" -o "$build_dir/tests"
"$build_dir/tests"
osacompile -o "$bundle" "$source_dir/launcher.applescript"
"$rust_compiler" --edition=2024 -C opt-level=s -C strip=symbols \
    "$source_dir/main.rs" -o "$bundle/Contents/MacOS/vault-launcher"
plist="$bundle/Contents/Info.plist"
plutil -replace CFBundleIdentifier -string com.waiphyoaung.vault-launcher "$plist"
plutil -replace CFBundleName -string 'KWG Vault Launcher' "$plist"
plutil -replace CFBundleShortVersionString -string 1.0.0 "$plist"
plutil -replace LSUIElement -bool true "$plist"
plutil -replace CFBundleURLTypes -json '[{"CFBundleURLName":"Vault desktop apps","CFBundleTypeRole":"Viewer","CFBundleURLSchemes":["kwg-vault"]}]' "$plist"
codesign --force --sign - "$bundle"
if [ -e "$destination" ]; then
    echo "Already installed: $destination. Move the existing launcher aside before reinstalling." >&2
    exit 1
fi
ditto "$bundle" "$destination"
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$destination"
echo "Installed $destination"
