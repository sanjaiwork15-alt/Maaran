"""Diwali decorations and cut-aways (Maran Thatha – Diwali specials). Everything drawn in code over the owner's art.

Frame helpers (720x1280 coords, the owner's 07_home art resized to 720x1280):
    dusk(rgb)            -> the house at dusk: sky replaced by a dusk gradient, the scene graded cooler/darker
    decor_static()       -> SVG: bulb wires along the roof edge, mango-leaf + marigold thoranam over the door, two
                            star lanterns (akash kandil), clay diyas on the verandah edge and the steps, a kolam
    HOME                 -> positions of the animated lights (for talk.py "lights" and draw_lights)
talk.py shot option "lights": {"mask": "frames/f_x_mask.png", "fireworks": true}: bulbs twinkle, diya flames flicker
    with a warm glow, lanterns pulse, far-off fireworks burst in the sky; nothing is drawn where mask > 0 (Thatha).

Cut-aways (python tools/toon/diwali.py OUT.mp4 TIMING.json; 1080x1920):
    dream:    imagination bubble over the dusk courtyard: three gift boxes pop open one by one – a sleek new
              smartphone, a premium suitcase, an air fryer (all unbranded, no logos or text) – sparkles; Thatha
              (action library clip) beside them, beaming; bursts at "pop".
    savings:  top-down close-up of his small tin savings box on his lap (veshti): the lid opens, a few notes and coins;
              the notes are counted over onto the cloth one by one (no loose hand drawn – frames f_old/f_tin show him).
    bike:     his parked roadster's front at the gate (dusk plate blurred): the yellow bag drops onto the handlebar and
              swings, the bell lever flicks twice.
    list:     close-up of a notebook page: a pencil draws a shopping list as pictures (no words): a rice sack,
              vegetables, a sweet box, snacks, an oil tin – each ticked.
    silhouette: wide dusk shot – Thatha cycles right to left along a raised bund as a dark silhouette against the
              glowing sky (his side drawing's outline + pedalling legs + roadster with the bag), village lights on the
              horizon, rockets bursting, all mirrored in the pond.
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
from rain import sky_mask  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
W7, H7 = 720, 1280
BULB = [(60, 60, 255), (255, 214, 10), (40, 220, 90), (255, 90, 200), (70, 170, 255), (255, 140, 30)]   # RGB


def svg_rgba(body, w, h):
    png = cairosvg.svg2png(bytestring=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">{body}</svg>'.encode())
    return np.array(Image.open(io.BytesIO(png)).convert("RGBA")).astype(np.float32)


def over(rgb, rgba):
    a = rgba[..., 3:4] / 255
    return rgb * (1 - a) + rgba[..., :3] * a


# ---------------------------------------------------------------- the decorated house (720x1280)

def _wire(points, sag):
    """Points along hanging wires between consecutive anchors (catenary-ish sag)."""
    out = []
    for (x0, y0), (x1, y1) in zip(points[:-1], points[1:]):
        n = max(2, int(abs(x1 - x0) / 16))
        for k in range(n):
            u = k / n
            out.append((x0 + (x1 - x0) * u, y0 + (y1 - y0) * u + sag * math.sin(math.pi * u)))
    out.append(points[-1])
    return out


ANCHORS = [(68, 552), (100, 556), (305, 556), (522, 556), (615, 556), (652, 552)]
BULBS = _wire(ANCHORS, 16)
DIYAS = [(140, 798), (195, 798), (250, 798), (560, 798), (620, 798), (335, 815), (500, 815), (342, 853), (493, 853),
         (60, 905), (128, 905)]
LANTERNS = [(205, 555, 92), (468, 555, 92)]                  # x, hook y, string length
HOME = {"bulbs": BULBS, "diyas": DIYAS, "lanterns": LANTERNS}


def dusk(rgb, horizon=520):
    m = sky_mask(rgb, horizon)[..., None]
    sky = np.zeros_like(rgb, np.float32)
    yy = np.arange(rgb.shape[0], dtype=np.float32)[:, None, None] / horizon
    top, mid, low = np.array([40, 30, 90]), np.array([150, 70, 120]), np.array([255, 150, 90])
    sky[:] = np.where(yy < 0.6, top + (mid - top) * (yy / 0.6), mid + (low - mid) * np.clip((yy - 0.6) / 0.4, 0, 1))
    rng = np.random.default_rng(3)
    for _ in range(70):
        x, y = int(rng.uniform(0, rgb.shape[1])), int(rng.uniform(0, horizon * 0.5))
        sky[y:y + 2, x:x + 2] = 255
    out = rgb.astype(np.float32) * (1 - m) + sky * m
    out = out * np.array([0.62, 0.58, 0.72]) + np.array([12, 6, 20])      # cool, darker dusk light
    H, W = rgb.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    vig = 1 - 0.35 * np.clip(((xx - W / 2) / (W * 0.7)) ** 2 + ((yy - H * 0.55) / (H * 0.6)) ** 2, 0, 1)
    out = out * vig[..., None]
    return np.clip(out, 0, 255).astype(np.uint8)


def diya(x, y, s=1.0):
    return (f'<g transform="translate({x:.0f} {y:.0f}) scale({s})"><path d="M -14,-4 Q 0,12 14,-4 Z" fill="#b5532a" stroke="#5a2410" stroke-width="2"/>'
            f'<path d="M -14,-4 L 14,-4" stroke="#e08a5c" stroke-width="3"/><path d="M 10,-6 L 18,-11" stroke="#5a2410" stroke-width="2.5"/></g>')


def kolam(cx, cy, r, squash=0.45):
    """A colourful rangoli kolam in perspective: rings of petals and dots."""
    g = [f'<g transform="translate({cx} {cy}) scale(1 {squash})">']
    g.append(f'<circle r="{r}" fill="#f2e8d0" fill-opacity="0.9"/>')
    for k, (rr, col, n) in enumerate(((r * 0.95, "#e53935", 16), (r * 0.72, "#fbc02d", 12), (r * 0.5, "#1e88e5", 8), (r * 0.28, "#43a047", 6))):
        for i in range(n):
            a = 2 * math.pi * i / n
            x, y = math.cos(a) * rr * 0.78, math.sin(a) * rr * 0.78
            g.append(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{rr * 0.22:.1f}" ry="{rr * 0.11:.1f}" fill="{col}" '
                     f'transform="rotate({math.degrees(a):.0f} {x:.1f} {y:.1f})"/>')
    for i in range(24):
        a = 2 * math.pi * i / 24
        g.append(f'<circle cx="{math.cos(a) * r * 1.02:.1f}" cy="{math.sin(a) * r * 1.02:.1f}" r="{r * 0.03:.1f}" fill="#ffffff"/>')
    g.append(f'<circle r="{r * 0.1}" fill="#ff7043"/></g>')
    return "".join(g)


def lantern_body(x, y, s=1.0):
    """Star lantern (akash kandil): an eight-point paper star with a tassel."""
    pts = []
    for k in range(16):
        a = math.pi * k / 8 - math.pi / 2
        r = 34 if k % 2 == 0 else 15
        pts.append(f"{x + math.cos(a) * r * s:.1f},{y + math.sin(a) * r * s:.1f}")
    return (f'<polygon points="{" ".join(pts)}" fill="#ff7a1a" stroke="#8a2a00" stroke-width="2.5"/>'
            f'<circle cx="{x}" cy="{y}" r="{9 * s:.0f}" fill="#ffe08a"/>'
            f'<path d="M {x},{y + 34 * s:.0f} l -6,{30 * s:.0f} M {x},{y + 34 * s:.0f} l 0,{34 * s:.0f} M {x},{y + 34 * s:.0f} l 6,{30 * s:.0f}" '
            f'stroke="#d81b60" stroke-width="2.5"/>')


def decor_static(kolam_at=(440, 990, 120)):
    g = []
    d = "M " + " L ".join(f"{x:.0f},{y:.0f}" for x, y in BULBS)
    g.append(f'<path d="{d}" stroke="#222" stroke-width="2" fill="none"/>')
    for x, y in BULBS:                                       # bulb sockets (the light itself is animated)
        g.append(f'<rect x="{x - 2:.0f}" y="{y:.0f}" width="4" height="5" fill="#333"/>')
    # thoranam over the door: mango leaves + marigolds
    tx0, tx1, ty = 312, 428, 604
    g.append(f'<path d="M {tx0},{ty} Q {(tx0 + tx1) / 2},{ty + 10} {tx1},{ty}" stroke="#6b3d1f" stroke-width="3" fill="none"/>')
    for k in range(9):
        x = tx0 + (tx1 - tx0) * (k + 0.5) / 9
        y = ty + 10 * math.sin(math.pi * (k + 0.5) / 9)
        if k % 2 == 0:
            g.append(f'<path d="M {x:.0f},{y:.0f} q -7,14 0,30 q 7,-16 0,-30 Z" fill="#2e7d32" stroke="#1b5e20" stroke-width="1.5"/>')
        else:
            g.append(f'<circle cx="{x:.0f}" cy="{y + 8:.0f}" r="7" fill="#ff9800" stroke="#e65100" stroke-width="2"/>'
                     f'<circle cx="{x:.0f}" cy="{y + 20:.0f}" r="6" fill="#ffc107" stroke="#ff8f00" stroke-width="2"/>')
    for x, hook, ln in LANTERNS:
        g.append(f'<line x1="{x}" y1="{hook}" x2="{x}" y2="{hook + ln - 34}" stroke="#333" stroke-width="2"/>' + lantern_body(x, hook + ln))
    for x, y in DIYAS:
        g.append(diya(x, y, 1.0 if y < 870 else 1.2))
    if kolam_at:
        g.append(kolam(*kolam_at))
    return "".join(g)


def _glow(img, x, y, r, col, a):
    x0, y0, x1, y1 = int(x - r), int(y - r), int(x + r), int(y + r)
    H, W = img.shape[:2]
    if x1 <= 0 or y1 <= 0 or x0 >= W or y0 >= H:
        return
    xs, ys, xe, ye = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    yy, xx = np.mgrid[ys:ye, xs:xe].astype(np.float32)
    g = np.exp(-(((xx - x) ** 2 + (yy - y) ** 2) / (0.18 * r * r)))[..., None] * a
    roi = img[ys:ye, xs:xe].astype(np.float32)
    img[ys:ye, xs:xe] = np.clip(roi + (np.array(col, np.float32) - roi * 0.3) * g, 0, 255).astype(img.dtype)


_MASKS = {}


def draw_lights(img, t, prm, K=1.5, rgb_order="bgr"):
    """Animated lights on a frame (720-coords * K). img is BGR (talk.py) unless rgb_order == "rgb"."""
    m = None
    if prm.get("mask"):
        key = prm["mask"]
        if key not in _MASKS:
            mk = cv2.imread(key, cv2.IMREAD_GRAYSCALE)
            _MASKS[key] = cv2.resize(mk, (img.shape[1], img.shape[0]))
        m = _MASKS[key]
    sx, sy, sc = prm.get("offset", [0, 0, 1.0])
    rev = rgb_order == "bgr"

    def C(c):
        return c[::-1] if rev else c

    def visible(x, y):
        return m is None or not (0 <= int(y) < m.shape[0] and 0 <= int(x) < m.shape[1]) or m[int(y), int(x)] < 60

    for i, (x, y) in enumerate(BULBS):
        X, Y = (x * sc + sx) * K, (y * sc + sy + 6) * K
        if not visible(X, Y):
            continue
        on = 0.55 + 0.45 * math.sin(t * 3.0 + i * 1.7)
        col = BULB[i % len(BULB)]
        cv2.circle(img, (int(X), int(Y)), max(2, int(3.2 * K * sc)), C(tuple(int(c * (0.6 + 0.4 * on)) for c in col)), -1, cv2.LINE_AA)
        _glow(img, X, Y, 16 * K * sc, C(col), 0.35 * on)
    for i, (x, y) in enumerate(DIYAS):
        s = (1.0 if y < 870 else 1.2) * sc
        X, Y = (x * sc + sx) * K, (y * sc + sy - 9 * s) * K
        if not visible(X, Y + 6 * K):
            continue
        fl = 1 + 0.18 * math.sin(t * 13 + i * 2.3) + 0.1 * math.sin(t * 29 + i)
        h = 11 * K * s * fl
        pts = np.array([[X - 4 * K * s, Y], [X, Y - h], [X + 4 * K * s, Y], [X, Y + 3 * K * s]], np.int32)
        cv2.fillConvexPoly(img, pts, C((255, 170, 30)), cv2.LINE_AA)
        cv2.circle(img, (int(X), int(Y - 2 * K * s)), max(1, int(2 * K * s)), C((255, 245, 200)), -1, cv2.LINE_AA)
        _glow(img, X, Y - 4 * K * s, 34 * K * s, C((255, 160, 60)), 0.45 * fl)
    for i, (x, hook, ln) in enumerate(prm.get("lanterns", LANTERNS)):
        X, Y = (x * sc + sx) * K, ((hook + ln) * sc + sy) * K
        if visible(X, Y):
            _glow(img, X, Y, 60 * K * sc, C((255, 140, 40)), 0.32 + 0.08 * math.sin(t * 2 + i))
    if prm.get("fireworks"):
        for k, (fx, fy, t0) in enumerate(((300, 95, 0.6), (420, 175, 2.3), (255, 205, 4.1), (375, 60, 5.6))):
            u = ((t - t0) % 6.5) / 1.4
            if 0 <= u <= 1:
                X, Y = (fx * sc + sx) * K, (fy * sc + sy) * K
                if not visible(X, Y):
                    continue
                col = BULB[k % len(BULB)]
                for j in range(14):
                    a = 2 * math.pi * j / 14
                    r = 60 * K * sc * math.sqrt(u)
                    px, py = X + math.cos(a) * r, Y + math.sin(a) * r + 25 * K * u * u
                    cv2.circle(img, (int(px), int(py)), max(1, int(2.5 * K * (1 - u) + 1)), C(tuple(int(c * (1 - 0.5 * u)) for c in col)), -1, cv2.LINE_AA)
                _glow(img, X, Y, 70 * K * sc, C(col), 0.25 * (1 - u))


# ================================================================ cut-aways (1080x1920)

W, H = 1080, 1920
def paste(dst, spr, x, y):
    h, w = spr.shape[:2]
    xs, ys, xe, ye = max(0, int(x)), max(0, int(y)), min(dst.shape[1], int(x) + w), min(dst.shape[0], int(y) + h)
    if xe <= xs or ye <= ys:
        return dst
    s = spr[ys - int(y):ye - int(y), xs - int(x):xe - int(x)]
    a = s[..., 3:4] / 255
    dst[ys:ye, xs:xe] = dst[ys:ye, xs:xe] * (1 - a) + s[..., :3] * a
    return dst


def blurred_plate(base, cfg, k=14, dark=0.75):
    im = np.array(Image.open(base / cfg["bg"]).convert("RGB").resize((W, H), Image.LANCZOS))
    return cv2.GaussianBlur(im, (0, 0), k).astype(np.float32) * dark


def ease(u):
    u = min(max(u, 0), 1)
    return u * u * (3 - 2 * u)


def sparkle_svg(t, n=18, seed=1, area=(0, 0, W, H)):
    rng = np.random.default_rng(seed)
    g = ""
    for k in range(n):
        x, y, ph = rng.uniform(area[0], area[2]), rng.uniform(area[1], area[3]), rng.uniform(0, 6.3)
        r = 16 + 12 * math.sin(t * 4 + ph)
        if r > 6:
            g += (f'<path d="M {x:.0f},{y - r:.0f} L {x + r * 0.25:.0f},{y:.0f} L {x:.0f},{y + r:.0f} L {x - r * 0.25:.0f},{y:.0f} Z '
                  f'M {x - r:.0f},{y:.0f} L {x:.0f},{y + r * 0.25:.0f} L {x + r:.0f},{y:.0f} L {x:.0f},{y - r * 0.25:.0f} Z" fill="#fff6b0"/>')
    return g


# ---------------------------------------------------------------- the gifts daydream

def gift_box(x, y, col, lid):
    """A gift box (ribbon) standing on (x, y); lid 0..1 flies off."""
    g = (f'<rect x="{x - 110}" y="{y - 150}" width="220" height="150" rx="10" fill="{col}" stroke="#222" stroke-width="6"/>'
         f'<rect x="{x - 14}" y="{y - 150}" width="28" height="150" fill="#ffd54f" stroke="#222" stroke-width="4"/>')
    lx, ly = x + 160 * lid, y - 170 - 220 * lid
    g += (f'<g transform="rotate({35 * lid:.0f} {lx:.0f} {ly:.0f})" opacity="{1 - 0.7 * ease((lid - 0.6) / 0.4):.2f}">'
          f'<rect x="{lx - 122:.0f}" y="{ly - 22:.0f}" width="244" height="44" rx="10" fill="{col}" stroke="#222" stroke-width="6"/>'
          f'<path d="M {lx:.0f},{ly - 22:.0f} q -50,-55 -75,-8 q 32,16 75,8 q 50,-55 75,-8 q -32,16 -75,8" fill="#ffd54f" stroke="#222" stroke-width="4"/></g>')
    return g


def item_phone(x, y, s=1.0):
    return (f'<g transform="translate({x} {y}) scale({s})"><rect x="-70" y="-140" width="140" height="280" rx="24" fill="#2b2f36" stroke="#111" stroke-width="6"/>'
            f'<rect x="-58" y="-126" width="116" height="252" rx="16" fill="#6aa8ff"/><path d="M -58,40 Q 0,-30 58,30 L 58,126 L -58,126 Z" fill="#9b6bff" opacity="0.85"/>'
            f'<path d="M -40,-112 L 20,-112" stroke="#fff" stroke-width="6" opacity="0.6" stroke-linecap="round"/>'
            f'<rect x="-20" y="-134" width="40" height="8" rx="4" fill="#111"/></g>')


def item_suitcase(x, y, s=1.0):
    return (f'<g transform="translate({x} {y}) scale({s})"><rect x="-100" y="-130" width="200" height="250" rx="24" fill="#1e88e5" stroke="#0d3c73" stroke-width="7"/>'
            + "".join(f'<line x1="{dx}" y1="-122" x2="{dx}" y2="112" stroke="#1565c0" stroke-width="8"/>' for dx in (-45, 0, 45)) +
            f'<rect x="-34" y="-176" width="68" height="50" rx="12" fill="none" stroke="#0d3c73" stroke-width="12"/>'
            f'<circle cx="-72" cy="132" r="14" fill="#333"/><circle cx="72" cy="132" r="14" fill="#333"/></g>')


def item_fryer(x, y, s=1.0):
    return (f'<g transform="translate({x} {y}) scale({s})"><path d="M -100,-140 Q 0,-168 100,-140 L 114,110 Q 0,130 -114,110 Z" fill="#37474f" stroke="#111" stroke-width="7"/>'
            f'<rect x="-80" y="-20" width="160" height="110" rx="18" fill="#263238" stroke="#111" stroke-width="5"/>'
            f'<rect x="-34" y="12" width="68" height="16" rx="8" fill="#90a4ae"/><circle cx="0" cy="-88" r="26" fill="#263238" stroke="#90a4ae" stroke-width="5"/>'
            f'<circle cx="0" cy="-88" r="7" fill="#ff7043"/></g>')


class Dream:
    def __init__(self, cfg, base):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from acre import bubble_mask  # noqa: E402
        from place_action import frames_of  # noqa: E402
        self.bubble = bubble_mask
        self.cfg = cfg
        self.bg = np.array(Image.open(base / cfg["bg"]).convert("RGB").resize((W, H), Image.LANCZOS)).astype(np.float32)
        self.meta, self.fig = frames_of(cfg.get("action", "laugh"))

    def frame(self, t):
        cfg = self.cfg
        g = ('<defs><radialGradient id="dg" cx="0.5" cy="0.4" r="0.75"><stop offset="0" stop-color="#fff2c4"/>'
             '<stop offset="0.6" stop-color="#ffc77a"/><stop offset="1" stop-color="#e86aa0"/></radialGradient></defs>'
             f'<rect width="{W}" height="{H}" fill="url(#dg)"/><rect y="1560" width="{W}" height="360" fill="#7b3f8c"/>'
             f'<path d="M 0,1560 Q 540,1520 1080,1560" fill="#9a56ad"/>' + sparkle_svg(t, 26, 4, (0, 120, W, 1500)))
        boxes = [(575, 1610, "#e53935", item_phone, 0.4), (770, 1610, "#43a047", item_suitcase, 1.6), (965, 1610, "#8e24aa", item_fryer, 2.8)]
        for x, y, col, item, t0 in boxes:
            g += f'<g transform="translate({x} {y}) scale(0.82) translate({-x} {-y})">'
            lid = ease((t - t0) / 0.35)
            rise = ease((t - t0 - 0.2) / 0.5)
            if rise > 0:
                pop = 1 + 0.12 * math.sin(math.pi * min(1, (t - t0 - 0.2) / 0.5))
                g += f'<circle cx="{x}" cy="{y - 330 * rise:.0f}" r="{150 * rise:.0f}" fill="#fffbe0" opacity="{0.55 * rise:.2f}"/>'
                g += item(x, y - 150 - 230 * rise + 70, 1.05 * pop)
            g += gift_box(x, y, col, lid) + "</g>"
        img = svg_rgba(g, W, H)[..., :3]
        fr = self.fig[int(t * 25) % len(self.fig)]
        x, y, hh = cfg.get("fig_x", 250), 1700, cfg.get("fig_h", 900)
        sc = hh / self.meta["fig_h"]
        spr = cv2.resize(fr, (round(fr.shape[1] * sc), round(fr.shape[0] * sc)), interpolation=cv2.INTER_AREA).astype(np.float32)
        paste(img, spr, x - self.meta["feet"][0] * sc, y - self.meta["feet"][1] * sc)
        m, flash = self.bubble(t, cfg)
        out = self.bg * (1 - m[..., None]) + img * m[..., None]
        return out + (255 - out) * flash


# ---------------------------------------------------------------- close-ups (props only, no loose hands)

def coin_svg(x, y, r=26):
    return (f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{r}" ry="{r * 0.8:.0f}" fill="#c9cdd2" stroke="#6d737a" stroke-width="4"/>'
            f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{r * 0.6:.0f}" ry="{r * 0.48:.0f}" fill="none" stroke="#9aa0a6" stroke-width="3"/>')


def note_svg(x, y, ang=0, col="#e3a0b8", s=1.0):
    return (f'<g transform="translate({x:.0f} {y:.0f}) rotate({ang:.1f}) scale({s:.3f})"><rect x="-120" y="-55" width="240" height="110" rx="6" fill="{col}" stroke="#6b4a55" stroke-width="4"/>'
            f'<rect x="-100" y="-38" width="40" height="76" fill="#ffffff" opacity="0.35"/><circle cx="50" cy="0" r="28" fill="none" stroke="#6b4a55" stroke-width="4"/>'
            f'<path d="M -45,-30 L 10,-30 M -45,30 L 10,30" stroke="#6b4a55" stroke-width="3" opacity="0.5"/></g>')


def bag_svg(sway=0.0, s=1.0):
    """The yellow cloth bag hanging from a hook at (0, 0) (its handles loop over a bar there)."""
    return (f'<g transform="rotate({sway:.2f}) scale({s})">'
            '<path d="M -70,110 Q -60,-30 0,-14 Q 60,-30 70,110" stroke="#c99300" stroke-width="16" fill="none"/>'
            '<path d="M -150,100 Q 0,84 150,100 Q 190,320 160,520 Q 0,560 -160,520 Q -190,320 -150,100 Z" fill="#f2c318" stroke="#8a6a00" stroke-width="8"/>'
            '<path d="M -80,110 Q -95,320 -70,510 M 80,110 Q 100,320 75,510" stroke="#c99a00" stroke-width="7" fill="none" opacity="0.7"/>'
            '<path d="M -140,160 Q 0,148 140,160" stroke="#c99a00" stroke-width="7" fill="none"/>'
            '<rect x="50" y="40" width="34" height="80" rx="6" fill="#fbfaf2" stroke="#999" stroke-width="4" transform="rotate(12 67 80)"/></g>')


class Close:
    """savings: top-down on his lap – the tin's lid opens; the notes inside are counted over onto the veshti, one by one.
    bike: his parked roadster's front at the gate; the cloth bag drops onto the handlebar and swings; the bell rings."""

    def __init__(self, cfg, base):
        self.cfg = cfg
        self.base = base
        if cfg["mode"] == "bike":
            self.bg = blurred_plate(base, cfg, k=10, dark=0.85)

    def frame(self, t):
        return self.savings(t) if self.cfg["mode"] == "savings" else self.bike(t)

    def savings(self, t):
        g = ('<rect width="1080" height="1920" fill="#dcd4e4"/>'
             '<path d="M -50,300 Q 400,380 1130,250 M -50,700 Q 500,640 1130,760 M -50,1250 Q 600,1320 1130,1180 M -50,1700 Q 450,1640 1130,1760" '
             'stroke="#b9aecb" stroke-width="26" fill="none" opacity="0.6"/>'
             '<path d="M -50,1560 L 1130,1820" stroke="#56b03a" stroke-width="54"/><path d="M -50,1640 L 1130,1900" stroke="#56b03a" stroke-width="18"/>')
        lid = ease((t - 0.2) / 0.6)
        g += '<ellipse cx="560" cy="1270" rx="380" ry="60" fill="#000" opacity="0.22"/>'
        g += ('<rect x="230" y="760" width="620" height="480" rx="40" fill="#8a2f2f" stroke="#3a1010" stroke-width="10"/>'
              '<rect x="262" y="792" width="556" height="416" rx="26" fill="#5a1d1d"/>')
        for x, y in ((330, 900), (420, 1110), (720, 1130), (760, 880), (330, 1040)):
            g += coin_svg(x, y, 30)
        per, t1, N = 0.6, 1.0, 5
        k_now = int((t - t1) // per) if t > t1 else -1
        done = min(N, max(0, k_now))
        for k in range(N - done - (1 if 0 <= k_now < N else 0)):           # pile still in the tin
            g += note_svg(540 + k * 6, 1000 - k * 8, -8 + k * 4)
        for k in range(done):                                               # counted pile, on the cloth
            g += note_svg(800 + k * 7, 1480 - k * 10, 14 - k * 5, "#d995ad")
        if 0 <= k_now < N:                                                   # the one being counted: lifts, arcs, lands
            u = ease(((t - t1) % per) / (per * 0.85))
            k = N - done - 1
            x0, y0, a0 = 540 + k * 6, 1000 - k * 8, -8 + k * 4
            x1, y1, a1 = 800 + done * 7, 1480 - done * 10, 14 - done * 5
            lift = math.sin(math.pi * u)
            x, y, a = x0 + (x1 - x0) * u, y0 + (y1 - y0) * u - 120 * lift, a0 + (a1 - a0) * u + 18 * lift
            g += note_svg(x, y, a, "#e3a0b8" if u < 0.5 else "#d995ad", 1 + 0.12 * lift)
        e = 1240 - (1240 - 540) * lid                                        # the lid's free edge: closed 1240 -> open 540
        y0, y1 = min(760, e), max(760, e)
        if y1 - y0 > 8:
            inner = e < 760
            g += (f'<rect x="{230 - 10 * (1 - lid):.0f}" y="{y0:.0f}" width="{620 + 20 * (1 - lid):.0f}" height="{y1 - y0:.0f}" rx="{min(40, (y1 - y0) / 3):.0f}" '
                  f'fill="{"#7a2626" if inner else "#a33a3a"}" stroke="#3a1010" stroke-width="10"/>')
            if not inner:
                cy = (y0 + y1) / 2
                g += (f'<ellipse cx="540" cy="{cy:.0f}" rx="90" ry="{max(4, 90 * (y1 - y0) / 480):.0f}" fill="#c9504f" stroke="#3a1010" stroke-width="8"/>'
                      f'<path d="M 470,{cy:.0f} L 610,{cy:.0f}" stroke="#ffd54f" stroke-width="14"/>')
            else:
                g += f'<rect x="262" y="{y0 + 26:.0f}" width="556" height="{max(0, y1 - y0 - 40):.0f}" rx="20" fill="#5a1d1d"/>'
        img = svg_rgba(g, W, H)[..., :3]
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)                       # warm diya light from the right, dusk vignette
        lit = 0.78 + 0.32 * np.exp(-(((xx - 980) / 700) ** 2 + ((yy - 1100) / 900) ** 2))
        return np.clip(img * lit[..., None] * np.array([1.02, 0.94, 0.9]), 0, 255)

    def bike(self, t):
        cfg = self.cfg
        img = self.bg.copy()
        drop = ease((t - 0.25) / 0.35)
        hook = (520, 975)
        sway = 0.0 if drop < 1 else 14 * math.exp(-(t - 0.6) / 0.7) * math.sin((t - 0.6) * 7.5)
        bell = [1.5, 1.72]
        lever = max([math.exp(-max(0, t - b) / 0.08) * (t >= b) for b in bell] + [0])
        g = ('<g stroke-linecap="round" stroke-linejoin="round">'
             '<circle cx="300" cy="1820" r="430" fill="none" stroke="#141414" stroke-width="44"/>'
             '<circle cx="300" cy="1820" r="402" fill="none" stroke="#7d848c" stroke-width="10"/>'
             + "".join(f'<line x1="300" y1="1820" x2="{300 + 395 * math.cos(math.radians(a)):.0f}" y2="{1820 + 395 * math.sin(math.radians(a)):.0f}" stroke="#a8aeb4" stroke-width="5"/>'
                       for a in range(0, 360, 15)) +
             '<path d="M -150,1380 A 470 470 0 0 1 760,1430" stroke="#1d1d1d" stroke-width="26" fill="none"/>'
             '<path d="M 300,1820 L 470,1110" stroke="#141414" stroke-width="40"/>'                       # fork
             '<path d="M 480,1180 L 1180,1260 M 470,1250 L 1180,1700" stroke="#141414" stroke-width="46"/>'   # top + down tube
             '<path d="M 455,1250 L 500,1060" stroke="#141414" stroke-width="58"/>'                         # head tube
             '<path d="M 495,1070 L 505,960" stroke="#9aa0a6" stroke-width="30"/>'                          # stem
             '<path d="M 420,985 Q 520,945 640,985 Q 760,1025 850,1010" stroke="#9aa0a6" stroke-width="26" fill="none"/>'
             '<path d="M 790,1012 L 930,1000" stroke="#111" stroke-width="44"/>'                            # grip
             '<path d="M 420,985 L 330,1000" stroke="#111" stroke-width="44"/>'
             '<circle cx="455" cy="1150" r="40" fill="#c0c4c8" stroke="#555" stroke-width="6"/>'             # lamp
             '<circle cx="440" cy="1150" r="24" fill="#fff3b0"/>'
             f'<g transform="rotate({-40 * lever:.0f} 650 975)"><path d="M 650,975 L 700,940" stroke="#777" stroke-width="10"/></g>'
             '<ellipse cx="640" cy="958" rx="58" ry="40" fill="#d6dade" stroke="#555" stroke-width="6"/>'
             '<ellipse cx="626" cy="944" rx="22" ry="10" fill="#ffffff" opacity="0.8"/></g>')
        if lever > 0.2:
            g += "".join(f'<path d="M {700 + 40 * k},{900 - 30 * k} q 20,-20 40,0" stroke="#fff6b0" stroke-width="6" fill="none" opacity="{lever:.2f}"/>' for k in range(3))
        bg_ = svg_rgba(g, W, H)
        bg_[..., :3] *= np.array([0.86, 0.82, 0.92])
        img = over(img, bg_)
        if drop > 0:
            y = hook[1] - 900 * (1 - drop)
            bag = svg_rgba(f'<g transform="translate({hook[0]} {y:.0f})">{bag_svg(sway, 1.0)}</g>', W, H)
            bag[..., :3] *= np.array([0.9, 0.86, 0.9])
            img = over(img, bag)
            bar = svg_rgba('<path d="M 455,990 Q 520,965 585,975" stroke="#9aa0a6" stroke-width="26" fill="none" stroke-linecap="round"/>', W, H)
            img = over(img, bar)                                             # the bar in front of the handles
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        img = img * (0.85 + 0.25 * np.exp(-(((xx - 700) / 600) ** 2 + ((yy - 800) / 700) ** 2)))[..., None]
        return np.clip(img, 0, 255)


