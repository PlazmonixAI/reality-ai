"""Classical orbital elements <-> Cartesian state vectors (Curtis, Orbital Mechanics, Alg. 4.2 & 4.5)."""
import math

import numpy as np

from app.core.registry import tool
from app.modules.physics.bodies import resolve_mu

_TOL = 1e-10


def _vector3(v: list[float], name: str) -> np.ndarray:
    a = np.asarray(v, dtype=float)
    if a.shape != (3,) or not np.all(np.isfinite(a)):
        raise ValueError(f"{name} must be a list of 3 finite numbers")
    return a


def elements_to_rv(mu, a, e, i, raan, argp, nu) -> tuple[np.ndarray, np.ndarray]:
    """Angles in radians. a < 0 for hyperbolic orbits (e > 1)."""
    p = a * (1 - e**2)
    if p <= 0:
        raise ValueError("Inconsistent elements: need a > 0 with e < 1, or a < 0 with e > 1")
    if e >= 1 and 1 + e * math.cos(nu) <= 0:
        raise ValueError("True anomaly lies outside the hyperbola's asymptotes")
    r_pf = p / (1 + e * math.cos(nu)) * np.array([math.cos(nu), math.sin(nu), 0.0])
    v_pf = math.sqrt(mu / p) * np.array([-math.sin(nu), e + math.cos(nu), 0.0])
    cO, sO, ci, si, cw, sw = map(float, (np.cos(raan), np.sin(raan), np.cos(i), np.sin(i),
                                         np.cos(argp), np.sin(argp)))
    # Perifocal -> inertial: R3(-raan) R1(-i) R3(-argp)
    q = np.array([
        [cO * cw - sO * sw * ci, -cO * sw - sO * cw * ci, sO * si],
        [sO * cw + cO * sw * ci, -sO * sw + cO * cw * ci, -cO * si],
        [sw * si, cw * si, ci],
    ])
    return q @ r_pf, q @ v_pf


def rv_to_elements(mu, r, v) -> dict:
    """Returns elements with angles in radians plus flags for degenerate cases."""
    rn, vn = np.linalg.norm(r), np.linalg.norm(v)
    if rn == 0:
        raise ValueError("Position vector must be non-zero")
    h = np.cross(r, v)
    hn = np.linalg.norm(h)
    if hn < _TOL * rn * max(vn, 1.0):
        raise ValueError("Radial trajectory (r parallel to v): orbital elements are undefined")
    energy = vn**2 / 2 - mu / rn
    e_vec = ((vn**2 - mu / rn) * r - np.dot(r, v) * v) / mu
    e = float(np.linalg.norm(e_vec))
    a = math.inf if abs(energy) < 1e-14 * mu / rn else float(-mu / (2 * energy))
    i = math.acos(np.clip(h[2] / hn, -1, 1))
    node = np.cross([0.0, 0.0, 1.0], h)
    nn = np.linalg.norm(node)
    equatorial, circular = nn < _TOL * hn, e < 1e-9
    notes = []

    if equatorial:
        raan = 0.0
        notes.append("Equatorial orbit: RAAN undefined, set to 0; periapsis measured from the x-axis")
    else:
        raan = math.acos(np.clip(node[0] / nn, -1, 1))
        if node[1] < 0:
            raan = 2 * math.pi - raan

    # Reference direction for measuring periapsis / position within the orbit.
    ref = np.array([1.0, 0.0, 0.0]) if equatorial else node / nn
    if circular:
        argp = 0.0
        notes.append("Circular orbit: argument of periapsis undefined, set to 0; true anomaly measured from "
                     + ("the x-axis" if equatorial else "the ascending node"))
        nu = _angle_between(ref, r, h)
    else:
        argp = _angle_between(ref, e_vec, h)
        nu = _angle_between(e_vec, r, h)

    return {
        "a": a, "e": e, "i": i, "raan": raan, "argp": argp, "nu": nu,
        "h": float(hn), "energy": float(energy), "notes": notes,
    }


