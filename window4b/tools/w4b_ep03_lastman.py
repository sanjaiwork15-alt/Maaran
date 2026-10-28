"""Window 4B Ep 3 renderer: "What If Everyone Disappeared Except One Man?" (built scene by scene).

    python window4b/tools/w4b_ep03.py MASKS_h.npz OUT.mp4 [--start S --end E] [--still T ...] [--jobs 4]

Same locked 16:9 master and engine as Eps 1-2 (city plate, grade and room from w4b_ep02). The man is
man2.py (locked character); street people are the Ep 1 cartoon people (actors.person).
"""
import argparse
import math
import os
import subprocess
import sys
import tempfile
from multiprocessing import Pool
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import w4b_ep02 as E            # noqa: E402
import w4b_render as R          # noqa: E402
import actors as A              # noqa: E402
import man2 as M                # noqa: E402
import stick as K               # noqa: E402
import story as S               # noqa: E402

G = E.G
FPS = 24
DURATION = 180.0
SILL_Y = 905                    # where his hands rest
MUG2 = (965, 962)              # where he puts his mug down (output px)
MAN_H, MAN_FEET = 1180, 1500
MAN_X = 1250                    # he stands right of centre so the street and the bus stop stay visible


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def lerp(a, b, u):
    return a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u


# ------------------------------------------------------------------ the city (scene 1: alive)

def street_life(canvas, height, t, alive=1.0):
    p = dict(traffic="busy", headlights=0.0, lights=0.0, level=-1.2)
    R.traffic(canvas, t, p, height)
    c = S.Ctx(G, t, p, canvas, height, G["float_mask"])
    # the bus pulls in to the stop and brakes (doors open from 5 s)
    k = ease((t - 0.5) / 5.0)
    bx, by = lerp((455, 575), (680, 726), k)
    G["draw_sprite_at"](c, "bus_road", bx, by)
    G["bus_at"] = (bx, by)
    # people: strolling the riverside walk, one crossing the road, two waiting at the stop
    rng = np.random.default_rng(8)
    for i in range(5):
        u0 = rng.random(); v = (0.012 + 0.01 * rng.random()) * (1 if i % 2 else -1)
        pos = (u0 + v * t) % 1.0
        x, y = lerp(*S.PROMENADE, pos) if i < 3 else lerp(*S.SIDEWALK, pos)
        c.stand(A.person, x, y, shirt=S.SHIRTS[i % 6], skin=S.SKIN[i % 4], phase=t * 6 + i, walking=True)
    x, y = lerp((560, 690), (760, 705), ((t * 0.07) % 1.0))           # crossing
    c.stand(A.person, x, y, shirt=S.SHIRTS[4], skin=S.SKIN[2], phase=t * 6, walking=True)
    for j, xx in enumerate((790, 812)):                                 # waiting at the stop
        c.stand(A.person, xx, 712, shirt=S.SHIRTS[2 + j], skin=S.SKIN[j], walking=False,
                bag=(0.3, 0.3, 0.6) if j else None)


def signal_light(canvas, t):
    """The traffic light at the junction keeps cycling (drawn small, like Ep 1's)."""
    c = S.Ctx(G, t, dict(level=-1.2), canvas, G["height_now"], G["float_mask"])
    ph = t % 8
    c.stand(A.signal, 470, 640, "green" if ph < 4 else ("amber" if ph < 5 else "red"))


# ------------------------------------------------------------------ the man (scene 1)

