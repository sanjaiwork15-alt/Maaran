"""Watering-and-waterlogging cut-aways (One-Acre Challenge Ep 4 – Thatha's water kingdom). 1080x1920.

python tools/toon/water.py OUT.mp4 TIMING.json   (TIMING.json "mode" + "duration"; "still": t renders one PNG)
    valve:    close-up of the field pipe's red wheel valve with the green hose: the wheel turns ("on": true – water
              bursts out of the hose end; false – the flow dies away).
    flood:    the field (cfg "bg", a 720x1280 plate, cfg "horizon"): the hose lies in the field gushing; the water
              spreads out in a growing sheet that mirrors the sky, splashes fly.
    grow:     his daydream (dream bubble over cfg "bg"): a brinjal plant shoots up huge and fruits pop out on it,
              Thatha (library laugh) beside it.
    mud:      close-up of his feet (the owner's 01_front art): the mud rises round his right foot, the foot strains up
              and is sucked back, bubbles and squelch blobs.
    slipper:  close-up: his empty slipper left stuck in the mud, bubbles.
    wobble:   wide: Thatha (01_front) stuck ankle-deep in mud on cfg "bg", wobbling, nearly falls back, recovers.
    compare:  a soil cross-section, left: moist soil with air spaces, white healthy roots, a green brinjal plant (tick);
              right: water standing on top, soil full of water and no air, brown rotting roots, a yellow drooping
              plant (cross). No words.
Fact (TNAU / FAO): roots need oxygen from air spaces in the soil; waterlogging fills them with water, roots suffocate
and rot, leaves yellow and wilt. Water by checking the soil moisture (finger test) and the crop's stage.
"""
import io
import json
import math
import subprocess
import sys
from pathlib import Path

import cairosvg
import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bugs import brinjal, leaf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
W, H = 1080, 1920


