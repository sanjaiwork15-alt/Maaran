# Thatha, Oru Doubt! Episode 2 – Kothamalli Yen Ivlo Seekiram Vaadidudhu?

Final video: `doubt_ep02.mp4` (46.4 s, 1080x1920, 25 fps, -14.3 LUFS); chat copy `doubt_ep02_share.mp4`.
Thumbnail `thumbnail.png`, posting text `description.md`, script + fact check `script.md`, edit `edit.json`.
**No GPU.** New location: the village kitchen. `make_frames.py` builds the start frames from approved art: Thatha from
Ep 1's f_two_s3 (bananas inpainted away with LaMa, cut out with rembg) on the Ep 10 kitchen with its Thatha removed,
holding code-drawn coriander (`tools/toon/coriander.py`), his fingers pasted back over the stems.
Talking shots: `tools/toon/talk.py` (rig in `rig.json`) – new this episode: eye direction (`gaze`) and head shake.

| Time | Scene | Made with |
|---|---|---|
| 0–7.4 | "Aiyayo makkaley!" – looks at the fresh bunch, then the wilted one, then at us | f_kfw + talk.py (gaze) |
| 7.4–12.6 | Coriander sprinkled on sambar, steam | `coriander.py` sprinkle |
| 12.6–17.0 | "...yen ivlo seekiram sorndhu poidudhu?" – fresh vs wilted close-up | talk.py, `compare` |
| 17.0–26.1 | "Oru chinna science" – vapour leaves a leaf on a cut stem, it droops | talk.py, `water` |
| 26.1–33.4 | Sun vs shade bunch; head shake "veyil-la vechidaadheenga!"; into a covered steel box | `sun`, talk.py (shake), `box` |
| 33.4–36.3 | "Eppavum open-aa vittutta..." – glance at the wilted bunch, head shake | talk.py |
| 36.3–46.4 | Comment question with two fresh bunches → fresh leaves close-up | f_kff + talk.py, `macro` |

Sound credits: "red_vented_bulbul.wav" by soundbytez and "rustling_leaves.wav" by laurenmg95 (freesound.org,
CC BY 3.0); other ambience CC0.
