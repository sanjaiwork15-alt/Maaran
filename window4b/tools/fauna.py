"""Window 4B Ep 3: animals and small street props, flat 2D with a dark outline like the Ep 1 people.

All functions draw straight onto a float BGR canvas (0..1) at output resolution.
x, y = feet / base point in output px; u = output px per metre at that spot.
"""
import math

import cv2
import numpy as np

AA = cv2.LINE_AA
INK = (0.13, 0.12, 0.14)


def _P(pts):
    return np.array([[int(round(x * 4)), int(round(y * 4))] for x, y in pts], np.int32)


def ell(img, c, ax, ay, col, ang=0, ow=1.0):
    if ow > 0:
        cv2.ellipse(img, (int(c[0] * 4), int(c[1] * 4)), (int((ax + ow) * 4), int((ay + ow) * 4)), ang, 0, 360, INK, -1, AA, 2)
    cv2.ellipse(img, (int(c[0] * 4), int(c[1] * 4)), (max(1, int(ax * 4)), max(1, int(ay * 4))), ang, 0, 360, col, -1, AA, 2)


def poly(img, pts, col, ow=1.0):
    p = _P(pts)
    if ow > 0:
        cv2.polylines(img, [p], True, INK, max(1, int(ow * 2)), AA, 2)
    cv2.fillPoly(img, [p], col, AA, 2)


def line(img, a, b, col, w):
    cv2.line(img, (int(a[0] * 4), int(a[1] * 4)), (int(b[0] * 4), int(b[1] * 4)), col, max(1, int(round(w))), AA, 2)


def quadruped(img, x, y, u, phase, facing, body_l, body_h, leg_l, col, head, tail, neck=0.25, head_down=0.0,
              walking=True, belly=None):
    """Generic four-legged animal standing on (x, y)."""
    f = facing
    by = y - leg_l * u
    bl, bh = body_l * u, body_h * u
    ow = max(0.8, u * 0.02)
    legs = []
    for i, dx in enumerate((-0.38, -0.25, 0.25, 0.38)):
        sw = math.sin(phase + (0, math.pi, math.pi, 0)[i]) * 0.12 * u if walking else 0.0
        hx = x + f * dx * bl
        legs.append(((hx, by), (hx + f * sw, y)))
    for a, b in legs[:2] + legs[2:]:
        line(img, a, b, INK, max(1, u * 0.07) + 2 * ow)
        line(img, a, b, col, max(1, u * 0.07))
    ell(img, (x, by - bh * 0.3), bl / 2, bh / 2, col, 0, ow)
    if belly is not None:
        ell(img, (x, by - bh * 0.1), bl * 0.35, bh * 0.22, belly, 0, 0)
    # neck + head
    nx, ny = x + f * bl * 0.42, by - bh * 0.5
    hx = nx + f * neck * u * (0.6 + 0.6 * head_down)
    hy = ny - neck * u * (1 - 1.9 * head_down)
    line(img, (nx, ny), (hx, hy), INK, head[1] * u * 1.2 + 2 * ow)
    line(img, (nx, ny), (hx, hy), col, head[1] * u * 1.2)
    ell(img, (hx + f * head[0] * u * 0.4, hy), head[0] * u * 0.6, head[1] * u * 0.55, col, f * (30 * head_down), ow)
    ell(img, (hx + f * head[0] * u * 0.85, hy + head[1] * u * 0.15), head[1] * u * 0.12, head[1] * u * 0.12, INK, 0, 0)
    ell(img, (hx + f * head[0] * u * 0.2, hy - head[1] * u * 0.15), head[1] * u * 0.08, head[1] * u * 0.08, INK, 0, 0)
    # tail
    tx, ty = x - f * bl * 0.5, by - bh * 0.5
    a = math.radians(tail[1] + 10 * math.sin(phase * 0.7))
    line(img, (tx, ty), (tx - f * math.cos(a) * tail[0] * u, ty - math.sin(a) * tail[0] * u), INK, max(1, u * 0.05) + 2 * ow)
    line(img, (tx, ty), (tx - f * math.cos(a) * tail[0] * u, ty - math.sin(a) * tail[0] * u), col, max(1, u * 0.05))
    return (hx, hy)


def dog(img, x, y, u, phase, facing=1, col=(0.3, 0.45, 0.62), walking=True, sniff=0.0):
    hd = quadruped(img, x, y, u, phase, facing, 0.75, 0.3, 0.38, col, (0.26, 0.2), (0.3, 50), 0.2, sniff, walking)
    ell(img, (hd[0] - facing * 0.04 * u, hd[1] - 0.12 * u), 0.04 * u, 0.07 * u, tuple(c * 0.7 for c in col), 20, 0.6)


def deer(img, x, y, u, phase, facing=1, walking=True, head_down=0.0):
    col = (0.35, 0.55, 0.72)
    hd = quadruped(img, x, y, u, phase, facing, 1.15, 0.45, 0.8, col, (0.3, 0.2), (0.15, 70), 0.55, head_down,
                   walking, belly=(0.75, 0.82, 0.88))
    for d in (-1, 1):   # ears
        ell(img, (hd[0] - facing * 0.03 * u + d * 0.04 * u, hd[1] - 0.15 * u), 0.04 * u, 0.09 * u, col, d * 25, 0.6)
    ell(img, (x - facing * 0.58 * u, y - 0.8 * u - 0.3 * u), 0.06 * u, 0.06 * u, (0.95, 0.95, 0.95), 0, 0.5)   # white tail


