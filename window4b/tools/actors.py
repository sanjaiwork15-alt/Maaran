"""Window 4B: small 2D actors drawn in code in the style of the master art
(flat colours, dark outline): people, rescue boats, a scooter, a traffic signal,
a helicopter, debris. All functions draw onto a float BGR canvas (0..1) at output
resolution. `u` = pixels per metre at the actor's position (perspective scale).
"""
import math

import cv2
import numpy as np

OUTLINE = (0.13, 0.12, 0.14)
MASKING = False   # True while Layer.draw paints the coverage mask (outlines must count as coverage)
OL = 1.0          # outline thickness multiplier (raise it for big foreground figures)
AA = cv2.LINE_AA


def _ol():
    return (1.0, 1.0, 1.0) if MASKING else OUTLINE


def _pt(x, y):
    return int(round(x * 4)), int(round(y * 4))


def _line(img, p0, p1, col, w, outline=True):
    wp = max(1, int(round(w)))
    if outline:
        cv2.line(img, _pt(*p0), _pt(*p1), _ol(), wp + int(2 * OL), AA, 2)
    cv2.line(img, _pt(*p0), _pt(*p1), col, wp, AA, 2)


def _circle(img, c, r, col, outline=True):
    if outline:
        cv2.circle(img, _pt(*c), int(r * 4 + 4 * OL), _ol(), -1, AA, 2)
    cv2.circle(img, _pt(*c), max(1, int(r * 4)), col, -1, AA, 2)


def _ellipse(img, c, ax, ay, col, ang=0, outline=True):
    if outline:
        cv2.ellipse(img, _pt(*c), (int(ax * 4 + 4 * OL), int(ay * 4 + 4 * OL)), ang, 0, 360, _ol(), -1, AA, 2)
    cv2.ellipse(img, _pt(*c), (max(1, int(ax * 4)), max(1, int(ay * 4))), ang, 0, 360, col, -1, AA, 2)


def _poly(img, pts, col, outline=True):
    p = np.array([[int(round(x * 4)), int(round(y * 4))] for x, y in pts], np.int32)
    if outline:
        cv2.polylines(img, [p], True, _ol(), max(2, int(2 * OL)), AA, 2)
    cv2.fillPoly(img, [p], col, AA, 2)


class Layer:
    """A small RGBA patch the actors draw into, pasted onto the scene with per-pixel heights
    (so flood water covers legs, wheels and poles from the bottom up)."""

    def __init__(self, x0, y0, x1, y1):
        self.x0, self.y0 = int(x0), int(y0)
        self.w, self.h = max(1, int(x1 - x0)), max(1, int(y1 - y0))
        self.rgb = np.zeros((self.h, self.w, 3), np.float32)
        self.a = np.zeros((self.h, self.w), np.float32)

    def draw(self, fn, *args, **kw):
        # draw into a scratch canvas twice: once in colour, once as a white mask
        c = np.zeros((self.h, self.w, 3), np.float32)
        m = np.zeros((self.h, self.w, 3), np.float32)
        fn(_Shift(c, self.x0, self.y0), *args, **kw)
        global MASKING
        MASKING = True
        try:
            fn(_Shift(m, self.x0, self.y0, mask=True), *args, **kw)
        finally:
            MASKING = False
        a = m[..., 0]                      # coverage; c is colour premultiplied by it
        self.rgb = self.rgb * (1 - a[..., None]) + c
        self.a = self.a * (1 - a) + a

    def paste(self, canvas, height=None, base_y=None, u=None, float_mask=None, clip=None):
        H, W = canvas.shape[:2]
        xa, ya = max(0, self.x0), max(0, self.y0)
        xb, yb = min(W, self.x0 + self.w), min(H, self.y0 + self.h)
        if xb <= xa or yb <= ya:
            return
        sub_a = self.a[ya - self.y0:yb - self.y0, xa - self.x0:xb - self.x0]
        if clip is not None:
            sub_a = sub_a * clip[ya:yb, xa:xb]
        sub = self.rgb[ya - self.y0:yb - self.y0, xa - self.x0:xb - self.x0]
        a = sub_a[..., None]
        prem = sub * (a / np.maximum(self.a[ya - self.y0:yb - self.y0, xa - self.x0:xb - self.x0, None], 1e-4))
        canvas[ya:yb, xa:xb] = canvas[ya:yb, xa:xb] * (1 - a) + prem
        if height is not None and base_y is not None:
            rows = np.arange(ya, yb, dtype=np.float32)[:, None]
            hv = np.broadcast_to((base_y - rows) / u, sub_a.shape)
            cur = height[ya:yb, xa:xb]
            height[ya:yb, xa:xb] = np.where(sub_a > 0.3, hv, cur)
        if float_mask is not None:
            float_mask[ya:yb, xa:xb] = np.maximum(float_mask[ya:yb, xa:xb], sub_a)