def _angle_between(u: np.ndarray, w: np.ndarray, h: np.ndarray) -> float:
    """Angle from u to w in [0, 2pi), measured in the direction of motion (about h)."""
    cos = np.dot(u, w) / (np.linalg.norm(u) * np.linalg.norm(w))
    ang = math.acos(np.clip(cos, -1, 1))
    return 2 * math.pi - ang if np.dot(np.cross(u, w), h) < 0 else ang


@tool(
    domain="physics",
    name="elements_to_state",
    description=(
        "Convert classical orbital elements to inertial position/velocity vectors. semi_major_axis in m "
        "(negative for hyperbolic), angles in degrees. Example: semi_major_axis=7000000, eccentricity=0.01, "
        "inclination_deg=51.6, raan_deg=0, arg_periapsis_deg=0, true_anomaly_deg=0, body='earth'."
    ),
)
def elements_to_state(
    semi_major_axis: float,
    eccentricity: float,
    inclination_deg: float = 0.0,
    raan_deg: float = 0.0,
    arg_periapsis_deg: float = 0.0,
    true_anomaly_deg: float = 0.0,
    body: str = "earth",
    mu: float | None = None,
) -> dict:
    if eccentricity < 0:
        raise ValueError("eccentricity must be >= 0")
    if math.isclose(eccentricity, 1.0):
        raise ValueError("Parabolic orbits (e = 1) are not supported by semi-major axis; use e slightly != 1")
    if not 0 <= inclination_deg <= 180:
        raise ValueError("inclination_deg must be in [0, 180]")
    gm = resolve_mu(body, mu)
    r, v = elements_to_rv(gm, semi_major_axis, eccentricity, *map(math.radians, (
        inclination_deg, raan_deg, arg_periapsis_deg, true_anomaly_deg)))
    return {
        "result": {"position": r.tolist(), "velocity": v.tolist()},
        "radius": float(np.linalg.norm(r)),
        "speed": float(np.linalg.norm(v)),
        "units": "position in m, velocity in m/s (body-centred inertial frame)",
        "assumptions": ["Two-body Keplerian orbit", "Frame: body-centred inertial, z along the reference pole"],
    }


@tool(
    domain="physics",
    name="state_to_elements",
    description=(
        "Convert inertial position (m) and velocity (m/s) vectors to classical orbital elements "
        "(a, e, i, RAAN, argument of periapsis, true anomaly; angles in degrees) plus period and apsides. "
        "Example: position=[7000000,0,0], velocity=[0,7546,0], body='earth'."
    ),
)
def state_to_elements(position: list[float], velocity: list[float], body: str = "earth", mu: float | None = None) -> dict:
    gm = resolve_mu(body, mu)
    el = rv_to_elements(gm, _vector3(position, "position"), _vector3(velocity, "velocity"))
    a, e = el["a"], el["e"]
    elliptic = e < 1 and math.isfinite(a)
    orbit_type = "circular" if e < 1e-9 else "elliptical" if e < 1 else "parabolic" if not math.isfinite(a) else "hyperbolic"
    p = el["h"] ** 2 / gm
    return {
        "result": {
            "semi_major_axis": a if math.isfinite(a) else None,
            "eccentricity": e,
            "inclination_deg": math.degrees(el["i"]),
            "raan_deg": math.degrees(el["raan"]),
            "arg_periapsis_deg": math.degrees(el["argp"]),
            "true_anomaly_deg": math.degrees(el["nu"]),
        },
        "orbit_type": orbit_type,
        "specific_angular_momentum": el["h"],
        "specific_energy": el["energy"],
        "periapsis_radius": p / (1 + e),
        "apoapsis_radius": a * (1 + e) if elliptic else None,
        "period": 2 * math.pi * math.sqrt(a**3 / gm) if elliptic else None,
        "units": "distances in m, angles in degrees, h in m^2/s, energy in J/kg, period in s",
        "assumptions": ["Two-body Keplerian orbit", "Body-centred inertial frame", *el["notes"]],
    }
