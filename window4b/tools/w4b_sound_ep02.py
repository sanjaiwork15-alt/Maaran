"""Window 4B Ep 2 soundtrack (synthesised, plus the CC0 birds from the Maaran library).

    python window4b/tools/w4b_sound_ep02.py OUT.wav

Warm everyday city -> construction -> futuristic machines -> back to the opening ambience.
A restrained piano (additive synthesis) from Scene 1, a gentle pulse in Scene 3, a low drone in
Scene 4, a swell in Scene 7 and one unresolved note at the end. Timings follow w4b_ep02.py.
"""
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

sys.path.insert(0, str(Path(__file__).parent))
from w4b_sound import bp, noise, reverb, tap, stereo, db, SR  # noqa: E402

DURATION = 180.0
N = int(DURATION * SR)
ROOT = Path(__file__).resolve().parents[2]
rng = np.random.default_rng(9)
t = np.arange(N) / SR


def place(buf, x, at, pan=0.0, gain=1.0):
    i = int(at * SR)
    if i >= N or i + len(x) <= 0:
        return
    x = x[: N - i]
    buf[i:i + len(x)] += stereo(x, pan) * gain


def env(points):
    ts, vs = zip(*points)
    return np.interp(t, ts, vs)


def piano(f, dur=3.5, vel=1.0):
    n = int(dur * SR); x = np.arange(n) / SR
    s = np.zeros(n)
    for k in range(1, 8):
        fk = f * k * (1 + 0.0004 * k * k)
        s += np.sin(2 * np.pi * fk * x) / k ** 1.4 * np.exp(-x * (0.9 + 0.55 * k))
    s *= np.minimum(1, x / 0.004)
    s += bp(rng.standard_normal(n), 800, 4000) * np.exp(-x * 80) * 0.02
    return s * vel


def note(name):
    names = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}
    pitch, octv = name[:-1], int(name[-1])
    semi = names[pitch[0]] + (1 if "#" in pitch else 0) + (octv - 4) * 12
    return 440.0 * 2 ** (semi / 12)


