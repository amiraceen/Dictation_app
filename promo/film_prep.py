"""Prepares the film stills for scenes-film.html.

For each still: a sharpened 1188 px wide upscale (1.1x the 1080 frame, room for the slow dolly moves) and,
where the laptop screen gets the real Kalam UI, a screen matte: the screen quad minus anything dark in
front of it (hands), so composited UI sits behind his fingers. Writes assets/film/hd/*.jpg, *-matte.png
and quads.json (screen corners TL, TR, BR, BL in hd pixels).

    python3 film_prep.py
"""
import json
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "assets/film")
OUT = os.path.join(SRC, "hd")
W = 1188

# Screen corners measured on the source stills (all plate edits and swaps share one laptop position).
PLATE = [(550.75, 842.5), (705.5, 853.75), (674.5, 993.5), (516.5, 962)]
CLOSE = [(806, 1225), (1031, 1240), (985.5, 1443), (756, 1397)]
STILLS = {
    "01-typing-close": CLOSE,
    "01-typing": PLATE,
    "03-discover": PLATE,
    "04-key-macro": None,
    "05-release": PLATE,
    "07-private-screen": None,
    "08-relaxed": PLATE,
    "09a-khaliji": PLATE,
    "09b-levantine": PLATE,
    "09c-english": PLATE,
}

os.makedirs(OUT, exist_ok=True)
quads = {}
for name, quad in STILLS.items():
    im = Image.open(os.path.join(SRC, name + ".jpg")).convert("RGB")
    k = W / im.width
    hd = im.resize((W, round(im.height * k)), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=1.6, percent=45, threshold=2))
    hd.save(os.path.join(OUT, name + ".jpg"), quality=95, subsampling=0)
    if not quad:
        continue
    q = [(x * k, y * k) for x, y in quad]
    quads[name] = q
    # Quad, drawn 4x and scaled down for clean edges, pulled in half a pixel off the bezel.
    ss = 4
    poly = Image.new("L", (hd.width * ss, hd.height * ss), 0)
    cx, cy = sum(p[0] for p in q) / 4, sum(p[1] for p in q) / 4
    ImageDraw.Draw(poly).polygon([((x + (cx - x) * 0.004) * ss, (y + (cy - y) * 0.004) * ss) for x, y in q], fill=255)
    poly = np.asarray(poly.resize(hd.size, Image.LANCZOS), float) / 255
    # Hands: dark pixels, or warm skin tones darker than the lit (sometimes coral) screen.
    px = np.asarray(hd, float)
    r, g, b = px[..., 0], px[..., 1], px[..., 2]
    luma = 0.299 * r + 0.587 * g + 0.114 * b
    hand = (px.max(axis=2) < 135) | ((r - b > 28) & (r < 205) & (luma < 175))
    # Keep only dark areas that reach in from outside the screen (hands, sleeves), not marks on the screen.
    seed = hand & (poly < 0.5)
    while True:
        grown = np.asarray(Image.fromarray((seed * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))) > 0
        grown &= hand
        if (grown == seed).all():
            break
        seed = grown
    hand = Image.fromarray((seed * 255).astype(np.uint8)).filter(ImageFilter.MedianFilter(5)).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.9))
    lit = 1 - np.asarray(hand, float) / 255
    a = (poly * lit * 255).astype(np.uint8)
    m = Image.new("RGBA", hd.size, (0, 0, 0, 0))
    m.putalpha(Image.fromarray(a))
    m.save(os.path.join(OUT, name + "-matte.png"))

json.dump({k: [[round(x, 2), round(y, 2)] for x, y in v] for k, v in quads.items()}, open(os.path.join(OUT, "quads.json"), "w"), indent=1)
print("ok", list(quads))
