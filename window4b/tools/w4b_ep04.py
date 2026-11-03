"""Window 4B Ep 4 renderer: "What If a Dust Storm Covered the Entire City?"

    python window4b/tools/w4b_ep04.py MASKS_h.npz OUT.mp4 [--start S --end E] [--still T ...] [--jobs 4]

Same locked 16:9 master and engine as Eps 1-3. The storm is a depth-based dust haze (far things vanish
first), an approaching dust wall, wind streaks, dust gathering on the glass and the sill, and sand that
rises over the street using the per-pixel height map (so cars, poles and the signal are buried from the
ground up). Positions are master px (1672 x 941) unless they say "out".
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

MARKERS = [(0, "DAY 1  |  8:00 AM"), (20, "DAY 1  |  11:00 AM"), (40, "DAY 1  |  AFTERNOON"), (65, "DAY 2"),
           (81, "DAY 7"), (90, "WEEK 2"), (104, "MONTH 1"), (115, "MONTH 2"), (128, "MONTH 3"), (140, "MONTH 6"),
           (165, "ONE YEAR LATER"), (168, None)]
FINAL = [(168.5, "ONE CITY."), (171.0, "ONE STORM."), (173.5, "A WORLD BURIED IN DUST.")]

SIGNAL = (470, 640)
LAMPS = [(468, 556), (603, 598), (1033, 648), (1352, 547)]
SUN = (1303, 316)
GAP = (1060, 270)                # where a building shows through a gap in the dust (Scene 3)
# Extra beats for the Shorts (w4b_ep04_extras.py sets this): world time = EXTRA["world"] + lt * rate, and
# any of density / wind / coat / sand may be overridden as functions of the local time lt (G["lt"]).
EXTRA = {}


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def ramp(t, a, b):
    return ease((t - a) / (b - a)) if b > a else float(t >= a)


def lerp(a, b, u):
    return a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u


def u_at(y_m):
    return G["s"](y_m) * G["sc"] * 1.2


def interp(t, ts, vs):
    return float(np.interp(t, ts, vs))


def interp3(t, ts, cols):
    return np.array([np.interp(t, ts, [c[i] for c in cols]) for i in range(3)], np.float32)


# ------------------------------------------------------------------ timeline

def night(t):
    if 65 <= t < 89:                        # Days 2-7: days and nights under the dust
        return 0.5 - 0.5 * math.cos(2 * math.pi * (t - 65) / 4.8)
    if 115 <= t < 140:                      # Months 2-3: barely any difference
        return 0.25 + 0.15 * math.sin(2 * math.pi * (t - 115) / 6.0)
    return 0.0


def gustiness(t):
    return 0.75 + 0.25 * math.sin(t * 1.7) * math.sin(t * 0.43 + 1)


def density(t):
    """Dust optical density for the whole city (far things count more, see depth)."""
    if "density" in EXTRA:
        return EXTRA["density"](G["lt"])
    base = interp(t, [0, 20, 30, 38, 40, 42.5, 64, 70, 82, 87, 89, 114, 116, 140, 150, 160, 180],
                  [0.0, 0.05, 0.3, 0.6, 0.8, 3.6, 3.6, 3.0, 2.6, 1.2, 0.9, 1.4, 3.2, 3.2, 1.5, 0.85, 0.8])
    if 89 <= t < 114:                       # storm waves, Week 2 -> Month 1
        base += 1.6 * max(0.0, math.sin(2 * math.pi * (t - 89) / 6.2)) ** 2
    if 42 < t < 150:
        base *= gustiness(t)
    return base


def wind(t):
    if "wind" in EXTRA:
        return EXTRA["wind"](G["lt"])
    return interp(t, [0, 18, 26, 38, 41, 64, 82, 88, 114, 140, 150, 160, 176, 177.5, 180],
                  [0.1, 0.12, 0.4, 0.8, 1.0, 1.0, 0.85, 0.5, 0.75, 0.6, 0.35, 0.15, 0.15, 0.6, 0.0])


def dust_col(t):
    c = interp3(t, [0, 30, 39, 43, 90, 114, 118, 140, 155, 180],
                [(0.62, 0.78, 0.9), (0.55, 0.76, 0.93), (0.4, 0.66, 0.92), (0.22, 0.47, 0.84), (0.26, 0.5, 0.82),
                 (0.24, 0.47, 0.8), (0.1, 0.25, 0.55), (0.12, 0.27, 0.55), (0.42, 0.6, 0.84), (0.46, 0.63, 0.86)])
    return c * (1 - 0.85 * night(t))


def ambient(t):
    a = interp(t, [0, 20, 38, 42, 65, 89, 114, 118, 140, 152, 165, 180],
               [1.0, 1.0, 0.8, 0.5, 0.5, 0.55, 0.55, 0.3, 0.3, 0.7, 0.8, 0.8])
    return a * (1 - 0.85 * night(t))


def sand_level(t):
    if "sand" in EXTRA:
        return EXTRA["sand"](G["lt"])
    return interp(t, [0, 65, 88, 102, 114, 140, 152, 165, 180], [-9, -9, 0.25, 0.8, 1.3, 2.2, 2.6, 2.9, 3.0])


def coat(t):
    if "coat" in EXTRA:
        return EXTRA["coat"](G["lt"])
    return interp(t, [0, 42, 64, 88, 114, 140, 180], [0, 0.08, 0.2, 0.35, 0.5, 0.65, 0.7])


def glass_dust(t):
    return interp(t, [0, 42, 64, 88, 114, 140, 155, 180], [0, 0.08, 0.15, 0.22, 0.28, 0.35, 0.25, 0.2])


def glass_film(t):
    return interp(t, [0, 115, 135, 150, 165, 180], [0, 0, 0.45, 0.3, 0.18, 0.18])


def sill_dust(t):
    return interp(t, [0, 66, 89, 114, 140, 165, 180], [0, 0.05, 0.18, 0.28, 0.4, 0.48, 0.5])


# ------------------------------------------------------------------ the living city (Scene 1-2)

def traffic(canvas, height, t):
    mode = "busy" if t < 41 else "stuck"
    p = dict(traffic=mode, headlights=0.0, lights=0.0, level=-1.2)
    R.traffic(canvas, t if t < 41 else 41, p, height)


def signal_state(t):
    ph = t % 8 if t < 89 else ((t - 89) * 2.5) % 8
    return "green" if ph < 4 else ("amber" if ph < 5 else "red")


def signal(canvas, height, t):
    c = S.Ctx(G, t, dict(level=-1.2), canvas, height, G["float_mask"])
    c.stand(A.signal, *SIGNAL, signal_state(t))


def crane(canvas, t):
    L = E.Layer(G["H"], G["W"])
    sw = 0.45 * math.sin(min(t, 41) * 0.25) + 0.08 * math.sin(t * 0.9) * ramp(t, 26, 40)
    E.crane(L, 1262, 330, 150, 95, 110, min(t, 41), swing=sw)
    canvas[:] = canvas * (1 - (L.a * G["sky"])[..., None]) + L.rgb * G["sky"][..., None]


def birds(canvas, t):
    """Morning flock over the river turns away from the haze at ~12 s and flees."""
    sc = G["sc"]
    if t > 22:
        return
    for i in range(9):
        if t < 12:
            x = 360 + t * 55 + i * 18
            y = 330 + 10 * abs(i - 4) + 6 * math.sin(t * 2 + i)
        else:
            k = t - 12
            x = 360 + 12 * 55 + i * 18 - k * 120 - k * k * 6
            y = 330 + 10 * abs(i - 4) - k * 22
        if 165 < x < 1600 and y > 0:
            F.flying_bird(canvas, x * sc, y * sc, 5 * sc, t * 1.3 + i, (0.15, 0.15, 0.17))


def leaves(canvas, t):
    if not 26 < t < 44:
        return
    sc = G["sc"]
    rng = np.random.default_rng(3)
    k = ramp(t, 26, 32)
    for i in range(int(30 * k)):
        x0 = rng.uniform(380, 1400); y0 = rng.uniform(560, 790); v = rng.uniform(80, 160)
        x = 1450 - ((1450 - x0 + (t - 26) * v) % 1100)
        y = y0 + 4 * math.sin(t * 9 + i) - abs(math.sin(t * 5 + i)) * 6
        col = (0.2, 0.42, 0.62) if i % 3 else (0.9, 0.92, 0.92)
        F.ell(canvas, (x * sc, y * sc), 2.6 * sc, 1.2 * sc, col, t * 400 % 360, 0)


# ------------------------------------------------------------------ dust

def sand(city, height, t):
    """Sand rising over the street from the ground up (dunes from noise), and closing over the river."""
    L = sand_level(t)
    if L < -5:
        return city
    dune = (G["dune_n"] - 0.5) * 0.7
    m = ((height + dune < L) & (height > -1.15)).astype(np.float32)
    q = interp(t, [0, 88, 140, 165, 180], [0, 0.05, 0.45, 0.72, 0.75])
    m = np.maximum(m, (G["river_dist"] < q * G["river_maxd"]).astype(np.float32) * G["river"])
    m = cv2.GaussianBlur(m, (0, 0), 1.2) * G["outside"]
    col = np.array([0.42, 0.6, 0.76], np.float32) * (0.82 + 0.3 * G["dune_n2"][..., None])
    col = col * (1 + 0.05 * G["ripples"][..., None])
    return city * (1 - m[..., None]) + col * m[..., None]


def coat_city(city, t):
    c = coat(t)
    if c <= 0:
        return city
    lum = (city @ np.array([0.114, 0.587, 0.299], np.float32))[..., None]
    tan = lum * np.array([0.72, 0.92, 1.12], np.float32) + 0.05
    k = c * G["outside"][..., None] * (1 - G["sky"][..., None]) * (0.55 + 0.45 * G["tops"][..., None])
    return city * (1 - k) + tan * k


def wall(city, t):
    """Scene 2: a brown haze on the horizon that becomes a moving wall and swallows the skyline."""
    if not 4 < t < 43:
        return city
    sc, W, H = G["sc"], G["W"], G["H"]
    hz = 400 * sc
    rows = G["yy"]
    col = interp3(t, [4, 25, 38, 43], [(0.45, 0.6, 0.72), (0.38, 0.58, 0.78), (0.28, 0.5, 0.8), (0.22, 0.47, 0.84)])
    if t < 22:     # faint band beyond the skyline
        a = 0.22 * ramp(t, 4, 18) * np.exp(-((rows - hz) / (55 * sc)) ** 2) * G["sky"]
        return city * (1 - a[..., None]) + col * a[..., None]
    hgt = interp(t, [22, 30, 37, 40], [40, 160, 380, 520]) * sc
    off = int(t * 22 * sc) % W
    edge = np.roll(G["wall_edge"], -off)
    top = hz - hgt * (0.7 + 0.6 * edge)
    tex = np.roll(G["clouds"][1], -int(t * 30 * sc) % W, axis=1)[:, :W]
    a = np.clip((rows - top[None, :]) / (40 * sc), 0, 1) * (0.75 + 0.25 * tex)
    reach = interp(t, [22, 37, 39.5, 42], [0.97, 0.9, 0.62, 0.0])        # how near the wall has come
    a = a * np.clip((G["depth"] - reach) * 12, 0, 1) * ramp(t, 22, 27)
    shade = col * (0.85 + 0.35 * tex[..., None]) * (1 - 0.25 * np.clip((rows - top[None, :]) / (200 * sc), 0, 1))[..., None]
    return city * (1 - a[..., None]) + shade * a[..., None]


def haze(city, t):
    d = density(t)
    if d <= 0.001:
        return city
    W, sc = G["W"], G["sc"]
    turb = np.roll(G["clouds"][0], -int(t * 60 * sc * (0.3 + wind(t))) % W, axis=1)[:, :W]
    dens = d * G["depth"] * (0.75 + 0.5 * turb)
    if 51.5 < t < 55.5:     # a gap opens: a building shows for a moment, then the next wall sweeps across
        g = ramp(t, 51.5, 52.5) * (1 - ramp(t, 53.8, 55.0))
        dens = dens * (1 - 0.72 * g * G["gap"] * (1 - G["sky"]))
    if "front" in EXTRA:         # a wave of dust sweeping across the view
        fx, k, d_ = EXTRA["front"](G["lt"])
        side = np.clip((fx * G["W"] - G["xx"]) * d_ / (170 * G["sc"]), 0, 1) if d_ > 0 else \
            np.clip((G["xx"] - fx * G["W"]) / (170 * G["sc"]), 0, 1)
        dens = dens + k * side * (0.6 + 0.8 * turb) * np.maximum(G["depth"], 0.5)
    a = 1 - np.exp(-dens)
    col = dust_col(t) * (0.85 + 0.3 * turb[..., None])
    return city * (1 - a[..., None]) + col * a[..., None]


def streaks(img, t):
    w = wind(t) * ramp(t, 30, 41)
    if w <= 0.02 or t > 176:
        return img
    W, H, sc = G["W"], G["H"], G["sc"]
    out = img
    col = dust_col(t) * 1.3 + 0.08
    for i, (tex, spd) in enumerate(zip(G["streak"], (700, 1100))):
        off = int(t * spd * sc * (0.5 + w)) % W
        r = np.roll(tex, -off, axis=1)
        r = np.roll(r, int(t * 40 * sc) % H, axis=0)
        out = out + (r * w * (0.35, 0.5)[i] * G["outside"])[..., None] * (col - out * 0.5)
    return out


def sun(img, t):
    k = ramp(t, 116, 119) * (1 - ramp(t, 126, 136))
    if k <= 0:
        return img
    sc = G["sc"]
    m = np.zeros(img.shape[:2], np.float32)
    cv2.circle(m, (int(SUN[0] * sc), int(SUN[1] * sc)), int(30 * sc), 1.0, -1, AA)
    m = cv2.GaussianBlur(m, (0, 0), 3 * sc)
    glow = cv2.GaussianBlur(m, (0, 0), 25 * sc)
    return img + (m * 0.45 + glow * 0.5)[..., None] * k * np.array([0.45, 0.72, 0.95], np.float32)


def lamps(img, t):
    if not 41 < t < 140:
        return img
    sc = G["sc"]
    vis = np.exp(-density(t) * 0.45)
    E_ = np.zeros(img.shape[:2], np.float32)
    for lx, ly in LAMPS:
        cv2.circle(E_, (int(lx * sc), int(ly * sc)), max(2, int(3 * sc)), 1.0, -1, AA)
    k = ramp(t, 41, 42.5) * (1 - ramp(t, 136, 140))
    halo = cv2.GaussianBlur(E_, (0, 0), 18 * sc) * 6 + E_ * vis
    return img + halo[..., None] * np.array([0.45, 0.75, 1.0], np.float32) * k * (0.35 + 0.65 * vis)


def glass(img, t):
    """Dust on the window: specks that build up, drifts along the frame edges, a film in Months 2-3."""
    g = glass_dust(t)
    if g <= 0:
        return img
    col = np.array([0.5, 0.66, 0.8], np.float32) * (0.4 + 0.6 * ambient(t)) + 0.04
    sp = (G["speck"] < g).astype(np.float32) * 0.85
    edge = np.clip(G["edge"] * (0.3 + 1.4 * g) - 0.15, 0, 1)
    f = glass_film(t)
    a = np.clip(np.maximum(sp, edge) + f, 0, 1) * G["outside"]
    if f > 0:
        img = img * (1 - (f * G["outside"])[..., None]) + cv2.GaussianBlur(img, (0, 0), 4 * G["sc"]) * (f * G["outside"])[..., None]
    return img * (1 - a[..., None] * 0.8) + col * a[..., None] * 0.8


def room(out, t):
    am = ambient(t)
    img = G["room_img"]
    warm = np.array(interp3(t, [0, 30, 42, 114, 118, 150, 180],
                            [(1, 1, 1), (0.92, 0.98, 1.05), (0.75, 0.92, 1.15), (0.78, 0.93, 1.12), (0.65, 0.85, 1.15),
                             (0.8, 0.92, 1.08), (0.85, 0.94, 1.05)]), np.float32)
    r = img * warm * (0.35 + 0.65 * am)
    # dust on the sill and a fine coat on the plant
    s = sill_dust(t)
    if s > 0:
        tan = np.array([0.55, 0.7, 0.82], np.float32) * (0.4 + 0.6 * am)
        k = (G["sill"] * s * (0.7 + 0.6 * G["dune_n2"]))[..., None]
        r = r * (1 - k) + tan * k
        pk = (G["plant"] * s * 1.2)[..., None]
        lum = (r @ np.array([0.114, 0.587, 0.299], np.float32))[..., None]
        r = r * (1 - pk) + lum * np.array([0.75, 0.9, 1.05], np.float32) * pk
    a = (1 - G["outside"])[..., None]
    f = out * (1 - a) + r * a
    # the plant shakes in the wind (Scene 3 on) and sways gently at the end
    w = wind(t) * ramp(t, 40, 42) if t < 165 else 0.25
    if w > 0.05:
        sc = G["sc"]
        x0, y0, x1, y1 = (np.array(G["cfg"]["plant_box"]) * sc).astype(int)
        sub = f[y0:y1, x0:x1]
        yy, xx = np.mgrid[0:sub.shape[0], 0:sub.shape[1]].astype(np.float32)
        amp = (2.0 + 4.0 * w) * sc * (1 - yy / sub.shape[0]) ** 1.5
        dx = amp * math.sin(t * (2 + 6 * w)) + amp * 0.5 * np.sin(t * 9 * w + xx * 0.03)
        m = G["plant"][y0:y1, x0:x1]
        ww = cv2.remap(sub, xx - dx, yy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        mm = np.maximum(m, cv2.remap(m, xx - dx, yy, cv2.INTER_LINEAR))[..., None]
        f[y0:y1, x0:x1] = sub * (1 - mm) + ww * mm
    if 42 < t < 64 and int(t * 30) % 3 == 0:     # the mug rattles on the sill
        x0, y0, x1, y1 = G["mug_box"]
        d = 1 if int(t * 47) % 2 else -1
        f[y0:y1, x0 + d:x1 + d] = f[y0:y1, x0:x1].copy()
    return f


# ------------------------------------------------------------------ frame

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
            items.append((line, ease((t - t0) / 1.0), (0, int((150 + 62 * j) * sc)), int(52 * sc), True))
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
    if EXTRA:
        G["lt"] = t - EXTRA.get("t0", 0.0)
        t = EXTRA["world"] + G["lt"] * EXTRA.get("rate", 1.0)
    city = G["city_img"].copy()
    height = G["height"].copy()
    G["float_mask"] = np.zeros(height.shape, np.float32)
    traffic(city, height, t)
    signal(city, height, t)
    leaves(city, t)
    city = E.grade(city, 1.0, 0.0)
    skyimg = E.sky(min(t, 41), 1.0, 0.0, 0.0, G["city_img"])
    city = city * (1 - G["sky"][..., None]) + skyimg * G["sky"][..., None]
    crane(city, t)
    birds(city, t)
    if t < 44:     # the river roughens in the wind
        w = wind(t)
        n = np.roll(G["ripples"], int(t * 40), axis=1)
        city = city + (n * 0.07 * w * G["river"])[..., None]
    city = coat_city(city, t)
    city = sand(city, height, t)
    city = city * ambient(t)
    city = wall(city, t)
    city = haze(city, t)
    city = sun(city, t)
    city = lamps(city, t)
    city = streaks(city, t)
    city = glass(city, t)
    f = room(city, t)
    f = text(f, t)
    if t > DURATION - 2.5 and not EXTRA:
        f = f * ease((DURATION - t) / 2.5)
    if "fade_at" in EXTRA:
        f = f * (1 - ramp(G["lt"], EXTRA["fade_at"], EXTRA["fade_at"] + 1.5))
    return (np.clip(f, 0, 1) * 255).astype(np.uint8)


def init(masks):
    E.init(masks)
    H, W, sc = G["H"], G["W"], G["sc"]
    rng = np.random.default_rng(44)
    ym = G["yy"] / sc
    depth = np.interp(ym, [0, 400, 470, 560, 700, 810], [1.0, 1.0, 0.85, 0.6, 0.42, 0.35]).astype(np.float32)
    for k in ("tower", "near_building"):
        m = np.zeros((H, W), np.uint8)
        cv2.fillPoly(m, [(np.array(G["cfg"][k]) * sc).astype(np.int32)], 1)
        depth[m > 0] = 0.24
    depth = np.where(G["sky"] > 0.5, 1.25, depth)
    G["depth"] = cv2.GaussianBlur(depth.astype(np.float32), (0, 0), 2) * G["outside"]
    G["dune_n"] = R.fbm(H, W, 61, 4, 6)
    G["dune_n2"] = R.fbm(H, W, 62, 5, 40)
    rip = np.sin(G["yy"] * 0.28 + G["xx"] * 0.03 + 9 * R.fbm(H, W, 63, 3, 10)).astype(np.float32)
    G["ripples"] = rip
    rv = (G["river"] > 0.5).astype(np.uint8)
    G["river_dist"] = cv2.distanceTransform(rv, cv2.DIST_L2, 5)
    G["river_maxd"] = float(G["river_dist"].max())
    up = np.roll(G["sky"], 3, axis=0)
    G["tops"] = cv2.GaussianBlur(np.clip(up - G["sky"], 0, 1), (0, 0), 2) + 0.2
    edge1 = R.fbm(1, W * 2, 64, 6, 16)[0]
    G["wall_edge"] = np.interp(np.arange(W), np.arange(W * 2) / 2, edge1).astype(np.float32)
    gap = np.zeros((H, W), np.float32)
    cv2.ellipse(gap, (int(GAP[0] * sc), int(GAP[1] * sc)), (int(150 * sc), int(220 * sc)), 0, 0, 360, 1.0, -1)
    gap = gap * (0.6 + 0.8 * R.fbm(H, W, 66, 4, 12))
    G["gap"] = np.clip(cv2.GaussianBlur(gap, (0, 0), 70 * sc) * 1.6, 0, 1)
    G["streak"] = [R.rain_texture(H, W, 1400, 40 * sc, 1, 82, 71, 0.5), R.rain_texture(H, W, 300, 90 * sc, 2, 84, 72, 0.6)]
    sp = np.full((H, W), 2.0, np.float32)
    for _ in range(9000):
        x, y = int(rng.uniform(0, W)), int(rng.uniform(0, H))
        cv2.circle(sp, (x, y), int(rng.uniform(1, 2.6) * sc), float(rng.random()), -1)
    G["speck"] = sp
    o = (G["outside"] > 0.5).astype(np.uint8)
    dist = cv2.distanceTransform(o, cv2.DIST_L2, 5)
    G["edge"] = (np.exp(-dist / (28 * sc)) * (0.7 + 0.6 * R.fbm(H, W, 65, 4, 30))).astype(np.float32)
    sill = np.zeros((H, W), np.float32)
    cv2.fillPoly(sill, [(np.array([(160, 735), (1600, 815), (1600, 870), (160, 790)]) * sc).astype(np.int32)], 1.0)
    G["sill"] = cv2.GaussianBlur(sill, (0, 0), 8 * sc) * (1 - G["outside"]) * (1 - G["plant"])
    G["mug_box"] = tuple(int(v * sc) for v in (305, 690, 440, 850))


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
