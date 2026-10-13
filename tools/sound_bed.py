"""Procedural (royalty-free) background sound for Maaran Thatha episodes.

Everything is synthesised with NumPy, so there are no licensing issues:
  * ambience: soft breeze + occasional distant birds
  * music: gentle plucked-string folk melody in Mohanam (S R2 G3 P D2) over a
    tanpura-style Sa-Pa drone (Karplus-Strong string synthesis)

Usage:
    python tools/sound_bed.py OUT.wav DURATION_SECONDS [--seed N] [--no-music]
"""
import argparse
import wave

import numpy as np
from scipy.signal import lfilter

SR = 44100


def write_wav(path, stereo):
    pcm = np.clip(stereo, -1, 1)
    pcm = (pcm * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def one_pole_lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    return lfilter([1 - a], [1, -a], x)


def breeze(n, rng):
    out = np.zeros((n, 2))
    t = np.arange(n) / SR
    for ch in range(2):
        noise = rng.standard_normal(n)
        brown = one_pole_lowpass(noise, 500) * 6
        gust = 0.55 + 0.45 * np.sin(2 * np.pi * (0.07 + 0.03 * ch) * t + rng.uniform(0, 6))
        gust *= 0.8 + 0.2 * np.sin(2 * np.pi * 0.19 * t + rng.uniform(0, 6))
        out[:, ch] = brown * gust
    return out / (np.abs(out).max() + 1e-9) * 0.05


def bird_call(rng):
    """A short group of chirps from a small songbird."""
    parts = []
    base = rng.uniform(2600, 4200)
    for _ in range(rng.integers(2, 5)):
        dur = rng.uniform(0.05, 0.12)
        m = int(dur * SR)
        t = np.arange(m) / SR
        sweep = base * (1 + rng.uniform(-0.25, 0.35) * t / dur)
        phase = 2 * np.pi * np.cumsum(sweep) / SR
        env = np.sin(np.pi * t / dur) ** 2
        chirp = (np.sin(phase) + 0.25 * np.sin(2 * phase)) * env
        parts.append(chirp)
        parts.append(np.zeros(int(rng.uniform(0.04, 0.12) * SR)))
    return np.concatenate(parts)


def birds(n, rng):
    out = np.zeros((n, 2))
    pos = int(rng.uniform(0.5, 2.5) * SR)
    while pos < n:
        call = bird_call(rng) * rng.uniform(0.012, 0.03)
        pan = rng.uniform(0.15, 0.85)
        end = min(n, pos + len(call))
        out[pos:end, 0] += call[: end - pos] * (1 - pan)
        out[pos:end, 1] += call[: end - pos] * pan
        pos += int(rng.uniform(3, 8) * SR)
    return out


def pluck(freq, dur, rng, decay=0.996):
    """Karplus-Strong plucked string: y[n] = x[n] + decay/2 * (y[n-P] + y[n-P-1])."""
    n = int(dur * SR)
    period = max(2, int(SR / freq))
    excite = np.zeros(n)
    excite[:period] = rng.uniform(-1, 1, period)
    den = np.zeros(period + 2)
    den[0] = 1
    den[period] = den[period + 1] = -decay / 2
    out = lfilter([1], den, excite)
    fade = int(0.05 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)
    return out


def music(n, rng):
    sa = 146.83  # D3 as Sa, a warm, low key under a male voice
    ratios = {"S": 1, "R": 9 / 8, "G": 5 / 4, "P": 3 / 2, "D": 5 / 3, "S'": 2}
    out = np.zeros((n, 2))

    # tanpura-style drone: P S' S' S, repeating
    cycle = [sa * 3 / 4, sa, sa, sa / 2]
    step = 0.9
    pos, k = 0, 0
    while pos < n:
        note = pluck(cycle[k % 4], 3.0, rng) * 0.12
        end = min(n, pos + len(note))
        out[pos:end, 0] += note[: end - pos] * 0.6
        out[pos:end, 1] += note[: end - pos] * 0.4
        pos += int(step * SR)
        k += 1

    # sparse Mohanam melody, two octaves up, gentle and slow
    phrases = [
        ["G", "P", "D", "P", "G", "R", "S"],
        ["S", "R", "G", "P", "G", "R", "G"],
        ["P", "D", "S'", "D", "P", "G", "P"],
        ["G", "R", "S", "R", "G", "P", "G"],
    ]
    beat = 0.45
    pos = int(1.5 * SR)
    p = 0
    while pos < n:
        for sw in phrases[p % len(phrases)]:
            if pos >= n:
                break
            f = sa * 2 * ratios[sw]
            dur = beat * rng.choice([1, 1, 2])
            note = pluck(f, dur + 0.6, rng) * 0.09
            end = min(n, pos + len(note))
            out[pos:end, 0] += note[: end - pos] * 0.45
            out[pos:end, 1] += note[: end - pos] * 0.55
            pos += int(dur * SR)
        pos += int(beat * 3 * SR)  # breathe between phrases
        p += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("duration", type=float)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--no-music", action="store_true")
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    n = int(a.duration * SR)
    mix = breeze(n, rng) + birds(n, rng)
    if not a.no_music:
        mix += music(n, rng)
    mix *= 10 ** (-24 / 20) / (np.sqrt(np.mean(mix ** 2)) + 1e-9)  # RMS -24 dBFS
    fade = int(0.3 * SR)
    mix[:fade] *= np.linspace(0, 1, fade)[:, None]
    mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
    write_wav(a.out, mix)


if __name__ == "__main__":
    main()
