# Thatha, Oru Doubt! Episode 8 – Mazhai Peinja Mann Vaasana Yen Varudhu? 🌧️

Final video: `doubt_ep08.mp4` (48.7 s, 1080x1920, 25 fps, -14.1 LUFS); chat copy `doubt_ep08_share.mp4`.
Thumbnail `thumbnail.png`, posting text `description.md`, script + fact check `script.md`, edit `edit.json`.
**No GPU.** New location: the semman kaadu field (well and hut) when the first monsoon rain comes – the sunny sky
replaced by storm clouds drawn in code, grey light, then wet red soil (`make_frames.py`, helpers in
`tools/toon/rain.py`). Four poses from approved Groundnut frames not used in this series before: f_mbreath /
f_mbreath_w (hand on chest, the smell; dry / wet soil), f_msoil (crouching, damp earth in his hands), f_mpoint
(pointing at the soil), f_mstick (standing with his stick). 26 cuts.
New in talk.py: `rain` (streaks + splash rings), `scent` (a warm glowing stream from the soil to his nose) and
`inhale` (eyes shut, brows up, chest rises). New in `tools/ambience.py`: rain and thunder synthesised in code
(`"rain"` level curve and `"thunder"` times in `edit.json`); the birds go quiet as the rain builds.

| Time | Scene | Made with |
|---|---|---|
| 0–9.3 | Clouds roll over the dry field, "Aahaa…" (eyes shut, the smell drifting to him), first drops on the soil | `storm`, f_mbreath + scent + light rain |
| 9.3–19.0 | Drops on dry cracked soil; crouched with damp earth; bacteria making geosmin (golden specks) | `drops`, f_msoil, `section` |
| 19.0–31.0 | Drop lands, air bubbles burst, tiny droplets carry the scent up – to his nose; the field in the rain | `drops`, `section`, f_mbreath_w + scent, `rainfield` |
| 31.0–42.6 | "Vivasaayikku mazhai vandha sandhosham… enakku pazhaya ninaivugal!" (chuckle); "mudivu panna mudiyaadhu" | f_mpoint (pointing at the wet soil), f_mbreath_w, `rainfield` |
| 42.6–48.7 | Comment question in the rain | f_mstick, `rainfield` |

Review fixes: pale blue fringe of the old sky on hair and leaves (sky mask grown, cut-out eroded); the storm's
cloud front was a hard vertical seam (now a wide soft front); opening re-ordered to clouds → breath as scripted; the
crouch pose's mouth line moved off the mustache; a 4.7 s run of field shots split with a face close-up.

Sound credits: "red_vented_bulbul.wav" by soundbytez and "rustling_leaves.wav" by laurenmg95 (freesound.org,
CC BY 3.0); other ambience CC0; rain and thunder made in code.
