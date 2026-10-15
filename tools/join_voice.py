"""Join per-line voice WAVs into one track and record when each line is spoken.

Usage:
    python tools/join_voice.py LINES.json LINE_WAV_DIR OUT_DIR [--ids L01,L02]

Trims silence from each line, adds the line's "pause_after" gap, then writes
OUT_DIR/voice.wav (44.1 kHz mono, loudness-normalised) and OUT_DIR/timings.json,
which tools/assemble_ep.py uses to cut shots on the voice.
"""
import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 44100
TRIM = ("silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
        "silenceremove=start_periods=1:start_threshold=-50dB,areverse")


def load_trimmed(path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-af", f"highpass=f=60,{TRIM}",
                          "-ar", str(SR), "-ac", "1", "-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).copy()
    fade = int(0.01 * SR)
    x[:fade] *= np.linspace(0, 1, fade)
    x[-fade:] *= np.linspace(1, 0, fade)
    return x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lines")
    ap.add_argument("wav_dir")
    ap.add_argument("out")
    ap.add_argument("--ids", default="")
    a = ap.parse_args()

    wanted = set(filter(None, a.ids.split(",")))
    lines = [l for l in json.loads(Path(a.lines).read_text()) if not wanted or l["id"] in wanted]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    pieces, timings, t = [np.zeros(int(0.3 * SR), np.float32)], [], 0.3
    for i, line in enumerate(lines):
        x = load_trimmed(Path(a.wav_dir) / f"{line['id']}.wav")
        timings.append({"id": line["id"], "start": round(t, 3), "end": round(t + len(x) / SR, 3)})
        pause = line.get("pause_after", 0.4) if i < len(lines) - 1 else 0.6
        pieces += [x, np.zeros(int(pause * SR), np.float32)]
        t += len(x) / SR + pause
    sf.write(out / "voice_raw.wav", np.concatenate(pieces), SR)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(out / "voice_raw.wav"),
                    "-af", "loudnorm=I=-16:TP=-1.5", "-ar", str(SR), str(out / "voice.wav")], check=True)
    (out / "voice_raw.wav").unlink()
    (out / "timings.json").write_text(json.dumps(timings, indent=1))
    print(f"voice.wav {t:.2f}s", timings)


if __name__ == "__main__":
    main()
