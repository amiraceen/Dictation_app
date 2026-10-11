#!/usr/bin/env bash
# ─── Dictation App Setup ──────────────────────────────────────────────────────
# Run once: bash setup.sh
# Then start with: bash run.sh

set -e
cd "$(dirname "$0")"

echo "──────────────────────────────────────────────"
echo "  Dictation App — Setup"
echo "──────────────────────────────────────────────"

# 1. Check Python 3.9+
if ! command -v python3 &>/dev/null; then
    echo "❌  Python 3 not found."
    echo "    Install it with:  brew install python3"
    exit 1
fi

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✓  Python $PY_VER found"

# 2. Create virtual environment
if [ ! -d "venv" ]; then
    echo "→  Creating virtual environment…"
    python3 -m venv venv
fi

# 3. Activate and install
source venv/bin/activate
echo "→  Installing dependencies (this may take a minute)…"
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

echo ""
echo "✓  Setup complete!"
echo ""
echo "──────────────────────────────────────────────"
echo "  IMPORTANT — macOS permissions needed:"
echo "  1. System Settings > Privacy & Security > Accessibility"
echo "     → Add Terminal (or your terminal app)"
echo "  2. System Settings > Privacy & Security > Microphone"
echo "     → Add Terminal (or your terminal app)"
echo "──────────────────────────────────────────────"
echo ""
echo "  First run will download the Whisper model (~145 MB)."
echo "  After that, everything runs 100% locally — no internet needed."
echo ""
echo "  Start the app:  bash run.sh"
echo "  Hotkey:         Hold RIGHT OPTION (⌥) to record,"
echo "                  release to transcribe and type."
echo ""
