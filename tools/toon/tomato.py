"""Tomatoes (thakkali) – fruits at any ripeness, staked plants, a thottam (garden) plate – and the Ep 4 cut-aways.

Usage:
    python tools/toon/tomato.py OUT.mp4 TIMING.json

TIMING.json: {"mode": "ripen" | "pigment" | "stages" | "plant", "duration": 4, "fps": 25, "span": [t0, t1],
              "camera": [[t, cy, h], ...]}
ripen:   one tomato on the vine goes mature-green -> breaker -> turning -> pink -> light red -> red.
pigment: a magnified piece of tomato skin: green chlorophyll discs fade away while red pigment (lycopene) crystals
         build up (no labels: no on-screen text).
stages:  the six ripeness stages appear one after another along a vine (close-up).
plant:   a staked plant with green, turning and red fruit on one truss, swaying gently.
Science (TNAU Agritech Portal, tomato post-harvest; Grierson & Kader, in "The Tomato Crop", Chapman & Hall): flowers on
a truss open over days to weeks, so the fruits on one plant are at different ages; as each ripens, chlorophyll is broken
down and the red carotenoid lycopene (with orange beta-carotene) builds up – ripeness stages green, breaker, turning,
pink, light red, red.
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import cairosvg
import numpy as np

W, H = 1080, 1920
OUT = "#2a1a12"
STAGES = ["#7cb342", "#a9c24a", "#e0b23c", "#ec8a3a", "#e4553a", "#cf2f2a"]   # green, breaker .. red


def mix(c1, c2, u):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    u = min(max(u, 0), 1)
    return "#" + "".join(f"{round(x + (y - x) * u):02x}" for x, y in zip(a, b))


def ripe_col(r):
    x = min(max(r, 0), 1) * (len(STAGES) - 1)
    i = min(int(x), len(STAGES) - 2)
    return mix(STAGES[i], STAGES[i + 1], x - i)


def ease(u):
    u = min(max(u, 0), 1)
    return u * u * (3 - 2 * u)


def tomato(x, y, r, ripe, ang=0.0):
    """A round tomato with lobes, a highlight and a green star-shaped calyx on top. ripe 0 (green) .. 1 (red)."""
    body = ripe_col(ripe)
    shade = mix(body, "#3a0f0a", 0.35)
    calyx = "".join(f'<path d="M 0,{-r * 0.9:.1f} Q {math.cos(math.radians(a)) * r * 0.35:.1f},{-r * 0.9 + math.sin(math.radians(a)) * r * 0.2:.1f} '
                    f'{math.cos(math.radians(a)) * r * 0.55:.1f},{-r * 0.85 + math.sin(math.radians(a)) * r * 0.35:.1f}" '
                    f'stroke="#3f7d26" stroke-width="{r * 0.13:.1f}" fill="none" stroke-linecap="round"/>' for a in (-160, -110, -70, -20, 20))
    return (f'<g transform="translate({x:.1f} {y:.1f}) rotate({ang:.1f})">'
            f'<path d="M 0,{-r * 0.88:.1f} C {r * 0.75:.1f},{-r * 1.05:.1f} {r * 1.12:.1f},{-r * 0.45:.1f} {r * 1.02:.1f},{r * 0.12:.1f} '
            f'C {r * 0.95:.1f},{r * 0.8:.1f} {r * 0.4:.1f},{r * 1.0:.1f} 0,{r * 0.96:.1f} C {-r * 0.4:.1f},{r * 1.0:.1f} '
            f'{-r * 0.95:.1f},{r * 0.8:.1f} {-r * 1.02:.1f},{r * 0.12:.1f} C {-r * 1.12:.1f},{-r * 0.45:.1f} {-r * 0.75:.1f},{-r * 1.05:.1f} 0,{-r * 0.88:.1f} Z" '
            f'fill="{body}" stroke="{OUT}" stroke-width="{max(2.0, r * 0.07):.1f}"/>'
            f'<path d="M {r * 0.15:.1f},{r * 0.9:.1f} C {r * 0.8:.1f},{r * 0.7:.1f} {r * 0.98:.1f},{r * 0.2:.1f} {r * 0.9:.1f},{-r * 0.3:.1f}" '
            f'stroke="{shade}" stroke-width="{r * 0.16:.1f}" fill="none" stroke-opacity="0.45"/>'
            f'<ellipse cx="{-r * 0.38:.1f}" cy="{-r * 0.35:.1f}" rx="{r * 0.2:.1f}" ry="{r * 0.12:.1f}" fill="#ffffff" fill-opacity="0.55" '
            f'transform="rotate(-35 {-r * 0.38:.1f} {-r * 0.35:.1f})"/>'
            f'{calyx}<line x1="0" y1="{-r * 0.88:.1f}" x2="{r * 0.08:.1f}" y2="{-r * 1.12:.1f}" stroke="#3f7d26" stroke-width="{r * 0.12:.1f}" '
            f'stroke-linecap="round"/></g>')


def leaf(x, y, ang, s):
    """Tomato compound leaf: a stalk with pairs of toothed leaflets and one at the tip."""
    out = []
    a = math.radians(ang)
    L = 70 * s
    ex, ey = x + math.cos(a) * L, y + math.sin(a) * L
    out.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" stroke="#2f5d1c" stroke-width="{3.5 * s:.1f}"/>')
    for k, u in enumerate((0.35, 0.65, 1.0)):
        px, py = x + math.cos(a) * L * u, y + math.sin(a) * L * u
        for side in ((-1, 1) if u < 1 else (0,)):
            la = ang + side * 55
            r = 13 * s * (1.15 if u == 1 else 1.0)
            cx = px + math.cos(math.radians(la)) * r * (0.9 if side else 0.6)
            cy = py + math.sin(math.radians(la)) * r * (0.9 if side else 0.6)
            pts = []
            for j in range(16):
                t = j / 16 * 2 * math.pi
                rr = r * (1 + 0.09 * math.cos(7 * t))
                xx = rr * math.cos(t) * 1.25
                yy = rr * math.sin(t) * 0.62
                ca, sa = math.cos(math.radians(la)), math.sin(math.radians(la))
                pts.append(f"{cx + xx * ca - yy * sa:.1f},{cy + xx * sa + yy * ca:.1f}")
            out.append(f'<polygon points="{" ".join(pts)}" fill="#4f9a32" stroke="#22401a" stroke-width="{1.4 * s:.1f}"/>')
    return "".join(out)


def plant_svg(x, base_y, h, s=1.0, fruits=(), seed=1, sway=0.0, stake=True):
    """A staked tomato plant: stake, zig-zag main stem, compound leaves, yellow flowers, and fruits.
    fruits: [(u, side, r, ripe)] with u = height along the stem (0 base .. 1 top), side -1/1."""
    rng = np.random.default_rng(seed)
    g = []
    top = base_y - h
    if stake:
        g.append(f'<rect x="{x + 10 * s:.1f}" y="{top - 20 * s:.1f}" width="{8 * s:.1f}" height="{h + 30 * s:.1f}" fill="#b98a4e" '
                 f'stroke="#5a3a18" stroke-width="{2 * s:.1f}"/>')
    pts = []
    for j in range(9):
        u = j / 8
        pts.append((x + (5 * s if j % 2 else -5 * s) + sway * u * u * 12, base_y - h * u))
    d = "M " + " L ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in pts)
    g.append(f'<path d="{d}" stroke="#22401a" stroke-width="{9 * s:.1f}" fill="none" stroke-linejoin="round"/>'
             f'<path d="{d}" stroke="#5e9b38" stroke-width="{5 * s:.1f}" fill="none" stroke-linejoin="round"/>')
    for j in range(1, 9):
        px, py = pts[j]
        side = -1 if j % 2 else 1
        g.append(leaf(px, py, -90 + side * (55 + rng.uniform(-10, 15)), s * rng.uniform(0.85, 1.1)))
    for j in (3, 6, 8):                               # yellow star flowers (more fruit still to come)
        px, py = pts[j]
        fx, fy = px + 22 * s, py - 4 * s
        petals = "".join(f'<ellipse cx="{fx + math.cos(math.radians(a)) * 6 * s:.1f}" cy="{fy + math.sin(math.radians(a)) * 6 * s:.1f}" '
                         f'rx="{5 * s:.1f}" ry="{2.6 * s:.1f}" fill="#f4d03f" stroke="#8a6d10" stroke-width="{0.8 * s:.1f}" '
                         f'transform="rotate({a} {fx + math.cos(math.radians(a)) * 6 * s:.1f} {fy + math.sin(math.radians(a)) * 6 * s:.1f})"/>'
                         for a in range(0, 360, 72))
        g.append(petals)
    for (u, side, r, ripe) in fruits:
        j = u * 8
        i0 = min(int(j), 7)
        px = pts[i0][0] + (pts[i0 + 1][0] - pts[i0][0]) * (j - i0)
        py = pts[i0][1] + (pts[i0 + 1][1] - pts[i0][1]) * (j - i0)
        fx, fy = px + side * (r * 0.9 + 6 * s), py + r * 1.25
        g.append(f'<path d="M {px:.1f},{py:.1f} Q {px + side * r * 0.5:.1f},{py + r * 0.1:.1f} {fx:.1f},{fy - r * 0.9:.1f}" '
                 f'stroke="#3f7d26" stroke-width="{3 * s:.1f}" fill="none"/>')
        g.append(tomato(fx, fy, r, ripe))
    return "".join(g)


def thottam_rows(w=720, h=1280, horizon=560, near=1280, seed=4):
    """Rows of staked tomato plants receding to the horizon, for the garden plate (720x1280 coords)."""
    rng = np.random.default_rng(seed)
    g = []
    for k, y in enumerate(np.linspace(horizon + 20, horizon + 260, 5)):
        s = 0.25 + (y - horizon) / (near - horizon) * 0.9
        for x in np.arange(-20 + (k % 2) * 40, w + 40, 95 * s + 30):
            fr = [(rng.uniform(0.3, 0.8), rng.choice([-1, 1]), 11 * s, rng.uniform(0, 1)) for _ in range(rng.integers(1, 4))]
            g.append(plant_svg(x + rng.uniform(-10, 10), y, 150 * s, s, fr, seed=int(x + y)))
    return "".join(g)


# ---------------------------------------------------------------- cut-aways

def bg(ground=True):
    """Soft garden backdrop: sky into blurred green bushes (and the red soil if ground)."""
    g = ('<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#bfe4f5"/>'
         '<stop offset="0.55" stop-color="#d9efcf"/><stop offset="1" stop-color="#8fc46a"/></linearGradient>'
         '<filter id="soft"><feGaussianBlur stdDeviation="18"/></filter></defs>'
         f'<rect width="{W}" height="{H}" fill="url(#sky)"/>')
    rng = np.random.default_rng(3)
    g += '<g filter="url(#soft)" opacity="0.8">' + "".join(
        f'<ellipse cx="{rng.uniform(0, W):.0f}" cy="{rng.uniform(900, 1500):.0f}" rx="{rng.uniform(90, 200):.0f}" '
        f'ry="{rng.uniform(60, 140):.0f}" fill="{rng.choice(["#5f9e3c", "#79b54a", "#4c8a30"])}"/>' for _ in range(16)) + '</g>'
    if ground:
        g += (f'<rect y="1300" width="{W}" height="{H - 1300}" fill="#b5532a"/>'
              '<ellipse cx="540" cy="1300" rx="520" ry="40" fill="#9a4322" fill-opacity="0.6"/>')
    return g


def scene(t, cfg):
    mode, span = cfg["mode"], cfg["span"]
    p = ease((t - span[0]) / (span[1] - span[0]))
    sw = math.sin(t * 1.7) * 0.8
    g = [bg(mode == "plant")]
    if mode == "ripen":
        g.append(f'<g transform="rotate({sw:.2f} 540 300)"><path d="M 540,300 Q 560,560 540,760" stroke="#3f7d26" stroke-width="18" '
                 f'fill="none"/>{leaf(540, 420, -20, 3.2)}{leaf(540, 520, 200, 3.0)}{tomato(540, 1000, 250, p)}</g>')
    elif mode == "pigment":
        g = ['<rect width="1080" height="1920" fill="#fbe9df"/>']
        rng = np.random.default_rng(5)
        for i in range(6):
            for j in range(4):
                x0, y0 = 90 + j * 230, 420 + i * 190
                g.append(f'<rect x="{x0}" y="{y0}" width="210" height="170" rx="22" fill="{mix("#eef6df", "#fde3d6", p)}" '
                         f'stroke="#b07a5a" stroke-width="5"/>')
                for k in range(6):                    # chloroplasts (green discs) shrink and fade
                    cx, cy = x0 + 30 + rng.uniform(0, 150), y0 + 25 + rng.uniform(0, 120)
                    r = 15 * (1 - 0.8 * p)
                    g.append(f'<ellipse cx="{cx:.0f}" cy="{cy:.0f}" rx="{r:.1f}" ry="{r * 0.6:.1f}" fill="#5aa832" '
                             f'fill-opacity="{1 - p:.2f}" stroke="#2f6b1a" stroke-width="2" stroke-opacity="{1 - p:.2f}"/>')
                for k in range(7):                    # lycopene crystals (red needles) build up
                    cx, cy = x0 + 25 + rng.uniform(0, 160), y0 + 20 + rng.uniform(0, 130)
                    q = ease((p - 0.15 - k * 0.07) / 0.4)
                    a = rng.uniform(0, 180)
                    g.append(f'<rect x="{cx - 14 * q:.0f}" y="{cy - 4:.0f}" width="{28 * q:.0f}" height="8" rx="4" fill="#d6332b" '
                             f'transform="rotate({a:.0f} {cx:.0f} {cy:.0f})" fill-opacity="{min(1, q * 1.5):.2f}"/>')
    elif mode == "stages":
        g.append(f'<path d="M 60,700 Q 540,560 1020,700" stroke="#3f7d26" stroke-width="16" fill="none"/>')
        for k in range(6):
            x = 140 + k * 160
            q = ease((t - span[0] - k * 0.35) / 0.4)
            y = 700 - 140 * math.sin(math.pi * (x - 60) / 960) * 0.95 + 20
            if q > 0:
                g.append(f'<line x1="{x}" y1="{y:.0f}" x2="{x}" y2="{y + 90:.0f}" stroke="#3f7d26" stroke-width="8"/>')
                g.append(f'<g transform="translate({x} {y + 175:.0f}) scale({q:.2f})">{tomato(0, 0, 70, k / 5)}</g>')
    else:  # plant
        g.append(plant_svg(540, 1300, 1050, 3.0, [(0.42, -1, 70, 1.0), (0.47, 1, 62, 0.45), (0.62, -1, 58, 0.0),
                                                   (0.7, 1, 52, 0.15)], seed=8, sway=sw))
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
