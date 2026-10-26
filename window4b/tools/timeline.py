"""Ep 1 timeline (owner's script v2, 26 Oct 2026): what the world looks like at time t (s).

Ten scenes, each with a new consequence: disruption, evacuation, power loss, failing
infrastructure, the bridge collapse, survival, abandonment, and the loop back to Day 1.
Colours are BGR 0..1 and stay natural (an overcast day, not a black-and-white storm).
Water levels are metres above street level (river surface on Day 1 = -1.2).
"""
FPS_DEFAULT = 24
DURATION = 150.0
TRANS = 2.5

STAGES = [  # start, counter text, values
    (0, "DAY 1", dict(level=-1.2, rain=0.6, wet=0.75, dark=0.05, puddles=0.1, river_mix=0.45, traffic="busy",
                      headlights=0.6, drops=0.4, rings=0.3, plant=0.0, moss=0.0, room_dark=0.08, water_alpha=0.92,
                      vines=0.0)),
    (12, "1 WEEK LATER", dict(level=-0.45, rain=0.8, wet=0.85, dark=0.07, puddles=0.6, river_mix=0.9,
                              traffic="slow", headlights=1.0, drops=0.8, rings=0.7, room_dark=0.1)),
    (30, "1 MONTH LATER", dict(level=0.18, rain=0.9, wet=0.88, dark=0.08, puddles=0.85, river_mix=1.0,
                               traffic="few", drops=0.95, rings=0.85, plant=0.12, room_dark=0.12)),
    (50, "2 MONTHS LATER", dict(level=1.45, rain=0.95, dark=0.1, traffic="stuck", headlights=0.0, plant=0.25,
                                room_dark=0.15)),
    (70, "3 MONTHS LATER", dict(level=2.0, rain=1.0, dark=0.12, plant=0.4, moss=0.25, room_dark=0.17)),
    (90, "6 MONTHS LATER", dict(level=2.45, dark=0.13, plant=0.6, moss=0.55, room_dark=0.18)),
    (110, "11 MONTHS LATER", dict(level=2.6, dark=0.14, plant=0.75, moss=0.75, room_dark=0.19)),
    (125, "1 WEEK LATER", dict(level=2.65, plant=0.82, moss=0.85, room_dark=0.19)),
    (138, "1 YEAR LATER", dict(level=2.7, rain=0.55, dark=0.12, drops=0.6, rings=0.55, plant=1.0, moss=1.0,
                               vines=1.0, room_dark=0.17)),
]
COLOURS = dict(tint=(1.0, 0.97, 0.94), haze=(0.74, 0.72, 0.69), sky_top=(0.66, 0.63, 0.6),
               sky_bot=(0.78, 0.76, 0.73), rain_col=(0.9, 0.9, 0.88), room_tint=(1.0, 0.97, 0.95))
WATER_RIVER = (0.5, 0.5, 0.42)     # grey-green river in the rain
WATER_MUD = (0.36, 0.47, 0.55)     # brown floodwater
LIGHTNING = [24.0, 47.0, 66.5, 97.0, 116.2, 131.0]
COLLAPSE = dict(cracks=111.0, groan=114.5, crack=116.4, fall=117.0, hit=118.1)
CLOSEUP = 148.0      # cut to the close-up of the mug
DROP_LANDS = 149.45  # the drop lands in the mug: cut to black


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


def stage_index(t):
    return max(k for k, s in enumerate(FILLED) if s[0] <= t)


def params(t):
    i = stage_index(t)
    start, label, v = FILLED[i]
    p = dict(v)
    if i > 0:
        prev = FILLED[i - 1][2]
        e = ease((t - start) / TRANS)
        for k in NUMERIC:
            p[k] = prev[k] + (v[k] - prev[k]) * e
    nxt = FILLED[i + 1][0] if i + 1 < len(FILLED) else DURATION
    if i + 1 < len(FILLED):  # the water keeps creeping up inside a stage
        creep = (FILLED[i + 1][2]["level"] - v["level"]) * 0.12
        p["level"] += creep * max(0.0, (t - start - TRANS) / (nxt - start - TRANS))
    if i == 0:  # Day 1: sunset, first drops at 2-4 s, rain builds, clouds swallow the sun
        r = ease((t - 4.0) / 6.0)
        cl = ease((t - 5.0) / 6.5)
        p.update(rain=0.6 * r, wet=0.75 * cl, dark=0.05 * cl, puddles=0.1 * cl, river_mix=0.45 * cl,
                 headlights=0.6 * cl, rings=0.3 * r, drops=0.4 * ease((t - 2.0) / 6), room_dark=0.08 * cl)
        p["overcast"] = cl
    else:
        p["overcast"] = 1.0
    p.update(COLOURS)
    mud = min(1.0, max(0.0, (p["level"] + 0.2) / 1.2))
    p["water"] = tuple(a * (1 - mud) + b * mud for a, b in zip(WATER_RIVER, WATER_MUD))
    p["sky_top"] = tuple(c * (1 - p["dark"]) for c in COLOURS["sky_top"])
    p["stage"], p["label"] = i, label
    p["label_a"] = ease((t - start - 0.3) / 0.6) * ease((nxt - t - 0.2) / 0.5)
    if i == len(FILLED) - 1:
        p["label_a"] = ease((t - start - 0.3) / 0.6) * ease((CLOSEUP - t - 0.1) / 0.4)
    p["jump"] = 0.0 if i == 0 else max(0.0, 1 - abs(t - start - 0.25) / 0.35)
    p["flash"], p["bolt"] = 0.0, 0
    for k, lt in enumerate(LIGHTNING):
        dt = t - lt
        if 0 <= dt < 0.45:
            p["flash"] = max(0.0, 1 - dt / 0.12) * 0.8 + (0.5 if 0.18 < dt < 0.26 else 0.0)
            p["bolt"] = k + 1
    p["closeup"] = t >= CLOSEUP
    p["black"] = t >= DROP_LANDS
    return p
