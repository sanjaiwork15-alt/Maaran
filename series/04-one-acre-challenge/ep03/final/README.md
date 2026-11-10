# Maran Thatha: The One-Acre Challenge — Ep 3 – Thatha's War Against Every Insect! 🐛

Final video: `thatha_acre03.mp4` (55.2 s, 1080x1920, 25 fps); chat copy `thatha_acre03_share.mp4`. Thumbnail
`thumbnail.png`, posting text `description.md`, edit `edit.json`. **No GPU.** After Ep 2's compost the field is alive:
the approved Groundnut field frames are used whole with the soil darkened to a rich moist brown and rows of young
**brinjal** plants drawn in code (`tools/toon/bugs.py`) – a new crop, so the groundnut plants and seeds don't repeat
(seeds in his hand, the pod in his fist and the sprout were removed with LaMa / replaced by props).

| Time | Scene | Made with |
|---|---|---|
| 0–7.4 | Inspecting his plants; a ladybird walks onto a leaf – "villain!", pointing | f_inspect, `spot`, f_point |
| 7.4–15.2 | Declares war: hand sprayer raised like a warrior; the nozzle trembles towards the bug (soft tiptoe knocks) | f_spray, `aim` |
| 15.2–20.4 | "Dei, oru nimisham!" – the ladybird is eating aphids | f_point punch-in, `eat` |
| 20.4–28.4 | Leans in close (the leaf with the ladybird in his hand); "Ada paavi!"; a respectful vanakkam bow to the guest | f_bend, `eat`, library `bow` |
| 28.4–36.2 | The lesson; sprayer put away on the ground, he examines the leaves; ladybird + larva eating aphids | f_inspect2, `eat` |
| 36.2–43.4 | The moral, to camera; arms crossed, nod | f_moral, f_cross |
| 43.4–55.2 | Walks to water the plants – "thanni oothalaam!" – a waterlogged patch, a pond in the field; he looks around and turns to the camera, puzzled (cliffhanger → Ep 4) | library `walk_side`, f_water, `waterlog`, library `look`, f_huh |

Fact check: adult ladybirds (Coccinellidae) and their larvae are predators of aphids (an adult eats dozens a day) –
classic natural pest control (TNAU IPM: conserve coccinellid predators; spray only after checking). Aphids cluster on
tender shoots and leaf undersides of brinjal. Waterlogging: standing water starves roots of oxygen – next episode.

Frames (`make_frames.py`, f5 env): f_inspect / f_inspect2 (Groundnut Ep 2 f_kneel_s3), f_point (Ep 2 f_hook2_s3),
f_spray (Ep 8 f_pod_s3), f_moral (Ep 1 f5_cliff_s3), f_huh (Ep 2 f_hook_s3), f_water (Ep 4 f_water_s8), f_bend and
f_cross (the owner's 04_poses sheet on the field plate), grown_plate / pond_plate (05_field_vertical).
Sounds: tiptoe knocks, munch flicks, shimmer at the bow, bubbles in the pond, a pop at the stare. No music.

Rebuild: `make_frames.py` → `tools/upscale.py --scale 1.5` → `talk.py rig.json A..J` → `bugs.py cut_*.mp4 cut_*.json`
→ `place_action.py act_*.json` → `sfx.py sfx_cues.json sfx.wav 55.2` → `assemble_ep.py edit.json raw.mp4` → amix sfx.

Sound credits: "red_vented_bulbul.wav" by soundbytez and "rustling_leaves.wav" by laurenmg95 (freesound.org,
CC BY 3.0); other ambience CC0; effects made in code.
