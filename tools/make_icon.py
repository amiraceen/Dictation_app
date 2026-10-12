"""Make the Kalam app icon (AppIcon.icns) from the square artwork in docs/brand/.

    python3 tools/make_icon.py          # needs Pillow

The artwork is fitted to Apple's icon grid: an 824 px rounded square centred on a
1024 px canvas, with a soft drop shadow, like other macOS apps.
"""

import os

from PIL import Image, ImageDraw, ImageFilter

S = 1024
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "docs", "brand", "app-icon-source.jpg")


def icon(size=S):
    k = 4                                               # supersample for smooth edges
    big = size * k
    pad = int(big * 0.098)                              # Apple's grid: 824/1024 body
    body_px = big - 2 * pad
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).rounded_rectangle((pad, pad, big - pad, big - pad), radius=int(body_px * 0.225), fill=255)
    art = Image.open(SOURCE).convert("RGB")
    # The artwork has its own small rounded corners: crop 3% so they fall outside the mask.
    w, h = art.size
    c = int(min(w, h) * 0.03)
    art = art.crop((c, c, w - c, h - c)).resize((body_px, body_px), Image.LANCZOS)
    body = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    body.paste(art, (pad, pad))
    out = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (big, big), (20, 30, 40, 0))
    shadow.putalpha(mask.filter(ImageFilter.GaussianBlur(big * 0.02)).point(lambda v: v * 0.35))
    out.alpha_composite(shadow, (0, int(big * 0.012)))
    body.putalpha(mask)
    out.alpha_composite(body)
    return out.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    img = icon()
    img.save(os.path.join(ROOT, "AppIcon.icns"), sizes=[(16, 16), (32, 32), (64, 64), (128, 128), (256, 256), (512, 512), (1024, 1024)])
    img.save(os.path.join(ROOT, "docs", "kalam-icon.png"))
    # Small copy for the window's top bar.
    img.crop((100, 100, 924, 924)).resize((96, 96), Image.LANCZOS).save(os.path.join(ROOT, "web", "img", "app-icon.webp"), "WEBP", quality=90)
    print("AppIcon.icns written")