def pigeon(img, x, y, u, phase=0.0, facing=1, peck=0.0):
    s = u * 0.32
    col = (0.62, 0.58, 0.58)
    ell(img, (x, y - s * 0.45), s * 0.55, s * 0.32, col, 0, max(0.5, s * 0.06))
    hy = y - s * 0.8 + peck * s * 0.5
    ell(img, (x + facing * s * 0.45, hy), s * 0.18, s * 0.18, (0.5, 0.48, 0.5), 0, max(0.5, s * 0.06))
    ell(img, (x + facing * s * 0.6, hy + s * 0.02), s * 0.06, s * 0.04, (0.3, 0.55, 0.85), 0, 0)
    poly(img, [(x - facing * s * 0.45, y - s * 0.5), (x - facing * s * 0.85, y - s * 0.6), (x - facing * s * 0.8, y - s * 0.35)],
         (0.45, 0.43, 0.45), max(0.5, s * 0.05))


def flying_bird(img, x, y, size, t, col=INK):
    f = math.sin(t * 14) * size * 0.5
    line(img, (x - size, y - f), (x, y), col, max(1, size * 0.25))
    line(img, (x + size, y - f), (x, y), col, max(1, size * 0.25))


def monkey(img, x, y, u, phase, facing=1, sitting=False):
    col = (0.25, 0.4, 0.55)
    ow = max(0.6, u * 0.02)
    by = y - (0.25 if sitting else 0.35) * u
    ell(img, (x, by - 0.12 * u), 0.14 * u, 0.2 * u, col, -facing * 15, ow)
    a = math.radians(200 + 30 * math.sin(phase))
    tx = x - facing * 0.12 * u
    line(img, (tx, by), (tx - facing * 0.25 * u, by + 0.05 * u), INK, max(1, u * 0.04) + 2 * ow)
    line(img, (tx, by), (tx - facing * 0.25 * u, by + 0.05 * u), col, max(1, u * 0.04))
    line(img, (tx - facing * 0.25 * u, by + 0.05 * u), (tx - facing * 0.3 * u, by - 0.2 * u), col, max(1, u * 0.04))
    for d in (-1, 1):
        sw = math.sin(phase + d) * 0.06 * u if not sitting else 0
        line(img, (x + d * 0.06 * u, by), (x + d * 0.08 * u + sw, y), INK, max(1, u * 0.05) + 2 * ow)
        line(img, (x + d * 0.06 * u, by), (x + d * 0.08 * u + sw, y), col, max(1, u * 0.05))
    hx, hy = x + facing * 0.08 * u, by - 0.4 * u
    ell(img, (hx, hy), 0.11 * u, 0.1 * u, col, 0, ow)
    ell(img, (hx + facing * 0.04 * u, hy + 0.01 * u), 0.07 * u, 0.065 * u, (0.6, 0.72, 0.85), 0, 0)
    ell(img, (hx + facing * 0.05 * u, hy - 0.01 * u), 0.012 * u, 0.012 * u, INK, 0, 0)


def butterfly(img, x, y, size, t, col):
    f = abs(math.sin(t * 18))
    for d in (-1, 1):
        ell(img, (x + d * size * 0.5 * f, y), size * 0.5 * f + 0.5, size * 0.4, col, d * 20, 0)
    line(img, (x, y - size * 0.3), (x, y + size * 0.3), INK, 1)


def paper_cup(img, x, y, u, ang=0.0, fade=0.0, crush=0.0, lying=False):
    col = tuple(c * (1 - fade) + 0.62 * fade for c in (0.97, 0.97, 0.97))
    band = tuple(c * (1 - fade) + 0.6 * fade for c in (0.25, 0.45, 0.85))
    h, w0, w1 = 0.13 * u, 0.04 * u, 0.06 * u
    if lying:
        c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        pts = [(-h / 2, -w0), (h / 2, -w1 * (1 - 0.4 * crush)), (h / 2, w1), (-h / 2, w0)]
        rot = [(x + px * c - py * s, y - w1 + px * s + py * c) for px, py in pts]
        poly(img, rot, col, 0.7)
        mid = [(x + (-h * 0.1) * c, y - w1 + (-h * 0.1) * s)]
        line(img, (mid[0][0] - s * w1, mid[0][1] + c * w1 * 0.0), (mid[0][0] + s * w1, mid[0][1]), band, max(1, u * 0.02))
    else:
        poly(img, [(x - w0, y), (x + w0, y), (x + w1, y - h), (x - w1, y - h)], col, 0.7)
        line(img, (x - w0 * 1.1, y - h * 0.5), (x + w0 * 1.1, y - h * 0.5), band, max(1, u * 0.02))


def sprout(img, x, y, u, g):
    if g <= 0:
        return
    for i, (dx, a) in enumerate(((-0.02, 110), (0.0, 90), (0.025, 70))):
        L = (0.08 + 0.05 * i % 2) * u * g
        tip = (x + dx * u + math.cos(math.radians(a)) * L, y - math.sin(math.radians(a)) * L)
        line(img, (x + dx * u, y), tip, (0.2, 0.55, 0.25), max(1, u * 0.012))
        ell(img, tip, 0.025 * u * g + 0.5, 0.012 * u * g + 0.5, (0.3, 0.72, 0.35), a - 90, 0)
