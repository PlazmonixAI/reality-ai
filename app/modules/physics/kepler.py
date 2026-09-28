"""Kepler's laws: an elliptical orbit solved from Kepler's equation, equal areas in equal times, and
the T² ∝ a³ law."""
import math

import numpy as np

from app.core.registry import tool

GM_SUN = 1.32712440018e20  # m³/s²
AU = 1.495978707e11  # m
YEAR = 365.25 * 86400


def solve_kepler(mean_anomaly: np.ndarray, e: float) -> np.ndarray:
    """Eccentric anomaly E from M = E − e sin E (Newton's method, vectorised)."""
    mean_anomaly = np.asarray(mean_anomaly, float)
    big = mean_anomaly + e * np.sin(mean_anomaly) if e < 0.8 else np.full_like(mean_anomaly, math.pi)
    for _ in range(50):
        f = big - e * np.sin(big) - mean_anomaly
        step = f / (1 - e * np.cos(big))
        big = big - step
        if np.max(np.abs(step)) < 1e-14:
            break
    return big


@tool(
    domain="physics",
    name="kepler_orbit",
    description=(
        "An orbit around a star from Kepler's laws: semi_major_axis_au and eccentricity (0 ≤ e < 1), star mass in "
        "solar masses. Solves Kepler's equation for position vs time, gives the period (T² = 4π² a³/GM), perihelion/"
        "aphelion distances and speeds (vis-viva), and the areas swept in equal time slices (Kepler's 2nd law). "
        "Example: semi_major_axis_au=1, eccentricity=0.0167 (Earth)."
    ),
)
def kepler_orbit(semi_major_axis_au: float, eccentricity: float, star_mass_solar: float = 1.0,
                 n_points: int = 721, n_sectors: int = 12) -> dict:
    if semi_major_axis_au <= 0 or star_mass_solar <= 0:
        raise ValueError("semi_major_axis_au and star_mass_solar must be positive")
    if not 0 <= eccentricity < 1:
        raise ValueError("eccentricity must be in [0, 1) for a closed orbit")
    if not 10 <= n_points <= 20000 or not 2 <= n_sectors <= 72:
        raise ValueError("n_points must be 10..20000 and n_sectors 2..72")
    a, e, gm = semi_major_axis_au * AU, eccentricity, GM_SUN * star_mass_solar
    period = 2 * math.pi * math.sqrt(a**3 / gm)
    b = a * math.sqrt(1 - e * e)
    t = np.linspace(0, period, n_points)
    mean = 2 * math.pi * t / period
    ecc = solve_kepler(mean, e)
    x = a * (np.cos(ecc) - e)  # star at the origin (a focus)
    y = b * np.sin(ecc)
    r = np.hypot(x, y)
    speed = np.sqrt(gm * (2 / r - 1 / a))
    # Kepler's 2nd law: area swept in each of n_sectors equal time slices (exact: ½ a b (ΔE − e Δ sin E))
    tk = np.linspace(0, period, n_sectors + 1)
    ek = solve_kepler(2 * math.pi * tk / period, e)
    ek[-1] = 2 * math.pi
    areas = 0.5 * a * b * (np.diff(ek) - e * np.diff(np.sin(ek)))
    return {
        "result": {
            "period_s": period,
            "period_years": period / YEAR,
            "semi_minor_axis_au": b / AU,
            "perihelion_au": a * (1 - e) / AU,
            "aphelion_au": a * (1 + e) / AU,
            "perihelion_speed": math.sqrt(gm * (1 + e) / (a * (1 - e))),
            "aphelion_speed": math.sqrt(gm * (1 - e) / (a * (1 + e))),
            "mean_speed": 2 * math.pi * a / period,
            "sector_areas_au2": (areas / AU**2).tolist(),
            "t2_over_a3": (period / YEAR) ** 2 / semi_major_axis_au**3,
            "specific_energy": -gm / (2 * a),
            "specific_angular_momentum": math.sqrt(gm * a * (1 - e * e)),
        },
        "orbit": {"t_years": (t / YEAR).tolist(), "x_au": (x / AU).tolist(), "y_au": (y / AU).tolist(),
                  "r_au": (r / AU).tolist(), "speed_km_s": (speed / 1000).tolist()},
        "sector_times_years": (tk / YEAR).tolist(),
        "units": "distances in AU (and m), times in years (and s), speeds in m/s (orbit speeds in km/s)",
        "assumptions": ["Two-body problem with the planet's mass negligible next to the star's",
                        "GM_sun = 1.32712440018e20 m³/s², 1 AU = 1.495978707e11 m, 1 year = 365.25 days"],
    }
