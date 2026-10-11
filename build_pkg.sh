#!/usr/bin/env bash
# Build Dictation.app, sign it with the stable local certificate, install to /Applications.
# Stable signing keeps the Accessibility/Microphone permissions across rebuilds.
set -e
cd "$(dirname "$0")"
rm -rf build dist
venv/bin/pyinstaller --noconfirm Dictation.spec > build.log 2>&1
codesign --force --deep -s "Dictation Local Signing" dist/Dictation.app
pkill -f 'Dictation.app/Contents/MacOS/Dictation' || true
sleep 1
rm -rf /Applications/Dictation.app
ditto dist/Dictation.app /Applications/Dictation.app
open /Applications/Dictation.app
