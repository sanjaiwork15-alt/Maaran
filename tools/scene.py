"""Paint Thatha's red-soil field ("semman kaadu") at early morning, in code (royalty-free).

Usage:
    python tools/scene.py OUT.png [--seed 7]

Draws a 1620x2880 stage (1.5x the 1080x1920 video, so the camera can move):
morning sky, faint Arunachala hill on the horizon, distant tree line, the
ploughed red-soil field, the neem tree at the left edge and the old well with
its motor shed on the right (see series/01-groundnut/ep01/script.md).
"""
import argparse

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1620, 2880
HORIZON = 1180


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def sky(img):
    top, mid, low = (150, 190, 222), (236, 214, 190), (250, 205, 160)
    px = img.load()
    for y in range(HORIZON + 40):
        t = y / HORIZON
        c = lerp(top, mid, min(t / 0.7, 1)) if t < 0.7 else lerp(mid, low, (t - 0.7) / 0.3)
        for x in range(W):
            px[x, y] = c
    # soft low sun glow on the right
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse((1080, 820, 1500, 1240), fill=255)
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    img.paste(Image.new("RGB", (W, H), (255, 236, 200)), (0, 0), glow.point(lambda v: int(v * 0.7)))


def hills(d, rng):
    # Arunachala: a broad, slightly peaked hill, hazy blue
    pts = [(250, HORIZON + 20)]
    for x in range(250, 1400, 10):
        u = (x - 820) / 560
        y = HORIZON - 230 * max(0.0, 1 - u * u) ** 1.6 - 25 * np.exp(-((x - 860) / 60) ** 2) + rng.normal(0, 1.5)
        pts.append((x, y))
    pts.append((1400, HORIZON + 20))
    d.polygon(pts, fill=(170, 172, 190))
    # nearer, low ridge
    pts = [(0, HORIZON + 20)] + [(x, HORIZON - 40 - 25 * np.sin(x / 210) - 15 * np.sin(x / 77)) for x in range(0, W + 20, 20)] + [(W, HORIZON + 20)]
    d.polygon(pts, fill=(150, 160, 160))


def tree_line(d, rng):
    for x in range(-40, W + 40, 26):
        h = rng.uniform(40, 95)
        r = rng.uniform(22, 40)
        c = lerp((88, 112, 82), (110, 130, 96), rng.uniform())
        d.ellipse((x - r, HORIZON - h, x + r, HORIZON - h + 2 * r), fill=c)
        d.rectangle((x - 3, HORIZON - h + r, x + 3, HORIZON + 8), fill=(90, 85, 70))
    d.rectangle((0, HORIZON - 5, W, HORIZON + 12), fill=(110, 118, 88))


def field(img, rng):
    a = np.array(img).astype(np.float32)
    ys = np.arange(HORIZON + 10, H)
    vx = W * 0.55
    xs = np.arange(W)
    for y in ys:
        depth = (y - HORIZON) / (H - HORIZON)          # 0 far .. 1 near
        base = np.array(lerp((176, 102, 72), (150, 66, 38), depth ** 0.7), np.float32)
        # furrows converge to a vanishing point on the horizon
        u = (xs - vx) / max(depth, 0.02)
        wobble = 9 * np.sin(u / 310.0 + y / 140.0) + 5 * np.sin(u / 97.0)
        stripe = (0.5 + 0.5 * np.sin((u + wobble) / 30.0)) ** 1.6
        shade = 1 - 0.11 * stripe * min(1, depth * 3)
        a[y, :, :] = base * shade[:, None]
    noise = rng.normal(0, 9, (H - HORIZON - 10, W, 1)).astype(np.float32)
    a[HORIZON + 10:] += noise
    # haze near the horizon
    for y in range(HORIZON + 10, HORIZON + 260):
        t = 1 - (y - HORIZON) / 260
        a[y] = a[y] * (1 - 0.45 * t) + np.array([215, 185, 165]) * 0.45 * t
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def well_and_shed(d):
    # motor shed: small whitewashed room with a tiled roof
    d.rectangle((1250, 1150, 1400, 1240), fill=(225, 214, 196))
    d.polygon([(1235, 1155), (1325, 1105), (1415, 1155)], fill=(150, 72, 52))
    d.rectangle((1305, 1185, 1335, 1240), fill=(90, 70, 55))
    # old stone well ring in front of it
    d.ellipse((1080, 1215, 1240, 1255), fill=(150, 140, 125))
    d.rectangle((1080, 1235, 1240, 1275), fill=(160, 150, 132))
    d.ellipse((1080, 1255, 1240, 1295), fill=(140, 130, 115))
    d.ellipse((1095, 1220, 1225, 1248), fill=(60, 55, 50))
    d.line((1100, 1235, 1100, 1180), fill=(95, 75, 55), width=5)
    d.line((1220, 1235, 1220, 1180), fill=(95, 75, 55), width=5)
    d.line((1095, 1180, 1225, 1180), fill=(95, 75, 55), width=6)


def neem(img, rng):
    d = ImageDraw.Draw(img)
    # trunk and main branches
    d.polygon([(70, 2050), (190, 2050), (165, 1500), (140, 1150), (110, 1150), (95, 1500)], fill=(92, 68, 50))
    d.line((140, 1300, 330, 1020), fill=(92, 68, 50), width=34)
    d.line((120, 1250, -20, 1000), fill=(92, 68, 50), width=30)
    d.line((150, 1180, 230, 820), fill=(92, 68, 50), width=26)
    # canopy: many small leaf clusters, darker inside, lighter on top
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    clusters = [(150, 760, 230, 170), (330, 900, 170, 140), (-20, 900, 190, 150), (180, 1040, 230, 120), (60, 640, 150, 110)]
    for cx0, cy0, rx, ry in clusters:
        ld.ellipse((cx0 - rx * 0.8, cy0 - ry * 0.8, cx0 + rx * 0.8, cy0 + ry * 0.8), fill=(40, 70, 36, 255))
    for _ in range(2600):
        cx0, cy0, rx, ry = clusters[rng.integers(len(clusters))]
        ang, rad = rng.uniform(0, 2 * np.pi), np.sqrt(rng.uniform()) * 0.95
        cx, cy = cx0 + rx * rad * np.cos(ang), cy0 + ry * rad * np.sin(ang)
        r = rng.uniform(9, 20)
        light = np.clip((1100 - cy) / 500 + rng.normal(0, 0.15), 0, 1)
        c = lerp((46, 82, 40), (120, 156, 70), light)
        ld.ellipse((cx - r, cy - r * 0.7, cx + r, cy + r * 0.7), fill=c + (255,))
    img.paste(layer, (0, 0), layer)
    # soft shadow of the tree on the soil
    sh = Image.new("L", img.size, 0)
    ImageDraw.Draw(sh).ellipse((-200, 1990, 520, 2130), fill=110)
    img.paste((70, 30, 18), (0, 0), sh.filter(ImageFilter.GaussianBlur(30)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)

    img = Image.new("RGB", (W, H))
    sky(img)
    d = ImageDraw.Draw(img)
    hills(d, rng)
    tree_line(d, rng)
    img = field(img, rng)
    d = ImageDraw.Draw(img)
    well_and_shed(d)
    neem(img, rng)
    # gentle painterly softening, like an out-of-focus background
    img = img.filter(ImageFilter.GaussianBlur(1.6))
    img.save(a.out)
    print("saved", a.out, img.size)


if __name__ == "__main__":
    main()
