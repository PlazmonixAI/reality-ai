"""Solar System ephemeris: where every planet is on a given date, how it spins and how it is tilted.

Positions use JPL's "Keplerian Elements for Approximate Positions of the Major Planets" (E. M. Standish,
valid 1800–2050, errors of arc-minutes), rotation and pole orientation use the IAU WGCCRE models, and the
Moon uses a short low-precision lunar series. Coordinates are heliocentric J2000 ecliptic, in AU.
"""
import math
from datetime import datetime, timezone

import numpy as np

from app.core.registry import tool

AU_KM = 149_597_870.7
OBLIQUITY = math.radians(23.43928)  # J2000 mean obliquity of the ecliptic
J2000_JD = 2451545.0
DAY_S = 86400.0

# a (AU), e, I, L, long. perihelion ϖ, long. node Ω (deg) and their rates per Julian century (Standish table 1)
ELEMENTS = {
    "mercury": ((0.38709927, 0.20563593, 7.00497902, 252.25032350, 77.45779628, 48.33076593),
                (0.00000037, 0.00001906, -0.00594749, 149472.67411175, 0.16047689, -0.12534081)),
    "venus": ((0.72333566, 0.00677672, 3.39467605, 181.97909950, 131.60246718, 76.67984255),
              (0.00000390, -0.00004107, -0.00078890, 58517.81538729, 0.00268329, -0.27769418)),
    "earth": ((1.00000261, 0.01671123, -0.00001531, 100.46457166, 102.93768193, 0.0),
              (0.00000562, -0.00004392, -0.01294668, 35999.37244981, 0.32327364, 0.0)),
    "mars": ((1.52371034, 0.09339410, 1.84969142, -4.55343205, -23.94362959, 49.55953891),
             (0.00001847, 0.00007882, -0.00813131, 19140.30268499, 0.44441088, -0.29257343)),
    "jupiter": ((5.20288700, 0.04838624, 1.30439695, 34.39644051, 14.72847983, 100.47390909),
                (-0.00011607, -0.00013253, -0.00183714, 3034.74612775, 0.21252668, 0.20469106)),
    "saturn": ((9.53667594, 0.05386179, 2.48599187, 49.95424423, 92.59887831, 113.66242448),
               (-0.00125060, -0.00050991, 0.00193609, 1222.49362201, -0.41897216, -0.28867794)),
    "uranus": ((19.18916464, 0.04725744, 0.77263783, 313.23810451, 170.95427630, 74.01692503),
               (-0.00196176, -0.00004397, -0.00242939, 428.48202785, 0.40805281, 0.04240589)),
    "neptune": ((30.06992276, 0.00859048, 1.77004347, -55.12002969, 44.96476227, 131.78422574),
                (0.00026291, 0.00005105, 0.00035372, 218.45945325, -0.32241464, -0.00508664)),
    "pluto": ((39.48211675, 0.24882730, 17.14001206, 238.92903833, 224.06891629, 110.30393684),
              (-0.00031596, 0.00005170, 0.00004818, 145.20780515, -0.04062942, -0.01183482)),
}

# IAU rotation models: north pole RA α0, Dec δ0 (deg, J2000 equatorial), prime meridian W0 (deg) and rate (deg/day)
ROTATION = {
    "sun": (286.13, 63.87, 84.176, 14.1844000),
    "mercury": (281.0103, 61.4155, 329.5988, 6.1385108),
    "venus": (272.76, 67.16, 160.20, -1.4813688),
    "earth": (0.0, 90.0, 190.147, 360.9856235),
    "moon": (269.9949, 66.5392, 38.3213, 13.17635815),
    "mars": (317.68143, 52.88650, 176.630, 350.89198226),
    "jupiter": (268.057, 64.495, 284.95, 870.5360000),
    "saturn": (40.589, 83.537, 38.90, 810.7939024),
    "uranus": (257.311, -15.175, 203.81, -501.1600928),
    "neptune": (299.36, 43.46, 253.18, 536.3128492),
    "pluto": (132.993, -6.163, 302.695, 56.3625225),
}

# Physical facts: mean radius (km), mass (kg), mean surface temperature (°C), known moons
FACTS = {
    "sun": (695_700, 1.98892e30, 5505, 0),
    "mercury": (2_439.7, 3.3011e23, 167, 0),
    "venus": (6_051.8, 4.8675e24, 464, 0),
    "earth": (6_371.0, 5.97217e24, 15, 1),
    "moon": (1_737.4, 7.342e22, -20, 0),
    "mars": (3_389.5, 6.4171e23, -65, 2),
    "jupiter": (69_911, 1.89813e27, -110, 95),
    "saturn": (58_232, 5.6834e26, -140, 146),
    "uranus": (25_362, 8.6813e25, -195, 28),
    "neptune": (24_622, 1.02413e26, -200, 16),
    "pluto": (1_188.3, 1.303e22, -225, 5),
}
TYPES = {"sun": "star", "mercury": "terrestrial planet", "venus": "terrestrial planet", "earth": "terrestrial planet",
         "moon": "natural satellite", "mars": "terrestrial planet", "jupiter": "gas giant", "saturn": "gas giant",
         "uranus": "ice giant", "neptune": "ice giant", "pluto": "dwarf planet"}
