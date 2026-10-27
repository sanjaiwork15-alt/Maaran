"""Potted plant / watering cut-aways (Maaran Thatha – Day 2). 1080x1920.

Usage:
    python tools/toon/pot.py OUT.mp4 TIMING.json
TIMING.json: {"mode": "pour" | "finger" | "section" | "tilt", "duration": 4, "fps": 25, "span": [t0, t1],
              "camera": [[t, cy, h], ...]}
pour:    close-up: the watering can's rose pours into the clay pot; the soil darkens, then water runs out of the
         drainage hole and a puddle spreads under the pot.
finger:  his finger presses into the soil and lifts out with dark wet soil on the tip – the moisture test.
tilt:    the pot tilts towards us, showing the drainage hole underneath with a drop hanging from it.
section: cross-section of the pot: soil grains with air pockets (white) between them and healthy white roots; then
         water fills the pockets (blue), the air bubbles out at the top and the roots turn brown.
Science (horticulture, e.g. RHS "Watering"; University of Minnesota Extension "Watering houseplants"): roots need oxygen
from the air spaces in the soil; constant overwatering fills those spaces with water, roots suffocate and rot; check
the soil a finger-joint deep and water when it feels dry; pots need drainage holes.
"""
import io
import json
import math
import subprocess
import sys
from pathlib import Path

import cairosvg
import numpy as np
from PIL import Image

W, H = 1080, 1920
CLAY, CLAY_D, CLAY_L, LINE = "#c8643a", "#9c4524", "#e08a5c", "#5a2410"
SKIN, SKIN_D = "#e4894a", "#a95a28"


def ease(u):
    u = min(max(u, 0), 1)
    return u * u * (3 - 2 * u)


def bg():
    return (f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#cfe8f5"/>'
            f'<stop offset="0.55" stop-color="#f6e3c4"/><stop offset="1" stop-color="#c98a56"/></linearGradient></defs>'
            f'<rect width="{W}" height="{H}" fill="url(#bg)"/>'
            f'<rect y="{H * 0.68}" width="{W}" height="{H * 0.32}" fill="#c27a44"/>')


def plant(x, y, s=1.0):
    g = ""
    for ang, ln in ((-62, 46), (-30, 52), (-95, 58), (-125, 50), (-150, 44)):
        a = math.radians(ang)
        ex, ey = x + math.cos(a) * ln * s, y + math.sin(a) * ln * s
        g += (f'<path d="M {x},{y} Q {x + math.cos(a - 0.35) * ln * 0.6 * s:.0f},{y + math.sin(a - 0.35) * ln * 0.6 * s:.0f} '
              f'{ex:.0f},{ey:.0f} Q {x + math.cos(a + 0.35) * ln * 0.6 * s:.0f},{y + math.sin(a + 0.35) * ln * 0.6 * s:.0f} {x},{y} Z" '
              f'fill="#4caf3c" stroke="#24651c" stroke-width="{2.5 * s:.1f}"/>')
    return g + f'<path d="M {x},{y} L {x},{y - 22 * s:.0f}" stroke="#2f7d24" stroke-width="{4 * s:.0f}"/>'


def pot(x, base, w, wet=0.0, ang=0.0):
    h = w * 0.82
    top, bot = w / 2, w * 0.36
    soil = f"rgb({int(122 - 40 * wet)},{int(74 - 24 * wet)},{int(42 - 12 * wet)})"
    return (f'<g transform="rotate({ang} {x} {base})">'
            f'<path d="M {x - top:.0f},{base - h:.0f} L {x + top:.0f},{base - h:.0f} L {x + bot:.0f},{base} L {x - bot:.0f},{base} Z" '
            f'fill="{CLAY}" stroke="{LINE}" stroke-width="{w / 35:.1f}"/>'
            f'<path d="M {x - top * 0.62:.0f},{base - h * 0.86:.0f} L {x - bot * 0.55:.0f},{base - w * 0.05:.0f}" stroke="{CLAY_L}" '
            f'stroke-width="{w / 16:.0f}" stroke-linecap="round"/>'
            f'<rect x="{x - top - w * 0.05:.0f}" y="{base - h - w * 0.13:.0f}" width="{w * 1.1:.0f}" height="{w * 0.17:.0f}" rx="{w * 0.04:.0f}" '
            f'fill="{CLAY_D}" stroke="{LINE}" stroke-width="{w / 35:.1f}"/>'
            f'<ellipse cx="{x}" cy="{base - h - w * 0.12:.0f}" rx="{top - 2:.0f}" ry="{w * 0.06:.0f}" fill="{soil}"/>'
            + plant(x, base - h - w * 0.13, w / 110) + "</g>")


