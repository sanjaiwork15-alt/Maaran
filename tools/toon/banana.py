"""Bananas ripening after harvest (Thatha, Oru Doubt! Ep 1). 1080x1920.

Usage:
    python tools/toon/banana.py OUT.mp4 TIMING.json

TIMING.json: {"mode": "ripen" | "ethylene" | "home", "duration": 4.0, "fps": 25, "ripen": [t0, t1],
              "camera": [[t, cy, h], ...]}
ripen:    one picked banana on the kitchen table goes green -> yellow -> yellow with a few brown sugar spots
          while the window outside turns day/night several times (days passing).
ethylene: a banana that has started to ripen gives off ethylene (drawn as faint, colourless shimmer rings, no
          label – it is an invisible gas); the gas grows as it ripens (ripening fruit makes more ethylene,
          "autocatalytic") and reaches the green banana next to it, which then ripens too.
home:     a green hand of bananas from the shop in a basket turns yellow over a few days.
Science (ICAR-NRC Banana / TNAU post-harvest notes): bananas are climacteric fruits, harvested mature green; they
keep ripening after picking, driven by the plant hormone ethylene, which ripening fruit itself releases.
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
# one banana in local coords, ~460 px long, curving up at both ends; stem on the left, dark tip on the right
SKIN = ("M -205,-62 C -150,118 140,126 222,-58 C 226,-66 214,-74 208,-66 "
        "C 120,14 -130,10 -186,-78 Z")
RIDGE = "M -196,-70 C -120,66 120,72 214,-62"
STAGES = ["#4f8f2a", "#7fae2e", "#b9c834", "#e9d43c", "#f6d538", "#f4cc2e"]


def mix(c1, c2, u):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * u):02x}" for x, y in zip(a, b))


def skin_col(r):
    """r 0 (green) .. 1 (fully yellow)."""
    x = min(max(r, 0), 1) * (len(STAGES) - 1)
    i = min(int(x), len(STAGES) - 2)
    return mix(STAGES[i], STAGES[i + 1], x - i)


def banana(x, y, ang, s, r, spots=0.0, seed=0):
    """r = ripeness 0..1; spots 0..1 adds the brown sugar flecks of a fully ripe banana."""
    body = skin_col(r)
    shade = mix(body, "#3b2416", 0.25)
    tipg = mix(body, "#4f8f2a", 0.6)                       # ends stay greener a little longer
    rng = np.random.default_rng(seed)
    fl = ""
    if spots > 0:
        for _ in range(14):
            u = rng.uniform(-0.8, 0.8)
            fx = u * 190
            fy = 60 * (1 - u * u) - 20 + rng.uniform(-10, 10)
            fl += (f'<ellipse cx="{fx:.0f}" cy="{fy:.0f}" rx="{rng.uniform(3, 6) * spots:.1f}" ry="{rng.uniform(2, 4) * spots:.1f}" '
                   f'fill="#6b4220" fill-opacity="{0.85 * spots:.2f}"/>')
    return (f'<g transform="translate({x:.0f} {y:.0f}) rotate({ang:.1f}) scale({s:.2f})">'
            f'<path d="{SKIN}" fill="{body}" stroke="{OUT}" stroke-width="6" stroke-linejoin="round"/>'
            f'<path d="M -150,-6 C -90,74 90,80 170,0" stroke="{shade}" stroke-width="22" fill="none" stroke-opacity="0.35" stroke-linecap="round"/>'
            f'<path d="{RIDGE}" stroke="{shade}" stroke-width="3" fill="none" stroke-opacity="0.6"/>'
            f'<path d="M -205,-62 C -196,-58 -190,-66 -186,-78" stroke="{tipg}" stroke-width="18" fill="none" stroke-linecap="round"/>'
            f'{fl}'
            # stem (left) and dark blossom tip (right)
            f'<path d="M -200,-70 L -236,-118 L -222,-128 L -186,-80 Z" fill="{mix(tipg, "#6b5a2a", 0.4)}" stroke="{OUT}" stroke-width="5" stroke-linejoin="round"/>'
            f'<path d="M 208,-66 L 226,-60 L 230,-72 L 214,-74 Z" fill="#3b2a1a" stroke="{OUT}" stroke-width="4"/>'
            f'</g>')


def room(t, days, d_t=None):
    """Kitchen wall, a window whose sky cycles day/night `days` times over the ripen span, and a wooden table."""
    g = [f'<rect width="{W}" height="{H}" fill="#f1dfbf"/>',
         f'<rect y="0" width="{W}" height="{H}" fill="url(#wall)"/>']
    # window (top right)
    u = d_t if d_t is not None else 0.0
    day = 0.5 - 0.5 * math.cos(2 * math.pi * u * days)     # 0 day .. 1 night
    sky = mix("#8fd0f5", "#1f2b4f", day)
    g.append(f'<rect x="600" y="230" width="360" height="420" rx="10" fill="{sky}" stroke="#6b4423" stroke-width="22"/>')
    a = 2 * math.pi * u * days
    sx, sy = 780 + 120 * math.sin(a), 470 - 170 * math.cos(a)
    g.append('<clipPath id="win"><rect x="611" y="241" width="338" height="398"/></clipPath>')
    g.append(f'<g clip-path="url(#win)"><circle cx="{sx:.0f}" cy="{sy:.0f}" r="44" fill="#ffd84a" fill-opacity="{1 - day:.2f}"/>'
             f'<circle cx="{1560 - sx:.0f}" cy="{940 - sy:.0f}" r="34" fill="#f4f1de" fill-opacity="{day:.2f}"/>'
             f'<path d="M 611,600 C 700,560 820,590 949,550 L 949,639 L 611,639 Z" fill="{mix("#5d9c3a", "#1d3326", day)}"/></g>')
    g.append('<line x1="780" y1="230" x2="780" y2="650" stroke="#6b4423" stroke-width="14"/>'
             '<line x1="600" y1="440" x2="960" y2="440" stroke="#6b4423" stroke-width="14"/>')
    # table
    g.append(f'<rect x="0" y="1180" width="{W}" height="{H - 1180}" fill="#a8693a"/>')
    g.append(f'<rect x="0" y="1180" width="{W}" height="40" fill="#8a5330"/>')
    for k in range(6):
        g.append(f'<line x1="0" y1="{1300 + k * 110}" x2="{W}" y2="{1290 + k * 110}" stroke="#8a5330" stroke-width="4" stroke-opacity="0.6"/>')
    # a darker room when it is night outside
    g.append(f'<rect width="{W}" height="{H}" fill="#1f2b4f" fill-opacity="{0.22 * day:.2f}"/>')
    return g


def shimmer(cx, cy, t, amount, seed):
    """Ethylene: colourless gas, drawn as faint expanding wavy rings."""
    out = []
    for k in range(5):
        ph = (t * 0.55 + k / 5 + seed * 0.13) % 1
        r = 60 + ph * 330
        op = amount * 0.75 * (1 - ph) * min(1, ph * 5)
        if op < 0.01:
            continue
        pts = []
        for j in range(49):
            a = j / 48 * 2 * math.pi
            rr = r * (1 + 0.05 * math.sin(6 * a + t * 3 + k))
            pts.append(f"{cx + rr * math.cos(a) * 1.25:.0f},{cy + rr * math.sin(a) * 0.8:.0f}")
        out.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="#ffffff" stroke-width="7" '
                   f'stroke-opacity="{op:.2f}" stroke-dasharray="26 16"/>')
    return out


DEFS = ('<defs><linearGradient id="wall" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f6e7c9"/>'
        '<stop offset="1" stop-color="#e2c79c"/></linearGradient></defs>')


def scene(t, cfg):
    mode = cfg["mode"]
    p = phase(t, cfg["ripen"])
    if mode == "ripen":
        g = room(t, cfg.get("days", 4), p)
        g.append('<ellipse cx="540" cy="1330" rx="300" ry="34" fill="#3b2416" fill-opacity="0.25"/>')
        g.append(banana(540, 1260, -4, 1.2, p, spots=phase(p, [0.8, 1.0]), seed=3))
    elif mode == "ethylene":
        g = room(t, 0)
        r1 = 0.35 + 0.65 * p                               # first banana has already started to ripen
        gas = 0.35 + 0.65 * p
        r2 = phase(p, [0.3, 1.0]) * 0.9                    # the green neighbour follows
        g += shimmer(420, 1110, t, gas, 0)
        g += shimmer(420, 1110, t + 0.9, gas * 0.8, 2)
        g.append('<ellipse cx="420" cy="1340" rx="270" ry="30" fill="#3b2416" fill-opacity="0.25"/>')
        g.append('<ellipse cx="760" cy="1520" rx="250" ry="28" fill="#3b2416" fill-opacity="0.25"/>')
        g.append(banana(420, 1270, -6, 1.05, r1, seed=4))
        g.append(banana(680, 1450, 8, 0.9, r2, seed=5))
    else:  # home: a hand of bananas in a basket
        g = room(t, cfg.get("days", 3), p)
        g.append('<ellipse cx="540" cy="1480" rx="380" ry="40" fill="#3b2416" fill-opacity="0.3"/>')
        g.append('<path d="M 200,1230 L 880,1230 L 870,1270 L 210,1270 Z" fill="#8a5a2a" stroke="#3b2416" stroke-width="7"/>')
        for k, (x, y, a) in enumerate([(520, 1215, -10), (600, 1205, -4), (560, 1250, 2), (640, 1255, 8)]):
            g.append(banana(x, y, a, 0.85, p, spots=phase(p, [0.85, 1.0]) * 0.7, seed=10 + k))
        g.append('<path d="M 200,1290 L 880,1290 L 820,1470 L 260,1470 Z" fill="#c9954f" stroke="#3b2416" stroke-width="7"/>')
        for k in range(4):
            g.append(f'<line x1="{220 + k * 12}" y1="{1330 + k * 38}" x2="{860 - k * 12}" y2="{1330 + k * 38}" stroke="#9b6a32" stroke-width="6"/>')
        g.append('<path d="M 190,1270 L 890,1270 L 880,1310 L 200,1310 Z" fill="#b07d3c" stroke="#3b2416" stroke-width="7"/>')
    return DEFS + "".join(g)


def main():
    out, cfg = sys.argv[1], json.loads(Path(sys.argv[2]).read_text())
    fps = cfg.get("fps", 25)
    n = round(cfg["duration"] * fps)
    cams = cfg.get("camera", [[0, H / 2, H]])
    only = cfg.get("still")                                # debug: write one PNG at this time
    if only is not None:
        cams = cams + [[1e9, cams[-1][1], cams[-1][2]]]
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
