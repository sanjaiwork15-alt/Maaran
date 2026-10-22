"""Paddy and rice (nel, arisi) – plants, panicles, grains, a bowl of rice, the vayal plate – and the Ep 5 cut-aways.

Usage:
    python tools/toon/rice.py OUT.mp4 TIMING.json

TIMING.json: {"mode": "field" | "grain" | "harvest" | "thresh" | "dry" | "mill" | "plate", "duration": 3, "fps": 25,
              "span": [t0, t1], "camera": [[t, cy, h], ...]}
field:   golden paddy close-up swaying in the breeze (panicles bending with ripe grain).
grain:   one paddy grain, big: the golden husk (two halves) opens and falls away, the rice grain is inside.
harvest: a sickle cuts the stalks in a row; the cut paddy is laid in bundles.
thresh:  a bundle is beaten on a stone; grains fly off and pile up below, straw stays in the hand.
dry:     the grains spread in one thin layer on a mat in the sun, turning a drier, paler gold.
mill:    paddy goes into a rice mill: husk blows out at the side, white rice pours out into a sack.
plate:   white rice on a banana leaf.
Science (TNAU Agritech Portal, rice post-harvest technology; IRRI Rice Knowledge Bank): paddy is harvested when ~80 % of
the grains are straw-coloured, threshed to separate grain from straw, dried to ~14 % moisture, then milled: the husk
(hull) is removed (brown rice) and polishing removes the bran to give white rice.
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import cairosvg
import numpy as np

W, H = 1080, 1920
OUT = "#3a2a10"


def mix(c1, c2, u):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    u = min(max(u, 0), 1)
    return "#" + "".join(f"{round(x + (y - x) * u):02x}" for x, y in zip(a, b))


def ease(u):
    u = min(max(u, 0), 1)
    return u * u * (3 - 2 * u)


def grain(x, y, ang, s, kind="paddy"):
    """kind: paddy (golden husk with a tiny tip), white (milled rice)."""
    if kind == "white":
        return (f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{7 * s:.1f}" ry="{3.2 * s:.1f}" fill="#fbf8ee" stroke="#b9ad8c" '
                f'stroke-width="{0.9 * s:.1f}" transform="rotate({ang:.0f} {x:.1f} {y:.1f})"/>')
    return (f'<g transform="translate({x:.1f} {y:.1f}) rotate({ang:.0f})">'
            f'<path d="M {-8 * s:.1f},0 C {-6 * s:.1f},{-4.6 * s:.1f} {6 * s:.1f},{-4.6 * s:.1f} {9 * s:.1f},0 C {6 * s:.1f},{4.6 * s:.1f} '
            f'{-6 * s:.1f},{4.6 * s:.1f} {-8 * s:.1f},0 Z" fill="#d9a92e" stroke="{OUT}" stroke-width="{0.9 * s:.1f}"/>'
            f'<line x1="{-6 * s:.1f}" y1="0" x2="{7 * s:.1f}" y2="0" stroke="#b07f1c" stroke-width="{0.8 * s:.1f}"/>'
            f'<line x1="{9 * s:.1f}" y1="0" x2="{12 * s:.1f}" y2="0" stroke="#8a6a1a" stroke-width="{0.9 * s:.1f}"/></g>')


def panicle(x, y, L, ang, droop, s, ripe=1.0, n=14, seed=0):
    """A drooping paddy ear: a curved stalk end with grains along it. droop 0 upright .. 1 hanging."""
    rng = np.random.default_rng(seed)
    pts, px, py, a = [], x, y, ang
    for j in range(n + 1):
        pts.append((px, py, a))
        a = ang + droop * 140 * (j / n) ** 1.3 * (1 if math.cos(math.radians(ang)) >= 0 else -1)
        px += math.cos(math.radians(a)) * L / n
        py += math.sin(math.radians(a)) * L / n
    stalk = mix("#6fae3a", "#c9a447", ripe)
    d = "M " + " L ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in pts)
    g = [f'<path d="{d}" stroke="{stalk}" stroke-width="{2.2 * s:.1f}" fill="none" stroke-linecap="round"/>']
    col_g = "#8cc04a"
    for j in range(2, n + 1):
        px, py, a = pts[j]
        for side in (-1, 1):
            ga = a + side * 25 + rng.uniform(-8, 8)
            gx, gy = px + math.cos(math.radians(ga)) * 6 * s, py + math.sin(math.radians(ga)) * 6 * s
            if ripe >= 0.99:
                g.append(grain(gx, gy, ga, s * 0.8))
            else:
                g.append(f'<ellipse cx="{gx:.1f}" cy="{gy:.1f}" rx="{6 * s:.1f}" ry="{2.8 * s:.1f}" fill="{mix(col_g, "#d9a92e", ripe)}" '
                         f'stroke="{OUT}" stroke-width="{0.7 * s:.1f}" transform="rotate({ga:.0f} {gx:.1f} {gy:.1f})"/>')
    return "".join(g)


def plant(x, base, h, s=1.0, ripe=1.0, sway=0.0, seed=0, ears=3):
    """A paddy clump: long narrow leaves fanning from the base, a few ears on top bending over."""
    rng = np.random.default_rng(seed)
    g = []
    leaf_c = mix("#4f9a32", "#b9a24a", ripe * 0.75)
    for k in range(9):
        a = -90 + (k - 4) * 9 + rng.uniform(-4, 4) + sway * 4
        L = h * rng.uniform(0.7, 1.0)
        cx = x + math.cos(math.radians(a)) * L * 0.5 + sway * 10
        cy = base + math.sin(math.radians(a)) * L * 0.5
        ex = x + math.cos(math.radians(a + (k - 4) * 4)) * L + sway * 22
        ey = base + math.sin(math.radians(a + (k - 4) * 4)) * L
        w = 5 * s
        g.append(f'<path d="M {x - w:.1f},{base:.1f} Q {cx - w:.1f},{cy:.1f} {ex:.1f},{ey:.1f} Q {cx + w:.1f},{cy:.1f} {x + w:.1f},{base:.1f} Z" '
                 f'fill="{leaf_c}" stroke="#2f4a14" stroke-width="{1.1 * s:.1f}"/>')
    for e in range(ears):
        a = -90 + (e - (ears - 1) / 2) * 14 + sway * 5
        sx = x + math.cos(math.radians(a)) * h * 0.95 + sway * 24
        sy = base + math.sin(math.radians(a)) * h * 0.95
        g.append(f'<line x1="{x:.1f}" y1="{base:.1f}" x2="{sx:.1f}" y2="{sy:.1f}" stroke="{mix("#6fae3a", "#c9a447", ripe)}" '
                 f'stroke-width="{2.4 * s:.1f}"/>')
        g.append(panicle(sx, sy, h * 0.45, a + (25 if e % 2 else -25), 0.25 + 0.6 * ripe, s, ripe, seed=seed * 10 + e))
    return "".join(g)


def vayal(w=720, h=1280, horizon=600, ripe=0.85, seed=3):
    """A paddy field over the lower part of the plate: rows of clumps in perspective + a bund path (720x1280 coords)."""
    rng = np.random.default_rng(seed)
    g = [f'<rect x="0" y="{horizon}" width="{w}" height="{h - horizon}" fill="{mix("#6f9a35", "#b59a3e", ripe)}"/>']
    for k, y in enumerate(np.linspace(horizon + 8, h + 60, 22)):
        s = 0.18 + (y - horizon) / (h - horizon) * 1.25
        step = 26 * s + 6
        for x in np.arange(-20 + (k % 2) * step / 2, w + 30, step):
            g.append(plant(x + rng.uniform(-4, 4), y, 85 * s, s * 0.55, ripe, seed=int(x * 7 + y)))
    g.append(f'<path d="M {w * 0.62},{horizon} L {w * 0.7},{horizon} L {w * 1.05},{h} L {w * 0.78},{h} Z" fill="#9a6a3a" '
             f'stroke="#6b4423" stroke-width="2" opacity="0.9"/>')                     # the bund path
    return "".join(g)


def bowl_rice(x, y, s=1.0, seed=2):
    """A mound of white cooked rice (grains drawn on a soft mound) – drawn over a bowl's mouth at (x, y)."""
    rng = np.random.default_rng(seed)
    g = [f'<path d="M {x - 95 * s:.1f},{y:.1f} Q {x - 70 * s:.1f},{y - 70 * s:.1f} {x:.1f},{y - 78 * s:.1f} '
         f'Q {x + 70 * s:.1f},{y - 70 * s:.1f} {x + 95 * s:.1f},{y:.1f} Z" fill="#fbf8ee" stroke="#c9bfa0" stroke-width="{2 * s:.1f}"/>']
    for _ in range(70):
        u = rng.uniform(-0.9, 0.9)
        gx = x + u * 90 * s
        top = y - 74 * s * (1 - u * u)
        gy = rng.uniform(top + 6 * s, y - 4 * s)
        g.append(grain(gx, gy, rng.uniform(0, 180), s * 0.9, "white"))
    return "".join(g)


