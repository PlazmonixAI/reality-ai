"""Physical constants for central bodies (SI units). Not a tool module."""
from dataclasses import dataclass

G = 6.67430e-11  # m^3 kg^-1 s^-2, CODATA 2018


@dataclass(frozen=True)
class Body:
    name: str
    mu: float      # standard gravitational parameter GM, m^3/s^2
    radius: float  # mean equatorial radius, m


# mu values from JPL/IERS; radii are equatorial.
BODIES: dict[str, Body] = {
    "sun": Body("Sun", 1.32712440018e20, 6.957e8),
    "mercury": Body("Mercury", 2.2032e13, 2.4397e6),
    "venus": Body("Venus", 3.24859e14, 6.0518e6),
    "earth": Body("Earth", 3.986004418e14, 6.378137e6),
    "moon": Body("Moon", 4.9048695e12, 1.7374e6),
    "mars": Body("Mars", 4.282837e13, 3.3962e6),
    "jupiter": Body("Jupiter", 1.26686534e17, 7.1492e7),
    "saturn": Body("Saturn", 3.7931187e16, 6.0268e7),
}

EARTH_MASS = 5.9722e24  # kg
MOON_MASS = 7.342e22    # kg
EARTH_MOON_DISTANCE = 3.844e8  # m, mean


def get_body(body: str) -> Body:
    key = body.strip().lower()
    if key not in BODIES:
        raise ValueError(f"Unknown body {body!r}; choose from {sorted(BODIES)}")
    return BODIES[key]


def resolve_mu(body: str, mu: float | None) -> float:
    """Gravitational parameter: explicit mu overrides the named body."""
    if mu is not None:
        if mu <= 0:
            raise ValueError("mu must be positive")
        return float(mu)
    return get_body(body).mu


def resolve_radius(body: str, radius: float | None, altitude: float | None) -> float:
    """Orbital radius from centre, given either radius or altitude above the body's surface."""
    if (radius is None) == (altitude is None):
        raise ValueError("Give exactly one of radius (from body centre) or altitude (above surface), in metres")
    r = float(radius) if radius is not None else get_body(body).radius + float(altitude)
    if r <= 0:
        raise ValueError("Orbital radius must be positive")
    return r
