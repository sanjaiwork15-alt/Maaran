"""Animated groundnut cut-away (how pods form underground), drawn in code, 1080x1920.

Usage:
    python tools/toon/cutaway.py OUT.mp4 TIMING.json

TIMING.json: {"duration": 11.0, "fps": 25, "flower": [t0, t1], "peg": [t0, t1], "pod": [t0, t1],
              "camera": [[t, cy, h], ...]}   # camera centre y and view height on the 1080x2400 stage

Botany (TNAU groundnut): a low, bushy plant with leaves of four leaflets; small yellow
pea-like flowers open near the base; after flowering a peg (gynophore) grows from the
flower down into the soil and its tip swells into a pod with a netted shell holding two
kernels. Roots: a taproot with side roots and small round nitrogen nodules.
The sky and trees above the soil come from the series background (assets/2d), softly
blurred, so the cut-away matches the episode's art.
"""
import io
import json
import math
import subprocess
import sys
from pathlib import Path

import cairosvg
import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
W, H = 1080, 2400           # stage
SOIL = 1180                 # soil surface y on the stage
OUT = "#3b2416"
RNG = np.random.default_rng(5)


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def phase(t, span):
    return ease((t - span[0]) / max(1e-6, span[1] - span[0]))


# ---------------------------------------------------------------- static layers

def sky_png():
    """Top of the series field background (sky, trees, hill), blurred, as the backdrop."""
    up = ROOT / "assets/2d/up/05_field_vertical.png"
    bg = Image.open(up if up.exists() else ROOT / "assets/2d/source/05_field_vertical.png").convert("RGB")
    crop = bg.crop((0, 0, bg.width, int(bg.height * 0.52)))
    crop = crop.resize((W, int(crop.height * W / crop.width)), Image.LANCZOS)
    canvas = Image.new("RGB", (W, SOIL + 40), (150, 200, 235))
    canvas.paste(crop, (0, SOIL + 40 - crop.height))
    canvas = canvas.filter(ImageFilter.GaussianBlur(5))
    buf = io.BytesIO()
    canvas.save(buf, "PNG")
    return buf.getvalue()


