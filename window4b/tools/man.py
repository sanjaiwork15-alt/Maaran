"""Window 4B Ep 3: the man, drawn in code in the flat 2D style of the master art.

He stands inside Flat 4B, close to the camera, so he is large and seen mostly from behind,
backlit by the window: a dark-ish figure with a soft rim of window light. All sizes are in output
pixels (1920 x 1080). `draw_man(canvas, pose)` returns the canvas; `pose` is a dict:

    x, y_head      centre x of the body, top of the head
    scale          1.0 = head ~120 px tall
    view           "back" | "left" | "right"   (profile views face that way)
    arms           "sill" (hands on the sill) | "down" | "phone" | "lamp" | "ball" | "wave" | "reach"
    age            0..1  (hair and beard grow, clothes fade and fray)
    light          (b, g, r) colour of the window light for the rim
    shade          0..1  how dark the back is (1 = night silhouette)
    smile          0..1  (profile only)
    phone_glow     0..1  screen light on the face/hands
"""
import math

import cv2
import numpy as np

AA = cv2.LINE_AA
OUT = (0.1, 0.09, 0.1)


def _P(pts):
    return np.array([[int(round(x * 4)), int(round(y * 4))] for x, y in pts], np.int32)


def _ell(img, c, ax, ay, col, ang=0, a0=0, a1=360):
    cv2.ellipse(img, (int(c[0] * 4), int(c[1] * 4)), (max(1, int(ax * 4)), max(1, int(ay * 4))), ang, a0, a1,
                col, -1, AA, 2)


def _poly(img, pts, col):
    cv2.fillPoly(img, [_P(pts)], col, AA, 2)