def svg_rgba(body, w=W, h=H):
    png = cairosvg.svg2png(bytestring=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">{body}</svg>'.encode())
    return np.array(Image.open(io.BytesIO(png)).convert("RGBA")).astype(np.float32)


def over(rgb, rgba):
    a = rgba[..., 3:4] / 255
    return rgb * (1 - a) + rgba[..., :3] * a


def paste(dst, spr, x, y):
    h, w = spr.shape[:2]
    xs, ys, xe, ye = max(0, int(x)), max(0, int(y)), min(dst.shape[1], int(x) + w), min(dst.shape[0], int(y) + h)
    if xe > xs and ye > ys:
        s = spr[ys - int(y):ye - int(y), xs - int(x):xe - int(x)]
        a = s[..., 3:4] / 255
        dst[ys:ye, xs:xe] = dst[ys:ye, xs:xe] * (1 - a) + s[..., :3] * a
    return dst


def ease(u):
    u = min(max(u, 0), 1)
    return u * u * (3 - 2 * u)


def plate(base, cfg, blur=0, dark=1.0):
    im = np.array(Image.open(base / cfg["bg"]).convert("RGB").resize((W, H), Image.LANCZOS)).astype(np.float32)
    if blur:
        im = cv2.GaussianBlur(im, (0, 0), blur)
    return im * dark


def water_layer(img, mask, hz, t, tint=(120, 105, 85), mix=0.4):
    """Standing water on the ground: mirrors the image above the horizon, rippling, a little muddy."""
    rows = np.arange(H)
    src = np.clip(2 * hz - rows, 0, hz - 1)
    shift = (5 * np.sin(rows * 0.07 + t * 3)).astype(np.int32)
    cols = (np.arange(W)[None, :] + shift[:, None]) % W
    refl = img[src[:, None], cols] * (1 - mix) + np.array(tint) * mix
    m = mask[..., None]
    return img * (1 - m) + refl * m


def blob_mask(blobs, grow=1.0, soft=14):
    m = np.zeros((H, W), np.float32)
    for cx, cy, rx, ry, ang in blobs:
        if grow * rx > 2:
            cv2.ellipse(m, (int(cx), int(cy)), (int(rx * grow), int(ry * grow)), ang, 0, 360, 1, -1)
    return cv2.GaussianBlur(m, (0, 0), soft)


# ---------------------------------------------------------------- valve

def hose_path(pts, col="#2e8b3a", w=34):
    d = "M " + " L ".join(f"{x:.0f},{y:.0f}" for x, y in pts)
    return (f'<path d="{d}" stroke="#14451c" stroke-width="{w + 10}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="{d}" stroke="{col}" stroke-width="{w}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="{d}" stroke="#7fd08a" stroke-width="{w * 0.25:.0f}" fill="none" stroke-linecap="round" opacity="0.5" transform="translate(-6 -8)"/>')


def scene_valve(t, cfg, bg):
    on = cfg.get("on", True)
    turn = ease((t - 0.2) / 0.8)
    rot = 300 * turn if on else 300 * (1 - turn)
    flow = ease((t - 0.7) / 0.4) if on else 1 - ease((t - 0.5) / 0.7)
    g = ['<rect x="380" y="900" width="120" height="1100" fill="#d8dcdf" stroke="#6a6f73" stroke-width="8"/>',
         '<rect x="330" y="860" width="220" height="120" rx="20" fill="#9aa0a5" stroke="#3c4044" stroke-width="8"/>',
         '<rect x="540" y="880" width="240" height="80" fill="#d8dcdf" stroke="#6a6f73" stroke-width="8"/>',
         '<rect x="760" y="860" width="60" height="120" rx="10" fill="#9aa0a5" stroke="#3c4044" stroke-width="7"/>',
         hose_path([(800, 920), (900, 940), (980, 1080), (960, 1300), (860, 1500), (760, 1640)]),
         '<rect x="425" y="700" width="30" height="170" fill="#6a6f73"/>',
         f'<g transform="rotate({rot:.1f} 440 690)"><circle cx="440" cy="690" r="150" fill="none" stroke="#c62828" stroke-width="34"/>'
         + "".join(f'<line x1="440" y1="690" x2="{440 + 140 * math.cos(math.radians(a)):.0f}" y2="{690 + 140 * math.sin(math.radians(a)):.0f}" stroke="#c62828" stroke-width="24"/>' for a in (0, 120, 240))
         + '<circle cx="440" cy="690" r="34" fill="#8e1b1b"/></g>']
    if flow > 0.02:                                                # water gushing from the hose end at the bottom
        rng = np.random.default_rng(int(t * 25))
        for k in range(int(60 * flow)):
            u = rng.uniform(0, 1)
            x = 760 - 40 - 500 * u + rng.normal(0, 12)
            y = 1640 + 260 * u * u - 80 * u + rng.normal(0, 10)
            g.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rng.uniform(6, 16):.0f}" fill="#bfe6ff" opacity="{0.85 * flow:.2f}"/>')
        g.append(f'<path d="M 740,1650 Q 520,1640 330,1900" stroke="#9fd4ff" stroke-width="{70 * flow:.0f}" fill="none" opacity="0.7" stroke-linecap="round"/>')
    if 0.2 < t < 1.0:
        g.append(f'<path d="M 230,560 A 260 260 0 0 1 440,430" stroke="#ffffff" stroke-width="12" fill="none" opacity="0.7" stroke-dasharray="20 14"/>')
    lay = svg_rgba("".join(g))
    return over(bg, lay)


# ---------------------------------------------------------------- flood

