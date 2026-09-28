"""Numerical orbit propagation: two-body and gravitational n-body (scipy solve_ivp)."""
import math
from typing import Any

import numpy as np
from scipy.integrate import solve_ivp

from app.core.registry import tool
from app.modules.physics.bodies import (
    BODIES, EARTH_MASS, EARTH_MOON_DISTANCE, G, MOON_MASS, get_body, resolve_mu,
)
from app.modules.physics.elements import _vector3

MAX_POINTS = 10_000
MAX_BODIES = 20
_RTOL, _ATOL = 1e-11, 1e-6


def _check_timing(duration: float, n_points: int) -> None:
    if not duration > 0:
        raise ValueError("duration must be positive (seconds)")
    if not 2 <= n_points <= MAX_POINTS:
        raise ValueError(f"n_points must be between 2 and {MAX_POINTS}")


@tool(
    domain="physics",
    name="propagate_two_body",
    description=(
        "Propagate a spacecraft around one central body from an initial position (m) and velocity (m/s) for "
        "duration seconds. Returns plot-ready trajectory arrays (t, x, y, z, vx, vy, vz) and the final state; "
        "stops early if the orbit hits the body's surface. Example: position=[6778000,0,0], "
        "velocity=[0,7669,0], duration=5554, body='earth'."
    ),
)
def propagate_two_body(
    position: list[float],
    velocity: list[float],
    duration: float,
    n_points: int = 361,
    body: str = "earth",
    mu: float | None = None,
) -> dict:
    _check_timing(duration, n_points)
    gm = resolve_mu(body, mu)
    r0, v0 = _vector3(position, "position"), _vector3(velocity, "velocity")
    surface = get_body(body).radius if mu is None else 0.0
    if np.linalg.norm(r0) <= surface:
        raise ValueError("Initial position is inside the central body")

    def rhs(_t, s):
        r = s[:3]
        return np.concatenate([s[3:], -gm * r / np.linalg.norm(r) ** 3])

    def impact(_t, s):
        return np.linalg.norm(s[:3]) - surface
    impact.terminal, impact.direction = True, -1

    t_eval = np.linspace(0.0, duration, n_points)
    sol = solve_ivp(rhs, (0.0, duration), np.concatenate([r0, v0]), method="DOP853", t_eval=t_eval,
                    rtol=_RTOL, atol=_ATOL, events=impact if surface > 0 else None)
    if sol.status == -1:
        raise ValueError(f"Propagation failed: {sol.message}")
    impacted = sol.status == 1

    def energy(s):
        return float(np.dot(s[3:], s[3:]) / 2 - gm / np.linalg.norm(s[:3]))
    e0 = energy(np.concatenate([r0, v0]))
    final = sol.y_events[0][0] if impacted else sol.y[:, -1]
    t_final = float(sol.t_events[0][0]) if impacted else float(sol.t[-1])

    return {
        "result": {
            "final_position": final[:3].tolist(),
            "final_velocity": final[3:].tolist(),
            "final_time": t_final,
            "impact": impacted,
        },
        "trajectory": {
            "t": sol.t.tolist(),
            **{k: sol.y[i].tolist() for i, k in enumerate(("x", "y", "z", "vx", "vy", "vz"))},
        },
        "relative_energy_drift": abs((energy(final) - e0) / e0),
        "units": "positions in m, velocities in m/s, time in s",
        "assumptions": [
            "Two-body point-mass gravity; no drag, J2 or third bodies",
            f"Numerical integration: DOP853, rtol={_RTOL}",
            *([f"Trajectory hit the surface at t = {t_final:.1f} s; propagation stopped"] if impacted else []),
        ],
    }


def _earth_moon_system() -> list[dict[str, Any]]:
    """Earth and Moon on a circular mutual orbit in the xy-plane, barycentre at rest at the origin."""
    m_total = EARTH_MASS + MOON_MASS
    d = EARTH_MOON_DISTANCE
    omega = math.sqrt(G * m_total / d**3)
    r_e, r_m = d * MOON_MASS / m_total, d * EARTH_MASS / m_total
    return [
        {"name": "Earth", "mass": EARTH_MASS, "radius": BODIES["earth"].radius,
         "position": [-r_e, 0.0, 0.0], "velocity": [0.0, -omega * r_e, 0.0]},
        {"name": "Moon", "mass": MOON_MASS, "radius": BODIES["moon"].radius,
         "position": [r_m, 0.0, 0.0], "velocity": [0.0, omega * r_m, 0.0]},
    ]


