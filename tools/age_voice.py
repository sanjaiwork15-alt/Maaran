"""Make a voice sound older (70+) without making it robotic.

Usage:
    python tools/age_voice.py IN.wav OUT.wav [--amount 1.0]

What an old man's voice has that a 35-year-old's doesn't, and how we add it:
  - breath / hoarseness : soft noise (1.2-6 kHz) that follows the voice's own loudness
  - a slight tremble    : slow, small pitch wobble (~5.5 Hz) and loudness wobble (~4 Hz)
  - a darker, "bigger" tone : pitch and formants lowered a few percent
  - less crisp top end  : gentle high-shelf cut
Slower delivery is handled at generation time (tools/f5_voice.py --speed).
"--amount" scales everything: 0.5 = subtle, 1.0 = default, 1.5 = very old.
"""
import argparse
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt


def breath(x, sr, level):
    hop = int(0.01 * sr)
    frames = np.sqrt(np.convolve(x ** 2, np.ones(hop) / hop, mode="same"))
    env = np.convolve(frames, np.hanning(4 * hop) / (2 * hop), mode="same")
    noise = sosfilt(butter(4, [1200, 6000], btype="band", fs=sr, output="sos"),
                    np.random.default_rng(7).standard_normal(len(x)))
    noise /= np.sqrt(np.mean(noise ** 2)) + 1e-9
    return x + level * env * noise


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("out")
    ap.add_argument("--amount", type=float, default=1.0)
    a = ap.parse_args()
    k = a.amount

    x, sr = sf.read(a.inp, dtype="float32")
    if x.ndim > 1:
        x = x.mean(axis=1)
    tmp = Path(tempfile.mkdtemp()) / "breathy.wav"
    y = breath(x, sr, 0.22 * k)
    sf.write(tmp, 0.8 * y / np.abs(y).max(), sr, subtype="FLOAT")
    # EQ filters go before rubberband/vibrato: in the other order ffmpeg's
    # IIR filters can blow up and output silence.
    chain = ",".join([
        f"treble=g={-3 * k:.1f}:f=5000",
        "highpass=f=70",
        f"rubberband=pitch={1 - 0.05 * k:.3f}:pitchq=quality",
        f"vibrato=f=5.5:d={0.035 * k:.3f}",
        f"tremolo=f=4:d={0.08 * k:.3f}",
    ])
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(tmp), "-af", chain, a.out], check=True)


if __name__ == "__main__":
    main()
