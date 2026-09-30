"""Interplanetary missions: Lambert's problem (universal variables), departure and arrival conditions from the
real planet positions (JPL approximate elements), porkchop plots of launch windows, and the transfer path.

Patched conics: the heliocentric leg is a Kepler arc about the Sun between the planets' centres; departure
and capture burns are computed from the hyperbolic excess speeds at a parking orbit and a capture orbit."""
from __future__ import annotations

import math

import numpy as np

from app.core.registry import tool
from app.modules.physics.ephemeris import AU_KM, OBLIQUITY, heliocentric, julian_date

MU_SUN = 1.32712440018e20
AU = AU_KM * 1000.0
DAY = 86_400.0
PLANETS = {  # mu (m³/s²), equatorial radius (m), sphere-of-influence radius (m)
    "mercury": (2.2032e13, 2.4397e6, 1.12e8), "venus": (3.24859e14, 6.0518e6, 6.16e8),
    "earth": (3.986004418e14, 6.378137e6, 9.25e8), "mars": (4.282837e13, 3.3962e6, 5.77e8),
    "jupiter": (1.26686534e17, 7.1492e7, 4.82e10), "saturn": (3.7931187e16, 6.0268e7, 5.48e10),
    "uranus": (5.793939e15, 2.5559e7, 5.18e10), "neptune": (6.836529e15, 2.4764e7, 8.66e10),
}
DEFAULT_CAPTURE_ALT = {"mercury": 400e3, "venus": 400e3, "earth": 400e3, "mars": 400e3, "jupiter": 1.0e9,
                       "saturn": 3.0e8, "uranus": 1.0e8, "neptune": 1.0e8}


def _stumpff(z: float) -> tuple[float, float]:
    if z > 1e-8:
        sz = math.sqrt(z)
        return (1 - math.cos(sz)) / z, (sz - math.sin(sz)) / sz**3
    if z < -1e-8:
        sz = math.sqrt(-z)
        return (math.cosh(sz) - 1) / -z, (math.sinh(sz) - sz) / sz**3
    return 0.5 - z / 24 + z * z / 720, 1 / 6 - z / 120 + z * z / 5040


