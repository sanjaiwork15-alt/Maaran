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

## Per-Short pipeline (updated 2026-10-14 after the Kaggle tests)
All GPU steps run in one Kaggle kernel, `tools/kaggle/comfy_jobs.py` (headless ComfyUI on 2x T4), driven by
`tools/kaggle_run.sh comfy_jobs IN_DIR OUT_DIR` with a `jobs.json` of `qwen_edit` / `i2v` / `s2v` jobs.
1. Script (Tanglish + Tamil lines in `lines.json`): owner approves.
2. Voice: IndicF5 with the locked Gemini "Charon" reference (`tools/f5_voice.py`) on the session CPU, ~5 min per line.
3. Scene frames: **Qwen-Image-Edit-2511** (+ 4-step Lightning LoRA) redraws the locked reference into a fully
   3D-animated scene of the series location, so background and character share one style. ~4-5 min per image.
4. Talking shots: **Wan 2.2 S2V 14B** (+ 4-step LoRA) animates a scene frame from the voice: lips, head, brows,
   hand gestures. Keeps the face and moustache intact. ~33 min per 10 s on one T4.
5. Action shots: Wan 2.2 I2V 14B (+ 4-step LoRA) from a scene frame. ~13 min per 5 s on one T4.
6. Finish on the session CPU: ffmpeg motion interpolation 16 -> 32 fps, upscale to 1080x1920, voice + sound bed
   (`tools/sound_bed.py`, `tools/mix.py`).

## Test results (2026-10-14)
- `series/01-groundnut/ep01/test-clips/thatha_10s_test.mp4`: 10 s talking shot (L02) in the animated field.
- MuseTalk lip-sync was dropped: it redraws the lower face like a real human and erased Thatha's moustache.
- Kaggle `NvidiaL4` is accepted by the API but ran CPU-only on the free tier; use `NvidiaTeslaT4`.
- Kaggle output files are served from www.kaggleusercontent.com, blocked by this environment's network policy.
  Workaround in place: the kernel prints outputs into the run log as base64 and `kaggle_run.sh` decodes them.
  Adding that host to Allowed domains would make downloads direct.
- Estimated GPU time for a 50 s Short (~35 s talking, ~15 s action, 4 scene frames): ~2.5-3 h on one T4.
  Next speed-ups: run two jobs at once (one per T4), and reuse scene frames across episodes of a series.

## Method used for Groundnut Episode 1 (2026-10-14) – the default from now on
- Start frames: Qwen-Image-Edit-2511 from the owner's 2D art (`assets/2d`), one per scene, with the props
  and pose the script asks for. Check every frame for anatomy (one left + one right hand) before use.
- Talking scenes: Wan 2.2 S2V on Kaggle from each start frame + that scene's voice clip.
- Action scenes: Wan 2.2 I2V on Kaggle. Explanations (how a crop grows): code animations (`tools/toon/`).
- Two Kaggle sessions in parallel (`SLUG=maaran-comfy-jobs-b`); the runner follows the live log so all
  outputs arrive. Ep 1 took ~2.5 h end to end and 6 GPU hours.
- Assembly: `tools/assemble_ep.py` cuts on the voice timings and adds the nature bed (`tools/ambience.py`).
- Pace: the owner wants it brisk. Final export runs 10% faster (`setpts=PTS/1.1`, `atempo=1.1`); for the
  next episodes generate the voice ~10% faster at the source (`f5_voice.py --speed 1.1`) and keep pauses short.
- Keep a share copy under 30 MB for chat (`-crf 21`); post the full-quality file.
- Description must credit the CC BY nature sounds (see `assets/sound/nature/CREDITS.md`).
