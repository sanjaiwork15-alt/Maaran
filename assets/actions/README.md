# Thatha action library – ready to use (owner 2026-11-02)

Owner: "code and animate these shots… create for others and keep it ready to use in future videos". No GPU, no
paid service: every clip is made in code from the owner's own drawings by `tools/toon/body.py` (the drawing is bent
smoothly with soft overlapping regions – no cut limb pieces, no visible joints; the stick and the side-view slippers
are rigid sprites). Demo of everything: `demo_reel.mp4` (built from `demo/*.json`).

| Clip | What | Length | Notes |
|---|---|---|---|
| `walk_front` | walking towards the camera with his stick | 1.1 s loop | grow the height along the path = he comes closer |
| `walk_side` | walking in profile, facing LEFT | 1.0 s loop | `flip: true` to walk right; path speed = ground_speed_px_s × height/fig_h (place_action prints it) |
| `turn` / `turn_right` | front → 3/4 → profile (left / right) | 0.6 s | then continue with walk_side (flipped after turn_right) |
| `idle` | standing, breathing, slow weight shift | 4 s loop | for any standing wide shot without talking |
| `look` | head turns left, right, back | 3 s | "what's that?" |
| `laugh` | belly laugh: shoulders shake, head back | 2.4 s | add a chuckle in the voice/sfx |
| `bow` | respectful nod-bow (vanakkam) | 1.8 s | |
| `tap` | tilts the stick out and taps it twice | 1.6 s | add `tools/sfx.py` "tap" at 0.35 s and 0.95 s |

Files: `<name>.webm` (VP9 with alpha, figure ~1600 px tall at the front size), `<name>.json` (frames, loop, size,
feet point, fig_h, facing, ground speed), `<name>_preview.mp4` (on grey).

## Use in an episode
Write a plan and run `python tools/toon/place_action.py PLAN.json OUT.mp4` (toon env), then use OUT.mp4 as a shot
in edit.json like any cut-away. Plan example (walk right across the farm, 4 s, figure 1150 px tall):
```json
{"bg": "frames/farm_plate.png", "duration": 4.0,
 "layers": [{"action": "walk_side", "flip": true, "shadow": 0.38,
             "path": [[0, 200, 1700, 1150], [4.0, 880, 1700, 1150]]}]}
```
Several layers can follow each other in one plan (e.g. turn_right at 0–0.6 s, then walk_side from 0.6 s).
`light` [r, g, b] multipliers match a scene's colour (sunset ~[1.05, 0.85, 0.65]). Library clips have no lip sync:
use them for wide/action shots under voice-over; talking close-ups stay talk.py.
Rebuild: `python -I tools/toon/body.py all` (f5 env; needs ~/.maaran/cache/up/08_turnaround_x2.png – make it with
`tools/upscale.py assets/2d/source/08_turnaround.png ~/.maaran/cache/up/08_turnaround_x2.png --scale 2`).

Lessons: never bend a rigid prop (stick) – rotate it as a sprite; a limb's region must exclude cloth but keep its
outlines; big motions need the inverse (destination) warp; in profile the arm swing must stay small (it overlaps the
shirt – there is nothing drawn behind it); a turn snaps between drawings (cross-fades look ghostly); erase a prop by
its own outline, never a box (the tap cut a slipper).
Earlier GPU plan (Wan 2.2 on Modal/Lightning) is not needed now.
