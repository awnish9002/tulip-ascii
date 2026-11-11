"""
TULIPS - three tulips grow one after another, open in the sun and sway,
while a little butterfly flutters between them.

    python tulip.py                     open the animated window
    python tulip.py --shot 14 out.png   render the frame at t=14s to a PNG (no window)

Keys: SPACE pause · R restart · S screenshot · ESC quit
Needs ../ascii_engine.py and:  pip install numpy pygame-ce
"""
import math
import os
import random
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import ascii_engine as E  # noqa: E402

E.SCREEN_CY = 430
E.EDGE_T = 0.30
E.RAMPS = [".:-=+*tfjzrcxvunoeaQ0&8B%$#@"]

GROUND_Y = -2.2
CAM_TILT = 0.15
T_BUTTERFLY = 7.0

TULIPS = [  # x, z, flower height, (tip colour, base colour), start time, sway phase, lean
    dict(x=-1.05, z=0.15, top=0.10, col=((255, 225, 120), (255, 120, 30)), t0=0.0, ph=0.0, lean=-0.18),
    dict(x=0.00, z=-0.25, top=0.70, col=((255, 175, 210), (230, 30, 105)), t0=0.7, ph=1.3, lean=0.05),
    dict(x=1.05, z=0.20, top=0.30, col=((235, 195, 255), (140, 60, 225)), t0=1.4, ph=2.4, lean=0.18),
]


def stem_curve(tp, s):
    s = np.asarray(s, float)
    x = tp["x"] + tp["lean"] * s ** 2 + 0.04 * np.sin(3 * s)
    y = GROUND_Y + (tp["top"] - GROUND_Y) * s
    z = tp["z"] + 0.03 * np.sin(4 * s)
    return np.stack([x, y, z], -1)


def tulip_flower(base, size, open_, nu=28, nv=13):
    """Six cupped petals (three outer, three inner) around the stem tip."""
    u = np.linspace(0, 1, nu)[:, None]
    v = np.linspace(-1, 1, nv)[None, :]
    out = []
    for k in range(6):
        inner = k % 2 == 1
        th = k * np.pi / 3 + 0.2
        hw = 0.64 * np.sqrt(np.clip(np.sin(np.pi * (0.15 + 0.85 * u)), 0, 1)) * (1 - u ** 6)
        ang = th + v * hw
        r = (0.04 + 0.31 * np.sin(np.pi * 0.85 * u) ** 0.6) * (0.86 if inner else 1.0)
        r = r + open_ * u ** 2 * (0.26 if inner else 0.34)
        r = r * (1 - 0.06 * v ** 2)                       # a slight crease down each petal
        h = 0.80 * u * (0.94 if inner else 1.0)
        P = np.asarray(base) + size * np.stack([r * np.cos(ang), h * np.ones_like(ang), r * np.sin(ang)], -1)
        out.append((P, E.surface_normals(P), np.broadcast_to(u, P.shape[:2])))
    return out


def sway(P, tp, t):
    """Bend a tulip in the wind; the flower trails behind the stem."""
    hgt = np.clip((P[..., 1] - GROUND_Y) / (tp["top"] + 0.8 - GROUND_Y), 0, 1.2)
    w = 0.10 + 0.05 * math.sin(t * 0.21)
    P = P.copy()
    P[..., 0] += w * hgt ** 2 * np.sin(1.1 * t + tp["ph"] - 1.3 * hgt)
    P[..., 2] += 0.5 * w * hgt ** 2 * np.sin(0.8 * t + tp["ph"] - 1.3 * hgt + 1)
    return P


def butterfly_wings(flap, nu=10, na=26):
    """Two wings in the butterfly's own frame (x = right, y = up, z = forward)."""
    u = np.linspace(0.05, 1, nu)[:, None]
    al = np.linspace(-1.45, 1.45, na)[None, :]
    R = 0.30 * (0.35 + 0.65 * np.abs(np.sin(2 * al)) ** 0.6) * (1 + 0.22 * np.sin(al))
    a = u * R * np.cos(al)
    b = u * R * np.sin(al)
    wings = []
    for side in (1, -1):
        P = np.stack([side * a * math.cos(flap), a * math.sin(flap), b], -1)
        col = (np.array([90, 170, 255])[None, None] * (1 - u[..., None])
               + np.array([215, 240, 255])[None, None] * u[..., None]) * np.ones((1, na, 1))
        rim = (u > 0.86)[..., None] * np.ones((1, na, 1))
        col = col * (1 - 0.55 * rim)
        wings.append((P, E.surface_normals(P), col))
    return wings


