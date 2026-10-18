"""Close-up of a pulled groundnut plant's roots with its pod cluster (Groundnut Ep 8). 1080x1920.

Usage:
    python tools/toon/harvest.py OUT.mp4 TIMING.json

TIMING.json: {"duration": 6.0, "fps": 25, "camera": [[t, cx, cy, h], ...]}
The plant hangs from the top of the frame (just pulled up), swaying a little; soil crumbs fall off. Pods hang from the
root zone on their pegs, in different sizes and stages: big filled two-kernel pods, smaller ones and a few still-thin
young pods (all from one plant – pods form over several weeks, so they are never all the same size).
Background: the series field art, blurred (cutaway.sky_png).
"""
import base64
import json
import math
import subprocess
import sys
from pathlib import Path

import cairosvg
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cutaway import OUT, leaf, sky_png  # noqa: E402

W, H = 1080, 1920
TOP = 520                       # where the stem base (crown) hangs
RNG = np.random.default_rng(8)
# pods: (x offset, peg length, scale, kind) kind: 2 = big filled, 1 = smaller, 0 = young/thin
PODS = [(-300, 330, 1.25, 2), (-190, 420, 1.1, 2), (-90, 300, 1.3, 2), (40, 380, 1.2, 2), (150, 290, 1.0, 1),
        (260, 400, 1.15, 2), (330, 260, 0.75, 1), (-360, 220, 0.7, 1), (-30, 470, 0.6, 0), (210, 520, 0.55, 0),
        (90, 220, 0.85, 1), (-240, 520, 0.6, 0)]


def pod(x, y, s, kind, ang):
    body = ("M -46,0 C -46,-24 -16,-26 -6,-14 C 2,-24 46,-28 50,0 C 46,28 2,24 -6,14 C -16,26 -46,24 -46,0 Z"
            if kind else "M -46,0 C -46,-12 46,-14 50,0 C 46,14 -46,12 -46,0 Z")
    fill = "#d9b47c" if kind else "#ead7b0"
    net = ""
    if kind:
        net = "".join(f'<path d="M {a},-20 C {a + 6},-6 {a + 6},6 {a},20" stroke="#a9834d" stroke-width="2.5" fill="none"/>'
                      for a in (-34, -20, 10, 26, 40))
        net += '<path d="M -44,-6 C -20,-2 20,-2 48,-6 M -44,8 C -20,12 20,12 48,8" stroke="#a9834d" stroke-width="2.5" fill="none"/>'
    dirt = "".join(f'<circle cx="{RNG.uniform(-35, 40):.0f}" cy="{RNG.uniform(-14, 14):.0f}" r="{RNG.uniform(3, 6):.1f}" '
                   f'fill="#a8481f" fill-opacity="0.85"/>' for _ in range(3))
    return (f'<g transform="translate({x:.0f} {y:.0f}) rotate({ang:.0f}) scale({2.1 * s:.3f})">'
            f'<path d="{body}" fill="{fill}" stroke="{OUT}" stroke-width="3.5"/>{net}{dirt}</g>')


def plant(t):
    sway = 4 * math.sin(t * 1.6)
    cx = W / 2
    g = [f'<g transform="rotate({sway:.2f} {cx} 0)">']
    # stem and leaves above the crown
    g.append(f'<path d="M {cx},{TOP} L {cx},-200" stroke="{OUT}" stroke-width="26"/><path d="M {cx},{TOP} L {cx},-200" stroke="#5f8f30" stroke-width="18"/>')
    for i, (dy, ang) in enumerate([(-120, -150), (-20, -30), (80, -160), (160, -20), (260, -140), (340, -40)]):
        g.append(leaf(cx, TOP + dy - 300, ang, 1.5 - 0.05 * i))
    # roots: taproot + side roots
    g.append(f'<path d="M {cx},{TOP} C {cx + 10},{TOP + 300} {cx - 15},{TOP + 650} {cx + 5},{TOP + 1050}" stroke="#e9d3a8" '
             f'stroke-width="16" fill="none" stroke-linecap="round"/>')
    for k in range(9):
        y0 = TOP + 60 + k * 85
        side = -1 if k % 2 else 1
        ln = 260 - k * 14
        g.append(f'<path d="M {cx},{y0} Q {cx + side * ln * 0.5},{y0 + 40} {cx + side * ln},{y0 + ln * 0.5}" stroke="#e9d3a8" '
                 f'stroke-width="7" fill="none" stroke-linecap="round"/>')
    # pegs + pods
    for i, (dx, ln, s, kind) in enumerate(PODS):
        x0, y0 = cx + dx * 0.25, TOP + 20
        x1, y1 = cx + dx, TOP + ln
        g.append(f'<path d="M {x0:.0f},{y0} Q {x0 + (x1 - x0) * 0.3:.0f},{y0 + (y1 - y0) * 0.8:.0f} {x1:.0f},{y1}" stroke="{OUT}" '
                 f'stroke-width="9" fill="none"/><path d="M {x0:.0f},{y0} Q {x0 + (x1 - x0) * 0.3:.0f},{y0 + (y1 - y0) * 0.8:.0f} '
                 f'{x1:.0f},{y1}" stroke="#8a5aa0" stroke-width="5" fill="none"/>')
        g.append(pod(x1, y1 + 45 * s, s, kind, 80 + (i * 17) % 30 - 15))
    g.append("</g>")
    return "".join(g)


def crumbs(t):
    rng = np.random.default_rng(int(t * 25))
    g = []
    for k in range(18):
        ph = (t * 0.9 + k / 18) % 1
        x = W / 2 + (np.random.default_rng(k).uniform(-380, 380))
        y = TOP + 200 + ph * 1400
        r = 5 + (k % 4) * 3
        g.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="#b5532a" stroke="{OUT}" stroke-width="2" fill-opacity="{1 - ph:.2f}" stroke-opacity="{1 - ph:.2f}"/>')
    return "".join(g)


def main():
    out, cfg = sys.argv[1], json.loads(Path(sys.argv[2]).read_text())
    sky = base64.b64encode(sky_png()).decode()
    fps = cfg.get("fps", 25)
    n = round(cfg["duration"] * fps)
    cams = cfg["camera"]
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "image2pipe", "-framerate", str(fps), "-i", "-",
                           "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i in range(n):
        t = i / fps
        cx, cy, h = (np.interp(t, [c[0] for c in cams], [c[j] for c in cams]) for j in (1, 2, 3))
        w = h * W / H
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="{cx - w / 2:.1f} {cy - h / 2:.1f} {w:.1f} {h:.1f}">'
               f'<image href="data:image/png;base64,{sky}" x="-300" y="-200" width="{W + 600}" height="{H + 400}" preserveAspectRatio="xMidYMid slice"/>'
               f'{plant(t)}{crumbs(t)}</svg>')
        ff.stdin.write(cairosvg.svg2png(bytestring=svg.encode()))
    ff.stdin.close()
    ff.wait()
    print("saved", out)


if __name__ == "__main__":
    main()
