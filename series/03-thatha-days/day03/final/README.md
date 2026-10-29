# Maaran Thatha — Day 3 – Thatha-voda Thookkamum Kozhi Koovuradhum! 😴🐓

Final video: `thatha_day03.mp4` (47.0 s, 1080x1920, 25 fps, -14.3 LUFS); chat copy `thatha_day03_share.mp4`.
Thumbnail `thumbnail.png`, posting text `description.md`, script `script.md`, edit `edit.json`. **No GPU.**
Thatha only. Locations: the thinnai at sunset (Day 1 plate) and his kattil (rope cot) in the courtyard (owner's
07_home art). Frames (`make_frames.py`): the sleeping head = the owner's head sheet with the eyes painted shut (one eye
open for the wake-up), turned onto a pillow under a checked blanket; sitting up = the head sheet bust; pointing at
the kattil / at the rooster = Groundnut Ep 5 pointing pose; finger at the temple = the owner's hands sheet; the arm
that switches off the alarm = the hands sheet's hanging hand. `tools/toon/morning.py`: night (stars, moon) -> dawn
-> morning light, the blanket breathing, the alarm clock set/ring/press, the rooster crowing, the far-away clock.
`tools/sfx.py`: clock ticks, snoring, alarm bell (code), rooster (CC0 recording); ambience `"night"` curve (birds
fade, crickets). talk.py `yawn`. 27 cuts.

| Time | Scene | Made with |
|---|---|---|
| 0–10.4 | Sunset yawn; "seekiramaa thoongap poren!"; points at his kattil; "En discipline-a paarunga!" | f_dsun, f_dpoint |
| 10.4–20.0 | Alarm set, phone beside it; night falls – asleep under the stars, snoring | `set`, `sleep` (night, wide + close) |
| 20.0–30.5 | Dawn; the rooster crows; the alarm rings – his arm presses it off; still asleep in the morning | `sleep` (dawn), `rooster`, `ring`, `sleep` (morning) |
| 30.5–38.4 | One eye opens; "Aiyayo!"; points at the rooster; "adhaan… mudiyala!" (head shake) | f_dbed1, f_dup, f_dpointr, `rooster` |
| 38.4–47.0 | Standing, blanket folded; finger at his temple; the clock now far away on the verandah; laugh | f_dstand, f_dtemple, `far` |

Review fixes: the wide night shot punched in on the empty yard (refocused on the cot); a static clock close-up got
a slow push-in; the far clock first floated on the wall (now on the verandah floor); towel/eye-mask overlap on the
sleeping head.

Sound credits: "red_vented_bulbul.wav" by soundbytez and "rustling_leaves.wav" by laurenmg95 (freesound.org,
CC BY 3.0); other ambience and the rooster CC0; alarm, ticks and snoring made in code.

**v2 (2026-10-29, owner: "some frames are not looking good"):** sitting up in bed is now the real seated Thatha
(Day 1 thinnai frame cut at the waist, hand at his cheek) instead of the head-sheet bust; the blanket is draped
(body shape, checks, folds, wavy hem over the cot edge, lining turned down at his chin); the finger-at-temple frame
(arm not attached) is dropped – a laughing standing close-up instead. `rebuild_v2.sh` redoes it.