class Flood:
    def __init__(self, cfg, base):
        self.cfg = cfg
        self.bg = plate(base, cfg)
        self.hz = int(cfg.get("horizon", 583) * 1.5)
        rng = np.random.default_rng(3)
        self.blobs = [(520, 1450, 380, 170, -3), (300, 1330, 230, 100, 6), (760, 1580, 300, 150, 2), (450, 1650, 330, 140, 0),
                      (180, 1500, 200, 110, 8), (650, 1340, 220, 80, 0)]
        self.drops = [(rng.uniform(0, 1), rng.uniform(-1, 1), rng.uniform(0.6, 1.4)) for _ in range(90)]

    def frame(self, t):
        cfg = self.cfg
        grow = 0.15 + 0.85 * ease(t / cfg.get("spread", 4.0))
        m = blob_mask(self.blobs, grow)
        img = water_layer(self.bg, m * 0.92, self.hz, t)
        g = [hose_path([(1120, 1780), (1000, 1720), (900, 1640), (830, 1560)], w=28),
             '<rect x="790" y="1530" width="60" height="40" rx="8" fill="#c9a227" stroke="#5a4510" stroke-width="5" transform="rotate(30 820 1550)"/>']
        nx, ny = 800, 1535
        for k, (u0, sp, s) in enumerate(self.drops):                   # the jet: an arc of water and spray
            u = (u0 + t * 1.6 * s) % 1
            x = nx - 520 * u + sp * 60 * u
            y = ny - 260 * u + 420 * u * u + sp * 30
            g.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{(5 + 9 * (1 - u)) * s:.0f}" fill="#d8f1ff" opacity="{0.9 - 0.5 * u:.2f}"/>')
        g.append(f'<path d="M {nx},{ny} Q {nx - 260},{ny - 260} {nx - 520},{ny + 160}" stroke="#bfe6ff" stroke-width="30" fill="none" opacity="0.6" stroke-linecap="round"/>')
        for k in range(5):                                             # splash crowns where it lands
            u = (t * 2.2 + k * 0.2) % 1
            x = nx - 500 + 40 * math.sin(k * 2.1)
            g.append(f'<path d="M {x - 50 * u:.0f},{ny + 170} q {-10 * u:.0f},{-70 * u:.0f} {-30 - 30 * u:.0f},{-60 * u:.0f} M {x + 50 * u:.0f},{ny + 170} q {10 * u:.0f},{-70 * u:.0f} {30 + 30 * u:.0f},{-60 * u:.0f}" '
                     f'stroke="#e6f6ff" stroke-width="7" fill="none" opacity="{1 - u:.2f}"/>')
        for k in range(8):
            u = (t * 0.6 + k * 0.137) % 1
            x, y = 220 + (k * 97) % 640, 1330 + (k * 61) % 330
            if m[int(y), int(x)] > 0.5:
                g.append(f'<ellipse cx="{x}" cy="{y}" rx="{10 + 60 * u:.0f}" ry="{4 + 18 * u:.0f}" fill="none" stroke="#e8f0ff" stroke-width="3" opacity="{0.7 * (1 - u):.2f}"/>')
        return over(img, svg_rgba("".join(g)))


# ---------------------------------------------------------------- the daydream

def fruit(x, y, s, ang=0):
    return (f'<g transform="translate({x:.0f} {y:.0f}) rotate({ang:.0f}) scale({s:.3f})">'
            '<path d="M 0,0 C 40,10 46,120 0,150 C -46,120 -40,10 0,0 Z" fill="#5b2a86" stroke="#2a1040" stroke-width="5"/>'
            '<path d="M -10,20 C -18,60 -16,100 -6,120" stroke="#b48ad8" stroke-width="8" fill="none" opacity="0.6" stroke-linecap="round"/>'
            '<path d="M -26,8 L 0,-14 L 26,8 L 12,18 L 0,6 L -12,18 Z" fill="#3f8a2a" stroke="#1d4a12" stroke-width="4"/></g>')


class Grow:
    def __init__(self, cfg, base):
        from acre import bubble_mask
        from place_action import frames_of
        self.bubble = bubble_mask
        self.cfg = cfg
        self.bg = plate(base, cfg)
        self.meta, self.fig = frames_of("laugh")

    def frame(self, t):
        cfg = self.cfg
        u = ease((t - 0.4) / 2.2)
        s = 0.5 + 2.6 * u
        g = ['<defs><radialGradient id="dg" cx="0.5" cy="0.4" r="0.8"><stop offset="0" stop-color="#fffbe0"/>'
             '<stop offset="0.6" stop-color="#bfe8ff"/><stop offset="1" stop-color="#9ad0ff"/></radialGradient></defs>'
             f'<rect width="{W}" height="{H}" fill="url(#dg)"/><rect y="1560" width="{W}" height="360" fill="#5a3a22"/>'
             '<path d="M 0,1560 Q 540,1530 1080,1560" fill="#6b4a2a"/>']
        g.append(brinjal(700, 1600, s, 3, 3 * math.sin(t * 5) * (1 - u)))
        for k, (dx, dy, t0) in enumerate(((-140, -330, 1.6), (120, -430, 1.9), (-90, -560, 2.2), (160, -650, 2.5), (-180, -470, 2.8))):
            p = ease((t - t0) / 0.3)
            if p > 0:
                g.append(fruit(700 + dx * s / 2.6, 1600 + dy * s / 2.6 * 1.25, 0.9 * p + 0.15 * math.sin(math.pi * p), 10 if dx > 0 else -10))
        rng = np.random.default_rng(2)
        for k in range(18):
            x, y, ph = rng.uniform(100, 1000), rng.uniform(200, 1400), rng.uniform(0, 6.3)
            r = 14 + 10 * math.sin(t * 4 + ph)
            g.append(f'<path d="M {x:.0f},{y - r:.0f} L {x + r * 0.25:.0f},{y:.0f} L {x:.0f},{y + r:.0f} L {x - r * 0.25:.0f},{y:.0f} Z '
                     f'M {x - r:.0f},{y:.0f} L {x:.0f},{y + r * 0.25:.0f} L {x + r:.0f},{y:.0f} L {x:.0f},{y - r * 0.25:.0f} Z" fill="#fff6b0"/>')
        d = svg_rgba("".join(g))[..., :3]
        fr = self.fig[int(t * 25) % len(self.fig)]
        hh = cfg.get("fig_h", 900)
        sc = hh / self.meta["fig_h"]
        spr = cv2.resize(fr, (round(fr.shape[1] * sc), round(fr.shape[0] * sc)), interpolation=cv2.INTER_AREA).astype(np.float32)
        paste(d, spr, 250 - self.meta["feet"][0] * sc, 1660 - self.meta["feet"][1] * sc)
        m, flash = self.bubble(t, cfg)
        img = self.bg * (1 - m[..., None]) + d * m[..., None]
        return img + (255 - img) * flash


