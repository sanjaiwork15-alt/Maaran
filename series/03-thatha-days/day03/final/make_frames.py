"""Day 3 start frames without a GPU: Thatha's village house – the thinnai at sunset and his kattil (rope cot) in the
courtyard (owner's 07_home art) through the night to the morning. Thatha only.

Run with the f5 env:  python -I make_frames.py
f_dsun:    the thinnai (Day 1 plate without the bowl) at sunset – he sits and yawns (talk.py "yawn").
f_dpoint:  courtyard at sunset, the kattil made up with pillow and blanket; Thatha (Groundnut Ep 5 pointing pose)
           points at it.
f_dbed:    the kattil in the courtyard; Thatha lying under the blanket – the owner's head sheet with the eyes painted
           shut, turned onto the pillow; the alarm clock stand (stool) and his phone beside the cot. Neutral light – the
           night -> dawn -> morning light is animated by tools/toon/bed.py. f_dbed1: one eye open.
f_dup:     sitting up in bed in the morning – the head sheet bust above the blanket (talks; surprise).
f_dpointr: morning, sitting on the kattil, pointing at the rooster on the tulsi maadam (pointing pose cut at the waist).
f_dstand:  morning, standing by the kattil with the blanket folded (owner's front art).
f_dtemple: the bust with his raised index finger (owner's hands sheet) at his temple – "naan dhaan niruthinen!".
Layers for bed.py are saved too (bed_*.png).
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
GN = ROOT / "series/01-groundnut"
sys.path.insert(0, str(ROOT / "tools/toon"))
from morning import rooster  # noqa: E402
W, H = 720, 1280
LINE = "#3a1a0a"


def svg_layer(body, w=W, h=H):
    return Image.open(io.BytesIO(cairosvg.svg2png(
        bytestring=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">{body}</svg>'.encode()))).convert("RGBA")


def cutout(im, seg):
    im = im.convert("RGB")
    a = np.array(remove(im, session=seg, only_mask=True)).astype(np.float32)
    a = np.clip((a - 90) * 2.6, 0, 255).astype(np.uint8)
    out = Image.fromarray(np.dstack([np.array(im), a]))
    return out.crop(out.getbbox())


def close_eyes(head, which=(0, 1)):
    """Paint the head sheet's eyes shut (1254 px sheet coords): skin over the eye, a curved lid line with lashes."""
    a = np.array(head.convert("RGB")).astype(np.float32)
    eyes = [((513, 535), (76, 54), (513, 612)), ((777, 527), (70, 53), (777, 602))]
    for k in which:
        (cx, cy), (rx, ry), (sx, sy) = eyes[k]
        skin = a[sy - 6:sy + 6, sx - 20:sx + 20].reshape(-1, 3).mean(axis=0)
        m = np.zeros(a.shape[:2], np.float32)
        cv2.ellipse(m, (cx, cy), (rx, ry), 0, 0, 360, 1.0, -1)
        m = cv2.GaussianBlur(m, (0, 0), 4)[..., None]
        yy = np.arange(a.shape[0])[:, None, None]
        shade = 1 - 0.14 * np.clip((cy + ry - yy) / (2 * ry), 0, 1)       # lid a little darker at the top
        a = a * (1 - m) + skin * shade * m
    img = Image.fromarray(a.astype(np.uint8))
    lids = ""
    for k in which:
        (cx, cy), (rx, ry), _ = eyes[k]
        y0 = cy + ry * 0.12
        lids += (f'<path d="M {cx - rx * 0.9:.0f},{y0:.0f} Q {cx:.0f},{y0 + ry * 0.62:.0f} {cx + rx * 0.9:.0f},{y0:.0f}" '
                 f'stroke="{LINE}" stroke-width="11" fill="none" stroke-linecap="round"/>')
        for j in range(5):                                   # lashes
            u = (j + 1) / 6
            px = cx - rx * 0.9 + u * rx * 1.8
            py = (1 - u) ** 2 * y0 + 2 * (1 - u) * u * (y0 + ry * 0.62) + u ** 2 * y0
            lids += (f'<line x1="{px:.0f}" y1="{py:.0f}" x2="{px + (u - 0.5) * 16:.0f}" y2="{py + 16:.0f}" stroke="{LINE}" '
                     f'stroke-width="5" stroke-linecap="round"/>')
    img = img.convert("RGBA")
    img.alpha_composite(svg_layer(lids, *img.size))
    return img


