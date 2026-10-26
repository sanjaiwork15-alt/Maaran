# Ep 1 – production notes and script review

Script: `script.md`. Masters: `window4b/assets/master/` (16:9 and 9:16). Status: **script reviewed, awaiting owner
answers below before stage stills.**

## Water-level ladder (one table drives both masters)

The script's levels contradict each other: Month 6 has "only the upper sections of some trees" above water (≈ 6–8 m
of flood), but Month 11 has water only "reaching the lower floors" of nearby buildings, which would already have been
under at Month 6. Proposed monotonic ladder, measured against landmarks that exist in both masters:

| Stage | River / street water | Landmark check |
|---|---|---|
| DAY 1 | Normal | Dry walkway and road |
| WEEK 1 | River darker, at the top of its bank | Puddles on road; walkway still dry |
| MONTH 1 | Over the walkway, ankle–knee deep | Bench seats awash, tree trunks in water, pool beside the shelter |
| MONTH 3 | Over the road, ≈ 0.5–1 m | Car wheels/doors under, shelter bench gone, streetlight bases under |
| MONTH 6 | ≈ 3 m | Shelter roof just under, car roofs gone, tree crowns half out, near building's ground floor under |
| MONTH 11 | ≈ 5–6 m | Only tree tops; near building's first floor under; water halfway up the bridge piers; debris and moss |
| 1 YEAR | ≈ 7 m (stays below the bridge deck) | Streetlights gone; piers mostly under; bridge an island line across the water |

Scene 6's visual becomes "water climbs past the first floor" instead of "reaches the lower floors".

## Other fixes proposed

1. **Hook timing.** The bible says the rule change must land in the first 2 s. Scene 1 runs 10 s: first drop at 0:01,
   full rain by ~0:05, clouds over the sun by 0:09.
2. **Rain inside the mug.** Drops hit the glass, so the window is closed and the mug (inside, on the sill) can't fill
   with rain. Options: the window is open a crack and rain blows in (show wet sill from MONTH 1), or a leak drips from
   the frame top. Recommend the leak: a slow drip from MONTH 3, a damp patch on the sill, the mug full at YEAR 1.
3. **Plant.** Drooping fits (a year without sun). Show the decline in steps: fine to MONTH 1, leaves yellowing MONTH 6,
   drooping YEAR 1.
4. **Glass layer.** Neither master shows glass. Raindrops and streams need a "glass plane" layer over the window opening
   only (not over the sill, plant or mug).
5. **Counter position.** Upper-left sky: 16:9 at about x 15 %, y 6 % (sky between the balcony building and the towers);
   9:16 at about x 18 %, y 6 % (right of the curtain, clear of the Shorts top bar).
6. **Thunder needs a picture.** Add 2–3 lightning flashes (whole-frame brightening, one bolt over the skyline) on the
   thunder hits in WEEK 1, MONTH 3 and MONTH 11.
7. **Vertical master has no glass tower** – Scene 6 moss/vines go on the near-left balcony building in both versions.
8. **Daylight.** DAY 1 is sunset; from WEEK 1 on, a flat grey daytime, darker each stage. Streetlights stay on until
   they go under (MONTH 6–11). Headlights on cars until traffic stops at MONTH 3.

## Making it (plan)

**Pictures:** 7 stage stills × 2 formats = 14 key frames, edited from the masters (Qwen-Image-Edit on Kaggle, the same
job as Maaran), each checked against the landmark tables so nothing moves. Masters upscaled to 3840 px first.
**Motion (code, so the camera can't drift):** rain particle layers in 3 depths, drops and streams on the glass, water
ripple and slow rise between stages (masked dissolve from the water line up), drifting debris, cloud drift, lightning,
car sprites on the bridge and road for DAY 1–MONTH 1. AI video (Wan I2V) only if a shot looks dead, and checked for
geometry drift.
**Sound:** none of the needed sounds are in the repo yet (it has birds and leaves only). Need CC0/CC BY: rain on glass,
light/heavy rain, distant city traffic, wet tyres, thunder (near/far), drain gurgle, water lapping on concrete, wind
gusts, creaking branches, plus one made-in-house whoosh-and-tick and a soft pad for the end. Credits go in the
episode's description file.
**Output:** `ep01_16x9.mp4` and `ep01_9x16.mp4`, both 2:30, same timings and sound mix.
