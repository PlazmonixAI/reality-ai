"""Charged particle in uniform electric and magnetic fields (Lorentz force): cyclotron motion,
helices and E×B drift."""
import math

import numpy as np
from scipy.integrate import solve_ivp

from app.core.registry import tool

QE = 1.602176634e-19  # C
ME = 9.1093837015e-31  # kg
MP = 1.67262192369e-27  # kg
PARTICLES = {"electron": (-QE, ME), "proton": (QE, MP), "positron": (QE, ME), "alpha": (2 * QE, 6.6446573357e-27)}


def _vec(v, name):
    a = np.asarray(v, float)
    if a.shape != (3,):
        raise ValueError(f"{name} must be a 3-vector [x, y, z]")
    return a


@tool(
    domain="physics",
    name="charged_particle",
    description=(
        "Motion of a charged particle in uniform fields, m dv/dt = q (E + v × B) (non-relativistic). Give particle "
        "('electron', 'proton', 'positron', 'alpha') or charge (C) and mass (kg); electric_field (V/m) and "
        "magnetic_field (T) as 3-vectors; velocity (m/s). Returns cyclotron frequency, Larmor radius, pitch, "
        "E×B drift velocity and the trajectory. Example: particle='proton', magnetic_field=[0,0,1], velocity=[1e5,0,0]."
    ),
)
def charged_particle(
    velocity: list[float],
    magnetic_field: list[float] = (0.0, 0.0, 0.0),
    electric_field: list[float] = (0.0, 0.0, 0.0),
    particle: str | None = "proton",
    charge: float | None = None,
    mass: float | None = None,
    position: list[float] = (0.0, 0.0, 0.0),
    duration: float | None = None,
    n_points: int = 1500,
) -> dict:
    if charge is not None or mass is not None:
        if charge is None or mass is None:
            raise ValueError("give both charge and mass (or a particle name)")
        q, m = charge, mass
    else:
        if particle not in PARTICLES:
            raise ValueError(f"unknown particle {particle!r}; choose from {', '.join(PARTICLES)}")
        q, m = PARTICLES[particle]
    if m <= 0:
        raise ValueError("mass must be positive")
    if not 2 <= n_points <= 20_000:
        raise ValueError("n_points must be between 2 and 20000")
    v0, b, e, r0 = _vec(velocity, "velocity"), _vec(magnetic_field, "magnetic_field"), _vec(electric_field, "electric_field"), _vec(position, "position")
    speed = float(np.linalg.norm(v0))
    if speed >= 0.1 * 299792458:
        raise ValueError("speed must be below 0.1 c for this non-relativistic model")
    bmag = float(np.linalg.norm(b))
    wc = abs(q) * bmag / m
    bhat = b / bmag if bmag > 0 else None
    drift = np.cross(e, b) / bmag**2 if bmag > 0 else np.zeros(3)
    if bhat is not None:
        v_par = float(v0 @ bhat)
        v_perp_vec = v0 - v_par * bhat - drift  # gyration relative to the drifting guiding centre
        v_perp = float(np.linalg.norm(v_perp_vec))
        radius = m * v_perp / (abs(q) * bmag) if q != 0 else math.inf
        period = 2 * math.pi / wc if wc > 0 else None
        pitch = v_par * period if period else None
        e_par = float(e @ bhat)
    else:
        v_par = v_perp = radius = period = pitch = None
        e_par = float(np.linalg.norm(e))
    if duration is None:
        duration = 3 * period if period else 1e-6
    if duration <= 0:
        raise ValueError("duration must be positive")

    qm = q / m

    def rhs(_t, s):
        v = s[3:]
        return np.concatenate([v, qm * (e + np.cross(v, b))])

    t = np.linspace(0, duration, n_points)
    max_step = period / 60 if period else np.inf
    sol = solve_ivp(rhs, (0, duration), np.concatenate([r0, v0]), t_eval=t, method="DOP853", rtol=1e-10,
                    atol=1e-14 * max(1.0, speed * duration), max_step=max_step)
    if not sol.success:
        raise ValueError(f"Integration failed: {sol.message}")
    r, v = sol.y[:3], sol.y[3:]
    ke = 0.5 * m * np.sum(v**2, axis=0)
    return {
        "result": {
            "charge": q,
            "mass": m,
            "cyclotron_frequency": wc,
            "cyclotron_frequency_hz": wc / (2 * math.pi),
            "period": period,
            "larmor_radius": radius,
            "parallel_speed": v_par,
            "perpendicular_speed": v_perp,
            "pitch": pitch,
            "drift_velocity": drift.tolist(),
            "drift_speed": float(np.linalg.norm(drift)),
            "parallel_electric_field": e_par,
            "final_speed": float(np.linalg.norm(v[:, -1])),
            "kinetic_energy_change": float(ke[-1] - ke[0]),
            "initial_kinetic_energy_ev": float(ke[0] / QE),
        },
        "trajectory": {"t": t.tolist(), "x": r[0].tolist(), "y": r[1].tolist(), "z": r[2].tolist(),
                       "speed": np.linalg.norm(v, axis=0).tolist(), "kinetic_energy_ev": (ke / QE).tolist()},
        "units": "SI: m, s, m/s, T, V/m, rad/s; energies in eV",
        "assumptions": ["Uniform static fields", "Non-relativistic (v < 0.1 c), no radiation losses",
                        "Drift E×B/B² is exact for E ⊥ B with |E| < c|B|"],
    }