# ---------------------------------------------------------------- the picture shopping list

def icon_rice(x, y):
    return (f'<path d="M {x - 60},{y + 70} Q {x - 75},{y - 10} {x - 45},{y - 60} L {x + 45},{y - 60} Q {x + 75},{y - 10} {x + 60},{y + 70} Z" fill="#d7c08a" stroke="#5a4a22" stroke-width="5"/>'
            f'<path d="M {x - 45},{y - 60} Q {x},{y - 90} {x + 45},{y - 60}" fill="#f5f0e1" stroke="#5a4a22" stroke-width="5"/>'
            + "".join(f'<ellipse cx="{x - 30 + k * 15}" cy="{y - 66 + (k % 2) * 6}" rx="5" ry="3" fill="#ffffff" stroke="#999" stroke-width="1"/>' for k in range(5)))


def icon_veg(x, y):
    return (f'<path d="M {x - 70},{y + 40} Q {x - 70},{y - 20} {x - 30},{y - 10} Q {x - 10},{y + 30} {x - 40},{y + 60} Z" fill="#6a1b9a" stroke="#2a0a3a" stroke-width="5"/>'
            f'<path d="M {x - 32},{y - 12} l 10,-20" stroke="#2e7d32" stroke-width="8"/>'
            f'<circle cx="{x + 15}" cy="{y + 25}" r="34" fill="#e53935" stroke="#7a0a0a" stroke-width="5"/><path d="M {x + 5},{y - 8} l 10,8 l 10,-8" stroke="#2e7d32" stroke-width="6" fill="none"/>'
            f'<path d="M {x + 55},{y - 40} L {x + 85},{y + 60} L {x + 70},{y - 40} Z" fill="#fb8c00" stroke="#8a3a00" stroke-width="5"/>')


