#!/usr/bin/env bash
# One-time setup for a fresh cloud session: installs the IndicF5 voice engine
# (AI4Bharat, MIT) and downloads its model from HuggingFace (needs HF_TOKEN with
# access to ai4bharat/IndicF5), plus the kaggle CLI and the animation/assembly env. ~10 min.
set -euo pipefail

WORK="${MAARAN_WORK:-$HOME/.maaran}"
mkdir -p "$WORK"
export UV_LINK_MODE=copy HF_HOME="$WORK/hf"

if [ ! -d "$WORK/f5" ]; then
  uv venv -q -p 3.11 "$WORK/f5"
fi
VIRTUAL_ENV="$WORK/f5" uv pip install -q torch torchaudio torchcodec \
  git+https://github.com/ai4bharat/IndicF5.git soundfile "pyarrow==20.0.0" praat-parselmouth
uv cache clean -q || true

"$WORK/f5/bin/python" -c "from huggingface_hub import snapshot_download; snapshot_download('ai4bharat/IndicF5')"

# Video tools: kaggle CLI (GPU jobs) and a small env for code animation / assembly
command -v kaggle >/dev/null || uv tool install -q kaggle
if [ ! -d "$WORK/toon" ]; then
  uv venv -q -p 3.11 "$WORK/toon"
fi
VIRTUAL_ENV="$WORK/toon" uv pip install -q cairosvg numpy scipy soundfile pillow opencv-python-headless
uv cache clean -q || true

echo "Setup done."
echo "  Voice:     HF_HOME=$WORK/hf $WORK/f5/bin/python tools/f5_voice.py LINES.json OUT_DIR"
echo "  Animation: $WORK/toon/bin/python tools/toon/cutaway.py ... / tools/assemble_ep.py ..."
echo "  GPU jobs:  tools/kaggle_run.sh comfy_jobs IN_DIR OUT_DIR   (needs KAGGLE_USERNAME, KAGGLE_API_TOKEN)"
