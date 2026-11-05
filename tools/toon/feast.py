"""Cooking-and-sharing cut-aways (Maran Thatha – Diwali special 2). Props drawn in code; 1080x1920 unless noted.

Prop helpers (SVG strings, any coords): table, rice_sack, veg_basket, sweet_box, snack_pack, oil_can, tiffin,
leaf_parcel, laddu – also used by series/05-diwali/sp02/final/make_frames.py.

Cut-aways (python tools/toon/feast.py OUT.mp4 TIMING.json):
    unpack:   the kitchen table (kitchen blurred behind): the shopping lands on it one by one – rice sack, vegetable
              basket, sweet box, snacks, oil – each with a little bounce.
    cook:     top-down close-up of a pot on the wood fire, "dish": rice (white grains, bubbles, steam), sambar (dal
              with drumstick, tomato, curry leaves; a ladle stirring), curry (beans-carrot poriyal tossed in a
              kadai), sweet (laddus appear one by one on a steel plate, boondi bowl beside).
    pack:     top-down on the table: three steel boxes fill with rice, sambar and curry, the lids close, a sweet box
              and a snack pack are set beside them, string ties the bundle, a red heart tag lands on top.
    load:     his bicycle's rear carrier (golden afternoon, farmhouse blurred): parcels stack onto it, a rope ties them.
    entrance: the children's home steps (frames/khome_empty.png, zoomed): the parcels are set down one by one.
    lamps:    the decorated farmhouse at night (Ep 1 dusk plate): the diyas light one by one, then the bulbs and lanterns.
    finale:   the farmhouse, every light on, big rockets bursting overhead; the camera eases back.
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
import diwali as D  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
W, H = 1080, 1920
WOOD, WOOD_D, WOOD_L, OUTL = "#8a5a2b", "#6b4220", "#b07a44", "#3e2410"


def svg_rgba(body, w=W, h=H):
    png = cairosvg.svg2png(bytestring=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">{body}</svg>'.encode())
    return np.array(Image.open(io.BytesIO(png)).convert("RGBA")).astype(np.float32)


def ease(u):
    u = min(max(u, 0), 1)
    return u * u * (3 - 2 * u)


def land(t, t0, dur=0.35, h=700):
    """Drop from h px above and settle with a small bounce: returns (dy, squash) or None before t0."""
    u = (t - t0) / dur
    if u < 0:
        return None
    if u < 1:
        return -h * (1 - u * u), 1.0
    v = (t - t0 - dur) / 0.25
    if v < 1:
        return -26 * math.sin(math.pi * v) * (1 - v), 1 - 0.06 * math.sin(math.pi * v)
    return 0.0, 1.0


def table(x0, x1, top, legs_to=1280, depth=46):
    return (f'<rect x="{x0 + 18}" y="{top + depth}" width="30" height="{legs_to - top - depth}" fill="{WOOD_D}" stroke="{OUTL}" stroke-width="5"/>'
            f'<rect x="{x1 - 48}" y="{top + depth}" width="30" height="{legs_to - top - depth}" fill="{WOOD_D}" stroke="{OUTL}" stroke-width="5"/>'
            f'<path d="M {x0 + 20},{top} L {x1 - 20},{top} L {x1},{top + 24} L {x0},{top + 24} Z" fill="{WOOD_L}" stroke="{OUTL}" stroke-width="5"/>'
            f'<rect x="{x0}" y="{top + 24}" width="{x1 - x0}" height="{depth - 10}" rx="4" fill="{WOOD}" stroke="{OUTL}" stroke-width="5"/>'
            f'<line x1="{x0 + 10}" y1="{top + 34}" x2="{x1 - 10}" y2="{top + 34}" stroke="{WOOD_L}" stroke-width="3" opacity="0.6"/>')


def rice_sack(x, y, s=1.0):
    return (f'<g transform="translate({x} {y}) scale({s})"><path d="M -60,0 Q -72,-80 -48,-130 L 48,-130 Q 72,-80 60,0 Z" fill="#e8dcb5" stroke="#6b5a2a" stroke-width="5"/>'
            '<path d="M -48,-130 Q 0,-150 48,-130 Q 0,-118 -48,-130" fill="#fbf7ec" stroke="#6b5a2a" stroke-width="4"/>'
            + "".join(f'<ellipse cx="{-30 + k * 12}" cy="{-134 + (k % 2) * 4}" rx="4" ry="2.5" fill="#fff"/>' for k in range(6)) +
            '<path d="M -40,-60 L 40,-60 M -42,-40 L 42,-40" stroke="#c9a85a" stroke-width="5"/>'
            '<circle cx="0" cy="-88" r="15" fill="#3e8e41"/><path d="M -8,-88 q 8,-14 16,0 q -8,10 -16,0" fill="#e8dcb5"/></g>')


def veg_basket(x, y, s=1.0):
    return (f'<g transform="translate({x} {y}) scale({s})">'
            '<ellipse cx="-30" cy="-62" rx="26" ry="20" fill="#e53935" stroke="#7a0a0a" stroke-width="4"/>'
            '<path d="M -40,-80 l 10,8 l 10,-8" stroke="#2e7d32" stroke-width="4" fill="none"/>'
            '<path d="M 0,-60 Q 20,-110 55,-100 Q 40,-62 0,-60 Z" fill="#6a1b9a" stroke="#2a0a3a" stroke-width="4"/>'
            '<path d="M 52,-100 l 10,-12" stroke="#2e7d32" stroke-width="6"/>'
            '<path d="M -10,-70 L 20,-140 L 30,-136 L 6,-66 Z" fill="#fb8c00" stroke="#8a3a00" stroke-width="3"/>'
            '<path d="M 22,-140 l -8,-16 M 24,-140 l 4,-18 M 26,-139 l 12,-12" stroke="#2e7d32" stroke-width="4"/>'
            '<ellipse cx="30" cy="-58" rx="22" ry="16" fill="#8bc34a" stroke="#33691e" stroke-width="4"/>'
            '<path d="M -70,-50 L 70,-50 L 56,0 L -56,0 Z" fill="#c8a05a" stroke="#5a3a10" stroke-width="5"/>'
            + "".join(f'<line x1="{-60 + k * 20}" y1="-48" x2="{-50 + k * 17}" y2="-2" stroke="#8a6a30" stroke-width="3"/>' for k in range(7)) +
            '<path d="M -64,-30 L 64,-30" stroke="#8a6a30" stroke-width="3"/></g>')


def sweet_box(x, y, s=1.0, open_=True):
    lad = "".join(f'<circle cx="{-36 + k * 24}" cy="-40" r="12" fill="#f6a623" stroke="#b86e00" stroke-width="3"/>' for k in range(4)) if open_ else ""
    return (f'<g transform="translate({x} {y}) scale({s})">{lad}'
            '<rect x="-56" y="-36" width="112" height="36" rx="4" fill="#e53935" stroke="#7a0a0a" stroke-width="4"/>'
            '<rect x="-56" y="-24" width="112" height="10" fill="#ffd54f"/></g>')


def snack_pack(x, y, s=1.0, col="#1e88e5"):
    return (f'<g transform="translate({x} {y}) scale({s})"><path d="M -30,0 L -34,-90 L -24,-98 L 24,-98 L 34,-90 L 30,0 Z" fill="{col}" stroke="#0d2c53" stroke-width="4"/>'
            '<path d="M -34,-90 L 34,-90" stroke="#ffffff" stroke-width="3" stroke-dasharray="4 4"/>'
            '<circle cx="0" cy="-48" r="16" fill="#ffd54f" stroke="#a67c00" stroke-width="3"/>'
            '<circle cx="0" cy="-48" r="7" fill="none" stroke="#a67c00" stroke-width="3"/></g>')


def oil_can(x, y, s=1.0):
    return (f'<g transform="translate({x} {y}) scale({s})"><rect x="-32" y="-96" width="64" height="96" rx="6" fill="#ffca28" stroke="#6d5200" stroke-width="4"/>'
            '<rect x="-12" y="-114" width="24" height="20" fill="#e53935" stroke="#6d5200" stroke-width="3"/>'
            '<path d="M -18,-46 q 18,-28 36,0 q -18,26 -36,0" fill="#ff8f00"/></g>')


def tiffin(x, y, s=1.0):
    """A three-tier steel tiffin carrier."""
    g = f'<g transform="translate({x} {y}) scale({s})">'
    for k in range(3):
        yy = -k * 34
        g += (f'<rect x="-34" y="{yy - 34}" width="68" height="34" rx="6" fill="#c9cdd2" stroke="#5a6068" stroke-width="4"/>'
              f'<line x1="-32" y1="{yy - 6}" x2="32" y2="{yy - 6}" stroke="#8a9096" stroke-width="3"/>')
    g += ('<path d="M -40,-100 L -40,-20 M 40,-100 L 40,-20" stroke="#7d848c" stroke-width="6"/>'
          '<path d="M -40,-100 Q 0,-150 40,-100" stroke="#7d848c" stroke-width="7" fill="none"/>'
          '<rect x="-36" y="-110" width="72" height="10" rx="4" fill="#aeb4ba" stroke="#5a6068" stroke-width="3"/></g>')
    return g


def leaf_parcel(x, y, s=1.0):
    """A banana-leaf food parcel tied with string, a small sweet box on top."""
    return (f'<g transform="translate({x} {y}) scale({s})"><path d="M -54,0 Q -60,-40 -50,-62 L 50,-62 Q 60,-40 54,0 Z" fill="#43a047" stroke="#1b5e20" stroke-width="4"/>'
            '<path d="M -50,-62 Q 0,-78 50,-62 Q 0,-50 -50,-62" fill="#66bb6a" stroke="#1b5e20" stroke-width="3"/>'
            '<path d="M -20,-62 L -22,0 M 20,-62 L 22,0 M -54,-30 L 54,-30" stroke="#d7c08a" stroke-width="4"/>'
            '<path d="M -6,-72 q 6,-14 12,0" stroke="#d7c08a" stroke-width="4" fill="none"/>'
            '<rect x="-26" y="-100" width="52" height="26" rx="3" fill="#e53935" stroke="#7a0a0a" stroke-width="3"/>'
            '<rect x="-26" y="-92" width="52" height="7" fill="#ffd54f"/></g>')


def laddu(x, y, r):
    rng = np.random.default_rng(int(x * 7 + y))
    dots = "".join(f'<circle cx="{x + rng.uniform(-r * .6, r * .6):.1f}" cy="{y + rng.uniform(-r * .6, r * .6):.1f}" r="{r * 0.09:.1f}" fill="#d9851a"/>' for _ in range(7))
    return (f'<circle cx="{x}" cy="{y}" r="{r}" fill="#f7a92c" stroke="#a8620a" stroke-width="{max(1.5, r * 0.1):.1f}"/>{dots}'
            f'<circle cx="{x - r * 0.35:.1f}" cy="{y - r * 0.35:.1f}" r="{r * 0.22:.1f}" fill="#ffd27a" opacity="0.8"/>')


# ---------------------------------------------------------------- scenes

def plate_img(path, k=0, dark=1.0, tint=(1, 1, 1)):
    im = np.array(Image.open(path).convert("RGB").resize((W, H), Image.LANCZOS)).astype(np.float32)
    if k:
        im = cv2.GaussianBlur(im, (0, 0), k)
    return np.clip(im * dark * np.array(tint), 0, 255)


def steam(t, cx, cy, n=4, spread=260, seed=1):
    rng = np.random.default_rng(seed)
    g = ""
    for k in range(n):
        x0, ph = cx + rng.uniform(-spread / 2, spread / 2), rng.uniform(0, 1)
        u = (t * 0.45 + ph) % 1
        y = cy - 500 * u
        x = x0 + 40 * math.sin(u * 6 + k)
        g += (f'<path d="M {x:.0f},{y:.0f} q 30,-60 0,-120 q -30,-60 0,-120" stroke="#ffffff" stroke-width="{34 - 14 * u:.0f}" '
              f'fill="none" stroke-linecap="round" opacity="{0.35 * math.sin(math.pi * u):.2f}"/>')
    return g


def bubbles(t, cx, cy, r, col, n=14, seed=2):
    rng = np.random.default_rng(seed)
    g = ""
    for k in range(n):
        a, d, ph, sp = rng.uniform(0, 6.28), r * math.sqrt(rng.uniform(0, 0.8)), rng.uniform(0, 1), rng.uniform(0.7, 1.4)
        u = (t * sp + ph) % 1
        rr = 6 + 16 * u
        g += f'<circle cx="{cx + d * math.cos(a):.0f}" cy="{cy + d * math.sin(a):.0f}" r="{rr:.0f}" fill="none" stroke="{col}" stroke-width="3" opacity="{(1 - u) * 0.8:.2f}"/>'
    return g


def scene_unpack(t, cfg, bg):
    g = table(-40, 1120, 1250, 1920, 90)
    items = [(rice_sack, 245, 1272, 1.7, 0.2), (veg_basket, 570, 1272, 1.6, 0.7), (sweet_box, 765, 1272, 1.4, 1.2),
             (snack_pack, 895, 1272, 1.2, 1.6), (oil_can, 405, 1272, 1.1, 2.0)]
    top = ""
    for fn, x, y, s, t0 in items:
        r = land(t, t0)
        if r is None:
            continue
        dy, sq = r
        top += f'<g transform="translate({x} {y + dy:.0f}) scale({1 / sq:.3f} {sq:.3f}) translate({-x} {-y})">{fn(x, y, s)}</g>'
        if dy > -5:
            top += f'<ellipse cx="{x}" cy="{y + 4}" rx="{90 * s:.0f}" ry="12" fill="#000" opacity="0.18"/>'
    return D.over(bg, svg_rgba(g + top))


def scene_cook(t, cfg, bg):
    dish = cfg.get("dish", "rice")
    cx, cy, R = 540, 1000, 430
    rng = np.random.default_rng(3)
    g = ['<rect width="1080" height="1920" fill="#2b1a10"/>']
    for k in range(10):                                          # fire licking round the pot
        a = math.radians(200 + k * 14)
        fl = 1 + 0.25 * math.sin(t * 11 + k * 1.7)
        x, y = cx + (R + 20) * math.cos(a), cy + (R + 20) * math.sin(a)
        g.append(f'<ellipse cx="{x:.0f}" cy="{y + 30:.0f}" rx="{38 * fl:.0f}" ry="{70 * fl:.0f}" fill="#ff8f00" opacity="0.85" transform="rotate({math.degrees(a) + 90:.0f} {x:.0f} {y:.0f})"/>')
    g.append(f'<circle cx="{cx}" cy="{cy}" r="{R + 28}" fill="#1c1c1c" stroke="#000" stroke-width="10"/>')
    g.append(f'<circle cx="{cx}" cy="{cy}" r="{R + 12}" fill="none" stroke="#5a5a5a" stroke-width="10"/>')
    if dish == "rice":
        g.append(f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="#e9e2cc"/>')
        for _ in range(520):
            a, d = rng.uniform(0, 6.28), R * math.sqrt(rng.uniform(0, 0.97))
            x, y = cx + d * math.cos(a), cy + d * math.sin(a)
            g.append(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="10" ry="4" fill="#ffffff" stroke="#b8ad8e" stroke-width="2.5" transform="rotate({rng.uniform(0, 180):.0f} {x:.0f} {y:.0f})"/>')
        g.append(bubbles(t, cx, cy, R, "#ffffff", 18))
    elif dish == "sambar":
        g.append(f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="#c0581e"/>')
        for _ in range(60):
            a, d = rng.uniform(0, 6.28), R * math.sqrt(rng.uniform(0, 0.95))
            g.append(f'<circle cx="{cx + d * math.cos(a):.0f}" cy="{cy + d * math.sin(a):.0f}" r="{rng.uniform(8, 22):.0f}" fill="#d9822f" opacity="0.5"/>')
        rot = t * 70
        pieces = [("dr", 0.5, 0), ("dr", 0.62, 80), ("dr", 0.3, 200), ("to", 0.55, 140), ("to", 0.25, 300), ("to", 0.7, 250),
                  ("cl", 0.45, 30), ("cl", 0.6, 170), ("cl", 0.35, 320), ("on", 0.5, 110), ("on", 0.72, 340)]
        for kind, d, a0 in pieces:
            a = math.radians(a0 + rot)
            x, y = cx + R * d * math.cos(a), cy + R * d * math.sin(a)
            if kind == "dr":
                g.append(f'<rect x="{x - 45:.0f}" y="{y - 13:.0f}" width="90" height="26" rx="13" fill="#7a9a2e" stroke="#33461a" stroke-width="4" transform="rotate({a0 + rot:.0f} {x:.0f} {y:.0f})"/>')
            elif kind == "to":
                g.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="24" fill="#e53935" stroke="#7a0a0a" stroke-width="4"/>')
            elif kind == "cl":
                g.append(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="26" ry="11" fill="#2e5e1e" transform="rotate({a0 * 2 + rot:.0f} {x:.0f} {y:.0f})"/>')
            else:
                g.append(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="22" ry="16" fill="#f3d9e0" stroke="#b07a8a" stroke-width="3"/>')
        g.append(bubbles(t, cx, cy, R, "#ffb070", 10, 5))
        a = math.radians(t * 160)                                  # the ladle stirring
        lx, ly = cx + 170 * math.cos(a), cy + 120 * math.sin(a)
        g.append(f'<path d="M {lx:.0f},{ly:.0f} L {lx + 520:.0f},{ly + 760:.0f}" stroke="#8a5a2b" stroke-width="40" stroke-linecap="round"/>')
        g.append(f'<ellipse cx="{lx:.0f}" cy="{ly:.0f}" rx="80" ry="64" fill="#a8743a" stroke="#5a3a10" stroke-width="7"/>')
    elif dish == "curry":
        g.append(f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="#6b4a2a"/>')
        toss = (t % 1.4) / 1.4
        jump = math.sin(math.pi * min(1, toss / 0.35)) if toss < 0.35 else 0
        for k in range(110):
            a, d = rng.uniform(0, 6.28), R * math.sqrt(rng.uniform(0, 0.9))
            sh = jump * 60 * rng.uniform(0.3, 1)
            x, y = cx + d * math.cos(a) + sh * 0.4, cy + d * math.sin(a) - sh
            if k % 3 == 0:
                g.append(f'<rect x="{x - 15:.0f}" y="{y - 15:.0f}" width="30" height="30" rx="5" fill="#fb8c00" stroke="#8a3a00" stroke-width="3" transform="rotate({rng.uniform(0, 90):.0f} {x:.0f} {y:.0f})"/>')
            else:
                g.append(f'<rect x="{x - 26:.0f}" y="{y - 9:.0f}" width="52" height="18" rx="8" fill="#5aa832" stroke="#2e5e1e" stroke-width="3" transform="rotate({rng.uniform(0, 180):.0f} {x:.0f} {y:.0f})"/>')
        for _ in range(80):
            a, d = rng.uniform(0, 6.28), R * math.sqrt(rng.uniform(0, 0.9))
            g.append(f'<circle cx="{cx + d * math.cos(a):.0f}" cy="{cy + d * math.sin(a) - jump * 40:.0f}" r="6" fill="#ffffff"/>')
        g.append(f'<circle cx="{cx}" cy="{cy}" r="{R + 12}" fill="none" stroke="#5a5a5a" stroke-width="10"/>')
    else:                                                          # sweet: laddus on a steel plate
        g = ['<rect width="1080" height="1920" fill="#6d4c33"/>',
             '<circle cx="540" cy="1080" r="430" fill="#c9cdd2" stroke="#7d848c" stroke-width="10"/>',
             '<circle cx="540" cy="1080" r="360" fill="#d8dce0" stroke="#aeb4ba" stroke-width="6"/>',
             '<circle cx="880" cy="420" r="230" fill="#8a9096" stroke="#5a6068" stroke-width="8"/>',
             '<circle cx="880" cy="420" r="200" fill="#f39c12"/>']
        for _ in range(160):
            a, d = rng.uniform(0, 6.28), 190 * math.sqrt(rng.uniform(0, 1))
            g.append(f'<circle cx="{880 + d * math.cos(a):.0f}" cy="{420 + d * math.sin(a):.0f}" r="9" fill="{rng.choice(["#f7b733", "#e8890c", "#ffcc4d"])}"/>')
        spots = [(400, 940), (540, 900), (680, 940), (360, 1090), (500, 1060), (640, 1070), (780, 1080), (430, 1220), (580, 1230), (720, 1210)]
        for k, (x, y) in enumerate(spots):
            u = (t - 0.2 - k * 0.2) / 0.25
            if u > 0:
                s = 0.6 + 0.4 * ease(u) + 0.08 * math.sin(math.pi * min(1, u)) 
                g.append(f'<ellipse cx="{x}" cy="{y + 60}" rx="62" ry="16" fill="#000" opacity="0.15"/>')
                g.append(f'<g transform="translate({x} {y}) scale({s:.3f}) translate({-x} {-y})">{laddu(x, y, 66)}</g>')
        g.append(D.sparkle_svg(t, 10, 6, (200, 700, 900, 1400)))
        return D.over(bg * 0, svg_rgba("".join(g)))
    g.append(steam(t, cx, cy - 100, 5, 500))
    return D.over(bg * 0, svg_rgba("".join(g)))


def scene_pack(t, cfg, bg):
    g = ['<rect width="1080" height="1920" fill="#9a6a3a"/>']
    for k in range(9):
        g.append(f'<line x1="0" y1="{k * 230 + 40}" x2="1080" y2="{k * 230 + 70}" stroke="#7a4f28" stroke-width="6" opacity="0.6"/>')
    boxes = [(300, 760, "#f4f1e6", 0.3), (780, 760, "#c0581e", 0.9), (540, 1220, "#5aa832", 1.5)]
    lid_t = 2.2
    for k, (x, y, col, t0) in enumerate(boxes):
        g.append(f'<ellipse cx="{x + 14}" cy="{y + 18}" rx="200" ry="200" fill="#000" opacity="0.2"/>')
        g.append(f'<circle cx="{x}" cy="{y}" r="200" fill="#c9cdd2" stroke="#5a6068" stroke-width="10"/>')
        g.append(f'<circle cx="{x}" cy="{y}" r="172" fill="#8a9096"/>')
        f = ease((t - t0) / 0.5)
        if f > 0:
            g.append(f'<circle cx="{x}" cy="{y}" r="{172 * (0.4 + 0.6 * f):.0f}" fill="{col}"/>')
            rng = np.random.default_rng(k)
            for _ in range(int(40 * f)):
                a, d = rng.uniform(0, 6.28), 150 * f * math.sqrt(rng.uniform(0, 1))
                px, py = x + d * math.cos(a), y + d * math.sin(a)
                c2 = {0: "#ffffff", 1: "#7a9a2e", 2: "#fb8c00"}[k]
                g.append(f'<ellipse cx="{px:.0f}" cy="{py:.0f}" rx="12" ry="6" fill="{c2}" transform="rotate({rng.uniform(0, 180):.0f} {px:.0f} {py:.0f})"/>')
        lid = ease((t - lid_t - k * 0.15) / 0.3)
        if lid > 0:
            off = 260 * (1 - lid)
            g.append(f'<circle cx="{x + off:.0f}" cy="{y - off:.0f}" r="205" fill="#d8dce0" stroke="#5a6068" stroke-width="10" opacity="{min(1, lid * 2):.2f}"/>'
                     f'<circle cx="{x + off:.0f}" cy="{y - off:.0f}" r="40" fill="#aeb4ba" stroke="#5a6068" stroke-width="6" opacity="{min(1, lid * 2):.2f}"/>')
    top = ""
    for fn, x, y, s, t0 in ((sweet_box, 210, 1360, 2.2, 3.0), (snack_pack, 870, 1420, 2.0, 3.3)):
        r = land(t, t0, 0.3, 600)
        if r:
            top += f'<g transform="translate(0 {r[0]:.0f})">{fn(x, y, s)}</g>'
    tie = ease((t - 3.8) / 0.5)
    if tie > 0:
        top += (f'<path d="M 60,{960 * 1:.0f} L {60 + 960 * tie:.0f},{960:.0f}" stroke="#e8d5a0" stroke-width="16" stroke-linecap="round"/>'
                f'<path d="M 540,180 L 540,{180 + 1500 * tie:.0f}" stroke="#e8d5a0" stroke-width="16" stroke-linecap="round"/>')
    r = land(t, 4.4, 0.3, 500)
    if r:
        top += (f'<g transform="translate(540 {960 + r[0]:.0f}) rotate(-8)"><path d="M 0,40 C -110,-30 -80,-120 0,-60 C 80,-120 110,-30 0,40 Z" '
                f'fill="#e53935" stroke="#7a0a0a" stroke-width="7"/><circle cx="0" cy="-70" r="8" fill="#fff"/></g>')
    return svg_rgba("".join(g) + top)[..., :3]


def scene_load(t, cfg, bg):
    g = ['<g stroke-linecap="round" stroke-linejoin="round">',
         '<circle cx="640" cy="1780" r="470" fill="none" stroke="#141414" stroke-width="44"/>',
         '<circle cx="640" cy="1780" r="440" fill="none" stroke="#7d848c" stroke-width="10"/>']
    for a in range(0, 360, 15):
        g.append(f'<line x1="640" y1="1780" x2="{640 + 435 * math.cos(math.radians(a)):.0f}" y2="{1780 + 435 * math.sin(math.radians(a)):.0f}" stroke="#a8aeb4" stroke-width="5"/>')
    g.append('<path d="M 120,1340 A 520 520 0 0 1 1160,1360" stroke="#1d1d1d" stroke-width="26" fill="none"/>')
    g.append('<path d="M 640,1780 L 140,1230 M 640,1780 L 60,1820 M 140,1230 L 60,1820" stroke="#141414" stroke-width="40"/>')
    g.append('<path d="M 120,1160 Q 40,1120 -40,1150 L -40,1210 Q 60,1190 140,1230 Z" fill="#3a2a1a" stroke="#111" stroke-width="7"/>')
    g.append('<path d="M 200,1190 L 1080,1190 M 200,1230 L 1080,1230 M 230,1190 L 640,1780 M 960,1190 L 900,1500" stroke="#3a3a3a" stroke-width="16"/>')
    for x in range(260, 1080, 70):
        g.append(f'<line x1="{x}" y1="1190" x2="{x}" y2="1230" stroke="#3a3a3a" stroke-width="8"/>')
    g.append('</g>')
    stack = [(leaf_parcel, 400, 1186, 2.2, 0.2), (tiffin, 680, 1186, 2.2, 0.8), (leaf_parcel, 940, 1186, 2.2, 1.4)]
    top = ""
    for fn, x, y, s, t0 in stack:
        r = land(t, t0, 0.35, 900)
        if r:
            top += f'<g transform="translate(0 {r[0]:.0f})">{fn(x, y, s)}</g>'
    tie = ease((t - 2.1) / 0.5)
    if tie > 0:
        top += f'<path d="M 260,1110 Q {260 + 420 * tie:.0f},{1080:.0f} {260 + 840 * tie:.0f},1110" stroke="#e8d5a0" stroke-width="18" fill="none" stroke-linecap="round"/>'
    lay = svg_rgba("".join(g) + top)
    lay[..., :3] *= np.array(cfg.get("tint", [1.0, 0.95, 0.85]))
    return D.over(bg, lay)


def scene_entrance(t, cfg, bg):
    g = ""
    for k, (fn, x, s) in enumerate(((leaf_parcel, 450, 0.9), (tiffin, 543, 0.9), (leaf_parcel, 636, 0.9))):
        r = land(t, 0.3 + k * 0.6, 0.3, 500)
        if r:
            g += f'<g transform="translate(0 {r[0]:.0f})">{fn(x, 1357, s)}</g>'
    if t > 2.3:
        g += D.sparkle_svg(t, 8, 3, (380, 1150, 720, 1380))
    return D.over(bg, svg_rgba(g))


class Lamps:
    def __init__(self, cfg, base):
        self.cfg = cfg
        self.bg = plate_img(base / cfg["bg"])

    def frame(self, t):
        img = self.bg.copy()
        prm = {k: v for k, v in self.cfg.get("lights", {}).items()}
        D.draw_lights(img, t, prm, K=1.5, rgb_order="rgb")
        if self.cfg.get("fireworks"):
            m = self.cfg.get("fw_mask_y", 760)
            sky = img[:m].copy()
            D.fireworks(sky, t, self.cfg["fireworks"], self.cfg.get("fw_scale", 1.0))
            img[:m] = sky
        return img


SCENES = {"unpack": scene_unpack, "cook": scene_cook, "pack": scene_pack, "load": scene_load, "entrance": scene_entrance}


def main():
    out, cfg_path = sys.argv[1], Path(sys.argv[2])
    cfg = json.loads(cfg_path.read_text())
    base = cfg_path.parent
    fps = cfg.get("fps", 25)
    mode = cfg["mode"]
    obj = Lamps(cfg, base) if mode in ("lamps", "finale") else None
    bg = None
    if not obj:
        bg = plate_img(base / cfg["bg"], cfg.get("blur", 12), cfg.get("dark", 0.8), cfg.get("bg_tint", (1, 1, 1))) if cfg.get("bg") else np.zeros((H, W, 3), np.float32)
    cams = cfg.get("camera", [[0, H / 2, H]])
    still = cfg.get("still")
    ff = None if still is not None else subprocess.Popen(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-framerate", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    n = round(cfg["duration"] * fps)
    for i in ([0] if still is not None else range(n)):
        t = still if still is not None else i / fps
        img = obj.frame(t) if obj else SCENES[mode](t, cfg, bg)
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
