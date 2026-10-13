#!/usr/bin/env bash
# Builds the Kalam promo into brag-output/.
#   promo/build.sh            → kalam-promo.mp4 + kalam-promo-poster.png            (16:9, 1920×1080)
#   promo/build.sh vertical   → kalam-promo-vertical.mp4 + kalam-promo-vertical-poster.png (9:16, 1080×1920)
#   promo/build.sh calm       → kalam-promo-vertical-calm.mp4 + poster (9:16, calm 3D cut)
# Needs node + Playwright (Chromium), python3 + numpy + Pillow, and ffmpeg.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/../brag-output"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$OUT"

if [ "${1:-}" = "calm" ]; then
  export PAGE=scenes-calm.html SIZE=1080x1920
  MUSIC=music_calm.py NAME=kalam-promo-vertical-calm POSTER_T=58
elif [ "${1:-}" = "vertical" ]; then
  export PAGE=scenes-vertical.html SIZE=1080x1920
  MUSIC=music_vertical.py NAME=kalam-promo-vertical POSTER_T=40
else
  export PAGE=scenes.html SIZE=1920x1080
  MUSIC=music.py NAME=kalam-promo POSTER_T=41
fi

python3 "$HERE/crop_screens.py"
python3 "$HERE/$MUSIC" "$WORK/music.wav"
node "$HERE/render.mjs" frames "$WORK/frames" 30

ffmpeg -y -hide_banner -loglevel error -framerate 30 -i "$WORK/frames/f%05d.jpg" -i "$WORK/music.wav" \
  -c:v libx264 -preset slow -crf 21 -pix_fmt yuv420p -profile:v high -movflags +faststart \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000,alimiter=limit=0.7:level=false" -c:a aac -b:a 192k -ar 48000 -shortest "$OUT/$NAME.mp4"

node "$HERE/render.mjs" stills "$WORK/poster" "$POSTER_T"
cp "$WORK/poster/t$POSTER_T.png" "$OUT/$NAME-poster.png"
echo "Done: $OUT/$NAME.mp4"
