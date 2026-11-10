# Maran Thatha: The One-Acre Challenge — Ep 6 – The Day Everything Went Wrong! 🌧️

Final video: `thatha_acre06.mp4` (54.4 s, 1080x1920, 25 fps); chat copy `thatha_acre06_share.mp4`. Thumbnail
`thumbnail.png`, posting text `description.md`, edit `edit.json`. **No GPU.** The brinjal field of Eps 3–4 on a storm
day: approved frames re-lit in code (`make_frames.py relight()` – storm-cloud sky, grey light, wet soil, puddles), live
rain from talk.py's `"rain"` option, rain + thunder sound from `tools/ambience.py`. New cut-away tool `tools/toon/storm.py`.

| Time | Scene | Made with |
|---|---|---|
| 0–8.2 | Sunny field – storm clouds roll in, wind; he glances up nervously; the downpour | `fortune.py sky`, f_sky, `downpour` |
| 8.2–16.6 | Banana leaf held up as an umbrella; the leaf shields a young plant, drops bouncing; water rising; his feet skid out | f_leaf, `shield`, `downpour`, `slip` |
| 16.6–22.4 | Plonked on a haystack in the rain, straw on him; the young plants bend over – "Thatha-vum saanjittaan!" | f_hay, `bend` |
| 22.4–28.8 | Rain stops: the higher side drains along the furrows, the low patch stays a pond; "andha pakkam mattum yen?" | `drain`, f_hmm |
| 28.8–35.8 | Notebook: field sketch, slope arrows, a drain along the low edge into a farm pond, water running | f_note, `drainplan` |
| 35.8–43.8 | Lifts a fallen plant; arms crossed, determined – the moral | f_lift, f_cross |
| 43.8–54.4 | The damaged field; the near-empty seed pouch – only five seeds roll out; wide-eyed – freeze (→ Ep 7) | `drain`, f_seed, `seeds`, freeze |

Script notes: he can't be animated running, so the banana-leaf shield is a held-up umbrella + a close-up of the leaf over a
plant; the fall is told by the feet skidding out + him landing on the haystack. Fact (TNAU): grade the field towards a
drain on the low side / a farm pond so rain water does not stand on the crop. No music.

Frames: f_sky (Ep 3 f_huh), f_leaf (Groundnut Ep 8 f_pod_s3 + banana leaf), f_hay (09_sitting on a code haystack),
f_hmm (Ep 3 f_point), f_note / f_seed (Ep 5 palm pose), f_lift (Ep 3 f_inspect), f_cross (Ep 3 f_cross).

Sound credits: "red_vented_bulbul.wav" by soundbytez and "rustling_leaves.wav" by laurenmg95 (freesound.org,
CC BY 3.0); other ambience CC0; rain, thunder and effects made in code.
