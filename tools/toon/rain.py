"""Rain (mazhai) – storm sky, wet soil, live rain and scent overlays for talk.py, plus the Doubt Ep 8 cut-aways. 1080x1920.

Usage:
    python tools/toon/rain.py OUT.mp4 TIMING.json          # a cut-away
Frame helpers (make_frames.py): storm_sky(w, h, seed) cloud layer, sky_mask(), overcast(), wet().
talk.py shot options (720x1280 coords):
    "rain":  {"rate": 0.6, "ground": 700}         falling streaks + splash rings on the ground below y = ground
    "scent": {"to": [x, y], "from": [x0, x1, y], "n": 16, "period": 2.8, "span": [t0, t1]}   a glowing stream
             drifting up to his nose (only between t0 and t1 if "span" is given, fading in and out)

TIMING.json: {"mode": "storm" | "drops" | "section", "duration": 4, "fps": 25, "span": [t0, t1],
              "camera": [[t, cy, h], ...]}
storm:   the owner's dry field art (05_field_vertical): dark clouds roll in over the sunny sky, the light goes grey,
         the first drops fall and leave dark wet spots on the red soil. "rain_rate" (default 0.25) sets the rain at
         the end; "soak": 1 also wets the whole field (use a span in the past for a steady rainy field).
drops:   close-up of dry, cracked soil: big drops hit it, splash, and fling up tiny droplets and dust.
section: soil cross-section: Streptomyces filaments (soil bacteria) make geosmin (golden specks) in dry soil; a raindrop
         lands, air bubbles rise through it and burst, and tiny droplets (aerosols) carrying the specks float up and away.
Science: Bear & Thomas, "Nature of argillaceous odour", Nature 201 (1964) – "petrichor"; geosmin is made by soil
actinobacteria such as Streptomyces (Gerber & Lechevalier 1965; Becher et al., Nat. Microbiol. 2020) and people smell
it at a few parts per trillion; Joung & Buie, Nat. Commun. 6 (2015) – drops on porous soil trap air bubbles that burst
into aerosols, which carry soil scent (and microbes) into the air; light rain makes more of them than a downpour.
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

W, H = 1080, 1920
ROOT = Path(__file__).resolve().parents[2]
SCENT = (40, 170, 225)          # BGR golden


def ease(u):
    u = min(max(u, 0), 1)
    return u * u * (3 - 2 * u)


def svg_png(body, w, h, view=None):
    vb = f' viewBox="{view}"' if view else ""
    png = cairosvg.svg2png(bytestring=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}"{vb}>{body}</svg>'.encode())
    return np.array(Image.open(io.BytesIO(png)).convert("RGBA"))


# ---------------------------------------------------------------- frame helpers

def storm_sky(w, h, seed=8):
    """RGBA storm-cloud layer, w x h: rows of lumpy dark clouds, lighter towards the horizon (bottom)."""
    rng = np.random.default_rng(seed)
    g = [f'<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#353e4a"/>'
         f'<stop offset="0.65" stop-color="#58636f"/><stop offset="1" stop-color="#959ea7"/></linearGradient></defs>'
         f'<rect width="{w}" height="{h}" fill="url(#g)"/>']
    rows = [(0.05, "#2c343f", "#3f4955"), (0.24, "#36404c", "#4d5865"), (0.44, "#45505c", "#606b77"),
            (0.63, "#58636f", "#76818b"), (0.82, "#6f7a85", "#8e979f")]
    for fy, dark, light in rows:
        x = rng.uniform(-200, 0)
        while x < w + 100:                                   # one cloud lump = a cluster of circles
            lw = rng.uniform(220, 420)
            cy = fy * h + rng.uniform(-0.03, 0.03) * h
            puffs = []
            for _ in range(int(lw / 32)):
                px = x + rng.uniform(0, lw)
                r = rng.uniform(38, 80) * (1 - abs(px - x - lw / 2) / lw)
                puffs.append((px, cy - rng.uniform(0, 0.6) * r, max(r, 22)))
            g += [f'<circle cx="{px:.0f}" cy="{py - 7:.0f}" r="{r:.0f}" fill="{light}"/>' for px, py, r in puffs]
            g += [f'<circle cx="{px:.0f}" cy="{py:.0f}" r="{r:.0f}" fill="{dark}"/>' for px, py, r in puffs]
            g.append(f'<rect x="{x:.0f}" y="{cy:.0f}" width="{lw:.0f}" height="{0.1 * h:.0f}" fill="{dark}"/>')
            x += lw * rng.uniform(0.55, 0.8)
    img = svg_png("".join(g), w, h)
    img[..., :3] = cv2.GaussianBlur(img[..., :3], (0, 0), 2.2)
    return img


def sky_mask(rgb, ymax, protect=None):
    """Soft mask of the sunny sky (blue, white clouds, sun glow) above y = ymax; protect = alpha of Thatha (0..255)."""
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(int)
    hh, ss, vv = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    blue = (hh >= 92) & (hh <= 128) & (ss > 35) & (vv > 120)
    white = (ss < 70) & (vv > 195)
    glow = (hh >= 8) & (hh <= 38) & (ss < 175) & (vv > 205)
    m = (blue | white | glow).astype(np.float32)
    yy = np.arange(rgb.shape[0])[:, None]
    m *= np.clip((ymax - yy) / 40.0, 0, 1)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    m = cv2.GaussianBlur(m, (0, 0), 1.2)
    if protect is not None:
        m *= 1 - cv2.dilate(protect.astype(np.float32) / 255, np.ones((5, 5), np.uint8))
    return np.clip(m, 0, 1)


def overcast(rgb, amount=1.0):
    """Grey, cool, dimmer light (no sun)."""
    x = rgb.astype(np.float32)
    grey = x.mean(axis=2, keepdims=True)
    y = x * (1 - 0.38 * amount) + grey * 0.38 * amount
    y *= 1 - 0.2 * amount
    y += np.array([-6, -2, 8], np.float32) * amount
    return np.clip(y, 0, 255).astype(np.uint8)


def wet(rgb, amount=1.0, protect=None, ytop=0):
    """Darker, richer red soil where it is wet (red/orange ground below ytop)."""
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(int)
    soil = (((hsv[..., 0] <= 22) | (hsv[..., 0] >= 172)) & (hsv[..., 1] > 70)).astype(np.float32)
    soil[:ytop] = 0
    if protect is not None:
        soil *= 1 - protect.astype(np.float32) / 255
    soil = cv2.GaussianBlur(soil, (0, 0), 1.5)[..., None] * amount
    x = rgb.astype(np.float32)
    d = x * np.array([0.66, 0.6, 0.6], np.float32)
    return np.clip(x * (1 - soil) + d * soil, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- live overlays (BGR frames)

def draw_rain(img, t, prm, K=1.5, seed=5):
    """Rain streaks over the whole frame and splash rings on the ground (coords in 720x1280 units * K)."""
    rate = prm.get("rate", 0.6)
    h, w = img.shape[:2]
    ground = prm.get("ground", 700) * K
    rng = np.random.default_rng(seed)
    n = int(170 * rate)
    xs, ph, ln, sp = rng.uniform(-0.1, 1.05, n) * w, rng.uniform(0, 1, n), rng.uniform(30, 64, n) * K, rng.uniform(0.9, 1.15, n)
    lay = img.copy()
    v = 1.35 * h                                            # px per second
    slant = prm.get("wind", 0.12)
    for k in range(n):
        y = ((ph[k] + t * sp[k] * v / h) % 1.15) * h - ln[k]
        x = xs[k] + y * slant
        cv2.line(lay, (int(x), int(y)), (int(x + ln[k] * slant), int(y + ln[k])), (236, 228, 218), max(1, int(1.1 * K)), cv2.LINE_AA)
    cv2.addWeighted(lay, 0.42, img, 0.58, 0, img)
    m = int(46 * rate) if ground < h else 0                  # no splashes when there is no ground in view
    sx, sy = rng.uniform(0, 1, m) * w, ground + rng.uniform(0, 1, m) ** 0.8 * (h - ground)
    per, sph = rng.uniform(0.35, 0.6, m), rng.uniform(0, 1, m)
    lay = img.copy()
    for k in range(m):
        u = ((t / per[k]) + sph[k]) % 1
        if u > 0.35:
            continue
        q = u / 0.35
        sc = 0.6 + 0.8 * (sy[k] - ground) / max(h - ground, 1)        # nearer = bigger
        rx = (3 + 13 * q) * K * sc
        cv2.ellipse(lay, (int(sx[k]), int(sy[k])), (int(rx), max(1, int(rx * 0.32))), 0, 0, 360, (225, 222, 215),
                    max(1, int(1.2 * K)), cv2.LINE_AA)
        for j in (-1, 0, 1):
            dx, dy = j * 6 * q * K * sc, -(10 * q - 9 * q * q) * 2.2 * K * sc
            cv2.circle(lay, (int(sx[k] + dx), int(sy[k] + dy)), max(1, int(1.3 * K * sc)), (235, 232, 226), -1, cv2.LINE_AA)
    a = 0.55
    cv2.addWeighted(lay, a, img, 1 - a, 0, img)


def draw_scent(img, t, prm, K=1.5, seed=9):
    """Soft glowing golden motes rising from the soil in a curving stream to his nose (the smell); they shrink and
    fade as they arrive."""
    tx, ty = np.array(prm["to"], float) * K
    x0, x1, y0 = np.array(prm["from"], float) * K
    n, per = prm.get("n", 16), prm.get("period", 2.8)
    rng = np.random.default_rng(seed)
    sx, ph, wob = rng.uniform(x0, x1, n), rng.uniform(0, 1, n), rng.uniform(0, 6.28, n)
    side = 1 if (x0 + x1) / 2 > tx else -1
    on = 1.0
    if "span" in prm:
        a, b = prm["span"]
        on = min(1.0, max(0.0, (t - a) / 0.5)) * min(1.0, max(0.0, (b - t) / 0.5))
        if on <= 0:
            return
    glow = np.zeros(img.shape[:2], np.float32)
    core = np.zeros(img.shape[:2], np.float32)
    for k in range(n):
        u = ((t / per) + ph[k]) % 1
        e = u * u * (3 - 2 * u)
        bow = math.sin(math.pi * e) * 90 * K * side                    # the stream curves out and back in
        x = sx[k] + (tx - sx[k]) * e + bow + math.sin(t * 2.0 + wob[k]) * 12 * K * (1 - e)
        y = y0 + (ty - y0) * (u ** 0.8)
        fade = min(1, u * 5) * min(1, (1 - u) * 6) * on
        r = (8 - 4 * e) * K
        cv2.circle(glow, (int(x), int(y)), int(r * 2.2), fade, -1, cv2.LINE_AA)
        cv2.circle(core, (int(x), int(y)), int(r * 0.7), fade, -1, cv2.LINE_AA)
    glow = cv2.GaussianBlur(glow, (0, 0), 6 * K)[..., None] * 0.55
    core = cv2.GaussianBlur(core, (0, 0), 1.5)[..., None] * 0.9
    col = np.array(SCENT, np.float32)
    x = img.astype(np.float32)
    x = x + (255 - x) * glow * (col / 255)                            # light, not paint: a warm glow
    x = x * (1 - core) + np.array([170, 235, 255], np.float32) * core
    img[:] = np.clip(x, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- cut-aways

class Storm:
    def __init__(self, cfg):
        src = Image.open(ROOT / "assets/2d/source/05_field_vertical.png").convert("RGB").resize((W, H), Image.LANCZOS)
        self.sunny = np.array(src)
        self.mask = sky_mask(self.sunny, int(0.365 * H))[..., None]
        self.clouds = storm_sky(2 * W, int(0.36 * H), seed=cfg.get("seed", 8))[..., :3].astype(np.float32)
        self.grey = overcast(self.sunny, 1.0)
        rng = np.random.default_rng(4)
        self.spots = [(rng.uniform(0, W), rng.uniform(0.45, 1.0) ** 0.7 * H, rng.uniform(0, 1)) for _ in range(160)]
        self.cfg = cfg

    def frame(self, t):
        span = self.cfg["span"]
        p = (t - span[0]) / (span[1] - span[0])
        c = ease(p / 0.75)                                   # clouds and grey light by 75 %
        off = int((1 - c) * W * 0.9)
        sky = np.zeros_like(self.sunny, np.float32)
        ch = self.clouds.shape[0]
        sky[:ch] = self.clouds[:, off:off + W]
        sky[ch:] = self.clouds[-1:, off:off + W]
        base = self.sunny * (1 - c) + self.grey * c
        edge = W - (W + 900) * c                              # the cloud front rolls in from the right, wide and soft
        front = np.clip((np.arange(W, dtype=np.float32) - edge) / 450, 0, 1)
        m = self.mask * front[None, :, None]
        img = base * (1 - m) + overcast(sky.astype(np.uint8), 0.2) * m
        img = img.astype(np.uint8)
        if self.cfg.get("soak"):
            img = wet(img, self.cfg["soak"], ytop=int(0.37 * H))
        wetp = ease((p - 0.7) / 0.3)                         # the first drops: dark spots on the red soil
        if wetp > 0:
            spot = np.zeros((H, W), np.float32)
            for x, y, s in self.spots:
                if s < wetp:
                    r = (6 + 16 * (y / H) ** 2) * min(1, (wetp - s) * 8)
                    cv2.ellipse(spot, (int(x), int(y)), (int(r * 1.6), int(r * 0.7)), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
            spot = cv2.GaussianBlur(spot, (0, 0), 2)[..., None]
            img = (img * (1 - 0.35 * spot)).astype(np.uint8)
        bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        if wetp > 0:
            draw_rain(bgr, t, {"rate": self.cfg.get("rain_rate", 0.25) * wetp, "ground": 0.45 * 1280}, K=1.5)
        return bgr


def soil_close(seed=3):
    """Dry, cracked red soil seen close up (SVG body, W x H): a dried-mud crack network (Voronoi cells) and grit."""
    rng = np.random.default_rng(seed)
    g = [f'<rect width="{W}" height="{H}" fill="#b8693a"/>']
    sub = cv2.Subdiv2D((-200, -200, W + 400, H + 400))
    for _ in range(85):
        sub.insert((float(rng.uniform(-100, W + 100)), float(rng.uniform(-100, H + 100))))
    cells, _ = sub.getVoronoiFacetList([])
    for c in cells:                                           # each mud plate a slightly different shade
        pts = " ".join(f"{x:.0f},{y:.0f}" for x, y in c)
        g.append(f'<polygon points="{pts}" fill="{rng.choice(["#b8693a", "#c0723f", "#ad6234", "#c77b47"])}" '
                 f'stroke="#5e3018" stroke-width="{rng.uniform(3.5, 6.5):.1f}" stroke-linejoin="round"/>')
    for _ in range(260):
        g.append(f'<circle cx="{rng.uniform(0, W):.0f}" cy="{rng.uniform(0, H):.0f}" r="{rng.uniform(2, 7):.0f}" '
                 f'fill="{rng.choice(["#8f4f29", "#d48c5a", "#9c5830"])}" fill-opacity="0.8"/>')
    return "".join(g)


def drops_scene(t, cfg, base):
    """Drops landing on dry soil: fall, crown splash, tiny droplets and dust flung up, a dark wet patch left behind."""
    p_list = cfg.get("drops", [[0.3, 540, 1150], [1.3, 300, 1400], [1.9, 800, 1300], [2.4, 520, 1600], [2.8, 200, 1050],
                               [3.1, 900, 1700], [3.4, 650, 900]])
    g = [base]
    for t0, x, y in p_list:
        dt = t - t0
        if dt < -0.5:
            continue
        if dt < 0:                                            # falling drop (slight motion stretch)
            yy = y + dt * 3200
            g.append(f'<ellipse cx="{x}" cy="{yy:.0f}" rx="26" ry="40" fill="#cfe6f3" fill-opacity="0.85" stroke="#7fa9c2" stroke-width="3"/>'
                     f'<ellipse cx="{x - 8}" cy="{yy - 12:.0f}" rx="6" ry="10" fill="#ffffff" fill-opacity="0.9"/>')
            continue
        wetr = min(1, dt * 4) * 95
        g.append(f'<ellipse cx="{x}" cy="{y}" rx="{wetr:.0f}" ry="{wetr * 0.55:.0f}" fill="#7a3d1f" fill-opacity="0.75"/>')
        if dt < 0.5:                                          # crown
            q = dt / 0.5
            r = 30 + 70 * q
            g.append(f'<ellipse cx="{x}" cy="{y}" rx="{r:.0f}" ry="{r * 0.35:.0f}" fill="none" stroke="#d8ecf6" '
                     f'stroke-width="{8 * (1 - q) + 2:.1f}" stroke-opacity="{1 - q:.2f}"/>')
        rng = np.random.default_rng(int(x + y))
        for k in range(14):                                   # droplets + dust flung up (ballistic)
            ang = rng.uniform(-2.6, -0.5)
            v = rng.uniform(380, 760)
            dust = k % 3 == 0
            tt = dt * (0.55 if dust else 1.0)
            px = x + math.cos(ang) * v * tt
            py = y + math.sin(ang) * v * tt + 900 * tt * tt * (0.15 if dust else 1)
            life = 1 - dt / (2.2 if dust else 0.9)
            if life <= 0 or (not dust and py > y + 40):
                continue
            if dust:
                g.append(f'<circle cx="{px:.0f}" cy="{py:.0f}" r="{rng.uniform(4, 9):.0f}" fill="#d9a27a" fill-opacity="{0.6 * life:.2f}"/>')
            else:
                g.append(f'<circle cx="{px:.0f}" cy="{py:.0f}" r="{rng.uniform(4, 8):.0f}" fill="#dcefff" fill-opacity="{0.9 * life:.2f}" '
                         f'stroke="#8fb5cc" stroke-width="1.5"/>')
    return "".join(g)


def bacteria(rng, x, y):
    """A small Streptomyces colony: branching filaments."""
    s = []
    for _ in range(5):
        a = rng.uniform(0, 6.28)
        px, py = x, y
        d = f"M {px:.0f},{py:.0f}"
        for _ in range(4):
            a += rng.uniform(-0.6, 0.6)
            px, py = px + math.cos(a) * 26, py + math.sin(a) * 26
            d += f" L {px:.0f},{py:.0f}"
        s.append(f'<path d="{d}" stroke="#4f8a3c" stroke-width="7" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
    return "".join(s)


def section_scene(t, cfg):
    """Cross-section: air above, soil below (surface at y = 1100); geosmin specks, then drop -> bubbles -> aerosols."""
    span = cfg["span"]
    p = (t - span[0]) / (span[1] - span[0])
    SY = 1100
    rng = np.random.default_rng(6)
    g = [f'<defs><linearGradient id="air" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5f6b78"/>'
         f'<stop offset="1" stop-color="#a7b1ba"/></linearGradient></defs>'
         f'<rect width="{W}" height="{SY}" fill="url(#air)"/><rect y="{SY}" width="{W}" height="{H - SY}" fill="#8a4a26"/>']
    for _ in range(170):                                      # soil grains
        g.append(f'<circle cx="{rng.uniform(0, W):.0f}" cy="{rng.uniform(SY + 20, H):.0f}" r="{rng.uniform(10, 30):.0f}" '
                 f'fill="{rng.choice(["#a35a30", "#7a3f1f", "#b86a3c", "#94512b"])}"/>')
    g.append(f'<path d="M 0,{SY} ' + " ".join(f"L {x},{SY + 10 * math.sin(x / 70):.0f}" for x in range(0, W + 40, 40)) +
             f' L {W},{SY - 30} L 0,{SY - 30} Z" fill="url(#air)"/>')
    g.append(f'<path d="M 0,{SY} ' + " ".join(f"L {x},{SY + 10 * math.sin(x / 70):.0f}" for x in range(0, W + 40, 40)) +
             '" stroke="#5a2e15" stroke-width="8" fill="none"/>')
    colonies = [(230, 1330), (560, 1500), (860, 1300), (380, 1700), (760, 1760)]
    for x, y in colonies:
        g.append(bacteria(np.random.default_rng(x), x, y))
    gp = ease(p / 0.3)                                        # 0-30 %: geosmin specks appear around the colonies
    srng = np.random.default_rng(11)
    for k in range(60):
        cx, cy = colonies[k % 5]
        if srng.uniform() < gp:
            g.append(f'<circle cx="{cx + srng.normal(0, 70):.0f}" cy="{cy + srng.normal(0, 60):.0f}" r="10" fill="#e8b33a" stroke="#9a7015" stroke-width="2.5"/>')
        else:
            srng.normal(0, 70), srng.normal(0, 60)
    dp = (p - 0.32) / 0.12                                    # 32-44 %: the raindrop falls
    DX = 540
    if 0 < dp < 1:
        yy = 200 + (SY - 60 - 200) * dp * dp
        g.append(f'<ellipse cx="{DX}" cy="{yy:.0f}" rx="70" ry="95" fill="#cfe6f3" fill-opacity="0.9" stroke="#7fa9c2" stroke-width="4"/>')
    if p >= 0.44:                                             # the drop sits on the soil, flattened
        q = ease((p - 0.44) / 0.06)
        g.append(f'<ellipse cx="{DX}" cy="{SY - 40 * q - 50 * (1 - q):.0f}" rx="{70 + 90 * q:.0f}" ry="{95 - 50 * q:.0f}" '
                 f'fill="#cfe6f3" fill-opacity="0.85" stroke="#7fa9c2" stroke-width="4"/>')
        brng = np.random.default_rng(3)
        for k in range(9):                                    # air bubbles rising through the drop
            st = 0.46 + k * 0.035
            u = (p - st) / 0.08
            if 0 < u < 1:
                g.append(f'<circle cx="{DX - 110 + brng.uniform(0, 220):.0f}" cy="{SY - 10 - 70 * u:.0f}" r="{6 + 6 * u:.0f}" '
                         f'fill="#ffffff" fill-opacity="0.75" stroke="#6f97b0" stroke-width="2"/>')
            else:
                brng.uniform(0, 220)
    arng = np.random.default_rng(21)
    for k in range(26):                                       # aerosols carrying the scent up and to the right
        st = 0.52 + k * 0.016
        u = (p - st) / 0.3
        ax0 = DX - 100 + arng.uniform(0, 200)
        sway = arng.uniform(0, 6.28)
        if u <= 0:
            continue
        x = ax0 + 380 * u * u + 30 * math.sin(u * 6 + sway)
        y = SY - 90 - 1000 * u
        if y < -40:
            continue
        g.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="19" fill="#dcefff" fill-opacity="0.8" stroke="#8fb5cc" stroke-width="2.5"/>'
                 f'<circle cx="{x:.0f}" cy="{y:.0f}" r="8" fill="#e8b33a"/>')
    return "".join(g)


def main():
    out = sys.argv[1]
    cfg = json.loads(Path(sys.argv[2]).read_text())
    fps = cfg.get("fps", 25)
    n = round(cfg["duration"] * fps)
    cams = cfg.get("camera", [[0, H / 2, H]])
    only = cfg.get("still")
    mode = cfg["mode"]
    storm = Storm(cfg) if mode == "storm" else None
    base = soil_close() if mode == "drops" else None
    ff = None if only is not None else subprocess.Popen(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
         "-framerate", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i in ([0] if only is not None else range(n)):
        t = only if only is not None else i / fps
        cy = np.interp(t, [c[0] for c in cams], [c[1] for c in cams])
        h = np.interp(t, [c[0] for c in cams], [c[2] for c in cams])
        w = h * W / H
        if storm:
            img = storm.frame(t)
            x0, y0 = int(W / 2 - w / 2), int(np.clip(cy - h / 2, 0, H - h))
            img = cv2.resize(img[y0:y0 + int(h), max(0, x0):max(0, x0) + int(w)], (W, H), interpolation=cv2.INTER_CUBIC)
        else:
            body = drops_scene(t, cfg, base) if mode == "drops" else section_scene(t, cfg)
            img = cv2.cvtColor(svg_png(body, W, H, f"{W / 2 - w / 2:.1f} {cy - h / 2:.1f} {w:.1f} {h:.1f}"), cv2.COLOR_RGBA2BGR)
        if mode in ("drops", "section"):
            draw_rain(img, t, {"rate": 0.35 if mode == "drops" else 0.2, "ground": 2000}, K=1.5)
        if only is not None:
            cv2.imwrite(out, img)
        else:
            ff.stdin.write(img.tobytes())
    if ff:
        ff.stdin.close()
        ff.wait()
    print("saved", out)


if __name__ == "__main__":
    main()