# ---------------------------------------------------------------- mud close-ups (the owner's 01_front art)

FRONT = ROOT / "assets/2d/up/01_front.png"
CACHE = Path.home() / ".maaran/cache/front_feet_1500_rgba.png"


def front_feet():
    """Feet + veshti crop (x 400..1800, y 1500..3072 of 01_front x2) as RGBA, background removed (cached)."""
    if not CACHE.exists():
        from rembg import new_session, remove
        im = Image.open(FRONT).convert("RGB")
        a = np.array(remove(im, session=new_session("isnet-anime"), only_mask=True)).astype(np.float32)
        a = np.clip((a - 90) * 2.6, 0, 255)
        rgba = np.dstack([np.array(im).astype(np.float32), a])[1500:3072, 400:1800]
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(rgba.astype(np.uint8)).save(CACHE)
    return np.array(Image.open(CACHE)).astype(np.float32)


def mud_svg(top, t, w=W, h=H, seed=1):
    rng = np.random.default_rng(seed)
    pts = " L ".join(f"{x},{top + 10 * math.sin(x * 0.012 + seed) + 6 * math.sin(x * 0.05 + t):.0f}" for x in range(0, w + 40, 40))
    g = (f'<path d="M 0,{h} L {pts} L {w},{h} Z" fill="#5a3b22"/>'
         f'<path d="M 0,{top + 30} L {w},{top + 30}" stroke="#7a5534" stroke-width="18" opacity="0.5"/>')
    for k in range(26):
        x, y = rng.uniform(0, w), rng.uniform(top + 40, h)
        g += f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{rng.uniform(20, 70):.0f}" ry="{rng.uniform(6, 16):.0f}" fill="#8a6440" opacity="0.45"/>'
    for k in range(8):
        x = rng.uniform(0, w)
        g += f'<ellipse cx="{x:.0f}" cy="{top + rng.uniform(10, 60):.0f}" rx="{rng.uniform(30, 90):.0f}" ry="8" fill="#c9d8e6" opacity="0.35"/>'
    return g


def bubbles(t, x0, x1, y, n=6, seed=3):
    rng = np.random.default_rng(seed)
    g = ""
    for k in range(n):
        x, ph, sp = rng.uniform(x0, x1), rng.uniform(0, 1), rng.uniform(0.8, 1.6)
        u = (t * sp + ph) % 1
        g += f'<circle cx="{x:.0f}" cy="{y - 6 * u:.0f}" r="{6 + 22 * u:.0f}" fill="none" stroke="#3a2412" stroke-width="5" opacity="{1 - u:.2f}"/>'
        if u > 0.85:
            g += "".join(f'<circle cx="{x + 30 * math.cos(a) * (u - 0.85) * 6:.0f}" cy="{y - 30 * (u - 0.85) * 6:.0f}" r="5" fill="#4a3018"/>' for a in (0.6, 1.6, 2.6))
    return g