def icon_sweets(x, y):
    return (f'<rect x="{x - 75}" y="{y - 40}" width="150" height="90" rx="10" fill="#f9a825" stroke="#6d3a00" stroke-width="5"/>'
            + "".join(f'<circle cx="{x - 40 + k * 40}" cy="{y - 48}" r="20" fill="#f6a623" stroke="#b86e00" stroke-width="4"/>' for k in range(3)))


def icon_snacks(x, y):
    return "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="none" stroke="#b3772f" stroke-width="10"/>' for r in (18, 36, 54))


def icon_oil(x, y):
    return (f'<rect x="{x - 55}" y="{y - 60}" width="110" height="130" rx="10" fill="#ffca28" stroke="#6d5200" stroke-width="5"/>'
            f'<rect x="{x - 15}" y="{y - 85}" width="30" height="28" fill="#e53935" stroke="#6d5200" stroke-width="4"/>'
            f'<path d="M {x - 30},{y + 10} q 30,-40 60,0 q -30,40 -60,0" fill="#ff8f00"/>')


ICONS = [icon_rice, icon_veg, icon_sweets, icon_snacks, icon_oil]


def scene_list(t, cfg):
    g = ['<rect width="1080" height="1920" fill="#6d4c33"/>',
         '<g transform="rotate(-4 540 960)"><rect x="140" y="180" width="800" height="1560" rx="18" fill="#fbf8ee" stroke="#8a7a5a" stroke-width="8"/>']
    for k in range(14):
        g.append(f'<line x1="180" y1="{300 + k * 100}" x2="900" y2="{300 + k * 100}" stroke="#9ec3e6" stroke-width="4"/>')
    g.append('<line x1="260" y1="200" x2="260" y2="1720" stroke="#e57373" stroke-width="4"/>')
    for k in range(9):
        g.append(f'<circle cx="140" cy="{260 + k * 170}" r="22" fill="none" stroke="#888" stroke-width="8"/>')
    per = cfg.get("per", 0.9)
    pen = None
    for k, icon in enumerate(ICONS):
        y = 360 + k * 270
        u = (t - 0.2 - k * per) / (per * 0.75)
        if u <= 0:
            continue
        r = min(1.0, u)
        g.append(f'<clipPath id="c{k}"><rect x="300" y="{y - 120}" width="{360 * r:.0f}" height="240"/></clipPath><g clip-path="url(#c{k})">{icon(470, y)}</g>')
        if r < 1:
            pen = (300 + 360 * r, y + 20 * math.sin(u * 40))
        tick = ease((t - 0.2 - k * per - per * 0.75) / 0.18)
        if tick > 0:
            g.append(f'<path d="M 720,{y} l {30 * min(1, tick * 2):.0f},{30 * min(1, tick * 2):.0f} l {70 * max(0, tick * 2 - 1):.0f},{-90 * max(0, tick * 2 - 1):.0f}" '
                     f'stroke="#2e7d32" stroke-width="16" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
            if tick < 1:
                pen = (720 + 100 * tick, y - 40 * tick)
    g.append('</g>')
    if pen:
        x, y = pen
        g.append(f'<g transform="translate({x:.0f} {y:.0f}) rotate(35)"><rect x="-14" y="-420" width="28" height="380" fill="#fbc02d" stroke="#5a4a00" stroke-width="4"/>'
                 f'<path d="M -14,-40 L 14,-40 L 0,0 Z" fill="#f2d2a0" stroke="#5a4a00" stroke-width="3"/><path d="M -4,-12 L 4,-12 L 0,0 Z" fill="#333"/>'
                 f'<rect x="-14" y="-440" width="28" height="24" fill="#e57373"/></g>')
    return "".join(g)


# ---------------------------------------------------------------- the bicycle ride

def fireworks(img, t, bursts, s=1.0, period=4.2):
    """Rockets rise and burst: bursts = [(x, y, t0, colour index)], drawn on an RGB float image."""
    for x, y, t0, ci in bursts:
        u = (t - t0) % period
        col = np.array(BULB[ci % len(BULB)], np.float32)
        if u < 0.55:                                               # the rocket's climb
            v = u / 0.55
            ry = y + 420 * s * (1 - v)
            for k in range(8):
                yy = ry + k * 14 * s
                cv2.circle(img, (int(x), int(yy)), max(1, int(4 * s * (1 - k / 8))), (255, 230, 170), -1, cv2.LINE_AA)
            continue
        v = (u - 0.55) / 1.7
        if v > 1:
            continue
        r = 210 * s * (1 - (1 - v) ** 3)
        fade = (1 - v) ** 1.3
        col2 = np.array(BULB[(ci + 2) % len(BULB)], np.float32)
        for j in range(16):                                        # inner ring, another colour
            a = 2 * math.pi * j / 16 + ci + 0.2
            px, py = x + math.cos(a) * r * 0.5, y + math.sin(a) * r * 0.5 + 40 * s * v * v
            cv2.circle(img, (int(px), int(py)), max(1, int(5 * s * (1 - v))), tuple(float(q) * fade for q in col2 + (255 - col2) * max(0, 1 - v * 3)), -1, cv2.LINE_AA)
        for j in range(40):
            a = 2 * math.pi * j / 40 + ci
            drop = 70 * s * v * v
            px, py = x + math.cos(a) * r, y + math.sin(a) * r + drop
            qx, qy = x + math.cos(a) * r * 0.72, y + math.sin(a) * r * 0.72 + drop * 0.7
            c = col + (255 - col) * max(0, 1 - v * 3)              # white-hot at first
            cv2.line(img, (int(qx), int(qy)), (int(px), int(py)), tuple(float(q) * fade for q in c), max(1, int(7 * s * (1 - v))), cv2.LINE_AA)
            if j % 2 == 0 and v > 0.3:
                cv2.circle(img, (int(px), int(py)), max(1, int(3 * s)), tuple(float(q) * fade for q in c), -1, cv2.LINE_AA)
        _glow(img, x, y, 330 * s, tuple(col), 0.3 * fade)


class Silhouette:
    """Wide shot at dusk: Thatha cycles from right to left along a raised bund, a dark silhouette against the glowing
    sky (his side-view drawing's outline + pedalling legs + the roadster, all one dark shade); the village's lights
    on the horizon, rockets bursting above, everything mirrored in the pond below."""

    def __init__(self, cfg, base):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import body  # noqa: E402
        self.cfg = cfg
        f = body.side()
        a = f.img[..., 3].astype(np.float32).copy()
        a[895:944, 220:286] = 0                                    # the stick above and below his fist
        a[1052:1110, 222:279] = 0
        yy = np.arange(a.shape[0], dtype=np.float32)[:, None]
        a *= np.clip((1330 - yy) / 12, 0, 1)                       # seated: below the hips = legs drawn in code
        self.alpha = a
        self.gy = cfg.get("bund_y", 1180)
        self.bg = self.build()

    def build(self):
        gy = self.gy
        yy = np.arange(H, dtype=np.float32)[:, None, None]
        top, mid, low = np.array([22, 16, 60]), np.array([120, 50, 110]), np.array([255, 150, 80])
        u = np.clip(yy / gy, 0, 1)
        img = np.where(u < 0.6, top + (mid - top) * (u / 0.6), mid + (low - mid) * ((u - 0.6) / 0.4)) * np.ones((1, W, 1))
        img = img.astype(np.float32)
        rng = np.random.default_rng(11)
        for _ in range(160):
            x, y = rng.uniform(0, W), rng.uniform(0, gy * 0.55)
            cv2.circle(img, (int(x), int(y)), 1 if rng.random() < 0.75 else 2, (255, 250, 225), -1, cv2.LINE_AA)
        g = []
        x = -20                                                    # the village on the horizon: roofs, palms, lights
        while x < W + 40:
            w, h = rng.uniform(70, 150), rng.uniform(45, 95)
            base = gy - 6
            g.append(f'<path d="M {x:.0f},{base} L {x:.0f},{base - h:.0f} L {x + w / 2:.0f},{base - h - 38:.0f} L {x + w:.0f},{base - h:.0f} L {x + w:.0f},{base} Z" fill="#3b2450"/>')
            for k in range(int(rng.integers(1, 3))):
                wx = x + rng.uniform(15, w - 25)
                g.append(f'<rect x="{wx:.0f}" y="{base - h * 0.6:.0f}" width="12" height="16" fill="#ffc46b"/>')
            x += w + rng.uniform(-10, 40)
        for px in rng.uniform(0, W, 6):
            hh = rng.uniform(170, 260)
            g.append(f'<path d="M {px:.0f},{gy - 5} Q {px + 14:.0f},{gy - hh / 2:.0f} {px + 6:.0f},{gy - hh:.0f}" stroke="#2c1a3c" stroke-width="9" fill="none"/>')
            cx, cy = px + 6, gy - hh
            for k in range(9):                                     # drooping fronds
                d = -1 if k % 2 else 1
                L = rng.uniform(60, 95)
                lift = rng.uniform(-30, 15)
                g.append(f'<path d="M {cx:.0f},{cy:.0f} Q {cx + d * L * 0.5:.0f},{cy - 38 + lift:.0f} {cx + d * L:.0f},{cy + rng.uniform(5, 38):.0f}" '
                         f'stroke="#2c1a3c" stroke-width="{rng.uniform(7, 11):.0f}" fill="none" stroke-linecap="round"/>')
        g.append(f'<rect x="0" y="{gy}" width="{W}" height="34" fill="#170d1e"/>')
        for k in range(60):
            gx = rng.uniform(0, W)
            g.append(f'<path d="M {gx:.0f},{gy + 2} l -6,-16 M {gx:.0f},{gy + 2} l 3,-20 M {gx:.0f},{gy + 2} l 9,-13" stroke="#170d1e" stroke-width="3"/>')
        img = over(img, svg_rgba("".join(g), W, H))
        self.lights = [(x, gy - rng.uniform(70, 130)) for x in np.arange(10, W, 26)]
        return img

    def rider_svg(self, t, X, K, col):
        """Bike + legs in screen px; figure px (side drawing, padded) * K, placed with the figure origin at X."""
        ox, oy = X
        Pp = lambda x, y: (ox + x * K, oy + y * K)                 # noqa: E731
        spd = self.cfg.get("speed", 330)
        rot = -t * spd / (240 * K)                                 # wheels roll left
        cr = rot / 2.4                                             # crank
        RA, FA, BB = Pp(880, 1700), Pp(70, 1700), Pp(560, 1760)
        r = 240 * K
        g = [f'<g stroke="{col}" fill="none" stroke-linecap="round" stroke-linejoin="round">']
        for cx, cy in (RA, FA):
            g.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" stroke-width="{16 * K:.1f}"/>')
            for k in range(12):
                a = rot + k * math.pi / 6
                g.append(f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{cx + r * math.cos(a):.1f}" y2="{cy + r * math.sin(a):.1f}" stroke-width="{3.5 * K:.1f}"/>')
        seat, head = Pp(650, 1290), Pp(140, 1260)
        g.append(f'<path d="M {RA[0]:.1f},{RA[1]:.1f} L {BB[0]:.1f},{BB[1]:.1f} L {seat[0]:.1f},{seat[1]:.1f} L {RA[0]:.1f},{RA[1]:.1f} '
                 f'M {seat[0]:.1f},{seat[1]:.1f} L {head[0]:.1f},{head[1]:.1f} L {BB[0]:.1f},{BB[1]:.1f} M {head[0]:.1f},{head[1]:.1f} L {FA[0]:.1f},{FA[1]:.1f}" stroke-width="{22 * K:.1f}"/>')
        g.append(f'<path d="M {head[0]:.1f},{head[1]:.1f} L {Pp(150, 1110)[0]:.1f},{Pp(150, 1110)[1]:.1f} Q {Pp(200, 1060)[0]:.1f},{Pp(200, 1060)[1]:.1f} {Pp(258, 1060)[0]:.1f},{Pp(258, 1060)[1]:.1f}" stroke-width="{20 * K:.1f}"/>')
        g.append(f'<path d="M {Pp(610, 1278)[0]:.1f},{Pp(610, 1278)[1]:.1f} L {Pp(730, 1282)[0]:.1f},{Pp(730, 1282)[1]:.1f}" stroke-width="{34 * K:.1f}"/>')
        g.append(f'<path d="M {Pp(700, 1420)[0]:.1f},{Pp(700, 1420)[1]:.1f} L {Pp(1000, 1420)[0]:.1f},{Pp(1000, 1420)[1]:.1f}" stroke-width="{16 * K:.1f}"/>')
        g.append(f'<path d="M {RA[0] - r * 1.05:.1f},{RA[1] - r * 0.3:.1f} A {r * 1.08:.1f} {r * 1.08:.1f} 0 0 1 {RA[0] + r * 1.05:.1f},{RA[1] - r * 0.3:.1f}" stroke-width="{12 * K:.1f}"/>')
        g.append('</g>')
        bx, by = Pp(150, 1110)                                     # the bag on the handlebar
        g.append(f'<g transform="translate({bx:.1f} {by:.1f}) rotate({4 * math.sin(t * 3):.1f}) scale({0.55 * K:.3f})">'
                 f'<path d="M -70,110 Q -60,-30 0,-14 Q 60,-30 70,110" stroke="{col}" stroke-width="18" fill="none"/>'
                 f'<path d="M -150,100 Q 0,84 150,100 Q 190,320 160,520 Q 0,560 -160,520 Q -190,320 -150,100 Z" fill="{col}"/></g>')
        hip = Pp(600, 1300)
        a_, b_ = 330 * K, 330 * K
        for k, ph in ((0, math.pi), (1, 0.0)):                    # far leg first, near leg last
            pd = (BB[0] + 95 * K * math.cos(cr + ph), BB[1] + 95 * K * math.sin(cr + ph))
            g.append(f'<line x1="{BB[0]:.1f}" y1="{BB[1]:.1f}" x2="{pd[0]:.1f}" y2="{pd[1]:.1f}" stroke="{col}" stroke-width="{16 * K:.1f}" stroke-linecap="round"/>')
            dx, dy = pd[0] - hip[0], pd[1] - hip[1] - 30 * K
            dist = min(a_ + b_ - 1, math.hypot(dx, dy))
            ang = math.atan2(dy, dx)
            q = math.acos(max(-1, min(1, (a_ * a_ + dist * dist - b_ * b_) / (2 * a_ * dist))))
            k1 = (hip[0] + a_ * math.cos(ang + q), hip[1] + a_ * math.sin(ang + q))
            k2 = (hip[0] + a_ * math.cos(ang - q), hip[1] + a_ * math.sin(ang - q))
            kn = k1 if k1[0] < k2[0] else k2                       # knee forward (to the left)
            ank = (hip[0] + dist * math.cos(ang), hip[1] + dist * math.sin(ang))
            g.append(f'<path d="M {hip[0]:.1f},{hip[1]:.1f} L {kn[0]:.1f},{kn[1]:.1f}" stroke="{col}" stroke-width="{115 * K:.1f}" stroke-linecap="round"/>')
            g.append(f'<path d="M {kn[0]:.1f},{kn[1]:.1f} L {ank[0]:.1f},{ank[1]:.1f}" stroke="{col}" stroke-width="{58 * K:.1f}" stroke-linecap="round"/>')
            g.append(f'<path d="M {ank[0] + 25 * K:.1f},{ank[1] - 5 * K:.1f} L {pd[0] - 85 * K:.1f},{pd[1] + 8 * K:.1f}" stroke="{col}" stroke-width="{40 * K:.1f}" stroke-linecap="round"/>')
        return "".join(g)

    def frame(self, t):
        cfg = self.cfg
        gy = self.gy
        img = self.bg.copy()
        for i, (x, y) in enumerate(self.lights):
            on = 0.55 + 0.45 * math.sin(t * 3 + i * 1.7)
            col = BULB[i % len(BULB)]
            y2 = y + 10 * math.sin(math.pi * ((x % 260) / 260))
            cv2.circle(img, (int(x), int(y2)), 4, tuple(c * (0.6 + 0.4 * on) for c in col), -1, cv2.LINE_AA)
            _glow(img, x, y2, 18, col, 0.3 * on)
        fireworks(img, t, cfg.get("fireworks", []), cfg.get("fw_scale", 1.0))
        K = cfg.get("scale", 0.3)
        x0, x1 = cfg.get("from_x", 1200), cfg.get("to_x", -300)
        dur = cfg["duration"]
        X = x0 + (x1 - x0) * t / dur
        bob = 2 * K * math.sin(t * 9)
        org = (X - 450 * K, gy - 1940 * K + bob)
        col = "#1b0f22"
        img = over(img, svg_rgba(self.rider_svg(t, org, K, col), W, H))
        a = cv2.resize(self.alpha, None, fx=K, fy=K, interpolation=cv2.INTER_AREA)
        spr = np.dstack([np.zeros(a.shape + (3,), np.float32) + np.array([27, 15, 34]), a])
        img = paste(img, spr, org[0], org[1])
        # the pond: everything above the bund, mirrored, darker, rippling
        top = img[:gy][::-1]
        n = H - gy - 34
        refl = top[:n].copy() if n <= gy else np.vstack([top, np.zeros((n - gy, W, 3), np.float32)])
        rows = np.arange(n)
        shift = (6 * np.sin(rows * 0.09 + t * 4) * (0.3 + rows / n)).astype(np.int32)
        cols = (np.arange(W)[None, :] + shift[:, None]) % W
        refl = refl[rows[:, None], cols]
        dark = (0.55 - 0.25 * rows / n)[:, None, None]
        img[gy + 34:] = refl * dark + np.array([10, 8, 30]) * (1 - dark)
        for k in range(18):                                       # light streaks on the water
            yy_ = gy + 50 + int((k * 97 + t * 30) % (n - 20))
            cv2.line(img, (int((k * 233) % W), yy_), (int((k * 233) % W + 80), yy_), (120, 90, 150), 2, cv2.LINE_AA)
        return np.clip(img, 0, 255)


def main():
    out = sys.argv[1]
    cfg_path = Path(sys.argv[2])
    cfg = json.loads(cfg_path.read_text())
    base = cfg_path.parent
    fps = cfg.get("fps", 25)
    n = round(cfg["duration"] * fps)
    mode = cfg["mode"]
    sc = {"dream": Dream, "savings": Close, "bike": Close, "silhouette": Silhouette}.get(mode)
    sc = sc(cfg, base) if sc else None
    cams = cfg.get("camera", [[0, H / 2, H]])
    still = cfg.get("still")
    ff = None if still is not None else subprocess.Popen(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-framerate", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i in ([0] if still is not None else range(n)):
        t = still if still is not None else i / fps
        img = sc.frame(t) if sc else svg_rgba(scene_list(t, cfg), W, H)[..., :3]
        cy = float(np.interp(t, [c[0] for c in cams], [c[1] for c in cams]))
        vh = float(np.interp(t, [c[0] for c in cams], [c[2] for c in cams]))
        if vh < H - 0.5:
            vw = vh * W / H
            M = np.float32([[W / vw, 0, -(W / 2 - vw / 2) * W / vw], [0, H / vh, -(cy - vh / 2) * H / vh]])
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
