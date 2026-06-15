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

# Stage bundle FUORI da iCloud Drive (Desktop sync ri-applica xattr
# com.apple.fileprovider.fpfs#P e FinderInfo, che invalidano la firma).
# Lavoriamo in /tmp dove iCloud non tocca.
STAGE_DIR="/tmp/cicerone_build_$$"
echo "==> Stage bundle in $STAGE_DIR (fuori da iCloud)"
rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR"
ditto --norsrc --noextattr --noacl dist/Cicerone.app "$STAGE_DIR/Cicerone.app"

# Ad-hoc re-sign: PyInstaller firma il binario PRIMA di COLLECT, quindi i file
# aggiunti dopo invalidano il seal. macOS interpreta seal rotto come "danneggiato"
# (errore senza nemmeno prompt Gatekeeper). Rifirmiamo tutto deep ad-hoc.
echo "==> Ri-firma ad-hoc deep del bundle"
codesign --force --deep --sign - "$STAGE_DIR/Cicerone.app"
codesign --verify --deep --strict "$STAGE_DIR/Cicerone.app" && echo "    firma valida"

# Sostituisci app in dist/ con quella firmata e pulita
rm -rf dist/Cicerone.app
ditto --norsrc --noextattr --noacl "$STAGE_DIR/Cicerone.app" dist/Cicerone.app

echo "==> Genero Cicerone.dmg (in $STAGE_DIR per evitare xattr iCloud)"
DMG_PATH="dist/Cicerone.dmg"
STAGE_DMG="$STAGE_DIR/Cicerone.dmg"
rm -f "$DMG_PATH"

if command -v create-dmg >/dev/null 2>&1; then
    ( cd "$STAGE_DIR" && create-dmg \
        --volname "Cicerone" \
        --volicon "$ROOT/packaging/icon.icns" \
        --window-pos 200 120 \
        --window-size 640 420 \
        --icon-size 128 \
        --text-size 13 \
        --icon "Cicerone.app" 170 200 \
        --app-drop-link 470 200 \
        --hide-extension "Cicerone.app" \
        --no-internet-enable \
        "$STAGE_DMG" \
        "Cicerone.app" )
else
    echo "    (create-dmg non installato, uso hdiutil)"
    STAGING="$STAGE_DIR/dmg_staging"
    rm -rf "$STAGING"
    mkdir -p "$STAGING"
    ditto --norsrc --noextattr --noacl "$STAGE_DIR/Cicerone.app" "$STAGING/Cicerone.app"
    ln -s /Applications "$STAGING/Applications"
    hdiutil create \
        -volname "Cicerone" \
        -srcfolder "$STAGING" \
        -ov \
        -format UDZO \
        "$STAGE_DMG"
    rm -rf "$STAGING"
fi

# Sposta DMG firmato in dist/, strip xattr finale (iCloud non lo tocca prima del move)
mv "$STAGE_DMG" "$DMG_PATH"
xattr -cr "$DMG_PATH" 2>/dev/null || true
rm -rf "$STAGE_DIR"

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
