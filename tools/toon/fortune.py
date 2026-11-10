"""Get-rich-crop cut-aways (One-Acre Challenge Ep 5 – the crop that promised crores). 1080x1920, no words anywhere.

python tools/toon/fortune.py OUT.mp4 TIMING.json   ("still": t renders one PNG)
    mag:      close-up of the farming magazine: a glossy dragon-fruit cover with money; the page sparkles; with "q": true
              the money greys out and a big red question mark bounces in (no market for it nearby).
    cash:     daydream bubble over cfg "bg": Thatha (library laugh) in a shower of money bundles and coins.
    fill:     the bare field (cfg "bg" plate) – dragon-fruit plants on their concrete posts pop up row by row, back to
              front, until the whole acre is full (golden, dreamy light).
    tractor:  daydream bubble: Thatha (the owner's sitting drawing, frames/sit_rgba.png) on a shiny red tractor coming
              towards the camera through a lush green farm; bounces; the bubble pops at cfg "pop".
    plan:     his notebook: a pencil draws a table of three crops (dragon fruit, brinjal, tomato) against cost (coin
              stacks), market nearby (a lorry: tick / cross) and his soil (a clod: tick / cross); brinjal gets circled.
    sky:      the bare field: storm clouds roll in from the right, the light goes grey, dust and leaves blow past.
    gust:     cfg "bg" frame (f_storm) with its mask: wind – his towel's loose end lifts and flaps, dust and leaves fly.
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
from bugs import brinjal  # noqa: E402

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


def plate(base, cfg, blur=0, dark=1.0, key="bg"):
    im = np.array(Image.open(base / cfg[key]).convert("RGB").resize((W, H), Image.LANCZOS)).astype(np.float32)
    return (cv2.GaussianBlur(im, (0, 0), blur) if blur else im) * dark


def sparkles(t, n=18, seed=1, area=(0, 0, W, H), col="#fff6b0"):
    rng = np.random.default_rng(seed)
    g = ""
    for k in range(n):
        x, y, ph = rng.uniform(area[0], area[2]), rng.uniform(area[1], area[3]), rng.uniform(0, 6.3)
        r = 14 + 10 * math.sin(t * 4 + ph)
        if r > 5:
            g += (f'<path d="M {x:.0f},{y - r:.0f} L {x + r * 0.25:.0f},{y:.0f} L {x:.0f},{y + r:.0f} L {x - r * 0.25:.0f},{y:.0f} Z '
                  f'M {x - r:.0f},{y:.0f} L {x:.0f},{y + r * 0.25:.0f} L {x + r:.0f},{y:.0f} L {x:.0f},{y - r * 0.25:.0f} Z" fill="{col}"/>')
    return g


# ---------------------------------------------------------------- props

def dragon_fruit(x, y, s=1.0, cut=False):
    scales = "".join(f'<path d="M {dx},{dy} q {14 * sx},-18 {30 * sx},-16" stroke="#7cb342" stroke-width="10" fill="none" stroke-linecap="round"/>'
                     for dx, dy, sx in ((-50, -30, -1), (-40, 20, -1), (40, -40, 1), (50, 10, 1), (-10, -62, -1), (12, 50, 1), (-20, 60, -1)))
    return (f'<g transform="translate({x:.0f} {y:.0f}) scale({s:.3f})"><ellipse cx="0" cy="0" rx="62" ry="74" fill="#e91e8c" stroke="#880e4f" stroke-width="6"/>'
            f'{scales}<path d="M -18,-50 q 8,-12 26,-10" stroke="#ff80c4" stroke-width="8" fill="none" opacity="0.7" stroke-linecap="round"/></g>')


def dragon_plant(x, y, s=1.0, fruit=True):
    """A dragon-fruit vine on its concrete post: post, a ring on top, green cactus stems drooping all round."""
    g = (f'<g transform="translate({x:.0f} {y:.0f}) scale({s:.3f})"><ellipse cx="0" cy="4" rx="70" ry="14" fill="#000" opacity="0.2"/>'
         '<rect x="-14" y="-230" width="28" height="234" fill="#b0b0a8" stroke="#5a5a52" stroke-width="4"/>'
         '<ellipse cx="0" cy="-236" rx="60" ry="14" fill="#9e9e96" stroke="#5a5a52" stroke-width="4"/>')
    for k, a in enumerate((-150, -110, -70, -30, 10, 50, 190, 230)):
        ang = math.radians(a)
        ex, ey = 90 * math.cos(ang), -236 + 60 * abs(math.sin(ang)) + 70
        g += f'<path d="M 0,-240 Q {ex * 0.6:.0f},-300 {ex:.0f},{ey:.0f}" stroke="#4e8a2e" stroke-width="18" fill="none" stroke-linecap="round"/>'
        g += f'<path d="M 0,-240 Q {ex * 0.6:.0f},-300 {ex:.0f},{ey:.0f}" stroke="#7cb342" stroke-width="8" fill="none" stroke-linecap="round"/>'
        if fruit and k % 2 == 0:
            g += dragon_fruit(ex, ey + 18, 0.32)
    return g + "</g>"


def bundle(x, y, s=1.0, ang=0):
    return (f'<g transform="translate({x:.0f} {y:.0f}) rotate({ang:.0f}) scale({s:.3f})"><rect x="-70" y="-34" width="140" height="68" rx="6" fill="#9ccc65" stroke="#33691e" stroke-width="5"/>'
            '<rect x="-70" y="-24" width="140" height="10" fill="#c5e1a5"/><rect x="-14" y="-34" width="28" height="68" fill="#ffd54f" stroke="#a67c00" stroke-width="3"/>'
            '<circle cx="-42" cy="4" r="14" fill="none" stroke="#33691e" stroke-width="4"/><circle cx="42" cy="4" r="14" fill="none" stroke="#33691e" stroke-width="4"/></g>')


def coin(x, y, s=1.0, spin=0.0):
    sx = abs(math.cos(spin)) * 0.9 + 0.1
    return (f'<g transform="translate({x:.0f} {y:.0f}) scale({s * sx:.3f} {s:.3f})"><circle r="30" fill="#ffca28" stroke="#a67c00" stroke-width="5"/>'
            '<circle r="20" fill="none" stroke="#ffe082" stroke-width="4"/></g>')


def lorry(x, y, s=1.0):
    return (f'<g transform="translate({x} {y}) scale({s})"><rect x="-70" y="-50" width="90" height="56" rx="6" fill="#1e88e5" stroke="#0d3c73" stroke-width="5"/>'
            '<path d="M 20,-34 L 52,-34 L 70,-10 L 70,6 L 20,6 Z" fill="#ffca28" stroke="#0d3c73" stroke-width="5"/>'
            '<rect x="30" y="-28" width="22" height="14" fill="#bbdefb"/>'
            '<circle cx="-42" cy="10" r="13" fill="#333"/><circle cx="46" cy="10" r="13" fill="#333"/></g>')


def clod(x, y, s=1.0):
    return (f'<g transform="translate({x} {y}) scale({s})"><path d="M -44,10 C -50,-20 -20,-40 4,-34 C 30,-42 52,-14 44,12 C 36,30 -36,32 -44,10 Z" fill="#6b4226" stroke="#2a1608" stroke-width="5"/>'
            '<circle cx="-14" cy="-6" r="6" fill="#8a5a34"/><circle cx="16" cy="6" r="5" fill="#4a2e18"/></g>')


def tick(x, y, s=1.0, p=1.0):
    return f'<path d="M {x - 28 * s},{y} l {20 * s * min(1, p * 2):.0f},{20 * s * min(1, p * 2):.0f} l {44 * s * max(0, p * 2 - 1):.0f},{-50 * s * max(0, p * 2 - 1):.0f}" stroke="#2e7d32" stroke-width="{14 * s:.0f}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'


def cross(x, y, s=1.0, p=1.0):
    a, b = min(1, p * 2), max(0, p * 2 - 1)
    return (f'<path d="M {x - 26 * s},{y - 26 * s} l {52 * s * a:.0f},{52 * s * a:.0f}" stroke="#d32f2f" stroke-width="{14 * s:.0f}" stroke-linecap="round"/>'
            + (f'<path d="M {x + 26 * s},{y - 26 * s} l {-52 * s * b:.0f},{52 * s * b:.0f}" stroke="#d32f2f" stroke-width="{14 * s:.0f}" stroke-linecap="round"/>' if b > 0 else ""))


def tractor(x, y, s=1.0, t=0.0):
    """A shiny red tractor seen from the front, (x, y) = ground centre."""
    sp = t * 8
    tread = "".join(f'<rect x="{-16}" y="{-150 + ((k * 40 + sp * 30) % 300):.0f}" width="32" height="14" fill="#222"/>' for k in range(7))
    return (f'<g transform="translate({x:.0f} {y:.0f}) scale({s:.3f})">'
            '<ellipse cx="0" cy="8" rx="330" ry="34" fill="#000" opacity="0.3"/>'
            f'<g transform="translate(-250 -160)"><rect x="-55" y="-150" width="110" height="310" rx="40" fill="#1d1d1d"/>{tread}</g>'
            f'<g transform="translate(250 -160)"><rect x="-55" y="-150" width="110" height="310" rx="40" fill="#1d1d1d"/>{tread}</g>'
            '<path d="M -290,-330 Q -250,-380 -200,-330 L -200,-300 L -300,-300 Z M 290,-330 Q 250,-380 200,-330 L 200,-300 L 300,-300 Z" fill="#c62828" stroke="#5a0a0a" stroke-width="6"/>'
            '<rect x="-150" y="-330" width="300" height="250" rx="24" fill="#d32f2f" stroke="#5a0a0a" stroke-width="8"/>'
            '<rect x="-112" y="-300" width="224" height="150" rx="12" fill="#2b2b2b"/>'
            + "".join(f'<rect x="-104" y="{-292 + k * 20}" width="208" height="10" rx="4" fill="#5a5a5a"/>' for k in range(7)) +
            '<circle cx="-120" cy="-110" r="28" fill="#fff8d0" stroke="#5a5a5a" stroke-width="6"/><circle cx="120" cy="-110" r="28" fill="#fff8d0" stroke="#5a5a5a" stroke-width="6"/>'
            '<rect x="-150" y="-90" width="300" height="40" rx="10" fill="#9e9e9e" stroke="#424242" stroke-width="6"/>'
            '<g transform="translate(-118 -40)"><rect x="-34" y="-50" width="68" height="100" rx="24" fill="#1d1d1d"/></g>'
            '<g transform="translate(118 -40)"><rect x="-34" y="-50" width="68" height="100" rx="24" fill="#1d1d1d"/></g>'
            '<rect x="150" y="-470" width="20" height="170" fill="#616161"/><ellipse cx="160" cy="-470" rx="16" ry="6" fill="#212121"/>'
            '<path d="M -150,-330 L -120,-370 L 120,-370 L 150,-330 Z" fill="#e53935" stroke="#5a0a0a" stroke-width="6"/>'
            '<path d="M -110,-322 Q -60,-340 -20,-322" stroke="#ff8a80" stroke-width="10" fill="none" opacity="0.8" stroke-linecap="round"/></g>')


# ---------------------------------------------------------------- scenes

def scene_mag(t, cfg, base):
    bg = plate(base, cfg, 14, 0.8)
    s = 1.0 + 0.05 * t
    g = [f'<g transform="translate(540 980) rotate(-4) scale({s:.3f}) translate(-540 -980)">',
         '<rect x="170" y="330" width="740" height="1060" rx="14" fill="#000" opacity="0.25" transform="translate(14 18)"/>',
         '<rect x="170" y="330" width="740" height="1060" rx="14" fill="#fffdf2" stroke="#2a2a2a" stroke-width="8"/>',
         '<rect x="200" y="360" width="680" height="150" fill="#e53935"/><rect x="240" y="395" width="360" height="34" rx="6" fill="#ffffff"/>'
         '<rect x="240" y="445" width="220" height="24" rx="6" fill="#ffd54f"/><circle cx="800" cy="435" r="46" fill="#ffd54f" stroke="#a67c00" stroke-width="6"/>',
         dragon_fruit(500, 820, 2.6), dragon_fruit(720, 960, 1.5),
         '<path d="M 310,1110 l 30,-40 l 30,40 Z" fill="#43a047"/>']
    for k, (x, y, a) in enumerate(((330, 1210, -8), (500, 1230, 6), (420, 1170, -2), (660, 1220, 10))):
        g.append(bundle(x, y, 1.1, a))
    g.append(coin(800, 1180, 1.6, t * 3) + coin(760, 1260, 1.3, t * 3 + 1))
    g.append('<rect x="230" y="1310" width="420" height="22" rx="6" fill="#bdbdbd"/><rect x="230" y="1346" width="300" height="18" rx="6" fill="#d6d6d6"/></g>')
    img = over(bg, svg_rgba("".join(g)))
    if cfg.get("q"):
        u = ease((t - 0.3) / 0.5)
        if u > 0:
            grey = img.mean(axis=2, keepdims=True)
            img = img * (1 - 0.6 * u) + grey * 0.6 * u
            b = 1 + 0.15 * math.sin(math.pi * min(1, (t - 0.3) / 0.5)) + 0.04 * math.sin(t * 6)
            img = over(img, svg_rgba(f'<g transform="translate(540 900) scale({u * b:.3f})">'
                                     '<path d="M -110,-150 C -110,-300 150,-310 150,-150 C 150,-60 30,-50 30,40 L 30,80 L -40,80 L -40,20 C -40,-90 80,-90 80,-150 C 80,-230 -40,-230 -40,-150 Z" '
                                     'fill="#e53935" stroke="#7a0a0a" stroke-width="12"/><circle cx="-5" cy="170" r="48" fill="#e53935" stroke="#7a0a0a" stroke-width="12"/></g>'))
    else:
        img = over(img, svg_rgba(sparkles(t, 14, 3, (180, 340, 900, 1380))))
    return img


class Bubble:
    """Daydream bubble (acre.bubble_mask) over cfg "bg"; subclasses draw the dream."""

    def __init__(self, cfg, base):
        from acre import bubble_mask
        self.bubble = bubble_mask
        self.cfg = cfg
        self.base = base
        self.bg = plate(base, cfg)

    def frame(self, t):
        d = self.dream(t)
        m, flash = self.bubble(t, self.cfg)
        img = self.bg * (1 - m[..., None]) + d * m[..., None]
        return img + (255 - img) * flash


class Cash(Bubble):
    def __init__(self, cfg, base):
        super().__init__(cfg, base)
        from place_action import frames_of
        self.meta, self.fig = frames_of("laugh")

    def dream(self, t):
        g = ['<defs><radialGradient id="dg" cx="0.5" cy="0.45" r="0.75"><stop offset="0" stop-color="#fffbe0"/>'
             '<stop offset="0.6" stop-color="#ffe08a"/><stop offset="1" stop-color="#f6b04a"/></radialGradient></defs>'
             f'<rect width="{W}" height="{H}" fill="url(#dg)"/>']
        rng = np.random.default_rng(5)
        for k in range(26):                                        # the pile round his feet
            x, y = rng.uniform(80, 1000), rng.uniform(1560, 1820)
            g.append(bundle(x, y, rng.uniform(0.8, 1.1), rng.uniform(-25, 25)))
        for k in range(16):                                        # bundles and coins raining
            u = (t * 0.5 + k / 16) % 1
            x = 60 + (k * 131) % 960
            g.append(bundle(x, -100 + 1800 * u, 0.9, (k * 37 + t * 90) % 360) if k % 2 else coin(x, -60 + 1750 * u, 1.1, t * 6 + k))
        g.append(sparkles(t, 22, 7, (40, 120, 1040, 1500), "#ffffff"))
        d = svg_rgba("".join(g))[..., :3]
        fr = self.fig[int(t * 25) % len(self.fig)]
        hh = self.cfg.get("fig_h", 1150)
        sc = hh / self.meta["fig_h"]
        spr = cv2.resize(fr, (round(fr.shape[1] * sc), round(fr.shape[0] * sc)), interpolation=cv2.INTER_AREA).astype(np.float32)
        paste(d, spr, 540 - self.meta["feet"][0] * sc, 1720 - self.meta["feet"][1] * sc)
        front = "".join(bundle(x, 1800 + 30 * math.sin(x), 1.1, (x * 7) % 40 - 20) for x in (200, 420, 640, 860))
        return over(d, svg_rgba(front))


class Fill:
    def __init__(self, cfg, base):
        self.cfg = cfg
        self.bg = plate(base, cfg)
        hz = cfg.get("horizon", 583) * 1.5
        self.spots = []
        rng = np.random.default_rng(2)
        rows = 5
        for r in range(rows):
            u = ((r + 1) / rows) ** 1.7
            y = hz + 40 + (H - hz - 40) * u
            s = 0.2 + 1.05 * u
            step = 300 * s
            x = rng.uniform(0, step)
            while x < W + 60:
                self.spots.append((x, y, s, (rows - r) * 0.33 + rng.uniform(0, 0.2)))
                x += step
        self.spots.sort(key=lambda p: p[1])

    def frame(self, t):
        g = []
        for x, y, s, t0 in self.spots:
            p = ease((t - t0) / 0.35)
            if p > 0:
                b = p + 0.15 * math.sin(math.pi * p)
                g.append(dragon_plant(x, y, s * b, fruit=t > t0 + 0.5))
        img = over(self.bg, svg_rgba("".join(g)))
        warm = np.array([1.08, 1.0, 0.86])
        img = img * warm + 12
        return over(img, svg_rgba(sparkles(t, 20, 9, (0, 200, W, H))))


class Tractor(Bubble):
    def __init__(self, cfg, base):
        super().__init__(cfg, base)
        sit = np.array(Image.open(base / "frames/sit_rgba.png")).astype(np.float32)
        sc = cfg.get("fig_scale", 0.62)
        self.sit = cv2.resize(sit, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)

    def dream(self, t):
        g = ['<defs><linearGradient id="sk" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7cc8ff"/><stop offset="1" stop-color="#e8f7ff"/></linearGradient></defs>',
             f'<rect width="{W}" height="{H}" fill="url(#sk)"/>',
             '<path d="M 0,760 Q 270,640 540,720 Q 800,620 1080,740 L 1080,900 L 0,900 Z" fill="#9ccc65"/>',
             f'<rect y="820" width="{W}" height="{H - 820}" fill="#7cb342"/>']
        for k in range(14):                                         # crop rows rushing towards the camera
            for side in (-1, 1):
                pts = []
                u0 = (k / 14 + t * 0.35) % 1
                for j in range(2):
                    u = u0 + j * 0.04
                    yy = 820 + (H - 820) * u ** 2
                    xx = 540 + side * (160 + 900 * u ** 2)
                    pts.append((xx, yy))
                (x0, y0), (x1, y1) = pts
                g.append(f'<path d="M {x0:.0f},{y0:.0f} L {x1:.0f},{y1:.0f}" stroke="#33691e" stroke-width="{6 + 60 * u0 ** 2:.0f}" stroke-linecap="round"/>')
        g.append('<path d="M 440,820 L 640,820 L 900,1920 L 180,1920 Z" fill="#a1887f"/>')
        g.append(sparkles(t, 14, 4, (0, 100, W, 700), "#ffffff"))
        d = svg_rgba("".join(g))[..., :3]
        bob = 10 * math.sin(t * 9)
        s = 1.2 + 0.25 * ease(t / 3)
        cx, ground = 540, 1720
        sit = self.sit
        sh = sit.shape
        paste(d, sit, cx - sh[1] / 2, ground - 330 * s - sh[0] * 0.62 + bob)        # seated behind the hood
        d = over(d, svg_rgba(tractor(cx, ground + bob * 0.3, s, t)))
        smoke = "".join(f'<circle cx="{cx + 160 * s + 20 * k + 10 * math.sin(t * 3 + k):.0f}" cy="{ground - 480 * s - 60 * k - (t * 80) % 60:.0f}" r="{18 + 10 * k}" fill="#9e9e9e" opacity="{0.5 - 0.08 * k:.2f}"/>' for k in range(5))
        return over(d, svg_rgba(smoke))


def scene_plan(t, cfg, base):
    g = ['<rect width="1080" height="1920" fill="#6d4c33"/>',
         '<g transform="rotate(-3 540 960)"><rect x="90" y="200" width="900" height="1520" rx="18" fill="#fbf8ee" stroke="#8a7a5a" stroke-width="8"/>']
    for k in range(14):
        g.append(f'<line x1="130" y1="{320 + k * 100}" x2="950" y2="{320 + k * 100}" stroke="#9ec3e6" stroke-width="4"/>')
    for k in range(9):
        g.append(f'<circle cx="90" cy="{280 + k * 170}" r="22" fill="none" stroke="#888" stroke-width="8"/>')
    cols = [400, 600, 820]                                          # cost / market / soil
    rows = [620, 980, 1340]
    heads = [f'<g transform="translate({cols[0]} 430)">' + coin(0, 0, 1.2) + coin(18, -16, 1.2) + '</g>',
             f'<g transform="translate({cols[1]} 440)">' + lorry(0, 0, 1.0) + '</g>', f'<g transform="translate({cols[2]} 440)">' + clod(0, 0, 1.1) + '</g>']
    crops = [dragon_fruit(220, rows[0], 0.9), f'<g transform="translate(220 {rows[1] + 110})">{brinjal(0, 0, 0.7, 2)}</g>',
             f'<g transform="translate(220 {rows[2]})"><circle r="52" fill="#e53935" stroke="#7a0a0a" stroke-width="6"/><path d="M -20,-48 l 20,14 l 20,-14" stroke="#2e7d32" stroke-width="10" fill="none"/></g>']
    cost = [5, 2, 2]
    marks = [[None, cross, cross], [None, tick, tick], [None, tick, cross]]
    per, t0 = 0.55, 0.2
    pen = None
    step = 0
    items = []
    for c in range(3):
        items.append(("head", c))
    for r in range(3):
        items.append(("crop", r))
        for c in range(3):
            items.append(("cell", r, c))
    for i, it in enumerate(items):
        u = (t - t0 - i * per * 0.55) / (per * 0.5)
        if u <= 0:
            continue
        p = min(1, u)
        if it[0] == "head":
            c = it[1]
            g.append(f'<g opacity="{p:.2f}">{heads[c]}</g>')
            if p < 1:
                pen = (cols[c] + 40, 450)
        elif it[0] == "crop":
            r = it[1]
            g.append(f'<g opacity="{p:.2f}">{crops[r]}</g>')
            if p < 1:
                pen = (260, rows[r] + 30)
        else:
            r, c = it[1], it[2]
            if c == 0:
                g.append("".join(coin(cols[0], rows[r] + 50 - 22 * k, 1.0) for k in range(int(round(cost[r] * p)))))
                if p < 1:
                    pen = (cols[0] + 30, rows[r] - 20 * cost[r] * p)
            else:
                g.append(marks[r][c](cols[c], rows[r] + 20, 1.6, p))
                if p < 1:
                    pen = (cols[c] + 40, rows[r])
    ring = ease((t - t0 - len(items) * per * 0.55 - 0.1) / 0.5)
    if ring > 0:
        g.append(f'<ellipse cx="540" cy="{rows[1]}" rx="440" ry="150" fill="none" stroke="#2e7d32" stroke-width="12" '
                 f'stroke-dasharray="{2800 * ring:.0f} 3000" transform="rotate(-2 540 {rows[1]})"/>')
        if ring < 1:
            a = 2 * math.pi * ring
            pen = (540 + 440 * math.cos(a), rows[1] + 150 * math.sin(a))
    g.append('</g>')
    if pen:
        x, y = pen
        g.append(f'<g transform="translate({x:.0f} {y:.0f}) rotate(35)"><rect x="-14" y="-420" width="28" height="380" fill="#fbc02d" stroke="#5a4a00" stroke-width="4"/>'
                 '<path d="M -14,-40 L 14,-40 L 0,0 Z" fill="#f2d2a0" stroke="#5a4a00" stroke-width="3"/><path d="M -4,-12 L 4,-12 L 0,0 Z" fill="#333"/>'
                 '<rect x="-14" y="-440" width="28" height="24" fill="#e57373"/></g>')
    return svg_rgba("".join(g))[..., :3]


class Sky:
    def __init__(self, cfg, base):
        from rain import overcast, sky_mask, storm_sky
        self.cfg = cfg
        src = np.array(Image.open(base / cfg["bg"]).convert("RGB").resize((W, H), Image.LANCZOS))
        self.sunny = src.astype(np.float32)
        hz = int(cfg.get("horizon", 583) * 1.5)
        self.mask = sky_mask(src, hz)[..., None]
        self.clouds = storm_sky(2 * W, hz, seed=cfg.get("seed", 8))[..., :3].astype(np.float32)
        self.grey = overcast(src, 1.0).astype(np.float32)
        self.cloud_grey = overcast(self.clouds.astype(np.uint8), 0.15).astype(np.float32)
        self.hz = hz
        self.leaves = [(np.random.default_rng(k).uniform(0, H), np.random.default_rng(k + 50).uniform(0, 1)) for k in range(26)]

    def frame(self, t):
        c = ease(t / self.cfg.get("roll", 3.0))
        off = int((1 - c) * W * 0.9)
        sky = np.zeros_like(self.sunny)
        sky[:self.hz] = self.cloud_grey[:, off:off + W]
        sky[self.hz:] = self.cloud_grey[-1:, off:off + W]
        edge = W - (W + 900) * c
        front = np.clip((np.arange(W, dtype=np.float32) - edge) / 450, 0, 1)
        m = self.mask * front[None, :, None]
        base = self.sunny * (1 - c) + self.grey * c
        img = base * (1 - m) + sky * m
        return over(img, svg_rgba(wind_bits(t, self.leaves, c)))


def wind_bits(t, leaves, amt=1.0):
    g = ""
    for k, (y0, ph) in enumerate(leaves):
        u = (t * (0.7 + ph) + ph) % 1
        x = W + 80 - (W + 200) * u
        y = y0 + 80 * math.sin(u * 9 + k)
        if k % 3 == 0:
            g += f'<path d="M {x:.0f},{y:.0f} l 70,-6" stroke="#d7ccc8" stroke-width="4" opacity="{0.5 * amt:.2f}" stroke-linecap="round"/>'
        else:
            g += (f'<g transform="translate({x:.0f} {y:.0f}) rotate({u * 900 + k * 40:.0f})" opacity="{amt:.2f}">'
                  f'<path d="M -14,0 Q 0,-10 14,0 Q 0,10 -14,0 Z" fill="{"#8d6e3f" if k % 2 else "#7cb342"}"/></g>')
    return g


class Gust:
    """Wind on a frame: the towel's loose end (cfg "towel": polygon in 720 coords, the hanging part) lifts and flaps."""

    def __init__(self, cfg, base):
        self.cfg = cfg
        self.img = plate(base, cfg)
        poly = np.array(cfg["towel"], np.float32) * 1.5
        m = np.zeros((H, W), np.uint8)
        cv2.fillPoly(m, [poly.astype(np.int32)], 1)
        hsv = cv2.cvtColor(np.clip(self.img, 0, 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(int)
        green = (hsv[..., 0] >= 30) & (hsv[..., 0] <= 85) & (hsv[..., 1] > 50)
        stripes = cv2.dilate(green.astype(np.uint8), np.ones((9, 9), np.uint8)) & (hsv[..., 1] < 60) & (hsv[..., 2] > 150)
        m = m & (green | stripes.astype(bool)).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
        self.top = poly[:, 1].min()
        self.bot = poly[:, 1].max()
        self.m = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.5)
        self.filled = cv2.inpaint(np.clip(self.img, 0, 255).astype(np.uint8), cv2.dilate(m, np.ones((7, 7), np.uint8)) * 255, 9,
                                  cv2.INPAINT_TELEA).astype(np.float32)
        self.yy, self.xx = np.mgrid[0:H, 0:W].astype(np.float32)
        rng = np.random.default_rng(3)
        self.leaves = [(rng.uniform(0, H), rng.uniform(0, 1)) for _ in range(30)]

    def frame(self, t):
        cfg = self.cfg
        g = ease(t / 0.5) * (0.8 + 0.2 * math.sin(t * 7))
        w = np.clip((self.yy - self.top) / (self.bot - self.top), 0, 1) ** 1.6       # 0 at the shoulder, 1 at the hem
        dx = (cfg.get('dx', -45) * g - 10 * math.sin(t * 13)) * w                   # blown sideways and up
        dy = (cfg.get('dy', -30) * g + 7 * math.sin(t * 11)) * w
        # move the towel: sample the source where the towel came from (inverse map), only inside its own swept area
        sx, sy = self.xx - dx, self.yy - dy
        moved = cv2.remap(self.img, sx, sy, cv2.INTER_LINEAR)
        mm = cv2.remap(self.m, sx, sy, cv2.INTER_LINEAR)[..., None]
        hole = np.clip(self.m * g * 1.5, 0, 1)[..., None]                            # the towel's old place, painted over
        base = self.img * (1 - hole) + self.filled * hole
        img = base * (1 - mm) + moved * mm
        shake = cfg.get("shake", 4)
        M = np.float32([[1, 0, shake * math.sin(t * 23)], [0, 1, shake * math.cos(t * 19)]])
        img = cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REPLICATE)
        return over(img, svg_rgba(wind_bits(t, self.leaves)))


def main():
    out, cfg_path = sys.argv[1], Path(sys.argv[2])
    cfg = json.loads(cfg_path.read_text())
    base = cfg_path.parent
    cfg["_base"] = str(base)
    fps = cfg.get("fps", 25)
    mode = cfg["mode"]
    obj = {"cash": Cash, "fill": Fill, "tractor": Tractor, "sky": Sky, "gust": Gust}.get(mode)
    obj = obj(cfg, base) if obj else None
    cams = cfg.get("camera", [[0, H / 2, H]])
    still = cfg.get("still")
    ff = None if still is not None else subprocess.Popen(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-framerate", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i in ([0] if still is not None else range(round(cfg["duration"] * fps))):
        t = still if still is not None else i / fps
        img = obj.frame(t) if obj else (scene_mag(t, cfg, base) if mode == "mag" else scene_plan(t, cfg, base))
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
