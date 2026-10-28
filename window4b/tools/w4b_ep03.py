"""Window 4B Ep 3 renderer: "What If the Entire City Became Empty Overnight?"

    python window4b/tools/w4b_ep03.py MASKS_h.npz OUT.mp4 [--start S --end E] [--still T ...] [--jobs 4]

Same locked 16:9 master and engine as Eps 1-2. People vanish at midnight on Day 1; over the next year
lights fail, dust and weather wear the city down, plants and animals take it back. Positions are
master px (1672 x 941) unless they say "out". Everything is a pure function of t.
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
from scenes import SCENES       # noqa: E402
import w4b_ep02 as E            # noqa: E402
import w4b_render as R          # noqa: E402
import actors as A              # noqa: E402
import story as S               # noqa: E402
import fauna as F               # noqa: E402

G = E.G
FPS = 24
DURATION = 180.0
FONT = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
AA = cv2.LINE_AA

MARKERS = [(0, "DAY 1  |  8:00 AM"), (20, "DAY 1  |  6:30 PM"), (40, "DAY 2"), (60, "DAY 7"), (72, "DAY 30"),
           (85, "MONTH 3"), (110, "MONTH 6"), (135, "DAY 365"), (165, None)]
FINAL = [(169.0, "DAY 1: EVERYONE WAS HERE."), (173.0, "DAY 365: THE CITY BELONGS TO NATURE.")]

SIGNAL = (470, 640)
BUS_STOP = (458, 616)            # the bus stops at the signal and stays there
CUP_DAY1 = (705, 704)
DRAIN = (515, 694)
POTHOLE = (692, 742)
FOUNTAIN = (1095, 768)
SHOP_SIGN = (262, 668)
LAMPS = [(468, 556), (603, 598), (1033, 648), (1352, 547)]
LAMP_OFF = [999, 64.5, 71.0, 79.0]
OFFICE_WIN = (686, 84)           # top-floor window of the tall office tower (lit to Day ~29)
LAST_LAMP = None                 # chosen in init: the streetlight nearest the bridge
# Extra beats rendered only for the Shorts (w4b_ep03_extras.py sets this): world time is held near
# EXTRA["world"] while the extra beat plays out on its own local clock G["lt"].
EXTRA = {}


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def ramp(t, a, b):
    return ease((t - a) / (b - a)) if b > a else float(t >= a)


def lerp(a, b, u):
    return a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u


def ou(p):
    return p[0] * G["sc"], p[1] * G["sc"]


def u_at(y_m):
    return G["s"](y_m) * G["sc"] * 1.2


# ------------------------------------------------------------------ time

def tod(t):
    """(day, night) light weights; sunset/sunrise = the rest."""
    def cycle(t, t0, period):          # 0 = midday, 1 = midnight
        return 0.5 - 0.5 * math.cos(2 * math.pi * (t - t0) / period)
    if t < 20:
        return 0.92, 0.0
    if t < 40:                         # 6:30 pm -> midnight
        return 0.75 * (1 - ramp(t, 20, 28)), 0.92 * ramp(t, 26, 33)
    if t < 60:                         # Day 2: dawn, day, dusk, night
        return ramp(t, 41, 45) * (1 - ramp(t, 52, 56)), 0.92 * (1 - ramp(t, 40, 44)) + 0.92 * ramp(t, 54, 58)
    if t < 85:                         # days 7-30: fast cycles, 4 s each
        n = cycle(t, 60, 4.0)
        return (1 - n) * 0.92, n * 0.92
    if t < 135:
        storm = ramp(t, 91, 93) * (1 - ramp(t, 99, 101))
        return 0.92 - 0.45 * storm, 0.0
    if t < 165:                        # Day 365, then evening
        return 0.92 * (1 - ramp(t, 152, 160)), 0.92 * ramp(t, 157, 164)
    return 0.0, 0.95


def decay(t):        # dust, stains, wear
    return float(np.interp(t, [0, 62, 85, 110, 135, 150, 180], [0, 0.05, 0.3, 0.6, 0.8, 1.0, 1.0]))


def green(t):        # vegetation
    return float(np.interp(t, [0, 95, 110, 135, 150, 180], [0, 0.05, 0.35, 0.65, 1.0, 1.0]))


def window_fraction(t):
    """Share of the city's windows lit at night."""
    return float(np.interp(t, [0, 24, 31, 34.5, 39.6, 40, 54, 60, 85, 135, 165, 180],
                           [0, 0, 0.8, 0.8, 0.05, 0.16, 0.16, 0.14, 0.03, 0.012, 0.012, 0.004]))


def people_alive(t):
    return t < 39.6


# ------------------------------------------------------------------ the living city

