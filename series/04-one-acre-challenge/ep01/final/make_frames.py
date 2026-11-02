"""One-Acre Challenge Ep 1 – start frames without a GPU: Thatha's dry, neglected one-acre field.

Run with the f5 env:  python -I make_frames.py
Every frame is an approved Groundnut field frame (same field, same light) used WHOLE, made dry in code:
the red tilled soil turns pale and dusty with a perspective crack network, green ground plants wilt to straw,
Thatha is protected by his rembg cut-out (his green towel stays green). Trees and sky are untouched.
f_proud:  Ep 1 f5_hoe_s8   – standing proud, hoe on his shoulder (the big dream / "mudhal vela")
f_seeds:  Ep 1 f1_hook_s3  – groundnut seeds held out in his palm ("indha vidhai")
f_nut:    Ep 1 f2b_s5      – holding one seed up, talking to it ("vidhaiye… valarndhuru")
f_dig:    Ep 2 f_hoe_s8    – digging with the hoe (the hard ground)
f_point:  Ep 2 f_hook2_s3  – pointing down at the soil ("indha mannukku enna kovam?!")
f_soil:   Ep 2 f_soil_s3   – crouching, crumbling dry soil in his hands (the mystery)
dry_plate.png: the empty field (owner's 05_field_vertical) made dry – for library actions (walk, laugh, bow).
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import new_session, remove

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FR = HERE / "frames"
GN = ROOT / "series/01-groundnut"
W, H = 720, 1280
HORIZON = {"f_proud": 615, "f_seeds": 690, "f_nut": 780, "f_dig": 630, "f_point": 690, "f_soil": 615}   # ground line
CLUMP = {"f_soil": (215, 590, 395, 800)}                  # the soil in his hands: dry it too
POSES = {"f_proud": "ep01/final/frames/f5_hoe_s8.png", "f_seeds": "ep01/final/frames/f1_hook_s3.png",
         "f_nut": "ep01/final/frames/f2b_s5.png", "f_dig": "ep02/final/frames/f_hoe_s8.png",
         "f_point": "ep02/final/frames/f_hook2_s3.png", "f_soil": "ep02/final/frames/f_soil_s3.png"}


def crack_layer(horizon, seed=5):
    """Dried-mud crack network on a flat plane, warped into perspective below the horizon. Returns 0..1 darkness."""
    rng = np.random.default_rng(seed)
    PW, PH = 1400, 1400
    plane = np.zeros((PH, PW), np.uint8)
    sub = cv2.Subdiv2D((-100, -100, PW + 200, PH + 200))
    for _ in range(260):
        sub.insert((float(rng.uniform(-50, PW + 50)), float(rng.uniform(-50, PH + 50))))
    cells, _ = sub.getVoronoiFacetList([])
    for c in cells:
        pts = np.array(c, np.float32)
        jit = pts + rng.normal(0, 4, pts.shape)              # wobbly, hand-drawn crack lines
        cv2.polylines(plane, [jit.astype(np.int32)], True, 255, int(rng.integers(3, 6)), cv2.LINE_AA)
    src = np.float32([[0, 0], [PW, 0], [PW, PH], [0, PH]])
    dst = np.float32([[-W * 0.6, horizon], [W * 1.6, horizon], [W * 2.2, H * 1.25], [-W * 1.2, H * 1.25]])
    M = cv2.getPerspectiveTransform(src, dst)
    out = cv2.warpPerspective(plane, M, (W, H)).astype(np.float32) / 255
    fade = np.clip((np.arange(H)[:, None] - horizon) / 160.0, 0, 1)     # fade into the distance
    return out * fade


def dry(rgb, protect, horizon):
    """Red tilled soil -> pale dry cracked soil; green ground plants -> straw. protect: 0..1 (Thatha)."""
    x = rgb.astype(np.float32)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
    hh, ss, vv = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    yy = np.arange(H, dtype=np.float32)[:, None] * np.ones((1, W), np.float32)
    below = np.clip((yy - horizon) / 30.0, 0, 1)
    soil = (((hh <= 22) | (hh >= 170)) & (ss > 60)).astype(np.float32) * below
    soil = cv2.GaussianBlur(soil, (0, 0), 1.2) * (1 - protect)
    grey = x.mean(axis=2, keepdims=True)
    pale = x * 0.45 + grey * 0.25 + np.array([92, 72, 52], np.float32) * 0.5       # dusty, washed-out
    pale = pale * (0.9 + 0.1 * (vv[..., None] / 255))
    out = x * (1 - soil[..., None]) + pale * soil[..., None]
    cr = crack_layer(horizon) * soil
    out = out * (1 - 0.55 * cr[..., None]) + np.array([70, 45, 28], np.float32) * 0.55 * cr[..., None]
    green = ((hh >= 30) & (hh <= 90) & (ss > 50)).astype(np.float32) * np.clip((yy - horizon - 40) / 60.0, 0, 1)
    green = cv2.GaussianBlur(green, (0, 0), 1.0) * (1 - protect)
    straw = np.stack([grey[..., 0] * 0.9 + 70, grey[..., 0] * 0.8 + 50, grey[..., 0] * 0.4 + 20], -1)
    out = out * (1 - green[..., None]) + straw * green[..., None]
    sky = (yy < horizon).astype(np.float32)[..., None] * (1 - protect[..., None])    # a hotter, hazier day
    out = out * (1 - 0.12 * sky) + np.array([250, 235, 205], np.float32) * 0.12 * sky
    return np.clip(out, 0, 255).astype(np.uint8)


def horizon_of(rgb):
    """Top of the red soil band (median over columns)."""
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(int)
    soil = (((hsv[..., 0] <= 22) | (hsv[..., 0] >= 170)) & (hsv[..., 1] > 90) & (hsv[..., 2] > 90))
    rows = soil.mean(axis=1)
    return int(np.argmax(rows > 0.45))


def main():
    seg = new_session("isnet-anime")
    only = sys.argv[1:]
    plate = np.array(Image.open(ROOT / "assets/2d/source/05_field_vertical.png").convert("RGB").resize((W, H), Image.LANCZOS))
    hz = horizon_of(plate)
    if not only or "dry_plate" in only:
        Image.fromarray(dry(plate, np.zeros((H, W), np.float32), hz)).save(FR / "dry_plate.png")
        print("dry_plate horizon", hz)
    for name, src in POSES.items():
        if only and name not in only:
            continue
        im = Image.open(GN / src).convert("RGB").resize((W, H))
        rgb = np.array(im)
        a = np.array(remove(im, session=seg, only_mask=True)).astype(np.float32)
        a = np.clip((a - 90) * 2.6, 0, 255) / 255
        a = cv2.GaussianBlur(cv2.dilate(a, np.ones((5, 5), np.uint8)), (0, 0), 1.5)
        out = dry(rgb, a, HORIZON[name])
        if name in CLUMP:
            x0, y0, x1, y1 = CLUMP[name]
            reg = out[y0:y1, x0:x1].astype(np.float32)
            hsv = cv2.cvtColor(rgb[y0:y1, x0:x1], cv2.COLOR_RGB2HSV).astype(int)
            soilm = ((hsv[..., 0] <= 14) | (hsv[..., 0] >= 170)) & (hsv[..., 1] > 120) & (hsv[..., 2] < 200)
            g = reg.mean(axis=2, keepdims=True)
            pale = reg * 0.45 + g * 0.25 + np.array([92, 72, 52], np.float32) * 0.5
            m = cv2.GaussianBlur(soilm.astype(np.float32), (0, 0), 1.0)[..., None]
            out[y0:y1, x0:x1] = np.clip(reg * (1 - m) + pale * m, 0, 255).astype(np.uint8)
        Image.fromarray(out).save(FR / f"{name}.png")
        print("saved", name)


if __name__ == "__main__":
    main()