class _Shift:
    """Canvas wrapper so actor code can use scene coordinates; mask mode paints white."""

    def __init__(self, img, x0, y0, mask=False):
        self.img, self.x0, self.y0, self.mask = img, x0, y0, mask


def _unwrap(c):
    return c.img, c.x0, c.y0, c.mask


def _col(mask, col):
    return (1.0, 1.0, 1.0) if mask else col


# ------------------------------------------------------------------ people

def person(c, x, y, u, shirt=(0.55, 0.35, 0.2), pants=(0.25, 0.22, 0.2), skin=(0.55, 0.68, 0.86),
           hair=(0.1, 0.1, 0.12), phase=0.0, walking=True, umbrella=None, bag=None, vest=False,
           sitting=False, arms_up=0.0, push=False):
    """A person with feet at (x, y); u = px per metre (1.7 m tall)."""
    img, X0, Y0, mask = _unwrap(c)
    h = 1.7 * u
    sx = lambda v: v - X0
    sy = lambda v: v - Y0
    k = lambda col: _col(mask, col)
    sw = math.sin(phase) * (0.16 if walking else 0.0)
    hip = (x, y - 0.5 * h)
    if not sitting:
        for s in (1, -1):
            foot = (x + s * sw * h, y)
            _line(img, (sx(hip[0]), sy(hip[1])), (sx(foot[0]), sy(foot[1])), k(pants), 0.12 * h)
    body_c = (x, y - 0.69 * h)
    shirt_c = (0.15, 0.45, 0.95) if vest else shirt
    _ellipse(img, (sx(body_c[0]), sy(body_c[1])), 0.16 * h, 0.21 * h, k(shirt_c))
    sh = (x, y - 0.83 * h)
    for s in (1, -1):
        if push:
            hand = (x + 0.3 * h, y - 0.62 * h)
        elif arms_up and s == 1:
            hand = (x + 0.12 * h, y - (0.83 + 0.25 * arms_up) * h)
        else:
            hand = (x - s * sw * 0.7 * h + s * 0.05 * h, y - 0.5 * h)
        _line(img, (sx(sh[0]), sy(sh[1])), (sx(hand[0]), sy(hand[1])), k(shirt_c), 0.09 * h)
    if bag is not None:
        _poly(img, [(sx(x + 0.08 * h), sy(y - 0.55 * h)), (sx(x + 0.24 * h), sy(y - 0.55 * h)),
                    (sx(x + 0.24 * h), sy(y - 0.36 * h)), (sx(x + 0.08 * h), sy(y - 0.36 * h))], k(bag))
    head = (x, y - 0.93 * h)
    _circle(img, (sx(head[0]), sy(head[1])), 0.11 * h, k(skin))
    if not mask:
        cv2.ellipse(img, _pt(sx(head[0]), sy(head[1] - 0.02 * h)), (int(0.113 * h * 4), int(0.08 * h * 4)), 0, 180, 360,
                    hair, -1, AA, 2)
    if umbrella is not None:
        top = (x + 0.05 * h, y - 1.18 * h)
        _line(img, (sx(x + 0.05 * h), sy(y - 0.75 * h)), (sx(top[0]), sy(top[1])), k(OUTLINE), 0.02 * h, False)
        img_e = img
        cv2.ellipse(img_e, _pt(sx(top[0]), sy(top[1])), (int(0.32 * h * 4) + 4, int(0.16 * h * 4) + 4), 0, 180, 360,
                    k(OUTLINE), -1, AA, 2)
        cv2.ellipse(img_e, _pt(sx(top[0]), sy(top[1])), (int(0.32 * h * 4), int(0.16 * h * 4)), 0, 180, 360,
                    k(umbrella), -1, AA, 2)


