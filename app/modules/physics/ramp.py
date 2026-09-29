"""Block on an inclined plane with static/kinetic friction and an applied force (piecewise-exact motion)."""
import math

import numpy as np

from app.core.registry import tool

G0 = 9.80665


@tool(
    domain="physics",
    name="ramp_motion",
    description=(
        "Block of mass m on a ramp inclined at angle_deg, with static/kinetic friction coefficients and an "
        "applied force along the ramp (positive = up the ramp). position is distance up the ramp from the bottom "
        "(0..length). Returns the force breakdown, whether the block moves, and plot-ready position/velocity/"
        "energy vs time (friction reverses and static friction can hold the block when it stops). "
        "Example: mass=10, angle_deg=30, mu_static=0.5, mu_kinetic=0.3, applied_force=0, position=4, length=5."
    ),
)
def ramp_motion(
    mass: float,
    angle_deg: float,
    mu_static: float = 0.0,
    mu_kinetic: float = 0.0,
    applied_force: float = 0.0,
    position: float = 2.0,
    velocity: float = 0.0,
    length: float = 5.0,
    gravity: float = G0,
    duration: float = 5.0,
    n_points: int = 501,
) -> dict:
    if mass <= 0 or gravity <= 0 or length <= 0 or duration <= 0:
        raise ValueError("mass, gravity, length and duration must be positive")
    if not 0 <= angle_deg <= 85:
        raise ValueError("angle_deg must be between 0 and 85")
    if mu_static < 0 or mu_kinetic < 0:
        raise ValueError("Friction coefficients must be >= 0")
    if mu_kinetic > mu_static:
        raise ValueError("mu_kinetic must not exceed mu_static")
    if not 0 <= position <= length:
        raise ValueError("position must be between 0 and length")
    if not 2 <= n_points <= 10_000:
        raise ValueError("n_points must be between 2 and 10000")

    th = math.radians(angle_deg)
    g_par = mass * gravity * math.sin(th)          # gravity component down the ramp
    normal = mass * gravity * math.cos(th)
    drive = applied_force - g_par                  # net force up the ramp before friction
    f_s_max, f_k = mu_static * normal, mu_kinetic * normal

    def accel(v: float) -> tuple[float, float]:
        """Acceleration and friction force (signed, up-ramp positive) given velocity."""
        if abs(v) > 1e-12:
            fr = -math.copysign(f_k, v)
            return (drive + fr) / mass, fr
        if abs(drive) <= f_s_max:
            return 0.0, -drive
        fr = -math.copysign(f_k, drive)
        return (drive + fr) / mass, fr

    # Piecewise-constant acceleration: segment ends when v hits 0 or the block reaches an end of the ramp.
    t_grid = np.linspace(0, duration, n_points)
    segs = []                                       # (t0, x0, v0, a)
    t, x, v = 0.0, float(position), float(velocity)
    stopped_at_end = None
    for _ in range(1000):
        a, _ = accel(v)
        if (x <= 0 and (v < 0 or (v == 0 and a < 0))) or (x >= length and (v > 0 or (v == 0 and a > 0))):
            stopped_at_end = "bottom" if x <= 0 else "top"
            segs.append((t, x, 0.0, 0.0))
            break
        segs.append((t, x, v, a))
        candidates = []
        if v != 0 and a != 0 and v * a < 0:
            candidates.append(-v / a)
        for edge in (0.0, length):
            # x + v tau + a tau^2 / 2 = edge
            A, B, C = a / 2, v, x - edge
            if abs(A) < 1e-15:
                if B != 0:
                    candidates.append(-C / B)
            else:
                disc = B * B - 4 * A * C
                if disc >= 0:
                    s = math.sqrt(disc)
                    candidates += [(-B - s) / (2 * A), (-B + s) / (2 * A)]
        candidates = [c for c in candidates if c > 1e-12]
        if not candidates or t + min(candidates) >= duration:
            break
        tau = min(candidates)
        x = min(length, max(0.0, x + v * tau + a * tau * tau / 2))
        v = v + a * tau
        if abs(v) < 1e-9:
            v = 0.0
        t += tau
        if x in (0.0, length) and v != 0:
            v = 0.0                                  # hits the stop at the end of the ramp
    seg_t = np.array([s[0] for s in segs])
    idx = np.searchsorted(seg_t, t_grid, side="right") - 1
    t0, x0, v0, a0 = (np.array([segs[i][k] for i in idx]) for k in range(4))
    dt = t_grid - t0
    xs = np.clip(x0 + v0 * dt + 0.5 * a0 * dt**2, 0, length)
    vs = v0 + a0 * dt

    a_init, f_init = accel(float(velocity))
    height = xs * math.sin(th)
    kinetic = 0.5 * mass * vs**2
    potential = mass * gravity * height
    applied_work = applied_force * (xs - position)
    thermal = 0.5 * mass * velocity**2 + mass * gravity * position * math.sin(th) + applied_work - kinetic - potential
    return {
        "result": {
            "moves": not (velocity == 0 and a_init == 0),
            "initial_acceleration": a_init,
            "tan_angle": math.tan(th),
            "angle_of_repose_deg": math.degrees(math.atan(mu_static)),
            "stopped_at_end": stopped_at_end,
        },
        "forces": {
            "gravity_along_ramp": -g_par, "normal": normal, "applied": applied_force,
            "friction": f_init, "net": mass * a_init, "max_static_friction": f_s_max, "kinetic_friction": f_k,
        },
        "trajectory": {"t": t_grid.tolist(), "position": xs.tolist(), "velocity": vs.tolist(),
                       "kinetic": kinetic.tolist(), "potential": potential.tolist(),
                       "thermal": np.maximum(thermal, 0).tolist(), "applied_work": applied_work.tolist()},
        "units": "forces N (up the ramp positive), position m along the ramp, velocity m/s, acceleration m/s^2, energy J",
        "assumptions": [
            "Rigid block sliding without rotation; Coulomb friction (static up to mu_s N, kinetic mu_k N)",
            "Constant applied force parallel to the ramp; the block stops at either end of the ramp",
        ],
    }
