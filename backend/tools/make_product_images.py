"""One-off helper used to draw assets/product_images/<sku>.png (needs Noto Color Emoji). Output is committed."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
OUT = Path(__file__).resolve().parents[1] / "assets" / "product_images"

# (emoji, top colour, bottom colour) in catalog order, matching seed_data.py (VB-0001 ...)
ITEMS = [
    ("🥛", "#E3F2FD", "#BBDEFB"), ("🥣", "#FFF8E1", "#FFECB3"), ("🧀", "#FFF3C4", "#FFE082"),
    ("🧈", "#FFFDE7", "#FFF59D"), ("🥚", "#FFF3E0", "#FFE0B2"),
    ("🍞", "#FFF3E0", "#FFCC80"), ("🥖", "#FBE9E7", "#FFAB91"), ("🧁", "#FCE4EC", "#F8BBD0"),
    ("🥟", "#FFF8E1", "#FFE082"), ("🍰", "#F3E5F5", "#E1BEE7"),
    ("🍟", "#FFEBEE", "#FFCDD2"), ("🥜", "#EFEBE9", "#D7CCC8"), ("🍪", "#EFEBE9", "#BCAAA4"),
    ("🍜", "#FFF3E0", "#FFCC80"), ("🍿", "#FFFDE7", "#FFF59D"),
    ("🍊", "#FFF3E0", "#FFCC80"), ("🥤", "#FFEBEE", "#EF9A9A"), ("🍵", "#E8F5E9", "#A5D6A7"),
    ("☕", "#EFEBE9", "#BCAAA4"), ("💧", "#E1F5FE", "#81D4FA"),
    ("💊", "#E8EAF6", "#C5CAE9"), ("🍋", "#F9FBE7", "#E6EE9C"), ("🩹", "#FBE9E7", "#FFCCBC"),
    ("🧪", "#E0F2F1", "#B2DFDB"), ("🧃", "#E8F5E9", "#C8E6C9"),
    ("🧴", "#F3E5F5", "#CE93D8"), ("☀️", "#FFF8E1", "#FFE082"), ("🪥", "#E0F7FA", "#80DEEA"),
    ("🧼", "#E1F5FE", "#B3E5FC"), ("🫧", "#E3F2FD", "#90CAF9"),
]
S = 600


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def gradient(top, bottom):
    img = Image.new("RGB", (S, S))
    px = img.load()
    t, b = hexrgb(top), hexrgb(bottom)
    for y in range(S):
        c = tuple(int(t[i] + (b[i] - t[i]) * y / S) for i in range(3))
        for x in range(S):
            px[x, y] = c
    return img


font = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", 109)
for n, (emoji, top, bottom) in enumerate(ITEMS, start=1):
    img = gradient(top, bottom).convert("RGBA")
    # soft white disc with shadow
    shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse((110, 130, 490, 510), fill=(0, 0, 0, 60))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(14)))
    disc = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(disc).ellipse((100, 110, 500, 510), fill=(255, 255, 255, 215))
    img.alpha_composite(disc)
    glyph = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(glyph).text((80, 80), emoji, font=font, embedded_color=True, anchor="mm")
    bbox = glyph.getbbox()
    glyph = glyph.crop(bbox).resize((int((bbox[2] - bbox[0]) * 2.4), int((bbox[3] - bbox[1]) * 2.4)), Image.LANCZOS)
    img.alpha_composite(glyph, ((S - glyph.width) // 2, 310 - glyph.height // 2))
    img.convert("RGB").save(OUT / f"VB-{n:04d}.png", optimize=True)
print("done", len(ITEMS))
