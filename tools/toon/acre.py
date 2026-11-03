"""One-Acre Challenge cut-aways (Maran Thatha, new series Ep 1). 1080x1920, drawn in code.

Usage:
    python tools/toon/acre.py OUT.mp4 TIMING.json
TIMING.json: {"mode": ..., "duration": 4, "fps": 25, "camera": [[t, cy, h], ...], ...}
car:     daydream: a cloud-edged dream bubble – a shiny red car, bundles of rupee notes piled up, gold coins
         raining – with Thatha (the action library's "laugh" clip) beside it; at "pop" (s) the bubble bursts
         (shrinks to a point + white flash) and the real dry field ("bg") is left.
heap:    the dry field: a giant compost mound grows as clumps pour onto it; Thatha (library clip) admires it.
tree:    daydream: a money tree – rupee notes for leaves, swaying, notes drifting down – Thatha laughing beside it;
         "pop" as above.
strike:  close-up of cracked, rock-hard soil: the hoe blade comes down and bounces off (dust, chips, sparks) at
         each time in "hits"; the last hit only makes a tiny hole.
seed:    close-up: a groundnut kernel drops into the tiny hole, dry crumbs fall over it, two finger pats.
days:    the seed spot seen low and close while the sky runs through two days (sun across, night, sun again) –
         nothing comes up; the light shadow of a stick sweeps round like a sundial.
section: cross-section under the field: a pale hard crust with cracks, tightly packed dry soil with almost no air or
         water spaces, the dry seed sitting in it; a slow push-in ("camera").
Science (TNAU Agritech, groundnut: soil and sowing; FAO soil-compaction notes): groundnut wants loose, friable,
well-drained soil with moisture at sowing; compacted, crusted dry soil holds little air and water, seeds cannot take
up water to germinate and seedlings struggle to push through the crust. Germination takes several days, not one.
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
from place_action import frames_of  # noqa: E402

W, H = 1080, 1920
ROOT = Path(__file__).resolve().parents[2]
OUT = "#3a1f10"


def ease(u):
    u = min(max(u, 0), 1)
    return u * u * (3 - 2 * u)


def svg_rgba(body, w=W, h=H):
    png = cairosvg.svg2png(bytestring=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">{body}</svg>'.encode())
    return np.array(Image.open(io.BytesIO(png)).convert("RGBA")).astype(np.float32)


def over(rgb, rgba):
    a = rgba[..., 3:4] / 255
    return rgb * (1 - a) + rgba[..., :3] * a


# ---------------------------------------------------------------- dream pieces

def car(x, y, s=1.0, t=0.0):
    """A shiny red hatchback, side view, wheels on (x +- 200 s, y)."""
    g = f'<g transform="translate({x} {y}) scale({s})">'
    g += ('<ellipse cx="0" cy="18" rx="330" ry="26" fill="#000" fill-opacity="0.25"/>'
          '<path d="M -330,-20 Q -335,-120 -250,-130 L -150,-140 Q -90,-250 40,-252 L 150,-250 Q 230,-246 280,-150 '
          'L 330,-130 Q 360,-110 350,-20 Z" fill="#d6242c" stroke="#5a0a0e" stroke-width="10" stroke-linejoin="round"/>'
          '<path d="M -120,-148 Q -70,-232 30,-234 L 60,-234 L 60,-148 Z" fill="#bfe6ff" stroke="#5a0a0e" stroke-width="8"/>'
          '<path d="M 90,-148 L 90,-234 L 145,-232 Q 210,-228 250,-150 Z" fill="#bfe6ff" stroke="#5a0a0e" stroke-width="8"/>'
          '<path d="M -100,-160 L -40,-222" stroke="#ffffff" stroke-width="14" stroke-linecap="round" opacity="0.8"/>'
          '<path d="M -300,-90 L 320,-100" stroke="#ff6b6b" stroke-width="10" opacity="0.7"/>'
          '<rect x="300" y="-110" width="40" height="24" rx="8" fill="#ffe680" stroke="#5a0a0e" stroke-width="5"/>'
          '<rect x="-338" y="-104" width="30" height="22" rx="6" fill="#ff8a3d" stroke="#5a0a0e" stroke-width="5"/>')
    for wx in (-200, 200):
        g += (f'<circle cx="{wx}" cy="-10" r="72" fill="#222" stroke="#000" stroke-width="8"/>'
              f'<circle cx="{wx}" cy="-10" r="34" fill="#c9ced3" stroke="#555" stroke-width="6"/>'
              + "".join(f'<line x1="{wx}" y1="-10" x2="{wx + 30 * math.cos(a + t * 0.5):.0f}" y2="{-10 + 30 * math.sin(a + t * 0.5):.0f}" '
                        f'stroke="#555" stroke-width="5"/>' for a in np.linspace(0, 2 * math.pi, 5)[:-1]))
    sh = (t * 0.6) % 1.6 - 0.3                                # a shine sweeping over the body
    if 0 < sh < 1:
        sx = -330 + 680 * sh
        g += f'<path d="M {sx:.0f},-130 L {sx + 40:.0f},-130 L {sx - 10:.0f},-30 L {sx - 50:.0f},-30 Z" fill="#ffffff" opacity="0.35"/>'
    return g + "</g>"


def note(x, y, ang, s=1.0):
    """A rupee note (green-grey with a darker band and a round watermark – no numbers/text)."""
    return (f'<g transform="translate({x:.0f} {y:.0f}) rotate({ang:.0f}) scale({s:.2f})">'
            f'<rect x="-60" y="-30" width="120" height="60" rx="5" fill="#9fd48c" stroke="#3f6b33" stroke-width="4"/>'
            f'<rect x="-48" y="-20" width="20" height="40" fill="#7fbf6c"/>'
            f'<circle cx="22" cy="0" r="16" fill="none" stroke="#3f6b33" stroke-width="4"/></g>')


def bundle(x, y, s=1.0):
    return (f'<g transform="translate({x} {y}) scale({s})">'
            + "".join(f'<rect x="-75" y="{-40 - k * 9}" width="150" height="60" rx="6" fill="#9fd48c" stroke="#3f6b33" stroke-width="4"/>'
                      for k in range(4)) +
            '<rect x="-14" y="-76" width="28" height="64" fill="#f2d16b" stroke="#8a6d12" stroke-width="4"/></g>')


def coin(x, y, s=1.0, spin=0.0):
    k = abs(math.cos(spin))
    return (f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{30 * s * max(0.15, k):.0f}" ry="{30 * s:.0f}" fill="#f5c542" stroke="#9a7212" '
            f'stroke-width="5"/>' + (f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{17 * s * k:.0f}" ry="{17 * s:.0f}" fill="none" '
                                    f'stroke="#c9961e" stroke-width="4"/>' if k > 0.35 else ""))


def money_tree(x, base, t):
    rng = np.random.default_rng(3)
    g = (f'<path d="M {x - 50},{base} Q {x - 30},{base - 300} {x - 60},{base - 520} L {x + 60},{base - 520} Q {x + 30},{base - 300} '
         f'{x + 50},{base} Z" fill="#8a5a2b" stroke="{OUT}" stroke-width="8"/>'
         f'<ellipse cx="{x}" cy="{base - 700}" rx="380" ry="300" fill="#3f8f3a" stroke="#1f4d1c" stroke-width="10"/>')
    for k in range(70):                                       # notes on the branches, swaying
        a, r = rng.uniform(0, 2 * math.pi), math.sqrt(rng.uniform(0, 1))
        nx, ny = x + math.cos(a) * 330 * r, base - 700 + math.sin(a) * 250 * r
        g += note(nx + 6 * math.sin(t * 2 + k), ny, rng.uniform(-40, 40) + 8 * math.sin(t * 2.4 + k), 0.75)
    for k in range(6):                                        # notes drifting down
        u = (t * 0.35 + k / 6) % 1
        g += note(x - 300 + k * 110 + 60 * math.sin(u * 7 + k), base - 520 + 700 * u, 30 * math.sin(u * 9 + k), 0.7)
    return g


def dream_bg(t, kind):
    sky = ('<defs><radialGradient id="dg" cx="0.5" cy="0.45" r="0.7"><stop offset="0" stop-color="#fff6d6"/>'
           '<stop offset="0.6" stop-color="#ffd9a8"/><stop offset="1" stop-color="#f7a8c4"/></radialGradient></defs>'
           f'<rect width="{W}" height="{H}" fill="url(#dg)"/>'
           f'<rect y="1450" width="{W}" height="470" fill="#9be07e"/><path d="M 0,1450 Q 540,1390 1080,1450" fill="#b6ec98"/>')
    rng = np.random.default_rng(1)
    for k in range(26):                                       # sparkles
        sx, sy, ph = rng.uniform(0, W), rng.uniform(80, 1350), rng.uniform(0, 6.28)
        r = 10 + 8 * math.sin(t * 4 + ph)
        sky += (f'<path d="M {sx},{sy - r} L {sx + r * 0.25},{sy} L {sx},{sy + r} L {sx - r * 0.25},{sy} Z M {sx - r},{sy} L {sx},{sy + r * 0.25} '
                f'L {sx + r},{sy} L {sx},{sy - r * 0.25} Z" fill="#ffffff" opacity="{0.5 + 0.4 * math.sin(t * 3 + ph):.2f}"/>')
    if kind == "car":
        sky += car(650, 1500, 0.95, t)
        for k, (bx, by) in enumerate(((150, 1560), (250, 1600), (190, 1500), (900, 1580), (980, 1620), (940, 1520))):
            sky += bundle(bx, by, 0.9)
        for k in range(14):                                   # coins raining
            u = (t * 0.45 + k / 14) % 1
            sky += coin(80 + (k * 73) % 920, -60 + 1700 * u, 0.9, t * 6 + k)
    else:
        sky += money_tree(700, 1520, t)
    return sky


def bubble_mask(t, cfg):
    """Cloud-edged dream bubble: grows in at the start, bursts at "pop"."""
    pop = cfg.get("pop", cfg["duration"] - 0.5)
    grow = ease(t / 0.4)
    burst = ease((t - pop) / 0.25)
    r = 1250 * grow * (1 - burst)
    m = np.zeros((H, W), np.float32)
    if r > 2:
        cx, cy = W / 2, H * 0.47
        cv2.circle(m, (int(cx), int(cy)), int(r), 1.0, -1, cv2.LINE_AA)
        for k in range(14):                                   # puffy cloud edge
            a = 2 * math.pi * k / 14 + 0.3 * math.sin(t)
            cv2.circle(m, (int(cx + math.cos(a) * r), int(cy + math.sin(a) * r * 1.05)), int(r * 0.22), 1.0, -1, cv2.LINE_AA)
        m = cv2.GaussianBlur(m, (0, 0), 6)
    flash = max(0.0, 1 - abs(t - pop - 0.22) / 0.12) if t > pop else 0.0
    return m, flash


class Dream:
    def __init__(self, cfg, base):
        self.cfg = cfg
        self.bg = np.array(Image.open(base / cfg["bg"]).convert("RGB").resize((W, H), Image.LANCZOS)).astype(np.float32)
        self.meta, self.fig = frames_of(cfg.get("action", "laugh"))

    def frame(self, t):
        cfg = self.cfg
        d = svg_rgba(dream_bg(t, cfg["mode"]))[..., :3]
        fr = self.fig[int(t * 25) % len(self.fig)]            # Thatha laughing beside his dream
        x, y, h = cfg.get("fig", [260, 1660, 980] if cfg["mode"] == "car" else [260, 1650, 1000])
        sc = h / self.meta["fig_h"]
        spr = cv2.resize(fr, (round(fr.shape[1] * sc), round(fr.shape[0] * sc)), interpolation=cv2.INTER_AREA).astype(np.float32)
        ax, ay = self.meta["feet"][0] * sc, self.meta["feet"][1] * sc
        x0, y0 = int(x - ax), int(y - ay)
        xs, ys, xe, ye = max(0, x0), max(0, y0), min(W, x0 + spr.shape[1]), min(H, y0 + spr.shape[0])
        s = spr[ys - y0:ye - y0, xs - x0:xe - x0]
        a = s[..., 3:4] / 255
        d[ys:ye, xs:xe] = d[ys:ye, xs:xe] * (1 - a) + s[..., :3] * a
        m, flash = bubble_mask(t, cfg)
        img = self.bg * (1 - m[..., None]) + d * m[..., None]
        img = img + (255 - img) * flash
        return img


def mound(cx, base, w, h, seed=3):
    """A huge rounded heap of dark compost: smooth dome, lumpy edge, lit from the upper left, crumbs, straw bits,
    steam wisps on top (fresh compost is warm)."""
    rng = np.random.default_rng(seed)
    pts = []
    for k in range(41):
        u = k / 40
        x = cx - w / 2 + w * u
        y = base - h * (1 - (2 * u - 1) ** 2) ** 0.55 + rng.normal(0, 3)
        pts.append((x, y))
    d = f"M {pts[0][0]:.0f},{base + 6} " + " ".join(f"L {x:.0f},{y:.0f}" for x, y in pts) + f" L {pts[-1][0]:.0f},{base + 6} Z"
    g = [f'<ellipse cx="{cx}" cy="{base + 4}" rx="{w * 0.58:.0f}" ry="{h * 0.08:.0f}" fill="#2a1408" fill-opacity="0.4"/>',
         f'<defs><radialGradient id="mg" cx="0.35" cy="0.25" r="0.85"><stop offset="0" stop-color="#7a5230"/>'
         f'<stop offset="0.55" stop-color="#4a2c18"/><stop offset="1" stop-color="#2a170a"/></radialGradient></defs>'
         f'<clipPath id="m"><path d="{d}"/></clipPath><path d="{d}" fill="url(#mg)" stroke="#1e0f06" stroke-width="5" stroke-linejoin="round"/>',
         '<g clip-path="url(#m)">']
    for _ in range(int(w * h / 500)):                       # crumbs and lumps
        x, y = rng.uniform(cx - w / 2, cx + w / 2), rng.uniform(base - h, base)
        r = rng.uniform(3, 10)
        g.append(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{r:.0f}" ry="{r * 0.7:.0f}" fill="{rng.choice(["#3a2212", "#5e3a20", "#6b4526", "#2e1a0c", "#86603a"])}" fill-opacity="0.85"/>')
    for _ in range(int(w * h / 2500)):                      # straw and leaf bits
        x, y = rng.uniform(cx - w / 2, cx + w / 2), rng.uniform(base - h, base)
        a = rng.uniform(0, 180)
        col = rng.choice(["#c9a24a", "#a8873a", "#8a6a2a", "#6f8a3a"])
        g.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{rng.uniform(10, 22):.0f}" height="3" fill="{col}" transform="rotate({a:.0f} {x:.0f} {y:.0f})"/>')
    g.append('</g>')
    for k in range(3):
        x = cx - 50 + k * 50
        g.append(f'<path d="M {x},{base - h - 6:.0f} q 14,-22 0,-44 q -14,-22 0,-44" stroke="#ffffff" stroke-width="7" fill="none" '
                 f'stroke-opacity="0.55" stroke-linecap="round"/>')
    return "".join(g)


class Heap:
    """heap: the dry field (bg) – a giant compost mound grows as clumps pour down onto it ("grow": [t0, t1]),
    Thatha (action library clip, default "laugh") beside it admiring it."""

    def __init__(self, cfg, base):
        self.cfg = cfg
        self.bg = np.array(Image.open(base / cfg["bg"]).convert("RGB").resize((W, H), Image.LANCZOS)).astype(np.float32)
        self.meta, self.fig = frames_of(cfg.get("action", "laugh"))

    def frame(self, t):
        cfg = self.cfg
        g0, g1 = cfg.get("grow", [0.0, 1.6])
        u = ease((t - g0) / (g1 - g0))
        cx, base, w, h = cfg.get("mound", [690, 1640, 760, 720])
        body = ""
        if u > 0.01:
            body += mound(cx, base, w * (0.45 + 0.55 * u), h * u, seed=6)
        if t < g1 + 0.2:                                       # clumps raining down onto the heap
            rng = np.random.default_rng(9)
            for k in range(18):
                tk = g0 + rng.uniform(0, g1 - g0)
                v = (t - tk) / 0.45
                if 0 <= v <= 1:
                    x = cx + rng.normal(0, w * 0.15)
                    y = -60 + (base - h * u - (-60)) * v * v
                    r = rng.uniform(18, 34)
                    body += f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{r:.0f}" ry="{r * 0.75:.0f}" fill="#3a2212" stroke="#1e0f06" stroke-width="3"/>'
        img = over(self.bg, svg_rgba(body)) if body else self.bg.copy()
        fr = self.fig[int(t * 25) % len(self.fig)]
        x, y, hh = cfg.get("fig", [250, 1690, 1000])
        sc = hh / self.meta["fig_h"]
        spr = cv2.resize(fr, (round(fr.shape[1] * sc), round(fr.shape[0] * sc)), interpolation=cv2.INTER_AREA).astype(np.float32)
        ax, ay = self.meta["feet"][0] * sc, self.meta["feet"][1] * sc
        sh = np.zeros((H, W), np.float32)
        cv2.ellipse(sh, (int(x), int(y)), (int(hh * 0.16), int(hh * 0.022)), 0, 0, 360, 1, -1)
        img *= 1 - 0.38 * cv2.GaussianBlur(sh, (0, 0), hh * 0.01)[..., None]
        x0, y0 = int(x - ax), int(y - ay)
        xs, ys, xe, ye = max(0, x0), max(0, y0), min(W, x0 + spr.shape[1]), min(H, y0 + spr.shape[0])
        s = spr[ys - y0:ye - y0, xs - x0:xe - x0]
        a = s[..., 3:4] / 255
        img[ys:ye, xs:xe] = img[ys:ye, xs:xe] * (1 - a) + s[..., :3] * a
        return img


# ---------------------------------------------------------------- close-ups of the dry ground

def cracked_ground(seed=7, tone=1.0):
    rng = np.random.default_rng(seed)
    g = [f'<rect width="{W}" height="{H}" fill="#3a2414"/>']
    sub = cv2.Subdiv2D((-200, -200, W + 400, H + 400))
    for _ in range(140):
        sub.insert((float(rng.uniform(-100, W + 100)), float(rng.uniform(-100, H + 100))))
    cells, _ = sub.getVoronoiFacetList([])
    for c in cells:
        c = np.array(c)
        ctr = c.mean(axis=0)
        c = ctr + (c - ctr) * 0.93                            # plates shrink apart: dark gaps between them
        pts = " ".join(f"{x + rng.normal(0, 2.5):.0f},{y + rng.normal(0, 2.5):.0f}" for x, y in c)
        g.append(f'<polygon points="{pts}" fill="{rng.choice(["#c29670", "#b3855d", "#c9a07a", "#ad7f58"])}" stroke="#7a5236" '
                 f'stroke-width="3" stroke-linejoin="round"/>')
        hl = " ".join(f"{x:.0f},{y - 4:.0f}" for x, y in (ctr + (c - ctr) * 0.8))
        g.append(f'<polygon points="{hl}" fill="#d9b994" fill-opacity="0.35"/>')
    for _ in range(220):
        g.append(f'<circle cx="{rng.uniform(0, W):.0f}" cy="{rng.uniform(0, H):.0f}" r="{rng.uniform(2, 7):.0f}" '
                 f'fill="{rng.choice(["#8f6a4a", "#d8b48e"])}" fill-opacity="0.7"/>')
    return "".join(g)


def hoe(x, y, ang):
    """The hoe blade (iron) on its handle, blade edge at (x, y)."""
    return (f'<g transform="translate({x:.0f} {y:.0f}) rotate({ang:.1f})">'
            f'<rect x="-22" y="-1400" width="44" height="1250" rx="18" fill="#8a5a2b" stroke="{OUT}" stroke-width="8"/>'
            f'<path d="M -120,-210 L 120,-210 L 140,-10 Q 0,20 -140,-10 Z" fill="#8b949c" stroke="#2c3238" stroke-width="10"/>'
            f'<path d="M -110,-180 L 110,-180" stroke="#c4cbd1" stroke-width="10"/>'
            f'<rect x="-40" y="-260" width="80" height="60" rx="8" fill="#6d757c" stroke="#2c3238" stroke-width="8"/></g>')


def scene_strike(t, cfg):
    hits = cfg.get("hits", [0.6, 1.5, 2.4])
    g = [cracked_ground()]
    y_ground = 1250
    last = hits[-1]
    hole = ease((t - last) / 0.2)
    if hole > 0:                                              # the only result: a tiny hole
        g.append(f'<ellipse cx="540" cy="{y_ground}" rx="{55 * hole:.0f}" ry="{24 * hole:.0f}" fill="#3a2414"/>')
    lift = 1.0
    for h in hits:                                            # hoe comes down fast, bounces back up
        u = t - h
        if -0.35 <= u < 0:
            lift = min(lift, ((-u) / 0.35) ** 1.6)
        elif 0 <= u < 0.4:
            lift = min(lift, 0.35 * math.sin(math.pi * min(1, u / 0.4)) if h != last else 0.0)
    if t > last + 0.4:
        lift = ease((t - last - 0.4) / 0.6) * 0.8
    bx, by = 540 + 40 * lift, y_ground - 20 - 700 * lift
    for h in hits:                                            # dust, chips and a spark at each hit
        v = (t - h) / 0.7
        if 0 <= v < 1:
            rng = np.random.default_rng(int(h * 100))
            for k in range(10):
                a = rng.uniform(-2.8, -0.35)
                sp = rng.uniform(250, 600)
                px = 540 + math.cos(a) * sp * v
                py = y_ground + math.sin(a) * sp * v + 700 * v * v
                g.append(f'<circle cx="{px:.0f}" cy="{py:.0f}" r="{rng.uniform(6, 14):.0f}" fill="#9a6e4a" stroke="#5a3a22" stroke-width="3"/>')
            g.append(f'<ellipse cx="540" cy="{y_ground - 40 - 120 * v:.0f}" rx="{120 + 260 * v:.0f}" ry="{50 + 90 * v:.0f}" '
                     f'fill="#d9b48e" fill-opacity="{0.55 * (1 - v):.2f}"/>')
            if v < 0.25:
                for k in range(6):
                    a = -math.pi * (0.1 + 0.8 * k / 5)
                    g.append(f'<line x1="540" y1="{y_ground - 20}" x2="{540 + math.cos(a) * 160 * (0.4 + v * 3):.0f}" '
                             f'y2="{y_ground - 20 + math.sin(a) * 160 * (0.4 + v * 3):.0f}" stroke="#fff3a0" stroke-width="8" '
                             f'stroke-linecap="round" opacity="{1 - v * 4:.2f}"/>')
    g.append(hoe(bx, by, -8 + 10 * lift))
    return "".join(g)


def kernel(x, y, s=1.0, ang=-20):
    return (f'<g transform="translate({x:.0f} {y:.0f}) rotate({ang:.0f}) scale({s})">'
            f'<ellipse cx="0" cy="0" rx="62" ry="40" fill="#c8566a" stroke="{OUT}" stroke-width="5"/>'
            f'<path d="M -40,-14 Q 0,-30 40,-16" stroke="#e48a9a" stroke-width="7" fill="none" stroke-linecap="round"/>'
            f'<ellipse cx="54" cy="4" rx="11" ry="8" fill="#f2d4b0" stroke="{OUT}" stroke-width="3"/></g>')


def finger_tip(x, y):
    return (f'<path d="M {x - 95},{y - 1100} L {x - 85},{y - 70} Q {x},{y + 35} {x + 85},{y - 70} L {x + 95},{y - 1100} Z" '
            f'fill="#e4894a" stroke="#a95a28" stroke-width="7"/>'
            f'<path d="M {x - 50},{y - 70} Q {x},{y - 45} {x + 50},{y - 70} L {x + 46},{y - 170} Q {x},{y - 152} {x - 46},{y - 170} Z" '
            f'fill="#f4c7a6" stroke="#a95a28" stroke-width="4"/>')


def scene_seed(t, cfg):
    y = 1250
    g = [cracked_ground(), f'<ellipse cx="540" cy="{y}" rx="80" ry="34" fill="#3a2414"/>']
    drop = ease(t / 0.7)
    if t < 0.75:
        g.append(kernel(540, 300 + (y - 330) * drop * drop, 1.6, -20 + 60 * drop))
    else:
        g.append(kernel(540, y - 12, 1.2, 40))
    cover = ease((t - 1.0) / 0.8)
    if cover > 0:                                             # dry crumbs fall over it
        rng = np.random.default_rng(4)
        for k in range(26):
            u = min(1.0, max(0.0, (t - 1.0 - k * 0.02) / 0.4))
            cx, cy = 540 + rng.normal(0, 45), y - 10 + rng.normal(0, 14)
            g.append(f'<ellipse cx="{cx:.0f}" cy="{cy - 300 * (1 - u):.0f}" rx="{rng.uniform(14, 26):.0f}" ry="{rng.uniform(9, 16):.0f}" '
                     f'fill="#b3855d" stroke="#5a3a22" stroke-width="3" opacity="{u:.2f}"/>')
    pat = 0.0
    for p0 in (2.0, 2.5):                                     # two pats with a fingertip
        u = (t - p0) / 0.4
        if 0 <= u <= 1:
            pat = max(pat, math.sin(math.pi * u))
    if pat > 0:                                               # a little puff of dust as he pats it down
        g.append(f'<ellipse cx="540" cy="{y - 30}" rx="{160 * pat:.0f}" ry="{60 * pat:.0f}" fill="#d9b48e" fill-opacity="{0.4 * pat:.2f}"/>')
    return "".join(g)


DAYS_BG = {}


def scene_days_img(t, cfg, base):
    """The dry field (real art) with the light running through two days and nights; a little sown mound up front."""
    if "img" not in DAYS_BG:
        im = Image.open(base / cfg["bg"]).convert("RGB").resize((W, H), Image.LANCZOS)
        DAYS_BG["img"] = np.array(im).astype(np.float32)
        DAYS_BG["mound"] = svg_rgba('<ellipse cx="540" cy="1700" rx="150" ry="40" fill="#8f6a4a" stroke="#5a3a22" stroke-width="6"/>'
                                    '<ellipse cx="520" cy="1690" rx="60" ry="14" fill="#a98463"/>')
    p = t / cfg["duration"] * 2
    day = p % 1
    sun = math.sin(math.pi * min(1, day / 0.7)) if day < 0.7 else 0.0
    dusk = max(0.0, 1 - abs(day - 0.7) / 0.12)
    night = np.array([0.32, 0.38, 0.62], np.float32)
    dayc = np.array([1.0, 1.0, 1.0], np.float32)
    duskc = np.array([1.05, 0.72, 0.5], np.float32)
    mult = night + (dayc - night) * sun
    mult = mult * (1 - dusk) + duskc * dusk
    img = over(DAYS_BG["img"], DAYS_BG["mound"]) * mult
    if sun < 0.3:                                             # stars at night
        rng = np.random.default_rng(2)
        for _ in range(60):
            x, y = int(rng.uniform(0, W)), int(rng.uniform(0, 520))
            img[y:y + 3, x:x + 3] = img[y:y + 3, x:x + 3] * 0.3 + 255 * 0.7 * (1 - sun / 0.3)
    return img


def scene_section(t, cfg):
    rng = np.random.default_rng(12)
    g = [f'<rect width="{W}" height="700" fill="#b9d8ee"/>', f'<rect y="700" width="{W}" height="{H - 700}" fill="#8f6a4a"/>']
    for _ in range(900):                                      # tightly packed dry grains, no gaps
        x, y = rng.uniform(0, W), rng.uniform(760, H)
        r = rng.uniform(16, 34)
        g.append(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{r:.0f}" ry="{r * 0.7:.0f}" fill="{rng.choice(["#9a7354", "#86634a", "#a57d5c", "#7d5c43"])}" '
                 f'stroke="#5a3e2a" stroke-width="2"/>')
    g.append(f'<rect y="690" width="{W}" height="90" fill="#c9a37e" stroke="#5a3a22" stroke-width="8"/>')    # hard crust
    for k in range(9):
        x = 60 + k * 120 + rng.uniform(-20, 20)
        d = f"M {x:.0f},690 L {x + rng.uniform(-15, 15):.0f},740 L {x + rng.uniform(-25, 25):.0f},{760 + rng.uniform(40, 160):.0f}"
        g.append(f'<path d="{d}" stroke="#3a2414" stroke-width="10" fill="none" stroke-linecap="round"/>')
    g.append(kernel(540, 900, 2.0, 15))                       # the dry seed, wrinkled
    g.append('<path d="M 450,885 q 30,-18 60,0 q 30,18 60,0" stroke="#7a2a3a" stroke-width="7" fill="none"/>')
    return "".join(g)


def leaf_bit(x, y, ang, s=1.0, col="#b8892f"):
    return (f'<g transform="translate({x:.0f} {y:.0f}) rotate({ang:.0f}) scale({s:.2f})"><path d="M -40,0 Q 0,-26 40,0 Q 0,26 -40,0 Z" '
            f'fill="{col}" stroke="#6a4a14" stroke-width="4"/><line x1="-36" y1="0" x2="36" y2="0" stroke="#6a4a14" stroke-width="3"/></g>')


def clod(x, y, r, col="#3a2212"):
    return f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{r:.0f}" ry="{r * 0.75:.0f}" fill="{col}" stroke="#1e0f06" stroke-width="3"/>'


def scene_recipe(t, cfg):
    """Thatha's 'secret recipe': compost and dry leaves drop onto the dry patch, then get stirred in a swirl."""
    g = [cracked_ground(11)]
    rng = np.random.default_rng(5)
    cx, cy = 540, 1050
    items = []
    for k in range(30):
        tk = 0.1 + k * 0.07
        kind = "leaf" if k % 3 == 2 else "clod"
        ang0 = rng.uniform(0, 2 * math.pi)
        rad = rng.uniform(20, 300)
        items.append((tk, kind, ang0, rad, rng.uniform(30, 52), rng.uniform(0, 180)))
    stir = ease((t - 2.2) / 0.5)
    spin = max(0.0, t - 2.2) * 3.2
    if stir > 0:                                              # a stirring stick sweeps round
        a = spin
        g.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{260 * stir:.0f}" ry="{170 * stir:.0f}" fill="#4a2c18" fill-opacity="{0.35 * stir:.2f}"/>')
    for tk, kind, a0, rad, r, rot in items:
        v = (t - tk) / 0.35
        if v < 0:
            continue
        a = a0 + spin * (1 - rad / 300)
        x = cx + math.cos(a) * rad * (1 - 0.3 * stir)
        y = cy + math.sin(a) * rad * 0.62 * (1 - 0.3 * stir)
        if v < 1:
            y = -80 + (y + 80) * v * v
        g.append(leaf_bit(x, y, rot + spin * 40, 1.9) if kind == "leaf" else clod(x, y, r))
    if stir > 0:
        a = spin
        sx, sy = cx + math.cos(a) * 140, cy + math.sin(a) * 90
        g.append(f'<line x1="{sx:.0f}" y1="{sy:.0f}" x2="{sx + 120:.0f}" y2="{sy - 1100:.0f}" stroke="#8a5a2b" stroke-width="34" stroke-linecap="round"/>'
                 f'<line x1="{sx:.0f}" y1="{sy:.0f}" x2="{sx + 120:.0f}" y2="{sy - 1100:.0f}" stroke="{OUT}" stroke-width="40" stroke-linecap="round" opacity="0.25"/>')
    return "".join(g)