def kattil(x, y, w=520, h=120):
    """A rope cot (kattil) seen from the front, legs down to y + h."""
    legs = "".join(f'<rect x="{lx - 12}" y="{y - 10}" width="24" height="{h + 10}" rx="5" fill="#7a4a22" stroke="#3d2410" stroke-width="3"/>'
                   for lx in (x - w / 2 + 14, x + w / 2 - 14))
    ropes = "".join(f'<line x1="{x - w / 2 + 20 + k * 18}" y1="{y - 20}" x2="{x - w / 2 + 20 + k * 18 + 14}" y2="{y + 14}" '
                    f'stroke="#d8c08a" stroke-width="3"/>' for k in range(int((w - 40) / 18)))
    return (f'<ellipse cx="{x}" cy="{y + h + 4}" rx="{w * 0.6:.0f}" ry="14" fill="#3a1606" fill-opacity="0.35"/>' + legs +
            f'<rect x="{x - w / 2}" y="{y - 24}" width="{w}" height="40" fill="#e9d7a8"/>' + ropes +
            f'<rect x="{x - w / 2}" y="{y - 30}" width="{w}" height="14" rx="5" fill="#8a5428" stroke="#3d2410" stroke-width="3"/>'
            f'<rect x="{x - w / 2}" y="{y + 10}" width="{w}" height="14" rx="5" fill="#8a5428" stroke="#3d2410" stroke-width="3"/>')


def pillow(x, y, w=150, h=62):
    return (f'<ellipse cx="{x}" cy="{y}" rx="{w / 2}" ry="{h / 2}" fill="#f4f1e6" stroke="#8a8270" stroke-width="3"/>'
            f'<path d="M {x - w * 0.3},{y - h * 0.1} q {w * 0.3},{h * 0.25} {w * 0.6},0" stroke="#d6d0bf" stroke-width="3" fill="none"/>')


def blanket(x0, x1, top, base, folded=False):
    """Checked cotton blanket (maroon/cream) over him on the cot: a long mound from x0 to x1."""
    if folded:
        return (f'<rect x="{x0}" y="{base - 46}" width="{x1 - x0}" height="40" rx="10" fill="#9b2c3c" stroke="#4d1018" stroke-width="3"/>'
                f'<rect x="{x0}" y="{base - 30}" width="{x1 - x0}" height="8" fill="#e8d7b0"/>')
    mound = (f'M {x0 + 30},{base} Q {x0 - 30},{(top + base) / 2} {x0},{top + 26} Q {x0 + 20},{top} {x0 + 80},{top + 6} Q {(x0 + x1) / 2},{top - 18} '
             f'{x1 - 140},{top + 20} Q {x1 - 60},{top + 4} {x1 - 20},{top + 40} L {x1 + 10},{base + 10} Z')
    stripes = "".join(f'<path d="M {sx},{top} L {sx - 10},{base + 10}" stroke="#e8d7b0" stroke-width="7" opacity="0.8"/>'
                      for sx in range(int(x0) + 40, int(x1), 70))
    return (f'<clipPath id="bl"><path d="{mound}"/></clipPath><path d="{mound}" fill="#9b2c3c"/>'
            f'<g clip-path="url(#bl)">{stripes}<path d="M {x0},{top + 44} L {x1},{top + 52}" stroke="#e8d7b0" stroke-width="7"/></g>'
            f'<path d="{mound}" fill="none" stroke="#4d1018" stroke-width="4"/>'
            f'<path d="M {x0},{top + 26} Q {x0 + 20},{top} {x0 + 80},{top + 6}" stroke="#f0e2c0" stroke-width="9" fill="none"/>')


