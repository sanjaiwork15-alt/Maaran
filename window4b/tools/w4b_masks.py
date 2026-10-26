"""Window 4B: build the layer masks for a master image (run once per master).

    python window4b/tools/w4b_masks.py h|v OUT.npz [--debug DIR]

Everything is derived from the locked master plus the hand-measured shapes in
`scenes.py` (master pixel coordinates). Output (all at master resolution):
    outside   float  1 = city seen through the glass, 0 = room (frame, sill, plant, mug, books)
    sky       float  soft sky mask (inside `outside`)
    height    float  metres above street level of every outside pixel (river = RIVER_H)
    river     bool   the river surface at Day 1
    ground    bool   street-level surfaces (road, walkway, grass, far bank)
    plant     float  the potted plant (for wilting)
    clean     uint8  master with moving vehicles painted out
    sprite_*  the cut-out vehicles (RGBA) and their positions
"""
import argparse
from pathlib import Path

import cv2
import numpy as np

from scenes import SCENES, RIVER_H


def poly(shape, pts):
    m = np.zeros(shape, np.uint8)
    cv2.fillPoly(m, [np.array(pts, np.int32)], 1)
    return m.astype(bool)


def polys(shape, items):
    m = np.zeros(shape, bool)
    for it in items:
        if it[0] == "rect":
            x0, y0, x1, y1 = it[1]
            m[y0:y1, x0:x1] = True
        elif it[0] == "ellipse":
            (cx, cy, ax, ay) = it[1]
            e = np.zeros(shape, np.uint8)
            cv2.ellipse(e, (cx, cy), (ax, ay), 0, 0, 360, 1, -1)
            m |= e.astype(bool)
        else:
            m |= poly(shape, it[1])
    return m


def grabcut(im, rect, it=6):
    m = np.zeros(im.shape[:2], np.uint8)
    bg = np.zeros((1, 65)); fg = np.zeros((1, 65))
    cv2.grabCut(im, m, rect, bg, fg, it, cv2.GC_INIT_WITH_RECT)
    return (m == 1) | (m == 3)


def scale_fn(cfg):
    (y0, s0), (y1, s1) = cfg["scale"]
    lo = cfg.get("scale_min", 1.2)
    return lambda y: np.maximum(lo, s0 + (np.asarray(y, float) - y0) * (s1 - s0) / (y1 - y0))


