import math

import numpy as np
import pytest

from app.modules.physics.universe import (
    EQ_TO_GAL, blackbody_rgb, bv_temperature, circular_velocity, cosmology, galaxy_catalog, milky_way, radec_unit,
    star_catalog,
)


def test_galactic_frame():
    # Sgr A* lies at l = b = 0, the north galactic pole at b = +90°
    assert EQ_TO_GAL @ radec_unit(266.405 / 15, -28.936) == pytest.approx([1, 0, 0], abs=2e-3)
    assert EQ_TO_GAL @ radec_unit(192.8595 / 15, 27.1283) == pytest.approx([0, 0, 1], abs=1e-4)


def test_star_colours_and_temperatures():
    assert bv_temperature(0.656) == pytest.approx(5772, rel=0.01)  # the Sun
    red, sun, blue = blackbody_rgb([3000, 5772, 20000])
    assert red[0] == pytest.approx(1) and red[2] < 0.5
    assert sun.min() > 0.85
    assert blue[2] == pytest.approx(1) and blue[0] < 0.8


@pytest.mark.parametrize("name, dist, lum", [("Sirius", 8.6, 22), ("Vega", 25.0, 49), ("Proxima Centauri", 4.24, 5.7e-5)])
def test_named_stars(name, dist, lum):
    r = star_catalog(name=name)["result"]
    assert r["name"][0] == name
    assert r["distance_ly"][0] == pytest.approx(dist, rel=0.02)
    assert r["luminosity_solar"][0] == pytest.approx(lum, rel=0.15)
    assert math.dist([0, 0, 0], [r["x_ly"][0], r["y_ly"][0], r["z_ly"][0]]) == pytest.approx(r["distance_ly"][0], rel=1e-4)


def test_star_filters_and_frames():
    naked = star_catalog(6.0)["result"]
    assert 4500 < naked["count"] < 5500  # ~5000 stars are visible to the naked eye
    assert max(naked["apparent_magnitude"]) <= 6.0
    near = star_catalog(-2, nearby_ly=20)["result"]
    assert all(d <= 20 for d in near["distance_ly"]) and near["count"] > 50
    betel = star_catalog(name="Betelgeuse", frame="galactic")["result"]
    assert betel["temperature_k"][0] < 4200 and betel["z_ly"][0] < 0  # Betelgeuse lies south of the galactic plane
    with pytest.raises(ValueError):
        star_catalog(frame="lunar")
    with pytest.raises(ValueError):
        star_catalog(name="Krypton")


def test_milky_way_rotation_and_structure():
    r = milky_way(2000)["result"]
    assert r["circular_speed_at_sun_km_s"] == pytest.approx(229, abs=0.5)
    assert r["galactic_year_myr"] == pytest.approx(218, abs=3)  # ~220 million years per orbit
    v = circular_velocity(np.array([6.0, 10.0, 20.0]))
    assert np.all((v > 190) & (v < 250))  # nearly flat rotation curve: evidence for dark matter
    assert 2e11 < r["mass_within_50kpc_msun"] < 7e11
    assert len(r["points"]["x_kpc"]) == 2000 and len(r["arms"]) == 4
    gc = r["globular_clusters"]
    assert len(gc["name"]) > 140
    i = gc["name"].index("OME Cen")  # ω Centauri, ~17,000 ly away
    d_sun = math.dist([gc["x_kpc"][i], gc["y_kpc"][i], gc["z_kpc"][i]], r["sun_position_kpc"])
    assert d_sun == pytest.approx(5.2, abs=0.6)


def test_galaxies():
    m31 = galaxy_catalog(name="Andromeda Galaxy")["result"]
    assert m31["distance_mly"][0] == pytest.approx(2.54, rel=0.05)
    assert m31["redshift"][0] is None  # Local Group: gravity, not the Hubble flow
    m87 = galaxy_catalog(name="M 87")["result"]
    assert m87["distance_mly"][0] == pytest.approx(53.5, rel=0.05)
    assert m87["hubble_velocity_km_s"][0] == pytest.approx(67.66 * 53.5 / 3.2616, rel=0.06)
    near = galaxy_catalog(max_distance_mly=10)["result"]
    assert "LMC" in near["name"] and all(d <= 10 for d in near["distance_mly"])
    assert galaxy_catalog()["result"]["count"] > 10000


def test_cosmology_planck2018():
    r = cosmology(1.0)["result"]
    assert r["age_now_gyr"] == pytest.approx(13.79, abs=0.02)
    assert r["comoving_distance_mpc"] == pytest.approx(3395, rel=0.003)
    assert r["lookback_time_gyr"] == pytest.approx(7.93, abs=0.05)
    assert r["luminosity_distance_gly"] == pytest.approx(2 * r["comoving_distance_gly"])  # flat: D_L = (1+z) D_C
    assert r["observable_universe_radius_gly"] == pytest.approx(46.2, abs=0.4)
    assert r["hubble_radius_gly"] == pytest.approx(14.45, abs=0.02)
    assert r["critical_density_kg_m3"] == pytest.approx(8.6e-27, rel=0.01)
    assert r["cmb_comoving_distance_gly"] < r["observable_universe_radius_gly"]
    assert cosmology(0)["result"]["lookback_time_gyr"] == pytest.approx(0, abs=1e-9)


def test_cosmology_limits():
    # Einstein–de Sitter universe: age = 2/(3 H0)
    eds = cosmology(0.5, h0=70, omega_m=1.0, omega_lambda=0.0, omega_r=0.0)["result"]
    assert eds["age_now_gyr"] == pytest.approx(2 / 3 * 977.8 / 70, rel=1e-3)
    assert eds["comoving_distance_gly"] == pytest.approx(2 * (1 - 1 / math.sqrt(1.5)) * 299792.458 / 70 * 3.2616 / 1000, rel=1e-4)
    with pytest.raises(ValueError):
        cosmology(z=-1)
