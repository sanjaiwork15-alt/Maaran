"""Ep 1 timeline: what the world looks like at time t (seconds). Colours are BGR 0..1.

Stage boundaries follow the owner's script (series script.md). At every boundary the values
ease to the next stage over TRANS seconds, starting with the whoosh-and-tick.
Water levels are metres above street level (river surface on Day 1 = -1.2).
"""
FPS_DEFAULT = 24
DURATION = 150.0
TRANS = 2.5

STAGES = [  # start, label, values
    (0, "DAY 1", dict(level=-1.2, rain=0.65, wet=0.8, dark=0.08, overcast=1.0, puddles=0.10, river_mix=0.55,
                      traffic="busy", headlights=0.6, lights=0.6, drops=0.45, rings=0.35, plant=0.0, mug=0.0,
                      sill_wet=0.0, moss=0.0, debris=0.0, room_dark=0.18, water_alpha=0.9)),
    (10, "WEEK 1", dict(level=-0.75, rain=0.85, wet=0.9, dark=0.14, puddles=0.35, river_mix=0.9,
                        traffic="busy", headlights=1.0, lights=0.8, drops=0.85, rings=0.7, room_dark=0.25)),
    (30, "MONTH 1", dict(level=0.08, rain=0.95, wet=0.95, dark=0.18, puddles=0.6, river_mix=1.0, traffic="slow",
                         headlights=1.0, drops=1.0, rings=0.9, plant=0.15, room_dark=0.3)),
    (55, "MONTH 3", dict(level=0.95, rain=1.0, dark=0.22, puddles=0.8, traffic="few", headlights=0.0,
                         lights=0.7, plant=0.35, mug=0.25, sill_wet=0.4, room_dark=0.33)),
    (80, "MONTH 6", dict(level=1.9, rain=0.9, dark=0.24, traffic="stuck", lights=0.45, plant=0.55, mug=0.5,
                         sill_wet=0.6, moss=0.35, debris=0.4, room_dark=0.35)),
    (105, "MONTH 11", dict(level=2.55, rain=1.0, dark=0.28, lights=0.3, plant=0.8, mug=0.8, sill_wet=0.8,
                           moss=0.85, debris=1.0, room_dark=0.38)),
    (130, "1 YEAR LATER", dict(level=2.85, rain=0.6, dark=0.25, lights=0.25, drops=0.7, rings=0.6, plant=1.0,
                               mug=1.0, sill_wet=0.9, moss=1.0, debris=0.8, room_dark=0.36)),
]
COLOURS = dict(tint=(0.98, 0.92, 0.86), haze=(0.62, 0.6, 0.57), sky_top=(0.46, 0.44, 0.42),
               sky_bot=(0.66, 0.64, 0.61), water=(0.42, 0.44, 0.42), rain_col=(0.85, 0.85, 0.83),
               room_tint=(0.95, 0.9, 0.86))
WATER_MUD = (0.33, 0.40, 0.44)
LIGHTNING = [21.0, 47.5, 66.2, 92.0, 118.4, 123.6]
DRIPS_FROM = 57.0   # first drip from the leak into the mug
DRIP_EVERY = 3.1


def _filled():
    vals, cur = [], {}
    for start, label, v in STAGES:
        cur = {**cur, **v}
        vals.append((start, label, dict(cur)))
    return vals


FILLED = _filled()
NUMERIC = [k for k, v in FILLED[0][2].items() if isinstance(v, (int, float))]


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def params(t):
    i = max(k for k, s in enumerate(FILLED) if s[0] <= t)
    start, label, v = FILLED[i]
    p = dict(v)
    if i > 0:  # ease from the previous stage
        prev = FILLED[i - 1][2]
        e = ease((t - start) / TRANS)
        for k in NUMERIC:
            p[k] = prev[k] + (v[k] - prev[k]) * e
        if e < 1 and t - start < 0.8:
            p["traffic"] = prev["traffic"]
    nxt = FILLED[i + 1][0] if i + 1 < len(FILLED) else DURATION
    # within a stage the water keeps creeping up a little
    if i + 1 < len(FILLED):
        creep = (FILLED[i + 1][2]["level"] - v["level"]) * 0.12
        p["level"] += creep * max(0.0, (t - start - TRANS) / (nxt - start - TRANS))
    # Day 1: sunset, then the first drops, then the city-wide rain and clouds over the sun
    if i == 0:
        r = ease((t - 2.0) / 4.5)
        cl = ease((t - 2.5) / 6.5)
        p.update(rain=0.65 * r, wet=0.8 * cl, dark=0.08 * cl, overcast=cl, puddles=0.1 * cl,
                 river_mix=0.55 * cl, headlights=0.6 * cl, lights=0.6 * cl, rings=0.35 * r,
                 drops=0.45 * ease((t - 1.0) / 6), room_dark=0.18 * cl)
        p["traffic"] = "busy"
    p["overcast"] = p.get("overcast", 1.0) if i == 0 else 1.0
    p.update(COLOURS)
    mud = min(1.0, max(0.0, (p["level"] - 0.2) / 1.2))
    p["water"] = tuple(a * (1 - mud) + b * mud for a, b in zip(COLOURS["water"], WATER_MUD))
    # darker sky, haze and room with each stage
    d = p["dark"]
    p["sky_top"] = tuple(c * (1 - d * 0.6) for c in COLOURS["sky_top"])
    # the counter: fades in after each jump, out before the next
    p["label"] = label
    p["label_a"] = ease((t - start - 0.3) / 0.6) * ease((nxt - t - 0.2) / 0.5) if t < DURATION - 0.01 else 1.0
    if label == "1 YEAR LATER":
        p["label_a"] = ease((t - start - 0.3) / 0.6)
    # the time jump: a quick dip as the whoosh passes
    p["jump"] = 0.0 if i == 0 else max(0.0, 1 - abs(t - start - 0.25) / 0.35)
    # lightning: a double flicker
    p["flash"], p["bolt"] = 0.0, 0
    for k, lt in enumerate(LIGHTNING):
        dt = t - lt
        if 0 <= dt < 0.45:
            p["flash"] = max(0.0, 1 - dt / 0.12) * 0.9 + (0.6 if 0.18 < dt < 0.26 else 0.0)
            p["bolt"] = k + 1
    # the drip into the mug
    p["drip"] = None
    if t >= DRIPS_FROM:
        p["drip"] = ((t - DRIPS_FROM) % DRIP_EVERY) / 1.0 if ((t - DRIPS_FROM) % DRIP_EVERY) < 1.0 else None
    # ending: one last drop slides down the glass
    p["final_drop"] = ease((t - 141.0) / 6.0) if t > 141.0 else 0
    return p
