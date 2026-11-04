"""Shorten the pauses inside IndicF5 voice lines (brisk pace) and trim their silent ends.

Usage:
    python tools/trim_pauses.py WAV_DIR OUT_DIR [--short 0.22] [--long 0.32] [--db -38]
Every internal silence of 0.3 s or more becomes `short` seconds (`long` when it was 1 s or more); the lead-in and
tail are cut to 0.05 s. Writes OUT_DIR/<same name>.wav and prints each line's length before/after.
"""
import argparse
from pathlib import Path

import numpy as np
import soundfile as sf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--short", type=float, default=0.22)
    ap.add_argument("--long", type=float, default=0.32)
    ap.add_argument("--db", type=float, default=-38)
    a = ap.parse_args()
    out = Path(a.dst)
    out.mkdir(exist_ok=True)
    for f in sorted(Path(a.src).glob("*.wav")):
        x, sr = sf.read(f, dtype="float32")
        mono = x if x.ndim == 1 else x.mean(axis=1)
        hop = int(0.01 * sr)
        n = len(mono) // hop
        rms = np.sqrt(np.mean(mono[:n * hop].reshape(n, hop) ** 2, axis=1) + 1e-12)
        loud = 20 * np.log10(rms) > a.db
        idx = np.nonzero(loud)[0]
        if len(idx) == 0:
            print(f.name, "silent?")
            continue
        first, last = idx[0], idx[-1]
        keep = []
        i = first
        pad = int(0.05 * sr / hop)
        keep.append((max(0, first - pad) * hop, first * hop))
        while i <= last:
            if loud[i]:
                j = i
                while j <= last and loud[j]:
                    j += 1
                keep.append((i * hop, j * hop))
                i = j
            else:
                j = i
                while j <= last and not loud[j]:
                    j += 1
                gap = (j - i) * 0.01
                if gap < 0.3:
                    keep.append((i * hop, j * hop))
                else:
                    tgt = a.long if gap >= 1.0 else a.short
                    m = i + int((j - i) / 2)
                    h = int(tgt / 2 / 0.01)
                    keep.append(((m - h) * hop, (m + h) * hop))
                i = j
        keep.append(((last + 1) * hop, min(len(mono), (last + 1 + pad) * hop)))
        y = np.concatenate([x[s:e] for s, e in keep])
        fade = int(0.01 * sr)
        y[:fade] *= np.linspace(0, 1, fade)[:, None] if y.ndim > 1 else np.linspace(0, 1, fade)
        y[-fade:] *= np.linspace(1, 0, fade)[:, None] if y.ndim > 1 else np.linspace(1, 0, fade)
        sf.write(out / f.name, y, sr)
        print(f"{f.name}: {len(x) / sr:.2f} s -> {len(y) / sr:.2f} s")


if __name__ == "__main__":
    main()
