"""Speak lines in Maaran Thatha's locked voice with AI4Bharat IndicF5 (MIT).

Usage (in the f5 venv, HF_TOKEN set):
    python tools/f5_voice.py LINES.json OUT_DIR [--ids L01,L02]

IndicF5 copies the voice from a short reference clip. Thatha's reference is
assets/voice/thatha_ref.wav, a clip designed with Indic Parler-TTS (synthetic,
so no real person's voice is cloned), and its Tamil text is thatha_ref.txt.
Writes one 24 kHz WAV per line.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from transformers import AutoModel

ROOT = Path(__file__).resolve().parent.parent
REF_WAV = ROOT / "assets/voice/thatha_ref.wav"
REF_TXT = ROOT / "assets/voice/thatha_ref.txt"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lines")
    ap.add_argument("out")
    ap.add_argument("--ids", default="")
    ap.add_argument("--ref-wav", default=str(REF_WAV))
    ap.add_argument("--ref-txt", default=str(REF_TXT))
    a = ap.parse_args()

    model = AutoModel.from_pretrained("ai4bharat/IndicF5", trust_remote_code=True)
    ref_text = Path(a.ref_txt).read_text().strip()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    wanted = set(filter(None, a.ids.split(",")))
    for line in json.loads(Path(a.lines).read_text()):
        if wanted and line["id"] not in wanted:
            continue
        audio = model(line["tamil"], ref_audio_path=a.ref_wav, ref_text=ref_text)
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768
        sf.write(out / f"{line['id']}.wav", np.asarray(audio, dtype=np.float32), 24000)
        print(line["id"], "done", flush=True)


if __name__ == "__main__":
    main()