def lambert(r1, r2, tof: float, mu: float, prograde: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """Velocities at r1 and r2 for a single-revolution transfer taking tof seconds (Curtis, Algorithm 5.2)."""
    r1, r2 = np.asarray(r1, float), np.asarray(r2, float)
    n1, n2 = np.linalg.norm(r1), np.linalg.norm(r2)
    cos_d = float(np.clip(np.dot(r1, r2) / (n1 * n2), -1, 1))
    dtheta = math.acos(cos_d)
    cz = np.cross(r1, r2)[2]
    if (prograde and cz < 0) or (not prograde and cz >= 0):
        dtheta = 2 * math.pi - dtheta
    a_ = math.sin(dtheta) * math.sqrt(n1 * n2 / (1 - math.cos(dtheta)))
    if abs(a_) < 1e-12:
        raise ValueError("the two positions are exactly opposite; Lambert's problem has no unique plane there")

    def y(z):
        c, s = _stumpff(z)
        return n1 + n2 + a_ * (z * s - 1) / math.sqrt(c)

    def f(z):
        c, s = _stumpff(z)
        yy = y(z)
        return (yy / c) ** 1.5 * s + a_ * math.sqrt(yy) - math.sqrt(mu) * tof

    # bracket the root: z from where y(z) > 0 up to below 4π² (one revolution)
    lo = -4 * math.pi**2
    while y(lo) < 0:
        lo = lo / 2 if lo < -1e-6 else lo + 0.1
        if lo > 4 * math.pi**2:
            raise ValueError("no transfer found")
    hi = 4 * math.pi**2 - 1e-6
    if f(lo) > 0:
        # step up from lo until y(z) turns positive with f < 0
        z = lo
        while f(z) > 0 and z < hi:
            z += 0.1
        lo = z
    if f(lo) * f(hi) > 0:
        raise ValueError("no single-revolution transfer with that flight time")
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
        if hi - lo < 1e-12:
            break
    z = (lo + hi) / 2
    yy = y(z)
    fl = 1 - yy / n1
    g = a_ * math.sqrt(yy / mu)
    gdot = 1 - yy / n2
    v1 = (r2 - fl * r1) / g
    v2 = (gdot * r2 - r1) / g
    return v1, v2


def planet_state(body: str, jd: float) -> tuple[np.ndarray, np.ndarray]:
    """Heliocentric ecliptic position (m) and velocity (m/s) of a planet."""
    h = 0.05
    p = heliocentric(body, np.array([jd - h, jd, jd + h])) * AU
    return p[:, 1], (p[:, 2] - p[:, 0]) / (2 * h * DAY)


def _check(origin: str, target: str) -> None:
    for b in (origin, target):
        if b not in PLANETS:
            raise ValueError(f"planets: {', '.join(PLANETS)} (got {b!r})")
    if origin == target:
        raise ValueError("origin and target must be different planets")


def transfer(origin: str, target: str, jd_dep: float, tof_days: float) -> dict:
    r1, vp1 = planet_state(origin, jd_dep)
    r2, vp2 = planet_state(target, jd_dep + tof_days)
    v1, v2 = lambert(r1, r2, tof_days * DAY, MU_SUN)
    vinf_d, vinf_a = v1 - vp1, v2 - vp2
    return {"r1": r1, "v1": v1, "r2": r2, "v2": v2, "vinf_dep": vinf_d, "vinf_arr": vinf_a,
            "c3": float(np.dot(vinf_d, vinf_d)), "vinf_arr_mag": float(np.linalg.norm(vinf_a))}


def burn_from_orbit(mu: float, r_peri: float, vinf: float, r_apo: float | None = None) -> float:
    """Δv at periapsis between a hyperbola with excess speed vinf and an orbit (circular, or up to r_apo)."""
    v_hyp = math.sqrt(vinf * vinf + 2 * mu / r_peri)
    v_orb = math.sqrt(mu / r_peri) if r_apo is None else math.sqrt(mu * (2 / r_peri - 2 / (r_peri + r_apo)))
    return v_hyp - v_orb


def _to_eq(v: np.ndarray) -> np.ndarray:
    c, s = math.cos(OBLIQUITY), math.sin(OBLIQUITY)
    return np.array([v[0], c * v[1] - s * v[2], s * v[1] + c * v[2]])


def iso(jd: float) -> str:
    from datetime import datetime, timezone
    return datetime.fromtimestamp((jd - 2440587.5) * DAY, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def conic_state(r0, v0, dt: float, mu: float = MU_SUN) -> tuple[np.ndarray, np.ndarray]:
    """Kepler propagation by universal variables (Curtis, Algorithm 3.4)."""
    r0, v0 = np.asarray(r0, float), np.asarray(v0, float)
    rn, vn = np.linalg.norm(r0), np.linalg.norm(v0)
    vr = np.dot(r0, v0) / rn
    alpha = 2 / rn - vn * vn / mu
    x = math.sqrt(mu) * abs(alpha) * dt
    sm = math.sqrt(mu)
    for _ in range(100):
        z = alpha * x * x
        c, s = _stumpff(z)
        fx = rn * vr / sm * x * x * c + (1 - alpha * rn) * x**3 * s + rn * x - sm * dt
        dfx = rn * vr / sm * x * (1 - alpha * x * x * s) + (1 - alpha * rn) * x * x * c + rn
        step = fx / dfx
        x -= step
        if abs(step) < 1e-8:
            break
    z = alpha * x * x
    c, s = _stumpff(z)
    f = 1 - x * x / rn * c
    g = dt - x**3 / sm * s
    r = f * r0 + g * v0
    rr = np.linalg.norm(r)
    fdot = sm / (rr * rn) * (alpha * x**3 * s - x)
    gdot = 1 - x * x / rr * c
    return r, fdot * r0 + gdot * v0


@tool(
    domain="physics",
    name="interplanetary_porkchop",
    description=(
        "Launch windows between two planets (mercury, venus, earth, mars, jupiter, saturn, uranus, neptune): solves "
        "Lambert's problem on a grid of departure dates and flight times using the real planet positions, and "
        "returns the departure energy C3 (km²/s²), arrival excess speed, total Δv from a 200 km parking orbit into "
        "a capture orbit, and the best window. Example: origin='earth', target='mars', depart_start='2026-09-01', "
        "depart_days=240, tof_min_days=150, tof_max_days=400."
    ),
)
def interplanetary_porkchop(origin: str = "earth", target: str = "mars", depart_start: str | None = None, depart_days: float = 780.0,
                            tof_min_days: float | None = None, tof_max_days: float | None = None, n_depart: int = 40,
                            n_tof: int = 30, parking_altitude: float = 200e3, capture_altitude: float | None = None) -> dict:
    _check(origin, target)
    jd0 = julian_date(depart_start)
    if not 2378496.5 <= jd0 <= 2469807.5:
        raise ValueError("departure dates between 1800 and 2050 (the ephemeris range)")
    a1 = np.linalg.norm(planet_state(origin, jd0)[0])
    a2 = np.linalg.norm(planet_state(target, jd0)[0])
    t_h = math.pi * math.sqrt(((a1 + a2) / 2) ** 3 / MU_SUN) / DAY
    tof_min = tof_min_days if tof_min_days is not None else 0.45 * t_h
    tof_max = tof_max_days if tof_max_days is not None else 1.5 * t_h
    if not 5 <= n_depart <= 120 or not 5 <= n_tof <= 120:
        raise ValueError("grid sizes between 5 and 120")
    if not 1 <= depart_days <= 3000 or not 5 <= tof_min < tof_max <= 6000:
        raise ValueError("depart_days 1..3000; 5 ≤ tof_min_days < tof_max_days ≤ 6000")
    if jd0 + depart_days + tof_max > 2469807.5:
        raise ValueError("the grid runs past 2050, the end of the ephemeris")
    mu1, rad1, _ = PLANETS[origin]
    mu2, rad2, _ = PLANETS[target]
    cap_alt = DEFAULT_CAPTURE_ALT[target] if capture_altitude is None else capture_altitude
    deps = np.linspace(jd0, jd0 + depart_days, n_depart)
    tofs = np.linspace(tof_min, tof_max, n_tof)
    c3 = np.full((n_tof, n_depart), np.nan)
    varr = np.full((n_tof, n_depart), np.nan)
    total = np.full((n_tof, n_depart), np.nan)
    best = None
    for j, jd in enumerate(deps):
        for i, tof in enumerate(tofs):
            try:
                tr = transfer(origin, target, float(jd), float(tof))
            except (ValueError, ZeroDivisionError, OverflowError):
                continue
            vd, va = math.sqrt(tr["c3"]), tr["vinf_arr_mag"]
            dv = burn_from_orbit(mu1, rad1 + parking_altitude, vd) + burn_from_orbit(mu2, rad2 + cap_alt, va)
            c3[i, j], varr[i, j], total[i, j] = tr["c3"] / 1e6, va / 1000, dv / 1000
            if best is None or dv < best["total_delta_v"]:
                best = {"depart_jd": float(jd), "depart": iso(float(jd)), "tof_days": float(tof), "arrive": iso(float(jd + tof)),
                        "c3_km2s2": tr["c3"] / 1e6, "vinf_arrival_kms": va / 1000, "total_delta_v": dv}
    if best is None:
        raise ValueError("no transfers found on this grid")
    clean = lambda a: [[None if not np.isfinite(v) else round(float(v), 4) for v in row] for row in a]
    return {"result": {"best": best, "hohmann_tof_days": t_h, "depart_jd": deps.tolist(), "depart": [iso(float(j))[:10] for j in deps],
                       "tof_days": tofs.tolist(), "c3": clean(c3), "vinf_arrival": clean(varr), "total_delta_v": clean(total),
                       "parking_altitude": parking_altitude, "capture_altitude": cap_alt},
            "units": "C3 in km²/s², speeds and Δv in km/s on the grid (best.total_delta_v in m/s), days",
            "assumptions": ["Patched conics; single-revolution prograde Lambert arcs between planet centres",
                            "Planet positions from JPL's approximate Keplerian elements (arc-minute accuracy)",
                            "Δv = departure burn from a circular parking orbit + capture burn into a circular orbit"]}


@tool(
    domain="physics",
    name="interplanetary_mission",
    description=(
        "A specific interplanetary transfer: departure and arrival dates (or depart + tof_days), the Lambert arc "
        "between the real planet positions, C3, departure declination, the burn from a parking orbit, arrival "
        "excess speed and the capture burn (circular, or into an ellipse up to capture_apoapsis), the path for "
        "drawing, and (with 'at') where the spacecraft is on that date. Example: origin='earth', target='mars', "
        "depart='2026-11-05', tof_days=260."
    ),
)
def interplanetary_mission(depart: str, origin: str = "earth", target: str = "mars", tof_days: float | None = None,
                           arrive: str | None = None, parking_altitude: float = 200e3, capture_altitude: float | None = None,
                           capture_apoapsis: float | None = None, at: str | None = None, n_points: int = 200) -> dict:
    _check(origin, target)
    jd_d = julian_date(depart)
    if arrive is not None:
        tof_days = julian_date(arrive) - jd_d
    if tof_days is None or not 5 <= tof_days <= 6000:
        raise ValueError("give tof_days (5..6000) or an arrival date after the departure")
    if not 2378496.5 <= jd_d <= 2469807.5 - tof_days:
        raise ValueError("dates between 1800 and 2050 (the ephemeris range)")
    if not 20 <= n_points <= 2000:
        raise ValueError("n_points 20..2000")
    tr = transfer(origin, target, jd_d, tof_days)
    mu1, rad1, _ = PLANETS[origin]
    mu2, rad2, _ = PLANETS[target]
    cap_alt = DEFAULT_CAPTURE_ALT[target] if capture_altitude is None else capture_altitude
    vd = math.sqrt(tr["c3"])
    dep_burn = burn_from_orbit(mu1, rad1 + parking_altitude, vd)
    cap_burn = burn_from_orbit(mu2, rad2 + cap_alt, tr["vinf_arr_mag"], None if capture_apoapsis is None else rad2 + capture_apoapsis)
    vinf_eq = _to_eq(tr["vinf_dep"]) if origin == "earth" else tr["vinf_dep"]
    dla = math.degrees(math.asin(vinf_eq[2] / np.linalg.norm(vinf_eq)))
    ts = np.linspace(0, tof_days * DAY, n_points)
    path = [(conic_state(tr["r1"], tr["v1"], float(t))[0] / AU).tolist() for t in ts]
    orbit_pts = lambda body, period_days: [(heliocentric(body, np.array([jd_d + d]))[:, 0]).tolist()
                                          for d in np.linspace(0, period_days, 181)]
    per = lambda body: 2 * math.pi * math.sqrt(np.linalg.norm(planet_state(body, jd_d)[0]) ** 3 / MU_SUN) / DAY
    # transfer orbit elements (about the Sun)
    h = np.cross(tr["r1"], tr["v1"])
    energy = np.dot(tr["v1"], tr["v1"]) / 2 - MU_SUN / np.linalg.norm(tr["r1"])
    a_t = -MU_SUN / (2 * energy)
    e_t = float(np.linalg.norm(np.cross(tr["v1"], h) / MU_SUN - tr["r1"] / np.linalg.norm(tr["r1"])))
    out = {
        "origin": origin, "target": target, "depart": iso(jd_d), "arrive": iso(jd_d + tof_days), "depart_jd": jd_d,
        "arrive_jd": jd_d + tof_days, "tof_days": tof_days,
        "c3_km2s2": tr["c3"] / 1e6, "vinf_departure": vd, "declination_deg": dla, "departure_burn": dep_burn,
        "vinf_arrival": tr["vinf_arr_mag"], "capture_burn": cap_burn, "capture_altitude": cap_alt,
        "total_delta_v": dep_burn + cap_burn, "flyby_only_delta_v": dep_burn,
        "transfer_orbit": {"a_au": a_t / AU, "e": e_t, "perihelion_au": a_t * (1 - e_t) / AU, "aphelion_au": a_t * (1 + e_t) / AU},
        "path_au": path, "path_t_days": (ts / DAY).tolist(),
        "origin_orbit_au": orbit_pts(origin, per(origin)), "target_orbit_au": orbit_pts(target, per(target)),
        "origin_at_departure_au": (tr["r1"] / AU).tolist(), "target_at_arrival_au": (tr["r2"] / AU).tolist(),
        "target_at_departure_au": (planet_state(target, jd_d)[0] / AU).tolist(),
        "origin_at_arrival_au": (planet_state(origin, jd_d + tof_days)[0] / AU).tolist(),
        "v1": tr["v1"].tolist(), "r1": tr["r1"].tolist(),
    }
    if at is not None:
        jd = julian_date(at)
        if jd < jd_d:
            out["now"] = {"phase": "waiting for launch", "days_to_launch": jd_d - jd}
        elif jd <= jd_d + tof_days:
            r, v = conic_state(tr["r1"], tr["v1"], (jd - jd_d) * DAY)
            e_pos = planet_state("earth", jd)[0]
            t_pos = planet_state(target, jd)[0]
            out["now"] = {"phase": "cruise", "position_au": (r / AU).tolist(), "speed_sun": float(np.linalg.norm(v)),
                          "distance_from_earth": float(np.linalg.norm(r - e_pos)), "distance_to_target": float(np.linalg.norm(r - t_pos)),
                          "light_time_s": float(np.linalg.norm(r - e_pos)) / 299_792_458.0, "days_to_arrival": jd_d + tof_days - jd,
                          "progress": (jd - jd_d) / tof_days}
        else:
            t_pos = planet_state(target, jd)[0]
            e_pos = planet_state("earth", jd)[0]
            out["now"] = {"phase": "arrived", "position_au": (t_pos / AU).tolist(), "days_since_arrival": jd - jd_d - tof_days,
                          "distance_from_earth": float(np.linalg.norm(t_pos - e_pos)),
                          "light_time_s": float(np.linalg.norm(t_pos - e_pos)) / 299_792_458.0}
    return {"result": out, "units": "m/s for speeds and burns, km²/s² for C3, AU for positions, days",
            "assumptions": ["Patched conics: Sun-only heliocentric arc; burns at periapsis of the departure and arrival hyperbolas",
                            "Planet positions from JPL's approximate Keplerian elements",
                            "Declination of the departure asymptote relative to Earth's equator (limits which launch sites can reach it directly)"]}
