"""Satellites in real time: J2 drift, drag decay and re-entry, burns and propellant, cameras."""
import math

import pytest

from app.modules.physics.fleet import (MU, RE, coe_to_rv, orbit_from_parameters, rv_to_coe, satellite_imaging,
                                       satellite_manoeuvre, satellite_track)

EPOCH = "2026-03-01T00:00:00Z"


def leo(alt=500e3, inc=97.5, **kw):
    return orbit_from_parameters(alt, EPOCH, inclination_deg=inc, **kw)["result"]["orbit"]


def test_rv_elements_round_trip():
    r, v = coe_to_rv(7.2e6, 0.05, math.radians(40), 1.0, 2.0, 0.5)
    el = rv_to_coe(r, v)
    assert el["a"] == pytest.approx(7.2e6, rel=1e-9) and el["e"] == pytest.approx(0.05, abs=1e-9)
    assert el["i"] == pytest.approx(math.radians(40)) and el["raan"] == pytest.approx(1.0)
    assert el["argp"] == pytest.approx(2.0) and el["m"] == pytest.approx(0.5)


def test_iss_node_drift_and_decay():
    o = leo(420e3, 51.6)
    r = satellite_track(o, EPOCH, "2026-03-02T00:00:00Z", mass=420_000, area_m2=1_700, cd=2.2, forecast=True)["result"]
    # J2 regression of the node for the ISS: about −5.0°/day
    assert (r["elements"]["raan_deg"] - 360) == pytest.approx(-5.0, abs=0.15)
    assert 30 < r["decay_m_per_day"] < 300  # tens of metres per day at 420 km
    assert 150 < r["lifetime_days"] < 2000
    assert r["altitude"] == pytest.approx(420e3, abs=20e3)
    assert -51.7 <= r["lat"] <= 51.7


def test_sun_synchronous_node_turns_with_the_sun():
    o = leo(700e3, 98.19)
    r = satellite_track(o, EPOCH, "2026-03-11T00:00:00Z", area_m2=0)["result"]  # no drag
    assert r["elements"]["raan_deg"] == pytest.approx(10 * 0.9856, abs=0.05)


def test_low_orbit_reenters_and_high_orbit_does_not():
    o = leo(250e3, 51.6)
    r = satellite_track(o, EPOCH, "2027-03-01T00:00:00Z", mass=100, area_m2=1.0)["result"]
    assert r["reentered"] and r["status"] == "re-entered"
    g = orbit_from_parameters(35_786e3, EPOCH, longitude_deg=85.0)["result"]["orbit"]
    far = satellite_track(g, EPOCH, "2036-03-01T00:00:00Z", mass=2367, area_m2=25, forecast=True)["result"]
    assert not far["reentered"] and far["lifetime_days"] is None
    # geostationary: stays over the same longitude (J2-corrected radius ≈ 42,166 km)
    assert far["lon"] == pytest.approx(85.0, abs=0.05) and far["lat"] == pytest.approx(0.0, abs=0.01)
    assert g["a"] == pytest.approx(42_166e3, abs=1e3)


def test_hohmann_leo_to_geo_costs_about_3_9_km_s():
    o = leo(300e3, 0.0)
    r = satellite_manoeuvre(o, EPOCH, "change_altitude", target_altitude=35_786e3, dry_mass=1000, propellant=5000, isp=320,
                            area_m2=0)["result"]
    assert r["delta_v_total"] == pytest.approx(3893, abs=15)
    assert r["orbit"]["perigee_alt"] == pytest.approx(35_786e3, abs=2e3)
    assert r["orbit"]["e"] < 1e-4
    m0 = 6000
    assert r["propellant_used"] == pytest.approx(m0 * (1 - math.exp(-r["delta_v_total"] / (320 * 9.80665))), rel=1e-9)
    assert r["manoeuvre_seconds"] == pytest.approx(math.pi * math.sqrt(((2 * RE + 300e3 + 35_786e3) / 2) ** 3 / MU), rel=2e-3)


def test_not_enough_propellant():
    with pytest.raises(ValueError, match="not enough propellant"):
        satellite_manoeuvre(leo(), EPOCH, "prograde", delta_v=500, dry_mass=1000, propellant=10, isp=220)


def test_prograde_burn_raises_apogee_and_deorbit_lowers_perigee():
    o = leo(500e3)
    up = satellite_manoeuvre(o, EPOCH, "prograde", delta_v=50, dry_mass=500, propellant=50, isp=220, area_m2=0)["result"]
    assert up["orbit"]["apogee_alt"] > 650e3 and up["orbit"]["perigee_alt"] == pytest.approx(500e3, abs=2e3)
    down = satellite_manoeuvre(o, EPOCH, "deorbit", dry_mass=500, propellant=100, isp=220, area_m2=0)["result"]
    assert down["orbit"]["perigee_alt"] == pytest.approx(50e3, abs=1e3) and down["will_reenter"]
    assert 100 < down["delta_v_total"] < 150  # ~ 125 m/s from 500 km


def test_camera_resolution_and_limits():
    cam = {"type": "optical", "aperture_m": 1.2, "ifov_urad": 0.55, "pixels_across": 57_000, "max_off_nadir_deg": 45}
    o = leo(509e3, 97.5)
    # find a daylight moment: step through the day until the ground below is lit
    for h in range(0, 24):
        r = satellite_imaging(o, EPOCH, cam, at=f"2026-03-01T{h:02d}:00:00Z")["result"]
        if r["sun_elevation_deg"] > 20:
            break
    assert r["possible"], r["reasons"]
    assert r["gsd_nadir"] == pytest.approx(0.28, abs=0.01)  # Cartosat-3 class
    assert r["diffraction_limit"] == pytest.approx(1.22 * 550e-9 / 1.2 * 509e3, rel=0.02)
    assert r["resolution"] >= r["gsd"]
    assert r["swath"] == pytest.approx(16e3, rel=0.05)
    # a target on the far side of the Earth is out of view
    far = satellite_imaging(o, EPOCH, cam, at=f"2026-03-01T{h:02d}:00:00Z", target_lat=-r["target"]["lat"],
                            target_lon=r["target"]["lon"] + 180)["result"]
    assert not far["possible"] and "horizon" in far["reasons"][0]


def test_geostationary_imager_resolution():
    g = orbit_from_parameters(35_786e3, EPOCH, longitude_deg=85.0)["result"]["orbit"]
    cam = {"type": "optical", "aperture_m": 0.7, "ifov_urad": 1.17, "pixels_across": 10_000, "max_off_nadir_deg": 9}
    r = satellite_imaging(g, EPOCH, cam, at="2026-03-01T06:30:00Z", target_lat=20.0, target_lon=78.0)["result"]
    assert r["gsd"] == pytest.approx(42, rel=0.1)  # EOS-05's 42 m multispectral
    assert r["diffraction_limit"] == pytest.approx(34.5, rel=0.1)


def test_radar_works_at_night_but_looks_sideways():
    sar = {"type": "sar", "resolution_m": 3.0, "swath_km": 25, "min_off_nadir_deg": 15, "max_off_nadir_deg": 45}
    o = leo(529e3, 97.5)
    nadir = satellite_imaging(o, EPOCH, sar, at="2026-03-01T00:00:00Z")["result"]
    assert not nadir["possible"] and "sideways" in " ".join(nadir["reasons"])
    assert nadir["resolution"] == 3.0
