"""Insects-in-the-field props and cut-aways (One-Acre Challenge Ep 3 – Thatha's war against every insect).

Props (SVG strings, any coords): brinjal(x, y, s) a young brinjal (kathiri) plant – purple-green stem, broad wavy
leaves; ladybird(x, y, s, ang, t) a red seven-spot ladybird with walking legs; aphid(x, y, s) a tiny green aphid;
sprayer(x, y, s, ang) a hand pump sprayer (green bottle, white trigger head); field_plants(horizon, ...) rows of
young brinjal plants in perspective for a field frame.

Cut-aways (python tools/toon/bugs.py OUT.mp4 TIMING.json; 1080x1920):
    spot:     macro on a brinjal plant: a ladybird walks onto a leaf ("villain!"), stops, looks around.
    aim:      the same leaf; a hand sprayer's nozzle edges in from the right, trembling, aimed at the ladybird.
    eat:      the tender shoot of the next plant, crowded with tiny green aphids; the ladybird munches them one by one
              (each aphid shrinks away with a crumb), a ladybird larva helps on the lower leaf. Fact: adult ladybirds and
              their larvae eat aphids (dozens a day) – natural pest control.
    waterlog: the field (frames/grown_plate.png) – a low patch has become a muddy pond: standing water reflecting the
              sky, young plants half drowned, ripples, bubbles; the camera pushes in.
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


# ---------------------------------------------------------------- props

def leaf(x, y, ang, s, col="#4f9a35", dark="#2a5a1a"):
    """A broad brinjal leaf with a wavy edge, base at (x, y), pointing at angle ang (deg)."""
    edge = "M 0,0 C 30,-40 80,-52 120,-44 C 150,-40 170,-22 182,0 C 170,22 150,40 120,44 C 80,52 30,40 0,0 Z"
    veins = "".join(f'<path d="M {30 + 34 * k},0 q 10,-14 22,-30 M {30 + 34 * k},0 q 10,14 22,30" stroke="{dark}" stroke-width="2.5" fill="none" opacity="0.6"/>' for k in range(4))
    return (f'<g transform="translate({x:.1f} {y:.1f}) rotate({ang:.1f}) scale({s:.3f})"><path d="{edge}" fill="{col}" stroke="{dark}" stroke-width="4"/>'
            f'<path d="M 0,0 L 176,0" stroke="{dark}" stroke-width="4" opacity="0.8"/>{veins}</g>')


def brinjal(x, y, s=1.0, seed=0, sway=0.0):
    """A young brinjal plant standing at (x, y) (ground), about 300*s px tall."""
    rng = np.random.default_rng(seed)
    g = [f'<g transform="translate({x:.1f} {y:.1f}) scale({s:.3f}) rotate({sway:.1f})">',
         '<ellipse cx="0" cy="4" rx="70" ry="14" fill="#000" opacity="0.18"/>',
         '<path d="M 0,0 Q -6,-130 4,-260" stroke="#4a2a4a" stroke-width="14" fill="none" stroke-linecap="round"/>',
         '<path d="M 0,0 Q -6,-130 4,-260" stroke="#6e4a6e" stroke-width="8" fill="none" stroke-linecap="round"/>']
    for k, (yy, side) in enumerate(((-70, -1), (-110, 1), (-160, -1), (-200, 1), (-245, -1), (-250, 1))):
        ang = (-150 if side < 0 else -30) + rng.uniform(-14, 14) + (k * 6 if side < 0 else -k * 6)
        sc = 0.75 - 0.08 * k + rng.uniform(-0.05, 0.05)
        col = rng.choice(["#4f9a35", "#5aa83c", "#468c2f"])
        g.append(leaf(side * 2, yy, ang, sc, col))
    g.append('<path d="M 4,-262 q -12,-22 0,-34 q 12,12 0,34" fill="#7cc24a" stroke="#2a5a1a" stroke-width="3"/></g>')
    return "".join(g)


def ladybird(x, y, s=1.0, ang=0.0, t=0.0, walk=False):
    """A red ladybird (seven spots), head pointing at angle ang (0 = up)."""
    lg = 6 * math.sin(t * 22) if walk else 0
    legs = "".join(f'<path d="M {side * 20},{yy} l {side * 22},{yy * 0.25 + (lg if (k + (side > 0)) % 2 else -lg):.1f}" stroke="#111" stroke-width="5" stroke-linecap="round"/>'
                   for k, yy in enumerate((-12, 4, 20)) for side in (-1, 1))
    spots = "".join(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#151515"/>' for cx, cy, r in
                    ((0, -16, 7), (-15, -2, 7), (15, -2, 7), (-13, 20, 6), (13, 20, 6), (-5, 34, 4), (5, 34, 4)))
    return (f'<g transform="translate({x:.1f} {y:.1f}) rotate({ang:.1f}) scale({s:.3f})">{legs}'
            '<ellipse cx="0" cy="-36" rx="14" ry="10" fill="#151515"/>'
            '<circle cx="-7" cy="-40" r="4" fill="#fff"/><circle cx="7" cy="-40" r="4" fill="#fff"/>'
            '<path d="M -5,-45 q -6,-14 -14,-16 M 5,-45 q 6,-14 14,-16" stroke="#111" stroke-width="3" fill="none"/>'
            '<ellipse cx="0" cy="8" rx="30" ry="36" fill="#e3261c" stroke="#5a0a06" stroke-width="4"/>'
            '<path d="M 0,-27 L 0,44" stroke="#5a0a06" stroke-width="3"/>' + spots +
            '<path d="M -18,-14 q 8,-12 22,-12" stroke="#ff8a7a" stroke-width="5" fill="none" opacity="0.7" stroke-linecap="round"/></g>')


def larva(x, y, s=1.0, t=0.0):
    """A ladybird larva (dark, spiky, orange spots) – also an aphid eater."""
    g = f'<g transform="translate({x:.1f} {y:.1f}) scale({s:.3f})">'
    for k in range(6):
        cx = -50 + k * 20
        cy = 3 * math.sin(t * 6 + k)
        g += f'<ellipse cx="{cx}" cy="{cy:.1f}" rx="13" ry="11" fill="#2b2b38" stroke="#111" stroke-width="2"/>'
        if k in (1, 3):
            g += f'<circle cx="{cx}" cy="{cy - 4:.1f}" r="4" fill="#f08a24"/>'
    return g + '<circle cx="-62" cy="0" r="9" fill="#111"/></g>'


def aphid(x, y, s=1.0, alive=1.0):
    if alive <= 0.02:
        return ""
    s *= 0.4 + 0.6 * alive
    return (f'<g transform="translate({x:.1f} {y:.1f}) scale({s:.3f})" opacity="{min(1, alive * 1.5):.2f}">'
            '<ellipse cx="0" cy="0" rx="9" ry="12" fill="#9fd65a" stroke="#4a7a20" stroke-width="2"/>'
            '<circle cx="0" cy="-11" r="5" fill="#8cc64a" stroke="#4a7a20" stroke-width="1.5"/>'
            '<path d="M -3,9 l -4,8 M 3,9 l 4,8" stroke="#4a7a20" stroke-width="2"/></g>')


def sprayer(x, y, s=1.0, ang=0.0):
    """A hand pump sprayer: translucent green bottle, white trigger head, nozzle pointing left; (x, y) = bottle base."""
    return (f'<g transform="translate({x:.1f} {y:.1f}) rotate({ang:.1f}) scale({s:.3f})">'
            '<path d="M -40,0 L -44,-150 Q -40,-172 -20,-176 L 20,-176 Q 40,-172 44,-150 L 40,0 Z" fill="#43b05a" stroke="#1e5a2a" stroke-width="5"/>'
            '<path d="M -40,-60 L 40,-60" stroke="#ffffff" stroke-width="4" opacity="0.35"/>'
            '<path d="M -26,-160 Q -30,-80 -24,-12" stroke="#ffffff" stroke-width="7" opacity="0.4" fill="none" stroke-linecap="round"/>'
            '<rect x="-18" y="-196" width="36" height="22" rx="4" fill="#f2f2f2" stroke="#666" stroke-width="4"/>'
            '<path d="M -22,-196 L -22,-232 L 30,-232 Q 46,-232 46,-216 L 46,-204 L 22,-204 L 22,-196 Z" fill="#f2f2f2" stroke="#666" stroke-width="4"/>'
            '<rect x="-62" y="-228" width="42" height="16" rx="4" fill="#f2f2f2" stroke="#666" stroke-width="4"/>'
            '<circle cx="-62" cy="-220" r="5" fill="#666"/>'
            '<path d="M 12,-204 Q 26,-170 14,-150 Q 4,-170 6,-204 Z" fill="#e8e8e8" stroke="#666" stroke-width="4"/></g>')


def field_plants(horizon, avoid=None, seed=1, x0=-30, x1=750, near=1280, rows=7, density=1.0):
    """Rows of young brinjal plants in perspective (720x1280 frame coords). avoid(x, y) -> True skips a spot."""
    rng = np.random.default_rng(seed)
    g = []
    for r in range(rows, 0, -1):
        u = (r / rows) ** 1.8
        y = horizon + 18 + (near - horizon - 18) * u
        sc = 0.05 + 0.42 * u
        step = max(26, 210 * sc / density)
        x = x0 + rng.uniform(0, step)
        while x < x1:
            if not (avoid and avoid(x, y)):
                g.append(brinjal(x + rng.uniform(-8, 8) * sc * 3, y, sc, int(rng.integers(0, 999)), rng.uniform(-6, 6)))
            x += step * rng.uniform(0.85, 1.15)
    return "".join(g)


# ---------------------------------------------------------------- cut-aways

def macro_bg(seed=2):
    return (f'<defs><radialGradient id="bk" cx="0.5" cy="0.35" r="0.8"><stop offset="0" stop-color="#cfe8a8"/>'
            f'<stop offset="0.6" stop-color="#8fbd6a"/><stop offset="1" stop-color="#5a7a40"/></radialGradient></defs>'
            f'<rect width="{W}" height="{H}" fill="url(#bk)"/>'
            '<circle cx="180" cy="300" r="120" fill="#f6f2c0" opacity="0.25"/><circle cx="880" cy="520" r="80" fill="#f6f2c0" opacity="0.2"/>'
            '<circle cx="760" cy="1650" r="160" fill="#4a6a30" opacity="0.3"/>')


def big_plant(t):
    """Macro stem and leaves of one brinjal plant (fills the frame)."""
    sway = 1.5 * math.sin(t * 1.3)
    g = [f'<g transform="rotate({sway:.2f} 540 2000)">',
         '<path d="M 520,2000 Q 500,1400 545,700" stroke="#3e2240" stroke-width="64" fill="none" stroke-linecap="round"/>',
         '<path d="M 520,2000 Q 500,1400 545,700" stroke="#6e4a6e" stroke-width="44" fill="none" stroke-linecap="round"/>']
    for x, y, ang, s in ((520, 1500, -160, 2.6), (515, 1150, -20, 3.0), (535, 900, -150, 2.2), (545, 760, -40, 1.9)):
        g.append(leaf(x, y, ang, s, "#55a33a"))
    g.append('<path d="M 545,700 q -40,-80 0,-130 q 40,50 0,130" fill="#7cc24a" stroke="#2a5a1a" stroke-width="5"/></g>')
    return "".join(g)


def scene_spot(t, cfg):
    g = [macro_bg(), big_plant(t)]
    u = ease(t / 1.6)                                           # walks in along the big right leaf, stops, looks round
    x, y = 1150 - 380 * u, 1150 - 120 * u
    ang = -100 + 20 * u + (12 * math.sin((t - 1.8) * 3) if t > 1.8 else 0)
    g.append(ladybird(x, y, 2.2, ang, t, walk=u < 0.99))
    return "".join(g)


def scene_aim(t, cfg):
    g = [macro_bg(), big_plant(t), ladybird(770, 1030, 2.2, -80 + 8 * math.sin(t * 2), t)]
    u = ease(t / 1.2)
    shake = 6 * math.sin(t * 31) + 4 * math.sin(t * 17)
    g.append(sprayer(1400 - 330 * u, 1330 + shake, 2.6, -8 + 0.6 * math.sin(t * 23)))
    return "".join(g)


APHIDS = [(540 + 26 * math.cos(k * 2.4) * (1 + k % 3 * 0.4), 640 + 30 * k + 8 * math.sin(k), 1 + 0.2 * (k % 3)) for k in range(16)]


def scene_eat(t, cfg):
    g = [macro_bg(5), big_plant(0.3)]
    t0, per = cfg.get("eat_from", 0.8), cfg.get("per", 0.42)
    order = sorted(range(len(APHIDS)), key=lambda k: -APHIDS[k][1])        # from the bottom up
    eaten = {k: (t - (t0 + i * per)) / 0.3 for i, k in enumerate(order)}
    for k, (x, y, s) in enumerate(APHIDS):
        g.append(aphid(x, y, 1.6 * s, 1 - min(1, max(0, eaten[k]))))
    i_now = min(len(order) - 1, max(0, int((t - t0) / per)))
    tx, ty, _ = APHIDS[order[i_now]]
    if t < t0:
        u = ease(t / t0)
        bx, by = 760 - 150 * u, 1300 - 280 * u
    else:
        bx, by = tx + 46, ty + 50
    chew = 4 * math.sin(t * 28) if t > t0 else 0
    g.append(ladybird(bx + chew * 0.3, by, 2.0, -30 + chew, t, walk=t < t0))
    for i, k in enumerate(order):                                       # little crumbs where one was eaten
        d = t - (t0 + i * per) - 0.2
        if 0 < d < 0.5:
            x, y, _ = APHIDS[k]
            g.append("".join(f'<circle cx="{x + 30 * math.cos(a) * d * 2:.0f}" cy="{y - 20 * d + 30 * math.sin(a) * d * 2:.0f}" r="4" fill="#b6e07a" opacity="{1 - d * 2:.2f}"/>' for a in (0.5, 2.0, 3.6, 5.0)))
    g.append(larva(620 - 15 * math.sin(t * 0.8), 1210, 1.6, t))
    return "".join(g)


class Waterlog:
    def __init__(self, cfg, base):
        self.cfg = cfg
        im = np.array(Image.open(base / cfg["bg"]).convert("RGB").resize((W, H), Image.LANCZOS)).astype(np.float32)
        self.bg = im
        hz = int(cfg.get("horizon", 470) * 1.5)
        # the pond: a soft irregular blob in the near field, reflecting the sky (mirrored top band, muddied)
        mask = np.zeros((H, W), np.float32)
        cv2.ellipse(mask, (560, 1430), (470, 230), -4, 0, 360, 1, -1)
        cv2.ellipse(mask, (300, 1300), (230, 120), 8, 0, 360, 1, -1)
        cv2.ellipse(mask, (820, 1560), (260, 150), 0, 0, 360, 1, -1)
        self.mask = cv2.GaussianBlur(mask, (0, 0), 14)
        sky = im[:hz][::-1]
        ref = cv2.resize(sky, (W, H - hz))
        self.refl = np.zeros_like(im)
        self.refl[hz:] = ref * 0.55 + np.array([120, 95, 60]) * 0.45
        self.hz = hz
        rng = np.random.default_rng(4)
        self.drown = [(rng.uniform(220, 900), rng.uniform(1260, 1640), rng.uniform(0.55, 0.8)) for _ in range(9)]

    def frame(self, t):
        rows = np.arange(H)
        shift = (5 * np.sin(rows * 0.07 + t * 3)).astype(np.int32)
        cols = (np.arange(W)[None, :] + shift[:, None]) % W
        refl = self.refl[rows[:, None], cols]
        m = self.mask[..., None]
        img = self.bg * (1 - m) + refl * m
        g = []
        for k, (x, y, s) in enumerate(self.drown):              # young plants standing in the water, only tops showing
            g.append(f'<g opacity="0.95">{brinjal(x, y, s, k, 2 * math.sin(t + k))}</g>')
            g.append(f'<rect x="{x - 90 * s:.0f}" y="{y - 120 * s:.0f}" width="{180 * s:.0f}" height="{130 * s:.0f}" fill="none"/>')
        lay = svg_rgba("".join(g))
        cut = np.zeros((H, W), np.float32)                      # water hides the lower stems
        for x, y, s in self.drown:
            cut[int(y - 110 * s):int(y + 10), int(x - 100 * s):int(x + 100 * s)] = 1
        lay[..., 3] *= 1 - cut * self.mask
        img = over(img, lay)
        w = []
        for k in range(10):                                       # ripples and bubbles
            u = (t * 0.6 + k * 0.137) % 1
            x, y = 300 + (k * 97) % 560, 1300 + (k * 61) % 330
            if self.mask[int(y), int(x)] > 0.5:
                w.append(f'<ellipse cx="{x}" cy="{y}" rx="{10 + 70 * u:.0f}" ry="{4 + 22 * u:.0f}" fill="none" stroke="#e8f0ff" stroke-width="3" opacity="{0.7 * (1 - u):.2f}"/>')
        img = over(img, svg_rgba("".join(w)))
        return img


SCENES = {"spot": scene_spot, "aim": scene_aim, "eat": scene_eat}


def main():
    out, cfg_path = sys.argv[1], Path(sys.argv[2])
    cfg = json.loads(cfg_path.read_text())
    fps = cfg.get("fps", 25)
    obj = Waterlog(cfg, cfg_path.parent) if cfg["mode"] == "waterlog" else None
    cams = cfg.get("camera", [[0, H / 2, H]])
    still = cfg.get("still")
    ff = None if still is not None else subprocess.Popen(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-framerate", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i in ([0] if still is not None else range(round(cfg["duration"] * fps))):
        t = still if still is not None else i / fps
        img = obj.frame(t) if obj else svg_rgba(SCENES[cfg["mode"]](t, cfg))[..., :3]
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