def puddle(x, y, r):
    if r <= 1:
        return ""
    return (f'<ellipse cx="{x}" cy="{y}" rx="{r * 1.12:.0f}" ry="{r * 0.3:.0f}" fill="#7a3a1a" fill-opacity="0.6"/>'
            f'<ellipse cx="{x}" cy="{y}" rx="{r * 0.92:.0f}" ry="{r * 0.23:.0f}" fill="#6fa6c4" fill-opacity="0.8" stroke="#4d7f99" stroke-width="3"/>'
            f'<ellipse cx="{x - r * 0.3:.0f}" cy="{y - r * 0.04:.0f}" rx="{r * 0.25:.0f}" ry="{r * 0.05:.0f}" fill="#fff" fill-opacity="0.6"/>')


def rose(x, y, ang=35):
    """The watering can's spout + rose coming in from the top right."""
    return (f'<g transform="translate({x} {y}) rotate({ang})"><rect x="0" y="-26" width="900" height="52" fill="#3f9a3a" stroke="#1d4d1a" stroke-width="6"/>'
            f'<ellipse cx="0" cy="0" rx="44" ry="70" fill="#2f7d2a" stroke="#1d4d1a" stroke-width="6"/>'
            + "".join(f'<circle cx="-6" cy="{dy}" r="6" fill="#163a14"/>' for dy in (-42, -21, 0, 21, 42)) + "</g>")


def streams(x, y0, y1, t, n=7, spread=70):
    s = ""
    for k in range(n):
        dx = (k - (n - 1) / 2) * spread / (n - 1)
        s += (f'<path d="M {x + dx * 0.35:.0f},{y0} Q {x + dx * 0.8:.0f},{(y0 + y1) / 2} {x + dx:.0f},{y1}" stroke="#bfe3f5" '
              f'stroke-width="7" fill="none" stroke-opacity="0.9" stroke-linecap="round" stroke-dasharray="40 18" '
              f'stroke-dashoffset="{-t * 900 + k * 13:.0f}"/>')
    return s


def scene_pour(t, cfg):
    span = cfg.get("span", [0, cfg["duration"]])
    p = (t - span[0]) / (span[1] - span[0])
    x, base, w = 540, 1560, 720
    wet = ease(p / 0.3)
    s = bg() + puddle(x, base + 10, 420 * ease((p - 0.4) / 0.4))
    s += pot(x, base, w, wet)
    if p > 0.35:                                                   # water out of the drainage hole
        q = ease((p - 0.35) / 0.2)
        s += (f'<path d="M {x - 30},{base - 4} q -6,{40 * q:.0f} -22,{90 * q:.0f}" stroke="#a9d4ea" stroke-width="16" fill="none" '
              f'stroke-linecap="round" stroke-opacity="0.95"/>'
              f'<path d="M {x + 40},{base - 4} q 8,{30 * q:.0f} 26,{70 * q:.0f}" stroke="#a9d4ea" stroke-width="12" fill="none" '
              f'stroke-linecap="round" stroke-opacity="0.9"/>')
    if p < 0.9:
        s += streams(x - 40, 420, base - w * 0.82 - 80, t) + rose(x - 20, 370)
    if wet > 0.6:
        s += f'<ellipse cx="{x + 30}" cy="{base - w * 0.82 - w * 0.12:.0f}" rx="{w * 0.2:.0f}" ry="{w * 0.025:.0f}" fill="#cfe9f7" fill-opacity="0.8"/>'
    return s


