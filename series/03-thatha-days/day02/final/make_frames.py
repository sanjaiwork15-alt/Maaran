"""Day 2 start frames without a GPU: Thatha's home garden (the owner's 07_home art – courtyard with plants and the
tulsi maadam), Thatha only.

Run with the f5 env:  python -I make_frames.py
Approved poses cut out with rembg and set on the courtyard ground (with a ground shadow); props drawn in code:
f_gwater:  Groundnut Ep 4 f_water_s8 – kneeling, pouring from his watering can into a clay pot with a small plant;
           finger up ("innum konjam"); a little water on the ground.
f_gflood:  the same, water running out of the pot's drainage hole and a big puddle around it.
f_gproud:  arms crossed, proud (owner's pose sheet), the pot in its puddle beside him, the can on the ground.
f_gsoil:   Groundnut Ep 2 f_soil_s3 – crouching, wet soil in his hands (darkened), the pot in its puddle.
f_gpoint:  Groundnut Ep 5 f_point_s3 – kneeling, pointing at the pot now on a wooden stool in the sun, no puddle.
f_gstand:  standing with his stick (owner's front art), the nearly empty can at his feet, the pot on its stool.
"""
import io
from pathlib import Path

import cairosvg
import numpy as np
from PIL import Image
from rembg import new_session, remove

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FR = HERE / "frames"
GN = ROOT / "series/01-groundnut"
W, H = 720, 1280
CLAY, CLAY_D, CLAY_L, LINE = "#c8643a", "#9c4524", "#e08a5c", "#5a2410"


