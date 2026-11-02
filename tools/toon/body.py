"""Thatha's whole-body action library, made in code from the owner's drawings – no GPU (owner 2026-11-02: "code and
animate these shots… create for others and keep it ready to use in future videos").

The drawing is never cut into limb pieces: soft, overlapping region weights (feet, veshti hem, stick + its hand, free
arm, head, torso) each get a small motion per frame and the picture is bent smoothly with one blended displacement
field, solved for the destination (fixed-point inverse warp) – so there are no visible joints. Props stay rigid
(bending the stick smeared it). In the side view the slippers are rigid layers UNDER the veshti (the hem hides the
ankles) and a darker copy is the far foot.

Usage:
    python tools/toon/body.py ACTION [ACTION ...]        # renders assets/actions/<ACTION>.webm (+ _preview.mp4)
    python tools/toon/body.py all
    python tools/toon/body.py ACTION --still T OUT.png   # one frame for checking
Actions (front = owner's 01_front.png; side = the profile on 08_turnaround.png, facing LEFT – flip to walk right):
    walk_front   walking towards the camera, stick in hand (seamless 1.1 s two-step loop)
    walk_side    walking to the left in profile (seamless 1.0 s loop; "speed" in the json = ground speed)
    idle         standing, breathing, a slow weight shift (seamless 4 s loop)
    laugh        a big belly laugh: eyes squeeze shut, mouth open, head back, shoulders bounce (2.4 s)
    bow          a respectful nod-bow (vanakkam) – head and chest dip and come up (1.8 s)
    tap          lifts the stick (fist and stick together) and strikes the ground twice, dust puffs (1.6 s) –
                 add sfx.py "tap" at 0.62 s and 1.22 s
    look         turns his head to look left, then right, then back (3 s) – "what's that?"
    turn         turns from front to profile (facing left) via the 3/4 view (0.6 s) – then continue with walk_side
    turn_right   the same turn to face right – then continue with walk_side flipped
Outputs are VP9 WebM with alpha at half resolution (figure ~1600 px tall), 25 fps, feet at the bottom centre;
assets/actions/<ACTION>.json has frames, loop flag, ground speed (px/s at the stored size) and the feet point.
Place them in a scene with tools/toon/place_action.py.
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "assets/actions"
CACHE = Path.home() / ".maaran/cache"
FPS = 25
STORE = 0.5                                                # stored size = source x2 upscale x 0.5


def _cut(path, box=None):
    """Owner's art -> RGBA cut-out (rembg isnet-anime, cached)."""
    key = CACHE / (Path(path).stem + ("_%d_%d_%d_%d" % tuple(box) if box else "") + "_rgba.png")
    if key.exists():
        return np.array(Image.open(key))
    from rembg import new_session, remove
    im = Image.open(path).convert("RGB")
    if box:
        im = im.crop(box)
    a = np.array(remove(im, session=new_session("isnet-anime"), only_mask=True)).astype(np.float32)
    a = np.clip((a - 90) * 2.6, 0, 255).astype(np.uint8)
    rgba = np.dstack([np.array(im), a])
    Image.fromarray(rgba).save(key)
    return rgba


