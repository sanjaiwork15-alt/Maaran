"""Window 4B Ep 1 renderer: "What If It Rained for 1 Year?" – everything drawn in code
on top of the locked master (no AI video).

    python window4b/tools/w4b_render.py h|v MASKS.npz OUT.mp4 [--still T ...] [--fps 30] [--jobs 4]

--still renders PNGs at the given times instead of the video (for checking).
The timeline (stages, water levels, rain, traffic, lightning) is in `timeline.py`.
"""
import argparse
import math
import os
import subprocess
import sys
import tempfile
from multiprocessing import Pool
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from scenes import SCENES, ROOT
from timeline import params, FPS_DEFAULT, DURATION, COLLAPSE, CLOSEUP, DROP_LANDS, ease
import story

FONT = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
G = {}  # per-process scene state


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def fbm(h, w, seed, octaves=5, base=8):
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32); amp = 1.0; tot = 0
    for o in range(octaves):
        n = base * 2 ** o
        g = rng.random((max(2, n * h // w + 1), n + 1)).astype(np.float32)
        out += amp * cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC); tot += amp; amp *= 0.5
    out /= tot
    return (out - out.min()) / (out.max() - out.min() + 1e-6)


def rain_texture(h, w, n, length, width, angle, seed, bright):
    rng = np.random.default_rng(seed)
    t = np.zeros((h, w), np.float32)
    dx = math.sin(math.radians(angle)); dy = math.cos(math.radians(angle))
    for _ in range(n):
        x, y = rng.random() * w, rng.random() * h
        L = length * (0.6 + 0.8 * rng.random())
        a = bright * (0.4 + 0.6 * rng.random())
        p0 = (int(x), int(y)); p1 = (int(x + dx * L), int(y + dy * L))
        cv2.line(t, p0, p1, a, width, cv2.LINE_AA)
        for k in (-1, 1):  # wrap so the texture tiles vertically
            cv2.line(t, (p0[0], p0[1] + k * h), (p1[0], p1[1] + k * h), a, width, cv2.LINE_AA)
    return cv2.GaussianBlur(t, (0, 0), 0.6)


def setup(which, masks_path):
    cfg = SCENES[which]
    m = np.load(masks_path)
    mh, mw = m["outside"].shape
    W, H = cfg["out_size"]
    sc = W / mw
    rs = lambda a, interp=cv2.INTER_LINEAR: cv2.resize(a, (W, H), interpolation=interp)
    master = cv2.imread(cfg["master"]).astype(np.float32) / 255
    clean = m["clean"].astype(np.float32) / 255
    G.update(cfg=cfg, W=W, H=H, sc=sc)
    G["room_img"] = rs(master, cv2.INTER_LANCZOS4).clip(0, 1)
    G["city_img"] = rs(clean, cv2.INTER_LANCZOS4).clip(0, 1)
    G["outside"] = rs(m["outside"].astype(np.float32)).clip(0, 1)
    G["sky"] = rs(m["sky"].astype(np.float32)).clip(0, 1)
    hgt = m["height"].astype(np.float32)
    hgt = cv2.GaussianBlur(np.minimum(hgt, 30), (0, 0), 1.2)
    G["height"] = rs(hgt)
    G["river"] = rs(m["river"].astype(np.float32))
    G["ground"] = rs(m["ground"].astype(np.float32))
    G["plant"] = rs(m["plant"].astype(np.float32))
    G["sprites"] = {k[7:]: m[k] for k in m.files if k.startswith("sprite_")}
    G["sprite_boxes"] = cfg["vehicles"]
    lo, hi = cfg["scale"][0], cfg["scale"][1]
    G["s"] = lambda y_m: max(cfg.get("scale_min", 1.2), lo[1] + (y_m - lo[0]) * (hi[1] - lo[1]) / (hi[0] - lo[0]))
    # emissive bits of the city (lit windows, lamps) keep glowing in the rain
    hsv = cv2.cvtColor((G["city_img"] * 255).astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
    em = ((hsv[..., 2] > 215) & (hsv[..., 1] > 60) & (hsv[..., 0] < 35)).astype(np.uint8)
    em[G["river"] > 0.3] = 0                      # sun glare on the water is not a light
    n, lab, st, _ = cv2.connectedComponentsWithStats(em)
    small = np.zeros(n, bool); small[1:] = st[1:, cv2.CC_STAT_AREA] < 500 * sc * sc
    em = small[lab].astype(np.float32)             # big bright patches are sunlit walls, not lights
    blds = np.zeros((H, W), np.uint8)              # ...except inside the near buildings: lit rooms
    for key in ("tower", "near_building"):
        if key in cfg:
            cv2.fillPoly(blds, [(np.array(cfg[key]) * sc).astype(np.int32)], 1)
    warm_lit = (hsv[..., 2] > 170) & (hsv[..., 1] > 50) & (hsv[..., 0] < 35)
    em = np.maximum(em, (warm_lit & (blds > 0)).astype(np.float32))
    G["emissive"] = cv2.GaussianBlur(em * (1 - G["sky"]) * G["outside"], (0, 0), 1.0)
    rows = np.arange(H, dtype=np.float32)[:, None] / H
    G["rows"] = rows
    G["xx"], G["yy"] = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    G["clouds"] = [fbm(H, W * 2, 11, 6, 6), fbm(H, W * 2, 12, 5, 10)]
    G["puddle"] = fbm(H, W, 21, 4, 24)
    G["moss"] = fbm(H, W, 31, 5, 40)
    G["ripple"] = fbm(H * 2, W, 41, 4, 60)
    k = sc
    G["rain"] = [
        rain_texture(H, W, 2600, 18 * k, 1, 9, 51, 0.35),   # far, fine
        rain_texture(H, W, 900, 34 * k, 1, 11, 52, 0.5),    # middle
        rain_texture(H, W, 160, 70 * k, 2, 13, 53, 0.55),   # near, big
    ]
    G["font"] = ImageFont.truetype(FONT, int(cfg["counter_size"] * k))
    G["canopy"] = rs(m["canopy"].astype(np.float32)) if "canopy" in m.files else np.zeros((H, W), np.float32)
    big = np.zeros((H, W), np.float32)
    pts, base = cfg["trees"][cfg.get("wind_tree", 1)]
    cv2.fillPoly(big, [(np.array(pts) * sc).astype(np.int32)], 1.0)
    top = min(p[1] for p in pts)
    G["big_tree"] = cv2.GaussianBlur(big, (0, 0), 6) * np.clip((base * sc - G["yy"]) / ((base - top) * sc), 0, 1)
    setup_lights(cfg, em)
    setup_vines(cfg)
    bus = cv2.imread(str(ROOT / "assets/sprites/bus_road.png"), cv2.IMREAD_UNCHANGED)
    G["extra_sprites"] = {"bus_road": (bus, 32.0)}   # sprite, px per metre where it was cut
    G["draw_sprite_at"] = draw_sprite_at
    # where the outside view is (for drops on the glass)
    ys, xs = np.nonzero(G["outside"] > 0.98)
    G["glass_box"] = (xs.min(), ys.min(), xs.max(), ys.max())


def setup_lights(cfg, em):
    """Every lit window and lamp gets its own moment: lamps switch on at dusk on Day 1,
    windows go dark through Month 2 (the power cut), streetlights flicker and die in Month 3."""
    W, H, sc = G["W"], G["H"], G["sc"]
    n, lab = cv2.connectedComponents(cv2.dilate((em > 0.5).astype(np.uint8), np.ones((3, 3), np.uint8)))
    G["light_lab"] = lab
    rng = np.random.default_rng(17)
    on_t = np.zeros(n); off_t = np.full(n, 1e9); lamp = np.zeros(n, bool)
    blds = [np.array(cfg[k]) * sc for k in ("tower", "near_building") if k in cfg]
    ys, xs = np.nonzero(lab)
    cx = np.bincount(lab[ys, xs], xs, n) / np.maximum(np.bincount(lab[ys, xs], None, n), 1)
    cy = np.bincount(lab[ys, xs], ys, n) / np.maximum(np.bincount(lab[ys, xs], None, n), 1)
    for i in range(1, n):
        inside = any(cv2.pointPolygonTest(b.astype(np.float32), (float(cx[i]), float(cy[i])), False) >= 0 for b in blds)
        if inside:
            off_t[i] = rng.uniform(53, 66) if rng.random() < 0.75 else rng.uniform(76, 92)
        elif cy[i] / sc > 470:
            lamp[i] = True
            on_t[i] = rng.uniform(2.5, 8.0)
            off_t[i] = rng.uniform(72.5, 76.5)
        else:
            off_t[i] = rng.uniform(55, 90)
    G["light_on"], G["light_off"], G["light_lamp"] = on_t, off_t, lamp
    G["em_lamp"] = G["emissive"] * lamp[lab]


def light_levels(t):
    on_t, off_t, lamp = G["light_on"], G["light_off"], G["light_lamp"]
    lvl = (np.clip((t - on_t) / 0.4, 0, 1) * np.clip((off_t - t) / 0.3, 0, 1)).astype(np.float32)
    flick = lamp & (t > off_t - 1.6) & (t < off_t)
    if flick.any():  # failing streetlights stutter before they die
        hsh = np.sin(np.arange(len(lvl)) * 12.9898 + int(t * 14) * 78.233) * 43758.5453
        lvl[flick] *= ((hsh[flick] - np.floor(hsh[flick])) > 0.45).astype(np.float32)
    lvl[0] = 1.0
    return lvl[G["light_lab"]]


def setup_vines(cfg):
    """Ivy that has crept over the near buildings and the bridge rail by Year 1."""
    W, H, sc = G["W"], G["H"], G["sc"]
    lay = np.zeros((H, W, 3), np.float32); a = np.zeros((H, W), np.float32)
    rng = np.random.default_rng(23)
    for (x0, y0, x1, y1), n in cfg.get("vine_zones", []):
        for _ in range(n):
            x = rng.uniform(x0, x1) * sc; y = rng.uniform(y0, y0 + (y1 - y0) * 0.4) * sc
            L = rng.uniform(0.3, 1.0) * (y1 - y) * 1.0
            pts = []
            for k in range(30):
                pts.append((x + math.sin(k * 0.6 + x) * 3 * sc, y + L * k / 29))
            pts = np.array(pts, np.int32)
            col = [(0.16, 0.38, 0.2), (0.2, 0.45, 0.25), (0.12, 0.3, 0.15)][int(rng.integers(3))]
            cv2.polylines(lay, [pts], False, col, max(1, int(1.6 * sc)), cv2.LINE_AA)
            cv2.polylines(a, [pts], False, 1.0, max(1, int(1.6 * sc)), cv2.LINE_AA)
            for q in pts[::3]:
                r = max(1, int(rng.uniform(1.5, 3.5) * sc))
                cv2.circle(lay, (int(q[0] + rng.uniform(-3, 3) * sc), int(q[1])), r, col, -1, cv2.LINE_AA)
                cv2.circle(a, (int(q[0] + rng.uniform(-3, 3) * sc), int(q[1])), r, 1.0, -1, cv2.LINE_AA)
    G["vines"] = (lay, a * G["outside"] * (1 - G["sky"]))


def draw_sprite_at(c, name, x_m, y_m):
    """A cut-out from the other master (e.g. the road bus) standing at a street point."""
    spr, ppm = G["extra_sprites"][name]
    sc = G["sc"] * G["s"](y_m) / ppm
    w = max(2, int(spr.shape[1] * sc)); h = max(2, int(spr.shape[0] * sc))
    s = cv2.resize(spr, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    X = int(x_m * G["sc"] - w / 2); Y = int(y_m * G["sc"] - h)
    xa, ya = max(0, X), max(0, Y); xb, yb = min(G["W"], X + w), min(G["H"], Y + h)
    sub = s[ya - Y:yb - Y, xa - X:xb - X]
    a = sub[..., 3:4] * G["outside"][ya:yb, xa:xb, None]
    c.canvas[ya:yb, xa:xb] = c.canvas[ya:yb, xa:xb] * (1 - a) + sub[..., :3] * a
    rows = np.arange(ya, yb, dtype=np.float32)[:, None]
    hv = np.broadcast_to((Y + h - rows) / (G["s"](y_m) * G["sc"]), a.shape[:2])
    c.height[ya:yb, xa:xb] = np.where(a[..., 0] > 0.4, hv, c.height[ya:yb, xa:xb])


# ---------------------------------------------------------------- pieces

def grade_city(img, p, lights):
    """Overcast daylight, natural colours: cooler white balance, the sunset glow gone, gentle haze."""
    w = p["wet"]
    lum = (img @ np.array([0.114, 0.587, 0.299], np.float32))[..., None]
    warm = np.clip((img[..., 2:3] - img[..., 0:1]) * 2.0, 0, 1)
    out = img * np.array([1 + 0.10 * w, 1.0, 1 - 0.10 * w], np.float32)
    k = (0.25 + 0.35 * warm) * w
    out = out * (1 - k) + lum * np.array(p["tint"], np.float32) * k
    out = (out - 0.5) * (1 - 0.12 * w) + 0.5
    em = G["emissive"][..., None]
    hi = np.clip(lum - 0.62, 0, 1) * (1 - em)
    out = out - hi * 0.5 * w
    out *= 1 - p["dark"]
    far = smoothstep(0.62, 0.30, G["rows"])[..., None]
    out = out * (1 - far * 0.3 * w) + np.array(p["haze"], np.float32) * far * 0.3 * w
    lv = lights[..., None]
    out = out * (1 - em * (1 - lv) * 0.72)                   # dead windows and lamps go dark
    out += em * img * lv * 0.35 * w                           # lit ones glow against the grey
    glow = cv2.GaussianBlur(G["em_lamp"] * lights, (0, 0), 5 * G["sc"])[..., None]
    out += glow * np.array([0.45, 0.75, 1.0], np.float32) * 0.5 * (0.3 + w)
    return out


def sway(city, t, p):
    """Wind in the trees; in Month 6 one big tree bends hard in the gusts."""
    H = G["H"]
    y0 = int(0.42 * H)
    cm = G["canopy"][y0:]
    xx, yy = G["xx"][y0:], G["yy"][y0:]
    wind = 0.6 + 0.8 * p["rain"]
    dx = cm * wind * 0.9 * G["sc"] * np.sin(2 * np.pi * 0.45 * t + xx * 0.013 + yy * 0.005)
    if 88 < t < 112:
        g = ease((t - 90) / 2) * ease((112 - t) / 2)
        gust = 0.65 + 0.35 * math.sin(2 * np.pi * 0.23 * t) + 0.15 * math.sin(2 * np.pi * 0.9 * t)
        dx = dx + G["big_tree"][y0:] * 9 * G["sc"] * g * gust
    if np.abs(dx).max() < 0.05:
        return city
    sub = city[y0:]
    warped = cv2.remap(sub, xx - dx, yy - y0, cv2.INTER_LINEAR)
    wm = np.maximum(cm, cv2.remap(cm, xx - dx, yy - y0, cv2.INTER_LINEAR))[..., None]
    city[y0:] = sub * (1 - wm) + warped * wm
    return city


def sky_layer(t, p):
    W, H = G["W"], G["H"]
    off = int(t * 6 * G["sc"]) % W
    c1 = np.roll(G["clouds"][0], -off, axis=1)[:, :W]
    c2 = np.roll(G["clouds"][1], -int(off * 1.7) % W, axis=1)[:, :W]
    n = 0.6 * c1 + 0.4 * c2
    top = np.array(p["sky_top"], np.float32); bot = np.array(p["sky_bot"], np.float32)
    grad = top * (1 - G["rows"][..., None] * 2.2).clip(0, 1) + bot * (G["rows"][..., None] * 2.2).clip(0, 1)
    return grad * (0.82 + 0.36 * n[..., None]) * (1 - p["dark"] * 0.6)


def lightning_bolt(seed, sky):
    rng = np.random.default_rng(seed)
    W, H = G["W"], G["H"]
    x = W * (0.3 + 0.5 * rng.random()); y = 0
    pts = [(x, y)]
    while y < H * 0.30:
        y += H * 0.02 * (0.6 + rng.random()); x += W * 0.012 * (rng.random() - 0.5) * 2
        pts.append((x, y))
    img = np.zeros((H, W), np.float32)
    cv2.polylines(img, [np.array(pts, np.int32)], False, 1.0, max(1, int(2 * G["sc"])), cv2.LINE_AA)
    glow = cv2.GaussianBlur(img, (0, 0), 6 * G["sc"])
    return np.clip(img + glow * 2.5, 0, 1) * sky


def draw_sprite(canvas, name, x_m, y_m, scale=1.0, flip=False, alpha=1.0, height_out=None, lights=0.0, floats=False):
    """Paste a cut-out vehicle with its wheels at master point (x_m, y_m)."""
    spr = G["sprites"][name]
    x0, y0, x1, y1 = G["sprite_boxes"][name]
    sc = G["sc"] * scale
    w = max(2, int((x1 - x0) * sc)); h = max(2, int((y1 - y0) * sc))
    s = cv2.resize(spr, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    if flip:
        s = s[:, ::-1]
    X = int(x_m * G["sc"] - w / 2); Y = int(y_m * G["sc"] - h)
    xa, ya = max(0, X), max(0, Y); xb, yb = min(G["W"], X + w), min(G["H"], Y + h)
    if xb <= xa or yb <= ya:
        return
    sub = s[ya - Y:yb - Y, xa - X:xb - X]
    a = sub[..., 3:4] * alpha * G["lane_clip"][ya:yb, xa:xb, None]
    canvas[ya:yb, xa:xb] = canvas[ya:yb, xa:xb] * (1 - a) + sub[..., :3] * a
    if floats:  # boats ride on the water instead of being covered by it
        G["float_mask"][ya:yb, xa:xb] = np.maximum(G["float_mask"][ya:yb, xa:xb], a[..., 0])
    if height_out is not None:  # parked vehicles get their own heights (so water climbs them)
        s_m = G["s"](y_m)
        rows = np.arange(ya, yb, dtype=np.float32)[:, None]
        hv = (Y + h - rows) / G["sc"] / s_m
        cur = height_out[ya:yb, xa:xb]
        height_out[ya:yb, xa:xb] = np.where(a[..., 0] > 0.5, np.broadcast_to(hv, cur.shape), cur)
    if lights > 0:
        G["lamps"].append((X + (w * 0.04 if not flip else w * 0.96), Y + h * 0.72, sc, lights, not flip))


def traffic(canvas, t, p, height_out):
    """Vehicles cut from the master: they drive in the first month, then stop where they are."""
    cfg = G["cfg"]
    G["lamps"] = []
    (bx0, by0), (bx1, by1) = cfg["bridge_lane"]
    bridge_y = lambda x: by0 + (by1 - by0) * (x - bx0) / (bx1 - bx0)
    mode = p["traffic"]
    G["lane_clip"] = G["bridge_clip"]
    if mode in ("busy", "slow", "few"):
        spd = {"busy": 1.0, "slow": 0.6, "few": 0.4}[mode]
        items = cfg["bridge_traffic"] if mode != "few" else cfg["bridge_traffic"][:2]
        span = bx1 - bx0 + 160
        for name, v, ph, flip, dy in items:
            x = bx0 - 80 + (ph + t * v * spd) % span
            draw_sprite(canvas, name, x, bridge_y(x) + dy, flip=flip, lights=p["headlights"])
    else:
        cl = cfg.get("collapse")
        for name, x, flip, dy in cfg["bridge_parked"]:
            if cl and t >= COLLAPSE["fall"] and cl["x0"] - 20 <= x <= cl["x1"] + 20:
                continue
            draw_sprite(canvas, name, x, bridge_y(x) + dy, flip=flip)
    G["lane_clip"] = G["outside"]
    for name, v in cfg.get("boats", []):
        x0, y0, x1, y1 = G["sprite_boxes"][name]
        y = y1 - 4 - max(0.0, p["level"] + 1.2) * G["s"](y1)
        draw_sprite(canvas, name, (x0 + x1) / 2 + v * t, y, floats=True)
    G["lane_clip"] = G["road_clip"]
    slope = cfg["road_slope"]
    for name, v, ph, flip in cfg["road_traffic"]:
        x0, y0, x1, y1 = G["sprite_boxes"][name]
        ox, oy = (x0 + x1) / 2, y1
        if mode in ("busy", "slow"):
            spd = 1.0 if mode == "busy" else 0.6
            x = ox + ((ph + t * v * spd + 300) % 600 - 300)
        else:
            x = ox + cfg["road_parked"][name]
        y = oy + (x - ox) * slope
        draw_sprite(canvas, name, x, y, scale=G["s"](y) / G["s"](oy), flip=flip,
                    lights=p["headlights"] if mode in ("busy", "slow") else 0,
                    height_out=None if mode in ("busy", "slow") else height_out)


def lamps(img, p):
    if not G["lamps"] or p["headlights"] <= 0:
        return img
    glow = np.zeros(img.shape[:2], np.float32)
    for x, y, sc, a, fwd in G["lamps"]:
        cv2.circle(glow, (int(x), int(y)), max(1, int(1.6 * sc)), a, -1, cv2.LINE_AA)
    glow = glow + cv2.GaussianBlur(glow, (0, 0), 4 * G["sc"]) * 3
    return img + glow[..., None] * np.array([0.75, 0.9, 1.0], np.float32)


def water(city, t, p, height):
    """Flood: where the ground (or object) height is below the water level."""
    W, H = G["W"], G["H"]
    L = p["level"]
    wob = (G["ripple"][(np.arange(H) + int(t * 20)) % (2 * H)][:, :W] - 0.5) * 0.10
    wet = ((height + wob < L) & (height > -1.15)).astype(np.float32) * G["outside"]
    # the river: painted river fades into the rain-water look as the weather turns
    wet = np.maximum(wet, G["river"] * p["river_mix"])
    # puddles on the street before the flood arrives
    pud = (G["puddle"] > 1 - p["puddles"]).astype(np.float32) * G["ground"] * 0.85
    wet = np.maximum(wet, pud)
    wet = cv2.GaussianBlur(wet, (0, 0), 0.8) * (1 - G["float_mask"])
    if wet.max() < 0.01:
        return city
    # distance from the top edge of each water run (for reflections and the waterline)
    on = wet > 0.5
    d = np.zeros((H, W), np.float32)
    for y in range(1, H):
        d[y] = np.where(on[y], d[y - 1] + 1, 0)
    rip = (G["ripple"][(np.arange(H) + int(t * 35)) % (2 * H)][:, :W] - 0.5)
    mx = G["xx"] + rip * 6 * G["sc"]
    my = np.clip(G["yy"] - 2 * d - 1 + rip * 2, 0, H - 1)
    refl = cv2.remap(city, mx, my, cv2.INTER_LINEAR)
    base = np.array(p["water"], np.float32) * (0.75 + 0.5 * (1 - G["rows"][..., None]))
    streak = (0.92 + 0.16 * rip[..., None])
    col = (base * 0.55 + refl * 0.45) * streak
    edge = np.exp(-d / (2.5 * G["sc"]))[..., None]
    col = col + edge * 0.06
    # just under the surface you still glimpse what is drowned
    see = np.exp(-d / (4 * G["sc"]))[..., None] * 0.35
    col = col * (1 - see) + city * see * 0.8
    # rain rings
    rings = np.zeros((H, W), np.float32)
    rng = np.random.default_rng(int(t * 1000) % 2 ** 31)
    ys, xs = np.nonzero(on[::4, ::4])
    if len(ys):
        n = int(p["rings"] * 220)
        idx = rng.integers(0, len(ys), n)
        for i in idx:
            y, x = ys[i] * 4, xs[i] * 4
            r = G["s"](y / G["sc"]) * G["sc"] * (0.15 + 0.35 * rng.random())
            cv2.ellipse(rings, (int(x), int(y)), (max(1, int(r)), max(1, int(r * 0.32))), 0, 0, 360, 0.5, 1, cv2.LINE_AA)
    col = col + rings[..., None] * 0.18 * on[..., None]
    a = wet[..., None] * p["water_alpha"]
    out = city * (1 - a) + col * a
    G["water_mask"] = on
    return out


def moss(city, p, height):
    if p["moss"] <= 0:
        return city
    L = p["level"]
    band = smoothstep(L + 2.2, L, height) * (height > L) * (1 - G["ground"]) * (1 - G["sky"]) * G["outside"]
    m = band * (G["moss"] > 0.45) * p["moss"]
    m = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.0)[..., None]
    green = city * np.array([0.55, 0.95, 0.6], np.float32) * 0.85
    return city * (1 - m * 0.7) + green * m * 0.7


def bridge(city, t, p, height):
    """Month 11: cracks spread across one span, it sags, breaks and falls into the flood."""
    cfg = G["cfg"].get("collapse")
    if not cfg or t < COLLAPSE["cracks"]:
        return city
    sc = G["sc"]
    x0, x1, y0, y1 = (np.array([cfg["x0"], cfg["x1"], cfg["y0"], cfg["y1"]]) * sc).astype(int)
    px0, py0, px1, py1 = (np.array(cfg["pier"]) * sc).astype(int)
    ws = int((490 - (p["level"] + 1.2) * G["s"](490)) * sc)   # flood surface at the bridge
    rng = np.random.default_rng(3)
    fall_k = max(0.0, (t - COLLAPSE["fall"]) / (COLLAPSE["hit"] - COLLAPSE["fall"]))
    if t < COLLAPSE["fall"]:
        g = ease((t - COLLAPSE["cracks"]) / (COLLAPSE["crack"] - COLLAPSE["cracks"]))
        for i in range(9):  # cracks grow across the deck face
            cx = rng.uniform(x0, x1); cy = rng.uniform(y0 + 0.45 * (y1 - y0), y1 - 2)
            pts = [(cx, cy)]
            for k in range(int(2 + 10 * g * rng.uniform(0.5, 1))):
                pts.append((pts[-1][0] + rng.uniform(-4, 4) * sc, pts[-1][1] - rng.uniform(1, 3) * sc))
            cv2.polylines(city, [np.array(pts, np.int32)], False, (0.12, 0.12, 0.13), max(1, int(1.2 * sc)), cv2.LINE_AA)
        if t > COLLAPSE["groan"]:  # chips fall off the underside
            for i in range(14):
                t0 = COLLAPSE["groan"] + rng.uniform(0, COLLAPSE["fall"] - COLLAPSE["groan"])
                if t > t0:
                    dt = t - t0
                    x = rng.uniform(x0, x1); y = y1 + 0.5 * 300 * sc * dt * dt
                    if y < ws:
                        cv2.circle(city, (int(x), int(y)), max(1, int(1.2 * sc)), (0.55, 0.56, 0.58), -1, cv2.LINE_AA)
        if t > COLLAPSE["crack"]:  # the span sags
            k = ease((t - COLLAPSE["crack"]) / (COLLAPSE["fall"] - COLLAPSE["crack"]))
            sub = city[y0 - 10:py1, x0:x1].copy()
            xx = np.arange(x1 - x0, dtype=np.float32)[None, :]
            dy = 4 * sc * k * np.sin(np.pi * xx / (x1 - x0))
            yy = np.arange(sub.shape[0], dtype=np.float32)[:, None] - dy
            city[y0 - 10:py1, x0:x1] = cv2.remap(sub, np.broadcast_to(xx, sub.shape[:2]).astype(np.float32),
                                                 yy.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        return city
    # ---- after the break: snapshot the span, open the gap, drop the piece
    piece = city[y0:py1, x0:x1].copy()
    pa = np.zeros(piece.shape[:2], np.float32)
    pa[: y1 - y0] = 1.0
    pa[y1 - y0:, px0 - x0:px1 - x0] = 1.0
    band = city[y0 - int(14 * sc):y0, x0:x1]                    # far bank just above the deck
    mid = int((y0 + y1) / 2)
    gy0 = y0 + int(11 * sc)                                       # the gap starts at the road surface
    top = cv2.GaussianBlur(city[gy0 - int(6 * sc):gy0, x0:x1], (0, 0), 2 * sc).mean(axis=0)
    bot = cv2.GaussianBlur(city[y1 + int(4 * sc):y1 + int(10 * sc), x0:x1], (0, 0), 2 * sc).mean(axis=0)
    k = np.linspace(0, 1, y1 - gy0, dtype=np.float32)[:, None, None]
    city[gy0:y1, x0:x1] = top[None] * (1 - k) + bot[None] * k          # the far bank seen through the gap
    deck = city[y0:y1, x0 - int(8 * sc):x0].mean(axis=(0, 1))
    for ex, sg in ((x0, 1), (x1, -1)):  # broken slabs hang from both ends into the water
        poly = np.array([(ex, y0 + 0.3 * (y1 - y0)), (ex + sg * 10 * sc, y0 + 0.4 * (y1 - y0)),
                         (ex + sg * 30 * sc, ws + 6), (ex + sg * 20 * sc, ws + 6), (ex, y1)], np.int32)
        cv2.fillPoly(city, [poly], (deck * 0.85).tolist(), cv2.LINE_AA)
        cv2.polylines(city, [poly], True, (0.15, 0.15, 0.16), max(1, int(sc)), cv2.LINE_AA)
    city[y1:py1, px0:px1] = city[y1:py1, px0 - (px1 - px0):px0]
    height[mid - int(2 * sc):py1 + 4, x0:x1] = -1.2              # water fills the bottom of the gap
    for ex in (x0, x1):  # jagged broken ends and bent rebar
        for k in range(6):
            yy = y0 + (y1 - y0) * k / 6
            dx = rng.uniform(1, 5) * sc * (1 if ex == x0 else -1)
            cv2.line(city, (ex, int(yy)), (int(ex + dx), int(yy + 3 * sc)), (0.15, 0.15, 0.16), max(1, int(sc)), cv2.LINE_AA)
    if fall_k < 1.6:
        k = min(fall_k, 1.6)
        ang = 32 * k * k
        drop = 75 * sc * k * k
        M = cv2.getRotationMatrix2D((float(x1 - x0), 0.0), -ang, 1.0)
        M[1, 2] += drop
        M[0, 2] += x0; M[1, 2] += y0
        Wd, Hd = G["W"], G["H"]
        warped = cv2.warpAffine(piece, M, (Wd, Hd))
        wa = cv2.warpAffine(pa, M, (Wd, Hd))
        wa[ws:] = 0                                              # what is under water is hidden
        city = city * (1 - wa[..., None]) + warped * wa[..., None]
    return city


def splash(img, t, p):
    """The span hits the water: spray, a mist cloud and rings rushing out."""
    cfg = G["cfg"].get("collapse")
    if not cfg:
        return img
    th = COLLAPSE["hit"] - 0.5
    if not th <= t < th + 5:
        return img
    sc = G["sc"]
    dt = t - th
    cx = (cfg["x0"] + cfg["x1"]) / 2 * sc
    ws = (490 - (p["level"] + 1.2) * G["s"](490)) * sc
    rng = np.random.default_rng(11)
    lay = np.zeros(img.shape[:2], np.float32)
    for i in range(260):
        vx = rng.uniform(-70, 70) * sc; vy = -rng.uniform(40, 150) * sc; x0 = cx + rng.uniform(-80, 80) * sc
        d0 = rng.uniform(0, 0.4)
        tt = dt - d0
        if tt < 0:
            continue
        x = x0 + vx * tt; y = ws + vy * tt + 0.5 * 260 * sc * tt * tt
        if y > ws or tt > 2.5:
            continue
        cv2.circle(lay, (int(x), int(y)), max(1, int(rng.uniform(0.8, 2.2) * sc)), 1.0 - tt / 2.5, -1, cv2.LINE_AA)
    mist = np.zeros(img.shape[:2], np.float32)
    r = (20 + 60 * min(dt, 2)) * sc
    cv2.ellipse(mist, (int(cx), int(ws - r * 0.35)), (int(r * 1.3), int(r * 0.6)), 0, 0, 360, 1.0, -1)
    mist = cv2.GaussianBlur(mist, (0, 0), 14 * sc) * max(0, 1 - dt / 4.5) * 0.55
    for k in range(3):
        rr = (40 + 120 * dt - 30 * k) * sc
        if rr > 0:
            cv2.ellipse(lay, (int(cx), int(ws + 2 * sc)), (int(rr * 1.5), int(rr * 0.18)), 0, 0, 360,
                        max(0.0, 0.8 - dt / 4), max(1, int(1.5 * sc)), cv2.LINE_AA)
    lay = np.clip(lay + mist, 0, 1)[..., None] * G["outside"][..., None]
    return img * (1 - lay * 0.85) + np.array([0.86, 0.87, 0.86], np.float32) * lay * 0.85


def wreckage(img, t, p):
    """After the collapse, chunks and planks drift away downstream."""
    if t < COLLAPSE["hit"] or "water_mask" not in G:
        return img
    cfg = G["cfg"]["collapse"]; sc = G["sc"]
    rng = np.random.default_rng(13)
    ws = (490 - (p["level"] + 1.2) * G["s"](490))
    for i in range(16):
        x = (cfg["x0"] + rng.uniform(0, cfg["x1"] - cfg["x0"]) + (t - COLLAPSE["hit"]) * rng.uniform(4, 14)) * sc
        y = (ws + rng.uniform(3, 40)) * sc
        if x >= G["W"] or not G["water_mask"][min(int(y), G["H"] - 1), int(x)]:
            continue
        L = rng.uniform(3, 9) * sc * (1 + (y / sc - ws) / 40)
        col = (0.5, 0.52, 0.55) if i % 3 else (0.18, 0.28, 0.38)
        cv2.line(img, (int(x - L), int(y)), (int(x + L), int(y + rng.uniform(-2, 2) * sc)), col, max(1, int(2 * sc)), cv2.LINE_AA)
    return img


def vines(city, p):
    if p["vines"] <= 0:
        return city
    lay, a = G["vines"]
    a = (a * p["vines"])[..., None]
    return city * (1 - a) + lay * (1 - p["dark"]) * a


def closeup(frame, t, p):
    """The loop: cut to a close-up of the mug, one drop falls from the frame into it, cut to black."""
    if p["black"]:
        return np.zeros_like(frame)
    cfg = G["cfg"]; sc = G["sc"]
    x0, y0, w, h = (np.array(cfg["closeup"]) * sc).astype(int)
    crop = frame[y0:y0 + h, x0:x0 + w]
    big = cv2.resize(crop, (G["W"], G["H"]), interpolation=cv2.INTER_CUBIC)
    oc = cv2.resize(G["outside"][y0:y0 + h, x0:x0 + w], (G["W"], G["H"]))[..., None]
    big = cv2.GaussianBlur(big, (0, 0), 1.5) * (1 - oc) + cv2.GaussianBlur(big, (0, 0), 6) * oc
    z = G["W"] / w
    mg = cfg["mug"]
    cx = (mg["cx"] * sc - x0) * z; rim = (mg["cy"] * sc - y0) * z
    k = np.clip((t - CLOSEUP - 0.5) / (DROP_LANDS - CLOSEUP - 0.5), 0, 1)
    y = -40 + (rim + 40) * k * k
    if t > CLOSEUP + 0.5:
        r = 9 * z / 5
        cv2.ellipse(big, (int(cx), int(y)), (int(r), int(r * 1.5)), 0, 0, 360, (0.78, 0.8, 0.82), -1, cv2.LINE_AA)
        cv2.line(big, (int(cx), int(y - r * 6 * k)), (int(cx), int(y - r)), (0.72, 0.74, 0.76), max(1, int(r * 0.5)), cv2.LINE_AA)
        cv2.circle(big, (int(cx - r * 0.35), int(y - r * 0.5)), max(1, int(r * 0.3)), (1, 1, 1), -1, cv2.LINE_AA)
    return big


def rain(img, t, p):
    out = img
    W, H = G["W"], G["H"]
    for i, (tex, spd) in enumerate(zip(G["rain"], (900, 1300, 1900))):
        a = p["rain"] * (0.55, 0.75, 0.9)[i]
        if a <= 0:
            continue
        off = int(t * spd * G["sc"]) % H
        r = np.roll(tex, off, axis=0)
        r = np.roll(r, int(off * 0.18) % W, axis=1)
        out = out + (r * a * G["outside"])[..., None] * (np.array(p["rain_col"], np.float32) - out * 0.6)
    return out


def glass(frame, t, p):
    """Drops on the window: beads that build up, some slide down leaving trails."""
    if p["drops"] <= 0 and t > 5:
        return frame
    x0, y0, x1, y1 = G["glass_box"]
    rng = np.random.default_rng(99)
    blur = cv2.GaussianBlur(frame, (0, 0), 3)
    out = frame.copy()
    trails = np.zeros(frame.shape[:2], np.float32)
    N = 420
    for i in range(N):
        born = rng.random() * DURATION if i > 6 else 2.0 + i * 0.33  # first few = the opening taps
        x = x0 + rng.random() * (x1 - x0); y = y0 + rng.random() * (y1 - y0)
        r = (2.5 + rng.random() ** 3 * 7) * G["sc"]
        slide = rng.random() < 0.35
        life = 4 + rng.random() * 10
        if i <= 6:
            born, x, y, r, slide = born, x0 + (0.30 + 0.07 * i) * (x1 - x0), y0 + (0.18 + 0.06 * (i % 4)) * (y1 - y0), (12 if i == 0 else 8) * G["sc"], False
        if born > t or (i > 6 and rng.random() > p["drops"]):
            continue
        age = t - born
        if age > life and i > 6:
            continue
        yy = y
        if slide and age > 1:
            v = (40 + 120 * rng.random()) * G["sc"] * p["drops"]
            yy = y + (age - 1) * v
            if yy > y1:
                continue
            cv2.line(trails, (int(x), int(y)), (int(x), int(yy)), 0.35, max(1, int(r * 0.6)), cv2.LINE_AA)
        if i <= 6 and age < 0.18:  # the impact: a flat splash that pulls into a bead
            k = 1 - age / 0.18
            cv2.ellipse(trails, (int(x), int(yy)), (int(r * (1 + 1.6 * k)), int(r * (0.6 + 0.6 * k))), 0, 0, 360, 0.8 * k, -1, cv2.LINE_AA)
        out = bead(out, blur, x, yy, r)
    tr = cv2.GaussianBlur(trails, (0, 0), 1.0)[..., None] * G["outside"][..., None]
    out = out * (1 - tr * 0.5) + (blur * 1.15 + 0.03) * tr * 0.5
    return out


def bead(img, blur, x, y, r):
    """A water bead acts like a tiny lens: shows the scene upside-down and brighter, dark rim, highlight."""
    R = int(r) + 2
    xa, ya, xb, yb = int(x) - R, int(y) - R, int(x) + R + 1, int(y) + R + 1
    if xa < 0 or ya < 0 or xb > G["W"] or yb > G["H"]:
        return img
    g = G["outside"][int(y), int(x)]
    if g < 0.5:
        return img
    yy, xx = np.mgrid[ya:yb, xa:xb].astype(np.float32)
    dd = np.sqrt((xx - x) ** 2 + ((yy - y) * 1.1) ** 2) / r
    inside = np.clip((1 - dd) * r, 0, 1)[..., None]
    sx = np.clip(x - (xx - x) * 3, 0, G["W"] - 1).astype(int); sy = np.clip(y - (yy - y) * 3 - 6 * r, 0, G["H"] - 1).astype(int)
    lens = blur[sy, sx] * 1.1 + 0.03
    rim = np.exp(-((dd - 0.85) / 0.18) ** 2)[..., None] * 0.35
    hl = np.exp(-(((xx - x + r * 0.35) ** 2 + (yy - y + r * 0.4) ** 2) / (0.09 * r * r)))[..., None]
    patch = img[ya:yb, xa:xb]
    patch = patch * (1 - inside) + (lens * (1 - rim) + hl * 0.8) * inside
    img[ya:yb, xa:xb] = patch
    return img


def room(t, p):
    """The flat interior: frame, sill, plant, mug, books – lit by the weather outside."""
    img = G["room_img"].copy()
    a = 1 - G["outside"]
    # plant: yellows and droops over the year
    if p["plant"] > 0:
        pl = G["plant"]
        k = p["plant"]
        x0, y0, x1, y1 = G["cfg"]["plant_box"]
        sc = G["sc"]
        cy = (y0 + 0.25 * (y1 - y0)) * sc
        fall = (np.clip((G["yy"] - y0 * sc) / ((y1 - y0) * sc), 0, 1))
        box = ((G["xx"] >= x0 * sc - 20) & (G["xx"] <= x1 * sc + 20) & (G["yy"] >= y0 * sc - 40) & (G["yy"] <= y1 * sc)).astype(np.float32)
        dy = k * 26 * sc * np.sin(np.pi * fall) * box
        mx, my = G["xx"], G["yy"] - dy
        img = cv2.remap(img, mx, my, cv2.INTER_LINEAR)
        a = cv2.remap(a.astype(np.float32), mx, my, cv2.INTER_LINEAR)
        pl = cv2.remap(pl, mx, my, cv2.INTER_LINEAR)
        lum = (img @ np.array([0.114, 0.587, 0.299], np.float32))[..., None]
        sick = lum * np.array([0.35, 0.72, 0.85], np.float32) * 1.05
        m = (pl * k)[..., None]
        img = img * (1 - m * 0.9) + sick * m * 0.9
    # light: warm sunset -> cool grey daylight
    w = p["wet"]
    lum = (img @ np.array([0.114, 0.587, 0.299], np.float32))[..., None]
    cool = lum * np.array(p["room_tint"], np.float32)
    img = img * np.array([1 + 0.06 * w, 1.0, 1 - 0.08 * w], np.float32)
    img = img * (1 - 0.3 * w) + cool * 0.3 * w
    img *= 1 - p["room_dark"]
    img += p["flash"] * 0.18
    return img, a


def counter(frame, p):
    if not p["label"] or p["label_a"] <= 0:
        return frame
    W, H = G["W"], G["H"]
    x, y = (np.array(G["cfg"]["counter_xy"]) * G["sc"]).astype(int)
    lay = Image.new("L", (W, H), 0); sh = Image.new("L", (W, H), 0)
    ImageDraw.Draw(lay).text((x, y), p["label"], font=G["font"], fill=255)
    ImageDraw.Draw(sh).text((x + int(2 * G["sc"]), y + int(3 * G["sc"])), p["label"], font=G["font"], fill=255)
    sh = sh.filter(ImageFilter.GaussianBlur(5 * G["sc"]))
    a = np.asarray(lay, np.float32)[..., None] / 255 * p["label_a"]
    s = np.asarray(sh, np.float32)[..., None] / 255 * p["label_a"] * 0.55
    frame = frame * (1 - s)
    return frame * (1 - a) + np.array([0.97, 0.98, 1.0], np.float32) * a


def render(t):
    p = params(t)
    if p["black"]:
        return np.zeros((G["H"], G["W"], 3), np.uint8)
    city = G["city_img"].copy()
    height = G["height"].copy()
    G["float_mask"] = np.zeros(height.shape, np.float32)
    traffic(city, t, p, height)
    story.play(G, t, p, city, height, G["float_mask"], pre=True)
    city = sway(city, t, p)
    city = grade_city(city, p, light_levels(t))
    sky = sky_layer(t, p)
    sa = (G["sky"] * p["overcast"])[..., None]
    city = city * (1 - sa) + sky * sa
    if p["flash"] > 0:
        city = city + p["flash"] * (0.3 + lightning_bolt(p["bolt"], G["sky"])[..., None] * 0.9)
    actors = city.copy()
    story.play(G, t, p, actors, height, G["float_mask"])          # people and boats keep their colours
    city = city + (actors - city) * (1 - p["dark"] * 0.5)
    city = moss(city, p, height)
    city = vines(city, p)
    city = bridge(city, t, p, height)
    city = water(city, t, p, height)
    city = wreckage(city, t, p)
    city = splash(city, t, p)
    city = lamps(city, p)
    city = rain(city, t, p)
    city = glass(city, t, p)
    rm, a = room(t, p)
    a = a[..., None]
    frame = city * (1 - a) + rm * a
    frame = frame * (1 - p["jump"] * 0.2)
    if p["closeup"]:
        frame = closeup(frame, t, p)
    else:
        if not os.environ.get("W4B_NO_COUNTER"):
            frame = counter(frame, p)
    return (np.clip(frame, 0, 1) * 255).astype(np.uint8)


def init_worker(which, masks):
    setup(which, masks)
    cfg = SCENES[which]
    W, H, sc = G["W"], G["H"], G["sc"]
    for key in ("bridge_clip", "road_clip"):
        m = np.zeros((H, W), np.float32)
        cv2.fillPoly(m, [(np.array(cfg[key]) * sc).astype(np.int32)], 1.0)
        G[key] = cv2.GaussianBlur(m, (0, 0), 3 * sc)


def render_chunk(args):
    which, masks, start, end, fps, path = args
    W, H = G["W"], G["H"]
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                           "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                           "-crf", "16", "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    for f in range(start, end):
        ff.stdin.write(render(f / fps).tobytes())
    ff.stdin.close(); ff.wait()
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("which"); ap.add_argument("masks"); ap.add_argument("out")
    ap.add_argument("--still", type=float, nargs="*")
    ap.add_argument("--fps", type=int, default=FPS_DEFAULT)
    ap.add_argument("--jobs", type=int, default=os.cpu_count())
    ap.add_argument("--start", type=float, default=0); ap.add_argument("--end", type=float, default=DURATION)
    a = ap.parse_args()
    if a.still:
        init_worker(a.which, a.masks)
        out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
        for t in a.still:
            cv2.imwrite(str(out / f"t{t:06.2f}.png"), render(t))
        return
    n0, n1 = int(a.start * a.fps), int(a.end * a.fps)
    tmp = Path(tempfile.mkdtemp(dir=Path(a.out).parent))
    k = a.jobs * 3
    bounds = [n0 + (n1 - n0) * i // k for i in range(k + 1)]
    jobs = [(a.which, a.masks, bounds[i], bounds[i + 1], a.fps, str(tmp / f"c{i:03d}.mp4")) for i in range(k)]
    with Pool(a.jobs, initializer=init_worker, initargs=(a.which, a.masks)) as pool:
        for i, _ in enumerate(pool.imap(render_chunk, jobs)):
            print(f"chunk {i + 1}/{k}", flush=True)
    (tmp / "list.txt").write_text("".join(f"file '{j[5]}'\n" for j in jobs))
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"),
                    "-c", "copy", a.out], check=True)
    for j in jobs:
        os.remove(j[5])
    os.remove(tmp / "list.txt"); tmp.rmdir()


if __name__ == "__main__":
    main()
