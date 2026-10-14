"""Maaran Thatha in flat 2D cartoon style, drawn entirely in code (SVG). Royalty-free.

thatha(pose)  -> SVG group of the rigged character, in a 1000 x 1800 box (feet at y=1790).
scene()       -> SVG of the red-soil field ("semman kaadu") on a 2160 x 3840 stage.
frame(cam, pose, char_at) -> complete SVG for one 1080x1920 frame; cam=(cx, cy, h) on the stage.

Pose keys (all optional): mouth (Rhubarb shape A-H or X), blink (0..1), brow (0..1 raise),
head (deg tilt), body (deg sway), r_up / r_fore (right arm, holds the stick), l_up / l_fore
(left arm), l_hand ("rest" | "open" | "point"), look (eye shift in px, -1..1).
The look follows assets/character/maaran_thatha_reference.webp and bible/character.md:
white hair combed back, curled white moustache, full white beard, cream half-sleeve shirt,
green towel on his LEFT shoulder, white veshti with a thin green border, brown slippers,
wooden walking stick in his RIGHT hand.
"""
import math

OUT = "#3b2416"
SKIN, SKIN_SH, SKIN_HI = "#c47d48", "#a3612f", "#d99a63"
HAIR, HAIR_SH = "#f6f3ec", "#d3cdc1"
SHIRT, SHIRT_SH = "#f0e6cc", "#d8c9a5"
TOWEL, TOWEL_SH, TOWEL_HI = "#7aba45", "#5a9630", "#9bd064"
VESHTI, VESHTI_SH, BORDER = "#fcfaf3", "#e4dfd2", "#5ea93a"
STICK, STICK_SH = "#8d5c2c", "#6a4320"
SLIPPER, SLIPPER_SH = "#7b4a25", "#5c341a"
MOUTH_IN, TEETH, TONGUE = "#5a1e1a", "#fbf6ec", "#c4524c"
W = 4  # outline width


def p(d, fill, stroke=OUT, w=W, extra=""):
    s = f'stroke="{stroke}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"' if stroke else ""
    return f'<path d="{d}" fill="{fill}" {s} {extra}/>'


def line(d, color=OUT, w=W):
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'


def rot(deg, x, y, inner):
    return f'<g transform="rotate({deg:.2f} {x} {y})">{inner}</g>'


# ------------------------------------------------------------------ face parts

def eye(cx, cy, blink, look, flip):
    if blink > 0.6:
        return line(f"M {cx-22},{cy+2} Q {cx},{cy+11} {cx+22},{cy+2}", OUT, 4.5)
    ry = 15 * (1 - blink)
    ix = cx + 4 * look
    lid = f"M {cx-24},{cy-1} Q {cx},{cy-ry-9} {cx+24},{cy-1}"
    return (f'<ellipse cx="{cx}" cy="{cy}" rx="22" ry="{ry:.1f}" fill="#fffdf8" stroke="{OUT}" stroke-width="3"/>'
            f'<clipPath id="ec{flip}"><ellipse cx="{cx}" cy="{cy}" rx="22" ry="{ry:.1f}"/></clipPath>'
            f'<g clip-path="url(#ec{flip})"><circle cx="{ix}" cy="{cy+1}" r="13" fill="#4a2a14"/>'
            f'<circle cx="{ix}" cy="{cy+1}" r="6.5" fill="#160b05"/><circle cx="{ix+4}" cy="{cy-4}" r="3.6" fill="#fff"/></g>'
            + line(lid, OUT, 4.5)
            + line(f"M {cx-14},{cy+15} Q {cx},{cy+21} {cx+14},{cy+15}", SKIN_SH, 3))


def brow(cx, cy, raise_, flip):
    s = -1 if flip else 1
    y = cy - 9 * raise_
    d = (f"M {cx-34*s},{y+12} C {cx-30*s},{y-14} {cx+10*s},{y-24} {cx+34*s},{y-6} C {cx+30*s},{y+2} {cx+26*s},{y+6} {cx+18*s},{y+6} "
         f"C {cx+6*s},{y+6} {cx-6*s},{y+10} {cx-14*s},{y+12} C {cx-22*s},{y+14} {cx-28*s},{y+16} {cx-34*s},{y+12} Z")
    return p(d, HAIR, OUT, 3)


