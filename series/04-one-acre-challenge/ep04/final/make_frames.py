"""One-Acre Challenge Ep 4 – start frames without a GPU: the same brinjal field as Ep 3 (rich soil + young brinjal rows
from tools/toon/bugs.py, Ep 3's helpers), now first dry, then flooded by Thatha's hose.

Run with the f5 env:  python -I make_frames.py [names...]
f_dry:    Groundnut Ep 4 f_water_s8 – kneeling with the watering can, finger up; the soil dry and pale (Ep 1's dry grade)
f_hose:   Groundnut Ep 8 f_pod_s3 – the pod in his raised fist becomes a hose nozzle, the green hose hangs to the ground
f_proud:  Groundnut Ep 2 f_humour2_s3 – hand on his belly, beaming; the field behind him under a sheet of water
f_stuck:  the owner's poses sheet (1st, pointing down) – standing ankle-deep in mud, pointing at his stuck foot
f_clod:   Groundnut Ep 2 f_cliff_s3 – the seed in his fingers becomes a dripping lump of mud ("ivlo thanni thevaiyaa?")
f_soilw:  Groundnut Ep 2 f_soil_s3 – crouching, wet soil in his hands (checking the moisture)
f_moral:  Groundnut Ep 9 f_hook2_s3 – facing the camera, pointing down at the flooded field behind him
f_urea:   Groundnut Ep 1 f2b_s5 – the pod he holds up becomes a small fertiliser packet (cliffhanger)
wet_plate.png: the empty field: a flooded section on the left, moist soil on the right (library actions)
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
GN = ROOT / "series/01-groundnut"
sys.path.insert(0, str(ROOT / "tools/toon"))
from bugs import brinjal, field_plants  # noqa: E402


def load_mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ep3 = load_mod("ep3frames", HERE.parents[1] / "ep03/final/make_frames.py")
ep1 = ep3.ep1
svg, over, rich, lama_fill, skin_in = ep3.svg, ep3.over, ep3.rich, ep3.lama_fill, ep3.skin_in
W, H = 720, 1280


def water_on(img, mask, hz, mix=0.38):
    """Standing water mirroring the scene above the horizon (720x1280)."""
    rows = np.arange(H)
    src = np.clip(2 * hz - rows, 0, hz - 1)
    shift = (3 * np.sin(rows * 0.09)).astype(np.int32)
    cols = (np.arange(W)[None, :] + shift[:, None]) % W
    refl = img[src[:, None], cols] * (1 - mix) + np.array([120, 105, 85]) * mix
    return img * (1 - mask[..., None]) + refl * mask[..., None]


def blobs(spec, soft=9):
    m = np.zeros((H, W), np.float32)
    for cx, cy, rx, ry in spec:
        cv2.ellipse(m, (int(cx), int(cy)), (int(rx), int(ry)), 0, 0, 360, 1, -1)
    return cv2.GaussianBlur(m, (0, 0), soft)


def load(rel):
    return np.array(Image.open(GN / rel).convert("RGB").resize((W, H), Image.LANCZOS)).astype(np.float32)


def cut(seg, rgb):
    from rembg import remove
    a = np.clip((np.array(remove(Image.fromarray(rgb.astype(np.uint8)), session=seg, only_mask=True)).astype(np.float32) - 90) * 2.6, 0, 255) / 255
    return cv2.GaussianBlur(cv2.dilate(a, np.ones((5, 5), np.uint8)), (0, 0), 1.2)


def field(rgb, a, seed, wet=None, hz=None):
    hz = hz or ep1.horizon_of(rgb.astype(np.uint8))
    out = rich(rgb, a, hz)
    out = over(out, svg(field_plants(hz, seed=seed)), keep=a)
    if wet:
        out = water_on(out, blobs(wet) * (1 - a), hz)
    return out, hz


def save(name, img, a):
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(FR / f"{name}.png")
    Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).save(FR / f"{name}_mask.png")
    print("saved", name)


def f_dry(seg):
    rgb = load("ep04/final/frames/f_water_s8.png")
    a = cut(seg, rgb)
    yy, xx = np.mgrid[0:H, 0:W]
    hsv = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(int)
    sprout = (xx > 40) & (xx < 170) & (yy > 975) & (yy < 1045) & (hsv[..., 0] >= 30) & (hsv[..., 0] <= 90) & (hsv[..., 1] > 50)
    rgb = lama_fill(rgb, cv2.dilate(sprout.astype(np.uint8), np.ones((9, 9), np.uint8)))
    hz = ep1.horizon_of(rgb.astype(np.uint8))
    out = ep1.dry(rgb.astype(np.uint8), a, hz).astype(np.float32)
    pale = field_plants(hz, seed=21).replace("#4f9a35", "#8fa848").replace("#5aa83c", "#9aaa4a").replace("#468c2f", "#86a044")
    out = over(out, svg(pale), keep=a)
    out = over(out, svg(brinjal(100, 1050, 0.36, 9, 8).replace("#4f9a35", "#8fa848").replace("#5aa83c", "#9aaa4a").replace("#468c2f", "#86a044")))
    save("f_dry", out, a)


def f_hose(seg):
    rgb = load("ep08/final/frames/f_pod_s3.png")
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
    out, hz = field(clean, a2, 31)
    hose = ('<path d="M 600,300 C 660,420 700,600 690,800 C 680,1000 610,1150 560,1290" stroke="#14451c" stroke-width="30" fill="none" stroke-linecap="round"/>'
            '<path d="M 600,300 C 660,420 700,600 690,800 C 680,1000 610,1150 560,1290" stroke="#2e8b3a" stroke-width="21" fill="none" stroke-linecap="round"/>')
    out = over(out, svg(hose), keep=a2)
    nozzle = ('<g transform="rotate(-25 590 230)"><rect x="570" y="150" width="40" height="120" rx="10" fill="#c9a227" stroke="#5a4510" stroke-width="5"/>'
              '<rect x="560" y="120" width="60" height="40" rx="8" fill="#b08a1a" stroke="#5a4510" stroke-width="5"/>'
              '<circle cx="590" cy="122" r="10" fill="#3a2a08"/><rect x="566" y="262" width="48" height="26" rx="6" fill="#2e8b3a" stroke="#14451c" stroke-width="5"/></g>')
    out = over(out, svg(nozzle))
    out[fing] = rich(rgb, a, hz)[fing]
    save("f_hose", out, np.maximum(a2, svg(nozzle)[..., 3] / 255))


def f_proud(seg):
    rgb = load("ep02/final/frames/f_humour2_s3.png")
    a = cut(seg, rgb)
    out, hz = field(rgb, a, 32, wet=[(160, 1150, 230, 70), (560, 1110, 260, 60), (90, 1000, 160, 40), (640, 980, 140, 34)])
    save("f_proud", out, a)


def f_stuck(seg):
    lay, org = ep3.sheet_figure(seg, 0, 470)
    out, a, sc, (x0, y0) = ep3.on_field(lay, 1060, 360, 1255)
    hz = 583
    out = water_on(out, blobs([(160, 1150, 260, 60), (600, 1140, 200, 50)]) * (1 - a), hz)
    rng = np.random.default_rng(3)
    mud = ('<defs><radialGradient id="md" cx="0.5" cy="0.35" r="0.7"><stop offset="0" stop-color="#6b4728"/><stop offset="1" stop-color="#4a2e18"/></radialGradient></defs>'
           '<path d="M -20,1290 L -20,1176 C 60,1160 150,1150 250,1156 C 330,1144 420,1146 500,1152 C 590,1156 680,1166 740,1176 L 740,1290 Z" fill="url(#md)"/>'
           '<path d="M -20,1176 C 60,1160 150,1150 250,1156 C 330,1144 420,1146 500,1152 C 590,1156 680,1166 740,1176" stroke="#2e1c0e" stroke-width="5" fill="none" opacity="0.8"/>'
           + "".join(f'<ellipse cx="{rng.uniform(40, 680):.0f}" cy="{rng.uniform(1170, 1270):.0f}" rx="{rng.uniform(14, 40):.0f}" ry="{rng.uniform(3, 7):.0f}" fill="#c9d8e6" opacity="0.35"/>' for _ in range(9))
           + '<path d="M 230,1158 q 20,-14 44,-4 M 420,1150 q 22,-12 40,2" stroke="#7a5534" stroke-width="6" fill="none"/>'
           + "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#4a3018"/>' for x, y, r in ((250, 1120, 6), (420, 1100, 5), (300, 1080, 4), (470, 1130, 5))))
    m = svg(mud)
    out = over(out, m)
    save("f_stuck", out, a * (1 - m[..., 3] / 255))


def f_clod(seg):
    rgb = load("ep02/final/frames/f_cliff_s3.png")
    a = cut(seg, rgb)
    yy, xx = np.mgrid[0:H, 0:W]
    hsv = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(int)
    seed = (xx > 525) & (xx < 595) & (yy > 385) & (yy < 480) & ((hsv[..., 0] >= 160) | (hsv[..., 0] <= 6)) & (hsv[..., 1] > 40) & (hsv[..., 2] > 140)
    seed = cv2.morphologyEx(seed.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    fing = skin_in(rgb, a, (520, 400, 660, 560)) & (cv2.dilate(seed, np.ones((5, 5), np.uint8)) == 0)
    out, hz = field(rgb, a, 33, wet=[(200, 1180, 260, 70)])
    clod = ('<path d="M 524,452 C 512,430 520,404 534,398 C 538,380 560,372 572,382 C 590,376 606,392 602,412 C 614,428 606,452 598,462 '
            'C 596,482 574,494 556,488 C 538,494 524,476 524,452 Z" fill="#6b4428" stroke="#2a1608" stroke-width="4"/>'
            '<circle cx="546" cy="430" r="7" fill="#4a2e18"/><circle cx="578" cy="452" r="6" fill="#4a2e18"/><circle cx="566" cy="410" r="5" fill="#8a5a34"/>'
            '<ellipse cx="552" cy="404" rx="11" ry="5" fill="#d6e4ef" opacity="0.6"/><ellipse cx="588" cy="430" rx="6" ry="3" fill="#d6e4ef" opacity="0.5"/>'
            '<path d="M 548,486 q -5,24 2,36 q 7,-12 -2,-36 Z" fill="#6b4428"/><circle cx="551" cy="532" r="5" fill="#6b4428"/>'
            '<path d="M 580,484 q 2,14 0,24" stroke="#6b4428" stroke-width="7" stroke-linecap="round"/>')
    out = over(out, svg(clod))
    out[fing] = rich(rgb, a, hz)[fing]
    save("f_clod", out, a)


def f_soilw(seg):
    rgb = load("ep02/final/frames/f_soil_s3.png")
    a = cut(seg, rgb)
    out, hz = field(rgb, a, 34, wet=[(560, 1150, 200, 60)])
    src = rgb[590:800, 215:395]
    hsv = cv2.cvtColor(src.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(int)
    soilm = ((hsv[..., 0] <= 14) | (hsv[..., 0] >= 170)) & (hsv[..., 1] > 120) & (hsv[..., 2] < 200)
    m = cv2.GaussianBlur(soilm.astype(np.float32), (0, 0), 1.0)[..., None]
    reg = out[590:800, 215:395]
    v = reg.mean(axis=2, keepdims=True) / 255
    wet = np.concatenate([50 + 60 * v, 30 + 40 * v, 18 + 24 * v], -1)
    out[590:800, 215:395] = reg * (1 - m) + wet * m
    shine = "".join(f'<ellipse cx="{x}" cy="{y}" rx="{r}" ry="{r * 0.5:.0f}" fill="#d6e4ef" opacity="0.55"/>' for x, y, r in ((270, 650, 9), (320, 700, 7), (300, 640, 6), (350, 680, 5)))
    drips = '<path d="M 290,770 q -3,18 2,30 q 5,-12 -2,-30 Z" fill="#5a3b22"/><path d="M 330,775 q -2,12 1,20 q 4,-8 -1,-20 Z" fill="#5a3b22"/>'
    out = over(out, svg(shine + drips))
    save("f_soilw", out, a)


def f_moral(seg):
    rgb = load("ep09/final/frames/f_hook2_s3.png")
    a = cut(seg, rgb)
    out, hz = field(rgb, a, 35, wet=[(620, 1170, 220, 70), (120, 1190, 160, 50), (660, 1040, 140, 40)])
    save("f_moral", out, a)


def f_urea(seg):
    rgb = load("ep01/final/frames/f2b_s5.png")
    a = cut(seg, rgb)
    yy, xx = np.mgrid[0:H, 0:W]
    hsv = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(int)
    pod = (xx > 545) & (xx < 640) & (yy > 330) & (yy < 480) & (hsv[..., 0] >= 12) & (hsv[..., 0] <= 32) & (hsv[..., 1] < 160) & (hsv[..., 2] > 150)
    pod = cv2.morphologyEx(pod.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8))
    fing = skin_in(rgb, a, (540, 380, 680, 520)) & (cv2.dilate(pod, np.ones((5, 5), np.uint8)) == 0)
    hole = cv2.dilate(pod, np.ones((9, 9), np.uint8)) & (~fing).astype(np.uint8)
    clean = lama_fill(rgb, hole)
    out, hz = field(clean, a, 36, hz=780)
    bag = ('<g transform="rotate(-6 590 420)"><path d="M 548,352 L 632,352 L 640,480 Q 590,492 540,480 Z" fill="#f4f4ee" stroke="#6a6a60" stroke-width="5"/>'
           '<path d="M 548,352 Q 560,330 572,350 Q 590,326 608,350 Q 620,330 632,352" fill="#f4f4ee" stroke="#6a6a60" stroke-width="5"/>'
           '<rect x="552" y="350" width="76" height="10" fill="#c99300"/>'
           '<rect x="546" y="400" width="88" height="34" fill="#2e8b3a"/>'
           '<path d="M 590,445 q -22,-10 -18,-34 q 22,6 18,34 Z M 590,445 q 22,-10 18,-34 q -22,6 -18,34 Z" fill="#ffffff" transform="translate(0 -24) scale(1 0.9) translate(0 30)"/>'
           '<circle cx="564" cy="458" r="4" fill="#9e9e94"/><circle cx="612" cy="462" r="4" fill="#9e9e94"/><circle cx="588" cy="466" r="4" fill="#9e9e94"/></g>')
    out = over(out, svg(bag))
    out[fing] = rich(rgb, a, hz)[fing]
    save("f_urea", out, a)


def wet_plate():
    rgb = np.array(Image.open(HERE.parents[1] / "ep03/final/frames/grown_plate.png").convert("RGB")).astype(np.float32)
    out = water_on(rgb, blobs([(170, 1080, 220, 70), (300, 1200, 280, 80), (120, 960, 140, 36), (360, 900, 120, 26)]), 583)
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(FR / "wet_plate.png")
    print("saved wet_plate")


def main():
    only = sys.argv[1:]
    seg = new_session("isnet-anime")
    for name, fn in (("f_dry", f_dry), ("f_hose", f_hose), ("f_proud", f_proud), ("f_stuck", f_stuck), ("f_clod", f_clod),
                     ("f_soilw", f_soilw), ("f_moral", f_moral), ("f_urea", f_urea)):
        if not only or name in only:
            fn(seg)
    if not only or "wet_plate" in only:
        wet_plate()


if __name__ == "__main__":
    main()
