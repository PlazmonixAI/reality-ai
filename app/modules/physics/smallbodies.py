"""Moons, dwarf planets, asteroids, comets and the debris belts of the Solar System.

Orbital elements come from app/data/space/moons.json and small_bodies.json (built by
scripts/build_space_catalogs.py from the Celestia catalogues, which take them from JPL/SSD). Bodies move on
fixed Keplerian ellipses from their element epoch (two-body motion, no perturbations). The belts are a
statistical model: orbits are drawn from the observed element distributions, with the resonance gaps and
groups placed where Kepler's third law puts them.
"""
import json
import math
from functools import lru_cache
from pathlib import Path

import numpy as np

from app.core.registry import tool
from app.modules.physics.ephemeris import (
    AU_KM, ELEMENTS, G, OBLIQUITY, J2000_JD, ROTATION, heliocentric, julian_date, kepler_xyz, pole_ecliptic,
)

DATA = Path(__file__).resolve().parents[2] / "data" / "space"
PLANETS_WITH_MOONS = ("mars", "jupiter", "saturn", "uranus", "neptune", "pluto")
NOT_LOCKED = {"hyperion", "phoebe", "nereid"}  # chaotic or distant irregular moons that do not keep one face


@lru_cache(maxsize=None)
def moon_catalog() -> tuple[dict, ...]:
    return tuple(json.loads((DATA / "moons.json").read_text()))


@lru_cache(maxsize=None)
def small_body_catalog() -> tuple[dict, ...]:
    return tuple(json.loads((DATA / "small_bodies.json").read_text()))


def _check_date(jd: float) -> None:
    if not 2378496.5 <= jd <= 2469807.5:
        raise ValueError("date must be between 1800 and 2050")


def _planet_equator_to_ecliptic(planet: str) -> np.ndarray:
    """Rotation matrix whose columns are the planet-equator frame axes in ecliptic J2000 coordinates.
    z = IAU north pole, x = ascending node of the planet's equator on the Earth's J2000 equator."""
    z = pole_ecliptic(planet)
    earth_pole = np.array([0.0, math.sin(OBLIQUITY), math.cos(OBLIQUITY)])
    x = np.cross(earth_pole, z)
    x /= np.linalg.norm(x)
    return np.column_stack([x, np.cross(z, x), z])


def _elements_xyz(el: dict, jd: np.ndarray, a: float) -> np.ndarray:
    """Position (3, n) in the body's own reference frame (units of a) at Julian dates jd."""
    m = np.radians(el["m0_deg"] + 360.0 / el["period_days"] * (np.asarray(jd, float) - el["epoch_jd"]))
    return kepler_xyz(a, el["e"], math.radians(el["i_deg"]), math.radians(el["node_deg"]),
                      math.radians(el["argp_deg"]), m)


def moon_position_km(moon: dict, jd: np.ndarray) -> np.ndarray:
    """Planetocentric ecliptic J2000 position of a moon (km), shape (3, n)."""
    p = _elements_xyz(moon, jd, moon["a_km"])
    if moon["frame"] == "planet_equator":
        p = _planet_equator_to_ecliptic(moon["parent"]) @ p
    return p


def small_body_position(body: dict, jd: np.ndarray) -> np.ndarray:
    """Heliocentric ecliptic J2000 position (AU), shape (3, n)."""
    return _elements_xyz(body, jd, body["a_au"])


def _orbit_normal(moon: dict) -> np.ndarray:
    i, node = math.radians(moon["i_deg"]), math.radians(moon["node_deg"])
    n = np.array([math.sin(i) * math.sin(node), -math.sin(i) * math.cos(node), math.cos(i)])
    return _planet_equator_to_ecliptic(moon["parent"]) @ n if moon["frame"] == "planet_equator" else n