# ------------------------------------------------------------------ vehicles

def rescue_boat(c, x, y, u, t, crew=2, passengers=1, cargo=2, facing=1, wake=1.0):
    """Orange inflatable rescue boat (~4 m), waterline at y, centre x, seen slightly from above:
    the far tube, the dark floor with the people and bags, then the near tube in front."""
    img, X0, Y0, mask = _unwrap(c)
    sx = lambda v: v - X0
    sy = lambda v: v - Y0
    k = lambda col: _col(mask, col)
    L = 4.0 * u
    y = y + math.sin(t * 2.3 + x * 0.01) * 0.05 * u
    f = facing
    P = lambda dx, dy: (sx(x + f * dx * L), sy(y + dy * u))
    if wake > 0 and not mask:
        for i in range(3):
            d = (i + 1) * 0.3 * L
            tail = x - f * (L * 0.5 + d)
            for sgn in (-1, 1):
                cv2.line(img, _pt(sx(x - f * L * 0.42), sy(y)), _pt(sx(tail), sy(y + sgn * 0.15 * u * (i + 1))),
                         (0.92, 0.92, 0.92), 1, AA, 2)
    orange, dark = (0.05, 0.42, 1.0), (0.04, 0.25, 0.65)
    # far tube and the floor between the tubes
    _poly(img, [P(-0.48, -1.0), P(0.3, -1.0), P(0.5, -0.7), P(0.3, -0.45), P(-0.48, -0.45)], k(dark))
    _poly(img, [P(-0.44, -0.85), P(0.28, -0.85), P(0.42, -0.65), P(0.28, -0.5), P(-0.44, -0.5)], k((0.22, 0.22, 0.24)))
    for j in range(cargo):
        bx = 0.08 + 0.12 * j
        _poly(img, [P(bx - 0.05, -1.05), P(bx + 0.05, -1.05), P(bx + 0.05, -0.55), P(bx - 0.05, -0.55)],
              k([(0.3, 0.55, 0.75), (0.25, 0.6, 0.3)][j % 2]))
    for i in range(crew + passengers):
        dx = -0.3 + 0.16 * i
        vest = i < crew
        person(c, x + f * dx * L, y - 0.15 * u, u * 0.9, shirt=(0.6, 0.4, 0.25) if not vest else (0.1, 0.5, 1.0),
               vest=vest, sitting=True, walking=False,
               skin=[(0.55, 0.68, 0.86), (0.4, 0.52, 0.7), (0.45, 0.6, 0.8)][i % 3])
    # near tube, rounded at the bow, with a grab line
    _poly(img, [P(-0.5, -0.55), P(0.3, -0.55), P(0.45, -0.48), P(0.52, -0.3), P(0.42, -0.05), P(0.3, 0.05),
                P(-0.48, 0.05), P(-0.52, -0.25)], k(orange))
    if not mask:
        cv2.line(img, _pt(*P(-0.47, -0.08)), _pt(*P(0.38, -0.08)), (0.03, 0.2, 0.55), 2, AA, 2)
        for q in range(5):
            cv2.circle(img, _pt(*P(-0.4 + 0.17 * q, -0.33)), 6, (0.92, 0.92, 0.92), -1, AA, 2)
    mx = -0.52  # outboard motor
    _poly(img, [P(mx - 0.06, -1.0), P(mx + 0.02, -1.0), P(mx + 0.01, 0.2), P(mx - 0.04, 0.2)], k((0.15, 0.15, 0.17)))


def scooter(c, x, y, u, facing=1):
    img, X0, Y0, mask = _unwrap(c)
    sx = lambda v: v - X0
    sy = lambda v: v - Y0
    k = lambda col: _col(mask, col)
    r = 0.25 * u
    for d in (-0.6, 0.6):
        _circle(img, (sx(x + d * u), sy(y - r)), r, k((0.12, 0.12, 0.13)))
    _poly(img, [(sx(x - 0.75 * u), sy(y - 0.75 * u)), (sx(x + 0.3 * u), sy(y - 0.75 * u)),
                (sx(x + 0.45 * u), sy(y - 0.35 * u)), (sx(x - 0.7 * u), sy(y - 0.35 * u))], k((0.2, 0.2, 0.75)))
    hx = x + facing * 0.55 * u
    _line(img, (sx(hx), sy(y - 0.4 * u)), (sx(hx + facing * 0.05 * u), sy(y - 1.1 * u)), k((0.25, 0.25, 0.27)), 0.07 * u)