def scene_spread(t, cfg):
    """The right way: a thin, even layer of mature compost sprinkled over the cracked soil, then worked in – the
    soil turns dark and crumbly, the cracks close."""
    rng = np.random.default_rng(8)
    sprinkle = ease((t - 0.2) / 1.6)
    mix = ease((t - 2.1) / 1.4)
    g = [cracked_ground(13)]
    if mix > 0:                                               # worked-in soil: dark, crumbly, no cracks
        g.append(f'<rect width="{W}" height="{H}" fill="#5a3a22" fill-opacity="{mix:.2f}"/>')
        r2 = np.random.default_rng(3)
        for _ in range(int(500 * mix)):
            x, y, r = r2.uniform(0, W), r2.uniform(0, H), r2.uniform(5, 16)
            g.append(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{r:.0f}" ry="{r * 0.75:.0f}" fill="{r2.choice(["#6b4526", "#3e2614", "#7a5232"])}"/>')
    n = int(900 * sprinkle * (1 - mix))
    for k in range(n):                                        # crumbs of compost, evenly spread
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        r = rng.uniform(4, 9)
        g.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.0f}" fill="{rng.choice(["#2e1a0c", "#3a2212", "#4a2c18"])}"/>')
    if 0 < sprinkle < 1:                                      # falling stream from the top
        for k in range(30):
            x = 120 + (k * 37 + t * 900) % 840
            y = (k * 113 + t * 1600) % 1700
            g.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="6" fill="#2e1a0c"/>')
    if 0 < mix < 1:                                           # a small hand-rake passes over
        x = -200 + 1500 * mix
        g.append(f'<g transform="translate({x:.0f} 1100) rotate(-20)"><rect x="-15" y="-1200" width="30" height="1150" fill="#8a5a2b" stroke="{OUT}" stroke-width="6"/>'
                 f'<rect x="-120" y="-60" width="240" height="30" rx="8" fill="#6d757c" stroke="#2c3238" stroke-width="6"/>'
                 + "".join(f'<rect x="{-110 + k * 44}" y="-34" width="14" height="70" fill="#8b949c" stroke="#2c3238" stroke-width="4"/>' for k in range(6)) + '</g>')
    return "".join(g)


