"""Day 1 (solo rework, owner 2026-10-26: "Thatha will be the solo person") – start frames without a GPU.

Run with the f5 env:  python -I make_frames.py
Base: the approved thinnai frame (Groundnut Ep 10 f_sit_s3, 720x1280): Thatha sitting on the thinnai of his house.
LaMa (CPU) removes the groundnut bowl (lap) and the groundnut in his raised hand; then props are drawn in code:
f_sphone:  his phone held in his lap hand (back of the phone to us; he looks down at it), steaming tea tumbler and his
           task list (paper with empty checkboxes – no text) on the thinnai beside him. Afternoon light.
f_slate:   the same later: tea without steam, warmer, lower light (time has slipped away).
f_slist:   the task list in his lap hand, the phone lying face down on the thinnai.
f_sstand:  the empty thinnai (Thatha removed with LaMa) + Thatha standing (owner's front art, x2) with his stick,
           the phone face down on the step behind him.
"""
import io
import sys
from pathlib import Path

import cairosvg
import cv2
import numpy as np
import torch
from PIL import Image, ImageFilter
from rembg import new_session, remove

_jl = torch.jit.load
torch.jit.load = lambda p, *a, **k: _jl(p, map_location="cpu")     # the LaMa TorchScript was saved on CUDA
from simple_lama_inpainting import SimpleLama  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FR = HERE / "frames"
W, H = 720, 1280
STEEL, EDGE = "#c9d0d6", "#3b4248"


