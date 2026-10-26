"""Window 4B: cut the finished Ep 1 long form into three connected 9:16 Shorts.

    python window4b/tools/w4b_shorts.py CLEAN_16x9.mp4 FINAL_16x9.mp4 OUT_DIR [--still]

Pure editing of the existing episode: CLEAN is the same render without the burned-in time
markers (they sit in the top-left corner, which a vertical crop would slice); the markers are
redrawn in the Shorts safe zone in the same style and with the same timing. Audio is the long
form's final mix (FINAL's track), cut with short crossfades. Nothing is regenerated.

Each Short is a list of source ranges; each range has crop keyframes (source time -> left edge of
a 608 px wide window in the 1920 x 1080 source), linear in between, with hard reframes only at
the time jumps (under the whoosh).
"""
import argparse
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from timeline import params, ease  # noqa: E402

FPS = 24
SRC_W, SRC_H = 1920, 1080
CW = 608                     # 9:16 window in the source
OW, OH = 1080, 1920
SR = 48000
FONT = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
MARK_XY = (72, 330)          # below the Shorts top bar
CARD_Y = 760                 # end text: upper middle, clear of the caption/buttons area

SHORTS = {
    "short1_the_rain_wont_stop": dict(
        ranges=[(0.0, 48.0, [(0, 880), (2.0, 880), (4.5, 640), (11.99, 640), (12.0, 1312), (30.0, 850),
                             (30.01, 300), (48, 300)])],
        card="One month of rain was\nonly the beginning…", card_at=45.6,
        end="cut",            # rain cut at the last moment
        tail=0.0),
    "short2_the_city_is_disappearing": dict(
        ranges=[(50.0, 56.6, [(50, 300), (56.6, 330)]),
                (57.0, 61.6, [(57, 1230), (61.6, 1200)]),
                (69.5, 81.5, [(69.5, 520), (81.5, 560)]),
                (89.5, 99.5, [(89.5, 560), (99.5, 560)]),
                (109.5, 116.3, [(109.5, 502), (116.3, 502)])],
        card="But the bridge was\nabout to break…", card_at=0.25,   # on black, after the cut
        end="black", tail=2.8, bed=(100.0, 103.0)),
    "short3_one_year_later": dict(
        ranges=[(110.0, 150.0, [(110, 502), (124.99, 502), (125.0, 290), (137.99, 290), (138.0, 330),
                                (147.99, 330), (148.0, 557), (150, 557)])],
        card="One year. One city.\nOne window.", card_at=0.2,
        end="black", tail=2.6),
}


def crop_x(keys, t):
    ts = [k[0] for k in keys]; xs = [k[1] for k in keys]
    return int(round(np.clip(np.interp(t, ts, xs), 0, SRC_W - CW)))


def text_layer(lines, size, alpha, xy=None, center=False):
    font = ImageFont.truetype(FONT, size)
    lay = Image.new("L", (OW, OH), 0); sh = Image.new("L", (OW, OH), 0)
    d, ds = ImageDraw.Draw(lay), ImageDraw.Draw(sh)
    y = xy[1] if xy else CARD_Y
    for line in lines.split("\n"):
        w = d.textlength(line, font=font)
        x = (OW - w) / 2 if center else xy[0]
        d.text((x, y), line, font=font, fill=255)
        ds.text((x + 3, y + 4), line, font=font, fill=255)
        y += int(size * 1.25)
    sh = sh.filter(ImageFilter.GaussianBlur(7))
    a = np.asarray(lay, np.float32)[..., None] / 255 * alpha
    s = np.asarray(sh, np.float32)[..., None] / 255 * alpha * 0.6
    return a, s


def overlay(frame, a, s):
    f = frame.astype(np.float32) / 255
    f = f * (1 - s)
    f = f * (1 - a) + np.array([0.97, 0.98, 1.0], np.float32) * a
    return (np.clip(f, 0, 1) * 255).astype(np.uint8)


def frames(src, t0, t1):
    """Decode source frames t0..t1 (frame accurate)."""
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", f"{t0:.4f}", "-i", src, "-t", f"{t1 - t0:.4f}",
                          "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    n = int(round((t1 - t0) * FPS))
    for i in range(n):
        buf = p.stdout.read(SRC_W * SRC_H * 3)
        if len(buf) < SRC_W * SRC_H * 3:
            break
        yield t0 + i / FPS, np.frombuffer(buf, np.uint8).reshape(SRC_H, SRC_W, 3)
    p.stdout.close(); p.wait()


def reframe(img, x0):
    crop = img[:, x0:x0 + CW]
    out = cv2.resize(crop, (OW, OH), interpolation=cv2.INTER_LANCZOS4)
    blur = cv2.GaussianBlur(out, (0, 0), 1.2)
    return cv2.addWeighted(out, 1.35, blur, -0.35, 0)        # light sharpening after the upscale