def finger(x, tip_y, wet=0.0):
    """His index finger pointing down, coming in from the top."""
    return (f'<path d="M {x - 120},{tip_y - 1100} L {x - 95},{tip_y - 90} Q {x},{tip_y + 30} {x + 95},{tip_y - 90} L {x + 120},{tip_y - 1100} Z" '
            f'fill="{SKIN}" stroke="{SKIN_D}" stroke-width="7"/>'
            f'<path d="M {x - 58},{tip_y - 80} Q {x},{tip_y - 50} {x + 58},{tip_y - 80} L {x + 52},{tip_y - 190} Q {x},{tip_y - 170} {x - 52},{tip_y - 190} Z" '
            f'fill="#f4c7a6" stroke="{SKIN_D}" stroke-width="4"/>'
            + "".join(f'<path d="M {x - 80},{tip_y - k} q 80,24 160,0" stroke="{SKIN_D}" stroke-width="5" fill="none"/>' for k in (420, 460))
            + (f'<path d="M {x - 95},{tip_y - 100} Q {x},{tip_y + 30} {x + 95},{tip_y - 100} L {x + 92},{tip_y - 170} Q {x},{tip_y - 50} {x - 92},{tip_y - 170} Z" '
               f'fill="#4a2a14" fill-opacity="{0.9 * wet:.2f}"/>' if wet > 0 else ""))


def soil_top(y):
    rng = np.random.default_rng(5)
    s = f'<rect y="{y}" width="{W}" height="{H - y}" fill="#5a3218"/>'
    for _ in range(320):
        s += (f'<circle cx="{rng.uniform(0, W):.0f}" cy="{rng.uniform(y + 10, H):.0f}" r="{rng.uniform(5, 18):.0f}" '
              f'fill="{rng.choice(["#4a2810", "#6b3c1e", "#3e220e", "#7a4524"])}"/>')
    for _ in range(40):
        s += (f'<ellipse cx="{rng.uniform(0, W):.0f}" cy="{rng.uniform(y + 10, H):.0f}" rx="{rng.uniform(8, 20):.0f}" ry="5" '
              f'fill="#cfe9f7" fill-opacity="0.45"/>')
    return s


def scene_finger(t, cfg):
    span = cfg.get("span", [0, cfg["duration"]])
    p = (t - span[0]) / (span[1] - span[0])
    y = 1100
    down = ease(p / 0.35) - ease((p - 0.6) / 0.3)                # in, hold, out
    tip = y - 260 + 420 * down
    s = (f'<rect width="{W}" height="{y}" fill="#9c4524"/>'
         f'<rect x="0" y="{y - 70}" width="{W}" height="70" fill="{CLAY_D}" stroke="{LINE}" stroke-width="8"/>')
    s += finger(540, tip, wet=ease((p - 0.6) / 0.15))              # behind the soil: it goes in
    s += soil_top(y)
    if down > 0.05:                                                # soil pushed up around the finger
        s += (f'<ellipse cx="540" cy="{y + 6}" rx="{150 * down:.0f}" ry="{26 * down:.0f}" fill="#3e220e"/>'
              f'<path d="M {540 - 140 * down:.0f},{y + 8} q {140 * down:.0f},-{36 * down:.0f} {280 * down:.0f},0" stroke="#4a2810" '
              f'stroke-width="{30 * down:.0f}" fill="none" stroke-linecap="round"/>')
    return s


def scene_tilt(t, cfg):
    span = cfg.get("span", [0, cfg["duration"]])
    p = (t - span[0]) / (span[1] - span[0])
    ang = -28 * ease(p / 0.4)
    x, base, w = 560, 1380, 600
    s = bg() + pot(x, base, w, 1.0, ang)
    hx, hy = x + math.sin(math.radians(-ang)) * 0, base
    if p > 0.3:                                                    # the hole underneath + a hanging drop
        q = ease((p - 0.3) / 0.2)
        s += (f'<g transform="rotate({ang} {x} {base})"><ellipse cx="{x}" cy="{base + 4}" rx="{w * 0.36:.0f}" ry="{w * 0.09 * q:.0f}" fill="{CLAY_D}" '
              f'stroke="{LINE}" stroke-width="12"/><circle cx="{x}" cy="{base + 4}" r="{36 * q:.0f}" fill="#24120a"/>'
              f'<ellipse cx="{x}" cy="{base + 50 + 30 * ((t * 1.4) % 1):.0f}" rx="14" ry="{20 * q:.0f}" fill="#a9d4ea" stroke="#6f9fbb" stroke-width="3"/></g>')
    return s


