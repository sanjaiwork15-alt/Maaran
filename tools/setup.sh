#!/usr/bin/env bash
# One-time setup for a fresh cloud session: installs the IndicF5 voice engine
# (AI4Bharat, MIT) and downloads its model from HuggingFace (needs HF_TOKEN with
# access to ai4bharat/IndicF5). Takes ~10 minutes.
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

echo "Setup done. Voice: HF_HOME=$WORK/hf $WORK/f5/bin/python tools/f5_voice.py LINES.json OUT_DIR"
