"""Onions (vengayam) – a cut half, a whole bulb, a knife – and the Ep 3 cut-aways. 1080x1920.

Usage:
    python tools/toon/onion.py OUT.mp4 TIMING.json

TIMING.json: {"mode": "chop" | "cells" | "board", "duration": 4, "fps": 25, "span": [t0, t1], "camera": [[t, cy, h], ...]}
chop:  close-up on a chopping board: the knife slices the onion half, slices fall over, a faint vapour rises.
cells: inside the onion: each cell keeps two things apart (sulphur compounds, purple; an enzyme in the vacuole, yellow).
       The knife breaks a row of cells, the two mix and a gas forms and drifts up (drawn as faint wisps, no label).
board: the cut onion resting on the chopping board, a gentle push-in (the ending).
Science (Imai et al., Nature 2002 "An onion enzyme that makes the eyes water"; Block, "Garlic and Other Alliums", RSC):
cutting breaks the cells, the enzyme alliinase meets the sulphur amino-acid compounds (S-alk(en)yl cysteine sulphoxides)
and makes sulphenic acids; lachrymatory-factor synthase turns them into syn-propanethial-S-oxide, a volatile gas that
reaches the eyes, stimulates the nerves of the cornea and so the tear glands.
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import cairosvg
import numpy as np

W, H = 1080, 1920
OUT = "#3b1f2b"
SKIN_O, SKIN_I = "#8e2f5a", "#b8487a"        # red onion skin (outer, inner)
FLESH, RING = "#f7e6ee", "#d9a7c0"


def ease(u):
    u = min(max(u, 0), 1)
    return u * u * (3 - 2 * u)


def onion_half(x, y, r, ang=0.0):
    """A red onion cut across: the cut face (concentric rings) towards the viewer, a little skin showing round it."""
    rings = "".join(f'<ellipse cx="0" cy="{r * 0.02 * k:.1f}" rx="{r * (0.9 - k * 0.11):.1f}" ry="{r * (0.84 - k * 0.1):.1f}" '
                    f'fill="none" stroke="{RING}" stroke-width="{max(1.5, r * 0.035):.1f}"/>' for k in range(1, 8))
    return (f'<g transform="translate({x:.1f} {y:.1f}) rotate({ang:.1f})">'
            f'<ellipse cx="0" cy="{r * 0.1:.1f}" rx="{r * 1.02:.1f}" ry="{r * 0.98:.1f}" fill="{SKIN_O}" stroke="{OUT}" stroke-width="{r * 0.06:.1f}"/>'
            f'<ellipse cx="0" cy="0" rx="{r * 0.95:.1f}" ry="{r * 0.9:.1f}" fill="{FLESH}" stroke="{SKIN_I}" stroke-width="{r * 0.07:.1f}"/>'
            f'{rings}<ellipse cx="0" cy="{r * 0.1:.1f}" rx="{r * 0.1:.1f}" ry="{r * 0.08:.1f}" fill="{RING}"/></g>')


def knife(x, y, s=1.0, ang=0.0):
    """Small kitchen knife: wooden handle at (x, y) going down, steel blade up."""
    return (f'<g transform="translate({x:.1f} {y:.1f}) rotate({ang:.1f}) scale({s:.2f})">'
            f'<path d="M -9,-10 L -9,-150 Q -9,-178 12,-190 L 12,-10 Z" fill="#cfd6dc" stroke="#2c3238" stroke-width="5" stroke-linejoin="round"/>'
            f'<line x1="-3" y1="-20" x2="-3" y2="-150" stroke="#f4f7f9" stroke-width="4"/>'
            f'<rect x="-13" y="-12" width="28" height="80" rx="9" fill="#7a4a24" stroke="#2c1a0c" stroke-width="5"/>'
            f'<circle cx="1" cy="10" r="4" fill="#d9c08a"/><circle cx="1" cy="45" r="4" fill="#d9c08a"/></g>')


def board_bg():
    return (f'<rect width="{W}" height="{H}" fill="#e9c9a0"/>'
            f'<rect y="1180" width="{W}" height="{H - 1180}" fill="#9a6235"/>'
            '<ellipse cx="540" cy="1420" rx="470" ry="70" fill="#3b2416" fill-opacity="0.25"/>'
            '<rect x="90" y="1200" width="900" height="210" rx="40" fill="#d8a565" stroke="#5a3418" stroke-width="8"/>'
            '<path d="M 140,1250 L 940,1250 M 160,1300 L 920,1300 M 140,1350 L 940,1350" stroke="#c48f50" stroke-width="5"/>')


def wisps(cx, cy, t, amount, spread=160, n=10, rise=520, col="#ffffff"):
    out = []
    for k in range(n):
        ph = (t * 0.5 + k / n) % 1
        x0 = cx + ((k * 61) % (2 * spread)) - spread + 20 * math.sin(t * 2 + k)
        y0 = cy - ph * rise
        op = 0.75 * amount * (1 - ph) * min(1, ph * 4)
        out.append(f'<path d="M {x0:.0f},{y0:.0f} q 16,-24 0,-48 q -16,-24 0,-48" stroke="{col}" stroke-width="8" '
                   f'fill="none" stroke-linecap="round" stroke-opacity="{op:.2f}"/>')
    return out


def scene(t, cfg):
    mode, span = cfg["mode"], cfg["span"]
    p = ease((t - span[0]) / (span[1] - span[0]))
    g = []
    if mode == "chop":
        g.append(board_bg())
        n_cut = int(p * 5)
        u = (p * 5) % 1                                       # knife stroke within the current slice
        # slices already cut lie to the right
        for k in range(n_cut):
            g.append(f'<g transform="translate({650 + k * 48} 1260) rotate({18 + k * 4})">'
                     f'<rect x="-14" y="-95" width="28" height="190" rx="12" fill="{FLESH}" stroke="{SKIN_O}" stroke-width="9"/>'
                     f'<line x1="0" y1="-80" x2="0" y2="80" stroke="{RING}" stroke-width="4"/></g>')
        g.append(f'<g>{onion_half(470, 1200, 190)}</g>')
        ky = 860 + 330 * math.sin(math.pi * u) if p < 1 else 860
        g.append(f'<g transform="translate({600 + n_cut * 4} {ky:.0f})">'
                 f'<path d="M -12,0 L -12,330 L 10,360 L 10,0 Z" fill="#cfd6dc" stroke="#2c3238" stroke-width="6"/>'
                 f'<rect x="-20" y="-130" width="38" height="135" rx="12" fill="#7a4a24" stroke="#2c1a0c" stroke-width="6"/></g>')
        g += wisps(520, 1080, t, min(1.0, p * 3) * 0.8, spread=170)
    elif mode == "cells":
        g.append('<rect width="1080" height="1920" fill="#f3dbe6"/>')
        cut_x = -100 + 1300 * ease((t - span[0]) / 1.2)       # the knife sweeps across first
        rows, cols = 7, 5
        for i in range(rows):
            for j in range(cols):
                x0, y0 = 70 + j * 190, 420 + i * 160
                broken = abs(i - 3) <= 1 and cut_x > x0 + 95
                mixing = ease((t - span[0] - 0.9 - j * 0.12) / 1.0) if broken else 0.0
                g.append(f'<rect x="{x0}" y="{y0}" width="180" height="150" rx="16" fill="#fbf1f6" '
                         f'stroke="#b56b90" stroke-width="{4 if not broken else 3}" '
                         f'stroke-dasharray="{"14 10" if broken else "none"}"/>')
                rng = np.random.default_rng(i * 10 + j)
                for k in range(6):                            # purple: sulphur compounds (cytoplasm)
                    ax, ay = x0 + 25 + rng.uniform(0, 40), y0 + 25 + rng.uniform(0, 100)
                    bx, by = x0 + 90 + rng.uniform(-10, 10), y0 + 75 + rng.uniform(-10, 10)
                    g.append(f'<circle cx="{ax + (bx - ax) * mixing:.0f}" cy="{ay + (by - ay) * mixing:.0f}" r="9" fill="#7b3fa0"/>')
                for k in range(5):                            # yellow: the enzyme, kept in the vacuole
                    ax, ay = x0 + 115 + rng.uniform(0, 40), y0 + 25 + rng.uniform(0, 100)
                    bx, by = x0 + 90 + rng.uniform(-10, 10), y0 + 75 + rng.uniform(-10, 10)
                    g.append(f'<circle cx="{ax + (bx - ax) * mixing:.0f}" cy="{ay + (by - ay) * mixing:.0f}" r="8" fill="#e8b923"/>')
                if not broken:
                    g.append(f'<line x1="{x0 + 100}" y1="{y0 + 15}" x2="{x0 + 100}" y2="{y0 + 135}" stroke="#d9a7c0" stroke-width="4"/>')
                if mixing > 0.6:
                    g += wisps(x0 + 90, y0 + 40, t + j, min(1.0, (mixing - 0.6) * 2.5), spread=45, n=4, rise=340, col="#b9c93a")
        g.append(f'<line x1="{cut_x:.0f}" y1="895" x2="{cut_x - 60:.0f}" y2="905" stroke="#2c3238" stroke-width="6"/>')
        if 0 < cut_x < 1080:
            g.append(f'<g transform="translate({cut_x:.0f} 900) rotate(-90) scale(1.8)"><path d="M -14,0 L -14,260 L 12,290 L 12,0 Z" '
                     f'fill="#cfd6dc" stroke="#2c3238" stroke-width="6"/><rect x="-20" y="-120" width="38" height="125" rx="12" '
                     f'fill="#7a4a24" stroke="#2c1a0c" stroke-width="6"/></g>')
    else:  # board
        g.append(board_bg())
        g.append(onion_half(420, 1190, 180))
        g.append(f'<g transform="translate(720 1230)"><ellipse cx="0" cy="0" rx="120" ry="110" fill="{SKIN_O}" stroke="{OUT}" stroke-width="8"/>'
                 f'<path d="M -20,-100 Q 0,-170 30,-200 Q 10,-150 20,-100 Z" fill="#c97a4a" stroke="{OUT}" stroke-width="6"/>'
                 f'<path d="M -80,-40 Q -60,40 -10,90 M 60,-60 Q 70,20 30,90" stroke="#6d1f42" stroke-width="5" fill="none"/></g>')
        g.append(knife(860, 1300, 1.2, 70))
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
