"""Ice (ice katti), glasses of water and juice, a small table – and the Ep 6 cut-aways. 1080x1920.

Usage:
    python tools/toon/ice.py OUT.mp4 TIMING.json

TIMING.json: {"mode": "drop" | "race" | "heat" | "molecules" | "juice" | "cube", "duration": 3, "fps": 25,
              "span": [t0, t1], "camera": [[t, cy, h], ...]}
drop:      two glasses side by side (left: normal water; right: warm water, faint steam); equal ice cubes fall in, splash.
race:      the same two glasses: the cube in the warm water shrinks much faster than the one in normal water.
heat:      close-up: heat (orange wave arrows) flows from the warm water into the cube; it rounds off and shrinks.
molecules: inside the ice: water molecules locked in a neat lattice start to jiggle, break free and flow (solid -> liquid).
juice:     a glass of orange juice with ice; as the ice melts the juice gets paler (diluted) and the level rises a little.
cube:      one ice cube turning slowly, catching light, a drop running off it.
Science (NCERT Class 9 Science ch. 1 "Matter in our surroundings"; any physics text on heat transfer): heat flows from
the warmer body to the colder one, faster when the temperature difference is larger; the ice uses that energy (latent
heat of fusion) to change from solid to liquid without warming up until it has melted.
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import cairosvg
import numpy as np

W, H = 1080, 1920
OUT = "#24323b"


def mix(c1, c2, u):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    u = min(max(u, 0), 1)
    return "#" + "".join(f"{round(x + (y - x) * u):02x}" for x, y in zip(a, b))


def ease(u):
    u = min(max(u, 0), 1)
    return u * u * (3 - 2 * u)


def cube(x, y, size, ang=0.0, round_=0.0, opacity=1.0):
    """An ice cube (simple 3/4 view): pale blue faces, white highlights; round_ 0..1 melts the corners."""
    s = size / 2
    r = s * (0.18 + 0.6 * round_)
    return (f'<g transform="translate({x:.1f} {y:.1f}) rotate({ang:.1f})" opacity="{opacity:.2f}">'
            f'<rect x="{-s:.1f}" y="{-s:.1f}" width="{2 * s:.1f}" height="{2 * s:.1f}" rx="{r:.1f}" fill="#d6f0fb" fill-opacity="0.92" '
            f'stroke="#7fb6cf" stroke-width="{max(1.5, s * 0.07):.1f}"/>'
            f'<rect x="{-s * 0.7:.1f}" y="{-s * 0.7:.1f}" width="{s * 0.9:.1f}" height="{s * 0.5:.1f}" rx="{r * 0.6:.1f}" fill="#ffffff" fill-opacity="0.75"/>'
            f'<path d="M {s * 0.2:.1f},{s * 0.55:.1f} L {s * 0.7:.1f},{s * 0.2:.1f}" stroke="#a9d6ea" stroke-width="{s * 0.08:.1f}" '
            f'stroke-linecap="round"/></g>')


def glass(x, y, w, h, fill_h, liquid="#cfeaf6", liquid_op=0.55, steam=0.0, t=0.0):
    """A clear tumbler standing on (x, y) (bottom centre), w x h, liquid filled to fill_h (0..1)."""
    top, bot = w / 2, w * 0.42
    g = [f'<path d="M {x - top:.1f},{y - h:.1f} L {x + top:.1f},{y - h:.1f} L {x + bot:.1f},{y:.1f} L {x - bot:.1f},{y:.1f} Z" '
         f'fill="#eef7fb" fill-opacity="0.35" stroke="{OUT}" stroke-width="5"/>']
    lh = h * fill_h
    ltop = top - (top - bot) * (1 - fill_h)
    g.append(f'<path d="M {x - ltop:.1f},{y - lh:.1f} L {x + ltop:.1f},{y - lh:.1f} L {x + bot:.1f},{y - 4:.1f} L {x - bot:.1f},{y - 4:.1f} Z" '
             f'fill="{liquid}" fill-opacity="{liquid_op:.2f}"/>')
    g.append(f'<ellipse cx="{x:.1f}" cy="{y - lh:.1f}" rx="{ltop:.1f}" ry="{w * 0.06:.1f}" fill="{mix(liquid, "#ffffff", 0.4)}" '
             f'fill-opacity="{liquid_op:.2f}" stroke="{mix(liquid, OUT, 0.3)}" stroke-width="2" stroke-opacity="0.6"/>')
    g.append(f'<line x1="{x - top * 0.75:.1f}" y1="{y - h * 0.9:.1f}" x2="{x - bot * 0.75:.1f}" y2="{y - h * 0.1:.1f}" stroke="#ffffff" '
             f'stroke-width="{w * 0.05:.1f}" stroke-opacity="0.7" stroke-linecap="round"/>')
    for k in range(4 if steam else 0):
        ph = (t * 0.5 + k / 4) % 1
        sx = x - top * 0.5 + k * top * 0.35 + 8 * math.sin(t * 2 + k)
        g.append(f'<path d="M {sx:.0f},{y - h - ph * 160:.0f} q 14,-22 0,-44 q -14,-22 0,-44" stroke="#ffffff" stroke-width="7" '
                 f'fill="none" stroke-linecap="round" stroke-opacity="{0.7 * steam * (1 - ph) * min(1, ph * 4):.2f}"/>')
    return "".join(g)


def table(x, y, w, s=1.0):
    """A small wooden village table, top surface centred at (x, y)."""
    return (f'<rect x="{x - w / 2 + 14 * s:.1f}" y="{y:.1f}" width="{14 * s:.1f}" height="{150 * s:.1f}" fill="#7a4a24" stroke="#3b2210" stroke-width="3"/>'
            f'<rect x="{x + w / 2 - 28 * s:.1f}" y="{y:.1f}" width="{14 * s:.1f}" height="{150 * s:.1f}" fill="#7a4a24" stroke="#3b2210" stroke-width="3"/>'
            f'<rect x="{x - w / 2:.1f}" y="{y - 10 * s:.1f}" width="{w:.1f}" height="{24 * s:.1f}" rx="{5 * s:.1f}" fill="#a0683a" stroke="#3b2210" stroke-width="4"/>')


def juice_glass(x, y, w, h, dil=0.0, ice=0.0, t=0.0):
    col = mix("#f39c27", "#f7d9a0", dil)
    g = glass(x, y, w, h, 0.78 + 0.08 * dil, col, 1.0)
    for k in range(3):
        if ice > 0.02:
            g += cube(x - w * 0.18 + k * w * 0.18, y - h * (0.72 + 0.08 * dil) + 6, w * 0.28 * ice, 10 * k - 10, 1 - ice, 0.85)
    return g


# ---------------------------------------------------------------- cut-aways

def room():
    return (f'<rect width="{W}" height="{H}" fill="#f1e2c6"/><rect y="1240" width="{W}" height="{H - 1240}" fill="#a0683a"/>'
            f'<rect y="1240" width="{W}" height="26" fill="#7d4c28"/>')


def scene(t, cfg):
    mode, span = cfg["mode"], cfg["span"]
    p = ease((t - span[0]) / (span[1] - span[0]))
    g = [room()]
    if mode in ("drop", "race"):
        if mode == "drop":
            fall = [ease((t - span[0] - k * 0.25) / 0.6) for k in (0, 1)]
            sizes = [1.0, 1.0]
        else:
            fall = [1.0, 1.0]
            sizes = [1 - 0.25 * p, max(0.0, 1 - 1.0 * p)]      # warm water: ~4x faster
        for k, (x, warm) in enumerate(((320, False), (760, True))):
            g.append(glass(x, 1240, 300, 420, 0.7, "#cfeaf6" if not warm else "#d8eef7", 0.55, 1.0 if warm else 0.0, t))
            y = 600 + (1240 - 420 * 0.7 - 40 - 600) * fall[k]
            if sizes[k] > 0.03:
                g.append(cube(x + (k - 0.5) * 10, y + 40 * (1 - sizes[k]), 120 * sizes[k], 12 - 20 * k, 1 - sizes[k], 0.95))
            if 0.85 < fall[k] < 1.0 or (mode == "drop" and 0 < t - span[0] - k * 0.25 - 0.6 < 0.35):
                for d in range(6):
                    a = math.radians(-160 + d * 28)
                    g.append(f'<circle cx="{x + math.cos(a) * 110:.0f}" cy="{1240 - 294 + math.sin(a) * 60:.0f}" r="9" fill="#bfe6f7"/>')
            if mode == "race" and warm:
                for d in range(5):                              # meltwater swirls around the shrinking cube
                    ph = (t * 0.9 + d / 5) % 1
                    g.append(f'<circle cx="{x - 60 + d * 30:.0f}" cy="{1000 + ph * 160:.0f}" r="5" fill="#9fd3ec" fill-opacity="{1 - ph:.2f}"/>')
    elif mode == "heat":
        g = ['<rect width="1080" height="1920" fill="#f7c58f"/>']
        size = 360 * (1 - 0.55 * p)
        for k in range(10):                                     # heat waves flowing in from all sides
            a = k / 10 * 2 * math.pi
            ph = (t * 0.8 + k * 0.13) % 1
            r = 520 - ph * (520 - size * 0.6)
            cx, cy = 540 + math.cos(a) * r, 960 + math.sin(a) * r
            ang = math.degrees(a) + 180
            g.append(f'<g transform="translate({cx:.0f} {cy:.0f}) rotate({ang:.0f})" opacity="{min(1, ph * 3) * (1 - ph * 0.3):.2f}">'
                     f'<path d="M -40,0 q 10,-14 20,0 q 10,14 20,0 q 10,-14 20,0" stroke="#e8562a" stroke-width="9" fill="none" stroke-linecap="round"/>'
                     f'<path d="M 24,-12 L 42,0 L 24,12" stroke="#e8562a" stroke-width="9" fill="none" stroke-linecap="round"/></g>')
        g.append(cube(540, 960, size, 8, p, 1.0))
        for d in range(4):
            ph = (t * 0.7 + d / 4) % 1
            g.append(f'<ellipse cx="{470 + d * 45:.0f}" cy="{960 + size / 2 + ph * 300:.0f}" rx="9" ry="13" fill="#7fc2e6" fill-opacity="{1 - ph:.2f}"/>')
    elif mode == "molecules":
        g = ['<rect width="1080" height="1920" fill="#e8f5fb"/>']
        rng = np.random.default_rng(4)
        for i in range(8):
            for j in range(6):
                x0, y0 = 170 + j * 150 + (75 if i % 2 else 0), 480 + i * 130
                free = ease((p - (j + i * 0.3) / 12) * 3)       # breaks free from one side first
                jig = 6 + 30 * free
                x = x0 + jig * math.sin(t * 7 + i * 3 + j) + free * 120 * math.sin(t * 1.3 + i + j * 2)
                y = y0 + jig * math.cos(t * 6 + j * 2 + i) + free * 90 * math.cos(t * 1.1 + i * 2 + j)
                if free < 0.5 and j < 5:                         # bonds of the solid lattice fade as it melts
                    g.append(f'<line x1="{x:.0f}" y1="{y:.0f}" x2="{x0 + 150:.0f}" y2="{y0:.0f}" stroke="#7fb6cf" stroke-width="5" '
                             f'stroke-opacity="{1 - 2 * free:.2f}"/>')
                g.append(f'<g transform="translate({x:.0f} {y:.0f})"><circle r="26" fill="#e74c3c" stroke="#8e2a20" stroke-width="3"/>'
                         f'<circle cx="-22" cy="20" r="14" fill="#ffffff" stroke="#888" stroke-width="2"/>'
                         f'<circle cx="22" cy="20" r="14" fill="#ffffff" stroke="#888" stroke-width="2"/></g>')
        _ = rng
    elif mode == "juice":
        g.append(juice_glass(540, 1240, 340, 520, dil=p, ice=1 - 0.85 * p, t=t))
    else:  # cube
        g = ['<rect width="1080" height="1920" fill="#cfe7f2"/>']
        g.append(cube(540, 900, 420, 8 * math.sin(t * 0.9), 0.15 * p))
        ph = (t * 0.6) % 1
        g.append(f'<ellipse cx="660" cy="{1110 + ph * 300:.0f}" rx="14" ry="20" fill="#9fd3ec" fill-opacity="{1 - ph:.2f}" stroke="#5aa0c8" stroke-width="3"/>')
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
