"""Black holes and the singularity: a non-rotating (Schwarzschild) black hole.

Everything is computed from general relativity in SI units:
- characteristic radii (event horizon, photon sphere, innermost stable circular orbit), Hawking temperature and lifetime
- how clocks, escape speed, tidal stretching and spacetime curvature (Kretschmann scalar) change with distance
- light rays bending round the hole (null geodesics, d²u/dφ² + u = (3/2) r_s u²)
- orbits of a test particle (timelike geodesics, d²u/dφ² + u = GM/h² + (3/2) r_s u²), including precession and plunging
- the proper time to fall from rest to the singularity at r = 0, where the curvature becomes infinite
"""
from __future__ import annotations

import math

import numpy as np
from scipy.integrate import quad, solve_ivp

from app.core.registry import tool

G = 6.67430e-11
C = 299_792_458.0
HBAR = 1.054571817e-34
KB = 1.380649e-23
M_SUN = 1.98892e30
YEAR = 365.25 * 86400


def _mass(mass_solar: float) -> float:
    if not (1e-20 <= mass_solar <= 1e12):
        raise ValueError("mass_solar must be between 1e-20 and 1e12 solar masses")
    return mass_solar * M_SUN


@tool(domain="physics", name="black_hole",
      description="Schwarzschild black hole of a given mass (in solar masses): event horizon, photon sphere, ISCO, Hawking "
                  "temperature and lifetime, and profiles against distance of clock rate, escape speed, tidal stretch and "
                  "curvature (Kretschmann scalar), plus the proper time to fall from rest to the singularity.")
def black_hole(mass_solar: float = 10.0, fall_from_rs: float = 1.0, body_length_m: float = 2.0) -> dict:
    M = _mass(mass_solar)
    if not (1.0 <= fall_from_rs <= 1e4):
        raise ValueError("fall_from_rs must be between 1 and 10000 (in units of the horizon radius)")
    if not (0 < body_length_m <= 1e3):
        raise ValueError("body_length_m must be between 0 and 1000 m")
    rs = 2 * G * M / C ** 2
    r0 = fall_from_rs * rs
    # Radial free fall from rest at r0 (Schwarzschild): proper time to r = 0 is (π/2)·sqrt(r0³ / 2GM)
    tau_fall = math.pi / 2 * math.sqrt(r0 ** 3 / (2 * G * M))
    tau_horizon_to_singularity = math.pi * G * M / C ** 3  # the longest possible, starting at rest on the horizon
    T_hawking = HBAR * C ** 3 / (8 * math.pi * G * M * KB)
    t_evap = 5120 * math.pi * G ** 2 * M ** 3 / (HBAR * C ** 4)
    x = np.geomspace(1.0, 30.0, 240)  # r / r_s, outside the horizon
    r = x * rs
    dilation = np.sqrt(1 - 1 / x)
    escape = np.sqrt(1 / x)  # fraction of c
    tidal = 2 * G * M * body_length_m / r ** 3
    xin = np.geomspace(0.05, 30.0, 240)
    kretsch = 12 * rs ** 2 / (xin * rs) ** 6  # R_abcd R^abcd = 48 G²M² / (c⁴ r⁶)
    return {
        "result": {
            "mass_kg": M, "schwarzschild_radius_m": rs, "photon_sphere_m": 1.5 * rs, "isco_m": 3 * rs,
            "critical_impact_parameter_m": 1.5 * math.sqrt(3) * rs,
            "surface_gravity_m_s2": C ** 4 / (4 * G * M), "hawking_temperature_K": T_hawking,
            "evaporation_time_years": t_evap / YEAR,
            "density_within_horizon_kg_m3": M / (4 / 3 * math.pi * rs ** 3),
            "fall_start_m": r0, "proper_time_to_singularity_s": tau_fall,
            "proper_time_horizon_to_singularity_s": tau_horizon_to_singularity,
            "curvature_at_horizon_m_minus4": 12 / rs ** 4,
            "tidal_at_horizon_m_s2": 2 * G * M * body_length_m / rs ** 3,
            "profiles": {
                "r_over_rs": x.tolist(), "clock_rate": dilation.tolist(), "escape_speed_over_c": escape.tolist(),
                "tidal_m_s2": tidal.tolist(),
            },
            "curvature_profile": {"r_over_rs": xin.tolist(), "log10_kretschmann": np.log10(kretsch).tolist()},
        },
        "units": {"lengths": "m", "mass": "kg", "time": "s", "temperature": "K", "curvature": "1/m⁴", "tidal": "m/s²",
                  "clock_rate": "dimensionless (dτ/dt for a clock at rest)", "evaporation_time": "years"},
        "assumptions": ["Non-rotating, uncharged black hole (Schwarzschild solution) in empty space.",
                        "Tidal stretch uses the leading-order formula 2GML/r³ along the radial direction.",
                        "Hawking lifetime counts photon emission only (the 5120πG²M³/ħc⁴ estimate).",
                        "At r = 0 the curvature is infinite: general relativity gives no prediction there."],
    }


