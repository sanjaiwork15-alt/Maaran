# Groundnut Episode 4 – Thatha, Something Is Growing!

Final video: `groundnut_ep04.mp4` (47.5 s, 1080x1920, 25 fps, -14.0 LUFS); chat copy `groundnut_ep04_share.mp4`.
Thumbnail `thumbnail.png`, posting text `description.md`, script + fact check `script.md`, edit `edit.json`.

| Time | Scene | Made with |
|---|---|---|
| 0.0–2.0 | Seedlings push up through the soil (1 s pause, then "Enna pa…") | `tools/toon/seedlings.py` (new) |
| 2.0–8.6 | Excited Thatha kneeling by the sprouts | Ep 3 frame f_patience s8 + Wan S2V |
| 8.6–17.6 | "Manasukku evlo sandhoshama…" – points at a sprout | Ep 3 frame f_patience s3 + S2V |
| 17.6–20.2 | Gentle watering, no pooling (cut before a puddle forms) | new Qwen frame f_water + I2V |
| 20.2–28.1 | Watering / moisture cut-aways, "chedi kashtappadum" | Ep 3 `cutaway_time.mp4`, sprout clip |
| 28.1–33.1 | Pretends to pull a seedling, laughs (voice-over) | f_patience s8 + I2V |
| 33.1–39.4 | "Innum neriya valaranum!" → "aduthu…" (Thatha standing) | sprout clip, base frame + S2V |
| 39.4–43.5 | Preview: yellow flowers (stops before the peg – the Ep 5 secret) | Ep 1 `cutaway_science.mp4` |
| 43.5–47.5 | Cliffhanger by a seedling, face close-up | thumbnail frame + S2V |

Voice: seven "…" pauses were shortened to 0.3 s and a 1 s lead was added; `timings.json` lists the cuts.
Retakes: sprout ends at frame 126 (hand smear 127–129); funny and cliff were lost to the Kaggle log stream /
a kernel error and rerun (`jobs/vc`, `jobs/vd`); funny came back through the new end-of-run re-emit.

Sound credits: "red_vented_bulbul.wav" by soundbytez and "rustling_leaves.wav" by laurenmg95 (freesound.org,
CC BY 3.0); other ambience CC0.
