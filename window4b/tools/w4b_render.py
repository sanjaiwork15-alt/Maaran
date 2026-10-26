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

from scenes import SCENES
from timeline import params, FPS_DEFAULT, DURATION

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
    em = ((hsv[..., 2] > 215) & (hsv[..., 1] > 60) & (hsv[..., 0] < 35)).astype(np.float32)
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
    # where the outside view is (for drops on the glass)
    ys, xs = np.nonzero(G["outside"] > 0.98)
    G["glass_box"] = (xs.min(), ys.min(), xs.max(), ys.max())


# ---------------------------------------------------------------- pieces

def grade_city(img, p):
    w = p["wet"]
    lum = (img @ np.array([0.114, 0.587, 0.299], np.float32))[..., None]
    grey = np.array(p["tint"], np.float32)  # BGR overcast tint
    warm = np.clip((img[..., 2:3] - img[..., 0:1]) * 2.5, 0, 1)   # sunset orange/pink (R - B)
    k = np.clip(0.88 + 0.4 * warm, 0, 1) * w                       # warm light goes fully grey
    out = img * (1 - k) + lum * grey * k
    out = (out - 0.5) * (1 - 0.25 * w) + 0.5 - 0.06 * w
    out *= 1 - p["dark"]
    # haze: far things fade into the rain
    far = smoothstep(0.62, 0.30, G["rows"])[..., None]
    hi = np.clip(lum - 0.55, 0, 1) * (1 - G["emissive"][..., None])   # no sun: flatten the lit faces
    out = out - hi * 0.9 * w * (0.4 + 0.6 * far)
    out = out * (1 - far * 0.45 * w) + np.array(p["haze"], np.float32) * far * 0.45 * w
    out += G["emissive"][..., None] * img * p["lights"] * 0.8
    return out


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
        for name, x, flip, dy in cfg["bridge_parked"]:
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


