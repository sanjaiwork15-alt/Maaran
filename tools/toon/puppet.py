"""2D Maaran Thatha puppet built from the owner's character art (assets/2d), animated in code.

The art is cut into layers once (build_rig) and moved per frame (render):
  body   : the full figure minus head and left arm (stick hand stays on the body)
  head   : hair, face, ears, beard; tilts around the neck. Eyes blink (painted lids),
           brows lift (moved patches over an inpainted forehead), mouth opens per
           Rhubarb shape (drawn under the moustache)
  arm    : his left arm below the sleeve hem; swings, or is swapped for a hand-sheet
           sprite (wave / point / palm up / thumbs up) pinned at the same hem
Coordinates below are in 01_front.png source pixels; the upscaled art (assets/2d/up,
2x) is used when present.

Pose keys: mouth, blink (0..1), brow (0..1), head (deg), body (deg), arm (deg swing),
hand ("rest" | "wave" | "point" | "palm" | "thumb"), hand_rot (deg extra for the sprite).
"""
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "assets/2d"

NECK = (505, 362)                   # head pivot (chin/collar)
HEAD_POLY = [(320, 0), (710, 0), (710, 250), (650, 300), (610, 336), (565, 366), (505, 384),
             (445, 366), (402, 336), (362, 300), (320, 250)]
EYES = [(461, 190, 25, 17), (543, 186, 25, 17)]       # cx, cy, rx, ry
BROWS = [(392, 128, 488, 166), (512, 122, 600, 158)]  # boxes holding the white brows
MOUTH = (514, 272)                  # top centre of the lips, just under the moustache
HEM = (752, 598)                    # left-arm pivot at the sleeve hem (whole-arm swing)
ARM_POLY = [(714, 600), (735, 590), (800, 584), (836, 640), (840, 1050), (724, 1050), (724, 880), (716, 700)]
FEET_Y = 1500                       # where the slippers touch the ground

ELBOW = (777, 752)                  # left elbow: gesture forearms bend here
# Hand-sheet gesture forearms (03_hands.png source px): crop box, elbow point inside the crop,
# scale to the body, angle (deg, PIL) that swings the forearm down to hang from the elbow,
# and whether the sprite's own upper arm (above the elbow) must be cut away.
SPRITES = {
    "wave": ((40, 20, 420, 650), (125, 565), 0.40, -170, False),
    "point": ((420, 15, 730, 660), (110, 580), 0.40, -170, False),
    "palm": ((1285, 30, 1770, 570), (60, 350), 0.47, -80, True),
    "thumb": ((1775, 30, 2150, 550), (65, 380), 0.47, -80, True),
}
MOUTHS = {"X": (0, 0), "A": (0, 0), "B": (26, 8), "C": (30, 15), "D": (34, 24), "E": (24, 17),
          "F": (16, 12), "G": (28, 9), "H": (30, 16)}
LIP, MOUTH_IN, TEETH, TONGUE, LASH = (186, 92, 52), (74, 24, 20), (250, 244, 232), (196, 84, 76), (52, 26, 14)


def load(name):
    up, src = ART / "up" / f"{name}.png", ART / "source" / f"{name}.png"
    return (Image.open(up), 2) if up.exists() else (Image.open(src), 1)


def cut_white(img, thresh=238):
    from scipy import ndimage
    a = np.asarray(img.convert("RGB")).astype(np.int16)
    white = (a.min(axis=2) >= thresh) & (a.max(axis=2) - a.min(axis=2) <= 14)
    lab, _ = ndimage.label(white)
    border = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    bg = ndimage.binary_opening(np.isin(lab, border[border > 0]), iterations=1)
    alpha = ndimage.gaussian_filter((~bg).astype(np.float32), 0.8)
    out = img.convert("RGBA")
    out.putalpha(Image.fromarray((alpha * 255).astype(np.uint8)))
    return out


def place(canvas, im, x, y):
    """alpha_composite that allows the layer to hang off the canvas edges."""
    x, y = round(x), round(y)
    l, t = max(0, -x), max(0, -y)
    r, b = min(im.width, canvas.width - x), min(im.height, canvas.height - y)
    if r > l and b > t:
        canvas.alpha_composite(im.crop((l, t, r, b)), (x + l, y + t))


