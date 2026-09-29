"""Rotational dynamics: shapes rolling down an incline (moment of inertia decides the race),
with the rolling-without-slipping friction limit."""
import math

import numpy as np

from app.core.registry import tool

G0 = 9.80665
# I = k m R² for common shapes about their symmetry axis
SHAPES = {
    "solid_sphere": 2 / 5, "hollow_sphere": 2 / 3, "solid_cylinder": 1 / 2, "hoop": 1.0,
    "thick_ring": None, "frictionless_block": 0.0,
}


@tool(
    domain="physics",
    name="rolling_race",
    description=(
        "Race objects down an incline: each shape (solid_sphere, hollow_sphere, solid_cylinder, hoop, "
        "thick_ring with inner_ratio, frictionless_block) rolls without slipping if friction allows, else it "
        "slides while spinning up. Returns acceleration, time, final speed and the translational/rotational energy "
        "split, plus trajectories. angle_deg, length (m), friction coefficient mu, radius (m) for spin rates. "
        "Example: shapes=['solid_sphere','hoop'], angle_deg=20, length=3."
    ),
)
def rolling_race(
    shapes: list[str],
    angle_deg: float = 20.0,
    length: float = 3.0,
    mu: float = 1.0,
    radius: float = 0.1,
    inner_ratio: float = 0.6,
    gravity: float = G0,
    n_points: int = 200,
) -> dict:
    if not shapes or len(shapes) > 6:
        raise ValueError("give 1 to 6 shapes")
    if not 0 < angle_deg < 90:
        raise ValueError("angle_deg must be between 0 and 90")
    if length <= 0 or radius <= 0 or gravity <= 0 or mu < 0:
        raise ValueError("length, radius and gravity must be positive and mu >= 0")
    if not 0 <= inner_ratio < 1:
        raise ValueError("inner_ratio must be in [0, 1)")
    if not 2 <= n_points <= 5000:
        raise ValueError("n_points must be between 2 and 5000")
    th = math.radians(angle_deg)
    s, c = math.sin(th), math.cos(th)
    racers = []
    for name in shapes:
        if name not in SHAPES:
            raise ValueError(f"unknown shape {name!r}; choose from {', '.join(SHAPES)}")
        k = SHAPES[name] if name != "thick_ring" else (1 + inner_ratio**2) / 2
        if name == "frictionless_block":
            a, alpha, rolling, mu_needed = gravity * s, 0.0, False, 0.0
        else:
            mu_needed = k * math.tan(th) / (1 + k)  # static friction needed to roll without slipping
            if mu >= mu_needed:
                a, rolling = gravity * s / (1 + k), True
                alpha = a / radius
            else:  # slips: kinetic friction μ m g cos θ both slows the centre and spins the body
                a, rolling = gravity * (s - mu * c), False
                alpha = mu * gravity * c / (k * radius)
        t_end = math.sqrt(2 * length / a)
        v = a * t_end
        omega = alpha * t_end
        # Energies per kg of mass (so shapes of any mass compare): translational, rotational, friction loss
        e_trans = 0.5 * v * v
        e_rot = 0.5 * k * radius**2 * omega**2
        drop = gravity * length * s
        t = np.linspace(0, t_end, n_points)
        racers.append({
            "shape": name, "inertia_factor": k, "rolling": rolling, "acceleration": a, "time": t_end,
            "final_speed": v, "final_spin": omega, "friction_needed": mu_needed,
            "energy_fraction_translational": e_trans / drop, "energy_fraction_rotational": e_rot / drop,
            "energy_fraction_lost": max(0.0, 1 - (e_trans + e_rot) / drop),
            "trajectory": {"t": t.tolist(), "distance": (0.5 * a * t**2).tolist(), "angle_rad": (0.5 * alpha * t**2).tolist()},
        })
    order = sorted(racers, key=lambda r: r["time"])
    return {
        "result": {
            "winner": order[0]["shape"],
            "finish_order": [r["shape"] for r in order],
            "racers": racers,
            "height_drop": length * s,
        },
        "units": "SI: m, s, m/s, m/s², rad/s; energy fractions of m g h",
        "assumptions": ["Uniform rigid bodies, I = k m R²; rolling without slipping when μ ≥ k tan θ/(1 + k)",
                        "No rolling resistance or air drag; mass cancels out of the race",
                        "Slipping bodies: kinetic friction μ m g cos θ, which dissipates energy"],
    }