def _limb(img, p0, p1, w0, w1, col):
    """A tapered limb as a polygon with round ends."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy) + 1e-6
    nx, ny = -dy / L, dx / L
    _poly(img, [(p0[0] + nx * w0, p0[1] + ny * w0), (p1[0] + nx * w1, p1[1] + ny * w1),
                (p1[0] - nx * w1, p1[1] - ny * w1), (p0[0] - nx * w0, p0[1] - ny * w0)], col)
    _ell(img, p0, w0, w0, col); _ell(img, p1, w1, w1, col)


def figure(pose, H, W):
    """Draw the man into a colour layer + mask (no lighting yet)."""
    col = np.zeros((H, W, 3), np.float32)
    s = pose.get("scale", 1.0)
    x, yh = pose["x"], pose["y_head"]
    view = pose.get("view", "back")
    age = pose.get("age", 0.0)
    skin = (0.47, 0.6, 0.78)
    hair = (0.12, 0.13, 0.16) if age < 0.5 else (0.2, 0.22, 0.25)
    shirt = tuple(c * (1 - 0.25 * age) + 0.12 * age for c in pose.get("shirt", (0.42, 0.33, 0.22)))  # faded blue-grey
    hh = 120 * s                       # head height
    hw = 98 * s
    cy = yh + hh / 2
    neck_y = yh + hh * 0.92
    sh_y = yh + hh * 1.25              # shoulder line
    sh_w = 150 * s if view == "back" else 95 * s
    bottom = H + 40
    face = -1 if view == "left" else 1
    # torso (shoulders down past the bottom of the frame)
    if view == "back":
        torso = [(x - sh_w, sh_y + 30 * s), (x - sh_w * 0.8, sh_y - 4 * s), (x - 30 * s, sh_y - 14 * s),
                 (x + 30 * s, sh_y - 14 * s), (x + sh_w * 0.8, sh_y - 4 * s), (x + sh_w, sh_y + 30 * s),
                 (x + sh_w * 0.92, bottom), (x - sh_w * 0.92, bottom)]
    else:
        torso = [(x - sh_w * 0.9, sh_y + 20 * s), (x - sh_w * 0.5, sh_y - 10 * s), (x + sh_w * 0.55, sh_y - 8 * s),
                 (x + sh_w * 0.95, sh_y + 30 * s), (x + sh_w * 0.85, bottom), (x - sh_w * 0.85, bottom)]
    # arms (drawn before the torso when behind it)
    arms = pose.get("arms", "down")
    sill_y = pose.get("sill_y", 880)
    sl = (x - sh_w * 0.9, sh_y + 22 * s); sr = (x + sh_w * 0.9, sh_y + 22 * s)
    hands = []
    if arms == "sill":
        hl, hr = (x - sh_w * 1.15, sill_y), (x + sh_w * 1.15, sill_y)
        el, er = (x - sh_w * 1.2, (sh_y + sill_y) / 2), (x + sh_w * 1.2, (sh_y + sill_y) / 2)
        segs = [(sl, el, hl), (sr, er, hr)]
        hands = [hl, hr]
    elif arms in ("phone", "lamp", "ball"):
        # the near arm raised in front of the body: hand at chest/face height
        hy = sh_y + (10 if arms == "phone" else 60) * s
        hx = x + face * (sh_w * 0.9 if view != "back" else 30 * s)
        hd = (hx + face * 60 * s, hy - (20 if arms == "phone" else 0) * s)
        segs = [(sl, (x - sh_w * 1.0, sh_y + 160 * s), (x - sh_w * 0.95, sh_y + 300 * s)),
                (sr, (x + face * sh_w * 0.6, sh_y + 140 * s), hd)]
        hands = [hd]
    elif arms == "wave":
        segs = [(sl, (x - sh_w * 1.4, sh_y - 60 * s), (x - sh_w * 1.5, sh_y - 200 * s)),
                (sr, (x + sh_w * 1.4, sh_y - 60 * s), (x + sh_w * 1.5, sh_y - 200 * s))]
        hands = [(x - sh_w * 1.5, sh_y - 200 * s), (x + sh_w * 1.5, sh_y - 200 * s)]
    elif arms == "reach":
        hd = (x + face * sh_w * 2.0, sill_y - 6)
        segs = [(sl, (x - sh_w * 1.0, sh_y + 160 * s), (x - sh_w * 0.95, sh_y + 300 * s)),
                (sr, (x + face * sh_w * 1.5, (sh_y + sill_y) / 2), hd)]
        hands = [hd]
    else:
        segs = [(sl, (x - sh_w * 1.02, sh_y + 160 * s), (x - sh_w * 0.98, sh_y + 300 * s)),
                (sr, (x + sh_w * 1.02, sh_y + 160 * s), (x + sh_w * 0.98, sh_y + 300 * s))]
    for a, e, h in segs:
        _limb(col, a, e, 30 * s, 25 * s, shirt)
        _limb(col, e, h, 24 * s, 17 * s, shirt)
    _poly(col, torso, shirt)
    # neck and head
    _limb(col, (x, sh_y - 10 * s), (x + (0 if view == "back" else face * 6 * s), neck_y), 26 * s, 24 * s, skin)
    hx = x + (0 if view == "back" else face * 8 * s)
    _ell(col, (hx, cy), hw / 2, hh / 2, skin)
    if view == "back":
        _ell(col, (hx - hw / 2, cy + 6 * s), 11 * s, 18 * s, skin)
        _ell(col, (hx + hw / 2, cy + 6 * s), 11 * s, 18 * s, skin)
        hl_ = hh * (0.62 + 0.25 * age)
        _ell(col, (hx, yh + hl_ / 2 - 2 * s), hw / 2 + 4 * s, hl_ / 2 + 4 * s, hair)
        if age > 0.3:   # longer, unkempt hair over the collar
            _poly(col, [(hx - hw / 2 - 2 * s, cy), (hx + hw / 2 + 2 * s, cy), (hx + hw / 2 - 4 * s, neck_y + 10 * s * age),
                        (hx - hw / 2 + 4 * s, neck_y + 10 * s * age)], hair)
    else:
        # profile: hair on top/back, nose, brow, beard
        _ell(col, (hx - face * 10 * s, cy - 16 * s), hw / 2 + 2 * s, hh / 2 - 8 * s, hair, 0, 180 if face > 0 else 0,
             360 if face > 0 else 180)
        _ell(col, (hx - face * 22 * s, cy - 2 * s), hw / 2 - 18 * s, hh / 2 - 6 * s, hair)
        _poly(col, [(hx + face * hw / 2 - 2 * s, cy - 6 * s), (hx + face * (hw / 2 + 12 * s), cy + 12 * s),
                    (hx + face * hw / 2 - 2 * s, cy + 16 * s)], skin)
        _ell(col, (hx - face * 4 * s, cy + 6 * s), 10 * s, 16 * s, skin)          # ear
        if age > 0.2:
            _ell(col, (hx + face * 14 * s, cy + hh * 0.36), hw * 0.36, hh * 0.2 * (0.6 + age), hair)
    for h in hands:
        _ell(col, h, 18 * s, 14 * s, skin)
    mask = (col.max(axis=2) > 0).astype(np.float32)
    return col, mask, dict(cy=cy, hx=hx, hh=hh, hw=hw, face=face, hands=hands, sh_y=sh_y)


def draw_man(canvas, pose):
    H, W = canvas.shape[:2]
    col, mask, geo = figure(pose, H, W)
    a = cv2.GaussianBlur(mask, (0, 0), 0.7)
    light = np.array(pose.get("light", (0.75, 0.88, 1.0)), np.float32)
    shade = pose.get("shade", 0.45)
    # backlit: the side we see is in shadow, lit softly by the room; the edges catch the window light
    body = col * (1 - 0.75 * shade) + col * light * 0.12
    inner = cv2.erode(mask, np.ones((9, 9), np.uint8))
    rim = cv2.GaussianBlur(mask - inner, (0, 0), 3.0)
    body = body + rim[..., None] * light * (0.55 * (1 - 0.4 * shade))
    # simple folds on the shirt and a soft vertical gradient (darker low down)
    g = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    body = body * (1 - 0.25 * np.clip((g * H - geo["sh_y"]) / 500, 0, 1))
    if pose.get("phone_glow", 0) > 0 and geo["hands"]:
        hx, hy = geo["hands"][-1]
        glow = np.zeros((H, W), np.float32)
        cv2.circle(glow, (int(hx), int(hy)), 70, 1.0, -1)
        glow = cv2.GaussianBlur(glow, (0, 0), 40) * pose["phone_glow"]
        body = body + (glow * mask)[..., None] * np.array([0.9, 0.85, 0.7], np.float32) * 0.6
        cv2.rectangle(canvas, (int(hx - 14), int(hy - 26)), (int(hx + 14), int(hy + 18)), (0.95, 0.9, 0.85), -1, AA)
    out_l = cv2.dilate(mask, np.ones((3, 3), np.uint8)) - mask
    canvas[:] = canvas * (1 - a[..., None]) + body * a[..., None]
    canvas[:] = canvas * (1 - out_l[..., None] * 0.8) + np.array(OUT, np.float32) * out_l[..., None] * 0.8
    return canvas, geo
