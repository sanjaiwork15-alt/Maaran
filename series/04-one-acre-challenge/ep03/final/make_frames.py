"""One-Acre Challenge Ep 3 – start frames without a GPU. After Ep 2's compost the field is alive again: the approved
Groundnut field frames are used WHOLE with the soil darkened to a rich, moist brown (no cracks) and rows of young
brinjal plants drawn in code (tools/toon/bugs.py) – a new crop, so the groundnut plants don't repeat.

Run with the f5 env:  python -I make_frames.py [names...]
f_inspect:  Groundnut Ep 2 f_kneel_s3 – kneeling, his fingers holding a young brinjal leaf (the seed in his hand removed)
f_inspect2: the same, his hand sprayer lying on the ground beside him (he has put it away)
f_point:    Groundnut Ep 2 f_hook2_s3 – pointing down at a plant: a ladybird on its leaf ("villain!")
f_spray:    Groundnut Ep 8 f_pod_s3 – the groundnut pod in his raised fist becomes a hand pump sprayer (warrior pose)
f_moral:    Groundnut Ep 1 f5_cliff_s3 – standing, open palm held out, explaining to the camera (the moral)
f_huh:      Groundnut Ep 2 f_hook_s3 – glancing sideways, palm raised (the seeds in it removed): "why is it a pond?!"
f_water:    Groundnut Ep 4 f_water_s8 – kneeling with the watering can, finger up; the sprout is a young brinjal
f_bend:     the owner's poses sheet (04_poses, 2nd) – bending low, a brinjal leaf with the ladybird lying in his cupped hand
            (the soil in it removed): examining the leaves
f_cross:    the owner's poses sheet (4th) – arms crossed, thoughtful (the moral)
grown_plate.png: the owner's empty field (05_field_vertical) with rich soil and plant rows (library actions, waterlog)
*_mask.png: Thatha's silhouette.
"""
import importlib.util
import io
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
GN = ROOT / "series/01-groundnut"
sys.path.insert(0, str(ROOT / "tools/toon"))
from bugs import brinjal, field_plants, ladybird, sprayer  # noqa: E402

spec = importlib.util.spec_from_file_location("ep1frames", HERE.parents[1] / "ep01/final/make_frames.py")
ep1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ep1)
W, H = 720, 1280

SRC = {"f_inspect": "ep02/final/frames/f_kneel_s3.png", "f_point": "ep02/final/frames/f_hook2_s3.png",
       "f_spray": "ep08/final/frames/f_pod_s3.png", "f_moral": "ep01/final/frames/f5_cliff_s3.png", "f_huh": "ep02/final/frames/f_hook_s3.png",
       "f_water": "ep04/final/frames/f_water_s8.png"}