def street_people(canvas, height, t):
    if t >= 39.0:
        return
    c = S.Ctx(G, t, dict(level=-1.2), canvas, height, G["float_mask"])
    rng = np.random.default_rng(8)
    n = 7 if t < 22 else int(7 * (1 - ramp(t, 22, 38)))
    for i in range(n):
        u0 = rng.random(); v = (0.012 + 0.01 * rng.random()) * (1 if i % 2 else -1)
        pos = (u0 + v * t) % 1.0
        x, y = lerp(*S.PROMENADE, pos) if i < 4 else lerp(*S.SIDEWALK, pos)
        c.stand(A.person, x, y, shirt=S.SHIRTS[i % 6], skin=S.SKIN[i % 4], phase=t * 6 + i, walking=True)
    if t < 20:
        x, y = lerp((560, 690), (760, 705), ((t * 0.07) % 1.0))
        c.stand(A.person, x, y, shirt=S.SHIRTS[4], skin=S.SKIN[2], phase=t * 6, walking=True)
        for j, xx in enumerate((790, 812)):
            c.stand(A.person, xx, 712, shirt=S.SHIRTS[2 + j], skin=S.SKIN[j], walking=False)


def traffic(canvas, height, t, nl):
    if t < 34:
        mode = "busy"
    elif t < 39.5:
        mode = "few"
    else:
        mode = "stuck"
    p = dict(traffic=mode, headlights=nl, lights=0.0, level=-1.2)
    R.traffic(canvas, t, p, height)
    if 37.0 < t < 39.6:          # the last car crosses the bridge
        x = 300 + (t - 37.0) * 300
        R.draw_sprite(canvas, "van", x, 436, lights=nl)


def bus(canvas, height, t):
    c = S.Ctx(G, t, dict(level=-1.2), canvas, height, G["float_mask"])
    k = ease((t - 6.0) / 6.5)
    bx, by = lerp((440, 580), BUS_STOP, k)
    G["draw_sprite_at"](c, "bus_road", bx, by)
    G["lane_clip"] = G["outside"]
    R.draw_sprite(canvas, "rtruck", 547.5, 688)       # the parked truck stays in front of the bus
    G["bus_box"] = (bx - 40, by - 50, bx + 40, by)


def signal_state(t):
    if t < 66:
        ph = t % 8 if t < 60 else (t * 1.6) % 8
        if 10 < t < 16:
            return "red"
        return "green" if ph < 4 else ("amber" if ph < 5 else "red")
    if t < 103:
        return "red"
    if t < 104.2:
        return "red" if int(t * 9) % 2 else "dead"
    return "dead"


def signal(canvas, height, t):
    c = S.Ctx(G, t, dict(level=-1.2), canvas, height, G["float_mask"])
    c.stand(A.signal, *SIGNAL, signal_state(t))
    g = green(t)
    if t > 96:      # a vine climbs the pole
        sc = G["sc"]; u = u_at(SIGNAL[1])
        x0, y0 = SIGNAL[0] * sc, SIGNAL[1] * sc
        hgt = 3.6 * u * ramp(t, 96, 150)
        pts = [(x0 + math.sin(k * 0.9) * 0.08 * u, y0 - hgt * k / 20) for k in range(21)]
        for a, b in zip(pts, pts[1:]):
            F.line(canvas, a, b, (0.18, 0.5, 0.22), max(1, u * 0.04))
        for k, p in enumerate(pts[2::3]):
            F.ell(canvas, p, 0.06 * u, 0.035 * u, (0.25, 0.62, 0.3), 30 * (-1) ** k, 0)
    if t > 104.5:   # green pushes through the crack under the dead signal
        x0, y0 = SIGNAL[0] * G["sc"], SIGNAL[1] * G["sc"]
        F.sprout(canvas, x0 + 6, y0 + 2, u_at(SIGNAL[1]) * 1.4, ramp(t, 104.5, 110) * (1 + g))


def crane(canvas, t):
    """A tower crane on the skyline, turning slowly in the day, still at night, gone by Day 365."""
    if t > 140:
        return
    L = E.Layer(G["H"], G["W"])
    sw = 0.0
    if t < 30:
        sw = 0.45 * math.sin(t * 0.25)
    elif t < 60:
        sw = 0.45 * math.sin(30 * 0.25)
    else:
        sw = 0.45 * math.sin(30 * 0.25) + 0.1 * math.sin(t * 0.05) * ramp(t, 90, 100)   # loose in storms
    E.crane(L, 1262, 330, 150, 95, 110, t if t < 30 else 30, swing=sw)
    a = L.a * G["sky"]
    canvas[:] = canvas * (1 - a[..., None]) + L.rgb * G["sky"][..., None]


def fountain(canvas, t, day):
    sc = G["sc"]; u = u_at(FOUNTAIN[1])
    x, y = FOUNTAIN[0] * sc, FOUNTAIN[1] * sc
    F.ell(canvas, (x, y - 0.15 * u), 0.9 * u, 0.22 * u, (0.6, 0.62, 0.64), 0, 1.0)
    F.ell(canvas, (x, y - 0.2 * u), 0.75 * u, 0.15 * u, (0.55, 0.5, 0.42) if t < 80 else (0.35, 0.42, 0.4), 0, 0)
    flow = 1.0 if t < 66 else max(0.0, 1 - (t - 66) / 14)
    if flow <= 0:
        return
    rng = np.random.default_rng(int(t * FPS))
    hgt = 1.3 * u * flow
    for i in range(int(110 * flow)):
        ph = rng.random()
        ang = rng.uniform(-0.6, 0.6)
        px = x + math.sin(ang) * 1.0 * u * ph
        py = y - 0.25 * u - hgt * 1.3 * (4 * ph * (1 - ph))
        F.ell(canvas, (px, py), 1.8, 1.8, (0.97, 0.95, 0.9), 0, 0)
    F.line(canvas, (x, y - 0.25 * u), (x, y - 0.25 * u - hgt), (0.95, 0.92, 0.88), max(1, 0.05 * u))


