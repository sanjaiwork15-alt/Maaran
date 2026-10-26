# Maaran Thatha — Day 1 – Phone Irukku, Neram Illai! 📱😂

Final video: `thatha_day01.mp4` (47.2 s, 1080x1920, 25 fps, -14.1 LUFS); chat copy `thatha_day01_share.mp4`.
Thumbnail `thumbnail.png`, posting text `description.md`, script `script.md`, edit `edit.json`. **No GPU.**
New series with a second character: the boy, from the owner's character sheet (`assets/2d/source/thambi/00_sheet.png`,
Real-ESRGAN x4 on CPU, cut out per expression tile); his voice = owner's Gemini "Puck" clip (`assets/voice/thambi_ref.*`).
Location: the village courtyard (owner's 07_home art). Frames (`make_frames.py`, composed straight at 1080x1920):
two-shot (Thatha 3/4 + the boy mirrored, phone in his hand, his books on the ground), the boy's big close-up and six
chest-up expression shots (frown, smile, thinking, laugh, happy, surprised) with the back of his phone in front, Thatha
front and arms-crossed medium shots. Phone screens: `tools/toon/phone.py` (code-drawn reels, swipes, lock; icons only).
Stick tap: two wooden knocks synthesised in code (`sfx_tap.wav`), mixed at 25.5 s. 27 cuts.

| Time | Scene | Made with |
|---|---|---|
| 0–6.4 | Phone feed; "Cha Thatha! … orey tension!" | `feed`, f_bfrown, two-shot |
| 6.4–14.7 | "Appadiyaa thambi?"; "Velaiyaa? … phone paakkuren!" | two-shot (punch-in), f_tfront, f_bsmile/f_bclose (eyes on the phone) |
| 14.7–25.4 | "Seri thambi…"; scrolling glimpses + silent laugh; "Theriyala… appuram innonnu!" | f_tcross, f_tfront, `feed`, f_blaugh, f_bthink, `swipe` |
| 25.4–35.4 | Stick tap; "Adhaan thambi prachanai! … neram enga irundhu varum?" – the boy looks up | f_tfront, f_tcross, two-shot, f_bsurp |
| 35.4–47.2 | Boy glances at his books; "Seri Thatha…"; phone locks; "Nalla mudivu… koodaadhu!" | f_bsmile, `lock`, f_tcross (nod), f_tfront, f_bhappy, two-shot pull-out |

Review fixes: a 5 s run on the two-shot split with the frown close-up and a punch-in on Thatha; the lock screen was
visible for only 0.3 s (now 0.6 s); the two-shot boy's mouth opening reduced for his small face.

Sound credits: "red_vented_bulbul.wav" by soundbytez and "rustling_leaves.wav" by laurenmg95 (freesound.org,
CC BY 3.0); other ambience CC0.
