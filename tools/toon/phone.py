"""Smartphone screen cut-aways (Maaran Thatha – Day 1): his phone seen up close, short funny reels, swipes, lock. 1080x1920.

Usage:
    python tools/toon/phone.py OUT.mp4 TIMING.json
TIMING.json: {"mode": "feed" | "lock", "duration": 4, "bg": "frames/plate.png" (blurred behind the phone; default 07_home), "fps": 25, "reels": ["cat", "cricket", "dosa", "dog"],
              "each": 1.2, "start": 0}
feed: the phone fills most of the frame (courtyard blurred behind), one reel after another, each swiped up after
      "each" seconds (a quick 0.25 s slide); right-side icons (heart, comment, share) and a progress bar – icons only,
      no text (the channel's no-on-screen-text rule).
lock: a reel plays, then the screen goes dark: a padlock appears and fades, leaving his dark screen.
Reels (all simple cartoon loops): cat – a cat in sunglasses dancing; cricket – a ball hit for six over the palms;
dosa – a dosa flipping on a tawa; dog – a puppy chasing its own tail.
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
ROOT = Path(__file__).resolve().parents[2]
PX, PY, PW, PH = 150, 170, 780, 1580          # phone body
SX, SY, SW, SH = 178, 230, 724, 1460          # screen


def svg_png(body, w=W, h=H):
    png = cairosvg.svg2png(bytestring=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">{body}</svg>'.encode())
    return np.array(Image.open(io.BytesIO(png)).convert("RGBA"))


# ---------------------------------------------------------------- reels (drawn in screen coords 0..SW x 0..SH)

def note(x, y, c="#e0457b"):
    """A drawn eighth note (no font needed)."""
    return (f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="22" ry="16" fill="{c}" transform="rotate(-20 {x:.0f} {y:.0f})"/>'
            f'<line x1="{x + 19:.0f}" y1="{y - 4:.0f}" x2="{x + 19:.0f}" y2="{y - 80:.0f}" stroke="{c}" stroke-width="7"/>'
            f'<path d="M {x + 19:.0f},{y - 80:.0f} q 30,15 26,48" stroke="{c}" stroke-width="7" fill="none"/>')


def reel_cat(u):
    b = abs(math.sin(u * 7)) * 40
    sw = math.sin(u * 7) * 12
    return (f'<rect width="{SW}" height="{SH}" fill="#ffd36b"/>'
            f'<circle cx="{SW * 0.2}" cy="{SH * 0.18}" r="70" fill="#ffe9a8"/>'
            f'<g transform="translate({SW / 2} {SH * 0.62 - b}) rotate({sw})">'
            f'<ellipse cx="0" cy="120" rx="150" ry="190" fill="#f28c38" stroke="#5a2d0c" stroke-width="8"/>'
            f'<circle cx="0" cy="-130" r="135" fill="#f28c38" stroke="#5a2d0c" stroke-width="8"/>'
            f'<path d="M -120,-200 L -90,-300 L -40,-230 Z M 120,-200 L 90,-300 L 40,-230 Z" fill="#f28c38" stroke="#5a2d0c" stroke-width="8"/>'
            f'<rect x="-110" y="-175" width="95" height="55" rx="18" fill="#111"/><rect x="15" y="-175" width="95" height="55" rx="18" fill="#111"/>'
            f'<line x1="-15" y1="-150" x2="15" y2="-150" stroke="#111" stroke-width="10"/>'
            f'<path d="M -45,-70 Q 0,-30 45,-70" stroke="#5a2d0c" stroke-width="9" fill="none" stroke-linecap="round"/>'
            f'<path d="M -150,60 L {-260 - sw * 4},{-60 - sw * 6}" stroke="#f28c38" stroke-width="46" stroke-linecap="round"/>'
            f'<path d="M 150,60 L {260 - sw * 4},{-60 + sw * 6}" stroke="#f28c38" stroke-width="46" stroke-linecap="round"/>'
            f'</g>'
            + "".join(note(SW * (0.15 + 0.7 * ((k * 0.37 + u * 0.3) % 1)), SH * (0.1 + 0.12 * k)) for k in range(3)))


def reel_cricket(u):
    p = (u * 0.9) % 1
    bx, by = SW * 0.25 + p * SW * 0.9, SH * 0.72 - math.sin(p * math.pi) * SH * 0.55
    return (f'<rect width="{SW}" height="{SH * 0.6}" fill="#7ec8f0"/><rect y="{SH * 0.6}" width="{SW}" height="{SH * 0.4}" fill="#5aa845"/>'
            f'<ellipse cx="{SW / 2}" cy="{SH * 0.82}" rx="{SW * 0.18}" ry="40" fill="#c9b27a"/>'
            + "".join(f'<g transform="translate({x} {SH * 0.6})"><rect x="-8" y="-260" width="16" height="260" fill="#8a5a2b"/>'
                      f'<path d="M 0,-260 q -90,10 -130,60 M 0,-260 q 90,10 130,60 M 0,-260 q -40,-60 -110,-70 M 0,-260 q 40,-60 110,-70" '
                      f'stroke="#2f7a2f" stroke-width="26" fill="none" stroke-linecap="round"/></g>' for x in (90, 620)) +
            f'<rect x="{SW * 0.2}" y="{SH * 0.62}" width="26" height="170" fill="#e9d3a0" transform="rotate({-50 + p * 60} {SW * 0.2 + 13} {SH * 0.78})"/>'
            f'<circle cx="{bx:.0f}" cy="{by:.0f}" r="26" fill="#c0262d" stroke="#fff" stroke-width="4"/>'
            + "".join(f'<circle cx="{bx - (k + 1) * 30:.0f}" cy="{by + (k + 1) * 12 * math.cos(p * math.pi):.0f}" r="{16 - k * 4}" '
                      f'fill="#ffffff" fill-opacity="{0.5 - k * 0.15:.2f}"/>' for k in range(3)))


def reel_dosa(u):
    p = (u * 1.1) % 1
    lift = math.sin(p * math.pi) * 330
    ang = p * 360
    sq = abs(math.cos(math.radians(ang)))
    return (f'<rect width="{SW}" height="{SH}" fill="#3b2a24"/>'
            f'<ellipse cx="{SW / 2}" cy="{SH * 0.7}" rx="300" ry="90" fill="#222" stroke="#555" stroke-width="10"/>'
            f'<rect x="{SW / 2 + 280}" y="{SH * 0.7 - 20}" width="220" height="40" rx="18" fill="#6b3d1f"/>'
            f'<ellipse cx="{SW / 2}" cy="{SH * 0.7 - 10 - lift:.0f}" rx="250" ry="{max(8, 70 * sq):.0f}" '
            f'fill="{"#e8b35a" if math.cos(math.radians(ang)) > 0 else "#c98a35"}" stroke="#9b6424" stroke-width="6"/>'
            + "".join(f'<path d="M {SW / 2 - 120 + k * 120},{SH * 0.6} q 20,-40 0,-80 q -20,-40 0,-80" stroke="#ffffff" '
                      f'stroke-opacity="0.45" stroke-width="10" fill="none"/>' for k in range(3)))


def reel_dog(u):
    a = u * 540
    return (f'<rect width="{SW}" height="{SH}" fill="#b7e39a"/>'
            f'<g transform="translate({SW / 2} {SH * 0.55}) rotate({a:.0f})"><g transform="translate(0 -150)">'
            f'<ellipse cx="0" cy="0" rx="150" ry="85" fill="#ffffff" stroke="#3a2a1a" stroke-width="8"/>'
            f'<circle cx="150" cy="-40" r="70" fill="#ffffff" stroke="#3a2a1a" stroke-width="8"/>'
            f'<ellipse cx="160" cy="-100" rx="22" ry="45" fill="#6b4a2a"/><circle cx="175" cy="-50" r="10" fill="#111"/>'
            f'<circle cx="215" cy="-30" r="14" fill="#111"/>'
            f'<path d="M -150,-10 q -80,-60 -60,-140" stroke="#ffffff" stroke-width="26" fill="none" stroke-linecap="round"/>'
            f'<path d="M -150,-10 q -80,-60 -60,-140" stroke="#3a2a1a" stroke-width="5" fill="none" stroke-linecap="round" stroke-dasharray="1 0"/>'
            + "".join(f'<rect x="{x}" y="60" width="26" height="{70 + 15 * math.sin(u * 30 + x)}" rx="10" fill="#ffffff" stroke="#3a2a1a" stroke-width="6"/>'
                      for x in (-110, -50, 50, 110)) + '</g></g>')


REELS = {"cat": reel_cat, "cricket": reel_cricket, "dosa": reel_dosa, "dog": reel_dog}


def ui(u, liked):
    """Right-side icons and a progress bar – no text."""
    x = SW - 90
    heart = "#ff3b5c" if liked else "#ffffff"
    s = (f'<path d="M {x},{SH * 0.58} c -40,-40 -90,-5 -60,35 l 60,55 l 60,-55 c 30,-40 -20,-75 -60,-35 Z" fill="{heart}" '
         f'stroke="#222" stroke-width="3" fill-opacity="0.95"/>'
         f'<path d="M {x - 50},{SH * 0.66} h 100 v 70 h -60 l -25,25 v -25 h -15 Z" fill="#ffffff" stroke="#222" stroke-width="3"/>'
         f'<path d="M {x - 45},{SH * 0.76 + 60} l 90,-45 l -90,-45 l 15,45 Z" fill="#ffffff" stroke="#222" stroke-width="3"/>'
         f'<circle cx="80" cy="{SH - 170}" r="42" fill="#ffffff" stroke="#222" stroke-width="3"/>'
         f'<circle cx="80" cy="{SH - 182}" r="15" fill="#8a8a8a"/><path d="M 52,{SH - 145} q 28,-30 56,0" fill="#8a8a8a"/>'
         f'<rect x="0" y="{SH - 12}" width="{SW}" height="12" fill="#ffffff" fill-opacity="0.35"/>'
         f'<rect x="0" y="{SH - 12}" width="{SW * u:.0f}" height="12" fill="#ffffff"/>')
    return s


def screen(t, cfg):
    """Screen content at time t (SW x SH SVG body)."""
    reels, each = cfg.get("reels", ["cat", "cricket", "dosa", "dog"]), cfg.get("each", 1.2)
    k = int(t // each)
    local = t - k * each
    body = ""
    swipe = 0.25
    for j, off in ((k, 0.0), (k + 1, 1.0)):
        name = reels[j % len(reels)]
        if j == k + 1 and local < each - swipe:
            continue
        slide = 0.0
        if local > each - swipe:
            q = (local - (each - swipe)) / swipe
            slide = -(q * q * (3 - 2 * q)) * SH
        y = slide + off * SH
        lt = local if j == k else local - each
        body += (f'<g transform="translate(0 {y:.0f})"><svg width="{SW}" height="{SH}">{REELS[name](t + j * 1.7)}'
                 f'{ui(min(1, max(0, lt / each)), (j % 2) == 0 and lt > 0.5)}</svg></g>')
    return body


def phone_frame(body, bg, t, cfg, dark=0.0, lock=0.0):
    sway = math.sin(t * 1.3) * 6, math.sin(t * 0.9 + 1) * 5                    # held in hand: a little drift
    ang = math.sin(t * 0.7) * 0.8
    g = (f'<g transform="translate({sway[0]:.1f} {sway[1]:.1f}) rotate({ang:.2f} {W / 2} {H / 2})">'
         f'<rect x="{PX}" y="{PY}" width="{PW}" height="{PH}" rx="70" fill="#15181c" stroke="#000" stroke-width="6"/>'
         f'<svg x="{SX}" y="{SY}" width="{SW}" height="{SH}"><rect width="{SW}" height="{SH}" rx="36" fill="#000"/>{body}'
         f'<rect width="{SW}" height="{SH}" fill="#000" fill-opacity="{dark:.2f}"/>'
         + (f'<g transform="translate({SW / 2} {SH * 0.45})" opacity="{lock:.2f}"><rect x="-55" y="-10" width="110" height="90" rx="14" fill="#e8e8e8"/>'
            f'<path d="M -35,-10 v -30 a 35,35 0 0 1 70,0 v 30" stroke="#e8e8e8" stroke-width="16" fill="none"/></g>' if lock > 0 else "")
         + f'</svg><rect x="{W / 2 - 60}" y="{PY + 22}" width="120" height="22" rx="11" fill="#000"/>'
         f'<path d="M {SX + 20},{SY + 20} l 140,0 l -140,300 Z" fill="#ffffff" fill-opacity="0.05"/></g>')
    fg = svg_png(g)
    a = fg[..., 3:4].astype(np.float32) / 255
    return (bg * (1 - a) + fg[..., :3] * a).astype(np.uint8)


def main():
    out = sys.argv[1]
    cfg = json.loads(Path(sys.argv[2]).read_text())
    fps = cfg.get("fps", 25)
    n = round(cfg["duration"] * fps)
    plate = Image.open(Path(sys.argv[2]).parent / cfg["bg"] if cfg.get("bg") else ROOT / "assets/2d/source/07_home.png").convert("RGB").resize((W, H), Image.LANCZOS)
    bg = cv2.GaussianBlur(np.array(plate), (0, 0), 18).astype(np.float32) * 0.6
    ff = subprocess.Popen(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-framerate", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "17",
                           "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    still = cfg.get("still")
    for i in ([0] if still is not None else range(n)):
        t = still if still is not None else i / fps
        t0 = t + cfg.get("start", 0)
        dark = lock = 0.0
        if cfg["mode"] == "lock":
            off = cfg.get("off", cfg["duration"] * 0.5)
            q = min(1, max(0, (t - off) / 0.2))
            dark = 0.97 * q
            lock = min(1, max(0, (t - off) / 0.25)) * min(1, max(0, (off + 1.2 - t) / 0.4))
            t0 = min(t0, off + cfg.get("start", 0))                              # the reel freezes as it locks
        frame = phone_frame(screen(t0, cfg), bg, t, cfg, dark, lock)
        if still is not None:
            Image.fromarray(frame).save(out.replace(".mp4", ".png"))
            ff.stdin.close()
            ff.kill()
            print("saved", out.replace(".mp4", ".png"))
            return
        ff.stdin.write(frame.tobytes())
    ff.stdin.close()
    ff.wait()
    print("saved", out)


if __name__ == "__main__":
    main()
