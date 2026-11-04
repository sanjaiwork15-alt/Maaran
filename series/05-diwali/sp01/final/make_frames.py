"""Diwali special 1 – start frames, no GPU: the owner's farmhouse art (07_home) at dusk with Diwali decorations
(tools/toon/diwali.py), Thatha = the owner's sitting drawing (09_sitting) on a wooden chair drawn in code (the
drawing's brick seat removed), his phone in his hand; and the owner's standing drawing with a yellow cloth bag.

Run with the f5 env:  python -I make_frames.py
f_chair:  sitting on the wooden chair in the decorated courtyard, phone in his hand (screen glow on his face).
f_warm:   the same, a warm golden light on his face (the idea).
f_old:    the same, his old keypad phone in his hand instead (reality).
f_tin:    the same, no phone: his open red savings tin on his lap, notes and coins inside.
f_bag:    standing (01_front) holding the yellow "manja pai" cloth bag, ready to go (shopping list in the bag).
*_mask.png: Thatha's silhouette per frame (the animated diya/bulb lights are not drawn over him).
"""
import io
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
sys.path.insert(0, str(ROOT / "tools/toon"))
import diwali as D  # noqa: E402

W, H = 720, 1280
WOOD, WOOD_D, WOOD_L, OUTL = "#8a5a2b", "#6b4220", "#b07a44", "#3e2410"


