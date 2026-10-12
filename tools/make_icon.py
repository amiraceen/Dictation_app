"""Draw the Kalam app icon (gradient-mesh squircle with a white voice wave) → AppIcon.icns.

    python3 tools/make_icon.py          # needs Pillow
"""

import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

S = 1024
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def mesh(size):
    """Warm aura: amber top-left, coral, rose, violet bottom-right, with a soft sky glow."""
    y, x = np.mgrid[0:size, 0:size] / size
    img = np.zeros((size, size, 3))
    blobs = [((0.05, 0.0), (255, 170, 70), 0.55), ((0.35, 0.45), (255, 107, 74), 0.45),
             ((0.95, 0.15), (236, 74, 139), 0.5), ((0.95, 1.0), (122, 92, 255), 0.6),
             ((0.1, 1.0), (240, 90, 150), 0.4), ((0.6, 0.85), (62, 155, 255), 0.25)]
    weight = np.zeros((size, size))
    for (cx, cy), col, r in blobs:
        w = np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * r * r)) ** 2
        img += w[..., None] * np.array(col)
        weight += w
    img /= weight[..., None]
    return Image.fromarray(img.clip(0, 255).astype(np.uint8))


def icon(size=S):
    k = 4                                               # supersample for smooth edges
    big = size * k
    pad = int(big * 0.098)                              # Apple's grid: 824/1024 body
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).rounded_rectangle((pad, pad, big - pad, big - pad), radius=int((big - 2 * pad) * 0.225), fill=255)
    body = mesh(big // 8).resize((big, big), Image.BICUBIC).convert("RGBA")
    # Glass sheen across the top.
    sheen = Image.new("L", (big, big), 0)
    ImageDraw.Draw(sheen).ellipse((-big * 0.2, -big * 0.75, big * 1.2, big * 0.42), fill=60)
    body = Image.composite(Image.new("RGBA", (big, big), (255, 255, 255, 255)), body,
                           sheen.filter(ImageFilter.GaussianBlur(big * 0.04)))
    # Voice wave: five rounded white bars.
    d = ImageDraw.Draw(body)
    heights = [0.22, 0.42, 0.6, 0.42, 0.22]
    bar_w, gap = big * 0.072, big * 0.058
    x0 = (big - (len(heights) * bar_w + (len(heights) - 1) * gap)) / 2
    for i, h in enumerate(heights):
        x = x0 + i * (bar_w + gap)
        hh = big * h
        d.rounded_rectangle((x, (big - hh) / 2, x + bar_w, (big + hh) / 2), radius=bar_w / 2, fill=(255, 255, 255, 245))
    out = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (big, big), (60, 20, 60, 0))
    shadow.putalpha(mask.filter(ImageFilter.GaussianBlur(big * 0.02)).point(lambda v: v * 0.35))
    out.alpha_composite(shadow, (0, int(big * 0.012)))
    body.putalpha(mask)
    out.alpha_composite(body)
    return out.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    img = icon()
    img.save(os.path.join(ROOT, "AppIcon.icns"), sizes=[(16, 16), (32, 32), (64, 64), (128, 128), (256, 256), (512, 512), (1024, 1024)])
    img.save(os.path.join(ROOT, "docs", "kalam-icon.png"))
    print("AppIcon.icns written")
