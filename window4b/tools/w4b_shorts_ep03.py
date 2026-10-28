"""Window 4B Ep 3: cut the finished long form into three connected 9:16 Shorts.

    python window4b/tools/w4b_shorts_ep03.py CLEAN.mp4 EXTRAS_DIR FINAL.mp4 OUT_DIR [--still]

CLEAN is the episode rendered without on-screen text; EXTRAS_DIR holds the two extra beats from
w4b_ep03_extras.py (same engine and view). They are joined into one 195 s source: 0-180 the episode,
180-188 the Short 1 cliffhanger, 188-195 the Short 2 cliffhanger. Audio is the long form's mix plus
matching sound for the two extra beats. One fixed 9:16 window (source x 440-1048) for every shot.
"""
import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).parent))
import w4b_shorts_ep02 as E2                               # noqa: E402
from w4b_sound import bp, noise, reverb, stereo, db         # noqa: E402

SR = E2.SR
X = 440

SHORTS = {
    "ep03_short1_the_night_everyone_disappeared": dict(
        segs=[(2.0, 10.0, X), (27.0, 31.0, X), (34.5, 40.5, X), (44.0, 56.0, X), (60.5, 72.5, X), (180.0, 188.0, X)],
        texts=[("seg", 0, 0.3, 7.7, "JUST ANOTHER DAY.", "line", 430),
               ("seg", 3, 0.6, 11.4, "EVERYONE WAS GONE.", "line", 430),
               ("end", None, -4.2, None, "BUT THE CITY WASN'T\nGOING TO STAY\nTHE SAME.", "line", 430)],
        tail=0.6, tail_audio="fade"),
    "ep03_short2_the_city_started_dying": dict(
        segs=[(84.5, 92.5, X), (92.5, 104.5, X), (110.0, 121.0, X), (121.0, 131.0, X), (188.0, 195.0, X)],
        texts=[("seg", 0, 0.3, 7.7, "30 DAYS LATER.", "line", 430),
               ("end", None, -3.0, None, "AND THIS WAS\nONLY SIX MONTHS.", "line", 430)],
        tail=1.0, tail_audio="hush"),
    "ep03_short3_one_year_without_people": dict(
        segs=[(136.0, 148.0, X), (148.0, 158.0, X), (158.0, 169.0, X), (169.0, 180.0, X)],
        texts=[("seg", 0, 0.3, 7.7, "ONE YEAR LATER.", "line", 430),
               ("src", 169.5, 0, None, "DAY 1:\nEVERYONE WAS HERE.", "line", 430),
               ("src", 173.5, 0, None, "DAY 365: THE CITY\nBELONGS TO NATURE.", "line", 600)],
        tail=0.5, tail_audio="fade"),
}


def extras_audio(mix):
    """Sound for the two extra beats, built from the episode's own ambience."""
    out = np.zeros((int(195 * SR), 2), np.float32)
    out[: len(mix[: 180 * SR])] = mix[: 180 * SR]
    # 180-188: the Day ~30 night ambience thins out; a faint electrical buzz as the office window holds
    a = mix[int(76 * SR):int(84 * SR)].copy()
    a *= np.linspace(0.8, 0.35, len(a))[:, None]
    n = len(a); t = np.arange(n) / SR
    buzz = (np.sign(np.sin(2 * np.pi * 100 * t)) * 0.3 + np.sin(2 * np.pi * 50 * t)) * np.clip((t - 2.5) / 1.5, 0, 1)
    a += stereo(bp(buzz, 60, 3000), 0.2) * db(-34)
    out[180 * SR:180 * SR + n] = a
    # 188-195: Month 6 birds and leaves; concrete cracks and crashes at 1.4 s, debris, then silence
    b = mix[int(131 * SR):int(138 * SR)].copy()
    n = len(b); t = np.arange(n) / SR
    b *= np.clip(1 - (t - 4.2) / 1.2, 0, 1)[:, None]
    k = int(1.4 * SR); m = int(4 * SR); x = np.arange(m) / SR
    crack = bp(noise(m), 400, 9000) * np.exp(-x * 14) * 0.6
    crash = bp(noise(m, "brown"), 30, 300) * np.exp(-x * 1.6) * np.minimum(1, (x - 0.5).clip(0) / 0.05)
    debris = bp(noise(m), 1500, 7000) * (np.random.default_rng(3).random(m) > 0.995) * np.exp(-x * 0.9) * 3
    hit = reverb(crack + crash + debris, 2.5, 0.5)
    hit *= np.clip(1 - (x - 3.2) / 0.8, 0, 1)
    b[k:k + m] += stereo(hit[: n - k], 0.25)[: n - k] * db(-6)
    out[188 * SR:188 * SR + n] = b
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clean"); ap.add_argument("extras"); ap.add_argument("final"); ap.add_argument("out")
    ap.add_argument("--still", action="store_true")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    src = out / "_source_195s.mp4"
    if not src.exists():
        lst = out / "_list.txt"
        lst.write_text("".join(f"file '{p}'\n" for p in (a.clean, f"{a.extras}/short1_end.mp4", f"{a.extras}/short2_end.mp4")))
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-c", "copy", str(src)], check=True)
    audio = None
    if not a.still:
        wav = out / "_longform_mix.wav"
        if not wav.exists():
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", a.final, "-vn", "-ac", "2", "-ar", str(SR),
                            "-c:a", "pcm_f32le", str(wav)], check=True)
        audio = extras_audio(sf.read(wav, dtype="float32")[0])
    for name, cfg in SHORTS.items():
        E2.make(name, cfg, str(src), audio, out, a.still)


if __name__ == "__main__":
    main()
