#!/usr/bin/env bash
# Builds the Kalam promo: brag-output/kalam-promo.mp4 and brag-output/kalam-promo-poster.png.
# Needs node + Playwright (Chromium), python3 + numpy + Pillow, and ffmpeg.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/../brag-output"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$OUT"

python3 "$HERE/crop_screens.py"
python3 "$HERE/music.py" "$WORK/music.wav"
node "$HERE/render.mjs" frames "$WORK/frames" 30

ffmpeg -y -hide_banner -loglevel error -framerate 30 -i "$WORK/frames/f%05d.jpg" -i "$WORK/music.wav" \
  -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p -profile:v high -movflags +faststart \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11" -c:a aac -b:a 192k -ar 48000 -shortest "$OUT/kalam-promo.mp4"

node "$HERE/render.mjs" stills "$WORK/poster" 41
cp "$WORK/poster/t41.png" "$OUT/kalam-promo-poster.png"
echo "Done: $OUT"