def paper_cup(canvas, t):
    sc = G["sc"]
    wind = math.sin(t * 2.1) * math.sin(t * 0.7)
    if t < 47:
        x, y = CUP_DAY1; ang = 8 * wind; lying = False; fade = 0
    elif t < 50:
        k = ease((t - 47) / 3.0)
        x, y = lerp(CUP_DAY1, (610, 690), k); ang = k * 720; lying = True; fade = 0
    elif t < 96:
        x, y = (610, 690); ang = 0 + 4 * wind; lying = True; fade = 0.2 * ramp(t, 60, 96)
    elif t < 100:     # the storm carries it to the drain
        k = ease((t - 96) / 4.0)
        x, y = lerp((610, 690), (DRAIN[0] + 10, DRAIN[1] - 1), k); ang = k * 900; lying = True; fade = 0.25
    else:
        x, y = DRAIN[0] + 10, DRAIN[1] - 1; ang = 160; lying = True; fade = 0.25 + 0.45 * ramp(t, 100, 150)
    u = u_at(y)
    F.paper_cup(canvas, x * sc, y * sc, u * 1.4, ang, fade, crush=ramp(t, 96, 150), lying=lying)


def drain(canvas, t):
    sc = G["sc"]; u = u_at(DRAIN[1])
    x, y = DRAIN[0] * sc, DRAIN[1] * sc
    F.poly(canvas, [(x - 0.3 * u, y - 0.05 * u), (x + 0.3 * u, y - 0.05 * u), (x + 0.32 * u, y + 0.06 * u),
                    (x - 0.32 * u, y + 0.06 * u)], (0.2, 0.2, 0.22), 0.6)
    for k in range(5):
        F.line(canvas, (x - 0.24 * u + k * 0.12 * u, y - 0.04 * u), (x - 0.24 * u + k * 0.12 * u, y + 0.05 * u),
               (0.4, 0.4, 0.42), 1)
    if t > 135:
        F.sprout(canvas, x + 0.45 * u, y, u * 1.6, ramp(t, 135, 150))


def shop_sign(canvas, E_add, t, nl):
    sc = G["sc"]
    x, y = SHOP_SIGN[0] * sc, SHOP_SIGN[1] * sc
    w, h = 24 * sc, 10 * sc
    on = 1.0 if t < 70 else (1.0 if (t < 71.2 and int(t * 11) % 2) else 0.0)
    F.poly(canvas, [(x - w, y - h), (x + w, y - h), (x + w, y + h), (x - w, y + h)], (0.15, 0.15, 0.17), 0.8)
    if on:
        cv2.rectangle(E_add, (int(x - w + 3), int(y - h + 3)), (int(x + w - 3), int(y + h - 3)), (0.3, 0.55, 1.0), -1)
        cv2.circle(E_add, (int(x), int(y)), int(h * 0.55), (0.45, 0.95, 1.0), -1)
    sw = 0.0
    if t > 85:      # comes loose and swings
        sw = 8 * math.sin(t * 2.4) * ramp(t, 85, 92)
    if sw:
        G["sign_swing"] = sw


