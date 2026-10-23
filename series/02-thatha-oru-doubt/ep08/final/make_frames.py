"""Ep 8 start frames without a GPU: the semman kaadu field when the first monsoon rain comes – four Thatha poses.

Run with the f5 env:  python -I make_frames.py
Every frame is an approved Groundnut frame on the field (well and hut behind), re-lit for the rain in code:
the sunny sky is replaced by storm clouds (tools/toon/rain.py storm_sky), the light goes grey (overcast; Thatha
gets a lighter grade so his skin stays warm) and, after the first drops, the red soil is darker and wet.
f_mbreath: Groundnut Ep 2 f_humour2_s3 – hand on his chest, big happy face (the smell!) – dry soil (the hook);
           f_mbreath_w is the same pose after the rain (wet soil).
f_msoil:   Groundnut Ep 2 f_soil_s3 – crouching, damp earth crumbling in his hands – wet.
f_mpoint:  Groundnut Ep 2 f_hook2_s3 – standing, pointing down at the soil – wet.
f_mstick:  Groundnut Ep 1 f4_soil_s3 – standing with his stick, open hand – wet (the ending).
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import new_session, remove

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tools/toon"))
from rain import overcast, sky_mask, storm_sky, wet  # noqa: E402

FR = HERE / "frames"
GN = ROOT / "series/01-groundnut"
POSES = [("f_mbreath", "ep02/final/frames/f_humour2_s3.png", 640, False, 11),
         ("f_mbreath_w", "ep02/final/frames/f_humour2_s3.png", 640, True, 11),
         ("f_msoil", "ep02/final/frames/f_soil_s3.png", 480, True, 12),
         ("f_mpoint", "ep02/final/frames/f_hook2_s3.png", 640, True, 13),
         ("f_mstick", "ep01/final/frames/f4_soil_s3.png", 620, True, 14)]


def main():
    seg = new_session("isnet-anime")
    only = sys.argv[1:]
    for name, src, horizon, is_wet, seed in POSES:
        if only and name not in only:
            continue
        im = Image.open(GN / src).convert("RGB").resize((720, 1280))
        rgb = np.array(im)
        alpha = np.array(remove(im, session=seg, only_mask=True))
        alpha = np.clip((alpha.astype(float) - 90) * 2.6, 0, 255).astype(np.uint8)
        # the old blue sky leaves a pale fringe on leaf and hair edges: grow the sky mask 2 px into the leaves, put
        # the clouds behind, and lay Thatha back on top with his cut-out eroded 2 px (his fringe goes too)
        m = cv2.GaussianBlur(cv2.dilate(sky_mask(rgb, horizon), np.ones((5, 5), np.uint8)), (0, 0), 1.0)[..., None]
        clouds = storm_sky(720, horizon + 40, seed)[..., :3]
        sky = np.zeros_like(rgb)
        sky[:horizon + 40] = clouds
        sky[horizon + 40:] = clouds[-1:]
        bg = rgb * (1 - m) + overcast(sky, 0.15) * m
        a = cv2.GaussianBlur(cv2.erode(alpha, np.ones((5, 5), np.uint8)), (0, 0), 0.8).astype(np.float32)[..., None] / 255
        out = (bg * (1 - a) + rgb * a).astype(np.uint8)
        out = (overcast(out, 1.0) * (1 - a) + overcast(out, 0.55) * a).astype(np.uint8)
        if is_wet:
            out = wet(out, 1.0, protect=alpha, ytop=horizon + 30)
        Image.fromarray(out).save(FR / f"{name}.png")
        print("saved", name)


if __name__ == "__main__":
    main()
