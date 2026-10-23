"""Ants (erumbu) – a live ant-trail overlay for talk.py shots, plus the Ep 7 cut-aways. 1080x1920.

Usage:
    python tools/toon/ants.py OUT.mp4 TIMING.json          # a cut-away
In talk.py, a shot option "ants": {"path": [[x, y], ...], "n": 14, "size": 1.0, "speed": 60} (720x1280 coords)
draws ants walking along the path on top of the frame (draw_cv), half of them carrying a crumb back.

TIMING.json: {"mode": "trail" | "scout" | "team", "duration": 3, "fps": 25, "span": [t0, t1], "camera": [[t, cy, h], ...]}
trail: close-up of the ground: a neat line of ants, the ones coming back carry crumbs.
scout: one ant finds a crumb and walks home to the nest, leaving a faint scent trail (drawn as soft purple dots – the
       pheromone itself is invisible); others come out and follow it; the trail grows stronger as more ants use it.
team:  several ants carry one big crumb together.
Science (Hölldobler & Wilson, "The Ants", Harvard 1990; Sumpter & Beekman, Anim. Behav. 2003): a forager that finds food
lays a trail pheromone on its way back to the nest; nestmates follow it with their antennae and, if they find food,
reinforce it; trails that are not reinforced fade as the chemical evaporates.
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import cairosvg
import numpy as np

W, H = 1080, 1920
ANT = "#2a1a14"


def ease(u):
    u = min(max(u, 0), 1)
    return u * u * (3 - 2 * u)


def path_point(path, u):
    """Point and heading at fraction u (0..1) along a polyline."""
    pts = np.array(path, float)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    L = seg.sum()
    d = (u % 1) * L if u < 1 else L                            # u = 1 is the end, not the start again
    i = int(np.searchsorted(np.cumsum(seg), d))
    i = min(i, len(seg) - 1)
    d0 = np.cumsum(seg)[i] - seg[i]
    f = (d - d0) / max(seg[i], 1e-6)
    p = pts[i] + (pts[i + 1] - pts[i]) * f
    a = math.degrees(math.atan2(pts[i + 1][1] - pts[i][1], pts[i + 1][0] - pts[i][0]))
    return p, a, L


def ant_svg(x, y, ang, s, t, crumb=False):
    """Side-on/top-down cartoon ant: abdomen, thorax, head, 6 legs moving, two antennae; optional crumb in the jaws."""
    leg = math.sin(t * 18) * 25
    legs = "".join(f'<line x1="{dx * s:.1f}" y1="0" x2="{(dx + math.cos(math.radians(side * (60 + sgn * leg))) * 9) * s:.1f}" '
                   f'y2="{side * math.sin(math.radians(60 + sgn * leg)) * 9 * s:.1f}" stroke="{ANT}" stroke-width="{1.4 * s:.1f}" '
                   f'stroke-linecap="round"/>'
                   for dx, sgn in ((-2, 1), (0, -1), (2, 1)) for side in (-1, 1))
    c = (f'<circle cx="{13.5 * s:.1f}" cy="0" r="{3.6 * s:.1f}" fill="#f3e2b8" stroke="#8a6a3a" stroke-width="{0.8 * s:.1f}"/>'
         if crumb else "")
    return (f'<g transform="translate({x:.1f} {y:.1f}) rotate({ang:.1f})">{legs}'
            f'<ellipse cx="{-7 * s:.1f}" cy="0" rx="{5.5 * s:.1f}" ry="{4 * s:.1f}" fill="{ANT}"/>'
            f'<ellipse cx="0" cy="0" rx="{3.2 * s:.1f}" ry="{2.2 * s:.1f}" fill="{ANT}"/>'
            f'<circle cx="{6 * s:.1f}" cy="0" r="{3 * s:.1f}" fill="{ANT}"/>'
            f'<path d="M {8 * s:.1f},-1 q {4 * s:.1f},{-5 * s:.1f} {7 * s:.1f},{-5 * s:.1f} M {8 * s:.1f},1 q {4 * s:.1f},{5 * s:.1f} '
            f'{7 * s:.1f},{5 * s:.1f}" stroke="{ANT}" stroke-width="{0.9 * s:.1f}" fill="none"/>{c}</g>')


def draw_cv(img, t, prm, K=1.5):
    """Draw walking ants on a BGR frame (talk.py overlay). Coordinates in 720x1280 units, scaled by K."""
    import cv2
    path = np.array(prm["path"], float) * K
    n, s, speed = prm.get("n", 14), prm.get("size", 1.0) * K, prm.get("speed", 60) * K
    _, _, L = path_point(path, 0)
    for k in range(n):
        back = k % 2 == 1                                     # every other ant walks back with a crumb
        u = (t * speed / L + k / n) % 1
        u = 1 - u if back else u
        p, a, _ = path_point(path, u)
        if back:
            a += 180
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        to = lambda dx, dy: (int(p[0] + (dx * ca - dy * sa) * s), int(p[1] + (dx * sa + dy * ca) * s))  # noqa: E731
        leg = math.sin(t * 18 + k) * 0.45
        for dx, sg in ((-2, 1), (0, -1), (2, 1)):
            for side in (-1, 1):
                ex = dx + math.cos(side * (1.05 + sg * leg)) * 8
                ey = side * abs(math.sin(1.05 + sg * leg)) * 8
                cv2.line(img, to(dx, 0), to(ex, ey), (20, 26, 42), max(1, int(1.3 * s)), cv2.LINE_AA)
        for cx, rx, ry in ((-7, 5.5, 4), (0, 3.2, 2.2), (6, 3, 3)):
            c = to(cx, 0)
            cv2.ellipse(img, c, (max(1, int(rx * s)), max(1, int(ry * s))), a, 0, 360, (20, 26, 42), -1, cv2.LINE_AA)
        if back:
            cv2.circle(img, to(13, 0), max(2, int(3.4 * s)), (184, 226, 243), -1, cv2.LINE_AA)
            cv2.circle(img, to(13, 0), max(2, int(3.4 * s)), (58, 106, 138), 1, cv2.LINE_AA)


# ---------------------------------------------------------------- cut-aways

def ground():
    rng = np.random.default_rng(2)
    g = [f'<rect width="{W}" height="{H}" fill="#c98a56"/>']
    for _ in range(140):
        g.append(f'<circle cx="{rng.uniform(0, W):.0f}" cy="{rng.uniform(0, H):.0f}" r="{rng.uniform(3, 12):.0f}" '
                 f'fill="{rng.choice(["#b07443", "#d9a06a", "#a8683a"])}" fill-opacity="0.7"/>')
    return "".join(g)


def scene(t, cfg):
    mode, span = cfg["mode"], cfg["span"]
    p = ease((t - span[0]) / (span[1] - span[0]))
    g = [ground()]
    if mode == "trail":
        path = [(-80, 1500), (300, 1300), (600, 1150), (850, 900), (1160, 700)]
        for k in range(8):
            back = k % 2 == 1
            u = (t * 0.06 + k / 8 + (0.04 if back else 0)) % 1
            pnt, a, _ = path_point(path, 1 - u if back else u)
            off = 40 if back else -40                          # two lanes: out and back
            g.append(ant_svg(pnt[0] + off * math.sin(math.radians(a)), pnt[1] - off * math.cos(math.radians(a)),
                             a + (180 if back else 0), 7.0, t + k, crumb=back))
    elif mode == "scout":
        nest, food = (200, 1500), (850, 650)
        g.append(f'<ellipse cx="{nest[0]}" cy="{nest[1]}" rx="70" ry="38" fill="#3a2214"/>'
                 f'<ellipse cx="{nest[0]}" cy="{nest[1] - 8}" rx="95" ry="50" fill="none" stroke="#a8683a" stroke-width="16"/>')
        g.append(f'<circle cx="{food[0]}" cy="{food[1]}" r="42" fill="#f3e2b8" stroke="#8a6a3a" stroke-width="5"/>'
                 f'<circle cx="{food[0] + 50}" cy="{food[1] + 20}" r="22" fill="#f3e2b8" stroke="#8a6a3a" stroke-width="4"/>')
        path = [nest, (330, 1250), (520, 1080), (700, 860), food]
        home = ease((p - 0.05) / 0.35)                         # the scout walks home, laying the trail
        strength = 0.35 + 0.65 * ease((p - 0.45) / 0.55)       # more ants -> stronger trail
        for k in range(40):
            u = k / 39
            if 1 - u <= home:
                pt, _, _ = path_point(path, u)
                g.append(f'<circle cx="{pt[0]:.0f}" cy="{pt[1]:.0f}" r="{9 + 7 * strength:.0f}" fill="#9b59b6" '
                         f'fill-opacity="{0.15 + 0.4 * strength:.2f}"/>')
        if home < 1:
            pt, a, _ = path_point(path, 1 - home)
            g.append(ant_svg(pt[0], pt[1], a + 180, 4.5, t, crumb=True))
        followers = int(ease((p - 0.4) / 0.6) * 8)
        for k in range(followers):
            u = (t * 0.12 + k / 8) % 1
            pt, a, _ = path_point(path, u)
            g.append(ant_svg(pt[0], pt[1], a, 4.2, t + k))
    else:  # team
        x = 700 - 380 * p
        g.append(f'<ellipse cx="{x:.0f}" cy="960" rx="120" ry="80" fill="#f3e2b8" stroke="#8a6a3a" stroke-width="6"/>')
        for k, (dx, dy, a) in enumerate([(-110, 60, 180), (-60, 95, 160), (20, 100, 200), (95, 70, 170), (115, -10, 180),
                                         (-120, -20, 190), (40, -95, 175)]):
            g.append(ant_svg(x + dx, 960 + dy, a, 4.0, t + k * 0.3))
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
