"""Crop each screenshot in ../screenshots to the app window (dropping the wallpaper)
and round its corners, so scenes can float the real window on brand backgrounds."""
import glob, os
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "assets", "screens")
os.makedirs(OUT, exist_ok=True)

for f in sorted(glob.glob(os.path.join(HERE, "..", "screenshots", "*.webp"))):
    im = Image.open(f).convert("RGB")
    a = np.asarray(im).astype(int)
    light = (a.min(2) > 170) & ((a.max(2) - a.min(2)) < 70)
    h, w = light.shape
    cols = np.where(light[h // 2 - 200:h // 2 + 200].mean(0) > 0.6)[0]
    rows = np.where(light[:, w // 2 - 300:w // 2 + 300].mean(1) > 0.6)[0]
    box = (cols[0] + 2, rows[0] + 2, cols[-1] - 1, rows[-1] - 1)
    win = im.crop(box).convert("RGBA")
    mask = Image.new("L", win.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, win.size[0] - 1, win.size[1] - 1), 30, fill=255)
    win.putalpha(mask)
    name = os.path.splitext(os.path.basename(f))[0]
    win.save(os.path.join(OUT, name + ".png"))
    print(name, win.size)
