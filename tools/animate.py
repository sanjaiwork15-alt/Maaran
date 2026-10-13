"""Animate Maaran Thatha on a scene, lip-synced to the voice. Renders 1080x1920 MP4.

Usage:
    python tools/animate.py SHOTS.json OUT.mp4

SHOTS.json:
{
  "scene": "scene.png",              # 1620x2880 stage from tools/scene.py
  "voice": "voice.wav", "audio": "mix.wav",   # voice drives the mouth; audio goes in the video
  "fps": 25,
  "shots": [  # camera per shot: centre (x, y) and height on the stage, eased from "from" to "to"
    {"start": 0, "end": 5.5, "from": [918, 1060, 760], "to": [918, 1065, 700], "bg_blur": 6},
    ...
  ],
  "brows": [[1.5, 3.9]],             # time ranges with raised eyebrows
  "blinks": [1.3, 4.9, 8.1, 11.6]    # blink start times
}

The character is assets/character/maaran_thatha_cutout.png (the locked look).
Animation: jaw/beard opens with the voice loudness, mouth interior and teeth
show when open, blinks, eyebrow raises, gentle breathing and sway. All face
positions below are pixel coordinates in the reference image.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import gaussian_filter, map_coordinates

ROOT = Path(__file__).resolve().parent.parent
CHAR = ROOT / "assets/character/maaran_thatha_cutout.png"
OUT_W, OUT_H = 1080, 1920

FEET_SRC = (448, 1290)      # point between the feet in the reference image
FEET_STAGE = (930, 2600)    # where that point stands on the stage
SCALE = 1.5                 # reference px -> stage px
HEAD_BOX = (330, 120, 560, 380)   # x0, y0, x1, y1 region that gets face animation
MOUTH = (443, 268, 26)      # centre x, lip line y, half width
EYES = [(396, 197, 16, 10), (467, 189, 15, 9)]   # centre x, y, radius x, y
JAW_MAX = 7.5               # max jaw drop in reference px
BROW_MAX = 4.0


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def ease(t):
    return 0.5 - 0.5 * np.cos(np.pi * np.clip(t, 0, 1))


def mouth_envelope(voice, fps, n):
    x, sr = sf.read(voice, dtype="float32")
    if x.ndim > 1:
        x = x.mean(1)
    hop = sr / fps
    win = int(0.045 * sr)
    rms = np.array([np.sqrt(np.mean(x[int(i * hop): int(i * hop) + win] ** 2) + 1e-10) for i in range(n)])
    db = 20 * np.log10(rms)
    top = np.percentile(db, 97)
    open_ = np.clip((db - (top - 30)) / 24, 0, 1) ** 0.9
    out = np.zeros(n)
    for i in range(n):          # fast open, slower close, like a real jaw
        prev = out[i - 1] if i else 0
        out[i] = open_[i] if open_[i] > prev else prev * 0.55 + open_[i] * 0.45
    return out


class Face:
    def __init__(self, rgba):
        x0, y0, x1, y1 = HEAD_BOX
        self.crop = rgba[y0:y1, x0:x1].astype(np.float32)
        self.yy, self.xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        mx, my, _ = MOUTH
        self.jaw_w = (smoothstep(my - 1, my + 5, self.yy) * (1 - smoothstep(318, 372, self.yy))
                      * (1 - smoothstep(30, 115, np.abs(self.xx - mx))))
        # blink: the upper-lid skin slides down over each eye
        self.lid_w = []
        for ex, ey, rx, ry in EYES:
            inside = np.clip(1 - ((self.xx - ex) / (rx + 3)) ** 2, 0, 1) ** 0.5
            prof = smoothstep(ey - ry - 7, ey + 0.5 * ry, self.yy) * (1 - smoothstep(ey + 0.6 * ry, ey + ry + 3, self.yy))
            self.lid_w.append((inside * prof, 2 * ry + 3))
        self.brow_w = (smoothstep(132, 150, self.yy) * (1 - smoothstep(176, 186, self.yy))
                       * (1 - smoothstep(70, 95, np.abs(self.xx - 432))))

    def render(self, jaw, brow, blink):
        x0, y0, _, _ = HEAD_BOX
        dy = -jaw * JAW_MAX * self.jaw_w + brow * BROW_MAX * self.brow_w
        for w, shift in self.lid_w:
            dy = dy - min(blink, 1) * 0.62 * shift * w   # deeper than ~0.6 the warp streaks
        coords = [self.yy - y0 + dy, self.xx - x0]
        out = np.stack([map_coordinates(self.crop[..., c], coords, order=1, mode="nearest") for c in range(4)], -1)
        img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")
        d = jaw * JAW_MAX
        if d > 0.6:
            self._mouth(img, d)
        return np.array(img)

    def _mouth(self, img, d):
        """Dark gap between the moustache line and the dropped lower lip, following the smile."""
        x0, y0, _, _ = HEAD_BOX
        mx, my, hw = MOUTH
        s = 4
        xs = np.linspace(-1, 1, 41)
        line = lambda u: (my - y0 - 4 * u ** 2)            # smile: corners sit a little higher
        gap = lambda u: d * 0.95 * (1 - u ** 2) ** 0.7
        top = [((mx - x0 + u * hw) * s, line(u) * s) for u in xs]
        bot = [((mx - x0 + u * hw) * s, (line(u) + gap(u)) * s) for u in xs[::-1]]
        big = (img.width * s, img.height * s)
        m = Image.new("L", big, 0)
        ImageDraw.Draw(m).polygon(top + bot, fill=255)
        m = m.resize(img.size, Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.5))
        a = np.array(img).astype(np.float32)
        mk = np.array(m).astype(np.float32)[..., None] / 255
        yy = np.arange(img.height)[:, None, None]
        depth = np.clip((yy - (my - y0)) / max(d, 1), 0, 1)           # darker at the top, warmer below
        inner = np.array([40, 16, 14]) * (1 - depth) + np.array([105, 42, 36]) * depth
        a[..., :3] = a[..., :3] * (1 - mk) + inner * mk
        img.paste(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA"))


def affine(cam, t, env):
    cx, cy, h = cam
    s = OUT_H / h
    ox, oy = cx - OUT_W / (2 * s), cy - h / 2
    out_to_stage = np.array([[1 / s, 0, ox], [0, 1 / s, oy], [0, 0, 1]])
    breathe = 0.005 * np.sin(2 * np.pi * t / 3.6)
    th = np.radians(0.45 * np.sin(2 * np.pi * t / 5.5) + 0.25 * env)
    kx, ky = SCALE * (1 - 0.3 * breathe), SCALE * (1 + breathe + 0.004 * env)
    rot = np.array([[np.cos(th), np.sin(th)], [-np.sin(th), np.cos(th)]])   # inverse rotation
    lin = np.diag([1 / kx, 1 / ky]) @ rot
    stage_to_src = np.eye(3)
    stage_to_src[:2, :2] = lin
    stage_to_src[:2, 2] = np.array(FEET_SRC) - lin @ np.array(FEET_STAGE)
    return out_to_stage, stage_to_src @ out_to_stage


def main():
    cfg = json.loads(Path(sys.argv[1]).read_text())
    base = Path(sys.argv[1]).parent
    out_path = sys.argv[2]
    fps = cfg.get("fps", 25)
    dur = sf.info(str(base / cfg["voice"])).duration
    n = int(dur * fps)

    scene = Image.open(base / cfg["scene"]).convert("RGB")
    blurred = {}
    rgba = np.array(Image.open(CHAR).convert("RGBA"))
    face = Face(rgba)
    env = mouth_envelope(str(base / cfg["voice"]), fps, n)
    hx0, hy0, hx1, hy1 = HEAD_BOX

    shadow = Image.new("L", (OUT_W * 2, OUT_H * 2), 0)
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{OUT_W}x{OUT_H}", "-r", str(fps), "-i", "-", "-i", str(base / cfg["audio"]),
                            "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", out_path],
                           stdin=subprocess.PIPE)
    for i in range(n):
        t = i / fps
        shot = next((s for s in cfg["shots"] if s["start"] <= t < s["end"]), cfg["shots"][-1])
        u = ease((t - shot["start"]) / (shot["end"] - shot["start"]))
        cam = [a + (b - a) * u for a, b in zip(shot["from"], shot["to"])]

        brow = max([ease((t - a) / 0.25) * ease((b - t) / 0.3) for a, b in cfg.get("brows", [])] + [0])
        blink = max([1 - abs((t - b0) / 0.09 - 1) for b0 in cfg.get("blinks", []) if 0 <= t - b0 <= 0.18] + [0])
        frame_rgba = rgba.copy()
        frame_rgba[hy0:hy1, hx0:hx1] = face.render(env[i], brow, blink)

        o2s, o2src = affine(cam, t, env[i])
        r = shot.get("bg_blur", 0)
        if r not in blurred:
            blurred[r] = scene.filter(ImageFilter.GaussianBlur(r)) if r else scene
        frame = blurred[r].transform((OUT_W, OUT_H), Image.AFFINE, tuple(o2s[:2].ravel()), Image.BILINEAR)

        # soft contact shadow under the feet and stick
        sx = (FEET_STAGE[0] - o2s[0, 2]) / o2s[0, 0]
        sy = (FEET_STAGE[1] - o2s[1, 2]) / o2s[1, 1]
        sc = 1 / o2s[0, 0]
        if -400 < sy < OUT_H + 400:
            sh = Image.new("L", (OUT_W, OUT_H), 0)
            ImageDraw.Draw(sh).ellipse((sx - 330 * sc, sy - 30 * sc, sx + 300 * sc, sy + 45 * sc), fill=120)
            frame.paste((60, 24, 14), (0, 0), sh.filter(ImageFilter.GaussianBlur(float(max(2, 22 * sc)))))

        ch = Image.fromarray(frame_rgba, "RGBA").transform((OUT_W, OUT_H), Image.AFFINE,
                                                           tuple(o2src[:2].ravel()), Image.BILINEAR)
        frame = frame.convert("RGBA")
        frame.alpha_composite(ch)
        enc.stdin.write(frame.convert("RGB").tobytes())
        if i % 50 == 0:
            print(f"frame {i}/{n}", flush=True)
    enc.stdin.close()
    enc.wait()
    print("saved", out_path)


if __name__ == "__main__":
    main()
