"""Window 4B Ep 4 soundtrack: "What If a Dust Storm Covered the Entire City?" – natural sound only, no music.

    python window4b/tools/w4b_sound_ep04.py OUT.wav

Birds, traffic, horns, breeze -> a low rumble far away -> rising wind, rattling, a deep rush ->
heavy wind, sand on glass, rattling frames -> steady gusts, metal rattles -> sand scraping, creaks, drone
-> muffled wind, window vibration -> gusts fading, loose objects rolling on sand -> soft gusts, one last
gust, silence. Synthesised, plus the CC0 birds from the Maaran library. Timings follow w4b_ep04.py.
"""
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

sys.path.insert(0, str(Path(__file__).parent))
from w4b_sound import bp, noise, reverb, tap, stereo, db, SR  # noqa: E402
from w4b_ep04 import wind, density, night  # noqa: E402

DURATION = 180.0
N = int(DURATION * SR)
ROOT = Path(__file__).resolve().parents[2]
rng = np.random.default_rng(31)
t = np.arange(N) / SR


def env(points):
    ts, vs = zip(*points)
    return np.interp(t, ts, vs)


def curve(fn, rate=20):
    ts = np.arange(0, DURATION + 1 / rate, 1 / rate)
    return np.interp(t, ts, [fn(x) for x in ts])


