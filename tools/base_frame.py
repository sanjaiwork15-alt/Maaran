"""Place the owner's 2D Thatha art on a series background: the base image for scene start frames.

Usage:
    python tools/base_frame.py OUT.png [--shot medium|wide] [--bg 05_field_vertical] [--size 720x1280]

Thatha (assets/2d .../01_front.png) is cut out of his white background and stood in the field
with a soft contact shadow. "medium" frames him from the knees up (talking scenes), "wide" shows
him head to toe. Qwen-Image-Edit then turns this into each scene's pose/prop start frame.
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

ART = Path(__file__).resolve().parent.parent / "assets/2d"
FEET = (0.46, 0.90)          # where his feet stand, as a fraction of the background
HEIGHT = 0.74                # his height as a fraction of the background height
CAMS = {"medium": (480, 620, 1000), "wide": (470, 836, 1672)}   # centre x, y, height (background source px)


def load(name):
    up, src = ART / "up" / f"{name}.png", ART / "source" / f"{name}.png"
    return (Image.open(up), 2) if up.exists() else (Image.open(src), 1)


def cut_white(img, thresh=238):
    """Make the white background transparent; white clothes inside the outline stay solid."""
    a = np.asarray(img.convert("RGB")).astype(np.int16)
    white = (a.min(axis=2) >= thresh) & (a.max(axis=2) - a.min(axis=2) <= 14)
    lab, _ = ndimage.label(white)
    border = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    bg = ndimage.binary_opening(np.isin(lab, border[border > 0]), iterations=1)
    alpha = ndimage.gaussian_filter((~bg).astype(np.float32), 0.8)
    out = img.convert("RGBA")
    out.putalpha(Image.fromarray((alpha * 255).astype(np.uint8)))
    return out


def base_frame(shot="medium", bg_name="05_field_vertical", size=(720, 1280)):
    bg, kb = load(bg_name)
    bg = bg.convert("RGBA")
    fig, k = load("01_front")
    fig = cut_white(fig)
    ys = np.nonzero(np.asarray(fig.getchannel("A")).max(axis=1) > 128)[0]
    feet_y, top_y = ys.max(), ys.min()
    s = HEIGHT * bg.height / (feet_y - top_y)
    fig = fig.resize((round(fig.width * s), round(fig.height * s)), Image.LANCZOS)
    fx, fy = FEET[0] * bg.width, FEET[1] * bg.height
    shadow = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    sw = fig.width * 0.36
    ImageDraw.Draw(shadow).ellipse([fx - sw, fy - sw * 0.12, fx + sw, fy + sw * 0.1], fill=(60, 25, 10, 90))
    bg.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(8 * kb)))
    bg.alpha_composite(fig, (round(fx - fig.width / 2), round(fy - feet_y * s)))
    cx, cy, h = (v * kb for v in CAMS[shot])
    w = h * size[0] / size[1]
    return bg.crop((round(cx - w / 2), round(cy - h / 2), round(cx + w / 2), round(cy + h / 2))).convert("RGB").resize(size, Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--shot", default="medium", choices=sorted(CAMS))
    ap.add_argument("--bg", default="05_field_vertical")
    ap.add_argument("--size", default="720x1280")
    a = ap.parse_args()
    base_frame(a.shot, a.bg, tuple(map(int, a.size.split("x")))).save(a.out)
    print("saved", a.out)


if __name__ == "__main__":
    main()
