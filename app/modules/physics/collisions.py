"""Collisions: 1D formula and event-driven 2D simulation of discs (exact, no time-stepping error)."""
import math
from typing import Any

import numpy as np

from app.core.registry import tool

MAX_BALLS = 12
MAX_EVENTS = 20_000


@tool(
    domain="physics",
    name="collision_1d",
    description=(
        "Head-on collision of two bodies with coefficient of restitution e (1 = elastic, 0 = perfectly "
        "inelastic). Masses in kg, velocities in m/s (signed). Returns final velocities, momentum and kinetic "
        "energy before/after. Example: m1=2, v1=3, m2=1, v2=-1, restitution=1."
    ),
)
def collision_1d(m1: float, v1: float, m2: float, v2: float, restitution: float = 1.0) -> dict:
    if m1 <= 0 or m2 <= 0:
        raise ValueError("Masses must be positive")
    if not 0 <= restitution <= 1:
        raise ValueError("restitution must be between 0 and 1")
    e, M = restitution, m1 + m2
    u1 = ((m1 - e * m2) * v1 + (1 + e) * m2 * v2) / M
    u2 = ((m2 - e * m1) * v2 + (1 + e) * m1 * v1) / M
    ke0, ke1 = 0.5 * (m1 * v1**2 + m2 * v2**2), 0.5 * (m1 * u1**2 + m2 * u2**2)
    return {
        "result": {"v1_final": u1, "v2_final": u2},
        "momentum": {"before": m1 * v1 + m2 * v2, "after": m1 * u1 + m2 * u2},
        "kinetic_energy": {"before": ke0, "after": ke1, "lost": ke0 - ke1},
        "centre_of_mass_velocity": (m1 * v1 + m2 * v2) / M,
        "units": "velocities m/s, momentum kg m/s, energy J",
        "assumptions": ["Point bodies in 1D, instantaneous impact", "Restitution e = relative speed after / before"],
    }


