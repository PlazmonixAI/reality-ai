"""Basic orbital mechanics: circular/escape velocity, Kepler's 3rd law, Hohmann transfer."""
import math

from app.core.registry import tool
from app.modules.physics.bodies import get_body, resolve_mu, resolve_radius

_BODY_NOTE = "Point-mass (spherical) central body; no drag, J2 or third-body perturbations"


def _surface_note(body: str, r: float, mu: float | None) -> list[str]:
    if mu is None and r < get_body(body).radius:
        return [f"Warning: radius {r:.0f} m is below the surface of {get_body(body).name}"]
    return []


@tool(
    domain="physics",
    name="circular_velocity",
    description=(
        "Speed of a circular orbit, v = sqrt(mu/r). Give radius (m, from centre) or altitude (m, above surface) "
        "and body (earth, moon, sun, mars, venus, mercury, jupiter, saturn) or a custom mu (m^3/s^2). "
        "Example: altitude=400000, body='earth'."
    ),
)
def circular_velocity(
    radius: float | None = None, altitude: float | None = None, body: str = "earth", mu: float | None = None,
) -> dict:
    gm, r = resolve_mu(body, mu), resolve_radius(body, radius, altitude)
    return {
        "result": math.sqrt(gm / r),
        "radius": r,
        "units": "m/s (radius in m)",
        "assumptions": ["Circular two-body orbit", _BODY_NOTE, *_surface_note(body, r, mu)],
    }


@tool(
    domain="physics",
    name="escape_velocity",
    description=(
        "Escape speed from a given distance, v = sqrt(2 mu / r). Give radius or altitude (m) and body or mu. "
        "Example: altitude=0, body='earth' -> ~11.2 km/s."
    ),
)
def escape_velocity(
    radius: float | None = None, altitude: float | None = None, body: str = "earth", mu: float | None = None,
) -> dict:
    gm, r = resolve_mu(body, mu), resolve_radius(body, radius, altitude)
    return {
        "result": math.sqrt(2 * gm / r),
        "radius": r,
        "units": "m/s (radius in m)",
        "assumptions": ["Ignores atmosphere and the body's rotation", _BODY_NOTE, *_surface_note(body, r, mu)],
    }


@tool(
    domain="physics",
    name="orbital_period",
    description=(
        "Kepler's third law, T = 2 pi sqrt(a^3/mu). Give semi_major_axis (m) to get the period (s), "
        "or period (s) to get the semi-major axis (m). Example: period=86164.1, body='earth' -> GEO radius."
    ),
)
def orbital_period(
    semi_major_axis: float | None = None, period: float | None = None, body: str = "earth", mu: float | None = None,
) -> dict:
    gm = resolve_mu(body, mu)
    if (semi_major_axis is None) == (period is None):
        raise ValueError("Give exactly one of semi_major_axis (m) or period (s)")
    if semi_major_axis is not None:
        if semi_major_axis <= 0:
            raise ValueError("semi_major_axis must be positive (elliptical orbit)")
        a = float(semi_major_axis)
        t = 2 * math.pi * math.sqrt(a**3 / gm)
        result, units = t, "s"
    else:
        if period <= 0:
            raise ValueError("period must be positive")
        t = float(period)
        a = (gm * (t / (2 * math.pi)) ** 2) ** (1 / 3)
        result, units = a, "m"
    return {
        "result": result,
        "semi_major_axis": a,
        "period": t,
        "period_hours": t / 3600,
        "units": f"{units} (semi_major_axis in m, period in s)",
        "assumptions": ["Two-body Keplerian orbit, orbiting mass negligible vs central body", _BODY_NOTE],
    }


@tool(
    domain="physics",
    name="hohmann_transfer",
    description=(
        "Hohmann transfer between two coplanar circular orbits: both burn delta-v's, total delta-v and "
        "transfer time. Give r1/r2 (m, from centre) or alt1/alt2 (m, above surface). "
        "Example LEO->GEO: alt1=300000, alt2=35786000, body='earth' -> ~3.9 km/s total."
    ),
)
def hohmann_transfer(
    r1: float | None = None,
    r2: float | None = None,
    alt1: float | None = None,
    alt2: float | None = None,
    body: str = "earth",
    mu: float | None = None,
) -> dict:
    gm = resolve_mu(body, mu)
    ra, rb = resolve_radius(body, r1, alt1), resolve_radius(body, r2, alt2)
    if math.isclose(ra, rb):
        raise ValueError("Initial and final orbits are the same; no transfer needed")

    a_t = (ra + rb) / 2
    v1, v2 = math.sqrt(gm / ra), math.sqrt(gm / rb)
    v_dep = math.sqrt(gm * (2 / ra - 1 / a_t))  # transfer-orbit speed at r1
    v_arr = math.sqrt(gm * (2 / rb - 1 / a_t))  # transfer-orbit speed at r2
    dv1, dv2 = v_dep - v1, v2 - v_arr
    raising = rb > ra
    t_transfer = math.pi * math.sqrt(a_t**3 / gm)
    return {
        "result": {
            "delta_v1": abs(dv1),
            "delta_v2": abs(dv2),
            "delta_v_total": abs(dv1) + abs(dv2),
            "transfer_time": t_transfer,
        },
        "burn_direction": "prograde (both burns)" if raising else "retrograde (both burns)",
        "transfer_orbit": {
            "semi_major_axis": a_t,
            "eccentricity": abs(rb - ra) / (ra + rb),
            "periapsis": min(ra, rb),
            "apoapsis": max(ra, rb),
        },
        "circular_speeds": {"initial": v1, "final": v2},
        "transfer_time_hours": t_transfer / 3600,
        "units": "delta-v in m/s, time in s, distances in m",
        "assumptions": [
            "Coplanar circular initial and final orbits (no plane change)",
            "Impulsive burns",
            _BODY_NOTE,
        ],
    }