def svg(body):
    return np.array(Image.open(io.BytesIO(cairosvg.svg2png(
        bytestring=f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">{body}</svg>'.encode()))).convert("RGBA")).astype(np.float32)


def over(rgb, rgba, keep=None):
    a = rgba[..., 3:4] / 255
    if keep is not None:
        a = a * (1 - keep[..., None])
    return rgb * (1 - a) + rgba[..., :3] * a


def rich(rgb, protect, horizon):
    """Red tilled soil -> darker, moist, compost-rich brown; everything else untouched. protect: 0..1 (Thatha)."""
    x = rgb.astype(np.float32)
    hsv = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
    yy = np.arange(H, dtype=np.float32)[:, None] * np.ones((1, W), np.float32)
    below = np.clip((yy - horizon) / 30.0, 0, 1)
    soil = (((hsv[..., 0] <= 22) | (hsv[..., 0] >= 170)) & (hsv[..., 1] > 60)).astype(np.float32) * below
    soil = cv2.GaussianBlur(soil, (0, 0), 1.2) * (1 - protect)
    dark = x * np.array([0.66, 0.6, 0.58]) + np.array([10, 6, 4])
    return x * (1 - soil[..., None]) + dark * soil[..., None]


def lama_fill(rgb, hole):
    from simple_lama_inpainting import SimpleLama
    import torch
    _load = torch.jit.load
    torch.jit.load = lambda f, map_location=None, **k: _load(f, map_location="cpu", **k)
    out = np.array(SimpleLama()(Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)), Image.fromarray(hole.astype(np.uint8) * 255))
                   .convert("RGB").resize((W, H))).astype(np.float32)
    torch.jit.load = _load
    return rgb * (1 - hole[..., None]) + out * hole[..., None]


def skin_in(rgb, a, box):
    x0, y0, x1, y1 = box
    hsv = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(int)
    yy, xx = np.mgrid[0:H, 0:W]
    return (xx > x0) & (xx < x1) & (yy > y0) & (yy < y1) & (hsv[..., 0] <= 22) & (hsv[..., 1] > 70) & (hsv[..., 2] > 90) & (a > 0.5)


def base(seg, name, seed=1, rows=7, density=1.0):
    rgb = np.array(Image.open(GN / SRC[name]).convert("RGB").resize((W, H), Image.LANCZOS)).astype(np.float32)
    a = np.clip((np.array(remove(Image.fromarray(rgb.astype(np.uint8)), session=seg, only_mask=True)).astype(np.float32) - 90) * 2.6, 0, 255) / 255
    a = cv2.GaussianBlur(cv2.dilate(a, np.ones((5, 5), np.uint8)), (0, 0), 1.2)
    hz = ep1.horizon_of(rgb.astype(np.uint8))
    out = rich(rgb, a, hz)
    out = over(out, svg(field_plants(hz, seed=seed, rows=rows, density=density)), keep=a)      # plants behind him
    return rgb, out, a, hz


def save(name, img, a):
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(FR / f"{name}.png")
    Image.fromarray((a * 255).astype(np.uint8)).save(FR / f"{name}_mask.png")
    print("saved", name)


def f_inspect(seg):
    rgb, out, a, hz = base(seg, "f_inspect", 3)
    yy, xx = np.mgrid[0:H, 0:W]
    hsv = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(int)
    seedm = (xx > 100) & (xx < 140) & (yy > 836) & (yy < 900) & (((hsv[..., 0] >= 160) | (hsv[..., 0] <= 5)) & (hsv[..., 1] > 40) & (hsv[..., 2] > 150))
    hole = cv2.dilate(cv2.morphologyEx(seedm.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)), np.ones((7, 7), np.uint8))
    out = lama_fill(out, hole)
    fing = skin_in(rgb, a, (80, 790, 160, 900)) & (hole == 0)
    plant = svg(brinjal(112, 1000, 0.62, 7, -4))
    out = over(out, plant)
    out[fing] = rich(rgb, a, hz)[fing]
    save("f_inspect", out, a)
    spr = svg(f'<g transform="translate(250 1060) rotate(-78)">{sprayer(0, 0, 0.55)}</g>')
    save("f_inspect2", over(out, spr), a)


def f_point(seg):
    rgb, out, a, hz = base(seg, "f_point", 4)
    g = brinjal(455, 1330, 0.9, 11, 3) + ladybird(500, 1135, 0.55, -70)
    out = over(out, svg(g))
    fing = skin_in(rgb, a, (480, 1040, 580, 1110))
    out[fing] = rich(rgb, a, hz)[fing]
    save("f_point", out, a)


def f_spray(seg):
    rgb, out, a, hz = base(seg, "f_spray", 5)
    yy, xx = np.mgrid[0:H, 0:W]
    hsv = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(int)
    pod = (xx > 525) & (xx < 615) & (yy > 80) & (yy < 265) & (hsv[..., 0] >= 10) & (hsv[..., 0] <= 30) & (hsv[..., 1] < 150) & (hsv[..., 2] > 150)
    pod = cv2.morphologyEx(pod.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((13, 13), np.uint8))
    fing = skin_in(rgb, a, (598, 196, 660, 300)) & (pod == 0)
    box = ((xx > 524) & (xx < 618) & (yy > 76) & (yy < 268)).astype(np.uint8)
    hole = (cv2.dilate(pod, np.ones((9, 9), np.uint8)) | box) & (~fing).astype(np.uint8)
    out = lama_fill(out, hole)
    a2 = a.copy()
    a2[hole > 0] = 0
    out = over(out, svg(sprayer(580, 300, 1.0, 4)))
    out[fing] = rich(rgb, a, hz)[fing]
    spr_a = svg(sprayer(580, 300, 1.0, 4))[..., 3] / 255
    save("f_spray", out, np.maximum(a2, spr_a))


def f_moral(seg):
    rgb, out, a, hz = base(seg, "f_moral", 6)
    save("f_moral", out, a)


def f_huh(seg):
    rgb, out, a, hz = base(seg, "f_huh", 12)
    yy, xx = np.mgrid[0:H, 0:W]
    hsv = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(int)
    seeds = (xx > 560) & (xx < 680) & (yy > 555) & (yy < 630) & ((hsv[..., 0] >= 160) | (hsv[..., 0] <= 6)) & (hsv[..., 1] > 40) & (hsv[..., 2] > 120)
    hole = cv2.dilate(cv2.morphologyEx(seeds.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8)), np.ones((7, 7), np.uint8))
    out = lama_fill(out, hole)
    save("f_huh", out, a)


def f_water(seg):
    rgb, out, a, hz = base(seg, "f_water", 8)
    yy, xx = np.mgrid[0:H, 0:W]
    hsv = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(int)
    sprout = (xx > 40) & (xx < 170) & (yy > 975) & (yy < 1045) & (hsv[..., 0] >= 30) & (hsv[..., 0] <= 90) & (hsv[..., 1] > 50)
    hole = cv2.dilate(sprout.astype(np.uint8), np.ones((9, 9), np.uint8))
    out = lama_fill(out, hole)
    out = over(out, svg(brinjal(100, 1050, 0.36, 9)))
    save("f_water", out, a)