def lamps_and_windows(t, nl):
    """Night light (BGR, out res): windows lit one by one / failing, streetlights, the office window."""
    H, W = G["H"], G["W"]
    Eadd = np.zeros((H, W, 3), np.float32)
    frac = window_fraction(t)
    lt = G.get("lt", 0.0)
    if "frac" in EXTRA:
        frac = EXTRA["frac"](lt)
    on = G["win_r"] < frac
    for (x, y, c), o in zip(G["wins"], on):
        if o:
            cv2.rectangle(Eadd, (x, y), (x + G["ww"], y + G["wh"]), c, -1)
    # the art's own lit windows follow the same share
    Eadd += G["em_art"] * min(1.0, frac / 0.8)
    # streetlights (the lamp heads in the art): on at dusk Day 1, fail between Day 7 and Day 30; one near the
    # bridge lasts all year and dies in the last scene; one flickers three times on Day 7
    sc = G["sc"]
    for i, (lx, ly) in enumerate(LAMPS):
        if t < 26.5 + 0.5 * i:
            continue
        if "lamps_off_at" in EXTRA and lt > EXTRA["lamps_off_at"] + 0.3 * i:
            continue
        off = LAMP_OFF[i]
        lv = 1.0 if t < off else 0.0
        if off - 1.2 < t < off:
            lv = float((int(t * 9 + i * 3) % 3) != 0)
        if i == 0:                                    # the last light
            lv = 0.0 if (166.2 < t < 166.45 or 167.0 < t < 167.3 or t > 168.2) else 1.0
        if i == 1 and 62 < t < 64.5:                  # three flickers, then dark
            lv = 1.0 if int((t - 62) * 2.6) % 2 == 0 and t < 63.9 else 0.0
        if lv <= 0:
            continue
        x, y = lx * sc, ly * sc
        cv2.circle(Eadd, (int(x), int(y)), max(2, int(3 * sc)), (0.75, 0.95, 1.0), -1, AA)
        halo = np.zeros((int(120 * sc), int(120 * sc)), np.float32)
        cv2.circle(halo, (halo.shape[1] // 2, halo.shape[0] // 2), int(10 * sc), 1.0, -1)
        halo = cv2.GaussianBlur(halo, (0, 0), 14 * sc) * 2.2 * lv
        y0, x0 = int(y) - halo.shape[0] // 2, int(x) - halo.shape[1] // 2
        ya, xa = max(0, y0), max(0, x0)
        yb, xb = min(G["H"], y0 + halo.shape[0]), min(G["W"], x0 + halo.shape[1])
        Eadd[ya:yb, xa:xb] += halo[ya - y0:yb - y0, xa - x0:xb - x0, None] * np.array([0.35, 0.65, 1.0], np.float32)
        pool = np.zeros((G["H"], G["W"]), np.float32) if False else None
    # the office tower's top window: last light standing, gone on Day ~29
    sc = G["sc"]
    ox, oy = OFFICE_WIN[0] * sc, OFFICE_WIN[1] * sc
    lit = t >= 26 and (t < 81.4 or (81.4 <= t < 82.4 and int(t * 10) % 3 == 0))
    if "office" in EXTRA:
        lit = EXTRA["office"](lt)
    if lit:
        cv2.rectangle(Eadd, (int(ox - 5 * sc), int(oy - 4 * sc)), (int(ox + 5 * sc), int(oy + 4 * sc)), (0.55, 0.85, 1.0), -1)
    # a ceiling fan and a flickering TV in the near tower (Day 2 night)
    if 54 < t < 66:
        tv = 0.5 + 0.5 * math.sin(t * 23) * math.sin(t * 7.3)
        x0, y0 = int(1500 * sc), int(560 * sc)
        cv2.rectangle(Eadd, (x0, y0), (x0 + int(30 * sc), y0 + int(18 * sc)),
                      (0.9 * tv, 0.7 * tv, 0.5 * tv), -1)
        fx, fy = int(1525 * sc), int(388 * sc)
        cv2.rectangle(Eadd, (fx - int(26 * sc), fy - int(4 * sc)), (fx + int(26 * sc), fy + int(22 * sc)), (0.4, 0.7, 0.95), -1)
        a = t * 9
        for k in range(3):
            ang = a + k * 2.094
            cv2.line(Eadd, (fx, fy + int(6 * sc)), (int(fx + math.cos(ang) * 20 * sc), int(fy + 6 * sc + math.sin(ang) * 4 * sc)),
                     (0.05, 0.08, 0.1), max(1, int(3 * sc)), AA)
    return Eadd


# ------------------------------------------------------------------ decay and growth

def weather_and_wear(city, t, day):
    d, g = decay(t), green(t)
    if d <= 0 and g <= 0:
        return city
    H, W = G["H"], G["W"]
    lum = (city @ np.array([0.114, 0.587, 0.299], np.float32))[..., None]
    dusty = lum * np.array([0.78, 0.86, 0.93], np.float32)
    k = 0.32 * d * G["outside"][..., None] * (1 - G["sky"][..., None])
    city = city * (1 - k) + dusty * k
    st = G["streaks"] * d * 0.45
    city = city * (1 - st[..., None])
    rd = G["road"] * d
    city = city * (1 - 0.35 * rd[..., None]) + np.array([0.52, 0.56, 0.6], np.float32) * 0.35 * rd[..., None]
    cr = G["cracks"] * min(1.0, d * 1.3)
    city = city * (1 - cr[..., None] * 0.8) + np.array([0.12, 0.13, 0.14], np.float32) * cr[..., None] * 0.8
    if g > 0:
        gm = np.clip((G["grass_n"] - (1 - g * 0.7)) * 4, 0, 1) * G["grass_zone"] * (G["grass_n2"] > 0.35)
        gm = np.maximum(gm * 0.75, G["cracks_wide"] * min(1.0, g * 1.4))
        tex = 0.6 + 0.8 * G["grass_n2"][..., None]
        col = np.array([0.22, 0.5, 0.32], np.float32) * tex
        city = city * (1 - gm[..., None] * 0.7) + col * gm[..., None] * 0.7
    if d > 0.25:   # dry leaves gather around tyres and the drain
        city = city * (1 - G["leaves"][..., None] * min(1, (d - 0.25) * 2)) + \
            G["leaves_col"] * G["leaves"][..., None] * min(1, (d - 0.25) * 2)
    return city


def pothole(city, t, day):
    if t < 100:
        return city
    sc = G["sc"]; u = u_at(POTHOLE[1])
    m = np.zeros(city.shape[:2], np.float32)
    cv2.ellipse(m, (int(POTHOLE[0] * sc), int(POTHOLE[1] * sc)), (int(0.9 * u), int(0.25 * u)), 0, 0, 360, 1.0, -1, AA)
    m = cv2.GaussianBlur(m, (0, 0), 1.0) * ramp(t, 100, 102)
    sky = np.array([0.92, 0.8, 0.65], np.float32) * (0.5 + 0.5 * day)
    rip = 0.85 + 0.15 * math.sin(t * 3)
    return city * (1 - m[..., None] * 0.85) + sky * rip * m[..., None] * 0.85


# ------------------------------------------------------------------ animals

def sky_birds(canvas, t):
    sc = G["sc"]
    # birds across the skyline (Day 1 morning, Day 2, then more and more)
    flocks = []
    if t < 20:
        flocks += [(t, 0)]
    if 42 < t < 52:
        flocks += [(t - 42, 1)]
    if t > 110:
        flocks += [((t - 110) % 14, 2), ((t - 117) % 14, 3)]
    if t > 166:
        flocks += [(t - 166, 4)]
    for tt, k in flocks:
        rng = np.random.default_rng(40 + k)
        for i in range(7):
            x = (-60 + tt * (120 + 10 * i) + i * 25) * sc
            y = (90 + 40 * k % 150 + 14 * abs(i - 3) + 10 * math.sin(tt + i)) * sc
            if k == 4:   # final: birds settle on the rooftops
                x = (1050 - tt * 70 + i * 22) * sc
                y = (120 + (180 - 120) * min(1.0, tt / 6) + 8 * i % 20) * sc
            if 0 < x < G["W"]:
                F.flying_bird(canvas, x, y, 5 * sc, t + i, (0.15, 0.15, 0.17))


def wildlife(canvas, t, day):
    sc = G["sc"]
    # birds on the bridge railing (Day 2 on)
    if t > 46:
        for i, bx in enumerate((520, 560, 575, 930, 952)):
            if t < 46 + i * 0.6:
                continue
            F.pigeon(canvas, bx * sc, 413 * sc, u_at(413) * 1.5, peck=max(0.0, math.sin(t * 3 + i)) * 0.5)
    if t > 110:
        # pigeons on the dead signal, on rooftops and on the car
        F.pigeon(canvas, (SIGNAL[0] - 4) * sc, (SIGNAL[1] - 100) * sc, u_at(640) * 1.4, peck=max(0, math.sin(t * 2)) * 0.6)
        for i, (px, py) in enumerate(((330, 254), (345, 254), (1005, 205), (1018, 205), (1190, 288))):
            F.pigeon(canvas, px * sc, py * sc, 7 * sc, peck=max(0, math.sin(t * 2.5 + i)) * 0.6)
        # stray dogs trotting along the walk
        for j in range(3):
            k = ((t - 110) * 0.03 + j * 0.06) % 1.3
            if k < 1:
                x, y = lerp((1110, 776), (840, 690), k)
                F.dog(canvas, x * sc, y * sc, u_at(y), t * 9 + j, facing=-1,
                      col=[(0.3, 0.45, 0.62), (0.2, 0.25, 0.3), (0.55, 0.65, 0.75)][j])
        # monkeys on the near building's balconies
        for j, (bx, by) in enumerate(((255, 196), (275, 375), (240, 540))):
            hop = ((t - 110 + j * 3) % 9) / 9
            mx = bx + 25 * math.sin(hop * 2 * math.pi)
            F.monkey(canvas, mx * sc, by * sc, 26 * sc, t * 5 + j, facing=1 if math.cos(hop * 2 * math.pi) > 0 else -1,
                     sitting=hop > 0.6)
        # butterflies by the roadside plants
        for j in range(5):
            bx = 760 + 60 * math.sin(t * 0.5 + j * 1.3) + j * 30
            by = 700 + 15 * math.sin(t * 0.9 + j)
            F.butterfly(canvas, bx * sc, by * sc, 4 * sc, t + j, [(0.2, 0.75, 1.0), (1.0, 0.95, 0.95), (0.3, 0.4, 0.95)][j % 3])
        # birds flitting under the bridge
        for j in range(3):
            x = (470 + 300 * ((t * 0.08 + j * 0.3) % 1.0)) * sc
            F.flying_bird(canvas, x, (470 + 6 * math.sin(t * 2 + j)) * sc, 3.5 * sc, t * 1.4 + j, (0.2, 0.2, 0.22))
    # the deer: in from the riverbank, stops by the car, drinks from the pothole (Month 6)
    if EXTRA.get("deer_flee"):
        lt = G["lt"]
        x0, y0 = POTHOLE[0] + 38, POTHOLE[1] + 2
        if lt < 2.2:     # drinking, then the head comes up at the sound
            hd = 0.95 if lt < 1.0 else 0.95 * (1 - ramp(lt, 1.0, 1.4))
            F.deer(canvas, x0 * sc, y0 * sc, u_at(y0), 0, facing=-1, walking=False, head_down=hd)
        else:            # turns and bolts back to the riverbank
            k = ease((lt - 2.2) / 2.4)
            x, y = lerp((x0, y0), (1010, 708), k)
            F.deer(canvas, x * sc, y * sc, u_at(y), lt * 16, facing=1, walking=True)
        F.pigeon(canvas, 606 * sc, 708 * sc, u_at(708) * 1.2, peck=0)
    elif 121 < t < 135:
        if t < 126:
            k = ease((t - 121) / 5.0)
            x, y = lerp((905, 712), (POTHOLE[0] + 38, POTHOLE[1] + 2), k)
            F.deer(canvas, x * sc, y * sc, u_at(y), t * 7, facing=-1, walking=k < 0.98)
        elif t < 127.5:      # looks around
            x, y = POTHOLE[0] + 38, POTHOLE[1] + 2
            F.deer(canvas, x * sc, y * sc, u_at(y), 0, facing=-1 if int(t * 1.5) % 2 == 0 else 1, walking=False)
        else:
            x, y = POTHOLE[0] + 38, POTHOLE[1] + 2
            F.deer(canvas, x * sc, y * sc, u_at(y), 0, facing=-1, walking=False,
                   head_down=ramp(t, 127.5, 129) * (0.9 + 0.1 * math.sin(t * 4)))
        if t > 129.5:   # a pigeon lands on the car roof
            k = ease((t - 129.5) / 1.2)
            px, py = lerp((660, 600), (606, 708), k)
            F.pigeon(canvas, px * sc, py * sc, u_at(708) * 1.2, peck=0)
    # Day 365: animals crossing without fear
    if t > 140:
        k = ((t - 140) * 0.06) % 1.4
        if k < 1:
            x, y = lerp((830, 720), (520, 700), k)
            F.dog(canvas, x * sc, y * sc, u_at(y), t * 9, facing=-1, col=(0.3, 0.45, 0.62))
        k = ((t - 143) * 0.05) % 1.5
        if 0 < k < 1:
            x, y = lerp((560, 640), (760, 655), k)
            F.deer(canvas, x * sc, y * sc, u_at(y), t * 7, facing=1)


# ------------------------------------------------------------------ frame

def storm(img, t, day):
    if not 91 < t < 101:
        return img
    k = ramp(t, 91, 93) * (1 - ramp(t, 99, 101))
    p = dict(rain=k, rain_col=(0.85, 0.85, 0.85))
    img = R.rain(img, t, p)
    for lt, seed in ((94.2, 2), (97.1, 5)):
        dt = t - lt
        if 0 <= dt < 0.4:
            fl = max(0.0, 1 - dt / 0.12) * 0.7 + (0.4 if 0.16 < dt < 0.24 else 0)
            img = img + fl * (0.25 + R.lightning_bolt(seed, G["sky"])[..., None] * 0.9)
    return img


def crumble(out, lt):
    """A slab of an old far-bank facade breaks away and falls behind the bridge; dust rises."""
    c = EXTRA.get("crumble")
    if c is None or lt < c:
        return out
    sc = G["sc"]
    k = lt - c
    x0, y0, x1, y1 = (np.array([832, 300, 878, 342]) * sc).astype(int)
    if "slab" not in G:
        G["slab"] = out[y0:y1, x0:x1].copy()
    slab = G["slab"]
    out[y0:y1, x0:x1] = out[y0:y1, x0:x1] * 0.35 + np.array([0.1, 0.1, 0.11], np.float32) * 0.65   # the raw hole
    bridge_y = int(410 * sc)
    rng = np.random.default_rng(5)
    hh, ww = slab.shape[:2]
    for i, (a, b) in enumerate(((0, ww // 2), (ww // 2, ww))):
        for j, (cc, dd) in enumerate(((0, hh // 2), (hh // 2, hh))):
            piece = slab[cc:dd, a:b]
            dy = int(0.5 * 520 * sc * (k * (1.0 + 0.15 * (i + j))) ** 2)
            dx = int((i - 0.5) * 30 * sc * k)
            ang = (i - 0.5) * 80 * k
            M = cv2.getRotationMatrix2D(((b - a) / 2, (dd - cc) / 2), ang, 1.0)
            pr = cv2.warpAffine(piece, M, (b - a, dd - cc), borderValue=(0, 0, 0))
            pm = cv2.warpAffine(np.ones(piece.shape[:2], np.float32), M, (b - a, dd - cc))
            yy, xx = y0 + cc + dy, x0 + a + dx
            ya, yb = max(0, yy), min(bridge_y, yy + (dd - cc))
            if yb <= ya:
                continue
            sub = pm[ya - yy:yb - yy, :, None]
            out[ya:yb, xx:xx + (b - a)] = out[ya:yb, xx:xx + (b - a)] * (1 - sub) + pr[ya - yy:yb - yy] * sub
    if k > 0.4:                                           # dust rising where it hit
        d = np.zeros(out.shape[:2], np.float32)
        r = (12 + 40 * min(k - 0.4, 3)) * sc
        cv2.ellipse(d, (int(855 * sc), int(400 * sc - r * 0.4)), (int(r * 1.4), int(r * 0.8)), 0, 0, 360, 1.0, -1)
        d = cv2.GaussianBlur(d, (0, 0), 10 * sc) * max(0.0, 1 - (k - 0.4) / 6) * 0.7
        out = out * (1 - d[..., None]) + np.array([0.62, 0.66, 0.7], np.float32) * d[..., None]
    return out


def text(frame, t):
    if os.environ.get("W4B_NO_TEXT"):
        return frame
    W, H, sc = G["W"], G["H"], G["sc"]
    i = max(k for k, s in enumerate(MARKERS) if s[0] <= t)
    start, label = MARKERS[i]
    nxt = MARKERS[i + 1][0] if i + 1 < len(MARKERS) else DURATION
    items = []
    if label:
        a = ease((t - start - 0.3) / 0.6) * ease((nxt - t - 0.2) / 0.5)
        items.append((label, a, (int(250 * sc), int(70 * sc)), int(46 * sc), False))
    for j, (t0, line) in enumerate(FINAL):
        if t >= t0:
            a = ease((t - t0) / 1.0)
            items.append((line, a, (0, int((150 + 62 * j) * sc)), int(50 * sc), True))
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


def plant_sway(f, t):
    """Only in the final hold: the plant's leaves move a little in the breeze."""
    if t < 165:
        return f
    sc = G["sc"]
    x0, y0, x1, y1 = (np.array(G["cfg"]["plant_box"]) * sc).astype(int)
    sub = f[y0:y1, x0:x1]
    yy, xx = np.mgrid[0:sub.shape[0], 0:sub.shape[1]].astype(np.float32)
    amp = 3.0 * sc * (1 - yy / sub.shape[0]) ** 1.5
    dx = amp * math.sin(t * 1.6) + amp * 0.4 * np.sin(t * 3.1 + xx * 0.02)
    m = G["plant"][y0:y1, x0:x1]
    w = cv2.remap(sub, xx - dx, yy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    mm = np.maximum(m, cv2.remap(m, xx - dx, yy, cv2.INTER_LINEAR))[..., None]
    f[y0:y1, x0:x1] = sub * (1 - mm) + w * mm
    return f


def render(t):
    if EXTRA:
        G["lt"] = t - EXTRA["t0"]
        t = EXTRA["world"] + G["lt"] * EXTRA.get("rate", 1.0)
    day, night = tod(t)
    sunset = max(0.0, 1 - day - night)
    nl = min(1.0, night * 1.25)
    city = G["city_img"].copy()
    height = G["height"].copy()
    G["float_mask"] = np.zeros(height.shape, np.float32)
    traffic(city, height, t, nl)
    bus(city, height, t)
    street_people(city, height, t)
    city = weather_and_wear(city, t, day)
    signal(city, height, t)
    drain(city, t)
    paper_cup(city, t)
    fountain(city, t, day)
    Eadd = lamps_and_windows(t, nl)
    shop_sign(city, Eadd, t, nl)
    city = pothole(city, t, day)
    wildlife(city, t, day)
    # the vines over cars, the near building and the bridge rail (Ep 1's vine layer)
    vk = green(t)
    if vk > 0:
        lay, a = G["vines"]
        city = city * (1 - (a * vk)[..., None]) + lay * (a * vk)[..., None]
    graded = E.grade(city, day, night)
    if 91 < t < 101:
        graded = graded * (1 - 0.35 * ramp(t, 91, 93) * (1 - ramp(t, 99, 101)))
    skyimg = E.sky(t, day, night, sunset, G["city_img"])
    graded = graded * (1 - G["sky"][..., None]) + skyimg * G["sky"][..., None]
    storm_k = ramp(t, 91, 93) * (1 - ramp(t, 99, 101))
    if storm_k > 0:
        grey = np.array([0.55, 0.53, 0.5], np.float32)
        graded = graded * (1 - G["sky"][..., None] * storm_k * 0.8) + grey * G["sky"][..., None] * storm_k * 0.8
    crane(graded, t)
    sky_birds(graded, t)
    lights_on = nl
    out = graded + Eadd * lights_on + cv2.GaussianBlur(Eadd, (0, 0), 3 * G["sc"]) * 0.5 * lights_on
    wc = np.array([0.6, 0.48, 0.34], np.float32) * (1 - 0.75 * night) + np.array([0.3, 0.35, 0.45], np.float32) * sunset * 0.3
    pw = dict(level=-1.2, river_mix=0.75, puddles=0.0, water=tuple(wc), water_alpha=0.75, rings=0.0)
    out = R.water(out, t, pw, height)
    out = storm(out, t, day)
    if EXTRA:
        out = crumble(out, G["lt"])
    f = E.room(out, day, night, t)
    f = plant_sway(f, t)
    f = text(f, t)
    if t > DURATION - 2.5:
        f = f * ease((DURATION - t) / 2.5)
    return (np.clip(f, 0, 1) * 255).astype(np.uint8)


# ------------------------------------------------------------------ setup

def init(masks):
    cfg = SCENES["h"]
    cfg["vine_zones"] = [((168, 40, 318, 720), 26), ((1442, 300, 1598, 800), 18), ((300, 412, 1075, 440), 14),
                         ((498, 611, 597, 688), 10), ((561, 706, 649, 761), 6), ((440, 590, 560, 640), 6)]
    E.init(masks)
    H, W, sc = G["H"], G["W"], G["sc"]
    rng = np.random.default_rng(31)
    # window lights: little rects on the buildings, each with its own switch-on order
    bld = (1 - G["sky"]) * G["outside"] * (G["yy"] < 400 * sc) * (G["xx"] > 228 * sc) * (G["xx"] < 1440 * sc)
    wins = []
    for _ in range(2200):
        x, y = int(rng.uniform(228, 1440) * sc), int(rng.uniform(20, 398) * sc)
        if bld[y, x] > 0.9 and G["canopy"][y, x] < 0.1:
            c = (0.45, 0.78, 1.0) if rng.random() < 0.6 else (1.0, 0.95, 0.8)
            wins.append((x, y, tuple(v * 1.0 for v in c)))
    G["wins"] = wins; G["ww"] = max(2, int(3 * sc)); G["wh"] = max(2, int(2 * sc))
    G["win_r"] = rng.random(len(wins))
    keep = np.zeros((H, W), np.float32); keep[: int(470 * sc)] = 1.0
    for k in ("tower", "near_building"):
        cv2.fillPoly(keep, [(np.array(G["cfg"][k]) * sc).astype(np.int32)], 1.0)
    G["em_art"] = (G["emissive"] * keep)[..., None] * G["city_img"] * 0.6 * (1 - G["em_lamp"][..., None])
    # streetlights: each lamp component gets a failing time; the one nearest the bridge lasts all year
    lab = G["light_lab"]
    ids = np.unique(lab[G["em_lamp"] > 0.3])
    ids = ids[ids > 0]
    ys, xs = np.nonzero(lab)
    cx = np.bincount(lab[ys, xs], xs, lab.max() + 1) / np.maximum(np.bincount(lab[ys, xs], None, lab.max() + 1), 1)
    cy = np.bincount(lab[ys, xs], ys, lab.max() + 1) / np.maximum(np.bincount(lab[ys, xs], None, lab.max() + 1), 1)
    G["lamp_ids"] = ids
    G["lamp_lut"] = np.zeros(lab.max() + 1)
    G["em_lamp_raw"] = (lab > 0).astype(np.float32) * G["emissive"]
    d = [(cx[i] - 700 * sc) ** 2 + (cy[i] - 520 * sc) ** 2 for i in ids]
    G["last_lamp"] = ids[int(np.argmin(d))] if len(ids) else -1
    G["flicker_lamp"] = ids[int(np.argmax([cy[i] for i in ids]))] if len(ids) else -1
    G["lamp_off"] = rng.uniform(64, 84, len(ids))
    # wear textures
    road = np.zeros((H, W), np.float32)
    cv2.fillPoly(road, [(np.array(G["cfg"]["road_clip"]) * sc).astype(np.int32)], 1.0)
    G["road"] = cv2.GaussianBlur(road, (0, 0), 2) * G["outside"]
    cr = np.zeros((H, W), np.float32); crw = np.zeros((H, W), np.float32)
    for _ in range(40):
        x, y = rng.uniform(430, 760), rng.uniform(560, 760)
        pts = [(x, y)]
        for k in range(rng.integers(4, 9)):
            pts.append((pts[-1][0] + rng.uniform(-12, 12), pts[-1][1] + rng.uniform(-6, 6)))
        p = (np.array(pts) * sc).astype(np.int32)
        cv2.polylines(cr, [p], False, 1.0, 1, AA)
        cv2.polylines(crw, [p], False, 1.0, max(2, int(3 * sc)), AA)
    G["cracks"] = cr * G["road"]
    G["cracks_wide"] = cv2.GaussianBlur(crw, (0, 0), 1.0) * G["road"]
    n1 = E.R.fbm(H, W, 51, 5, 20); n2 = E.R.fbm(H, W, 52, 4, 60)
    G["grass_n"], G["grass_n2"] = n1, n2
    zone = np.clip(G["ground"] + G["road"] * 0.6, 0, 1) * G["outside"]
    G["grass_zone"] = cv2.GaussianBlur(zone, (0, 0), 2)
    st = np.zeros((H, W), np.float32)
    for _ in range(900):
        x, y = int(rng.uniform(165, 1600) * sc), int(rng.uniform(20, 420) * sc)
        L = int(rng.uniform(20, 70) * sc)
        cv2.line(st, (x, y), (x + int(rng.uniform(-2, 2)), y + L), rng.uniform(0.3, 1.0), max(1, int(rng.uniform(1, 3) * sc)), AA)
    G["streaks"] = cv2.GaussianBlur(st, (0, 0), 1.5) * (1 - G["sky"]) * G["outside"] * (G["emissive"] < 0.5)
    lv = np.zeros((H, W), np.float32)
    for cxm, cym, n in ((520, 688, 40), (600, 760, 30), (DRAIN[0], DRAIN[1], 30), (BUS_STOP[0], BUS_STOP[1], 30)):
        for _ in range(n):
            x, y = (cxm + rng.normal(0, 18)) * sc, (cym + rng.normal(0, 3)) * sc
            cv2.ellipse(lv, (int(x), int(y)), (int(3 * sc), int(1.5 * sc)), rng.uniform(0, 180), 0, 360, 1.0, -1, AA)
    G["leaves"] = lv * G["outside"]
    G["leaves_col"] = np.array([0.2, 0.4, 0.6], np.float32)


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
