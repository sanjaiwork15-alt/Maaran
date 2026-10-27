"""Window 4B Ep 2 renderer: "100 Years on the Same Street, But One Window Never Changes".

    python window4b/tools/w4b_ep02.py MASKS_h.npz OUT.mp4 [--still T ...] [--jobs 4]

Same locked 16:9 master and engine as Ep 1 (w4b_render.setup). The city is rebuilt in code over
100 years: an old brick building with one warm window on the far bank, the shop next to it that
closes, glass towers rising in stages behind and in front of the old skyline, an elevated metro,
automated pods, a demolition machine that spares the old building, colossal towers, a billboard,
and a fast day/night cycle. All positions are in master pixels (1672 x 941).
"""
import argparse
import math
import os
import subprocess
import sys
import tempfile
from multiprocessing import Pool
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
import w4b_render as R  # noqa: E402

G = R.G
FPS = 24
DURATION = 180.0
FONT = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
OUTLINE = (0.14, 0.13, 0.15)
AA = cv2.LINE_AA

SCENES = [  # start, counter
    (0, "YEAR 0  |  2026"), (15, "10 YEARS LATER  |  2036"), (35, "25 YEARS LATER  |  2051"),
    (58, "40 YEARS LATER  |  2066"), (80, "60 YEARS LATER  |  2086"), (105, "80 YEARS LATER  |  2106"),
    (128, "100 YEARS LATER  |  2126"), (155, None),
]
FINAL_LINES = [(157.0, "100 YEARS."), (161.5, "SAME WINDOW."), (166.0, "SAME WORLD?")]

# the old building and its window (the hero of the episode)
OLD = dict(x0=1118, x1=1206, top=392, peak=377, base=480)
WIN = dict(x0=1179, x1=1197, y0=397, y1=419)            # arched window, 3rd floor
TRAIN_HIDE = (46.2, 49.6)                              # the metro train passes in front of it


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def ramp(t, a, b):
    return ease((t - a) / (b - a)) if b > a else float(t >= a)


# ------------------------------------------------------------------ time of day

def tod(t):
    """(day, night) weights; sunset = 1 - day - night."""
    def cyc(t, t0, period, lo=0.0):
        c = 0.5 - 0.5 * math.cos(2 * math.pi * (t - t0) / period)   # 0 = sunset start, 1 = mid-cycle
        return c
    if t < 15:
        return 0.0, 0.55 * ramp(t, 4, 15)
    if t < 35:      # fast cycles: night -> day -> night ...
        ph = ((t - 15) / 5.0) % 1.0
        night = 0.5 + 0.5 * math.cos(2 * math.pi * ph)
        return 1 - night, night * 0.85
    if t < 58:      # slower cycles, evening at the train
        if 43 < t < 52:
            return 0.0, 0.55
        ph = ((t - 35) / 8.0) % 1.0
        night = 0.5 + 0.5 * math.cos(2 * math.pi * ph)
        return (1 - night) * (1 - ramp(t, 41, 43)) * ramp(t, 52, 54) + (1 - night) * (t < 41), night * 0.8
    if t < 80:      # day -> evening -> night, the site lights go off
        return 1 - ramp(t, 62, 70), 0.85 * ramp(t, 68, 76)
    if t < 105:     # day, then dusk for the machine's lights
        if t < 82:
            return ramp(t, 80, 81), 0.85 * (1 - ramp(t, 80, 81))
        return 1 - ramp(t, 88, 94), 0.9 * ramp(t, 92, 97)
    if t < 128:
        return 0.0, 0.95
    if t < 138:     # rapid transitions
        ph = ((t - 128) / 2.5) % 1.0
        night = 0.5 + 0.5 * math.cos(2 * math.pi * ph)
        return (1 - night), night * 0.95
    return 1 - ramp(t, 138, 146) if t < 146 else 0.0, 0.95 * ramp(t, 141, 150)


def year(t):
    return float(np.interp(t, [0, 15, 35, 58, 80, 105, 128, 150, 180], [0, 0.5, 10, 25, 40, 60, 80, 100, 100]))


# ------------------------------------------------------------------ drawing

