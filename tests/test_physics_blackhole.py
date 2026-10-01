"""Schwarzschild black hole and the singularity, checked against textbook general relativity."""
import math

import pytest

from app.modules.physics.blackhole import black_hole, black_hole_light, black_hole_orbit, light_deflection


def test_radii_and_hawking_values_for_one_solar_mass():
    r = black_hole(1.0)["result"]
    assert r["schwarzschild_radius_m"] == pytest.approx(2953.3, rel=2e-3)        # 2GM/c² for the Sun ≈ 2.95 km
    assert r["photon_sphere_m"] == pytest.approx(1.5 * r["schwarzschild_radius_m"])
    assert r["isco_m"] == pytest.approx(3 * r["schwarzschild_radius_m"])
    assert r["hawking_temperature_K"] == pytest.approx(6.17e-8, rel=5e-3)
    assert r["evaporation_time_years"] == pytest.approx(2.1e67, rel=0.05)


def test_fall_to_the_singularity():
    r = black_hole(10.0, fall_from_rs=1.0)["result"]
    gm_c3 = 6.67430e-11 * 10 * 1.98892e30 / 299792458.0 ** 3
    assert r["proper_time_horizon_to_singularity_s"] == pytest.approx(math.pi * gm_c3, rel=1e-9)   # π GM/c³
    assert r["proper_time_to_singularity_s"] == pytest.approx(r["proper_time_horizon_to_singularity_s"], rel=1e-9)
    far = black_hole(10.0, fall_from_rs=8.0)["result"]
    assert far["proper_time_to_singularity_s"] == pytest.approx(8 ** 1.5 * r["proper_time_to_singularity_s"], rel=1e-9)


def test_profiles_clock_rate_and_curvature():
    r = black_hole(4e6)["result"]  # Sagittarius A*
    p = r["profiles"]
    i = min(range(len(p["r_over_rs"])), key=lambda k: abs(p["r_over_rs"][k] - 2.0))
    assert p["clock_rate"][i] == pytest.approx(math.sqrt(1 - 1 / p["r_over_rs"][i]), rel=1e-9)
    rs = r["schwarzschild_radius_m"]
    assert r["curvature_at_horizon_m_minus4"] == pytest.approx(12 / rs ** 4)
    k = r["curvature_profile"]["log10_kretschmann"]
    assert k[0] > k[-1]  # curvature grows without limit towards r = 0
    # a supermassive hole is gentle at the horizon: tidal stretch on a 2 m body far below 1 g
    assert r["tidal_at_horizon_m_s2"] < 1e-2


def test_light_bending():
    assert light_deflection(1000.0) == pytest.approx(2 / 1000 + 15 * math.pi / 16 / 1000 ** 2, rel=1e-5)
    sun_b = 6.957e8 / 2953.3
    assert math.degrees(light_deflection(sun_b)) * 3600 == pytest.approx(1.75, abs=0.01)   # Eddington 1919
    assert light_deflection(2.5) is None  # inside the critical impact parameter
    rays = black_hole_light(1.2, 6.0, 12)["result"]["rays"]
    bc = 1.5 * math.sqrt(3)
    assert all(r["captured"] == (r["b"] < bc) for r in rays)
    assert all(r["closest_approach"] >= 1.0 - 1e-6 for r in rays)


def test_orbits_precess_and_plunge():
    o = black_hole_orbit(1000, 0.95, 3)["result"]
    h2 = 0.5 * 1000 / (1 - 1.5 / 1000) * 0.95 ** 2
    assert o["precession_deg_per_orbit"] == pytest.approx(math.degrees(6 * math.pi * 0.25 / h2), rel=0.01)
    assert not o["plunges"] and o["apoapsis"] == pytest.approx(1000, rel=1e-6)
    assert black_hole_orbit(8, 0.5)["result"]["plunges"]          # too slow: falls in
    c = black_hole_orbit(10, 1.0, 2)["result"]                     # circular
    assert c["periapsis"] == pytest.approx(10, rel=1e-4) and c["circular_speed_over_c"] == pytest.approx(math.sqrt(0.5 / 9))
    with pytest.raises(ValueError):
        black_hole_orbit(1.2)