class Tulips:
    title = "TULIPS - ASCII"

    def __init__(self):
        self.rng = random.Random(21)
        self.reset()

    def reset(self):
        self.t = 0.0
        self.fx = E.Particles(self.rng)
        self.pollen = E.Particles(self.rng)
        self.pollen_timer = 0.0
        for _ in range(30):
            self._pollen(y=self.rng.uniform(-2, 2.5))

    def _pollen(self, y=None):
        r = self.rng
        self.pollen.emit([r.uniform(-4, 4), r.uniform(-2.2, -1) if y is None else y, r.uniform(-1, 2)], n=1,
                         vel=[r.uniform(-.05, .05), r.uniform(.04, .15), 0], life=(10, 16),
                         rgb=r.choice([(255, 230, 120), (255, 255, 200), (255, 200, 120)]),
                         chars="•*.", gravity=0.0, drag=1.0, wobble=0.25)

    def grow(self, tp):
        return E.sstep(tp["t0"], tp["t0"] + 2.5, self.t)

    def openness(self, tp):
        o = E.sstep(tp["t0"] + 5, tp["t0"] + 9, self.t)
        return -0.12 + 0.62 * o + 0.05 * o * math.sin(self.t * 0.8 + tp["ph"])

    def butterfly(self):
        """Position, orientation matrix and wing flap, or None before it arrives."""
        t = self.t
        if t < T_BUTTERFLY:
            return None
        tau = t - T_BUTTERFLY
        def pos(tt):
            return np.array([2.0 * math.cos(0.37 * tt) - 0.4 + 0.0 * tt, 0.9 + 0.35 * math.sin(0.83 * tt),
                             -0.4 + 0.7 * math.sin(0.29 * tt)])
        p = pos(tau)
        v = pos(tau + 0.05) - p
        f = E.normalize(np.array([v[0], 0.25 * v[1], v[2]]))
        up = np.array([0, 1.0, 0])
        r = E.normalize(np.cross(up, f))
        up = np.cross(f, r)
        flap = 0.15 + 0.95 * math.sin(t * 15)
        return p, np.stack([r, up, f], 1), flap, E.sstep(T_BUTTERFLY, T_BUTTERFLY + 0.8, t)

    def update(self, dt):
        for tp in TULIPS:
            g = self.grow(tp)
            if 0 < g < 1:
                self.fx.emit(sway(stem_curve(tp, g)[None], tp, self.t)[0], n=3, spread=0.4, up=0.1,
                             life=(0.4, 0.9), rgb=(200, 255, 200), chars="*+.", gravity=-0.8)
        bf = self.butterfly()
        if bf is not None and self.rng.random() < 0.5:
            self.fx.emit(bf[0], n=1, spread=0.08, up=-0.05, life=(0.6, 1.2), rgb=(170, 220, 255),
                         chars="*•.", gravity=-0.2)
        self.pollen_timer -= dt
        if self.pollen_timer <= 0:
            self.pollen_timer = 0.5
            self._pollen()
        self.fx.update(dt)
        self.pollen.update(dt)
        self.t += dt

    def render(self, R, screen, stars):
        t = self.t
        cam = E.rot_x(CAM_TILT) @ E.rot_y(0.18 * math.sin(t * 0.15))
        R.begin(screen, stars, t)
        b = E.Batch()
        for tp in TULIPS:
            g = self.grow(tp)
            if g <= 0:
                continue
            s = np.linspace(0, 1, 160)
            P, N = E.tube(stem_curve(tp, s), 0.034 - 0.008 * s, nv=10)
            vis = np.broadcast_to((s <= g)[:, None], P.shape[:2])
            b.add(sway(P, tp, t), N, (45, 200, 80), spec=0.08, mask=vis, gain=0.85)
            lg = E.sstep(tp["t0"] + 0.8, tp["t0"] + 2.6, t)
            if lg > 0:
                for yaw, L in ((math.pi + 0.3, 1.45), (-0.3, 1.2)):
                    base = stem_curve(tp, 0.03)
                    P, N, var = E.leaf(base, yaw, 1.32, L, 0.26, lg, droop=0.28, roll=0.35, fold=0.4)
                    b.add(sway(P, tp, t), N, (60, 215, 95), spec=0.2, gain=1.05 * var)
            bud = E.sstep(tp["t0"] + 2.2, tp["t0"] + 3.4, t)
            if bud > 0:
                light, dark = np.array(tp["col"][0]), np.array(tp["col"][1])
                for P, N, u in tulip_flower(stem_curve(tp, 1.0) - [0, 0.03, 0], 1.25 * bud, self.openness(tp)):
                    w = (u ** 1.3)[..., None]
                    b.add(sway(P, tp, t), N, dark * (1 - w) + light * w, spec=0.35, gain=1.15)
        bf = self.butterfly()
        if bf is not None:
            p, Mb, flap, a = bf
            a = a * 1.6
            for P, N, col in butterfly_wings(flap):
                b.add(P * a @ Mb.T + p, N @ Mb.T, col, spec=0.4, gain=1.25)
            P, N, _ = E.ellipsoid([0, 0, 0], [0.028, 0.03, 0.13], 12, 8)
            b.add(P * a @ Mb.T + p, N @ Mb.T, (60, 50, 80), spec=0.2, gain=0.9)

        R.render_batch(b, cam, [((-0.5, 0.8, -0.6), 0.95, 18), ((0.7, 0.3, -0.4), 0.35, 30),
                                ((0.3, -0.4, 0.9), 0.25, 8)])
        R.draw_grid()
        gr = R.ground_row(cam, GROUND_Y)
        R.draw_reflection(gr, n=8, strength=0.18)
        self.draw_grass(R, gr - 1, t)

        if bf is not None:          # antennae
            p, Mb, flap, a = bf
            a = a * 1.6
            head = (p + Mb @ np.array([0, 0.02, 0.13]) * a) @ cam.T
            for sx in (-1, 1):
                tip = (p + Mb @ np.array([0.07 * sx, 0.12, 0.24]) * a) @ cam.T
                R.draw_line(head, tip, (190, 200, 230), 0.8)

        self.pollen.draw(R, cam, fade_in=2.0)
        self.fx.draw(R, cam)
        for tp in TULIPS:
            g = self.grow(tp)
            if 0 < g < 1:
                x, y = R.cell_of(sway(stem_curve(tp, g)[None], tp, t)[0] @ cam.T)
                R.draw_flare(R.layer, x, y, 3, (220, 255, 225), 1.0)

        R.finish(screen)
        op = max(0.0, (self.openness(TULIPS[1]) + 0.12) / 0.62)
        R.hud(screen, ["TULIPS  .  2026", f"bloom {min(op, 1) * 100:5.1f}%   tulips {sum(self.grow(tp) > 0 for tp in TULIPS)}",
                       f"letters {R.letters:,}"], t)

    def draw_grass(self, R, row, t):
        """A strip of little grass characters along the ground."""
        a = E.sstep(0, 1.5, t)
        blits = []
        c0, c1 = int(R.cols * 0.18), int(R.cols * 0.82)
        for c in range(c0, c1):
            h = (c * 7919) % 13
            edge = min(c - c0, c1 - c) / 10.0
            f = a * min(1.0, edge) * (0.35 + 0.25 * (h % 3))
            ch = ",'`\"/\\|.v,'`\"/"[h]
            lean = math.sin(t * 1.1 + c * 0.3)
            if ch in "/\\|":
                ch = "/" if lean > 0.4 else "\\" if lean < -0.4 else "|"
            col = R.q(np.array([70, 190, 90]) * f)
            if max(col) >= 12:
                blits.append((R.glyph(ch, col), (c * R.cw, row * R.ch)))
        R.layer.blits(blits, doreturn=False)


if __name__ == "__main__":
    E.run(Tulips(), E.Starfield(random.Random(8), n=240, flares=7, flare_size=(2, 5), flare_a=0.55),
          prefix="tulips")
