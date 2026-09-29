import math

import numpy as np
import pytest

from app.modules.physics.ephemeris import AU_KM, J2000_JD, heliocentric, julian_date, moon_geocentric, solar_system

# JPL Horizons heliocentric ecliptic J2000 positions at 2000-01-01 12:00 TDB (AU)
HORIZONS_J2000 = {
    "earth": (-0.1771, 0.9672, 0.0),      # (Earth–Moon barycentre ≈ Earth)
    "mars": (1.3907, -0.0134, -0.0345),
    "jupiter": (4.0012, 2.9378, -0.1018),
    "saturn": (6.4064, 6.5707, -0.3693),
}


def test_julian_date():
    assert julian_date("2000-01-01T12:00:00Z") == pytest.approx(J2000_JD)
    assert julian_date("2026-09-29") == pytest.approx(2461312.5)
    with pytest.raises(ValueError):
        julian_date("yesterday")


@pytest.mark.parametrize("body", HORIZONS_J2000)
def test_positions_match_horizons(body):
    p = heliocentric(body, np.array([J2000_JD]))[:, 0]
    assert np.allclose(p, HORIZONS_J2000[body], atol=0.01 if body in ("earth", "mars") else 0.03)  # element accuracy ~arc-minutes


def test_earth_perihelion_aphelion_and_year():
    # Early January Earth is at perihelion (~0.9833 AU), early July at aphelion (~1.0167 AU)
    d = lambda iso: float(np.linalg.norm(heliocentric("earth", np.array([julian_date(iso)]))[:, 0]))  # noqa: E731
    assert d("2026-01-03") == pytest.approx(0.9833, abs=5e-4)
    assert d("2026-07-06") == pytest.approx(1.0167, abs=5e-4)
    a = heliocentric("earth", np.array([J2000_JD]))[:, 0]
    b = heliocentric("earth", np.array([J2000_JD + 365.256363]))[:, 0]
    assert np.linalg.norm(a - b) < 1e-4  # back to the same place after one sidereal year


def test_moon_distance_range():
    d = np.linalg.norm(moon_geocentric(J2000_JD + np.arange(0, 60, 0.25)), axis=0) * AU_KM
    assert 355_000 < d.min() < 362_000 and 400_000 < d.max() < 407_500


def test_body_facts_and_tilts():
    r = {b["id"]: b for b in solar_system("2000-01-01T12:00:00Z")["result"]["bodies"]}
    for body, tilt in [("earth", 23.44), ("mars", 25.19), ("jupiter", 3.13), ("saturn", 26.73), ("venus", 177.36), ("uranus", 97.77)]:
        assert r[body]["axial_tilt_deg"] == pytest.approx(tilt, abs=0.1)
    assert r["earth"]["surface_gravity"] == pytest.approx(9.82, abs=0.02)
    assert r["earth"]["rotation_period_hours"] == pytest.approx(23.934, abs=1e-3)  # sidereal day
    assert r["venus"]["retrograde_rotation"] and r["venus"]["rotation_period_hours"] == pytest.approx(243.0 * 24, rel=2e-3)
    assert r["jupiter"]["orbital_period_days"] == pytest.approx(4332.6, rel=2e-3)
    assert r["earth"]["escape_velocity_km_s"] == pytest.approx(11.19, abs=0.02)
    assert r["mars"]["light_time_min"] > 3


def test_track_and_orbits():
    out = solar_system("2026-01-01", span_days=365.25, n_track=5, bodies=["earth", "mars", "moon"])
    bodies = out["result"]["bodies"]
    earth = bodies[0]
    assert len(earth["track"]) == 5 and np.allclose(earth["track"][0], earth["track"][-1], atol=2e-4)
    assert len(earth["orbit"]) == 240
    assert bodies[2]["orbit_relative_to"] == "earth"


def test_validation():
    with pytest.raises(ValueError):
        solar_system("1700-01-01")
    with pytest.raises(ValueError):
        solar_system("2026-01-01", bodies=["vulcan"])
