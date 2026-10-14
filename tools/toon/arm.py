"""Thatha's left arm as a smooth cut-out rig built from assets/2d/source/10_arm_parts.png.

Parts (sleeve + upper arm, forearm, four hands) bend at shoulder, elbow and wrist. Joints never
show a break: every joint end is rebuilt as a round end painted with the part's own skin and
shading (mirrored from just inside the end, which also hides the drawn flat end-caps), the
upper part's round end covers the lower part at any angle, and a dark ring under each joint
keeps the outline on the outside of a bend.

Angles are degrees counter-clockwise on screen: a1 at the shoulder, a2 at the elbow (relative
to the upper arm), a3 at the wrist (relative to the forearm).
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ART = Path(__file__).resolve().parents[2] / "assets/2d/source/10_arm_parts.png"
OUTLINE = (92, 46, 22, 255)

# Part boxes and joints in 10_arm_parts.png px. Joint = centre of the drawn end-cap.
PARTS = {
    "upper": ((77, 61, 350, 623), {"shoulder": (219, 452), "elbow": (221, 590)}, 129),
    "fore": ((419, 165, 573, 683), {"elbow": (484, 194), "wrist": (496, 652)}, 112),
    "rest": ((650, 325, 855, 688), {"wrist": (753, 347)}, 93),
    "wave": ((911, 223, 1220, 680), {"wrist": (1045, 653)}, 113),
    "point": ((1269, 235, 1474, 674), {"wrist": (1386, 648)}, 113),
    "palm": ((1571, 425, 1949, 674), {"wrist": (1744, 656)}, 98),
}
UP_HANDS = {"wave", "point", "palm"}     # drawn with the wrist at the bottom


def rot(v, deg):
    t = math.radians(deg)
    return (v[0] * math.cos(t) + v[1] * math.sin(t), -v[0] * math.sin(t) + v[1] * math.cos(t))


def round_end(rgba, joint, inward, r, cap):
    """Replace the end beyond `joint` with a round end of radius r, painted by mirroring the
    part from just inside (skips the flat end-cap drawn at the tip)."""
    h, w = rgba.shape[:2]
    jx, jy = joint[0] + inward[0] * cap, joint[1] + inward[1] * cap
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = (xx - jx) * inward[0] + (yy - jy) * inward[1]          # >0 inside the part
    out = rgba.copy()
    beyond = d < 0
    mx = np.clip(np.round(xx - 2 * d * inward[0]), 0, w - 1).astype(int)
    my = np.clip(np.round(yy - 2 * d * inward[1]), 0, h - 1).astype(int)
    out[beyond] = rgba[my[beyond], mx[beyond]]
    dist = np.hypot(xx - jx, yy - jy)
    disc = np.clip((r - dist) / 2.0, 0, 1)
    a = out[..., 3].astype(np.float32)
    out[..., 3] = np.where(beyond, a * disc, a).astype(np.uint8)
    return out, (jx, jy)


class Arm:
    def __init__(self, scale):
        sheet = np.asarray(Image.open(ART).convert("RGBA"))
        self.parts = {}
        for name, (box, joints, width) in PARTS.items():
            x0, y0, x1, y1 = box
            pad = width
            rgba = np.zeros((y1 - y0 + 2 * pad, x1 - x0 + 2 * pad, 4), np.uint8)
            rgba[pad:pad + y1 - y0, pad:pad + x1 - x0] = sheet[y0:y1, x0:x1]
            j = {k: (v[0] - x0 + pad, v[1] - y0 + pad) for k, v in joints.items()}
            r, cap = width / 2, width * 0.33
            if name == "upper":
                # keep only the bare arm: the body's own sleeve is drawn over its top
                px = rgba.astype(np.int16)
                cream = (px[..., 0] > 190) & (px[..., 1] > 175) & (px[..., 2] > 130) & (px[..., 0] - px[..., 2] < 100)
                ys = np.nonzero(cream.any(axis=1))[0]
                hem_y = int(np.percentile(np.nonzero(cream)[0], 98))   # lowest sleeve rows
                cut = np.zeros(cream.shape, bool)
                cut[: hem_y + 4] = True
                rgba[cut | cream, 3] = 0
                # extend the arm upwards under the sleeve so a turned arm never shows its top
                band = rgba[hem_y + 6:hem_y + 14].copy()
                for yy in range(max(0, hem_y - 60), hem_y + 6):
                    rgba[yy] = np.where(band[yy % len(band)][..., 3:4] > 0, band[yy % len(band)], rgba[yy])
                rgba, j["elbow"] = round_end(rgba, j["elbow"], (0, -1), r, cap)
            elif name == "fore":
                rgba, j["elbow"] = round_end(rgba, j["elbow"], (0, 1), r, cap)
                rgba, j["wrist"] = round_end(rgba, j["wrist"], (0, -1), r * 0.93, cap)
            elif name in UP_HANDS:
                rgba, j["wrist"] = round_end(rgba, j["wrist"], (0, -1), r * 0.9, cap)
            else:
                rgba, j["wrist"] = round_end(rgba, j["wrist"], (0, 1), r * 0.9, cap)
            img = Image.fromarray(rgba)
            img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
            self.parts[name] = (img, {k: (v[0] * scale, v[1] * scale) for k, v in j.items()}, width * scale / 2)

    def _put(self, layer, name, joint, angle, at):
        img, j, _ = self.parts[name]
        jx, jy = j[joint]
        pad = max(img.size)
        big = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
        big.alpha_composite(img, (pad, pad))
        big = big.rotate(angle, resample=Image.BICUBIC, center=(jx + pad, jy + pad))
        x, y = round(at[0] - jx - pad), round(at[1] - jy - pad)
        l, t = max(0, -x), max(0, -y)
        rr, bb = min(big.width, layer.width - x), min(big.height, layer.height - y)
        if rr > l and bb > t:
            layer.alpha_composite(big.crop((l, t, rr, bb)), (x + l, y + t))

    def draw(self, layer, shoulder_at, a1, a2, a3, hand="rest", sleeve=None, flip=None):
        """Arm parts + the body's own sleeve (drawn over the upper arm's top). A raised
        forearm goes in front of the sleeve; a lowered one hangs below it."""
        up, up_j, _ = self.parts["upper"]
        fo, fo_j, r_el = self.parts["fore"]
        _, h_j, r_wr = self.parts[hand]
        v = (up_j["elbow"][0] - up_j["shoulder"][0], up_j["elbow"][1] - up_j["shoulder"][1])
        e = rot(v, a1)
        elbow = (shoulder_at[0] + e[0], shoulder_at[1] + e[1])
        v = (fo_j["wrist"][0] - fo_j["elbow"][0], fo_j["wrist"][1] - fo_j["elbow"][1])
        w = rot(v, a1 + a2)
        wrist = (elbow[0] + w[0], elbow[1] + w[1])
        up_hand = hand in UP_HANDS if flip is None else flip
        hand_angle = a1 + a2 + a3 + (180 if up_hand else 0)
        raised = abs(a2) > 60
        d = ImageDraw.Draw(layer)
        for (cx, cy), r in ((elbow, r_el + 2.5), (wrist, r_wr * 0.9 + 2.5)):
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=OUTLINE)
        if not raised:
            self._put(layer, hand, "wrist", hand_angle, wrist)
            self._put(layer, "fore", "elbow", a1 + a2, elbow)
        self._put(layer, "upper", "shoulder", a1, shoulder_at)
        if sleeve is not None:
            layer.alpha_composite(sleeve)
        if raised:
            self._put(layer, "fore", "elbow", a1 + a2, elbow)
            self._put(layer, hand, "wrist", hand_angle, wrist)
        return elbow, wrist
