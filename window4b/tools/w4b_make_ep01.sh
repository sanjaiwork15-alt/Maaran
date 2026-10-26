#!/usr/bin/env bash
# Window 4B Ep 1, end to end (CPU only, ~1.5 h unattended on 4 cores):
#   bash window4b/tools/w4b_make_ep01.sh OUT_DIR
# Builds the masks for both masters, the soundtrack, renders the 16:9 video and the 9:16 Short,
# and muxes each with the sound at -14 LUFS.
set -euo pipefail
OUT="${1:?OUT_DIR}"; mkdir -p "$OUT"
PY="${PY:-$HOME/.maaran/toon/bin/python}"
T="$(cd "$(dirname "$0")" && pwd)"
for v in h v; do [ -f "$OUT/masks_$v.npz" ] || "$PY" "$T/w4b_masks.py" $v "$OUT/masks_$v.npz"; done
[ -f "$OUT/ep01_sound.wav" ] || "$PY" "$T/w4b_sound.py" "$OUT/ep01_sound.wav"
for v in h v; do
  name=$([ $v = h ] && echo 16x9 || echo 9x16)
  [ -f "$OUT/ep01_${name}_silent.mp4" ] || "$PY" "$T/w4b_render.py" $v "$OUT/masks_$v.npz" "$OUT/ep01_${name}_silent.mp4"
  ffmpeg -loglevel error -y -i "$OUT/ep01_${name}_silent.mp4" -i "$OUT/ep01_sound.wav" -map 0:v -map 1:a \
    -c:v copy -af loudnorm=I=-14:TP=-1.5:LRA=11 -c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart \
    "$OUT/window4b_ep01_${name}.mp4"
done
echo "done: $OUT/window4b_ep01_16x9.mp4 $OUT/window4b_ep01_9x16.mp4"
