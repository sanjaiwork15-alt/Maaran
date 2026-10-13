"""Design Maaran Thatha's voice with AI4Bharat Indic Parler-TTS (Apache-2.0).

Usage (in the parler venv, HF_TOKEN set):
    python tools/parler_voice.py LINES.json OUT_DIR --desc "..." [--seed 7] [--ids L01,L02]

Each line is generated from a plain-English description of the voice. The same
description and seed are used for every line, which keeps the voice close, but
not identical, from line to line. To lock one exact voice, use the best line
as the reference clip for IndicF5 (tools/f5_voice.py).
"""
import argparse
import json
from pathlib import Path

import soundfile as sf
import torch
from parler_tts import ParlerTTSForConditionalGeneration
from transformers import AutoTokenizer

REPO = "ai4bharat/indic-parler-tts"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lines")
    ap.add_argument("out")
    ap.add_argument("--desc", required=True)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--ids", default="")
    a = ap.parse_args()

    torch.set_num_threads(torch.get_num_threads())
    model = ParlerTTSForConditionalGeneration.from_pretrained(REPO).eval()
    tok = AutoTokenizer.from_pretrained(REPO)
    desc_tok = AutoTokenizer.from_pretrained(model.config.text_encoder._name_or_path)
    desc = desc_tok(a.desc, return_tensors="pt")

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    wanted = set(filter(None, a.ids.split(",")))
    for line in json.loads(Path(a.lines).read_text()):
        if wanted and line["id"] not in wanted:
            continue
        torch.manual_seed(a.seed)
        prompt = tok(line["tamil"], return_tensors="pt")
        with torch.inference_mode():
            audio = model.generate(input_ids=desc.input_ids, attention_mask=desc.attention_mask,
                                   prompt_input_ids=prompt.input_ids,
                                   prompt_attention_mask=prompt.attention_mask)
        sf.write(out / f"{line['id']}.wav", audio.cpu().numpy().squeeze(), model.config.sampling_rate)
        print(line["id"], "done", flush=True)


if __name__ == "__main__":
    main()
