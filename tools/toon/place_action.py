"""Put a library action (assets/actions/<name>.webm, made by tools/toon/body.py) into a scene. 1080x1920 MP4 out.

Usage:
    python tools/toon/place_action.py PLAN.json OUT.mp4
PLAN.json:
{"bg": "frames/plate.png",            # background still (any size; resized to 1080x1920), relative to PLAN.json
 "duration": 4.0, "fps": 25,
 "layers": [                           # drawn in order (later = in front)
   {"action": "walk_side",             # library name
    "start": 0.0, "src_start": 0.0,    # when it appears / where in the clip it starts (loops if the action loops)
    "path": [[0, 900, 1700, 1200], [4, 200, 1700, 1200]],   # [t, feet_x, feet_y, figure height px] keyframes
    "flip": true,                      # mirror (walk_side faces left; flip to walk right)
    "shadow": 0.38,                    # soft ground shadow under the feet (0 = none)
    "light": [1.0, 0.97, 0.9]}],       # colour multiplier to match the scene light (optional)
 "camera": [[0, 960, 1920]]}           # optional [t, centre_y, view_height] push-in on the final frame
For walk_side the json's ground speed tells how fast the path should move so the feet don't slide:
   px/s on screen = ground_speed_px_s * (figure height / fig_h); place_action prints that speed as a check.
"""
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "assets/actions"
W, H = 1080, 1920


def frames_of(name):
    meta = json.load(open(LIB / f"{name}.json"))
    w, h = meta["size"]
    raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-c:v", "libvpx-vp9", "-i", str(LIB / f"{name}.webm"),
                          "-f", "rawvideo", "-pix_fmt", "rgba", "-"], capture_output=True, check=True).stdout
    arr = np.frombuffer(raw, np.uint8).reshape(-1, h, w, 4)
    return meta, arr


def interp(path, t):
    ts = [p[0] for p in path]
    return [float(np.interp(t, ts, [p[k] for p in path])) for k in (1, 2, 3)]


def main():
    plan_path = Path(sys.argv[1])
    out = sys.argv[2]
    plan = json.loads(plan_path.read_text())
    fps = plan.get("fps", 25)
    n = round(plan["duration"] * fps)
    bg = np.array(Image.open(plan_path.parent / plan["bg"]).convert("RGB").resize((W, H), Image.LANCZOS)).astype(np.float32)
    clips = {}
    for L in plan["layers"]:
        if L["action"] not in clips:
            clips[L["action"]] = frames_of(L["action"])
        meta = clips[L["action"]][0]
        if L["action"] == "walk_side" and len(L["path"]) > 1:
            p0, p1 = L["path"][0], L["path"][-1]
            need = meta["ground_speed_px_s"] * (p0[3] / meta["fig_h"])
            have = abs(p1[1] - p0[1]) / max(1e-6, p1[0] - p0[0])
            print(f"walk_side: path speed {have:.0f} px/s, feet need {need:.0f} px/s")
    cams = plan.get("camera", [[0, H / 2, H]])
    ff = subprocess.Popen(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-framerate", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "17",
                           "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i in range(n):
        t = i / fps
        img = bg.copy()
        for L in plan["layers"]:
            if t < L.get("start", 0):
                continue
            meta, arr = clips[L["action"]]
            k = round((t - L.get("start", 0) + L.get("src_start", 0)) * fps)
            k = k % len(arr) if meta["loop"] else min(k, len(arr) - 1)
            fr = arr[k]
            fx, fy, fh = interp(L["path"], t)
            sc = fh / meta["fig_h"]
            spr = cv2.resize(fr, (max(1, round(fr.shape[1] * sc)), max(1, round(fr.shape[0] * sc))), interpolation=cv2.INTER_AREA)
            ax, ay = meta["feet"][0] * sc, meta["feet"][1] * sc
            if L.get("flip"):
                spr = spr[:, ::-1]
                ax = spr.shape[1] - ax
            spr = spr.astype(np.float32)
            if L.get("light"):
                spr[..., :3] *= np.array(L["light"], np.float32)
            sh = L.get("shadow", 0.38)
            if sh:
                m = np.zeros((H, W), np.float32)
                cv2.ellipse(m, (int(fx), int(fy)), (int(fh * 0.16), int(fh * 0.022)), 0, 0, 360, 1, -1)
                img *= 1 - sh * cv2.GaussianBlur(m, (0, 0), fh * 0.01)[..., None]
            x0, y0 = int(round(fx - ax)), int(round(fy - ay))
            xs, ys = max(0, x0), max(0, y0)
            xe, ye = min(W, x0 + spr.shape[1]), min(H, y0 + spr.shape[0])
            if xe > xs and ye > ys:
                s = spr[ys - y0:ye - y0, xs - x0:xe - x0]
                a = s[..., 3:4] / 255
                img[ys:ye, xs:xe] = img[ys:ye, xs:xe] * (1 - a) + s[..., :3] * a
        cy = float(np.interp(t, [c[0] for c in cams], [c[1] for c in cams]))
        vh = float(np.interp(t, [c[0] for c in cams], [c[2] for c in cams]))
        if vh < H - 0.5:
            vw = vh * W / H
            M = np.float32([[W / vw, 0, -(W / 2 - vw / 2) * W / vw], [0, H / vh, -(cy - vh / 2) * H / vh]])
            img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        ff.stdin.write(np.clip(img, 0, 255).astype(np.uint8).tobytes())
    ff.stdin.close()
    ff.wait()
    print("saved", out)


if __name__ == "__main__":
    main()
