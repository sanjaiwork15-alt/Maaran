"""Talking / reacting Thatha from ONE approved still frame, all in code (no GPU). 1080x1920, 25 fps.

Usage:
    python tools/toon/talk.py RIG.json SHOT_NAME OUT.mp4

RIG.json:
{
  "frames": {"f_two_s3": {"image": "frames/up/f_two_s3.png",          # 1080x1920 (Real-ESRGAN 1.5x of the 720x1280 frame)
                          "mouth": [[318, 449], [348, 451], [378, 449]],  # mouth line L, mid, R (720x1280 coords)
                          "chin": 545, "beard": [255, 445],              # beard bottom y, beard x span
                          "eyes": [[303, 372, 22, 20], [387, 369, 22, 20]],  # cx, cy, rx, ry
                          "brows": [[300, 335], [390, 330]], "pivot": [350, 560],
                          "head": [350, 380, 150, 190],                  # head ellipse cx, cy, rx, ry
                          "hands": [[120, 540], [590, 540]]}},
  "shots": {"hook": {"frame": "f_two_s3", "audio": "voice_hook.wav", "duration": 7.4, "seed": 1,
                     "brows": [0.3, 4.3]}}                               # extra eyebrow lifts (s)
}
Only small, natural motions on the owner's art (no limb articulation – see docs/video-pipeline-plan.md):
jaw drop + mouth interior from the voice loudness, blinks, eyebrow lifts on phrase starts, a slow head sway with
small nods on stressed syllables, breathing, and a slight hand bob. "mode": "stare" instead makes him squint at
the banana in his hand, brows down, leaning in (no talking). Shot options: "gaze": [[t0, t1, dx, dy], ...] moves his
pupils (720-px units; the head turns a little with them), "shake": [[t0, dur], ...] a playful head shake,
"tears": [[t0, t1], ...] watery eyes and tear drops, "laugh": [[t0, dur], ...] a silent chuckle,
"brows": [t, ...] extra eyebrow lifts, "jaw": max mouth opening (default 12.5;
6 for frames marked "grin": true, whose art already shows an open smile – only the jaw moves there).
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import soundfile as sf

W, H, FPS, K = 1080, 1920, 25, 1.5       # K: rig coords (720x1280) -> output pixels
OUTLINE = (36, 22, 20)                   # BGR of the art's dark brown outline
MOUTH = (22, 22, 60)
TONGUE = (70, 80, 170)


def envelope(path, n, lead=1):
    """Mouth opening 0..1 per video frame from the voice loudness (attack fast, release slower)."""
    x, sr = sf.read(path, always_2d=True)
    x = x.mean(1)
    hop = sr / FPS
    x = np.concatenate([x, np.zeros(int(sr * (n / FPS + 0.1)))])     # shot may run past the clip: silence
    rms = np.array([np.sqrt(np.mean(x[int(i * hop):int(i * hop + 0.05 * sr)] ** 2) + 1e-12) for i in range(n)])
    ref = np.percentile(rms[rms > rms.max() * 0.05], 90)
    o = np.clip((rms / ref - 0.1) / 0.85, 0, 1) ** 0.7
    out = np.zeros(n)
    for i in range(n):
        prev = out[i - 1] if i else 0
        a = 0.65 if o[i] > prev else 0.45
        out[i] = prev + a * (o[i] - prev)
    return np.concatenate([out[lead:], np.zeros(lead)])


def onsets(env, thr=0.25, gap=8):
    """Frames where speech starts after a pause (for nods and brow lifts)."""
    res, quiet = [], gap
    for i, v in enumerate(env):
        if v > thr and quiet >= gap:
            res.append(i)
        quiet = quiet + 1 if v < 0.08 else 0
    return res


def bump(t, t0, rise=0.12, fall=0.5):
    if t < t0:
        return 0.0
    u = t - t0
    return min(1.0, u / rise) * math.exp(-max(0.0, u - rise) / fall)


class Rig:
    def __init__(self, base, fr):
        self.img = cv2.imread(str(base / fr["image"]), cv2.IMREAD_COLOR)
        assert self.img.shape[:2] == (H, W), self.img.shape
        s = lambda p: np.array(p, float) * K  # noqa: E731
        self.mouth = s(fr["mouth"])
        self.chin = fr["chin"] * K
        self.beard = s(fr["beard"])
        self.eyes = [s(e) for e in fr["eyes"]]
        self.brows = [s(b) for b in fr["brows"]]
        self.pivot = s(fr["pivot"])
        self.hands = [s(h) for h in fr.get("hands", [])]
        self.grin = fr.get("grin", False)           # open grin in the art (teeth showing): move the jaw, draw no mouth
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.xx, self.yy = xx, yy
        hc = s(fr["head"])
        m = (((xx - hc[0]) / hc[2]) ** 2 + ((yy - hc[1]) / hc[3]) ** 2 <= 1).astype(np.float32)
        m[yy > self.pivot[1]] = 0
        self.head_w = cv2.GaussianBlur(m, (0, 0), 22)
        # jaw: below the mouth line, fading out at the beard bottom and to the beard sides
        lx, mx, rx = self.mouth[:, 0]
        ly, my, ry = self.mouth[:, 1]
        cx = (lx + rx) / 2
        u = np.clip((xx - lx) / (rx - lx), 0, 1)
        line = (1 - u) ** 2 * ly + 2 * (1 - u) * u * (2 * my - (ly + ry) / 2) + u ** 2 * ry   # quadratic through mid
        below = yy - line
        v = np.clip(below / 4, 0, 1) * np.clip((self.chin + 15 - yy) / ((self.chin - my) * 0.55), 0, 1)
        half = (self.beard[1] - self.beard[0]) / 2
        wx = np.exp(-((xx - cx) / (half * 0.62)) ** 2)
        self.jaw_w = (v * wx).astype(np.float32)
        self.jaw_w[(xx < self.beard[0]) | (xx > self.beard[1])] = 0
        self.brow_w = sum(np.exp(-(((xx - b[0]) / 55) ** 2 + ((yy - b[1]) / 26) ** 2)) for b in self.brows).astype(np.float32)
        self.brow_w[yy > np.mean([e[1] for e in self.eyes]) - 4] *= 0.0
        self.brow_w = cv2.GaussianBlur(self.brow_w, (0, 0), 4)
        self.hand_w = [np.exp(-(((xx - h[0]) / 120) ** 2 + ((yy - h[1]) / 120) ** 2)).astype(np.float32) for h in self.hands]
        self.skin = [self.img[int(e[1] + e[3] + 10), int(e[0])].astype(int).tolist() for e in self.eyes]

    def disp(self, jaw, brow, theta, tx, ty, breath, hands, gaze=(0.0, 0.0)):
        """Total (dx, dy) forward displacement field."""
        xx, yy = self.xx, self.yy
        dx = np.zeros_like(xx)
        dy = jaw * self.jaw_w - brow * self.brow_w
        c, s = math.cos(theta), math.sin(theta)
        px, py = xx - self.pivot[0], yy - self.pivot[1]
        dx += self.head_w * (c * px - s * py - px + tx)
        dy += self.head_w * (s * px + c * py - py + ty)
        for w, (hx, hy) in zip(self.hand_w, hands):
            dx += w * hx
            dy += w * hy
        dx += (breath - 1) * (xx - W / 2) * 0.5
        dy += (breath - 1) * (yy - H)
        return dx, dy

    def at(self, dx, dy, p):
        x, y = int(np.clip(p[0], 0, W - 1)), int(np.clip(p[1], 0, H - 1))
        return np.array([p[0] + dx[y, x], p[1] + dy[y, x]])


def draw_mouth(img, pts, open_px):
    """Dark mouth opening between the (moved) mouth line and the dropped lower lip."""
    if open_px < 1.0:
        return
    (lx, ly), (mx, my), (rx, ry) = pts
    n = 24
    top, bot = [], []
    shrink = 0.12 + 0.1 * (1 - min(1, open_px / 12))
    for i in range(n + 1):
        u = shrink + (1 - 2 * shrink) * i / n
        x = (1 - u) ** 2 * lx + 2 * (1 - u) * u * (2 * mx - (lx + rx) / 2) + u ** 2 * rx
        y = (1 - u) ** 2 * ly + 2 * (1 - u) * u * (2 * my - (ly + ry) / 2) + u ** 2 * ry
        prof = math.sin(math.pi * (i / n)) ** 0.8
        top.append((x, y + 1.5))
        bot.append((x, y + 1.5 + open_px * prof))
    poly = np.array(top + bot[::-1], np.float32)
    S = 4
    x0, y0 = int(poly[:, 0].min()) - 6, int(poly[:, 1].min()) - 6
    x1, y1 = int(poly[:, 0].max()) + 6, int(poly[:, 1].max()) + 6
    patch = np.zeros(((y1 - y0) * S, (x1 - x0) * S), np.uint8)
    q = ((poly - [x0, y0]) * S).astype(np.int32)
    cv2.fillPoly(patch, [q], 255)
    tongue = np.zeros_like(patch)
    if open_px > 6:
        cxm, cym = q[:, 0].mean(), q[len(top):, 1].mean()
        cv2.ellipse(tongue, (int(cxm), int(cym)), (int((q[:, 0].max() - q[:, 0].min()) * 0.28), int(open_px * S * 0.3)),
                    0, 0, 360, 255, -1)
        tongue = cv2.bitwise_and(tongue, patch)
    edge = cv2.morphologyEx(patch, cv2.MORPH_GRADIENT, np.ones((S * 2 + 1, S * 2 + 1), np.uint8))
    sz = (x1 - x0, y1 - y0)
    a_m = cv2.resize(patch, sz, interpolation=cv2.INTER_AREA)[..., None] / 255.0
    a_t = cv2.resize(tongue, sz, interpolation=cv2.INTER_AREA)[..., None] / 255.0
    a_e = cv2.resize(edge, sz, interpolation=cv2.INTER_AREA)[..., None] / 255.0
    roi = img[y0:y1, x0:x1].astype(float)
    roi = roi * (1 - a_m) + np.array(MOUTH) * a_m
    roi = roi * (1 - a_t * 0.9) + np.array(TONGUE) * a_t * 0.9
    roi = roi * (1 - a_e) + np.array(OUTLINE) * a_e
    img[y0:y1, x0:x1] = roi.clip(0, 255).astype(np.uint8)


def draw_gaze(img, c, e, shift):
    """Slide the iris + pupil inside the eye (outline stays put), filling the uncovered part with eye-white."""
    sx, sy = shift
    if abs(sx) < 0.3 and abs(sy) < 0.3:
        return
    cx, cy = c
    rx, ry = e[2] * 0.86, e[3] * 0.86
    ri = min(e[2], e[3]) * 0.72
    x0, y0, x1, y1 = int(cx - rx - 2), int(cy - ry - 2), int(cx + rx + 3), int(cy + ry + 3)
    roi = img[y0:y1, x0:x1].astype(float)
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(float)
    inside = np.clip((1 - np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)) * rx / 1.5, 0, 1)[..., None]
    lum = roi.mean(2)
    white = np.percentile(roi[(inside[..., 0] > 0.5) & (lum > np.percentile(lum, 70))], 60, axis=0) \
        if ((inside[..., 0] > 0.5) & (lum > np.percentile(lum, 70))).any() else np.array([238, 240, 242])
    src = cv2.remap(img, (xx - sx).astype(np.float32), (yy - sy).astype(np.float32), cv2.INTER_CUBIC)
    iris = np.clip((ri - np.sqrt((xx - cx - sx) ** 2 + (yy - cy - sy) ** 2)) / 1.2, 0, 1)[..., None]
    new = white * (1 - iris) + src.astype(float) * iris
    img[y0:y1, x0:x1] = (roi * (1 - inside) + new * inside).clip(0, 255).astype(np.uint8)


def draw_tears(img, c, e, amt, t, side):
    """Watery eye: a wet shine on the lower lid and drops that well up at the outer corner and run down the cheek."""
    if amt < 0.02:
        return
    cx, cy = c
    rx, ry = e[2], e[3]
    over = img.copy()
    cv2.ellipse(over, (int(cx), int(cy + ry * 0.55)), (int(rx * 0.85), int(ry * 0.35)), 0, 10, 170, (255, 236, 205), 3,
                cv2.LINE_AA)
    for k in range(3):                            # a drop every ~0.6 s per eye, 1.3 s down the cheek
        ph = (t * 0.75 + k / 3 + side * 0.17) % 1
        x = cx + side * rx * (0.55 + 0.25 * ph)
        y = cy + ry * 0.95 + ph ** 1.6 * 95 * K
        r = (3.2 + 2.2 * min(1, ph * 3)) * K
        if ph > 0.08:                             # the wet trail it leaves
            cv2.line(over, (int(x - side * 2 * K), int(y - r - 22 * K)), (int(x), int(y - r)), (250, 230, 200),
                     max(1, int(1.2 * K)), cv2.LINE_AA)
        pts = np.array([[x, y - r * 2.1], [x + r, y], [x, y + r], [x - r, y]], np.float32)
        cv2.fillPoly(over, [pts.astype(np.int32)], (250, 222, 180), cv2.LINE_AA)
        cv2.circle(over, (int(x), int(y)), int(r), (250, 222, 180), -1, cv2.LINE_AA)
        cv2.circle(over, (int(x), int(y)), int(r), (200, 150, 90), 1, cv2.LINE_AA)
        cv2.circle(over, (int(x - r * 0.35), int(y - r * 0.35)), max(1, int(r * 0.3)), (255, 255, 255), -1, cv2.LINE_AA)
    cv2.addWeighted(over, 0.85 * amt, img, 1 - 0.85 * amt, 0, img)


def draw_lid(img, c, e, skin, close):
    """Upper eyelid coming down over the eye (close 0..1), skin-coloured with a dark lid line."""
    if close < 0.05:
        return
    cx, cy = c
    rx, ry = e[2] * 1.18, e[3] * 1.25
    S = 4
    x0, y0, x1, y1 = int(cx - rx - 4), int(cy - ry - 4), int(cx + rx + 4), int(cy + ry + 4)
    ell = np.zeros(((y1 - y0) * S, (x1 - x0) * S), np.uint8)
    cv2.ellipse(ell, (int((cx - x0) * S), int((cy - y0) * S)), (int(rx * S), int(ry * S)), 0, 0, 360, 255, -1)
    lid_y = (cy - ry) + close * 2 * ry * 0.92
    yy, xx = np.mgrid[0:ell.shape[0], 0:ell.shape[1]]
    xr = (xx / S + x0 - cx) / rx
    curve = lid_y + 0.25 * ry * (1 - xr ** 2) * close
    cover = ((yy / S + y0) <= curve) & (ell > 0)
    line = (np.abs((yy / S + y0) - curve) <= 1.6) & (ell > 0) & (np.abs(xr) < 0.84)
    sz = (x1 - x0, y1 - y0)
    a_c = cv2.resize(cover.astype(np.uint8) * 255, sz, interpolation=cv2.INTER_AREA)[..., None] / 255.0
    a_l = cv2.resize(line.astype(np.uint8) * 255, sz, interpolation=cv2.INTER_AREA)[..., None] / 255.0
    roi = img[y0:y1, x0:x1].astype(float)
    roi = roi * (1 - a_c) + np.array(skin) * a_c
    roi = roi * (1 - a_l) + np.array(OUTLINE) * a_l
    img[y0:y1, x0:x1] = roi.clip(0, 255).astype(np.uint8)


def main():
    rig_path, name, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    cfg = json.loads(rig_path.read_text())
    base = rig_path.resolve().parent
    shot = cfg["shots"][name]
    rig = Rig(base, cfg["frames"][shot["frame"]])
    n = round(shot["duration"] * FPS)
    rng = np.random.default_rng(shot.get("seed", 1))
    stare = shot.get("mode") == "stare"
    env = np.zeros(n) if stare else envelope(base / shot["audio"], n)
    ons = [] if stare else onsets(env)
    # blinks every 2.5-4.5 s
    blinks, t = [], rng.uniform(0.8, 2.0)
    while t < shot["duration"]:
        blinks.append(t)
        t += rng.uniform(2.5, 4.5)
    brow_t = [o / FPS for o in ons[::2]] + shot.get("brows", [])
    nod_t = [o / FPS for o in ons]
    ph = rng.uniform(0, 6.28, 6)
    ff = subprocess.Popen(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "16",
                           "-preset", "medium", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    jaw_max = shot.get("jaw", 6.0 if rig.grin else 12.5) * K
    for i in range(n):
        t = i / FPS
        jaw = env[i] * jaw_max
        brow = sum(bump(t, b, 0.15, 0.45) for b in brow_t) * 4.5 * K
        theta = math.radians(1.1 * math.sin(2 * math.pi * 0.21 * t + ph[0]) +
                             1.4 * sum(bump(t, b, 0.1, 0.3) for b in nod_t))
        tx = 3.0 * K * math.sin(2 * math.pi * 0.17 * t + ph[1])
        ty = 3.5 * K * sum(bump(t, b, 0.1, 0.3) for b in nod_t)
        breath = 1 + 0.0025 * math.sin(2 * math.pi * 0.25 * t + ph[2])
        talk = float(np.mean(env[max(0, i - 12):i + 1]))
        hands = [(1.5 * K * math.sin(2 * math.pi * 0.3 * t + ph[3 + k]),
                  (2.5 * math.sin(2 * math.pi * 0.37 * t + ph[4 + k]) - 4.5 * talk) * K) for k in range(len(rig.hands))]
        close = max([0.0] + [max(0.0, 1 - abs(t - b) / 0.09) for b in blinks])
        gx = gy = 0.0
        for t0, t1, ex, ey in shot.get("gaze", []):          # look at something: [t0, t1, dx, dy] (720 px)
            u = min(1.0, max(0.0, (t - t0) / 0.15)) * min(1.0, max(0.0, (t1 - t) / 0.15))
            gx += ex * u * K
            gy += ey * u * K
            tx += ex * u * K * 0.9                           # the head follows the eyes a little
            theta += math.radians(ex * u * 0.25)
        cry = 0.0
        for t0, t1 in shot.get("tears", []):                 # watery eyes, drops running down, sad squint
            cry = max(cry, min(1.0, max(0.0, (t - t0) / 0.4)) * min(1.0, max(0.0, (t1 - t) / 0.4)))
        if cry:
            close = max(close, 0.3 * cry)
            brow += 3.0 * K * cry                            # brows up in the middle: a pleading, teary face
            ty += 1.2 * K * cry * math.sin(2 * math.pi * 3.2 * t)   # little sobs
        for t0, dur in shot.get("laugh", []):                # silent chuckle: quick bounce, happy squint
            if t0 <= t <= t0 + dur:
                env_l = math.sin(math.pi * (t - t0) / dur)
                ty += 2.5 * K * env_l * abs(math.sin(2 * math.pi * 2.6 * (t - t0)))
                theta += math.radians(-1.2 * env_l)
                close = max(close, 0.3 * env_l)
                jaw = max(jaw, jaw_max * 0.55 * env_l * (0.6 + 0.4 * math.sin(2 * math.pi * 5.2 * (t - t0))))
        for t0, dur in shot.get("shake", []):                # playful "no-no" head shake
            if t0 <= t <= t0 + dur:
                env_s = math.sin(math.pi * (t - t0) / dur)
                theta += math.radians(2.6 * env_s * math.sin(2 * math.pi * 2.6 * (t - t0)))
                tx += 5 * K * env_s * math.sin(2 * math.pi * 2.6 * (t - t0))
        if stare:
            u = min(1.0, t / 1.2)
            u = u * u * (3 - 2 * u)
            brow = -3.5 * K * u
            theta = math.radians(-1.6 * u + 0.25 * math.sin(2 * math.pi * 0.2 * t))
            tx, ty = -5 * K * u, 3 * K * u
            hands = [(5 * K * u, -7 * K * u)] + hands[1:]
            close = max(close, 0.42 * u)
        dx, dy = rig.disp(jaw, brow, theta, tx, ty, breath, hands)
        frame = cv2.remap(rig.img, (rig.xx - dx).astype(np.float32), (rig.yy - dy).astype(np.float32), cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        # overlays follow the moved face (displacement sampled just above the mouth line / at the eyes)
        dx0, dy0 = rig.disp(0, brow, theta, tx, ty, breath, hands)
        mp = [rig.at(dx0, dy0, p - [0, 3]) + [0, 3] for p in rig.mouth]
        if not rig.grin:
            draw_mouth(frame, mp, jaw)
        for e, skin in zip(rig.eyes, rig.skin):
            draw_gaze(frame, rig.at(dx0, dy0, e[:2]), e, (gx, gy))
            draw_lid(frame, rig.at(dx0, dy0, e[:2]), e, skin, close)
        for side, e in zip((-1, 1), sorted(rig.eyes, key=lambda q: q[0])):
            draw_tears(frame, rig.at(dx0, dy0, e[:2]), e, cry, t, side)
        ff.stdin.write(frame.tobytes())
    ff.stdin.close()
    ff.wait()
    print("saved", out)


if __name__ == "__main__":
    main()
