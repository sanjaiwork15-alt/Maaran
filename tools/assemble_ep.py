"""Assemble an episode from its shots, cut exactly on the voice, with the nature sound bed.

Usage:
    python tools/assemble_ep.py EDIT.json OUT.mp4

EDIT.json (paths relative to the file):
{
  "voice": "voice.wav", "ambience_seed": 3,
  "shots": [
    {"video": "hook.mp4", "start": 0.0, "end": 6.1, "src_start": 0.0},   # a piece of a clip
    {"video": "hook.mp4", "start": 6.1, "end": 9.0, "src_start": 6.1,
     "zoom": [1.0, 1.15], "focus": [0.5, 0.35]},                         # slow push-in / punch-in
    ...
  ]
}
"zoom" is a punch-in factor (1.3 = 30% closer) or [from, to] for a smooth push over the shot;
"focus" is the point to zoom on, as fractions of the frame (default: his face, [0.5, 0.35]).
Each shot shows its clip from src_start for (end - start) seconds; the pieces butt together
on the voice timeline. AI clips (16 fps, 480x848) are motion-interpolated to 25 fps and
upscaled to 1080x1920; code clips are already 1080x1920. The last shot is held on its final
frame if the clip is shorter than its slot.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def zoom_piece(src, out, dur, zoom, focus):
    """Re-frame a 1080x1920 piece with a (possibly animated) zoom, sub-pixel smooth (no zoompan jitter)."""
    import numpy as np
    from PIL import Image
    W, H = 1080, 1920
    z0, z1 = (zoom, zoom) if isinstance(zoom, (int, float)) else zoom
    fx, fy = focus
    n = round(dur * 25)
    dec = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", str(src), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", "25", "-i", "-", "-c:v", "libx264", "-crf", "16", "-preset", "medium",
                            "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
    for i in range(n):
        buf = dec.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            break
        u = i / max(1, n - 1)
        u = u * u * (3 - 2 * u)                       # ease in/out
        z = z0 + (z1 - z0) * u
        w, h = W / z, H / z
        x0 = min(max(fx * W - w / 2, 0), W - w)
        y0 = min(max(fy * H - h / 2, 0), H - h)
        img = Image.frombuffer("RGB", (W, H), buf).transform((W, H), Image.EXTENT, (x0, y0, x0 + w, y0 + h),
                                                             Image.BICUBIC)
        enc.stdin.write(img.tobytes())
    dec.stdout.close()
    dec.wait()
    enc.stdin.close()
    enc.wait()


def piece(src, ss, n, out):
    """n frames (25 fps) of src from ss on, upscaled/cropped to 1080x1920."""
    dur = n / 25
    fps = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=r_frame_rate",
                          "-of", "csv=p=0", str(src)], capture_output=True, text=True).stdout.strip()
    interp = "" if fps == "25/1" else "minterpolate=fps=25:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,"
    lead = max(0.0, -ss)                  # a negative start holds the first frame
    ss = max(0.0, ss)
    vf = (f"{interp}scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,"
          f"tpad=start_mode=clone:start_duration={lead}:stop_mode=clone:stop_duration={dur}")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{ss:.3f}", "-i", str(src), "-t", f"{dur + 0.5:.3f}",
                    "-vf", vf, "-frames:v", str(n), "-an", "-c:v", "libx264", "-crf", "16", "-preset", "medium",
                    "-pix_fmt", "yuv420p", "-r", "25", str(out)], check=True)


def main():
    edit = Path(sys.argv[1])
    out = sys.argv[2]
    cfg = json.loads(edit.read_text())
    base = edit.resolve().parent
    tmp = Path(tempfile.mkdtemp())
    cache = base / ".pieces"                  # finished pieces, reused when a shot is unchanged
    cache.mkdir(exist_ok=True)

    def make(i, s):
        n = round(s["end"] * 25) - round(s["start"] * 25)   # cumulative 25 fps grid: cuts never drift
        src = base / s["video"]
        key = hashlib.sha1(json.dumps([str(src), src.stat().st_mtime, s.get("src_start", 0.0), n,
                                       s.get("zoom"), s.get("focus")]).encode()).hexdigest()[:16]
        done = cache / f"{key}.mp4"
        if not done.exists():
            p = tmp / f"p{i:02d}.mp4"
            piece(src, s.get("src_start", 0.0), n, p)
            if s.get("zoom"):
                zp = tmp / f"p{i:02d}z.mp4"
                zoom_piece(p, zp, n / 25, s["zoom"], s.get("focus", [0.5, 0.35]))
                p = zp
            shutil.move(str(p), done)
        print("piece", i, s["video"], n, "frames", flush=True)
        return done

    # minterpolate is single-threaded: render the pieces side by side, one per core
    with ThreadPoolExecutor(os.cpu_count() or 1) as ex:
        pieces = list(ex.map(lambda a: make(*a), enumerate(cfg["shots"])))
    lst = [f"file '{p}'" for p in pieces]
    (tmp / "list.txt").write_text("\n".join(lst))
    video = tmp / "video.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"),
                    "-c", "copy", str(video)], check=True)
    total = cfg["shots"][-1]["end"]
    py = sys.executable
    subprocess.run([py, str(ROOT / "tools/ambience.py"), str(tmp / "amb.wav"), str(total + 1),
                    "--seed", str(cfg.get("ambience_seed", 3))] +
                   (["--rain", ",".join(f"{a}:{b}" for a, b in cfg["rain"])] if cfg.get("rain") else []) +
                   (["--thunder", ",".join(str(v) for v in cfg["thunder"])] if cfg.get("thunder") else []), check=True)
    subprocess.run([py, str(ROOT / "tools/mix.py"), str(base / cfg["voice"]), str(tmp / "amb.wav"), str(tmp / "mix.wav"),
                    "--bed-db", "-2", "--tail", str(max(0.0, total - float(subprocess.run(
                        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(base / cfg["voice"])],
                        capture_output=True, text=True).stdout)))], check=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(video), "-i", str(tmp / "mix.wav"),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.3f}",
                    "-movflags", "+faststart", out], check=True)
    print("saved", out)


if __name__ == "__main__":
    main()
