"""Coriander (kothamalli) – a bunch that can be fresh or wilted, and the Ep 2 cut-aways. 1080x1920.

Usage:
    python tools/toon/coriander.py OUT.mp4 TIMING.json      # a cut-away
    python tools/toon/coriander.py OUT.png --bunch WILT     # one bunch on transparent (WILT 0 fresh .. 1 wilted)

TIMING.json: {"mode": "compare" | "water" | "sun" | "box" | "sprinkle" | "macro", "duration": 4, "fps": 25,
              "span": [t0, t1], "camera": [[t, cy, h], ...]}
compare:  a fresh, crisp bunch next to a limp wilted one (close-up).
water:    one leaf on a cut stem: water vapour leaves through the leaf (transpiration, from the tiny pores on the
          leaf); no roots any more to replace it, so the stem softens and the leaf droops.
sun:      on the kitchen shelf, a bunch in a hot patch of sun wilts fast while the one in the shade stays fresh.
box:      a bunch goes into a steel box and the lid closes (kept covered and cool it loses water more slowly).
sprinkle: chopped leaves fall onto a pot of sambar, steam rising.
macro:    a close-up of fresh leaves swaying gently.
Science (TNAU Agritech post-harvest, Kader "Postharvest technology of horticultural crops"): harvested leafy herbs keep
losing water by transpiration but no longer get water from the roots; heat, sun, dry air and air movement speed it up;
cool, humid, covered storage slows it. Losing ~5 % of their water makes leaves visibly limp.
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import cairosvg
import numpy as np

W, H = 1080, 1920
OUT = "#22401a"


def mix(c1, c2, u):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    u = min(max(u, 0), 1)
    return "#" + "".join(f"{round(x + (y - x) * u):02x}" for x, y in zip(a, b))


def leaflet(x, y, ang, s, wilt, rng):
    """A coriander leaflet: a fan of three wedge-shaped lobes with scalloped (rounded-tooth) edges."""
    fill = mix("#56b23a", "#97994a", wilt)
    if wilt > 0.5 and rng.random() < 0.45:
        fill = mix(fill, "#b8a740", (wilt - 0.6) * 1.6)
    vein = mix(fill, "#1f4d17", 0.45)
    curl = 1 - 0.4 * wilt                      # the fan closes and droops as it wilts
    out = ""
    for k, da in enumerate((-48 * curl, 0, 48 * curl)):
        r = s * (18 if k == 1 else 15) * (1 - 0.1 * wilt)
        a0 = math.radians(ang + da + wilt * 30)
        half = math.radians(24 * curl + 6)
        pts = [f"{x:.1f},{y:.1f}"]
        for j in range(13):                     # outer edge: three rounded teeth
            t = a0 - half + 2 * half * j / 12
            rr = r * (0.82 + 0.18 * abs(math.cos(j / 12 * 3 * math.pi)))
            pts.append(f"{x + rr * math.cos(t):.1f},{y + rr * math.sin(t):.1f}")
        out += f'<polygon points="{" ".join(pts)}" fill="{fill}" stroke="{OUT}" stroke-width="{1.4 * s:.1f}" stroke-linejoin="round"/>'
        out += (f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + r * 0.8 * math.cos(a0):.1f}" y2="{y + r * 0.8 * math.sin(a0):.1f}" '
                f'stroke="{vein}" stroke-width="{1.1 * s:.1f}"/>')
    return out


def bunch_svg(x, y, wilt=0.0, s=1.0, seed=1, n=13, height=230, sway=0.0):
    """Bunch whose stems meet at (x, y) (where the hand holds it), fanning upwards. wilt 0..1 bends them down."""
    rng = np.random.default_rng(seed)
    stems, leaves = [], []
    stem_col = mix("#7fb83e", "#9aa457", wilt)
    for i in range(n):
        base_a = -90 + (i / (n - 1) - 0.5) * 50 + rng.uniform(-4, 4) + sway * 3
        L = height * s * rng.uniform(0.75, 1.0)
        bend = rng.uniform(0.7, 1.0) * wilt * (1 if base_a > -90 else -1) * 150   # soft stems hang to the outside
        pts, px, py, a = [], x, y + 40 * s, base_a
        steps = 14
        for j in range(steps + 1):
            pts.append((px, py))
            u = j / steps
            a = base_a + bend * max(0.0, u - 0.25) ** 1.3 / 0.75 ** 1.3
            px += math.cos(math.radians(a)) * L / steps
            py += math.sin(math.radians(a)) * L / steps
        d = "M " + " L ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in pts)
        stems.append(f'<path d="{d}" stroke="{OUT}" stroke-width="{5.2 * s:.1f}" fill="none" stroke-linecap="round"/>'
                     f'<path d="{d}" stroke="{stem_col}" stroke-width="{2.8 * s:.1f}" fill="none" stroke-linecap="round"/>')
        # leaflets along the top half and at the tip
        for j in range(steps // 3, steps, 2):
            px2, py2 = pts[j]
            side = 1 if (j // 2) % 2 else -1
            la = a + side * 50 + rng.uniform(-15, 15) + wilt * 40 * side
            leaves.append(leaflet(px2, py2, la, s * rng.uniform(0.85, 1.15) * (1 - 0.15 * wilt), wilt, rng))
        leaves.append(leaflet(pts[-1][0], pts[-1][1], a, s * 1.15 * (1 - 0.15 * wilt), wilt, rng))
    # cut stem ends below the hand
    ends = "".join(f'<circle cx="{x + (k - 3) * 3.2 * s:.1f}" cy="{y + 42 * s:.1f}" r="{1.8 * s:.1f}" fill="#c9df8a"/>' for k in range(7))
    return "".join(stems) + "".join(leaves) + ends


def bunch_png(path, wilt, size=(600, 620), seed=1, s=1.6):
    w, h = size
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">'
           f'{bunch_svg(w / 2, h - 110, wilt, s, seed)}</svg>')
    Path(path).write_bytes(cairosvg.svg2png(bytestring=svg.encode()))


# ---------------------------------------------------------------- cut-aways

def ease(u):
    u = min(max(u, 0), 1)
    return u * u * (3 - 2 * u)


def kitchen_bg(warm=0.0):
    return (f'<rect width="{W}" height="{H}" fill="{mix("#e9c9a0", "#f3d9a6", warm)}"/>'
            f'<rect y="1250" width="{W}" height="{H - 1250}" fill="#9a6235"/>'
            f'<rect y="1250" width="{W}" height="36" fill="#7d4c28"/>')


def scene(t, cfg):
    mode, p = cfg["mode"], ease((t - cfg["span"][0]) / (cfg["span"][1] - cfg["span"][0]))
    g = []
    if mode == "compare":
        g.append(kitchen_bg())
        g.append('<ellipse cx="325" cy="1300" rx="150" ry="24" fill="#3b2416" fill-opacity="0.25"/>')
        g.append('<ellipse cx="705" cy="1300" rx="150" ry="24" fill="#3b2416" fill-opacity="0.25"/>')
        sw = math.sin(t * 2.2) * 0.6
        g.append(f'<g transform="rotate({sw:.2f} 325 1240)">{bunch_svg(325, 1190, 0.0, 1.6, 3, sway=sw)}</g>')
        g.append(bunch_svg(705, 1190, 0.15 + 0.85 * p, 1.6, 4))
    elif mode == "water":
        g.append('<rect width="1080" height="1920" fill="#c99a6b"/>')
        g.append('<rect y="1560" width="1080" height="360" fill="#8a5330"/>')
        droop = ease((p - 0.3) / 0.7)
        # one big leaf on a cut stem; the stem softens and bends, the leaf turns down and dulls
        pts, x, y, ang = [], 430.0, 1560.0, -90.0
        for j in range(21):
            pts.append((x, y))
            ang = -90 + droop * 120 * (j / 20) ** 1.5
            x += math.cos(math.radians(ang)) * 24
            y += math.sin(math.radians(ang)) * 24
        d = "M " + " L ".join(f"{q[0]:.1f},{q[1]:.1f}" for q in pts)
        g.append(f'<path d="{d}" stroke="{OUT}" stroke-width="24" fill="none" stroke-linecap="round"/>'
                 f'<path d="{d}" stroke="{mix("#7fb83e", "#9aa457", droop)}" stroke-width="14" fill="none" stroke-linecap="round"/>')
        rng = np.random.default_rng(3)
        g.append(leaflet(pts[-1][0], pts[-1][1], ang, 11, 0.15 + 0.85 * droop, rng))
        lx, ly = pts[-1]
        for k in range(18):                       # water vapour leaving the leaf (invisible in life; drawn as wisps)
            ph = (t * 0.5 + k / 18) % 1
            amt = 1 - 0.7 * droop
            x0 = lx + ((k * 47) % 260) - 130 + 25 * math.sin(t * 2 + k)
            y0 = ly - 40 - ph * 520
            g.append(f'<path d="M {x0:.0f},{y0:.0f} q 18,-26 0,-52 q -18,-26 0,-52" stroke="#ffffff" stroke-width="9" fill="none" '
                     f'stroke-linecap="round" stroke-opacity="{0.95 * (1 - ph) * min(1, ph * 4) * amt:.2f}"/>')
        g.append('<ellipse cx="430" cy="1562" rx="20" ry="9" fill="#c9df8a" stroke="#22401a" stroke-width="4"/>')
    elif mode == "sun":
        g.append(kitchen_bg())
        g.append('<polygon points="120,0 500,0 580,1290 170,1290" fill="#fff3b0" fill-opacity="0.55"/>')   # sunbeam
        for k in range(10):
            ph = (t * 0.6 + k / 10) % 1
            g.append(f'<path d="M {150 + k * 38},{1180 - ph * 300:.0f} q 12,-20 0,-40" stroke="#ffb347" stroke-width="4" '
                     f'fill="none" stroke-opacity="{0.5 * (1 - ph):.2f}"/>')
        g.append('<ellipse cx="360" cy="1300" rx="150" ry="24" fill="#3b2416" fill-opacity="0.25"/>')
        g.append('<ellipse cx="740" cy="1300" rx="150" ry="24" fill="#3b2416" fill-opacity="0.35"/>')
        g.append(bunch_svg(360, 1200, 0.95 * p, 1.5, 5))
        g.append(bunch_svg(740, 1200, 0.08 * p, 1.5, 6))
    elif mode == "box":
        g.append(kitchen_bg())
        lid = ease((p - 0.55) / 0.45)
        g.append('<ellipse cx="540" cy="1330" rx="300" ry="40" fill="#3b2416" fill-opacity="0.3"/>')
        g.append('<rect x="260" y="1060" width="560" height="270" rx="26" fill="#c7ccd1" stroke="#3b3f44" stroke-width="8"/>')
        drop = ease(min(1, p / 0.5))
        bx, by = 540 + 220 * drop, 860 + 290 * drop      # lowered in, laid on its side
        clip = ('<clipPath id="bx"><rect x="264" y="0" width="552" height="1326"/></clipPath>' if drop > 0.6 else
                '<clipPath id="bx"><rect x="0" y="0" width="1080" height="1920"/></clipPath>')
        g.append(clip + f'<g clip-path="url(#bx)"><g transform="translate({bx - 540:.0f} {by - 900:.0f}) rotate({-90 * drop:.1f} 540 940)">'
                 f'{bunch_svg(540, 900, 0.0, 1.3, 8, n=10)}</g></g>')
        g.append('<rect x="260" y="1150" width="560" height="180" rx="22" fill="#c7ccd1" stroke="#3b3f44" stroke-width="8"/>'
                 '<line x1="290" y1="1200" x2="790" y2="1200" stroke="#e8ebee" stroke-width="10"/>')
        ly = 700 + 380 * lid
        g.append(f'<g opacity="{min(1, lid * 3):.2f}"><rect x="240" y="{ly:.0f}" width="600" height="46" rx="20" fill="#d5d9dd" '
                 f'stroke="#3b3f44" stroke-width="8"/><rect x="500" y="{ly - 24:.0f}" width="80" height="30" rx="12" '
                 f'fill="#aeb4ba" stroke="#3b3f44" stroke-width="6"/></g>')
    elif mode == "sprinkle":
        g.append(kitchen_bg(0.3))
        g.append('<ellipse cx="540" cy="1390" rx="330" ry="44" fill="#3b2416" fill-opacity="0.3"/>')
        g.append('<path d="M 230,1150 Q 240,1380 540,1390 Q 840,1380 850,1150 Z" fill="#2b2b2b" stroke="#111" stroke-width="8"/>')
        g.append('<ellipse cx="540" cy="1150" rx="310" ry="70" fill="#c8661f" stroke="#111" stroke-width="8"/>')
        g.append('<ellipse cx="540" cy="1150" rx="270" ry="52" fill="#d9822b"/>')
        rng = np.random.default_rng(2)
        for k in range(40):
            t0 = 0.2 + k * 0.05
            u = (t - t0) / 0.9
            x0 = 420 + rng.uniform(0, 240)
            xe = 330 + rng.uniform(0, 420)
            ye = 1130 + rng.uniform(-30, 40)
            if u <= 0:
                continue
            uu = min(u, 1)
            x = x0 + (xe - x0) * uu + 14 * math.sin(t * 5 + k) * (1 - uu)
            y = 600 + (ye - 600) * uu ** 1.6
            g.append(leaflet(x, y, rng.uniform(0, 360), 1.6, 0.0, rng))
        for k in range(6):
            ph = (t * 0.35 + k / 6) % 1
            x = 380 + k * 65
            g.append(f'<path d="M {x},{1100 - ph * 380:.0f} q 30,-50 0,-100 q -30,-50 0,-100" stroke="#ffffff" stroke-width="10" '
                     f'fill="none" stroke-linecap="round" stroke-opacity="{0.45 * (1 - ph):.2f}"/>')
    else:  # macro
        g.append('<rect width="1080" height="1920" fill="#f2e2c4"/>')
        for k, (x, sd) in enumerate([(250, 20), (820, 21), (540, 22)]):
            sw = math.sin(t * 1.6 + k) * 1.4
            g.append(f'<g transform="rotate({sw:.2f} {x} 1900)">{bunch_svg(x, 1760, 0.0, 3.2, sd, n=14, height=300)}</g>')
    return "".join(g)


def main():
    out = sys.argv[1]
    if sys.argv[2] == "--bunch":
        bunch_png(out, float(sys.argv[3]))
        return
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