class Layer:
    """Premultiplied colour + coverage + emissive (night lights) + constant emissive (the window)."""

    def __init__(self, H, W):
        self.rgb = np.zeros((H, W, 3), np.float32)
        self.a = np.zeros((H, W), np.float32)
        self.e = np.zeros((H, W, 3), np.float32)

    def P(self, pts):
        return np.array([[int(round(x * G["sc"] * 4)), int(round(y * G["sc"] * 4))] for x, y in pts], np.int32)

    def poly(self, pts, col, outline=True, lw=1):
        p = self.P(pts)
        cv2.fillPoly(self.rgb, [p], col, AA, 2)
        cv2.fillPoly(self.a, [p], 1.0, AA, 2)
        if outline:
            cv2.polylines(self.rgb, [p], True, OUTLINE, lw, AA, 2)
            cv2.polylines(self.a, [p], True, 1.0, lw, AA, 2)

    def rect(self, x0, y0, x1, y1, col, outline=True):
        self.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], col, outline)

    def line(self, p0, p1, col, w=1.0, outline=False):
        a, b = self.P([p0, p1])
        wp = max(1, int(round(w * G["sc"])))
        if outline:
            cv2.line(self.rgb, tuple(a), tuple(b), OUTLINE, wp + 2, AA, 2)
            cv2.line(self.a, tuple(a), tuple(b), 1.0, wp + 2, AA, 2)
        cv2.line(self.rgb, tuple(a), tuple(b), col, wp, AA, 2)
        cv2.line(self.a, tuple(a), tuple(b), 1.0, wp, AA, 2)

    def light(self, x, y, r, col, a=1.0, target="e"):
        buf = self.e
        c = tuple(float(v) * a for v in col)
        X, Y = int(round(x * G["sc"] * 4)), int(round(y * G["sc"] * 4))
        cv2.circle(buf, (X, Y), max(1, int(r * G["sc"] * 4)), c, -1, AA, 2)

    def light_rect(self, x0, y0, x1, y1, col, a=1.0):
        p = self.P([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
        cv2.fillPoly(self.e, [p], tuple(float(v) * a for v in col), AA, 2)


def shade(col, k):
    return tuple(min(1.0, c * k) for c in col)


def crane(L, x, y_base, h, jib_l, jib_r, t, swing=0.0):
    """Tower crane: mast from y_base up h px, jib to both sides, a hook line."""
    yel = (0.12, 0.72, 0.95)
    top = y_base - h
    L.line((x, y_base), (x, top), yel, 2.2, outline=True)
    for k in range(int(h // 6)):
        yy = y_base - k * 6
        L.line((x - 1.5, yy), (x + 1.5, yy - 6), yel, 0.6)
    s = math.cos(swing)
    L.line((x - jib_l * 0.35 * s, top), (x + jib_r * s, top), yel, 1.6, outline=True)
    L.line((x, top - 8), (x + jib_r * s, top), yel, 0.6)
    L.line((x, top - 8), (x - jib_l * 0.35 * s, top), yel, 0.6)
    L.rect(x - jib_l * 0.35 * s - 3, top - 2, x - jib_l * 0.35 * s + 3, top + 4, (0.3, 0.3, 0.32))
    hx = x + jib_r * s * (0.55 + 0.25 * math.sin(t * 0.4))
    hy = top + 18 + 8 * math.sin(t * 0.7)
    L.line((hx, top), (hx, hy), (0.2, 0.2, 0.22), 0.5)
    L.light(x, top - 9, 1.2, (0.15, 0.15, 1.0))


def glass_tower(L, s, t, night, frac=1.0):
    """A glass tower from spec s, `frac` of it built (with a crane and a bare frame on top)."""
    if frac <= 0:
        return
    x0, x1, top, base = s["x0"], s["x1"], s["top"], s["base"]
    col = s.get("col", (0.72, 0.55, 0.38))
    w = x1 - x0
    vt = base - (base - top) * frac
    built = vt + (14 if frac < 1 else 0)
    side = x1 - w * s.get("side", 0.22)
    if built < base:
        L.poly([(x0, built), (side, built), (side, base), (x0, base)], col)
        L.poly([(side, built), (x1, built + w * 0.03), (x1, base), (side, base)], shade(col, 0.7))
        rng = np.random.default_rng(s.get("seed", 1))
        fl = s.get("floor", 7)
        y = built + fl
        while y < base:
            L.line((x0 + 1, y), (x1 - 1, y), shade(col, 0.82), 0.5)
            y += fl
        mx = s.get("mull", 9)
        x = x0 + mx
        while x < side - 2:
            L.line((x, built + 1), (x, base), shade(col, 0.9), 0.4)
            x += mx
        # a soft diagonal sky reflection
        L.poly([(x0 + w * 0.15, built), (x0 + w * 0.32, built), (x0 + w * 0.05, min(base, built + w * 1.4)),
                (x0, min(base, built + w * 1.4)), (x0, built + w * 0.5)], shade(col, 1.18), outline=False)
        if s.get("crown") == "spire" and frac >= 1:
            L.line(((x0 + side) / 2, top), ((x0 + side) / 2, top - 30), (0.6, 0.62, 0.65), 1.2, outline=True)
        if s.get("crown") == "slant" and frac >= 1:
            L.poly([(x0, top), (side, top - w * 0.5), (side, top)], shade(col, 1.08))
        if s.get("crown") == "ring" and frac >= 1:
            L.rect(x0 - 3, top - 6, x1 + 3, top, (0.85, 0.85, 0.8))
        # night windows
        if night > 0.05:
            lit = s.get("lit", 0.16)
            cw, ch = 3, 2
            ys = np.arange(built + 3, base - 2, fl)
            xs = np.arange(x0 + 2, side - 3, mx / 2)
            m = rng.random((len(ys), len(xs))) < lit
            warm = rng.random((len(ys), len(xs))) < 0.6
            for i, yy in enumerate(ys):
                for j, xx in enumerate(xs):
                    if m[i, j] and yy > s.get("lit_from", -1e9):
                        c = (0.4, 0.72, 1.0) if warm[i, j] else (0.95, 0.92, 0.8)
                        L.light_rect(xx, yy, xx + cw, yy + ch, c, night * s.get("lit_a", 0.9))
        if frac >= 1 and s.get("beacon", True):
            on = (int(t * 1.2 + s.get("seed", 1)) % 2) == 0
            L.light((x0 + side) / 2, top - (30 if s.get("crown") == "spire" else 2), 1.3, (0.1, 0.1, 1.0), 1.0 if on else 0.2)
    if frac < 1:  # bare frame above the glass and a crane
        for k in range(5):
            x = x0 + w * k / 4
            L.line((x, built), (x, vt), (0.35, 0.35, 0.38), 0.8)
        L.line((x0, vt), (x1, vt), (0.35, 0.35, 0.38), 0.8)
        crane(L, x0 + w * 0.6, vt, 46, 70, 70, t, swing=0.3 * math.sin(t * 0.2 + x0))
        if night > 0.1:
            L.light(x0 + w * 0.5, vt + 2, 2.5, (0.7, 0.9, 1.0), night)


# ------------------------------------------------------------------ the city over time

def spec(x0, x1, top, base, build, **kw):
    return dict(x0=x0, x1=x1, top=top, base=base, build=build, **kw)


SKY_BEHIND = [  # rise behind the 2026 skyline (seen only against the sky)
    spec(600, 652, 120, 400, (16, 30), col=(0.74, 0.58, 0.42), seed=2, crown="slant"),
    spec(905, 950, 140, 400, (18, 32), col=(0.7, 0.6, 0.48), seed=3),
    spec(1000, 1044, 110, 400, (38, 50), col=(0.78, 0.62, 0.45), seed=4, crown="spire"),
    spec(1230, 1290, 150, 400, (36, 48), col=(0.72, 0.6, 0.5), seed=5),
    spec(820, 880, 90, 400, (40, 52), col=(0.8, 0.66, 0.5), seed=6, crown="ring"),
    spec(1360, 1420, 170, 400, (22, 33), col=(0.66, 0.56, 0.46), seed=7),
]
SKYLINE_FRONT = [  # replace the old towers: in front of them
    spec(462, 560, 30, 402, (59, 71), col=(0.76, 0.6, 0.44), seed=11, crown="spire", side=0.25),
    spec(752, 852, 20, 402, (61, 73), col=(0.7, 0.62, 0.52), seed=12, crown="slant"),
    spec(330, 420, -60, 402, (106, 115), col=(0.82, 0.74, 0.62), seed=13, crown="ring", mull=7),
    spec(560, 640, -80, 402, (107, 116), col=(0.86, 0.8, 0.7), seed=14, floor=6),
    spec(900, 1000, -90, 402, (106, 114), col=(0.8, 0.72, 0.58), seed=15, crown="spire"),
    spec(640, 760, -40, 402, (108, 117), col=(0.62, 0.55, 0.48), seed=16, side=0.18, billboard=True),
    spec(228, 300, -50, 402, (129, 136), col=(0.84, 0.78, 0.68), seed=17),
    spec(1040, 1110, -70, 402, (129, 137), col=(0.78, 0.7, 0.58), seed=18, crown="ring"),
    spec(852, 905, 60, 402, (130, 137), col=(0.9, 0.85, 0.75), seed=19),
]
MASSIVE = spec(1108, 1232, -40, 400, (59, 70), col=(0.6, 0.5, 0.4), seed=21, side=0.2, crown="slant")
NEW_APTS = spec(1212, 1300, 330, 480, (27, 33), col=(0.8, 0.8, 0.78), seed=22, floor=9, mull=11, beacon=False,
                side=0.15, lit=0.35)
C_TOWER = spec(1300, 1440, 30, 482, (106, 113), col=(0.74, 0.66, 0.56), seed=23, side=0.16)
F_TOWER = spec(1086, 1172, 60, 486, (106, 114), col=(0.72, 0.64, 0.54), seed=24, side=0.2, crown="slant")


def old_building(L, t, night, spot=0.0):
    """The old brick building and its window."""
    o = OLD
    brick = (0.27, 0.36, 0.58)
    L.poly([(o["x0"], o["top"]), (o["x1"], o["top"]), (o["x1"], o["base"]), (o["x0"], o["base"])], brick)
    L.poly([(o["x0"] - 3, o["top"]), ((o["x0"] + o["x1"]) / 2, o["peak"]), (o["x1"] + 3, o["top"])], (0.3, 0.3, 0.33))
    L.rect(o["x0"] + 12, o["peak"] - 2, o["x0"] + 19, o["top"] - 6, (0.25, 0.3, 0.45))        # chimney
    L.rect(o["x0"] - 2, o["top"], o["x1"] + 2, o["top"] + 3, (0.7, 0.75, 0.8))             # cornice
    for yy in (o["top"] + 25, o["top"] + 50):
        L.line((o["x0"], yy), (o["x1"], yy), (0.22, 0.3, 0.48), 0.8)
    for cx in (o["x0"] + 10, o["x0"] + 34):
        for ry in (o["top"] + 6, o["top"] + 31, o["top"] + 56):
            L.rect(cx, ry, cx + 12, ry + 14, (0.25, 0.22, 0.2))
            L.line((cx, ry + 7), (cx + 12, ry + 7), (0.75, 0.8, 0.82), 0.4)
    for ry in (o["top"] + 31, o["top"] + 56):
        L.rect(WIN["x0"] + 2, ry, WIN["x1"] - 2, ry + 14, (0.25, 0.22, 0.2))
    # the window: cream frame, arched top, cross bars
    w = WIN
    cx = (w["x0"] + w["x1"]) / 2
    arch = [(w["x0"], w["y1"]), (w["x0"], w["y0"] + 6)] + \
           [(cx + (w["x1"] - w["x0"]) / 2 * math.cos(a), w["y0"] + 6 - 6 * math.sin(a)) for a in np.linspace(math.pi, 0, 9)] + \
           [(w["x1"], w["y1"])]
    L.poly(arch, (0.8, 0.9, 0.95), lw=1)
    inner = [(x + (cx - x) * 0.18, y + (w["y1"] - y) * 0.12 if y < w["y1"] else y - 2) for x, y in arch]
    L.poly(inner, (0.35, 0.72, 1.0), outline=False)
    L.line((cx, w["y0"] + 1), (cx, w["y1"] - 2), (0.8, 0.9, 0.95), 0.7)
    L.line((w["x0"] + 2, w["y0"] + 10), (w["x1"] - 2, w["y0"] + 10), (0.8, 0.9, 0.95), 0.7)
    L.rect(w["x0"] - 2, w["y1"], w["x1"] + 2, w["y1"] + 2, (0.8, 0.9, 0.95))                 # sill
    # the glow (constant, day and night)
    p = L.P(inner)
    cv2.fillPoly(G["const_e"], [p], (0.3, 0.62, 1.0), AA, 2)
    if spot > 0:   # a machine's lights on the facade
        cv2.ellipse(L.e, (int(((o["x0"] + o["x1"]) / 2 + 10) * G["sc"]), int(430 * G["sc"])),
                    (int(48 * G["sc"]), int(40 * G["sc"])), 0, 0, 360, (0.16 * spot, 0.2 * spot, 0.22 * spot), -1, AA)


def shop_building(L, t, night):
    """The old shop next door: closes and is pulled down in the first decade."""
    x0, x1, top, base = 1212, 1300, 420, 480
    if t >= 27:
        return
    k = ramp(t, 24.5, 27)                       # demolished from the top down
    tt = top + (base - top) * k
    L.poly([(x0, tt), (x1, tt), (x1, base), (x0, base)], (0.55, 0.68, 0.78))
    if k < 0.2:
        L.rect(x0 - 2, top - 3, x1 + 2, top, (0.4, 0.45, 0.5))
        for cx in range(x0 + 8, x1 - 10, 20):
            L.rect(cx, top + 6, cx + 11, top + 18, (0.3, 0.27, 0.25))
            if night > 0.2 and t < 21:
                L.light_rect(cx + 1, top + 7, cx + 10, top + 17, (0.4, 0.75, 1.0), night * 0.8)
        # shop front: awning, window or shutters
        shut = ramp(t, 21.5, 22.5)
        L.rect(x0 + 4, 446, x1 - 4, 470, (0.35, 0.55, 0.75) if shut < 0.5 else (0.62, 0.64, 0.66))
        if shut > 0.5:
            for yy in range(448, 470, 3):
                L.line((x0 + 5, yy), (x1 - 5, yy), (0.45, 0.47, 0.5), 0.4)
        else:
            L.poly([(x0 + 2, 442), (x1 - 2, 442), (x1 + 3, 449), (x0 - 3, 449)], (0.15, 0.2, 0.75))
            if night > 0.2:
                L.light_rect(x0 + 6, 450, x1 - 6, 469, (0.4, 0.75, 1.0), night)
        # the sign: tilts and drops
        sg = ramp(t, 20.0, 21.2)
        if sg < 1:
            ang = 25 * sg
            cxs, cys = (x0 + x1) / 2, 433 + 30 * sg * sg
            pts = [(-30, -6), (30, -6), (30, 6), (-30, 6)]
            ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            L.poly([(cxs + px * ca - py * sa, cys + px * sa + py * ca) for px, py in pts], (0.2, 0.55, 0.9))
            if night > 0.2 and t < 20:
                L.light_rect(x0 + 16, 429, x1 - 16, 437, (0.3, 0.6, 1.0), night)
    if 17 < t < 25.5:   # scaffolding
        sk = ramp(t, 17, 19)
        st = base - (base - top + 8) * sk
        for xx in np.arange(x0 - 3, x1 + 4, 8):
            L.line((xx, base), (xx, st), (0.55, 0.6, 0.65), 0.5)
        for yy in np.arange(base, st, -7):
            L.line((x0 - 3, yy), (x1 + 3, yy), (0.55, 0.6, 0.65), 0.5)
    if 22.5 < t < 33:   # site fence
        L.rect(x0 - 6, 466, x1 + 6, 480, (0.85, 0.6, 0.25))
        for xx in np.arange(x0 - 4, x1 + 4, 10):
            L.line((xx, 467), (xx, 479), (0.95, 0.95, 0.95), 0.6)


def old_block_c(L, t, night):
    """The 3-storey block on the right, pulled down by the machine in Year 60."""
    x0, x1, top, base = 1302, 1436, 405, 480
    if t >= 96:
        if t < 106:   # rubble
            L.poly([(x0 + 10, base), (x0 + 40, 466), (x0 + 75, 470), (x0 + 110, 462), (x1 - 4, base)], (0.5, 0.52, 0.55))
        return
    cut = 0.0
    if t > 85:
        cut = ramp(t, 85, 95.5)
    rx = x1 - (x1 - x0) * cut                # bitten away from the right
    L.poly([(x0, top), (rx, top + 30 * cut), (rx, base), (x0, base)], (0.62, 0.75, 0.82))
    for cx in np.arange(x0 + 8, rx - 10, 16):
        for ry in (top + 8, top + 30, top + 52):
            L.rect(cx, ry, cx + 9, ry + 12, (0.3, 0.3, 0.3))
            if night > 0.3 and t < 70 and (int(cx + ry) % 3):
                L.light_rect(cx + 1, ry + 1, cx + 8, ry + 11, (0.45, 0.78, 1.0), night * 0.8)


def demolition_machine(L, t, night):
    """Year 60: the excavator eats block C, then turns to the old building, stops, powers down, backs away."""
    if not 82 <= t < 105.5:
        return 0.0
    base = 482
    x = 1395
    if t < 84:
        x = 1470 - 75 * ramp(t, 82, 84)
    facing = 1                                         # 1 = towards C (right), -1 = towards the old building
    if 96.5 <= t:
        facing = -1
    if t > 102.5:
        x = 1395 + 90 * ease((t - 102.5) / 3)
    if t > 96.5 and t < 98.2:
        x = 1395 - 60 * ramp(t, 96.5, 98.2)
    elif 98.2 <= t <= 102.5:
        x = 1335
    elif t > 102.5:
        x = 1335 + 140 * ease((t - 102.5) / 3)
    yel = (0.1, 0.62, 0.95)
    L.rect(x - 24, base - 10, x + 24, base, (0.18, 0.18, 0.2))                      # tracks
    L.rect(x - 18, base - 30, x + 18, base - 10, yel)                               # body
    L.rect(x - facing * 2 - (12 if facing > 0 else -12) * 0 - 6, base - 44, x + 8, base - 30, yel)   # cab
    L.rect(x - 4, base - 42, x + 6, base - 34, (0.55, 0.45, 0.35))                  # cab glass
    # the long arm
    work = 85 <= t < 95.5
    sw = math.sin(t * 2.2) if work else 0.0
    ax0, ay0 = x + facing * 10, base - 30
    ax1, ay1 = x + facing * 38, base - 92 + 8 * sw
    ax2, ay2 = x + facing * (52 + 6 * sw), base - 70 + 10 * sw
    if t >= 96.5:
        ax1, ay1, ax2, ay2 = x + facing * 30, base - 66, x + facing * 44, base - 40
    L.line((ax0, ay0), (ax1, ay1), yel, 3.0, outline=True)
    L.line((ax1, ay1), (ax2, ay2), yel, 2.4, outline=True)
    L.poly([(ax2 - 5, ay2), (ax2 + 5, ay2), (ax2 + facing * 7, ay2 + 9), (ax2 - facing * 2, ay2 + 9)], (0.25, 0.25, 0.27))
    lights = 1.0 if t < 101.6 else 0.0
    if lights:
        L.light(x + facing * 18, base - 24, 1.6, (0.85, 0.95, 1.0), 1.0)
        L.light(x - 6, base - 46, 1.0, (0.1, 0.6, 1.0), 1.0 if int(t * 3) % 2 else 0.3)
    spot = 0.0
    if 97.5 < t < 101.6:
        spot = ramp(t, 97.5, 98.4)
        bx = x + facing * 18
        cv2.fillPoly(L.e, [L.P([(bx, base - 26), (1205, 400), (1205, 470), (bx, base - 20)])],
                     (0.07 * spot, 0.09 * spot, 0.1 * spot), AA, 2)
    return spot


def dust(L, t):
    if not 86 <= t < 100:
        return None
    rng = np.random.default_rng(31)
    a = np.zeros((G["H"], G["W"]), np.float32)
    for i in range(26):
        t0 = 86 + rng.random() * 9
        if t < t0:
            continue
        dt = t - t0
        x = 1380 - dt * rng.uniform(6, 16) - rng.uniform(0, 40)
        y = 470 - dt * rng.uniform(4, 9)
        r = 12 + dt * 7
        k = max(0.0, 1 - dt / 7) * 0.5 * (1 - ramp(t, 96, 100))
        cv2.circle(a, (int(x * G["sc"]), int(y * G["sc"])), int(r * G["sc"]), k, -1, AA)
    return cv2.GaussianBlur(a, (0, 0), 9 * G["sc"])


def metro(L, t, night, train_light=0.0):
    """Elevated metro on the far bank, built in Year 25, with trains."""
    if t < 36:
        return
    k = ramp(t, 36, 42)
    y = lambda x: 396 + (x - 300) * 0.024
    xs = 1440 - (1440 - 300) * k
    L.poly([(xs, y(xs)), (1440, y(1440)), (1440, y(1440) + 6), (xs, y(xs) + 6)], (0.78, 0.8, 0.82))
    for px in np.arange(1420, xs, -70):
        L.rect(px - 2, y(px) + 6, px + 2, min(482, y(px) + 70), (0.7, 0.72, 0.75))
    if night > 0.2:
        for px in np.arange(1430, xs, -12):
            L.light(px, y(px) + 5, 0.6, (0.9, 0.85, 0.6), night * 0.7)

    def train(x_head, direction, length=230, bright=False):
        x_tail = x_head - direction * length
        a, b = min(x_head, x_tail), max(x_head, x_tail)
        a2, b2 = max(a, 300), min(b, 1440)
        if b2 <= a2:
            return
        L.poly([(a2, y(a2) - 20), (b2, y(b2) - 20), (b2, y(b2)), (a2, y(a2))], (0.92, 0.93, 0.94))
        L.line((a2, y(a2) - 8), (b2, y(b2) - 8), (0.75, 0.5, 0.15), 1.5)
        for wx in np.arange(a2 + 4, b2 - 6, 9):
            L.rect(wx, y(wx) - 17, wx + 6, y(wx) - 11, (0.35, 0.3, 0.28), outline=False)
            if night > 0.1:
                L.light_rect(wx, y(wx) - 17, wx + 6, y(wx) - 11, (0.75, 0.95, 1.0), max(night, 0.4))
        if bright:
            L.light(x_head, y(x_head) - 8, 3, (0.9, 1.0, 1.0), 1.0)

    if TRAIN_HIDE[0] - 2 < t < TRAIN_HIDE[1] + 2:
        train(1500 - (t - (TRAIN_HIDE[0] - 2)) * 140, -1)
    for t0 in (55.0, 66.0, 90.0, 132.0, 140.0, 170.0):
        if t0 < t < t0 + 9:
            train(250 + (t - t0) * 160, 1)


def pods(L, t, night, auto=False):
    """Automated pods on the bridge (Year 25+), evenly spaced and in step when automated."""
    (bx0, by0), (bx1, by1) = G["cfg"]["bridge_lane"]
    by = lambda x: by0 + (by1 - by0) * (x - bx0) / (bx1 - bx0)
    n = 9 if auto else 6
    for i in range(n):
        d = 1 if i % 2 == 0 else -1
        sp = 55 if auto else 40 + 9 * (i % 3)
        span = bx1 - bx0 + 60
        ph = i * span / n
        x = bx0 - 30 + (ph + d * t * sp) % span
        y = by(x) + (-3 if d < 0 else 0)
        L.poly([(x - 11, y - 7), (x + 9, y - 7), (x + 12, y - 3), (x + 12, y), (x - 12, y), (x - 12, y - 3)],
               (0.93, 0.93, 0.92) if i % 3 else (0.85, 0.8, 0.7))
        L.line((x - 10, y - 3), (x + 10, y - 3), (0.95, 0.75, 0.2), 0.8)
        if night > 0.1:
            L.light(x + d * 12, y - 3, 1.2, (0.95, 1.0, 1.0), night)
            L.light(x - d * 12, y - 3, 1.0, (0.3, 0.3, 1.0), night)


def riverfront(L, t, night):
    """Year 25: a new walkway with a lit rail along the near river bank."""
    if t < 39:
        return
    k = ramp(t, 39, 42)
    pts = [(800, 652), (870, 685), (990, 704), (1110, 726), (1310, 694)]
    n = int(1 + (len(pts) - 1) * k)
    for a, b in zip(pts[:n], pts[1:n + 1]):
        for u in np.linspace(0, 1, 7)[:-1]:
            x, y = a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u
            L.line((x, y + 2), (x, y - 10), (0.85, 0.86, 0.86), 1.0)
            L.light(x, y - 10, 1.4, (0.95, 0.9, 0.7), 0.25 + 0.75 * night)


def modern_parked(L, t, night):
    """Sleek delivery pod over the old truck, a small pod over the old car."""
    L.poly([(494, 688), (494, 640), (510, 612), (586, 612), (600, 630), (602, 688)], (0.9, 0.9, 0.9))
    L.poly([(510, 616), (584, 616), (592, 632), (504, 632)], (0.45, 0.4, 0.35), outline=False)
    L.line((496, 660), (600, 660), (0.95, 0.7, 0.15), 2.0)
    L.rect(500, 682, 520, 690, (0.15, 0.15, 0.16)); L.rect(574, 682, 594, 690, (0.15, 0.15, 0.16))
    L.poly([(556, 762), (558, 735), (580, 708), (630, 708), (650, 732), (652, 762)], (0.82, 0.86, 0.9))
    L.poly([(584, 712), (626, 712), (640, 730), (570, 730)], (0.45, 0.4, 0.35), outline=False)
    L.line((558, 744), (650, 744), (0.95, 0.85, 0.3), 1.6)
    if night > 0.1:
        L.light(650, 748, 2.0, (0.95, 1.0, 1.0), night)
        L.light(600, 665, 2.0, (0.95, 1.0, 1.0), night * 0.6)


def barrier(L, t):
    if t < 138:
        return
    k = ramp(t, 138, 140)
    x1 = 1110 + (1222 - 1110) * k
    for xx in np.arange(1110, x1, 7):
        L.rect(xx, 470, xx + 6, 478, (0.1, 0.45, 0.95) if int(xx / 7) % 2 else (0.95, 0.95, 0.95))


def big_machine(L, t, night):
    """Year 100: a large machine approaches the old building, stops just short, goes dark."""
    if t < 139:
        return
    x = 1520 - (1520 - 1262) * ease((t - 139) / 7)
    base = 482
    L.rect(x - 34, base - 12, x + 34, base, (0.2, 0.2, 0.22))
    L.poly([(x - 30, base - 12), (x - 26, base - 52), (x + 30, base - 52), (x + 34, base - 12)], (0.82, 0.84, 0.86))
    L.rect(x - 22, base - 64, x + 10, base - 52, (0.3, 0.32, 0.35))
    L.line((x - 26, base - 40), (x - 50, base - 30), (0.6, 0.62, 0.65), 2.5, outline=True)
    L.poly([(x - 56, base - 38), (x - 46, base - 38), (x - 46, base - 18), (x - 56, base - 18)], (0.5, 0.52, 0.55))
    on = 1.0 - ramp(t, 147.2, 147.5)
    if on > 0:
        L.light_rect(x - 28, base - 34, x + 28, base - 30, (1.0, 0.85, 0.3), on)
        L.light(x - 50, base - 28, 2.5, (0.9, 1.0, 1.0), on)
        if t < 147.2:
            cv2.fillPoly(L.e, [L.P([(x - 52, base - 30), (1206, 410), (1206, 470), (x - 52, base - 24)])],
                         (0.14 * on, 0.17 * on, 0.2 * on), AA, 2)


def billboard(L, t, s):
    """Removed at the owner's request (read as a glitch); kept for reference."""
    return
    x0, x1, y0, y1 = 600, 860, 145, 270
    on = ramp(t, 112, 112.6) * (1 - ramp(t, 119.0, 119.2))
    L.rect(x0 - 4, y0 - 4, x1 + 4, y1 + 4, (0.08, 0.08, 0.1))
    import colorsys
    for i in range(26):   # a slowly shifting colour gradient with a light sweep (no text, no logos)
        u = i / 26
        h = (0.55 + 0.35 * u + 0.08 * t) % 1.0
        r, g, b = colorsys.hsv_to_rgb(h, 0.55, 1.0)
        xa = x0 + (x1 - x0) * u
        L.light_rect(xa, y0, xa + (x1 - x0) / 26 + 0.5, y1, (b, g, r), on * 0.55)
    sx = x0 + (x1 - x0) * (((t - 112) * 0.35) % 1.0)
    L.light_rect(sx - 12, y0, sx + 12, y1, (1.0, 1.0, 1.0), on * 0.35)


# ------------------------------------------------------------------ frame

def compose(t):
    W, H, sc = G["W"], G["H"], G["sc"]
    day, night = tod(t)
    sunset = max(0.0, 1 - day - night)
    nl = min(1.0, night * 1.25)                                  # how "on" night lights are
    G["const_e"] = np.zeros((H, W, 3), np.float32)
    city = G["city_img"].copy()
    height = G["height"].copy()
    G["float_mask"] = np.zeros(height.shape, np.float32)
    # traffic: the 2026 vehicles until Year 25, then pods
    if t < 38:
        p = dict(traffic="busy", headlights=nl, lights=0)
        R.traffic(city, t * (1.0 if t < 15 else 1.6), p, height)
    groups = []

    def grp():
        L = Layer(H, W); groups.append(L); return L

    # 1. towers behind the old skyline
    L1 = grp()
    for s in SKY_BEHIND:
        glass_tower(L1, s, t, nl, ramp(t, *s["build"]) if t >= s["build"][0] else 0)
    L1.a *= G["sky"]; L1.rgb *= G["sky"][..., None]; L1.e *= G["sky"][..., None]
    # 2. towers that replace the old skyline (in front of it, behind the far trees and bridge)
    L2 = grp()
    for s in SKYLINE_FRONT:
        if t >= s["build"][0]:
            glass_tower(L2, s, t, nl, ramp(t, *s["build"]))
            if s.get("billboard"):
                billboard(L2, t, s)
    if t >= MASSIVE["build"][0]:
        glass_tower(L2, MASSIVE, t, nl, ramp(t, *MASSIVE["build"]))
        if 58 < t < 80:   # site lights on the massive tower: off one by one as evening falls
            for i, (lx, ly) in enumerate(((1120, 120), (1150, 220), (1200, 300), (1130, 340), (1215, 180))):
                if t < 74 + i * 0.9 and t > 70:
                    L2.light(lx, ly, 2.4, (0.8, 0.95, 1.0), 1.0)
    occ = G["occ_skyline"]
    for L in (L2,):
        L.a *= 1 - occ; L.rgb *= (1 - occ)[..., None]; L.e *= (1 - occ)[..., None]
    # 3. the far bank: old building, shop, block C, new apartments, the tower on C's lot
    L3 = grp()
    spot = 0.0
    if t >= NEW_APTS["build"][0]:
        glass_tower(L3, NEW_APTS, t, nl, ramp(t, *NEW_APTS["build"]))
    if t >= C_TOWER["build"][0]:
        glass_tower(L3, C_TOWER, t, nl, ramp(t, *C_TOWER["build"]))
    shop_building(L3, t, nl)
    old_block_c(L3, t, nl)
    if 102 < t < 105.5:
        pass
    # the machine's light on the facade is computed with the machine (group 5)
    L5 = Layer(H, W)
    spot = demolition_machine(L5, t, nl)
    old_building(L3, t, nl, spot)
    tm = G["trees_far"]
    L3.a *= 1 - tm; L3.rgb *= (1 - tm)[..., None]; L3.e *= (1 - tm)[..., None]
    G["const_e"] *= (1 - tm)[..., None]
    # 4. metro and trains
    L4 = grp()
    metro(L4, t, nl)
    # 5. in front on the far bank: the Year-80 tower, machines, barriers, dust
    groups.append(L5)
    if t >= F_TOWER["build"][0]:
        glass_tower(L5, F_TOWER, t, nl, ramp(t, *F_TOWER["build"]))
    barrier(L5, t)
    big_machine(L5, t, nl)
    if 58 < t < 80:   # fence and a mobile crane at the old building's boundary
        if t > 64:
            L5.rect(1080, 468, 1116, 482, (0.85, 0.6, 0.25))
            crane(L5, 1096, 470, 60, 40, 50, t, 0.2 * math.sin(t * 0.3))
    L5.a *= 1 - tm * 0.6; L5.rgb *= (1 - tm * 0.6)[..., None]; L5.e *= (1 - tm * 0.6)[..., None]
    # 6. bridge pods and the riverfront
    L6 = grp()
    if t >= 38:
        L6c = G["bridge_clip"]
        pods(L6, t, nl, auto=t >= 80)
        L6.a *= L6c; L6.rgb *= L6c[..., None]; L6.e *= L6c[..., None]
    L7 = grp()
    riverfront(L7, t, nl)
    if t >= 38:   # the parked 2026 truck and car are replaced by modern vehicles
        modern_parked(L7, t, nl)
    cm = G["canopy"]
    L7.a *= 1 - cm; L7.rgb *= (1 - cm)[..., None]; L7.e *= (1 - cm)[..., None]

    order = [L1, L2, L3, L4, L5, L6, L7]
    A = np.zeros((H, W), np.float32)
    E = np.zeros((H, W, 3), np.float32)
    CE = G["const_e"]
    for L in order:
        city = city * (1 - L.a[..., None]) + L.rgb
        E = E * (1 - L.a[..., None]) + L.e
        if L in (L4, L5):
            CE = CE * (1 - L.a[..., None])
        A = A + L.a * (1 - A)
    # dust partly hides the old building
    d = dust(L5, t)
    if d is not None:
        city = city * (1 - d[..., None]) + np.array([0.62, 0.66, 0.7], np.float32) * d[..., None]
        G["dust_lit"] = d
        CE = CE * (1 - d[..., None] * 0.6)
        E = E * (1 - d[..., None])
    # 2026 window lights and street lamps at night
    base_e = (G["em_base"] + G["nightwin"]) * (1 - A)[..., None]
    sections = 1.0
    if 145 < t < 155:   # night falls: the city lights up one section at a time
        xs = G["xx"] / G["W"]
        sections = (xs < ramp(t, 147.5, 151.5) * 1.05).astype(np.float32)[..., None]
    if 119.2 <= t < 121.2:   # billboard off: the city goes dark for a moment
        sections = 0.15
    if 158 < t:
        sections = sections * (1 - 0.35 * ramp(t, 170, 176) * G["off_late"][..., None])
    E_night = (E + base_e * 1.2) * nl * sections + base_e * 0.0
    # grade
    graded = grade(city, day, night)
    skyw = G["sky"] * (1 - A)
    skyimg = sky(t, day, night, sunset, city)
    graded = graded * (1 - skyw[..., None]) + skyimg * skyw[..., None]
    out = graded + E_night + CE * 1.4
    if d is not None:   # dust catches the machine's work lights
        out = out + G["dust_lit"][..., None] * np.array([0.35, 0.4, 0.45], np.float32) * nl
    # a passing transit's light band (Year 80)
    if 121.0 < t < 124.5:
        bx = (1500 - (t - 121) * 360) * G["sc"]
        by = (396 + (bx / G["sc"] - 300) * 0.024) * G["sc"]
        band = np.exp(-((G["xx"] - bx) / (110 * G["sc"])) ** 2 - ((G["yy"] - by) / (34 * G["sc"])) ** 2)
        out = out + (band * G["outside"])[..., None] * (city * 1.2 + 0.06) * (1 - skyw[..., None])
    # bloom on the old window and lights
    glow = cv2.GaussianBlur(CE, (0, 0), 6 * sc) * 1.6 + cv2.GaussianBlur(E_night, (0, 0), 3 * sc) * 0.5
    out = out + glow
    # the window's reflection on the Year-80 tower's glass
    if t >= F_TOWER["build"][1]:
        rx, ry = 1158 * sc, 410 * sc
        refl = np.zeros((H, W), np.float32)
        cv2.ellipse(refl, (int(rx), int(ry)), (int(5 * sc), int(8 * sc)), 0, 0, 360, 1.0, -1, AA)
        refl = cv2.GaussianBlur(refl, (0, 0), 2 * sc)
        out = out + refl[..., None] * np.array([0.25, 0.5, 0.8], np.float32) * (0.4 + 0.6 * nl)
    # the river reflects the new city
    mix = ramp(t, 15, 30) * 0.85
    if mix > 0:
        wc = np.array([0.55, 0.45, 0.32], np.float32) * (1 - 0.75 * night) + np.array([0.3, 0.35, 0.45], np.float32) * sunset * 0.3
        pw = dict(level=-1.2, river_mix=mix, puddles=0.0, water=tuple(wc), water_alpha=0.8, rings=0.0)
        out = R.water(out, t, pw, height)
    return out, day, night, sunset, nl


def grade(img, day, night):
    sunset = max(0.0, 1 - day - night)
    lum = (img @ np.array([0.114, 0.587, 0.299], np.float32))[..., None]
    warm = np.clip((img[..., 2:3] - img[..., 0:1]) * 2.0, 0, 1)
    d = img * np.array([1.12, 1.03, 0.9], np.float32)
    d = d * (1 - 0.35 * warm) + lum * np.array([1.0, 1.0, 0.98], np.float32) * 0.35 * warm
    d = d * 1.05
    n = img * 0.2 * np.array([1.35, 1.0, 0.75], np.float32) + lum * 0.06 * np.array([1.2, 0.9, 0.7], np.float32)
    return img * sunset + d * day + n * night


def sky(t, day, night, sunset, city):
    rows = G["rows"][..., None]
    dsky = np.array([0.92, 0.72, 0.5], np.float32) * (1 - rows * 1.2) + np.array([0.95, 0.88, 0.78], np.float32) * rows * 1.2
    off = int(t * 4 * G["sc"]) % G["W"]
    cl = np.roll(G["clouds"][0], -off, axis=1)[:, :G["W"]][..., None]
    dsky = dsky * (1 - 0.25 * cl) + 0.25 * cl
    nsky = np.array([0.22, 0.12, 0.06], np.float32) * (1 - rows) + np.array([0.3, 0.2, 0.14], np.float32) * rows * 1.5
    nsky = nsky + G["stars"][..., None] * night
    return city * sunset + dsky * day + nsky * night


def room(frame_city, day, night, t):
    img = G["room_img"]
    lum = (img @ np.array([0.114, 0.587, 0.299], np.float32))[..., None]
    d = img * np.array([1.06, 1.0, 0.94], np.float32)
    n = img * 0.3 * np.array([1.25, 1.0, 0.85], np.float32)
    sunset = max(0.0, 1 - day - night)
    r = img * sunset + d * day + n * night
    if 159 < t < 163:   # a distant vehicle's light slides across the mug
        mg = G["cfg"]["mug"]; sc = G["sc"]
        k = (t - 159) / 4
        x = (mg["cx"] - 70 + 140 * k) * sc
        band = np.exp(-((G["xx"] - x) / (6 * sc)) ** 2) * (np.abs(G["yy"] - (mg["cy"] + 40) * sc) < 45 * sc)
        r = r + (band * G["mug_mask"])[..., None] * 0.35 * math.sin(math.pi * k)
    a = (1 - G["outside"])[..., None]
    return frame_city * (1 - a) + r * a


def text(frame, t):
    i = max(k for k, s in enumerate(SCENES) if s[0] <= t)
    start, label = SCENES[i]
    nxt = SCENES[i + 1][0] if i + 1 < len(SCENES) else DURATION
    W, H, sc = G["W"], G["H"], G["sc"]
    items = []
    if label:
        a = ease((t - start - 0.3) / 0.6) * ease((nxt - t - 0.2) / 0.5)
        items.append((label, a, (int(250 * sc), int(70 * sc)), int(46 * sc), False))
    for t0, line in FINAL_LINES:
        if t >= t0:
            a = ease((t - t0) / 1.0) * ease((DURATION - t) / 1.0)
            y = int((150 + 62 * FINAL_LINES.index((t0, line))) * sc)
            items.append((line, a, (0, y), int(54 * sc), True))
    for s, a, (x, y), size, center in items:
        if a <= 0:
            continue
        font = G.setdefault(("font", size), ImageFont.truetype(FONT, size))
        lay = Image.new("L", (W, H), 0); sh = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(lay)
        if center:
            x = int((W - d.textlength(s, font=font)) / 2)
        d.text((x, y), s, font=font, fill=255)
        ImageDraw.Draw(sh).text((x + int(2 * sc), y + int(3 * sc)), s, font=font, fill=255)
        sh = sh.filter(ImageFilter.GaussianBlur(5 * sc))
        aa = np.asarray(lay, np.float32)[..., None] / 255 * a
        ss = np.asarray(sh, np.float32)[..., None] / 255 * a * 0.55
        frame = frame * (1 - ss)
        frame = frame * (1 - aa) + np.array([0.97, 0.98, 1.0], np.float32) * aa
    return frame


def render(t):
    city, day, night, sunset, nl = compose(t)
    frame = room(city, day, night, t)
    frame = text(frame, t)
    if t > DURATION - 1.0:
        frame = frame * ease((DURATION - t) / 1.0)
    return (np.clip(frame, 0, 1) * 255).astype(np.uint8)


def init(masks):
    R.init_worker("h", masks)
    W, H, sc = G["W"], G["H"], G["sc"]
    master = cv2.imread(G["cfg"]["master"])
    hsv = cv2.cvtColor(master, cv2.COLOR_BGR2HSV).astype(np.float32)
    leafy = ((hsv[..., 0] >= 22) & (hsv[..., 0] <= 90) & (hsv[..., 1] > 55)).astype(np.uint8)
    rows = np.arange(master.shape[0])[:, None]
    cols = np.arange(master.shape[1])[None, :]
    far = leafy & (rows > 430) & (rows < 486) & (cols > 1075) & (cols < 1442)
    far = cv2.morphologyEx(far, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    G["trees_far"] = cv2.GaussianBlur(cv2.resize(far.astype(np.float32), (W, H)), (0, 0), 0.8)
    occ = (leafy & (rows > 372)) | ((rows > 408) & (cols > 295) & (cols < 1080))
    occ = occ | (rows > 402)
    G["occ_skyline"] = cv2.GaussianBlur(cv2.resize(occ.astype(np.float32), (W, H)), (0, 0), 0.8)
    # 2026 lights: the lit windows of the art, plus random lit windows in the old towers at night
    keep = np.zeros((H, W), np.float32)
    keep[: int(470 * sc)] = 1.0
    for k in ("tower", "near_building"):
        cv2.fillPoly(keep, [(np.array(G["cfg"][k]) * sc).astype(np.int32)], 1.0)
    G["em_base"] = (G["emissive"] * keep)[..., None] * G["city_img"] * 0.6
    rng = np.random.default_rng(3)
    nw = np.zeros((H, W, 3), np.float32)
    bld = (1 - G["sky"]) * G["outside"] * (G["yy"] < 400 * sc) * (G["xx"] > 228 * sc) * (G["xx"] < 1440 * sc)
    for _ in range(1100):
        x, y = int(rng.uniform(228, 1440) * sc), int(rng.uniform(20, 398) * sc)
        if bld[y, x] > 0.9 and G["canopy"][y, x] < 0.1:
            c = (0.45, 0.78, 1.0) if rng.random() < 0.6 else (1.0, 0.95, 0.8)
            cv2.rectangle(nw, (x, y), (x + 1, y + 1), tuple(v * 0.55 for v in c), -1)
    G["nightwin"] = nw
    off = (rng.random((H // 8 + 1, W // 8 + 1)) < 0.25).astype(np.float32)
    G["off_late"] = cv2.resize(off, (W, H), interpolation=cv2.INTER_NEAREST)
    st = np.zeros((H, W), np.float32)
    for _ in range(260):
        cv2.circle(st, (int(rng.uniform(0, W)), int(rng.uniform(0, 0.4 * H))), 1, rng.uniform(0.2, 0.7), -1)
    G["stars"] = st
    mg = G["cfg"]["mug"]
    mm = np.zeros((H, W), np.float32)
    cv2.rectangle(mm, (int((mg["cx"] - 66) * sc), int((mg["cy"] - 2) * sc)), (int((mg["cx"] + 66) * sc), int((mg["cy"] + 92) * sc)), 1.0, -1)
    G["mug_mask"] = mm * (1 - G["outside"])


def render_chunk(args):
    masks, start, end, path = args
    W, H = G["W"], G["H"]
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                           "-crf", "16", "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    for f in range(start, end):
        ff.stdin.write(render(f / FPS).tobytes())
    ff.stdin.close(); ff.wait()
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("masks"); ap.add_argument("out")
    ap.add_argument("--still", type=float, nargs="*")
    ap.add_argument("--jobs", type=int, default=os.cpu_count())
    ap.add_argument("--start", type=float, default=0); ap.add_argument("--end", type=float, default=DURATION)
    a = ap.parse_args()
    if a.still:
        init(a.masks)
        out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
        for t in a.still:
            cv2.imwrite(str(out / f"t{t:06.2f}.png"), render(t))
        return
    n0, n1 = int(a.start * FPS), int(a.end * FPS)
    tmp = Path(tempfile.mkdtemp(dir=Path(a.out).parent))
    k = a.jobs * 3
    b = [n0 + (n1 - n0) * i // k for i in range(k + 1)]
    jobs = [(a.masks, b[i], b[i + 1], str(tmp / f"c{i:03d}.mp4")) for i in range(k)]
    with Pool(a.jobs, initializer=init, initargs=(a.masks,)) as pool:
        for i, _ in enumerate(pool.imap(render_chunk, jobs)):
            print(f"chunk {i + 1}/{k}", flush=True)
    (tmp / "list.txt").write_text("".join(f"file '{j[3]}'\n" for j in jobs))
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"),
                    "-c", "copy", a.out], check=True)
    for j in jobs:
        os.remove(j[3])
    os.remove(tmp / "list.txt"); tmp.rmdir()


if __name__ == "__main__":
    main()
