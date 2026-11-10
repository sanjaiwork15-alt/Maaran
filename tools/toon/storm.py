"""Storm-day cut-aways (One-Acre Challenge Ep 6 – the day everything went wrong). 1080x1920, no words.

python tools/toon/storm.py OUT.mp4 TIMING.json   ("still": t renders one PNG)
    downpour: cfg "bg" (a stormy 720x1280 plate) under heavy slanting rain; water creeps up the furrows.
    shield:   macro: a young brinjal plant in the rain; a big banana leaf swings in above it, drops bounce off it.
    bend:     macro: young plants in wind and rain bend over one by one and lie flat in the water.
    slip:     close-up of his feet (the owner's 01_front art) on wet mud: the right foot skids forward, both feet fly
              up out of frame, a splash of mud.
    drain:    after the rain (cfg "bg" plate): the higher left side is draining – water runs off along the furrows –
              while the low right patch stays a still pond; the camera pans across.
    drainplan: his notebook: a pencil draws the field from above, slope arrows down to the low corner, a drainage
              channel along the edge to a farm pond; blue water then runs along the channel.
    seeds:    close-up: the nearly empty jute seed pouch on the wet ground, tipped over – only a few seeds roll out.
Fact (TNAU): plan field drainage before the rains – grade towards a channel at the low side, open drains / a farm
pond so water does not stand on the crop.
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
from bugs import brinjal, leaf  # noqa: E402
from rain import draw_rain  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
W, H = 1080, 1920


def svg_rgba(body, w=W, h=H):
    png = cairosvg.svg2png(bytestring=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">{body}</svg>'.encode())
    return np.array(Image.open(io.BytesIO(png)).convert("RGBA")).astype(np.float32)


def over(rgb, rgba):
    a = rgba[..., 3:4] / 255
    return rgb * (1 - a) + rgba[..., :3] * a


def paste(dst, spr, x, y):
    h, w = spr.shape[:2]
    xs, ys, xe, ye = max(0, int(x)), max(0, int(y)), min(dst.shape[1], int(x) + w), min(dst.shape[0], int(y) + h)
    if xe > xs and ye > ys:
        s = spr[ys - int(y):ye - int(y), xs - int(x):xe - int(x)]
        a = s[..., 3:4] / 255
        dst[ys:ye, xs:xe] = dst[ys:ye, xs:xe] * (1 - a) + s[..., :3] * a
    return dst


def ease(u):
    u = min(max(u, 0), 1)
    return u * u * (3 - 2 * u)


def plate(base, cfg, key="bg"):
    return np.array(Image.open(base / cfg[key]).convert("RGB").resize((W, H), Image.LANCZOS)).astype(np.float32)


def rain(img, t, rate=1.0, ground=700, wind=0.22, seed=5):
    bgr = np.clip(img[..., ::-1], 0, 255).astype(np.uint8).copy()
    draw_rain(bgr, t, {"rate": rate, "ground": ground, "wind": wind}, K=1.5, seed=seed)
    draw_rain(bgr, t * 1.1 + 0.3, {"rate": rate * 0.6, "ground": 2000, "wind": wind}, K=1.5, seed=seed + 7)
    return bgr[..., ::-1].astype(np.float32)


def banana_leaf(x, y, s=1.0, ang=0.0):
    """A big banana leaf: midrib from (x, y) along +x; the blade with parallel veins and a couple of tears."""
    g = [f'<g transform="translate({x:.0f} {y:.0f}) rotate({ang:.1f}) scale({s:.3f})">',
         '<path d="M 0,0 C 120,-130 420,-150 620,-40 C 520,10 300,30 0,0 Z" fill="#4caf50" stroke="#1b5e20" stroke-width="6"/>',
         '<path d="M 0,0 C 140,80 420,90 620,-40" fill="#43a047" stroke="#1b5e20" stroke-width="6"/>']
    for k in range(1, 12):
        u = k / 12
        x0, y0 = 620 * u, -40 * u ** 2 + 4
        g.append(f'<path d="M {x0:.0f},{y0:.0f} q 20,-50 {30 - 10 * u:.0f},{-100 + 40 * u:.0f}" stroke="#2e7d32" stroke-width="3" fill="none"/>')
        g.append(f'<path d="M {x0:.0f},{y0:.0f} q 20,40 {30 - 10 * u:.0f},{70 - 30 * u:.0f}" stroke="#2e7d32" stroke-width="3" fill="none"/>')
    g.append('<path d="M 260,-112 L 280,-60 M 420,-96 L 436,-58" stroke="#a5d6a7" stroke-width="5"/>')
    g.append('<path d="M -60,30 Q -20,20 0,0 Q 300,-30 620,-40" stroke="#c5e1a5" stroke-width="12" fill="none" stroke-linecap="round"/></g>')
    return "".join(g)


def macro_bg(dark=True):
    top, bot = ("#5d6873", "#3a4148") if dark else ("#b7c3cc", "#7f8c96")
    return (f'<defs><linearGradient id="mb" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{top}"/>'
            f'<stop offset="1" stop-color="{bot}"/></linearGradient></defs><rect width="{W}" height="{H}" fill="url(#mb)"/>'
            '<rect y="1500" width="1080" height="420" fill="#4a2e1a"/><path d="M 0,1500 Q 540,1460 1080,1500" fill="#5a3a22"/>')


def scene_shield(t, cfg):
    sway = 4 * math.sin(t * 5)
    g = [macro_bg(), f'<g transform="translate(540 1520) scale(3.2) rotate({sway:.1f}) translate(-540 -1520)">{brinjal(540, 1520, 1.0, 3)}</g>']
    u = ease((t - 0.4) / 0.7)
    lx, ly = 1500 - 1260 * u, 560 + 40 * math.sin(t * 3)
    g.append(banana_leaf(lx, ly, 1.25, -8 + 4 * math.sin(t * 4)))
    img = svg_rgba("".join(g))[..., :3]
    img = rain(img, t, 1.2, 1000, 0.25)
    if u > 0.9:                                                # drops bouncing off the leaf
        rng = np.random.default_rng(int(t * 25))
        bits = "".join(f'<circle cx="{rng.uniform(260, 960):.0f}" cy="{rng.uniform(380, 520):.0f}" r="{rng.uniform(4, 9):.0f}" fill="#e3f2fd" opacity="0.9"/>' for _ in range(22))
        img = over(img, svg_rgba(bits))
    return img


def scene_bend(t, cfg):
    g = [macro_bg()]
    water = 1500 - 70 * ease(t / 3)
    for k, (x, s, t0) in enumerate(((220, 1.5, 0.4), (540, 1.9, 1.0), (860, 1.5, 1.6))):
        fall = ease((t - t0) / 0.9)
        ang = -52 * fall * (1 if k != 1 else 0.8) + 4 * math.sin(t * 6 + k) * (1 - fall)
        g.append(f'<g transform="translate({x} 1520) rotate({ang:.1f}) scale({s}) translate({-x} -1520)">{brinjal(x, 1520, 1.0, 10 + k)}</g>')
    g.append(f'<rect x="0" y="{water:.0f}" width="1080" height="{1920 - water:.0f}" fill="#8a7a62" opacity="0.8"/>')
    g.append(f'<path d="M 0,{water:.0f} L 1080,{water:.0f}" stroke="#c9d3da" stroke-width="5" opacity="0.7"/>')
    img = svg_rgba("".join(g))[..., :3]
    return rain(img, t, 1.3, 1350, 0.35)


FEET = Path.home() / ".maaran/cache/front_feet_1500_rgba.png"


def scene_slip(t, cfg):
    from water import front_feet, mud_svg
    feet = front_feet()
    sc = 1080 / feet.shape[1] * 1.2
    lay = cv2.resize(feet, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
    img = np.zeros((H, W, 3), np.float32) + np.array([70, 74, 80])
    img = over(img, svg_rgba(mud_svg(1450, t, seed=3)))
    u = ease((t - 0.6) / 0.5)                                  # the skid, then the feet fly up and out
    ang = -50 * u
    dx, dy = 260 * u, -900 * ease((t - 0.9) / 0.4)
    M = cv2.getRotationMatrix2D((lay.shape[1] * 0.5, lay.shape[0]), ang, 1.0)
    r = cv2.warpAffine(lay, M, (lay.shape[1], lay.shape[0]))
    paste(img, r, (W - lay.shape[1]) / 2 - 60 + dx, 1500 - lay.shape[0] + dy)
    if t > 0.6:
        v = min(1, (t - 0.6) / 0.6)
        img = over(img, svg_rgba("".join(f'<circle cx="{540 + 420 * math.cos(a) * v:.0f}" cy="{1450 - 380 * math.sin(a) * v + 500 * v * v:.0f}" r="{22 * (1 - v) + 6:.0f}" fill="#4a3018"/>'
                                         for a in (0.2, 0.6, 1.0, 1.4, 1.8, 2.3, 2.8))))
        img = over(img, svg_rgba(f'<path d="M 260,1440 Q 560,{1440 - 30 * v:.0f} 900,1450" stroke="#2e1c0e" stroke-width="16" fill="none" opacity="{1 - v * 0.5:.2f}"/>'))
    return rain(img, t, 1.0, 1300, 0.25)


class Drain:
    def __init__(self, cfg, base):
        self.cfg = cfg
        self.bg = plate(base, cfg)
        m = np.zeros((H, W), np.float32)
        cv2.ellipse(m, (800, 1480), (330, 200), -6, 0, 360, 1, -1)
        cv2.ellipse(m, (950, 1330), (200, 90), 0, 0, 360, 1, -1)
        self.pond = cv2.GaussianBlur(m, (0, 0), 16)
        hz = int(cfg.get("horizon", 583) * 1.5)
        rows = np.arange(H)
        src = np.clip(2 * hz - rows, 0, hz - 1)
        self.refl = self.bg[src] * 0.6 + np.array([110, 100, 90]) * 0.4
        rng = np.random.default_rng(2)
        self.streams = [(rng.uniform(40, 520), rng.uniform(0, 1), rng.uniform(0.7, 1.3)) for _ in range(46)]

    def frame(self, t):
        img = self.bg * (1 - self.pond[..., None]) + self.refl * self.pond[..., None]
        g = []
        for x0, ph, sp in self.streams:                        # trickles running down the furrows towards the camera
            u = (t * 0.5 * sp + ph) % 1
            y = 980 + 900 * u
            x = x0 + (x0 - 300) * u * 0.6
            g.append(f'<path d="M {x:.0f},{y:.0f} l {(x0 - 300) * 0.04:.0f},{60 + 60 * u:.0f}" stroke="#d6e4ef" stroke-width="{3 + 5 * u:.0f}" opacity="{0.75 * (1 - abs(u - 0.5)):.2f}" stroke-linecap="round"/>')
        for k in range(6):
            u = (t * 0.4 + k * 0.17) % 1
            g.append(f'<ellipse cx="{720 + (k * 83) % 300}" cy="{1400 + (k * 47) % 160}" rx="{10 + 50 * u:.0f}" ry="{4 + 16 * u:.0f}" fill="none" stroke="#e8f0ff" stroke-width="3" opacity="{0.6 * (1 - u):.2f}"/>')
        return over(img, svg_rgba("".join(g)))


def scene_drainplan(t, cfg):
    g = ['<rect width="1080" height="1920" fill="#6d4c33"/>',
         '<g transform="rotate(-3 540 960)"><rect x="90" y="200" width="900" height="1520" rx="18" fill="#fbf8ee" stroke="#8a7a5a" stroke-width="8"/>']
    for k in range(14):
        g.append(f'<line x1="130" y1="{320 + k * 100}" x2="950" y2="{320 + k * 100}" stroke="#9ec3e6" stroke-width="4"/>')
    for k in range(9):
        g.append(f'<circle cx="90" cy="{280 + k * 170}" r="22" fill="none" stroke="#888" stroke-width="8"/>')
    pen = None
    # 1. the field square
    u = ease((t - 0.2) / 0.9)
    per = 4 * 560
    if u > 0:
        g.append(f'<rect x="230" y="520" width="560" height="560" fill="none" stroke="#5d4037" stroke-width="10" stroke-dasharray="{per * u:.0f} {per}"/>')
        if u < 1:
            d = per * u
            pen = (230 + min(d, 560), 520) if d < 560 else ((790, 520 + d - 560) if d < 1120 else ((790 - (d - 1120), 1080) if d < 1680 else (230, 1080 - (d - 1680))))
    # 2. crop rows inside
    v = ease((t - 1.1) / 0.6)
    for k in range(5):
        if v > k / 5:
            g.append(f'<line x1="280" y1="{580 + k * 110}" x2="740" y2="{580 + k * 110}" stroke="#66bb6a" stroke-width="8" stroke-dasharray="14 12"/>')
    # 3. slope arrows towards the low corner (bottom right)
    w = ease((t - 1.8) / 0.8)
    for k, (x, y) in enumerate(((330, 600), (500, 640), (360, 820), (560, 830), (660, 700))):
        if w > k / 5:
            g.append(f'<path d="M {x},{y} l 80,80" stroke="#1e88e5" stroke-width="8" stroke-linecap="round"/><path d="M {x + 80},{y + 80} l -34,-4 m 34,4 l -4,-34" stroke="#1e88e5" stroke-width="8" stroke-linecap="round"/>')
            if w < 1 and k == int(w * 5):
                pen = (x + 80, y + 80)
    # 4. the drain along the bottom and right edge to a farm pond
    c = ease((t - 2.8) / 1.0)
    if c > 0:
        L = 600 + 580
        g.append(f'<path d="M 230,1130 L 840,1130 L 840,560" stroke="#5d4037" stroke-width="30" fill="none" stroke-dasharray="{L * c:.0f} {L}" stroke-linecap="round"/>')
        if c < 1:
            d = L * c
            pen = (230 + d, 1130) if d < 610 else (840, 1130 - (d - 610))
    p = ease((t - 3.8) / 0.5)
    if p > 0:
        g.append(f'<ellipse cx="840" cy="1300" rx="{110 * p:.0f}" ry="{70 * p:.0f}" fill="#64b5f6" stroke="#1565c0" stroke-width="8"/>')
        g.append(f'<path d="M 840,1130 L 840,1240" stroke="#5d4037" stroke-width="30" opacity="{p:.2f}"/>')
    f = (t - 4.4)
    if f > 0:                                                  # water running along the channel into the pond
        for k in range(10):
            u = (f * 0.6 + k / 10) % 1
            L = 610 + 110
            d = L * u
            x, y = (230 + d, 1130) if d < 610 else (840, 1130 + (d - 610))
            g.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="10" fill="#1e88e5"/>')
        g.append(f'<path d="M 840,1130 L 840,560" stroke="#64b5f6" stroke-width="12" stroke-dasharray="20 20" stroke-dashoffset="{-f * 80:.0f}"/>')
    g.append('</g>')
    if pen:
        x, y = pen
        g.append(f'<g transform="translate({x:.0f} {y:.0f}) rotate(35)"><rect x="-14" y="-420" width="28" height="380" fill="#fbc02d" stroke="#5a4a00" stroke-width="4"/>'
                 '<path d="M -14,-40 L 14,-40 L 0,0 Z" fill="#f2d2a0" stroke="#5a4a00" stroke-width="3"/><path d="M -4,-12 L 4,-12 L 0,0 Z" fill="#333"/>'
                 '<rect x="-14" y="-440" width="28" height="24" fill="#e57373"/></g>')
    return svg_rgba("".join(g))[..., :3]


def pouch(x, y, s=1.0, ang=0.0, n_seeds=0):
    """A small jute seed pouch lying on its side, mouth open to the right."""
    seeds = "".join(f'<ellipse cx="{150 + 18 * k}" cy="{6 + (k % 2) * 8}" rx="7" ry="5" fill="#f1e3b0" stroke="#8a7a40" stroke-width="2"/>' for k in range(n_seeds))
    return (f'<g transform="translate({x:.0f} {y:.0f}) rotate({ang:.1f}) scale({s:.3f})">'
            '<path d="M -150,10 C -160,-70 -60,-110 40,-90 C 100,-80 130,-50 140,-30 L 150,40 C 120,60 40,70 -40,64 C -120,58 -150,44 -150,10 Z" fill="#c8a165" stroke="#5a4020" stroke-width="7"/>'
            + "".join(f'<path d="M {-130 + 26 * k},-60 L {-120 + 26 * k},50" stroke="#a5814a" stroke-width="4" opacity="0.7"/>' for k in range(10))
            + "".join(f'<path d="M -146,{-50 + 18 * k} L 136,{-50 + 18 * k}" stroke="#a5814a" stroke-width="3" opacity="0.55"/>' for k in range(7)) +
            '<path d="M 112,-50 C 96,-10 96,30 112,56" stroke="#7a5a2a" stroke-width="12" fill="none"/>'
            '<path d="M 104,40 q -30,30 -70,26 M 104,40 q -10,40 -40,60" stroke="#e8d5a0" stroke-width="7" fill="none" stroke-linecap="round"/>' +
            '<ellipse cx="146" cy="5" rx="22" ry="40" fill="#3a2a14" stroke="#5a4020" stroke-width="6"/>'
            '<path d="M 120,-36 Q 170,-70 200,-40" stroke="#8a6a3a" stroke-width="7" fill="none"/>' + seeds + '</g>')


def scene_seeds(t, cfg):
    g = [macro_bg(False), '<rect y="900" width="1080" height="1020" fill="#4a2e1a"/>',
         '<ellipse cx="300" cy="1500" rx="160" ry="30" fill="#c9d8e6" opacity="0.4"/><ellipse cx="820" cy="1640" rx="200" ry="34" fill="#c9d8e6" opacity="0.35"/>']
    shake = 6 * math.sin(t * 18) * ease((t - 0.3) / 0.3) * (1 - ease((t - 1.6) / 0.3))
    g.append(pouch(430, 1200, 2.4, -12 + shake))
    rng = np.random.default_rng(2)
    for k in range(5):                                         # only five seeds roll out
        t0 = 0.6 + 0.25 * k
        u = ease((t - t0) / 0.6)
        if u > 0:
            x = 760 + u * (80 + 60 * k)
            y = 1230 + 60 * u + 20 * k - 30 * math.sin(math.pi * u)
            g.append(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="16" ry="11" fill="#f1e3b0" stroke="#8a7a40" stroke-width="4" transform="rotate({u * 400:.0f} {x:.0f} {y:.0f})"/>')
    return svg_rgba("".join(g))[..., :3]


SCENES = {"shield": scene_shield, "bend": scene_bend, "slip": scene_slip, "drainplan": scene_drainplan, "seeds": scene_seeds}


def main():
    out, cfg_path = sys.argv[1], Path(sys.argv[2])
    cfg = json.loads(cfg_path.read_text())
    base = cfg_path.parent
    fps = cfg.get("fps", 25)
    mode = cfg["mode"]
    obj = Drain(cfg, base) if mode == "drain" else None
    bg = plate(base, cfg) if mode == "downpour" else None
    cams = cfg.get("camera", [[0, H / 2, H]])
    still = cfg.get("still")
    ff = None if still is not None else subprocess.Popen(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-framerate", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i in ([0] if still is not None else range(round(cfg["duration"] * fps))):
        t = still if still is not None else i / fps
        if obj:
            img = obj.frame(t)
        elif mode == "downpour":
            img = bg.copy()
            hz = int(cfg.get("horizon", 583) * 1.5)
            lvl = ease(t / cfg["duration"])
            yy = np.arange(H)[:, None]
            m = (((yy - hz) % 60) < 14 * lvl).astype(np.float32) * (yy > hz + 200) * np.ones((1, W))
            m = cv2.GaussianBlur(m, (0, 0), 2)[..., None] * 0.7
            img = img * (1 - m) + np.array([150, 150, 150]) * m
            img = rain(img, t, 1.5, 700, 0.3)
        else:
            img = SCENES[mode](t, cfg)
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
