"""Ep 6 start frames without a GPU: the veedu (house front, owner's art 07_home.png) and four Thatha poses.

Run with the f5 env:  python -I make_frames.py
f_hice:   raised-arm layers (Ep 3) holding up an ice cube; a small table with two glasses beside him.
f_hcubes: the Ep 2 layers – an ice cube in each fist, the table with the two glasses in front of him.
f_hjuice: Groundnut Ep 3 f_bowl_s3 – a tall glass of orange juice drawn over the bowl, his front fingers on top.
f_hfin:   Groundnut Ep 4 f_patience_s3 (kneeling, finger raised) in the courtyard.
"""
import io
import sys
from pathlib import Path

import cairosvg
import numpy as np
from PIL import Image
from rembg import new_session, remove

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tools/toon"))
from ice import cube, glass, juice_glass, table  # noqa: E402

FR = HERE / "frames"
EP2 = ROOT / "series/02-thatha-oru-doubt/ep02/final/frames"
EP3 = ROOT / "series/02-thatha-oru-doubt/ep03/final/frames"
GN = ROOT / "series/01-groundnut"


def svg_layer(body):
    return Image.open(io.BytesIO(cairosvg.svg2png(
        bytestring=f'<svg xmlns="http://www.w3.org/2000/svg" width="720" height="1280">{body}</svg>'.encode())))


def cutout(path, seg):
    im = Image.open(path).convert("RGB").resize((720, 1280))
    a = np.array(remove(im, session=seg, only_mask=True))
    a = np.clip((a.astype(float) - 90) * 2.6, 0, 255).astype(np.uint8)
    return Image.fromarray(np.dstack([np.array(im), a]))


def two_glasses(x, y, s=1.0):
    """The table with a normal-water glass (left) and a warm-water glass (right, steam)."""
    return (table(x, y, 260 * s, s) + glass(x - 60 * s, y - 10 * s, 70 * s, 110 * s, 0.7) +
            glass(x + 60 * s, y - 10 * s, 70 * s, 110 * s, 0.7, "#d8eef7", 0.55, 1.0, 0.4))


def main():
    seg = new_session("isnet-anime")
    plate = Image.open(ROOT / "assets/2d/source/07_home.png").convert("RGBA").resize((720, 1280))
    plate.save(FR / "veedu_plate.png")

    PDX = 60
    out = plate.copy()
    out.alpha_composite(svg_layer(two_glasses(150, 1010, 1.15)))
    out.alpha_composite(Image.open(EP3 / "body_pod.png"), (PDX, 0))
    out.alpha_composite(svg_layer(cube(588 + PDX, 205, 128, 8, 0.1)))
    out.alpha_composite(Image.open(EP3 / "fingers_pod.png"), (PDX, 0))
    out.convert("RGB").save(FR / "f_hice.png")
    print("saved f_hice")

    K, DX, DY = 0.94, 45, 1280 * 0.06
    out = plate.copy()
    out.alpha_composite(Image.open(EP2 / "body_two.png"), (int(DX), int(DY)))
    rx, ry = 98 * K + DX, 527 * K + DY
    lx, ly = 602 * K + DX, 530 * K + DY
    out.alpha_composite(svg_layer(cube(rx + 2, ry - 30, 70, -8, 0.15) + cube(lx - 2, ry - 30, 70, 10, 0.15)))
    out.alpha_composite(Image.open(EP2 / "fingers_two.png"), (int(DX), int(DY)))
    out.alpha_composite(svg_layer(two_glasses(360, 1060, 1.5)))
    out.convert("RGB").save(FR / "f_hcubes.png")
    print("saved f_hcubes")

    src = GN / "ep03/final/frames/f_bowl_s3.png"
    body = cutout(src, seg)
    a = np.array(Image.open(src).convert("RGB"))
    h = np.array(Image.open(src).convert("HSV")).astype(int)
    H_, S_, V_ = h[..., 0] * 180 // 255, h[..., 1], h[..., 2]
    yy, xx = np.mgrid[0:1280, 0:720]
    front = (yy > 842) & (yy < 910) & (xx > 315) & (xx < 500) & (((H_ <= 16) & (S_ > 100) & (V_ > 165)) | (V_ < 70))
    fingers = Image.fromarray(np.dstack([a, (front * 255).astype(np.uint8)]))
    out = plate.copy()
    out.alpha_composite(body)
    out.alpha_composite(svg_layer(juice_glass(425, 872, 236, 290, dil=0.0, ice=1.0)))
    out.alpha_composite(fingers)
    out.convert("RGB").save(FR / "f_hjuice.png")
    print("saved f_hjuice")

    out = plate.copy()
    out.alpha_composite(svg_layer('<ellipse cx="450" cy="1048" rx="210" ry="30" fill="#4a1c08" fill-opacity="0.5"/><ellipse cx="200" cy="952" rx="55" ry="14" fill="#4a1c08" fill-opacity="0.45"/>'))
    out.alpha_composite(cutout(GN / "ep04/final/frames/f_patience_s3.png", seg))
    out.convert("RGB").save(FR / "f_hfin.png")
    print("saved f_hfin")


if __name__ == "__main__":
    main()
