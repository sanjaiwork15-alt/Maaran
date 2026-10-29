"""A groundnut seed from sowing to seedling, seen as a soil cross-section (Maaran Thatha – Day 4). 1080x1920.

Usage:
    python tools/toon/sprout.py OUT.mp4 TIMING.json
TIMING.json: {"mode": "sow" | "grow" | "seed", "duration": 6, "fps": 25, "span": [t0, t1], "camera": [[t, cy, h], ...]}
seed:  close-up of one groundnut kernel (pink skin) held between finger and thumb against the blurred field.
sow:   a finger pokes a small hole, the kernel drops in, soil closes over it, water drops soak in (dark wet soil),
       the sun's warmth (warm glow) and air pockets between the soil grains (white) – what a seed needs:
       water, warmth, air.
grow:  time-lapse: the sky above flickers day/night; the kernel swells with water, the root (radicle) comes out first
       and grows down with side roots, then the shoot pushes up as a hook, breaks the surface and straightens, and the
       first leaf (four leaflets) opens; then a second.
Botany (TNAU groundnut; seed germination basics): seeds need moisture, a suitable temperature and oxygen to germinate;
the radicle (root) emerges first, then the hypocotyl pushes the shoot up; groundnut cotyledons come up to about the
soil surface; leaves have four leaflets.
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
SOIL = 900
SX, SY = 540, 1180                      # where the seed rests


def bg(night=0.0):
    sky = base64.b64encode(sky_png()).decode()
    rng = np.random.default_rng(3)
    g = [f'<defs><clipPath id="soil"><rect x="0" y="{SOIL}" width="{W}" height="{H - SOIL}"/></clipPath>'
         f'<radialGradient id="wetg"><stop offset="0" stop-color="#3a1404" stop-opacity="1"/><stop offset="0.65" stop-color="#3a1404" stop-opacity="0.8"/>'
         f'<stop offset="1" stop-color="#3a1404" stop-opacity="0"/></radialGradient></defs>'
         f'<image href="data:image/png;base64,{sky}" x="0" y="{SOIL + 40 - 1220}" width="{W}" height="1220" preserveAspectRatio="none"/>']
    if night > 0:
        g.append(f'<rect width="{W}" height="{SOIL}" fill="#0b1430" fill-opacity="{0.8 * night:.2f}"/>')
    g.append(f'<rect x="0" y="{SOIL}" width="{W}" height="{H - SOIL}" fill="#a34b22"/>'
             f'<rect x="0" y="{SOIL}" width="{W}" height="26" fill="#c9622f"/>')
    for _ in range(170):                                  # soil grains
        x, y = rng.uniform(0, W), rng.uniform(SOIL + 30, H)
        r = rng.uniform(10, 26)
        g.append(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{r:.0f}" ry="{r * 0.75:.0f}" fill="{rng.choice(["#b8582a", "#8f3f1c", "#c4683a"])}" '
                 f'stroke="{OUT}" stroke-width="1.5" stroke-opacity="0.35"/>')
    return "".join(g)


def air(rng, n, alpha):
    """Small air pockets between the grains."""
    return "".join(f'<ellipse cx="{rng.uniform(80, W - 80):.0f}" cy="{rng.uniform(SOIL + 60, H - 80):.0f}" rx="{rng.uniform(7, 14):.0f}" '
                   f'ry="{rng.uniform(5, 9):.0f}" fill="#ffffff" fill-opacity="{alpha:.2f}"/>' for _ in range(n))


def kernel(x, y, s=1.3, ang=-20, swell=0.0):
    """A groundnut kernel: pink-red skin, the pale germ tip at one end."""
    k = 1 + 0.18 * swell
    return (f'<g transform="translate({x} {y}) rotate({ang}) scale({s * k:.3f})">'
            f'<ellipse cx="0" cy="0" rx="62" ry="40" fill="#c8566a" stroke="{OUT}" stroke-width="5"/>'
            f'<path d="M -40,-14 Q 0,-30 40,-16" stroke="#e48a9a" stroke-width="7" fill="none" stroke-linecap="round"/>'
            f'<ellipse cx="54" cy="4" rx="11" ry="8" fill="#f2d4b0" stroke="{OUT}" stroke-width="3"/></g>')


def scene_seed(t, cfg):
    sky = base64.b64encode(sky_png()).decode()
    bob = math.sin(t * 1.6) * 8
    return (f'<image href="data:image/png;base64,{sky}" x="-300" y="-200" width="{W + 600}" height="{H + 400}" preserveAspectRatio="none"/>'
            f'<rect width="{W}" height="{H}" fill="#ffffff" fill-opacity="0.12"/>'
            f'<path d="M -60,{1700 + bob} Q 300,{1300 + bob} 520,{1060 + bob} Q 600,{990 + bob} 650,{1050 + bob} Q 560,{1180 + bob} 380,{1420 + bob} L 200,{1960} Z" '
            f'fill="#e4894a" stroke="#a95a28" stroke-width="8"/>'
            f'<path d="M 1140,{1500 + bob} Q 820,{1250 + bob} 640,{1150 + bob} Q 590,{1120 + bob} 560,{1170 + bob} Q 650,{1260 + bob} 820,{1460 + bob} L 1140,{1800} Z" '
            f'fill="#e4894a" stroke="#a95a28" stroke-width="8"/>'
            f'<ellipse cx="610" cy="{1040 + bob}" rx="36" ry="24" fill="#f4c7a6" stroke="#a95a28" stroke-width="4"/>'
            + kernel(560, 1000 + bob, 2.2, -28))


def scene_sow(t, cfg):
    span = cfg.get("span", [0, cfg["duration"]])
    p = (t - span[0]) / (span[1] - span[0])
    rng = np.random.default_rng(9)
    hole = ease(p / 0.18) * (1 - ease((p - 0.42) / 0.12))         # hole opens, then closes
    g = [bg()]
    if hole > 0:
        g.append(f'<path d="M {SX - 70 * hole:.0f},{SOIL} Q {SX},{SOIL + 300 * hole:.0f} {SX + 70 * hole:.0f},{SOIL} Z" fill="#5e260d"/>')
    if p < 0.3:                                                    # the finger pokes the hole
        d = ease(p / 0.15) - ease((p - 0.18) / 0.1)
        tip = SOIL - 360 + 520 * d
        g.append(f'<path d="M {SX - 70},{tip - 900} L {SX - 60},{tip - 60} Q {SX},{tip + 22} {SX + 60},{tip - 60} L {SX + 70},{tip - 900} Z" '
                 f'fill="#e4894a" stroke="#a95a28" stroke-width="7"/>'
                 f'<path d="M {SX - 32},{tip - 64} Q {SX},{tip - 44} {SX + 32},{tip - 64} L {SX + 28},{tip - 130} Q {SX},{tip - 116} {SX - 28},{tip - 130} Z" '
                 f'fill="#f4c7a6" stroke="#a95a28" stroke-width="4"/>')
    drop = ease((p - 0.26) / 0.14)                                  # the kernel drops into the hole
    if p > 0.24:
        ky = SOIL - 260 + (SY - (SOIL - 260)) * drop
        g.append(kernel(SX, ky, 1.3, -20 + 30 * drop))
    wet = ease((p - 0.58) / 0.25)                                  # water soaks in: darker soil, a wet front
    if p > 0.54:
        for k in range(6):                                         # drops falling
            u = (p - 0.54 - k * 0.03) / 0.12
            if 0 < u < 1:
                g.append(f'<ellipse cx="{SX - 150 + k * 60}" cy="{120 + (SOIL - 120) * u:.0f}" rx="16" ry="24" fill="#9fd0ec" stroke="#5a8fb0" stroke-width="3"/>')
        g.append(f'<g clip-path="url(#soil)"><ellipse cx="{SX}" cy="{SOIL}" rx="{520 * wet:.0f}" ry="{480 * wet:.0f}" fill="url(#wetg)" '
                 f'fill-opacity="{0.5 * wet:.2f}"/></g>')
    warm = ease((p - 0.72) / 0.15)
    if warm > 0:                                                   # warmth: a soft sun glow on the soil
        g.append(f'<circle cx="900" cy="230" r="{110 + 8 * math.sin(t * 2)}" fill="#ffd34d" fill-opacity="{0.9 * warm:.2f}"/>'
                 f'<g clip-path="url(#soil)"><ellipse cx="{SX}" cy="{SY}" rx="380" ry="260" fill="#ffb347" fill-opacity="{0.2 * warm:.2f}"/></g>')
    airp = ease((p - 0.82) / 0.12)
    if airp > 0:
        g.append(air(rng, 40, 0.85 * airp))
    return "".join(g)


def root(u):
    """Radicle + side roots growing down from the seed (u 0..1)."""
    if u <= 0:
        return ""
    L = 520 * u
    pts = [(SX + 40 + 14 * math.sin(k / 3), SY + 30 + L * k / 12) for k in range(13)]
    d = "M " + " L ".join(f"{x:.0f},{y:.0f}" for x, y in pts)
    g = (f'<path d="{d}" stroke="{OUT}" stroke-width="20" fill="none" stroke-linecap="round"/>'
         f'<path d="{d}" stroke="#f3ead2" stroke-width="13" fill="none" stroke-linecap="round"/>')
    for k, (fy, side, ln) in enumerate(((0.3, -1, 130), (0.42, 1, 150), (0.56, -1, 120), (0.7, 1, 110), (0.82, -1, 80))):
        v = ease((u - fy) / 0.3)
        if v > 0:
            x0, y0 = pts[int(fy * 12)]
            x1, y1 = x0 + side * ln * v, y0 + 70 * v
            g += (f'<path d="M {x0:.0f},{y0:.0f} Q {x0 + side * ln * v * 0.6:.0f},{y0 + 10:.0f} {x1:.0f},{y1:.0f}" stroke="{OUT}" '
                  f'stroke-width="10" fill="none" stroke-linecap="round"/><path d="M {x0:.0f},{y0:.0f} Q {x0 + side * ln * v * 0.6:.0f},'
                  f'{y0 + 10:.0f} {x1:.0f},{y1:.0f}" stroke="#f3ead2" stroke-width="5" fill="none" stroke-linecap="round"/>')
    return g


def shoot(u):
    """Hook pushing up through the soil, breaking the surface, straightening, first leaf opening."""
    if u <= 0:
        return ""
    top_y = SY - 40 - (SY - 40 - (SOIL - 150)) * ease(u / 0.6)
    bend = 90 * (1 - ease((u - 0.45) / 0.25))
    d = f"M {SX - 10},{SY - 30} Q {SX - 10 + bend},{(SY + top_y) / 2:.0f} {SX + bend * 0.4:.0f},{top_y:.0f}"
    g = (f'<path d="{d}" fill="none" stroke="{OUT}" stroke-width="30" stroke-linecap="round"/>'
         f'<path d="{d}" fill="none" stroke="#86bf4a" stroke-width="20" stroke-linecap="round"/>')
    if top_y < SOIL:                                              # crumbs pushed aside where it breaks through
        g += (f'<ellipse cx="{SX - 50}" cy="{SOIL - 6}" rx="26" ry="12" fill="#c9622f" stroke="{OUT}" stroke-width="2"/>'
              f'<ellipse cx="{SX + 60}" cy="{SOIL - 4}" rx="22" ry="10" fill="#c9622f" stroke="{OUT}" stroke-width="2"/>')
    op = ease((u - 0.65) / 0.3)
    tx, ty = SX + bend * 0.4, top_y
    if op > 0:
        g += f'<g transform="translate({tx:.0f} {ty:.0f}) scale({0.3 + 0.7 * op:.3f}) translate({-tx:.0f} {-ty:.0f})">{leaf(tx, ty, -55, 2.0)}</g>'
        op2 = ease((u - 0.85) / 0.15)
        if op2 > 0:
            g += f'<g transform="translate({tx:.0f} {ty:.0f}) scale({0.3 + 0.7 * op2:.3f}) translate({-tx:.0f} {-ty:.0f})">{leaf(tx, ty, -125, 1.8)}</g>'
    else:
        g += f'<ellipse cx="{tx:.0f}" cy="{ty:.0f}" rx="18" ry="28" fill="#5fa83a" stroke="{OUT}" stroke-width="3"/>'
    return g


def scene_grow(t, cfg):
    span = cfg.get("span", [0, cfg["duration"]])
    p = (t - span[0]) / (span[1] - span[0])
    days = cfg.get("days", 6)
    night = max(0.0, -math.cos(2 * math.pi * p * days)) ** 2       # day/night flicker = time passing
    rng = np.random.default_rng(9)
    g = [bg(night), f'<g clip-path="url(#soil)"><ellipse cx="{SX}" cy="{SOIL}" rx="520" ry="480" fill="url(#wetg)" fill-opacity="0.45"/></g>',
         air(rng, 40, 0.6)]
    swell = ease(p / 0.15)
    g.append(root(ease((p - 0.1) / 0.5)))
    g.append(kernel(SX, SY, 1.3, 10, swell))
    g.append(shoot(ease((p - 0.35) / 0.65)))
    return "".join(g)


SCENES = {"seed": scene_seed, "sow": scene_sow, "grow": scene_grow}


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
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" '
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
