"""Animated soil cut-away for Groundnut Ep 2: why the field is prepared before sowing. 1080x1920.

Usage:
    python tools/toon/soil_prep.py OUT.mp4 TIMING.json

TIMING.json: {"duration": 9.0, "fps": 25,
              "loosen": [t0, t1],   # hard clods break into fine crumbs; stones and weeds come out
              "seed":   [t0, t1],   # a groundnut kernel drops into the loose soil
              "root":   [t0, t1],   # the taproot grows down first
              "spread": [t0, t1],   # side roots spread wide through the loose soil
              "shoot":  [t0, t1],   # the shoot comes up with its first leaf (four leaflets)
              "camera": [[t, cy, h], ...]}    # view centre y and view height on the 1080x1920 stage

Agronomy (TNAU): plough 2-3 times to a fine tilth; groundnut wants loose, friable, well-drained soil,
free of clods, stones and weeds. Botany: on germination the radicle (taproot) comes out first, side roots
follow, then the shoot with a leaf of four leaflets. Root nodules form weeks later, so none are drawn.
Same drawing style as tools/toon/cutaway.py (its sky and leaf are reused).
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
from cutaway import OUT, ease, leaf, phase, sky_png  # noqa: E402

W, H = 1080, 1920
SOIL = 760                  # soil surface y
RNG = np.random.default_rng(11)
SEED_AT = (540, SOIL + 170)


def soil_base(loose):
    """Soil body: darker and dense when hard, lighter red with air pores when loose (crossfaded)."""
    g = [f'<defs><linearGradient id="hard" x1="0" y1="0" x2="0" y2="1">'
         f'<stop offset="0" stop-color="#8f3d1c"/><stop offset="1" stop-color="#5e2510"/></linearGradient>'
         f'<linearGradient id="loose" x1="0" y1="0" x2="0" y2="1">'
         f'<stop offset="0" stop-color="#cf6a34"/><stop offset="0.5" stop-color="#b8532a"/>'
         f'<stop offset="1" stop-color="#83361a"/></linearGradient></defs>',
         f'<rect x="0" y="{SOIL}" width="{W}" height="{H - SOIL}" fill="url(#hard)"/>',
         f'<rect x="0" y="{SOIL}" width="{W}" height="{H - SOIL}" fill="url(#loose)" fill-opacity="{loose:.3f}"/>']
    return "".join(g)


def make_static():
    rng = np.random.default_rng(11)
    hard = []   # cracks of a hard pan
    for _ in range(18):
        x, y = rng.uniform(0, W), rng.uniform(SOIL + 60, H - 60)
        pts = [(x, y)]
        for _ in range(4):
            x += rng.uniform(-60, 60)
            y += rng.uniform(20, 70)
            pts.append((x, y))
        hard.append(f'<polyline points="{" ".join(f"{a:.0f},{b:.0f}" for a, b in pts)}" fill="none" '
                    f'stroke="#3d170a" stroke-opacity="0.55" stroke-width="5" stroke-linecap="round"/>')
    pores = []  # air spaces and crumbs of loose soil
    for _ in range(420):
        x, y = rng.uniform(0, W), rng.uniform(SOIL + 10, H - 10)
        r = rng.uniform(3, 9)
        if rng.random() < 0.5:
            pores.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.1f}" fill="#4a1d0c" fill-opacity="0.35"/>')
        else:
            pores.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.1f}" fill="#e89262" fill-opacity="0.5"/>')
    return "".join(hard), "".join(pores)


CLODS = [(x, SOIL - 10 + RNG.uniform(-8, 10), RNG.uniform(60, 95)) for x in np.arange(40, W, 120)]
BURIED = [(RNG.uniform(60, W - 60), RNG.uniform(SOIL + 90, SOIL + 560), RNG.uniform(55, 95)) for _ in range(10)]
STONES = [(200, SOIL + 70, 52, -1), (860, SOIL + 120, 58, 1), (330, SOIL + 330, 44, -1), (780, SOIL + 400, 42, 1)]
WEEDS = [(110, -1), (330, -1), (760, 1), (985, 1)]


def clod(x, y, r, s, dark=False):
    if s <= 0.02:
        return ""
    pts = []
    for k in range(7):
        a = k / 7 * 2 * math.pi
        rr = r * (0.75 + 0.25 * math.sin(3 * a + x))
        pts.append((x + rr * math.cos(a) * s, y + rr * 0.62 * math.sin(a) * s))
    fill = "#8a3a18" if dark else "#a6481f"
    return (f'<polygon points="{" ".join(f"{a:.0f},{b:.0f}" for a, b in pts)}" fill="{fill}" '
            f'stroke="{OUT}" stroke-width="3.5" stroke-linejoin="round"/>')


def crumbs(L):
    """Fine crumbs on the surface, appearing as the clods break."""
    if L <= 0:
        return ""
    rng = np.random.default_rng(3)
    g = [f'<path d="M 0,{SOIL + 14} ' + " ".join(f"L {x},{SOIL - 6 + 7 * math.sin(x / 37) + 4 * math.sin(x / 11):.0f}"
                                                for x in range(0, W + 20, 20)) +
         f' L {W},{SOIL + 14} Z" fill="#c9652f" fill-opacity="{L:.3f}"/>']
    for _ in range(150):
        x, y = rng.uniform(0, W), SOIL - 4 + rng.uniform(-6, 18)
        r = rng.uniform(4, 13) * L
        g.append(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{r:.1f}" ry="{r * 0.7:.1f}" '
                 f'fill="{"#d97a42" if rng.random() < 0.6 else "#b65428"}" stroke="{OUT}" stroke-width="2" stroke-opacity="0.8"/>')
    return "".join(g)


def stone(x, y, r, side, u):
    """Stone lifts out of the soil and away to the side (picked out by hand)."""
    if u >= 1:
        return ""
    k = ease(u)
    x += side * 520 * k * k
    y -= (y - SOIL + 260) * k
    return (f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{r:.0f}" ry="{r * 0.68:.0f}" fill="#a39a95" '
            f'stroke="{OUT}" stroke-width="3.5"/><ellipse cx="{x - r * 0.3:.0f}" cy="{y - r * 0.25:.0f}" '
            f'rx="{r * 0.35:.0f}" ry="{r * 0.18:.0f}" fill="#d4ccc6"/>')


def weed(x, side, u):
    """A grass tuft with fibrous roots, pulled up and away."""
    if u >= 1:
        return ""
    k = ease(u)
    dx, dy = side * 420 * k * k, -360 * k
    g = [f'<g transform="translate({dx:.0f} {dy:.0f}) rotate({side * 25 * k:.0f} {x} {SOIL})">']
    for a in (-30, -15, 0, 12, 28):
        bx = x + a * 2.2
        g.append(f'<path d="M {x},{SOIL} Q {x + a * 0.6:.0f},{SOIL - 70} {bx:.0f},{SOIL - 190 - abs(a) * 1.2:.0f}" '
                 f'fill="none" stroke="{OUT}" stroke-width="12" stroke-linecap="round"/>'
                 f'<path d="M {x},{SOIL} Q {x + a * 0.6:.0f},{SOIL - 70} {bx:.0f},{SOIL - 190 - abs(a) * 1.2:.0f}" '
                 f'fill="none" stroke="#7fae3c" stroke-width="7" stroke-linecap="round"/>')
    for a in (-24, -10, 4, 18):
        g.append(f'<path d="M {x},{SOIL + 4} Q {x + a * 1.3:.0f},{SOIL + 60} {x + a * 2.2:.0f},{SOIL + 130}" fill="none" '
                 f'stroke="#e6cf9f" stroke-width="5" stroke-linecap="round"/>')
    g.append("</g>")
    return "".join(g)


def kernel(x, y, s=1.0):
    """A shelled groundnut kernel: plump oval with a pink-red seed coat."""
    return (f'<g transform="translate({x:.0f} {y:.0f}) rotate(-18) scale({s:.3f})">'
            f'<path d="M -34,0 C -34,-22 -10,-26 4,-22 C 22,-26 36,-14 36,0 C 36,16 20,24 2,22 C -14,26 -34,20 -34,0 Z" '
            f'fill="#c9605a" stroke="{OUT}" stroke-width="3.5"/>'
            f'<path d="M -22,-10 C -12,-16 4,-16 14,-12" stroke="#e8968c" stroke-width="4" fill="none" stroke-linecap="round"/>'
            f'<path d="M -32,2 C -36,6 -36,10 -30,12" stroke="#7a2f2a" stroke-width="3" fill="none"/></g>')


def grow_path(pts, frac, width, colour="#e9d3a8"):
    if frac <= 0:
        return ""
    m = max(2, int(round(len(pts) * min(frac, 1))))
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts[:m])
    return (f'<polyline points="{d}" fill="none" stroke="{OUT}" stroke-width="{width + 5}" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<polyline points="{d}" fill="none" stroke="{colour}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>')


def curve(p0, p1, p2, n=40):
    return [((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * p1[0] + u * u * p2[0],
             (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * p1[1] + u * u * p2[1]) for u in np.linspace(0, 1, n)]


SX, SY = SEED_AT
TAPROOT = curve((SX - 8, SY + 14), (SX + 20, SY + 450), (SX - 6, SY + 900), 60)
SIDE = [(0.18, -1, 300), (0.28, 1, 340), (0.42, -1, 380), (0.55, 1, 330), (0.68, -1, 280), (0.8, 1, 220)]
SHOOT = curve((SX + 6, SY - 16), (SX + 22, SOIL - 40), (SX, SOIL - 250), 40)


def side_roots(frac):
    g = []
    for i, (f, side, ln) in enumerate(SIDE):
        x0, y0 = TAPROOT[int(f * (len(TAPROOT) - 1))]
        pts = curve((x0, y0), (x0 + side * ln * 0.55, y0 + 30), (x0 + side * ln, y0 + ln * 0.45), 30)
        g.append(grow_path(pts, ease((frac - 0.08 * i) / 0.6), 6))
        for j, (ff, sub) in enumerate(((0.45, 70), (0.75, 55))):   # finer root hairs off each side root
            bx, by = pts[int(ff * 29)]
            sp = curve((bx, by), (bx + side * sub * 0.3, by + sub * 0.6), (bx + side * sub * 0.5, by + sub), 16)
            g.append(grow_path(sp, ease((frac - 0.08 * i - 0.25 - 0.1 * j) / 0.4), 3))
    return "".join(g)


def water_and_days(t, cfg):
    """Optional: "water": [t0, t1] rain-can drops soak the soil darker; "days": [t0, t1, n] n day/night cycles."""
    g = []
    if "water" in cfg:
        w = phase(t, cfg["water"])
        if 0 < w < 1:
            rng = np.random.default_rng(int(t * 25))
            for _ in range(55):
                x, y = rng.uniform(0, W), rng.uniform(SOIL - 500, SOIL)
                g.append(f'<path d="M {x:.0f},{y:.0f} q -11,26 0,40 q 11,-14 0,-40 Z" fill="#8fd0ff" stroke="#2f6f9f" stroke-width="3"/>')
        if w > 0:
            g.append(f'<rect x="0" y="{SOIL}" width="{W}" height="{H - SOIL}" fill="#3a1408" fill-opacity="{0.3 * w:.3f}"/>')
    if "days" in cfg:
        t0, t1, n = cfg["days"]
        if t0 < t < t1:
            u = (t - t0) / (t1 - t0) * n
            dark = 0.5 - 0.5 * math.cos(2 * math.pi * u)          # 0 = day, 1 = night
            g.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#0b1a3a" fill-opacity="{0.6 * dark:.3f}"/>')
            if dark > 0.4:
                g.append(f'<circle cx="{820}" cy="{SOIL - 330}" r="44" fill="#f4f1d0" fill-opacity="{(dark - 0.4) / 0.6:.3f}"/>')
    return "".join(g)


class SoilPrep:
    def __init__(self):
        sky = sky_png()
        self.sky = base64.b64encode(sky).decode()
        self.sky_h = 1220                     # cutaway.sky_png() is 1080 x (its soil line + 40)
        self.hard, self.pores = make_static()

    def svg(self, t, cfg):
        L = phase(t, cfg["loosen"])
        sd, rt, sp, sh = (phase(t, cfg[k]) for k in ("seed", "root", "spread", "shoot"))
        cams = cfg["camera"]
        cy = np.interp(t, [c[0] for c in cams], [c[1] for c in cams])
        h = np.interp(t, [c[0] for c in cams], [c[2] for c in cams])
        w = h * W / H
        p = [f'<image href="data:image/png;base64,{self.sky}" x="0" y="{SOIL + 40 - self.sky_h}" width="{W}" height="{self.sky_h}"/>',
             soil_base(L),
             f'<g opacity="{1 - L:.3f}">{self.hard}</g>',
             f'<g opacity="{L:.3f}">{self.pores}</g>']
        for x, y, r in BURIED:                # buried clods crumble away
            p.append(clod(x, y, r, 1 - ease(L * 1.3), dark=True))
        for i, (x, y, r, side) in enumerate(STONES):
            p.append(stone(x, y, r, side, ease((L - 0.1 * i) / 0.5)))
        for i, (x, side) in enumerate(WEEDS):
            p.append(weed(x, side, ease((L - 0.05 - 0.1 * i) / 0.5)))
        # roots under, seed, shoot above
        p.append(side_roots(sp))
        p.append(grow_path(TAPROOT, rt, 11))
        if sd > 0:
            y = SOIL - 260 + (SY - SOIL + 260) * ease(sd)
            p.append(kernel(SX, y, 1.6 + 0.15 * ease(rt)))          # swells a little as it takes up water
        if sh > 0:
            p.append(grow_path(SHOOT, sh, 9, "#6aa53a"))
            if sh > 0.75:
                s = ease((sh - 0.75) / 0.25)
                tx, ty = SHOOT[-1]
                p.append(f'<g transform="translate({tx:.0f} {ty:.0f}) scale({s:.3f}) translate({-tx:.0f} {-ty:.0f})">'
                         f'{leaf(tx, ty, -90, 1.35)}</g>')
        for x, y, r in CLODS:                 # surface: big clods give way to fine crumbs
            p.append(clod(x, y, r, 1 - ease(L * 1.2)))
        p.append(crumbs(ease((L - 0.2) / 0.8)))
        p.append(water_and_days(t, cfg))
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
                f'viewBox="{W / 2 - w / 2:.1f} {cy - h / 2:.1f} {w:.1f} {h:.1f}">{"".join(p)}</svg>')


def main():
    out, cfg = sys.argv[1], json.loads(Path(sys.argv[2]).read_text())
    c = SoilPrep()
    fps = cfg.get("fps", 25)
    n = round(cfg["duration"] * fps)
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "image2pipe", "-framerate", str(fps), "-i", "-",
                           "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i in range(n):
        ff.stdin.write(cairosvg.svg2png(bytestring=c.svg(i / fps, cfg).encode()))
    ff.stdin.close()
    ff.wait()
    print("saved", out)


if __name__ == "__main__":
    main()
