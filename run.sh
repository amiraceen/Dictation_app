#!/usr/bin/env bash
# Start the dictation app
cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "Run setup first: bash setup.sh"
    exit 1
fi

source venv/bin/activate
python dictation.py