@tool(
    domain="physics",
    name="planet_moons",
    description=(
        "The major moons of Mars, Jupiter, Saturn, Uranus, Neptune and Pluto on a date (ISO 8601, default now): "
        "planetocentric ecliptic position, distance, orbital period, eccentricity, inclination to the planet's "
        "equator (measured from the spin axis), size, mass, surface gravity, and one full orbit sampled at equal time steps from the date "
        "(so an animation can follow it by phase). planet='all' or a planet name. Example: planet='jupiter'."
    ),
)
def planet_moons(date: str | None = None, planet: str = "all", orbit_points: int = 256) -> dict:
    jd = julian_date(date)
    _check_date(jd)
    planet = planet.lower().strip()
    if planet != "all" and planet not in PLANETS_WITH_MOONS:
        raise ValueError(f"planet must be 'all' or one of {', '.join(PLANETS_WITH_MOONS)} (Earth's Moon is in solar_system)")
    if not 16 <= orbit_points <= 2000:
        raise ValueError("orbit_points must be 16..2000")
    out = []
    for m in moon_catalog():
        if planet != "all" and m["parent"] != planet:
            continue
        p = moon_position_km(m, np.array([jd]))[:, 0]
        times = jd + np.linspace(0, m["period_days"], orbit_points, endpoint=False)
        spin = pole_ecliptic(m["parent"]) * (1 if ROTATION[m["parent"]][3] > 0 else -1)  # Uranus and Pluto spin backwards
        tilt = math.degrees(math.acos(float(np.clip(_orbit_normal(m) @ spin, -1, 1))))
        mass = m["mass_kg"]
        r_m = m["radius_km"] * 1000
        out.append({
            "id": m["id"], "name": m["name"], "parent": m["parent"], "type": "natural satellite",
            "radius_km": m["radius_km"], "mass_kg": mass,
            "surface_gravity": G * mass / r_m ** 2 if mass else None,
            "escape_velocity_km_s": math.sqrt(2 * G * mass / r_m) / 1000 if mass else None,
            "orbital_period_days": m["period_days"], "semi_major_axis_km": m["a_km"], "eccentricity": m["e"],
            "inclination_to_equator_deg": tilt, "retrograde_orbit": tilt > 90,
            "tidally_locked": m["id"] not in NOT_LOCKED,
            "position_km": p.tolist(), "position_au": (p / AU_KM).tolist(), "distance_km": float(np.linalg.norm(p)),
            "orbit": (moon_position_km(m, times) / AU_KM).T.round(10).tolist(), "orbit_start_jd": jd,
        })
    return {
        "result": {"julian_date": jd, "moons": out},
        "units": "positions in AU and km relative to the parent planet (ecliptic J2000), periods in days, masses in kg",
        "assumptions": [
            "Mean Keplerian elements (Celestia catalogue, from JPL/SSD) on fixed ellipses: no precession or mutual perturbations",
            "Orbit samples are equally spaced in time over one period starting at the requested date",
            "Phobos and Deimos elements are referred to Mars' IAU equator; all others to the ecliptic J2000",
        ],
    }


