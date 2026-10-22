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
- **Variety (owner, Doubt Ep 4):** nothing should feel repeated – use 3–4 different Thatha poses per episode, cut every
  ~1.5–3 s (never hold one frame long), mix poses, punch-ins and code animations; keep idle head motion calm
  (no constant shaking) – head shakes/nods only where the script asks.

## Method now (no GPU, since Doubt Ep 1 – Kaggle account suspended 2026-10-20)
Talking/reacting shots = `tools/toon/talk.py RIG.json SHOT OUT.mp4`: one approved still frame (CPU-upscaled with
`tools/upscale.py --scale 1.5`) animated in code – jaw + mouth from the voice loudness, blinks, brow lifts, head
sway/nods, breathing, small hand bob; `"mode": "stare"` squints and leans in. Rig = face points per frame in 720x1280
coords (`series/02-thatha-oru-doubt/ep01/final/rig.json`; find them on a 10 px grid crop). No limb articulation.
Renders ~40 s per shot; whole episode assembled in ~2 min. Shot options: `gaze` (pupils slide, head follows;
not on narrow smiling eyes), `shake`, `tears`, `laugh`, `brows`, `jaw`; frame option `grin` for art with teeth showing. New places without a GPU (Doubt Ep 2): cut Thatha out of an approved frame with
rembg (`isnet-anime`), remove props/people with LaMa (`simple-lama-inpainting`, CPU; patch `torch.jit.load` to
`map_location="cpu"`), and draw new props in code (`tools/toon/coriander.py`), fingers re-pasted on top – see
`series/02-thatha-oru-doubt/ep02/final/make_frames.py`. Kitchen plate = Ep 10 kitchen with Thatha removed. New start frames / new places still need an image model
(see overview "Locations"). Everything else below (voice, cut-aways, assembly) is unchanged.

## Method used for Groundnut (GPU on Kaggle – not available now)
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
- Fresh session: `bash tools/setup.sh` (needs `HF_TOKEN`; Kaggle needs `KAGGLE_USERNAME`, `KAGGLE_API_TOKEN`). It takes
  ~35 min (CUDA torch wheels, ~7 GB) – run it detached in the background and read the scripts meanwhile.
- **2026-10-20: the owner's Kaggle account was suspended** (login page: "Your account has been suspended or banned").
  All GPU work (Qwen frames, Wan S2V/I2V, Real-ESRGAN) is blocked until Kaggle restores it or the owner picks another
  GPU service. Do not create or use another Kaggle account to get around a suspension.
- Kaggle token stopped working overnight (Doubt Ep 1, 2026-10-20: every API call 403 "Permission 'users.get' was denied",
  CLI says "Authentication required"). The owner makes a new API token on kaggle.com → Settings and updates
  `KAGGLE_API_TOKEN` in the environment settings; a new session picks it up. Never ask for the token in chat.
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
- If the voice runs long, trim pauses first (Doubt Ep 4: 62 s → 53 s with 0.22 s pauses, then `atempo=1.07` on
  voice.wav BEFORE animating talk.py shots, timings ÷ 1.07), then speed the FINISHED video (setpts + atempo together keeps lip sync);
  Ep 7 used 1.06x. Make each S2V clip fit its chunks (4.8 s each) or plan a cut-away over the uncovered tail.
- `tools/mix.py` hangs (ffmpeg at ~0% CPU) when the edit runs longer than voice.wav (its apad tail). Pad voice.wav
  with silence to the edit's full length first (Ep 8). Run long renders detached with `< /dev/null`.
- S2V can drop a held prop over a long clip (Ep 9: the bowl vanished after 2.5 s). For long lines with a prop, use a
  short I2V "holds it steady" shot (2 seeds) under the voice instead, or keep the S2V clip to 1 chunk.
