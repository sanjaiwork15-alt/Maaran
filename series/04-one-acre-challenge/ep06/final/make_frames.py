"""One-Acre Challenge Ep 6 – start frames without a GPU: the brinjal field of Eps 3–4 on the storm day.
Approved frames from Eps 3/5 used whole, re-lit in code: "storm" (storm-cloud sky, grey light, wet dark soil; rain is
added live by talk.py's "rain" option) and "after" (lighter grey sky, wet soil, puddles in the low ground).

Run with the f5 env:  python -I make_frames.py [names...]
storm_plate / after_plate: Ep 3's grown_plate (empty field) re-lit
f_sky:    Ep 3 f_huh (glancing sideways, palm up) under the storm sky – nervous
f_leaf:   Ep 3's raised-fist pose (Groundnut Ep 8 f_pod_s3) holding a big banana leaf over his head as an umbrella
f_hay:    the owner's sitting drawing (09_sitting, brick seat removed) plonked on a haystack in the rain, straw on him
f_hmm:    Ep 3 f_point (pointing down at a plant), after the rain, puddles
f_note:   Ep 5's palm pose (04_poses) with his closed notebook, after the rain
f_lift:   Ep 3 f_inspect (kneeling, holding a young brinjal plant up by its leaf), after the rain
f_cross:  Ep 3 f_cross (arms crossed, determined), after the rain
f_seed:   Ep 5's palm pose with a nearly empty jute seed pouch in his palm, after the rain
"""
import importlib.util
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import new_session

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FR = HERE / "frames"
EP3 = HERE.parents[1] / "ep03/final/frames"
sys.path.insert(0, str(ROOT / "tools/toon"))
from rain import overcast, sky_mask, storm_sky, wet  # noqa: E402
from storm import banana_leaf, pouch  # noqa: E402


def load_mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ep5 = load_mod("ep5frames", HERE.parents[1] / "ep05/final/make_frames.py")
ep4, ep3, ep1, sp1 = ep5.ep4, ep5.ep3, ep5.ep1, ep5.sp1
svg, over, lama_fill, skin_in, cut = ep3.svg, ep3.over, ep3.lama_fill, ep3.skin_in, ep4.cut
W, H = 720, 1280
HZ = 583


def relight(img, a, kind, hz=None, puddles=None, seed=11):
    """kind "storm" or "after"; a = Thatha's alpha 0..1 (kept out of sky/soil changes)."""
    img = np.clip(img, 0, 255).astype(np.uint8)
    hz = hz or HZ
    prot = (a * 255).astype(np.uint8)
    m = sky_mask(img, hz + 20, protect=prot)[..., None]
    clouds = storm_sky(W, hz + 40, seed=seed)[..., :3].astype(np.float32)
    sky = np.zeros((H, W, 3), np.float32)
    sky[:hz + 40] = clouds
    sky[hz + 40:] = clouds[-1:]
    amt = 1.0 if kind == "storm" else 0.55
    if kind == "after":
        sky = sky * 0.55 + np.array([200, 206, 212]) * 0.45
    grey = overcast(img, amt).astype(np.float32)
    out = grey * (1 - m) + overcast(np.clip(sky, 0, 255).astype(np.uint8), 0.1).astype(np.float32) * m
    out = wet(np.clip(out, 0, 255).astype(np.uint8), 1.0, protect=prot, ytop=hz + 10).astype(np.float32)
    if puddles:
        out = ep4.water_on(out, ep4.blobs(puddles) * (1 - a), hz, mix=0.3)
    return out


def save(name, img, a):
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(FR / f"{name}.png")
    Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).save(FR / f"{name}_mask.png")
    print("saved", name)


def ep3_frame(name):
    img = np.array(Image.open(EP3 / f"{name}.png").convert("RGB")).astype(np.float32)
    a = np.array(Image.open(EP3 / f"{name}_mask.png").convert("L")).astype(np.float32) / 255
    return img, a


PUD = [(560, 1160, 190, 50), (130, 1210, 150, 40), (640, 1040, 120, 28)]


def plates():
    g = np.array(Image.open(EP3 / "grown_plate.png").convert("RGB")).astype(np.float32)
    z = np.zeros((H, W), np.float32)
    Image.fromarray(np.clip(relight(g, z, "storm"), 0, 255).astype(np.uint8)).save(FR / "storm_plate.png")
    after = relight(g, z, "after", puddles=[(520, 1130, 260, 70), (180, 1220, 200, 50), (620, 1000, 160, 34)])
    Image.fromarray(np.clip(after, 0, 255).astype(np.uint8)).save(FR / "after_plate.png")
    Image.fromarray(np.clip(after, 0, 255).astype(np.uint8)).save(FR / "empty_plate.png")       # for ep5.palm_frame
    print("saved plates")


def f_sky(seg):
    img, a = ep3_frame("f_huh")
    save("f_sky", relight(img, a, "storm"), a)