def signal(c, x, y, u, state):
    """Traffic signal on a pole (4.2 m). state: 'red', 'amber', 'green' or 'dead'."""
    img, X0, Y0, mask = _unwrap(c)
    sx = lambda v: v - X0
    sy = lambda v: v - Y0
    k = lambda col: _col(mask, col)
    _line(img, (sx(x), sy(y)), (sx(x), sy(y - 3.4 * u)), k((0.3, 0.3, 0.3)), 0.12 * u)
    _poly(img, [(sx(x - 0.22 * u), sy(y - 4.3 * u)), (sx(x + 0.22 * u), sy(y - 4.3 * u)),
                (sx(x + 0.22 * u), sy(y - 3.2 * u)), (sx(x - 0.22 * u), sy(y - 3.2 * u))], k((0.15, 0.17, 0.15)))
    cols = {"red": (0.2, 0.2, 1.0), "amber": (0.1, 0.65, 1.0), "green": (0.45, 0.95, 0.3)}
    for i, name in enumerate(("red", "amber", "green")):
        on = state == name
        col = cols[name] if on else (0.12, 0.13, 0.13)
        _circle(img, (sx(x), sy(y - (4.08 - 0.33 * i) * u)), 0.11 * u, k(col), outline=False)


def helicopter(c, x, y, u, t):
    img, X0, Y0, mask = _unwrap(c)
    sx = lambda v: v - X0
    sy = lambda v: v - Y0
    k = lambda col: _col(mask, col)
    _ellipse(img, (sx(x), sy(y)), 1.6 * u, 0.8 * u, k((0.22, 0.24, 0.26)))
    _line(img, (sx(x + 1.2 * u), sy(y - 0.1 * u)), (sx(x + 4.0 * u), sy(y - 0.5 * u)), k((0.22, 0.24, 0.26)), 0.3 * u)
    _line(img, (sx(x - 1.3 * u), sy(y + 1.1 * u)), (sx(x + 1.2 * u), sy(y + 1.1 * u)), k((0.15, 0.15, 0.16)), 0.12 * u, False)
    blade = 3.4 * u * abs(math.cos(t * 40))
    _line(img, (sx(x - blade), sy(y - 0.95 * u)), (sx(x + blade), sy(y - 0.95 * u)), k((0.3, 0.3, 0.32)), 0.12 * u, False)
    if not mask and int(t * 2) % 2 == 0:
        cv2.circle(img, _pt(sx(x + 4.0 * u), sy(y - 0.5 * u)), 8, (0.2, 0.2, 1.0), -1, AA, 2)


def debris(c, x, y, u, seed, n=6):
    """A raft of branches and planks caught at the waterline."""
    img, X0, Y0, mask = _unwrap(c)
    sx = lambda v: v - X0
    sy = lambda v: v - Y0
    k = lambda col: _col(mask, col)
    rng = np.random.default_rng(seed)
    for i in range(n):
        L = u * (0.8 + 1.8 * rng.random())
        a = (rng.random() - 0.5) * 0.6
        cx = x + (rng.random() - 0.5) * 3 * u; cy = y - rng.random() * 0.3 * u
        col = [(0.15, 0.25, 0.35), (0.2, 0.3, 0.42), (0.18, 0.35, 0.3)][i % 3]
        _line(img, (sx(cx - math.cos(a) * L / 2), sy(cy - math.sin(a) * L / 2)),
              (sx(cx + math.cos(a) * L / 2), sy(cy + math.sin(a) * L / 2)), k(col), 0.18 * u)
    for i in range(3):
        _circle(img, (sx(x + (rng.random() - 0.5) * 2.5 * u), sy(y - 0.1 * u)), 0.35 * u,
                k((0.15, 0.32, 0.25)), outline=False)


def finish(c_img):
    """Down-sample a 4x supersampled scratch canvas (shift=2 in cv2 means 1/4 px precision already)."""
    return c_img
