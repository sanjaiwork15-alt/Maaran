"""YouTube thumbnail for a long-form compilation (1280x720), built from approved episode frames.

Usage: python tools/longform_thumb.py OUT.png
Left: title + the journey in four round badges (seed, sprout, flower, pods); right: Thatha with the roasted
groundnuts (Ep 10 thumbnail frame). Background: the series field art, blurred.
"""
import io
import sys
from pathlib import Path

import cairosvg
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
G = ROOT / "series/01-groundnut"
W, H = 1280, 720
BADGES = [("ep03/final/frames/thumb_s5.png", 435, 905, 150), ("ep04/final/frames/thumb_s5.png", 285, 1080, 135),
          ("ep06/final/frames/thumb_s5.png", 570, 1080, 150), ("ep08/final/frames/thumb_s5.png", 180, 715, 175)]


def badge(path, cx, cy, r, size):
    im = Image.open(G / path).convert("RGB").crop((cx - r, cy - r, cx + r, cy + r)).resize((size, size))
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).ellipse((0, 0, size - 1, size - 1), fill=255)
    out = Image.new("RGBA", (size + 12, size + 12), (0, 0, 0, 0))
    ImageDraw.Draw(out).ellipse((0, 0, size + 11, size + 11), fill="#3b2416")
    ImageDraw.Draw(out).ellipse((4, 4, size + 7, size + 7), fill="#ffd84a")
    out.paste(im, (6, 6), m)
    return out


def main():
    bg = Image.open(ROOT / "assets/2d/up/05_field_vertical.png").convert("RGB")
    bg = bg.resize((W, round(bg.height * W / bg.width)))
    top = round(bg.height * 0.42 - H / 2)
    bg = ImageEnhance.Brightness(bg.crop((0, top, W, top + H)).filter(ImageFilter.GaussianBlur(10))).enhance(0.7)
    th = Image.open(G / "ep10/final/frames/thumb_s5.png").convert("RGB")
    th = th.crop((0, 0, th.width, round(th.height * 0.74)))          # knees up
    th = th.resize((round(th.width * H / th.height), H))
    fade = Image.linear_gradient("L").rotate(90).resize((th.width, H))  # soft left edge
    fade = fade.point(lambda v: min(255, v * 4))
    bg.paste(th, (W - th.width + 30, 0), fade)
    font = "font-family='Inter Display, Inter' font-weight='900' text-anchor='middle'"
    def t(x, y, s, txt, fill, sw):
        return (f"<text x='{x}' y='{y}' {font} font-size='{s}' fill='#3b2416' stroke='#3b2416' stroke-width='{sw}' "
                f"stroke-linejoin='round'>{txt}</text><text x='{x}' y='{y}' {font} font-size='{s}' fill='{fill}'>{txt}</text>")
    arrows = "".join(f"<path d='M {x},505 l 22,0 l -8,-10 M {x + 22},505 l -8,10' stroke='#ffffff' stroke-width='6' "
                     f"stroke-linecap='round' fill='none'/>" for x in (168, 338, 508))
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}'>"
           + t(360, 150, 118, "SEED", "#ffd84a", 18) + t(360, 270, 96, "to SNACK", "#ffffff", 18)
           + "<rect x='120' y='305' width='480' height='70' rx='35' fill='#d6332a' stroke='#3b2416' stroke-width='6'/>"
           + f"<text x='360' y='353' {font} font-size='40' fill='#ffffff'>FULL JOURNEY</text>" + arrows + "</svg>")
    fg = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert("RGBA")
    bg.paste(fg, (0, 0), fg)
    for i, b in enumerate(BADGES):
        im = badge(*b, 116)
        bg.paste(im, (30 + i * 170, 440), im)
    bg.save(sys.argv[1])
    print("saved", sys.argv[1])


if __name__ == "__main__":
    main()
