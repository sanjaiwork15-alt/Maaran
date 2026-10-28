"""Window 4B Ep 3: the stick-figure man (and tiny stick people), plus the line-art props he uses.

Drawn straight onto a float BGR canvas (0..1) at output resolution. The figure is a two-bone IK
rig: give the hip, lean and where each hand (and foot) should be, and the elbows/knees follow.

pose keys (all output px unless noted):
    x, hip_y         hip position
    s                scale (1.0 = the foreground man: head radius 40 px)
    lean             torso tilt in radians (+ = towards the right)
    face             "away" | "left" | "right" | "front"
    look             (dx, dy) head offset in px at s=1 (where he looks)
    hand_l, hand_r   absolute hand targets, or None for "hanging" (swing with walk phase)
    walk             walk phase in radians, or None (standing); feet target from it
    sit              0..1 sitting
    age              0..1 (beard, stoop)
    smile            0..1 (needs a face that is not "away")
    ink, halo        line colour and how strong a light halo is (for night)
    holding          list of (prop_name, hand) for the props drawn in a hand
"""
import math

import cv2
import numpy as np

AA = cv2.LINE_AA
INK = (0.09, 0.08, 0.1)
HEAD_FILL = (0.9, 0.93, 0.95)


def _p(x, y):
    return int(round(x * 4)), int(round(y * 4))


def line(img, a, b, col, w):
    cv2.line(img, _p(*a), _p(*b), col, max(1, int(round(w))), AA, 2)


def circle(img, c, r, col, w=-1):
    cv2.circle(img, _p(*c), max(1, int(r * 4)), col, w if w < 0 else max(1, int(round(w))), AA, 2)


def poly(img, pts, col, outline=None, w=2):
    p = np.array([_p(x, y) for x, y in pts], np.int32)
    cv2.fillPoly(img, [p], col, AA, 2)
    if outline is not None:
        cv2.polylines(img, [p], True, outline, max(1, int(round(w))), AA, 2)


def ik(root, target, a, b, bend):
    """Two-bone IK: returns the middle joint; bend = +1/-1 picks the side the joint bends to."""
    dx, dy = target[0] - root[0], target[1] - root[1]
    d = max(1e-3, min(math.hypot(dx, dy), a + b - 1e-3))
    ang = math.atan2(dy, dx)
    cos_a = (a * a + d * d - b * b) / (2 * a * d)
    off = math.acos(max(-1.0, min(1.0, cos_a)))
    t = ang + bend * off
    return root[0] + a * math.cos(t), root[1] + a * math.sin(t)