MOUTHS = {  # Rhubarb mouth shapes: (half width, open height, teeth, tongue)
    "X": (22, 0, False, False), "A": (20, 0, False, False), "B": (22, 7, True, False),
    "C": (24, 14, True, False), "D": (26, 22, True, True), "E": (19, 15, False, True),
    "F": (12, 10, False, False), "G": (22, 8, True, False), "H": (23, 15, True, True),
}


def mouth(shape, cx=500, cy=284):
    hw, h, teeth, tongue = MOUTHS.get(shape, MOUTHS["X"])
    if h == 0:
        return line(f"M {cx-hw},{cy-2} Q {cx},{cy+8} {cx+hw},{cy-2}", OUT, 4.5)
    d = f"M {cx-hw},{cy-3} Q {cx},{cy-6} {cx+hw},{cy-3} Q {cx+hw*0.8},{cy+h} {cx},{cy+h+2} Q {cx-hw*0.8},{cy+h} {cx-hw},{cy-3} Z"
    inner = p(d, MOUTH_IN, OUT, 3.5)
    clip = f'<clipPath id="mclip"><path d="{d}"/></clipPath><g clip-path="url(#mclip)">'
    if teeth:
        clip += f'<rect x="{cx-hw}" y="{cy-6}" width="{2*hw}" height="{min(7, h*0.5):.1f}" fill="{TEETH}"/>'
    if tongue:
        clip += f'<ellipse cx="{cx}" cy="{cy+h+2}" rx="{hw*0.6:.1f}" ry="{h*0.45:.1f}" fill="{TONGUE}"/>'
    return inner + clip + "</g>"


def hair_outline():
    """Tufted silhouette of thick white hair combed back: wavy bumps over the crown, short above the ears."""
    pts = []
    n = 13
    for i in range(n + 1):
        a = math.radians(196 + 148 * i / n)
        r = 1.0 + (0.07 if i % 2 else 0.0)
        pts.append((500 + 118 * r * math.cos(a), 128 + 104 * r * math.sin(a)))
    d = f"M 392,178 L {pts[0][0]:.0f},{pts[0][1]:.0f} "
    for i in range(1, len(pts)):
        (x0, y0), (x1, y1) = pts[i - 1], pts[i]
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        k = 1.10 if i % 2 else 1.02
        d += f"Q {500 + (mx - 500) * k:.0f},{128 + (my - 128) * k:.0f} {x1:.0f},{y1:.0f} "
    return d + "L 608,178 C 590,150 410,150 392,178 Z"


