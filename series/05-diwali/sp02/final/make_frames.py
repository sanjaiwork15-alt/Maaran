"""Diwali special 2 – start frames, no GPU: approved frames used whole + props drawn in code (tools/toon/diwali.py).

Run with the f5 env:  python -I make_frames.py [names...]
f_kbag:   the Doubt kitchen (Thatha removed) – Thatha (01_front) back from the market, his cloth bag bulging with
          greens and a sweet box, the table beside him piled with the shopping (rice sack, vegetables, sweets, snacks, oil).
f_kcook:  Groundnut Ep 10 f_kitchen_s3 (stirring the pot on the wood stove) – the pot now holds sambar.
f_kpack:  the kitchen – Thatha (01_front) behind the table, food parcels (steel tiffins, leaf parcels tied with string)
          in front of him (the table edge hides him from the hips down).
f_khome:  the children's home at golden hour (07_home re-tinted, bunting, a signboard with a house-and-children
          picture and CHILDREN'S HOME, parcels on the steps) – Thatha (01_front) beside the gate.
f_sweet:  Groundnut Ep 10 f_sit_s3 (sitting on his step, eating) at dusk, diyas on the step – the bowl now holds
          laddus and he is biting a laddu.
f_diya:   Groundnut Ep 10 f_roast_s3 (smiling, a bowl raised on his palm) cut out and placed in front of the decorated
          farmhouse at night (Ep 1 dusk plate) – the bowl is now a lit clay diya.
*_mask.png: Thatha's silhouette (animated lights are not drawn over him).
"""
import io
import math
import sys
from pathlib import Path

import cairosvg
import cv2
import numpy as np
from PIL import Image
from rembg import new_session, remove

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FR = HERE / "frames"
SRC = ROOT / "assets/2d/source"
GN10 = ROOT / "series/01-groundnut/ep10/final/frames"
KITCHEN = ROOT / "series/02-thatha-oru-doubt/ep02/final/frames/kitchen_plate.png"
SP1 = ROOT / "series/05-diwali/sp01/final/frames"
sys.path.insert(0, str(ROOT / "tools/toon"))
import diwali as D  # noqa: E402

W, H = 720, 1280
WOOD, WOOD_D, WOOD_L, OUTL = "#8a5a2b", "#6b4220", "#b07a44", "#3e2410"


