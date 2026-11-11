"""Harvest-season cut-aways (One-Acre Challenge Ep 8 – the finale). 1080x1920, no words.

Props (SVG, any coords): brinjal_fruit, fruiting_brinjal (a grown bush with purple fruits and a flower), basket,
fence (sticks + rope round a patch in perspective).

python tools/toon/finale.py OUT.mp4 TIMING.json   ("still": t renders one PNG)
    goataway: cfg "bg" field plate: the goat turns and trots off to the right, out of frame (guided away).
    fence:    side view at soil level: the seedling patch; sticks drop in one by one and a rope wraps round them.
    tend:     side view, time-lapse: days race past; a weed pops up and is plucked (puff), the soil darkens when watered
              only when it looks dry; the seedlings grow into bushes, flower, and bear purple brinjals.
    pick:     close-up: ripe brinjals come off the plant one by one and land in a wicker basket, which fills.
    ledger:   his notebook: pictograms – basket of brinjals with tally marks, coin stacks (spent vs earned, earned taller),
              a little jar of seeds set aside with a heart, a smiling sun – ticked.
    beyond:   cfg "bg" field plate: the camera pans from his fenced patch to an empty plot beyond; faint dream crops
              (tomato, banana, beans) shimmer in over it and fade.
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
from sow import goat, seedling  # noqa: E402

W, H = 1080, 1920


def svg_rgba(body, w=W, h=H):
    png = cairosvg.svg2png(bytestring=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">{body}</svg>'.encode())
    return np.array(Image.open(io.BytesIO(png)).convert("RGBA")).astype(np.float32)


def over(rgb, rgba):
    a = rgba[..., 3:4] / 255
    return rgb * (1 - a) + rgba[..., :3] * a


def ease(u):
    u = min(max(u, 0), 1)
    return u * u * (3 - 2 * u)


def plate(base, cfg):
    return np.array(Image.open(base / cfg["bg"]).convert("RGB").resize((W, H), Image.LANCZOS)).astype(np.float32)


# ---------------------------------------------------------------- props

def brinjal_fruit(x, y, s=1.0, ang=0.0):
    return (f'<g transform="translate({x:.1f} {y:.1f}) rotate({ang:.1f}) scale({s:.3f})">'
            '<path d="M 0,0 C 36,8 44,110 0,140 C -44,110 -36,8 0,0 Z" fill="#5b2a86" stroke="#2a1040" stroke-width="5"/>'
            '<path d="M -10,20 C -18,56 -16,96 -6,116" stroke="#b48ad8" stroke-width="8" fill="none" opacity="0.6" stroke-linecap="round"/>'
            '<path d="M -26,8 L 0,-14 L 26,8 L 12,18 L 0,6 L -12,18 Z" fill="#3f8a2a" stroke="#1d4a12" stroke-width="4"/>'
            '<path d="M 0,-14 L 0,-34" stroke="#3f8a2a" stroke-width="8" stroke-linecap="round"/></g>')


def flower(x, y, s=1.0):
    return (f'<g transform="translate({x:.0f} {y:.0f}) scale({s:.3f})">'
            + "".join(f'<ellipse cx="{14 * math.cos(a):.1f}" cy="{14 * math.sin(a):.1f}" rx="12" ry="7" fill="#b39ddb" stroke="#5e35b1" stroke-width="2" transform="rotate({math.degrees(a):.0f} {14 * math.cos(a):.1f} {14 * math.sin(a):.1f})"/>'
                      for a in np.linspace(0, 2 * math.pi, 5, endpoint=False)) +
            '<circle r="7" fill="#fdd835"/></g>')


def fruiting_brinjal(x, y, s=1.0, seed=0, fruits=3, flowers=1, sway=0.0):
    g = brinjal(x, y, s, seed, sway)
    for k in range(fruits):
        fx = x + s * (-60 + 120 * ((k * 0.37 + seed * 0.13) % 1))
        fy = y - s * (120 + 70 * (k % 2))
        g += brinjal_fruit(fx, fy, 0.42 * s, 10 * (1 if k % 2 else -1))
    for k in range(flowers):
        g += flower(x + s * (40 - 80 * k), y - s * 250, 0.9 * s)
    return g


def basket(x, y, s=1.0, fill=1.0, seed=3):
    """A wicker basket standing at (x, y) (bottom centre), heaped with brinjals by `fill` (0..1)."""
    rng = np.random.default_rng(seed)
    g = [f'<g transform="translate({x:.0f} {y:.0f}) scale({s:.3f})">',
         '<path d="M -150,-170 Q 0,-330 150,-170" stroke="#8d5a2b" stroke-width="16" fill="none"/>',
         '<path d="M -150,-170 Q 0,-330 150,-170" stroke="#c49a5a" stroke-width="6" fill="none"/>']
    n = int(round(9 * fill))
    for k in range(n):
        bx = -110 + 220 * ((k * 0.41) % 1)
        by = -170 - 30 * (k // 4) + rng.uniform(-8, 8)
        g.append(brinjal_fruit(bx, by - 60, 0.55, rng.uniform(-70, 70)))
    g.append('<path d="M -160,-170 L 160,-170 L 130,0 L -130,0 Z" fill="#c49a5a" stroke="#6d4320" stroke-width="7"/>')
    for k in range(6):
        g.append(f'<path d="M {-150 + 5 * k},{-140 + 26 * k} L {150 - 5 * k},{-140 + 26 * k}" stroke="#8d5a2b" stroke-width="5"/>')
    for k in range(9):
        g.append(f'<path d="M {-140 + 35 * k},-168 L {-115 + 29 * k},-2" stroke="#a87a40" stroke-width="4"/>')
    g.append('<rect x="-166" y="-182" width="332" height="20" rx="8" fill="#a87a40" stroke="#6d4320" stroke-width="5"/></g>')
    return "".join(g)


def fence(pts, s=1.0, p=1.0, rope=1.0):
    """Sticks at each point (base points, perspective scale per point in pts as (x, y, sc)); rope through them."""
    g = ""
    vis = [q for i, q in enumerate(pts) if p * len(pts) > i]
    for x, y, sc in vis:
        h = 120 * sc * s
        g += (f'<path d="M {x:.0f},{y:.0f} L {x + 4 * sc:.0f},{y - h:.0f}" stroke="#5d3a1a" stroke-width="{12 * sc * s:.1f}" stroke-linecap="round"/>'
              f'<path d="M {x - 2:.0f},{y - 4:.0f} L {x + 2 * sc:.0f},{y - h:.0f}" stroke="#8d5a2b" stroke-width="{5 * sc * s:.1f}" stroke-linecap="round"/>')
    if rope > 0 and len(vis) > 1:
        ring = vis + [vis[0]] if len(vis) == len(pts) else vis
        for lvl in (0.45, 0.8):
            d = "M " + " L ".join(f"{x + 3 * sc:.0f},{y - 120 * sc * s * lvl:.0f}" for x, y, sc in ring)
            L = 3000
            g += f'<path d="{d}" stroke="#e8d5a0" stroke-width="{4 * s:.1f}" fill="none" stroke-dasharray="{L * rope:.0f} {L}"/>'
    return g


# ---------------------------------------------------------------- scenes

def scene_goataway(t, cfg, bg):
    u = ease((t - 0.3) / 1.6)
    x = 640 + 700 * u
    flip = t > 0.3
    g = goat(0, 0, 1.0, t, walk=0 < u < 1)
    tr = f'translate({x:.0f} 1560) scale(-1 1)' if flip else f'translate({x:.0f} 1560)'
    return over(bg, svg_rgba(f'<g transform="{tr}">{g}</g>'))


def soil_side(seed=4):
    rng = np.random.default_rng(seed)
    g = ['<defs><linearGradient id="sk" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7cc8ff"/><stop offset="1" stop-color="#dff3ff"/></linearGradient></defs>',
         '<rect width="1080" height="1920" fill="url(#sk)"/>',
         '<path d="M 0,980 Q 300,930 540,960 Q 800,990 1080,940 L 1080,1120 L 0,1120 Z" fill="#7cb342"/>',
         '<rect y="1120" width="1080" height="800" fill="#6b4226"/>']
    for _ in range(90):
        g.append(f'<ellipse cx="{rng.uniform(0, 1080):.0f}" cy="{rng.uniform(1130, 1900):.0f}" rx="{rng.uniform(8, 22):.0f}" ry="{rng.uniform(4, 10):.0f}" fill="{rng.choice(["#8a5a34", "#5a361e"])}"/>')
    g.append('<path d="M 0,1120 L 1080,1120" stroke="#4a2e18" stroke-width="10"/>')
    return "".join(g)


PLANTS = (200, 420, 640, 860)
POSTS = [(70, 1150, 1.6), (300, 1150, 1.6), (540, 1150, 1.6), (780, 1150, 1.6), (1010, 1150, 1.6)]


def scene_fence(t, cfg):
    g = [soil_side()]
    for x in PLANTS:
        g.append(seedling(x, 1124, 0.85, 1.6))
    p = ease((t - 0.2) / 1.6)
    for i, (x, y, sc) in enumerate(POSTS):
        q = ease((t - 0.2 - i * 0.3) / 0.25)
        if q > 0:
            dy = -500 * (1 - q)
            g.append(fence([(x, y + dy, sc)], 1.5))
    r = ease((t - 1.9) / 1.0)
    if r > 0:
        for lvl in (0.45, 0.8):
            yy = 1150 - 120 * 1.6 * 1.5 * lvl
            g.append(f'<path d="M 60,{yy:.0f} L {60 + 960 * r:.0f},{yy:.0f}" stroke="#e8d5a0" stroke-width="7"/>')
            for x, _, _ in POSTS:
                if 60 + 960 * r > x:
                    g.append(f'<circle cx="{x + 4}" cy="{yy:.0f}" r="9" fill="none" stroke="#e8d5a0" stroke-width="5"/>')
    return svg_rgba("".join(g))[..., :3]


def scene_tend(t, cfg):
    dur = cfg.get("duration", 6.0)
    day = t / dur * 6
    ph = day % 1
    sun = math.sin(math.pi * min(1, ph / 0.7)) if ph < 0.7 else 0
    g = [soil_side()]
    shade = 0.6 + 0.4 * sun
    if ph < 0.7:
        a = math.pi * ph / 0.7
        g.append(f'<circle cx="{540 - 460 * math.cos(a):.0f}" cy="{960 - 700 * math.sin(a):.0f}" r="64" fill="#ffd54f"/>')
    grow = ease(t / dur)
    for i, x in enumerate(PLANTS):
        if grow < 0.15:
            g.append(seedling(x, 1124, 0.85 + grow, 1.6))
        else:
            s = 0.35 + 0.75 * (grow - 0.15) / 0.85
            fr = int(3 * ease((grow - 0.7) / 0.3))
            fl = 1 if 0.5 < grow < 0.95 else 0
            g.append(fruiting_brinjal(x, 1124, s, i + 3, fr, fl, 2 * math.sin(t * 2 + i)))
    for x, y, sc in POSTS:
        g.append(fence([(x, y, sc)], 1.5))
    for lvl in (0.45, 0.8):
        yy = 1150 - 120 * 1.6 * 1.5 * lvl
        g.append(f'<path d="M 60,{yy:.0f} L 1020,{yy:.0f}" stroke="#e8d5a0" stroke-width="7"/>')
    for k, (wx, t0) in enumerate(((310, 1.2), (740, 3.0))):           # weeds pop up, then are plucked (puff)
        u = (t - t0) / 0.8
        if 0 < u < 1:
            hgt = 70 * min(1, u * 2)
            g.append(f'<path d="M {wx},{1122} q -16,{-hgt * 0.6:.0f} -26,{-hgt:.0f} M {wx},{1122} q 4,{-hgt * 0.7:.0f} 14,{-hgt:.0f} M {wx},{1122} q 14,{-hgt * 0.4:.0f} 30,{-hgt * 0.8:.0f}" stroke="#9e9d24" stroke-width="6" fill="none"/>')
        elif 1 <= u < 1.5:
            v = (u - 1) / 0.5
            g.append(f'<path d="M {wx},{1122 - 180 * v:.0f} q -16,-42 -26,-70 M {wx},{1122 - 180 * v:.0f} q 4,-49 14,-70" stroke="#9e9d24" stroke-width="6" fill="none" opacity="{1 - v:.2f}"/>')
            g += [f'<circle cx="{wx + 40 * math.cos(a) * v:.0f}" cy="{1118 - 30 * math.sin(a) * v:.0f}" r="{8 * (1 - v) + 2:.0f}" fill="#8a5a34"/>' for a in (0.4, 1.2, 2.0, 2.7)]
    for t0 in (2.2, 4.6):                                               # watering only on the dry days
        u = (t - t0) / 0.6
        if 0 < u < 1:
            rr = np.random.default_rng(int(t * 25))
            g += [f'<line x1="{x:.0f}" y1="{y:.0f}" x2="{x - 5:.0f}" y2="{y + 36:.0f}" stroke="#d6eefe" stroke-width="5" opacity="0.85"/>'
                  for x, y in zip(rr.uniform(120, 960, 40), rr.uniform(700, 1100, 40))]
    img = svg_rgba("".join(g))[..., :3]
    return img * (0.65 + 0.35 * shade)


def scene_pick(t, cfg):
    g = ['<defs><radialGradient id="pb" cx="0.5" cy="0.4" r="0.8"><stop offset="0" stop-color="#d9efb0"/><stop offset="1" stop-color="#7fae5a"/></radialGradient></defs>',
         '<rect width="1080" height="1920" fill="url(#pb)"/>', '<rect y="1500" width="1080" height="420" fill="#6b4226"/>']
    g.append(f'<g transform="translate(330 1520) scale(2.6) translate(-330 -1520)">{brinjal(330, 1520, 1.0, 7)}</g>')
    spots = [(250, 1090, -12), (420, 980, 14), (300, 830, -8), (470, 1180, 6)]
    picked = 0
    for k, (x, y, a) in enumerate(spots):
        t0 = 0.4 + 0.7 * k
        u = (t - t0) / 0.5
        if u < 0:
            g.append(brinjal_fruit(x, y, 1.2, a))
        elif u < 1:                                                       # arc into the basket
            bx, by = 800, 1380
            xx = x + (bx - x) * u
            yy = y + (by - y) * u - 260 * math.sin(math.pi * u)
            g.append(brinjal_fruit(xx, yy, 1.2 - 0.4 * u, a + 300 * u))
        else:
            picked += 1
    g.append(basket(800, 1640, 1.4, 0.2 + 0.8 * picked / 4))
    if picked:
        g.append(f'<g opacity="{0.5 + 0.5 * math.sin(t * 6):.2f}">' + "".join(
            f'<path d="M {x},{y - 16} L {x + 4},{y} L {x},{y + 16} L {x - 4},{y} Z M {x - 16},{y} L {x},{y + 4} L {x + 16},{y} L {x},{y - 4} Z" fill="#fffde7"/>'
            for x, y in ((700, 1180), (920, 1220), (810, 1120))) + '</g>')
    return svg_rgba("".join(g))[..., :3]


def scene_ledger(t, cfg):
    from fortune import coin
    g = ['<rect width="1080" height="1920" fill="#6d4c33"/>',
         '<g transform="rotate(-3 540 960)"><rect x="90" y="200" width="900" height="1520" rx="18" fill="#fbf8ee" stroke="#8a7a5a" stroke-width="8"/>']
    for k in range(14):
        g.append(f'<line x1="130" y1="{320 + k * 100}" x2="950" y2="{320 + k * 100}" stroke="#9ec3e6" stroke-width="4"/>')
    for k in range(9):
        g.append(f'<circle cx="90" cy="{280 + k * 170}" r="22" fill="none" stroke="#888" stroke-width="8"/>')
    steps = [0.2, 1.4, 2.6, 3.8]
    pen = None
    u = ease((t - steps[0]) / 1.0)                        # 1. harvest: basket + tally marks
    if u > 0:
        g.append(f'<g opacity="{min(1, u * 2):.2f}">{basket(260, 560, 0.75, 1.0)}</g>')
        n = int(12 * u)
        for k in range(n):
            x = 430 + 34 * (k % 5) + 200 * (k // 5)
            if k % 5 == 4:
                g.append(f'<path d="M {x - 140},{420} L {x + 6},{500}" stroke="#2a2a2a" stroke-width="8"/>')
            else:
                g.append(f'<path d="M {x},{410} L {x},{510}" stroke="#2a2a2a" stroke-width="8"/>')
        if u < 1:
            pen = (430 + 34 * (n % 5) + 200 * (n // 5), 500)
    u = ease((t - steps[1]) / 1.0)                        # 2. spent (short stack, red) vs earned (tall stack, green)
    if u > 0:
        for k in range(int(3 * u)):
            g.append(coin(280, 900 - 30 * k, 1.4))
        for k in range(int(7 * u)):
            g.append(coin(560, 900 - 30 * k, 1.4))
        g.append(f'<path d="M 230,960 L 330,960" stroke="#d32f2f" stroke-width="10" opacity="{u:.2f}"/>')
        g.append(f'<path d="M 510,960 L 610,960" stroke="#2e7d32" stroke-width="10" opacity="{u:.2f}"/>')
        g.append(f'<path d="M 700,820 l 70,-70 l 70,70" stroke="#2e7d32" stroke-width="14" fill="none" opacity="{u:.2f}" stroke-linecap="round"/>')
        if u < 1:
            pen = (560, 900 - 30 * int(7 * u))
    u = ease((t - steps[2]) / 1.0)                        # 3. seeds set aside for next season
    if u > 0:
        g.append(f'<g opacity="{min(1, u * 2):.2f}"><path d="M 220,1300 L 220,1140 Q 220,1110 250,1110 L 370,1110 Q 400,1110 400,1140 L 400,1300 Q 310,1330 220,1300 Z" fill="#e3f2fd" stroke="#546e7a" stroke-width="7"/>'
                 '<rect x="232" y="1080" width="156" height="36" rx="8" fill="#8d6e63" stroke="#4e342e" stroke-width="5"/>'
                 + "".join(f'<ellipse cx="{250 + 26 * (k % 6)}" cy="{1280 - 22 * (k // 6)}" rx="10" ry="7" fill="#efe0b0" stroke="#8a7a40" stroke-width="2"/>' for k in range(24)) +
                 '<path d="M 520,1210 C 490,1180 470,1150 500,1130 C 520,1120 540,1140 540,1150 C 540,1140 560,1120 580,1130 C 610,1150 590,1180 560,1210 L 540,1230 Z" fill="#e53935"/></g>')
        if u < 1:
            pen = (520, 1230)
    u = ease((t - steps[3]) / 0.8)                        # 4. a big tick
    if u > 0:
        g.append(f'<path d="M 680,1460 l {50 * min(1, u * 2):.0f},{50 * min(1, u * 2):.0f} l {120 * max(0, u * 2 - 1):.0f},{-150 * max(0, u * 2 - 1):.0f}" stroke="#2e7d32" stroke-width="22" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
        if u < 1:
            pen = (730 + 120 * max(0, u * 2 - 1), 1510 - 150 * max(0, u * 2 - 1))
    g.append('</g>')
    if pen:
        x, y = pen
        g.append(f'<g transform="translate({x:.0f} {y:.0f}) rotate(35)"><rect x="-14" y="-420" width="28" height="380" fill="#fbc02d" stroke="#5a4a00" stroke-width="4"/>'
                 '<path d="M -14,-40 L 14,-40 L 0,0 Z" fill="#f2d2a0" stroke="#5a4a00" stroke-width="3"/><path d="M -4,-12 L 4,-12 L 0,0 Z" fill="#333"/>'
                 '<rect x="-14" y="-440" width="28" height="24" fill="#e57373"/></g>')
    return svg_rgba("".join(g))[..., :3]


def scene_beyond(t, cfg, bg):
    u = ease((t - 2.0) / 1.2) - ease((t - cfg.get("duration", 5) + 0.6) / 0.6)
    rng0 = np.random.default_rng(9)                          # the empty plot beyond his field: bare, un-tilled ground
    plot = ('<path d="M 0,905 Q 540,885 1080,900 L 1080,1080 Q 540,1060 0,1080 Z" fill="#a8774a"/>'
            '<path d="M 0,905 Q 540,885 1080,900" stroke="#7a5534" stroke-width="5" fill="none"/>'
            + "".join(f'<ellipse cx="{rng0.uniform(0, 1080):.0f}" cy="{rng0.uniform(915, 1070):.0f}" rx="{rng0.uniform(6, 18):.0f}" ry="{rng0.uniform(2, 5):.0f}" fill="#8d6239"/>' for _ in range(70))
            + "".join(f'<path d="M {x:.0f},{y:.0f} l -4,-10 M {x:.0f},{y:.0f} l 3,-12" stroke="#b5a04a" stroke-width="2.5"/>' for x, y in zip(rng0.uniform(0, 1080, 30), rng0.uniform(920, 1075, 30))))
    bg = over(bg, svg_rgba(plot))
    g = ""
    if u > 0:
        rng = np.random.default_rng(6)
        for k in range(14):
            x, y = rng.uniform(60, 1020), rng.uniform(930, 1070)
            s = 0.35 + (y - 930) / 400
            kind = k % 3
            if kind == 0:                                   # tomato bush
                g += (f'<g transform="translate({x:.0f} {y:.0f}) scale({s:.2f})"><path d="M 0,0 L 0,-90" stroke="#558b2f" stroke-width="10"/>'
                      '<circle cx="-30" cy="-80" r="34" fill="#7cb342"/><circle cx="26" cy="-96" r="30" fill="#8bc34a"/>'
                      '<circle cx="-18" cy="-60" r="14" fill="#e53935"/><circle cx="20" cy="-70" r="12" fill="#e53935"/></g>')
            elif kind == 1:                                 # banana plant
                g += (f'<g transform="translate({x:.0f} {y:.0f}) scale({s:.2f})"><path d="M 0,0 L 0,-140" stroke="#8d6e3f" stroke-width="18"/>'
                      '<path d="M 0,-140 Q -90,-180 -120,-100 M 0,-140 Q 90,-190 130,-110 M 0,-140 Q -20,-230 30,-250" stroke="#66bb6a" stroke-width="30" fill="none" stroke-linecap="round"/></g>')
            else:                                           # beans on a stick
                g += (f'<g transform="translate({x:.0f} {y:.0f}) scale({s:.2f})"><path d="M 0,0 L 0,-160" stroke="#8d6e3f" stroke-width="6"/>'
                      + "".join(f'<ellipse cx="{10 * (1 if j % 2 else -1)}" cy="{-30 - 30 * j}" rx="16" ry="9" fill="#7cb342"/>' for j in range(5)) + '</g>')
        g = f'<g opacity="{0.75 * u:.2f}">{g}</g>' + "".join(
            f'<path d="M {x},{y - 14} L {x + 4},{y} L {x},{y + 14} L {x - 4},{y} Z M {x - 14},{y} L {x},{y + 4} L {x + 14},{y} L {x},{y - 4} Z" fill="#fffde7" opacity="{u * (0.5 + 0.5 * math.sin(t * 5 + x)):.2f}"/>'
            for x, y in ((200, 860), (520, 900), (860, 870), (380, 960), (760, 950)))
    return over(bg, svg_rgba(g))


def main():
    out, cfg_path = sys.argv[1], Path(sys.argv[2])
    cfg = json.loads(cfg_path.read_text())
    base = cfg_path.parent
    fps = cfg.get("fps", 25)
    mode = cfg["mode"]
    bg = plate(base, cfg) if cfg.get("bg") else None
    cams = cfg.get("camera", [[0, H / 2, H]])
    still = cfg.get("still")
    ff = None if still is not None else subprocess.Popen(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-framerate", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i in ([0] if still is not None else range(round(cfg["duration"] * fps))):
        t = still if still is not None else i / fps
        if mode in ("goataway", "beyond"):
            img = (scene_goataway if mode == "goataway" else scene_beyond)(t, cfg, bg)
        else:
            img = {"fence": scene_fence, "tend": scene_tend, "pick": scene_pick, "ledger": scene_ledger}[mode](t, cfg)
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
