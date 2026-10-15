# Maaran Thatha – production notes for Claude

YouTube Shorts / Instagram Reels about a 70-year-old Tamil farmer, Maaran Thatha, who shows how food grows
from soil to plate. Owner writes or approves each script (Tanglish); Claude makes the video end to end.
Read `bible/character.md`, `bible/world.md`, `docs/video-pipeline-plan.md` and the current series
`series/NN-name/overview.md` before starting an episode.

## Owner's standing preferences (do not re-ask)
- **Look:** the owner's 2D cartoon art in `assets/2d/source` (character, head, hands, poses, turnaround,
  sitting, field, home, arm parts). Not 3D. Thatha's look never changes.
- **Movement must look human, always.** The owner will not review frame by frame. Check every shot yourself
  before sending: hands/arms anatomically correct (one left, one right; thumb on the right side; no broken or
  "glued" joints), face never cut off, no glitches. Reject and regenerate bad AI frames.
- **Sound:** Thatha's voice + natural village sounds (`tools/ambience.py`). **No music.**
- **Pace:** brisk and engaging; 45–50 s per Short. Ep 1 needed a 10% speed-up to feel right.
- **Time:** "not very time consuming" – target ~2 h per episode, mostly unattended.
- For a new style/look: show 2–3 stills first, render the clip only after approval.
- Keep improving every episode (see backlog below). On-screen text: none.

## Method (used for Groundnut Ep 1 – the default)
| Part | Tool |
|---|---|
| Voice | IndicF5 + locked reference `assets/voice/thatha_ref.wav`: `tools/f5_voice.py lines.json OUT` (Tamil script; CPU, slow – start it first) |
| Base frame | `tools/base_frame.py OUT.png --shot medium|wide` – the owner's Thatha art on the series background |
| Scene start frames | Qwen-Image-Edit-2511 on Kaggle (`qwen_edit` job) from the base frame + pose/prop prompt |
| Talking scenes | Wan 2.2 S2V on Kaggle (`s2v` job): start frame + that scene's voice clip; 77 frames (4.8 s) per chunk |
| Full-body actions | Wan 2.2 I2V on Kaggle (`i2v` job), 81 frames |
| Explanations (crop biology) | Code animations, e.g. `tools/toon/cutaway.py` – must be botanically exact (check TNAU) |
| Assembly | `tools/assemble_ep.py edit.json OUT.mp4` – cuts on voice timings, upscales AI clips, adds nature bed |
| Kaggle | `tools/kaggle_run.sh comfy_jobs IN OUT` (job list in `IN/jobs.json`); a second session in parallel with `SLUG=maaran-comfy-jobs-b` |

Worked example with every file: `series/01-groundnut/ep01/final/` (`lines.json`, `timings.json`, `edit.json`,
`shots/`, `frames/`, `README.md`). Copy its structure for the next episode.

Rejected approaches (3D look, code-drawn Thatha, code puppet, MuseTalk, music bed, other voices…) were removed
from the repo; the list and reasons are in `docs/video-pipeline-plan.md`. Do not retry them.

## Gotchas learned the hard way
- Fresh session: `bash tools/setup.sh` (needs `HF_TOKEN`; Kaggle needs `KAGGLE_USERNAME`, `KAGGLE_API_TOKEN`).
- Kaggle machine: use `NvidiaTeslaT4` (default). `NvidiaL4` is accepted but runs CPU-only on the free tier.
- `www.kaggleusercontent.com` is blocked here, so `kaggle kernels output` fails. Outputs are printed into the
  run log as base64 and the runner follows the **live** log (finished runs keep only the tail). Don't remove that.
- Qwen-Image-Edit sometimes draws two right hands (prop hand + stick hand on the same side). Inspect every
  frame; say which hand ("his LEFT hand, the arm on the right side of the image, next to the green towel").
- Wan S2V decides gestures itself from the prompt; put the key pose/prop in the start frame instead.
- Voice: ~4 min per line on this CPU (12 lines ≈ 50 min). Start it before anything else.
- Chat upload limit is 30 MB: send a `-crf 21` share copy; the full file goes in the repo.
- GPU budget: 30 h/week (`kaggle quota`). Ep 1 used ~6 h incl. one lost re-run.
- Every published video must credit the CC BY nature sounds (`assets/sound/nature/CREDITS.md`).
- Commit and push work as you go (the container is temporary).

## Improvement backlog (work through these, newest first)
1. Generate the voice ~10% faster at the source (`f5_voice.py --speed 1.1`) and use shorter pauses, instead
   of speeding up the finished video.
2. Hook must land within 3–5 s (Ep 1's hook ran 9 s). Trim the first line or split it across two shots.
3. More visual variety for engagement: punch-in/zoom cuts every ~3–5 s, a close-up for the punchline,
   cut-aways or B-roll of the crop.
4. Better upscaling of AI clips (Real-ESRGAN via `tools/upscale.py`, or on Kaggle) instead of plain Lanczos.
5. Automatic artifact check on AI shots (e.g. shirt smudge in Ep 1 intro at the chest tap): sample frames
   and look for blotches/extra hands before assembly.
6. Thumbnail for each episode (Qwen-Image-Edit from the owner's art).
7. Write the video description (with sound credits) into the episode folder.

## Status
- Groundnut Ep 1: done, approved for posting (`series/01-groundnut/ep01/final/groundnut_ep01.mp4`, 49.6 s; script in `final/script.md`).
- Next: Groundnut Ep 2 (soil preparation) – see `series/01-groundnut/overview.md`.
