"""Ep 5 start frames without a GPU: the vayal (paddy field) and four Thatha poses.

Run with the f5 env:  python -I make_frames.py
Plate: the owner's field art with a paddy field painted over the soil in code (tools/toon/rice.py vayal()).
f_vbowl:  Groundnut Ep 3 f_bowl_s3 – his bowl now heaped with white rice.
f_vpoint: Groundnut Ep 5 f_point_s3 (kneeling, pointing) at a golden paddy clump.
f_vraise: the raised-arm layers (Ep 3) holding up a bunch of cut paddy.
f_vhold:  the Ep 2 layers – a small bunch of paddy in his right fist, a steel cup of white rice in his left.
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
from rice import bowl_rice, plant, sheaf, vayal  # noqa: E402

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


def steel_cup(x, y, s=1.0):
    """A small steel tumbler-cup heaped with white rice, held at (x, y)."""
    return (f'<path d="M {x - 34 * s:.1f},{y - 40 * s:.1f} L {x + 34 * s:.1f},{y - 40 * s:.1f} L {x + 28 * s:.1f},{y + 45 * s:.1f} '
            f'L {x - 28 * s:.1f},{y + 45 * s:.1f} Z" fill="#c9d0d6" stroke="#3b4248" stroke-width="{4 * s:.1f}"/>'
            f'<line x1="{x - 18 * s:.1f}" y1="{y - 34 * s:.1f}" x2="{x - 14 * s:.1f}" y2="{y + 38 * s:.1f}" stroke="#eef2f5" stroke-width="{6 * s:.1f}"/>'
            + bowl_rice(x, y - 40 * s, 0.38 * s))


def main():
    seg = new_session("isnet-anime")
    plate = Image.open(ROOT / "assets/2d/source/05_field_vertical.png").convert("RGBA").resize((720, 1280))
    plate.alpha_composite(svg_layer(vayal()))
    plate.save(FR / "vayal_plate.png")

    out = plate.copy()
    out.alpha_composite(cutout(GN / "ep03/final/frames/f_bowl_s3.png", seg))
    out.alpha_composite(svg_layer(bowl_rice(426, 822, 1.32)))
    out.convert("RGB").save(FR / "f_vbowl.png")
    print("saved f_vbowl")

    out = plate.copy()
    out.alpha_composite(svg_layer(plant(40, 1100, 560, 2.4, 1.0, seed=51, ears=5) + plant(150, 1230, 500, 2.2, 1.0, seed=52, ears=4)))
    out.alpha_composite(cutout(GN / "ep05/final/frames/f_point_s3.png", seg))
    out.convert("RGB").save(FR / "f_vpoint.png")
    print("saved f_vpoint")

    PDX = 40
    out = plate.copy()
    out.alpha_composite(svg_layer(plant(90, 1280, 460, 1.8, 1.0, seed=53)))
    out.alpha_composite(Image.open(EP3 / "body_pod.png"), (PDX, 0))
    out.alpha_composite(svg_layer(sheaf(588 + PDX, 228, 1.8, seed=5, top=60, ears=9)))
    out.alpha_composite(Image.open(EP3 / "fingers_pod.png"), (PDX, 0))
    out.convert("RGB").save(FR / "f_vraise.png")
    print("saved f_vraise")

    K, DX, DY = 0.94, 45, 1280 * 0.06
    out = plate.copy()
    out.alpha_composite(Image.open(EP2 / "body_two.png"), (int(DX), int(DY)))
    rx, ry = 98 * K + DX, 527 * K + DY
    lx, ly = 602 * K + DX, 530 * K + DY
    out.alpha_composite(svg_layer(sheaf(rx + 2, ry - 10, 1.1, seed=6, top=55, ears=7) + steel_cup(lx - 2, ly - 8, 1.0)))
    out.alpha_composite(Image.open(EP2 / "fingers_two.png"), (int(DX), int(DY)))
    out.convert("RGB").save(FR / "f_vhold.png")
    print("saved f_vhold")


if __name__ == "__main__":
    main()
