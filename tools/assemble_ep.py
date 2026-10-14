"""Assemble an episode from its shots, cut exactly on the voice, with the nature sound bed.

Usage:
    python tools/assemble_ep.py EDIT.json OUT.mp4

EDIT.json (paths relative to the file):
{
  "voice": "voice.wav", "ambience_seed": 3,
  "shots": [
    {"video": "hook.mp4", "start": 0.0, "end": 6.1, "src_start": 0.0},   # a piece of a clip
    ...
  ]
}
Each shot shows its clip from src_start for (end - start) seconds; the pieces butt together
on the voice timeline. AI clips (16 fps, 480x848) are motion-interpolated to 25 fps and
upscaled to 1080x1920; code clips are already 1080x1920. The last shot is held on its final
frame if the clip is shorter than its slot.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def piece(src, ss, dur, out):
    vf = ("minterpolate=fps=25:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,"
          "scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,"
          f"tpad=stop_mode=clone:stop_duration={dur}")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{ss:.3f}", "-i", str(src), "-t", f"{dur + 0.5:.3f}",
                    "-vf", vf, "-t", f"{dur:.3f}", "-an", "-c:v", "libx264", "-crf", "16", "-preset", "medium",
                    "-pix_fmt", "yuv420p", "-r", "25", str(out)], check=True)


def main():
    edit = Path(sys.argv[1])
    out = sys.argv[2]
    cfg = json.loads(edit.read_text())
    base = edit.parent
    tmp = Path(tempfile.mkdtemp())
    lst = []
    for i, s in enumerate(cfg["shots"]):
        p = tmp / f"p{i:02d}.mp4"
        piece(base / s["video"], s.get("src_start", 0.0), s["end"] - s["start"], p)
        lst.append(f"file '{p}'")
        print("piece", i, s["video"], round(s["end"] - s["start"], 2), flush=True)
    (tmp / "list.txt").write_text("\n".join(lst))
    video = tmp / "video.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"),
                    "-c", "copy", str(video)], check=True)
    total = cfg["shots"][-1]["end"]
    py = sys.executable
    subprocess.run([py, str(ROOT / "tools/ambience.py"), str(tmp / "amb.wav"), str(total + 1),
                    "--seed", str(cfg.get("ambience_seed", 3))], check=True)
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
