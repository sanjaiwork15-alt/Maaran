# Groundnut Episode 2 – Before the Seeds Go In

Final video: `groundnut_ep02.mp4` (49.4 s, 1080x1920, 25 fps, -15 LUFS). Share copy for chat: `groundnut_ep02_share.mp4`.
Thumbnail: `thumbnail.png`. Posting text with sound credits: `description.md`. Script + fact check: `script.md`.
No speed-up of the finished video: the voice was made at `--speed 1.1` with short pauses.

| Time | Scene | Made with |
|---|---|---|
| 0.0–2.4 | Hook: "Vidhai nalla irundhaa mattum podhaadhu pa!" (seeds in his palm) | Qwen start frame + Wan 2.2 S2V |
| 2.4–5.9 | "Mannum nalla irukkanum!" (points at the soil) → punch-in on "…paadu dhaan waste!" | Wan 2.2 S2V |
| 5.9–11.0 | Squats, rubs the soil between his fingers (slow push-in) | Wan 2.2 S2V |
| 11.0–14.9 | Picks out stones and weeds | Wan 2.2 I2V |
| 14.9–17.1 | Loosens the soil with a spade | Wan 2.2 I2V |
| 17.1–25.1 | Cut-away: hard clods → fine tilth, seed sprouts, roots spread, first leaf | `tools/toon/soil_prep.py` (code) |
| 25.1–33.2 | Pats his stomach (humour) → punch-in on "…ellaathukkum oru neram irukku pa!" | Wan 2.2 S2V |
| 33.2–45.6 | Holds up one kernel: cliffhanger (slow push, then face close-up) | Wan 2.2 S2V |
| 45.6–49.4 | Kneels and places the kernel in the soil, looks up and smiles (gentle push-in) | Wan 2.2 I2V |

All AI shots were upscaled with Real-ESRGAN x4plus on Kaggle (`"upscale": true`, `shots/*.mp4` are 1088x1920)
and checked with `tools/check_shot.py` plus a look at the hands in every shot.

Files: `lines.json` (Tamil lines) → `voice.wav` + `timings.json` (one 0.54 s pause inside the hook was shortened,
see `timings.json` "cuts") → `voice_<shot>.wav` (S2V audio) · `frames/` (base + chosen start frames) · `jobs/`
(the Kaggle job lists: `qa`/`qb` start frames, `va`/`vb`/`vc`/`vd` video) · `cutaway_soil.json` → `cutaway_soil.mp4` ·
`edit.json` → `tools/assemble_ep.py edit.json groundnut_ep02.mp4`.

Rejected AI frames: f_hoe s3 (towel on the wrong shoulder), f_humour s3/s8 (balloon belly – regenerated as
f_humour2 with "body shape stays exactly the same"). The first humour video (from f_humour2 s3) smeared his hand
while patting; redone from s8 as `humour3` with a slow-rub prompt (`jobs/vd_jobs.json`). hook2 is cut before frames 68–70 (hand smear in a fast swing). Run B (`vb`) lost its hoe output to a stalled log stream; hoe came from `vc`.

## Video description credit (required for CC BY sounds)
Nature sounds from freesound.org: "red_vented_bulbul.wav" by soundbytez and "rustling_leaves.wav"
by laurenmg95 (CC BY 3.0); other ambience CC0.
