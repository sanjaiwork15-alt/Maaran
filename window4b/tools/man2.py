"""Window 4B Ep 3: the man, v2 – the Ep 1 cartoon person rebuilt with proper anatomy.

Same look as the city people (round head with a dark hair cap, blue top, dark trousers, flat colours,
dark outline), but with a neck, shoulders, two-part arms with hands, a waist, two-part legs and shoes.

    draw(canvas, x, feet_y, height, pose)   # canvas: float BGR 0..1, height in px (1.75 m)

pose keys:
    view     "back" (looking out of the window) | "front" | "side" (facing right; side_dir=-1 = left)
    arms     "down" | "sill" (both hands on the sill at sill_y) | "phone" | "wave" | "hold" (one hand forward)
    walk     phase in radians, or None
    look     head turn in px (x offset)
    age      0..1  (hair grows, beard in front/side views, clothes fade)
    smile    0..1
    sill_y   row of the sill top (for "sill")
"""
import math

import cv2
import numpy as np

AA = cv2.LINE_AA
INK = (0.12, 0.11, 0.13)
SKIN = (0.55, 0.68, 0.86)
HAIR = (0.1, 0.1, 0.12)
TOP = (0.62, 0.42, 0.22)        # blue top (BGR)
PANTS = (0.25, 0.22, 0.2)
SHOE = (0.12, 0.12, 0.13)


class Pen:
    """Shapes are queued and drawn per group: all outlines first, then all fills, so the joints
    inside one group (shoulder-elbow-hand, hip-knee-foot) show no seams."""

    def __init__(self, img, ow):
        self.img, self.ow, self.q = img, ow, []

    def P(self, pts):
        return np.array([[int(round(x * 4)), int(round(y * 4))] for x, y in pts], np.int32)

    def poly(self, pts, col):
        self.q.append(("poly", self.P(pts), col))

    def limb(self, a, b, wa, wb, col):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) + 1e-6
        nx, ny = -dy / L, dx / L
        quad = [(a[0] + nx * wa, a[1] + ny * wa), (b[0] + nx * wb, b[1] + ny * wb),
                (b[0] - nx * wb, b[1] - ny * wb), (a[0] - nx * wa, a[1] - ny * wa)]
        self.q.append(("poly", self.P(quad), col))
        for c, r in ((a, wa), (b, wb)):
            self.q.append(("circ", self.P([c])[0], r, col))

    def ell(self, c, ax, ay, col, ang=0, outline=True):
        self.q.append(("ell", self.P([c])[0], ax, ay, ang, col, outline))

    def flush(self):
        o = int(round(self.ow * 4))
        for it in self.q:
            if it[0] == "poly":
                cv2.polylines(self.img, [it[1]], True, INK, max(1, int(self.ow * 2)), AA, 2)
            elif it[0] == "circ":
                cv2.circle(self.img, tuple(it[1]), int(it[2] * 4) + o, INK, -1, AA, 2)
            elif it[6]:
                cv2.ellipse(self.img, tuple(it[1]), (int(it[2] * 4) + o, int(it[3] * 4) + o), it[4], 0, 360, INK, -1, AA, 2)
        for it in self.q:
            if it[0] == "poly":
                cv2.fillPoly(self.img, [it[1]], it[2], AA, 2)
            elif it[0] == "circ":
                cv2.circle(self.img, tuple(it[1]), int(it[2] * 4), it[3], -1, AA, 2)
            else:
                cv2.ellipse(self.img, tuple(it[1]), (int(it[2] * 4), int(it[3] * 4)), it[4], 0, 360, it[5], -1, AA, 2)
        self.q = []

    def arc(self, c, ax, ay, a0, a1, col, w):
        self.flush()
        cv2.ellipse(self.img, tuple(self.P([c])[0]), (int(ax * 4), int(ay * 4)), 0, a0, a1, col, max(1, int(w)), AA, 2)

    def dot(self, c, r, col):
        self.flush()
        cv2.circle(self.img, tuple(self.P([c])[0]), max(1, int(r * 4)), col, -1, AA, 2)


def ik(root, target, a, b, bend):
    dx, dy = target[0] - root[0], target[1] - root[1]
    d = max(1e-3, min(math.hypot(dx, dy), a + b - 1e-3))
    ang = math.atan2(dy, dx)
    off = math.acos(max(-1.0, min(1.0, (a * a + d * d - b * b) / (2 * a * d))))
    t = ang + bend * off
    return root[0] + a * math.cos(t), root[1] + a * math.sin(t)


def hand(pen, at, toward, r, col=SKIN, thumb_side=1):
    """A mitten hand with a thumb, pointing along `toward` (unit vector)."""
    tx, ty = toward
    c = (at[0] + tx * r * 0.6, at[1] + ty * r * 0.6)
    ang = math.degrees(math.atan2(ty, tx))
    pen.ell(c, r * 1.05, r * 0.8, col, ang)
    nx, ny = -ty * thumb_side, tx * thumb_side
    pen.ell((at[0] + tx * r * 0.2 + nx * r * 0.8, at[1] + ty * r * 0.2 + ny * r * 0.8), r * 0.45, r * 0.3, col, ang - 30 * thumb_side)


