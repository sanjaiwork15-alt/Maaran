"""Ep 4 start frames without a GPU: the thottam (tomato garden) and four different Thatha poses.

Run with the f5 env:  python -I make_frames.py
Plate: the owner's field art (assets/2d/source/05_field_vertical.png) with rows of staked tomato plants drawn in code.
f_tpoint:  Groundnut Ep 5 f_point_s3 (kneeling, pointing) – he points at a big plant with green, orange and red fruit.
f_tfinger: Groundnut Ep 4 f_patience_s3 (kneeling, finger raised) beside a plant.
f_thold:   the Ep 2 Thatha layers – a green tomato in his right fist, a red one in his left.
f_traise:  the Ep 3 raised-arm layers – a red tomato held up proudly – beside a plant.
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
from tomato import plant_svg, thottam_rows, tomato  # noqa: E402

FR = HERE / "frames"
EP2 = ROOT / "series/02-thatha-oru-doubt/ep02/final/frames"
EP3 = ROOT / "series/02-thatha-oru-doubt/ep03/final/frames"
GN = ROOT / "series/01-groundnut"


def svg_layer(body):
    return Image.open(io.BytesIO(cairosvg.svg2png(
        bytestring=f'<svg xmlns="http://www.w3.org/2000/svg" width="720" height="1280">{body}</svg>'.encode())))


def shadow(cx, cy, rx, ry):
    return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="#5a2410" fill-opacity="0.35"/>'


def cutout(path, seg):
    im = Image.open(path).convert("RGB").resize((720, 1280))
    a = np.array(remove(im, session=seg, only_mask=True))
    a = np.clip((a.astype(float) - 90) * 2.6, 0, 255).astype(np.uint8)   # solid body, soft 1-2 px edge (no ghost fingers)
    return Image.fromarray(np.dstack([np.array(im), a]))


def main():
    seg = new_session("isnet-anime")
    plate = Image.open(ROOT / "assets/2d/source/05_field_vertical.png").convert("RGBA").resize((720, 1280))
    plate.alpha_composite(svg_layer(thottam_rows()))
    plate.save(FR / "thottam_plate.png")

    # f_tpoint: the fruit cluster sits right at his fingertip (142, 690)
    out = plate.copy()
    out.alpha_composite(svg_layer(shadow(330, 1060, 220, 30) +
                                  plant_svg(60, 1120, 760, 1.5, [(0.42, 1, 34, 0.55), (0.56, 1, 38, 0.0), (0.68, 1, 36, 1.0),
                                                                 (0.82, 1, 30, 0.1)], seed=21)))
    out.alpha_composite(cutout(GN / "ep05/final/frames/f_point_s3.png", seg))
    out.convert("RGB").save(FR / "f_tpoint.png")
    print("saved f_tpoint")

    # f_tfinger: plant behind him on the right
    out = plate.copy()
    out.alpha_composite(svg_layer(shadow(380, 1080, 220, 30) +
                                  plant_svg(640, 1120, 820, 1.5, [(0.45, -1, 34, 1.0), (0.6, -1, 36, 0.0), (0.72, -1, 30, 0.6)],
                                            seed=22)))
    out.alpha_composite(cutout(GN / "ep04/final/frames/f_patience_s3.png", seg))
    out.convert("RGB").save(FR / "f_tfinger.png")
    print("saved f_tfinger")

    # f_thold: Ep 2 layers (scaled 0.94, at 45, 76.8); fists at (98, 527) and (602, 530) in f_two coords
    K, DX, DY = 0.94, 45, 1280 * 0.06
    out = plate.copy()
    out.alpha_composite(svg_layer(plant_svg(650, 1280, 900, 1.6, [(0.5, -1, 36, 0.8), (0.66, -1, 32, 0.2)], seed=23)))
    out.alpha_composite(Image.open(EP2 / "body_two.png"), (int(DX), int(DY)))
    rx, ry = 98 * K + DX, 527 * K + DY
    lx, ly = 602 * K + DX, 530 * K + DY
    out.alpha_composite(svg_layer(tomato(rx + 4, ry - 36, 40, 0.0) + tomato(lx - 4, ly - 38, 42, 1.0)))
    out.alpha_composite(Image.open(EP2 / "fingers_two.png"), (int(DX), int(DY)))
    out.convert("RGB").save(FR / "f_thold.png")
    print("saved f_thold")

    # f_traise: raised arm (f_pod coords; onion-free layers from Ep 3), red tomato in the raised hand
    PDX = 40
    out = plate.copy()
    out.alpha_composite(svg_layer(plant_svg(110, 1250, 900, 1.6, [(0.5, 1, 36, 0.0), (0.62, 1, 34, 0.4), (0.75, 1, 30, 1.0)],
                                            seed=24)))
    out.alpha_composite(Image.open(EP3 / "body_pod.png"), (PDX, 0))
    out.alpha_composite(svg_layer(tomato(586 + PDX, 210, 74, 1.0, -8)))
    out.alpha_composite(Image.open(EP3 / "fingers_pod.png"), (PDX, 0))
    out.convert("RGB").save(FR / "f_traise.png")
    print("saved f_traise")


if __name__ == "__main__":
    main()
