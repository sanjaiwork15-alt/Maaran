"""Window 4B Ep 2: cut the finished long form into three connected 9:16 Shorts (editing only).

    python window4b/tools/w4b_shorts_ep02.py CLEAN.mp4 FINAL.mp4 OUT_DIR [--only NAME] [--still]

CLEAN is the same render without on-screen text (W4B_NO_TEXT=1); FINAL supplies the audio (the
long form's mix). The camera never moves: each segment is a fixed 9:16 window of the source
(608 px of 1920), chosen so the old building and the action stay in frame; between segments there
are only cuts. Time markers and end lines are redrawn in the Shorts safe area, above the old
window (which sits at y ~ 810-860 in the Short).
"""
import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).parent))
from w4b_shorts import frames, reframe, text_layer, overlay, FPS, SR, OW, OH, CW  # noqa: E402
from timeline import ease  # noqa: E402

OLD = 1040      # window around the old building (source px)
DEMO = 1080     # a little further right: the demolition and the machines
FINAL = 1230    # old window + books
MUG = 250       # plant + mug

MARK = dict(size=64, xy=(72, 330))
LINE = dict(size=66)

SHORTS = {
    "ep02_short1_the_city_starts_changing": dict(
        segs=[(0.0, 6.0, OLD), (17.0, 31.0, OLD), (41.0, 51.0, OLD), (62.0, 79.0, OLD)],
        texts=[("seg", 0, 0.2, 4.0, "100 YEARS.\nONE STREET.", "line", 430),
               ("seg", 1, 0.3, 13.6, "10 YEARS LATER  |  2036", "mark", None),
               ("seg", 2, 0.3, 9.6, "25 YEARS LATER  |  2051", "mark", None),
               ("seg", 3, 0.3, 11.0, "40 YEARS LATER  |  2066", "mark", None),
               ("end", None, -5.2, None, "EVERYTHING CHANGED.", "line", 430),
               ("end", None, -2.9, None, "SO WHY IS THIS\nWINDOW STILL LIT?", "line", 515)],
        tail=0.8, tail_audio="fade"),
    "ep02_short2_the_building_nobody_touches": dict(
        segs=[(80.5, 84.0, OLD), (84.0, 105.0, DEMO), (105.5, 114.0, OLD), (117.0, 128.0, OLD)],
        texts=[("seg", 0, 0.2, 9.0, "60 YEARS LATER  |  2086", "mark", None),
               ("seg", 2, 0.3, 14.0, "80 YEARS LATER  |  2106", "mark", None),
               ("end", None, -5.0, None, "80 YEARS HAVE PASSED.", "line", 430),
               ("end", None, -2.7, None, "WILL IT\nSURVIVE 100?", "line", 515)],
        tail=1.0, tail_audio="hush"),
    "ep02_short3_100_years_later": dict(
        segs=[(128.5, 132.5, OLD), (136.0, 153.0, DEMO), (155.5, 159.5, FINAL), (159.5, 162.8, MUG),
              (162.8, 176.0, FINAL)],
        texts=[("seg", 0, 0.2, 18.0, "100 YEARS LATER  |  2126", "mark", None),
               ("src", 157.0, 0, None, "100 YEARS.", "line", 430),
               ("src", 161.5, 0, None, "SAME WINDOW.", "line", 515),
               ("src", 166.0, 0, None, "SAME WORLD?", "line", 600)],
        tail=1.2, tail_audio="fade"),
}


def layout(cfg):
    """Map every segment to Short time; resolve text times to (start, end) in Short time."""
    t, starts = 0.0, []
    for a, b, _ in cfg["segs"]:
        starts.append(t); t += b - a
    body = t
    total = body + cfg["tail"]
    out = []
    for kind, ref, off, dur, txt, style, y in cfg["texts"]:
        if kind == "seg":
            s = starts[ref] + off; e = s + dur
        elif kind == "end":
            s = body + off; e = total
        else:   # a source time: find the segment that contains it
            s = None
            for (a, b, _), st in zip(cfg["segs"], starts):
                if a <= ref < b:
                    s = st + ref - a
            if s is None:
                continue
            e = total
        out.append((s, e, txt, style, y))
    return starts, body, total, out


