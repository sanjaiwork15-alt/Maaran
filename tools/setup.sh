#!/usr/bin/env bash
# One-time setup for a fresh cloud session: installs the free Tamil voice engine
# and downloads the AI4Bharat Tamil model (~1.5 GB) from GitHub releases.
set -euo pipefail

WORK="${MAARAN_WORK:-$HOME/.maaran}"
mkdir -p "$WORK/models"

if [ ! -d "$WORK/venv" ]; then
  python3 -m venv "$WORK/venv"
fi
# shellcheck disable=SC1091
. "$WORK/venv/bin/activate"
pip install -q --upgrade pip
pip install -q torch torchaudio torchcodec coqui-tts "transformers>=4.57,<5" pillow numpy

if [ ! -d "$WORK/models/ta" ]; then
  curl -sSL -o "$WORK/models/ta.zip" \
    https://github.com/AI4Bharat/Indic-TTS/releases/download/v1-checkpoints-release/ta.zip
  unzip -q "$WORK/models/ta.zip" -d "$WORK/models"
  rm "$WORK/models/ta.zip"
fi

echo "Setup done. Activate with: . $WORK/venv/bin/activate"