- Kaggle may run only ONE GPU session at a time (Ep 10: session B sat QUEUED 2.5 h while A ran, then started anyway
  and used quota). Check both statuses ~5 min after launch; if B is still QUEUED, move its jobs to A. A stale queued
  run can only be stopped on kaggle.com. The whole-dataset results download 404s for a while after a new version;
  `kaggle_run.sh` now falls back to per-file downloads.
- A run can sit QUEUED for hours even with no other session running (Doubt Ep 1: 3.5 h on 2026-10-19). Don't wait past
  ~30 min: ask the owner to open kaggle.com → ☰ → "View Active Events" and cancel the stuck run, then resubmit (the
  resubmitted run started within 1 min). Do all CPU work (voice, clips, cut-aways, job lists) meanwhile.
- IndicF5 can return near-silence for a one-word line (Doubt Ep 3 "Aiyayo!": 0.5 s at -42 dB). Check every line's
  max_volume; regenerate with `--ids LINE --seed 3 --speed 0.85` (slower gives a natural ending).
- Never `uv pip install` into `~/.maaran/f5` while the voice runs: the half-replaced packages crashed IndicF5 at start
  ("Could not import module 'pipeline'", Doubt Ep 2). rembg, simple-lama-inpainting, spandrel, cairosvg are now in f5.
- The container restarts sometimes (uptime resets); background jobs die with it. Check `pgrep` before waiting on one.
- Waiting on a process with `pgrep -f "pattern"` inside `bash -c` matches its own command line – use a bracket
  pattern (`"kaggle/q[a] series"`). Same for `pkill -f`: never put the killed pattern's plain text anywhere else in
  the same command (a `pkill` + relaunch of `kaggle_run.sh` in one command killed its own shell).

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
- Groundnut Ep 8: done (`series/01-groundnut/ep08/final/groundnut_ep08.mp4`, 46.0 s).
- Groundnut Ep 9: done (`series/01-groundnut/ep09/final/groundnut_ep09.mp4`, 45.1 s).
- Groundnut Ep 10 (series finale): done, waiting for review (`series/01-groundnut/ep10/final/groundnut_ep10.mp4`, 46.2 s).
- Groundnut long-form compilation: done, waiting for review (`series/01-groundnut/longform/groundnut_longform.mp4`, 6:44, 16:9; `tools/compile_longform.py`).
- Series 02 "Thatha, Oru Doubt!" (8 everyday-science Q&A Shorts): brief saved in `series/02-thatha-oru-doubt/overview.md`;
  episodes go in `series/02-thatha-oru-doubt/epNN/final/`.
- Doubt Ep 1 (bananas ripening after picking): done without GPU, waiting for review
  (`series/02-thatha-oru-doubt/ep01/final/doubt_ep01.mp4`, 49.6 s; talk.py shots).
- Doubt Ep 2 (coriander, village kitchen): done without GPU, waiting for review
  (`series/02-thatha-oru-doubt/ep02/final/doubt_ep02.mp4`, 46.4 s). Owner: "keep improvising the animation".
- Doubt Ep 3 (onion tears, two kitchen corners): done without GPU, waiting for review
  (`series/02-thatha-oru-doubt/ep03/final/doubt_ep03.mp4`, 45.1 s).
- Doubt Ep 4 (tomato colours, thottam, 4 poses, fast cuts): done without GPU, waiting for review
  (`series/02-thatha-oru-doubt/ep04/final/doubt_ep04.mp4`, 51.0 s).
- Doubt Ep 5 (rice journey, vayal, 4 poses): done without GPU, waiting for review
  (`series/02-thatha-oru-doubt/ep05/final/doubt_ep05.mp4`, 41.6 s).
- Doubt Ep 6 ("Ice Yen Urugudhu?" – owner changed the topic from mango; veedu = owner's 07_home art): done without
  GPU, waiting for review (`series/02-thatha-oru-doubt/ep06/final/doubt_ep06.mp4`, 45.3 s).
- Next: Doubt Ep 7 – wait for the owner's script (topics can change, as Ep 6 did).