def poly_mask(size, poly, k):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).polygon([(x * k, y * k) for x, y in poly], fill=255)
    return m


class Rig:
    def __init__(self):
        img, k = load("01_front")
        self.k = k
        full = cut_white(img)
        a = full.getchannel("A")
        hm = Image.fromarray(np.minimum(np.asarray(poly_mask(full.size, HEAD_POLY, k)), np.asarray(a)))
        am = Image.fromarray(np.minimum(np.asarray(poly_mask(full.size, ARM_POLY, k)), np.asarray(a)))
        self.head = full.copy(); self.head.putalpha(hm)
        self.arm = full.copy(); self.arm.putalpha(am)
        split = np.zeros((full.height, full.width), np.uint8)
        split[: ELBOW[1] * k] = 255
        self.upper_arm = full.copy()
        self.upper_arm.putalpha(Image.fromarray(np.minimum(np.asarray(am), split)))
        rest = np.asarray(a).astype(np.int16) - np.asarray(hm) - np.asarray(am)
        self.body = full.copy(); self.body.putalpha(Image.fromarray(np.clip(rest, 0, 255).astype(np.uint8)))
        # a dark neck patch under the head so a small tilt never shows a gap
        neck = Image.new("RGBA", full.size, (0, 0, 0, 0))
        ImageDraw.Draw(neck).ellipse([(440 * k, 300 * k), (570 * k, 395 * k)], fill=(120, 60, 30, 255))
        neck.alpha_composite(self.body)
        self.body = neck
        # brows: lift them out and inpaint the forehead underneath
        rgb = np.asarray(self.head.convert("RGB")).copy()
        bmask = np.zeros(rgb.shape[:2], np.uint8)
        self.brows = []
        for x0, y0, x1, y1 in BROWS:
            box = (x0 * k, y0 * k, x1 * k, y1 * k)
            reg = rgb[box[1]:box[3], box[0]:box[2]].astype(np.int16)
            m = ((reg.min(axis=2) > 175) & (reg.max(axis=2) - reg.min(axis=2) < 60)).astype(np.uint8) * 255
            m = cv2.dilate(m, np.ones((3, 3), np.uint8), iterations=2 * k)
            bmask[box[1]:box[3], box[0]:box[2]] = m
            patch = self.head.crop(box)
            pa = np.minimum(np.asarray(patch.getchannel("A")), cv2.GaussianBlur(m, (9, 9), 0))
            patch.putalpha(Image.fromarray(pa))
            self.brows.append((patch, box[:2]))
        filled = cv2.inpaint(rgb, bmask, 6 * k, cv2.INPAINT_TELEA)
        base = Image.fromarray(filled).convert("RGBA")
        base.putalpha(self.head.getchannel("A"))
        self.head_base = base
        # closed eyes: fill each eye from the surrounding skin, keeping the art's shading
        emask = np.zeros(filled.shape[:2], np.uint8)
        for cx, cy, rx, ry in EYES:
            cv2.ellipse(emask, (cx * k, cy * k), ((rx + 4) * k, (ry + 5) * k), 0, 0, 360, 255, -1)
        closed = Image.fromarray(cv2.inpaint(filled, emask, 9 * k, cv2.INPAINT_TELEA)).convert("RGBA")
        closed.putalpha(self.head.getchannel("A"))
        self.head_closed = closed
        self.lip = tuple(int(c) for c in np.median(rgb[(MOUTH[1] + 10) * k:(MOUTH[1] + 16) * k, (MOUTH[0] - 20) * k:(MOUTH[0] + 20) * k]
                                                   .reshape(-1, 3), axis=0))
        self._mouths = {}
        # gesture forearms from the hand sheet: drop the sheet's shirt cuff (and, for the
        # sideways arms, its upper arm) so only forearm + hand remain, pinned at the elbow
        sheet, ks = load("03_hands")
        sheet = cut_white(sheet)
        self.sprites = {}
        for name, (box, elbow, scale, down, cut_upper) in SPRITES.items():
            crop = sheet.crop(tuple(v * ks for v in box))
            px = np.asarray(crop).astype(np.int16)
            r, g, b_, al = px[..., 0], px[..., 1], px[..., 2], px[..., 3]
            cream = (r > 195) & (g > 180) & (b_ > 135) & (r - b_ < 95)
            skin = (r - b_ > 110) & (al > 0)
            near_cream = cv2.dilate(cream.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=5 * ks) > 0
            near_skin = cv2.dilate(skin.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=2 * ks) > 0
            drop = cream | (near_cream & ~near_skin)
            if cut_upper:
                drop[: (elbow[1] - 30) * ks] = True
            alpha = np.where(drop, 0, al).astype(np.uint8)
            crop.putalpha(Image.fromarray(cv2.GaussianBlur(alpha, (3, 3), 0)))
            f = scale * k / ks
            crop = crop.resize((round(crop.width * f), round(crop.height * f)), Image.LANCZOS)
            self.sprites[name] = (crop, (elbow[0] * ks * f, elbow[1] * ks * f), down)

    # ------------------------------------------------------------- face
    def face(self, pose):
        k = self.k
        h = self.head_base.copy()
        lift = int(round(pose.get("brow", 0) * 7 * k))
        for patch, (x, y) in self.brows:
            h.alpha_composite(patch, (x, y - lift))
        d = ImageDraw.Draw(h)
        b = pose.get("blink", 0)
        if b > 0.05:
            for cx, cy, rx, ry in EYES:
                cx, cy, rx, ry = cx * k, cy * k, (rx + 4) * k, (ry + 5) * k
                y_lid = cy - ry + 2 * ry * min(b, 1) * (0.82 if b < 0.95 else 1.0)
                lid = Image.new("L", h.size, 0)
                dl = ImageDraw.Draw(lid)
                dl.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255)
                if b < 0.95:
                    dl.rectangle([0, y_lid, h.width, h.height], fill=0)
                h.paste(self.head_closed, (0, 0), lid.filter(ImageFilter.GaussianBlur(1.5 * k)))
                if b >= 0.95:   # closed: a soft downward-curved lash line
                    d.arc([cx - rx * 0.85, cy - ry * 0.75, cx + rx * 0.85, cy + ry * 0.55], 20, 160, fill=LASH, width=max(3, 3 * k))
                else:
                    half = rx * 0.62 * math.sqrt(max(0.0, 1 - ((y_lid - cy) / ry) ** 2))
                    d.line([(cx - half, y_lid), (cx + half, y_lid)], fill=LASH, width=max(3, 3 * k))
        hw, op = MOUTHS.get(pose.get("mouth", "X"), (0, 0))
        if op:
            m = self.mouth_img(hw, op)
            h.alpha_composite(m, (round(MOUTH[0] * k - m.width / 2), round(MOUTH[1] * k - 6 * k)))
        return h

    def mouth_img(self, hw, op):
        """A soft, shaded open mouth (drawn 4x larger, then reduced), hw/op in source px."""
        key = (hw, op)
        if key in self._mouths:
            return self._mouths[key]
        k, ss = self.k, 4
        W, H = (2 * hw + 20) * k * ss, (op + 26) * k * ss
        u = k * ss
        cx, top = W / 2, 6 * u
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        # lips
        d.ellipse([cx - (hw + 3) * u, top - u, cx + (hw + 3) * u, top + (op + 6) * u], fill=tuple(int(c * 0.86) for c in self.lip) + (255,))
        # inside: darker towards the top
        inside = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        di = ImageDraw.Draw(inside)
        for i in range(12):
            t = i / 11
            col = tuple(int(a + (b - a) * t) for a, b in zip((58, 16, 12), (112, 40, 32)))
            di.rectangle([0, top + op * u * t, W, H], fill=col + (255,))
        di.rounded_rectangle([cx - hw * u, top - 2 * u, cx + hw * u, top + min(op * 0.38, 7) * u], radius=3 * u, fill=(246, 238, 224, 255))
        di.line([(cx - hw * u, top + min(op * 0.38, 7) * u), (cx + hw * u, top + min(op * 0.38, 7) * u)], fill=(205, 190, 172, 255), width=u)
        if op > 12:
            di.ellipse([cx - hw * 0.6 * u, top + op * 0.6 * u, cx + hw * 0.6 * u, top + op * 1.35 * u], fill=(200, 92, 82, 255))
        clip = Image.new("L", (W, H), 0)
        ImageDraw.Draw(clip).ellipse([cx - hw * u, top, cx + hw * u, top + op * u], fill=255)
        img.paste(inside, (0, 0), clip)
        # lower-lip highlight
        d.arc([cx - hw * 0.7 * u, top + (op + 1) * u, cx + hw * 0.7 * u, top + (op + 6) * u], 20, 160, fill=(232, 150, 108, 200), width=2 * u)
        img = img.resize((W // ss, H // ss), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.6 * k))
        self._mouths[key] = img
        return img

    # ------------------------------------------------------------- figure
    def figure(self, pose):
        """The posed character on a transparent canvas the size of 01_front (x k)."""
        k = self.k
        canvas = self.body.copy()
        hand = pose.get("hand", "rest")
        if hand == "rest":
            arm = self.arm.rotate(pose.get("arm", 0), resample=Image.BICUBIC, center=(HEM[0] * k, HEM[1] * k))
            canvas.alpha_composite(arm)
        else:
            canvas.alpha_composite(self.upper_arm)
            sp, (hx, hy), _ = self.sprites[hand]
            pad = max(sp.size)
            big = Image.new("RGBA", (sp.width + 2 * pad, sp.height + 2 * pad), (0, 0, 0, 0))
            big.alpha_composite(sp, (pad, pad))
            big = big.rotate(pose.get("hand_rot", 0), resample=Image.BICUBIC, center=(hx + pad, hy + pad))
            place(canvas, big, ELBOW[0] * k - hx - pad, ELBOW[1] * k - hy - pad)
        head = self.face(pose).rotate(pose.get("head", 0), resample=Image.BICUBIC, center=(NECK[0] * k, NECK[1] * k))
        canvas.alpha_composite(head)
        if pose.get("body"):
            canvas = canvas.rotate(pose["body"], resample=Image.BICUBIC, center=(canvas.width / 2, FEET_Y * k))
        return canvas


class Stage:
    """Background + character placement; cam = (cx, cy, h) in the background's source pixels."""

    def __init__(self, bg="05_field_vertical", feet=(0.50, 0.90), height=0.74):
        self.bg, self.kb = load(bg)
        self.bg = self.bg.convert("RGB")
        self.feet = (feet[0] * self.bg.width, feet[1] * self.bg.height)
        self.char_h = height * self.bg.height

    def frame(self, rig, pose, cam, out=(1080, 1920)):
        fig = rig.figure(pose)
        s = self.char_h / (FEET_Y * rig.k)
        cx, cy, h = (v * self.kb for v in cam)
        w = h * out[0] / out[1]
        z = out[1] / h
        # background crop
        img = self.bg.transform(out, Image.AFFINE, (1 / z, 0, cx - w / 2, 0, 1 / z, cy - h / 2), resample=Image.BICUBIC)
        img = img.convert("RGBA")
        # character: figure px -> bg px (scale s, feet anchored) -> frame px
        fz = s * z
        fx = (self.feet[0] - fig.width / 2 * s - (cx - w / 2)) * z
        fy = (self.feet[1] - FEET_Y * rig.k * s - (cy - h / 2)) * z
        small = fig.resize((max(1, round(fig.width * fz)), max(1, round(fig.height * fz))), Image.LANCZOS)
        shadow = Image.new("RGBA", out, (0, 0, 0, 0))
        sx, sy, sw = (self.feet[0] - (cx - w / 2)) * z, (self.feet[1] - (cy - h / 2)) * z, 330 * s * rig.k * z
        ImageDraw.Draw(shadow).ellipse([sx - sw, sy - sw * 0.12, sx + sw, sy + sw * 0.1], fill=(60, 25, 10, 90))
        img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(8)))
        place(img, small, fx, fy)
        return img.convert("RGB")
