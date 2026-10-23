"""Ep 7 start frames without a GPU: outside the house – the thinnai (tea) and the verandah – four Thatha poses.

Run with the f5 env:  python -I make_frames.py
f_atea:   Groundnut Ep 10 f_sit_s3 on the thinnai – a steel tumbler in a davara drawn over his bowl (tea time).
f_afin:   Groundnut Ep 4 f_patience_s3 (kneeling, finger raised, hand on the ground) by the verandah – the ants pass
          his hand (the ants themselves are animated in talk.py, "ants" overlay).
f_aphone: raised-arm layers (Ep 3) holding up a mobile phone ("erumbukku phone illa!").
f_atwo:   Ep 2 layers – a tea tumbler in his right fist, a murukku in his left.
Verandah plate: a closer crop of the owner's house art (assets/2d/source/07_home.png), different from Ep 6's wide view.
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
FR = HERE / "frames"
EP2 = ROOT / "series/02-thatha-oru-doubt/ep02/final/frames"
EP3 = ROOT / "series/02-thatha-oru-doubt/ep03/final/frames"
GN = ROOT / "series/01-groundnut"
STEEL, EDGE = "#c9d0d6", "#3b4248"


def svg_layer(body):
    return Image.open(io.BytesIO(cairosvg.svg2png(
        bytestring=f'<svg xmlns="http://www.w3.org/2000/svg" width="720" height="1280">{body}</svg>'.encode())))


def cutout(path, seg):
    im = Image.open(path).convert("RGB").resize((720, 1280))
    a = np.array(remove(im, session=seg, only_mask=True))
    a = np.clip((a.astype(float) - 90) * 2.6, 0, 255).astype(np.uint8)
    return Image.fromarray(np.dstack([np.array(im), a]))


def tumbler(x, y, w=56, h=96, tea=True):
    """Steel tumbler standing on (x, y), milky tea showing at the top, a little steam."""
    s = (f'<path d="M {x - w / 2:.1f},{y - h:.1f} L {x + w / 2:.1f},{y - h:.1f} L {x + w * 0.42:.1f},{y:.1f} L {x - w * 0.42:.1f},{y:.1f} Z" '
         f'fill="{STEEL}" stroke="{EDGE}" stroke-width="3.5"/>'
         f'<line x1="{x - w * 0.25:.1f}" y1="{y - h * 0.92:.1f}" x2="{x - w * 0.2:.1f}" y2="{y - h * 0.08:.1f}" stroke="#eef2f5" stroke-width="5"/>'
         f'<ellipse cx="{x:.1f}" cy="{y - h:.1f}" rx="{w / 2:.1f}" ry="{w * 0.14:.1f}" fill="{"#c99a6a" if tea else STEEL}" stroke="{EDGE}" stroke-width="3"/>')
    if tea:
        s += "".join(f'<path d="M {x - 12 + k * 12:.0f},{y - h - 12:.0f} q 8,-12 0,-24 q -8,-12 0,-24" stroke="#ffffff" stroke-width="4" '
                     f'fill="none" stroke-opacity="0.7" stroke-linecap="round"/>' for k in range(3))
    return s


def davara(x, y, w=170, h=58):
    """The wide steel cup-saucer (davara) with its rim at height y."""
    return (f'<path d="M {x - w / 2:.1f},{y:.1f} Q {x - w / 2 + 6:.1f},{y + h:.1f} {x:.1f},{y + h:.1f} Q {x + w / 2 - 6:.1f},{y + h:.1f} {x + w / 2:.1f},{y:.1f} Z" '
            f'fill="{STEEL}" stroke="{EDGE}" stroke-width="4"/>'
            f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{w / 2:.1f}" ry="{h * 0.22:.1f}" fill="#dfe4e8" stroke="{EDGE}" stroke-width="4"/>')


def phone(x, y, ang=-6):
    return (f'<g transform="translate({x} {y}) rotate({ang})"><rect x="-38" y="-75" width="76" height="150" rx="12" fill="#22272c" stroke="#0e1114" stroke-width="4"/>'
            f'<rect x="-31" y="-62" width="62" height="118" rx="5" fill="#5aa9e6"/><path d="M -31,30 L 31,-20 L 31,56 L -31,56 Z" fill="#7cc0ef"/>'
            f'<circle cx="0" cy="65" r="4" fill="#555"/></g>')


def murukku(x, y, r=34):
    rings = "".join(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r * k / 4:.0f}" fill="none" stroke="#b3772f" stroke-width="{r * 0.22:.0f}"/>'
                    for k in (1, 2, 3, 4))
    return rings + "".join(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r * k / 4:.0f}" fill="none" stroke="#d99a48" stroke-width="{r * 0.12:.0f}"/>'
                           for k in (1, 2, 3, 4))


def main():
    seg = new_session("isnet-anime")
    home = Image.open(ROOT / "assets/2d/source/07_home.png").convert("RGBA").resize((720, 1280))
    plate = home.crop((70, 250, 650, 1281)).resize((720, 1280), Image.LANCZOS)      # closer on the verandah
    plate.save(FR / "verandah_plate.png")

    # f_atea – the original thinnai frame, tea set over the bowl, his fingers back on top
    src = GN / "ep10/final/frames/f_sit_s3.png"
    im = Image.open(src).convert("RGBA")
    a = np.array(im.convert("RGB"))
    h = np.array(im.convert("HSV")).astype(int)
    H_, S_, V_ = h[..., 0] * 180 // 255, h[..., 1], h[..., 2]
    yy, xx = np.mgrid[0:1280, 0:720]
    front = (yy > 808) & (yy < 845) & (xx > 375) & (xx < 495) & (((H_ <= 16) & (S_ > 100) & (V_ > 196)) | (V_ < 50))
    out = im.copy()
    out.alpha_composite(svg_layer(davara(418, 748, 196, 66) + tumbler(418, 762)))
    out.alpha_composite(Image.fromarray(np.dstack([a, (front * 255).astype(np.uint8)])))
    out.convert("RGB").save(FR / "f_atea.png")
    print("saved f_atea")

    out = plate.copy()
    out.alpha_composite(svg_layer('<ellipse cx="450" cy="1048" rx="210" ry="30" fill="#4a1c08" fill-opacity="0.5"/>'
                                  '<ellipse cx="200" cy="952" rx="55" ry="14" fill="#4a1c08" fill-opacity="0.45"/>'))
    out.alpha_composite(cutout(GN / "ep04/final/frames/f_patience_s3.png", seg))
    out.convert("RGB").save(FR / "f_afin.png")
    print("saved f_afin")

    PDX = 50
    out = plate.copy()
    out.alpha_composite(Image.open(EP3 / "body_pod.png"), (PDX, 0))
    out.alpha_composite(svg_layer(phone(588 + PDX, 205)))
    out.alpha_composite(Image.open(EP3 / "fingers_pod.png"), (PDX, 0))
    out.convert("RGB").save(FR / "f_aphone.png")
    print("saved f_aphone")

    K, DX, DY = 0.94, 45, 1280 * 0.06
    out = plate.copy()
    out.alpha_composite(Image.open(EP2 / "body_two.png"), (int(DX), int(DY)))
    rx, ry = 98 * K + DX, 527 * K + DY
    lx, ly = 602 * K + DX, 530 * K + DY
    out.alpha_composite(svg_layer(tumbler(rx + 2, ry + 30, 60, 100) + murukku(lx - 2, ly - 40, 40)))
    out.alpha_composite(Image.open(EP2 / "fingers_two.png"), (int(DX), int(DY)))
    out.convert("RGB").save(FR / "f_atwo.png")
    print("saved f_atwo")


if __name__ == "__main__":
    main()
