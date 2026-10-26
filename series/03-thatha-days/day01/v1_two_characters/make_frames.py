"""Day 1 start frames without a GPU: the village courtyard (owner's 07_home art), Thatha and the boy (owner's sheet,
assets/2d/source/thambi/00_sheet.png, 2026-10-26).

Run with the f5 env:  python -I make_frames.py [--draft]
All frames are composed directly at 1080x1920 from upscaled sources (no per-frame upscale):
  boy  – $HOME/.maaran/cache/up/00_sheet_x4.png (Real-ESRGAN x4 of the sheet; --draft uses the 1x sheet, Lanczos)
  Thatha – assets/2d/up/01_front.png, 04_poses.png (x2, made earlier) and the x2 turnaround.
f_two:    two-shot – Thatha (3/4, left) turned to the boy (3/4, mirrored, right) who holds his phone; his school books
          and notebook on the courtyard ground beside him (the unfinished work).
f_bclose: the boy's big close-up (sheet portrait), phone in the foreground, screen light on his face.
f_bsmile / f_bfrown / f_bthink / f_blaugh / f_bhappy / f_bsurp: chest-up shots from the sheet's expression tiles,
          the back of his phone rising from the bottom of the frame (he looks at it with talk.py "gaze").
f_tfront: Thatha medium shot (front). f_tcross: Thatha with arms crossed (observing patiently).
"""
import io
import os
import sys
from pathlib import Path

import cairosvg
import cv2
import numpy as np
from PIL import Image
from rembg import new_session, remove

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FR = HERE / "frames"
SRC = ROOT / "assets/2d/source"
CACHE = Path(os.environ["HOME"]) / ".maaran/cache/up"
W, H = 1080, 1920
DRAFT = "--draft" in sys.argv

# regions on the boy's sheet (1x, 1024x1536)
BOY = {"close": (338, 34, 586, 497), "front": (323, 523, 447, 867), "34": (461, 524, 572, 870),
       "smile_open": (586, 20, 716, 192), "laugh": (716, 20, 862, 192), "surp": (862, 20, 1000, 192),
       "smile": (586, 194, 716, 362), "smile2": (716, 194, 862, 362), "wink": (862, 194, 1000, 362),
       "think": (586, 362, 716, 530), "frown": (716, 362, 862, 530), "happy": (862, 362, 1000, 530)}


