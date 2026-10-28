"""Night-to-morning animation (Maaran Thatha – Day 3). 1080x1920.

Usage:
    python tools/toon/morning.py OUT.mp4 TIMING.json
TIMING.json: {"mode": "sleep" | "set" | "ring" | "rooster" | "far", "duration": 4, "fps": 25, ...}
sleep:   animates a still ("frame", 720x1280 or 1080x1920; path relative to TIMING.json): the light follows
         "light": [[t, L], ...] (L 0 = night, 0.5 = dawn, 1 = morning) – the sky (if any) becomes a starry night or
         a pink-orange dawn – and the blanket breathes ("breath": [y_top, x0, x1] in 720 units, slow rise and fall).
set:     close-up of the old twin-bell alarm clock on the stool by his kattil at night: the alarm hand turns to the
         wake-up time, then his phone slides in beside it ("oramaa vechitten").
ring:    morning close-up: the clock rings (shakes, ring lines), his arm reaches down from the blanket ("arm": PNG of
         the owner's hanging-hand drawing) and presses the button; the clock stops ("press": t).
rooster: the rooster on the tulsi maadam at sunrise, crowing twice ("crow": [t, ...]).
far:     the clock far away on the thinnai step, small in the courtyard ("frame" = the courtyard still).
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
from rain import sky_mask  # noqa: E402

W, H = 1080, 1920
ROOT = Path(__file__).resolve().parents[2]


def ease(u):
    u = min(max(u, 0), 1)
    return u * u * (3 - 2 * u)


def svg_rgba(body, w=W, h=H):
    png = cairosvg.svg2png(bytestring=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">{body}</svg>'.encode())
    return np.array(Image.open(io.BytesIO(png)).convert("RGBA"))


def over(rgb, rgba):
    a = rgba[..., 3:4].astype(np.float32) / 255
    return (rgb * (1 - a) + rgba[..., :3] * a).astype(np.uint8)


# ---------------------------------------------------------------- light

NIGHT = np.array([0.30, 0.36, 0.62], np.float32)
DAWN = np.array([0.95, 0.74, 0.70], np.float32)
DAY = np.array([1.02, 0.99, 0.93], np.float32)


def light_mult(L):
    if L <= 0.5:
        return NIGHT + (DAWN - NIGHT) * (L / 0.5)
    return DAWN + (DAY - DAWN) * ((L - 0.5) / 0.5)


def night_sky(h, seed=4):
    rng = np.random.default_rng(seed)
    stars = "".join(f'<circle cx="{rng.uniform(0, W):.0f}" cy="{rng.uniform(0, h * 0.8):.0f}" r="{rng.uniform(1.5, 3.5):.1f}" '
                    f'fill="#ffffff" fill-opacity="{rng.uniform(0.5, 1):.2f}"/>' for _ in range(90))
    return svg_rgba(f'<defs><linearGradient id="n" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#070d22"/>'
                    f'<stop offset="1" stop-color="#22325a"/></linearGradient></defs><rect width="{W}" height="{h}" fill="url(#n)"/>{stars}'
                    f'<circle cx="{W * 0.78:.0f}" cy="{h * 0.2:.0f}" r="46" fill="#f4f0d8"/><circle cx="{W * 0.78 + 20:.0f}" cy="{h * 0.2 - 12:.0f}" r="42" fill="#0d1630"/>',
                    W, h)[..., :3].astype(np.float32)


def dawn_sky(h):
    return svg_rgba(f'<defs><linearGradient id="d" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#6f86c4"/>'
                    f'<stop offset="0.55" stop-color="#f2a6a0"/><stop offset="1" stop-color="#f8c77a"/></linearGradient></defs>'
                    f'<rect width="{W}" height="{h}" fill="url(#d)"/>', W, h)[..., :3].astype(np.float32)


class Sleep:
    def __init__(self, cfg, base):
        img = Image.open(base / cfg["frame"]).convert("RGB")
        if img.size != (W, H):
            img = img.resize((W, H), Image.LANCZOS)
        self.img = np.array(img).astype(np.float32)
        self.cfg = cfg
        hor = cfg.get("horizon", 0)
        self.mask = sky_mask(np.array(img), int(hor * 1.5))[..., None] if hor else None
        if hor:
            self.night = np.zeros_like(self.img)
            self.dawn = np.zeros_like(self.img)
            self.night[:int(hor * 1.5)] = night_sky(int(hor * 1.5))
            self.dawn[:int(hor * 1.5)] = dawn_sky(int(hor * 1.5))
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.yy, self.xx = yy, xx
        b = cfg.get("breath")
        if b:
            y0, x0, x1 = (v * 1.5 for v in b)
            self.bw = (np.exp(-((yy - y0) / 70) ** 2) * (1 / (1 + np.exp(-(xx - x0) / 20))) * (1 / (1 + np.exp((xx - x1) / 20)))).astype(np.float32)

    def frame(self, t):
        cfg = self.cfg
        lt = cfg.get("light", [[0, 1], [1, 1]])
        L = float(np.interp(t, [p[0] for p in lt], [p[1] for p in lt]))
        img = self.img
        if cfg.get("breath"):
            dy = (self.bw * 7 * math.sin(2 * math.pi * t / 3.6)).astype(np.float32)
            img = cv2.remap(img, self.xx, self.yy + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        out = img * light_mult(L)
        if self.mask is not None:
            if L < 0.5:
                sky = self.night * (1 - L / 0.5) + self.dawn * (L / 0.5)
                k = 1.0
            else:
                sky = self.dawn
                k = 1 - (L - 0.5) / 0.5
            out = out * (1 - self.mask * k) + sky * self.mask * k
        if L < 0.35:                                          # a lamp's warm glow by the cot at night
            g = cfg.get("lamp")
            if g:
                gx, gy = g[0] * 1.5, g[1] * 1.5
                m = np.exp(-(((self.xx - gx) / 380) ** 2 + ((self.yy - gy) / 380) ** 2))[..., None] * (0.35 - L) / 0.35 * 0.35
                out = out + (np.array([255, 190, 110], np.float32) - out) * m
        return cv2.cvtColor(np.clip(out, 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR)


def rooster(x, y, s=1.0, crow=0.0):
    """Cartoon rooster standing at (x, y) facing left; crow 0..1 opens the beak and lifts the head."""
    lift = -18 * crow
    return (f'<g transform="translate({x} {y}) scale({s})">'
            f'<path d="M 30,-60 Q 95,-120 80,-30 Q 70,-75 40,-50 Z" fill="#1f5b3a" stroke="#0e2e1c" stroke-width="3"/>'
            f'<path d="M 45,-70 Q 110,-95 85,-20" stroke="#2f8a54" stroke-width="10" fill="none"/>'
            f'<ellipse cx="10" cy="-40" rx="52" ry="38" fill="#c0461e" stroke="#5a1e0a" stroke-width="3.5"/>'
            f'<path d="M -10,-40 Q 20,-10 50,-38" fill="#e07a2e" stroke="#5a1e0a" stroke-width="2.5"/>'
            f'<line x1="-5" y1="-4" x2="-12" y2="0" stroke="#e0a020" stroke-width="5"/><line x1="15" y1="-4" x2="20" y2="0" stroke="#e0a020" stroke-width="5"/>'
            f'<line x1="-5" y1="-6" x2="-5" y2="-2" stroke="#e0a020" stroke-width="5"/><line x1="15" y1="-6" x2="15" y2="-2" stroke="#e0a020" stroke-width="5"/>'
            f'<g transform="translate(0 {lift:.1f}) rotate({-14 * crow:.1f} -30 -70)">'
            f'<path d="M -30,-55 Q -40,-95 -28,-108 Q -10,-100 -12,-60 Z" fill="#d8552a" stroke="#5a1e0a" stroke-width="3"/>'
            f'<circle cx="-30" cy="-100" r="20" fill="#e06a2e" stroke="#5a1e0a" stroke-width="3"/>'
            f'<path d="M -42,-118 q 4,-14 10,-2 q 4,-16 10,-2 q 6,-12 8,4" fill="#d81e1e" stroke="#7a0a0a" stroke-width="2"/>'
            f'<path d="M -48,-102 L {-66 - 4 * crow:.0f},{-98 - 6 * crow:.0f} L -48,-94 Z" fill="#f2b420" stroke="#7a5a0a" stroke-width="2"/>'
            + (f'<path d="M -48,-96 L {-66 - 4 * crow:.0f},{-88 + 4 * crow:.0f} L -48,-92 Z" fill="#f2b420" stroke="#7a5a0a" stroke-width="2"/>' if crow > 0.2 else "")
            + f'<path d="M -36,-88 q -4,10 2,16 q 6,-4 2,-16" fill="#d81e1e"/><circle cx="-34" cy="-104" r="3.5" fill="#111"/></g></g>')


# ---------------------------------------------------------------- the alarm clock

def clock(x, y, s, t=0.0, ring=0.0, alarm_ang=300.0, night=False):
    """Old twin-bell alarm clock standing on (x, y); ring 0..1 shakes it and draws the ring lines."""
    sh = math.sin(t * 60) * 6 * ring
    face = "#f6f1df" if not night else "#c8d4f0"
    hour, minute = -30 + 150, 60
    g = f'<g transform="translate({x + sh:.1f} {y}) scale({s}) rotate({math.sin(t * 47) * 4 * ring:.1f} 0 -120)">'
    g += ('<line x1="-60" y1="-30" x2="-80" y2="0" stroke="#3a3a3a" stroke-width="12" stroke-linecap="round"/>'
          '<line x1="60" y1="-30" x2="80" y2="0" stroke="#3a3a3a" stroke-width="12" stroke-linecap="round"/>')
    for bx in (-62, 62):                                          # bells
        g += (f'<path d="M {bx - 40},-205 A 40 40 0 0 1 {bx + 40},-205 Z" fill="#c9a43a" stroke="#6a5010" stroke-width="5" '
              f'transform="rotate({-25 if bx < 0 else 25} {bx} -205)"/>')
    hx = math.sin(t * 70) * 26 * ring
    g += (f'<line x1="0" y1="-200" x2="{hx:.0f}" y2="-238" stroke="#555" stroke-width="7"/><circle cx="{hx:.0f}" cy="-240" r="9" fill="#777"/>'
          f'<rect x="-14" y="-232" width="28" height="18" rx="4" fill="#8a1a1a" stroke="#3a0808" stroke-width="3"/>'
          f'<circle cx="0" cy="-110" r="105" fill="#b62a2a" stroke="#4a0c0c" stroke-width="7"/>'
          f'<circle cx="0" cy="-110" r="84" fill="{face}" stroke="#4a0c0c" stroke-width="4"/>')
    for k in range(12):
        a = math.radians(k * 30)
        g += (f'<line x1="{math.sin(a) * 68:.1f}" y1="{-110 - math.cos(a) * 68:.1f}" x2="{math.sin(a) * 78:.1f}" '
              f'y2="{-110 - math.cos(a) * 78:.1f}" stroke="#222" stroke-width="{6 if k % 3 == 0 else 3}"/>')

    def hand(ang, ln, wdt, col):
        a = math.radians(ang)
        return f'<line x1="0" y1="-110" x2="{math.sin(a) * ln:.1f}" y2="{-110 - math.cos(a) * ln:.1f}" stroke="{col}" stroke-width="{wdt}" stroke-linecap="round"/>'
    g += hand(hour, 44, 9, "#222") + hand(minute, 64, 6, "#222") + hand(alarm_ang, 58, 4, "#d02020")
    g += '<circle cx="0" cy="-110" r="8" fill="#222"/>'
    g += '<path d="M -50,-160 A 70 70 0 0 1 20,-176" stroke="#ffffff" stroke-width="7" fill="none" stroke-opacity="0.6"/>'
    if ring > 0.05:                                               # ring lines
        for side in (-1, 1):
            for k in range(3):
                r = 140 + k * 30 + (t * 120 % 30)
                g += (f'<path d="M {side * r * 0.75:.0f},{-250 + k * 6} q {side * 18},-20 {side * 6},-44" stroke="#f2c230" '
                      f'stroke-width="8" fill="none" stroke-linecap="round" stroke-opacity="{ring * (1 - k * 0.25):.2f}"/>')
    return g + "</g>"


def blur_bg(base, path, k=16, mult=(1, 1, 1)):
    img = Image.open(base / path).convert("RGB").resize((W, H), Image.LANCZOS)
    a = cv2.GaussianBlur(np.array(img), (0, 0), k).astype(np.float32) * np.array(mult, np.float32)
    return np.clip(a, 0, 255).astype(np.uint8)


def stool_top(cx, y, w):
    return (f'<rect x="{cx - w / 2}" y="{y}" width="{w}" height="60" rx="10" fill="#9a6a3a" stroke="#4a2a10" stroke-width="6"/>'
            f'<rect x="{cx - w / 2 + 30}" y="{y + 60}" width="40" height="{H - y}" fill="#7a4e26" stroke="#4a2a10" stroke-width="6"/>'
            f'<rect x="{cx + w / 2 - 70}" y="{y + 60}" width="40" height="{H - y}" fill="#7a4e26" stroke="#4a2a10" stroke-width="6"/>')


def phone_flat(x, y, s=1.0):
    return (f'<g transform="translate({x} {y}) scale({s})"><path d="M -150,0 L 150,0 L 128,-44 L -128,-44 Z" fill="#2a2f36" stroke="#0d0f12" stroke-width="6"/>'
            f'<rect x="-100" y="-38" width="60" height="22" rx="6" fill="#15181c"/></g>')


class Close:
    def __init__(self, cfg, base):
        self.cfg = cfg
        mode = cfg["mode"]
        self.bg = blur_bg(base, cfg["bg"], 14, (0.4, 0.46, 0.75) if mode == "set" else (1.0, 0.97, 0.9))
        self.arm = None
        if cfg.get("arm"):
            a = Image.open(base / cfg["arm"]).convert("RGBA")
            sc = 1100 / a.height
            self.arm = a.resize((round(a.width * sc), 1100), Image.LANCZOS).rotate(-14, expand=True, resample=Image.BICUBIC)

    def frame(self, t):
        cfg = self.cfg
        mode = cfg["mode"]
        body = stool_top(540, 1430, 900)
        if mode == "set":
            u = ease((t - 0.3) / 1.6)
            body += clock(470, 1440, 2.2, t, 0, 300 + 60 * u, night=True)
            ph = ease((t - cfg.get("phone", 2.4)) / 0.6)
            if ph > 0:
                body += phone_flat(1200 - 380 * ph, 1436, 1.0)
            body += f'<rect width="{W}" height="{H}" fill="#000814" fill-opacity="0.18"/>'
        else:
            press = cfg.get("press", 2.0)
            ring = 1.0 if t < press else 0.0
            ring *= min(1, t / 0.15)
            body += clock(560, 1440, 2.2, t, ring, 360)
        out = over(self.bg, svg_rgba(body))
        if self.arm is not None:                                  # the arm comes down from the blanket and presses
            press = cfg.get("press", 2.0)
            d = ease((t - (press - 1.0)) / 1.0) - ease((t - (press + 0.5)) / 0.8)
            ax = 190
            ay = -self.arm.height + 220 + 760 * d
            lay = Image.new("RGBA", (W, H))
            lay.alpha_composite(self.arm, (ax, int(ay)))
            out = over(out, np.array(lay))
            out = over(out, svg_rgba('<path d="M -40,-40 L 720,-40 L 700,90 Q 400,150 120,110 L -40,140 Z" fill="#9b2c3c" stroke="#4d1018" stroke-width="8"/>'
                                     '<path d="M 60,-40 L 40,130 M 200,-40 L 190,140 M 340,-40 L 340,140 M 480,-40 L 490,130 M 620,-40 L 640,100" '
                                     'stroke="#e8d7b0" stroke-width="14" opacity="0.8"/>'))
        return cv2.cvtColor(out, cv2.COLOR_RGB2BGR)


class Rooster:
    def __init__(self, cfg, base):
        self.cfg = cfg
        self.bg = blur_bg(base, cfg["bg"], 10, (1.04, 0.86, 0.76))
        self.rooster = rooster

    def frame(self, t):
        crow = 0.0
        for c in self.cfg.get("crow", [0.6]):
            if c <= t <= c + 1.3:
                crow = max(crow, math.sin(math.pi * (t - c) / 1.3))
        body = (''.join(f'<rect x="{px}" y="1120" width="70" height="820" fill="#7a4e26" stroke="#3d2410" stroke-width="8"/>' for px in (150, 860))
                + f'<rect x="-20" y="1130" width="1120" height="70" rx="12" fill="#9a6a3a" stroke="#3d2410" stroke-width="8"/>'
                f'<rect x="-20" y="1420" width="1120" height="60" rx="12" fill="#9a6a3a" stroke="#3d2410" stroke-width="8"/>'
                f'<circle cx="840" cy="420" r="{90 + 10 * math.sin(t)}" fill="#ffe08a" fill-opacity="0.85"/>'
                + self.rooster(560, 1140, 4.2, crow))
        return cv2.cvtColor(over(self.bg, svg_rgba(body)), cv2.COLOR_RGB2BGR)


class Far:
    def __init__(self, cfg, base):
        self.cfg = cfg
        img = Image.open(base / cfg["frame"]).convert("RGB").resize((W, H), Image.LANCZOS)
        self.img = np.array(img)

    def frame(self, t):
        x, y, s = self.cfg.get("clock", [880, 1040, 0.28])
        bounce = abs(math.sin(t * 3)) * 6 if t < 1.0 else 0
        return cv2.cvtColor(over(self.img, svg_rgba(clock(x, y - bounce, s, t, 0, 360))), cv2.COLOR_RGB2BGR)


def main():
    out = sys.argv[1]
    cfg_path = Path(sys.argv[2])
    cfg = json.loads(cfg_path.read_text())
    base = cfg_path.parent
    fps = cfg.get("fps", 25)
    n = round(cfg["duration"] * fps)
    mode = cfg["mode"]
    sc = {"sleep": Sleep, "set": Close, "ring": Close, "rooster": Rooster, "far": Far}[mode](cfg, base)
    still = cfg.get("still")
    ff = None if still is not None else subprocess.Popen(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
         "-framerate", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i in ([0] if still is not None else range(n)):
        t = still if still is not None else i / fps
        img = sc.frame(t)
        if still is not None:
            cv2.imwrite(out, img)
        else:
            ff.stdin.write(img.tobytes())
    if ff:
        ff.stdin.close()
        ff.wait()
    print("saved", out)


if __name__ == "__main__":
    main()