@tool(
    domain="physics",
    name="minor_bodies",
    description=(
        "Dwarf planets (Ceres, Eris, Haumea, Makemake…), notable asteroids (Vesta, Pallas, Eros, Bennu, Ryugu…), "
        "centaurs and comets (Halley, Encke, Hale-Bopp, NEOWISE…) on a date: heliocentric ecliptic position (AU), "
        "distances from the Sun and Earth, orbital elements, perihelion/aphelion, period and orbit path. kind: "
        "'all', 'dwarf planet', 'asteroid' or 'comet'. Optional track over span_days for animation."
    ),
)
def minor_bodies(date: str | None = None, kind: str = "all", span_days: float = 0.0, n_track: int = 2,
                 orbit_points: int = 240) -> dict:
    jd = julian_date(date)
    _check_date(jd)
    kinds = {"all", "dwarf planet", "asteroid", "comet"}
    if kind not in kinds:
        raise ValueError(f"kind must be one of {sorted(kinds)}")
    if not 0 <= span_days <= 73050 or not 2 <= n_track <= 2000 or not 16 <= orbit_points <= 2000:
        raise ValueError("span_days must be 0..73050, n_track 2..2000 and orbit_points 16..2000")
    earth = heliocentric("earth", np.array([jd]))[:, 0]
    times = jd + np.linspace(0, span_days, n_track)
    out = []
    for b in small_body_catalog():
        group = "asteroid" if b["kind"] in ("centaur", "Kuiper belt object") else b["kind"]
        if kind != "all" and group != kind:
            continue
        p = small_body_position(b, np.array([jd]))[:, 0]
        a, e = b["a_au"], b["e"]
        big = np.linspace(-math.pi, math.pi, orbit_points, endpoint=False)  # equal steps in eccentric anomaly
        orbit = kepler_xyz(a, e, math.radians(b["i_deg"]), math.radians(b["node_deg"]), math.radians(b["argp_deg"]),
                           big - e * np.sin(big))
        d_e = float(np.linalg.norm(p - earth))
        entry = {
            "id": b["id"], "name": b["name"], "designation": b["designation"], "type": b["kind"],
            "radius_km": b["radius_km"], "semi_major_axis_au": a, "eccentricity": e, "inclination_deg": b["i_deg"],
            "perihelion_au": a * (1 - e), "aphelion_au": a * (1 + e), "orbital_period_days": b["period_days"],
            "position_au": p.tolist(), "distance_sun_au": float(np.linalg.norm(p)), "distance_earth_au": d_e,
            "light_time_min": d_e * AU_KM / 299_792.458 / 60, "elements_epoch_jd": b["epoch_jd"],
            "orbit": orbit.T.round(6).tolist(),
        }
        if span_days > 0:
            entry["track"] = small_body_position(b, times).T.round(7).tolist()
        out.append(entry)
    return {
        "result": {"julian_date": jd, "bodies": out},
        "track_times_jd": times.tolist() if span_days > 0 else None,
        "units": "positions in AU (heliocentric ecliptic J2000), radii in km, periods in days, angles in degrees",
        "assumptions": [
            "Osculating elements (Celestia catalogue, from JPL/SSD) propagated as two-body Keplerian orbits",
            "Planetary perturbations are ignored, so positions drift for dates far from each element epoch",
        ],
    }


def _resonance_a(planet: str, period_ratio: float) -> float:
    """Semi-major axis (AU) whose period is period_ratio × the planet's (Kepler's third law)."""
    return ELEMENTS[planet][0][0] * period_ratio ** (2 / 3)


def _mean_longitude(planet: str, jd: float) -> float:
    (_, _, _, l0, _, _), (_, _, _, dl, _, _) = ELEMENTS[planet]
    return math.radians(l0 + dl * (jd - J2000_JD) / 36525.0)


