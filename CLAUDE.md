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
| Explanations (crop biology) | Code animations, e.g. `tools/toon/cutaway.py`, `tools/toon/soil_prep.py` – must be botanically exact (check TNAU) |
| Shot check | `tools/check_shot.py SHOT.mp4 --start FRAME.png` – contact sheet, jumps, shirt smudges; then look at hands yourself |
| Assembly | `tools/assemble_ep.py edit.json OUT.mp4` – cuts on voice timings, upscales AI clips, adds nature bed |
| Kaggle | `tools/kaggle_run.sh comfy_jobs IN OUT` (job list in `IN/jobs.json`); a second session in parallel with `SLUG=maaran-comfy-jobs-b` |

Worked example with every file: `series/01-groundnut/ep02/final/` (Ep 1: `ep01/final/`) (`lines.json`, `timings.json`, `edit.json`,
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
- Qwen-Image-Edit: "pats his stomach" gave him a huge balloon belly; say "his body shape stays exactly the
  same". It also mirrors the towel to the wrong shoulder on some seeds (check: towel on the image's RIGHT side
  when he faces the camera). Make 2 seeds per frame and pick.
- Wan S2V runs ~19 min per 4.8 s chunk on the T4 now (Ep 1 noted ~12); a 2-run episode takes ~2.5 h of GPU each.
- Don't mix all three model families (qwen_edit + s2v + i2v) in one Kaggle run: Ep 2's run B went silent in its
  i2v job after a qwen_edit and an s2v job (likely RAM thrash). Keep start frames in their own runs; s2v + i2v
  together is fine (run A did 3 s2v + 2 i2v).
- `assemble_ep.py` now cuts pieces on the exact 25 fps frame grid (before: each piece lost up to a frame, so the
  picture ran ~0.2 s ahead of the voice by the end of Ep 2's first render).
- **Speed rules (owner: 5.5 h for Ep 2 was too long; use tokens sparingly):** reuse approved start frames from
  earlier episodes; launch the first Kaggle run as soon as its voice lines exist (voice in priority order);
  prefer code cut-aways and voice-over on action shots over extra S2V chunks; review all shots in one sheet;
  no drafts; `assemble_ep.py` renders pieces in parallel and caches them in `final/.pieces/`.
- **Kaggle results now come back as a private dataset** (`<user>/<slug>-out`, uploaded by the kernel with the owner's
  token from the private input dataset – owner approved, Ep 6). `kaggle_run.sh` waits until a version holds every
  expected file, then downloads it into OUT. The log channel below is only a fallback now.
- **The Kaggle log stream drops chunks** (Ep 3 lost a whole run once and the patience shot twice). Run a second
  follower (`kaggle kernels logs -f` in a restart loop) next to `kaggle_run.sh`, decode from both, and check
  in the first 5 min that the logs are growing. The kernel prints every file 3 times (0, +2, +5 min) and
  **once more at the very end** (upscaled copies last): Kaggle keeps the last ~7 MB of a finished run's log, so
  the newest outputs can always be decoded from `run_log.json` (this recovered Ep 4's funny shot).
  Lost shots so far came from runs with 3+ jobs; keep runs to 2–3 jobs.
- Qwen frames with a NEW background (flowering field) drift in style and dropped his slippers (Ep 5) – frame those
  shots knees-up, or ask for "brown leather slippers" explicitly.
- If the voice runs long, trim pauses first, then speed the FINISHED video (setpts + atempo together keeps lip sync);
  Ep 7 used 1.06x. Make each S2V clip fit its chunks (4.8 s each) or plan a cut-away over the uncovered tail.
- `tools/mix.py` hangs (ffmpeg at ~0% CPU) when the edit runs longer than voice.wav (its apad tail). Pad voice.wav
  with silence to the edit's full length first (Ep 8). Run long renders detached with `< /dev/null`.
- Waiting on a process with `pgrep -f "pattern"` inside `bash -c` matches its own command line – use a bracket
  pattern (`"kaggle/q[a] series"`).

## Improvement backlog (work through these, newest first)
Done in Ep 2: voice at `--speed 1.1` at the source + short pauses; hook split over two shots (first line ends at
2.2 s); punch-in/push cuts every ~3–5 s (`zoom` in `edit.json`); Real-ESRGAN on Kaggle (`"upscale": true`);
`tools/check_shot.py`; thumbnail; `description.md`.
1. Real chuckles: the script's "(chuckles)" are not voiced by IndicF5. Make a short laugh/chuckle reference clip in
   the same Gemini "Charon" voice and splice it in (see `bible/character.md`, Voice).
2. S2V smears hands (with a pink tint) during fast arm swings and pats (Ep 2 hook2 frames 68–70; the first humour
   take patted twice and smeared both times, so it was redone with "one slow, small rub, no fast patting").
   Prompt slow, small gestures and cut around any smear. The checker does not catch motion blur yet – add a
   hand-sharpness-drop check.
3. Real-ESRGAN takes ~2.7 s/frame on the T4 (~40 min per episode on the spare GPU). Try batching frames or a
   lighter model (realesr-animevideov3) if it starts to hold up the run.
4. Assembly takes ~10 min because motion interpolation now runs at 1088x1920; interpolate at 480x848 *before*
   Kaggle upscaling (do the 16→25 fps step on Kaggle) to cut both times.
5. Hand counting in `check_shot.py` (skin-blob count per frame) so fewer frames need a human look.

## Status
- Groundnut Ep 1: done, approved for posting (`series/01-groundnut/ep01/final/groundnut_ep01.mp4`, 49.6 s; script in `final/script.md`).
- Groundnut Ep 2: approved by the owner.
- Groundnut Ep 3: done (`series/01-groundnut/ep03/final/groundnut_ep03.mp4`, 44.6 s).
- Groundnut Ep 4: done (`series/01-groundnut/ep04/final/groundnut_ep04.mp4`, 47.5 s).
- Groundnut Ep 5: done (`series/01-groundnut/ep05/final/groundnut_ep05.mp4`, 45.8 s).
- Groundnut Ep 6: done (`series/01-groundnut/ep06/final/groundnut_ep06.mp4`, 48.0 s).
- Groundnut Ep 7: done (`series/01-groundnut/ep07/final/groundnut_ep07.mp4`, 50.3 s).
- Groundnut Ep 8: done, waiting for review (`series/01-groundnut/ep08/final/groundnut_ep08.mp4`, 46.0 s).
- Next: Groundnut Ep 9 (drying the pods before eating/storing – the owner extended the series) – see `series/01-groundnut/overview.md`.