@tool(
    domain="physics",
    name="propagate_n_body",
    description=(
        "Simulate mutual Newtonian gravity between several bodies. bodies: list of {name, mass (kg), "
        "position [m], velocity [m/s], optional radius (m) for collision detection}; mass 0 = test particle "
        "(e.g. a spacecraft). preset='earth_moon' adds Earth and Moon (barycentric, circular orbit in the xy-plane) "
        "and then extra bodies' position/velocity are taken RELATIVE TO EARTH. Returns plot-ready trajectories. "
        "Example: preset='earth_moon', bodies=[{name:'sc', mass:0, position:[6678000,0,0], velocity:[0,10900,0]}], "
        "duration=432000."
    ),
)
def propagate_n_body(
    duration: float,
    bodies: list[dict[str, Any]] | None = None,
    preset: str | None = None,
    n_points: int = 501,
) -> dict:
    _check_timing(duration, n_points)
    extra = list(bodies or [])
    if preset is None:
        system = []
    elif preset == "earth_moon":
        system = _earth_moon_system()
    else:
        raise ValueError("preset must be None or 'earth_moon'")

    frame_offset = (np.array(system[0]["position"]), np.array(system[0]["velocity"])) if system else None
    for b in extra:
        missing = {"name", "mass", "position", "velocity"} - set(b)
        if missing:
            raise ValueError(f"Body {b.get('name', b)!r} is missing {sorted(missing)}")
        pos, vel = _vector3(b["position"], "position"), _vector3(b["velocity"], "velocity")
        if frame_offset is not None:
            pos, vel = pos + frame_offset[0], vel + frame_offset[1]
        system.append({**b, "position": pos.tolist(), "velocity": vel.tolist()})

    if not 2 <= len(system) <= MAX_BODIES:
        raise ValueError(f"Need between 2 and {MAX_BODIES} bodies in total")
    names = [str(b["name"]) for b in system]
    if len(set(names)) != len(names):
        raise ValueError("Body names must be unique")
    mass = np.array([float(b["mass"]) for b in system])
    if np.any(mass < 0) or mass.sum() == 0:
        raise ValueError("Masses must be >= 0 and at least one body must have mass")
    radius = np.array([float(b.get("radius") or 0.0) for b in system])
    n = len(system)
    y0 = np.concatenate([np.ravel([b["position"] for b in system]), np.ravel([b["velocity"] for b in system])])
    iu = np.triu_indices(n, 1)

    def accelerations(pos):
        diff = pos[None, :, :] - pos[:, None, :]          # diff[i, j] = r_j - r_i
        dist = np.linalg.norm(diff, axis=-1)
        np.fill_diagonal(dist, np.inf)
        return G * np.einsum("j,ijk->ik", mass, diff / dist[..., None] ** 3)

    def rhs(_t, s):
        pos = s[: 3 * n].reshape(n, 3)
        return np.concatenate([s[3 * n:], accelerations(pos).ravel()])

    def collision(_t, s):
        pos = s[: 3 * n].reshape(n, 3)
        dist = np.linalg.norm(pos[:, None, :] - pos[None, :, :], axis=-1)
        return float(np.min(dist[iu] - (radius[:, None] + radius[None, :])[iu]))
    collision.terminal, collision.direction = True, -1

    if collision(0, y0) <= 0:
        raise ValueError("Bodies overlap at t = 0")

    def total_energy(s):
        pos, vel = s[: 3 * n].reshape(n, 3), s[3 * n:].reshape(n, 3)
        kinetic = 0.5 * np.sum(mass * np.sum(vel**2, axis=1))
        dist = np.linalg.norm(pos[:, None, :] - pos[None, :, :], axis=-1)[iu]
        return kinetic - G * np.sum((mass[:, None] * mass[None, :])[iu] / dist)

    t_eval = np.linspace(0.0, duration, n_points)
    sol = solve_ivp(rhs, (0.0, duration), y0, method="DOP853", t_eval=t_eval,
                    rtol=_RTOL, atol=_ATOL, events=collision)
    if sol.status == -1:
        raise ValueError(f"Propagation failed: {sol.message}")
    collided = sol.status == 1
    final = sol.y_events[0][0] if collided else sol.y[:, -1]
    e0 = total_energy(y0)

    trajectories = {
        name: {axis: sol.y[3 * k + a].tolist() for a, axis in enumerate("xyz")} for k, name in enumerate(names)
    }
    final_state = {
        name: {"position": final[3 * k: 3 * k + 3].tolist(),
               "velocity": final[3 * (n + k): 3 * (n + k) + 3].tolist()}
        for k, name in enumerate(names)
    }
    return {
        "result": {
            "final_state": final_state,
            "final_time": float(sol.t_events[0][0]) if collided else float(sol.t[-1]),
            "collision": collided,
        },
        "trajectory": {"t": sol.t.tolist(), "bodies": trajectories},
        "relative_energy_drift": abs((total_energy(final) - e0) / e0) if e0 != 0 else None,
        "units": "positions in m, velocities in m/s, time in s, masses in kg",
        "assumptions": [
            "Newtonian point-mass gravity between all bodies; no relativity, drag or non-spherical gravity",
            "Output frame: barycentric (Earth-Moon barycentre)" if preset == "earth_moon"
            else "Output frame: the inertial frame the inputs were given in",
            f"Numerical integration: DOP853, rtol={_RTOL}",
            *(["A collision (bodies touching, using given radii) stopped the run early"] if collided else []),
        ],
    }
