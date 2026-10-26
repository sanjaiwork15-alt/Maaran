"""Ep 1 story beats: the people, boats and machines that make each time jump mean something.

All positions are in master pixels of the 16:9 master ("h"); `ground` rows are where the thing
would stand at street level, so boats ride the flood surface above that point. Each beat is a
pure function of t, so frames can be rendered in any order.
"""
import math

import numpy as np

import actors as A
from timeline import ease

SKIN = [(0.55, 0.68, 0.86), (0.42, 0.55, 0.74), (0.33, 0.45, 0.62), (0.6, 0.72, 0.88)]
SHIRTS = [(0.25, 0.25, 0.7), (0.6, 0.45, 0.2), (0.3, 0.55, 0.35), (0.75, 0.75, 0.75), (0.2, 0.2, 0.25),
          (0.35, 0.6, 0.8)]
UMBRELLAS = [(0.2, 0.2, 0.75), (0.15, 0.15, 0.17), (0.6, 0.3, 0.2), (0.25, 0.6, 0.85)]

SIDEWALK = ((560, 612), (820, 752))      # along the road, right side
PROMENADE = ((820, 690), (1110, 775))    # by the river railing
ROAD = ((440, 625), (540, 765))            # left lane (the truck stands in the right one)
SIGNAL = (690, 712)
BUS = (440, 607)                          # stranded bus (wheels)
BALCONY = (262, 667)                      # floor of the lowest balcony, near-left building


def lerp(a, b, u):
    return (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)


class Ctx:
    def __init__(self, G, t, p, canvas, height, float_mask):
        self.G, self.t, self.p = G, t, p
        self.canvas, self.height, self.float_mask = canvas, height, float_mask
        self.sc = G["sc"]
        self.s = G["s"]                    # px per metre (master) at master row y
        self.L = p["level"]

    def u(self, y_m):
        return self.s(y_m) * self.sc * 1.2   # people and boats a touch larger than life, to read on a phone

    def surface(self, ground_y, ground_h=0.0):
        """Image row (master) of the flood surface above a street point."""
        return ground_y - max(0.0, self.L - ground_h) * self.s(ground_y)

    def stand(self, fn, xm, ym, *args, **kw):
        """Something standing on the ground: water covers it from its feet up."""
        x, y, u = xm * self.sc, ym * self.sc, self.u(ym)
        lay = A.Layer(x - 6 * u, y - 5 * u, x + 6 * u, y + 1.5 * u)
        lay.draw(fn, x, y, u, *args, **kw)
        lay.paste(self.canvas, self.height, y, u, clip=self.G["outside"])

    def float(self, fn, xm, ground_y, *args, ground_h=0.0, **kw):
        """Something floating on the flood above street point (xm, ground_y)."""
        y = self.surface(ground_y, ground_h) * self.sc
        x, u = xm * self.sc, self.u(ground_y)
        lay = A.Layer(x - 6 * u, y - 4 * u, x + 6 * u, y + 1.5 * u)
        lay.draw(fn, x, y, u, *args, **kw)
        lay.paste(self.canvas, float_mask=self.float_mask, clip=self.G["outside"])

    def sky(self, fn, xm, ym, u_m, *args, **kw):
        x, y, u = xm * self.sc, ym * self.sc, u_m * self.sc
        lay = A.Layer(x - 6 * u, y - 3 * u, x + 6 * u, y + 3 * u)
        lay.draw(fn, x, y, u, *args, **kw)
        lay.paste(self.canvas, clip=self.G["outside"])


# ---------------------------------------------------------------- beats

def day1_walkers(c):
    """People stroll the riverside at sunset, stop and look up at the first drops, then hurry."""
    t = c.t
    if t > 13:
        return
    rng = np.random.default_rng(5)
    for i in range(7):
        lane = SIDEWALK if i < 4 else PROMENADE
        u0 = rng.random(); v = (0.018 + 0.012 * rng.random()) * (1 if i % 2 else -1)
        stop = 6.2 + 0.4 * rng.random()
        if t < stop:
            pos = u0 + v * t; walking = True
        elif t < stop + 1.2:
            pos = u0 + v * stop; walking = False
        else:
            pos = u0 + v * stop + v * 2.6 * (t - stop - 1.2); walking = True
        if not 0 <= pos <= 1:
            continue
        x, y = lerp(*lane, pos)
        umb = UMBRELLAS[i % 4] if (t > stop + 0.9 and i % 3 != 2) else None
        c.stand(A.person, x, y, shirt=SHIRTS[i % 6], skin=SKIN[i % 4], phase=t * (6 if t < stop else 9) + i,
                walking=walking, umbrella=umb, arms_up=(1.0 if (not walking and i % 3 == 2) else 0.0))


def week1(c):
    t = c.t
    if 12 <= t < 30.5:
        k = (t - 12) / 18
        x, y = lerp(*ROAD, 0.05 + 0.7 * k)  # pushing a dead scooter through the puddles
        c.stand(A.scooter, x + 14, y + 4)
        c.stand(A.person, x, y, shirt=SHIRTS[1], phase=t * 4, walking=True, push=True)
        # the first rescue boat, far side of the river, carrying people and supplies
        bx = 1440 - 24 * (t - 12)
        c.float(A.rescue_boat, bx, 585, t, crew=1, passengers=2, cargo=2, facing=-1, ground_h=-1.2)


