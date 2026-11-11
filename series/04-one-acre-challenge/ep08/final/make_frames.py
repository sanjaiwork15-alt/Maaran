"""One-Acre Challenge Ep 8 (finale) – start frames without a GPU. The sunny brinjal field: Ep 7's sown patch, now fenced,
and later grown into fruiting brinjal bushes.

Run with the f5 env:  python -I make_frames.py [names...]
f_point:  Ep 3 f_point (pointing down at a plant) – "Adei aadu!"
f_fence:  Ep 7 f_mark (hoe) – the patch beside him now fenced with sticks and rope
f_check:  Ep 4 f_soilw (crouching, soil in his hands) – as it is
f_water:  Ep 7 f_water (watering can, the pegged patch) – as it is
f_pick:   Ep 3 f_inspect (kneeling, fingers at a brinjal plant) – the plant now bears purple brinjals, a full basket beside him
f_basket: the owner's standing drawing (01_front) holding a wicker basket heaped with brinjals, beside the fenced patch
f_note:   Ep 5's palm pose with his closed notebook, on the harvest field
f_moral:  Ep 3 f_moral (open palm) – as it is
f_grin:   Ep 3 f_huh (sideways glance, palm up, smiling) – as it is
fence_plate / lush_plate: Ep 3's grown_plate with the fenced patch – seedlings / grown fruiting bushes
"""
import importlib.util
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import new_session

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FR = HERE / "frames"
S4 = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools/toon"))
from finale import basket, brinjal_fruit, fence, fruiting_brinjal  # noqa: E402


def load_mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ep7 = load_mod("ep7frames", S4 / "ep07/final/make_frames.py")
ep5, ep4, ep3 = ep7.ep5, ep7.ep4, ep7.ep3
sp2 = load_mod("sp2frames", ROOT / "series/05-diwali/sp02/final/make_frames.py")
svg, over = ep3.svg, ep3.over
W, H = 720, 1280


def save(name, img, a):
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(FR / f"{name}.png")
    Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).save(FR / f"{name}_mask.png")
    print("saved", name)


def frame(path):
    img = np.array(Image.open(path).convert("RGB")).astype(np.float32)
    a = np.array(Image.open(str(path).replace(".png", "_mask.png")).convert("L")).astype(np.float32) / 255
    return img, a


def patch_fence(cx, cy, w, h):
    """Fence posts round the ep7 patch(cx, cy, w, h) corners + mid points, smaller further away."""
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
    sk = w * 0.12
    far, near = h / 260, h / 160
    pts = [(x0 + sk, y0, far), (cx, y0, far), (x1 - sk, y0, far), (x1, y1, near), (cx, y1, near), (x0, y1, near)]
    return pts


def plates():
    g = np.array(Image.open(S4 / "ep03/final/frames/grown_plate.png").convert("RGB")).astype(np.float32)
    cx, cy, w, h = 360, 1110, 420, 170
    pts = patch_fence(cx, cy, w, h)
    back, front = pts[:3], pts[3:]
    for name, grown in (("fence_plate", False), ("lush_plate", True)):
        out = over(g, svg(ep7.patch(cx, cy, w, h, 0.0 if grown else 1.0)))
        out = over(out, svg(fence(back, 1.0)))
        if grown:
            for k, (x, y) in enumerate(((250, 1060), (360, 1060), (470, 1060), (230, 1150), (360, 1150), (490, 1150))):
                out = over(out, svg(fruiting_brinjal(x, y, 0.32 if y < 1100 else 0.4, k, 3, 1)))
        out = over(out, svg(fence(front, 1.0) + fence(pts, 1.0, 1.0, 1.0).split('<path d="M ', 1)[0] * 0 +
                            "".join(f'<path d="M {a[0] + 3},{a[1] - 120 * a[2] * l:.0f} L {b[0] + 3},{b[1] - 120 * b[2] * l:.0f}" stroke="#e8d5a0" stroke-width="2.5"/>'
                                    for l in (0.45, 0.8) for a, b in zip(pts, pts[1:] + pts[:1]))))
        Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(FR / f"{name}.png")
    print("saved plates")


