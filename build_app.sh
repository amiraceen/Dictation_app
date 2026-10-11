#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

APP="/Applications/Dictation.app"
MACOS="$APP/Contents/MacOS"
RESOURCES="$APP/Contents/Resources"

pkill -x Dictation 2>/dev/null || true; sleep 0.4
rm -rf "$APP"
mkdir -p "$MACOS" "$RESOURCES"

echo "→ Compiling…"
clang -O2 -fobjc-arc -fmodules \
  -mmacosx-version-min=13.0 \
  -framework Cocoa -framework AVFoundation \
  -framework Speech -framework Carbon \
  -o "$MACOS/Dictation" main.m

cat > "$APP/Contents/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleIdentifier</key>      <string>com.dictation.app</string>
  <key>CFBundleName</key>            <string>Dictation</string>
  <key>CFBundleExecutable</key>      <string>Dictation</string>
  <key>CFBundleVersion</key>         <string>3.0</string>
  <key>CFBundleIconFile</key>
    <string>AppIcon</string>
  <key>LSUIElement</key>             <true/>
  <key>NSMicrophoneUsageDescription</key>
    <string>Dictation uses your microphone to record speech.</string>
  <key>NSSpeechRecognitionUsageDescription</key>
    <string>Dictation converts your speech to text.</string>
</dict></plist>
PLIST

tccutil reset Accessibility com.dictation.app 2>/dev/null || true
codesign --force --deep -s - "$APP" 2>/dev/null || true

echo ""
echo "✅  Dictation.app is on your Desktop!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  1. Quit Wispr Flow (so keys don't conflict)"
echo "  2. Double-click Dictation.app on your Desktop"
echo "  3. Click OK for Microphone"
echo "  4. Click OK for Speech Recognition"
echo "  5. You'll see ⚠️  in menu bar — go to:"
echo "     System Settings → Privacy → Accessibility"
echo "     → + → Dictation.app → toggle ON"
echo "  6. Icon auto-changes to 🎤 — you're ready!"
echo "     NO restart needed."
echo ""
echo "  THEN: hold RIGHT SHIFT ⇧ to speak, release to type"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
open "$APP"