def svg_layer(body, w=W, h=H):
    return Image.open(io.BytesIO(cairosvg.svg2png(
        bytestring=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">{body}</svg>'.encode()))).convert("RGBA")


def tumbler(x, y, w=40, h=70, steam=True):
    s = (f'<ellipse cx="{x}" cy="{y + 2}" rx="{w * 0.62:.0f}" ry="7" fill="#3a1c0a" fill-opacity="0.35"/>'
         f'<path d="M {x - w / 2:.1f},{y - h:.1f} L {x + w / 2:.1f},{y - h:.1f} L {x + w * 0.42:.1f},{y:.1f} L {x - w * 0.42:.1f},{y:.1f} Z" '
         f'fill="{STEEL}" stroke="{EDGE}" stroke-width="3"/>'
         f'<line x1="{x - w * 0.25:.1f}" y1="{y - h * 0.9:.1f}" x2="{x - w * 0.2:.1f}" y2="{y - h * 0.1:.1f}" stroke="#eef2f5" stroke-width="4"/>'
         f'<ellipse cx="{x}" cy="{y - h:.1f}" rx="{w / 2:.1f}" ry="{w * 0.14:.1f}" fill="#c99a6a" stroke="{EDGE}" stroke-width="2.5"/>')
    if steam:
        s += "".join(f'<path d="M {x - 9 + k * 9:.0f},{y - h - 8:.0f} q 6,-9 0,-18 q -6,-9 0,-18" stroke="#ffffff" stroke-width="3.5" '
                     f'fill="none" stroke-opacity="0.75" stroke-linecap="round"/>' for k in range(3))
    return s


def task_list(x, y, ang=-8, s=1.0, ticks=0):
    """A paper with empty checkboxes and scribble lines (no letters)."""
    rows = "".join(f'<rect x="-34" y="{-46 + i * 22}" width="12" height="12" fill="none" stroke="#333" stroke-width="2"/>'
                   f'<path d="M -14,{-40 + i * 22} q 10,-5 20,0 t 20,0 t 18,0" stroke="#4a6fa5" stroke-width="2.4" fill="none"/>'
                   + (f'<path d="M -33,{-41 + i * 22} l 4,5 l 8,-10" stroke="#2e8b3e" stroke-width="3" fill="none"/>' if i < ticks else "")
                   for i in range(4))
    return (f'<g transform="translate({x} {y}) rotate({ang}) scale({s})">'
            f'<rect x="-46" y="-62" width="98" height="120" fill="#fbf8ee" stroke="#8a7a5a" stroke-width="2.5"/>{rows}</g>')


def phone_back(x, y, w=58, ang=-6):
    """His phone seen from the back, held upright (he looks at the screen)."""
    h = w * 2.0
    return (f'<g transform="rotate({ang} {x} {y})">'
            f'<rect x="{x - w / 2:.1f}" y="{y - h:.1f}" width="{w}" height="{h:.1f}" rx="9" fill="#2a2f36" stroke="#0d0f12" stroke-width="3.5"/>'
            f'<rect x="{x - w / 2 + 6:.1f}" y="{y - h + 6:.1f}" width="{w * 0.36:.1f}" height="{w * 0.56:.1f}" rx="6" fill="#15181c"/>'
            f'<circle cx="{x - w / 2 + 6 + w * 0.18:.1f}" cy="{y - h + 6 + w * 0.15:.1f}" r="{w * 0.09:.1f}" fill="#0a0c0e" stroke="#666" stroke-width="2"/>'
            f'<circle cx="{x - w / 2 + 6 + w * 0.18:.1f}" cy="{y - h + 6 + w * 0.41:.1f}" r="{w * 0.09:.1f}" fill="#0a0c0e" stroke="#666" stroke-width="2"/>'
            f'<path d="M {x + w * 0.3:.1f},{y - h + 8:.1f} l 5,0 l {-w * 0.45:.1f},{h - 16:.1f} l -5,0 Z" fill="#ffffff" fill-opacity="0.08"/></g>')


def phone_down(x, y, ang=4):
    """The phone lying face down on the thinnai (back up, seen from the front, a bit foreshortened)."""
    return (f'<g transform="translate({x} {y}) rotate({ang})"><ellipse cx="0" cy="10" rx="44" ry="7" fill="#3a1c0a" fill-opacity="0.35"/>'
            f'<path d="M -40,6 L 40,6 L 34,-8 L -34,-8 Z" fill="#2a2f36" stroke="#0d0f12" stroke-width="3"/>'
            f'<rect x="-26" y="-6" width="14" height="6" rx="2" fill="#15181c"/></g>')


def grade(img, warm=0.0, dim=0.0):
    """Later light: warmer and a little dimmer."""
    a = np.asarray(img).astype(np.float32)
    a[..., 0] *= 1 + 0.08 * warm
    a[..., 2] *= 1 - 0.18 * warm
    a *= 1 - dim
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def main():
    seg = new_session("isnet-anime")
    lama = SimpleLama(device=torch.device("cpu"))
    src = Image.open(ROOT / "series/01-groundnut/ep10/final/frames/f_sit_s3.png").convert("RGB").resize((W, H))
    rgb = np.array(src)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(int)
    hh, ss, vv = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    yy, xx = np.mgrid[0:H, 0:W]

    # the bowl + groundnuts in his lap (keep the fingers under it and the thumb on its rim), and the nut at his mouth
    bowl = np.zeros((H, W), np.uint8)
    cv2.ellipse(bowl, (420, 772), (80, 50), 0, 0, 360, 1, -1)
    skin = (hh <= 16) & (ss > 110) & (vv > 150)
    fingers = (yy > 806) | ((xx > 437) & (xx < 475) & (yy > 772) & skin)
    bowl = bowl.astype(bool) & ~fingers
    nut = (xx > 280) & (xx < 335) & (yy > 452) & (yy < 500) & (hh >= 14) & (hh <= 32) & (ss > 110) & (vv > 170)
    m = (bowl | cv2.dilate(nut.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)).astype(np.uint8) * 255
    clean = lama(src, Image.fromarray(m).filter(ImageFilter.MaxFilter(5))).resize((W, H))
    clean.save(FR / "lama_clean.png")
    front = np.array(src)
    fmask = (((yy > 806) & (yy < 850) & (xx > 330) & (xx < 500)) | ((xx > 437) & (xx < 475) & (yy > 772) & (yy < 806))) \
        & (((hh <= 16) & (ss > 100) & (vv > 150)) | (vv < 60))
    fingers_l = Image.fromarray(np.dstack([front, (fmask * 255).astype(np.uint8)])).convert("RGBA")

    out = clean.convert("RGBA")
    out.alpha_composite(svg_layer(tumbler(640, 1000) + task_list(652, 1092, -14, 0.72)))
    out.alpha_composite(svg_layer(phone_back(420, 815)))
    out.alpha_composite(fingers_l)
    out.convert("RGB").save(FR / "f_sphone.png")

    out = grade(clean, warm=1.0, dim=0.1).convert("RGBA")
    out.alpha_composite(svg_layer(tumbler(640, 1000, steam=False) + task_list(652, 1092, -14, 0.72)))
    out.alpha_composite(svg_layer(phone_back(420, 815)))
    lay = np.array(fingers_l)
    lay[..., :3] = np.array(grade(Image.fromarray(lay[..., :3]), warm=1.0, dim=0.1))
    out.alpha_composite(Image.fromarray(lay))
    out.convert("RGB").save(FR / "f_slate.png")

    out = grade(clean, warm=1.0, dim=0.1).convert("RGBA")
    out.alpha_composite(svg_layer(tumbler(640, 1000, steam=False) + phone_down(652, 1098, -6)))
    out.alpha_composite(svg_layer(task_list(418, 768, -4, 1.05)))
    out.alpha_composite(Image.fromarray(lay))
    out.convert("RGB").save(FR / "f_slist.png")

    # empty thinnai + standing Thatha
    alpha = np.array(remove(src, session=seg, only_mask=True))
    body = (alpha > 60) & (xx > 100) & (xx < 640) & (yy > 200) & (yy < 1225)             # him, not the house
    stick = (xx > 30) & (xx < 140) & (yy > 590) & (yy < 1230) & (hh >= 5) & (hh <= 22) & (vv < 175) & (ss > 90)
    tm = cv2.dilate((body | stick).astype(np.uint8), np.ones((15, 15), np.uint8)) * 255
    plate = lama(src, Image.fromarray(tm)).resize((W, H))
    plate.save(FR / "thinnai_plate.png")
    out = grade(plate, warm=1.0, dim=0.1).convert("RGBA")
    out.alpha_composite(svg_layer(tumbler(640, 1000, steam=False) + phone_down(470, 1040)))
    fr = Image.open(ROOT / "assets/2d/up/01_front.png").convert("RGB")
    fa = np.array(remove(fr, session=seg, only_mask=True)).astype(np.float32)
    fa = np.clip((fa - 90) * 2.6, 0, 255).astype(np.uint8)
    fig = Image.fromarray(np.dstack([np.array(fr), fa]))
    bb = fig.getbbox()
    fig = fig.crop(bb)
    hgt = 1150
    fig = fig.resize((round(fig.width * hgt / fig.height), hgt), Image.LANCZOS)
    fg = np.array(fig)
    fg[..., :3] = np.array(grade(Image.fromarray(fg[..., :3]), warm=0.6, dim=0.05))
    out.alpha_composite(svg_layer('<ellipse cx="330" cy="1238" rx="190" ry="26" fill="#3a1c0a" fill-opacity="0.4"/>'))
    out.alpha_composite(Image.fromarray(fg), (330 - fig.width // 2, 1245 - hgt))
    out.convert("RGB").save(FR / "f_sstand.png")
    import json
    k = hgt / fig.height if False else hgt / (bb[3] - bb[1])
    json.dump({"bbox_x2": bb, "scale": k, "off": [330 - round((bb[2] - bb[0]) * k) // 2, 1245 - hgt]},
              open(FR / "f_sstand_place.json", "w"))
    print("saved frames")


if __name__ == "__main__":
    main()