def head(pose):
    blink, look, br = pose.get("blink", 0), pose.get("look", 0), pose.get("brow", 0)
    g = []
    # hair mass behind the head
    g.append(p(hair_outline(), HAIR))
    # ears
    for x, s in ((396, 1), (604, -1)):
        g.append(f'<ellipse cx="{x}" cy="205" rx="19" ry="31" fill="{SKIN}" stroke="{OUT}" stroke-width="{W}"/>')
        g.append(line(f"M {x+6*s},{193} Q {x-4*s},{205} {x+5*s},{218}", SKIN_SH, 3))
    # face
    g.append(p("M 400,190 C 398,120 440,78 500,78 C 560,78 602,120 600,190 C 602,250 580,318 500,322 C 420,318 398,250 400,190 Z", SKIN))
    g.append(p("M 560,96 C 590,120 600,160 598,205 C 596,250 585,285 560,305 C 585,260 590,200 560,96 Z", SKIN_SH, None))
    g.append(line("M 456,126 Q 500,118 544,126", SKIN_SH, 3) + line("M 466,138 Q 500,132 534,138", SKIN_SH, 3))
    g.append(f'<ellipse cx="438" cy="236" rx="20" ry="11" fill="#d9775a" opacity="0.35"/>'
             f'<ellipse cx="562" cy="236" rx="20" ry="11" fill="#d9775a" opacity="0.35"/>')
    # hair on top, combed back with a receding hairline
    g.append(p("M 400,170 C 394,120 420,70 470,58 C 490,50 520,50 538,58 C 584,70 608,120 600,170 "
               "C 594,150 586,132 574,122 C 562,110 550,106 538,110 C 526,98 512,106 500,101 C 488,106 474,98 462,110 "
               "C 450,106 438,110 426,122 C 414,132 406,150 400,170 Z", HAIR, None))
    g.append(line("M 400,170 C 406,150 414,132 426,122 C 438,110 450,106 462,110 C 474,98 488,106 500,101 "
                  "C 512,106 526,98 538,110 C 550,106 562,110 574,122 C 586,132 594,150 600,170"))
    g.append(line("M 432,92 Q 462,70 500,66", HAIR_SH, 3) + line("M 512,70 Q 548,72 576,94", HAIR_SH, 3)
             + line("M 412,134 Q 420,108 440,94", HAIR_SH, 3) + line("M 590,134 Q 582,108 562,94", HAIR_SH, 3)
             + line("M 470,86 Q 500,78 530,86", HAIR_SH, 3))
    # eyes, brows
    g.append(eye(456, 186, blink, look, 0) + eye(544, 186, blink, look, 1))
    g.append(brow(456, 152, br, False) + brow(544, 152, br, True))
    # beard (full, white), with a gap where the mouth is
    g.append(p("M 401,212 C 396,285 425,352 470,378 C 490,388 510,388 530,378 C 575,352 604,285 599,212 "
               "C 590,250 570,268 545,272 C 530,300 470,300 455,272 C 430,268 410,250 401,212 Z", HAIR))
    g.append(line("M 430,300 Q 445,335 470,355", HAIR_SH, 3) + line("M 570,300 Q 555,335 530,355", HAIR_SH, 3)
             + line("M 500,330 L 500,368", HAIR_SH, 3) + line("M 415,250 Q 420,285 440,312", HAIR_SH, 3)
             + line("M 585,250 Q 580,285 560,312", HAIR_SH, 3))
    g.append(mouth(pose.get("mouth", "X")))
    # nose
    g.append(p("M 489,172 C 486,198 474,214 476,232 C 480,250 520,250 524,232 C 526,214 514,198 511,172", SKIN_HI, OUT, 3.5))
    g.append(f'<ellipse cx="489" cy="238" rx="5" ry="3.5" fill="{SKIN_SH}"/><ellipse cx="511" cy="238" rx="5" ry="3.5" fill="{SKIN_SH}"/>')
    # curled moustache
    g.append(p("M 500,252 C 480,240 452,240 432,254 C 420,262 404,262 398,248 C 392,266 408,282 434,278 "
               "C 458,274 482,266 500,266 C 518,266 542,274 566,278 C 592,282 608,266 602,248 "
               "C 596,262 580,262 568,254 C 548,240 520,240 500,252 Z", HAIR))
    g.append(line("M 445,258 Q 470,252 492,258", HAIR_SH, 3) + line("M 555,258 Q 530,252 508,258", HAIR_SH, 3))
    return rot(pose.get("head", 0), 500, 340, "".join(g))


# ------------------------------------------------------------------ body parts

def stick():
    return (f'<rect x="302" y="700" width="24" height="1092" rx="10" fill="{STICK}" stroke="{OUT}" stroke-width="{W}"/>'
            f'<rect x="316" y="712" width="5" height="1070" fill="{STICK_SH}"/>')


def hand(kind):
    """A hand with the wrist at (0, 0), hanging down (+y)."""
    if kind == "open":   # open palm facing the viewer, thumb on the inside
        d = ("M -24,0 C -30,20 -30,40 -24,54 L -26,94 C -26,102 -13,102 -13,94 L -12,62 L -9,106 C -9,114 5,114 5,106 "
             "L 4,63 L 9,102 C 9,110 23,110 22,102 L 18,60 L 28,88 C 30,96 42,94 40,86 L 30,44 C 30,24 28,10 24,0 Z")
        return (p("M -22,22 C -40,30 -50,48 -46,60 C -42,68 -32,64 -30,56 L -22,44 Z", SKIN) + p(d, SKIN)
                + line("M -16,38 Q 0,46 18,40", SKIN_SH, 3))
    if kind == "point":  # fist with the index finger out
        return (p("M -6,40 L -6,108 C -6,118 8,118 8,108 L 8,40 Z", SKIN) + fist())
    return fist()


