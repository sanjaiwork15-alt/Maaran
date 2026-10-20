"""Ep 3 start frames without a GPU (see ../../ep02/final/make_frames.py for the method).

Run with the f5 env:  python -I make_frames.py
f_kon:  the Ep 2 kitchen pose (Thatha layers saved by Ep 2) holding a small kitchen knife and a cut red onion half.
f_kpod: Groundnut Ep 9's f_pod_s3 (arm raised, big smile) – the groundnut pod inpainted away, an onion half drawn in
        his raised hand – on the kitchen plate mirrored (stove on the other side: a different corner of the kitchen).
"""
import io
import json
import sys
from pathlib import Path

import cairosvg
import numpy as np
import torch
from PIL import Image, ImageFilter, ImageOps
from rembg import new_session, remove
from scipy.ndimage import binary_fill_holes, label

_jl = torch.jit.load
torch.jit.load = lambda p, *a, **k: _jl(p, map_location="cpu")
from simple_lama_inpainting import SimpleLama  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tools/toon"))
from onion import knife, onion_half  # noqa: E402

EP2 = ROOT / "series/02-thatha-oru-doubt/ep02/final/frames"
POD = ROOT / "series/01-groundnut/ep09/final/frames/f_pod_s3.png"
FR = HERE / "frames"
K2, DX2, DY2 = 0.94, 45, 1280 * 0.06          # Ep 2 placement of the f_two layers
PK, PDX, PDY = 1.0, -40, 0                      # f_pod placement on the mirrored plate


def svg_layer(body):
    return Image.open(io.BytesIO(cairosvg.svg2png(
        bytestring=f'<svg xmlns="http://www.w3.org/2000/svg" width="720" height="1280">{body}</svg>'.encode())))


def grow(m, k):
    return np.array(Image.fromarray(m.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(k))) > 0


def main():
    plate = Image.open(EP2 / "kitchen_plate.png").convert("RGBA")
    # --- f_kon
    body, fingers = Image.open(EP2 / "body_two.png"), Image.open(EP2 / "fingers_two.png")
    out = plate.copy()
    out.alpha_composite(body, (int(DX2), int(DY2)))
    rx, ry = 98 * K2 + DX2, 527 * K2 + DY2      # his right fist (image left)
    lx, ly = 602 * K2 + DX2, 530 * K2 + DY2     # his left fist (image right)
    out.alpha_composite(svg_layer(knife(rx + 2, ry - 18, 0.95, -6) + onion_half(lx - 4, ly - 52, 52, 8)))
    out.alpha_composite(fingers, (int(DX2), int(DY2)))
    out.convert("RGB").save(FR / "f_kon.png")
    print("saved f_kon")

    # --- f_kpod
    lama = SimpleLama(device=torch.device("cpu"))
    seg = new_session("isnet-anime")
    src = Image.open(POD).convert("RGB")
    a = np.array(src)
    h = np.array(src.convert("HSV")).astype(int)
    H_, S_, V_ = h[..., 0] * 180 // 255, h[..., 1], h[..., 2]
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
    skin = (H_ >= 4) & (H_ <= 16) & (S_ > 100) & (V_ > 90)          # fingers hue 13-14 (the pod is 16-18)
    capsule = ((xx - 590) / 50) ** 2 + ((yy - 197) / 110) ** 2 < 1    # the pod, by shape
    fzone = (xx > 601) & (yy > 203) & (yy < 335) & (xx < 672)        # his fingers wrap the pod's right side
    fing = fzone & (skin | ((V_ < 90) & grow(skin, 7)))
    holes, n = label(binary_fill_holes(fing) & ~fing)
    sizes = np.bincount(holes.ravel())
    fing |= np.isin(holes, [i for i in range(1, n + 1) if sizes[i] < 90])   # fingernails only, not pod bits
    pod = grow(capsule, 7) & ~fing
    clean = lama(src, Image.fromarray(pod.astype(np.uint8) * 255)).resize(src.size)
    alpha = np.array(remove(clean, session=seg, only_mask=True))
    alpha[alpha < 170] = 0
    alpha[grow(capsule, 7) & (yy < 215) & ~fing] = 0                 # sky where the pod stood above his hand
    fing &= alpha > 0
    body_p = Image.fromarray(np.dstack([np.array(clean), alpha]))
    fing_p = Image.fromarray(np.dstack([a, (fing * 255).astype(np.uint8)]))
    body_p.save(FR / "body_pod.png")              # reusable layers (unscaled, f_pod_s3 coordinates)
    fing_p.save(FR / "fingers_pod.png")
    out = ImageOps.mirror(plate.convert("RGB")).convert("RGBA")
    out.alpha_composite(body_p, (PDX, PDY))
    out.alpha_composite(svg_layer(onion_half(586 + PDX, 212 + PDY, 72, -10)))
    out.alpha_composite(fing_p, (PDX, PDY))
    out.convert("RGB").save(FR / "f_kpod.png")
    print("saved f_kpod")
    json.dump({"f_kon": [K2, DX2, DY2], "f_kpod": [PK, PDX, PDY]}, open(FR / "xf.json", "w"))


if __name__ == "__main__":
    main()