def main(out):
    mix = np.zeros((N, 2))

    def place(x, at, pan=0.0, gain=1.0):
        i = int(at * SR)
        if i >= N or i < 0:
            return
        x = x[: N - i]
        mix[i:i + len(x)] += stereo(x, pan) * gain

    W = curve(wind)
    D = curve(density)
    inside = env([(0, 0), (114, 0), (120, 1), (140, 1), (150, 0.3), (180, 0.3)])   # Months 2-3: muffled
    # ---- morning: traffic, horns, birds, breeze (gone when the storm hits)
    city = env([(0, 1), (30, 1), (38, 0.6), (41, 0.15), (43, 0), (DURATION, 0)])
    hum = bp(noise(N, "brown"), hi=240)
    passes = np.zeros(N)
    for c in rng.uniform(0, 42, 32):
        d = rng.uniform(2.5, 5); i0, i1 = int((c - d / 2) * SR), int((c + d / 2) * SR)
        if 0 <= i0 and i1 < N:
            passes[i0:i1] += np.hanning(i1 - i0) ** 2 * rng.uniform(0.3, 1)
    traffic = hum * 0.4 + bp(noise(N, "pink"), 150, 1100) * passes
    mix += np.stack([traffic * 0.9, traffic], 1) * (city * db(-17))[:, None]
    for at, f0, pan in ((4.2, 415, 0.5), (13.5, 370, -0.4), (24.0, 440, 0.3)):
        n = int(0.6 * SR); x = np.arange(n) / SR
        horn = (np.sin(2 * np.pi * f0 * x) + 0.6 * np.sin(2 * np.pi * f0 * 1.26 * x)) * np.minimum(1, x / 0.03) * np.minimum(1, (0.6 - x) / 0.1)
        place(reverb(bp(horn, 200, 2500), 1.2, 0.35), at, pan, db(-33))
    for name, at, g, pan, ln in (("birds_chirps", 0.0, -14, -0.4, 14), ("birds_morning_calls", 0.5, -17, 0.5, 13)):
        b, sr = sf.read(ROOT / f"assets/sound/nature/{name}.wav")
        b = resample_poly(b, SR, sr)
        b = np.tile(b, 3)[: int(ln * SR)]
        e = np.minimum(1, np.minimum(np.arange(len(b)) / SR, (len(b) - np.arange(len(b))) / SR / 3))
        place(b * e, at, pan, db(g))
    # the flock takes off and flees at ~12 s: a burst of wingbeats
    n = int(2.5 * SR); x = np.arange(n) / SR
    flap = bp(noise(n), 400, 3000) * (0.5 + 0.5 * np.sin(2 * np.pi * 9 * x)) ** 3 * np.exp(-x * 1.2)
    place(flap, 12.0, 0.3, db(-26))

    # ---- the low rumble far away, growing into a deep rush as the wall comes (Scene 1 end -> Scene 2)
    rumble = bp(noise(N, "brown"), 20, 90, 3)
    mix += stereo(rumble, 0) * (env([(0, 0), (15, 0), (20, 0.25), (32, 0.6), (39, 1.0), (42, 0.7), (64, 0.5), (90, 0.3),
                                      (140, 0.3), (150, 0.1), (180, 0.0)]) * db(-14))[:, None]
    rush = bp(noise(N, "pink"), 120, 900)
    mix += stereo(rush, 0.2) * (env([(0, 0), (30, 0), (37, 0.6), (40.5, 1.0), (43, 0.4), (DURATION, 0.4)]) * db(-18))[:, None]

    # ---- wind: follows the picture's wind, gusty; muffled behind dusty glass in Months 2-3
    gx = np.arange(0, DURATION + 3, 3)
    gust = np.interp(t, gx, rng.uniform(0.45, 1.0, len(gx)))
    wl = bp(noise(N, "pink"), 150, 1400)
    wh = bp(noise(N, "pink"), 1200, 5000)
    wn = W * gust
    mix += stereo(wl, -0.2) * (wn * db(-15))[:, None]
    mix += stereo(wh, 0.3) * (wn * (1 - 0.8 * inside) * db(-24))[:, None]
    howl = np.sin(2 * np.pi * (330 + 60 * np.sin(2 * np.pi * 0.11 * t)) * t) * 0.3
    mix += stereo(bp(howl, 200, 900), 0.4) * (np.clip(wn - 0.6, 0, 1) * db(-30))[:, None]

    # ---- sand hitting the glass: dense crackle following the dust density and wind
    hiss = np.zeros(N); nimp = int(DURATION * 2500)
    pos = rng.integers(0, N, nimp); hiss[pos] = rng.uniform(-1, 1, nimp)
    hiss = bp(hiss, 2500, 10000)
    sandamt = np.clip(D / 3.6, 0, 1) * np.clip(W, 0, 1) * env([(0, 0), (39.5, 0), (41, 1), (DURATION, 1)])
    mix += np.stack([hiss, np.roll(hiss, 131)], 1) * (sandamt * (1 - 0.5 * inside) * db(-21) / (np.abs(hiss).max() + 1e-9) * 6)[:, None]

    # ---- rattles: loose objects on buildings (Scene 2), the window frame (Scene 3 on), metal (Week 2+)
    def rattle(at, f, pan, g, dur=0.5):
        n = int(dur * SR); x = np.arange(n) / SR
        r = sum(np.sin(2 * np.pi * ff * x) * np.exp(-x * dd) for ff, dd in ((f, 9), (f * 2.4, 14), (f * 3.8, 20))) / 3
        place(reverb(r * (rng.random(n) > 0.45), 0.6, 0.3), at, pan, db(g))
    for at in np.arange(30, 41, 0.9):
        if rng.random() < 0.7:
            rattle(at, rng.uniform(500, 900), rng.uniform(-0.7, 0.7), -30)
    for at in np.arange(41, 114, 0.35):                     # window frame rattling in the gusts
        if rng.random() < 0.5 * float(np.interp(at, [41, 64, 90, 114], [1, 0.8, 0.4, 0.6])):
            n = int(0.08 * SR); x = np.arange(n) / SR
            k = bp(noise(n), 200, 2500) * np.exp(-x * 60)
            place(k, at, rng.uniform(-0.9, 0.9), db(-24))
    for at in np.arange(64, 150, 3.1):
        if rng.random() < 0.5:
            rattle(at, rng.uniform(350, 700), rng.uniform(-0.7, 0.7), -29, 0.7)

    # ---- sand scraping on concrete and metal creaks (Week 2 -> Month 1), low drone
    scrape = bp(noise(N), 300, 2500) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.7 * t)) ** 2
    mix += stereo(scrape, -0.3) * (env([(0, 0), (88, 0), (92, 1), (114, 1), (118, 0.3), (150, 0.4), (165, 0), (180, 0)]) * db(-27))[:, None]
    for at in (94.5, 99.0, 104.0, 108.5, 111.5):
        n = int(0.9 * SR); x = np.arange(n) / SR
        f = rng.uniform(70, 120) * (1 + 0.25 * np.sin(2 * np.pi * 2.5 * x))
        saw = 2 * ((np.cumsum(f) / SR) % 1) - 1
        place(reverb(bp(saw * (0.6 + 0.4 * rng.random(n)), 120, 1400) * np.hanning(n), 0.9, 0.35), at, rng.uniform(-0.5, 0.5), db(-25))
    drone = bp(noise(N, "brown"), 40, 160)
    mix += stereo(drone, 0) * (env([(0, 0), (88, 0), (95, 1), (140, 1), (150, 0.2), (180, 0)]) * db(-24))[:, None]

    # ---- Months 2-3: the glass hums and vibrates
    vib = np.sin(2 * np.pi * 62 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.3 * t)) + bp(noise(N), 60, 200) * 0.5
    mix += stereo(vib, 0) * (inside * np.clip(W, 0, 1) * db(-30))[:, None]

    # ---- Month 6: wind fades; loose objects rolling over the sand
    for at, pan in ((143.5, -0.6), (151.0, 0.5), (157.5, -0.2)):
        n = int(2.2 * SR); x = np.arange(n) / SR
        roll = bp(noise(n), 300, 2000) * (0.5 + 0.5 * np.sin(2 * np.pi * 7 * x)) ** 4 * np.hanning(n)
        place(roll, at, pan, db(-29))

    # ---- everything settles to silence; one last gust passes over the sand
    mix *= env([(0, 1), (174.0, 1), (177.0, 0), (DURATION, 0)])[:, None]
    n = int(3.0 * SR); x = np.arange(n) / SR
    last = (bp(noise(n, "pink"), 200, 3000) + bp(noise(n), 2000, 6000) * 0.4) * np.sin(np.pi * x / 3.0) ** 2
    place(last, 175.0, 0.2, db(-14))
    mix *= np.clip(t / 0.2, 0, 1)[:, None]
    mix *= 0.89 / np.abs(mix).max()
    sf.write(out, mix.astype(np.float32), SR, subtype="PCM_24")


if __name__ == "__main__":
    main(sys.argv[1])
