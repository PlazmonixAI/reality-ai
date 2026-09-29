import math

import numpy as np
import pytest

from app.modules.physics.elements import elements_to_state, state_to_elements
from app.modules.physics.propagation import propagate_n_body, propagate_two_body

MU_EARTH = 3.986004418e14
G = 6.67430e-11


def test_circular_orbit_quarter_and_full_period():
    r0 = 7e6
    v = math.sqrt(MU_EARTH / r0)
    period = 2 * math.pi * math.sqrt(r0**3 / MU_EARTH)
    res = propagate_two_body([r0, 0, 0], [0, v, 0], period, n_points=5)
    traj = res["trajectory"]
    # Quarter period: at (0, r0, 0)
    assert [traj["x"][1], traj["y"][1]] == pytest.approx([0, r0], abs=1e-2)
    # Full period: back at start
    assert res["result"]["final_position"] == pytest.approx([r0, 0, 0], abs=1e-2)
    assert res["relative_energy_drift"] < 1e-10
    assert len(traj["t"]) == 5 and set(traj) >= {"x", "y", "z", "vx", "vy", "vz"}


def test_matches_kepler_for_eccentric_orbit():
    # Propagate an inclined eccentric orbit to a known time and compare with Kepler's equation.
    a, e = 2.0e7, 0.6
    state = elements_to_state(a, e, 40, 30, 60, 0)["result"]   # start at periapsis
    n = math.sqrt(MU_EARTH / a**3)
    t = 4000.0
    m = n * t
    ecc_anom = m
    for _ in range(50):
        ecc_anom -= (ecc_anom - e * math.sin(ecc_anom) - m) / (1 - e * math.cos(ecc_anom))
    nu = 2 * math.atan2(math.sqrt(1 + e) * math.sin(ecc_anom / 2), math.sqrt(1 - e) * math.cos(ecc_anom / 2))
    expected = elements_to_state(a, e, 40, 30, 60, math.degrees(nu))["result"]
    res = propagate_two_body(state["position"], state["velocity"], t, n_points=2)
    assert res["result"]["final_position"] == pytest.approx(expected["position"], abs=1.0)
    assert res["result"]["final_velocity"] == pytest.approx(expected["velocity"], abs=1e-3)
    # Elements are conserved (except anomaly).
    el = state_to_elements(res["result"]["final_position"], res["result"]["final_velocity"])["result"]
    assert el["semi_major_axis"] == pytest.approx(a, rel=1e-8)
    assert el["eccentricity"] == pytest.approx(e, abs=1e-8)


def test_impact_detection():
    # Suborbital: 7000 km radius at 5 km/s horizontal -> falls into the Earth
    res = propagate_two_body([7e6, 0, 0], [0, 5000, 0], 20_000)
    assert res["result"]["impact"] is True
    assert np.linalg.norm(res["result"]["final_position"]) == pytest.approx(6.378137e6, rel=1e-6)
    assert res["result"]["final_time"] < 20_000


def test_two_body_validation():
    with pytest.raises(ValueError):
        propagate_two_body([1e6, 0, 0], [0, 7000, 0], 100)       # inside Earth
    with pytest.raises(ValueError):
        propagate_two_body([7e6, 0, 0], [0, 7000, 0], -1)
    with pytest.raises(ValueError):
        propagate_two_body([7e6, 0, 0], [0, 7000, 0], 100, n_points=1)


def test_n_body_two_masses_matches_kepler():
    # Equal-mass binary on a circular orbit about the barycentre returns after one period.
    m, d = 1e24, 1e8
    omega = math.sqrt(G * 2 * m / d**3)
    v = omega * d / 2
    period = 2 * math.pi / omega
    res = propagate_n_body(period, bodies=[
        {"name": "A", "mass": m, "position": [-d / 2, 0, 0], "velocity": [0, -v, 0]},
        {"name": "B", "mass": m, "position": [d / 2, 0, 0], "velocity": [0, v, 0]},
    ], n_points=3)
    fs = res["result"]["final_state"]
    assert fs["A"]["position"] == pytest.approx([-d / 2, 0, 0], abs=1.0)
    assert fs["B"]["position"] == pytest.approx([d / 2, 0, 0], abs=1.0)
    # Half period: swapped sides
    assert res["trajectory"]["bodies"]["A"]["x"][1] == pytest.approx(d / 2, rel=1e-8)
    assert res["relative_energy_drift"] < 1e-10


def test_earth_moon_preset_sidereal_month():
    # Moon completes one orbit in ~27.28 days (circular, 384,400 km, Earth+Moon mass)
    res = propagate_n_body(10 * 86400, preset="earth_moon", n_points=3)
    moon0 = res["trajectory"]["bodies"]["Moon"]
    earth = res["trajectory"]["bodies"]["Earth"]
    # Earth-Moon distance stays constant on the circular orbit
    for k in range(3):
        d = math.dist((moon0["x"][k], moon0["y"][k]), (earth["x"][k], earth["y"][k]))
        assert d == pytest.approx(3.844e8, rel=1e-8)
    # Angle swept in 10 days = 10 / 27.28 of a revolution
    ang = math.atan2(moon0["y"][-1], moon0["x"][-1])
    period_days = 2 * math.pi * 10 / ang
    assert period_days == pytest.approx(27.28, rel=2e-3)


def test_earth_moon_spacecraft_relative_to_earth():
    # Spacecraft in a 400 km circular LEO given relative to Earth stays near 6778 km from Earth over 1 orbit.
    r0 = 6.778137e6
    v = math.sqrt(3.986004418e14 * (1 + 0) / r0)
    res = propagate_n_body(5000, preset="earth_moon", bodies=[
        {"name": "sc", "mass": 0, "position": [r0, 0, 0], "velocity": [0, v, 0]},
    ], n_points=51)
    b = res["trajectory"]["bodies"]
    dist = [math.dist((b["sc"]["x"][k], b["sc"]["y"][k], b["sc"]["z"][k]),
                      (b["Earth"]["x"][k], b["Earth"]["y"][k], b["Earth"]["z"][k])) for k in range(51)]
    # Small differences from the Earth-only mu (Earth mass value vs GM) and lunar tides only.
    assert max(dist) / min(dist) - 1 < 1e-3
    assert res["result"]["collision"] is False


def test_n_body_collision_detected():
    res = propagate_n_body(1e6, preset="earth_moon", bodies=[
        {"name": "impactor", "mass": 1000, "position": [1e7, 0, 0], "velocity": [0, 0, 0]},
    ])
    assert res["result"]["collision"] is True
    assert res["result"]["final_time"] < 1e6


def test_n_body_validation():
    with pytest.raises(ValueError, match="between 2"):
        propagate_n_body(100, bodies=[{"name": "A", "mass": 1, "position": [0, 0, 0], "velocity": [0, 0, 0]}])
    with pytest.raises(ValueError, match="missing"):
        propagate_n_body(100, preset="earth_moon", bodies=[{"name": "x"}])
    with pytest.raises(ValueError, match="preset"):
        propagate_n_body(100, preset="solar_system")
    with pytest.raises(ValueError, match="overlap"):
        propagate_n_body(100, preset="earth_moon", bodies=[
            {"name": "x", "mass": 1, "position": [0, 0, 0], "velocity": [0, 0, 0]}])
