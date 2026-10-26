"""Window 4B Ep 1 soundtrack, synthesised in code from the same timeline as the picture.

    python window4b/tools/w4b_sound.py OUT.wav

Layers: city traffic (fades out by Month 3), birds (Day 1 only, CC0 recordings from the Maaran
library), rain body + hard-surface crackle + taps on the glass, thunder after each lightning,
drains/rushing/lapping water, wind gusts, creaking branches, the whoosh-and-tick at every time
jump, drips into the mug, and a very soft pad in the last scene. No other recordings are used.
"""
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly

sys.path.insert(0, str(Path(__file__).parent))
from timeline import params, DURATION, LIGHTNING, STAGES, DRIPS_FROM, DRIP_EVERY  # noqa: E402

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


def main(out):
    mix = np.zeros((N, 2))
    t = np.arange(N) / SR
    rain = env_from("rain"); drops = env_from("drops"); level = env_from("level")

    # ---- city: distant traffic hum, passing cars, wet tyres --------------------
    city = np.clip(1 - np.clip((t - 55) / 22, 0, 1), 0, 1) * np.where(t < 30, 1, 0.7)
    hum = bp(noise(N, "brown"), hi=260) * 0.5
    passes = np.zeros(N)
    for k in range(60):
        c = rng.uniform(0, 80); d = rng.uniform(2.5, 5)
        i0, i1 = int((c - d / 2) * SR), int((c + d / 2) * SR)
        if i0 < 0 or i1 >= N:
            continue
        e = np.hanning(i1 - i0) ** 2
        passes[i0:i1] += e * rng.uniform(0.3, 1)
    wetness = np.clip((t - 4) / 10, 0, 1)
    car = bp(noise(N, "pink"), 150, 900) * passes * (1 - 0.5 * wetness)
    hiss = bp(noise(N), 1500, 7000) * passes * wetness * 0.6
    traffic = (hum * 0.5 + car + hiss) * city
    mix += np.stack([traffic * 0.9, traffic], 1) * db(-24)

    # ---- birds: Day 1 only, fading as the rain starts -------------------------
    for name, start, gain, pan in (("birds_chirps", 0.0, -20, -0.4), ("birds_morning_calls", 0.3, -24, 0.5)):
        b, sr = sf.read(ROOT / f"assets/sound/nature/{name}.wav")
        b = resample_poly(b, SR, sr)[: int(9 * SR)]
        e = np.clip(1 - (np.arange(len(b)) / SR - 3.0) / 5.0, 0, 1)
        place(mix, b * e, start, pan, db(gain))

    # ---- wind -------------------------------------------------------------------
    gx = np.arange(0, DURATION + 4, 4)
    gust = np.interp(t, gx, rng.uniform(0.2, 1, len(gx)))
    wind_amt = 0.25 + 0.75 * np.clip((t - 80) / 30, 0, 1)
    wind = bp(noise(N, "pink"), 200, 1200) * gust * wind_amt
    mix += stereo(wind, 0.2) * db(-27)

    # ---- rain body (steady shower -> roar) and hard-surface crackle -------------
    body = bp(noise(N, "pink"), 300, 9000)
    roar = bp(noise(N, "brown"), 80, 600)
    L = np.stack([body, bp(noise(N, "pink"), 300, 9000)], 1)
    rain_lvl = rain ** 1.3
    mix += L * rain_lvl[:, None] * db(-17)
    mix += stereo(roar, 0) * (np.clip(rain - 0.7, 0, 1) * 2.5)[:, None] * db(-20)
    crack = np.zeros(N)
    nimp = int(DURATION * 900)
    pos = rng.integers(0, N, nimp)
    crack[pos] = rng.uniform(-1, 1, nimp)
    crack = bp(crack, 2000, 9000)
    crack *= rain_lvl / (np.abs(crack).max() + 1e-9)
    mix += np.stack([crack, np.roll(crack, 97)], 1) * db(-16)

    # ---- taps on the glass: the opening drops, then a patter that follows the drops
    for i in range(7):
        place(mix, reverb(tap(2300 + 250 * (i % 3), 0.08), 0.6, 0.2), 1.0 + i * 0.45, (i - 3) * 0.1,
              db(-10 if i == 0 else -16))
    glass = np.zeros((N, 2))
    k = 0
    for tt in np.cumsum(rng.exponential(0.06, int(DURATION / 0.03))):
        if tt >= DURATION:
            break
        if rng.random() < params(min(tt, DURATION - 0.01))["drops"] * (0.25 if tt < 6 else 1):
            place(glass, tap(rng.uniform(1800, 4200), 0.03, 0.6), tt, rng.uniform(-0.8, 0.8), rng.uniform(0.05, 0.25))
            k += 1
    mix += glass * db(-14)

    # ---- thunder after each lightning ------------------------------------------
    for j, lt in enumerate(LIGHTNING):
        delay = (0.6, 1.8, 0.4, 2.4, 1.2, 0.9)[j % 6]
        dur = rng.uniform(4, 7)
        n = int(dur * SR); tt = np.arange(n) / SR
        rumble = bp(noise(n, "brown"), 25, 180, 3)
        mod = np.interp(tt, np.linspace(0, dur, 14), rng.uniform(0.3, 1, 14))
        e = np.minimum(tt / 0.15, 1) * np.exp(-tt / (dur / 3)) * mod
        th = rumble * e
        if delay < 1.0:  # near strike: a crack first
            cr = bp(noise(n), 800, 6000) * np.exp(-tt * 18)
            th += cr * 0.35
        place(mix, reverb(th, 2.0, 0.4), lt + delay, rng.uniform(-0.4, 0.4), db(-6 if delay < 1 else -10))

    # ---- water: drains, rushing street water, lapping against walls -------------
    drain = np.zeros(N)
    for tt in np.cumsum(rng.exponential(0.09, int(DURATION / 0.05))):
        if tt >= DURATION - 0.2 or tt < 25:
            continue
        n = int(rng.uniform(0.03, 0.09) * SR); x = np.arange(n) / SR
        f0 = rng.uniform(180, 520)
        drain[int(tt * SR):int(tt * SR) + n] += np.sin(2 * np.pi * f0 * x * (1 + 3 * x)) * np.exp(-x * 40)
    drain_amt = np.clip((t - 28) / 6, 0, 1) * np.clip(1 - (t - 85) / 15, 0.15, 1)
    mix += stereo(drain * drain_amt, -0.3) * db(-26)
    rush = bp(noise(N, "pink"), 150, 1600) * np.clip((level - 0.4) * 1.5, 0, 1) * np.clip(1 - (t - 100) / 20, 0.35, 1)
    mix += stereo(rush, 0.1) * db(-21)
    lap_env = 0.5 + 0.5 * np.sin(2 * np.pi * t / 2.7) * np.sin(2 * np.pi * t / 4.1 + 1)
    lap = bp(noise(N, "brown"), 60, 500) * np.clip(lap_env, 0, 1) ** 2 * np.clip((level - 1.4) / 0.6, 0, 1)
    mix += stereo(lap, -0.2) * db(-14)

    # ---- creaking branches in the last months -----------------------------------
    for tt in (108.5, 113.2, 119.6, 126.0, 133.5):
        n = int(rng.uniform(0.5, 0.9) * SR); x = np.arange(n) / SR
        f = rng.uniform(90, 140) * (1 + 0.2 * np.sin(2 * np.pi * 3 * x))
        saw = 2 * ((np.cumsum(f) / SR) % 1) - 1
        cr = bp(saw * (0.6 + 0.4 * rng.random(n)), 150, 1500) * np.hanning(n)
        place(mix, reverb(cr, 0.8, 0.3), tt, rng.uniform(-0.6, 0.6), db(-26))

    # ---- whoosh and tick at every time jump --------------------------------------
    for start, label, _ in STAGES[1:]:
        n = int(0.9 * SR); x = np.arange(n) / SR
        w = noise(n, "pink")
        sweep = np.zeros(n)
        for a in range(0, n, 2400):  # band sweeps up
            fc = 300 + 2600 * (a / n)
            seg = bp(w[a:a + 2400 + 2400], fc * 0.7, fc * 1.4)[:2400]
            sweep[a:a + len(seg)] = seg
        sweep *= np.sin(np.pi * x / 0.9) ** 2
        place(mix, reverb(sweep, 0.7, 0.25), start - 0.45, 0, db(-17))
        tick = tap(1150, 0.05, 0.3); tick[:1440] += 0.5 * tap(3300, 0.03, 0.2)
        place(mix, reverb(tick, 0.5, 0.2), start, 0, db(-17))

    # ---- drips into the mug -------------------------------------------------------
    tt = DRIPS_FROM + 0.6
    while tt < DURATION - 1:
        n = int(0.12 * SR); x = np.arange(n) / SR
        pl = np.sin(2 * np.pi * (1400 - 2500 * x) * x) * np.exp(-x * 45)
        place(mix, pl, tt, -0.55, db(-30))
        tt += DRIP_EVERY

    # ---- last scene: storm softens, a soft pad, and the closing tap on the glass ----
    soft = 1 - 0.35 * np.clip((t - 130) / 4, 0, 1)
    mix *= soft[:, None]
    pad = np.zeros(N)
    for f in (110.0, 164.8, 220.0, 261.6, 329.6):
        ph = rng.uniform(0, 6.28)
        pad += np.sin(2 * np.pi * f * t + ph + 0.002 * np.sin(2 * np.pi * 0.2 * t)) / 5
    pe = np.clip((t - 131) / 7, 0, 1) * np.clip((DURATION - t) / 2.5, 0, 1)
    mix += stereo(bp(pad, hi=1200) * pe, 0) * db(-30)
    place(mix, reverb(tap(2300, 0.09), 1.2, 0.35), 147.2, 0.0, db(-9))

    # gentle fades and a loudness-friendly peak level
    fi = np.clip(t / 0.08, 0, 1); fo = np.clip((DURATION - t) / 0.3, 0, 1)
    mix *= (fi * fo)[:, None]
    mix *= 0.89 / np.abs(mix).max()
    sf.write(out, mix.astype(np.float32), SR, subtype="PCM_24")


if __name__ == "__main__":
    main(sys.argv[1])
