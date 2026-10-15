# Video pipeline (final approach, locked after Groundnut Episode 1, 2026-10-15)

Goal: one 45–50 s Short in about 2 hours, mostly unattended, free tools only, in the owner's 2D style,
with human-looking movement and no glitches.

## Steps for every episode
1. **Script** – Tanglish voice-over + scene notes, written or approved by the owner. Save it as
   `series/NN-name/epNN/final/script.md`.
2. **Voice (start first, ~50 min on CPU)** – write each line in Tamil script in `lines.json` (with `group` =
   scene and `pause_after`), then `tools/f5_voice.py lines.json OUT --speed 1.1` (brisk pace, owner's request).
   Join with short pauses into `voice.wav`, one `voice_<scene>.wav` per scene and `timings.json`
   (see Ep 1 for the exact join step; `tools/join_voice.py` has the trim helper).
3. **Base frames** – `tools/base_frame.py OUT.png --shot medium|wide` places Thatha on the series background.
4. **Scene start frames (Kaggle, Qwen-Image-Edit-2511, ~4–5 min each)** – one per scene, pose + props from
   the script ("holding groundnuts in his palm", "carrying a hoe"). Name the hand explicitly. **Inspect every
   frame**: one left + one right hand, stick in his right hand, face and outfit unchanged. Regenerate bad ones.
5. **Talking scenes (Kaggle, Wan 2.2 S2V, ~12 min per 4.8 s chunk)** – start frame + that scene's voice clip;
   the prompt describes his acting. Natural lip sync and whole-body movement.
6. **Action scenes (Kaggle, Wan 2.2 I2V, ~20 min per 5 s)** – walking, bending, picking, sowing, etc.
7. **Explanations (code)** – crop biology as code animations (`tools/toon/cutaway.py` is the template);
   must be botanically exact and checked against TNAU.
8. **Check every AI shot** before assembly (sample frames: hands, face, outfit, glitches/smudges).
9. **Assemble** – `edit.json` (shot list on the voice timeline) → `tools/assemble_ep.py edit.json OUT.mp4`
   (upscales AI clips to 1080x1920 25 fps, adds the nature bed from `tools/ambience.py`, -15 LUFS).
10. **Deliver** – full file in the repo, a `-crf 21` share copy under 30 MB for chat, and the description with
    the CC BY sound credits (`assets/sound/nature/CREDITS.md`).

Run Kaggle work as two parallel sessions (`SLUG=maaran-comfy-jobs-b`). Budget: 30 GPU h/week; Ep 1 used ~6 h.
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