FIELD_BLUR = {}


def field_top(base, cfg, hgt):
    key = (str(base), hgt)
    if key not in FIELD_BLUR:
        im = np.array(Image.open(base / cfg.get("bg", "frames/grown_plate.png")).convert("RGB").resize((W, H), Image.LANCZOS)).astype(np.float32)
        FIELD_BLUR[key] = cv2.GaussianBlur(im[H - hgt - 300:H - 300], (0, 0), 6)
    return FIELD_BLUR[key]


def scene_mud(t, cfg, base):
    feet = front_feet()[:, 100:760]                                   # his right foot (image left) and the hem above it
    sc = 1080 / feet.shape[1]
    lay = cv2.resize(feet, (W, round(feet.shape[0] * sc)), interpolation=cv2.INTER_CUBIC)
    img = np.zeros((H, W, 3), np.float32) + np.array([90, 62, 40])
    img[:1500] = field_top(base, cfg, 1500)
    tug = max(0.0, math.sin(t * 4.2 - 1.2)) * (1 - ease((t - cfg.get("duration", 3) + 0.6) / 0.6)) * 50
    hem = int((2815 - 1500) * sc)
    foot = np.zeros_like(lay)
    foot[hem:] = lay[hem:]
    top_part = lay.copy()
    top_part[hem:, :, 3] = 0
    y0 = 1500 - lay.shape[0] + 60
    paste(img, foot, 0, y0 - tug)
    paste(img, top_part, 0, y0)
    sink = ease(t / 1.2)
    top = 1500 - 60 - 170 * sink                                      # the mud rises over the foot
    img = over(img, svg_rgba(mud_svg(top, t, seed=5) + bubbles(t, 150, 950, top + 20, 8)))
    if tug > 38:                                                      # squelch: mud blobs fly off
        img = over(img, svg_rgba("".join(f'<circle cx="{540 + 300 * math.cos(a):.0f}" cy="{top - 40 - 120 * math.sin(a):.0f}" r="18" fill="#4a3018"/>'
                                         for a in (0.4, 1.0, 1.6, 2.2, 2.7))))
    return img


def slipper_svg(x, y, s=1.0, ang=0):
    """His brown leather slipper (as in the owner's art: thick sole, one broad strap), 3/4 view from above."""
    return (f'<g transform="translate({x} {y}) rotate({ang}) scale({s})">'
            '<path d="M -150,10 C -150,-50 -60,-70 40,-62 C 120,-56 170,-30 170,6 C 170,40 110,58 20,58 C -80,58 -150,50 -150,10 Z" fill="#4a2a14" stroke="#1e0e04" stroke-width="7"/>'
            '<path d="M -134,4 C -134,-40 -60,-54 36,-48 C 108,-44 152,-24 152,4 C 152,30 100,42 22,42 C -70,42 -134,38 -134,4 Z" fill="#a0602e"/>'
            '<path d="M -40,-50 C -30,-110 70,-112 86,-46 L 60,40 C 50,-20 -10,-20 -20,40 Z" fill="#6b3a1a" stroke="#1e0e04" stroke-width="7"/>'
            '<path d="M -18,-70 C 0,-92 52,-92 66,-66" stroke="#9a5a2a" stroke-width="8" fill="none" opacity="0.7"/></g>')


def scene_slipper(t, cfg, base):
    img = np.zeros((H, W, 3), np.float32) + np.array([90, 62, 40])
    img[:800] = field_top(base, cfg, 800)
    img = over(img, svg_rgba(mud_svg(800, t, seed=6)))
    sink = 25 * ease(t / 2.5)
    img = over(img, svg_rgba(slipper_svg(540, 1120 + sink, 2.6, -18)))
    lip = (f'<path d="M 120,{1250 + sink * 0.4:.0f} Q 540,{1250 + sink * 0.6:.0f} 960,{1250 + sink * 0.4:.0f} L 1080,1920 L 0,1920 Z" fill="#5a3b22"/>'
           f'<path d="M 140,{1248 + sink * 0.4:.0f} Q 540,{1246 + sink * 0.6:.0f} 940,{1248 + sink * 0.4:.0f}" stroke="#2e1c0e" stroke-width="10" fill="none"/>'
           + mud_svg(1340, t, seed=8).replace('<path d="M 0,1920', '<path opacity="0" d="M 0,1920') + bubbles(t, 300, 800, 1320, 6, 7))
    return over(img, svg_rgba(lip))


