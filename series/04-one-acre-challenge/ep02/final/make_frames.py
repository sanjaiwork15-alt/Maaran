"""One-Acre Challenge Ep 2 – start frames without a GPU: the same dry field as Ep 1 (its dry() grade), new poses,
and the compost in code (a giant steaming compost mound behind him, compost spread on the ground).

Run with the f5 env:  python -I make_frames.py
f_idea:    Groundnut Ep 4 f_patience_s3 – kneeling, finger up ("Thatha kitta oru idea irukku!")
f_compost: Groundnut Ep 2 f_soil_s3    – crouching, dark crumbly compost in his hands (kept dark, the field dried)
f_collect: Groundnut Ep 2 f_clear_s3   – bending to pick up dry grass and leaves
f_admire:  Groundnut Ep 2 f_humour2_s3 – hand on his belly, beaming, a GIANT compost mound behind him
f_mound:   Ep 1 f_point (dry)          – pointing at the ground, the giant mound behind him ("malaiye uruvaakkittene!")
f_mix:     Ep 1 f_dig (dry)            – digging, a thin layer of compost spread on the soil around the spade
Ep 1's dry frames (f_proud, f_seeds, f_nut, f_soil …) are reused from ../../ep01/final/frames/.
"""
import importlib.util
import io
from pathlib import Path

import cairosvg
import cv2
import numpy as np
from PIL import Image
from rembg import new_session, remove

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FR = HERE / "frames"
GN = ROOT / "series/01-groundnut"
EP1 = HERE.parents[1] / "ep01/final"
spec = importlib.util.spec_from_file_location("ep1frames", EP1 / "make_frames.py")
ep1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ep1)
import sys  # noqa: E402
sys.path.insert(0, str(ROOT / "tools/toon"))
from acre import mound  # noqa: E402
W, H = 720, 1280


def svg_layer(body):
    return np.array(Image.open(io.BytesIO(cairosvg.svg2png(
        bytestring=f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">{body}</svg>'.encode()))).convert("RGBA")).astype(np.float32)


import math  # noqa: E402  (used by mound)


def compost_layer(x0, x1, y0, y1, seed=5):
    """A thin, even layer of compost spread on the ground (perspective: smaller crumbs further away)."""
    rng = np.random.default_rng(seed)
    g = []
    for _ in range(1600):
        y = rng.uniform(y0, y1)
        k = (y - y0) / (y1 - y0)
        x = rng.uniform(x0 - 60 * k, x1 + 60 * k)
        r = 2.5 + 6 * k
        g.append(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{r:.1f}" ry="{r * 0.6:.1f}" fill="{rng.choice(["#3a2212", "#5e3a20", "#2e1a0c"])}"/>')
    return "".join(g)


def behind(frame_rgb, alpha, layer):
    """Composite an RGBA layer into the background only (Thatha stays in front)."""
    a = layer[..., 3:4] / 255 * (1 - alpha[..., None])
    return np.clip(frame_rgb * (1 - a) + layer[..., :3] * a, 0, 255).astype(np.uint8)


def main():
    seg = new_session("isnet-anime")

    def cut(rgb):
        a = np.array(remove(Image.fromarray(rgb), session=seg, only_mask=True)).astype(np.float32)
        a = np.clip((a - 90) * 2.6, 0, 255) / 255
        return cv2.GaussianBlur(cv2.dilate(a, np.ones((5, 5), np.uint8)), (0, 0), 1.5)

    def dried(src, horizon):
        rgb = np.array(Image.open(src).convert("RGB").resize((W, H)))
        a = cut(rgb)
        return ep1.dry(rgb, a, horizon), a

    out, a = dried(GN / "ep04/final/frames/f_patience_s3.png", 640)
    reg = out[930:1080, 80:200].astype(np.float32)               # the little sprout by his hand: dried too
    hsv = cv2.cvtColor(reg.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(int)
    g = ((hsv[..., 0] >= 28) & (hsv[..., 0] <= 90) & (hsv[..., 1] > 50)).astype(np.float32)[..., None]
    grey = reg.mean(axis=2, keepdims=True)
    straw = np.concatenate([grey * 0.9 + 70, grey * 0.8 + 50, grey * 0.4 + 20], -1)
    out[930:1080, 80:200] = np.clip(reg * (1 - g) + straw * g, 0, 255).astype(np.uint8)
    Image.fromarray(out).save(FR / "f_idea.png")
    out, a = dried(GN / "ep02/final/frames/f_soil_s3.png", 615)  # the handful becomes dark, rich compost
    reg = out[590:800, 215:395].astype(np.float32)
    src = np.array(Image.open(GN / "ep02/final/frames/f_soil_s3.png").convert("RGB").resize((W, H)))[590:800, 215:395]
    hsv = cv2.cvtColor(src, cv2.COLOR_RGB2HSV).astype(int)
    soilm = ((hsv[..., 0] <= 14) | (hsv[..., 0] >= 170)) & (hsv[..., 1] > 120) & (hsv[..., 2] < 200)
    m = cv2.GaussianBlur(soilm.astype(np.float32), (0, 0), 1.0)[..., None]
    v = reg.mean(axis=2, keepdims=True) / 255
    dark = np.concatenate([40 + 70 * v, 22 + 45 * v, 10 + 25 * v], -1)
    out[590:800, 215:395] = np.clip(reg * (1 - m) + dark * m, 0, 255).astype(np.uint8)
    Image.fromarray(out).save(FR / "f_compost.png")
    out, a = dried(GN / "ep02/final/frames/f_clear_s3.png", 640)
    Image.fromarray(out).save(FR / "f_collect.png")
    out, a = dried(GN / "ep02/final/frames/f_humour2_s3.png", 700)
    Image.fromarray(behind(out, a, svg_layer(mound(680, 1070, 820, 540)))).save(FR / "f_admire.png")
    p = np.array(Image.open(EP1 / "frames/f_point.png").convert("RGB"))
    Image.fromarray(behind(p, cut(p), svg_layer(mound(680, 1020, 820, 520, seed=4)))).save(FR / "f_mound.png")
    d = np.array(Image.open(EP1 / "frames/f_dig.png").convert("RGB"))
    Image.fromarray(behind(d, cut(d), svg_layer(compost_layer(150, 640, 1030, 1240)))).save(FR / "f_mix.png")
    print("saved frames")


if __name__ == "__main__":
    main()
