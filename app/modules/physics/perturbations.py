"""Orbital perturbations: J2 (oblateness) precession of the node and perigee, sun-synchronous orbits,
and atmospheric drag decay of low orbits."""
import math

import numpy as np
from scipy.integrate import solve_ivp

from app.core.registry import tool
from app.modules.physics.bodies import get_body

# Second zonal harmonic J2 (dimensionless), referenced to the body's equatorial radius in bodies.py.
J2 = {"earth": 1.08262668e-3, "mars": 1.96045e-3, "moon": 2.0330e-4, "venus": 4.458e-6, "jupiter": 1.4736e-2, "saturn": 1.6298e-2}
DAY = 86400.0
TROPICAL_YEAR = 365.2422 * DAY

# Exponential atmosphere above 100 km (base altitude km, base density kg/m³, scale height km),
# after the widely used static model in Vallado, "Fundamentals of Astrodynamics", table 8-4.
ATMOSPHERE = [
    (100, 5.297e-7, 5.877), (110, 9.661e-8, 7.263), (120, 2.438e-8, 9.473), (130, 8.484e-9, 12.636),
    (140, 3.845e-9, 16.149), (150, 2.070e-9, 22.523), (180, 5.464e-10, 29.740), (200, 2.789e-10, 37.105),
    (250, 7.248e-11, 45.546), (300, 2.418e-11, 53.628), (350, 9.518e-12, 53.298), (400, 3.725e-12, 58.515),
    (450, 1.585e-12, 60.828), (500, 6.967e-13, 63.822), (600, 1.454e-13, 71.835), (700, 3.614e-14, 88.667),
    (800, 1.170e-14, 124.64), (900, 5.245e-15, 181.05), (1000, 3.019e-15, 268.00),
]


def density(alt_km: float) -> float:
    """Static exponential-atmosphere density (kg/m³) at an altitude of 100–1500 km."""
    if alt_km < 100:
        alt_km = 100.0
    base = ATMOSPHERE[0]
    for row in ATMOSPHERE:
        if alt_km >= row[0]:
            base = row
    h0, rho0, scale = base
    return rho0 * math.exp(-(alt_km - h0) / scale)


def _j2(body: str) -> float:
    key = body.strip().lower()
    if key not in J2:
        raise ValueError(f"no J2 value for {body!r}; choose from {', '.join(J2)}")
    return J2[key]


def secular_rates(a: float, e: float, i: float, mu: float, r_eq: float, j2: float) -> tuple[float, float]:
    """Mean-element J2 rates (rad/s) of the right ascension of the ascending node and argument of perigee."""
    n = math.sqrt(mu / a**3)
    p = a * (1 - e * e)
    k = n * j2 * (r_eq / p) ** 2
    return -1.5 * k * math.cos(i), 0.75 * k * (5 * math.cos(i) ** 2 - 1)


@tool(
    domain="physics",
    name="j2_precession",
    description=(
        "Oblateness (J2) perturbation of an orbit: secular drift rates of the ascending node (RAAN) and argument of "
        "perigee, the sun-synchronous inclination for this orbit size, and (propagate=True) a numerical two-body + J2 "
        "propagation that confirms the drift. perigee_alt/apogee_alt in m above the surface, inclination in degrees. "
        "Example: perigee_alt=400e3, apogee_alt=400e3, inclination_deg=51.6 (ISS: node drifts ≈ −5°/day)."
    ),
)
def j2_precession(
    perigee_alt: float,
    apogee_alt: float | None = None,
    inclination_deg: float = 51.6,
    body: str = "earth",
    duration_days: float = 3.0,
    propagate: bool = True,
    n_points: int = 200,
) -> dict:
    b = get_body(body)
    j2 = _j2(body)
    apogee_alt = perigee_alt if apogee_alt is None else apogee_alt
    if perigee_alt <= 0 or apogee_alt < perigee_alt:
        raise ValueError("need 0 < perigee_alt ≤ apogee_alt (m above the surface)")
    if not 0 <= inclination_deg <= 180:
        raise ValueError("inclination_deg must be between 0 and 180")
    if not 0 < duration_days <= 60 or not 10 <= n_points <= 5000:
        raise ValueError("duration_days must be in (0, 60] and n_points in 10..5000")
    rp, ra = b.radius + perigee_alt, b.radius + apogee_alt
    a, e = (rp + ra) / 2, (ra - rp) / (ra + rp)
    inc = math.radians(inclination_deg)
    raan_dot, argp_dot = secular_rates(a, e, inc, b.mu, b.radius, j2)
    period = 2 * math.pi * math.sqrt(a**3 / b.mu)
    # Sun-synchronous: node must turn 360° per tropical year (Earth only makes sense, but computed for any body)
    target = 2 * math.pi / TROPICAL_YEAR
    n = math.sqrt(b.mu / a**3)
    cos_ss = -target / (1.5 * n * j2 * (b.radius / (a * (1 - e * e))) ** 2)
    sun_sync = math.degrees(math.acos(cos_ss)) if -1 <= cos_ss <= 1 else None
    out = {
        "raan_rate_deg_per_day": math.degrees(raan_dot) * DAY,
        "perigee_rate_deg_per_day": math.degrees(argp_dot) * DAY,
        "period_minutes": period / 60,
        "semi_major_axis": a,
        "eccentricity": e,
        "sun_synchronous_inclination_deg": sun_sync,
        "critical_inclinations_deg": [math.degrees(math.acos(math.sqrt(1 / 5))), math.degrees(math.acos(-math.sqrt(1 / 5)))],
    }
    trace = None
    if propagate:
        mu, re_ = b.mu, b.radius

        def rhs(_t, s):
            x, y, z = s[:3]
            r2 = x * x + y * y + z * z
            r = math.sqrt(r2)
            f = 1.5 * j2 * mu * re_**2 / r**5
            zz = 5 * z * z / r2
            ax = -mu * x / r**3 + f * x * (zz - 1)
            ay = -mu * y / r**3 + f * y * (zz - 1)
            az = -mu * z / r**3 + f * z * (zz - 3)
            return [s[3], s[4], s[5], ax, ay, az]

        # Start at perigee on the ascending node (RAAN = 0, argument of perigee = 0)
        v = math.sqrt(mu * (2 / rp - 1 / a))
        s0 = [rp, 0, 0, 0, v * math.cos(inc), v * math.sin(inc)]
        t_end = duration_days * DAY
        t = np.linspace(0, t_end, n_points)
        sol = solve_ivp(rhs, (0, t_end), s0, t_eval=t, method="DOP853", rtol=1e-11, atol=1e-6)
        if not sol.success:
            raise ValueError(f"propagation failed: {sol.message}")
        rvec, vvec = sol.y[:3], sol.y[3:]
        h = np.cross(rvec.T, vvec.T)
        raan = np.unwrap(np.arctan2(h[:, 0], -h[:, 1]))
        incl = np.degrees(np.arccos(h[:, 2] / np.linalg.norm(h, axis=1)))
        # Osculating RAAN wiggles twice per orbit; fit a line for the secular rate
        slope = np.polyfit(t, raan, 1)[0]
        out["raan_rate_numerical_deg_per_day"] = math.degrees(slope) * DAY
        trace = {"t_days": (t / DAY).tolist(), "raan_deg": np.degrees(raan).tolist(), "inclination_deg": incl.tolist(),
                 "raan_analytic_deg": (math.degrees(raan_dot) * t).tolist()}
    return {
        "result": out,
        "trace": trace,
        "units": "rates in degrees per day, angles in degrees, lengths in m",
        "assumptions": [f"Only the J2 zonal harmonic of {b.name} (J2 = {j2}) plus point-mass gravity",
                        "Analytic rates are first-order secular (mean-element) theory; the numerical run is osculating",
                        "Sun-synchronous condition: node advances 360° per tropical year"],
    }


