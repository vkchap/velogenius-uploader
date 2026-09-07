"""Draw the disk image's background: a heading and an arrow from the app to
the Applications folder, so the window says what to do with itself.

Written at build time rather than committed, because a 1320x800 PNG in the
repository is a thing nobody can review in a diff.
"""

import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 660, 360
BG = (248, 248, 250)
INK = (28, 28, 30)
GREY = (162, 162, 170)

# Where the DMG puts the two icons; the arrow lives between them.
APP_X, APPS_X, ICON_Y = 165, 495, 178


def font(size: int, scale: int):
    for path in (
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ):
        try:
            return ImageFont.truetype(path, size * scale)
        except OSError:
            continue
    return ImageFont.load_default()


def draw(scale: int) -> Image.Image:
    img = Image.new("RGB", (W * scale, H * scale), BG)
    d = ImageDraw.Draw(img)
    s = scale

    title = "Drag VeloGenius Uploader into Applications"
    f = font(15, s)
    tw = d.textbbox((0, 0), title, font=f)[2]
    d.text(((W * s - tw) / 2, 40 * s), title, font=f, fill=INK)

    sub = "Then open it from Applications."
    f2 = font(12, s)
    sw = d.textbbox((0, 0), sub, font=f2)[2]
    d.text(((W * s - sw) / 2, 66 * s), sub, font=f2, fill=GREY)

    # The arrow, between the two icons and level with their middles.
    y = ICON_Y * s
    x0, x1 = (APP_X + 92) * s, (APPS_X - 92) * s
    head = 17 * s
    d.line([(x0, y), (x1 - head, y)], fill=GREY, width=3 * s)
    d.polygon(
        [(x1, y), (x1 - head, y - head * 0.55), (x1 - head, y + head * 0.55)],
        fill=GREY,
    )
    return img


out = sys.argv[1]
draw(1).save(out + ".png")
draw(2).save(out + "@2x.png")