def build(cfg, debug=None):
    im = cv2.imread(cfg["master"])
    h, w = im.shape[:2]
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV).astype(np.float32)
    hue, sat, val = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32)
    mean = cv2.blur(gray, (7, 7)); sq = cv2.blur(gray * gray, (7, 7))
    texture = np.sqrt(np.maximum(sq - mean * mean, 0))

    # ---- vehicles that move (cut out, painted out of the clean plate) -------
    clean = im.copy()
    hole = np.zeros((h, w), np.uint8)
    sprites = {}
    for name, (x0, y0, x1, y1) in cfg["vehicles"].items():
        crop = im[y0:y1, x0:x1]
        sub_hsv = hsv[y0:y1, x0:x1]
        bgc = grabcut(im, (x0 + 1, y0 + 1, x1 - x0 - 2, y1 - y0 - 2), 4)[y0:y1, x0:x1]
        a = cv2.GaussianBlur(bgc.astype(np.float32), (0, 0), 0.6)
        sprites[name] = np.dstack([crop, (a * 255).astype(np.uint8)])
        hole[y0:y1, x0:x1] |= cv2.dilate(bgc.astype(np.uint8), np.ones((5, 5), np.uint8))
    for x0, y0, x1, y1 in cfg.get("paint_out", []):
        hole[y0:y1, x0:x1] = 1
    clean = cv2.inpaint(clean, hole * 255, 5, cv2.INPAINT_TELEA)

    im_master = im
    im = clean
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV).astype(np.float32)
    hue, sat, val = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32)

    # ---- room vs outside -------------------------------------------------
    opening = poly((h, w), cfg["opening"])
    occ = np.zeros((h, w), bool)
    for o in cfg["occluders"]:
        if o[0] == "grabcut":
            x0, y0, x1, y1 = o[1]
            g = grabcut(im, (x0, y0, x1 - x0, y1 - y0))
            leafy = (hue >= o[2][0]) & (hue <= o[2][1]) & (sat > o[2][2])
            occ |= g & leafy
        elif o[0] == "colour":
            x0, y0, x1, y1 = o[1]
            box = np.zeros((h, w), bool); box[y0:y1, x0:x1] = True
            occ |= box & (hue >= o[2][0]) & (hue <= o[2][1]) & (sat > o[2][2]) & (val > o[2][3])
        else:
            occ |= polys((h, w), [o])
    occ = cv2.morphologyEx(occ.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)).astype(bool)
    outside = (opening & ~occ).astype(np.float32)
    outside = cv2.GaussianBlur(outside, (0, 0), cfg.get("fg_soft", 2.0))  # the room is out of focus
    plant = polys((h, w), [("rect", cfg["plant_box"])]) & ~opening
    plant |= occ & polys((h, w), [("rect", cfg["plant_box"])])
    plant_leaf = plant & (hue >= 18) & (hue <= 50) & (sat > 70)
    plant_soft = cv2.GaussianBlur(plant_leaf.astype(np.float32), (0, 0), 2)

    # ---- sky ---------------------------------------------------------------
    sky_zone = poly((h, w), cfg["sky_zone"]) & opening & ~occ
    line = np.interp(np.arange(w), [p[0] for p in cfg["skyline"]], [p[1] for p in cfg["skyline"]])
    rows = np.arange(h)[:, None]
    band = cfg.get("sky_band", 12)
    gc = np.full((h, w), cv2.GC_BGD, np.uint8)
    gc[(rows < line - band) & sky_zone] = cv2.GC_FGD
    gc[(abs(rows - line) <= band) & sky_zone] = cv2.GC_PR_FGD
    gc[(rows > line) & (rows <= line + band) & sky_zone] = cv2.GC_PR_BGD
    bg = np.zeros((1, 65)); fg = np.zeros((1, 65))
    cv2.grabCut(im, gc, None, bg, fg, 5, cv2.GC_INIT_WITH_MASK)
    sky = ((gc == 1) | (gc == 3)) & sky_zone
    # keep only sky connected to the top
    n, lab = cv2.connectedComponents(sky.astype(np.uint8))
    top = set(np.unique(lab[: cfg["sky_top_row"] + 3][sky[: cfg["sky_top_row"] + 3]])) - {0}
    sky = np.isin(lab, list(top))
    sky = cv2.morphologyEx(sky.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)
    sky_soft = cv2.GaussianBlur(sky.astype(np.float32), (0, 0), 1.2)

    # ---- street level ------------------------------------------------------
    objects = polys((h, w), cfg["objects"])
    river = poly((h, w), cfg["river"]) & opening & ~occ & ~objects
    canopy = (hue >= 25) & (hue <= 85) & (sat > 60)
    dark = val < 55
    trunk = (hue >= 5) & (hue <= 22) & (sat > 90) & (val < 150)
    river &= ~(canopy & (texture > 9)) & ~dark
    land = polys((h, w), [("poly", p) for p in cfg["land"]]) & opening & ~occ & ~objects & ~river
    grass = polys((h, w), [("poly", p) for p in cfg["grass"]]) & canopy & ~dark
    leafy = canopy | ((hue >= 18) & (sat > 110))
    ground = land & ~dark & ~trunk & (~leafy | grass)
    ground = cv2.morphologyEx(ground.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(ground)
    ground = np.isin(lab, [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] >= cfg.get("min_ground", 120)])
    river = cv2.morphologyEx(river.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)

    # height of every pixel = height of the first ground found straight below + distance / scale
    s = scale_fn(cfg)
    bottom = np.array([cfg["bottom"](x) for x in range(w)])
    height = np.full((h, w), 99.0, np.float32)
    gh = np.where(river, RIVER_H, np.where(ground, 0.0, np.nan))
    for x in range(w):
        last_y, last_h = int(bottom[x]), 0.0  # below the sill line is street level
        for y in range(min(h - 1, int(bottom[x])), -1, -1):
            g = gh[y, x]
            if not np.isnan(g):
                last_y, last_h = y, g
                height[y, x] = g
            else:
                height[y, x] = last_h + (last_y - y) / s(last_y)
    # trees: things seen below a crown (river through gaps) are behind it, so use the trunk base
    for pts, base in cfg.get("trees", []):
        t = poly((h, w), pts) & (leafy | dark | trunk) & ~river & ~ground
        ys = np.nonzero(t)[0]
        height[t] = (base - ys) / s(base)
    height[sky] = 99.0

    out = dict(outside=outside, sky=sky_soft, height=height, river=river, ground=ground,
               plant=plant_soft, clean=clean, hole=hole.astype(bool))
    for k, v in sprites.items():
        out["sprite_" + k] = v

    if debug:
        d = Path(debug); d.mkdir(parents=True, exist_ok=True)
        im = im_master
        v = im.copy()
        v[~(outside > 0.5)] = (v[~(outside > 0.5)] * 0.3).astype(np.uint8)
        cv2.imwrite(str(d / "outside.png"), v)
        v = im.copy(); v[sky] = (v[sky] * 0.4 + np.array([0, 0, 150])).astype(np.uint8)
        cv2.imwrite(str(d / "sky.png"), v)
        v = im.copy(); v[ground] = (v[ground] * 0.4 + np.array([0, 150, 0])).astype(np.uint8)
        v[river] = (v[river] * 0.4 + np.array([150, 0, 0])).astype(np.uint8)
        cv2.imwrite(str(d / "ground.png"), v)
        for L in (0.3, 1.0, 2.0, 3.0, 4.0):
            v = im.copy(); f = (height < L) & (outside > 0.5)
            v[f] = (v[f] * 0.3 + np.array([140, 90, 40])).astype(np.uint8)
            cv2.imwrite(str(d / f"flood_{L}.png"), v)
        cv2.imwrite(str(d / "clean.png"), clean)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("which", choices=list(SCENES))
    ap.add_argument("out")
    ap.add_argument("--debug")
    a = ap.parse_args()
    np.savez_compressed(a.out, **build(SCENES[a.which], a.debug))


if __name__ == "__main__":
    main()
