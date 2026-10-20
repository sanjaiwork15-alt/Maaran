# Thatha, Oru Doubt! Episode 3 – Vengayam Vettumbodhu Yen Kannula Thanni Varudhu?

Final video: `doubt_ep03.mp4` (45.1 s, 1080x1920, 25 fps, -14.1 LUFS); chat copy `doubt_ep03_share.mp4`.
Thumbnail `thumbnail.png` (a frame of the crying hook), posting text `description.md`, script + fact check `script.md`,
edit `edit.json`. **No GPU.** Two corners of the kitchen: `make_frames.py` builds f_kon (Ep 2 Thatha layers with a
code-drawn knife and cut onion) and f_kpod (Groundnut Ep 9 f_pod_s3, the pod inpainted away, an onion in his raised hand,
on the mirrored kitchen plate). Talking shots: `tools/toon/talk.py` (rig `rig.json`) – new: `tears`, `laugh`, `grin`.
The 1-word line "Aiyayo!" came out silent from IndicF5; regenerated with `--ids L1a --seed 3 --speed 0.85`.

| Time | Scene | Made with |
|---|---|---|
| 0–6.9 | "Aiyayo!" – crying, then a suspicious look at the onion | f_kon + talk.py tears, gaze |
| 6.9–14.6 | Knife slicing onion, vapour; "saapdumbodhu azhuromaa?" | `onion.py` chop, talk.py |
| 14.6–24.6 | Science: knife breaks cells, compounds mix, gas rises | talk.py, `onion.py` cells |
| 24.6–26.5 | "Adhanaala dhaan kannula thanni varudhu!" – teary close-up | talk.py tears |
| 26.5–35.1 | Onion held up, grin, mock head shake, chuckle | f_kpod + talk.py (grin, shake, laugh) |
| 35.1–45.1 | Comment question → onion on the chopping board | f_kpod + talk.py, `onion.py` board |

Sound credits: "red_vented_bulbul.wav" by soundbytez and "rustling_leaves.wav" by laurenmg95 (freesound.org,
CC BY 3.0); other ambience CC0.