def fist():
    return (p("M -30,-6 C -30,-20 -10,-24 8,-22 C 28,-20 38,-8 38,12 C 40,38 24,54 2,54 C -20,54 -36,42 -36,20 Z", SKIN)
            + line("M -30,14 Q 0,8 34,16", SKIN_SH, 3) + line("M -32,30 Q 0,24 34,32", SKIN_SH, 3)
            + line("M -26,44 Q 0,40 28,46", SKIN_SH, 3))


def arm(up, fore, hand_svg, with_stick):
    """His right arm in its own coordinates; the left arm is this, mirrored."""
    upper = p("M 326,428 C 314,490 310,552 314,616 L 362,620 C 366,556 370,490 374,428 Z", SKIN)
    lower = p("M 314,606 C 306,660 298,712 294,764 L 338,770 C 344,714 352,660 362,612 Z", SKIN)
    lower += p("M 344,616 C 340,660 334,712 330,768 L 338,770 C 344,714 352,660 360,616 Z", SKIN_SH, None)
    lower += f'<g transform="translate(314 772)">{hand_svg}</g>'
    if with_stick:
        lower = stick() + lower
    sleeve = p("M 340,400 C 314,416 300,470 296,566 C 322,580 362,582 384,570 C 386,512 384,452 376,408 Z", SHIRT)
    sleeve += line("M 300,550 Q 340,564 382,554", SHIRT_SH, 3)
    return rot(up, 350, 420, upper + rot(fore, 338, 612, lower) + sleeve)


def right_arm(pose):
    """His right arm (viewer's left): holds the walking stick."""
    return arm(pose.get("r_up", 0), pose.get("r_fore", 0), fist(), True)


def left_arm(pose):
    """His left arm (viewer's right), free for gestures: the right arm mirrored."""
    h = f'<g transform="scale(-1 1)">{hand(pose.get("l_hand", "rest"))}</g>'
    return f'<g transform="matrix(-1 0 0 1 1000 0)">{arm(-pose.get("l_up", 0), -pose.get("l_fore", 0), h, False)}</g>'


def towel():
    d = "M 568,384 C 600,378 640,384 662,402 C 668,520 668,640 664,770 L 590,774 C 594,640 590,500 568,384 Z"
    g = p(d, TOWEL)
    g += p("M 640,392 C 655,398 662,404 664,420 C 664,540 664,650 662,770 L 646,771 C 650,640 650,520 640,392 Z", TOWEL_SH, None)
    g += line("M 600,420 Q 610,560 606,700", TOWEL_HI, 4)
    for y in (712, 726, 740):
        g += line(f"M {591},{y} L {663},{y-2}", "#f4f8ee", 5)
    for i in range(9):
        x = 594 + i * 8.5
        g += line(f"M {x:.1f},{772} L {x+1:.1f},{798}", TOWEL_SH, 4)
    return g


