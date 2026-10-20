"""Ep 2 start frames without a GPU: Thatha (approved Ep 1 frame f_two_s3) moved into the village kitchen, the bananas
in his hands replaced by code-drawn coriander bunches.

Run with the f5 env (torch, rembg, simple-lama-inpainting):
    python -I make_frames.py
1. Bananas out of f_two_s3 (hue mask in the two hand boxes) -> LaMa inpaint (CPU) fills his shirt/arms behind them.
2. rembg (isnet-anime) cuts Thatha out; LaMa also removed the Ep 10 Thatha from the kitchen -> kitchen_plate.png.
3. Plate + Thatha + coriander bunch (tools/toon/coriander.py) + his fingers from the original frame on top.
Writes frames/f_kfw.png (fresh + wilted) and frames/f_kff.png (fresh + fresh), 720x1280, and frames/xf.json
(how rig points move: x' = x * k + dx, y' = y * k + dy).
"""
import json
import sys
from pathlib import Path

import cairosvg
import numpy as np
import torch
from scipy.ndimage import binary_fill_holes
from PIL import Image, ImageFilter
from rembg import new_session, remove

_jl = torch.jit.load
torch.jit.load = lambda p, *a, **k: _jl(p, map_location="cpu")     # the LaMa TorchScript was saved on CUDA
from simple_lama_inpainting import SimpleLama  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tools/toon"))
from coriander import bunch_svg  # noqa: E402

SRC = ROOT / "series/02-thatha-oru-doubt/ep01/final/frames/f_two_s3.png"
KIT = ROOT / "series/01-groundnut/ep10/final/frames/f_kitchen_s3.png"
FR = HERE / "frames"
BOXES = {"R": (40, 380, 250, 650, (26, 52)), "L": (452, 380, 640, 650, (20, 34))}   # x0,y0,x1,y1, banana hue range
FISTS = {"R": (98, 527), "L": (602, 530)}
TIPS = [(135, 510), (571, 508)]       # where the stems go through his fists (f_two_s3 coords)
K, DX, DY = 0.94, 45, 1280 * 0.06               # Thatha a little smaller and right of centre, the stove on the left


def hsv(img):
    return np.array(img.convert("HSV")).astype(int)


def main():
    lama = SimpleLama(device=torch.device("cpu"))
    seg = new_session("isnet-anime")
    src = Image.open(SRC).convert("RGB")
    a = np.array(src)
    h = hsv(src)
    H_, S_, V_ = h[..., 0] * 180 // 255, h[..., 1], h[..., 2]
    skin = (H_ >= 4) & (H_ <= 19) & (S_ > 115) & (V_ > 90) & (V_ < 248)   # sunset sky is cream: low saturation
    ban = np.zeros(a.shape[:2], bool)
    for x0, y0, x1, y1, (h0, h1) in BOXES.values():
        box = np.zeros_like(ban)
        box[y0:y1, x0:x1] = True
        ban |= box & (H_ >= h0) & (H_ <= h1) & (S_ > 90) & (V_ > 70)
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
    grow = lambda m, k: np.array(Image.fromarray(m.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(k))) > 0  # noqa: E731
    dark0 = V_ < 90
    ban_d = (grow(ban, 9) & ~skin) | (grow(ban, 21) & dark0 & ~grow(skin, 3))     # + the banana's dark tips/outline
    clean = lama(src, Image.fromarray(ban_d.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(3)))
    clean = clean.resize(src.size)
    clean.save(FR / "f_two_nobanana.png")
    alpha = np.array(remove(clean, session=seg, only_mask=True))
    # where a banana stood against the sky there is no body behind it: keep only the torso part (shirt, towel)
    alpha[alpha < 170] = 0                       # drop half-transparent background (the palm by his arm)
    torso = (yy > 548) & (xx > 140) & (xx < 545)
    alpha[ban_d & ~torso] = 0
    # sky left inside the silhouette between each raised fist and his body: keep only skin, towel green and outlines
    green = (H_ >= 35) & (H_ <= 85) & (S_ > 80)
    keep = skin | green | (V_ < 90)
    for x0, y0, x1, y1 in ((130, 430, 215, 565), (495, 430, 570, 565)):
        reg = np.zeros_like(keep)
        reg[y0:y1, x0:x1] = True
        alpha[reg & ~grow(keep, 3)] = 0
    alpha[(xx < 80) & (yy > 300) & ~grow(skin, 5)] = 0    # palm leaves beside his left-side arm
    alpha = Image.fromarray(alpha)

    kit = Image.open(KIT).convert("RGB")
    kmask = np.array(remove(kit, session=seg, only_mask=True)) > 237
    plate = lama(kit, Image.fromarray(kmask.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(15))).resize(kit.size)
    plate = plate.filter(ImageFilter.GaussianBlur(1.2))          # slight depth: the room a touch softer than Thatha
    plate.save(FR / "kitchen_plate.png")

    # fingers from the original frame (skin + their dark outlines), only around the fists
    dark = V_ < 80
    fing = np.zeros_like(ban)
    for (fx, fy) in FISTS.values():
        fing[fy - 60:fy + 55, fx - 75:fx + 75] = True
    near_skin = np.array(Image.fromarray(skin.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(7))) > 0
    fing &= (skin | (dark & near_skin)) & ~ban_d
    fing = binary_fill_holes(fing) & (np.array(alpha) > 0)   # the cream fingernails; only on his body
    for cx, cy in TIPS:                          # thumb tips that pressed on the banana: the stems cover them now
        fing &= (xx - cx) ** 2 + (yy - cy) ** 2 > 14 ** 2
    fing_rgba = np.dstack([a, (fing * 255).astype(np.uint8)])

    def place(img_rgba):
        w, hh = img_rgba.size
        return img_rgba.resize((round(w * K), round(hh * K)), Image.LANCZOS)

    body = place(Image.fromarray(np.dstack([np.array(clean), np.array(alpha)])))
    fingers = place(Image.fromarray(fing_rgba))
    body.save(FR / "body_two.png")                # reusable layers for later episodes (already scaled by K)
    fingers.save(FR / "fingers_two.png")
    for name, wilts in (("f_kfw", {"R": 0.0, "L": 1.0}), ("f_kff", {"R": 0.0, "L": 0.0})):
        out = plate.copy().convert("RGBA")
        out.alpha_composite(body, (int(DX), int(DY)))
        svg = "".join(bunch_svg(FISTS[s][0] * K + DX, FISTS[s][1] * K + DY, wilts[s], 1.0, seed=3 if s == "R" else 9,
                                n=14, height=230) for s in ("R", "L"))
        b = Image.open(__import__("io").BytesIO(cairosvg.svg2png(
            bytestring=f'<svg xmlns="http://www.w3.org/2000/svg" width="720" height="1280">{svg}</svg>'.encode())))
        out.alpha_composite(b)
        out.alpha_composite(fingers, (int(DX), int(DY)))
        out.convert("RGB").save(FR / f"{name}.png")
        print("saved", name)
    json.dump({"k": K, "dx": DX, "dy": DY}, open(FR / "xf.json", "w"))


if __name__ == "__main__":
    main()