def f_fence(seg):
    img, a = frame(S4 / "ep07/final/frames/f_mark.png")
    pts = patch_fence(470, 1110, 300, 120)
    rope = "".join(f'<path d="M {p[0] + 3},{p[1] - 120 * p[2] * l:.0f} L {q[0] + 3},{q[1] - 120 * q[2] * l:.0f}" stroke="#e8d5a0" stroke-width="2.5"/>'
                   for l in (0.45, 0.8) for p, q in zip(pts, pts[1:] + pts[:1]))
    out = over(img, svg(fence(pts, 1.0) + rope), keep=a)
    save("f_fence", out, a)


def f_pick(seg):
    img, a = frame(S4 / "ep03/final/frames/f_inspect.png")
    g = (brinjal_fruit(160, 940, 0.42, 12) + brinjal_fruit(70, 900, 0.38, -10) + brinjal_fruit(115, 965, 0.4, 4)
         + basket(330, 1265, 0.62, 1.0))
    out = over(img, svg(g), keep=a * 0)
    rgb = np.array(Image.open(S4 / "ep03/final/frames/f_inspect.png").convert("RGB")).astype(np.float32)
    fing = ep3.skin_in(rgb, a, (80, 790, 170, 935))
    out[fing] = rgb[fing]
    save("f_pick", out, a)


def f_basket(seg):
    hang = ('<g transform="translate(1560 1900) scale(1.5) translate(-1560 -1900)">'
            '<path d="M 1420,2150 Q 1560,1650 1700,2150" stroke="#8d5a2b" stroke-width="26" fill="none"/>'
            '<path d="M 1420,2150 Q 1560,1650 1700,2150" stroke="#c49a5a" stroke-width="10" fill="none"/>'
            + "".join(brinjal_fruit(1430 + 44 * k, 2040 - (k % 3) * 26, 0.85, -60 + 20 * k) for k in range(7)) +
            '<path d="M 1360,2150 L 1760,2150 L 1720,2440 L 1400,2440 Z" fill="#c49a5a" stroke="#6d4320" stroke-width="9"/>'
            + "".join(f'<path d="M {1366 + 6 * k},{2190 + 44 * k} L {1754 - 6 * k},{2190 + 44 * k}" stroke="#8d5a2b" stroke-width="7"/>' for k in range(6))
            + "".join(f'<path d="M {1380 + 44 * k},2152 L {1410 + 36 * k},2436" stroke="#a87a40" stroke-width="6"/>' for k in range(9)) +
            '<rect x="1348" y="2132" width="424" height="30" rx="10" fill="#a87a40" stroke="#6d4320" stroke-width="7"/></g>')
    lay = sp2.front_figure(seg, hang)
    plate = np.array(Image.open(FR / "lush_plate.png").convert("RGB")).astype(np.float32)
    sh = svg('<ellipse cx="480" cy="1240" rx="150" ry="20" fill="#000" fill-opacity="0.3"/>')
    out, mask = sp2.place(over(plate, sh), lay, 1000, 480, 1245)
    save("f_basket", out.astype(np.float32), mask / 255)


def f_note(seg):
    ep5.FR = FR
    shutil.copy(FR / "lush_plate.png", FR / "empty_plate.png")
    out, a, _ = ep5.palm_frame(seg, lambda x, y, s: ep5.magazine(x, y, s * 0.55, closed=True))
    save("f_note", out, a)


def copy(src, name):
    shutil.copy(src, FR / f"{name}.png")
    shutil.copy(str(src).replace(".png", "_mask.png"), FR / f"{name}_mask.png")
    print("copied", name)


def main():
    only = sys.argv[1:]
    if not only or "plates" in only:
        plates()
    seg = new_session("isnet-anime")
    for name, fn in (("f_fence", f_fence), ("f_pick", f_pick), ("f_basket", f_basket), ("f_note", f_note)):
        if not only or name in only:
            fn(seg)
    if not only or "copy" in only:
        copy(S4 / "ep03/final/frames/f_point.png", "f_point")
        copy(S4 / "ep04/final/frames/f_soilw.png", "f_check")
        copy(S4 / "ep07/final/frames/f_water.png", "f_water")
        copy(S4 / "ep03/final/frames/f_moral.png", "f_moral")
        copy(S4 / "ep03/final/frames/f_huh.png", "f_grin")


if __name__ == "__main__":
    main()