def svg_layer(body, w=W, h=H):
    return Image.open(io.BytesIO(cairosvg.svg2png(
        bytestring=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">{body}</svg>'.encode()))).convert("RGBA")


class Sheet:
    def __init__(self, path_up, path_1x, scale, seg, despeck=False):
        self.s = scale
        self.despeck = despeck
        self.im = Image.open(path_up if (path_up and Path(path_up).exists() and not DRAFT) else path_1x).convert("RGB")
        if self.im.width != Image.open(path_1x).width * scale:
            self.im = self.im.resize((Image.open(path_1x).width * scale, Image.open(path_1x).height * scale), Image.LANCZOS)
        self.seg = seg

    def cut(self, box, mirror=False):
        x0, y0, x1, y1 = (v * self.s for v in box)
        im = self.im.crop((x0, y0, x1, y1))
        a = np.array(remove(im, session=self.seg, only_mask=True)).astype(np.float32)
        a = np.clip((a - 90) * 2.6, 0, 255).astype(np.uint8)
        rgb = np.array(im)
        yy = np.arange(rgb.shape[0])[:, None]
        if self.despeck:
            a[(rgb.min(axis=2) > 222) & (yy < rgb.shape[0] * 0.22)] = 0      # tile-border specks in the boy's hair
        out = Image.fromarray(np.dstack([rgb, a]))
        out = out.crop(out.getbbox())
        return out.transpose(Image.FLIP_LEFT_RIGHT) if mirror else out


def place(canvas, fig, h, cx, bottom):
    """Scale fig to height h, centre it at x = cx, feet at y = bottom."""
    w = round(fig.width * h / fig.height)
    f = fig.resize((w, h), Image.LANCZOS)
    canvas.alpha_composite(f, (round(cx - w / 2), round(bottom - h)))
    return (round(cx - w / 2), round(bottom - h), w, h)


def books(x, y, s=1.0):
    """School books and an open notebook on the ground (the unfinished work)."""
    b = ""
    for k, (col, ww, hh, dx) in enumerate([("#2f6db3", 150, 26, 0), ("#c0392b", 140, 24, 6), ("#27ae60", 146, 22, -4)]):
        yy = y - (k + 1) * 24 * s
        b += (f'<rect x="{x - ww * s / 2 + dx * s:.0f}" y="{yy:.0f}" width="{ww * s:.0f}" height="{hh * s:.0f}" rx="3" '
              f'fill="{col}" stroke="#222" stroke-width="2.5"/>'
              f'<rect x="{x - ww * s / 2 + dx * s + 6:.0f}" y="{yy + 4 * s:.0f}" width="{(ww - 12) * s:.0f}" height="{6 * s:.0f}" fill="#f4f1e8"/>')
    nx, ny = x + 150 * s, y - 10 * s
    b += (f'<g transform="translate({nx:.0f} {ny:.0f}) skewX(-25)"><rect x="-80" y="-34" width="160" height="40" fill="#fafafa" '
          f'stroke="#333" stroke-width="2.5"/><line x1="0" y1="-34" x2="0" y2="6" stroke="#333" stroke-width="2"/>'
          + "".join(f'<line x1="{-70 + j * 80}" y1="{-24 + i * 8}" x2="{-10 + j * 80}" y2="{-24 + i * 8}" stroke="#7fa7d6" stroke-width="1.5"/>'
                    for i in range(4) for j in range(2) if not (j == 1 and i > 1)) + '</g>'
          f'<line x1="{nx + 40:.0f}" y1="{ny - 2:.0f}" x2="{nx + 95:.0f}" y2="{ny - 30:.0f}" stroke="#e5b33a" stroke-width="7" stroke-linecap="round"/>')
    return b


def phone_back(cx, top, w, ang=-8, glow=True):
    """The back of his phone rising from the bottom of the frame (he is looking at the screen)."""
    h = w * 2.05
    s = (f'<g transform="rotate({ang} {cx} {top + h / 2})">'
         f'<rect x="{cx - w / 2:.0f}" y="{top:.0f}" width="{w:.0f}" height="{h:.0f}" rx="{w * 0.14:.0f}" fill="#2a2f36" stroke="#0d0f12" stroke-width="6"/>'
         f'<rect x="{cx - w / 2 + w * 0.1:.0f}" y="{top + w * 0.1:.0f}" width="{w * 0.32:.0f}" height="{w * 0.5:.0f}" rx="{w * 0.08:.0f}" fill="#15181c"/>'
         f'<circle cx="{cx - w / 2 + w * 0.26:.0f}" cy="{top + w * 0.22:.0f}" r="{w * 0.08:.0f}" fill="#0a0c0e" stroke="#555" stroke-width="3"/>'
         f'<circle cx="{cx - w / 2 + w * 0.26:.0f}" cy="{top + w * 0.47:.0f}" r="{w * 0.08:.0f}" fill="#0a0c0e" stroke="#555" stroke-width="3"/>'
         f'<path d="M {cx + w * 0.3:.0f},{top + 12:.0f} l {w * 0.12:.0f},0 l -{w * 0.5:.0f},{h:.0f} l -{w * 0.12:.0f},0 Z" fill="#ffffff" fill-opacity="0.06"/>'
         f'</g>')
    return s


def screen_light(img, cx, cy, r, amt=0.18):
    """Cool screen light on his face from below."""
    a = np.asarray(img).astype(np.float32)
    yy, xx = np.mgrid[0:img.height, 0:img.width]
    m = np.exp(-(((xx - cx) / r) ** 2 + ((yy - cy) / (r * 1.2)) ** 2))[..., None] * amt
    a[..., :3] = a[..., :3] + (np.array([200, 225, 255], np.float32) - a[..., :3]) * m
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), img.mode)


def main():
    seg = new_session("isnet-anime")
    plate = Image.open(SRC / "07_home.png").convert("RGBA").resize((W, H), Image.LANCZOS)
    plate.save(FR / "courtyard_plate.png")
    blur = Image.fromarray(cv2.GaussianBlur(np.array(plate), (0, 0), 9))
    boy = Sheet(CACHE / "00_sheet_x4.png", SRC / "thambi/00_sheet.png", 4, seg, despeck=True)
    turn = Sheet(CACHE / "08_turnaround_x2.png", SRC / "08_turnaround.png", 2, seg)
    poses = Sheet(ROOT / "assets/2d/up/04_poses.png", SRC / "04_poses.png", 2, seg)
    front = Sheet(ROOT / "assets/2d/up/01_front.png", SRC / "01_front.png", 2, seg)

    # two-shot
    out = plate.copy()
    out.alpha_composite(svg_layer('<ellipse cx="330" cy="1805" rx="200" ry="28" fill="#4a1c08" fill-opacity="0.45"/>'
                                  '<ellipse cx="800" cy="1815" rx="170" ry="26" fill="#4a1c08" fill-opacity="0.45"/>'))
    out.alpha_composite(svg_layer(books(935, 1660, 0.8)))
    place(out, turn.cut((40, 0, 430, 887)), 1330, 320, 1810)
    boy_layer = Image.new("RGBA", (W, H))
    bx = place(boy_layer, boy.cut(BOY["34"], mirror=True), 1080, 790, 1820)
    out.alpha_composite(boy_layer)
    # phone in his near hand: draw it, then lay his fingers (his skin pixels only) back on top
    hand = np.array(boy_layer)[1360:1450, 630:705].copy()
    hsv = cv2.cvtColor(hand[..., :3], cv2.COLOR_RGB2HSV).astype(int)
    skin = ((hsv[..., 0] <= 20) & (hsv[..., 1] > 110) & (hsv[..., 2] > 120) & (hand[..., 3] > 200)).astype(np.uint8)
    skin = cv2.morphologyEx(skin, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) * 255
    out.alpha_composite(svg_layer('<g transform="rotate(6 672 1420)"><rect x="652" y="1372" width="40" height="92" rx="7" '
                                  'fill="#2a2f36" stroke="#0d0f12" stroke-width="3"/>'
                                  '<rect x="656" y="1440" width="32" height="3" fill="#555"/></g>'))
    out.alpha_composite(Image.fromarray(np.dstack([hand[..., :3], skin])), (630, 1360))
    out.save(FR / "f_two.png")
    print("saved f_two", "boy box", bx)

    # boy close-up (portrait)
    out = blur.copy()
    place(out, boy.cut(BOY["close"]), 1930, 545, 1960)
    out = screen_light(out, 560, 1100, 380, 0.12)
    out.alpha_composite(svg_layer(phone_back(830, 1560, 240, -10)))
    out.save(FR / "f_bclose.png")
    print("saved f_bclose")

    # chest-up tiles
    for name, key in [("f_bsmile", "smile"), ("f_bfrown", "frown"), ("f_bthink", "think"), ("f_blaugh", "laugh"),
                      ("f_bhappy", "happy"), ("f_bsurp", "surp")]:
        out = blur.copy()
        place(out, boy.cut(BOY[key]), 1400, 540, 1960)
        if key not in ("surp",):
            out = screen_light(out, 540, 1150, 340, 0.12)
            out.alpha_composite(svg_layer(phone_back(560, 1640, 230, -6)))
        out.save(FR / f"{name}.png")
        print("saved", name)

    # Thatha medium shots
    out = plate.copy()
    place(out, front.cut((0, 0, 1024, 1536)), 2500, 560, 2500 + 260)
    out.save(FR / "f_tfront.png")
    out = plate.copy()
    place(out, poses.cut((1403, 0, 1744, 887)), 2350, 540, 2350 + 300)
    out.save(FR / "f_tcross.png")
    print("saved Thatha frames")


if __name__ == "__main__":
    main()