def sheet_figure(seg, x0, x1, clean=None):
    """One figure from the owner's poses sheet (1774x887, white background) as RGBA; clean = (x0, y0, x1, y1) in sheet
    coords inpainted first (a prop to remove)."""
    sh = np.array(Image.open(ROOT / "assets/2d/source/04_poses.png").convert("RGB")).astype(np.float32)
    if clean:
        cx0, cy0, cx1, cy1 = clean
        hsv = cv2.cvtColor(sh.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(int)
        yy, xx = np.mgrid[0:sh.shape[0], 0:sh.shape[1]]
        soil = (xx > cx0) & (xx < cx1) & (yy > cy0) & (yy < cy1) & (hsv[..., 2] < 170) & ((hsv[..., 0] <= 12) | (hsv[..., 0] >= 165)) & (hsv[..., 1] > 80)
        hole = cv2.dilate(soil.astype(np.uint8), np.ones((7, 7), np.uint8))
        from simple_lama_inpainting import SimpleLama
        import torch
        _load = torch.jit.load
        torch.jit.load = lambda f, map_location=None, **k: _load(f, map_location="cpu", **k)
        fixed = np.array(SimpleLama()(Image.fromarray(sh.astype(np.uint8)), Image.fromarray(hole * 255)).convert("RGB")
                         .resize((sh.shape[1], sh.shape[0]))).astype(np.float32)
        torch.jit.load = _load
        sh = sh * (1 - hole[..., None]) + fixed * hole[..., None]
    crop = sh[:, x0:x1]
    a = np.clip((np.array(remove(Image.fromarray(crop.astype(np.uint8)), session=seg, only_mask=True)).astype(np.float32) - 90) * 2.6, 0, 255)
    ys, xs = np.nonzero(a > 30)
    return np.dstack([crop, a])[ys.min():ys.max() + 1, xs.min():xs.max() + 1], (x0 + xs.min(), ys.min())


def on_field(lay, height, cx, bottom):
    plate = np.array(Image.open(FR / "grown_plate.png").convert("RGB")).astype(np.float32)
    sc = height / lay.shape[0]
    lay = cv2.resize(lay, (round(lay.shape[1] * sc), round(height)), interpolation=cv2.INTER_CUBIC)
    can = np.zeros((H, W, 4), np.float32)
    x0, y0 = round(cx - lay.shape[1] / 2), round(bottom - height)
    xs, xe = max(0, x0), min(W, x0 + lay.shape[1])
    can[y0:y0 + lay.shape[0], xs:xe] = lay[:, xs - x0:xe - x0]
    sh = svg(f'<ellipse cx="{cx}" cy="{bottom - 6}" rx="{lay.shape[1] * 0.42:.0f}" ry="20" fill="#000" fill-opacity="0.3"/>')
    out = over(over(plate, sh), can)
    return out, can[..., 3] / 255, sc, (x0, y0)


def f_bend(seg):
    lay, org = sheet_figure(seg, 494, 912, clean=(838, 524, 902, 580))
    out, a, sc, (x0, y0) = on_field(lay, 1000, 380, 1240)
    hx, hy = x0 + (865 - org[0]) * sc, y0 + (500 - org[1]) * sc            # his cupped hand
    rgb = out.copy()
    from bugs import leaf
    out = over(out, svg(leaf(hx + 62, hy - 2, 192, 0.62, "#4f9a35") + leaf(hx - 58, hy - 14, -12, 0.6, "#5aa83c")
                        + ladybird(hx - 4, hy - 22, 0.3, -60)))
    hsv = cv2.cvtColor(np.clip(rgb, 0, 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(int)
    yy, xx = np.mgrid[0:H, 0:W]
    fing = (np.hypot(xx - hx, yy - hy) < 70) & (xx > hx + 18) & (hsv[..., 0] <= 22) & (hsv[..., 1] > 70) & (a > 0.5)
    save("f_bend", out, a)
    print("hand at", round(hx), round(hy))


def f_cross(seg):
    lay, org = sheet_figure(seg, 1420, 1774)
    out, a, sc, _ = on_field(lay, 1040, 360, 1245)
    save("f_cross", out, a)


def grown_plate():
    rgb = np.array(Image.open(ROOT / "assets/2d/source/05_field_vertical.png").convert("RGB").resize((W, H), Image.LANCZOS)).astype(np.float32)
    hz = ep1.horizon_of(rgb.astype(np.uint8))
    out = rich(rgb, np.zeros((H, W), np.float32), hz)
    out = over(out, svg(field_plants(hz, seed=9, rows=8)))
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(FR / "grown_plate.png")
    print("saved grown_plate, horizon", hz)


def main():
    only = sys.argv[1:]
    seg = new_session("isnet-anime")
    for name, fn in (("f_inspect", f_inspect), ("f_point", f_point), ("f_spray", f_spray), ("f_moral", f_moral), ("f_huh", f_huh), ("f_water", f_water)):
        if not only or name in only:
            fn(seg)
    if not only or "grown_plate" in only:
        grown_plate()
    for name, fn in (("f_bend", f_bend), ("f_cross", f_cross)):
        if not only or name in only:
            fn(seg)


if __name__ == "__main__":
    main()