def light_deflection(b: float) -> float | None:
    """Total bending angle of a ray with impact parameter b (units of r_s), from ∞ to ∞:
    δ = 2∫₀^u₁ du / sqrt(1/b² − u² + u³) − π, u₁ the turning point. None if the ray is captured."""
    if b <= 1.5 * math.sqrt(3):
        return None
    roots = np.roots([1.0, -1.0, 0.0, 1 / b ** 2])
    u1 = min(r.real for r in roots if abs(r.imag) < 1e-12 and r.real > 0)
    f = lambda u: 1 / b ** 2 - u ** 2 + u ** 3
    # substitute u = u1 (1 − t²) so the square-root singularity at the turning point disappears
    g = lambda t: 2 * u1 * t / math.sqrt(max(f(u1 * (1 - t * t)), 1e-300))
    val, _ = quad(g, 0.0, 1.0, limit=200, epsabs=1e-13, epsrel=1e-12)
    return 2 * val - math.pi


def _null_ray(b: float, r_start: float = 25.0, max_phi: float = 6 * math.pi) -> dict:
    """A light ray with impact parameter b (units of r_s, r_s = 1) arriving from x = -∞ moving in +x."""
    u0 = 1 / r_start
    du0_sq = 1 / b ** 2 - u0 ** 2 + u0 ** 3
    if du0_sq <= 0:
        raise ValueError("impact parameter too large for the starting radius")

    def rhs(phi, y):
        return [y[1], -y[0] + 1.5 * y[0] ** 2]

    def horizon(phi, y):
        return y[0] - 1.0
    horizon.terminal = True

    def escaped(phi, y):
        return y[0] - u0 * 0.999 if phi > 0.1 else 1.0
    escaped.terminal = True
    escaped.direction = -1
    sol = solve_ivp(rhs, (0, max_phi), [u0, math.sqrt(du0_sq)], events=[horizon, escaped], max_step=0.01,
                    rtol=1e-9, atol=1e-12, dense_output=False)
    phi, u = sol.t, sol.y[0]
    r = 1 / u
    xs, ys = r * np.cos(phi), r * np.sin(phi)
    # rotate so the incoming direction is +x and the ray starts on the left
    d = np.array([xs[1] - xs[0], ys[1] - ys[0]])
    ang = math.atan2(d[1], d[0])
    ca, sa = math.cos(-ang), math.sin(-ang)
    X, Y = ca * xs - sa * ys, sa * xs + ca * ys
    if Y[0] < 0:
        Y = -Y
    captured = bool(sol.t_events[0].size)
    deflection = None if captured else light_deflection(b)
    step = max(1, len(X) // 400)
    return {"b": b, "captured": captured, "deflection_rad": deflection, "x": X[::step].tolist(), "y": Y[::step].tolist(),
            "closest_approach": float(r.min())}


@tool(domain="physics", name="black_hole_light",
      description="Light rays bending round a Schwarzschild black hole: integrates null geodesics for a fan of impact "
                  "parameters (in units of the horizon radius r_s). Returns each path, whether it falls in, and the "
                  "deflection angle of the rays that escape.")
def black_hole_light(b_min: float = 1.2, b_max: float = 6.0, rays: int = 15, mass_solar: float = 10.0) -> dict:
    if not (2 <= rays <= 60):
        raise ValueError("rays must be between 2 and 60")
    if not (0.05 <= b_min < b_max <= 1e4):
        raise ValueError("need 0.05 <= b_min < b_max <= 10000 (units of r_s)")
    rs = 2 * G * _mass(mass_solar) / C ** 2
    bs = np.linspace(b_min, b_max, rays)
    out = [_null_ray(float(b), r_start=max(25.0, 3 * b_max)) for b in bs]
    bc = 1.5 * math.sqrt(3)
    return {"result": {"rays": out, "critical_impact_parameter": bc, "photon_sphere": 1.5, "rs_m": rs},
            "units": {"x": "r_s", "y": "r_s", "b": "r_s", "deflection_rad": "rad", "rs_m": "m"},
            "assumptions": ["Schwarzschild black hole; rays move in its equatorial plane.",
                            f"Rays with b below 3√3/2 r_s = {bc:.4f} r_s are captured."]}


@tool(domain="physics", name="black_hole_orbit",
      description="Orbit of a test mass round a Schwarzschild black hole (timelike geodesic). Start at radius r0 (units "
                  "of r_s) moving sideways at speed_factor times the circular-orbit speed. Returns the path, whether it "
                  "plunges, the apsides and the precession of the periapsis per orbit.")
def black_hole_orbit(r0: float = 8.0, speed_factor: float = 0.92, orbits: float = 4.0) -> dict:
    if not (1.6 <= r0 <= 1e4):
        raise ValueError("r0 must be between 1.6 and 10000 (units of r_s)")
    if not (0.0 <= speed_factor <= 1.5):
        raise ValueError("speed_factor must be between 0 and 1.5")
    if not (0.5 <= orbits <= 20):
        raise ValueError("orbits must be between 0.5 and 20")
    # Units: r_s = 1, c = 1 so GM = 1/2. Circular orbit angular momentum per unit mass h_c² = GM r / (1 - 3GM/r).
    gm = 0.5
    if r0 <= 1.5:
        raise ValueError("no circular reference orbit inside the photon sphere")
    hc2 = gm * r0 / (1 - 3 * gm / r0)
    h2 = hc2 * speed_factor ** 2
    plunge_only = h2 == 0

    def rhs(phi, y):
        return [y[1], -y[0] + (gm / h2 if not plunge_only else 0) + 1.5 * y[0] ** 2]

    def horizon(phi, y):
        return y[0] - 1.0
    horizon.terminal = True

    def periapsis(phi, y):  # u is largest where du/dφ crosses zero going down
        return y[1]
    periapsis.direction = -1
    if plunge_only:  # pure radial fall: report the straight path to the horizon
        rr = np.linspace(r0, 1.0, 100)
        return {"result": {"x": rr.tolist(), "y": [0.0] * 100, "plunges": True, "periapsis": 1.0, "apoapsis": r0,
                           "precession_deg_per_orbit": None, "stable_circular": r0 >= 3.0},
                "units": {"x": "r_s", "y": "r_s"}, "assumptions": ["Radial fall from rest."]}
    sol = solve_ivp(rhs, (0, 2 * math.pi * orbits), [1 / r0, 0.0], events=[horizon, periapsis], max_step=0.005, rtol=1e-11, atol=1e-13)
    phi, u = sol.t, sol.y[0]
    r = 1 / u
    plunges = bool(sol.t_events[0].size)
    peri_phis = list(sol.t_events[1])
    precession = None
    if len(peri_phis) >= 2:
        precession = math.degrees((peri_phis[1] - peri_phis[0]) - 2 * math.pi)
    step = max(1, len(phi) // 1500)
    return {"result": {"x": (r * np.cos(phi))[::step].tolist(), "y": (r * np.sin(phi))[::step].tolist(),
                       "plunges": plunges, "periapsis": float(r.min()), "apoapsis": float(r.max()),
                       "precession_deg_per_orbit": precession, "stable_circular": r0 >= 3.0,
                       "circular_speed_over_c": math.sqrt(gm / (r0 - 1.0)) if r0 > 1.5 else None},
            "units": {"x": "r_s", "y": "r_s", "periapsis": "r_s", "apoapsis": "r_s", "precession": "deg per orbit",
                      "circular_speed": "fraction of c (measured by a static observer)"},
            "assumptions": ["Test mass much lighter than the black hole; no radiation or drag.",
                            "Circular orbits are stable only outside 3 r_s (the ISCO); inside, any nudge plunges."]}
