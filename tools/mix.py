"""Mix Thatha's voice over the background sound bed.

Usage:
    python tools/mix.py voice.wav bed.wav OUT.wav [--bed-db -20] [--duck-db -9]

The bed plays continuously (so pauses never fall into dead silence) and is
automatically lowered (ducked) while Thatha speaks, then rises gently in the gaps.
"""
import argparse
import subprocess


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("voice")
    ap.add_argument("bed")
    ap.add_argument("out")
    ap.add_argument("--bed-db", type=float, default=-6)
    ap.add_argument("--tail", type=float, default=1.5, help="seconds of bed after the voice ends")
    a = ap.parse_args()
    graph = (
        f"[1:a]volume={a.bed_db}dB,aformat=channel_layouts=stereo[bed];"
        f"[0:a]aformat=channel_layouts=stereo,apad=pad_dur={a.tail},asplit=2[v][key];"
        "[bed][key]sidechaincompress=threshold=0.03:ratio=4:attack=60:release=600:makeup=1[ducked];"
        "[v][ducked]amix=inputs=2:duration=first:normalize=0,"
        "loudnorm=I=-14:TP=-1.5[out]"
    )
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", a.voice, "-i", a.bed,
                    "-filter_complex", graph, "-map", "[out]", "-ar", "44100", a.out], check=True)


if __name__ == "__main__":
    main()
