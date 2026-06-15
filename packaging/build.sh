#!/bin/bash
# Build script Cicerone.app + Cicerone.dmg
#
# Sequenza:
#   1. pyinstaller --clean --noconfirm con cicerone.spec
#   2. verifica dist/Cicerone.app esiste
#   3. genera dist/Cicerone.dmg (create-dmg se disponibile, fallback hdiutil)
#
# Usage:
#   bash packaging/build.sh
#
# Output:
#   dist/Cicerone.app
#   dist/Cicerone.dmg

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

UV="${UV:-uv}"
if ! command -v "$UV" >/dev/null 2>&1; then
    if [ -x "$HOME/.local/bin/uv" ]; then
        UV="$HOME/.local/bin/uv"
    else
        echo "uv non trovato (cercato in PATH e ~/.local/bin/)" >&2
        exit 1
    fi
fi

echo "==> Pulizia build precedenti"
rm -rf build dist

echo "==> PyInstaller: building Cicerone.app"
"$UV" run pyinstaller packaging/cicerone.spec --clean --noconfirm

if [ ! -d "dist/Cicerone.app" ]; then
    echo "ERRORE: dist/Cicerone.app non generato dopo PyInstaller" >&2
    exit 1
fi

APP_SIZE_MB=$(du -sm dist/Cicerone.app | cut -f1)
echo "==> Cicerone.app pronto (${APP_SIZE_MB} MB)"

echo "==> Genero Cicerone.dmg"
DMG_PATH="dist/Cicerone.dmg"
rm -f "$DMG_PATH"

if command -v create-dmg >/dev/null 2>&1; then
    create-dmg \
        --volname "Cicerone" \
        --window-size 600 400 \
        --icon-size 128 \
        --icon "Cicerone.app" 150 200 \
        --app-drop-link 450 200 \
        --no-internet-enable \
        "$DMG_PATH" \
        "dist/Cicerone.app"
else
    echo "    (create-dmg non installato, uso hdiutil)"
    STAGING="dist/dmg_staging"
    rm -rf "$STAGING"
    mkdir -p "$STAGING"
    cp -R "dist/Cicerone.app" "$STAGING/"
    ln -s /Applications "$STAGING/Applications"
    hdiutil create \
        -volname "Cicerone" \
        -srcfolder "$STAGING" \
        -ov \
        -format UDZO \
        "$DMG_PATH"
    rm -rf "$STAGING"
fi

if [ ! -f "$DMG_PATH" ]; then
    echo "ERRORE: $DMG_PATH non generato" >&2
    exit 1
fi

DMG_SIZE_MB=$(du -m "$DMG_PATH" | cut -f1)
echo ""
echo "================================================================"
echo "  Build completato"
echo "    .app: dist/Cicerone.app (${APP_SIZE_MB} MB)"
echo "    .dmg: $DMG_PATH (${DMG_SIZE_MB} MB)"
echo "================================================================"
echo "Test: open $DMG_PATH"