def marker(t_src):
    p = params(t_src)
    if p["closeup"] or p["label_a"] <= 0.01:
        return None
    return p["label"], p["label_a"]


def build_audio(audio, cfg, total):
    """Cut the long form's mix at the same ranges, 60 ms crossfades, then the ending treatment."""
    out = np.zeros((int(total * SR) + SR, 2), np.float32)
    pos = 0; xf = int(0.06 * SR)
    for i, (a, b, _) in enumerate(cfg["ranges"]):
        seg = audio[int(a * SR):int(b * SR)].copy()
        if i > 0:
            seg[:xf] *= np.linspace(0, 1, xf)[:, None]
            out[pos - xf:pos] *= np.linspace(1, 0, xf)[:, None]
            pos -= xf
        out[pos:pos + len(seg)] += seg
        pos += len(seg)
    body = pos
    if cfg["end"] == "cut":
        n = int(0.6 * SR)                                  # ambience dips, then the rain stops dead
        out[body - n - int(0.9 * SR):body - n] *= np.linspace(1, 0.55, int(0.9 * SR))[:, None]
        out[body - n:body] = 0
    else:
        out[body - int(0.03 * SR):body] *= np.linspace(1, 0, int(0.03 * SR))[:, None]
        if cfg.get("bed"):                                 # the rain carries on, faintly, under black
            a, b = cfg["bed"]
            bed = audio[int(a * SR):int(b * SR)] * 0.18
            n = min(len(bed), int(cfg["tail"] * SR))
            bed = bed[:n] * np.minimum(1, np.linspace(0, 6, n))[:, None] * np.linspace(1, 0, n)[:, None] ** 0.5
            out[body:body + n] += bed
        else:                                              # Short 3: the plink rings out into black
            end = cfg["ranges"][-1][1]
            tail = audio[int(end * SR) - 1:int(end * SR) - 1 + int(cfg["tail"] * SR)]
            out[body:body + len(tail)] += tail
    out[: int(0.25 * SR)] *= np.linspace(0, 1, int(0.25 * SR))[:, None]
    return out[: int(total * SR)]


def make(name, cfg, clean, final, out_dir, audio, still=False):
    W = out_dir / f"{name}.mp4"
    body = sum(b - a for a, b, _ in cfg["ranges"])
    total = body + cfg["tail"]
    if still:
        for a, b, keys in cfg["ranges"]:
            for t, img in frames(clean, a, b):
                if abs((t - a) % 4) < 1 / FPS:
                    cv2.imwrite(str(out_dir / f"{name}_{t:06.2f}.png"), reframe(img, crop_x(keys, t)))
        return
    vtmp = out_dir / f"{name}_v.mp4"; atmp = out_dir / f"{name}.wav"
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                            "-s", f"{OW}x{OH}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow",
                            "-crf", "17", "-pix_fmt", "yuv420p", str(vtmp)], stdin=subprocess.PIPE)
    clock = 0.0
    last = None
    for a, b, keys in cfg["ranges"]:
        for t, img in frames(clean, a, b):
            f = reframe(img, crop_x(keys, t))
            m = marker(t)
            if m:
                f = overlay(f, *text_layer(m[0], 68, m[1], MARK_XY))
            if cfg["end"] == "cut" and clock >= cfg["card_at"]:
                f = overlay(f, *text_layer(cfg["card"], 62, ease((clock - cfg["card_at"]) / 0.6), center=True))
            enc.stdin.write(f.tobytes()); last = f; clock += 1 / FPS
    black = np.zeros((OH, OW, 3), np.uint8)
    n_tail = int(round(cfg["tail"] * FPS))
    for i in range(n_tail):
        k = ease((i / FPS - cfg["card_at"]) / 0.6)
        f = overlay(black, *text_layer(cfg["card"], 62, k, center=True)) if k > 0 else black
        enc.stdin.write(f.tobytes())
    enc.stdin.close(); enc.wait()
    sf.write(atmp, build_audio(audio, cfg, total), SR, subtype="PCM_24")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(vtmp), "-i", str(atmp), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(W)],
                   check=True)
    vtmp.unlink(); atmp.unlink()
    print(name, f"{total:.1f}s", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clean"); ap.add_argument("final"); ap.add_argument("out")
    ap.add_argument("--still", action="store_true")
    ap.add_argument("--only")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    wav = out / "_longform_mix.wav"
    if not a.still and not wav.exists():
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", a.final, "-vn", "-ac", "2", "-ar", str(SR),
                        "-c:a", "pcm_f32le", str(wav)], check=True)
    audio = None if a.still else sf.read(wav, dtype="float32")[0]
    for name, cfg in SHORTS.items():
        if a.only and a.only not in name:
            continue
        make(name, cfg, a.clean, a.final, out, audio, a.still)


if __name__ == "__main__":
    main()