def svg_layer(body):
    return Image.open(io.BytesIO(cairosvg.svg2png(
        bytestring=f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">{body}</svg>'.encode()))).convert("RGBA")


def cut(seg, path, box=None):
    im = Image.open(path).convert("RGB")
    if box:
        im = im.crop(box)
    a = np.array(remove(im, session=seg, only_mask=True)).astype(np.float32)
    a = np.clip((a - 90) * 2.6, 0, 255).astype(np.uint8)
    out = Image.fromarray(np.dstack([np.array(im), a]))
    return out.crop(out.getbbox()) if box else out


def place(canvas, fig, s, dx, dy, shadow=None):
    f = fig.resize((round(fig.width * s), round(fig.height * s)), Image.LANCZOS)
    if shadow:
        cx, cy, rx = shadow
        canvas.alpha_composite(svg_layer(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{rx * 0.13:.0f}" fill="#3a1606" fill-opacity="0.38"/>'))
    canvas.alpha_composite(f, (round(dx), round(dy)))


def puddle(x, y, r, a=0.75):
    if r <= 0:
        return ""
    return (f'<ellipse cx="{x}" cy="{y}" rx="{r * 1.12:.0f}" ry="{r * 0.32:.0f}" fill="#5e2a12" fill-opacity="0.6"/>'
            f'<ellipse cx="{x}" cy="{y}" rx="{r * 0.92:.0f}" ry="{r * 0.24:.0f}" fill="#6fa6c4" fill-opacity="{a:.2f}" stroke="#4d7f99" stroke-width="2"/>'
            f'<ellipse cx="{x - r * 0.3:.0f}" cy="{y - r * 0.05:.0f}" rx="{r * 0.25:.0f}" ry="{r * 0.05:.0f}" fill="#ffffff" fill-opacity="0.55"/>')


def plant(x, y, s=1.0):
    leaves = ""
    for ang, ln in ((-62, 46), (-30, 52), (-95, 58), (-125, 50), (-150, 44)):
        a = np.radians(ang)
        ex, ey = x + np.cos(a) * ln * s, y + np.sin(a) * ln * s
        cx, cy = x + np.cos(a - 0.35) * ln * 0.6 * s, y + np.sin(a - 0.35) * ln * 0.6 * s
        leaves += (f'<path d="M {x},{y} Q {cx:.0f},{cy:.0f} {ex:.0f},{ey:.0f} Q {x + np.cos(a + 0.35) * ln * 0.6 * s:.0f},'
                   f'{y + np.sin(a + 0.35) * ln * 0.6 * s:.0f} {x},{y} Z" fill="#4caf3c" stroke="#24651c" stroke-width="2.5"/>')
    return leaves + f'<path d="M {x},{y} L {x},{y - 22 * s}" stroke="#2f7d24" stroke-width="4"/>'


def pot(x, base, w=120, wet=0.0, drip=0.0, pool=0.0):
    """Clay pot standing on y = base, centre x; soil darkens with wet; drip = water out of the drainage hole."""
    h = w * 0.82
    top, bot = w / 2, w * 0.36
    soil = "#5a3218" if wet > 0.5 else "#7a4a2a"
    s = puddle(x, base + 4, pool * w * 1.15)
    s += (f'<path d="M {x - top:.0f},{base - h:.0f} L {x + top:.0f},{base - h:.0f} L {x + bot:.0f},{base} L {x - bot:.0f},{base} Z" '
          f'fill="{CLAY}" stroke="{LINE}" stroke-width="3.5"/>'
          f'<path d="M {x - top * 0.62:.0f},{base - h * 0.86:.0f} L {x - bot * 0.55:.0f},{base - 6}" stroke="{CLAY_L}" stroke-width="7" stroke-linecap="round"/>'
          f'<rect x="{x - top - 6:.0f}" y="{base - h - 16:.0f}" width="{w + 12}" height="20" rx="5" fill="{CLAY_D}" stroke="{LINE}" stroke-width="3.5"/>'
          f'<ellipse cx="{x}" cy="{base - h - 14:.0f}" rx="{top - 2:.0f}" ry="7" fill="{soil}"/>')
    if wet > 0.8:
        s += f'<ellipse cx="{x + 10}" cy="{base - h - 15:.0f}" rx="{top * 0.45:.0f}" ry="3.5" fill="#bfe0f0" fill-opacity="0.7"/>'
    if drip > 0:
        s += (f'<path d="M {x - 4},{base - 2} q -3,{6 + 10 * drip:.0f} -9,{14 + 16 * drip:.0f}" stroke="#a9d4ea" stroke-width="{3 + 3 * drip:.0f}" '
              f'fill="none" stroke-linecap="round" stroke-opacity="0.9"/>')
    return s + plant(x, base - h - 16, w / 110)


def stream(x0, y0, x1, y1):
    return "".join(f'<path d="M {x0 + k * 4},{y0} Q {x0 + k * 4 + 3},{(y0 + y1) / 2} {x1 + k * 5},{y1}" stroke="#bfe3f5" '
                   f'stroke-width="3" fill="none" stroke-opacity="0.85" stroke-linecap="round"/>' for k in (-1, 0, 1))


def can(x, y, s=1.0, empty=False):
    """A big green watering can standing on the ground at (x, y)."""
    g = f'<g transform="translate({x} {y}) scale({s})">'
    g += ('<ellipse cx="0" cy="4" rx="70" ry="10" fill="#3a1606" fill-opacity="0.35"/>'
          '<path d="M 40,-40 L 112,-104 L 122,-96 L 58,-22 Z" fill="#3f9a3a" stroke="#1d4d1a" stroke-width="3.5"/>'
          '<ellipse cx="118" cy="-104" rx="11" ry="16" transform="rotate(-40 118 -104)" fill="#2f7d2a" stroke="#1d4d1a" stroke-width="3"/>'
          '<rect x="-50" y="-92" width="100" height="92" rx="12" fill="#4caf45" stroke="#1d4d1a" stroke-width="3.5"/>'
          '<path d="M -40,-92 Q 0,-150 40,-92" stroke="#1d4d1a" stroke-width="9" fill="none"/>'
          '<path d="M -40,-92 Q 0,-150 40,-92" stroke="#3f9a3a" stroke-width="5" fill="none"/>'
          '<rect x="-36" y="-80" width="10" height="66" rx="5" fill="#7fd477"/>')
    if empty:
        g += '<path d="M 112,-96 q 6,10 2,22" stroke="#a9d4ea" stroke-width="4" fill="none" stroke-linecap="round"/>'
    return g + "</g>"


def stool(x, base, w=130, h=150):
    return (f'<rect x="{x - w / 2}" y="{base - h}" width="{w}" height="18" rx="4" fill="#9a6a3a" stroke="#4a2a10" stroke-width="3"/>'
            f'<rect x="{x - w / 2 + 10}" y="{base - h + 18}" width="14" height="{h - 18}" fill="#7a4e26" stroke="#4a2a10" stroke-width="3"/>'
            f'<rect x="{x + w / 2 - 24}" y="{base - h + 18}" width="14" height="{h - 18}" fill="#7a4e26" stroke="#4a2a10" stroke-width="3"/>'
            f'<ellipse cx="{x}" cy="{base + 3}" rx="{w * 0.62:.0f}" ry="9" fill="#3a1606" fill-opacity="0.3"/>')


def sun_patch(x, y, r):
    return f'<ellipse cx="{x}" cy="{y}" rx="{r}" ry="{r * 0.35:.0f}" fill="#fff1b0" fill-opacity="0.35"/>'


def wet_soil_in_hands(img, box):
    """Darken the soil he holds (it is damp)."""
    a = np.array(img).astype(np.float32)
    x0, y0, x1, y1 = box
    reg = a[y0:y1, x0:x1, :3]
    r, g, b = reg[..., 0], reg[..., 1], reg[..., 2]
    soil = (r > g * 1.25) & (r < 200) & (b < 110) & (g < 120)
    reg[soil] *= 0.62
    a[y0:y1, x0:x1, :3] = reg
    return Image.fromarray(a.astype(np.uint8), img.mode)


def main():
    seg = new_session("isnet-anime")
    plate = Image.open(ROOT / "assets/2d/source/07_home.png").convert("RGBA").resize((W, H), Image.LANCZOS)
    plate.save(FR / "garden_plate.png")
    water = cut(seg, GN / "ep04/final/frames/f_water_s8.png")
    soil = cut(seg, GN / "ep02/final/frames/f_soil_s3.png")
    point = cut(seg, GN / "ep05/final/frames/f_point_s3.png")
    crossed = cut(seg, ROOT / "assets/2d/up/04_poses.png", (2786, 0, 3508, 1774))
    front = cut(seg, ROOT / "assets/2d/up/01_front.png", (0, 0, 2048, 3072))

    # watering: figure x0.9 shifted right; rose spout (120, 965) -> (238, 973)
    s, dx, dy = 0.9, 130, 105
    rx, ry = dx + 120 * s, dy + 975 * s
    for name, pool, drip in (("f_gwater", 0.3, 0.0), ("f_gflood", 1.15, 1.0)):
        out = plate.copy()
        out.alpha_composite(svg_layer(pot(rx, 1150, 120, wet=1.0, drip=drip, pool=pool)))
        place(out, water, s, dx, dy, shadow=(dx + 400 * s, dy + 1170 * s, 190))
        out.alpha_composite(svg_layer(stream(rx, ry + 8, rx + 2, 1150 - 98 - 14)))
        out.convert("RGB").save(FR / f"{name}.png")
        print("saved", name)

    out = plate.copy()
    out.alpha_composite(svg_layer(pot(170, 1170, 120, wet=1.0, drip=0.5, pool=1.1) + can(575, 1240, 0.7)))
    place(out, crossed, 940 / crossed.height, 380 - crossed.width * 940 / crossed.height / 2, 1225 - 940, shadow=(380, 1222, 160))
    out.convert("RGB").save(FR / "f_gproud.png")

    out = plate.copy()
    out.alpha_composite(svg_layer(pot(610, 1175, 110, wet=1.0, drip=0.4, pool=1.1)))
    place(out, wet_soil_in_hands(soil, (430, 560, 620, 760)), 0.92, 20, 120, shadow=(330, 1235, 230))
    out.convert("RGB").save(FR / "f_gsoil.png")

    out = plate.copy()
    out.alpha_composite(svg_layer(sun_patch(150, 1110, 150) + stool(150, 1110, h=185) + pot(150, 925, 118, wet=0.4)))
    place(out, point, 0.92, 90, 110, shadow=(450, 1225, 220))
    out.convert("RGB").save(FR / "f_gpoint.png")

    out = plate.copy()
    out.alpha_composite(svg_layer(sun_patch(130, 1135, 130) + stool(130, 1135) + pot(130, 985, 112, wet=0.4)))
    hgt = 1130
    sc = hgt / front.height
    out.alpha_composite(svg_layer(can(95, 1252, 0.68, empty=True)))
    place(out, front, sc, 400 - front.width * sc / 2, 1250 - hgt, shadow=(400, 1245, 170))
    out.convert("RGB").save(FR / "f_gstand.png")
    print("saved all")


if __name__ == "__main__":
    main()
