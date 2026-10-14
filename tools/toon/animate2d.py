"""Animate 2D Thatha (tools/toon/art.py) from a timeline and render a 1080x1920 MP4. CPU only.

Usage:
    python tools/toon/animate2d.py TIMELINE.json OUT.mp4

TIMELINE.json (paths relative to the file):
{
  "fps": 25, "duration": 9.9,
  "audio": "mix.wav",                     # goes into the video
  "mouth": "mouth.json",                  # Rhubarb Lip Sync output (rhubarb -r phonetic -f json)
  "camera": [[0, 1080, 1920, 1100], [9.9, 1080, 1890, 980]],   # t, centre x, centre y, height (stage px)
  "tracks": {"l_up": [[0, 0], [0.6, -35]], ...},   # numeric pose keys, eased between keyframes
  "steps": {"l_hand": [[0, "rest"], [0.6, "open"]]},  # discrete pose keys
  "waves": [[1.0, 2.3, 12, 2.4]],         # t0, t1, amplitude (deg), Hz: forearm wave on top of l_fore
  "blinks": [1.7, 4.4, 7.3],
  "talk_bob": 1.5                         # head nod (deg) that follows the speech
}
"""
import json
import math
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

import cairosvg

sys.path.insert(0, str(Path(__file__).parent))
import art  # noqa: E402

CFG = SCENE = CUES = None


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def track(keys, t):
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            return v0 + (v1 - v0) * ease((t - t0) / (t1 - t0))
    return keys[-1][1]


def step(keys, t):
    v = keys[0][1]
    for k, val in keys:
        if t >= k:
            v = val
    return v


def mouth_at(t):
    m = "X"
    for c in CUES:
        if c["start"] <= t:
            m = c["value"]
    return m


def speaking(t):
    return mouth_at(t) not in ("X", "A")


def pose_at(t):
    pose = {k: track(v, t) for k, v in CFG.get("tracks", {}).items()}
    pose.update({k: step(v, t) for k, v in CFG.get("steps", {}).items()})
    for t0, t1, amp, hz in CFG.get("waves", []):
        if t0 <= t <= t1:
            fade = min(1, (t - t0) / 0.25, (t1 - t) / 0.25)
            pose["l_fore"] = pose.get("l_fore", 0) + amp * fade * math.sin(2 * math.pi * hz * (t - t0))
    pose["mouth"] = mouth_at(t)
    blink = 0.0
    for b in CFG.get("blinks", []):
        if b <= t < b + 0.16:
            blink = 1 - abs((t - b) / 0.08 - 1)
    pose["blink"] = blink * 1.0
    # life: breathing sway, a head bob that follows speech, a tiny idle drift
    bob = CFG.get("talk_bob", 1.5) * math.sin(2 * math.pi * 1.7 * t) if speaking(t) else 0
    pose["head"] = pose.get("head", 0) + bob + 0.8 * math.sin(2 * math.pi * t / 4.1)
    pose["body"] = pose.get("body", 0) + 0.5 * math.sin(2 * math.pi * t / 3.3)
    return pose


def camera_at(t):
    keys = CFG["camera"]
    return tuple(track([(k[0], k[i]) for k in keys], t) for i in (1, 2, 3))


def init(cfg, scene_svg, cues):
    global CFG, SCENE, CUES
    CFG, SCENE, CUES = cfg, scene_svg, cues


def render(i):
    t = i / CFG["fps"]
    return cairosvg.svg2png(bytestring=art.frame(camera_at(t), pose_at(t), scene_svg=SCENE).encode())


def main():
    tl = Path(sys.argv[1])
    out = sys.argv[2]
    cfg = json.loads(tl.read_text())
    cues = json.loads((tl.parent / cfg["mouth"]).read_text())["mouthCues"]
    n = round(cfg["duration"] * cfg["fps"])
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "image2pipe", "-framerate", str(cfg["fps"]),
                           "-i", "-", "-i", str(tl.parent / cfg["audio"]), "-map", "0:v", "-map", "1:a",
                           "-c:v", "libx264", "-crf", "16", "-preset", "slow", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out],
                          stdin=subprocess.PIPE)
    with Pool(initializer=init, initargs=(cfg, art.scene(), cues)) as pool:
        for k, png in enumerate(pool.imap(render, range(n), chunksize=4)):
            ff.stdin.write(png)
            if k % 50 == 0:
                print(f"frame {k}/{n}", flush=True)
    ff.stdin.close()
    ff.wait()
    print("saved", out)


if __name__ == "__main__":
    main()