def body(pose):
    g = []
    # veshti
    g.append(p("M 332,856 L 668,856 C 680,1100 690,1480 704,1748 L 296,1748 C 310,1480 320,1100 332,856 Z", VESHTI))
    g.append(p("M 600,860 C 640,1100 660,1450 704,1748 L 640,1748 C 620,1450 600,1150 580,860 Z", VESHTI_SH, None))
    g.append(line("M 452,870 C 448,1150 436,1450 428,1744", BORDER, 7) + line("M 470,870 C 468,1150 460,1450 456,1744", VESHTI_SH, 3))
    g.append(p("M 298,1718 L 702,1718 L 704,1748 L 296,1748 Z", BORDER, OUT, 3))
    # feet in slippers
    for cx in (440, 566):
        g.append(f'<ellipse cx="{cx}" cy="1786" rx="58" ry="16" fill="{SLIPPER_SH}" stroke="{OUT}" stroke-width="{W}"/>')
        g.append(p(f"M {cx-40},1782 C {cx-42},1755 {cx+40},1755 {cx+42},1782 Z", SKIN))
        g.append(p(f"M {cx-34},1770 C {cx-10},1758 {cx+10},1758 {cx+34},1770 L {cx+30},1782 L {cx-30},1782 Z", SLIPPER))
    # neck
    g.append(p("M 468,320 L 532,320 L 536,392 L 464,392 Z", SKIN_SH))
    # shirt
    g.append(p("M 342,404 C 380,384 430,374 468,370 L 532,370 C 570,374 620,384 658,404 C 674,470 680,620 672,700 "
               "L 682,882 C 600,898 400,898 318,882 L 328,700 C 320,620 326,470 342,404 Z", SHIRT))
    g.append(p("M 610,392 C 640,400 658,404 658,404 C 674,470 680,620 672,700 L 682,882 C 660,886 640,889 620,890 "
               "C 630,700 628,520 610,392 Z", SHIRT_SH, None))
    g.append(line("M 500,392 L 500,890", SHIRT_SH, 3))
    for y in (440, 510, 580, 650, 720, 790, 860):
        g.append(f'<circle cx="508" cy="{y}" r="6" fill="#fffaf0" stroke="{OUT}" stroke-width="2.5"/>')
    g.append(p("M 528,470 L 588,470 L 588,540 C 570,548 546,548 528,540 Z", SHIRT, OUT, 3))
    # collar
    g.append(p("M 468,366 L 428,394 L 472,436 L 500,394 Z", SHIRT, OUT, 3.5)
             + p("M 532,366 L 572,394 L 528,436 L 500,394 Z", SHIRT, OUT, 3.5))
    return "".join(g)


def thatha(pose=None):
    pose = pose or {}
    l_front = pose.get("l_hand", "rest") != "rest"
    parts = []
    if not l_front:
        parts.append(left_arm(pose))
    parts += [body(pose), towel()]
    if l_front:
        parts.append(left_arm(pose))
    parts += [right_arm(pose), f'<g transform="translate(500 336) scale(1.12) translate(-500 -336)">{head(pose)}</g>']
    return rot(pose.get("body", 0), 500, 1790, "".join(parts))


# ------------------------------------------------------------------ scene

SW, SH, HORIZON = 2160, 3840, 1520
VP = (1080, 1320)


def palm(x, y, s, lean):
    g = line(f"M {x},{y} C {x+lean*0.3},{y-200*s} {x+lean*0.7},{y-330*s} {x+lean},{y-420*s}", "#7a5432", 18 * s)
    tx, ty = x + lean, y - 420 * s
    for a in (-160, -125, -90, -55, -20, 15, 200):
        r = math.radians(a)
        ex, ey = tx + math.cos(r) * 150 * s, ty + math.sin(r) * 80 * s + 50 * s
        mx, my = tx + math.cos(r) * 80 * s, ty + math.sin(r) * 60 * s - 30 * s
        g += line(f"M {tx},{ty} Q {mx:.0f},{my:.0f} {ex:.0f},{ey:.0f}", "#3f8a3a", 16 * s)
    return g


def neem(x, y):
    g = p(f"M {x-40},{y} C {x-30},{y-200} {x-50},{y-380} {x-120},{y-560} L {x-60},{y-580} C {x},{y-420} {x+10},{y-300} "
          f"{x+60},{y-480} L {x+110},{y-470} C {x+40},{y-300} {x+40},{y-150} {x+50},{y} Z", "#7a5130", OUT, 6)
    blobs = [(-260, -700, 230), (-40, -760, 250), (180, -680, 210), (-330, -500, 170), (60, -560, 190),
             (-150, -560, 200), (260, -520, 150), (-420, -680, 150)]
    for dx, dy, r in blobs:
        g += f'<circle cx="{x+dx}" cy="{y+dy}" r="{r}" fill="#4f9440" stroke="{OUT}" stroke-width="6"/>'
    for dx, dy, r in blobs:
        g += f'<circle cx="{x+dx-r*0.25:.0f}" cy="{y+dy-r*0.3:.0f}" r="{r*0.55:.0f}" fill="#69ad4f"/>'
    return g


