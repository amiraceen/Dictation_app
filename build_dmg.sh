#!/usr/bin/env bash
# Build "Kalam.app" and wrap it in a drag-to-Applications disk image: dist/Kalam.dmg
#
#   bash build_dmg.sh
#
# Runs on a Mac with Apple silicon (also used by .github/workflows/build-macos.yml).
# Signing: set SIGN_IDENTITY to a code-signing certificate name (e.g. "Developer ID
# Application: …" or "Dictation Local Signing"); without it the app is ad-hoc signed.
set -euo pipefail
cd "$(dirname "$0")"

APP_NAME="Kalam"
DMG_NAME="Kalam"
VERSION="${VERSION:-1.0}"
PY="${PYTHON:-python3}"

# 1. Python environment
if [ ! -d venv ]; then
    echo "→ Creating virtual environment…"
    "$PY" -m venv venv
fi
venv/bin/pip install --upgrade pip --quiet
venv/bin/pip install -r requirements.txt --quiet

# 2. Whisper model (bundled so the app works offline; ~460 MB, cached after the first run)
echo "→ Fetching the Whisper small model…"
venv/bin/python -c "from faster_whisper import download_model; print(download_model('small'))"

# 3. Build the .app
echo "→ Building ${APP_NAME}.app…"
rm -rf build dist
venv/bin/pyinstaller --noconfirm Dictation.spec
APP="dist/${APP_NAME}.app"
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString ${VERSION}" "$APP/Contents/Info.plist"

# 4. Sign
if [ -n "${SIGN_IDENTITY:-}" ]; then
    echo "→ Signing with \"${SIGN_IDENTITY}\"…"
    codesign --force --deep --options runtime --timestamp --entitlements entitlements.plist -s "$SIGN_IDENTITY" "$APP"
else
    echo "→ Ad-hoc signing (no SIGN_IDENTITY set)…"
    codesign --force --deep -s - "$APP"
fi
codesign --verify --deep --strict "$APP"

# 5. Disk image: the app plus an Applications shortcut to drag it onto
echo "→ Creating ${DMG_NAME}.dmg…"
STAGE="$(mktemp -d)"
ditto "$APP" "$STAGE/${APP_NAME}.app"
ln -s /Applications "$STAGE/Applications"
hdiutil create -volname "$APP_NAME" -srcfolder "$STAGE" -ov -format UDZO "dist/${DMG_NAME}.dmg"
rm -rf "$STAGE"
if [ -n "${SIGN_IDENTITY:-}" ]; then
    codesign --force --timestamp -s "$SIGN_IDENTITY" "dist/${DMG_NAME}.dmg"
fi

# 6. Optional notarization (needs a Developer ID identity above and an App Store Connect login)
if [ -n "${NOTARY_APPLE_ID:-}" ] && [ -n "${SIGN_IDENTITY:-}" ]; then
    echo "→ Notarizing…"
    xcrun notarytool submit "dist/${DMG_NAME}.dmg" --apple-id "$NOTARY_APPLE_ID" \
        --team-id "$NOTARY_TEAM_ID" --password "$NOTARY_PASSWORD" --wait
    xcrun stapler staple "dist/${DMG_NAME}.dmg"
fi

echo ""
echo "✓ dist/${DMG_NAME}.dmg ($(du -h "dist/${DMG_NAME}.dmg" | cut -f1))"
