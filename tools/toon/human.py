"""Human-body rules for the 2D Thatha puppet, applied automatically to every frame.

Every animation goes through this before rendering, so no clip can contain a pose or a
movement a real 70-year-old couldn't make:

  limits()        joint ranges: the elbow only bends one way, the wrist and shoulder stay in
                  a natural range; out-of-range angles are clamped (and reported)
  move_time()     arm moves take as long as a real arm needs (bigger moves take longer)
  hand_box()      where the hand is in the video frame, used to keep it fully in shot
  check_clip()    runs every frame: joint limits, speed (no jumps), hand in frame, hand
                  shape changes only while the arm is moving; returns a report

Angles are degrees counter-clockwise on screen for his LEFT arm (viewer's right):
shoulder > 0 lifts the arm out to the side, elbow > 0 bends the forearm up (flexion).
"""
import math

# natural range for an elderly man's left arm in this front view (degrees)
SHOULDER = (-8.0, 40.0)        # slightly in front of the body .. lifted out to the side
ELBOW = (0.0, 165.0)           # straight .. fully bent; never backwards
WRIST = (-70.0, 35.0)          # -70: a relaxed hand drooping fully at the wrist
HAND_TURN = 18.0               # max extra wave/rotation of the hand at the wrist

# speeds: degrees per second a relaxed older person moves at (peak, not average)
MAX_SPEED = {"shoulder": 260.0, "elbow": 520.0, "wrist": 400.0}
MIN_MOVE, MAX_MOVE = 0.30, 0.9 # seconds for one gesture-to-gesture arm move
MAX_HAND_PX = 95.0             # hand travel per frame in the 1080x1920 video (25 fps)
MAX_ZOOM = 0.30                # camera may change its framing height by 30% per second at most
MAX_PAN = 0.35                 # ... and pan by 35% of the frame height per second


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def limits(pose, report=None, t=None):
    """Clamp the arm joints into the human range."""
    for key, (lo, hi) in (("shoulder", SHOULDER), ("elbow", ELBOW), ("wrist", WRIST)):
        if key in pose:
            v = clamp(pose[key], lo, hi)
            if report is not None and abs(v - pose[key]) > 0.5:
                report.append(f"{t:.2f}s {key} {pose[key]:.0f} deg outside {lo:.0f}..{hi:.0f}: clamped")
            pose[key] = v
    if "hand_rot" in pose:
        pose["hand_rot"] = clamp(pose["hand_rot"], -HAND_TURN, HAND_TURN)
    return pose


RAISED_SHAPES = {"wave", "open", "point", "palm"}
OPEN_AT = 135.0                # forearm angle at which a raised hand opens into its gesture


def hand_shape(wanted, shoulder, elbow):
    """The hand shape a real person would show for this arm position: gesture shapes only
    once the forearm is raised, pointing down only while the arm reaches down, otherwise
    a relaxed hand."""
    fore = shoulder + elbow                      # forearm direction: 0 hangs down, 180 straight up
    if wanted in RAISED_SHAPES:
        return wanted if fore >= (60 if wanted == "palm" else OPEN_AT) else "rest"
    if wanted == "point_down":
        return wanted if elbow <= 30 and shoulder >= 14 else "rest"
    return wanted


def droop(shoulder, elbow):
    """Wrist angle for a RELAXED hand: it hangs towards the ground under its own weight
    instead of sticking out in line with the forearm."""
    fore = shoulder + elbow
    sag = clamp(-0.75 * fore, WRIST[0], 0.0)
    # the hand hangs fully while the forearm is level or lower; above that the wrist
    # straightens, fully by OPEN_AT, so the moment the hand opens there is no snap
    k = clamp((OPEN_AT - fore) / (OPEN_AT - 95.0), 0.0, 1.0)
    return sag * k * k * (3 - 2 * k)


def move_time(old, new):
    """Seconds an arm move should take: the joint that turns furthest sets the pace,
    using an ease-in-out curve whose peak speed is 1.5x the average."""
    need = 0.0
    for (o, n), key in zip(zip(old, new), ("shoulder", "elbow", "wrist")):
        need = max(need, 1.5 * abs(n - o) / MAX_SPEED[key])
    return clamp(need, MIN_MOVE, MAX_MOVE)