def man_scene1(f, t):
    """Walks in from the right carrying a mug, puts it on the sill, rests his hands and looks out."""
    if t < 2.0:
        return
    if t < 5.2:                     # walking in, side view facing left, mug held in front
        k = ease((t - 2.0) / 3.2)
        x = 2150 + (MAN_X - 2150) * k
        M.draw(f, x, MAN_FEET, MAN_H, dict(view="side", side_dir=-1, walk=t * 7.5 if k < 0.98 else None,
                                           arms="hold", hold_at=(x - 150, 640)))
        K.mug(f, (x - 150, 682), 2.4, col=(0.75, 0.85, 0.95))
        return
    if t < 6.6:                     # bends to put the mug down
        k = ease((t - 5.2) / 1.0)
        hx, hy = lerp((MAN_X - 150, 640), (MUG2[0], MUG2[1] - 42), k)
        M.draw(f, MAN_X, MAN_FEET, MAN_H, dict(view="side", side_dir=-1, arms="hold", hold_at=(hx, hy)))
        if t < 6.2:
            K.mug(f, (hx, hy + 42), 2.4, col=(0.75, 0.85, 0.95))
        return
    # turns to the window: hands on the sill, looks left then right
    look = 0.0
    if t > 7.6:
        look = -18 * math.sin(min(1.0, (t - 7.6) / 1.2) * math.pi / 2)
    M.draw(f, MAN_X, MAN_FEET, MAN_H, dict(view="back", arms="sill", sill_y=SILL_Y, look=look))


def sill_props(f, t):
    if t >= 6.2:
        K.mug(f, MUG2, 2.4, col=(0.75, 0.85, 0.95))


# ------------------------------------------------------------------ frame

def render(t):
    W, H = G["W"], G["H"]
    day, night = 0.9, 0.0
    city = G["city_img"].copy()
    height = G["height"].copy()
    G["float_mask"] = np.zeros(height.shape, np.float32)
    G["height_now"] = height
    street_life(city, height, t)
    signal_light(city, t)
    city = E.grade(city, day, night)
    sk = E.sky(t, day, night, max(0.0, 1 - day - night), G["city_img"])
    city = city * (1 - G["sky"][..., None]) + sk * G["sky"][..., None]
    pw = dict(level=-1.2, river_mix=0.35, puddles=0.0, water=(0.62, 0.5, 0.38), water_alpha=0.6, rings=0.0)
    city = R.water(city, t, pw, height)
    f = E.room(city, day, night, t)
    sill_props(f, t)
    man_scene1(f, t)
    return (np.clip(f, 0, 1) * 255).astype(np.uint8)


def init(masks):
    E.init(masks)


def render_chunk(args):
    masks, start, end, path = args
    W, H = G["W"], G["H"]
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                           "-crf", "16", "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    for f in range(start, end):
        ff.stdin.write(render(f / FPS).tobytes())
    ff.stdin.close(); ff.wait()
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("masks"); ap.add_argument("out")
    ap.add_argument("--still", type=float, nargs="*")
    ap.add_argument("--jobs", type=int, default=os.cpu_count())
    ap.add_argument("--start", type=float, default=0); ap.add_argument("--end", type=float, default=DURATION)
    a = ap.parse_args()
    if a.still:
        init(a.masks)
        out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
        for t in a.still:
            cv2.imwrite(str(out / f"t{t:06.2f}.png"), render(t))
        return
    n0, n1 = int(a.start * FPS), int(a.end * FPS)
    tmp = Path(tempfile.mkdtemp(dir=Path(a.out).parent))
    k = a.jobs * 2
    b = [n0 + (n1 - n0) * i // k for i in range(k + 1)]
    jobs = [(a.masks, b[i], b[i + 1], str(tmp / f"c{i:03d}.mp4")) for i in range(k)]
    with Pool(a.jobs, initializer=init, initargs=(a.masks,)) as pool:
        for i, _ in enumerate(pool.imap(render_chunk, jobs)):
            print(f"chunk {i + 1}/{k}", flush=True)
    (tmp / "list.txt").write_text("".join(f"file '{j[3]}'\n" for j in jobs))
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"),
                    "-c", "copy", a.out], check=True)
    for j in jobs:
        os.remove(j[3])
    os.remove(tmp / "list.txt"); tmp.rmdir()


if __name__ == "__main__":
    main()