def f_leaf(seg):
    rgb = ep4.load("ep08/final/frames/f_pod_s3.png")
    a = cut(seg, rgb)
    yy, xx = np.mgrid[0:H, 0:W]
    hsv = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(int)
    pod = (xx > 525) & (xx < 615) & (yy > 80) & (yy < 265) & (hsv[..., 0] >= 10) & (hsv[..., 0] <= 30) & (hsv[..., 1] < 150) & (hsv[..., 2] > 150)
    pod = cv2.morphologyEx(pod.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((13, 13), np.uint8))
    fing = skin_in(rgb, a, (598, 196, 660, 300)) & (pod == 0)
    box = ((xx > 524) & (xx < 618) & (yy > 76) & (yy < 268)).astype(np.uint8)
    hole = (cv2.dilate(pod, np.ones((9, 9), np.uint8)) | box) & (~fing).astype(np.uint8)
    clean = lama_fill(rgb, hole)
    a2 = a.copy()
    a2[hole > 0] = 0
    out, hz = ep4.field(clean, a2, 41)
    out = relight(out, a2, "storm")
    sp = np.array(Image.open(FR / "storm_plate.png").convert("RGB")).astype(np.float32)
    h2 = (cv2.dilate(hole, np.ones((15, 15), np.uint8)) > 0) & ~fing & (a2 < 0.5) & (yy < 300)
    out[h2] = sp[h2]
    lf = svg(banana_leaf(604, 222, 1.05, -150))
    lf[..., :3] *= np.array([0.7, 0.72, 0.78])
    lit = relight(rgb, a, "storm")
    out = over(out, lf)
    out[fing] = lit[fing]
    save("f_leaf", out, np.maximum(a2, lf[..., 3] / 255))


def haystack():
    rng = np.random.default_rng(4)
    g = ['<path d="M 0,1440 C -10,900 160,600 512,580 C 864,600 1034,900 1024,1440 Z" fill="#d6b04a" stroke="#7a5a10" stroke-width="10"/>',
         '<path d="M 60,1300 C 110,900 280,660 512,640" stroke="#f0d070" stroke-width="30" fill="none" opacity="0.6"/>',
         '<path d="M 512,560 l -10,-60 M 520,560 l 18,-56 M 505,562 l -36,-40" stroke="#a07a1a" stroke-width="8"/>']
    for _ in range(520):
        x, y = rng.uniform(30, 1000), rng.uniform(620, 1430)
        ang = rng.uniform(-40, 40)
        L = rng.uniform(30, 80)
        g.append(f'<path d="M {x:.0f},{y:.0f} l {L * np.sin(np.radians(ang)):.0f},{-L * np.cos(np.radians(ang)):.0f}" stroke="{rng.choice(["#a07a1a", "#e8c860", "#c09a30"])}" stroke-width="5"/>')
    return "".join(g)


def f_hay(seg):
    rgb, a = sp1.sitting_without_seat(seg)
    fig = np.dstack([rgb, a]).astype(np.float32)
    fig[..., :3] = fig[..., :3] * np.array([0.78, 0.8, 0.86])
    hay = sp1.svg(haystack(), 1024, 1536).astype(np.float32)
    hay[..., :3] *= np.array([0.78, 0.8, 0.86])
    rng = np.random.default_rng(9)
    bits = "".join(f'<path d="M {x:.0f},{y:.0f} l {rng.uniform(-30, 30):.0f},{rng.uniform(-24, 24):.0f}" stroke="#d6b04a" stroke-width="6" stroke-linecap="round"/>'
                   for x, y in [(rng.uniform(380, 640), rng.uniform(150, 260)) for _ in range(9)] + [(rng.uniform(250, 800), rng.uniform(600, 900)) for _ in range(12)])
    straw = sp1.svg(bits, 1024, 1536).astype(np.float32)
    layer = np.zeros((1536, 1024, 4), np.float32)
    for part in (hay, fig, straw):
        al = part[..., 3:4] / 255
        layer[..., :3] = layer[..., :3] * (1 - al) + part[..., :3] * al
        layer[..., 3:4] = np.maximum(layer[..., 3:4], part[..., 3:4])
    plate = np.array(Image.open(FR / "storm_plate.png").convert("RGB"))
    out, mask, off = sp1.place(plate, np.clip(layer, 0, 255).astype(np.uint8), 0.62, 360, 1250, 1440)
    save("f_hay", out, mask / 255)


def after_frame(name, out_name, seed):
    img, a = ep3_frame(name)
    save(out_name, relight(img, a, "after", puddles=PUD, seed=seed), a)


def dim(out, a):
    """Grey after-rain light on a figure composited onto the (already re-lit) plate."""
    g = overcast(np.clip(out, 0, 255).astype(np.uint8), 0.55).astype(np.float32)
    m = cv2.dilate(a.astype(np.float32), np.ones((25, 25), np.uint8))[..., None]
    return out * (1 - m) + g * m


def f_note(seg):
    ep5.FR = FR
    out, a, _ = ep5.palm_frame(seg, lambda x, y, s: ep5.magazine(x, y, s * 0.55, closed=True))
    save("f_note", dim(out, a), a)


def f_seed(seg):
    ep5.FR = FR
    out, a, h = ep5.palm_frame(seg, lambda x, y, s: pouch(x + 4, y - 16, s * 0.2, -6, 2))
    save("f_seed", dim(out, a), a)


def main():
    only = sys.argv[1:]
    if not only or "plates" in only:
        plates()
    seg = new_session("isnet-anime")
    for name, fn in (("f_sky", f_sky), ("f_leaf", f_leaf), ("f_hay", f_hay), ("f_note", f_note), ("f_seed", f_seed)):
        if not only or name in only:
            fn(seg)
    for src, name, seed in (("f_point", "f_hmm", 12), ("f_inspect", "f_lift", 13), ("f_cross", "f_cross", 14)):
        if not only or name in only:
            after_frame(src, name, seed)


if __name__ == "__main__":
    main()
