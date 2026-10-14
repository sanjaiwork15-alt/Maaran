# Video pipeline plan (decided 2026-10-14)

## Goal
One ~50-60 s Short in 1.5-2 hours, good quality (no glitches), fully automated by Claude, free tools only.

## What we tried (and why not)
| Approach | Result |
|---|---|
| 2D puppet from the reference image (`tools/animate.py`, `tools/scene.py`) | Works, but looks cheap: owner rejected |
| Wan2.2 TI2V-5B Turbo on this cloud CPU (stable-diffusion.cpp) | ~9 min per 1 s of 352x640 video, glitchy: too slow and low quality |
| Google Flow (owner's AI Pro plan) | Good quality, but Flow credits are browser-only (no API), so it needs manual work: rejected |
| Paid APIs (fal.ai, Kling, Veo API) | Not free: rejected |

## Chosen: free Kaggle GPUs driven by Claude through the Kaggle API
- Kaggle Notebooks: ~30 GPU hours/week free (2x T4 or P100). Claude pushes a script kernel, runs it on GPU, downloads the outputs.
- Credentials: `KAGGLE_API_TOKEN` + `KAGGLE_USERNAME` environment variables (new-style API token, kaggle CLI >= 1.8). Network: www.kaggle.com, api.kaggle.com, storage.googleapis.com allowed.
- Fallback if T4 is too slow: Modal ($30/month free credits, A100/L4), via its Python SDK.

## Per-Short pipeline
1. Script (Tanglish + Tamil lines in `lines.json`): owner approves.
2. Voice: IndicF5 with the locked Gemini "Charon" reference (`tools/f5_voice.py`), on the cloud session CPU (~25 min), in parallel with step 3.
3. Action shots: Wan 2.2 I2V 14B + 4-step distill LoRA on Kaggle GPU, starting from Thatha's reference look; 8-10 clips of 5-8 s; Claude checks frames and regenerates glitchy clips.
4. Talking shots: MuseTalk (MIT, commercial OK) lip-syncs Thatha's mouth to the Tamil voice, on Kaggle GPU.
5. Upscale to 1080x1920, cut to the voice, add sound bed (`tools/sound_bed.py`, `tools/mix.py`), export.

## Next step
Two-shot test (one action shot, one talking shot) to measure real Kaggle timing and quality before scaling up.
