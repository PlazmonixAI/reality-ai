"""Energy skate park: a skater sliding along a smooth spline track under gravity with friction."""
import math

import numpy as np
from scipy.integrate import solve_ivp
from scipy.interpolate import CubicSpline

from app.core.registry import tool

G0 = 9.80665


def build_track(points: list[list[float]], samples: int = 2000) -> dict:
    """Spline through control points (x increasing), tabulated against arc length."""
    pts = np.array(points, dtype=float)
    if pts.ndim != 2 or pts.shape[1] != 2 or not 3 <= len(pts) <= 40:
        raise ValueError("track_points must be 3..40 points [x, y]")
    if np.any(np.diff(pts[:, 0]) <= 0):
        raise ValueError("track_points must have strictly increasing x")
    spline = CubicSpline(pts[:, 0], pts[:, 1], bc_type="natural")    # y(x): x is strictly increasing
    x = np.linspace(pts[0, 0], pts[-1, 0], samples)
    y, dy, ddy = spline(x), spline(x, 1), spline(x, 2)
    ds_dx = np.sqrt(1 + dy * dy)
    s = np.concatenate([[0], np.cumsum(0.5 * (ds_dx[1:] + ds_dx[:-1]) * np.diff(x))])
    return {
        "s": s, "x": x, "y": y,
        "phi": np.arctan(dy),
        "kappa": ddy / ds_dx**3,
        "length": float(s[-1]),
    }


@tool(
    domain="physics",
    name="skate_track",
    description=(
        "Skater (point mass) sliding along a smooth track through the given control points (spline, x "
        "increasing) under gravity, with optional kinetic friction coefficient. start is the fraction of the way "
        "along the track (0..1). The skater stays on the track; at either end it stops and can slide back. "
        "Returns plot-ready position, speed and kinetic / potential / thermal energy over time. "
        "Example: track_points=[[-4,4],[-2,1],[0,0],[2,1],[4,4]], mass=60, start=0.1, friction=0."
    ),
)
def skate_track(
    track_points: list[list[float]],
    mass: float = 60.0,
    start: float = 0.1,
    initial_speed: float = 0.0,
    friction: float = 0.0,
    gravity: float = G0,
    duration: float = 10.0,
    n_points: int = 601,
) -> dict:
    if mass <= 0 or gravity <= 0 or duration <= 0 or friction < 0:
        raise ValueError("mass, gravity and duration must be positive, friction >= 0")
    if not 0 <= start <= 1:
        raise ValueError("start must be between 0 and 1")
    if not 2 <= n_points <= 10_000:
        raise ValueError("n_points must be between 2 and 10000")
    tr = build_track(track_points)
    S, L = tr["s"], tr["length"]
    # Smooth (C2) interpolants of slope angle and curvature: linear interpolation would put a kink at every
    # sample and force the integrator into tiny steps.
    phi_s = CubicSpline(S, tr["phi"])
    kappa_s = CubicSpline(S, tr["kappa"])
    phi = lambda s: float(phi_s(min(max(s, 0.0), L)))       # noqa: E731
    v_eps = 1e-2

    def rhs(_t, z):
        s, v = z
        p, k = phi(s), float(kappa_s(min(max(s, 0.0), L)))
        normal = max(0.0, gravity * math.cos(p) + k * v * v)   # per unit mass
        fr = friction * normal * math.tanh(v / v_eps)
        return [v, -gravity * math.sin(p) - fr]

    def hit_start(_t, z): return z[0]
    def hit_end(_t, z): return z[0] - L
    hit_start.terminal = hit_end.terminal = True
    hit_start.direction, hit_end.direction = -1, 1

    t_eval = np.linspace(0, duration, n_points)
    ts, ss, vs = [], [], []
    t0, z0 = 0.0, [start * L, float(initial_speed)]
    for _ in range(200):
        remaining = t_eval[t_eval >= t0 - 1e-12]
        if len(remaining) == 0:
            break
        sol = solve_ivp(rhs, (t0, duration), z0, t_eval=remaining, events=[hit_start, hit_end],
                        method="DOP853", rtol=1e-9, atol=1e-9)
        ts += sol.t.tolist(); ss += sol.y[0].tolist(); vs += sol.y[1].tolist()
        if sol.status != 1:
            break
        # Hit an end: stop there. If gravity pulls it back onto the track it slides back, otherwise it rests.
        t0 = float(sol.t_events[0][0] if len(sol.t_events[0]) else sol.t_events[1][0])
        at_end = len(sol.t_events[1]) > 0
        s_end = L * (1 - 1e-9) if at_end else L * 1e-9
        pull = -gravity * math.sin(phi(s_end))
        if (at_end and pull >= 0) or (not at_end and pull <= 0):
            rest = t_eval[t_eval > t0]
            ts += rest.tolist(); ss += [s_end] * len(rest); vs += [0.0] * len(rest)
            break
        z0 = [s_end, 0.0]
    ts, ss, vs = map(np.array, (ts, ss, vs))
    x, y = np.interp(ss, S, tr["x"]), np.interp(ss, S, tr["y"])
    kinetic, potential = 0.5 * mass * vs**2, mass * gravity * y
    e0 = kinetic[0] + potential[0]
    thermal = np.maximum(0.0, e0 - kinetic - potential)
    normal = mass * np.maximum(0.0, gravity * np.cos(np.interp(ss, S, tr["phi"])) + np.interp(ss, S, tr["kappa"]) * vs**2)
    step = max(1, len(S) // 400)
    return {
        "result": {
            "max_speed": float(np.max(np.abs(vs))),
            "track_length": L,
            "total_energy": float(e0),
            "energy_dissipated": float(thermal[-1]),
        },
        "trajectory": {"t": ts.tolist(), "x": x.tolist(), "y": y.tolist(), "speed": np.abs(vs).tolist(),
                       "kinetic": kinetic.tolist(), "potential": potential.tolist(), "thermal": thermal.tolist(),
                       "normal_force": normal.tolist()},
        "track": {"x": tr["x"][::step].tolist(), "y": tr["y"][::step].tolist()},
        "units": "positions m, speed m/s, energy J (potential relative to y = 0), force N, time s",
        "assumptions": [
            "Point-mass skater that stays on the track (does not fly off)",
            "Kinetic friction = mu x normal force (including the centripetal part); no air drag",
            "Track is a natural cubic spline through the control points",
        ],
    }