G = 6.67430e-11
ORDER = ["sun", "mercury", "venus", "earth", "moon", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"]


def julian_date(date: str | None) -> float:
    """Julian date (TT ≈ UTC for this accuracy) of an ISO date/time string; None = now."""
    if date is None:
        dt = datetime.now(timezone.utc)
    else:
        try:
            dt = datetime.fromisoformat(date.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError(f"date must be ISO 8601, e.g. '2026-09-29' or '2026-09-29T12:00:00Z' (got {date!r})") from None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    return 2440587.5 + dt.timestamp() / DAY_S


def _solve_kepler(m: np.ndarray, e: float) -> np.ndarray:
    big = m + 0.85 * e * np.sign(np.sin(m))  # Danby's starting value converges for e up to ~1
    for _ in range(50):
        big = big - (big - e * np.sin(big) - m) / (1 - e * np.cos(big))
    return big


def heliocentric(body: str, jd: np.ndarray) -> np.ndarray:
    """Heliocentric ecliptic J2000 position (AU), shape (3, len(jd))."""
    (a0, e0, i0, l0, w0, o0), (da, de, di, dl, dw, do) = ELEMENTS[body]
    t = (np.asarray(jd, float) - J2000_JD) / 36525.0
    a, e = a0 + da * t, e0 + de * t
    inc, lon, peri, node = (np.radians(v0 + dv * t) for v0, dv in ((i0, di), (l0, dl), (w0, dw), (o0, do)))
    return kepler_xyz(a, e, inc, node, peri - node, lon - peri)


def kepler_xyz(a, e, inc, node, argp, m) -> np.ndarray:
    """Position on a Keplerian ellipse (angles in radians, m = mean anomaly), shape (3, n), same units as a."""
    m = np.mod(np.asarray(m, float) + np.pi, 2 * np.pi) - np.pi
    big = _solve_kepler(m, e)
    xp, yp = a * (np.cos(big) - e), a * np.sqrt(1 - e * e) * np.sin(big)
    cw, sw, co, so, ci, si = np.cos(argp), np.sin(argp), np.cos(node), np.sin(node), np.cos(inc), np.sin(inc)
    x = (cw * co - sw * so * ci) * xp + (-sw * co - cw * so * ci) * yp
    y = (cw * so + sw * co * ci) * xp + (-sw * so + cw * co * ci) * yp
    z = (sw * si) * xp + (cw * si) * yp
    return np.array([x, y, z])


def moon_geocentric(jd: np.ndarray) -> np.ndarray:
    """Geocentric ecliptic position of the Moon (AU), low-precision series (~0.3°, ~500 km)."""
    d = np.asarray(jd, float) - J2000_JD
    lp = np.radians(218.316 + 13.176396 * d)
    mm = np.radians(134.963 + 13.064993 * d)
    ms = np.radians(357.529 + 0.98560028 * d)
    dd = np.radians(297.850 + 12.190749 * d)
    f = np.radians(93.272 + 13.229350 * d)
    lon = lp + np.radians(6.289 * np.sin(mm) + 1.274 * np.sin(2 * dd - mm) + 0.658 * np.sin(2 * dd)
                          + 0.214 * np.sin(2 * mm) - 0.186 * np.sin(ms) - 0.114 * np.sin(2 * f))
    lat = np.radians(5.128 * np.sin(f))
    r_km = 385_001 - 20_905 * np.cos(mm) - 3_699 * np.cos(2 * dd - mm) - 2_956 * np.cos(2 * dd)
    r = r_km / AU_KM
    return np.array([r * np.cos(lat) * np.cos(lon), r * np.cos(lat) * np.sin(lon), r * np.sin(lat)])


def position(body: str, jd: np.ndarray) -> np.ndarray:
    if body == "sun":
        return np.zeros((3, np.size(jd)))
    if body == "moon":
        return heliocentric("earth", jd) + moon_geocentric(jd)
    return heliocentric(body, jd)


def pole_ecliptic(body: str) -> np.ndarray:
    """Unit north-pole vector in ecliptic J2000 coordinates."""
    ra, dec = (math.radians(v) for v in ROTATION[body][:2])
    eq = np.array([math.cos(dec) * math.cos(ra), math.cos(dec) * math.sin(ra), math.sin(dec)])
    c, s = math.cos(OBLIQUITY), math.sin(OBLIQUITY)
    return np.array([eq[0], c * eq[1] + s * eq[2], -s * eq[1] + c * eq[2]])


def orbit_normal(body: str, jd: float) -> np.ndarray:
    if body in ("sun",):
        return np.array([0.0, 0.0, 1.0])
    if body == "moon":  # mean lunar orbit is inclined 5.145° to the ecliptic
        return np.array([0.0, 0.0, 1.0])
    (_, _, i0, _, _, o0), (_, _, di, _, _, do) = ELEMENTS[body]
    t = (jd - J2000_JD) / 36525.0
    inc, node = math.radians(i0 + di * t), math.radians(o0 + do * t)
    return np.array([math.sin(inc) * math.sin(node), -math.sin(inc) * math.cos(node), math.cos(inc)])


def _info(body: str, jd: float) -> dict:
    radius, mass, temp, moons = FACTS[body]
    w0, rate = ROTATION[body][2:]
    pole = pole_ecliptic(body)
    spin = pole if rate > 0 else -pole  # obliquity is measured from the spin (angular momentum) axis
    tilt = math.degrees(math.acos(float(np.clip(spin @ orbit_normal(body, jd), -1, 1))))
    info = {
        "name": body.capitalize(), "type": TYPES[body], "radius_km": radius, "mass_kg": mass,
        "surface_gravity": G * mass / (radius * 1000) ** 2,
        "escape_velocity_km_s": math.sqrt(2 * G * mass / (radius * 1000)) / 1000,
        "mean_temperature_c": temp, "moons": moons,
        "rotation_period_hours": abs(360.0 / rate) * 24, "retrograde_rotation": rate < 0,
        "axial_tilt_deg": tilt, "pole_ecliptic": pole.tolist(),
        "prime_meridian_deg": (w0 + rate * (jd - J2000_JD)) % 360.0, "rotation_rate_deg_per_day": rate,
    }
    if body in ELEMENTS:
        (a0, e0, i0, *_), (da, de, di, *_) = ELEMENTS[body]
        t = (jd - J2000_JD) / 36525.0
        a = a0 + da * t
        info.update({"semi_major_axis_au": a, "eccentricity": e0 + de * t, "inclination_deg": i0 + di * t,
                     "orbital_period_days": 365.25 * a ** 1.5, "perihelion_au": a * (1 - e0 - de * t),
                     "aphelion_au": a * (1 + e0 + de * t)})
    if body == "moon":
        info.update({"orbital_period_days": 27.321661, "semi_major_axis_au": 384_400 / AU_KM})
    return info


@tool(
    domain="physics",
    name="solar_system",
    description=(
        "Positions of the Sun, planets, Pluto and the Moon on a date (ISO 8601, default now) from JPL approximate "
        "Keplerian elements (1800–2050): heliocentric ecliptic coordinates in AU, distance from the Sun and Earth, "
        "light time, IAU spin angle and pole direction, axial tilt, physical facts and orbit paths. Optional track "
        "gives positions at n_track times over span_days for smooth animation. Example: date='2026-09-29'."
    ),
)
def solar_system(
    date: str | None = None,
    span_days: float = 0.0,
    n_track: int = 2,
    orbit_points: int = 240,
    bodies: list[str] | None = None,
) -> dict:
    jd = julian_date(date)
    if not 2378496.5 <= jd <= 2469807.5:  # 1800-01-01 .. 2050-12-31
        raise ValueError("date must be between 1800 and 2050 (validity range of the elements)")
    names = bodies or ORDER
    unknown = [b for b in names if b not in ORDER]
    if unknown:
        raise ValueError(f"unknown bodies {unknown}; choose from {', '.join(ORDER)}")
    if not 0 <= span_days <= 365.25 * 200 or not 2 <= n_track <= 2000 or not 16 <= orbit_points <= 2000:
        raise ValueError("span_days must be 0..73050, n_track 2..2000 and orbit_points 16..2000")
    earth = heliocentric("earth", np.array([jd]))[:, 0]
    times = jd + np.linspace(0, span_days, n_track)
    out = []
    for b in names:
        p = position(b, np.array([jd]))[:, 0]
        entry = {"id": b, **_info(b, jd), "position_au": p.tolist(), "distance_sun_au": float(np.linalg.norm(p))}
        if b != "earth":
            d_e = float(np.linalg.norm(p - earth))
            entry["distance_earth_au"] = d_e
            entry["light_time_min"] = d_e * AU_KM / 299_792.458 / 60
        if span_days > 0:
            tr = position(b, times)
            entry["track"] = tr.T.round(9).tolist()
        if b in ELEMENTS:
            period = 365.25 * ELEMENTS[b][0][0] ** 1.5
            entry["orbit"] = heliocentric(b, jd + np.linspace(0, period, orbit_points)).T.round(7).tolist()
        elif b == "moon":
            entry["orbit"] = moon_geocentric(jd + np.linspace(0, 27.321661, orbit_points)).T.round(9).tolist()
            entry["orbit_relative_to"] = "earth"
        out.append(entry)
    return {
        "result": {"julian_date": jd, "date": date, "bodies": out},
        "track_times_jd": times.tolist() if span_days > 0 else None,
        "units": "positions in AU (heliocentric J2000 ecliptic), radii in km, masses in kg, gravity in m/s², angles in degrees",
        "assumptions": [
            "JPL approximate Keplerian elements (Standish), valid 1800–2050, accuracy of order arc-minutes",
            "Moon from a low-precision lunar series (~0.3°); its orbit path is geocentric",
            "Rotation and pole directions from the IAU WGCCRE models; UTC used as TT",
        ],
    }