def limit_camera(cams, fps):
    """Rate-limit a camera path (list of (cx, cy, h)) so it never zooms or pans faster than
    MAX_ZOOM / MAX_PAN, by spreading each change over time (forward and backward pass)."""
    cams = [list(c) for c in cams]
    # backward first: a needed change starts early (anticipation), then forward
    for order in (range(len(cams) - 2, -1, -1), range(1, len(cams))) * 3:
        for i in order:
            j = i - 1 if order.step == 1 else i + 1
            a, b = cams[j], cams[i]
            dh = MAX_ZOOM * 0.95 * a[2] / fps
            b[2] = max(b[2], a[2] - dh)            # only ever widen to meet the limit
            dist = math.dist(a[:2], b[:2])
            lim = MAX_PAN * 0.95 * a[2] / fps
            if dist > lim:
                b[0] = a[0] + (b[0] - a[0]) * lim / dist
                b[1] = a[1] + (b[1] - a[1]) * lim / dist
    return [tuple(c) for c in cams]


def check_clip(frames, fps, frame_size=(1080, 1920), margin=24, cam_ok=None):
    """frames: list of dicts with t, pose, hand_box (x0, y0, x1, y1 in video px or None),
    moving (bool). Returns a list of human-readable problems (empty = clean)."""
    problems = []
    W, H = frame_size
    prev = None
    for f in frames:
        t, p, box = f["t"], f["pose"], f.get("hand_box")
        for key, (lo, hi) in (("shoulder", SHOULDER), ("elbow", ELBOW), ("wrist", WRIST)):
            if key in p and not (lo - 0.5 <= p[key] <= hi + 0.5):
                problems.append(f"{t:.2f}s {key} {p[key]:.0f} deg is not a human angle")
        if cam_ok and not cam_ok(f["cam"]):
            problems.append(f"{t:.2f}s camera goes past the edge of the background")
        hb = f.get("head_box")
        if hb and (hb[0] < 0 or hb[1] < 0 or hb[2] > W or hb[3] > H):
            problems.append(f"{t:.2f}s his face is cut off by the frame edge")
        if prev is not None and f.get("cam") and prev.get("cam"):
            dt = t - prev["t"]
            (x0, y0, h0), (x1, y1, h1) = prev["cam"], f["cam"]
            if abs(h1 - h0) / h0 / dt > MAX_ZOOM:
                problems.append(f"{t:.2f}s camera zooms too fast")
            if math.dist((x0, y0), (x1, y1)) / h0 / dt > MAX_PAN:
                problems.append(f"{t:.2f}s camera pans too fast")
        if box and p.get("hand", "rest") != "rest" and (box[0] < margin or box[1] < margin or box[2] > W - margin or box[3] > H - margin):
            problems.append(f"{t:.2f}s hand leaves the frame {tuple(round(v) for v in box)}")
        if prev is not None:
            dt = t - prev["t"]
            for key in ("shoulder", "elbow", "wrist"):
                if key in p and key in prev["pose"]:
                    v = abs(p[key] - prev["pose"][key]) / dt
                    if v > MAX_SPEED[key] * 1.6:
                        problems.append(f"{t:.2f}s {key} jumps at {v:.0f} deg/s")
            if box and prev.get("hand_box") and p.get("hand") == prev["pose"].get("hand"):
                c0 = ((prev["hand_box"][0] + prev["hand_box"][2]) / 2, (prev["hand_box"][1] + prev["hand_box"][3]) / 2)
                c1 = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
                if math.dist(c0, c1) > MAX_HAND_PX:
                    problems.append(f"{t:.2f}s hand jumps {math.dist(c0, c1):.0f} px in one frame")
            if p.get("hand") == "rest" and not f.get("moving") and p.get("wrist", 0) > droop(p.get("shoulder", 0), p.get("elbow", 0)) + 8:
                problems.append(f"{t:.2f}s relaxed hand sticks out instead of hanging down")
            if p.get("hand") != hand_shape(p.get("hand"), p.get("shoulder", 0), p.get("elbow", 0)):
                problems.append(f"{t:.2f}s {p.get('hand')} hand shape does not fit the arm position")
            if p.get("hand") != prev["pose"].get("hand") and not f.get("moving"):
                problems.append(f"{t:.2f}s hand shape pops ({prev['pose'].get('hand')} -> {p.get('hand')}) while the arm is still")
        prev = f
    return problems
