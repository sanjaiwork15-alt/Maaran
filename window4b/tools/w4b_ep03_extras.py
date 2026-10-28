"""Window 4B Ep 3: the extra beats for the Shorts (same engine, same fixed view, no on-screen text).

    W4B_NO_TEXT=1 python window4b/tools/w4b_ep03_extras.py MASKS_h.npz OUT_DIR

short1_end  (8 s): Day ~30 night – the last lamps and windows go out, the office window flickers once, stays lit
short2_end  (7 s): Month 6 – the deer looks up, a slab of an old facade falls behind the bridge, the deer bolts
"""
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import w4b_ep03 as M  # noqa: E402

BEATS = {
    "short1_end": (8.0, dict(world=77.85, rate=0.06, frac=lambda lt: 0.03 * max(0.0, 1 - lt / 2.0),
                             lamps_off_at=0.8, office=lambda lt: not (3.6 < lt < 3.85))),
    "short2_end": (7.0, dict(world=131.0, rate=1.0, deer_flee=True, crumble=1.4)),
}


def main(masks, out):
    M.init(masks)
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    W, H = M.G["W"], M.G["H"]
    for name, (dur, cfg) in BEATS.items():
        M.EXTRA.clear(); M.EXTRA.update(cfg); M.EXTRA["t0"] = 0.0
        M.G.pop("slab", None)
        ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                               "-s", f"{W}x{H}", "-r", str(M.FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                               "-crf", "16", "-pix_fmt", "yuv420p", str(out / f"{name}.mp4")], stdin=subprocess.PIPE)
        for f in range(int(dur * M.FPS)):
            ff.stdin.write(M.render(f / M.FPS).tobytes())
        ff.stdin.close(); ff.wait()
        print(name, flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