class Figure:
    """A drawing + soft regions in SOURCE px (K = up-scale of the image we bend)."""

    def __init__(self, rgba, K, pad, regions, pivot):
        self.K, self.pad = K, pad
        self.img = cv2.copyMakeBorder(rgba, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=(0, 0, 0, 0)).astype(np.float32)
        h, w = self.img.shape[:2]
        self.shape = (h, w)
        self.yy, self.xx = np.mgrid[0:h, 0:w].astype(np.float32)
        hsv = cv2.cvtColor(self.img[..., :3].astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.int32)
        self.cloth = (((hsv[..., 1] < 70) & (hsv[..., 2] > 150)) | ((hsv[..., 0] >= 30) & (hsv[..., 0] <= 90) & (hsv[..., 1] > 60)))
        cl = cv2.dilate(self.cloth.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(np.float32)
        self.cloth_soft = cv2.GaussianBlur(cl, (0, 0), 3)
        ws = ((hsv[..., 0] <= 25) & (hsv[..., 1] > 70)).astype(np.float32)
        self.woodskin = cv2.GaussianBlur(cv2.dilate(ws, np.ones((7, 7), np.uint8)), (0, 0), 3)
        self.w = {}
        for name, (pts, blur, ramp, kind) in regions.items():
            m = np.zeros(self.shape, np.float32)
            cv2.fillPoly(m, [np.array([self.pt(x, y) for x, y in pts], np.int32)], 1.0)
            if blur:
                m = cv2.GaussianBlur(m, (0, 0), blur * K)
            if ramp:
                y0, y1 = (self.pt(0, v)[1] for v in ramp)
                m *= np.clip((self.yy - y0) / (y1 - y0), 0, 1) if y1 > y0 else np.clip((y0 - self.yy) / (y0 - y1), 0, 1)
            if kind == "limb":
                m *= 1 - self.cloth_soft                   # the arm with its outlines, never the shirt beside it
            elif kind == "prop":
                m *= self.woodskin
            self.w[name] = m
        self.pivot = pivot                                 # feet point (source px) for body sway

    def pt(self, x, y):
        return (x * self.K + self.pad, y * self.K + self.pad)

    def moved(self, x, y):
        """Where source point (x, y) went in the last render (padded up px)."""
        px, py = self.pt(x, y)
        dx, dy = self.last
        return px + float(dx[int(py), int(px)]), py + float(dy[int(py), int(px)])

    def field(self, moves):
        dx = np.zeros(self.shape, np.float32)
        dy = np.zeros(self.shape, np.float32)
        for name, mv in moves.items():
            mx, my, rot, px, py = mv[:5]
            sc = mv[5] if len(mv) > 5 else 1.0
            w = self.w[name]
            cx, cy = self.pt(px, py)
            c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
            X, Y = self.xx - cx, self.yy - cy
            dx += w * ((c * X - s * Y) * sc - X + mx * self.K)
            dy += w * ((s * X + c * Y) * sc - Y + my * self.K)
        return dx, dy

    def render(self, moves, body=(0.0, 0.0, 0.0), keep=None):
        """moves {region: (dx, dy, rot, px, py[, scale])} in source px; body (dx, dy, rot) about the feet for all
        pixels except `keep` (a region that stays planted, e.g. the feet)."""
        dx, dy = self.field(moves)
        bx, by, br = body
        cx, cy = self.pt(*self.pivot)
        c, s = math.cos(math.radians(br)), math.sin(math.radians(br))
        X, Y = self.xx - cx, self.yy - cy
        stand = 1 - (np.clip(sum(self.w[k] for k in keep), 0, 1) * 0.8 if keep else 0)
        dx += stand * ((c * X - s * Y) - X + bx * self.K)
        dy += stand * ((s * X + c * Y) - Y + by * self.K)
        self.last = (dx, dy)
        fx, fy = dx.copy(), dy.copy()                      # destination-space field: d(x) = D(x - d(x))
        for _ in range(5):
            fx, fy = (cv2.remap(dx, self.xx - fx, self.yy - fy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE),
                      cv2.remap(dy, self.xx - fx, self.yy - fy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE))
        out = cv2.remap(self.img, self.xx - fx, self.yy - fy, cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT,
                        borderValue=(0, 0, 0, 0))
        return np.clip(out, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- the two figures

_FIG = {}


def front():
    if "front" not in _FIG:
        rgba = _cut(ROOT / "assets/2d/up/01_front.png")
        R = {
            "footL": ([(245, 1380), (455, 1380), (455, 1560), (245, 1560)], 4, None, None),
            "footR": ([(575, 1380), (795, 1380), (795, 1560), (575, 1560)], 4, None, None),
            "hemL": ([(320, 1150), (515, 1150), (515, 1440), (320, 1440)], 18, (1150, 1400), None),
            "hemR": ([(515, 1150), (720, 1150), (720, 1440), (515, 1440)], 18, (1150, 1400), None),
            "stick": ([(185, 610), (330, 610), (330, 790), (300, 790), (300, 1530), (215, 1530), (215, 790), (185, 790)], 0, None, "prop"),
            "arm": ([(705, 600), (820, 600), (845, 1040), (715, 1040)], 10, (640, 980), "limb"),
            "head": ([(320, -20), (680, -20), (680, 330), (320, 330)], 25, None, None),
            "chest": ([(200, 300), (830, 300), (830, 900), (200, 900)], 40, (900, 420), None),
        }
        _FIG["front"] = Figure(rgba, 2.0, 160, R, (500, 1450))
    return _FIG["front"]


def front_nostick():
    """Front figure with his FIST and the whole stick lifted out as one rigid sprite (lifts and strikes together).
    Behind the fist there is only background (the shirt starts right of it), so lifting it reveals nothing drawn."""
    if "front_ns" not in _FIG:
        f = front()
        rgba = f.img.astype(np.uint8).copy()
        h, w = rgba.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w]
        hsv = cv2.cvtColor(rgba[..., :3], cv2.COLOR_RGB2HSV).astype(np.int32)
        body = ((((hsv[..., 0] <= 25) & (hsv[..., 1] > 60)) | (hsv[..., 2] < 90)) & (rgba[..., 3] > 20))
        poly = np.zeros((h, w), np.uint8)
        cv2.fillPoly(poly, [np.array([f.pt(188, 645), f.pt(334, 645), f.pt(334, 800), f.pt(312, 800), f.pt(257, 1560),
                                      f.pt(198, 1560), f.pt(188, 800)], np.int32)], 1)
        part = poly.astype(bool) & body
        part = cv2.dilate(part.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool) & poly.astype(bool) & (rgba[..., 3] > 0)
        tip = np.zeros((h, w), np.uint8)
        cv2.fillPoly(tip, [np.array([f.pt(190, 1470), f.pt(256, 1470), f.pt(256, 1580), f.pt(190, 1580)], np.int32)], 1)
        shadow = tip.astype(bool) & (rgba[..., 3] > 0) & ~part   # the art's tiny ground shadow at the tip: drop it
        sprite = rgba.copy()
        sprite[..., 3] = np.where(part, sprite[..., 3], 0)
        # keep the fist itself in the figure too (it hides the seam); only the stick below the fist is removed
        below = yy > f.pt(0, 790)[1]
        rgba[..., 3] = np.where((part & below) | shadow, 0, rgba[..., 3])
        g = Figure.__new__(Figure)
        g.__dict__.update(f.__dict__)
        g.img = rgba.astype(np.float32)
        g.stick = sprite.astype(np.float32)
        g.tip = f.pt(228, 1515)
        g.wrist = f.pt(262, 650)
        _FIG["front_ns"] = g
    return _FIG["front_ns"]


SIDE_BOX = (2 * 516, 0, 2 * 832, 1774)                    # the profile on the x2 turnaround (source x 516..832)


def side():
    if "side" not in _FIG:
        rgba = _cut(CACHE / "up/08_turnaround_x2.png", SIDE_BOX)
        rgba = rgba.copy()
        # lift the slipper out as a rigid sprite and erase it from the figure (the hem stays)
        yy = np.arange(rgba.shape[0])[:, None]
        foot_zone = (yy > 2 * 792) & (np.arange(rgba.shape[1])[None, :] > 2 * (600 - 516))
        sprite = rgba.copy()
        sprite[..., 3] = np.where(foot_zone, sprite[..., 3], 0)
        rgba[..., 3] = np.where(foot_zone, 0, rgba[..., 3])
        X0 = 516
        # the lower stick (below his fist) becomes a rigid sprite that pivots in the hand – warping a thin rigid
        # prop far leaves a ghost copy behind
        xx = np.arange(rgba.shape[1])[None, :]
        lower = (yy > 2 * 470) & (yy < 2 * 860) & (xx > 2 * (528 - X0)) & (xx < 2 * (602 - X0))
        hsv = cv2.cvtColor(rgba[..., :3], cv2.COLOR_RGB2HSV).astype(np.int32)
        wood = lower & (((hsv[..., 0] <= 25) & (hsv[..., 1] > 60)) | (hsv[..., 2] < 90))
        wood = cv2.dilate(wood.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & lower
        stick = rgba.copy()
        stick[..., 3] = np.where(wood, stick[..., 3], 0)
        rgba[..., 3] = np.where(wood, 0, rgba[..., 3])
        R = {
            "hem": ([(600 - X0, 700), (810 - X0, 700), (810 - X0, 800), (600 - X0, 800)], 10, (700, 790), None),
            "arm": ([(655 - X0, 360), (750 - X0, 360), (755 - X0, 590), (650 - X0, 590)], 6, (370, 470), "limb"),
            "head": ([(595 - X0, -20), (800 - X0, -20), (800 - X0, 220), (595 - X0, 220)], 18, None, None),
        }
        f = Figure(rgba, 2.0, 160, R, (700 - X0, 860))
        pad = f.pad
        sp = cv2.copyMakeBorder(sprite, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=(0, 0, 0, 0))
        ys, xs = np.nonzero(sp[..., 3] > 10)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        f.foot = sp[y0:y1, x0:x1].astype(np.float32)
        f.foot_xy = (x0, y0)
        far = f.foot.copy()
        far[..., :3] *= 0.72
        f.foot_far = far
        f.stick = cv2.copyMakeBorder(stick, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=(0, 0, 0, 0)).astype(np.float32)
        f.grip = f.pt(565 - X0, 445)
        f.stick_len = (860 - 445) * f.K
        _FIG["side"] = f
    return _FIG["side"]


def paste(dst, sprite, x, y):
    """Alpha-composite sprite (float RGBA) onto dst (float RGBA) at integer x, y – the result is premultiplied-correct."""
    h, w = sprite.shape[:2]
    H, W = dst.shape[:2]
    xs, ys = max(0, x), max(0, y)
    xe, ye = min(W, x + w), min(H, y + h)
    if xe <= xs or ye <= ys:
        return
    s = sprite[ys - y:ye - y, xs - x:xe - x]
    a = s[..., 3:4] / 255
    d = dst[ys:ye, xs:xe]
    da = d[..., 3:4] / 255
    oa = a + da * (1 - a)
    rgb = (s[..., :3] * a + d[..., :3] * da * (1 - a)) / np.maximum(oa, 1e-6)
    dst[ys:ye, xs:xe] = np.dstack([rgb, oa * 255])


# ---------------------------------------------------------------- actions (t in seconds -> RGBA frame)

def walk_front(t, cycle=1.1):
    f = front()
    ph = 2 * math.pi * (t % cycle) / cycle
    lift_l, lift_r = max(0.0, math.sin(ph)), max(0.0, -math.sin(ph))
    bob = -7 * (abs(math.cos(ph)) ** 1.5) + 3
    sway = -6 * math.sin(ph)
    moves = {"footL": (-4 * lift_l, -42 * lift_l, -6 * lift_l, 350, 1460, 1 + 0.12 * lift_l),
             "footR": (4 * lift_r, -42 * lift_r, 6 * lift_r, 680, 1460, 1 + 0.12 * lift_r),
             "hemL": (-6 * lift_l, -24 * lift_l, 0, 420, 1400), "hemR": (6 * lift_r, -24 * lift_r, 0, 610, 1400),
             "arm": (0, 0, 6 * math.sin(ph), 760, 600), "head": (-0.6 * sway, -0.4 * bob, 0.4 * math.sin(ph), 500, 330)}
    return f.render(moves, body=(sway, bob, 0.8 * math.sin(ph)), keep=["footL", "footR"])


SIDE_CYCLE, SIDE_STRIDE = 1.0, 62.0                       # s per two steps; foot travel (source px)


def walk_side(t, cycle=SIDE_CYCLE):
    f = side()
    p = (t % cycle) / cycle
    S, L = SIDE_STRIDE, 20.0

    def foot(q):                                           # x (forward = -x) and lift for a foot at phase q
        q %= 1
        if q < 0.5:                                        # stance: planted, slides back under the body
            return -S / 2 + S * (q / 0.5), 0.0
        u = (q - 0.5) / 0.5                                # swing: lifts and comes forward
        return S / 2 - S * (u * u * (3 - 2 * u)), -L * math.sin(math.pi * u)
    nx, nl = foot(p)
    fx, fl = foot(p + 0.5)
    ph = 2 * math.pi * p
    bob = 5 * math.cos(2 * ph)                              # lowest at heel strike, twice per cycle
    moves = {"hem": (0.22 * (nx + fx) / 2 - 3 * math.sin(ph), 0, 0, 700 - 516, 790),
             "arm": (0, 0, -3.5 * math.sin(ph), 705 - 516, 350),
             "head": (0, -0.3 * bob, 0.5 * math.sin(2 * ph), 700 - 516, 220)}
    img = f.render(moves, body=(0, bob, 0)).astype(np.float32)
    canvas = np.zeros_like(img)
    X0, Y0 = f.foot_xy
    K = f.K
    paste(canvas, f.foot_far, int(X0 + (fx + 8) * K), int(Y0 + (fl - 4) * K))
    paste(canvas, f.foot, int(X0 + nx * K), int(Y0 + nl * K))
    paste(canvas, img, 0, 0)                               # the veshti covers the ankles
    # the stick pivots in his fist: its tip moves with the far foot (planted while that foot is planted) and lifts
    ang = math.degrees(math.asin(max(-0.4, min(0.4, 0.75 * fx * K / f.stick_len))))
    gx, gy = f.grip
    M = cv2.getRotationMatrix2D((gx, gy), ang, 1.0)
    M[1, 2] += (bob + 0.4 * fl) * K
    st = cv2.warpAffine(f.stick, M, (img.shape[1], img.shape[0]), flags=cv2.INTER_CUBIC, borderValue=(0, 0, 0, 0))
    paste(canvas, np.clip(st, 0, 255), 0, 0)
    return np.clip(canvas, 0, 255).astype(np.uint8)


def idle(t, cycle=4.0):
    f = front()
    ph = 2 * math.pi * t / cycle
    breath = math.sin(2 * ph)
    moves = {"chest": (0, -2.2 * breath, 0, 500, 900, 1 + 0.004 * breath),
             "head": (0.8 * math.sin(ph), -1.5 * breath, 0.6 * math.sin(ph + 1), 500, 330),
             "arm": (0, 0, 1.2 * math.sin(ph + 0.7), 760, 600)}
    return f.render(moves, body=(2.5 * math.sin(ph), 0, 0.35 * math.sin(ph)), keep=["footL", "footR"])


def env(t, a, b, ramp=0.25):
    return min(1.0, max(0.0, (t - a) / ramp)) * min(1.0, max(0.0, (b - t) / ramp))


EYES = [(458, 190, 27, 18), (552, 180, 27, 18)]         # front art (source px): centre, half-width, half-height
MOUTH = [(462, 268), (507, 276), (552, 266)]


def laugh_face(f, img, e, open_px):
    """Happy crescent eyes (skin over the eye, an upward lid arc with a crease) and an open laughing mouth, drawn
    where the face moved to. e 0..1 fades them in."""
    if e <= 0.02:
        return img
    K = f.K
    base = img.copy()
    rgb = np.clip(img[..., :3], 0, 255).astype(np.uint8)
    hole = np.zeros(img.shape[:2], np.uint8)
    arcs = []
    for (x, y, rx, ry) in EYES:
        cx, cy = f.moved(x, y)
        RX, RY = rx * K * 1.2, ry * K * 1.45
        cv2.ellipse(hole, (int(cx), int(cy)), (int(RX), int(RY)), 0, 0, 360, 255, -1)
        arcs.append((cx, cy, RX, RY))
    x0, y0, w, h = cv2.boundingRect(hole)
    pad = int(30 * K)
    X0, Y0, X1, Y1 = max(0, x0 - pad), max(0, y0 - pad), x0 + w + pad, y0 + h + pad
    patch = cv2.inpaint(np.ascontiguousarray(rgb[Y0:Y1, X0:X1]), hole[Y0:Y1, X0:X1], 9, cv2.INPAINT_TELEA)
    filled = rgb.copy()
    filled[Y0:Y1, X0:X1] = patch
    a = cv2.GaussianBlur(hole.astype(np.float32) / 255, (0, 0), 2)[..., None] * e
    out = img.copy()
    out[..., :3] = img[..., :3] * (1 - a) + filled.astype(np.float32) * a
    ln = np.zeros(img.shape[:2], np.uint8)                 # closed lids: upward arcs ("^ ^" laughing eyes)
    for cx, cy, RX, RY in arcs:
        cv2.ellipse(ln, (int(cx), int(cy + RY * 0.3)), (int(RX * 0.8), int(RY * 0.62)), 0, 198, 342, 255, int(4.5 * K), cv2.LINE_AA)
    a = (ln.astype(np.float32) / 255)[..., None] * e
    out[..., :3] = out[..., :3] * (1 - a) + np.array([60, 30, 15], np.float32) * a
    img = out
    lay = np.zeros(img.shape[:2] + (4,), np.float32)
    (lx, ly), (mx, my), (rx_, ry_) = (f.moved(*p) for p in MOUTH)
    o = open_px * K
    top, bot = [], []
    for i in range(21):
        u = 0.02 + 0.96 * i / 20
        x = (1 - u) ** 2 * lx + 2 * (1 - u) * u * mx + u ** 2 * rx_
        y = (1 - u) ** 2 * ly + 2 * (1 - u) * u * my + u ** 2 * ry_
        top.append((x, y))
        bot.append((x, y + o * math.sin(math.pi * i / 20) ** 0.7))
    poly = np.array(top + bot[::-1], np.int32)
    m = np.zeros(img.shape[:2], np.uint8)
    cv2.fillPoly(m, [poly], 255, cv2.LINE_AA)
    a = m.astype(np.float32) / 255
    col = np.zeros(img.shape[:2] + (3,), np.float32)
    col[...] = (95, 25, 25)
    yy = np.arange(img.shape[0], dtype=np.float32)[:, None]
    teeth = (yy < (ly + my) / 2 + o * 0.3).astype(np.float32)[..., None] * np.ones_like(col)
    col = col * (1 - teeth) + np.array([250, 246, 236]) * teeth
    tong = np.zeros(img.shape[:2], np.uint8)
    cv2.ellipse(tong, (int(mx), int(my + o * 0.85)), (int(abs(rx_ - lx) * 0.25), int(o * 0.35)), 0, 0, 360, 255, -1, cv2.LINE_AA)
    tg = (tong.astype(np.float32) / 255)[..., None]
    col = col * (1 - tg) + np.array([205, 95, 95]) * tg
    edge = cv2.morphologyEx(m, cv2.MORPH_GRADIENT, np.ones((5, 5), np.uint8)).astype(np.float32)[..., None] / 255
    col = col * (1 - edge) + np.array([60, 20, 10]) * edge
    lay[..., :3] = lay[..., :3] * (1 - a[..., None]) + col * a[..., None]
    lay[..., 3] = np.maximum(lay[..., 3], a * 255)
    lay[..., 3] *= e
    out = img.copy()
    paste(out, lay, 0, 0)
    return out


def laugh(t, dur=2.4):
    """A big belly laugh: head goes back, shoulders bounce in "ho-ho-ho" beats, eyes squeeze shut, mouth open."""
    f = front()
    e = env(t, 0.05, dur - 0.05, 0.3)
    beat = abs(math.sin(2 * math.pi * 2.3 * t)) * e          # ~4.6 bounces a second
    moves = {"chest": (0, -7 * beat, 0, 500, 900, 1 + 0.012 * beat),
             "head": (0, -10 * e - 5 * beat, -5 * e, 500, 330),
             "arm": (0, -5 * beat, -2 * e, 760, 600)}
    img = f.render(moves, body=(0, -3 * beat, -0.5 * e), keep=["footL", "footR"]).astype(np.float32)
    snap = min(1.0, max(0.0, (e - 0.3) / 0.08))          # eyes snap shut / open in ~2 frames (no ghost fades)
    img = laugh_face(f, img, snap, (13 + 9 * beat) * e)
    return np.clip(img, 0, 255).astype(np.uint8)


def bow(t, dur=1.8):
    f = front()
    u = math.sin(math.pi * min(1.0, max(0.0, (t - 0.15) / (dur - 0.4))))
    moves = {"head": (0, 26 * u, 0, 500, 330, 1 - 0.02 * u),
             "chest": (0, 14 * u, 0, 500, 900, 1 - 0.015 * u)}
    return f.render(moves, keep=["footL", "footR"])


def front_tap():
    """Front figure + a 'hand' region: the fist and the whole stick as one smooth rigid block (pure translation, so
    nothing bends), fading out under the sleeve hem; the art's little ground shadow at the stick tip is removed."""
    if "front_tap" not in _FIG:
        f = front()
        g = Figure.__new__(Figure)
        g.__dict__.update(f.__dict__)
        g.w = dict(f.w)
        img = f.img.copy()
        h, w = img.shape[:2]
        hsv = cv2.cvtColor(img[..., :3].astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.int32)
        wood = ((hsv[..., 0] <= 25) & (hsv[..., 1] > 60)) | (hsv[..., 2] < 90)
        tip = np.zeros((h, w), np.uint8)
        cv2.fillPoly(tip, [np.array([f.pt(190, 1500), f.pt(256, 1500), f.pt(256, 1580), f.pt(190, 1580)], np.int32)], 1)
        img[..., 3] = np.where(tip.astype(bool) & ~wood & (img[..., 3] > 0), 0, img[..., 3])
        g.img = img
        m = np.zeros((h, w), np.float32)
        cv2.fillPoly(m, [np.array([f.pt(182, 600), f.pt(340, 600), f.pt(340, 700), f.pt(305, 800), f.pt(258, 1590),
                                   f.pt(190, 1590), f.pt(182, 800)], np.int32)], 1.0)
        m = cv2.GaussianBlur(m, (0, 0), 2 * f.K)
        yy, xx = g.yy, g.xx
        y0, y1 = f.pt(0, 606)[1], f.pt(0, 652)[1]
        r = np.clip((yy - y0) / (y1 - y0), 0, 1)
        m *= r * r * (3 - 2 * r)                           # the forearm stretches smoothly; the fist moves as one piece
        g.w["hand"] = m
        # the shirt cuff above the fist, laid back on top after the lift (the wrist slides under the sleeve)
        hh = hsv
        cream = (hh[..., 0] >= 15) & (hh[..., 0] <= 40) & (hh[..., 1] < 90) & (hh[..., 2] > 150)
        box = (xx > f.pt(186, 0)[0]) & (xx < f.pt(345, 0)[0]) & (yy > f.pt(0, 560)[1]) & (yy < f.pt(0, 662)[1])
        cuff = cv2.morphologyEx((cream & box & (img[..., 3] > 200)).astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        cuff = cv2.dilate(cuff, np.ones((3, 3), np.uint8)).astype(np.float32)
        layer = img.copy()
        layer[..., 3] = cv2.GaussianBlur(cuff, (0, 0), 1.0) * 255
        g.cuff = layer
        g.tip = f.pt(228, 1515)
        _FIG["front_tap"] = g
    return _FIG["front_tap"]


def tap(t, dur=1.6):
    """Lifts the stick (fist and stick rise together, the wrist slides under the sleeve) and strikes the ground
    twice; a dust puff at each strike, a small nod with it."""
    f = front_tap()
    lift, nod, puff = 0.0, 0.0, []
    for t0 in (0.2, 0.8):
        u = (t - t0) / 0.42
        if 0 <= u <= 1:                                   # up slowly (0-0.65), down fast (0.65-1)
            lift = max(lift, math.sin(math.pi / 2 * u / 0.65) if u < 0.65 else math.cos(math.pi / 2 * (u - 0.65) / 0.35))
        v = (t - (t0 + 0.42)) / 0.4
        if 0 <= v <= 1:
            puff.append(v)
            nod = max(nod, math.sin(math.pi * v))
    img = f.render({"hand": (0, -20 * lift, 0, 260, 700), "head": (0, 3 * nod, 0, 500, 330)},
                   keep=["footL", "footR"]).astype(np.float32)
    paste(img, f.cuff, 0, 0)
    tx, ty = f.tip
    for v in puff:                                        # dust kicked up at the tip
        lay = np.zeros(img.shape[:2], np.float32)
        for k, (ox, oy) in enumerate(((-30, -8), (28, -10), (-10, -22), (12, -4), (0, -14))):
            r = (14 + 46 * v) * f.K * (0.75 + 0.1 * k)
            cv2.ellipse(lay, (int(tx + ox * f.K * (0.7 + 1.2 * v)), int(ty + oy * f.K * (0.8 + 1.4 * v))), (int(r), int(r * 0.6)),
                        0, 0, 360, 1.0, -1, cv2.LINE_AA)
        lay = np.clip(cv2.GaussianBlur(lay, (0, 0), 4 * f.K), 0, 1) * (1 - v) ** 0.8 * 0.9
        dust = np.zeros_like(img)
        dust[..., :3] = (190, 140, 95)
        dust[..., 3] = 255 * lay
        paste(img, dust, 0, 0)
    return np.clip(img, 0, 255).astype(np.uint8)


def look(t, dur=3.0):
    f = front()
    a = 5.0 * math.sin(2 * math.pi * min(1.0, t / dur)) * env(t, 0.05, dur - 0.05, 0.4)
    return f.render({"head": (-2.2 * a, 0.3 * abs(a), a, 500, 330)}, keep=["footL", "footR"])


def turn(t, dur=0.6):
    """front -> 3/4 -> profile, each drawing scaled to the same height and feet point, cross-faded with a small squash."""
    if "turn" not in _FIG:
        fr = front().img
        q = _cut(CACHE / "up/08_turnaround_x2.png", (2 * 40, 0, 2 * 434, 1774))
        sd = side()
        pr = np.zeros_like(sd.img)
        paste(pr, sd.foot, *sd.foot_xy)
        paste(pr, sd.img, 0, 0)
        paste(pr, sd.stick, 0, 0)

        def norm(img):
            a = img[..., 3] > 20
            ys, xs = np.nonzero(a)
            crop = img[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
            h = 1500
            im = cv2.resize(crop, (round(crop.shape[1] * h / crop.shape[0]), h), interpolation=cv2.INTER_AREA)
            out = np.zeros((1600, 1100, 4), np.float32)
            paste(out, im.astype(np.float32), 550 - im.shape[1] // 2, 1580 - h)
            return out
        _FIG["turn"] = [norm(fr.astype(np.float32)), norm(q.astype(np.float32)), norm(pr.astype(np.float32))]
    a, b, c = _FIG["turn"]
    i = int(t * FPS)
    img = a if i < 5 else (b if i < 10 else c)              # snap front -> 3/4 -> profile (limited-animation turn)
    sq = 0.95 if i in (4, 5, 9, 10) else 1.0                # a small squash on the change frames
    w = img.shape[1]
    img = cv2.resize(img, (round(w * sq), img.shape[0]), interpolation=cv2.INTER_AREA)
    out = np.zeros((1600, 1100, 4), np.float32)
    paste(out, img, 550 - img.shape[1] // 2, 0)
    return np.clip(out, 0, 255).astype(np.uint8)


def turn_right(t, dur=0.6):
    """Like turn, but to his left (image right): the front view stays as drawn, the 3/4 and profile are mirrored –
    so the stick never jumps hands. Continue with walk_side flipped."""
    img = turn(t, dur)
    return img if int(t * FPS) < 5 else np.ascontiguousarray(img[:, ::-1])


ACTIONS = {"walk_front": (walk_front, 1.1, True), "walk_side": (walk_side, SIDE_CYCLE, True), "idle": (idle, 4.0, True),
           "laugh": (laugh, 2.4, False), "bow": (bow, 1.8, False), "tap": (tap, 1.6, False), "look": (look, 3.0, False),
           "turn": (turn, 0.6, False),
           "turn_right": (turn_right, 0.6, False)}


def build(name):
    fn, dur, loop = ACTIONS[name]
    n = round(dur * FPS)
    frames = [fn(i / FPS) for i in range(n)]
    h = max(fr.shape[0] for fr in frames)
    w = max(fr.shape[1] for fr in frames)
    sw, sh = (round(w * STORE) // 2) * 2, (round(h * STORE) // 2) * 2
    LIB.mkdir(parents=True, exist_ok=True)
    ff = subprocess.Popen(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba",
                           "-s", f"{sw}x{sh}", "-framerate", str(FPS), "-i", "-", "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
                           "-crf", "22", "-b:v", "0", "-auto-alt-ref", "0", str(LIB / f"{name}.webm")], stdin=subprocess.PIPE)
    feet = None
    a0 = frames[0][..., 3] > 40
    ys0 = np.nonzero(a0.any(axis=1))[0]
    fig_h = round((ys0.max() - ys0.min()) * STORE)
    for fr in frames:
        fr = cv2.resize(fr, (sw, sh), interpolation=cv2.INTER_AREA)
        if feet is None:
            ys, xs = np.nonzero(fr[..., 3] > 40)
            feet = [int(np.median(xs[ys > ys.max() - 6])), int(ys.max())]
        ff.stdin.write(fr.tobytes())
    ff.stdin.close()
    ff.wait()
    speed = SIDE_STRIDE * 2.0 * STORE * 2 / (SIDE_CYCLE / 2) / 2 if name == "walk_side" else 0.0
    meta = {"action": name, "fps": FPS, "frames": n, "seconds": dur, "loop": loop, "size": [sw, sh], "feet": feet,
            "fig_h": fig_h, "facing": "left" if name == "walk_side" else ("profile_left_end" if name == "turn" else ("profile_right_end" if name == "turn_right" else "front")), "ground_speed_px_s": round(speed, 1)}
    json.dump(meta, open(LIB / f"{name}.json", "w"), indent=1)
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-c:v", "libvpx-vp9", "-i", str(LIB / f"{name}.webm"),
                    "-filter_complex", f"color=c=0x8a8f96:s={sw}x{sh}[bg];[bg][0:v]overlay=shortest=1,scale=540:-2",
                    "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", str(LIB / f"{name}_preview.mp4")], check=True)
    print("saved", name, n, "frames", meta["size"])


def main():
    args = sys.argv[1:]
    if "--still" in args:
        name, t, out = args[0], float(args[args.index("--still") + 1]), args[args.index("--still") + 2]
        Image.fromarray(ACTIONS[name][0](t)).save(out)
        return
    for name in (list(ACTIONS) if args == ["all"] else args):
        build(name)


if __name__ == "__main__":
    main()
