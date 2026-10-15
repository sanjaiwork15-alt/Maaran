# Video pipeline (final approach, locked after Groundnut Episode 1, 2026-10-15)

Goal: one 45–50 s Short in about 2 hours, mostly unattended, free tools only, in the owner's 2D style,
with human-looking movement and no glitches.

## Steps for every episode
1. **Script** – Tanglish voice-over + scene notes, written or approved by the owner. Save it as
   `series/NN-name/epNN/final/script.md`.
2. **Voice (start first, ~40 min on CPU)** – write each line in Tamil script in `lines.json` (with `group` =
   scene and `pause_after` 0.2–0.3 s), then `tools/f5_voice.py lines.json OUT --speed 1.1` (brisk pace at the
   source; no speed-up of the finished video). `tools/join_voice.py lines.json OUT .` → `voice.wav` + `timings.json`;
   then cut one `voice_<shot>.wav` per talking shot (44.1 kHz mono). Check for long pauses inside a line
   (`silencedetect`) and shorten them, cutting the shot at that pause (Ep 2 did this for the hook).
   **Hook:** the first line must end by ~3 s – split the hook over two shots (Ep 2: 2.2 s).
3. **Base frames** – `tools/base_frame.py OUT.png --shot medium|wide` places Thatha on the series background.
4. **Scene start frames (Kaggle, Qwen-Image-Edit-2511, ~4–5 min each)** – one per scene, pose + props from
   the script ("holding groundnuts in his palm", "carrying a hoe"). Name the hand explicitly. **Inspect every
   frame**: one left + one right hand, stick in his right hand, face and outfit unchanged. Regenerate bad ones.
5. **Talking scenes (Kaggle, Wan 2.2 S2V, ~12–19 min per 4.8 s chunk)** – start frame + that scene's voice clip;
   the prompt describes his acting. Natural lip sync and whole-body movement. Add `"upscale": true` to every
   i2v/s2v job: Real-ESRGAN x4plus runs on the second T4 in the background (~2.7 s/frame) and returns
   `<name>_up.mp4` (1088x1920) – use that as `shots/<name>.mp4`. Much crisper than Lanczos.
6. **Action scenes (Kaggle, Wan 2.2 I2V, ~20 min per 5 s)** – walking, bending, picking, sowing, etc.
7. **Explanations (code)** – crop biology as code animations (`tools/toon/cutaway.py`, `tools/toon/soil_prep.py`);
   must be botanically exact and checked against TNAU.
8. **Check every AI shot** before assembly: `tools/check_shot.py SHOT.mp4 --start FRAME.png` writes a contact
   sheet and flags jumps and shirt/veshti smudges (it catches the Ep 1 intro smudge). Then look at the sheet
   yourself for hands (one left, one right, stick in his right hand) and face.
9. **Assemble** – `edit.json` (shot list on the voice timeline) → `tools/assemble_ep.py edit.json OUT.mp4`
   (AI clips to 1080x1920 25 fps, nature bed from `tools/ambience.py`, -15 LUFS). Cut every ~3–5 s; use
   `"zoom": 1.3` punch-ins for punchlines and `"zoom": [1.0, 1.2]` slow pushes (smooth, sub-pixel).
10. **Deliver** – full file in the repo, a `-crf 21` share copy under 30 MB for chat, `thumbnail.png`
    (Qwen-Image-Edit `thumb` job + `tools/upscale.py --scale 1.5`) and `description.md` with the CC BY sound
    credits (`assets/sound/nature/CREDITS.md`).

Run Kaggle work as two parallel sessions (`SLUG=maaran-comfy-jobs-b`). Budget: 30 GPU h/week; Ep 1 used ~6 h.
Start frames: put 2 seeds of every frame in one run (~4.5 min per image); decode them from the live log while the
run continues (the `@@FILE` blocks) to inspect early. A start frame needed by a later job in the same run can be
referenced by its output name (e.g. `"image": "f_humour2_s3.png"`).
Full worked example: `series/01-groundnut/ep01/final/`.

## Rejected (removed from the repo – do not retry)
| Approach | Why rejected |
|---|---|
| AI4Bharat Indic-TTS, Indic Parler-TTS, aged/processed voices, other IndicF5 references | Voice locked to the owner's Gemini "Charon" clip with IndicF5 |
| Procedural folk-music bed (`sound_bed.py`) | Owner: no music, natural sounds only |
| Code-drawn scenery + cut-out of the 3D-style reference (`scene.py`, `animate.py`) | Looked cheap |
| 3D-style look (Wan on the 3D reference, Qwen 3D scenes) | Owner chose 2D cartoon art instead |
| Wan on the cloud CPU (stable-diffusion.cpp) | ~9 min per second of video, glitchy |
| Google Flow / paid video APIs | Manual (no API) or not free |
| Kaggle L4 machine | Runs CPU-only on the free tier; use T4 |
| MuseTalk lip sync | Redraws the mouth like a real human; erased Thatha's moustache |
| Thatha drawn entirely in code (`toon/art.py`) | Too simple next to the owner's art |
| Code cut-out puppet of the owner's art (arm rig, human-motion rules) | Arm joints never looked natural enough; Wan S2V moves like a real person |