@tool(
    domain="physics",
    name="orbital_decay",
    description=(
        "Atmospheric drag decay of a circular low Earth orbit: orbit-averaged da/dt = −ρ(h) √(μ a) / B with a static "
        "exponential atmosphere (or a constant density), where B = m/(C_d A) is the ballistic coefficient in kg/m². "
        "Returns altitude vs time, the decay rate now and the time until re-entry (100 km). "
        "Example: altitude=400e3, ballistic_coefficient=140 (ISS-like)."
    ),
)
def orbital_decay(
    altitude: float,
    ballistic_coefficient: float = 100.0,
    max_days: float = 3650.0,
    density_model: str = "exponential",
    constant_density: float = 1e-12,
    n_points: int = 300,
) -> dict:
    b = get_body("earth")
    if not 100e3 < altitude <= 1500e3:
        raise ValueError("altitude must be between 100 and 1500 km (in m)")
    if ballistic_coefficient <= 0 or max_days <= 0 or max_days > 36500:
        raise ValueError("ballistic_coefficient must be positive and max_days in (0, 36500]")
    if density_model not in ("exponential", "constant") or constant_density <= 0:
        raise ValueError("density_model must be 'exponential' or 'constant' (with a positive constant_density)")
    if not 10 <= n_points <= 5000:
        raise ValueError("n_points must be between 10 and 5000")
    mu, re_ = b.mu, b.radius
    rho = (lambda h: density(h / 1000)) if density_model == "exponential" else (lambda h: constant_density)

    def rhs(_t, y):
        a = y[0]
        return [-rho(a - re_) * math.sqrt(mu * a) / ballistic_coefficient]

    def reentry(_t, y):
        return y[0] - re_ - 100e3

    reentry.terminal, reentry.direction = True, -1
    t_max = max_days * DAY
    sol = solve_ivp(rhs, (0, t_max), [re_ + altitude], events=reentry, method="LSODA", rtol=1e-8, atol=1.0,
                    dense_output=True, max_step=t_max / 50)
    t_end = sol.t[-1]
    t = np.linspace(0, t_end, n_points)
    alt = sol.sol(t)[0] - re_
    lifetime = float(sol.t_events[0][0] / DAY) if len(sol.t_events[0]) else None
    rate0 = rhs(0, [re_ + altitude])[0]
    return {
        "result": {
            "lifetime_days": lifetime,
            "reentered": lifetime is not None,
            "final_altitude": float(alt[-1]),
            "initial_decay_rate_m_per_day": -rate0 * DAY,
            "density_at_start": rho(altitude),
            "orbits_per_day": DAY / (2 * math.pi * math.sqrt((re_ + altitude) ** 3 / mu)),
        },
        "curve": {"t_days": (t / DAY).tolist(), "altitude_km": (alt / 1000).tolist()},
        "units": "altitude in m (curve in km), time in days, density in kg/m³, B in kg/m²",
        "assumptions": ["Circular orbit shrinking slowly (orbit-averaged drag), no lift, non-rotating atmosphere",
                        "Static exponential atmosphere — real density varies ×2–10 with solar activity",
                        "Re-entry counted at 100 km altitude"],
    }
