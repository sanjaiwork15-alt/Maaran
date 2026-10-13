"""Generate Maaran Thatha's voice for an episode.

Usage:
    python tools/tts.py LINES.json OUT_DIR

LINES.json is a list of
    {"id": "L01", "tamil": "...", "pause_after": 0.35, "expressiveness": 2.1}
("pause_after" and "expressiveness" are optional). The Tamil-script text is only
for the voice engine; the readable script is the Tanglish episode file.

Each line is synthesised in ONE pass (no sentence splitting), so the model makes
its own natural pauses at commas and full stops instead of hard cuts. Lines are
then joined with soft fades. Writes voice.wav (mono, 44.1 kHz) and timings.json,
which the animation uses to sync the mouth.
"""
import json
import os
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
SETTINGS = json.loads((ROOT / "voice_settings.json").read_text())
MODELS = Path(os.environ.get("MAARAN_WORK", Path.home() / ".maaran")) / "models" / "ta"
SR = 44100


def load_synth():
    from TTS.utils.synthesizer import Synthesizer

    cfg = json.loads((MODELS / "fastpitch/config.json").read_text())
    speakers = str(MODELS / "fastpitch/speakers.pth")
    cfg["speakers_file"] = speakers
    cfg["model_args"]["speakers_file"] = speakers
    tmp_cfg = Path(tempfile.mkdtemp()) / "config.json"
    tmp_cfg.write_text(json.dumps(cfg))
    synth = Synthesizer(
        tts_checkpoint=str(MODELS / "fastpitch/best_model.pth"),
        tts_config_path=str(tmp_cfg),
        tts_speakers_file=speakers,
        vocoder_checkpoint=str(MODELS / "hifigan/best_model.pth"),
        vocoder_config=str(MODELS / "hifigan/config.json"),
        use_cuda=False,
    )
    # Expressive pitch: widen the predicted pitch contour around its mean and
    # lower it slightly. This happens inside the model, so it stays natural.
    model = synth.tts_model
    predict = model.pitch_predictor.forward
    model.prosody = {"scale": SETTINGS["pitch_expressiveness"], "shift": SETTINGS["pitch_shift"]}

    def expressive(*args, **kwargs):
        pitch = predict(*args, **kwargs)
        mean = pitch.mean(dim=-1, keepdim=True)
        return (pitch - mean) * model.prosody["scale"] + mean + model.prosody["shift"]

    model.pitch_predictor.forward = expressive
    model.length_scale = SETTINGS["length_scale"]
    return synth


def read_wav(path):
    with wave.open(str(path)) as w:
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return data.astype(np.float32) / 32768


def write_wav(path, x):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def trim(x, threshold=0.01):
    loud = np.where(np.abs(x) > threshold)[0]
    if len(loud) == 0:
        return x
    pad = int(0.03 * SR)
    return x[max(0, loud[0] - pad): loud[-1] + pad]


def soften(x):
    fi = int(SETTINGS["fade_in_ms"] / 1000 * SR)
    fo = int(SETTINGS["fade_out_ms"] / 1000 * SR)
    x = x.copy()
    x[:fi] *= np.sin(np.linspace(0, np.pi / 2, fi)) ** 2
    x[-fo:] *= np.cos(np.linspace(0, np.pi / 2, fo)) ** 2
    return x


def render_line(synth, line, tmp):
    synth.tts_model.prosody["scale"] = line.get("expressiveness", SETTINGS["pitch_expressiveness"])
    raw = tmp / f"{line['id']}_raw.wav"
    proc = tmp / f"{line['id']}.wav"
    wav = synth.tts(line["tamil"], speaker_name=SETTINGS["speaker"], split_sentences=False)
    synth.save_wav(wav, str(raw))
    chain = f"aresample={SR},rubberband=pitch={SETTINGS['rubberband_pitch']}:formant=preserved:pitchq=quality,{SETTINGS['post_filter']}"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(raw), "-af", chain,
                    "-ar", str(SR), "-ac", "1", str(proc)], check=True)
    return soften(trim(read_wav(proc)))


def main(lines_file, out_dir):
    lines = json.loads(Path(lines_file).read_text())
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp())
    synth = load_synth()

    pieces, timings, t = [], [], 0.0
    for line in lines:
        clip = render_line(synth, line, tmp)
        pause = line.get("pause_after", SETTINGS["pause_after_default"])
        timings.append({"id": line["id"], "start": round(t, 3), "end": round(t + len(clip) / SR, 3)})
        pieces += [clip, np.zeros(int(pause * SR), dtype=np.float32)]
        t += len(clip) / SR + pause

    write_wav(tmp / "joined.wav", np.concatenate(pieces))
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(tmp / "joined.wav"),
                    "-af", f"loudnorm=I={SETTINGS['loudness_lufs']}:TP=-1.5", "-ar", str(SR),
                    str(out / "voice.wav")], check=True)
    (out / "timings.json").write_text(json.dumps(timings, indent=1))
    print(f"voice.wav: {t:.1f}s, {len(lines)} lines")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
