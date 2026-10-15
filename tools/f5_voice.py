"""Speak lines in Maaran Thatha's locked voice with AI4Bharat IndicF5 (MIT).

Usage (in the f5 venv, HF_TOKEN set):
    python tools/f5_voice.py LINES.json OUT_DIR [--ids L01,L02] [--speed 0.95]

IndicF5 copies the voice from a short reference clip. Thatha's reference is
assets/voice/thatha_ref.wav, a real elderly Tamil farmer from AI4Bharat
IndicVoices-R (CC BY 4.0, credited in assets/voice/CREDITS.md), and its
spoken-Tamil transcript is thatha_ref.txt. Writes one 24 kHz WAV per line.

The model is loaded directly from its safetensors weights instead of through
transformers' AutoModel, whose newer versions break IndicF5's remote code.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from f5_tts.infer.utils_infer import infer_process, load_model, load_vocoder, preprocess_ref_audio_text
from f5_tts.model import DiT
from huggingface_hub import hf_hub_download
from safetensors.torch import load_file

ROOT = Path(__file__).resolve().parent.parent
REF_WAV = ROOT / "assets/voice/thatha_ref.wav"
REF_TXT = ROOT / "assets/voice/thatha_ref.txt"
REPO = "ai4bharat/IndicF5"


def load():
    vocoder = load_vocoder(vocoder_name="vocos", is_local=False, device="cpu")
    model = load_model(DiT, dict(dim=1024, depth=22, heads=16, ff_mult=2, text_dim=512, conv_layers=4),
                       mel_spec_type="vocos", vocab_file=hf_hub_download(REPO, "checkpoints/vocab.txt"),
                       device="cpu")
    weights = load_file(hf_hub_download(REPO, "model.safetensors"))
    prefix = "ema_model._orig_mod."
    model.load_state_dict({k[len(prefix):]: v for k, v in weights.items() if k.startswith(prefix)})
    return model.eval(), vocoder


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lines")
    ap.add_argument("out")
    ap.add_argument("--ids", default="")
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--ref-wav", default=str(REF_WAV))
    ap.add_argument("--ref-txt", default=str(REF_TXT))
    a = ap.parse_args()

    model, vocoder = load()
    ref_audio, ref_text = preprocess_ref_audio_text(a.ref_wav, Path(a.ref_txt).read_text().strip(), device="cpu")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    wanted = set(filter(None, a.ids.split(",")))
    for line in json.loads(Path(a.lines).read_text()):
        if wanted and line["id"] not in wanted:
            continue
        torch.manual_seed(a.seed)
        audio, sr, _ = infer_process(ref_audio, ref_text, line["tamil"], model, vocoder,
                                     mel_spec_type="vocos", speed=line.get("speed", a.speed), device="cpu")
        sf.write(out / f"{line['id']}.wav", np.asarray(audio, dtype=np.float32), sr)
        print(line["id"], "done", flush=True)


if __name__ == "__main__":
    main()
