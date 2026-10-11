#!/usr/bin/env bash
# Installs a Launch Agent so dictation starts automatically on login.
# Run AFTER setup.sh:  bash install-autostart.sh
# To remove autostart: bash install-autostart.sh --uninstall

set -e
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_FILE="$PLIST_DIR/com.dictation.app.plist"

if [ "$1" = "--uninstall" ]; then
    launchctl unload "$PLIST_FILE" 2>/dev/null || true
    rm -f "$PLIST_FILE"
    echo "✓  Autostart removed."
    exit 0
fi

mkdir -p "$PLIST_DIR"

cat > "$PLIST_FILE" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.dictation.app</string>
    <key>ProgramArguments</key>
    <array>
        <string>$APP_DIR/venv/bin/python</string>
        <string>$APP_DIR/dictation.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$APP_DIR/dictation.log</string>
    <key>StandardErrorPath</key>
    <string>$APP_DIR/dictation.log</string>
</dict>
</plist>
PLIST

launchctl load "$PLIST_FILE"
echo "✓  Autostart installed. Dictation will start on next login."
echo "   To start now:   launchctl start com.dictation.app"
echo "   To uninstall:   bash install-autostart.sh --uninstall"