def scene_bug(t, cfg):
    """Cliffhanger: a young groundnut leaf close-up; a little green caterpillar sits on it – it lifts its head and
    looks around (no labels)."""
    g = [f'<defs><radialGradient id="bb" cx="0.5" cy="0.4" r="0.8"><stop offset="0" stop-color="#d9efb0"/>'
         f'<stop offset="1" stop-color="#7fae5a"/></radialGradient></defs><rect width="{W}" height="{H}" fill="url(#bb)"/>']
    g.append(f'<path d="M 540,1950 Q 520,1450 545,930" stroke="#2f5a1a" stroke-width="48" fill="none" stroke-linecap="round"/>'
             f'<path d="M 540,1950 Q 520,1450 545,930" stroke="#4f7d2a" stroke-width="36" fill="none" stroke-linecap="round"/>')
    for (cx, cy, ang, sc) in ((330, 880, -20, 2.6), (765, 860, 18, 2.6), (370, 1380, -35, 2.0), (705, 1360, 30, 2.0)):
        g.append(f'<g transform="translate({cx} {cy}) rotate({ang}) scale({sc})"><path d="M -110,0 Q 0,-70 110,0 Q 0,70 -110,0 Z" '
                 f'fill="#5fa83a" stroke="#2f5a1a" stroke-width="4"/><path d="M -100,0 Q 0,-8 100,0" stroke="#3f7a26" stroke-width="4" fill="none"/>'
                 + "".join(f'<path d="M {-60 + 30 * k},{-4 + k % 2} q 14,-20 26,-30" stroke="#3f7a26" stroke-width="3" fill="none"/>' for k in range(5)) + '</g>')
    # the caterpillar on the top-right leaf (segments, little feet, head that lifts and turns)
    lift = 0.5 + 0.5 * math.sin(t * 2.2)
    look = math.sin(t * 1.3) * 12
    bx, by = 640, 820
    for k in range(7):
        x = bx + k * 46
        y = by - 9 * math.sin(k * 0.9 + t * 4)
        g.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="34" fill="#7cc242" stroke="#2f5a1a" stroke-width="5"/>'
                 f'<circle cx="{x - 9:.0f}" cy="{y - 12:.0f}" r="9" fill="#bfe88a"/>'
                 f'<line x1="{x:.0f}" y1="{y + 28:.0f}" x2="{x:.0f}" y2="{y + 46:.0f}" stroke="#2f5a1a" stroke-width="7" stroke-linecap="round"/>')
    hx, hy = bx - 46, by - 26 - 30 * lift
    g.append(f'<circle cx="{hx:.0f}" cy="{hy:.0f}" r="42" fill="#8fd04e" stroke="#2f5a1a" stroke-width="5"/>'
             f'<circle cx="{hx - 14 + look * 0.4:.0f}" cy="{hy - 6:.0f}" r="13" fill="#fff" stroke="#222" stroke-width="3"/>'
             f'<circle cx="{hx + 14 + look * 0.4:.0f}" cy="{hy - 6:.0f}" r="13" fill="#fff" stroke="#222" stroke-width="3"/>'
             f'<circle cx="{hx - 13 + look * 0.8:.0f}" cy="{hy - 4:.0f}" r="6" fill="#111"/><circle cx="{hx + 15 + look * 0.8:.0f}" cy="{hy - 4:.0f}" r="6" fill="#111"/>'
             f'<path d="M {hx - 14:.0f},{hy - 38:.0f} q -8,-34 -26,-42 M {hx + 14:.0f},{hy - 38:.0f} q 8,-34 26,-42" stroke="#2f5a1a" stroke-width="5" fill="none"/>'
             f'<path d="M {hx - 12:.0f},{hy + 16:.0f} q 12,9 24,0" stroke="#2f5a1a" stroke-width="4" fill="none"/>')
    g.append(f'<path d="M 700,860 q 20,30 40,10 q 10,-10 0,-20" fill="#c9a24a" stroke="#6a4a14" stroke-width="3" opacity="0.9"/>')   # a nibbled edge
    return "".join(g)