def figure(img, pose):
    s = pose.get("s", 1.0)
    ink = pose.get("ink", INK)
    W = 10 * s                                    # line width
    torso, upper, lower, thigh, shin, r = 410 * s, 150 * s, 140 * s, 210 * s, 200 * s, 40 * s
    age = pose.get("age", 0.0)
    lean = pose.get("lean", 0.0) + 0.12 * age
    hx, hy = pose["x"], pose["hip_y"]
    sit = pose.get("sit", 0.0)
    neck = (hx + math.sin(lean) * torso, hy - math.cos(lean) * torso)
    lx, ly = pose.get("look", (0, 0))
    head = (neck[0] + math.sin(lean) * (r + 8 * s) + lx * s, neck[1] - math.cos(lean) * (r + 8 * s) + ly * s)
    sh = (neck[0] + math.sin(lean) * 30 * s, neck[1] + math.cos(lean) * 30 * s)
    walk = pose.get("walk")
    segs = []
    # legs
    for side in (-1, 1):
        if sit > 0:
            knee = (hx + 150 * s * sit * (1 if pose.get("face") != "left" else -1) + side * 8 * s, hy + 10 * s)
            foot = (knee[0] + side * 6 * s, knee[1] + shin)
        else:
            sw = math.sin(walk + (0 if side < 0 else math.pi)) if walk is not None else 0.0
            foot = (hx + side * 22 * s + sw * 90 * s, hy + thigh + shin - (max(0.0, sw) * 25 * s if walk is not None else 0))
            knee = ik((hx, hy), foot, thigh, shin, 1 if pose.get("face") != "left" else -1)
        segs += [((hx, hy), knee), (knee, foot)]
    # arms
    hands = {}
    for side, key in ((-1, "hand_l"), (1, "hand_r")):
        tgt = pose.get(key)
        if tgt is None:
            sw = math.sin(walk + (math.pi if side < 0 else 0)) if walk is not None else 0.0
            tgt = (sh[0] + side * 30 * s + sw * 70 * s, sh[1] + upper + lower - 20 * s)
        e1, e2 = ik(sh, tgt, upper, lower, 1), ik(sh, tgt, upper, lower, -1)
        el = max((e1, e2), key=lambda e: e[1] + 0.3 * side * (e[0] - sh[0]))   # elbows hang down and out
        segs += [(sh, el), (el, tgt)]
        hands[key] = tgt
    segs.append(((hx, hy), neck))
    halo = pose.get("halo", 0.25)
    if halo > 0:
        hc = tuple(0.92 * halo + c * (1 - halo) for c in (0.0, 0.0, 0.0))
        for a, b in segs:
            line(img, a, b, (0.85, 0.87, 0.9), W + 5 * s * halo * 2)
        circle(img, head, r + 4 * s * (1 + halo), (0.85, 0.87, 0.9))
    for a, b in segs:
        line(img, a, b, ink, W)
    # props in hands (drawn before the head so the head stays on top)
    for name, key in pose.get("holding", []):
        PROPS[name](img, hands[key], s, pose)
    circle(img, head, r, HEAD_FILL)
    circle(img, head, r, ink, W * 0.9)
    face = pose.get("face", "away")
    if face != "away":
        e = 5 * s
        if face == "front":
            circle(img, (head[0] - 13 * s, head[1] - 6 * s), e, ink)
            circle(img, (head[0] + 13 * s, head[1] - 6 * s), e, ink)
            mx = head[0]
        else:
            d = -1 if face == "left" else 1
            circle(img, (head[0] + d * 18 * s, head[1] - 7 * s), e, ink)
            mx = head[0] + d * 16 * s
        sm = pose.get("smile", 0.0)
        cv2.ellipse(img, _p(mx, head[1] + 14 * s), (int(10 * s * 4), int((2 + 7 * sm) * s * 4)), 0, 10, 170, ink,
                    max(1, int(3 * s)), AA, 2)
        if age > 0.2:   # scruffy beard
            rng = np.random.default_rng(4)
            for i in range(int(14 * age)):
                a = math.radians(rng.uniform(25, 155))
                p0 = (mx + math.cos(a) * r * 0.75 - (head[0] - mx) * 0.3, head[1] + math.sin(a) * r * 0.75)
                line(img, p0, (p0[0], p0[1] + 9 * s * age), ink, 2.5 * s)
    elif age > 0.2:
        for i in range(int(8 * age)):
            a = math.radians(40 + i * 12)
            line(img, (head[0] + math.cos(a) * r, head[1] + math.sin(a) * r * 0.9),
                 (head[0] + math.cos(a) * (r + 7 * s * age), head[1] + math.sin(a) * (r + 7 * s * age)), ink, 2.5 * s)
    return dict(head=head, hands=hands, neck=neck)


# ------------------------------------------------------------------ props (line art)

def mug(img, c, s=1.0, pose=None, col=(0.95, 0.95, 0.94)):
    x, y = c
    poly(img, [(x - 22 * s, y - 50 * s), (x + 22 * s, y - 50 * s), (x + 19 * s, y), (x - 19 * s, y)], col, INK, 3 * s)
    cv2.ellipse(img, _p(x + 26 * s, y - 28 * s), (int(11 * s * 4), int(13 * s * 4)), 0, -90, 90, INK, max(1, int(3 * s)), AA, 2)


def phone(img, c, s=1.0, pose=None):
    x, y = c
    poly(img, [(x - 14 * s, y - 34 * s), (x + 14 * s, y - 34 * s), (x + 14 * s, y + 14 * s), (x - 14 * s, y + 14 * s)],
         (0.15, 0.15, 0.17), INK, 2 * s)
    g = (pose or {}).get("screen", 1.0)
    if g > 0:
        poly(img, [(x - 11 * s, y - 31 * s), (x + 11 * s, y - 31 * s), (x + 11 * s, y + 9 * s), (x - 11 * s, y + 9 * s)],
             (0.95 * g, 0.9 * g, 0.75 * g))
        if (pose or {}).get("battery_low"):
            poly(img, [(x - 6 * s, y - 4 * s), (x - 2 * s, y - 4 * s), (x - 2 * s, y + 2 * s), (x - 6 * s, y + 2 * s)],
                 (0.1, 0.1, 0.9))


