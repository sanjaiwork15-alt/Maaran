"""Natural village-morning ambience from real field recordings (assets/sound/nature, CC0/CC BY).

Usage:
    python tools/ambience.py OUT.wav DURATION [--seed 3] [--no-rooster]

Layers, all quiet so the voice stays clear:
  bed      soft forest/field birds, looped with crossfades
  insects  very faint daytime crickets (Kollam, Kerala)
  breeze   rustling leaves, slowly swelling and fading
  calls    individual birds (bulbul, chirps, morning calls, a distant cuckoo) placed at
           random times, panned left/right and filtered by distance
  crow     one distant crow; rooster  one far-off cockcrow near the start
Credits for CC BY clips: assets/sound/nature/CREDITS.md (put them in the video description).
"""
import argparse
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

SR = 44100
DIR = Path(__file__).resolve().parent.parent / "assets/sound/nature"


def load(name):
    x, sr = sf.read(DIR / f"{name}.wav", dtype="float32", always_2d=True)
    x = x.mean(axis=1)
    if sr != SR:
        idx = np.arange(0, len(x), sr / SR)
        x = np.interp(idx, np.arange(len(x)), x).astype(np.float32)
    return x


def filt(x, lo=None, hi=None):
    if lo:
        x = sosfilt(butter(2, lo, "highpass", fs=SR, output="sos"), x)
    if hi:
        x = sosfilt(butter(2, hi, "lowpass", fs=SR, output="sos"), x)
    return x.astype(np.float32)


def rms(x):
    return float(np.sqrt(np.mean(x ** 2)) + 1e-9)


def at_level(x, db):
    """Scale so the clip's RMS sits at db dBFS."""
    return x * (10 ** (db / 20) / rms(x))


def loop(x, n, fade=SR):
    out = np.zeros(n, np.float32)
    ramp = np.linspace(0, 1, fade, dtype=np.float32)
    pos = 0
    while pos < n:
        seg = x.copy()
        seg[:fade] *= ramp
        seg[-fade:] *= ramp[::-1]
        end = min(n, pos + len(seg))
        out[pos:end] += seg[:end - pos]
        pos += len(seg) - fade
    return out


def place(stereo, x, t, pan):
    i = int(t * SR)
    if i >= len(stereo):
        return
    x = x[:len(stereo) - i]
    left, right = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    stereo[i:i + len(x), 0] += x * left
    stereo[i:i + len(x), 1] += x * right


def fade_edges(x, ms=40):
    n = min(len(x) // 2, int(SR * ms / 1000))
    r = np.linspace(0, 1, n, dtype=np.float32)
    x = x.copy()
    x[:n] *= r
    x[-n:] *= r[::-1]
    return x


def segments(x, seg_s, rng, k):
    """k random snippets of a long recording, each seg_s seconds."""
    n = int(seg_s * SR)
    if len(x) <= n:
        return [x]
    return [x[s:s + n] for s in rng.integers(0, len(x) - n, size=k)]


def build(dur, seed=3, rooster=True):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    st = np.zeros((n, 2), np.float32)

    bed = at_level(filt(load("bed_forest_birds"), lo=180, hi=7500), -36)
    b2 = np.roll(bed, len(bed) // 2)
    st[:, 0] += loop(bed, n)
    st[:, 1] += loop(b2, n)

    insects = at_level(filt(load("crickets_kollam"), lo=2500, hi=7000), -54)
    st += loop(insects, n)[:, None] * 0.7

    leaves = at_level(filt(filt(load("leaves_rustling"), lo=250, hi=2800), hi=2800), -45)
    t = np.arange(n) / SR
    swell = 0.55 + 0.45 * np.sin(2 * np.pi * t / 7.5 + rng.uniform(0, 6)) ** 2
    lv = loop(leaves, n) * swell.astype(np.float32)
    st[:, 0] += lv * 0.8
    st[:, 1] += np.roll(lv, SR // 3) * 0.8

    calls = [("birds_chirps", 2.5, -33), ("birds_morning_calls", 2.0, -36), ("bulbul_red_vented", 2.3, -33)]
    pieces = []
    for name, seg_s, db in calls:
        src = filt(load(name), lo=900)
        for s in segments(src, seg_s, rng, 3):
            pieces.append(at_level(fade_edges(s, 120), db))
    rng.shuffle(pieces)
    tt = rng.uniform(0.2, 1.2)
    for p in pieces:
        if tt > dur - 0.5:
            break
        dist = rng.uniform(0, 1)                     # 0 near, 1 far: quieter and duller
        p = filt(p, hi=12000 - 7000 * dist) * (1 - 0.6 * dist)
        place(st, p, tt, rng.uniform(-0.85, 0.85))
        tt += rng.uniform(1.4, 3.2)

    if dur > 6:
        cuckoo = at_level(fade_edges(filt(load("cuckoo_plaintive"), lo=600, hi=7000), 200), -40)
        place(st, cuckoo, rng.uniform(dur * 0.45, dur * 0.75), rng.choice([-0.7, 0.7]))
    crow = load("crows")
    crow = at_level(fade_edges(filt(crow[: int(1.6 * SR)], lo=400, hi=6000), 150), -39)
    place(st, crow, rng.uniform(dur * 0.25, dur * 0.6), rng.uniform(-0.8, 0.8))
    if rooster:
        r = at_level(fade_edges(filt(load("rooster_distant"), lo=500, hi=4000), 200), -44)
        place(st, r[: int(3.5 * SR)], rng.uniform(0.3, 1.5), rng.choice([-0.8, 0.8]))

    fade = min(n // 4, int(0.8 * SR))
    st[:fade] *= np.linspace(0, 1, fade)[:, None]
    st[-fade:] *= np.linspace(1, 0, fade)[:, None]
    peak = np.abs(st).max()
    if peak > 0.5:
        st *= 0.5 / peak
    return st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("duration", type=float)
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--no-rooster", action="store_true")
    a = ap.parse_args()
    sf.write(a.out, build(a.duration, a.seed, not a.no_rooster), SR)
    print("saved", a.out)


if __name__ == "__main__":
    main()
