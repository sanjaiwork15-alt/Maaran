"""Opened groundnut pods: immature vs mature (Groundnut Ep 7 – when to harvest). 1080x1920.

Usage:
    python tools/toon/pods.py OUT.mp4 TIMING.json

TIMING.json: {"duration": 6.0, "fps": 25, "open": [t0, t1], "compare": [t0, t1], "camera": [[t, cy, h], ...]}
Two pods lie on red soil. They split open along the seam ("open"). Then the mature one is highlighted ("compare").
Botany (TNAU maturity sign): in a MATURE pod the inside of the shell has turned dark brown/black with dark veins and
the kernels are plump with a pink-red seed coat; in an IMMATURE pod the inner shell is still white and the kernels are
small, pale and wrinkled. The shell outside is netted and light brown in both.
"""
import json
import subprocess
import sys
from pathlib import Path

import cairosvg
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cutaway import OUT, ease, phase  # noqa: E402

W, H = 1080, 1920
BODY = "M -150,0 C -150,-78 -60,-86 -22,-48 C 4,-86 150,-92 160,0 C 150,92 4,86 -22,48 C -60,86 -150,78 -150,0 Z"


def bg():
    rng = np.random.default_rng(2)
    g = [f'<rect width="{W}" height="{H}" fill="#b9562a"/>']
    for _ in range(500):
        r = rng.uniform(3, 14)
        g.append(f'<ellipse cx="{rng.uniform(0, W):.0f}" cy="{rng.uniform(0, H):.0f}" rx="{r:.1f}" ry="{r * 0.65:.1f}" '
                 f'fill="{"#d27440" if rng.random() < 0.55 else "#9a4320"}" fill-opacity="0.8"/>')
    return "".join(g)


def half(mature, top, k):
    """One opened half-shell (top or bottom) with kernels; k = how far it has swung open (0..1)."""
    inner = "#3b2416" if mature else "#f4efe2"
    vein = "#1d120a" if mature else "#e2d9c3"
    kern, kern_hi = (("#c44b45", "#e88c84") if mature else ("#efe3cf", "#fff8ec"))
    ks = 1.0 if mature else 0.62
    sign = -1 if top else 1
    clip = f'<clipPath id="c{int(mature)}{int(top)}"><rect x="-200" y="{-200 if top else 0}" width="400" height="200"/></clipPath>'
    shell = (f'<g clip-path="url(#c{int(mature)}{int(top)})"><path d="{BODY}" fill="#d8b27a" stroke="{OUT}" stroke-width="7"/>'
             f'<path d="{BODY}" transform="scale(0.88)" fill="{inner}"/>')
    for x in (-110, -60, 40, 100):
        shell += f'<path d="M {x},{sign * 8} C {x + 10},{sign * 40} {x - 6},{sign * 58} {x + 4},{sign * 70}" stroke="{vein}" stroke-width="5" fill="none"/>'
    shell += "</g>"
    kernels = ""
    if not top:
        for cx in (-82, 78):
            rx, ry = 52 * ks, 40 * ks
            wr = "" if mature else (f'<path d="M {cx - rx * 0.6},{-4} q {rx * 0.3},10 {rx * 0.6},0 q {rx * 0.3},-10 {rx * 0.6},0" '
                                   f'stroke="#c9b89a" stroke-width="4" fill="none"/>')
            kernels += (f'<ellipse cx="{cx}" cy="0" rx="{rx:.0f}" ry="{ry:.0f}" fill="{kern}" stroke="{OUT}" stroke-width="5"/>'
                        f'<ellipse cx="{cx - rx * 0.3:.0f}" cy="{-ry * 0.35:.0f}" rx="{rx * 0.35:.0f}" ry="{ry * 0.2:.0f}" fill="{kern_hi}"/>{wr}')
    dy = sign * 70 * k
    rot = sign * -12 * k
    return f'<defs>{clip}</defs><g transform="translate(0 {dy:.1f}) rotate({rot:.1f})">{shell}{kernels}</g>'


def pod(cx, cy, mature, k, glow):
    g = [f'<g transform="translate({cx} {cy}) scale(1.6)">']
    if glow > 0:
        g.append(f'<ellipse cx="0" cy="0" rx="250" ry="210" fill="#ffe27a" fill-opacity="{0.45 * glow:.3f}"/>')
    g.append(half(mature, False, k) + half(mature, True, k))
    closed = 1 - min(1.0, k * 4)            # the closed, netted outer shell until it starts to split
    if closed > 0:
        net = "".join(f'<path d="M {x},-70 C {x + 12},-25 {x + 12},25 {x},70" stroke="#a9834d" stroke-width="5" fill="none"/>'
                      for x in (-110, -70, 30, 75, 120))
        net += ('<path d="M -145,-18 C -60,-8 60,-8 155,-18 M -145,20 C -60,30 60,30 155,20" '
                'stroke="#a9834d" stroke-width="5" fill="none"/>')
        g.append(f'<g opacity="{closed:.3f}"><path d="{BODY}" fill="#e3c28a" stroke="{OUT}" stroke-width="7"/>{net}</g>')
    g.append("</g>")
    return "".join(g)


def main():
    out, cfg = sys.argv[1], json.loads(Path(sys.argv[2]).read_text())
    back = bg()
    fps = cfg.get("fps", 25)
    n = round(cfg["duration"] * fps)
    cams = cfg["camera"]
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "image2pipe", "-framerate", str(fps), "-i", "-",
                           "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i in range(n):
        t = i / fps
        k = phase(t, cfg["open"])
        c = phase(t, cfg["compare"])
        cy = np.interp(t, [p[0] for p in cams], [p[1] for p in cams])
        h = np.interp(t, [p[0] for p in cams], [p[2] for p in cams])
        w = h * W / H
        parts = [back, pod(540, 640, False, k, 0), pod(540, 1260, True, k, ease(c))]
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
               f'viewBox="{W / 2 - w / 2:.1f} {cy - h / 2:.1f} {w:.1f} {h:.1f}">{"".join(parts)}</svg>')
        ff.stdin.write(cairosvg.svg2png(bytestring=svg.encode()))
    ff.stdin.close()
    ff.wait()
    print("saved", out)


if __name__ == "__main__":
    main()