def grains(rng, x0, y0, x1, y1, n):
    out, tries = [], 0
    while len(out) < n and tries < 20000:
        tries += 1
        r = rng.uniform(26, 48)
        cx, cy = rng.uniform(x0 + r, x1 - r), rng.uniform(y0 + r, y1 - r)
        if all((cx - a) ** 2 + (cy - b) ** 2 > (r + c + 10) ** 2 for a, b, c in out):
            out.append((cx, cy, r))
    return out


def scene_section(t, cfg):
    span = cfg.get("span", [0, cfg["duration"]])
    p = (t - span[0]) / (span[1] - span[0])
    rng = np.random.default_rng(8)
    x0, x1, y0, y1 = 150, 930, 560, 1640
    fill = ease((p - 0.3) / 0.4)                                   # water fills the pockets
    rot = ease((p - 0.65) / 0.3)                                   # roots turn brown
    s = (f'<rect width="{W}" height="{H}" fill="#f3e6cf"/>'
         f'<path d="M 110,500 L 970,500 L 900,1700 L 180,1700 Z" fill="{CLAY}" stroke="{LINE}" stroke-width="10"/>'
         f'<path d="M {x0},{y0} L {x1},{y0} L {x1 - 50},{y1} L {x0 + 50},{y1} Z" fill="#fdfdfb"/>')
    wl = y1 - (y1 - y0 + 20) * fill                                # water level rising
    if fill > 0:
        s += (f'<clipPath id="in"><path d="M {x0},{y0} L {x1},{y0} L {x1 - 50},{y1} L {x0 + 50},{y1} Z"/></clipPath>'
              f'<rect x="0" y="{wl:.0f}" width="{W}" height="{H}" fill="#7fb8d8" clip-path="url(#in)"/>')
    for cx, cy, r in grains(rng, x0 + 40, y0 + 20, x1 - 40, y1 - 10, 95):
        s += f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r:.0f}" fill="#7a4a2a" stroke="#4e2c16" stroke-width="4"/>'
    rc = f"rgb({int(245 - 120 * rot)},{int(240 - 150 * rot)},{int(225 - 170 * rot)})"
    for k, (dx, ln) in enumerate(((-120, 700), (-40, 820), (60, 780), (150, 640), (-200, 520), (230, 500))):
        d = f"M 540,{y0 - 10}"
        x, y = 540.0, float(y0 - 10)
        for j in range(6):
            x += dx / 6 + 18 * math.sin(j * 1.7 + k)
            y += ln / 6
            d += f" L {x:.0f},{y:.0f}"
        s += f'<path d="{d}" stroke="{rc}" stroke-width="{11 - k:.0f}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
    for k in range(14):                                            # air bubbles escaping as the water rises
        u = (p - 0.32 - k * 0.025) / 0.25
        if 0 < u < 1:
            bx = x0 + 80 + (k * 53) % (x1 - x0 - 160)
            by = wl + 120 - 360 * u
            s += f'<circle cx="{bx:.0f}" cy="{by:.0f}" r="{10 + 6 * u:.0f}" fill="#ffffff" fill-opacity="{0.9 - 0.6 * u:.2f}" stroke="#6f9fbb" stroke-width="3"/>'
    s += (f'<rect x="90" y="440" width="900" height="80" rx="16" fill="{CLAY_D}" stroke="{LINE}" stroke-width="10"/>'
          + plant(540, 440, 4.2))
    return s


SCENES = {"pour": scene_pour, "finger": scene_finger, "tilt": scene_tilt, "section": scene_section}


def main():
    out = sys.argv[1]
    cfg = json.loads(Path(sys.argv[2]).read_text())
    fps = cfg.get("fps", 25)
    n = round(cfg["duration"] * fps)
    cams = cfg.get("camera", [[0, H / 2, H]])
    only = cfg.get("still")
    ff = None if only is not None else subprocess.Popen(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "image2pipe", "-framerate", str(fps), "-i", "-",
         "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i in ([0] if only is not None else range(n)):
        t = only if only is not None else i / fps
        cy = np.interp(t, [c[0] for c in cams], [c[1] for c in cams])
        h = np.interp(t, [c[0] for c in cams], [c[2] for c in cams])
        w = h * W / H
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
               f'viewBox="{W / 2 - w / 2:.1f} {cy - h / 2:.1f} {w:.1f} {h:.1f}">{SCENES[cfg["mode"]](t, cfg)}</svg>')
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