def stool(x, base, w=90, h=80):
    return (f'<ellipse cx="{x}" cy="{base + 3}" rx="{w * 0.6:.0f}" ry="8" fill="#3a1606" fill-opacity="0.3"/>'
            f'<rect x="{x - w / 2}" y="{base - h}" width="{w}" height="14" rx="4" fill="#9a6a3a" stroke="#4a2a10" stroke-width="3"/>'
            f'<rect x="{x - w / 2 + 8}" y="{base - h + 14}" width="11" height="{h - 14}" fill="#7a4e26" stroke="#4a2a10" stroke-width="2.5"/>'
            f'<rect x="{x + w / 2 - 19}" y="{base - h + 14}" width="11" height="{h - 14}" fill="#7a4e26" stroke="#4a2a10" stroke-width="2.5"/>')


def phone_flat(x, y):
    return (f'<path d="M {x - 26},{y} L {x + 26},{y} L {x + 22},{y - 9} L {x - 22},{y - 9} Z" fill="#2a2f36" stroke="#0d0f12" stroke-width="2.5"/>')


def grade(img, kind):
    """sunset: warm orange, a little darker; morning: soft, slightly warm."""
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    if kind == "sunset":
        a = a * np.array([1.05, 0.82, 0.62]) * 0.88 + np.array([18, 6, 0])
    elif kind == "morning":
        a = a * np.array([1.02, 0.98, 0.9]) + np.array([6, 4, 0])
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def main():
    seg = new_session("isnet-anime")
    plate = Image.open(SRC / "07_home.png").convert("RGBA").resize((W, H), Image.LANCZOS)
    head = Image.open(SRC / "02_head.png").convert("RGB")
    head_cut = cutout(head, seg)                              # bust with shirt + towel
    hb = head_cut.getbbox()

    # --- the sleeping head: eyes shut, rotated onto the pillow (top of the head to the left)
    def lying(which, scale):
        h2 = close_eyes(head, which)
        a = np.array(remove(head, session=seg, only_mask=True)).astype(np.float32)
        a = np.clip((a - 90) * 2.6, 0, 255).astype(np.uint8)
        hsv = cv2.cvtColor(np.array(head), cv2.COLOR_RGB2HSV).astype(int)
        towel = (hsv[..., 0] >= 30) & (hsv[..., 0] <= 90) & (hsv[..., 1] > 60)
        towel[:880, :] = False
        towel[:, :800] = False
        a[cv2.dilate(towel.astype(np.uint8), np.ones((25, 25), np.uint8)).astype(bool)] = 0     # under the blanket
        h2 = Image.fromarray(np.dstack([np.array(h2.convert("RGB")), a]))
        h2 = h2.crop(h2.getbbox()).rotate(82, expand=True, resample=Image.BICUBIC)
        return h2.resize((round(h2.width * scale), round(h2.height * scale)), Image.LANCZOS)

    # wide: the cot in the courtyard
    CX, CY = 360, 1040
    out = plate.copy()
    out.alpha_composite(svg_layer(kattil(CX - 20, CY, 560)))
    out.alpha_composite(svg_layer(pillow(CX - 225, CY - 42, 110, 46)))
    hd = lying((0, 1), 0.105)
    out.alpha_composite(hd, (CX - 268, CY - 38 - hd.height + 18))
    out.alpha_composite(svg_layer(blanket(CX - 190, CX + 275, CY - 92, CY - 16)))
    out.convert("RGB").save(FR / "f_dbedw.png")

    # close: background = the courtyard zoomed in (lower left of the house), the cot across the frame
    bg = plate.crop((0, 560, 360, 1200)).resize((W, H), Image.LANCZOS)
    for name, which in (("f_dbed", (0, 1)), ("f_dbed1", (1,))):
        out = bg.copy()
        out.alpha_composite(svg_layer(kattil(470, 1000, 900, 300)))
        out.alpha_composite(svg_layer(pillow(150, 900, 300, 120)))
        hd = lying(which, 0.33)
        out.alpha_composite(hd, (-10, 905 - hd.height + 40))
        out.alpha_composite(svg_layer(blanket(215, 900, 700, 985)))
        out.convert("RGB").save(FR / f"{name}.png")
        print("saved", name)

    # sunset on the thinnai (Day 1 plate: the bowl removed; his hand at his mouth = covering a yawn)
    th = Image.open(ROOT / "series/03-thatha-days/day01/final/frames/lama_clean.png")
    grade(th, "sunset").save(FR / "f_dsun.png")

    # sunset in the courtyard: the made-up kattil, Thatha pointing at it
    ppl = cutout(Image.open(GN / "ep05/final/frames/f_point_s3.png"), seg)
    out = grade(plate, "sunset").convert("RGBA")
    out.alpha_composite(svg_layer(kattil(200, 1050, 360) + pillow(65, 1018, 90, 40) + blanket(110, 380, 1000, 1034)))
    sc = 760 / ppl.height
    p2 = ppl.resize((round(ppl.width * sc), 760), Image.LANCZOS)
    p2 = Image.fromarray(np.dstack([np.array(grade(p2, "sunset")), np.array(p2)[..., 3]]))
    out.alpha_composite(svg_layer('<ellipse cx="520" cy="1240" rx="170" ry="22" fill="#3a1606" fill-opacity="0.4"/>'))
    out.alpha_composite(p2, (700 - p2.width, 1250 - 760))
    out.convert("RGB").save(FR / "f_dpoint.png")

    # morning, sitting up in bed (close courtyard background)
    bgm = grade(bg, "morning").convert("RGBA")
    bust = head_cut.resize((round(head_cut.width * 0.5), round(head_cut.height * 0.5)), Image.LANCZOS)
    out = bgm.copy()
    out.alpha_composite(svg_layer(kattil(400, 1060, 900, 240) + pillow(130, 900, 240, 100)))
    out.alpha_composite(bust, (360 - bust.width // 2, 1000 - bust.height))
    out.alpha_composite(svg_layer(blanket(80, 900, 930, 1045)))
    out.convert("RGB").save(FR / "f_dup.png")

    # pointing at the rooster (the pointing pose cut at the waist, sitting in bed)
    out = bgm.copy()
    out.alpha_composite(svg_layer(rooster(115, 655, 1.5)))
    out.alpha_composite(svg_layer(kattil(420, 1060, 900, 240) + pillow(620, 905, 220, 96)))
    pc = ppl.crop((0, 0, ppl.width, round(ppl.height * 0.66)))
    sc = 760 / pc.height
    pc = pc.resize((round(pc.width * sc), 760), Image.LANCZOS)
    out.alpha_composite(pc, (740 - pc.width, 980 - pc.height))
    out.alpha_composite(svg_layer(blanket(-40, 900, 900, 1045)))
    out.convert("RGB").save(FR / "f_dpointr.png")

    # morning, standing by the kattil, blanket folded
    fr = cutout(Image.open(ROOT / "assets/2d/up/01_front.png"), seg)
    out = grade(plate, "morning").convert("RGBA")
    out.alpha_composite(svg_layer(kattil(190, 1060, 340) + pillow(70, 1025, 90, 40) + blanket(150, 330, 0, 1046, folded=True)))
    sc = 1080 / fr.height
    f2 = fr.resize((round(fr.width * sc), 1080), Image.LANCZOS)
    out.alpha_composite(svg_layer('<ellipse cx="480" cy="1243" rx="170" ry="24" fill="#3a1606" fill-opacity="0.4"/>'))
    out.alpha_composite(f2, (480 - f2.width // 2, 1250 - 1080))
    out.convert("RGB").save(FR / "f_dstand.png")

    # finger at his temple: the bust + the hands sheet's raised index finger
    hands = Image.open(SRC / "03_hands.png").convert("RGB")
    arm = cutout(hands.crop((440, 0, 770, 724)), seg)
    cutout(hands.crop((900, 0, 1210, 724)), seg).save(FR / "arm_down.png")       # hanging hand: reaches for the alarm
    out = bgm.copy()
    b2 = head_cut.resize((round(head_cut.width * 0.62), round(head_cut.height * 0.62)), Image.LANCZOS)
    out.alpha_composite(b2, (360 - b2.width // 2, H - b2.height + 40))
    asc = 820 / arm.height
    a2 = arm.resize((round(arm.width * asc), 820), Image.LANCZOS)
    out.alpha_composite(a2, (455, 600))
    out.convert("RGB").save(FR / "f_dtemple.png")
    print("saved morning frames")


if __name__ == "__main__":
    main()
