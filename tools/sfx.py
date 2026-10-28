"""Sound effects track from a cue list (no music): alarm bell, snoring, clock ticks, rooster, stick tap, yawn breath.

Usage:
    python tools/sfx.py CUES.json OUT.wav DURATION
CUES.json: [{"type": "alarm" | "snore" | "tick" | "rooster" | "tap", "t": 12.0, "dur": 3.0, "db": -18, "pan": 0}, ...]
alarm:   an old twin-bell alarm clock: a fast clapper (~22 Hz) hitting two bright bells (synthesised).
snore:   gentle snoring, one breath every ~3.6 s (low, rough inhale; soft whistle out) – synthesised.
tick:    clock ticks, 2 per second.
rooster: the real cockcrow recording (assets/sound/nature/rooster_distant.wav, CC0), brought close (louder, less
         filtered than the distant one in the ambience).
tap:     two wooden knocks (a walking stick on the floor).
Mix the result over the assembled episode: ffmpeg amix (normalize=0).
"""
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

SR = 44100
ROOT = Path(__file__).resolve().parent.parent


def bp(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], "bandpass", fs=SR, output="sos"), x)


def lp(x, hi):
    return sosfilt(butter(2, hi, "lowpass", fs=SR, output="sos"), x)


def alarm(dur, rng):
    n = int(dur * SR)
    out = np.zeros(n)
    k = np.arange(int(0.12 * SR)) / SR
    for i, t0 in enumerate(np.arange(0, dur, 1 / 22)):
        f = (2550, 3080)[i % 2]
        hit = (np.sin(2 * np.pi * f * k) + 0.4 * np.sin(2 * np.pi * f * 2.76 * k)) * np.exp(-k / 0.05)
        hit += 0.3 * rng.standard_normal(len(k)) * np.exp(-k / 0.004)
        j = int(t0 * SR)
        e = min(n, j + len(k))
        out[j:e] += hit[:e - j]
    env = np.minimum(1, np.arange(n) / (0.02 * SR)) * np.minimum(1, (n - np.arange(n)) / (0.03 * SR))
    return out * env


def snore(dur, rng):
    n = int(dur * SR)
    out = np.zeros(n)
    period = 3.6
    for t0 in np.arange(0.2, dur, period):
        m = int(1.3 * SR)
        t = np.arange(m) / SR
        buzz = np.sign(np.sin(2 * np.pi * 34 * t + 0.5 * np.sin(2 * np.pi * 3 * t))) * 0.5 + rng.standard_normal(m) * 0.6
        buzz = lp(bp(buzz, 60, 900), 700) * np.sin(np.pi * t / 1.3) ** 1.5
        out_m = int(1.1 * SR)
        to = np.arange(out_m) / SR
        exhale = bp(rng.standard_normal(out_m), 300, 2200) * np.sin(np.pi * to / 1.1) ** 2 * 0.35
        j = int(t0 * SR)
        e = min(n, j + m)
        out[j:e] += buzz[:e - j]
        j2 = j + int(1.5 * SR)
        e2 = min(n, j2 + out_m)
        if j2 < n:
            out[j2:e2] += exhale[:e2 - j2]
    return out


def tick(dur, rng):
    n = int(dur * SR)
    out = np.zeros(n)
    k = np.arange(int(0.02 * SR)) / SR
    for i, t0 in enumerate(np.arange(0, dur, 0.5)):
        c = bp(rng.standard_normal(len(k)), 2500, 6000) * np.exp(-k / 0.003) * (1 if i % 2 else 0.7)
        j = int(t0 * SR)
        out[j:j + len(k)] += c[:max(0, min(len(k), n - j))]
    return out


def rooster(dur, rng):
    x, sr = sf.read(ROOT / "assets/sound/nature/rooster_distant.wav", dtype="float64", always_2d=True)
    x = x.mean(axis=1)
    if sr != SR:
        x = np.interp(np.arange(0, len(x), sr / SR), np.arange(len(x)), x)
    x = bp(x, 350, 6000)[: int(dur * SR)]
    f = int(0.05 * SR)
    x[-f:] *= np.linspace(1, 0, f)
    return x


def tap(dur, rng):
    out = np.zeros(int(max(dur, 0.6) * SR))
    for t0, a in ((0.0, 1.0), (0.28, 0.7)):
        n = int(0.16 * SR)
        t = np.arange(n) / SR
        body = np.sin(2 * np.pi * 210 * t) * np.exp(-t / 0.035) + 0.5 * np.sin(2 * np.pi * 470 * t) * np.exp(-t / 0.02)
        click = bp(rng.standard_normal(n), 700, 3500) * np.exp(-t / 0.006)
        j = int(t0 * SR)
        out[j:j + n] += a * (0.8 * body + 0.6 * click)
    return out


KINDS = {"alarm": alarm, "snore": snore, "tick": tick, "rooster": rooster, "tap": tap}


def main():
    cues = json.loads(Path(sys.argv[1]).read_text())
    total = float(sys.argv[3])
    st = np.zeros((int(total * SR), 2))
    rng = np.random.default_rng(7)
    for c in cues:
        x = KINDS[c["type"]](c.get("dur", 1.0), rng)
        x = x / (np.sqrt(np.mean(x ** 2)) + 1e-9) * 10 ** (c.get("db", -20) / 20)
        pan = c.get("pan", 0.0)
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        j = int(c["t"] * SR)
        e = min(len(st), j + len(x))
        st[j:e, 0] += x[:e - j] * l
        st[j:e, 1] += x[:e - j] * r
    peak = np.abs(st).max()
    if peak > 0.95:
        st *= 0.95 / peak
    sf.write(sys.argv[2], st.astype(np.float32), SR)
    print("saved", sys.argv[2])


if __name__ == "__main__":
    main()
