"""Close-up of groundnut seedlings coming up through the soil (Groundnut Ep 4 opening). 1080x1920.

Usage:
    python tools/toon/seedlings.py OUT.mp4 TIMING.json

TIMING.json: {"duration": 3.0, "fps": 25, "grow": [t0, t1], "camera": [[t, cy, h], ...]}
A row of seedlings in the sown red soil, nearest one biggest. Each pushes up as a bent hook that straightens,
then its first leaf (four leaflets, folded at first) opens. The cotyledons stay at the soil surface
(groundnut emergence). Background: the series field art, blurred (as in tools/toon/cutaway.py).
"""
import base64
import json
import subprocess
import sys
from pathlib import Path

import cairosvg
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cutaway import OUT, ease, leaf, phase, sky_png  # noqa: E402

W, H = 1080, 1920
SOIL = 1250
PLANTS = [(170, 0.55, 0.25), (420, 0.7, 0.12), (700, 0.85, 0.05), (540, 1.35, 0.0)]   # x, scale, start delay


def soil():
    rng = np.random.default_rng(4)
    g = [f'<rect x="0" y="{SOIL}" width="{W}" height="{H - SOIL}" fill="#b9562a"/>',
         f'<rect x="0" y="{SOIL}" width="{W}" height="60" fill="#cf6a34"/>']
    for _ in range(260):                       # fine crumbs, bigger towards the camera
        y = rng.uniform(SOIL, H)
        r = 3 + (y - SOIL) / (H - SOIL) * 12 * rng.uniform(0.5, 1)
        g.append(f'<ellipse cx="{rng.uniform(0, W):.0f}" cy="{y:.0f}" rx="{r:.1f}" ry="{r * 0.6:.1f}" '
                 f'fill="{"#d97a42" if rng.random() < 0.5 else "#9c4520"}" stroke="{OUT}" stroke-width="1.5" stroke-opacity="0.6"/>')
    return "".join(g)


def seedling(x, s, u):
    """u: 0..1 growth. Hook rises and straightens (0-0.6), then the leaf opens (0.55-1)."""
    if u <= 0:
        return ""
    rise = ease(u / 0.6)
    hgt = 120 * s * rise
    bend = (1 - ease((u - 0.3) / 0.35)) * 70 * s        # hooked top straightens
    top = (x + bend * 0.3, SOIL - hgt)
    g = [f'<ellipse cx="{x - 22 * s:.0f}" cy="{SOIL - 4:.0f}" rx="{26 * s:.0f}" ry="{14 * s:.0f}" fill="#d8b98a" stroke="{OUT}" stroke-width="3"/>',
         f'<ellipse cx="{x + 22 * s:.0f}" cy="{SOIL - 4:.0f}" rx="{26 * s:.0f}" ry="{14 * s:.0f}" fill="#d8b98a" stroke="{OUT}" stroke-width="3"/>']
    d = f"M {x},{SOIL} Q {x + bend:.0f},{SOIL - hgt * 0.6:.0f} {top[0]:.0f},{top[1]:.0f}"
    g.append(f'<path d="{d}" fill="none" stroke="{OUT}" stroke-width="{22 * s:.1f}" stroke-linecap="round"/>'
             f'<path d="{d}" fill="none" stroke="#7cb342" stroke-width="{14 * s:.1f}" stroke-linecap="round"/>')
    op = ease((u - 0.55) / 0.45)
    if op > 0:
        k = 0.35 + 0.65 * op
        g.append(f'<g transform="translate({top[0]:.0f} {top[1]:.0f}) scale({k:.3f}) translate({-top[0]:.0f} {-top[1]:.0f})">'
                 f'{leaf(top[0], top[1], -90, s * 1.5)}</g>')
    elif rise > 0.5:                                      # folded leaf bud on the hook
        g.append(f'<ellipse cx="{top[0]:.0f}" cy="{top[1]:.0f}" rx="{14 * s:.0f}" ry="{22 * s:.0f}" fill="#5fa83a" stroke="{OUT}" stroke-width="3"/>')
    return "".join(g)


def main():
    out, cfg = sys.argv[1], json.loads(Path(sys.argv[2]).read_text())
    sky = base64.b64encode(sky_png()).decode()
    ground = soil()
    fps = cfg.get("fps", 25)
    n = round(cfg["duration"] * fps)
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "image2pipe", "-framerate", str(fps), "-i", "-",
                           "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    cams = cfg["camera"]
    for i in range(n):
        t = i / fps
        g = phase(t, cfg["grow"])
        cy = np.interp(t, [c[0] for c in cams], [c[1] for c in cams])
        h = np.interp(t, [c[0] for c in cams], [c[2] for c in cams])
        w = h * W / H
        parts = [f'<image href="data:image/png;base64,{sky}" x="0" y="{SOIL + 40 - 1220}" width="{W}" height="1220"/>', ground]
        for x, s, delay in PLANTS:
            parts.append(seedling(x, s, (g - delay) / (1 - delay) if g > delay else 0))
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
               f'viewBox="{W / 2 - w / 2:.1f} {cy - h / 2:.1f} {w:.1f} {h:.1f}">{"".join(parts)}</svg>')
        ff.stdin.write(cairosvg.svg2png(bytestring=svg.encode()))
    ff.stdin.close()
    ff.wait()
    print("saved", out)


if __name__ == "__main__":
    main()