def main(out):
    mix = np.zeros((N, 2))
    music = np.zeros((N, 2))

    # ---------------- ambience: traffic, wind, river (opening and ending share it)
    city = env([(0, 1), (15, 1), (35, 1.2), (58, 1.1), (80, 0.8), (101.6, 0.8), (101.7, 0), (103.5, 0), (105, 0.6),
                (128, 0.6), (147.3, 0.6), (147.4, 0.1), (151, 0.1), (155, 1), (DURATION, 1)])
    hum = bp(noise(N, "brown"), hi=240)
    passes = np.zeros(N)
    for c in rng.uniform(0, DURATION, 90):
        d = rng.uniform(2.5, 5); i0, i1 = int((c - d / 2) * SR), int((c + d / 2) * SR)
        if 0 <= i0 and i1 < N:
            passes[i0:i1] += np.hanning(i1 - i0) ** 2 * rng.uniform(0.3, 1)
    cars = bp(noise(N, "pink"), 150, 1100) * passes
    future = env([(0, 0), (35, 0), (60, 0.5), (105, 1), (DURATION, 1)])     # cars become electric hums
    epods = bp(noise(N, "pink"), 300, 2500) * passes * 0.6
    traffic = hum * 0.4 + cars * (1 - future) + epods * future
    mix += np.stack([traffic * 0.9, traffic], 1) * (city * db(-24))[:, None]
    gx = np.arange(0, DURATION + 4, 4)
    gust = np.interp(t, gx, rng.uniform(0.3, 1, len(gx)))
    mix += stereo(bp(noise(N, "pink"), 180, 1100) * gust, 0.2) * db(-31)
    lap = bp(noise(N, "brown"), 60, 450) * (0.5 + 0.5 * np.sin(2 * np.pi * t / 3.1)) ** 2
    mix += stereo(lap, -0.3) * db(-30)
    for name, start, gain, pan in (("birds_chirps", 0.0, -20, -0.4), ("birds_morning_calls", 0.4, -24, 0.5),
                                   ("birds_chirps", 155.5, -30, 0.3)):
        b, sr = sf.read(ROOT / f"assets/sound/nature/{name}.wav")
        b = resample_poly(b, SR, sr)[: int(14 * SR)]
        place(mix, b * np.clip(1 - (np.arange(len(b)) / SR - 9) / 5, 0, 1), start, pan, db(gain))
    n = int(0.9 * SR); x = np.arange(n) / SR                                  # a faint horn
    horn = (np.sin(2 * np.pi * 330 * x) + 0.6 * np.sin(2 * np.pi * 415 * x)) * np.minimum(1, x / 0.03) * np.minimum(1, (0.9 - x) / 0.1)
    place(mix, reverb(bp(horn, 200, 2000), 1.5, 0.5), 7.6, 0.5, db(-34))

    # ---------------- Scene 2: construction
    for k, at in enumerate(np.arange(16.5, 33, 0.55)):
        if rng.random() < 0.7:
            n = int(0.15 * SR); x = np.arange(n) / SR
            hit = bp(noise(n), 1500, 7000) * np.exp(-x * 60) + np.sin(2 * np.pi * rng.uniform(900, 1400) * x) * np.exp(-x * 30) * 0.5
            place(mix, reverb(hit, 0.7, 0.3), at, rng.uniform(0.2, 0.8), db(-33))
    for at in np.arange(18.0, 21.4, 0.8):                                     # reversing beeps
        n = int(0.4 * SR); x = np.arange(n) / SR
        place(mix, np.sin(2 * np.pi * 1050 * x) * np.minimum(1, (0.4 - x) / 0.02), at, 0.6, db(-36))
    n = int(1.2 * SR); x = np.arange(n) / SR                                  # the sign comes down
    clank = sum(np.sin(2 * np.pi * f * x) * np.exp(-x * d) for f, d in ((523, 6), (1310, 9), (2210, 14))) / 3
    place(mix, reverb(clank + bp(noise(n), 2000, 8000) * np.exp(-x * 25) * 0.5, 1.0, 0.3), 21.1, 0.6, db(-22))

    # ---------------- Scene 3: electric trains
    for at, dur, pan0, pan1, g in ((44.2, 7.4, 0.9, -0.6, -20), (55.0, 9, -0.8, 0.8, -28), (66, 9, -0.8, 0.8, -29),
                                   (90, 9, -0.8, 0.8, -28), (121.0, 3.5, 0.9, -0.9, -22), (132, 9, -0.8, 0.8, -30)):
        n = int(dur * SR); x = np.arange(n) / SR
        e = np.sin(np.pi * x / dur) ** 1.5
        whine = np.sin(2 * np.pi * (380 + 60 * np.sin(np.pi * x / dur)) * x) * 0.25
        clack = np.zeros(n)
        for c in np.arange(0.1, dur, 0.31):
            clack[int(c * SR):int(c * SR) + 300] += np.hanning(300)
        rumble = bp(noise(n, "brown"), 40, 300) + bp(clack * noise(n), 200, 2000) * 0.6
        s = (rumble + whine) * e
        pan = np.linspace(pan0, pan1, n)
        seg = np.stack([s * np.cos((pan + 1) * np.pi / 4), s * np.sin((pan + 1) * np.pi / 4)], 1)
        i0 = int(at * SR); mix[i0:i0 + n] += seg[: N - i0] * db(g)

    # ---------------- Scene 4: machinery, then only wind
    mach = bp(noise(N, "brown"), 40, 260) * (1 + 0.3 * np.sin(2 * np.pi * 9 * t))
    mix += stereo(mach, 0.5) * (env([(0, 0), (58, 0), (60, 1), (73, 1), (78, 0), (DURATION, 0)]) * db(-24))[:, None]
    for at in rng.uniform(60, 73, 8):
        n = int(0.8 * SR); x = np.arange(n) / SR
        place(mix, reverb(bp(noise(n, "brown"), 30, 200) * np.exp(-x * 6), 1.5, 0.4), at, rng.uniform(0, 0.8), db(-27))

    # ---------------- Scene 5: the demolition machine spares the old building
    hyd = np.sin(2 * np.pi * (220 + 40 * np.sin(2 * np.pi * 0.5 * t)) * t) * 0.3 + bp(noise(N, "brown"), 50, 400)
    mix += stereo(hyd, 0.6) * (env([(0, 0), (82, 0), (83.5, 1), (101.6, 1), (101.65, 0), (DURATION, 0)]) * db(-22))[:, None]
    for at in np.arange(85.3, 95.5, 1.25):
        n = int(1.6 * SR); x = np.arange(n) / SR
        crash = bp(noise(n, "brown"), 30, 250) * np.exp(-x * 4) + bp(noise(n), 400, 6000) * np.exp(-x * 7) * 0.6
        place(mix, reverb(crash, 1.6, 0.4), at, 0.6, db(-18))
    n = int(5 * SR); x = np.arange(n) / SR                                     # dust settling
    place(mix, bp(noise(n), 2000, 9000) * np.exp(-x * 0.7) * np.minimum(1, x / 0.5), 95.5, 0.4, db(-34))
    n = int(1.6 * SR); x = np.arange(n) / SR                                   # motor shutdown
    f = 260 * np.exp(-x * 1.6)
    down = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 2) + bp(noise(n, "brown"), 40, 300) * np.exp(-x * 4)
    place(mix, reverb(down, 1.2, 0.3), 101.6, 0.4, db(-16))
    duck = env([(0, 1), (101.6, 1), (101.8, 0.15), (103.4, 0.15), (105, 1), (DURATION, 1)])

    # ---------------- Scene 6: futuristic hum, billboard
    fut = sum(np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) for f in (55, 82.5, 110)) / 3
    mix += stereo(bp(fut, 40, 300), 0) * (env([(0, 0), (104, 0), (108, 1), (138, 1), (147.3, 0.6), (150, 0), (DURATION, 0)]) * db(-30))[:, None]
    place(mix, tap(900, 0.05, 0.4), 119.2, -0.2, db(-24))

    # ---------------- Scene 7: the last machine
    eng = bp(noise(N, "brown"), 35, 220) * (1 + 0.2 * np.sin(2 * np.pi * 6 * t)) + np.sin(2 * np.pi * 70 * t) * 0.3
    mix += stereo(eng, 0.5) * (env([(0, 0), (139, 0), (141, 0.6), (146, 1), (147.3, 1), (147.35, 0), (DURATION, 0)]) * db(-20))[:, None]
    n = int(2 * SR); x = np.arange(n) / SR
    f = 180 * np.exp(-x * 1.2)
    place(mix, reverb(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 1.5), 1.4, 0.35), 147.3, 0.3, db(-14))
    place(mix, reverb(tap(1700, 0.04, 0.2), 0.6, 0.2), 157.0, 0.35, db(-30))   # quiet click as the window glows

    # ---------------- whoosh and tick at each time jump
    for at in (15, 35, 58, 80, 105, 128):
        n = int(0.9 * SR); x = np.arange(n) / SR
        w = noise(n, "pink"); sweep = np.zeros(n)
        for a in range(0, n, 2400):
            fc = 300 + 2600 * (a / n)
            seg = bp(w[a:a + 4800], fc * 0.7, fc * 1.4)[:2400]
            sweep[a:a + len(seg)] = seg
        sweep *= np.sin(np.pi * x / 0.9) ** 2
        place(mix, reverb(sweep, 0.7, 0.25), at - 0.45, 0, db(-19))
        tick = tap(1150, 0.05, 0.3); tick[:1440] += 0.5 * tap(3300, 0.03, 0.2)
        place(mix, reverb(tick, 0.5, 0.2), at, 0, db(-19))

    # ---------------- music
    melody = [("E4", 1.5), ("A4", 3.2), ("G4", 5.0), ("E4", 6.6), ("D4", 8.6), ("E4", 10.4), ("C5", 12.4), ("B4", 13.6),
              ("A4", 17), ("C5", 21), ("B4", 25), ("G4", 29), ("A4", 33)]
    bass = [("A2", 1.5), ("F2", 6.6), ("C3", 10.4), ("E2", 13.6), ("A2", 17), ("F2", 25), ("E2", 33)]
    for nm, at in melody:
        place(music, piano(note(nm), 4, 0.5), at, 0.15, 1.0)
    for nm, at in bass:
        place(music, piano(note(nm), 6, 0.45), at, -0.2, 1.0)
    for at in np.arange(36, 57.5, 0.6):                                       # the pulse
        nm = "A3" if int((at - 36) / 4.8) % 2 == 0 else "G3"
        place(music, piano(note(nm), 1.2, 0.22), at, -0.1, 1.0)
    for nm, at in (("E5", 37), ("C5", 41.8), ("D5", 46.6), ("B4", 51.4), ("A4", 56)):
        place(music, piano(note(nm), 4, 0.42), at, 0.2, 1.0)
    drone = sum(np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) for f in (55.0, 82.4, 110.2)) / 3
    music += stereo(bp(drone, 40, 400), 0) * env([(0, 0), (58, 0), (62, 0.6), (78, 0.6), (82, 0.25), (101.6, 0.25),
                                                  (101.7, 0), (105, 0), (DURATION, 0)])[:, None] * 0.5
    for nm, at in (("A4", 84), ("G4", 90), ("E4", 97), ("A3", 106), ("E4", 112), ("C4", 122), ("E4", 126)):
        place(music, piano(note(nm), 5, 0.3), at, 0.1, 1.0)
    swell = env([(0, 0), (136, 0), (146.8, 1), (147.3, 0.05), (150, 0), (DURATION, 0)])
    pad = sum(np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) for f in (110, 164.8, 220, 261.6, 329.6, 440)) / 6
    music += stereo(bp(pad, 80, 2000), 0) * swell[:, None] * 0.6
    for nm, at in (("A3", 137), ("E4", 139), ("A4", 141), ("C5", 143), ("E5", 145)):
        place(music, piano(note(nm), 4, 0.45), at, 0.0, 1.0)
    for nm, at, v in (("E4", 158.5, 0.35), ("A4", 163, 0.35), ("B4", 168, 0.4)):  # unresolved: ends on the 2nd
        place(music, piano(note(nm), 9, v), at, 0.1, 1.0)
    place(music, piano(note("A2"), 9, 0.3), 168, -0.2, 1.0)
    music *= env([(0, 1), (101.6, 1), (101.7, 0.2), (104, 1), (119.2, 1), (119.3, 0.4), (124, 0.6), (DURATION, 1)])[:, None]
    music = reverb(music, 2.2, 0.35)

    mix = mix * duck[:, None] + music * db(-15)
    mix *= np.clip(t / 0.1, 0, 1)[:, None] * np.clip((DURATION - t) / 1.5, 0, 1)[:, None]
    mix *= 0.89 / np.abs(mix).max()
    sf.write(out, mix.astype(np.float32), SR, subtype="PCM_24")


if __name__ == "__main__":
    main(sys.argv[1])
