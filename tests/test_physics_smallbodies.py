import math

import numpy as np
import pytest

from app.modules.physics.ephemeris import pole_ecliptic
from app.modules.physics.smallbodies import asteroid_belt, minor_bodies, planet_moons

# Jovicentric ecliptic J2000 positions (AU) of the Galilean moons from astronomy-engine (L1.2 theory)
GALILEAN = {
    "2020-06-01T00:00:00Z": {"io": [0.0011313, -0.0025684, -0.000077], "europa": [-0.0017744, 0.004073, 0.0001251],
                             "ganymede": [0.0028124, -0.0065606, -0.0002109], "callisto": [0.0124638, 0.000854, 0.0001939]},
    "2026-09-29T00:00:00Z": {"io": [0.0022462, 0.0016822, 0.0000928], "europa": [0.0039096, 0.0022779, 0.0001475],
                             "ganymede": [0.003251, -0.0063596, -0.0001958], "callisto": [-0.0126209, 0.0011352, -0.000133]},
}


@pytest.mark.parametrize("date", list(GALILEAN))
def test_galilean_moons_match_theory(date):
    moons = {m["id"]: m for m in planet_moons(date, "jupiter", 16)["result"]["moons"]}
    for mid, ref in GALILEAN[date].items():
        p, r = np.array(moons[mid]["position_au"]), np.array(ref)
        angle = math.degrees(math.acos(p @ r / np.linalg.norm(p) / np.linalg.norm(r)))
        assert angle < 3.0, (mid, angle)
        assert np.linalg.norm(p) == pytest.approx(np.linalg.norm(r), rel=0.03)


def test_regular_moons_orbit_in_their_planets_equator():
    for m in planet_moons("2026-01-01", "all", 16)["result"]["moons"]:
        if m["id"] in ("iapetus", "phoebe", "nereid", "triton"):
            continue  # Laplace plane far from the equator, or captured retrograde moon
        assert m["inclination_to_equator_deg"] < 5, m["name"]
    triton = next(m for m in planet_moons("2026-01-01", "neptune")["result"]["moons"] if m["id"] == "triton")
    assert triton["retrograde_orbit"] and triton["inclination_to_equator_deg"] == pytest.approx(157, abs=3)


def test_moon_orbits_are_closed_and_facts():
    r = planet_moons("2025-03-01", "saturn", 64)["result"]["moons"]
    titan = next(m for m in r if m["id"] == "titan")
    assert titan["orbit"][0] == pytest.approx(titan["position_au"], abs=1e-9)  # the sampled orbit starts at the date
    d = [np.linalg.norm(p) * 149597870.7 for p in titan["orbit"]]
    assert min(d) == pytest.approx(1221865 * (1 - 0.0288), rel=0.002)
    assert max(d) == pytest.approx(1221865 * (1 + 0.0288), rel=0.002)
    assert titan["surface_gravity"] == pytest.approx(1.35, abs=0.02)
    assert titan["tidally_locked"] and not next(m for m in r if m["id"] == "hyperion")["tidally_locked"]
    # Kepler's third law: Titan and Rhea give the same GM for Saturn
    rhea = next(m for m in r if m["id"] == "rhea")
    gm = lambda m: 4 * math.pi ** 2 * (m["semi_major_axis_km"] * 1e3) ** 3 / (m["orbital_period_days"] * 86400) ** 2
    assert gm(titan) == pytest.approx(3.7931e16, rel=0.01) and gm(rhea) == pytest.approx(3.7931e16, rel=0.01)


def test_minor_bodies_orbits_and_positions():
    r = minor_bodies("1986-02-09", "comet")["result"]["bodies"]  # Halley's perihelion
    halley = next(b for b in r if b["id"] == "1p_halley")
    assert halley["perihelion_au"] == pytest.approx(0.586, abs=0.01)
    assert halley["orbital_period_days"] / 365.25 == pytest.approx(75.3, abs=1.5)
    assert halley["distance_sun_au"] == pytest.approx(0.59, abs=0.05)
    ceres = next(b for b in minor_bodies("2026-01-01", "dwarf planet")["result"]["bodies"] if b["id"] == "ceres")
    assert ceres["semi_major_axis_au"] == pytest.approx(2.77, abs=0.01)
    assert ceres["perihelion_au"] <= ceres["distance_sun_au"] <= ceres["aphelion_au"]
    eris = next(b for b in minor_bodies("2026-01-01", "dwarf planet")["result"]["bodies"] if b["id"] == "eris")
    assert 90 < eris["distance_sun_au"] < 100  # Eris is near aphelion (~96 AU) in the 2020s


def test_minor_bodies_track_and_validation():
    r = minor_bodies("2026-01-01", "asteroid", span_days=100, n_track=11)
    assert len(r["track_times_jd"]) == 11
    assert all(len(b["track"]) == 11 for b in r["result"]["bodies"])
    with pytest.raises(ValueError):
        minor_bodies(kind="planet")
    with pytest.raises(ValueError):
        planet_moons(planet="earth")


def test_belt_resonances_and_gaps():
    r = asteroid_belt("2026-01-01", n_main=3000, n_trojans=400, n_kuiper=600)["result"]
    gaps = {g["resonance"]: g["semi_major_axis_au"] for g in r["kirkwood_gaps"]}
    assert gaps["3:1"] == pytest.approx(2.50, abs=0.01) and gaps["2:1"] == pytest.approx(3.28, abs=0.01)
    assert r["neptune_resonances"][0]["semi_major_axis_au"] == pytest.approx(39.4, abs=0.1)
    main = np.array(r["groups"][0]["semi_major_axis_au"])
    assert not np.any(np.abs(main - gaps["3:1"]) < 0.03)
    assert len(r["groups"][0]["orbits"][0]) == r["samples_per_orbit"]
    # Trojans sit ~60° ahead of or behind Jupiter
    from app.modules.physics.ephemeris import heliocentric, julian_date
    jup = heliocentric("jupiter", np.array([julian_date("2026-01-01")]))[:, 0]
    lj = math.atan2(jup[1], jup[0])
    for p in r["groups"][1]["positions_au"][:100]:
        d = math.degrees((math.atan2(p[1], p[0]) - lj + math.pi) % (2 * math.pi) - math.pi)
        assert 15 < abs(d) < 105


def test_mars_moon_frame_uses_mars_equator():
    phobos = next(m for m in planet_moons("2026-01-01", "mars")["result"]["moons"] if m["id"] == "phobos")
    n = np.cross(phobos["orbit"][0], phobos["orbit"][10])
    assert math.degrees(math.acos(abs(n @ pole_ecliptic("mars")) / np.linalg.norm(n))) < 4