def ball(img, c, s=1.0, pose=None):
    circle(img, (c[0], c[1] - 6 * s), 17 * s, (0.15, 0.15, 0.85))
    circle(img, (c[0], c[1] - 6 * s), 17 * s, INK, 3 * s)
    circle(img, (c[0] - 6 * s, c[1] - 12 * s), 4 * s, (0.6, 0.6, 1.0))


def bag(img, c, s=1.0, pose=None):
    x, y = c
    poly(img, [(x - 34 * s, y + 10 * s), (x + 34 * s, y + 10 * s), (x + 30 * s, y + 90 * s), (x - 30 * s, y + 90 * s)],
         (0.55, 0.7, 0.8), INK, 3 * s)
    line(img, (x - 14 * s, y + 10 * s), (x, y), INK, 3 * s); line(img, (x + 14 * s, y + 10 * s), (x, y), INK, 3 * s)
    line(img, (x - 18 * s, y + 4 * s), (x - 26 * s, y - 16 * s), (0.2, 0.6, 0.3), 5 * s)


def lamp(img, c, s=1.0, pose=None, on=None):
    """A small desk lamp; `c` is its base on the sill."""
    x, y = c
    on = (pose or {}).get("lamp_on", 1.0) if on is None else on
    poly(img, [(x - 26 * s, y), (x + 26 * s, y), (x + 20 * s, y - 10 * s), (x - 20 * s, y - 10 * s)], (0.3, 0.3, 0.32), INK, 3 * s)
    line(img, (x, y - 10 * s), (x, y - 70 * s), INK, 5 * s)
    shade = (0.45, 0.8, 1.0) if on > 0.5 else (0.55, 0.6, 0.62)
    poly(img, [(x - 30 * s, y - 70 * s), (x + 30 * s, y - 70 * s), (x + 18 * s, y - 108 * s), (x - 18 * s, y - 108 * s)],
         shade, INK, 3 * s)


def cap(img, c, s=1.0, col=(0.2, 0.25, 0.85)):
    cv2.ellipse(img, _p(c[0], c[1] - 3 * s), (int(10 * s * 4), int(5 * s * 4)), 0, 0, 360, col, -1, AA, 2)
    cv2.ellipse(img, _p(c[0], c[1] - 3 * s), (int(10 * s * 4), int(5 * s * 4)), 0, 0, 360, INK, max(1, int(2 * s)), AA, 2)


def paper(img, c, s=1.0):
    x, y = c
    poly(img, [(x - 16 * s, y), (x + 14 * s, y - 3 * s), (x + 18 * s, y - 14 * s), (x - 12 * s, y - 11 * s)],
         (0.93, 0.93, 0.9), INK, 2 * s)


def sprout(img, c, s=1.0, g=1.0):
    """The seedling in an old cup: g = 0..1 growth."""
    x, y = c
    mug(img, (x, y), s * 0.8, col=(0.75, 0.8, 0.86))
    if g <= 0:
        return
    top = y - 40 * s - 70 * s * g
    line(img, (x, y - 40 * s), (x, top), (0.15, 0.5, 0.2), 4 * s)
    for k in range(int(1 + 3 * g)):
        yy = y - 50 * s - k * 20 * s
        if yy < top:
            break
        d = 1 if k % 2 else -1
        cv2.ellipse(img, _p(x + d * 12 * s, yy), (int(12 * s * 4), int(6 * s * 4)), d * -25, 0, 360, (0.25, 0.7, 0.3), -1, AA, 2)


