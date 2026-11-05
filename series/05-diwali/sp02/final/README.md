# Diwali Special 2 – "Thatha's Gift of Happiness!" (no GPU)

Back from the market, Thatha unpacks the shopping, cooks a full meal on his wood stove (rice, sambar, beans-carrot
poriyal, laddus), packs it into tiffins and leaf parcels "with love", carries them on his bicycle at sunset to a
children's home and leaves them at the entrance (no other people shown). At night he lights the diyas round his house,
enjoys a laddu on his step, and – holding a lit lamp in front of the decorated farmhouse – gives the moral and asks
viewers what their office gave them for Diwali (callback: the gift reels of Special 1). Rockets close the video with
"Iniya Deepavali Nalvaazhthukkal!" spoken (no on-screen text). No music.

## Frames (`make_frames.py`, f5 env)
| Frame | From |
|---|---|
| `f_kbag` | Doubt Ep 2 kitchen plate (its pot repainted as sambar) + the owner's 01_front drawing, cloth bag bulging with greens and a sweet box |
| `f_kcook` | Groundnut Ep 10 `f_kitchen_s3` used whole – the groundnuts in the pot repainted as sambar |
| `f_kpack` | kitchen + 01_front behind a table of tiffins and leaf parcels (table edge = the cut line at his hips) |
| `f_khome` | 07_home re-tinted (pale-blue walls, golden hour), bunting, a signboard (house + two children + heart, "CHILDREN'S HOME"), parcels on the step + 01_front |
| `f_sweet` | Groundnut Ep 10 `f_sit_s3` – the nuts in his bowl become laddus (LaMa + code), a laddu at his lips, dusk, diyas on the step |
| `f_diya` | Groundnut Ep 10 `f_roast_s3` cut out – the bowl of nuts on his palm becomes a big clay lamp with a flame – on the Ep 1 decorated farmhouse at night |

## Cut-aways
`tools/toon/feast.py`: `cut_unpack`, `cut_rice`, `cut_sambar`, `cut_curry`, `cut_sweet`, `cut_pack`, `cut_load`,
`cut_entrance`, `cut_lamps` (diyas lit one by one, then bulbs), `cut_finale` (rockets over the farmhouse).
`tools/toon/diwali.py` silhouette mode with `"cargo": true, "sky": "sunset"`: `cut_ride`. Ep 1's `cut_feed.mp4` is reused
for the iPhone / suitcase / air-fryer callback.

## Rebuild
```
~/.maaran/f5/bin/python -I make_frames.py ; tools/upscale.py --scale 1.5 each frame into frames/up
~/.maaran/toon/bin/python ../../../../tools/toon/feast.py cut_X.mp4 cut_X.json        # each cut_*.json (ride: diwali.py)
~/.maaran/toon/bin/python ../../../../tools/toon/talk.py rig.json A shots/A.mp4         # A–F
~/.maaran/toon/bin/python ../../../../tools/sfx.py sfx_cues.json sfx.wav 60
~/.maaran/toon/bin/python ../../../../tools/assemble_ep.py edit.json raw.mp4
ffmpeg -i raw.mp4 -i sfx.wav -filter_complex "[0:a][1:a]amix=inputs=2:normalize=0:duration=first[a]" -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k thatha_diwali02.mp4
```
Voice: 8 lines (L8 = the end-card greeting, spoken), pauses trimmed with `tools/trim_pauses.py`, placed by `timings.json`.