def well(x, y):
    g = p(f"M {x-150},{y} L {x-150},{y+130} C {x-150},{y+175} {x+150},{y+175} {x+150},{y+130} L {x+150},{y} Z", "#b8a99a", OUT, 5)
    g += f'<ellipse cx="{x}" cy="{y}" rx="150" ry="40" fill="#cfc2b4" stroke="{OUT}" stroke-width="5"/>'
    g += f'<ellipse cx="{x}" cy="{y}" rx="118" ry="27" fill="#3c3530"/>'
    for i, yy in enumerate((y + 45, y + 90, y + 135)):
        for k in range(5):
            xx = x - 150 + k * 60 + (30 if i % 2 else 0)
            g += line(f"M {xx},{yy-40} L {xx},{yy}", "#8f8070", 3)
        g += line(f"M {x-150},{yy} L {x+150},{yy}", "#8f8070", 3)
    g += p(f"M {x-130},{y-10} L {x-118},{y-230} L {x-98},{y-230} L {x-104},{y-10} Z", "#7a5130", OUT, 4)
    g += p(f"M {x+130},{y-10} L {x+118},{y-230} L {x+98},{y-230} L {x+104},{y-10} Z", "#7a5130", OUT, 4)
    g += p(f"M {x-135},{y-240} L {x+135},{y-240} L {x+135},{y-218} L {x-135},{y-218} Z", "#6a4422", OUT, 4)
    g += f'<circle cx="{x}" cy="{y-200}" r="20" fill="#9a9590" stroke="{OUT}" stroke-width="4"/>'
    g += line(f"M {x},{y-180} L {x},{y-40}", "#5c4a3a", 3)
    return g


def shed(x, y):
    g = p(f"M {x},{y} L {x+240},{y} L {x+240},{y-170} L {x},{y-170} Z", "#ead9b6", OUT, 5)
    g += p(f"M {x-30},{y-160} L {x+120},{y-260} L {x+270},{y-160} Z", "#c2603a", OUT, 5)
    for k in range(1, 6):
        g += line(f"M {x-30+k*50},{y-160} L {x+120},{y-258}", "#9e4a2a", 3)
    g += p(f"M {x+90},{y} L {x+90},{y-100} L {x+150},{y-100} L {x+150},{y} Z", "#7a5130", OUT, 4)
    return g