def text_on(f, clock, texts):
    for s, e, txt, style, y in texts:
        if not s <= clock < e + 0.01:
            continue
        a = ease((clock - s) / 0.6) * (ease((e - clock) / 0.4) if style == "mark" else 1.0)
        if a <= 0:
            continue
        if style == "mark":
            f = overlay(f, *text_layer(txt, MARK["size"], a, MARK["xy"]))
        else:
            f = overlay(f, *text_layer(txt, LINE["size"], a, (0, y), center=True))
    return f


def build_audio(audio, cfg, body, total):
    out = np.zeros((int(total * SR) + SR, 2), np.float32)
    pos, xf = 0, int(0.08 * SR)
    for i, (a, b, _) in enumerate(cfg["segs"]):
        seg = audio[int(a * SR):int(b * SR)].copy()
        if i > 0:
            seg[:xf] *= np.linspace(0, 1, xf)[:, None]
            out[pos - xf:pos] *= np.linspace(1, 0, xf)[:, None]
            pos -= xf
        out[pos:pos + len(seg)] += seg
        pos += len(seg)
    end = cfg["segs"][-1][1]
    n_tail = int(cfg["tail"] * SR)
    tail = audio[int(end * SR):int(end * SR) + n_tail].copy()
    if cfg["tail_audio"] == "hush":       # cut to near silence on black
        tail *= 0.06
    else:                                 # the ambience fades out under black
        tail *= np.linspace(1, 0, len(tail))[:, None] ** 1.5
    out[pos:pos + len(tail)] += tail
    out[: int(0.15 * SR)] *= np.linspace(0, 1, int(0.15 * SR))[:, None]
    return out[: int(total * SR)]


def make(name, cfg, clean, audio, out_dir, still=False):
    starts, body, total, texts = layout(cfg)
    if still:
        for (a, b, x0), st in zip(cfg["segs"], starts):
            for t, img in frames(clean, a, b):
                c = st + t - a
                if abs((t - a) % 3) < 1 / FPS or abs(t - (b - 1 / FPS)) < 1 / FPS:
                    f = text_on(reframe(img, x0), c, texts)
                    import cv2
                    cv2.imwrite(str(out_dir / f"{name}_{c:05.1f}.png"), f)
        return
    vtmp, atmp = out_dir / f"{name}_v.mp4", out_dir / f"{name}.wav"
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                            "-s", f"{OW}x{OH}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow",
                            "-crf", "17", "-pix_fmt", "yuv420p", str(vtmp)], stdin=subprocess.PIPE)
    clock = 0.0
    for (a, b, x0), st in zip(cfg["segs"], starts):
        for t, img in frames(clean, a, b):
            c = st + t - a
            f = reframe(img, x0)
            if c > body - 1.0 and cfg["tail_audio"] == "fade" and name.endswith("later"):
                f = (f.astype(np.float32) * ease((body - c) / 1.0)).astype(np.uint8)    # slow fade on the last shot
            enc.stdin.write(text_on(f, c, texts).tobytes())
    black = np.zeros((OH, OW, 3), np.uint8)
    for i in range(int(round(cfg["tail"] * FPS))):
        enc.stdin.write(text_on(black, body + i / FPS, texts).tobytes())
    enc.stdin.close(); enc.wait()
    sf.write(atmp, build_audio(audio, cfg, body, total), SR, subtype="PCM_24")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(vtmp), "-i", str(atmp), "-map", "0:v", "-map",
                    "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                    str(out_dir / f"{name}.mp4")], check=True)
    vtmp.unlink(); atmp.unlink()
    print(name, f"{total:.1f}s", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clean"); ap.add_argument("final"); ap.add_argument("out")
    ap.add_argument("--only"); ap.add_argument("--still", action="store_true")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    audio = None
    if not a.still:
        wav = out / "_longform_mix.wav"
        if not wav.exists():
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", a.final, "-vn", "-ac", "2", "-ar", str(SR),
                            "-c:a", "pcm_f32le", str(wav)], check=True)
        audio = sf.read(wav, dtype="float32")[0]
    for name, cfg in SHORTS.items():
        if a.only and a.only not in name:
            continue
        make(name, cfg, a.clean, audio, out, a.still)


if __name__ == "__main__":
    main()
