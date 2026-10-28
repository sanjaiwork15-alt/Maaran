"""Window 4B Ep 3 soundtrack: "What If the Entire City Became Empty Overnight?"

    python window4b/tools/w4b_sound_ep03.py OUT.wav

Synthesised, plus the CC0 birds from the Maaran library. Follows w4b_ep03.py's timeline:
alive morning -> evening fading to one horn and a hum -> the empty Day 2 (signal clicks, fountain,
hum) -> failing lights (buzz, relays, a transformer pop) -> storm and rattling metal -> wildlife
(birdsong, insects, leaves) -> Day 365 (wind, water under the bridge, a creaking sign) -> one bird call,
flowing water, silence. Gentle music, sparse later.
"""
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

sys.path.insert(0, str(Path(__file__).parent))
from w4b_sound import bp, noise, reverb, tap, stereo, db, SR  # noqa: E402
from w4b_sound_ep02 import piano, note  # noqa: E402

DURATION = 180.0
N = int(DURATION * SR)
ROOT = Path(__file__).resolve().parents[2]
rng = np.random.default_rng(21)
t = np.arange(N) / SR


def env(points):
    ts, vs = zip(*points)
    return np.interp(t, ts, vs)


def main(out):
    mix = np.zeros((N, 2))
    music = np.zeros((N, 2))

    def place(buf, x, at, pan=0.0, gain=1.0):
        i = int(at * SR)
        if i >= N or i < 0:
            return
        x = x[: N - i]
        buf[i:i + len(x)] += stereo(x, pan) * gain

    def birds(name, at, gain, pan, length, fade_from=None):
        b, sr = sf.read(ROOT / f"assets/sound/nature/{name}.wav")
        b = resample_poly(b, SR, sr)
        reps = int(np.ceil(length * SR / len(b)))
        b = np.tile(b, reps)[: int(length * SR)]
        e = np.minimum(1, np.minimum(np.arange(len(b)) / SR / 1.0, (len(b) - np.arange(len(b))) / SR / 1.5))
        place(mix, b * e, at, pan, db(gain))

    # ---- city life (Day 1), fading through the evening; nothing after midnight
    city = env([(0, 1), (20, 1), (30, 0.8), (35, 0.5), (39.6, 0.15), (40.5, 0), (DURATION, 0)])
    hum = bp(noise(N, "brown"), hi=240)
    passes = np.zeros(N)
    for c in rng.uniform(0, 40, 60):
        d = rng.uniform(2.5, 5); i0, i1 = int((c - d / 2) * SR), int((c + d / 2) * SR)
        if 0 <= i0 and i1 < N:
            passes[i0:i1] += np.hanning(i1 - i0) ** 2 * rng.uniform(0.3, 1) * (1 if c < 30 else 0.4)
    traffic = hum * 0.4 + bp(noise(N, "pink"), 150, 1100) * passes
    mix += np.stack([traffic * 0.9, traffic], 1) * (city * db(-23))[:, None]
    for at, f0, pan in ((3.4, 415, 0.5), (11.0, 370, -0.4), (16.5, 440, 0.3), (36.5, 392, 0.6)):   # horns
        n = int(0.7 * SR); x = np.arange(n) / SR
        horn = (np.sin(2 * np.pi * f0 * x) + 0.6 * np.sin(2 * np.pi * f0 * 1.26 * x)) * np.minimum(1, x / 0.03) * np.minimum(1, (0.7 - x) / 0.1)
        place(mix, reverb(bp(horn, 200, 2500), 2.0 if at > 30 else 1.0, 0.5 if at > 30 else 0.3), at, pan,
              db(-30 if at > 30 else -33))
    n = int(8 * SR); x = np.arange(n) / SR                      # the bus pulls up and stops at the signal
    eng = bp(noise(n, "brown"), 40, 320) * (1 + 0.3 * np.sin(2 * np.pi * 7 * x)) * np.minimum(1, x / 1.5)
    eng *= np.clip((7.0 - x) / 1.0, 0.25, 1)
    place(mix, eng, 5.5, -0.4, db(-22))
    n = int(0.6 * SR); x = np.arange(n) / SR
    place(mix, bp(np.sin(2 * np.pi * (2500 - 300 * x) * x) * np.exp(-x * 3), 1500, 5000), 12.2, -0.4, db(-32))
    place(mix, bp(noise(int(1.1 * SR)), 2000, 9000) * np.exp(-np.arange(int(1.1 * SR)) / SR * 2.5), 12.8, -0.4, db(-31))
    birds("birds_chirps", 0.0, -19, -0.4, 20)
    birds("birds_morning_calls", 1.0, -23, 0.5, 18)

    # ---- breeze throughout; strong in the storm
    gx = np.arange(0, DURATION + 4, 4)
    gust = np.interp(t, gx, rng.uniform(0.3, 1, len(gx)))
    wind = env([(0, 0.4), (40, 0.6), (90, 0.7), (92, 1.4), (100, 1.4), (102, 0.7), (DURATION, 0.7)])
    mix += stereo(bp(noise(N, "pink"), 180, 1100) * gust * wind, 0.2) * db(-30)

    # ---- the empty city: electrical hum, signal clicks, the fountain
    ehum = (np.sin(2 * np.pi * 50 * t) + 0.5 * np.sin(2 * np.pi * 100 * t) + 0.3 * np.sin(2 * np.pi * 150 * t))
    mix += stereo(bp(ehum, 40, 400), 0) * (env([(0, 0), (38, 0), (41, 1), (66, 1), (85, 0.3), (104, 0), (DURATION, 0)])
                                           * db(-35))[:, None]
    for at in np.arange(41, 103, 2.0):                             # the signal relay clicks for empty roads
        if at > 66 and at % 8 > 0.5:
            continue
        place(mix, tap(1400, 0.03, 0.2), at, -0.5, db(-30))
    fnt = bp(noise(N), 800, 6000) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.5 * t))
    mix += stereo(fnt, 0.5) * (env([(0, 0.25), (40, 0.25), (41, 1), (66, 1), (80, 0), (DURATION, 0)]) * db(-36))[:, None]

    # ---- lights failing (Days 7-30): buzz, relay clicks, a transformer pop, then silence
    for at in (62.0, 62.4, 62.8, 70.9, 78.8, 81.4, 81.7):
        n = int(0.25 * SR); x = np.arange(n) / SR
        buzz = np.sign(np.sin(2 * np.pi * 100 * x)) * 0.3 + bp(noise(n), 2000, 8000) * (rng.random(n) > 0.95)
        place(mix, bp(buzz, 80, 8000) * np.exp(-x * 6), at, rng.uniform(-0.5, 0.5), db(-27))
        place(mix, tap(900, 0.03, 0.3), at + 0.2, 0, db(-30))
    n = int(1.5 * SR); x = np.arange(n) / SR
    pop = bp(noise(n), 300, 6000) * np.exp(-x * 18) + np.sin(2 * np.pi * 70 * x) * np.exp(-x * 5) * 0.6
    place(mix, reverb(pop, 1.8, 0.5), 71.2, 0.3, db(-17))

    # ---- storm (Month 3): rain, thunder, rushing gutters, loose metal
    storm = env([(0, 0), (91, 0), (93, 1), (99, 1), (101, 0), (DURATION, 0)])
    rain = np.stack([bp(noise(N, "pink"), 300, 9000), bp(noise(N, "pink"), 300, 9000)], 1)
    mix += rain * (storm * db(-16))[:, None]
    mix += stereo(bp(noise(N, "pink"), 150, 1500), 0.1) * (storm * db(-24))[:, None]
    for lt, delay in ((94.2, 0.4), (97.1, 1.6)):
        dur = 6; n = int(dur * SR); x = np.arange(n) / SR
        th = bp(noise(n, "brown"), 25, 180, 3) * np.minimum(x / 0.15, 1) * np.exp(-x / 2)
        if delay < 1:
            th += bp(noise(n), 800, 6000) * np.exp(-x * 18) * 0.35
        place(mix, reverb(th, 2.0, 0.4), lt + delay, 0.2, db(-8))
    for at in np.arange(86, 135, 2.3):                              # a loose sign / metal rattles
        if rng.random() < 0.6:
            n = int(0.5 * SR); x = np.arange(n) / SR
            r = sum(np.sin(2 * np.pi * f * x) * np.exp(-x * dd) for f, dd in ((640, 9), (1530, 14), (2410, 20))) / 3
            place(mix, reverb(r * (rng.random(n) > 0.4), 0.7, 0.3), at, -0.6, db(-31))

    # ---- wildlife (Month 6 on): birdsong grows, insects, leaves; a dog's paws
    birds("birds_chirps", 108, -21, -0.3, 40)
    birds("birds_morning_calls", 112, -24, 0.5, 30)
    birds("bed_forest_birds", 115, -22, 0.0, 50)
    birds("crickets_kollam", 150, -27, 0.2, 18)
    birds("leaves_rustling", 110, -27, 0.4, 55)
    insects = bp(noise(N), 4000, 7000) * (0.5 + 0.5 * np.sin(2 * np.pi * 9 * t)) ** 4
    mix += stereo(insects, 0.3) * (env([(0, 0), (110, 0), (118, 1), (165, 0.6), (170, 0), (DURATION, 0)]) * db(-36))[:, None]
    water = bp(noise(N, "brown"), 60, 700) * (0.6 + 0.4 * np.sin(2 * np.pi * t / 3.3)) ** 2
    mix += stereo(water, -0.2) * (env([(0, 0.2), (110, 0.3), (140, 0.8), (DURATION, 1.0)]) * db(-29))[:, None]
    for at in (138.0, 146.5, 155.0, 161.0):                          # a loose sign creaks
        n = int(0.8 * SR); x = np.arange(n) / SR
        f = 110 * (1 + 0.25 * np.sin(2 * np.pi * 2.5 * x))
        saw = 2 * ((np.cumsum(f) / SR) % 1) - 1
        place(mix, reverb(bp(saw * (0.6 + 0.4 * rng.random(n)), 150, 1500) * np.hanning(n), 0.8, 0.3), at, -0.5, db(-29))

    # ---- the last streetlight: two flicker buzzes and a click (Scene 8)
    for at in (166.2, 167.0, 168.2):
        n = int(0.2 * SR); x = np.arange(n) / SR
        place(mix, bp(np.sign(np.sin(2 * np.pi * 100 * x)) * 0.3, 80, 4000) * np.exp(-x * 10), at, -0.4, db(-28))
    place(mix, tap(1700, 0.04, 0.2), 168.2, -0.4, db(-26))

    # ---- whoosh and tick at each marker
    for at in (20, 40, 60, 72, 85, 110, 135):
        n = int(0.9 * SR); x = np.arange(n) / SR
        w = noise(n, "pink"); sweep = np.zeros(n)
        for a in range(0, n, 2400):
            fc = 300 + 2600 * (a / n)
            seg = bp(w[a:a + 4800], fc * 0.7, fc * 1.4)[:2400]
            sweep[a:a + len(seg)] = seg
        sweep *= np.sin(np.pi * x / 0.9) ** 2
        place(mix, reverb(sweep, 0.7, 0.25), at - 0.45, 0, db(-21))
        tick = tap(1150, 0.05, 0.3); tick[:1440] += 0.5 * tap(3300, 0.03, 0.2)
        place(mix, reverb(tick, 0.5, 0.2), at, 0, db(-21))

    # ---- music: gentle at first, sparse and uneasy as the lights fail, melancholic in the storm,
    #      warmer with the animals, reflective at Day 365, one unresolved note at the end
    for nm, at, v in (("C4", 1.0, 0.45), ("E4", 3.0, 0.4), ("G4", 5.0, 0.4), ("E4", 7.5, 0.35), ("D4", 10.0, 0.4),
                      ("F4", 12.0, 0.35), ("A4", 14.0, 0.4), ("G4", 17.0, 0.4), ("E4", 21, 0.35), ("C4", 25, 0.35),
                      ("A3", 30, 0.3), ("E4", 35, 0.25)):
        place(music, piano(note(nm), 4, v), at, 0.15)
    for nm, at in (("C3", 1.0), ("F2", 10.0), ("A2", 21), ("E2", 30)):
        place(music, piano(note(nm), 6, 0.4), at, -0.2)
    for nm, at, v in (("B3", 63, 0.25), ("F4", 69, 0.22), ("E4", 76, 0.25), ("A3", 86, 0.3), ("C4", 92, 0.28),
                      ("B3", 98, 0.28), ("A3", 104, 0.3)):
        place(music, piano(note(nm), 5, v), at, 0.1)
    for nm, at, v in (("C4", 111, 0.3), ("E4", 114, 0.3), ("G4", 117, 0.32), ("A4", 121, 0.3), ("G4", 125, 0.3),
                      ("E4", 129, 0.32), ("C4", 136, 0.3), ("D4", 141, 0.28), ("E4", 146, 0.3), ("C4", 152, 0.28),
                      ("A3", 158, 0.28)):
        place(music, piano(note(nm), 5, v), at, 0.15)
    for nm, at in (("C3", 111), ("A2", 121), ("F2", 136), ("C3", 146), ("A2", 158)):
        place(music, piano(note(nm), 7, 0.35), at, -0.2)
    place(music, piano(note("D4"), 9, 0.3), 170.0, 0.1)          # unresolved
    pad = sum(np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) for f in (130.8, 196.0, 261.6)) / 3
    music += stereo(bp(pad, 80, 1500), 0) * env([(0, 0.25), (20, 0.25), (40, 0.05), (60, 0), (110, 0), (115, 0.2),
                                                  (165, 0.2), (170, 0), (DURATION, 0)])[:, None] * 0.4
    music = reverb(music, 2.2, 0.35)

    # ---- ending: one bird call, flowing water, then silence
    b, sr = sf.read(ROOT / "assets/sound/nature/birds_chirps.wav")
    b = resample_poly(b, SR, sr)[int(2.0 * SR):int(3.2 * SR)]
    place(mix, b * np.hanning(len(b)), 174.5, 0.3, db(-18))
    mix = mix + music * db(-14)
    fade = env([(0, 1), (175, 1), (178.5, 0.0), (DURATION, 0)])
    mix *= fade[:, None]
    mix *= np.clip(t / 0.2, 0, 1)[:, None]
    mix *= 0.89 / np.abs(mix).max()
    sf.write(out, mix.astype(np.float32), SR, subtype="PCM_24")


if __name__ == "__main__":
    main(sys.argv[1])
