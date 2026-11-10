"""One-Acre Challenge Ep 5 – start frames without a GPU. The one-acre field is bare now (rich tilled soil, no crop):
Thatha dreams of a "crores" crop (dragon fruit, from a picture-only farming magazine – no text).

Run with the f5 env:  python -I make_frames.py [names...]
empty_plate.png: the owner's field (05_field_vertical), rich bare soil
f_mag:     the owner's poses sheet (3rd) – the groundnuts in his cupped palm removed; a glossy farming magazine stands in
           his hand (dragon fruit + money on the cover, no words)
f_note:    the same pose, a closed notebook in his hand instead (planned!) – sunny
f_storm:   f_note under a darkening storm sky, grey light (cliffhanger)
f_present: Groundnut Ep 2 f_hook_s3 – palm raised to the whole field (the seeds in it removed)
f_mark:    Groundnut Ep 2 f_hoe_s8 – digging; marking pegs and a string line in the bare field
f_stool:   the owner's sitting drawing (09_sitting, brick seat removed – Diwali Sp 1's code) on a small wooden stool in
           the field, a glowing, half-see-through bundle of imaginary cash in his hand
f_stool2:  the same, the hand empty (the dream is gone)
f_moral:   Groundnut Ep 1 f5_cliff_s3 – open palm, explaining to the camera
sit_rgba.png: the seated figure alone (for the tractor daydream)
The planning shot uses Day 1's f_slist (thinking, a list in his hand) as it is (frames/f_think.png copy).
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
GN = ROOT / "series/01-groundnut"
sys.path.insert(0, str(ROOT / "tools/toon"))


def load_mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ep4 = load_mod("ep4frames", HERE.parents[1] / "ep04/final/make_frames.py")
ep3, ep1 = ep4.ep3, ep4.ep1
sp1 = load_mod("sp1frames", ROOT / "series/05-diwali/sp01/final/make_frames.py")
svg, over, rich, lama_fill, skin_in, cut = ep3.svg, ep3.over, ep3.rich, ep3.lama_fill, ep3.skin_in, ep4.cut
W, H = 720, 1280


def save(name, img, a):
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(FR / f"{name}.png")
    Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).save(FR / f"{name}_mask.png")
    print("saved", name)


def bare(rgb, a):
    hz = ep1.horizon_of(rgb.astype(np.uint8))
    return rich(rgb, a, hz), hz


def empty_plate():
    rgb = np.array(Image.open(ROOT / "assets/2d/source/05_field_vertical.png").convert("RGB").resize((W, H), Image.LANCZOS)).astype(np.float32)
    out, hz = bare(rgb, np.zeros((H, W), np.float32))
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(FR / "empty_plate.png")
    print("saved empty_plate, horizon", hz)


def magazine(x, y, s=1.0, closed=False):
    """A glossy magazine (or a closed notebook) standing in his palm; (x, y) = bottom centre."""
    if closed:
        return (f'<g transform="translate({x} {y}) rotate(-8) scale({s})"><rect x="-58" y="-150" width="116" height="150" rx="6" fill="#1565c0" stroke="#0a2a5a" stroke-width="5"/>'
                '<rect x="-58" y="-150" width="18" height="150" fill="#0d47a1"/><rect x="-28" y="-120" width="70" height="22" rx="3" fill="#e3f2fd"/>'
                '<path d="M -48,-146 L -48,-4" stroke="#bbdefb" stroke-width="3" stroke-dasharray="6 6"/></g>')
    return (f'<g transform="translate({x} {y}) rotate(-8) scale({s})"><rect x="-62" y="-160" width="124" height="160" rx="4" fill="#fffdf2" stroke="#3a3a3a" stroke-width="5"/>'
            '<rect x="-56" y="-154" width="112" height="26" fill="#e53935"/><rect x="-46" y="-148" width="60" height="6" fill="#ffffff"/><rect x="-46" y="-138" width="40" height="5" fill="#ffd54f"/>'
            '<ellipse cx="-6" cy="-78" rx="36" ry="30" fill="#e91e8c" stroke="#880e4f" stroke-width="4"/>'
            '<path d="M -40,-92 l -14,-10 M -30,-104 l -6,-16 M 26,-96 l 16,-8 M 18,-106 l 8,-14 M -10,-108 l 2,-18 M 30,-74 l 18,0" stroke="#66bb6a" stroke-width="7" stroke-linecap="round"/>'
            + "".join(f'<circle cx="{-18 + 12 * (k % 3)}" cy="{-86 + 12 * (k // 3)}" r="2.5" fill="#111"/>' for k in range(6)) +
            '<rect x="20" y="-46" width="34" height="18" rx="2" fill="#7cb342" stroke="#33691e" stroke-width="3"/><rect x="24" y="-40" width="34" height="18" rx="2" fill="#8bc34a" stroke="#33691e" stroke-width="3"/>'
            '<circle cx="-36" cy="-30" r="14" fill="#ffca28" stroke="#a67c00" stroke-width="3"/>'
            '<path d="M -42,-36 L -30,-36 M -42,-31 L -30,-31 M -40,-36 Q -30,-36 -34,-29 L -38,-22" stroke="#a67c00" stroke-width="2.5" fill="none"/>'
            '<rect x="-46" y="-14" width="70" height="5" fill="#bdbdbd"/></g>')


def palm_frame(seg, prop):
    """The poses sheet's 3rd figure, the pods removed, on the bare field, `prop` (SVG fn of hand x, y, scale) in his palm."""
    sh = np.array(Image.open(ROOT / "assets/2d/source/04_poses.png").convert("RGB")).astype(np.float32)
    hsv = cv2.cvtColor(sh.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(int)
    yy, xx = np.mgrid[0:sh.shape[0], 0:sh.shape[1]]
    pods = (xx > 1200) & (xx < 1295) & (yy > 325) & (yy < 385) & (hsv[..., 0] >= 10) & (hsv[..., 0] <= 34) & (hsv[..., 1] < 165) & (hsv[..., 2] > 150)
    hole = cv2.dilate(cv2.morphologyEx(pods.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)), np.ones((5, 5), np.uint8))
    from simple_lama_inpainting import SimpleLama
    import torch
    _load = torch.jit.load
    torch.jit.load = lambda f, map_location=None, **k: _load(f, map_location="cpu", **k)
    fixed = np.array(SimpleLama()(Image.fromarray(sh.astype(np.uint8)), Image.fromarray(hole * 255)).convert("RGB").resize((sh.shape[1], sh.shape[0]))).astype(np.float32)
    torch.jit.load = _load
    sh = sh * (1 - hole[..., None]) + fixed * hole[..., None]
    from rembg import remove
    x0, x1 = 930, 1400
    crop = sh[:, x0:x1]
    a = np.clip((np.array(remove(Image.fromarray(crop.astype(np.uint8)), session=seg, only_mask=True)).astype(np.float32) - 90) * 2.6, 0, 255)
    ys, xs = np.nonzero(a > 30)
    lay = np.dstack([crop, a])[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    org = (x0 + xs.min(), ys.min())
    plate = np.array(Image.open(FR / "empty_plate.png").convert("RGB")).astype(np.float32)
    height, cx, bottom = 1060, 360, 1250
    sc = height / lay.shape[0]
    lay = np.clip(cv2.resize(lay, (round(lay.shape[1] * sc), height), interpolation=cv2.INTER_CUBIC), 0, 255)
    can = np.zeros((H, W, 4), np.float32)
    px0, py0 = round(cx - lay.shape[1] / 2), bottom - height
    can[py0:py0 + height, max(0, px0):min(W, px0 + lay.shape[1])] = lay[:, max(0, -px0):min(W, px0 + lay.shape[1]) - px0]
    shadow = svg(f'<ellipse cx="{cx}" cy="{bottom - 6}" rx="150" ry="20" fill="#000" fill-opacity="0.3"/>')
    out = over(over(plate, shadow), can)
    hx, hy = px0 + (1248 - org[0]) * sc, py0 + (372 - org[1]) * sc
    p = svg(prop(hx, hy, sc * 2.0))
    rgb0 = out.copy()
    out = over(out, p)
    hsvo = cv2.cvtColor(np.clip(rgb0, 0, 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(int)
    YY, XX = np.mgrid[0:H, 0:W]
    fing = (np.abs(XX - hx) < 60 * sc * 2) & (YY > hy - 4) & (YY < hy + 50 * sc * 2) & (hsvo[..., 0] <= 22) & (hsvo[..., 1] > 80) & (can[..., 3] > 128)
    out[fing] = rgb0[fing]
    return out, np.maximum(can[..., 3] / 255, p[..., 3] / 255 * 0), (hx, hy)


def f_mag(seg):
    out, a, h = palm_frame(seg, lambda x, y, s: magazine(x, y, s * 0.55))
    save("f_mag", out, a)
    print("palm at", h)


def f_note(seg):
    out, a, _ = palm_frame(seg, lambda x, y, s: magazine(x, y, s * 0.55, closed=True))
    save("f_note", out, a)
    from rain import overcast, sky_mask, storm_sky
    img = np.clip(out, 0, 255).astype(np.uint8)
    m = sky_mask(img, 640, protect=(a * 255).astype(np.uint8))[..., None]
    clouds = storm_sky(W, 640, seed=11)[..., :3].astype(np.float32)
    sky = np.zeros((H, W, 3), np.float32)
    sky[:640] = clouds
    grey = overcast(img, 0.9).astype(np.float32)
    st = grey * (1 - m) + overcast(sky.astype(np.uint8), 0.15).astype(np.float32) * m
    save("f_storm", st, a)
    Image.fromarray(st.astype(np.uint8)).save(FR / "storm_still.png")


def f_present(seg):
    rgb = ep4.load("ep02/final/frames/f_hook_s3.png")
    a = cut(seg, rgb)
    yy, xx = np.mgrid[0:H, 0:W]
    hsv = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(int)
    seeds = (xx > 560) & (xx < 680) & (yy > 555) & (yy < 630) & ((hsv[..., 0] >= 160) | (hsv[..., 0] <= 6)) & (hsv[..., 1] > 40) & (hsv[..., 2] > 120)
    hole = cv2.dilate(cv2.morphologyEx(seeds.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8)), np.ones((7, 7), np.uint8))
    rgb = lama_fill(rgb, hole)
    out, hz = bare(rgb, a)
    save("f_present", out, a)


def f_mark(seg):
    rgb = ep4.load("ep02/final/frames/f_hoe_s8.png")
    a = cut(seg, rgb)
    out, hz = bare(rgb, a)
    g = ""
    for k, (x, y, s) in enumerate(((120, 1060, 1.0), (330, 930, 0.7), (520, 860, 0.55), (650, 800, 0.45), (90, 820, 0.5), (240, 760, 0.42))):
        g += (f'<rect x="{x - 5 * s:.0f}" y="{y - 70 * s:.0f}" width="{10 * s:.0f}" height="{74 * s:.0f}" fill="#8a5a2b" stroke="#3e2410" stroke-width="2"/>'
              f'<rect x="{x - 7 * s:.0f}" y="{y - 74 * s:.0f}" width="{14 * s:.0f}" height="{10 * s:.0f}" fill="#e53935"/>')
    g += ('<path d="M 120,1000 L 330,888 L 520,826 L 650,772" stroke="#f5f5f5" stroke-width="2.5" fill="none"/>'
          '<path d="M 90,785 L 240,730" stroke="#f5f5f5" stroke-width="2" fill="none"/>')
    out = over(out, svg(g), keep=a)
    save("f_mark", out, a)


def stool():
    P = sp1.plank
    return (P(232, 1000, 34, 380, sp1.WOOD_D) + P(826, 1000, 34, 380, sp1.WOOD_D) + P(150, 925, 792, 48) +
            P(162, 965, 44, 455) + P(886, 965, 44, 455) + P(185, 1250, 722, 26, sp1.WOOD_D))


def f_stool(seg):
    rgb, a = sp1.sitting_without_seat(seg)
    fig = np.dstack([rgb, a]).astype(np.float32)
    ch = sp1.svg(stool(), 1024, 1536).astype(np.float32)
    yy, xx = np.mgrid[0:1536, 0:1024]
    hand = (xx > 320) & (xx < 450) & (yy > 820) & (yy < 950)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(int)
    skin = hand & (hsv[..., 0] <= 22) & (hsv[..., 1] > 100) & (a > 200)
    fingers = fig.copy()
    fingers[..., 3] = skin * 255
    cash = ('<ellipse cx="385" cy="800" rx="150" ry="120" fill="#fff59d" opacity="0.35"/>'
            + "".join(f'<g transform="rotate({ang} 390 900)" opacity="0.88"><rect x="352" y="740" width="76" height="150" rx="6" fill="#9ccc65" stroke="#33691e" stroke-width="5"/>'
                      f'<circle cx="390" cy="800" r="18" fill="none" stroke="#33691e" stroke-width="4"/><rect x="360" y="752" width="60" height="8" fill="#c5e1a5"/></g>'
                      for ang in (-34, -14, 6, 26))
            + "".join(f'<path d="M {x},{y - 16} L {x + 5},{y} L {x},{y + 16} L {x - 5},{y} Z M {x - 16},{y} L {x},{y + 5} L {x + 16},{y} L {x},{y - 5} Z" fill="#fffde7"/>'
                      for x, y in ((280, 760), (500, 780), (330, 690), (470, 700), (250, 860))))
    sitting = {}
    plate = np.array(Image.open(FR / "empty_plate.png").convert("RGB"))
    for name, extra in (("f_stool", sp1.svg(cash, 1024, 1536).astype(np.float32)), ("f_stool2", None)):
        layer = np.zeros((1536, 1024, 4), np.float32)
        parts = (ch, fig) + ((extra, fingers) if extra is not None else ())
        for part in parts:
            al = part[..., 3:4] / 255
            layer[..., :3] = layer[..., :3] * (1 - al) + part[..., :3] * al
            layer[..., 3:4] = np.maximum(layer[..., 3:4], part[..., 3:4])
        lay = np.clip(layer, 0, 255).astype(np.uint8)
        sitting[name] = lay
        shadow = sp1.svg('<ellipse cx="360" cy="1238" rx="210" ry="22" fill="#000" fill-opacity="0.3"/>', W, H)
        pl = over(plate.astype(np.float32), shadow.astype(np.float32)).astype(np.uint8)
        out, mask, off = sp1.place(pl, lay, 0.62, 360, 1245, 1430)
        save(name, out, mask / 255)
    sit = np.dstack([rgb, a])
    Image.fromarray(sit).save(FR / "sit_rgba.png")


def f_moral(seg):
    rgb = ep4.load("ep01/final/frames/f5_cliff_s3.png")
    a = cut(seg, rgb)
    out, hz = bare(rgb, a)
    save("f_moral", out, a)


def f_think():
    shutil.copy(ROOT / "series/03-thatha-days/day01/final/frames/f_slist.png", FR / "f_think.png")
    print("saved f_think")


def main():
    only = sys.argv[1:]
    if not only or "empty_plate" in only:
        empty_plate()
    seg = new_session("isnet-anime")
    for name, fn in (("f_mag", f_mag), ("f_note", f_note), ("f_present", f_present), ("f_mark", f_mark), ("f_stool", f_stool), ("f_moral", f_moral)):
        if not only or name in only:
            fn(seg)
    if not only or "f_think" in only:
        f_think()


if __name__ == "__main__":
    main()
