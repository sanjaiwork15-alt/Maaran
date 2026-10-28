"""Window 4B Ep 3 soundtrack (built scene by scene; synthesised + CC0 birds from the Maaran library).

    python window4b/tools/w4b_sound_ep03.py OUT.wav [DURATION]
"""
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

sys.path.insert(0, str(Path(__file__).parent))
from w4b_sound import bp, noise, reverb, tap, stereo, db, SR  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
rng = np.random.default_rng(12)


def main(out, dur):
    N = int(dur * SR); t = np.arange(N) / SR
    mix = np.zeros((N, 2))

    def place(x, at, pan=0.0, gain=1.0):
        i = int(at * SR)
        if i >= N:
            return
        x = x[: N - i]
        mix[i:i + len(x)] += stereo(x, pan) * gain

    # morning city: traffic hum, passing cars, birds, a little wind
    hum = bp(noise(N, "brown"), hi=240)
    passes = np.zeros(N)
    for c in rng.uniform(0, dur, int(dur * 0.5) + 2):
        d = rng.uniform(2.5, 5); i0, i1 = int((c - d / 2) * SR), int((c + d / 2) * SR)
        if 0 <= i0 and i1 < N:
            passes[i0:i1] += np.hanning(i1 - i0) ** 2 * rng.uniform(0.3, 1)
    traffic = hum * 0.4 + bp(noise(N, "pink"), 150, 1100) * passes
    mix += np.stack([traffic * 0.9, traffic], 1) * db(-25)
    mix += stereo(bp(noise(N, "pink"), 180, 1100), 0.2) * db(-34)
    for name, at, g, pan in (("birds_chirps", 0.0, -19, -0.4), ("birds_morning_calls", 1.0, -22, 0.5)):
        b, sr = sf.read(ROOT / f"assets/sound/nature/{name}.wav")
        b = resample_poly(b, SR, sr)[: int(dur * SR)]
        place(b, at, pan, db(g))
    # the bus pulls in: engine swell, then the brake squeal and air hiss at the stop (~5.3 s)
    n = int(5.5 * SR); x = np.arange(n) / SR
    eng = bp(noise(n, "brown"), 40, 300) * (1 + 0.3 * np.sin(2 * np.pi * 7 * x)) * np.minimum(1, x / 1.5) * np.clip((5.3 - x) / 0.6, 0.2, 1)
    place(eng, 0.2, -0.3, db(-22))
    n = int(0.7 * SR); x = np.arange(n) / SR
    squeal = np.sin(2 * np.pi * (2600 - 300 * x) * x) * np.exp(-x * 3) * np.minimum(1, x / 0.05)
    place(bp(squeal, 1500, 5000), 5.0, -0.3, db(-31))
    n = int(1.2 * SR); x = np.arange(n) / SR
    place(bp(noise(n), 2000, 9000) * np.exp(-x * 2.5) * np.minimum(1, x / 0.02), 5.6, -0.3, db(-30))
    # the man: footsteps on a wooden floor (2.0-5.2 s), the mug set down on the sill (6.2 s)
    for at in np.arange(2.1, 5.2, 0.42):
        n = int(0.12 * SR); x = np.arange(n) / SR
        st = bp(noise(n, "brown"), 60, 900) * np.exp(-x * 40) + bp(noise(n), 900, 3000) * np.exp(-x * 90) * 0.3
        place(reverb(st, 0.4, 0.15), at, 0.4 - (at - 2) * 0.1, db(-18))
    clink = tap(1900, 0.12, 0.6) + 0.6 * np.pad(tap(3100, 0.08, 0.4), (0, int(0.04 * SR)))[: int(0.12 * SR)]
    place(reverb(clink, 0.5, 0.2), 6.2, 0.1, db(-16))
    mix *= np.clip(t / 0.3, 0, 1)[:, None]
    mix *= 0.89 / np.abs(mix).max()
    sf.write(out, mix.astype(np.float32), SR, subtype="PCM_24")


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 180.0)
