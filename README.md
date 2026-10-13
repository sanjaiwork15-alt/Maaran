# Maaran Thatha – YouTube Shorts & Instagram Reels

Maaran Thatha is a ~70-year-old Tamil farmer who shows, in short episodes, how a food actually grows, from soil to plate. He speaks Tamil; the scripts are written in Tanglish so anyone can read them.

Channel: https://www.youtube.com/@MaaranThatha

## How we work (every series)

1. **Series overview.** One page that lists every episode: its hook, story and cliffhanger, plus a fact-check table. *You approve it before any script is written.*
2. **Full episode script.** Tanglish dialogue, scene and shot notes, timing, and fact checks. *You approve it before the video is made.*
3. **Video.** Voice generated with the locked Thatha voice; the character is animated on illustrated scenes of that series' location. No on-screen text.
4. Each episode continues from the previous one, and every series keeps one location.

## Folders

| Path | What |
|---|---|
| `bible/character.md` | Look, personality, speech style and voice rules for Maaran Thatha |
| `bible/world.md` | Home village, farm locations, list of series |
| `assets/character/` | Reference image of the character (the look is locked to this) |
| `series/NN-name/overview.md` | Series overview (step 1) |
| `series/NN-name/epNN/` | Episode script, voice lines and final video |
| `tools/` | Free, open-source production tools (voice now, animation next) |
| `voice-tests/` | Voice samples used to choose Thatha's voice |

## Tools (all free)

- **Voice:** [AI4Bharat Indic-TTS](https://github.com/AI4Bharat/Indic-TTS) (MIT license), Tamil male voice, with expressive pitch and a slightly older tone, each line generated in one continuous pass with soft fades. Settings: `tools/voice_settings.json`.
- **Background sound:** `tools/sound_bed.py` synthesises a soft village breeze, distant birds and a gentle plucked-string folk tune (Mohanam raga) in code, so it's royalty-free. `tools/mix.py` lays it under the voice and dips it while Thatha talks.
- **Video:** Python (Pillow/NumPy) + ffmpeg, rendering 1080×1920 vertical video.

Fresh session setup: `bash tools/setup.sh`