def svg(body, w, h):
    return np.array(Image.open(io.BytesIO(cairosvg.svg2png(
        bytestring=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">{body}</svg>'.encode()))).convert("RGBA"))


def plank(x, y, w, h, col=WOOD):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{col}" stroke="{OUTL}" stroke-width="7"/>'
            f'<line x1="{x + 8}" y1="{y + 8}" x2="{x + 8}" y2="{y + h - 8}" stroke="{WOOD_L}" stroke-width="5" opacity="0.6"/>')


def chair():
    """A plain wooden chair in the sitting drawing's own coords (1024x1536): back, seat, legs."""
    g = []
    g.append(plank(232, 1000, 34, 380, WOOD_D) + plank(826, 1000, 34, 380, WOOD_D))      # rear legs
    g.append(plank(205, 430, 44, 560) + plank(843, 430, 44, 560))                          # back posts
    g.append(plank(195, 440, 702, 58) + plank(215, 560, 662, 34))                          # back rails
    for x in (330, 430, 530, 630, 730):
        g.append(plank(x, 498, 34, 64, WOOD_D))
    g.append(plank(150, 925, 792, 48))                                                      # seat front edge
    g.append(plank(162, 965, 44, 455) + plank(886, 965, 44, 455))                          # front legs
    g.append(plank(185, 1250, 722, 26, WOOD_D))                                            # stretcher
    return "".join(g)


def sitting_without_seat(seg):
    im = Image.open(SRC / "09_sitting.png").convert("RGB")
    rgb = np.array(im)
    a = np.array(remove(im, session=seg, only_mask=True)).astype(np.float32)
    a = np.clip((a - 90) * 2.6, 0, 255)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(int)
    yy, xx = np.mgrid[0:rgb.shape[0], 0:rgb.shape[1]]
    white = ((hsv[..., 1] < 45) & (hsv[..., 2] > 150)) | ((hsv[..., 0] >= 35) & (hsv[..., 0] <= 85) & (hsv[..., 1] > 60))
    keep_cloth = cv2.dilate(white.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    legs = np.zeros(rgb.shape[:2], np.uint8)
    cv2.fillPoly(legs, [np.array([(255, 1160), (402, 1160), (412, 1385), (412, 1432), (172, 1432), (176, 1335), (250, 1300)], np.int32)], 1)
    cv2.fillPoly(legs, [np.array([(698, 1160), (832, 1160), (835, 1300), (908, 1345), (908, 1432), (666, 1432), (690, 1380)], np.int32)], 1)
    st = np.zeros(rgb.shape[:2], np.uint8)                 # the slanted stick only
    cv2.line(st, (165, 235), (88, 1392), 1, 58)
    stick = st.astype(bool)
    hands = np.zeros(rgb.shape[:2], np.uint8)
    cv2.rectangle(hands, (318, 815), (452, 955), 1, -1)
    cv2.rectangle(hands, (628, 845), (772, 975), 1, -1)
    block = (xx > 8) & (xx < 1012) & (yy > 918) & (yy < 1372)
    cloth_x = (xx > 186) & (xx < 893)                       # the veshti's own width; outside it, pale = brick face
    brick = block & ~(keep_cloth & cloth_x) & ~legs.astype(bool) & ~stick & ~hands.astype(bool)
    a[brick] = 0
    a[(yy > 1372) & ~legs.astype(bool) & ~stick] *= (rgb[(yy > 1372) & ~legs.astype(bool) & ~stick].min(axis=1) < 200)   # block shadow
    return rgb, a.astype(np.uint8)


def place(plate, layer, sc, cx, bottom, src_bottom):
    """Scale a 1024x1536 RGBA layer by sc and put its point (512, src_bottom) at (cx, bottom)."""
    h, w = layer.shape[:2]
    lay = cv2.resize(layer, (round(w * sc), round(h * sc)), interpolation=cv2.INTER_AREA)
    x0, y0 = round(cx - 512 * sc), round(bottom - src_bottom * sc)
    out = Image.fromarray(plate).convert("RGBA")
    tmp = Image.new("RGBA", out.size)
    tmp.paste(Image.fromarray(lay), (x0, y0))
    out.alpha_composite(tmp)
    return np.array(out.convert("RGB")), np.array(tmp)[..., 3], (x0, y0)


def main():
    only = sys.argv[1:]                                     # e.g. "f_old f_tin": rebuild just those
    seg = new_session("isnet-anime")
    home = np.array(Image.open(SRC / "07_home.png").convert("RGB").resize((W, H), Image.LANCZOS))
    plate = D.over(D.dusk(home).astype(np.float32), svg(D.decor_static((560, 1150, 105)), W, H).astype(np.float32)).astype(np.uint8)
    Image.fromarray(plate).save(FR / "dusk_plate.png")
    rgb, a = sitting_without_seat(seg)
    fig = np.dstack([rgb, a])
    # dusk light on Thatha too (a little less), warm diya light from below, cool screen light on the face
    lit = fig.astype(np.float32)
    lit[..., :3] = lit[..., :3] * np.array([0.78, 0.74, 0.84]) + np.array([10, 4, 12])
    ch = svg(chair(), 1024, 1536).astype(np.float32)
    ch[..., :3] = ch[..., :3] * np.array([0.78, 0.74, 0.84])
    yy, xx = np.mgrid[0:1536, 0:1024].astype(np.float32)
    # the phone in his right hand (image left), resting on his knee; his fingers back on top
    hand = ((xx > 320) & (xx < 450) & (yy > 820) & (yy < 950)) | ((xx > 628) & (xx < 772) & (yy > 845) & (yy < 975))
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(int)
    skin = hand & (hsv[..., 0] <= 22) & (hsv[..., 1] > 100) & (a > 200)
    phone = svg('<g transform="rotate(-18 390 900)"><rect x="350" y="830" width="82" height="150" rx="12" fill="#1d2228" '
                'stroke="#0a0c0e" stroke-width="5"/><rect x="358" y="840" width="66" height="128" rx="6" fill="#7fc8ff" fill-opacity="0.85"/></g>',
                1024, 1536).astype(np.float32)
    keypad = svg('<g transform="translate(-14 82) rotate(-18 390 900)"><rect x="356" y="836" width="70" height="140" rx="16" fill="#3d4a55" '
                 'stroke="#0f1418" stroke-width="5"/><rect x="366" y="848" width="50" height="40" rx="4" fill="#a9c27a" stroke="#0f1418" stroke-width="3"/>'
                 + "".join(f'<rect x="{367 + c * 17}" y="{898 + r * 17}" width="13" height="11" rx="3" fill="#cfd4d8"/>' for r in range(4) for c in range(3))
                 + '<line x1="368" y1="852" x2="410" y2="880" stroke="#5d6b4a" stroke-width="2"/></g>', 1024, 1536).astype(np.float32)
    tin = svg('<ellipse cx="540" cy="984" rx="118" ry="13" fill="#000" fill-opacity="0.28"/>'
              '<path d="M 462,832 L 618,832 L 628,882 L 452,882 Z" fill="#a33a3a" stroke="#3a1010" stroke-width="6"/>'   # lid, open (upright)
              '<circle cx="540" cy="857" r="15" fill="#c9504f" stroke="#3a1010" stroke-width="4"/><path d="M 528,857 L 552,857" stroke="#ffd54f" stroke-width="5"/>'
              '<path d="M 452,882 L 628,882 L 640,905 L 440,905 Z" fill="#4a1414" stroke="#3a1010" stroke-width="5"/>'      # inside
              '<g transform="rotate(-8 500 890)"><rect x="470" y="872" width="70" height="30" fill="#e3a0b8" stroke="#6b4a55" stroke-width="3"/></g>'
              '<g transform="rotate(6 575 890)"><rect x="545" y="874" width="66" height="28" fill="#d995ad" stroke="#6b4a55" stroke-width="3"/></g>'
              '<ellipse cx="610" cy="896" rx="12" ry="6" fill="#c9cdd2" stroke="#6d737a" stroke-width="2"/>'
              '<rect x="440" y="903" width="200" height="82" rx="8" fill="#8a2f2f" stroke="#3a1010" stroke-width="6"/>'
              '<path d="M 446,925 L 634,925" stroke="#c9504f" stroke-width="5"/><path d="M 446,962 L 634,962" stroke="#5a1d1d" stroke-width="5"/>',
              1024, 1536).astype(np.float32)
    fingers = lit.copy()
    fingers[..., 3] = skin * 255
    for name, warm, prop in (("f_chair", 0.0, phone), ("f_warm", 1.0, phone), ("f_old", 0.0, keypad), ("f_tin", 0.0, tin)):
        if only and name not in only:
            continue
        L = lit.copy()
        face = np.exp(-(((xx - 520) / 260) ** 2 + ((yy - 380) / 300) ** 2))[..., None]
        if prop is phone:
            L[..., :3] += (np.array([120, 190, 255]) - L[..., :3]) * face * 0.10 * (1 - warm)  # phone light
        L[..., :3] = L[..., :3] * (1 + face * 0.22 * warm * np.array([0.25, 0.08, -0.25]))   # golden idea light
        L[..., :3] += face * warm * np.array([18, 10, 0])
        layer = np.zeros((1536, 1024, 4), np.float32)
        p_ = prop.copy()
        p_[..., :3] *= np.array([0.85, 0.82, 0.9])
        for part in (ch, L, p_, fingers):
            al = part[..., 3:4] / 255
            layer[..., :3] = layer[..., :3] * (1 - al) + part[..., :3] * al
            layer[..., 3:4] = np.maximum(layer[..., 3:4], part[..., 3:4])
        out, mask, off = place(plate, np.clip(layer, 0, 255).astype(np.uint8), 0.62, 330, 1245, 1430)
        if warm:
            gl = np.zeros((H, W, 3), np.float32)
            cy, cx = off[1] + 380 * 0.62, off[0] + 520 * 0.62
            Y, X = np.mgrid[0:H, 0:W]
            g = np.exp(-(((X - cx) / 260) ** 2 + ((Y - cy) / 260) ** 2))[..., None] * 0.10
            out = np.clip(out * (1 + g * np.array([1.6, 0.6, -1.4])), 0, 255).astype(np.uint8)
        Image.fromarray(out).save(FR / f"{name}.png")
        Image.fromarray(mask).save(FR / f"{name}_mask.png")
        print("saved", name, off)
    if only and "f_bag" not in only:
        return
    # standing with the yellow cloth bag
    fr = Image.open(ROOT / "assets/2d/up/01_front.png").convert("RGB")
    fa = np.array(remove(fr, session=seg, only_mask=True)).astype(np.float32)
    fa = np.clip((fa - 90) * 2.6, 0, 255).astype(np.uint8)
    frgb = np.array(fr).astype(np.float32) * np.array([0.8, 0.76, 0.86]) + np.array([10, 4, 12])
    figb = np.dstack([np.clip(frgb, 0, 255), fa]).astype(np.uint8)
    # bag hangs from his free fist (image right; source fist ~ (780, 1030) in the 1024x1536 drawing -> x2 here)
    bag = svg('<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#e0aa10"/>'
              '<stop offset="0.45" stop-color="#ffd23a"/><stop offset="1" stop-color="#c99300"/></linearGradient></defs>'
              '<path d="M 1468,2050 Q 1560,1830 1652,2050" stroke="#c99300" stroke-width="24" fill="none"/>'
              '<path d="M 1385,2040 Q 1560,2020 1735,2040 Q 1790,2300 1755,2560 Q 1560,2610 1365,2560 Q 1330,2300 1385,2040 Z" '
              'fill="url(#bg)" stroke="#8a6a00" stroke-width="10"/>'
              '<path d="M 1470,2060 Q 1450,2300 1480,2540 M 1640,2060 Q 1675,2300 1650,2540" stroke="#b88a00" stroke-width="8" fill="none" opacity="0.7"/>'
              '<path d="M 1400,2120 Q 1560,2105 1720,2120" stroke="#b88a00" stroke-width="8" fill="none"/>'
              '<rect x="1600" y="1990" width="40" height="90" rx="6" fill="#fbfaf2" stroke="#999" stroke-width="5" transform="rotate(12 1620 2030)"/>'
              '<path d="M 1440,2200 q 120,40 240,0" stroke="#c99a00" stroke-width="6" fill="none"/>', 2048, 3072).astype(np.float32)
    hsv = cv2.cvtColor(np.array(fr), cv2.COLOR_RGB2HSV).astype(int)
    YY, XX = np.mgrid[0:3072, 0:2048]
    fist = (XX > 1430) & (XX < 1700) & (YY > 1880) & (YY < 2110) & (hsv[..., 0] <= 22) & (hsv[..., 1] > 100) & (fa > 200)
    lay = figb.astype(np.float32)
    al = bag[..., 3:4] / 255
    lay[..., :3] = lay[..., :3] * (1 - al) + bag[..., :3] * np.array([0.95, 0.9, 0.85]) * al
    lay[..., 3:4] = np.maximum(lay[..., 3:4], bag[..., 3:4])
    f2 = figb.astype(np.float32).copy()
    f2[..., 3] = fist * 255
    al = f2[..., 3:4] / 255
    lay[..., :3] = lay[..., :3] * (1 - al) + f2[..., :3] * al
    lay = np.clip(lay, 0, 255).astype(np.uint8)
    ys, xs = np.nonzero(lay[..., 3] > 30)
    lay = lay[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    hgt = 1080
    sc = hgt / lay.shape[0]
    lay = cv2.resize(lay, (round(lay.shape[1] * sc), hgt), interpolation=cv2.INTER_AREA)
    D.LANTERNS[:] = [(80, 555, 92), (650, 555, 92)]
    plate_b = D.over(D.dusk(home).astype(np.float32), svg(D.decor_static((560, 1150, 105)), W, H).astype(np.float32)).astype(np.uint8)
    Image.fromarray(plate_b).save(FR / "dusk_plate_b.png")
    out = Image.fromarray(plate_b).convert("RGBA")
    sh = svg('<ellipse cx="360" cy="1232" rx="170" ry="24" fill="#000" fill-opacity="0.35"/>', W, H)
    out.alpha_composite(Image.fromarray(sh))
    tmp = Image.new("RGBA", out.size)
    x0, y0 = 360 - lay.shape[1] // 2 + 20, 1240 - hgt
    tmp.paste(Image.fromarray(lay), (x0, y0))
    out.alpha_composite(tmp)
    out.convert("RGB").save(FR / "f_bag.png")
    Image.fromarray(np.array(tmp)[..., 3]).save(FR / "f_bag_mask.png")
    print("saved f_bag", (x0, y0, sc))


if __name__ == "__main__":
    main()