SCENES = {"strike": scene_strike, "seed": scene_seed, "section": scene_section, "recipe": scene_recipe,
          "spread": scene_spread, "bug": scene_bug}


def main():
    out = sys.argv[1]
    cfg_path = Path(sys.argv[2])
    cfg = json.loads(cfg_path.read_text())
    fps = cfg.get("fps", 25)
    n = round(cfg["duration"] * fps)
    cams = cfg.get("camera", [[0, H / 2, H]])
    dream = Dream(cfg, cfg_path.parent) if cfg["mode"] in ("car", "tree") else (
        Heap(cfg, cfg_path.parent) if cfg["mode"] == "heap" else None)
    still = cfg.get("still")
    ff = None if still is not None else subprocess.Popen(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-framerate", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i in ([0] if still is not None else range(n)):
        t = still if still is not None else i / fps
        if dream:
            img = dream.frame(t)
        elif cfg["mode"] == "days":
            img = scene_days_img(t, cfg, cfg_path.parent)
        else:
            img = svg_rgba(SCENES[cfg["mode"]](t, cfg))[..., :3]
            if cfg["mode"] == "section" and cfg.get("bg"):     # the real field (blurred) above the cut
                if "sky" not in DAYS_BG:
                    im = np.array(Image.open(cfg_path.parent / cfg["bg"]).convert("RGB").resize((W, H), Image.LANCZOS))
                    DAYS_BG["sky"] = cv2.GaussianBlur(im[1000:1700], (0, 0), 4).astype(np.float32)
                img[:690] = DAYS_BG["sky"][10:700]
        cy = float(np.interp(t, [c[0] for c in cams], [c[1] for c in cams]))
        vh = float(np.interp(t, [c[0] for c in cams], [c[2] for c in cams]))
        if vh < H - 0.5:
            vw = vh * W / H
            M = np.float32([[W / vw, 0, -(W / 2 - vw / 2) * W / vw], [0, H / vh, -(cy - vh / 2) * H / vh]])
            img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
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
