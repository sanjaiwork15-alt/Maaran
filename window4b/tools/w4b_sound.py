"""Window 4B Ep 1 soundtrack, synthesised in code from the same timeline as the picture.

    python window4b/tools/w4b_sound.py OUT.wav

Follows the story: birds and evening traffic, the first taps on the glass, rain that never
stops, wet tyres, rescue-boat outboards, distant sirens, failing streetlights crackling, the
city falling silent, wind and creaking in Month 6, the bridge groaning, cracking and crashing
into the flood, boats and a helicopter during the evacuation, near silence at Year 1, and one
plink in the mug that loops into the first raindrop. Birds are CC0 recordings from the Maaran
library; everything else is synthesised. No music.
"""
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly

sys.path.insert(0, str(Path(__file__).parent))
from timeline import params, DURATION, LIGHTNING, STAGES, COLLAPSE, CLOSEUP, DROP_LANDS  # noqa: E402

SR = 48000
N = int(DURATION * SR)
ROOT = Path(__file__).resolve().parents[2]
rng = np.random.default_rng(4)


def bp(x, lo=None, hi=None, order=2):
    if lo and hi:
        sos = butter(order, [lo, hi], "bandpass", fs=SR, output="sos")
    elif lo:
        sos = butter(order, lo, "highpass", fs=SR, output="sos")
    else:
        sos = butter(order, hi, "lowpass", fs=SR, output="sos")
    return sosfilt(sos, x, axis=0)


def noise(n, colour="white"):
    w = rng.standard_normal(n)
    if colour == "brown":
        w = np.cumsum(w); w = bp(w, lo=15)
    elif colour == "pink":
        f = np.fft.rfft(w); k = np.arange(len(f)); k[0] = 1
        w = np.fft.irfft(f / np.sqrt(k), n)
    return w / (np.abs(w).max() + 1e-9)


def env_from(key, rate=50):
    """A timeline parameter as a per-sample envelope."""
    ts = np.arange(0, DURATION + 1 / rate, 1 / rate)
    v = np.array([params(t)[key] for t in ts], float)
    return np.interp(np.arange(N) / SR, ts, v)


def stereo(x, pan=0.0):
    l = np.cos((pan + 1) * np.pi / 4); r = np.sin((pan + 1) * np.pi / 4)
    return np.stack([x * l, x * r], 1)


def db(x):
    return 10 ** (x / 20)


def place(buf, x, t, pan=0.0, gain=1.0):
    i = int(t * SR)
    if i >= N:
        return
    x = x[: N - i]
    buf[i:i + len(x)] += stereo(x, pan) * gain


def reverb(x, secs=1.2, mix=0.3):
    ir_n = int(secs * SR)
    ir = rng.standard_normal(ir_n) * np.exp(-np.arange(ir_n) / (SR * secs / 6))
    ir = bp(ir, lo=200, hi=6000); ir /= np.abs(ir).sum() / 40
    from scipy.signal import fftconvolve
    wet = fftconvolve(x, ir[:, None] if x.ndim == 2 else ir, axes=0)[: len(x)]
    return x * (1 - mix) + wet * mix


def tap(freq=2600, dur=0.06, bright=1.0):
    t = np.arange(int(dur * SR)) / SR
    s = np.sin(2 * np.pi * freq * t * (1 - 0.15 * t / dur)) * np.exp(-t * 90)
    s += bp(rng.standard_normal(len(t)), lo=2500) * np.exp(-t * 300) * 0.5 * bright
    return s


def envelope(points):
    """Piecewise-linear envelope over the whole episode from (time, value) pairs."""
    ts, vs = zip(*points)
    return np.interp(np.arange(N) / SR, ts, vs)


def outboard(n, f0=24.0):
    """A small outboard motor: a putter of filtered noise pulses over a low buzz."""
    x = np.arange(n) / SR
    wob = 1 + 0.04 * np.sin(2 * np.pi * 0.7 * x)
    ph = np.cumsum(f0 * wob) / SR
    pulse = (np.sin(2 * np.pi * ph) > 0.6).astype(float)
    putt = bp(noise(n) * pulse, 120, 1400)
    buzz = bp(2 * ((ph * 4) % 1) - 1, 80, 900)
    return putt * 0.8 + buzz * 0.25


def siren(n):
    x = np.arange(n) / SR
    f = 720 + 330 * np.sin(2 * np.pi * 0.22 * x)
    ph = np.cumsum(f) / SR
    return bp(np.sin(2 * np.pi * ph) + 0.3 * np.sin(4 * np.pi * ph), 300, 2500)


