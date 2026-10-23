"""Upscale art 4x with Real-ESRGAN x4plus (BSD-3, commercial use OK) on CPU, tile by tile.

Usage:
    python tools/upscale.py IN.png OUT.png [--scale 2]

--scale is the final size factor (the model always works at 4x; the result is resized
down with Lanczos, which also smooths the upscaler's texture). Needs torch and spandrel.
Weights: Comfy-Org/Real-ESRGAN_repackaged on HuggingFace (downloaded once).
Guard: where the ESRGAN result strays far from a plain Lanczos upscale (it turned a near-invisible pattern on the
dhoti of the Ep 2/3 body layers into a grey smudge), the Lanczos pixels are used instead.
    python tools/upscale.py IN.png OUT.png --fix      # apply only the guard to an existing OUT.png (no ESRGAN run)
"""
import argparse

import cv2
import numpy as np
import torch
from huggingface_hub import hf_hub_download
from PIL import Image
from spandrel import ModelLoader


def guard(src, res):
    """Use Lanczos where ESRGAN invented detail on smooth art: seeds where the blurred mean difference passes 28
    levels (clean art stays under ~23) and the source is flat there (local std < 14: the dhoti smudges sit at ~7,
    paddy or leaf texture at 21+), grown by ~40 px and feathered so the whole invented blob goes."""
    lz = np.asarray(src.convert("RGB").resize(res.size, Image.LANCZOS), dtype=np.float32)
    r = np.asarray(res.convert("RGB"), dtype=np.float32)
    d = cv2.GaussianBlur(np.abs(r - lz).mean(axis=2), (0, 0), 6)
    g = lz.mean(axis=2)
    mu = cv2.GaussianBlur(g, (0, 0), 8)
    sd = np.sqrt(np.maximum(cv2.GaussianBlur(g * g, (0, 0), 8) - mu * mu, 0))
    seed = ((d > 28) & (sd < 14)).astype(np.uint8)
    m = cv2.dilate(seed, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (81, 81))).astype(np.float32)
    m = cv2.GaussianBlur(m, (0, 0), 10)[..., None]
    print(f"guard: {(m > 0.5).mean() * 100:.3f}% of pixels replaced")
    return Image.fromarray((r * (1 - m) + lz * m).round().astype(np.uint8))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--scale", type=float, default=2)
    ap.add_argument("--tile", type=int, default=256)
    ap.add_argument("--fix", action="store_true", help="only apply the guard to an existing dst")
    a = ap.parse_args()
    img = Image.open(a.src)
    alpha = img.getchannel("A") if img.mode == "RGBA" else None
    if a.fix:
        res = guard(img, Image.open(a.dst))
        if alpha is not None:
            res.putalpha(alpha.resize(res.size, Image.LANCZOS))
        res.save(a.dst)
        print("fixed", a.dst)
        return
    model = ModelLoader().load_from_file(
        hf_hub_download("Comfy-Org/Real-ESRGAN_repackaged", "RealESRGAN_x4plus.safetensors")).model.eval()
    torch.set_num_threads(torch.get_num_threads())

    x = torch.from_numpy(np.asarray(img.convert("RGB"), dtype=np.float32) / 255).permute(2, 0, 1)[None]
    _, _, h, w = x.shape
    out = torch.zeros(1, 3, h * 4, w * 4)
    t, pad = a.tile, 16
    with torch.inference_mode():
        for y0 in range(0, h, t):
            for x0 in range(0, w, t):
                ya, xa = max(y0 - pad, 0), max(x0 - pad, 0)
                yb, xb = min(y0 + t + pad, h), min(x0 + t + pad, w)
                r = model(x[:, :, ya:yb, xa:xb])
                oy, ox = (y0 - ya) * 4, (x0 - xa) * 4
                th, tw = min(t, h - y0) * 4, min(t, w - x0) * 4
                out[:, :, y0 * 4:y0 * 4 + th, x0 * 4:x0 * 4 + tw] = r[:, :, oy:oy + th, ox:ox + tw]
    res = Image.fromarray((out[0].permute(1, 2, 0).clamp(0, 1).numpy() * 255).round().astype(np.uint8))
    size = (round(w * a.scale), round(h * a.scale))
    res = guard(img, res.resize(size, Image.LANCZOS))
    if alpha is not None:
        res.putalpha(alpha.resize(size, Image.LANCZOS))
    res.save(a.dst)
    print("saved", a.dst, size)


if __name__ == "__main__":
    main()
