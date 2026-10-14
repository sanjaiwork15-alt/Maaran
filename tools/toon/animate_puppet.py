"""Animate the 2D Thatha puppet (tools/toon/puppet.py, owner's art) from a timeline. CPU only.

Usage:
    python tools/toon/animate_puppet.py TIMELINE.json OUT.mp4

TIMELINE.json (paths relative to the file):
{
  "fps": 25, "duration": 9.9, "audio": "mix.wav", "mouth": "mouth.json",   # Rhubarb cues
  "background": "05_field_vertical",
  "camera": [[t, cx, cy, h], ...],                 # background source px, eased
  "tracks": {"brow": [[t, v], ...], "head": ..., "arm": ..., "hand_rot": ...},
  "hands": [[t, "wave"], [t, "rest"], ...],        # arm swaps; each swings in over 0.25 s
  "waves": [[t0, t1, amp_deg, hz]],                # wave oscillation added to hand_rot
  "blinks": [t, ...], "talk_bob": 1.2
}
"""
import json
import math
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import puppet  # noqa: E402

CFG = CUES = RIG = STAGE = None
MOVE = 0.34                # seconds an arm takes to move between gestures


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


def mouth_at(t):
    m = "X"
    for c in CUES:
        if c["start"] <= t:
            m = c["value"]
    return m


def pose_at(t):
    pose = {k: track(v, t) for k, v in CFG.get("tracks", {}).items()}
    # arm changes: shoulder, elbow and wrist move smoothly from one gesture's angles to the
    # next; the hand changes shape halfway, while the arm is moving
    hand, angles = "rest", puppet.GESTURES["rest"]
    fore_len, fore_front = 1.0, None
    for t0, name in CFG.get("hands", []):
        if t < t0:
            break
        p = ease((t - t0) / MOVE)
        new = puppet.GESTURES[name]
        old = angles
        angles = tuple(o + (n - o) * p for o, n in zip(old, new))
        # the hand opens/forms as the arm starts lifting, and relaxes only once it is down
        lifting = abs(new[1]) > abs(old[1])
        hand = name if p >= (0.2 if lifting else 0.8) else hand
        if p >= 1:
            angles, fore_len, fore_front = new, 1.0, None
        elif abs(new[1] - old[1]) > 60:
            # the forearm swings towards the camera: it looks shorter mid-move and stays
            # in front of the sleeve, instead of sweeping out sideways at full length
            fore_len = 1 - 0.4 * math.sin(math.pi * p)
            fore_front = max(abs(new[1]), abs(old[1])) > 60
    pose["fore_len"], pose["fore_front"] = fore_len, fore_front
    pose["hand"] = hand
    pose["shoulder"], pose["elbow"], pose["wrist"] = angles
    for t0, t1, amp, hz in CFG.get("waves", []):
        if t0 <= t <= t1:
            fade = min(1, (t - t0) / 0.2, (t1 - t) / 0.2)
            pose["hand_rot"] = pose.get("hand_rot", 0) + amp * fade * math.sin(2 * math.pi * hz * (t - t0))
    pose["mouth"] = mouth_at(t)
    blink = 0.0
    for b in CFG.get("blinks", []):
        if b <= t < b + 0.16:
            blink = 1 - abs((t - b) / 0.08 - 1)
    pose["blink"] = min(1.0, blink * 1.3)
    speaking = pose["mouth"] not in ("X", "A")
    bob = CFG.get("talk_bob", 1.2) * math.sin(2 * math.pi * 1.6 * t) if speaking else 0
    pose["head"] = pose.get("head", 0) + bob + 0.7 * math.sin(2 * math.pi * t / 4.3)
    pose["body"] = pose.get("body", 0) + 0.35 * math.sin(2 * math.pi * t / 3.4)
    pose["shoulder"] += 1.2 * math.sin(2 * math.pi * t / 3.4 + 0.6)      # gentle idle sway
    return pose


def init(cfg, cues):
    global CFG, CUES, RIG, STAGE
    CFG, CUES = cfg, cues
    RIG = puppet.Rig()
    STAGE = puppet.Stage(cfg.get("background", "05_field_vertical"), feet=tuple(cfg.get("feet", (0.5, 0.9))))


def render(i):
    t = i / CFG["fps"]
    cam = tuple(track([(k[0], k[j]) for k in CFG["camera"]], t) for j in (1, 2, 3))
    return STAGE.frame(RIG, pose_at(t), cam).tobytes()


def main():
    tl = Path(sys.argv[1])
    out = sys.argv[2]
    cfg = json.loads(tl.read_text())
    cues = json.loads((tl.parent / cfg["mouth"]).read_text())["mouthCues"]
    n = round(cfg["duration"] * cfg["fps"])
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", "1080x1920", "-framerate", str(cfg["fps"]), "-i", "-",
                           "-i", str(tl.parent / cfg["audio"]), "-map", "0:v", "-map", "1:a",
                           "-c:v", "libx264", "-crf", "17", "-preset", "slow", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out],
                          stdin=subprocess.PIPE)
    with Pool(initializer=init, initargs=(cfg, cues)) as pool:
        for k, frame in enumerate(pool.imap(render, range(n), chunksize=2)):
            ff.stdin.write(frame)
            if k % 50 == 0:
                print(f"frame {k}/{n}", flush=True)
    ff.stdin.close()
    ff.wait()
    print("saved", out)


if __name__ == "__main__":
    main()