@tool(
    domain="physics",
    name="asteroid_belt",
    description=(
        "Statistical model of the Solar System's debris belts on a date: the main asteroid belt with its Kirkwood "
        "gaps (Jupiter resonances 4:1, 3:1, 5:2, 7:3, 2:1), the Jupiter trojans at L4/L5, and the Kuiper belt "
        "(classical belt, plutinos in 3:2 and twotinos in 2:1 resonance with Neptune). Returns resonance locations "
        "from Kepler's third law and sample particles with one orbit sampled in time for animation."
    ),
)
def asteroid_belt(date: str | None = None, n_main: int = 2000, n_trojans: int = 500, n_kuiper: int = 1200,
                  seed: int = 1, samples_per_orbit: int = 16) -> dict:
    jd = julian_date(date)
    _check_date(jd)
    if not (0 <= n_main <= 20000 and 0 <= n_trojans <= 5000 and 0 <= n_kuiper <= 10000):
        raise ValueError("n_main must be 0..20000, n_trojans 0..5000 and n_kuiper 0..10000")
    if not 4 <= samples_per_orbit <= 64:
        raise ValueError("samples_per_orbit must be 4..64")
    rng = np.random.default_rng(seed)
    kirkwood = [(f"{p}:{q}", _resonance_a("jupiter", q / p), w) for p, q, w in
                ((4, 1, 0.03), (3, 1, 0.035), (5, 2, 0.03), (7, 3, 0.02), (2, 1, 0.05))]
    neptune = [("3:2 (plutinos)", _resonance_a("neptune", 1.5)), ("2:1 (twotinos)", _resonance_a("neptune", 2.0))]

    def rayleigh(sigma, n, cap):
        return np.minimum(rng.rayleigh(sigma, n), cap)

    # Main belt: a between the 4:1 and 2:1 resonances, resonance gaps removed
    a = np.empty(0)
    while a.size < n_main:
        c = rng.uniform(2.06, 3.3, 4 * n_main + 16)
        keep = np.ones(c.size, bool)
        for _, ar, w in kirkwood:
            keep &= np.abs(c - ar) > w
        a = np.concatenate([a, c[keep]])[:n_main]
    main = {"a": a, "e": rayleigh(0.08, n_main, 0.3), "i": np.radians(rayleigh(7.0, n_main, 30.0)),
            "node": rng.uniform(0, 2 * np.pi, n_main), "argp": rng.uniform(0, 2 * np.pi, n_main),
            "lam": rng.uniform(0, 2 * np.pi, n_main)}
    # Trojans: Jupiter's orbit, leading (L4, +60°) or trailing (L5, −60°), librating up to ~30°
    lj = _mean_longitude("jupiter", jd)
    side = rng.choice([1.0, -1.0], n_trojans)
    troj = {"a": ELEMENTS["jupiter"][0][0] + rng.normal(0, 0.05, n_trojans), "e": rayleigh(0.06, n_trojans, 0.2),
            "i": np.radians(rayleigh(12.0, n_trojans, 40.0)), "node": rng.uniform(0, 2 * np.pi, n_trojans),
            "argp": rng.uniform(0, 2 * np.pi, n_trojans),
            "lam": lj + side * math.radians(60) + np.radians(rng.normal(0, 12, n_trojans))}
    # Kuiper belt: 60% classical (42–48 AU), 25% plutinos, 15% twotinos
    n_c, n_p = int(0.6 * n_kuiper), int(0.25 * n_kuiper)
    n_t = n_kuiper - n_c - n_p
    cold = rng.random(n_c) < 0.5
    ka = np.concatenate([rng.uniform(42, 48, n_c), neptune[0][1] + rng.normal(0, 0.2, n_p),
                         neptune[1][1] + rng.normal(0, 0.3, n_t)])
    ke = np.concatenate([rayleigh(0.05, n_c, 0.2), rng.uniform(0.05, 0.3, n_p), rng.uniform(0.1, 0.35, n_t)])
    ki = np.concatenate([np.where(cold, rayleigh(2.0, n_c, 10), rayleigh(12.0, n_c, 35)),
                         rayleigh(10.0, n_p, 35), rayleigh(10.0, n_t, 35)])
    kuiper = {"a": ka, "e": ke, "i": np.radians(ki), "node": rng.uniform(0, 2 * np.pi, n_kuiper),
              "argp": rng.uniform(0, 2 * np.pi, n_kuiper), "lam": rng.uniform(0, 2 * np.pi, n_kuiper)}

    def group(name, g):
        n = g["a"].size
        period = 365.25 * g["a"] ** 1.5  # Kepler's third law with the Sun's GM (days)
        m0 = g["lam"] - g["node"] - g["argp"]  # mean anomaly at the date
        steps = np.linspace(0, 2 * np.pi, samples_per_orbit, endpoint=False)
        orbits = np.stack([kepler_xyz(g["a"], g["e"], g["i"], g["node"], g["argp"], m0 + s) for s in steps], axis=0)
        return {"name": name, "count": n, "period_days": period.round(2).tolist(),
                "semi_major_axis_au": g["a"].round(4).tolist(),
                "positions_au": orbits[0].T.round(4).tolist(),
                "orbits": orbits.transpose(2, 0, 1).round(4).tolist() if n else []}

    return {
        "result": {
            "julian_date": jd, "orbit_start_jd": jd, "samples_per_orbit": samples_per_orbit,
            "kirkwood_gaps": [{"resonance": r, "semi_major_axis_au": ar} for r, ar, _ in kirkwood],
            "neptune_resonances": [{"resonance": r, "semi_major_axis_au": ar} for r, ar in neptune],
            "groups": [group("main belt", main), group("Jupiter trojans", troj), group("Kuiper belt", kuiper)],
        },
        "units": "positions and semi-major axes in AU (heliocentric ecliptic J2000), periods in days",
        "assumptions": [
            "Statistical sample: element distributions resemble the observed belts, individual particles are not real objects",
            "Resonance locations from Kepler's third law with the planets' J2000 semi-major axes",
            "Each particle moves on a fixed Keplerian ellipse; orbit samples are equally spaced in time from the date",
        ],
    }