@tool(
    domain="physics",
    name="collisions_2d",
    description=(
        "Event-driven simulation of discs colliding in 2D (exact between collisions). balls: list of "
        "{mass, radius, x, y, vx, vy} in SI units. restitution applies to ball-ball impacts; walls (a box of "
        "width x height with the origin at the bottom-left) reflect elastically if reflecting_walls is true. "
        "Returns plot-ready positions per frame, collision events, and momentum / kinetic energy over time. "
        "Example: balls=[{mass:1,radius:0.1,x:0.5,y:0.5,vx:1,vy:0},{mass:1,radius:0.1,x:1.5,y:0.55,vx:0,vy:0}], "
        "width=2, height=1, duration=2."
    ),
)
def collisions_2d(
    balls: list[dict[str, Any]],
    duration: float,
    width: float = 2.0,
    height: float = 1.0,
    restitution: float = 1.0,
    reflecting_walls: bool = True,
    n_frames: int = 301,
) -> dict:
    if not 1 <= len(balls) <= MAX_BALLS:
        raise ValueError(f"Give between 1 and {MAX_BALLS} balls")
    if duration <= 0 or width <= 0 or height <= 0:
        raise ValueError("duration, width and height must be positive")
    if not 0 <= restitution <= 1:
        raise ValueError("restitution must be between 0 and 1")
    if not 2 <= n_frames <= 5000:
        raise ValueError("n_frames must be between 2 and 5000")
    m = np.array([float(b["mass"]) for b in balls])
    r = np.array([float(b["radius"]) for b in balls])
    p = np.array([[float(b["x"]), float(b["y"])] for b in balls])
    v = np.array([[float(b.get("vx", 0)), float(b.get("vy", 0))] for b in balls])
    n = len(balls)
    if np.any(m <= 0) or np.any(r <= 0):
        raise ValueError("Masses and radii must be positive")
    if reflecting_walls and (np.any(p[:, 0] - r < -1e-12) or np.any(p[:, 0] + r > width + 1e-12)
                             or np.any(p[:, 1] - r < -1e-12) or np.any(p[:, 1] + r > height + 1e-12)):
        raise ValueError("Every ball must start inside the box")
    for i in range(n):
        for j in range(i + 1, n):
            if np.linalg.norm(p[i] - p[j]) < r[i] + r[j] - 1e-12:
                raise ValueError(f"Balls {i} and {j} overlap at the start")

    def pair_time(i: int, j: int) -> float:
        dp, dv = p[j] - p[i], v[j] - v[i]
        b = dp @ dv
        if b >= 0:
            return math.inf
        dvv, dpp, s = dv @ dv, dp @ dp, r[i] + r[j]
        disc = b * b - dvv * (dpp - s * s)
        if disc < 0 or dvv == 0:
            return math.inf
        return max(0.0, (-b - math.sqrt(disc)) / dvv)

    def wall_time(i: int) -> tuple[float, int]:
        best, axis = math.inf, -1
        for k, hi in ((0, width), (1, height)):
            if v[i, k] > 0:
                t = (hi - r[i] - p[i, k]) / v[i, k]
            elif v[i, k] < 0:
                t = (r[i] - p[i, k]) / v[i, k]
            else:
                continue
            if t < best:
                best, axis = max(0.0, t), k
        return best, axis

    frame_t = np.linspace(0, duration, n_frames)
    frames, mom, ke = [], [], []
    events: list[dict[str, Any]] = []
    t, k = 0.0, 0
    last_pair = None

    def record(upto: float) -> None:
        nonlocal k
        while k < n_frames and frame_t[k] <= upto + 1e-15:
            dt = frame_t[k] - t
            frames.append((p + v * dt).tolist())
            mom.append((m[:, None] * v).sum(axis=0).tolist())
            ke.append(float(0.5 * (m * (v**2).sum(axis=1)).sum()))
            k += 1

    for _ in range(MAX_EVENTS):
        best, kind, who = math.inf, None, None
        for i in range(n):
            for j in range(i + 1, n):
                if last_pair == (i, j):
                    continue
                tc = pair_time(i, j)
                if tc < best:
                    best, kind, who = tc, "ball", (i, j)
            if reflecting_walls:
                tw, axis = wall_time(i)
                if tw < best:
                    best, kind, who = tw, "wall", (i, axis)
        if t + best > duration:
            break
        record(t + best)
        p += v * best
        t += best
        if kind == "ball":
            i, j = who
            nrm = (p[j] - p[i]) / np.linalg.norm(p[j] - p[i])
            rel = (v[i] - v[j]) @ nrm
            jimp = (1 + restitution) * rel / (1 / m[i] + 1 / m[j])
            v[i] -= jimp / m[i] * nrm
            v[j] += jimp / m[j] * nrm
            events.append({"t": t, "type": "ball", "a": i, "b": j})
            last_pair = (i, j)
        else:
            i, axis = who
            v[i, axis] = -v[i, axis]
            events.append({"t": t, "type": "wall", "a": i, "axis": "x" if axis == 0 else "y"})
            last_pair = None
    else:
        raise ValueError("Too many collisions to simulate; shorten the duration")
    record(duration)
    frames_arr = np.array(frames)
    return {
        "result": {
            "final_velocities": v.tolist(),
            "ball_collisions": sum(e["type"] == "ball" for e in events),
            "wall_bounces": sum(e["type"] == "wall" for e in events),
        },
        "frames": {"t": frame_t.tolist(), "x": frames_arr[:, :, 0].T.tolist(), "y": frames_arr[:, :, 1].T.tolist()},
        "momentum": {"px": [q[0] for q in mom], "py": [q[1] for q in mom]},
        "kinetic_energy": ke,
        "events": events[:500],
        "units": "positions m, velocities m/s, momentum kg m/s, energy J, time s",
        "assumptions": [
            "Smooth (frictionless) rigid discs, instantaneous impacts along the line of centres",
            f"Ball-ball restitution {restitution}; walls elastic" if reflecting_walls else f"Ball-ball restitution {restitution}; no walls",
            "Event-driven: exact straight-line motion between collisions",
        ],
    }
