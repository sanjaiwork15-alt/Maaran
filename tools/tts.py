"""Generate Maaran Thatha's voice for an episode.

Usage:
    python tools/tts.py series/01-groundnut/ep01/voice_lines.json out_dir/

voice_lines.json is a list of {"id": "L01", "tamil": "...", "pause_after": 0.4}.
The Tamil-script text is only for the voice engine; the readable script is the
Tanglish episode file. Writes one processed clip per line plus voice.wav (all
lines joined) and timings.json, which the animation uses to sync the mouth.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parent
SETTINGS = json.loads((ROOT / "voice_settings.json").read_text())
MODELS = Path(os.environ.get("MAARAN_WORK", Path.home() / ".maaran")) / "models" / "ta"


def load_synth():
    from TTS.utils.synthesizer import Synthesizer

    cfg = json.loads((MODELS / "fastpitch/config.json").read_text())
    speakers = str(MODELS / "fastpitch/speakers.pth")
    cfg["speakers_file"] = speakers
    cfg["model_args"]["speakers_file"] = speakers
    tmp_cfg = Path(tempfile.mkdtemp()) / "config.json"
    tmp_cfg.write_text(json.dumps(cfg))
    return Synthesizer(
        tts_checkpoint=str(MODELS / "fastpitch/best_model.pth"),
        tts_config_path=str(tmp_cfg),
        tts_speakers_file=speakers,
        vocoder_checkpoint=str(MODELS / "hifigan/best_model.pth"),
        vocoder_config=str(MODELS / "hifigan/config.json"),
        use_cuda=False,
    )


def thatha_filter():
    s = SETTINGS
    p = s["pitch_factor"]
    return ",".join([
        f"asetrate=22050*{p}",
        "aresample=44100",
        f"atempo={s['tempo'] / p:.4f}",
        f"bass=g={s['bass_gain_db']}:f={s['bass_freq_hz']}",
        f"treble=g={s['treble_gain_db']}:f={s['treble_freq_hz']}",
        f"vibrato=f={s['vibrato_freq_hz']}:d={s['vibrato_depth']}",
        f"aecho={s['echo']}",
    ])


def duration(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", str(path)])
    return float(out)


def main(lines_file, out_dir):
    lines = json.loads(Path(lines_file).read_text())
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    synth = load_synth()

    timings, t = [], 0.0
    concat = out / "concat.txt"
    with concat.open("w") as cl:
        for line in lines:
            raw = out / f"{line['id']}_raw.wav"
            clip = out / f"{line['id']}.wav"
            synth.save_wav(synth.tts(line["tamil"], speaker_name=SETTINGS["speaker"]), str(raw))
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(raw),
                            "-af", thatha_filter(), "-ar", "44100", "-ac", "1", str(clip)], check=True)
            raw.unlink()
            d = duration(clip)
            pause = line.get("pause_after", 0.35)
            timings.append({"id": line["id"], "start": round(t, 3), "end": round(t + d, 3)})
            t += d + pause
            cl.write(f"file '{clip.name}'\n")
            sil = out / f"{line['id']}_pause.wav"
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                            "anullsrc=r=44100:cl=mono", "-t", str(pause), str(sil)], check=True)
            cl.write(f"file '{sil.name}'\n")

    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
                    "-i", str(concat), "-af", f"loudnorm=I={SETTINGS['loudness_lufs']}:TP=-1.5",
                    "-ar", "44100", str(out / "voice.wav")], check=True)
    (out / "timings.json").write_text(json.dumps(timings, indent=1))
    print(f"voice.wav: {t:.1f}s, {len(lines)} lines")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
