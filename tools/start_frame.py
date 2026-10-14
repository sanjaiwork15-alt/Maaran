"""Make a start frame for an AI video shot: Thatha standing on a scene, framed by a camera.

Usage:
    python tools/start_frame.py SCENE.png OUT.png --cam CX,CY,H [--size 720x1280]

SCENE.png is the 1620x2880 stage from tools/scene.py. The locked character
cut-out (assets/character/maaran_thatha_cutout.png) is placed on the stage with
the same geometry as tools/animate.py, given a soft contact shadow, and the
camera box (centre CX,CY and height H in stage pixels, 9:16) is cropped and
resized to --size. The image-to-video model (Wan 2.2 I2V on Kaggle) then
animates from this frame, so his look stays locked to the reference.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
CHAR = ROOT / "assets/character/maaran_thatha_cutout.png"
FEET_SRC = (448, 1290)      # same as tools/animate.py
FEET_STAGE = (930, 2600)
SCALE = 1.5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    ap.add_argument("out")
    ap.add_argument("--cam", required=True, help="CX,CY,H in stage pixels")
    ap.add_argument("--size", default="720x1280")
    a = ap.parse_args()
    cx, cy, h = map(float, a.cam.split(","))
    ow, oh = map(int, a.size.split("x"))

    stage = Image.open(a.scene).convert("RGBA")
    char = Image.open(CHAR).convert("RGBA")
    char = char.resize((round(char.width * SCALE), round(char.height * SCALE)), Image.LANCZOS)
    x0, y0 = round(FEET_STAGE[0] - FEET_SRC[0] * SCALE), round(FEET_STAGE[1] - FEET_SRC[1] * SCALE)

    shadow = Image.new("L", stage.size, 0)
    ImageDraw.Draw(shadow).ellipse((FEET_STAGE[0] - 330, FEET_STAGE[1] - 40, FEET_STAGE[0] + 330, FEET_STAGE[1] + 50), fill=150)
    shadow = shadow.filter(ImageFilter.GaussianBlur(30))
    stage.paste(Image.new("RGBA", stage.size, (70, 30, 15, 255)), (0, 0), shadow)
    stage.alpha_composite(char, (x0, y0))

    w = h * ow / oh
    box = (round(cx - w / 2), round(cy - h / 2), round(cx + w / 2), round(cy + h / 2))
    stage.convert("RGB").crop(box).resize((ow, oh), Image.LANCZOS).save(a.out)
    print("saved", a.out, (ow, oh))


if __name__ == "__main__":
    main()
