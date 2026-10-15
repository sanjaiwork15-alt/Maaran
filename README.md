# Maaran Thatha – YouTube Shorts & Instagram Reels

Maaran Thatha is a ~70-year-old Tamil farmer who shows, in short episodes, how a food actually grows, from soil to plate. He speaks Tamil; the scripts are written in Tanglish so anyone can read them.

Channel: https://www.youtube.com/@MaaranThatha

## How we work (every series)

1. **Series overview.** One page that lists every episode: its hook, story and cliffhanger, plus a fact-check table. *You approve it before any script is written.*
2. **Episode script.** Tanglish voice-over with scene notes and fact checks. *You approve it (or write it) before the video is made.*
3. **Video.** 45–50 s, 1080×1920, in the owner's 2D art style, Thatha's locked voice, natural village sounds (no music), no on-screen text. See `docs/video-pipeline-plan.md`.
4. Each episode continues from the previous one, and every series keeps one location.

## Folders

| Path | What |
|---|---|
| `CLAUDE.md` | Production notes for Claude: preferences, method, gotchas, improvement backlog |
| `bible/character.md` | Look, personality, speech style and voice rules for Maaran Thatha |
| `bible/world.md` | Home village, farm locations, list of series |
| `assets/2d/` | The owner's 2D character and background art (the look is locked to this); `up/` = 2x upscales |
| `assets/voice/` | Thatha's locked voice reference clip |
| `assets/sound/nature/` | Real field recordings for the village sound bed (CC0 / CC BY, see CREDITS.md) |
| `series/NN-name/overview.md` | Series overview |
| `series/NN-name/epNN/final/` | Episode script, voice, shots, edit list and final video |
| `tools/` | Production tools (all free) |
| `docs/video-pipeline-plan.md` | The video method |

## Tools (all free)

| Tool | What it does |
|---|---|
| `tools/f5_voice.py` | Speaks each Tamil line in Thatha's locked voice (AI4Bharat IndicF5, MIT) |
| `tools/join_voice.py` | Joins lines with pauses and records line timings |
| `tools/base_frame.py` | Places the owner's Thatha art on a series background (base for start frames) |
| `tools/kaggle_run.sh` + `tools/kaggle/comfy_jobs.py` | Runs GPU jobs on free Kaggle T4s: Qwen-Image-Edit start frames, Wan 2.2 S2V talking scenes, Wan 2.2 I2V action scenes |
| `tools/toon/cutaway.py` | Code animation of how groundnut pods form underground (template for future explanations) |
| `tools/ambience.py`, `tools/mix.py` | Natural village sound bed from real recordings, mixed under the voice |
| `tools/assemble_ep.py` | Cuts all shots on the voice timeline and exports the episode |
| `tools/upscale.py` | Real-ESRGAN 4x upscaler (art and frames) |
| `tools/set_reference.py` | Cleans a new voice reference clip (only if the voice is ever re-locked) |

Fresh session setup: `bash tools/setup.sh` (needs `HF_TOKEN`; Kaggle jobs need `KAGGLE_USERNAME` and `KAGGLE_API_TOKEN`).