class Wobble:
    def __init__(self, cfg, base):
        from rembg import new_session, remove
        self.cfg = cfg
        self.bg = plate(base, cfg)
        im = Image.open(FRONT).convert("RGB")
        a = np.clip((np.array(remove(im, session=new_session("isnet-anime"), only_mask=True)).astype(np.float32) - 90) * 2.6, 0, 255)
        fig = np.dstack([np.array(im).astype(np.float32), a])
        ys, xs = np.nonzero(a > 30)
        fig = fig[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        h = cfg.get("fig_h", 1500)
        sc = h / fig.shape[0]
        self.fig = cv2.resize(fig, (round(fig.shape[1] * sc), round(h)), interpolation=cv2.INTER_AREA)
        self.fig[..., :3] *= np.array(cfg.get("light", [1, 1, 1]))

    def frame(self, t):
        cfg = self.cfg
        f = self.fig
        fh, fw = f.shape[:2]
        k = 1 - ease((t - 2.0) / 0.6)
        ang = (6 * math.sin(t * 7) * min(1, t / 0.4) + 9 * math.exp(-((t - 1.2) / 0.25) ** 2)) * k   # wobble, then nearly over
        cx, foot = cfg.get("x", 540), cfg.get("ground", 1800)
        M = cv2.getRotationMatrix2D((fw / 2, fh - 40), ang, 1.0)
        pad = 300
        can = np.zeros((fh + pad, fw + 2 * pad, 4), np.float32)
        can[pad:, pad:pad + fw] = f
        M = cv2.getRotationMatrix2D((pad + fw / 2, pad + fh - 40), ang, 1.0)
        r = cv2.warpAffine(can, M, (can.shape[1], can.shape[0]))
        img = paste(self.bg.copy(), r, cx - pad - fw / 2, foot - pad - fh + 40 + 25)
        g = mud_svg(foot - 70, t, seed=9).replace(f'<path d="M 0,{H}', f'<path d="M 0,{H}')
        img = over(img, svg_rgba(f'<g opacity="0.97">{g}</g>' + bubbles(t, cx - 200, cx + 200, foot - 60, 5)))
        if 1.0 < t < 1.6:
            u = (t - 1.0) / 0.6
            img = over(img, svg_rgba("".join(f'<circle cx="{cx + 260 * math.cos(a) * u:.0f}" cy="{foot - 80 - 200 * math.sin(a) * u + 300 * u * u:.0f}" r="{16 * (1 - u) + 4:.0f}" fill="#4a3018"/>'
                                             for a in (0.3, 0.9, 1.5, 2.2, 2.8))))
        return img


# ---------------------------------------------------------------- the lesson: cross-section

def roots(x, y, col, n=7, L=260, seed=1, rot=False):
    rng = np.random.default_rng(seed)
    g = ""
    for k in range(n):
        a = math.pi / 2 + rng.uniform(-0.9, 0.9)
        px, py = x, y
        d = f"M {px},{py}"
        for j in range(5):
            a += rng.uniform(-0.35, 0.35)
            px += math.cos(a) * L / 5
            py += math.sin(a) * L / 5
            d += f" L {px:.0f},{py:.0f}"
        dash = ' stroke-dasharray="18 10"' if rot else ""
        g += f'<path d="{d}" stroke="{col}" stroke-width="{7 if not rot else 6}" fill="none" stroke-linecap="round"{dash}/>'
    return g


def scene_compare(t, cfg):
    g = ['<rect width="1080" height="1920" fill="#bfe6ff"/>']
    surf = 980
    g.append(f'<rect x="0" y="{surf}" width="540" height="940" fill="#6b4226"/>')            # left: moist crumbly soil
    rng = np.random.default_rng(1)
    for _ in range(110):                                                                       # air spaces
        x, y = rng.uniform(10, 530), rng.uniform(surf + 20, 1900)
        g.append(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{rng.uniform(6, 16):.0f}" ry="{rng.uniform(4, 10):.0f}" fill="#c9a37a" opacity="0.8"/>')
    g.append(f'<rect x="540" y="{surf}" width="540" height="940" fill="#3d2a1c"/>')           # right: soggy soil, water on top
    lvl = surf - 90 * ease(t / 1.0)
    g.append(f'<rect x="540" y="{lvl:.0f}" width="540" height="{surf - lvl + 40:.0f}" fill="#7fb8e0" opacity="0.85"/>')
    for k in range(9):
        u = (t * 0.5 + k * 0.11) % 1
        x = 580 + (k * 53) % 460
        y = 1800 - 800 * u
        g.append(f'<circle cx="{x}" cy="{y:.0f}" r="{5 + 4 * (k % 2)}" fill="none" stroke="#9fd0f0" stroke-width="3" opacity="{(1 - u) * 0.8:.2f}"/>')
    g.append(roots(270, surf + 10, "#f5efe0", 9, 300, 2))
    g.append(roots(810, surf + 10, "#7a5a30", 6, 200, 3, rot=True))
    g.append(brinjal(270, surf + 5, 1.6, 4))
    droop = 4 + 3 * math.sin(t * 1.5)
    sick = brinjal(810, surf + 5, 1.35, 5, droop).replace("#4f9a35", "#b8b040").replace("#5aa83c", "#c2a83a").replace("#468c2f", "#a89a38")
    g.append(sick)
    g.append(f'<line x1="540" y1="300" x2="540" y2="1920" stroke="#ffffff" stroke-width="10" stroke-dasharray="30 20"/>')
    p = ease((t - 1.2) / 0.4)
    if p > 0:
        g.append(f'<g transform="translate(270 240) scale({p:.2f})"><circle r="90" fill="#43a047" stroke="#1b5e20" stroke-width="8"/>'
                 '<path d="M -40,0 L -10,32 L 46,-30" stroke="#fff" stroke-width="20" fill="none" stroke-linecap="round" stroke-linejoin="round"/></g>')
        g.append(f'<g transform="translate(810 240) scale({p:.2f})"><circle r="90" fill="#e53935" stroke="#8e1b1b" stroke-width="8"/>'
                 '<path d="M -34,-34 L 34,34 M 34,-34 L -34,34" stroke="#fff" stroke-width="20" stroke-linecap="round"/></g>')
    return svg_rgba("".join(g))[..., :3]


SCENES = {"valve": scene_valve, "compare": scene_compare}


def main():
    out, cfg_path = sys.argv[1], Path(sys.argv[2])
    cfg = json.loads(cfg_path.read_text())
    base = cfg_path.parent
    fps = cfg.get("fps", 25)
    mode = cfg["mode"]
    obj = {"flood": Flood, "grow": Grow, "wobble": Wobble}.get(mode)
    obj = obj(cfg, base) if obj else None
    bg = plate(base, cfg, cfg.get("blur", 10), cfg.get("dark", 0.9)) if (mode == "valve") else None
    cams = cfg.get("camera", [[0, H / 2, H]])
    still = cfg.get("still")
    ff = None if still is not None else subprocess.Popen(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-framerate", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i in ([0] if still is not None else range(round(cfg["duration"] * fps))):
        t = still if still is not None else i / fps
        if obj:
            img = obj.frame(t)
        elif mode == "valve":
            img = scene_valve(t, cfg, bg)
        elif mode in ("mud", "slipper"):
            img = (scene_mud if mode == "mud" else scene_slipper)(t, cfg, base)
        else:
            img = SCENES[mode](t, cfg)
        cy = float(np.interp(t, [c[0] for c in cams], [c[1] for c in cams]))
        vh = float(np.interp(t, [c[0] for c in cams], [c[2] for c in cams]))
        cx = float(np.interp(t, [c[0] for c in cams], [c[3] if len(c) > 3 else W / 2 for c in cams]))
        if vh < H - 0.5:
            vw = vh * W / H
            M = np.float32([[W / vw, 0, -(cx - vw / 2) * W / vw], [0, H / vh, -(cy - vh / 2) * H / vh]])
            img = cv2.warpAffine(np.float32(img), M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        img = np.clip(img, 0, 255).astype(np.uint8)
        if still is not None:
            Image.fromarray(img).save(out)
        else:
            ff.stdin.write(img.tobytes())
    if ff:
        ff.stdin.close()
        ff.wait()
    print("saved", out)


if __name__ == "__main__":
    main()