def sheaf(x, y, s=1.0, seed=4, ripe=1.0, top=150, ears=7):
    """A bunch of cut paddy stalks gripped at (x, y): stems below and above, ears drooping over the top."""
    rng = np.random.default_rng(seed)
    g = []
    stem = mix("#7fae3a", "#c9a447", ripe)
    for k in range(11):
        dx = (k - 5) * 3.2 * s
        g.append(f'<line x1="{x + dx * 0.4:.1f}" y1="{y + 70 * s:.1f}" x2="{x + dx * 1.6:.1f}" y2="{y - top * s:.1f}" stroke="{OUT}" '
                 f'stroke-width="{4 * s:.1f}"/><line x1="{x + dx * 0.4:.1f}" y1="{y + 70 * s:.1f}" x2="{x + dx * 1.6:.1f}" '
                 f'y2="{y - top * s:.1f}" stroke="{stem}" stroke-width="{2.6 * s:.1f}"/>')
    for k in range(ears):
        c = (ears - 1) / 2
        sx = x + (k - c) * 6 * s
        g.append(panicle(sx, y - top * s, 110 * s, -90 + (k - c) * 14 + rng.uniform(-5, 5), 0.85, s, ripe, n=12, seed=seed + k))
    return "".join(g)


def leaf_plate(x, y, s=1.0):
    return (f'<path d="M {x - 300 * s:.1f},{y:.1f} Q {x - 280 * s:.1f},{y - 90 * s:.1f} {x:.1f},{y - 100 * s:.1f} Q {x + 300 * s:.1f},{y - 90 * s:.1f} '
            f'{x + 320 * s:.1f},{y:.1f} Q {x + 300 * s:.1f},{y + 90 * s:.1f} {x:.1f},{y + 100 * s:.1f} Q {x - 280 * s:.1f},{y + 90 * s:.1f} '
            f'{x - 300 * s:.1f},{y:.1f} Z" fill="#3f9b3a" stroke="#1f5a1a" stroke-width="{5 * s:.1f}"/>'
            f'<line x1="{x - 290 * s:.1f}" y1="{y:.1f}" x2="{x + 310 * s:.1f}" y2="{y:.1f}" stroke="#7cc46a" stroke-width="{6 * s:.1f}"/>')


