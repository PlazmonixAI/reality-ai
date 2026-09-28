import math

import pytest

from app.modules.physics.orbital import circular_velocity, escape_velocity, hohmann_transfer, orbital_period

R_EARTH = 6.378137e6


def test_circular_velocity_iss():
    # ISS at ~400 km: ~7.67 km/s
    r = circular_velocity(altitude=400e3)
    assert r["result"] == pytest.approx(7668.6, rel=1e-3)
    assert r["radius"] == pytest.approx(R_EARTH + 400e3)


def test_escape_velocity_earth_surface():
    assert escape_velocity(altitude=0)["result"] == pytest.approx(11_180, rel=1e-3)


def test_escape_is_sqrt2_times_circular():
    assert escape_velocity(radius=1e7)["result"] == pytest.approx(math.sqrt(2) * circular_velocity(radius=1e7)["result"])


def test_escape_velocity_moon():
    assert escape_velocity(altitude=0, body="moon")["result"] == pytest.approx(2376, rel=2e-3)


def test_geo_radius_from_sidereal_day():
    r = orbital_period(period=86164.0905)
    assert r["result"] == pytest.approx(42_164e3, rel=1e-4)


def test_period_from_semi_major_axis():
    # 1 AU around the Sun ~ 365.25 days
    r = orbital_period(semi_major_axis=1.495978707e11, body="sun")
    assert r["result"] / 86400 == pytest.approx(365.25, rel=1e-3)


def test_custom_mu():
    assert circular_velocity(radius=1.0, mu=4.0)["result"] == pytest.approx(2.0)


def test_leo_to_geo_hohmann():
    # Curtis, Orbital Mechanics for Engineering Students, Ex. 6.1-style: 300 km LEO -> GEO
    r = hohmann_transfer(alt1=300e3, alt2=35_786e3)
    res = r["result"]
    assert res["delta_v1"] == pytest.approx(2426, rel=2e-3)
    assert res["delta_v2"] == pytest.approx(1467, rel=2e-3)
    assert res["delta_v_total"] == pytest.approx(3893, rel=2e-3)
    assert r["transfer_time_hours"] == pytest.approx(5.275, rel=2e-3)
    assert r["burn_direction"].startswith("prograde")


def test_hohmann_is_reversible():
    up = hohmann_transfer(r1=7e6, r2=2e7)
    down = hohmann_transfer(r1=2e7, r2=7e6)
    assert down["result"]["delta_v_total"] == pytest.approx(up["result"]["delta_v_total"])
    assert down["burn_direction"].startswith("retrograde")


def test_earth_to_mars_heliocentric():
    # Classic Earth -> Mars Hohmann: ~5.6 km/s total (2.94 + 2.65), ~259 days
    r = hohmann_transfer(r1=1.496e11, r2=2.279e11, body="sun")
    assert r["result"]["delta_v1"] == pytest.approx(2945, rel=5e-3)
    assert r["result"]["delta_v2"] == pytest.approx(2649, rel=5e-3)
    assert r["result"]["transfer_time"] / 86400 == pytest.approx(259, rel=5e-3)


@pytest.mark.parametrize("kwargs", [
    {},                                  # no radius or altitude
    {"radius": 7e6, "altitude": 1e5},    # both
    {"radius": -1.0},
])
def test_radius_validation(kwargs):
    with pytest.raises(ValueError):
        circular_velocity(**kwargs)


def test_unknown_body():
    with pytest.raises(ValueError, match="Unknown body"):
        circular_velocity(altitude=1e5, body="pluto")


def test_below_surface_warning():
    r = circular_velocity(radius=1e6)
    assert any("below the surface" in a for a in r["assumptions"])
