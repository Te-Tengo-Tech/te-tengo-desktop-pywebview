#!/usr/bin/env bash
# Packages the PyInstaller macOS build into a compressed disk image with an Applications link, so the
# user drags «Te Tengo Captura» into Applications (docs/RELEASES.md). Only macOS tools (hdiutil).
#
#   packaging/macos/crear-dmg.sh ["dist/Te Tengo Captura.app"] [dist/te-tengo-captura.dmg]
#
# With TT_MACOS_IDENTIDAD_FIRMA set (a Developer ID Application identity in the keychain), it also
# signs the disk image, which notarization expects; otherwise the image is left unsigned (the app
# inside keeps its own signature).
set -euo pipefail

APP="${1:-dist/Te Tengo Captura.app}"
DMG="${2:-dist/te-tengo-captura.dmg}"
VOLUMEN="Te Tengo Captura"

if [[ ! -d "$APP" ]]; then
  echo "Missing $APP: build it first with: uv run pyinstaller packaging/te-tengo-captura.spec --noconfirm" >&2
  exit 1
fi

contenido=$(mktemp -d)
trap 'rm -rf "$contenido"' EXIT
# ditto keeps the bundle's symlinks, extended attributes and code signature intact.
ditto "$APP" "$contenido/$(basename "$APP")"
ln -s /Applications "$contenido/Applications"

mkdir -p "$(dirname "$DMG")"
rm -f "$DMG"
hdiutil create -volname "$VOLUMEN" -srcfolder "$contenido" -fs HFS+ -format UDZO -ov "$DMG"

if [[ -n "${TT_MACOS_IDENTIDAD_FIRMA:-}" ]]; then
  codesign --force --sign "$TT_MACOS_IDENTIDAD_FIRMA" --timestamp "$DMG"
fi
hdiutil verify "$DMG"
echo "Disk image: $DMG ($(du -h "$DMG" | cut -f1))"