def soil_svg():
    g = [f'<defs><linearGradient id="soil" x1="0" y1="0" x2="0" y2="1">'
         f'<stop offset="0" stop-color="#c8602e"/><stop offset="0.35" stop-color="#b14d24"/>'
         f'<stop offset="1" stop-color="#7a3117"/></linearGradient></defs>',
         f'<rect x="0" y="{SOIL}" width="{W}" height="{H - SOIL}" fill="url(#soil)"/>']
    # strata and texture
    for i in range(7):
        y = SOIL + 140 + i * 160 + RNG.uniform(-20, 20)
        pts = " ".join(f"{x},{y + 10 * math.sin(x / 90 + i)}" for x in range(0, W + 60, 60))
        g.append(f'<polyline points="{pts}" fill="none" stroke="#6e2a12" stroke-opacity="0.18" stroke-width="5"/>')
    for _ in range(140):
        x, y = RNG.uniform(0, W), RNG.uniform(SOIL + 30, H - 20)
        r = RNG.uniform(3, 9)
        g.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.1f}" fill="#e08a55" fill-opacity="0.35"/>')
    for _ in range(26):
        x, y = RNG.uniform(30, W - 30), RNG.uniform(SOIL + 80, H - 40)
        rx, ry = RNG.uniform(10, 24), RNG.uniform(7, 15)
        g.append(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{rx:.0f}" ry="{ry:.0f}" fill="#a9928a" stroke="{OUT}" stroke-width="3"/>')
    # surface: crumbly clods and a darker rim
    g.append(f'<rect x="0" y="{SOIL - 6}" width="{W}" height="22" fill="#9c4120"/>')
    for x in range(0, W + 40, 34):
        r = RNG.uniform(14, 26)
        g.append(f'<ellipse cx="{x + RNG.uniform(-8, 8):.0f}" cy="{SOIL - 4:.0f}" rx="{r:.0f}" ry="{r * 0.55:.0f}" fill="#c85f2d" stroke="{OUT}" stroke-width="3"/>')
    return "".join(g)


def roots_svg():
    g = [f'<path d="M 540,{SOIL} C 545,{SOIL + 300} 530,{SOIL + 650} 540,{SOIL + 980}" fill="none" stroke="#e9d3a8" stroke-width="13" stroke-linecap="round"/>']
    for i, (y, side, ln) in enumerate([(160, -1, 220), (240, 1, 260), (360, -1, 260), (470, 1, 230), (600, -1, 200), (720, 1, 170)]):
        y0 = SOIL + y
        x1, y1 = 540 + side * ln, y0 + ln * 0.55
        g.append(f'<path d="M 540,{y0} Q {540 + side * ln * 0.5},{y0 + 20} {x1:.0f},{y1:.0f}" fill="none" stroke="#e9d3a8" stroke-width="6" stroke-linecap="round"/>')
        for k in range(3):
            f = 0.35 + 0.25 * k
            nx, ny = 540 + side * ln * f, y0 + 20 * f + ln * 0.55 * f * f + 6
            g.append(f'<circle cx="{nx:.0f}" cy="{ny:.0f}" r="8" fill="#e59b9b" stroke="{OUT}" stroke-width="2.5"/>')
    return "".join(g)


def leaf(x, y, ang, s=1.0):
    """A groundnut leaf: petiole with two pairs of oval leaflets."""
    a = math.radians(ang)
    dx, dy = math.cos(a), math.sin(a)
    px, py = -dy, dx
    L = 120 * s
    g = [f'<path d="M {x},{y} L {x + dx * L:.0f},{y + dy * L:.0f}" stroke="#4f7d2a" stroke-width="{6 * s:.1f}" stroke-linecap="round"/>']
    for f in (0.55, 1.0):
        cx, cy = x + dx * L * f, y + dy * L * f
        for side in (-1, 1):
            lx, ly = cx + px * side * 34 * s + dx * 16 * s, cy + py * side * 34 * s + dy * 16 * s
            rot = math.degrees(math.atan2(py * side + dy * 0.5, px * side + dx * 0.5))
            g.append(f'<ellipse cx="{lx:.0f}" cy="{ly:.0f}" rx="{40 * s:.0f}" ry="{22 * s:.0f}" transform="rotate({rot:.0f} {lx:.0f} {ly:.0f})" '
                     f'fill="#5fa83a" stroke="{OUT}" stroke-width="3"/>')
            g.append(f'<path d="M {cx:.0f},{cy:.0f} L {lx + (lx - cx) * 0.7:.0f},{ly + (ly - cy) * 0.7:.0f}" stroke="#3f7a26" stroke-width="2"/>')
    return "".join(g)


BRANCHES = [  # (end x, end y) of low spreading branches from the crown at (540, SOIL)
    (330, SOIL - 120), (750, SOIL - 130), (420, SOIL - 300), (660, SOIL - 290), (540, SOIL - 380),
    (250, SOIL - 40), (830, SOIL - 50)]
FLOWERS = [(400, SOIL - 46), (690, SOIL - 52), (520, SOIL - 70), (610, SOIL - 30)]
PEG_END = [(300, SOIL + 150), (800, SOIL + 160), (430, SOIL + 210), (690, SOIL + 125)]   # pods form just below the surface


def plant_svg():
    g = []
    for ex, ey in BRANCHES:
        g.append(f'<path d="M 540,{SOIL - 4} Q {(540 + ex) / 2:.0f},{SOIL - 10 - (SOIL - ey) * 0.3:.0f} {ex},{ey}" '
                 f'fill="none" stroke="#56862f" stroke-width="11" stroke-linecap="round"/>')
    for i, (ex, ey) in enumerate(BRANCHES):
        for f, ang in ((0.45, -60 if ex < 540 else -120), (0.8, -110 if ex < 540 else -70), (1.0, -90 + (ex - 540) * 0.12)):
            x = 540 + (ex - 540) * f
            y = SOIL - (SOIL - ey) * f
            g.append(leaf(x, y, ang + (i * 13 % 25) - 12, 0.9 + 0.1 * (i % 2)))
    return "".join(g)


def flower(x, y, s):
    if s <= 0:
        return ""
    return (f'<g transform="translate({x} {y}) scale({s:.3f})">'
            f'<path d="M 0,6 L 0,22" stroke="#4f7d2a" stroke-width="5"/>'
            f'<ellipse cx="-13" cy="4" rx="13" ry="9" fill="#ffd23a" stroke="{OUT}" stroke-width="2.5"/>'
            f'<ellipse cx="13" cy="4" rx="13" ry="9" fill="#ffd23a" stroke="{OUT}" stroke-width="2.5"/>'
            f'<path d="M -26,-2 C -30,-38 30,-38 26,-2 C 14,6 -14,6 -26,-2 Z" fill="#ffc21a" stroke="{OUT}" stroke-width="3"/>'
            f'<path d="M 0,-4 L 0,-24 M -8,-6 L -14,-22 M 8,-6 L 14,-22" stroke="#d9532b" stroke-width="2.2"/>'
            f'</g>')


def peg_points(i, n=40):
    (x0, y0), (x1, y1) = FLOWERS[i], PEG_END[i]
    pts = []
    for k in range(n + 1):
        u = k / n
        # down from the flower, then turning sideways at the tip (where the pod forms)
        x = x0 + (x1 - x0) * (u ** 2.2)
        y = y0 + (y1 - y0) * (1 - (1 - u) ** 1.6)
        pts.append((x, y))
    return pts


def peg(i, frac):
    if frac <= 0:
        return ""
    pts = peg_points(i)
    m = max(2, int(len(pts) * frac))
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts[:m])
    return (f'<polyline points="{d}" fill="none" stroke="{OUT}" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<polyline points="{d}" fill="none" stroke="#8a5aa0" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>')