# ---------------------------------------------------------------- cut-aways

def sky_bg(ground="#b59a3e"):
    return ('<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9fd3f2"/>'
            '<stop offset="1" stop-color="#fbe9b8"/></linearGradient></defs>'
            f'<rect width="{W}" height="{H}" fill="url(#sky)"/><rect y="1200" width="{W}" height="{H - 1200}" fill="{ground}"/>')


def scene(t, cfg):
    mode, span = cfg["mode"], cfg["span"]
    p = ease((t - span[0]) / (span[1] - span[0]))
    sw = math.sin(t * 1.6)
    g = []
    if mode == "field":
        g.append(sky_bg())
        for k, (x, s) in enumerate([(160, 2.6), (420, 3.0), (700, 2.7), (950, 2.9), (300, 3.6), (820, 3.6)]):
            base = 1400 if s < 3.5 else 1700
            g.append(plant(x, base, 340 * s / 2.6, s, 1.0, sway=math.sin(t * 1.6 + k) * 0.9, seed=40 + k))
    elif mode == "grain":
        g.append('<rect width="1080" height="1920" fill="#f6ead0"/>')
        s = 32
        open_ = ease((p - 0.15) / 0.6)
        g.append('<g transform="translate(540 960) rotate(-20)">')
        g.append(f'<ellipse cx="0" cy="0" rx="{7 * s * 0.92:.0f}" ry="{3.2 * s * 0.92:.0f}" fill="#fbf6e6" stroke="#b9ad8c" stroke-width="6"/>')
        g.append(f'<path d="M {-5 * s},{-0.8 * s} Q 0,{-1.6 * s} {5 * s},{-0.8 * s}" stroke="#e8dfc4" stroke-width="8" fill="none"/>')
        for side in (-1, 1):                                  # the two husk halves (lemma and palea) open and fall away
            dy, rot = side * (90 * open_ + 260 * open_ ** 2), side * 30 * open_
            g.append(f'<clipPath id="h{side + 1}"><rect x="-400" y="{-300 if side < 0 else 0}" width="800" height="300"/></clipPath>'
                     f'<g transform="translate(0 {dy:.0f}) rotate({rot:.0f})" opacity="{1 - 0.5 * open_:.2f}">'
                     f'<g clip-path="url(#h{side + 1})">{grain(0, 0, 0, s * 1.08)}</g></g>')
        g.append('</g>')
    elif mode == "harvest":
        g.append(sky_bg())
        cut = p * 1100 - 60
        for k in range(9):
            x = 80 + k * 115
            fall = ease((cut - x) / 140)                      # cut stalks fall over, ears to the right
            g.append(f'<g transform="rotate({80 * fall:.0f} {x} 1400)">{plant(x, 1400, 380, 2.2, 1.0, sway=sw * 0.5 * (1 - fall), seed=60 + k)}</g>')
        a = -60 + 70 * abs(math.sin(t * 5))                   # the sickle swinging along the row
        g.append(f'<g transform="translate({cut + 40:.0f} 1330) rotate({a:.0f})"><path d="M 0,0 Q 90,-10 110,60 Q 70,10 0,22 Z" fill="#cfd6dc" '
                 f'stroke="#2c3238" stroke-width="5"/><rect x="-80" y="2" width="82" height="18" rx="8" fill="#7a4a24" stroke="#2c1a0c" stroke-width="4"/></g>')
    elif mode == "thresh":
        g.append(sky_bg("#c99a5a"))
        g.append('<rect x="300" y="1150" width="480" height="140" rx="30" fill="#8d8a84" stroke="#3a3833" stroke-width="8"/>')
        hit = abs(math.sin(t * 3.2))
        g.append(f'<g transform="rotate({25 + 55 * hit:.0f} 330 1120)">{sheaf(330, 1050, 2.0, seed=2, ripe=1.0)}</g>')
        rng = np.random.default_rng(7)
        for k in range(60):                                    # grains flying off and piling up
            ph = (t * 1.3 + k / 60) % 1
            x0, y0 = 560 + rng.uniform(-80, 80), 1140
            vx, vy = rng.uniform(-260, 260), rng.uniform(-420, -180)
            x, y = x0 + vx * ph, y0 + vy * ph + 900 * ph * ph
            if y < 1500:
                g.append(grain(x, y, rng.uniform(0, 180), 2.2))
        pile = 40 + 120 * p
        g.append(f'<ellipse cx="540" cy="1560" rx="{220 + pile:.0f}" ry="{pile * 0.45:.0f}" fill="#d9a92e" stroke="{OUT}" stroke-width="4"/>')
    elif mode == "dry":
        g.append(sky_bg("#c99a5a"))
        g.append(f'<circle cx="880" cy="260" r="{90 + 6 * math.sin(t * 3):.0f}" fill="#ffd84a"/>')
        g.append('<rect x="80" y="1050" width="920" height="560" rx="20" fill="#d9b779" stroke="#3b2416" stroke-width="6"/>')
        rng = np.random.default_rng(3)
        col = "#d9a92e"
        for k in range(320):
            x, y = rng.uniform(110, 970), rng.uniform(1080, 1580)
            g.append(grain(x, y, rng.uniform(0, 180), 2.0).replace("#d9a92e", mix("#b9922a", "#e8c25a", p)))
        for k in range(8):                                     # moisture leaving
            ph = (t * 0.7 + k / 8) % 1
            g.append(f'<path d="M {150 + k * 105},{1060 - ph * 380:.0f} q 14,-22 0,-44 q -14,-22 0,-44" stroke="#ffffff" stroke-width="7" '
                     f'fill="none" stroke-opacity="{0.6 * (1 - ph) * (1 - 0.7 * p):.2f}"/>')
        _ = col
    elif mode == "mill":
        g.append('<rect width="1080" height="1920" fill="#e7dccb"/><rect y="1500" width="1080" height="420" fill="#a39a8c"/>')
        g.append('<path d="M 360,520 L 720,520 L 620,760 L 460,760 Z" fill="#c0392b" stroke="#3a1a14" stroke-width="8"/>')   # hopper
        g.append('<rect x="330" y="760" width="420" height="520" rx="24" fill="#2e6fa8" stroke="#13324d" stroke-width="8"/>')
        g.append('<circle cx="540" cy="1000" r="90" fill="#9fb8cc" stroke="#13324d" stroke-width="8"/>')
        g.append(f'<line x1="540" y1="1000" x2="{540 + 80 * math.cos(t * 9):.0f}" y2="{1000 + 80 * math.sin(t * 9):.0f}" stroke="#13324d" stroke-width="10"/>')
        g.append('<rect x="750" y="880" width="170" height="70" fill="#2e6fa8" stroke="#13324d" stroke-width="8"/>')       # husk outlet
        g.append('<rect x="470" y="1280" width="140" height="70" fill="#2e6fa8" stroke="#13324d" stroke-width="8"/>')       # rice outlet
        g.append('<path d="M 420,1420 L 660,1420 L 700,1760 L 380,1760 Z" fill="#efe3c4" stroke="#7a6a44" stroke-width="7"/>')   # sack
        rng = np.random.default_rng(9)
        for k in range(40):
            ph = (t * 1.1 + k / 40) % 1
            g.append(grain(540 + rng.uniform(-120, 120), 380 + ph * 200, rng.uniform(0, 180), 2.4))            # paddy in
            hx, hy = 920 + ph * 160, 915 + rng.uniform(-30, 30) - 80 * math.sin(ph * 3)
            g.append(f'<path d="M {hx:.0f},{hy:.0f} q 10,-6 20,0" stroke="#c9a447" stroke-width="5" fill="none" '
                     f'stroke-opacity="{1 - ph:.2f}"/>')                                                         # husk out
            g.append(grain(540 + rng.uniform(-30, 30), 1350 + ph * 140, rng.uniform(0, 180), 2.4, "white"))  # rice out
        level = 1700 - 200 * p
        g.append(f'<path d="M 395,1700 Q 540,{level - 40:.0f} 685,1700 Z" fill="#fbf8ee" stroke="#c9bfa0" stroke-width="4"/>')
    else:  # plate
        g.append('<rect width="1080" height="1920" fill="#b98a5a"/>')
        g.append(leaf_plate(540, 1050, 1.0))
        g.append(bowl_rice(540, 1100, 2.0 * (0.6 + 0.4 * ease(p * 2))))
    return "".join(g)


def main():
    out = sys.argv[1]
    cfg = json.loads(Path(sys.argv[2]).read_text())
    fps = cfg.get("fps", 25)
    n = round(cfg["duration"] * fps)
    cams = cfg.get("camera", [[0, H / 2, H]])
    only = cfg.get("still")
    ff = None if only is not None else subprocess.Popen(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "image2pipe", "-framerate", str(fps),
         "-i", "-", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i in ([0] if only is not None else range(n)):
        t = only if only is not None else i / fps
        cy = np.interp(t, [c[0] for c in cams], [c[1] for c in cams])
        h = np.interp(t, [c[0] for c in cams], [c[2] for c in cams])
        w = h * W / H
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
               f'viewBox="{W / 2 - w / 2:.1f} {cy - h / 2:.1f} {w:.1f} {h:.1f}">{scene(t, cfg)}</svg>')
        png = cairosvg.svg2png(bytestring=svg.encode())
        if ff is None:
            Path(out).write_bytes(png)
        else:
            ff.stdin.write(png)
    if ff:
        ff.stdin.close()
        ff.wait()
    print("saved", out)


if __name__ == "__main__":
    main()
