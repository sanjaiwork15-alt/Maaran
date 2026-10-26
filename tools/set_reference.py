"""Lock Maaran Thatha's voice from one short reference clip (done once, reused forever).

Usage:
    python tools/set_reference.py CLIP.(mp3|wav|m4a|mp4|...) "exact Tamil words spoken in the clip" [--start 0] [--length 12]
        [--name thatha]

Cleans the clip and saves it as assets/voice/NAME_ref.wav (mono, 24 kHz) plus NAME_ref.txt (default NAME = thatha;
other characters, e.g. --name thambi for the young man in "Maaran Thatha – Day N", get their own reference). tools/f5_voice.py then speaks every new script line in this voice.

A good clip: 6-12 seconds, one man talking, no music or background noise, natural
spoken Tamil in the mood we want for Thatha (warm, smiling, unhurried). The words
must match the audio exactly, because IndicF5 aligns the voice to the text.
"""
import argparse
import subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets/voice"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clip")
    ap.add_argument("text")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--length", type=float, default=12.0)
    ap.add_argument("--name", default="thatha")
    a = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    trim = "silenceremove=start_periods=1:start_threshold=-50dB,areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse"
    chain = f"highpass=f=60,afftdn=nr=8:nf=-50,{trim},loudnorm=I=-20:TP=-2"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(a.start), "-t", str(a.length),
                    "-i", a.clip, "-vn", "-af", chain, "-ac", "1", "-ar", "24000",
                    str(OUT / f"{a.name}_ref.wav")], check=True)
    (OUT / f"{a.name}_ref.txt").write_text(a.text.strip() + "\n")
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                          str(OUT / f"{a.name}_ref.wav")], capture_output=True, text=True).stdout.strip()
    print(f"Saved assets/voice/{a.name}_ref.wav ({float(dur):.1f}s) and {a.name}_ref.txt")


if __name__ == "__main__":
    main()