def pod(i, s):
    if s <= 0:
        return ""
    pts = peg_points(i)
    (x, y), (px, py) = pts[-1], pts[-4]
    ang = math.degrees(math.atan2(y - py, x - px))
    body = ("M -46,0 C -46,-24 -16,-26 -6,-14 C 2,-24 46,-28 50,0 C 46,28 2,24 -6,14 C -16,26 -46,24 -46,0 Z")
    net = "".join(f'<path d="M {a},-20 C {a + 6},-6 {a + 6},6 {a},20" stroke="#b08850" stroke-width="2" fill="none"/>' for a in (-34, -20, 10, 26, 40))
    net += '<path d="M -44,-6 C -20,-2 20,-2 48,-6 M -44,8 C -20,12 20,12 48,8" stroke="#b08850" stroke-width="2" fill="none"/>'
    return (f'<g transform="translate({x:.0f} {y:.0f}) rotate({ang:.0f}) translate(52 0) scale({1.35 * s:.3f})">'
            f'<path d="{body}" fill="#e3c28a" stroke="{OUT}" stroke-width="3.5"/>{net}</g>')


# ---------------------------------------------------------------- frames

class Cutaway:
    def __init__(self):
        import base64
        self.sky = base64.b64encode(sky_png()).decode()
        self.static_under = soil_svg() + roots_svg()
        self.plant = plant_svg()

    def svg(self, t, cfg):
        fl, pg, pd = phase(t, cfg["flower"]), phase(t, cfg["peg"]), phase(t, cfg["pod"])
        cams = cfg["camera"]
        cy = np.interp(t, [c[0] for c in cams], [c[1] for c in cams])
        h = np.interp(t, [c[0] for c in cams], [c[2] for c in cams])
        w = h * 1080 / 1920
        # flowers open, then wither (shrink) as their pegs grow
        fs = fl * (1 - 0.7 * pg)
        parts = [f'<image href="data:image/png;base64,{self.sky}" x="0" y="0" width="{W}" height="{SOIL + 40}"/>',
                 self.static_under]
        for i in range(len(FLOWERS)):
            parts.append(peg(i, ease((pg - 0.12 * i) / 0.64)))
            parts.append(pod(i, ease((pd - 0.15 * i) / 0.55)))
        parts.append(self.plant)
        for i, (x, y) in enumerate(FLOWERS):
            parts.append(flower(x, y, ease((fs - 0.1 * i) / 0.7) * 1.7))
        return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1080" height="1920" '
                f'viewBox="{540 - w / 2:.1f} {cy - h / 2:.1f} {w:.1f} {h:.1f}">{"".join(parts)}</svg>')


def main():
    out, cfg = sys.argv[1], json.loads(Path(sys.argv[2]).read_text())
    c = Cutaway()
    fps, n = cfg.get("fps", 25), round(cfg["duration"] * cfg.get("fps", 25))
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "image2pipe", "-framerate", str(fps), "-i", "-",
                           "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i in range(n):
        ff.stdin.write(cairosvg.svg2png(bytestring=c.svg(i / fps, cfg).encode()))
    ff.stdin.close()
    ff.wait()
    print("saved", out)


if __name__ == "__main__":
    main()
