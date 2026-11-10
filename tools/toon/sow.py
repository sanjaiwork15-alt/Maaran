"""Sowing cut-aways (One-Acre Challenge Ep 7 – Thatha's last chance). 1080x1920, no words.

python tools/toon/sow.py OUT.mp4 TIMING.json   ("still": t renders one PNG)
    scatter:  cfg "bg" field plate: a handful of seeds flies in from the right in wide arcs and lands everywhere – some in
              the puddles (little splashes), some between the bent plants.
    soak:     close-up: seeds lying in a muddy puddle, sinking; one floats, bubbles (wasted).
    sow:      top-down on a small marked patch (pegs + string): holes appear at even spacing, a seed drops into each,
              the soil closes over, then a watering-can rose sprinkles it dark.
    sprout:   time-lapse on the patch (side view at soil level): sun and moon race across the sky, the soil cracks,
              tiny brinjal seedlings push up and open two round seed leaves, then a first true leaf.
    goat:     cfg "bg" field plate: a cheeky goat trots in from the right towards the seedlings, stops, chews, bleats.
"""
import io
import json
import math
import subprocess
import sys
from pathlib import Path

import cairosvg
import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bugs import leaf  # noqa: E402

W, H = 1080, 1920


def svg_rgba(body, w=W, h=H):
    png = cairosvg.svg2png(bytestring=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">{body}</svg>'.encode())
    return np.array(Image.open(io.BytesIO(png)).convert("RGBA")).astype(np.float32)


def over(rgb, rgba):
    a = rgba[..., 3:4] / 255
    return rgb * (1 - a) + rgba[..., :3] * a


def ease(u):
    u = min(max(u, 0), 1)
    return u * u * (3 - 2 * u)


def plate(base, cfg):
    return np.array(Image.open(base / cfg["bg"]).convert("RGB").resize((W, H), Image.LANCZOS)).astype(np.float32)


def seed(x, y, s=1.0, ang=0):
    return (f'<g transform="translate({x:.0f} {y:.0f}) rotate({ang:.0f}) scale({s:.3f})"><ellipse rx="10" ry="7" fill="#efe0b0" stroke="#8a7a40" stroke-width="2.5"/>'
            '<ellipse cx="-3" cy="-2" rx="3" ry="2" fill="#fffbe8"/></g>')


def scene_scatter(t, cfg, bg):
    rng = np.random.default_rng(3)
    g = ""
    for k in range(70):
        t0 = 0.1 + rng.uniform(0, 0.5)
        dur = rng.uniform(0.7, 1.1)
        tx, ty = rng.uniform(40, 1040), rng.uniform(1000, 1880)
        sx, sy = 1150, rng.uniform(700, 900)
        u = (t - t0) / dur
        s = 0.6 + 1.4 * (ty - 900) / 1000
        if u < 0:
            continue
        if u < 1:
            x = sx + (tx - sx) * u
            y = sy + (ty - sy) * u - 520 * math.sin(math.pi * u)
            g += seed(x, y, s * (1.2 - 0.2 * u), u * 700 + k * 30)
        else:
            g += seed(tx, ty, s, k * 30)
            d = t - t0 - dur
            if d < 0.35 and k % 4 == 0:                    # splash where it lands in water
                g += f'<ellipse cx="{tx:.0f}" cy="{ty:.0f}" rx="{8 + 50 * d:.0f}" ry="{3 + 15 * d:.0f}" fill="none" stroke="#e8f0ff" stroke-width="3" opacity="{1 - d / 0.35:.2f}"/>'
    return over(bg, svg_rgba(g))


def scene_soak(t, cfg):
    g = ['<rect width="1080" height="1920" fill="#4a2e1a"/>',
         '<ellipse cx="540" cy="1080" rx="620" ry="520" fill="#6e604c"/>',
         '<ellipse cx="540" cy="1080" rx="600" ry="500" fill="#8a7c66"/>',
         '<path d="M 0,700 Q 300,640 540,690 Q 780,740 1080,680" stroke="#b9c4cc" stroke-width="40" opacity="0.35" fill="none"/>']
    rng = np.random.default_rng(5)
    for k in range(9):
        x, y = rng.uniform(220, 860), rng.uniform(800, 1380)
        sink = ease((t - 0.2 - 0.15 * k) / 1.8) if k != 4 else 0
        bob = 6 * math.sin(t * 3 + k) if k == 4 else 0
        op = 1 - 0.65 * sink
        g.append(f'<g opacity="{op:.2f}">{seed(x, y + 30 * sink + bob, 3.2, k * 40)}</g>')
        if k != 4:
            u = (t * 0.9 + k * 0.13) % 1
            g.append(f'<circle cx="{x + 20:.0f}" cy="{y - 40 * u:.0f}" r="{6 + 6 * u:.0f}" fill="none" stroke="#d6e4ef" stroke-width="3" opacity="{(1 - u) * 0.8:.2f}"/>')
    for k in range(4):
        u = (t * 0.5 + k * 0.25) % 1
        g.append(f'<ellipse cx="540" cy="1080" rx="{80 + 420 * u:.0f}" ry="{40 + 260 * u:.0f}" fill="none" stroke="#c9d3da" stroke-width="3" opacity="{0.5 * (1 - u):.2f}"/>')
    return svg_rgba("".join(g))[..., :3]


HOLES = [(300 + 240 * (k % 3), 700 + 260 * (k // 3)) for k in range(12)]


def scene_sow(t, cfg):
    g = ['<rect width="1080" height="1920" fill="#7a4a2a"/>']
    rng = np.random.default_rng(1)
    for _ in range(260):
        g.append(f'<ellipse cx="{rng.uniform(0, 1080):.0f}" cy="{rng.uniform(0, 1920):.0f}" rx="{rng.uniform(6, 20):.0f}" ry="{rng.uniform(4, 10):.0f}" fill="{rng.choice(["#8a5a34", "#6b4226", "#94603a"])}"/>')
    for x, y in ((180, 560), (900, 560), (180, 1520), (900, 1520)):
        g.append(f'<circle cx="{x}" cy="{y}" r="22" fill="#8a5a2b" stroke="#3e2410" stroke-width="5"/><circle cx="{x}" cy="{y}" r="9" fill="#e53935"/>')
    g.append('<path d="M 180,560 L 900,560 L 900,1520 L 180,1520 Z" stroke="#f5f5f5" stroke-width="5" fill="none"/>')
    wet = ease((t - 4.2) / 0.8)
    if wet > 0:
        g.append(f'<rect x="185" y="565" width="710" height="950" fill="#3e2414" opacity="{0.45 * wet:.2f}"/>')
    for k, (x, y) in enumerate(HOLES):
        t0 = 0.3 + k * 0.28
        hole = ease((t - t0) / 0.15)
        drop = (t - t0 - 0.15) / 0.2
        close = ease((t - t0 - 0.5) / 0.25)
        if hole > 0 and close < 1:
            g.append(f'<ellipse cx="{x}" cy="{y}" rx="{50 * hole * (1 - close):.0f}" ry="{38 * hole * (1 - close):.0f}" fill="#2a1408"/>')
        if 0 < drop:
            yy = y - 300 * (1 - min(1, drop)) ** 2
            if close < 0.9:
                g.append(seed(x, yy, 3.4 * (1 + 0.6 * (1 - min(1, drop))), k * 25))
        if close > 0:
            g.append(f'<ellipse cx="{x}" cy="{y}" rx="40" ry="28" fill="#6b4226" opacity="{close:.2f}"/><circle cx="{x}" cy="{y}" r="6" fill="#4a2e18" opacity="{close:.2f}"/>')
    if 3.8 < t:                                          # the watering-can rose: a soft shower
        u = min(1, (t - 3.8) / 0.4)
        rr = np.random.default_rng(int(t * 25))
        g += [f'<line x1="{x:.0f}" y1="{y:.0f}" x2="{x - 6:.0f}" y2="{y + 40:.0f}" stroke="#d6eefe" stroke-width="5" opacity="{0.8 * u:.2f}" stroke-linecap="round"/>'
              for x, y in zip(rr.uniform(160, 920, 70), rr.uniform(450, 1600, 70))]
    return svg_rgba("".join(g))[..., :3]


def seedling(x, y, p, s=1.0):
    """p 0..1: the hook pushes up (0–0.4), the two seed leaves open (0.4–0.7), a first true leaf (0.7–1)."""
    if p <= 0:
        return ""
    h = 120 * min(1, p / 0.4)
    g = f'<g transform="translate({x:.0f} {y:.0f}) scale({s:.3f})">'
    if p < 0.4:
        g += f'<path d="M 0,0 Q 0,{-h:.0f} {14 * (1 - p / 0.4):.0f},{-h + 10:.0f}" stroke="#a8d080" stroke-width="10" fill="none" stroke-linecap="round"/>'
    else:
        o = ease((p - 0.4) / 0.3)
        g += f'<path d="M 0,0 L 0,-120" stroke="#7cb342" stroke-width="10" stroke-linecap="round"/>'
        g += (f'<ellipse cx="{-34 * o:.0f}" cy="{-124 - 8 * o:.0f}" rx="{14 + 22 * o:.0f}" ry="{10 + 6 * o:.0f}" fill="#8bc34a" stroke="#33691e" stroke-width="4" transform="rotate({-20 * o:.0f} {-34 * o:.0f} {-124 - 8 * o:.0f})"/>'
              f'<ellipse cx="{34 * o:.0f}" cy="{-124 - 8 * o:.0f}" rx="{14 + 22 * o:.0f}" ry="{10 + 6 * o:.0f}" fill="#8bc34a" stroke="#33691e" stroke-width="4" transform="rotate({20 * o:.0f} {34 * o:.0f} {-124 - 8 * o:.0f})"/>')
        tl = ease((p - 0.7) / 0.3)
        if tl > 0:
            g += leaf(0, -130, -90, 0.35 * tl, "#5aa83c")
    return g + "</g>"


def scene_sprout(t, cfg):
    dur = cfg.get("duration", 4.0)
    day = t / dur * 3.2                                   # ~3 days race past
    ph = day % 1
    sun = math.sin(math.pi * min(1, ph / 0.62)) if ph < 0.62 else 0
    sky = np.array([60, 70, 120]) + (np.array([150, 205, 245]) - np.array([60, 70, 120])) * sun
    g = [f'<rect width="1080" height="1920" fill="rgb({int(sky[0])},{int(sky[1])},{int(sky[2])})"/>']
    if ph < 0.62:
        a = math.pi * ph / 0.62
        g.append(f'<circle cx="{540 - 460 * math.cos(a):.0f}" cy="{1000 - 760 * math.sin(a):.0f}" r="70" fill="#ffd54f"/>')
    else:
        a = math.pi * (ph - 0.62) / 0.38
        g.append(f'<circle cx="{540 - 460 * math.cos(a):.0f}" cy="{1000 - 700 * math.sin(a):.0f}" r="50" fill="#eceff1"/>')
    g.append('<path d="M 0,1000 Q 300,940 540,980 Q 800,1020 1080,960 L 1080,1100 L 0,1100 Z" fill="#6a8f4a"/>')
    g.append('<rect y="1100" width="1080" height="820" fill="#6b4226"/>')
    rng = np.random.default_rng(4)
    for _ in range(80):
        g.append(f'<ellipse cx="{rng.uniform(0, 1080):.0f}" cy="{rng.uniform(1110, 1900):.0f}" rx="{rng.uniform(8, 22):.0f}" ry="{rng.uniform(4, 10):.0f}" fill="{rng.choice(["#8a5a34", "#5a361e"])}"/>')
    g.append('<path d="M 0,1100 L 1080,1100" stroke="#4a2e18" stroke-width="10"/>')
    for k, x in enumerate((180, 400, 620, 860)):
        p = (t / dur - 0.2 - 0.06 * k) / 0.7
        if 0 < p < 0.25:
            g.append(f'<path d="M {x - 30},1102 l 20,-6 l 14,8 l 22,-8" stroke="#3a2010" stroke-width="5" fill="none"/>')
        g.append(seedling(x, 1104, p, 1.7))
    shade = 0.55 + 0.45 * sun
    img = svg_rgba("".join(g))[..., :3]
    return img * (0.55 + 0.45 * shade)


def goat(x, y, s=1.0, t=0.0, walk=True, chew=False):
    """A cartoon goat facing left, (x, y) = between its front hooves on the ground."""
    st = 18 * math.sin(t * 12) if walk else 0
    jaw = 6 * abs(math.sin(t * 9)) if chew else 0
    legs = "".join(f'<path d="M {lx},-120 L {lx + (st if i % 2 else -st):.0f},0" stroke="#3e2723" stroke-width="18" stroke-linecap="round"/>'
                   f'<ellipse cx="{lx + (st if i % 2 else -st):.0f}" cy="2" rx="14" ry="8" fill="#212121"/>'
                   for i, lx in enumerate((-10, 30, 170, 200)))
    return (f'<g transform="translate({x:.0f} {y:.0f}) scale({s:.3f})">' + legs +
            '<ellipse cx="100" cy="-170" rx="140" ry="80" fill="#f5f0e6" stroke="#5d4037" stroke-width="7"/>'
            '<ellipse cx="140" cy="-190" rx="50" ry="36" fill="#8d6e63" opacity="0.8"/>'
            '<path d="M 236,-200 q 40,-30 30,-70" stroke="#f5f0e6" stroke-width="18" fill="none" stroke-linecap="round"/>'
            '<path d="M -10,-200 Q -40,-260 -60,-280" stroke="#f5f0e6" stroke-width="56" stroke-linecap="round"/>'
            f'<g transform="translate(-80 -300)"><ellipse cx="0" cy="0" rx="58" ry="42" fill="#f5f0e6" stroke="#5d4037" stroke-width="7"/>'
            '<path d="M -10,-38 Q 10,-90 50,-96 M 14,-36 Q 34,-80 66,-82" stroke="#a1887f" stroke-width="12" fill="none" stroke-linecap="round"/>'
            '<path d="M 30,-20 Q 80,-24 92,4 Q 70,6 30,-4 Z" fill="#d7ccc8" stroke="#5d4037" stroke-width="5"/>'
            '<circle cx="-18" cy="-8" r="10" fill="#fff"/><circle cx="-22" cy="-8" r="5" fill="#222"/><rect x="-27" y="-10" width="10" height="3" fill="#222"/>'
            '<ellipse cx="-56" cy="8" rx="6" ry="4" fill="#5d4037"/>'
            f'<path d="M -56,{22 + jaw:.0f} q -20,40 4,70 q 6,-30 10,-60" fill="#d7ccc8" stroke="#5d4037" stroke-width="4"/>'
            f'<path d="M -50,{20 + jaw:.0f} q 14,8 28,2" stroke="#5d4037" stroke-width="4" fill="none"/></g></g>')


class Goat:
    def __init__(self, cfg, base):
        self.cfg = cfg
        self.bg = plate(base, cfg)

    def frame(self, t):
        walk = ease(t / 1.6)
        x = 1250 - 600 * walk
        g = goat(x, 1560, 1.0, t, walk=walk < 0.99, chew=walk >= 0.99)
        if t > 2.1:                                         # a bleat: little sound arcs
            u = (t - 2.1) % 0.8 / 0.8
            g += "".join(f'<path d="M {660 - 40 * k - 60 * u:.0f},{1230 - 30 * k:.0f} q -20,20 0,40" stroke="#ffffff" stroke-width="7" fill="none" opacity="{1 - u:.2f}"/>' for k in range(3))
        return over(self.bg, svg_rgba(g))


def main():
    out, cfg_path = sys.argv[1], Path(sys.argv[2])
    cfg = json.loads(cfg_path.read_text())
    base = cfg_path.parent
    fps = cfg.get("fps", 25)
    mode = cfg["mode"]
    obj = Goat(cfg, base) if mode == "goat" else None
    bg = plate(base, cfg) if mode == "scatter" else None
    cams = cfg.get("camera", [[0, H / 2, H]])
    still = cfg.get("still")
    ff = None if still is not None else subprocess.Popen(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-framerate", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i in ([0] if still is not None else range(round(cfg["duration"] * fps))):
        t = still if still is not None else i / fps
        if obj:
            img = obj.frame(t)
        elif mode == "scatter":
            img = scene_scatter(t, cfg, bg)
        else:
            img = {"soak": scene_soak, "sow": scene_sow, "sprout": scene_sprout}[mode](t, cfg)
        cy = float(np.interp(t, [c[0] for c in cams], [c[1] for c in cams]))
        vh = float(np.interp(t, [c[0] for c in cams], [c[2] for c in cams]))
        cx = float(np.interp(t, [c[0] for c in cams], [c[3] if len(c) > 3 else W / 2 for c in cams]))
        if vh < H - 0.5:
            vw = vh * W / H
            M = np.float32([[W / vw, 0, -(cx - vw / 2) * W / vw], [0, H / vh, -(cy - vh / 2) * H / vh]])
            img = cv2.warpAffine(np.float32(img), M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        img = np.clip(img, 0, 255).astype(np.uint8)
        if still is not None:
            Image.fromarray(img).save(out)
        else:
            ff.stdin.write(img.tobytes())
    if ff:
        ff.stdin.close()
        ff.wait()
    print("saved", out)


if __name__ == "__main__":
    main()
