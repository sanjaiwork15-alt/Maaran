# Diwali Special 1 – "Thatha's Diwali Gift Aasai!" (no GPU)

Thatha scrolls Diwali gift unboxings on his phone, daydreams of an iPhone, a suitcase and an air fryer, looks at his
old keypad mobile and counts his savings, sees a sweet-box ad, and decides to spend on the village children's
Diwali instead: a picture shopping list, the yellow bag on his bicycle's handlebar, and a ride at dusk under fireworks.
Voice + village dusk ambience + sound effects (far-off crackers, bell, rockets). No music, no on-screen text.

## Files
| File | What |
|---|---|
| `lines.json`, `wav/`, `wav_c/` | 6 lines (IndicF5, `--speed 1.1`); pauses trimmed with `tools/trim_pauses.py` |
| `voice.wav`, `timings.json` | lines placed on the timeline (starts 1.6 / 10.2 / 16.0 / 25.4 / 32.6 / 42.0 s), 49.6 s |
| `make_frames.py` | frames: dusk farmhouse with decorations (`tools/toon/diwali.py`), the owner's sitting drawing on a code-drawn chair (`f_chair` phone, `f_warm` golden idea light, `f_old` keypad phone, `f_tin` open savings tin on his lap), standing with the cloth bag (`f_bag`) + masks |
| `rig.json`, `shots/A–E.mp4` | talk.py shots (with the `lights` overlay: twinkling bulbs, diya flames, lanterns, far fireworks) |
| `cut_feed`, `cut_sweets` | phone reels (`tools/toon/phone.py`: gphone, suitcase, fryer, hamper, sweets) |
| `cut_dream` | daydream bubble: three gift boxes pop open (phone, suitcase, air fryer), Thatha (library laugh clip) beside them |
| `cut_savings` | top-down: the tin's lid opens, notes counted over onto his veshti |
| `cut_list` | pencil draws the shopping list as pictures (rice, vegetables, sweets, snacks, oil), each ticked |
| `cut_bike` | his parked roadster: the bag drops onto the handlebar, the bell rings |
| `cut_ride` | wide dusk silhouette: he cycles along the bund, village lights, rockets, pond reflection |
| `edit.json`, `sfx_cues.json`, `sfx.wav` | the cut; effects mixed on top (`amix normalize=0`) |
| `thatha_diwali01.mp4` | final (1080x1920, 25 fps); `_share` = `-crf 22` copy |

## Rebuild
```
~/.maaran/f5/bin/python -I make_frames.py                 # frames (+ tools/upscale.py --scale 1.5 into frames/up)
~/.maaran/toon/bin/python ../../../../tools/toon/talk.py rig.json A shots/A.mp4      # A–E
~/.maaran/toon/bin/python ../../../../tools/toon/phone.py cut_feed.mp4 cut_feed.json  # feed, sweets
~/.maaran/f5/bin/python ../../../../tools/toon/diwali.py cut_dream.mp4 cut_dream.json # dream savings list bike ride
~/.maaran/toon/bin/python ../../../../tools/sfx.py sfx_cues.json sfx.wav 49.6
~/.maaran/toon/bin/python ../../../../tools/assemble_ep.py edit.json raw.mp4
ffmpeg -i raw.mp4 -i sfx.wav -filter_complex "[0:a][1:a]amix=inputs=2:normalize=0:duration=first[a]" -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k thatha_diwali01.mp4
```

## Notes
- First tries rejected in review: close-ups with the owner's hand drawings pasted as loose arms (floating sleeve), and
  a code-drawn bicycle rider in colour (puppet-like legs). Replaced by props in his own frames (`f_old`, `f_tin`), a
  hand-free counting close-up, and the silhouette ride (his real side-view outline).
- Nature sounds: credit `assets/sound/nature/CREDITS.md` in the description.
