"""Groundnut pods drying in the sun vs a damp heap going mouldy (Groundnut Ep 9). 1080x1920.

Usage:
    python tools/toon/drying.py OUT.mp4 TIMING.json

TIMING.json: {"duration": 9.0, "fps": 25, "dry": [t0, t1], "mould": [t0, t1], "camera": [[t, cy, h], ...]}
Top: fresh pods spread in ONE thin layer on a woven mat in the sun – damp-dark with soil specks at first, turning
dry light-tan as the sun dries them ("dry"); a few drops evaporate. Bottom: a thick damp heap in the shade where
grey-green mould spots grow ("mould") – why pods must be dried well before storing (TNAU post-harvest guidance:
dry the pods in the sun before storage; damp pods spoil and grow fungus).
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import cairosvg
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cutaway import OUT, phase  # noqa: E402

W, H = 1080, 1920
SHAPE = "M -46,0 C -46,-24 -16,-26 -6,-14 C 2,-24 46,-28 50,0 C 46,28 2,24 -6,14 C -16,26 -46,24 -46,0 Z"


def mix(c1, c2, u):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * u):02x}" for x, y in zip(a, b))


def pod(x, y, ang, s, wet, mould=0.0, seed=0):
    rng = np.random.default_rng(seed)
    fill = mix("#e3c28a", "#8f6b45", wet)
    net = "".join(f'<path d="M {a},-20 C {a + 6},-6 {a + 6},6 {a},20" stroke="{mix("#b08850", "#5c4026", wet)}" '
                  f'stroke-width="2.5" fill="none"/>' for a in (-34, -20, 10, 26, 40))
    specks = "".join(f'<circle cx="{rng.uniform(-38, 42):.0f}" cy="{rng.uniform(-15, 15):.0f}" r="{rng.uniform(3, 6):.1f}" '
                     f'fill="#9a4320" fill-opacity="{0.9 * wet:.2f}"/>' for _ in range(4))
    mould_s = ""
    if mould > 0:
        for _ in range(3):
            mould_s += (f'<circle cx="{rng.uniform(-30, 35):.0f}" cy="{rng.uniform(-12, 12):.0f}" r="{rng.uniform(6, 13) * mould:.1f}" '
                        f'fill="#8fa38a" fill-opacity="0.85" stroke="#5f7259" stroke-width="2"/>')
    return (f'<g transform="translate({x:.0f} {y:.0f}) rotate({ang:.0f}) scale({s:.2f})">'
            f'<path d="{SHAPE}" fill="{fill}" stroke="{OUT}" stroke-width="3.5"/>{net}{specks}{mould_s}</g>')


def scene(t, cfg):
    d = phase(t, cfg["dry"])
    m = phase(t, cfg["mould"])
    g = [f'<rect width="{W}" height="{H}" fill="#c4683a"/>',
         '<rect y="0" width="1080" height="250" fill="#8fd0f5"/>',
         f'<circle cx="880" cy="140" r="{70 + 6 * math.sin(t * 3):.0f}" fill="#ffd84a"/>']
    # sunny mat with a thin layer
    g.append('<rect x="60" y="300" width="960" height="760" rx="20" fill="#d9b779" stroke="#3b2416" stroke-width="6"/>')
    for k in range(0, 960, 40):
        g.append(f'<line x1="{60 + k}" y1="300" x2="{60 + k}" y2="1060" stroke="#b8955a" stroke-width="3"/>')
    rng = np.random.default_rng(1)
    for i in range(7):
        for j in range(8):
            x = 130 + j * 118 + rng.uniform(-12, 12)
            y = 360 + i * 100 + rng.uniform(-10, 10)
            g.append(pod(x, y, rng.uniform(-40, 40), 1.0, 1 - d, seed=i * 10 + j))
    for k in range(10):                                   # drops lifting off as it dries
        ph = (t * 0.7 + k / 10) % 1
        if 0 < d < 0.95:
            x = 120 + k * 90
            y = 1000 - ph * 600
            g.append(f'<path d="M {x},{y:.0f} q -9,20 0,30 q 9,-10 0,-30 Z" fill="#bfe6ff" fill-opacity="{(1 - ph) * 0.8:.2f}"/>')
    # shade: a thick damp heap, mould grows
    g.append('<rect x="0" y="1150" width="1080" height="770" fill="#7a3a1d"/>')
    g.append('<rect x="0" y="1150" width="1080" height="770" fill="#1b2a3a" fill-opacity="0.35"/>')
    rng = np.random.default_rng(2)
    for k in range(60):
        r = math.sqrt(k / 60)
        a = k * 2.4
        x = 540 + math.cos(a) * 330 * r
        y = 1560 + math.sin(a) * 200 * r - (1 - r) * 120
        g.append(pod(x, y, rng.uniform(-60, 60), 1.0, 1.0, mould=m if rng.random() < 0.6 else 0, seed=100 + k))
    return "".join(g)


def main():
    out, cfg = sys.argv[1], json.loads(Path(sys.argv[2]).read_text())
    fps = cfg.get("fps", 25)
    n = round(cfg["duration"] * fps)
    cams = cfg["camera"]
    ff = subprocess.Popen(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "image2pipe", "-framerate", str(fps),
                           "-i", "-", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i in range(n):
        t = i / fps
        cy = np.interp(t, [c[0] for c in cams], [c[1] for c in cams])
        h = np.interp(t, [c[0] for c in cams], [c[2] for c in cams])
        w = h * W / H
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
               f'viewBox="{W / 2 - w / 2:.1f} {cy - h / 2:.1f} {w:.1f} {h:.1f}">{scene(t, cfg)}</svg>')
        ff.stdin.write(cairosvg.svg2png(bytestring=svg.encode()))
    ff.stdin.close()
    ff.wait()
    print("saved", out)


if __name__ == "__main__":
    main()