def bottle(img, c, s=1.0):
    x, y = c
    poly(img, [(x - 14 * s, y), (x + 14 * s, y), (x + 14 * s, y - 60 * s), (x + 6 * s, y - 72 * s), (x - 6 * s, y - 72 * s),
               (x - 14 * s, y - 60 * s)], (0.9, 0.82, 0.62), INK, 2.5 * s)
    poly(img, [(x - 13 * s, y - 2 * s), (x + 13 * s, y - 2 * s), (x + 13 * s, y - 35 * s), (x - 13 * s, y - 35 * s)], (0.85, 0.7, 0.45))


def pot(img, c, s=1.0, seed=0):
    x, y = c
    poly(img, [(x - 18 * s, y - 30 * s), (x + 18 * s, y - 30 * s), (x + 13 * s, y), (x - 13 * s, y)], (0.3, 0.45, 0.75), INK, 2.5 * s)
    rng = np.random.default_rng(seed)
    for k in range(4):
        a = math.radians(rng.uniform(-60, 60) - 90)
        L = rng.uniform(25, 45) * s
        tip = (x + math.cos(a) * L, y - 30 * s + math.sin(a) * L)
        line(img, (x, y - 30 * s), tip, (0.15, 0.5, 0.2), 3 * s)
        cv2.ellipse(img, _p(*tip), (int(9 * s * 4), int(5 * s * 4)), math.degrees(a), 0, 360, (0.25, 0.65, 0.3), -1, AA, 2)


def leaf(img, c, s=1.0):
    """The fresh green leaf, still wet."""
    x, y = c
    pts = [(x - 26 * s, y), (x - 8 * s, y - 13 * s), (x + 16 * s, y - 10 * s), (x + 28 * s, y - 2 * s), (x + 8 * s, y + 6 * s)]
    poly(img, pts, (0.2, 0.72, 0.35), INK, 2 * s)
    line(img, (x - 24 * s, y), (x + 24 * s, y - 3 * s), (0.15, 0.5, 0.25), 1.5 * s)
    for dx, dy in ((-6, -6), (10, -4)):
        circle(img, (x + dx * s, y + dy * s), 2.5 * s, (0.95, 0.95, 0.95))


def bird(img, c, s=1.0, t=0.0, flying=0.0):
    x, y = c
    poly(img, [(x - 22 * s, y - 14 * s), (x - 4 * s, y - 26 * s), (x + 16 * s, y - 22 * s), (x + 22 * s, y - 12 * s),
               (x + 8 * s, y - 2 * s), (x - 18 * s, y - 4 * s), (x - 34 * s, y - 2 * s)], (0.2, 0.22, 0.25), INK, 2 * s)
    circle(img, (x + 14 * s, y - 28 * s), 9 * s, (0.2, 0.22, 0.25))
    poly(img, [(x + 22 * s, y - 30 * s), (x + 32 * s, y - 27 * s), (x + 22 * s, y - 25 * s)], (0.1, 0.55, 0.95))
    circle(img, (x + 16 * s, y - 30 * s), 1.8 * s, (0.95, 0.95, 0.95))
    if flying > 0:
        f = math.sin(t * 30) * 22 * s
        line(img, (x - 2 * s, y - 18 * s), (x - 20 * s, y - 40 * s - f), INK, 4 * s)
        line(img, (x + 4 * s, y - 18 * s), (x + 18 * s, y - 42 * s - f), INK, 4 * s)
    else:
        line(img, (x - 2 * s, y - 2 * s), (x - 4 * s, y + 8 * s), INK, 2 * s)
        line(img, (x + 6 * s, y - 2 * s), (x + 8 * s, y + 8 * s), INK, 2 * s)


PROPS = {"mug": lambda img, h, s, p: mug(img, (h[0], h[1] + 20 * s), s),
         "phone": lambda img, h, s, p: phone(img, h, s, p),
         "ball": lambda img, h, s, p: ball(img, (h[0], h[1] + 10 * s), s),
         "bag": lambda img, h, s, p: bag(img, h, s),
         "lamp": lambda img, h, s, p: lamp(img, (h[0], h[1] + 110 * s), s, p),
         "cup": lambda img, h, s, p: mug(img, (h[0], h[1] + 20 * s), s * 0.85, col=(0.7, 0.85, 0.95)),
         "cap": lambda img, h, s, p: cap(img, (h[0], h[1] + 6 * s), s),
         "paper": lambda img, h, s, p: paper(img, (h[0], h[1] + 8 * s), s)}
