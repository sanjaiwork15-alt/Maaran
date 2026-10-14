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
import human  # noqa: E402
import puppet  # noqa: E402

CFG = CUES = RIG = STAGE = CAMS = None
SLOW = {}                  # per-move slow-down factors found by the automatic check


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
    fore_len, fore_front, p = 1.0, None, 1.0
    prev_name, cur_name = "rest", "rest"
    for idx, (t0, name) in enumerate(CFG.get("hands", [])):
        if t < t0:
            break
        new = puppet.GESTURES[name]
        old = angles
        prev_name, cur_name = cur_name, name
        p = ease((t - t0) / (human.move_time(old, new) * SLOW.get(idx, 1.0)))
        angles = tuple(o + (n - o) * p for o, n in zip(old, new))
        hand = name
        if p >= 1:
            angles, fore_len, fore_front = new, 1.0, None
        elif abs(new[1] - old[1]) > 60:
            # the forearm swings towards the camera: it looks shorter mid-move and stays
            # in front of the sleeve, instead of sweeping out sideways at full length
            fore_len = 1 - 0.55 * math.sin(math.pi * p)
            fore_front = max(abs(new[1]), abs(old[1])) > 60
    pose["fore_len"], pose["fore_front"] = fore_len, fore_front
    pose["shoulder"], pose["elbow"], pose["wrist"] = angles
    pose["hand"] = human.hand_shape(hand, angles[0], angles[1])
    # wrist blends continuously from the old gesture's hold to the new one's (a relaxed
    # hand's hold is its gravity droop), so the wrist never snaps when the hand changes
    def hold(name):
        return human.droop(angles[0], angles[1]) if name == "rest" else puppet.GESTURES[name][2]
    q = min(1.0, p) if p < 1 else 1.0
    pose["wrist"] = hold(prev_name) + (hold(cur_name) - hold(prev_name)) * q
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
    pose["moving"] = 0 < p < 1 if CFG.get("hands") and t >= CFG["hands"][0][0] else False
    return human.limits(pose)


def base_cam(t):
    return tuple(track([(k[0], k[j]) for k in CFG["camera"]], t) for j in (1, 2, 3))


def plan(n):
    """Pose + camera for every frame, with the hand kept in shot automatically and the
    human-motion check run on the result. Returns (cams, problems)."""
    import numpy as np
    from scipy.ndimage import gaussian_filter1d, maximum_filter1d
    fps = CFG["fps"]
    poses = [pose_at(i / fps) for i in range(n)]
    base = np.array([base_cam(i / fps) for i in range(n)])
    hb = RIG.head_box()

    def union(a, b):
        return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))
    fit = np.array([STAGE.fit(RIG, tuple(base[i]), hb if poses[i]["hand"] == "rest" else union(RIG.hand_box(poses[i]), hb))
                    for i in range(n)])
    # smooth the camera corrections: hold each correction for the whole move, ease in/out slowly
    d = fit - base
    for j in range(3):
        mag = maximum_filter1d(np.abs(d[:, j]), size=int(fps * 2.0) | 1)
        sign = np.sign(gaussian_filter1d(d[:, j], fps * 0.5) + 1e-9) if j < 2 else 1
        d[:, j] = gaussian_filter1d(sign * mag, fps * 0.5)
    cams = human.limit_camera([STAGE.clamp_cam(tuple(c)) for c in base + d], fps)
    cams = np.array([STAGE.clamp_cam(c) for c in cams])
    frames = [{"t": i / fps, "pose": poses[i], "moving": poses[i]["moving"], "cam": tuple(cams[i]),
               "hand_box": STAGE.to_video(RIG, tuple(cams[i]), RIG.hand_box(poses[i])),
               "head_box": STAGE.to_video(RIG, tuple(cams[i]), hb)} for i in range(n)]
    return [tuple(c) for c in cams], human.check_clip(frames, fps, cam_ok=STAGE.cam_inside)


def plan_corrected(n):
    """Run the check; slow down any arm move that is faster than a person, and repeat."""
    fps = CFG["fps"]
    starts = [h[0] for h in CFG.get("hands", [])]
    for attempt in range(12):
        cams, problems = plan(n)
        fast = [q for q in problems if "jumps" in q]
        if not fast:
            return cams, problems
        for q in fast:
            t = float(q.split("s ")[0])
            idx = max([i for i, t0 in enumerate(starts) if t0 <= t], default=None)
            if idx is not None:
                SLOW[idx] = SLOW.get(idx, 1.0) * 1.15
        nxt = starts[1:] + [CFG["duration"]]
        for idx, f in list(SLOW.items()):      # a move must finish before the next starts
            room = (nxt[idx] - starts[idx]) * 0.95
            base = human.move_time(*(puppet.GESTURES[CFG["hands"][i - 1][1]] if i else puppet.GESTURES["rest"]
                                     for i in (idx,)), puppet.GESTURES[CFG["hands"][idx][1]])
            SLOW[idx] = min(f, room / base)
        print(f"  auto-fix {attempt + 1}: slowed moves {sorted(SLOW)} ({len(fast)} fast frames)")
    return plan(n)


def init(cfg, cues, cams=None, slow=None):
    global CFG, CUES, RIG, STAGE, CAMS
    CFG, CUES, CAMS = cfg, cues, cams
    SLOW.update(slow or {})
    RIG = puppet.Rig()
    STAGE = puppet.Stage(cfg.get("background", "05_field_vertical"), feet=tuple(cfg.get("feet", (0.5, 0.9))))


def render(i):
    t = i / CFG["fps"]
    return STAGE.frame(RIG, pose_at(t), CAMS[i]).tobytes()


def main():
    tl = Path(sys.argv[1])
    out = sys.argv[2]
    cfg = json.loads(tl.read_text())
    cues = json.loads((tl.parent / cfg["mouth"]).read_text())["mouthCues"]
    n = round(cfg["duration"] * cfg["fps"])
    init(cfg, cues)
    cams, problems = plan_corrected(n)
    if problems:
        print("HUMAN-MOTION CHECK FAILED - nothing rendered:")
        for q in problems[:40]:
            print("  ", q)
        sys.exit(2)
    print(f"human-motion check passed: {n} frames, joints in range, no jumps, hand always in shot")
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", "1080x1920", "-framerate", str(cfg["fps"]), "-i", "-",
                           "-i", str(tl.parent / cfg["audio"]), "-map", "0:v", "-map", "1:a",
                           "-c:v", "libx264", "-crf", "17", "-preset", "slow", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out],
                          stdin=subprocess.PIPE)
    with Pool(initializer=init, initargs=(cfg, cues, cams, dict(SLOW))) as pool:
        for k, frame in enumerate(pool.imap(render, range(n), chunksize=2)):
            ff.stdin.write(frame)
            if k % 50 == 0:
                print(f"frame {k}/{n}", flush=True)
    ff.stdin.close()
    ff.wait()
    print("saved", out)
    # review sheet: 10 frames across every arm move, one row per move
    rows = []
    for t0, name in cfg.get("hands", []):
        a = max(0, int(t0 * cfg["fps"]) - 2)
        rows.append(f"between(n\\,{a}\\,{a + 27})*not(mod(n-{a}\\,3))")
    if rows:
        sheet = str(Path(out).with_suffix("")) + "_moves.jpg"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", out, "-vf",
                        f"select='{'+'.join(rows)}',scale=216:-1,tile=10x{len(rows)}", "-frames:v", "1", sheet])
        print("review sheet", sheet)


if __name__ == "__main__":
    main()