def main(out):
    mix = np.zeros((N, 2))
    t = np.arange(N) / SR
    rain = env_from("rain"); level = env_from("level")

    # ---- city: traffic hum and passing cars until the water takes the streets -------
    city = envelope([(0, 1), (12, 1), (30, 0.8), (50, 0.45), (72, 0.3), (82, 0.0), (DURATION, 0)])
    hum = bp(noise(N, "brown"), hi=260) * 0.5
    passes = np.zeros(N)
    for k in range(70):
        c = rng.uniform(0, 60); d = rng.uniform(2.5, 5)
        i0, i1 = int((c - d / 2) * SR), int((c + d / 2) * SR)
        if i0 < 0 or i1 >= N:
            continue
        passes[i0:i1] += np.hanning(i1 - i0) ** 2 * rng.uniform(0.3, 1) * (1 if c < 30 else 0.5)
    wet = np.clip((t - 6) / 8, 0, 1)
    car = bp(noise(N, "pink"), 150, 900) * passes * (1 - 0.5 * wet)
    tyres = bp(noise(N), 1500, 7000) * passes * wet * 0.7
    traffic = (hum * 0.5 + car + tyres) * city
    mix += np.stack([traffic * 0.9, traffic], 1) * db(-24)

    # ---- birds at sunset, gone when the rain sets in ---------------------------------
    for name, start, gain, pan in (("birds_chirps", 0.0, -19, -0.4), ("birds_morning_calls", 0.3, -23, 0.5)):
        b, sr = sf.read(ROOT / f"assets/sound/nature/{name}.wav")
        b = resample_poly(b, SR, sr)[: int(10 * SR)]
        e = np.clip(1 - (np.arange(len(b)) / SR - 4.0) / 5.0, 0, 1)
        place(mix, b * e, start, pan, db(gain))

    # ---- wind: gentle, then strong gusts in Month 6 ----------------------------------
    gx = np.arange(0, DURATION + 4, 4)
    gust = np.interp(t, gx, rng.uniform(0.2, 1, len(gx)))
    wind_amt = envelope([(0, 0.3), (12, 0.35), (88, 0.45), (92, 1.0), (110, 1.0), (125, 0.7), (138, 0.4), (DURATION, 0.3)])
    mix += stereo(bp(noise(N, "pink"), 180, 1200) * gust * wind_amt, 0.2) * db(-24)

    # ---- rain: body, roar and hard-surface crackle; muffled for the close-up ---------
    rain_lvl = rain ** 1.3
    body = np.stack([bp(noise(N, "pink"), 300, 9000), bp(noise(N, "pink"), 300, 9000)], 1)
    mix += body * rain_lvl[:, None] * db(-17)
    mix += stereo(bp(noise(N, "brown"), 80, 600), 0) * (np.clip(rain - 0.7, 0, 1) * 2.5)[:, None] * db(-20)
    crack = np.zeros(N); nimp = int(DURATION * 900); pos = rng.integers(0, N, nimp)
    crack[pos] = rng.uniform(-1, 1, nimp)
    crack = bp(crack, 2000, 9000); crack *= rain_lvl / (np.abs(crack).max() + 1e-9)
    mix += np.stack([crack, np.roll(crack, 97)], 1) * db(-16)

    # ---- taps on the glass: the first drops at 2 s, then a patter ----------------------
    for i in range(7):
        place(mix, reverb(tap(2300 + 250 * (i % 3), 0.08), 0.6, 0.2), 2.0 + i * 0.33, (i - 3) * 0.1,
              db(-9 if i == 0 else -15))
    glass = np.zeros((N, 2))
    for tt in np.cumsum(rng.exponential(0.06, int(DURATION / 0.03))):
        if tt >= CLOSEUP:
            break
        pound = 1.4 if 50 <= tt < 70 else 1.0                      # Month 2: rain pounding the glass
        if rng.random() < min(1, params(tt)["drops"] * pound) * (0.2 if tt < 5 else 1):
            place(glass, tap(rng.uniform(1800, 4200), 0.03, 0.6), tt, rng.uniform(-0.8, 0.8), rng.uniform(0.05, 0.25) * pound)
    mix += glass * db(-14)

    # ---- thunder --------------------------------------------------------------------
    for j, lt in enumerate(LIGHTNING):
        delay = (1.4, 0.6, 1.8, 2.2, 0.4, 2.6)[j % 6]
        dur = rng.uniform(4, 7); n = int(dur * SR); tt = np.arange(n) / SR
        rumble = bp(noise(n, "brown"), 25, 180, 3)
        mod = np.interp(tt, np.linspace(0, dur, 14), rng.uniform(0.3, 1, 14))
        th = rumble * np.minimum(tt / 0.15, 1) * np.exp(-tt / (dur / 3)) * mod
        if delay < 1.0:
            th += bp(noise(n), 800, 6000) * np.exp(-tt * 18) * 0.35
        place(mix, reverb(th, 2.0, 0.4), lt + delay, rng.uniform(-0.4, 0.4), db(-7 if delay < 1 else -11))

    # ---- water: drains, rushing around buildings, lapping on concrete --------------------
    drain = np.zeros(N)
    for tt in np.cumsum(rng.exponential(0.09, int(DURATION / 0.05))):
        if tt >= DURATION - 0.2 or tt < 14:
            continue
        n = int(rng.uniform(0.03, 0.09) * SR); x = np.arange(n) / SR
        drain[int(tt * SR):int(tt * SR) + n] += np.sin(2 * np.pi * rng.uniform(180, 520) * x * (1 + 3 * x)) * np.exp(-x * 40)
    mix += stereo(drain * envelope([(0, 0), (14, 0.4), (30, 1), (55, 1), (75, 0.3), (DURATION, 0.15)]), -0.3) * db(-25)
    rush = bp(noise(N, "pink"), 150, 1600) * envelope([(0, 0), (28, 0), (34, 0.6), (70, 1), (95, 0.8), (125, 0.6), (138, 0.25), (DURATION, 0.2)])
    mix += stereo(rush, 0.1) * db(-21)
    lap_env = np.clip(0.5 + 0.5 * np.sin(2 * np.pi * t / 2.7) * np.sin(2 * np.pi * t / 4.1 + 1), 0, 1) ** 2
    lap = bp(noise(N, "brown"), 60, 500) * lap_env * np.clip((level - 1.0) / 0.8, 0, 1)
    mix += stereo(lap, -0.2) * db(-14)

    # ---- rescue boats -------------------------------------------------------------------
    for start, end, gain, pan0, pan1, f0 in ((12.5, 30, -30, 0.7, 0.2, 23), (30, 50, -22, -0.5, -0.2, 26),
                                             (50, 70, -24, 0.3, -0.5, 24), (56, 70, -27, 0.8, 0.3, 21),
                                             (72, 90, -23, -0.4, 0.4, 25), (125, 138.5, -22, -0.7, -0.3, 26),
                                             (125, 138.5, -27, 0.2, 0.7, 22)):
        n = int((end - start) * SR)
        e = np.minimum(1, np.minimum(np.arange(n) / SR / 1.5, (n - np.arange(n)) / SR / 1.5))
        eng = outboard(n, f0) * e
        pan = np.linspace(pan0, pan1, n)
        seg = np.stack([eng * np.cos((pan + 1) * np.pi / 4), eng * np.sin((pan + 1) * np.pi / 4)], 1)
        i0 = int(start * SR); mix[i0:i0 + n] += seg[: N - i0] * db(gain)

    # ---- sirens, far away, fading as the city empties ----------------------------------
    for start, dur, gain in ((33, 9, -31), (44, 7, -33), (53, 10, -32), (62, 7, -36)):
        n = int(dur * SR)
        e = np.hanning(n)
        sg = reverb(siren(n) * e, 2.5, 0.5)
        place(mix, bp(sg, hi=1800), start, rng.uniform(-0.6, 0.6), db(gain))

    # ---- streetlights dying: electrical crackle and buzz --------------------------------
    for k in range(18):
        tt = rng.uniform(71.5, 77)
        n = int(rng.uniform(0.05, 0.3) * SR); x = np.arange(n) / SR
        buzz = np.sign(np.sin(2 * np.pi * 100 * x)) * 0.3 + bp(noise(n), 2000, 9000) * (rng.random(n) > 0.97)
        place(mix, bp(buzz, 80, 8000) * np.exp(-x * 6), tt, rng.uniform(-0.5, 0.5), db(-27))

    # ---- structural creaks in Month 6, then the bridge -----------------------------------
    for tt in (94.0, 99.5, 104.2, 108.0, 112.3):
        n = int(rng.uniform(0.6, 1.0) * SR); x = np.arange(n) / SR
        f = rng.uniform(70, 120) * (1 + 0.25 * np.sin(2 * np.pi * 2.5 * x))
        saw = 2 * ((np.cumsum(f) / SR) % 1) - 1
        cr = bp(saw * (0.6 + 0.4 * rng.random(n)), 120, 1400) * np.hanning(n)
        place(mix, reverb(cr, 0.9, 0.35), tt, rng.uniform(-0.5, 0.5), db(-24))
    n = int(3.2 * SR); x = np.arange(n) / SR                        # the deep groan
    f = 42 + 10 * np.sin(2 * np.pi * 0.4 * x)
    groan = bp(2 * ((np.cumsum(f) / SR) % 1) - 1, 40, 500, 3) * np.hanning(n) * (0.6 + 0.4 * rng.random(n))
    place(mix, reverb(groan, 1.5, 0.45), COLLAPSE["groan"], 0.15, db(-10))
    for k, dt in enumerate((0.0, 0.35, 0.55)):                      # concrete cracking
        n = int(0.4 * SR); x = np.arange(n) / SR
        cr = bp(noise(n), 400, 9000) * np.exp(-x * 14) + bp(noise(n, "brown"), 40, 300) * np.exp(-x * 6)
        place(mix, reverb(cr, 1.2, 0.4), COLLAPSE["crack"] + dt, 0.15, db(-9 if k == 0 else -14))
    n = int(5 * SR); x = np.arange(n) / SR                          # the span hits the water
    boom = np.sin(2 * np.pi * 34 * x) * np.exp(-x * 1.6) + bp(noise(n, "brown"), 25, 220, 3) * np.exp(-x * 0.9)
    spl = bp(noise(n), 300, 9000) * np.exp(-x * 1.4) * np.minimum(x / 0.05, 1)
    place(mix, reverb(boom * 0.9 + spl * 0.7, 2.5, 0.4), COLLAPSE["hit"] - 0.5, 0.15, db(-8))

    # ---- helicopter crossing far away during the evacuation -------------------------------
    n = int(12.5 * SR); x = np.arange(n) / SR
    slap = (0.5 + 0.5 * np.sin(2 * np.pi * 17 * x)) ** 4
    heli = bp(noise(n), 90, 700) * slap + 0.15 * np.sin(2 * np.pi * 1150 * x)
    heli *= np.sin(np.pi * x / x[-1]) ** 1.5
    pan = np.linspace(0.8, -0.8, n)
    seg = np.stack([heli * np.cos((pan + 1) * np.pi / 4), heli * np.sin((pan + 1) * np.pi / 4)], 1)
    i0 = int(125.5 * SR); mix[i0:i0 + n] += bp(seg, hi=2500) * db(-25)

    # ---- whoosh and tick at every time jump ---------------------------------------------------
    for start, label, _ in STAGES[1:]:
        n = int(0.9 * SR); x = np.arange(n) / SR
        w = noise(n, "pink"); sweep = np.zeros(n)
        for a in range(0, n, 2400):
            fc = 300 + 2600 * (a / n)
            seg = bp(w[a:a + 4800], fc * 0.7, fc * 1.4)[:2400]
            sweep[a:a + len(seg)] = seg
        sweep *= np.sin(np.pi * x / 0.9) ** 2
        place(mix, reverb(sweep, 0.7, 0.25), start - 0.45, 0, db(-17))
        tick = tap(1150, 0.05, 0.3); tick[:1440] += 0.5 * tap(3300, 0.03, 0.2)
        place(mix, reverb(tick, 0.5, 0.2), start, 0, db(-17))

    # ---- Year 1 quiet, the close-up, the plink, black -----------------------------------------
    quiet = envelope([(0, 1), (138, 1), (141, 0.6), (CLOSEUP, 0.5), (CLOSEUP + 0.05, 0.3), (DROP_LANDS, 0.3),
                      (DROP_LANDS + 0.02, 0.0), (DURATION, 0.0)])
    mix *= quiet[:, None]
    mix[: int(CLOSEUP * SR)] *= 1
    plink = reverb(tap(2300, 0.09), 1.0, 0.35)                       # same voice as the first drop
    place(mix, plink, DROP_LANDS, 0.0, db(-6))

    fi = np.clip(t / 0.08, 0, 1)
    mix *= fi[:, None]
    mix *= 0.89 / np.abs(mix).max()
    sf.write(out, mix.astype(np.float32), SR, subtype="PCM_24")


if __name__ == "__main__":
    main(sys.argv[1])