def draw(canvas, x, feet_y, height, pose):
    H = height
    view = pose.get("view", "back")
    sd = pose.get("side_dir", 1)
    age = pose.get("age", 0.0)
    ow = max(1.5, H * 0.0045)
    pen = Pen(canvas, ow)
    top = tuple(c * (1 - 0.3 * age) + 0.15 * age for c in pose.get("top", TOP))
    pants = pose.get("pants", PANTS)
    walk = pose.get("walk")
    # proportions (fractions of height)
    head_r = 0.068 * H
    head_c = (x + pose.get("look", 0), feet_y - H + head_r * 1.05)
    neck_b = (x, feet_y - 0.82 * H)
    sh_y = feet_y - 0.80 * H
    sh_w = 0.13 * H if view != "side" else 0.06 * H
    hip_y = feet_y - 0.50 * H
    hip_w = 0.085 * H if view != "side" else 0.05 * H
    upper, fore = 0.17 * H, 0.15 * H
    thigh, shin = 0.245 * H, 0.235 * H
    arm_w, leg_w = 0.034 * H, 0.05 * H
    shL, shR = (x - sh_w + 0.02 * H, sh_y + 0.02 * H), (x + sh_w - 0.02 * H, sh_y + 0.02 * H)
    hipL, hipR = (x - hip_w * 0.55, hip_y), (x + hip_w * 0.55, hip_y)

    # ---- hands targets
    arms = pose.get("arms", "down")
    tgt = {}
    for side, sh in ((-1, shL), (1, shR)):
        if arms == "sill":
            tgt[side] = (x + side * 0.17 * H, pose.get("sill_y", feet_y - 0.45 * H))
        elif arms == "wave":
            tgt[side] = (x + side * 0.30 * H, sh_y - 0.22 * H + 0.03 * H * math.sin(pose.get("t", 0) * 10 + side))
        elif arms == "phone" and side == 1:
            tgt[side] = (x + 0.10 * H * (sd if view == "side" else 0.3), sh_y - 0.05 * H) if view != "back" else (x + 0.06 * H, sh_y + 0.04 * H)
        elif arms == "hold" and side == 1:
            tgt[side] = pose.get("hold_at", (x + 0.18 * H, sh_y + 0.18 * H))
        else:
            sw = math.sin(walk + (math.pi if side < 0 else 0)) * 0.12 * H if walk is not None else 0.0
            if view == "side":
                tgt[side] = (sh[0] + sw * sd, sh[1] + upper + fore - 0.02 * H)
            else:
                tgt[side] = (sh[0] + side * 0.025 * H, sh[1] + upper + fore - 0.01 * H)

    def arm(side):
        sh = shL if side < 0 else shR
        h = tgt[side]
        e1, e2 = ik(sh, h, upper, fore, 1), ik(sh, h, upper, fore, -1)
        out = 0.0 if (arms == "phone" and side == 1) else 0.4     # a phone arm tucks its elbow in
        el = max((e1, e2), key=lambda e: e[1] + out * side * (e[0] - sh[0]))   # elbows down and out
        if arms == "phone" and side == 1:     # elbow tucked down in front of the chest, hand up at the face
            f_ = sd if view == "side" else 0.3
            el = (x + f_ * 0.09 * H, sh_y + 0.15 * H)
            h = tgt[side] = (x + f_ * 0.10 * H, sh_y - 0.02 * H)
        pen.limb(sh, el, arm_w, arm_w * 0.9, top)
        pen.limb(el, h, arm_w * 0.85, arm_w * 0.7, top)
        d = (h[0] - el[0], h[1] - el[1]); L = math.hypot(*d) + 1e-6
        if arms == "phone" and side == 1:
            pen.flush()
            px = h[0] + (sd if view == "side" else 1) * 0.01 * H
            cv2.rectangle(pen.img, (int((px - 0.022 * H) * 4), int((h[1] - 0.045 * H) * 4)),
                          (int((px + 0.022 * H) * 4), int((h[1] + 0.035 * H) * 4)), INK, -1, AA, 2)
            cv2.rectangle(pen.img, (int((px - 0.016 * H) * 4), int((h[1] - 0.039 * H) * 4)),
                          (int((px + 0.016 * H) * 4), int((h[1] + 0.025 * H) * 4)),
                          tuple(c * pose.get("screen", 1.0) for c in (0.95, 0.9, 0.75)), -1, AA, 2)
        hand(pen, h, (d[0] / L, d[1] / L), 0.03 * H, thumb_side=(-side if view == "back" else side))
        pen.flush()

    def leg(side):
        hp = hipL if side < 0 else hipR
        if walk is not None:
            sw = math.sin(walk + (0 if side < 0 else math.pi))
            foot = (hp[0] + sw * 0.16 * H * (sd if view == "side" else 0.4), feet_y - max(0.0, sw) * 0.03 * H)
        else:
            foot = (hp[0] + side * 0.02 * H, feet_y)
        bend = -sd if view == "side" else side
        knee = ik(hp, foot, thigh, shin, bend)
        if view != "side" and walk is None:
            knee = ((hp[0] + foot[0]) / 2, (hp[1] + foot[1]) / 2)
        pen.limb(hp, knee, leg_w, leg_w * 0.85, pants)
        pen.limb(knee, foot, leg_w * 0.85, leg_w * 0.75, pants)
        fd = sd if view == "side" else 0
        pen.ell((foot[0] + fd * 0.025 * H, foot[1] + 0.005 * H), 0.05 * H if view == "side" else 0.035 * H, 0.022 * H, SHOE)
        pen.flush()

    back_arm_first = view in ("back", "side")
    # legs, then torso, then arms (arms in front for "front"/"sill"; behind torso edge otherwise)
    for s_ in (-1, 1):
        leg(s_)
    if view == "side":
        arm(-sd)
    # torso: shoulders -> waist, plus hips/belt
    torso = [(x - sh_w, sh_y + 0.03 * H), (x - sh_w * 0.75, sh_y - 0.012 * H), (x + sh_w * 0.75, sh_y - 0.012 * H),
             (x + sh_w, sh_y + 0.03 * H), (x + hip_w * 1.05, hip_y + 0.01 * H), (x - hip_w * 1.05, hip_y + 0.01 * H)]
    pen.limb((x, sh_y), neck_b, 0.035 * H, 0.033 * H, SKIN)                         # neck
    pen.flush()
    pen.poly(torso, top)
    pen.poly([(x - hip_w * 1.05, hip_y - 0.005 * H), (x + hip_w * 1.05, hip_y - 0.005 * H),
              (x + hip_w * 1.02, hip_y + 0.035 * H), (x - hip_w * 1.02, hip_y + 0.035 * H)], pants)
    if view == "front":
        pen.poly([(x - 0.03 * H, sh_y - 0.012 * H), (x + 0.03 * H, sh_y - 0.012 * H), (x, sh_y + 0.03 * H)], SKIN)
    pen.flush()
    # head
    hx, hy = head_c
    if view == "back":
        pen.ell((hx - head_r * 0.98, hy + head_r * 0.1), head_r * 0.2, head_r * 0.3, SKIN)    # ears
        pen.ell((hx + head_r * 0.98, hy + head_r * 0.1), head_r * 0.2, head_r * 0.3, SKIN)
        pen.ell((hx, hy), head_r, head_r * 1.05, HAIR)
    else:
        pen.ell((hx, hy), head_r, head_r * 1.05, SKIN)
        if view == "side":
            pen.flush()
            cv2.ellipse(pen.img, tuple(pen.P([(hx, hy - head_r * 0.15)])[0]), (int(head_r * 4 * 0.98), int(head_r * 4 * 0.88)),
                        0, 180, 360, HAIR, -1, AA, 2)
            cv2.ellipse(pen.img, tuple(pen.P([(hx - sd * head_r * 0.45, hy)])[0]), (int(head_r * 4 * 0.52), int(head_r * 4 * 0.8)),
                        0, 0, 360, HAIR, -1, AA, 2)
            pen.ell((hx - sd * head_r * 0.05, hy + head_r * 0.12), head_r * 0.16, head_r * 0.24, SKIN)
            ex = hx + sd * head_r * 0.55
            pen.dot((ex, hy - head_r * 0.05), head_r * 0.09, INK)
            pen.ell((hx + sd * head_r * 1.0, hy + head_r * 0.15), head_r * 0.13, head_r * 0.12, SKIN, outline=False)
            pen.arc((hx + sd * head_r * 0.6, hy + head_r * 0.45), head_r * 0.22, head_r * (0.06 + 0.12 * pose.get("smile", 0)),
                    20, 160, INK, ow * 1.5)
        else:
            pen.flush()
            cv2.ellipse(pen.img, tuple(pen.P([(hx, hy - head_r * 0.2)])[0]), (int(head_r * 4 * 1.02), int(head_r * 4 * 0.9)),
                        0, 180, 360, HAIR, -1, AA, 2)
            for d in (-1, 1):
                pen.dot((hx + d * head_r * 0.35, hy + head_r * 0.05), head_r * 0.09, INK)
            pen.arc((hx, hy + head_r * 0.45), head_r * 0.25, head_r * (0.05 + 0.15 * pose.get("smile", 0)), 20, 160,
                    INK, ow * 1.5)
        if age > 0.2:
            rng = np.random.default_rng(3)
            bx = hx + (sd * head_r * 0.3 if view == "side" else 0)
            for i in range(int(40 * age)):
                a = math.radians(rng.uniform(20, 160))
                rr = head_r * rng.uniform(0.75, 1.0)
                pen.dot((bx + math.cos(a) * rr * (0.8 if view == "side" else 0.95), hy + math.sin(a) * rr), head_r * 0.07, HAIR)
    pen.flush()
    # arms on top
    if view == "side":
        arm(sd)
    else:
        arm(-1); arm(1)
    return dict(head=head_c, hands=tgt, sh_y=sh_y)
