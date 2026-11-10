"""One-Acre Challenge Ep 7 – start frames without a GPU. The brinjal field the day after the storm (Ep 6's after-rain
light, puddles, damaged plants), then sunny days for the careful re-sowing.

Run with the f5 env:  python -I make_frames.py [names...]
f_sad:    the owner's sitting drawing on Ep 5's stool, the near-empty jute seed pouch in his hand, after the rain
f_raise:  Groundnut Ep 8 f_pod_s3 (pod removed) – fist raised high, excited (about to throw the seeds), after the rain
f_doubt:  Ep 3 f_huh (sideways glance, palm up), after the rain
f_check:  Ep 4 f_soilw (crouching, wet soil in his hands) – used as it is (sunny, a puddle beside him)
f_mark:   Groundnut Ep 2 f_hoe_s8 on the sunny brinjal field: a small square of pegs and string marked off beside him
f_sow:    Groundnut Ep 2 f_kneel_s3 – kneeling; its groundnut seed replaced by a small brinjal seed pinched over a dibbled
          hole, a neat row of filled holes along the string
f_water:  Ep 3 f_water (kneeling with the watering can) + the pegged patch – sunny
f_hope:   Groundnut Ep 2 f_humour2_s3 (hand on his belly, beaming) on the sunny field
f_moral:  Ep 3 f_moral (open palm to the camera) – used as it is
f_goat:   Ep 3 f_huh – sunny (the goat!)
sunny_plate: Ep 3's grown_plate with a pegged patch of sprouting soil (for the goat and the joy jump)
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
from storm import pouch  # noqa: E402


def load_mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ep6 = load_mod("ep6frames", S4 / "ep06/final/make_frames.py")
ep5, ep4, ep3, sp1 = ep6.ep5, ep6.ep4, ep6.ep3, ep6.sp1
svg, over, lama_fill, skin_in, cut, relight = ep3.svg, ep3.over, ep3.lama_fill, ep3.skin_in, ep4.cut, ep6.relight
W, H = 720, 1280
PUD = ep6.PUD


def save(name, img, a):
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(FR / f"{name}.png")
    Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).save(FR / f"{name}_mask.png")
    print("saved", name)


def patch(cx, cy, w, h, sprouts=0.0):
    """A small pegged-off square of fresh, levelled soil in perspective (4 pegs, string)."""
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
    sk = w * 0.12
    pts = [(x0 + sk, y0), (x1 - sk, y0), (x1, y1), (x0, y1)]
    poly = " ".join(f"{x:.0f},{y:.0f}" for x, y in pts)
    g = f'<polygon points="{poly}" fill="#5a3620"/>'
    rng = np.random.default_rng(int(cx))
    for _ in range(40):
        u, v = rng.uniform(0.1, 0.9), rng.uniform(0.1, 0.9)
        x = (x0 + sk * (1 - v)) + (w - 2 * sk * (1 - v)) * u
        y = y0 + h * v
        g += f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{2 + 4 * v:.1f}" ry="{1 + 2 * v:.1f}" fill="#7a4a2a"/>'
    for r in range(3):                                    # rows of sown spots
        v = (r + 0.5) / 3
        for c in range(4):
            u = (c + 0.5) / 4
            x = (x0 + sk * (1 - v)) + (w - 2 * sk * (1 - v)) * u
            y = y0 + h * v
            g += f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{2 + 3 * v:.1f}" fill="#3a2010"/>'
            if sprouts:
                s = (0.4 + 0.6 * v) * sprouts
                g += (f'<path d="M {x:.0f},{y:.0f} l 0,{-14 * s:.0f}" stroke="#7cb342" stroke-width="{2 + 2 * s:.1f}"/>'
                      f'<ellipse cx="{x - 6 * s:.0f}" cy="{y - 15 * s:.0f}" rx="{6 * s:.1f}" ry="{3.5 * s:.1f}" fill="#8bc34a"/>'
                      f'<ellipse cx="{x + 6 * s:.0f}" cy="{y - 15 * s:.0f}" rx="{6 * s:.1f}" ry="{3.5 * s:.1f}" fill="#8bc34a"/>')
    s = h / 120
    for x, y in pts:
        g += (f'<rect x="{x - 3 * s:.0f}" y="{y - 30 * s:.0f}" width="{6 * s:.0f}" height="{32 * s:.0f}" fill="#8a5a2b" stroke="#3e2410" stroke-width="1.5"/>'
              f'<rect x="{x - 4 * s:.0f}" y="{y - 32 * s:.0f}" width="{8 * s:.0f}" height="{6 * s:.0f}" fill="#e53935"/>')
    pp = pts + [pts[0]]
    g += "".join(f'<line x1="{a[0]:.0f}" y1="{a[1] - 22 * s:.0f}" x2="{b[0]:.0f}" y2="{b[1] - 22 * s:.0f}" stroke="#f5f5f5" stroke-width="1.6"/>' for a, b in zip(pp[:-1], pp[1:]))
    return g


def f_sad(seg):
    rgb, a = sp1.sitting_without_seat(seg)
    fig = np.dstack([rgb, a]).astype(np.float32)
    ch = sp1.svg(ep5.stool(), 1024, 1536).astype(np.float32)
    yy, xx = np.mgrid[0:1536, 0:1024]
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(int)
    skin = (xx > 320) & (xx < 450) & (yy > 820) & (yy < 950) & (hsv[..., 0] <= 22) & (hsv[..., 1] > 100) & (a > 200)
    fingers = fig.copy()
    fingers[..., 3] = skin * 255
    bag = sp1.svg(pouch(400, 905, 0.95, -18, 0), 1024, 1536).astype(np.float32)
    layer = np.zeros((1536, 1024, 4), np.float32)
    for part in (ch, fig, bag, fingers):
        al = part[..., 3:4] / 255
        layer[..., :3] = layer[..., :3] * (1 - al) + part[..., :3] * al
        layer[..., 3:4] = np.maximum(layer[..., 3:4], part[..., 3:4])
    plate = np.array(Image.open(S4 / "ep06/final/frames/after_plate.png").convert("RGB"))
    sh = sp1.svg('<ellipse cx="360" cy="1238" rx="210" ry="22" fill="#000" fill-opacity="0.3"/>', W, H)
    pl = over(plate.astype(np.float32), sh.astype(np.float32)).astype(np.uint8)
    out, mask, off = sp1.place(pl, np.clip(layer, 0, 255).astype(np.uint8), 0.62, 360, 1245, 1430)
    save("f_sad", ep6.dim(out.astype(np.float32), mask / 255), mask / 255)


def f_raise(seg):
    rgb = ep4.load("ep08/final/frames/f_pod_s3.png")
    a = cut(seg, rgb)
    yy, xx = np.mgrid[0:H, 0:W]
    hsv = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(int)
    pod = (xx > 525) & (xx < 615) & (yy > 80) & (yy < 265) & (hsv[..., 0] >= 10) & (hsv[..., 0] <= 30) & (hsv[..., 1] < 150) & (hsv[..., 2] > 150)
    pod = cv2.morphologyEx(pod.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((13, 13), np.uint8))
    fing = skin_in(rgb, a, (598, 196, 660, 300)) & (pod == 0)
    box = ((xx > 524) & (xx < 618) & (yy > 76) & (yy < 268)).astype(np.uint8)
    hole = (cv2.dilate(pod, np.ones((9, 9), np.uint8)) | box) & (~fing).astype(np.uint8)
    a2 = a.copy()
    a2[hole > 0] = 0
    out, hz = ep4.field(lama_fill(rgb, hole), a2, 51)
    out = relight(out, a2, "after", puddles=PUD, seed=11)
    ap = np.array(Image.open(S4 / "ep06/final/frames/after_plate.png").convert("RGB")).astype(np.float32)
    skin = (hsv[..., 0] <= 22) & (hsv[..., 1] > 70) & (hsv[..., 2] > 90)
    above = (xx > 550) & (xx < 650) & (yy > 90) & (yy < 268) & ~cv2.dilate(skin.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    a2[above] = 0
    h2 = ((cv2.dilate(hole, np.ones((31, 31), np.uint8)) > 0) & ~fing & (a2 < 0.5) & (yy < 300)) | above
    h2 = (cv2.dilate(box, np.ones((31, 31), np.uint8)) > 0) & (yy < 296) & ~cv2.dilate(fing.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    a2[h2] = 0
    from rain import overcast, storm_sky
    cl = storm_sky(W, ep6.HZ + 40, seed=11)[..., :3].astype(np.float32) * 0.55 + np.array([200, 206, 212]) * 0.45
    sky = np.zeros((H, W, 3), np.float32)
    sky[:ep6.HZ + 40] = overcast(np.clip(cl, 0, 255).astype(np.uint8), 0.1)
    m = cv2.GaussianBlur(cv2.dilate(h2.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32), (0, 0), 1.5)[..., None]
    out = out * (1 - m) + sky * m
    lit = relight(rgb, a, "after", seed=11)
    out[fing] = lit[fing]
    seeds = ('<ellipse cx="588" cy="282" rx="30" ry="14" fill="#4a2a14"/>'
             + "".join(f'<ellipse cx="{x}" cy="{y}" rx="6" ry="4.5" fill="#e6d6a6" stroke="#7a6a30" stroke-width="1.5" transform="rotate({r} {x} {y})"/>'
                       for x, y, r in ((570, 276, 20), (582, 270, -10), (596, 274, 30), (606, 280, 0), (588, 280, 50), (575, 284, -30))))
    sd = svg(seeds)
    out = over(out, sd)
    out[fing & (yy > 286)] = lit[fing & (yy > 286)]
    save("f_raise", out, a2)


def f_doubt(seg):
    img, a = ep6.ep3_frame("f_huh")
    save("f_doubt", relight(img, a, "after", puddles=PUD, seed=15), a)


def copy(src, name):
    shutil.copy(src, FR / f"{name}.png")
    m = Path(str(src).replace(".png", "_mask.png"))
    if m.exists():
        shutil.copy(m, FR / f"{name}_mask.png")
    print("copied", name)


def f_mark(seg):
    rgb = ep4.load("ep02/final/frames/f_hoe_s8.png")
    a = cut(seg, rgb)
    out, hz = ep4.field(rgb, a, 52)
    out = over(out, svg(patch(470, 1110, 300, 120)), keep=a)
    save("f_mark", out, a)


def f_sow(seg):
    rgb = ep4.load("ep02/final/frames/f_kneel_s3.png")
    a = cut(seg, rgb)
    yy, xx = np.mgrid[0:H, 0:W]
    hsv = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(int)
    seedm = (xx > 100) & (xx < 160) & (yy > 836) & (yy < 930) & (((hsv[..., 0] >= 160) | (hsv[..., 0] <= 5)) & (hsv[..., 1] > 40) & (hsv[..., 2] > 150))
    hole = cv2.dilate(cv2.morphologyEx(seedm.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)), np.ones((7, 7), np.uint8))
    clean = lama_fill(rgb, hole)
    out, hz = ep4.field(clean, a, 53)
    g = ('<path d="M 30,1010 L 330,1000" stroke="#f5f5f5" stroke-width="2"/>'
         + "".join(f'<ellipse cx="{x}" cy="{1012 - (x - 30) * 0.03:.0f}" rx="9" ry="4" fill="#3a2010"/>' for x in (190, 240, 290))
         + '<ellipse cx="136" cy="1006" rx="10" ry="5" fill="#2a1408"/>'
         '<ellipse cx="136" cy="935" rx="7" ry="5" fill="#efe0b0" stroke="#8a7a40" stroke-width="1.5"/>')
    out = over(out, svg(g), keep=None)
    fing = skin_in(rgb, a, (80, 790, 170, 935)) & (hole == 0)
    lit = ep3.rich(rgb, a, hz)
    out[fing] = lit[fing]
    save("f_sow", out, a)


def f_water(seg):
    img = np.array(Image.open(S4 / "ep03/final/frames/f_water.png").convert("RGB")).astype(np.float32)
    a = np.array(Image.open(S4 / "ep03/final/frames/f_water_mask.png").convert("L")).astype(np.float32) / 255
    out = over(img, svg(patch(260, 1150, 360, 150)), keep=a)
    save("f_water", out, a)


def f_hope(seg):
    rgb = ep4.load("ep02/final/frames/f_humour2_s3.png")
    a = cut(seg, rgb)
    out, hz = ep4.field(rgb, a, 54)
    save("f_hope", out, a)


def sunny_plate():
    g = np.array(Image.open(S4 / "ep03/final/frames/grown_plate.png").convert("RGB")).astype(np.float32)
    for name, sp in (("patch_plate", 0.0), ("sprout_plate", 1.0)):
        out = over(g, svg(patch(360, 1110, 420, 170, sp)))
        Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(FR / f"{name}.png")
    print("saved plates")


def main():
    only = sys.argv[1:]
    seg = new_session("isnet-anime")
    for name, fn in (("f_sad", f_sad), ("f_raise", f_raise), ("f_doubt", f_doubt), ("f_mark", f_mark), ("f_sow", f_sow),
                     ("f_water", f_water), ("f_hope", f_hope)):
        if not only or name in only:
            fn(seg)
    if not only or "copy" in only:
        copy(S4 / "ep04/final/frames/f_soilw.png", "f_check")
        copy(S4 / "ep03/final/frames/f_moral.png", "f_moral")
        copy(S4 / "ep03/final/frames/f_huh.png", "f_goat")
    if not only or "plates" in only:
        sunny_plate()


if __name__ == "__main__":
    main()