def month1(c):
    t = c.t
    if not 30 <= t < 50.5:
        return
    # evacuation: people with bags wade up the sidewalk, away from the river
    for i in range(3):
        u0 = 0.85 - 0.05 * i
        pos = u0 - 0.03 * (t - 30) - 0.06 * i
        if 0 <= pos <= 1:
            x, y = lerp(*SIDEWALK, pos)
            c.stand(A.person, x, y, shirt=SHIRTS[(i + 2) % 6], skin=SKIN[i], phase=t * 5 + i, bag=(0.25, 0.3, 0.55))
    # a passenger helped from the stranded bus into a rescue boat, which then leaves
    boat = (432, 652)
    if t < 40:
        k = ease((t - 32) / 5)
        c.float(A.rescue_boat, *boat, t, crew=2, passengers=1, facing=1, wake=0)
        if k < 1:
            c.stand(A.person, BUS[0] + 18 + (boat[0] - BUS[0] - 18) * k, BUS[1] + 3 + (boat[1] - BUS[1] - 3) * k,
                    shirt=SHIRTS[3], phase=t * 4, walking=0 < k < 1, bag=(0.3, 0.3, 0.6))
    else:
        k = (t - 40) / 10
        x, y = lerp(boat, (520, 790), k)
        c.float(A.rescue_boat, x, y, t, crew=2, passengers=2, facing=1)


def month2(c):
    t = c.t
    if not 50 <= t < 70.5:
        return
    x, y = lerp((740, 760), (430, 600), (t - 50) / 20)
    c.float(A.rescue_boat, x, y, t, crew=2, passengers=1, facing=-1)
    if t > 56:
        x, y = lerp((1180, 790), (840, 660), (t - 56) / 14)
        c.float(A.rescue_boat, x, y, t, crew=1, passengers=2, cargo=1, facing=-1)


def month3(c):
    t = c.t
    if 72 <= t < 90.5:
        x, y = lerp((560, 650), (840, 790), (t - 72) / 16)  # passes the dead traffic signal
        c.float(A.rescue_boat, x, y, t, crew=2, passengers=0, cargo=2, facing=1)


def traffic_signal(c):
    t = c.t
    if t >= 138:
        return
    if t < 70:
        ph = t % 8
        state = "green" if ph < 4 else ("amber" if ph < 5 else "red")
        if 66 < t < 70 and int(t * 7) % 3 == 0:
            state = "dead"
    else:
        state = "dead"
    c.stand(A.signal, *SIGNAL, state)


def stranded_bus(c):
    """The bus that stalls on Day 30 stays where it stopped, slowly swallowed by the water."""
    if c.t >= 30:
        c.G["draw_sprite_at"](c, "bus_road", BUS[0], BUS[1])


def bridge_debris(c):
    if c.t < 90:
        return
    for i, px in enumerate((460, 580, 724, 825, 940)):
        if c.t >= 117 and 600 <= px <= 790:
            continue
        y = c.surface(490, -1.2) * c.sc
        x, u = px * c.sc, c.u(490)
        lay = A.Layer(x - 6 * u, y - 3 * u, x + 6 * u, y + 2 * u)
        lay.draw(A.debris, x, y, u, i, n=5 + i % 3)
        lay.paste(c.canvas, float_mask=c.float_mask, clip=c.G["outside"])


def evacuation(c):
    """A week after the collapse: boats between buildings, a family taken from a balcony, a helicopter."""
    t = c.t
    if not 125 <= t < 138.5:
        return
    bx = 372
    if t < 133:
        c.float(A.rescue_boat, bx, 731, t, crew=2, passengers=int(t > 129.5) + int(t > 132), cargo=1,
                facing=1, wake=0)
    else:
        c.float(A.rescue_boat, bx + 60 * (t - 133), 731 + 4 * (t - 133), t, crew=2, passengers=2, facing=1)
    # family on the balcony, stepping across one by one
    for j, (start, scale, shirt) in enumerate(((127.5, 1.0, SHIRTS[0]), (130.3, 0.65, SHIRTS[2]))):
        if t < start:
            x, y = BALCONY[0] + 18 * j, BALCONY[1]
            c.stand(A.person, x, y, shirt=shirt, skin=SKIN[j], walking=False, arms_up=0.5 if j == 0 else 0)
        elif t < start + 2.0:
            k = ease((t - start) / 2.0)
            x = BALCONY[0] + 18 * j + (bx - 20 + 12 * j - BALCONY[0] - 18 * j) * k
            y = BALCONY[1] - math.sin(math.pi * k) * 10
            c.stand(A.person, x, y, shirt=shirt, skin=SKIN[j], phase=t * 5, walking=True)
    x, y = lerp((640, 735), (1300, 790), (t - 125) / 13)
    c.float(A.rescue_boat, x, y, t, crew=1, passengers=2, cargo=2, facing=1)
    x, y = lerp((1420, 560), (980, 520), (t - 125) / 13)
    c.float(A.rescue_boat, x, y, t, crew=1, passengers=1, facing=-1, ground_h=-1.2)
    hx = 1480 - (t - 125) * 100
    c.sky(A.helicopter, hx, 170 + 6 * math.sin(t), 4.5, t)


BEATS = [traffic_signal, stranded_bus, day1_walkers, week1, month1, month2, month3, bridge_debris, evacuation]


PRE_GRADE = [stranded_bus]   # cut from the art: graded with the city


def play(G, t, p, canvas, height, float_mask, pre=False):
    c = Ctx(G, t, p, canvas, height, float_mask)
    for beat in BEATS:
        if (beat in PRE_GRADE) == pre:
            beat(c)