def scene():
    g = ['<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">'
         '<stop offset="0" stop-color="#7cc4ec"/><stop offset="0.55" stop-color="#b9e0f2"/>'
         '<stop offset="1" stop-color="#ffe2b3"/></linearGradient>'
         '<radialGradient id="sun"><stop offset="0" stop-color="#fff6d2"/><stop offset="0.35" stop-color="#ffe9a8" stop-opacity="0.9"/>'
         '<stop offset="1" stop-color="#ffe9a8" stop-opacity="0"/></radialGradient></defs>']
    g.append(f'<rect width="{SW}" height="{HORIZON+40}" fill="url(#sky)"/>')
    g.append(f'<circle cx="1620" cy="1300" r="330" fill="url(#sun)"/><circle cx="1620" cy="1300" r="80" fill="#fff4cf"/>')
    for cx, cy, s in ((420, 520, 1.0), (1500, 380, 1.2), (980, 820, 0.8), (1950, 760, 0.7)):
        g.append(f'<g transform="translate({cx} {cy}) scale({s})"><path d="M -160,40 C -170,-10 -110,-40 -70,-20 '
                 f'C -50,-80 40,-90 70,-30 C 110,-60 180,-30 170,30 C 175,55 150,60 120,60 L -130,60 C -155,60 -165,55 -160,40 Z" '
                 f'fill="#ffffff" opacity="0.9"/></g>')
    # Arunachala: broad hill with a soft peak, hazy blue
    g.append(p("M 560,1530 C 760,1420 980,1240 1240,1110 C 1290,1085 1330,1085 1380,1112 C 1600,1230 1830,1420 2060,1530 Z",
               "#8c95c9", "#6f78ad", 4))
    g.append(p("M 1240,1110 C 1290,1085 1330,1085 1380,1112 C 1420,1150 1440,1240 1420,1330 C 1360,1240 1300,1180 1240,1110 Z", "#a3abd8", None))
    g.append(p("M -40,1530 C 160,1430 360,1390 600,1440 C 760,1470 820,1500 880,1530 Z", "#9aa3cf", "#7d86b8", 4))
    # distant tree line
    for i in range(30):
        x = -40 + i * 76
        r = 46 + (i * 37 % 23)
        g.append(f'<circle cx="{x}" cy="{1500 - (i*53 % 30)}" r="{r}" fill="#5c9a48" stroke="#3f7334" stroke-width="3"/>')
    g.append(f'<rect x="0" y="1500" width="{SW}" height="40" fill="#6aa84f"/>')
    # field with furrows converging to the vanishing point
    g.append(f'<rect x="0" y="{HORIZON}" width="{SW}" height="{SH-HORIZON}" fill="#b4532a"/>')
    furrows = []
    for i in range(-24, 25):
        xb, xn = VP[0] + i * 300, VP[0] + i * 300 + 130
        t = (HORIZON - VP[1]) / (SH - VP[1])
        xt, xtn = VP[0] + (xb - VP[0]) * t, VP[0] + (xn - VP[0]) * t
        furrows.append(f'<path d="M {xt:.0f},{HORIZON} L {xtn:.0f},{HORIZON} L {xn:.0f},{SH} L {xb:.0f},{SH} Z" fill="#c9643a"/>')
        furrows.append(line(f"M {xt:.0f},{HORIZON} L {xb:.0f},{SH}", "#93401f", 6))
    g.append(f'<clipPath id="field"><rect x="0" y="{HORIZON}" width="{SW}" height="{SH-HORIZON}"/></clipPath>'
             f'<g clip-path="url(#field)">{"".join(furrows)}</g>')
    g.append(f'<defs><linearGradient id="haze" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f3c9a0" stop-opacity="0.45"/>'
             f'<stop offset="1" stop-color="#f3c9a0" stop-opacity="0"/></linearGradient></defs>'
             f'<rect x="0" y="{HORIZON}" width="{SW}" height="700" fill="url(#haze)"/>')
    # grass strip at the field edge
    for i in range(70):
        x = i * 32
        g.append(line(f"M {x},{HORIZON+18} L {x+8},{HORIZON-8} M {x+12},{HORIZON+18} L {x+22},{HORIZON-2}", "#5d9c45", 6))
    g.append(palm(1850, 1560, 1.25, 60) + palm(2010, 1580, 1.05, -50) + palm(600, 1545, 0.9, 40))
    g.append(shed(1700, 1640) + well(1560, 1700))
    g.append(neem(330, 1760))
    # a few clods and tufts in the foreground
    for x, y, r in ((300, 3400, 40), (1850, 3300, 34), (700, 3700, 30), (1500, 3650, 44), (1950, 3750, 30)):
        g.append(f'<ellipse cx="{x}" cy="{y}" rx="{r}" ry="{r*0.55:.0f}" fill="#a14823" stroke="{OUT}" stroke-width="4"/>')
    return "".join(g)


# ------------------------------------------------------------------ frame

def frame(cam, pose=None, char_at=(1080, 3330, 1.0), scene_svg=None):
    """cam = (centre x, centre y, height) on the stage; returns a 1080x1920 SVG."""
    cx, cy, h = cam
    w = h * 1080 / 1920
    fx, fy, s = char_at
    char = f'<g transform="translate({fx - 500*s:.1f} {fy - 1790*s:.1f}) scale({s})">{thatha(pose)}</g>'
    shadow = f'<ellipse cx="{fx}" cy="{fy}" rx="{300*s:.0f}" ry="{40*s:.0f}" fill="#5a230e" opacity="0.35"/>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" '
            f'viewBox="{cx - w/2:.1f} {cy - h/2:.1f} {w:.1f} {h:.1f}">{scene_svg or scene()}{shadow}{char}</svg>')
