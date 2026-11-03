"""Window 4B Ep 4: cut the finished dust-storm episode into three connected 9:16 Shorts.

    python window4b/tools/w4b_shorts_ep04.py CLEAN.mp4 EXTRAS_DIR FINAL.mp4 OUT_DIR [--still]

CLEAN is the episode without on-screen text; EXTRAS_DIR holds the three extra beats from
w4b_ep04_extras.py. Joined source: 0-180 episode, 180-188 Short 1 ending (Day 1 lull), 188-195 Short 2
ending (new dust wave), 195-213 Short 3 ending (final gust, hold, fade). Audio is the long form's natural
mix plus matching natural sound for the extra beats. One fixed 9:16 window (source x 560-1168, centred on
the bridge, river and street) for every shot.
"""
import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).parent))
import w4b_shorts_ep02 as E2                               # noqa: E402
from w4b_sound import bp, noise, stereo, db                # noqa: E402

SR = E2.SR
X = 560

SHORTS = {
    "ep04_short1_the_dust_storm_arrives": dict(
        segs=[(0.0, 8.0, X), (9.0, 14.0, X), (24.0, 28.0, X), (30.0, 43.0, X), (43.0, 51.0, X), (56.0, 60.0, X),
              (180.0, 188.0, X)],
        texts=[("seg", 0, 0.3, 7.7, "JUST ANOTHER\nMORNING.", "line", 430),
               ("seg", 1, 0.5, 8.5, "BUT SOMETHING\nWAS COMING.", "line", 430),
               ("end", None, -4.0, None, "THIS WAS\nONLY DAY ONE.", "line", 430)],
        tail=0.4, tail_audio="hush"),
    "ep04_short2_the_city_begins_to_disappear": dict(
        segs=[(86.0, 94.0, X), (96.0, 108.0, X), (120.0, 132.0, X), (141.0, 152.0, X), (188.0, 195.0, X)],
        texts=[("seg", 0, 0.3, 7.7, "7 DAYS LATER.", "line", 430),
               ("seg", 2, 0.5, 11.5, "THE SUN WAS\nDISAPPEARING.", "line", 430),
               ("end", None, -3.6, None, "AND THE WORST WAS\nSTILL TO COME.", "line", 430)],
        tail=0.4, tail_audio="hush"),
    "ep04_short3_one_year_under_the_dust": dict(
        segs=[(146.0, 154.0, X), (154.0, 166.0, X), (166.0, 177.0, X), (195.0, 213.0, X)],
        texts=[("seg", 0, 0.3, 7.7, "6 MONTHS LATER.", "line", 430),
               ("seg", 2, 0.3, 10.7, "365 DAYS LATER.", "line", 430),
               ("end", None, -7.2, None, "ONE CITY.", "line", 430),
               ("end", None, -5.6, None, "ONE STORM.", "line", 515),
               ("end", None, -4.0, None, "A WORLD BURIED\nIN DUST.", "line", 600)],
        tail=0.6, tail_audio="hush"),
}


def gust(n, start, length, gain):
    x = np.arange(n) / SR
    e = np.clip((x - start) / (length * 0.35), 0, 1) * np.clip((start + length - x) / (length * 0.65), 0, 1)
    g = bp(noise(n, "pink"), 150, 1400) + bp(noise(n, "pink"), 1200, 5000) * 0.5
    return stereo(g * e, 0.2) * db(gain)


def extras_audio(mix):
    out = np.zeros((int(213 * SR), 2), np.float32)
    out[: 180 * SR] = mix[: 180 * SR]
    # 180-188: the Day 1 storm, then the wind drops away for a moment
    a = mix[int(60 * SR):int(68 * SR)].copy()
    t = np.arange(len(a)) / SR
    a *= (0.25 + 0.75 * np.clip(1 - t / 3.0, 0, 1))[:, None]
    out[180 * SR:188 * SR] = a
    # 188-195: the calm of Month 6, then a powerful new gust rushes in
    b = mix[int(150 * SR):int(157 * SR)].copy()
    n = len(b)
    hiss = np.zeros(n); r = np.random.default_rng(5); pos = r.integers(0, n, n // 20); hiss[pos] = r.uniform(-1, 1, len(pos))
    x = np.arange(n) / SR
    b += gust(n, 0.6, 9.0, -3) + stereo(bp(hiss, 2500, 10000) * np.clip((x - 1.2) / 1.5, 0, 1), 0) * db(-14)
    b += stereo(bp(noise(n, "brown"), 20, 90, 3) * np.clip((x - 0.6) / 2.0, 0, 1), 0) * db(-12)
    out[188 * SR:195 * SR] = b
    # 195-213: soft wind; a final gust sweeps over (1.5-9 s), soft gusts, then silence before the end
    n = 18 * SR; x = np.arange(n) / SR
    c = gust(n, 0.0, 18.0, -16) + gust(n, 1.5, 7.5, -2) + gust(n, 12.5, 3.0, -7)
    c *= np.clip((16.2 - x) / 0.8, 0, 1)[:, None]
    out[195 * SR:213 * SR] = c
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clean"); ap.add_argument("extras"); ap.add_argument("final"); ap.add_argument("out")
    ap.add_argument("--still", action="store_true")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    src = out / "_source_213s.mp4"
    if not src.exists():
        lst = out / "_list.txt"
        lst.write_text("".join(f"file '{p}'\n" for p in (a.clean, f"{a.extras}/short1_end.mp4", f"{a.extras}/short2_end.mp4",
                                                         f"{a.extras}/short3_end.mp4")))
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