def svg(body, w=W, h=H):
    return np.array(Image.open(io.BytesIO(cairosvg.svg2png(
        bytestring=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">{body}</svg>'.encode()))).convert("RGBA")).astype(np.float32)


def over(rgb, rgba):
    a = rgba[..., 3:4] / 255
    return rgb * (1 - a) + rgba[..., :3] * a


def load(p):
    return np.array(Image.open(p).convert("RGB").resize((W, H), Image.LANCZOS)).astype(np.float32)


def cutout(seg, rgb):
    a = np.array(remove(Image.fromarray(rgb.astype(np.uint8)), session=seg, only_mask=True)).astype(np.float32)
    return np.clip((a - 90) * 2.6, 0, 255)


# ---------------------------------------------------------------- props (720 coords)

def table(x0, x1, top, legs_to=1280, depth=46):
    return (f'<rect x="{x0 + 18}" y="{top + depth}" width="30" height="{legs_to - top - depth}" fill="{WOOD_D}" stroke="{OUTL}" stroke-width="5"/>'
            f'<rect x="{x1 - 48}" y="{top + depth}" width="30" height="{legs_to - top - depth}" fill="{WOOD_D}" stroke="{OUTL}" stroke-width="5"/>'
            f'<path d="M {x0 + 20},{top} L {x1 - 20},{top} L {x1},{top + 24} L {x0},{top + 24} Z" fill="{WOOD_L}" stroke="{OUTL}" stroke-width="5"/>'
            f'<rect x="{x0}" y="{top + 24}" width="{x1 - x0}" height="{depth - 10}" rx="4" fill="{WOOD}" stroke="{OUTL}" stroke-width="5"/>'
            f'<line x1="{x0 + 10}" y1="{top + 34}" x2="{x1 - 10}" y2="{top + 34}" stroke="{WOOD_L}" stroke-width="3" opacity="0.6"/>')


def rice_sack(x, y, s=1.0):
    return (f'<g transform="translate({x} {y}) scale({s})"><path d="M -60,0 Q -72,-80 -48,-130 L 48,-130 Q 72,-80 60,0 Z" fill="#e8dcb5" stroke="#6b5a2a" stroke-width="5"/>'
            '<path d="M -48,-130 Q 0,-150 48,-130 Q 0,-118 -48,-130" fill="#fbf7ec" stroke="#6b5a2a" stroke-width="4"/>'
            + "".join(f'<ellipse cx="{-30 + k * 12}" cy="{-134 + (k % 2) * 4}" rx="4" ry="2.5" fill="#fff"/>' for k in range(6)) +
            '<path d="M -40,-60 L 40,-60 M -42,-40 L 42,-40" stroke="#c9a85a" stroke-width="5"/>'
            '<circle cx="0" cy="-88" r="15" fill="#3e8e41"/><path d="M -8,-88 q 8,-14 16,0 q -8,10 -16,0" fill="#e8dcb5"/></g>')


def veg_basket(x, y, s=1.0):
    return (f'<g transform="translate({x} {y}) scale({s})">'
            '<ellipse cx="-30" cy="-62" rx="26" ry="20" fill="#e53935" stroke="#7a0a0a" stroke-width="4"/>'
            '<path d="M -40,-80 l 10,8 l 10,-8" stroke="#2e7d32" stroke-width="4" fill="none"/>'
            '<path d="M 0,-60 Q 20,-110 55,-100 Q 40,-62 0,-60 Z" fill="#6a1b9a" stroke="#2a0a3a" stroke-width="4"/>'
            '<path d="M 52,-100 l 10,-12" stroke="#2e7d32" stroke-width="6"/>'
            '<path d="M -10,-70 L 20,-140 L 30,-136 L 6,-66 Z" fill="#fb8c00" stroke="#8a3a00" stroke-width="3"/>'
            '<path d="M 22,-140 l -8,-16 M 24,-140 l 4,-18 M 26,-139 l 12,-12" stroke="#2e7d32" stroke-width="4"/>'
            '<ellipse cx="30" cy="-58" rx="22" ry="16" fill="#8bc34a" stroke="#33691e" stroke-width="4"/>'
            '<path d="M -70,-50 L 70,-50 L 56,0 L -56,0 Z" fill="#c8a05a" stroke="#5a3a10" stroke-width="5"/>'
            + "".join(f'<line x1="{-60 + k * 20}" y1="-48" x2="{-50 + k * 17}" y2="-2" stroke="#8a6a30" stroke-width="3"/>' for k in range(7)) +
            '<path d="M -64,-30 L 64,-30" stroke="#8a6a30" stroke-width="3"/></g>')


def sweet_box(x, y, s=1.0, open_=True):
    lad = "".join(f'<circle cx="{-36 + k * 24}" cy="-40" r="12" fill="#f6a623" stroke="#b86e00" stroke-width="3"/>' for k in range(4)) if open_ else ""
    return (f'<g transform="translate({x} {y}) scale({s})">{lad}'
            '<rect x="-56" y="-36" width="112" height="36" rx="4" fill="#e53935" stroke="#7a0a0a" stroke-width="4"/>'
            '<rect x="-56" y="-24" width="112" height="10" fill="#ffd54f"/></g>')


def snack_pack(x, y, s=1.0, col="#1e88e5"):
    return (f'<g transform="translate({x} {y}) scale({s})"><path d="M -30,0 L -34,-90 L -24,-98 L 24,-98 L 34,-90 L 30,0 Z" fill="{col}" stroke="#0d2c53" stroke-width="4"/>'
            '<path d="M -34,-90 L 34,-90" stroke="#ffffff" stroke-width="3" stroke-dasharray="4 4"/>'
            '<circle cx="0" cy="-48" r="16" fill="#ffd54f" stroke="#a67c00" stroke-width="3"/>'
            '<circle cx="0" cy="-48" r="7" fill="none" stroke="#a67c00" stroke-width="3"/></g>')


def oil_can(x, y, s=1.0):
    return (f'<g transform="translate({x} {y}) scale({s})"><rect x="-32" y="-96" width="64" height="96" rx="6" fill="#ffca28" stroke="#6d5200" stroke-width="4"/>'
            '<rect x="-12" y="-114" width="24" height="20" fill="#e53935" stroke="#6d5200" stroke-width="3"/>'
            '<path d="M -18,-46 q 18,-28 36,0 q -18,26 -36,0" fill="#ff8f00"/></g>')


def tiffin(x, y, s=1.0):
    """A three-tier steel tiffin carrier."""
    g = f'<g transform="translate({x} {y}) scale({s})">'
    for k in range(3):
        yy = -k * 34
        g += (f'<rect x="-34" y="{yy - 34}" width="68" height="34" rx="6" fill="#c9cdd2" stroke="#5a6068" stroke-width="4"/>'
              f'<line x1="-32" y1="{yy - 6}" x2="32" y2="{yy - 6}" stroke="#8a9096" stroke-width="3"/>')
    g += ('<path d="M -40,-100 L -40,-20 M 40,-100 L 40,-20" stroke="#7d848c" stroke-width="6"/>'
          '<path d="M -40,-100 Q 0,-150 40,-100" stroke="#7d848c" stroke-width="7" fill="none"/>'
          '<rect x="-36" y="-110" width="72" height="10" rx="4" fill="#aeb4ba" stroke="#5a6068" stroke-width="3"/></g>')
    return g


def leaf_parcel(x, y, s=1.0):
    """A banana-leaf food parcel tied with string, a small sweet box on top."""
    return (f'<g transform="translate({x} {y}) scale({s})"><path d="M -54,0 Q -60,-40 -50,-62 L 50,-62 Q 60,-40 54,0 Z" fill="#43a047" stroke="#1b5e20" stroke-width="4"/>'
            '<path d="M -50,-62 Q 0,-78 50,-62 Q 0,-50 -50,-62" fill="#66bb6a" stroke="#1b5e20" stroke-width="3"/>'
            '<path d="M -20,-62 L -22,0 M 20,-62 L 22,0 M -54,-30 L 54,-30" stroke="#d7c08a" stroke-width="4"/>'
            '<path d="M -6,-72 q 6,-14 12,0" stroke="#d7c08a" stroke-width="4" fill="none"/>'
            '<rect x="-26" y="-100" width="52" height="26" rx="3" fill="#e53935" stroke="#7a0a0a" stroke-width="3"/>'
            '<rect x="-26" y="-92" width="52" height="7" fill="#ffd54f"/></g>')


def grocery_table():
    g = table(430, 715, 905)
    g += rice_sack(500, 925, 0.95) + veg_basket(625, 925, 0.85) + sweet_box(540, 905 + 22, 0.75) + snack_pack(675, 925, 0.75, "#1e88e5")
    g += snack_pack(455, 925, 0.6, "#e53935") + oil_can(700, 920, 0.55)
    return g


def full_bag(seg_bag=True):
    """The yellow cloth bag (in 01_front x2 coords, hanging from his free fist), bulging with shopping."""
    return ('<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#e0aa10"/>'
            '<stop offset="0.45" stop-color="#ffd23a"/><stop offset="1" stop-color="#c99300"/></linearGradient></defs>'
            '<path d="M 1440,2060 Q 1400,1900 1360,1880 M 1450,2060 Q 1450,1890 1430,1850 M 1460,2060 Q 1500,1900 1520,1870" stroke="#2e7d32" stroke-width="22" fill="none" stroke-linecap="round"/>'
            '<ellipse cx="1360" cy="1880" rx="34" ry="20" fill="#43a047"/><ellipse cx="1430" cy="1850" rx="34" ry="20" fill="#43a047"/><ellipse cx="1520" cy="1870" rx="34" ry="20" fill="#66bb6a"/>'
            '<rect x="1600" y="1960" width="150" height="90" rx="8" fill="#e53935" stroke="#7a0a0a" stroke-width="8" transform="rotate(-10 1675 2005)"/>'
            '<rect x="1600" y="1990" width="150" height="22" fill="#ffd54f" transform="rotate(-10 1675 2005)"/>'
            '<path d="M 1468,2050 Q 1560,1830 1652,2050" stroke="#c99300" stroke-width="24" fill="none"/>'
            '<path d="M 1370,2040 Q 1560,2010 1750,2040 Q 1820,2300 1775,2570 Q 1560,2630 1345,2570 Q 1300,2300 1370,2040 Z" '
            'fill="url(#bg)" stroke="#8a6a00" stroke-width="10"/>'
            '<path d="M 1470,2060 Q 1440,2300 1475,2550 M 1650,2060 Q 1690,2300 1655,2550" stroke="#b88a00" stroke-width="8" fill="none" opacity="0.7"/>'
            '<path d="M 1390,2120 Q 1560,2100 1730,2120" stroke="#b88a00" stroke-width="8" fill="none"/>')


def front_figure(seg, bag_svg=None, tint=(1, 1, 1), add=(0, 0, 0)):
    """The owner's standing drawing (01_front, 2048x3072) as RGBA; optional bag hung from his free fist (fist on top)."""
    fr = Image.open(ROOT / "assets/2d/up/01_front.png").convert("RGB")
    fa = np.clip((np.array(remove(fr, session=seg, only_mask=True)).astype(np.float32) - 90) * 2.6, 0, 255)
    rgb = np.array(fr).astype(np.float32) * np.array(tint) + np.array(add)
    lay = np.dstack([np.clip(rgb, 0, 255), fa])
    if bag_svg:
        bag = svg(bag_svg, 2048, 3072)
        hsv = cv2.cvtColor(np.array(fr), cv2.COLOR_RGB2HSV).astype(int)
        YY, XX = np.mgrid[0:3072, 0:2048]
        fist = (XX > 1430) & (XX < 1700) & (YY > 1880) & (YY < 2110) & (hsv[..., 0] <= 22) & (hsv[..., 1] > 100) & (fa > 200)
        al = bag[..., 3:4] / 255
        top = lay.copy()
        lay[..., :3] = lay[..., :3] * (1 - al) + bag[..., :3] * np.array(tint) * al
        lay[..., 3:4] = np.maximum(lay[..., 3:4], bag[..., 3:4])
        lay[fist] = top[fist]
    ys, xs = np.nonzero(lay[..., 3] > 30)
    return lay[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def place(plate, lay, height, cx, bottom, under=None, over_=None):
    """Scale the figure layer to `height` px, feet at (cx, bottom); `under`/`over_` = RGBA layers behind / in front."""
    sc = height / lay.shape[0]
    lay = cv2.resize(lay, (round(lay.shape[1] * sc), round(height)), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((H, W, 4), np.float32)
    x0, y0 = round(cx - lay.shape[1] / 2), round(bottom - height)
    xs, ys = max(0, x0), max(0, y0)
    xe, ye = min(W, x0 + lay.shape[1]), min(H, y0 + lay.shape[0])
    canvas[ys:ye, xs:xe] = lay[ys - y0:ye - y0, xs - x0:xe - x0]
    out = plate.copy()
    if under is not None:
        out = over(out, under)
    out = over(out, canvas)
    mask = canvas[..., 3].copy()
    if over_ is not None:
        out = over(out, over_)
        mask *= 1 - over_[..., 3] / 255
    return np.clip(out, 0, 255).astype(np.uint8), mask.astype(np.uint8)


def save(name, img, mask=None):
    Image.fromarray(img).save(FR / f"{name}.png")
    if mask is not None:
        Image.fromarray(mask).save(FR / f"{name}_mask.png")
    print("saved", name)


# ---------------------------------------------------------------- frames

def sambar(rgb, box=(860, 985, 20, 360), ladle=None, seed=4, ell=None):
    """Repaint the groundnuts heaped in the kitchen pot as sambar (dal, drumstick, tomato, curry leaves)."""
    y0, y1, x0, x1 = box
    hsv = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(int)
    yy, xx = np.mgrid[0:H, 0:W]
    nuts = (yy > y0) & (yy < y1) & (xx > x0) & (xx < x1) & (hsv[..., 0] >= 8) & (hsv[..., 0] <= 30) & (hsv[..., 1] > 60) & (hsv[..., 2] > 150)
    region = cv2.morphologyEx(nuts.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    region = cv2.dilate(region, np.ones((5, 5), np.uint8))
    if ell is not None:                                                    # only inside the pot's mouth
        em = np.zeros((H, W), np.uint8)
        cv2.ellipse(em, (ell[0], ell[1]), (ell[2], ell[3]), 0, 0, 360, 1, -1)
        region &= em
    if ladle is not None:
        lm = np.zeros((H, W), np.uint8)
        cv2.fillPoly(lm, [np.array(ladle, np.int32)], 1)
        region &= 1 - lm
    ys, xs = np.nonzero(region)
    if len(ys) == 0:
        return rgb
    bx0, bx1, by0, by1 = xs.min(), xs.max(), ys.min(), ys.max()
    rng = np.random.default_rng(seed)
    g = ['<rect width="720" height="1280" fill="#b4561c"/>']
    for _ in range(140):
        x, y = rng.uniform(bx0, bx1), rng.uniform(by0, by1)
        g.append(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{rng.uniform(4, 10):.0f}" ry="{rng.uniform(2, 4):.0f}" fill="{rng.choice(["#c96a2a", "#9c4412", "#d9822f"])}"/>')
    for _ in range(9):
        x, y = rng.uniform(bx0 + 15, bx1 - 15), rng.uniform(by0 + 8, by1 - 8)
        g.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="24" height="7" rx="3.5" fill="#6b8e23" stroke="#33461a" stroke-width="2" transform="rotate({rng.uniform(-30, 30):.0f} {x:.0f} {y:.0f})"/>')
    for _ in range(8):
        x, y = rng.uniform(bx0 + 15, bx1 - 15), rng.uniform(by0 + 8, by1 - 8)
        g.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="5" fill="#e53935" stroke="#7a0a0a" stroke-width="2"/>')
    for _ in range(10):
        x, y = rng.uniform(bx0 + 10, bx1 - 10), rng.uniform(by0 + 6, by1 - 6)
        g.append(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="7" ry="3" fill="#2e5e1e" transform="rotate({rng.uniform(0, 180):.0f} {x:.0f} {y:.0f})"/>')
    tex = svg("".join(g))[..., :3]
    m = cv2.GaussianBlur(region.astype(np.float32), (0, 0), 1.2)[..., None]
    return rgb * (1 - m) + tex * m


def kitchen():
    return sambar(load(KITCHEN), (895, 965, 60, 310), ell=(188, 933, 110, 26))


def f_kcook(seg):
    rgb = load(GN10 / "f_kitchen_s3.png")
    out = sambar(rgb, (895, 965, 50, 340), [(158, 948), (163, 880), (188, 800), (218, 800), (233, 880), (231, 948)])
    a = cutout(seg, rgb)
    save("f_kcook", np.clip(out, 0, 255).astype(np.uint8), a.astype(np.uint8))


def f_kbag(seg):
    plate = kitchen()
    lay = front_figure(seg, full_bag())
    sh = svg('<ellipse cx="500" cy="1240" rx="150" ry="22" fill="#000" fill-opacity="0.3"/>')
    out, mask = place(over(plate, sh), lay, 980, 500, 1245)
    save("f_kbag", out, mask)


def f_kpack(seg):
    plate = kitchen()
    lay = front_figure(seg)
    g = table(140, 715, 800, 1280, 60)
    for k, x in enumerate((210, 320, 430, 540, 650)):
        g += tiffin(x, 816, 0.9) if k % 2 == 0 else leaf_parcel(x, 816, 0.95)
    tb = svg(g)
    out, mask = place(plate, lay, 1080, 450, 1250, over_=tb)
    save("f_kpack", out, mask)


def home_plate(golden=True):
    home = load(SRC / "07_home.png")
    hsv = cv2.cvtColor(home.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
    wall = (hsv[..., 1] < 50) & (hsv[..., 2] > 170)                        # whitewashed walls -> pale sky blue
    m = cv2.GaussianBlur(wall.astype(np.float32), (0, 0), 1.0)[..., None]
    home = home * (1 - m) + (home * np.array([0.78, 0.9, 1.05]) + np.array([0, 10, 25])) * m
    if golden:
        home = home * np.array([1.08, 0.95, 0.78]) + np.array([14, 6, 0])
    return np.clip(home, 0, 255)


def signboard(x, y):
    """A board on two posts: a house with two children and a heart, and the words CHILDREN'S HOME."""
    return (f'<g transform="translate({x} {y}) scale(0.88)"><rect x="-90" y="0" width="12" height="230" fill="#5a3a1a"/><rect x="78" y="0" width="12" height="230" fill="#5a3a1a"/>'
            '<rect x="-110" y="-120" width="220" height="130" rx="10" fill="#fff8e1" stroke="#1565c0" stroke-width="7"/>'
            '<path d="M -88,-62 L -60,-92 L -32,-62 Z" fill="#e53935"/><rect x="-82" y="-62" width="44" height="34" fill="#ffd54f" stroke="#a67c00" stroke-width="3"/>'
            '<circle cx="-14" cy="-80" r="8" fill="#8d5524"/><path d="M -22,-70 L -6,-70 L -4,-44 L -24,-44 Z" fill="#43a047"/>'
            '<circle cx="12" cy="-76" r="7" fill="#8d5524"/><path d="M 5,-67 L 19,-67 L 22,-44 L 2,-44 Z" fill="#e91e63"/>'
            '<path d="M 60,-58 q -14,-16 -24,-4 q -8,12 24,32 q 32,-20 24,-32 q -10,-12 -24,4 z" fill="#e53935"/>'
            '<text x="0" y="-12" font-family="DejaVu Sans, Arial, sans-serif" font-weight="bold" font-size="17" text-anchor="middle" fill="#1565c0">'
            "CHILDREN&#8217;S HOME</text></g>")


def bunting(y=548):
    cols = ["#e53935", "#ffd54f", "#43a047", "#1e88e5", "#fb8c00", "#8e24aa"]
    g = ""
    for k in range(22):
        x = 40 + k * 30
        yy = y + 14 * math.sin(math.pi * ((x - 40) % 330) / 330)
        g += f'<path d="M {x},{yy:.0f} L {x + 26},{yy:.0f} L {x + 13},{yy + 26:.0f} Z" fill="{cols[k % 6]}" stroke="#333" stroke-width="1.5"/>'
    return g


def f_khome(seg):
    plate = home_plate()
    g = bunting()
    for k, x in enumerate((300, 362, 424)):                                 # the parcels he left on the step
        g += tiffin(x, 905, 0.6) if k == 1 else leaf_parcel(x, 905, 0.6)
    g += signboard(598, 900)
    plate = over(plate, svg(g))
    lay = front_figure(seg, tint=(1.06, 0.97, 0.85), add=(10, 4, 0))
    sh = svg('<ellipse cx="190" cy="1238" rx="150" ry="20" fill="#000" fill-opacity="0.3"/>')
    out, mask = place(over(plate, sh), lay, 1040, 190, 1245)
    save("f_khome", out, mask)
    Image.fromarray(np.clip(plate, 0, 255).astype(np.uint8)).save(FR / "khome_plate.png")


def laddu(x, y, r):
    rng = np.random.default_rng(int(x * 7 + y))
    dots = "".join(f'<circle cx="{x + rng.uniform(-r * .6, r * .6):.1f}" cy="{y + rng.uniform(-r * .6, r * .6):.1f}" r="{r * 0.09:.1f}" fill="#d9851a"/>' for _ in range(7))
    return (f'<circle cx="{x}" cy="{y}" r="{r}" fill="#f7a92c" stroke="#a8620a" stroke-width="{max(1.5, r * 0.1):.1f}"/>{dots}'
            f'<circle cx="{x - r * 0.35:.1f}" cy="{y - r * 0.35:.1f}" r="{r * 0.22:.1f}" fill="#ffd27a" opacity="0.8"/>')


def f_sweet(seg):
    rgb = load(GN10 / "f_sit_s3.png")
    a = cutout(seg, rgb)
    hsv = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(int)
    yy, xx = np.mgrid[0:H, 0:W]
    # the nuts heaped in the bowl -> laddus; the nut at his lips -> a bitten laddu piece
    bowl = (yy > 718) & (yy < 778) & (xx > 345) & (xx < 495) & (hsv[..., 0] >= 10) & (hsv[..., 0] <= 32) & (hsv[..., 1] > 60) & (hsv[..., 2] > 140)
    reg = cv2.morphologyEx(bowl.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8))
    lips = (yy > 460) & (yy < 505) & (xx > 280) & (xx < 315) & (hsv[..., 0] >= 12) & (hsv[..., 0] <= 32) & (hsv[..., 2] > 120)
    from simple_lama_inpainting import SimpleLama  # noqa: E402
    import torch  # noqa: E402
    _load = torch.jit.load
    torch.jit.load = lambda f, map_location=None, **k: _load(f, map_location="cpu", **k)
    lama = SimpleLama()
    hole = cv2.dilate((reg | lips.astype(np.uint8)), np.ones((7, 7), np.uint8))
    clean = np.array(lama(Image.fromarray(rgb.astype(np.uint8)), Image.fromarray(hole * 255)).convert("RGB").resize((W, H))).astype(np.float32)
    rgb = rgb * (1 - hole[..., None]) + clean * hole[..., None]
    g = "".join(laddu(x, y, 17) for x, y in ((385, 745), (418, 740), (452, 744), (402, 728), (436, 726), (470, 748)))
    g += ('<path d="M 280,482 a 15,15 0 1 1 26,6 q -6,-6 -10,-2 q -4,-8 -16,-4 z" fill="#f7a92c" stroke="#a8620a" stroke-width="2"/>'
          '<circle cx="290" cy="476" r="2" fill="#d9851a"/><circle cx="298" cy="484" r="2" fill="#d9851a"/>')
    props = svg(g)
    out = over(rgb, props)
    # his fingers back on top of the laddu at his lips
    fing = (yy > 470) & (yy < 520) & (xx > 255) & (xx < 300) & (hsv[..., 0] <= 18) & (hsv[..., 1] > 90) & (hsv[..., 2] > 110) & (a > 200)
    out[fing] = rgb[fing]
    out = D.dusk(np.clip(out, 0, 255).astype(np.uint8), 300).astype(np.float32)
    g = "".join(D.diya(x, 1135, 1.3) for x in (70, 150, 590, 660))
    out = over(out, svg(g))
    save("f_sweet", np.clip(out, 0, 255).astype(np.uint8), a.astype(np.uint8))
    return [(x, 1135) for x in (70, 150, 590, 660)]


def f_diya(seg):
    """The bowl on his palm becomes a big clay lamp: the heaped nuts go, an oil surface fills the rim, a spout and a
    flame on the right rim (all drawn in the source frame's coords, so his fingers stay in front of the bowl)."""
    rgb = load(GN10 / "f_roast_s3.png")
    a = cutout(seg, rgb)
    yy, xx = np.mgrid[0:H, 0:W]
    heap = (yy < 476) & (yy > 400) & (xx > 522) & (xx < 714)
    a[heap] = 0
    lamp = svg('<ellipse cx="619" cy="481" rx="86" ry="15" fill="#5a2a10"/>'
               '<ellipse cx="619" cy="483" rx="78" ry="11" fill="#e0a030"/><ellipse cx="600" cy="481" rx="30" ry="4" fill="#ffe08a" opacity="0.8"/>'
               '<path d="M 533,481 Q 619,505 705,481" stroke="#3a1a08" stroke-width="5" fill="none"/>'
               '<path d="M 548,476 Q 520,466 508,452 Q 516,478 536,490 Z" fill="#a8562c" stroke="#3a1a08" stroke-width="4"/>'
               '<path d="M 512,452 Q 498,416 514,388 Q 532,416 518,452 Z" fill="#ffb300"/>'
               '<path d="M 513,450 Q 506,426 514,410 Q 523,428 517,450 Z" fill="#fff3b0"/>')
    rgb = over(rgb, lamp)
    a = np.maximum(a, lamp[..., 3])
    fig = np.dstack([rgb * np.array([0.8, 0.76, 0.86]) + np.array([10, 4, 12]), a])
    fl = (yy < 455) & (xx > 495) & (xx < 535) & (yy > 380)               # the flame keeps its own colour
    fig[fl, :3] = rgb[fl]
    plate = np.array(Image.open(SP1 / "dusk_plate_b.png").convert("RGB")).astype(np.float32)
    ys, xs = np.nonzero(a > 30)
    lay = fig[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    sc = 1060 / lay.shape[0]
    lay = cv2.resize(lay, (round(lay.shape[1] * sc), 1060), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((H, W, 4), np.float32)
    x0, y0 = 330 - lay.shape[1] // 2, 1245 - 1060
    xe = min(W, x0 + lay.shape[1])
    canvas[y0:y0 + 1060, max(0, x0):xe] = lay[:, max(0, -x0):xe - x0]
    px, py = (515 - xs.min()) * sc + x0, (430 - ys.min()) * sc + y0     # the flame
    sh = svg('<ellipse cx="320" cy="1238" rx="170" ry="22" fill="#000" fill-opacity="0.35"/>')
    out = over(over(plate, sh), canvas)
    YY, XX = np.mgrid[0:H, 0:W]
    glow = np.exp(-(((XX - px) / 280) ** 2 + ((YY - py) / 320) ** 2))[..., None]
    m = canvas[..., 3:4] / 255
    out = out * (1 + glow * m * np.array([0.35, 0.18, -0.05])) + glow * np.array([40, 22, 0]) * 0.5
    save("f_diya", np.clip(out, 0, 255).astype(np.uint8), canvas[..., 3].astype(np.uint8))
    print("diya flame at", round(px), round(py))


def main():
    only = sys.argv[1:]
    seg = new_session("isnet-anime")
    for name, fn in (("f_kcook", f_kcook), ("f_kbag", f_kbag), ("f_kpack", f_kpack), ("f_khome", f_khome), ("f_sweet", f_sweet), ("f_diya", f_diya)):
        if not only or name in only:
            fn(seg)


if __name__ == "__main__":
    main()
