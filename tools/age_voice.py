"""Give a voice Maaran Thatha's warm, kind, 70+ grandfather tone.

Usage:
    python tools/age_voice.py IN.wav OUT.wav [--amount 1.0]

Thatha (assets/character/) is round-faced, smiling and gentle, so his voice
should sound warm, soft and unhurried, not rough or shaky. This adds NO noise
(an earlier "breath" layer added hiss and was removed). What it does:
  - rounder, "bigger" voice : pitch and formants lowered a few percent
  - chest warmth            : low-shelf lift around 200 Hz
  - soft, mellow top        : presence and treble eased off, lowpass at 9 kHz
  - a barely-there tremble  : very slow, tiny pitch wobble
  - gentle denoise          : removes any faint hiss copied from the reference
Slower delivery is handled at generation time (tools/f5_voice.py --speed).
"--amount" scales everything: 0.5 = subtle, 1.0 = default, 1.5 = strong.
"""
import argparse
import subprocess


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("out")
    ap.add_argument("--amount", type=float, default=1.0)
    a = ap.parse_args()
    k = a.amount
    # EQ filters go before rubberband/vibrato: in the other order ffmpeg's
    # IIR filters can blow up and output silence.
    chain = ",".join([
        "afftdn=nr=10:nf=-50",
        "highpass=f=70",
        f"bass=g={2.5 * k:.1f}:f=200:w=0.8",
        f"equalizer=f=3200:t=q:w=1.2:g={-1.5 * k:.1f}",
        f"treble=g={-2.5 * k:.1f}:f=6000",
        "lowpass=f=9000",
        "volume=0.8",
        f"rubberband=pitch={1 - 0.05 * k:.3f}:pitchq=quality",
        f"vibrato=f=4.5:d={0.012 * k:.3f}",
    ])
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", a.inp, "-af", chain, a.out], check=True)


if __name__ == "__main__":
    main()
