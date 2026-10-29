#!/bin/bash
# Day 3 v2 (owner: "some frames are not looking good"): draped blanket, real seated body, no unattached arm.
cd "$(dirname "$0")"
PY=$HOME/.maaran/toon/bin/python
for f in f_dbed f_dbed1 f_dbedw f_dpoint f_dup f_dpointr; do
  $HOME/.maaran/f5/bin/python -I ../../../../tools/upscale.py frames/$f.png frames/up/$f.png --scale 1.5 2>&1 | grep -E "guard|saved"
done
for c in cut_set cut_ring cut_rooster s_night_w s_dawn_w s_morn_w s_night_c s_morn_c s_eye; do
  $PY ../../../../tools/toon/morning.py $c.mp4 $c.json < /dev/null | tail -1
done
for s in B C D E; do $PY ../../../../tools/toon/talk.py rig.json $s shots/$s.mp4 < /dev/null 2>&1 | grep -E "saved|Error" | tail -1; done
rm -rf .pieces
$PY ../../../../tools/assemble_ep.py edit.json raw.mp4 < /dev/null 2>&1 | tail -1
ffmpeg -nostdin -loglevel error -y -i raw.mp4 -i sfx.wav -filter_complex "[0:a][1:a]amix=inputs=2:duration=first:normalize=0[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -movflags +faststart thatha_day03.mp4 && rm raw.mp4
ffmpeg -nostdin -loglevel error -y -i thatha_day03.mp4 -c:v libx264 -crf 21 -c:a aac -b:a 128k thatha_day03_share.mp4
echo DAY3DONE
