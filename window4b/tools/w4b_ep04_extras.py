"""Window 4B Ep 4: extra beats for the Shorts (same engine, same fixed view, no on-screen text).

    W4B_NO_TEXT=1 python window4b/tools/w4b_ep04_extras.py MASKS_h.npz OUT_DIR

short1_end  (8 s): Day 1 afternoon – the wind drops for a moment; roads, cars and buildings under thick sand
short2_end  (7 s): Month 6 – the city emerging, then a new wall of dust sweeps across the whole view
short3_end (18 s): Year 1 – a final gust sweeps dust over the skyline, then the settled view holds and fades
"""
import sys
from pathlib import Path

import numpy as np
import subprocess

sys.path.insert(0, str(Path(__file__).parent))
import w4b_ep04 as M  # noqa: E402

ip = lambda xs, ys: (lambda lt: float(np.interp(lt, xs, ys)))

BEATS = {
    "short1_end": (8.0, dict(world=60.0, rate=1.0, density=ip([0, 3.0, 8], [3.6, 0.85, 0.75]),
                             wind=ip([0, 3, 8], [1.0, 0.35, 0.3]), coat=lambda lt: 0.6,
                             sand=lambda lt: 0.9)),
    "short2_end": (7.0, dict(world=150.0, rate=1.0, wind=ip([0, 0.8, 2.0, 7], [0.35, 0.4, 1.0, 1.0]),
                             front=lambda lt: (-0.2 + 1.5 * min(1.0, max(0.0, (lt - 0.8) / 3.2)), 4.0, 1))),
    "short3_end": (18.0, dict(world=168.0, rate=0.3, wind=ip([0, 1.5, 3, 7, 9, 18], [0.15, 0.2, 1.0, 1.0, 0.2, 0.15]),
                              front=lambda lt: (1.2 - 1.5 * min(1.0, max(0.0, (lt - 1.5) / 3.5)),
                                                3.0 * float(np.interp(lt, [1.5, 5, 7, 9.5], [1, 1, 0.6, 0])), -1),
                              sand=ip([0, 5, 9, 18], [2.9, 2.9, 3.15, 3.15]), fade_at=16.4)),
}


def main(masks, out):
    M.init(masks)
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    W, H = M.G["W"], M.G["H"]
    for name, (dur, cfg) in BEATS.items():
        M.EXTRA.clear(); M.EXTRA.update(cfg)
        ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                               "-s", f"{W}x{H}", "-r", str(M.FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                               "-crf", "16", "-pix_fmt", "yuv420p", str(out / f"{name}.mp4")], stdin=subprocess.PIPE)
        for f in range(int(round(dur * M.FPS))):
            ff.stdin.write(M.render(f / M.FPS).tobytes())
        ff.stdin.close(); ff.wait()
        print(name, flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
