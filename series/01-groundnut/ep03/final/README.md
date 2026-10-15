# Groundnut Episode 3 – One Seed… How Much Can It Give?

Final video: `groundnut_ep03.mp4` (44.6 s, 1080x1920, 25 fps, -14.4 LUFS); chat copy `groundnut_ep03_share.mp4`.
Thumbnail `thumbnail.png`, posting text `description.md`, script + fact check `script.md`. Edit: `edit.json`.

| Time | Scene | Made with |
|---|---|---|
| 0.0–9.3 | Intro with the bowl of seeds (slow push on the 2nd line) | new Qwen frame + Wan S2V |
| 9.3–11.0 | "Indha chinna vidhaiya paaru pa!" – seed close-up | Ep 2 frame f_cliff + S2V |
| 11.0–13.3 | Kneels, puts the seed in the hole | Ep 2 frame f_kneel + Wan I2V |
| 13.3–15.2 | Cut-away: the seed drops into loose soil | `soil_prep.py` (`cutaway_plant.json`) |
| 15.2–17.8 | Covers and pats the soil (voice-over) | same I2V shot |
| 17.8–24.0 | Cut-away: watering, days and nights pass | `soil_prep.py` (`cutaway_time.json`, new water/days options) |
| 24.0–28.1 | The big question, seed in his fingers | Ep 2 frame f_cliff s8 + S2V |
| 28.1–30.9 | Preview: grown plant with pods | Ep 1 `cutaway_science.mp4` |
| 30.9–33.9 | "Porumaiya irukkanum pa!" (face close-up) | base frame + S2V |
| 33.9–44.6 | Sown soil → first sprout (Ep 4 teaser), Thatha smiles | Ep 2 cut-away + S2V |

Changes from the plan: the "patience" talking shot was generated but lost in the Kaggle log stream twice, so that
line is voice-over on the planting shot. Both new Qwen "patience" frames were rejected (they drew sprouts already up).
The outro is a 1.8x face close-up because the hand smears at frames 6–9 and 32–38; question cuts before frame 70.

Sound credits: "red_vented_bulbul.wav" by soundbytez and "rustling_leaves.wav" by laurenmg95 (freesound.org,
CC BY 3.0); other ambience CC0.
