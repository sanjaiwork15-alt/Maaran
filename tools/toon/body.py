"""Whole-body actions for Thatha from ONE drawing of the owner, without a GPU (owner 2026-11-02: "code and animate
these shots"). The drawing is never cut into pieces: soft, overlapping region weights (feet, veshti hem, stick + its
hand, free arm, head) each get a small motion per frame, and the picture is bent smoothly with a blended displacement
field (2D linear-blend skinning, like the face warp in talk.py) – so there are no visible joints.

Usage:
    python tools/toon/body.py ACTION OUT_DIR [--seconds 4] [--still T]
ACTION: walk_front – walking towards the camera with his stick (step cycle 1.1 s; feet lift and come forward, the
        veshti hem swings, the body bobs and sways onto the standing foot, the free arm swings against the stepping
        leg, the stick lifts and plants with the opposite foot, the head stays steady).
OUT_DIR gets RGBA PNG frames (25 fps) of the figure on transparency, plus preview.mp4 (on a grey card) – composite
them onto any location; the walk cycle is a seamless loop (frames 0..N-1 of one cycle, cycle.json).
Source: assets/2d/up/01_front.png (x2 upscale of the owner's 01_front.png). Region coordinates below are in the
1024x1536 source pixels.
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
FPS = 25
K = 2.0                                                    # source px -> up px


def poly_mask(shape, pts, blur):
    m = np.zeros(shape, np.float32)
    cv2.fillPoly(m, [np.array(pts, np.float32).astype(np.int32) * int(K)], 1.0)
    return cv2.GaussianBlur(m, (0, 0), blur * K) if blur else m


def ramp_y(shape, y0, y1):
    """0 above y0, 1 below y1 (source px)."""
    yy = np.arange(shape[0], dtype=np.float32)[:, None] / K
    return np.clip((yy - y0) / (y1 - y0), 0, 1) * np.ones(shape, np.float32)


class Figure:
    def __init__(self):
        cache = Path.home() / ".maaran/cache/front_rgba.png"
        if cache.exists():
            rgba = np.array(Image.open(cache))
        else:
            from rembg import new_session, remove
            im = Image.open(ROOT / "assets/2d/up/01_front.png").convert("RGB")
            a = np.array(remove(im, session=new_session("isnet-anime"), only_mask=True)).astype(np.float32)
            a = np.clip((a - 90) * 2.6, 0, 255).astype(np.uint8)
            rgba = np.dstack([np.array(im), a])
            Image.fromarray(rgba).save(cache)
        pad = 160                                          # room to move
        self.img = cv2.copyMakeBorder(rgba, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=(0, 0, 0, 0)).astype(np.float32)
        self.pad = pad
        h, w = self.img.shape[:2]
        self.yy, self.xx = np.mgrid[0:h, 0:w].astype(np.float32)
        S = (h, w)
        P = lambda pts: [(x + pad / K, y + pad / K) for x, y in pts]     # noqa: E731
        # soft regions (source px)
        self.w = {
            "footL": poly_mask(S, P([(245, 1380), (455, 1380), (455, 1560), (245, 1560)]), 4),
            "footR": poly_mask(S, P([(575, 1380), (795, 1380), (795, 1560), (575, 1560)]), 4),
            "hemL": poly_mask(S, P([(320, 1150), (515, 1150), (515, 1440), (320, 1440)]), 18) * ramp_y(S, 1150 + pad / K, 1400 + pad / K),
            "hemR": poly_mask(S, P([(515, 1150), (720, 1150), (720, 1440), (515, 1440)]), 18) * ramp_y(S, 1150 + pad / K, 1400 + pad / K),
            "stick": poly_mask(S, P([(185, 610), (330, 610), (330, 790), (300, 790), (300, 1515), (215, 1515), (215, 790), (185, 790)]), 4),
            "arm": poly_mask(S, P([(705, 600), (820, 600), (845, 1040), (715, 1040)]), 10) * ramp_y(S, 640 + pad / K, 980 + pad / K),
            "head": poly_mask(S, P([(320, 0), (680, 0), (680, 330), (320, 330)]), 25),
        }
        # the stick region must not drag the shirt/veshti behind it: keep it to wood + hand colours
        hsv = cv2.cvtColor(self.img[..., :3].astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.int32)
        woodskin = ((hsv[..., 0] <= 25) & (hsv[..., 1] > 70)).astype(np.float32)
        woodskin = cv2.GaussianBlur(cv2.dilate(woodskin, np.ones((7, 7), np.uint8)), (0, 0), 3)
        self.w["stick"] *= woodskin
        cloth = (((hsv[..., 1] < 70) & (hsv[..., 2] > 150)) | ((hsv[..., 0] >= 30) & (hsv[..., 0] <= 90) & (hsv[..., 1] > 60)))
        cloth = cv2.GaussianBlur(cv2.dilate(cloth.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(np.float32), (0, 0), 3)
        self.w["arm"] *= 1 - cloth                           # the arm with its outlines swings; shirt/veshti/towel stay
        self.shape = S

    def pt(self, x, y):
        return (x + self.pad / K) * K, (y + self.pad / K) * K

    def render(self, moves, body=(0.0, 0.0, 0.0), sway_pivot=(500, 1450)):
        """moves: {region: (dx, dy, rot_deg, pivot_x, pivot_y, scale)} in source px; body: (dx, dy, rot) for all."""
        dx = np.zeros(self.shape, np.float32)
        dy = np.zeros(self.shape, np.float32)
        for name, (mx, my, rot, px, py, sc) in moves.items():
            w = self.w[name]
            cx, cy = self.pt(px, py)
            c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
            X, Y = self.xx - cx, self.yy - cy
            tx = (c * X - s * Y) * sc - X + mx * K
            ty = (s * X + c * Y) * sc - Y + my * K
            dx += w * tx
            dy += w * ty
        bx, by, br = body                                      # whole-body sway / bob about the feet
        cx, cy = self.pt(*sway_pivot)
        c, s = math.cos(math.radians(br)), math.sin(math.radians(br))
        X, Y = self.xx - cx, self.yy - cy
        stand = 1 - np.clip(self.w["footL"] + self.w["footR"], 0, 1) * 0.8   # feet stay put while the body bobs
        dx += stand * ((c * X - s * Y) - X + bx * K)
        dy += stand * ((s * X + c * Y) - Y + by * K)
        # the fields are forward motions of SOURCE pixels; the remap needs them at the DESTINATION: solve
        # d(x) = D(x - d(x)) by fixed-point iteration (otherwise big swings leave ghost outlines behind)
        fx, fy = dx.copy(), dy.copy()
        for _ in range(5):
            fx, fy = (cv2.remap(dx, self.xx - fx, self.yy - fy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE),
                      cv2.remap(dy, self.xx - fx, self.yy - fy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE))
        dx, dy = fx, fy
        out = cv2.remap(self.img, self.xx - dx, self.yy - dy, cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT,
                        borderValue=(0, 0, 0, 0))
        return np.clip(out, 0, 255).astype(np.uint8)


def walk_front(fig, t, cycle=1.1):
    """One full cycle = two steps. phase 0: left foot (image left, his right) starts to lift."""
    ph = 2 * math.pi * (t % cycle) / cycle
    lift_l = max(0.0, math.sin(ph))                             # image-left foot swings in the first half
    lift_r = max(0.0, -math.sin(ph))
    bob = -7 * (abs(math.cos(ph)) ** 1.5) + 3                   # highest over the standing foot
    sway = -6 * math.sin(ph)                                    # weight over the standing foot
    moves = {
        "footL": (-4 * lift_l, -42 * lift_l, -6 * lift_l, 350, 1460, 1 + 0.12 * lift_l),
        "footR": (4 * lift_r, -42 * lift_r, 6 * lift_r, 680, 1460, 1 + 0.12 * lift_r),
        "hemL": (-6 * lift_l, -24 * lift_l, 0, 420, 1400, 1.0),
        "hemR": (6 * lift_r, -24 * lift_r, 0, 610, 1400, 1.0),
        # the stick stays rigid in his hand (bending it smeared the wood); it rides with the body bob
        # free arm swings against the image-right leg
        "arm": (0, 0, 6 * math.sin(ph), 760, 600, 1.0),
        "head": (-0.6 * sway, -0.4 * bob, 0.4 * math.sin(ph), 500, 330, 1.0),
    }
    return fig.render(moves, body=(sway, bob, 0.8 * math.sin(ph)))


ACTIONS = {"walk_front": (walk_front, 1.1)}


def main():
    action, out = sys.argv[1], Path(sys.argv[2])
    secs = float(sys.argv[sys.argv.index("--seconds") + 1]) if "--seconds" in sys.argv else None
    fn, cycle = ACTIONS[action]
    out.mkdir(parents=True, exist_ok=True)
    fig = Figure()
    if "--still" in sys.argv:
        t = float(sys.argv[sys.argv.index("--still") + 1])
        Image.fromarray(fn(fig, t)).save(out / f"still_{t:.2f}.png")
        return
    n = round((secs or cycle) * FPS)
    for i in range(n):
        Image.fromarray(fn(fig, i / FPS)).save(out / f"{i:04d}.png")
    json.dump({"action": action, "fps": FPS, "frames": n, "cycle_frames": round(cycle * FPS), "pad": fig.pad, "scale": K},
              open(out / "cycle.json", "w"))
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", str(out / "%04d.png"),
                    "-filter_complex", "color=c=0x8a8f96:s=2368x3392[bg];[bg][0:v]overlay=shortest=1,scale=720:-2",
                    "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(out / "preview.mp4")], check=True)
    print("saved", out, n, "frames")


if __name__ == "__main__":
    main()