def debris(city, t, p):
    if p["debris"] <= 0 or "water_mask" not in G:
        return city
    rng = np.random.default_rng(7)
    on = G["water_mask"]
    for i in range(int(40 * p["debris"])):
        x0, y0 = rng.random() * G["W"], (0.5 + 0.35 * rng.random()) * G["H"]
        x = (x0 + t * (4 + 6 * rng.random()) * G["sc"]) % G["W"]
        y = y0 + math.sin(t * 0.7 + i) * 2
        if not on[int(min(y, G["H"] - 1)), int(x)]:
            continue
        L = G["s"](y / G["sc"]) * G["sc"] * (0.6 + rng.random())
        ang = rng.random() * math.pi
        p1 = (int(x - math.cos(ang) * L), int(y - math.sin(ang) * L * 0.3))
        p2 = (int(x + math.cos(ang) * L), int(y + math.sin(ang) * L * 0.3))
        cv2.line(city, p1, p2, (0.12, 0.16, 0.2), max(1, int(G["sc"] * 1.5)), cv2.LINE_AA)
    return city


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
    if p["drops"] <= 0 and not p["final_drop"]:
        return frame
    x0, y0, x1, y1 = G["glass_box"]
    rng = np.random.default_rng(99)
    blur = cv2.GaussianBlur(frame, (0, 0), 3)
    out = frame.copy()
    trails = np.zeros(frame.shape[:2], np.float32)
    N = 420
    for i in range(N):
        born = rng.random() * DURATION if i > 6 else 1.0 + i * 0.45  # first few = the opening taps
        x = x0 + rng.random() * (x1 - x0); y = y0 + rng.random() * (y1 - y0)
        r = (2.5 + rng.random() ** 3 * 7) * G["sc"]
        slide = rng.random() < 0.35
        life = 4 + rng.random() * 10
        if i <= 6:
            born, x, y, r, slide = born, x0 + (0.30 + 0.07 * i) * (x1 - x0), y0 + (0.18 + 0.06 * (i % 4)) * (y1 - y0), (12 if i == 0 else 8) * G["sc"], False
        if born > t or rng.random() > p["drops"] and i > 6:
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
    if p["final_drop"]:
        ft = p["final_drop"]
        fx = x0 + 0.5 * (x1 - x0); fy = y0 + 0.2 * (y1 - y0) + ft * 0.45 * (y1 - y0)
        cv2.line(trails, (int(fx), int(y0 + 0.2 * (y1 - y0))), (int(fx), int(fy)), 0.6, max(1, int(6 * G["sc"])), cv2.LINE_AA)
        out = bead(out, blur, fx, fy, 13 * G["sc"])
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
    # wet sill and the mug filling with drips from a leak in the frame
    if p["sill_wet"] > 0:
        cfg = G["cfg"]
        sp = np.zeros(img.shape[:2], np.float32)
        cv2.fillPoly(sp, [(np.array(cfg["sill_puddle"]) * G["sc"]).astype(np.int32)], 1.0)
        sp = cv2.GaussianBlur(sp, (0, 0), 10 * G["sc"]) * p["sill_wet"]
        sheen = (0.85 + 0.3 * G["puddle"])[..., None]
        img = img * (1 - sp[..., None] * 0.35) + img * sheen * 0.35 * sp[..., None] * 0.6 + sp[..., None] * 0.04
    if p["mug"] > 0:
        mg = G["cfg"]["mug"]; sc = G["sc"]
        cx, cy, ax, ay = mg["cx"] * sc, mg["cy"] * sc, mg["ax"] * sc, mg["ay"] * sc
        lvl = p["mug"]
        ov = np.zeros(img.shape[:2], np.float32)
        cv2.ellipse(ov, (int(cx), int(cy + (1 - lvl) * 6 * sc)), (int(ax * (0.85 + 0.15 * lvl)), int(ay * 0.9)), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
        ov = cv2.GaussianBlur(ov, (0, 0), 1)[..., None]
        water_col = np.array([0.52, 0.5, 0.46], np.float32) * (1 - p["dark"] * 0.5)
        img = img * (1 - ov * 0.8) + water_col * ov * 0.8
    # light: warm sunset -> cool grey daylight
    w = p["wet"]
    lum = (img @ np.array([0.114, 0.587, 0.299], np.float32))[..., None]
    cool = lum * np.array(p["room_tint"], np.float32)
    img = img * (1 - 0.75 * w) + cool * 0.75 * w
    img *= 1 - p["room_dark"]
    img += p["flash"] * 0.18
    return img, a


def drip(img, p):
    """A drip from a leak in the window head falls into the mug (in front of the glass)."""
    if p["drip"] is None or p["mug"] <= 0:
        return img
    mg = G["cfg"]["mug"]; sc = G["sc"]
    cx, cy, ax, ay = mg["cx"] * sc, mg["cy"] * sc, mg["ax"] * sc, mg["ay"] * sc
    ph = p["drip"]
    if ph < 0.6:
        yy = int((ph / 0.6) ** 2 * cy)
        cv2.line(img, (int(cx), max(0, yy - int(22 * sc))), (int(cx), yy), (0.78, 0.8, 0.82), max(2, int(3 * sc)), cv2.LINE_AA)
        cv2.circle(img, (int(cx), yy), max(2, int(3 * sc)), (0.85, 0.87, 0.9), -1, cv2.LINE_AA)
    else:
        rr = (ph - 0.6) / 0.4
        cv2.ellipse(img, (int(cx), int(cy)), (int(ax * 0.8 * rr) + 1, int(ay * 0.8 * rr) + 1), 0, 0, 360,
                    (0.9, 0.9, 0.9), max(1, int(1.5 * sc)), cv2.LINE_AA)
    return img


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
    city = G["city_img"].copy()
    height = G["height"].copy()
    G["float_mask"] = np.zeros(height.shape, np.float32)
    traffic(city, t, p, height)
    city = grade_city(city, p)
    sky = sky_layer(t, p)
    sa = (G["sky"] * p["overcast"])[..., None]
    city = city * (1 - sa) + sky * sa
    if p["flash"] > 0:
        city = city + p["flash"] * (0.35 + lightning_bolt(p["bolt"], G["sky"])[..., None] * 0.9)
    city = moss(city, p, height)
    city = water(city, t, p, height)
    city = debris(city, t, p)
    city = lamps(city, p)
    city = rain(city, t, p)
    city = glass(city, t, p)
    rm, a = room(t, p)
    a = a[..., None]
    frame = city * (1 - a) + rm * a
    frame = drip(frame, p)
    frame = frame * (1 - p["jump"] * 0.25)
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
