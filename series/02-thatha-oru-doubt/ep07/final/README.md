# Thatha, Oru Doubt! Episode 7 – Erumbunga Eppadi Varisaiyaa Pogudhu? 🐜

Final video: `doubt_ep07.mp4` (46.3 s, 1080x1920, 25 fps, -14.4 LUFS); chat copy `doubt_ep07_share.mp4`.
Thumbnail `thumbnail.png`, posting text `description.md`, script + fact check `script.md`, edit `edit.json`.
**No GPU.** New location: outside the house – the thinnai at tea time (Groundnut Ep 10 art) and a closer crop of the
verandah (owner's 07_home art, different from Ep 6's wide view). Four poses (`make_frames.py`): f_atea (tumbler in a
davara over the bowl), f_afin (kneeling, hand by the ant line), f_aphone (mobile phone held up), f_atwo (tea tumbler
+ murukku). New: live ants walking through the Thatha shots (`"ants"` overlay in `tools/toon/talk.py`, drawn by
`tools/toon/ants.py`, which also makes the cut-aways). 25 cuts.

| Time | Scene | Made with |
|---|---|---|
| 0–6.4 | "Indha erumbunga mattum paarunga!" – tea on the thinnai, ants passing his feet; trail close-up | f_atea + ants, `trail` |
| 6.4–18.7 | Pheromone: the first ant leaves a scent, the others follow – ants crossing his fingers | f_afin + ants, `trail` |
| 18.7–32.1 | A scout finds a crumb, lays the trail home; others follow and the trail grows stronger | `scout`, f_atea, f_afin |
| 32.1–37.6 | "Erumbukku phone illa, WhatsApp group-um illa…" (head shake) → ants carrying a big crumb together | f_aphone, `team` |
| 37.6–46.3 | Comment question: where have you seen ants marching in a line? | f_atwo, f_atea + ants, `trail` |

Review fixes: the ant path in B/D now goes round his knee (it walked over the dhoti); the scout no longer starts at
the nest (`path_point` wrapped u = 1 to 0); E's full shot is knees-up (the Ep 3 raised-arm layer has no slipper on
his left foot); Real-ESRGAN's dhoti smudge removed from f_aphone / f_atwo (`tools/upscale.py` guard, see CLAUDE.md).

Sound credits: "red_vented_bulbul.wav" by soundbytez and "rustling_leaves.wav" by laurenmg95 (freesound.org,
CC BY 3.0); other ambience CC0.
