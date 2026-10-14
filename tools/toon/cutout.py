"""Cut a character out of a plain white background (art from assets/2d/source).

Usage:
    python tools/toon/cutout.py IN.png OUT.png

Only near-white pixels that connect to the image border become transparent, so white
clothes, hair and beard inside the outline stay solid. The edge is softened by one
pixel so the cut-out sits cleanly on any background.
"""
import sys

import numpy as np
from PIL import Image
from scipy import ndimage


def cutout(img, thresh=238):
    a = np.asarray(img.convert("RGB")).astype(np.int16)
    white = (a.min(axis=2) >= thresh) & (a.max(axis=2) - a.min(axis=2) <= 14)
    lab, _ = ndimage.label(white)
    border = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    bg = np.isin(lab, border[border > 0])
    bg = ndimage.binary_opening(bg, iterations=1)
    alpha = (~bg).astype(np.float32)
    alpha = ndimage.gaussian_filter(alpha, 0.8)
    out = img.convert("RGBA")
    out.putalpha(Image.fromarray((alpha * 255).astype(np.uint8)))
    return out


if __name__ == "__main__":
    cutout(Image.open(sys.argv[1])).save(sys.argv[2])
    print("saved", sys.argv[2])
