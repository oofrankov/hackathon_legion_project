"""Generates assets/icon.png/.ico/.icns (simple placeholder: a green focus target)."""
from pathlib import Path

from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parent.parent / "assets"
S = 1024


def draw():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((40, 40, S - 40, S - 40), radius=220, fill=(26, 29, 36, 255))
    c = S // 2
    for r, w in ((330, 44), (205, 44)):
        d.ellipse((c - r, c - r, c + r, c + r), outline=(34, 197, 94, 255), width=w)
    d.ellipse((c - 95, c - 95, c + 95, c + 95), fill=(34, 197, 94, 255))
    return img


if __name__ == "__main__":
    ASSETS.mkdir(exist_ok=True)
    img = draw()
    img.resize((512, 512), Image.LANCZOS).save(ASSETS / "icon.png")
    img.save(ASSETS / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    img.save(ASSETS / "icon.icns")
    print("icons written to", ASSETS)
