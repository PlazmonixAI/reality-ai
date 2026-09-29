import math

import numpy as np
import pytest

from app.modules.physics.modern import (
    SIGMA, blackbody, hydrogen_spectrum, photoelectric, planck, radioactive_decay, special_relativity,
)
from app.modules.physics.thermo import heat_engine_cycle


def test_stefan_boltzmann_constant():
    assert SIGMA == pytest.approx(5.670374419e-8, rel=1e-9)


def test_wien_peak_sun_and_numerical_maximum():
    r = blackbody(5778, 200, 1500, n_points=5001)
    assert r["result"]["peak_wavelength_nm"] == pytest.approx(501.5, abs=0.1)
    wl, b = np.array(r["spectrum"]["wavelength_nm"]), np.array(r["spectrum"]["radiance"])
    assert wl[np.argmax(b)] == pytest.approx(r["result"]["peak_wavelength_nm"], abs=0.5)


def test_planck_integrates_to_sigma_t4():
    wl = np.geomspace(10e-9, 1e-3, 200_000)
    total = math.pi * np.trapezoid(planck(wl, 3000.0), wl)
    assert total == pytest.approx(SIGMA * 3000.0**4, rel=1e-4)


def test_photoelectric_einstein():
    r = photoelectric(400, 2.28)["result"]
    assert r["photon_energy_ev"] == pytest.approx(1239.84198 / 400, rel=1e-7)
    assert r["stopping_voltage"] == pytest.approx(1239.84198 / 400 - 2.28, rel=1e-6)
    assert r["threshold_wavelength_nm"] == pytest.approx(1239.84198 / 2.28, rel=1e-7)


def test_no_emission_below_threshold_whatever_the_power():
    r = photoelectric(700, 2.28, power=10)["result"]
    assert r["electrons_emitted"] is False and r["saturation_current"] == 0


def test_photocurrent_stops_at_stopping_voltage():
    r = photoelectric(300, 4.3, power=1e-3)
    v, i = np.array(r["iv_curve"]["voltage"]), np.array(r["iv_curve"]["current"])
    vs = r["result"]["stopping_voltage"]
    assert np.all(i[v <= -vs] == 0) and i[-1] == pytest.approx(r["result"]["saturation_current"])


def test_hydrogen_lines():
    assert hydrogen_spectrum(3, 2)["result"]["wavelength_nm"] == pytest.approx(656.47, abs=0.02)   # H-alpha (vacuum)
    assert hydrogen_spectrum(2, 1)["result"]["wavelength_nm"] == pytest.approx(121.57, abs=0.02)   # Lyman-alpha
    r = hydrogen_spectrum(4, 2)["result"]
    assert r["series"] == "Balmer" and r["wavelength_nm"] == pytest.approx(486.27, abs=0.02)
    levels = hydrogen_spectrum()["levels"]
    assert levels[0]["energy_ev"] == pytest.approx(-13.598, abs=0.001)


def test_single_decay_half_life():
    r = radioactive_decay([10.0], [800], 30, n_points=4)
    assert r["curves"]["amounts"][0] == pytest.approx([800, 400, 200, 100])


def test_bateman_parent_daughter():
    h1, h2 = 5.0, 2.0
    l1, l2 = math.log(2) / h1, math.log(2) / h2
    r = radioactive_decay([h1, h2, None], [1000, 0, 0], 20, n_points=41)
    t = np.array(r["curves"]["t"]); nb = np.array(r["curves"]["amounts"][1])
    exact = 1000 * l1 / (l2 - l1) * (np.exp(-l1 * t) - np.exp(-l2 * t))
    assert nb == pytest.approx(exact, rel=1e-9, abs=1e-9)
    total = np.sum(r["curves"]["amounts"], axis=0)
    assert total == pytest.approx(1000)            # atoms are conserved down the chain


def test_lorentz_factor_and_twins():
    r = special_relativity(0.6)["result"]
    assert r["gamma"] == pytest.approx(1.25)
    trip = special_relativity(0.8, distance_ly=4)["result"]["trip"]
    assert trip["earth_years"] == pytest.approx(10) and trip["traveller_years"] == pytest.approx(6)


def test_muon_lifetime_dilation():
    r = special_relativity(0.998, proper_time=2.197e-6)["result"]
    assert r["gamma"] == pytest.approx(15.82, abs=0.01)
    assert r["dilated_time"] * 0.998 * 299_792_458 == pytest.approx(10_400, rel=0.01)   # ~10 km of travel


def test_low_speed_kinetic_energy_is_newtonian():
    r = special_relativity(1e-4, rest_mass=2)["result"]
    assert r["kinetic_energy"] == pytest.approx(r["newtonian_kinetic_energy"], rel=1e-6)


@pytest.mark.parametrize("cycle, kw", [("carnot", {"t_hot": 800, "t_cold": 300}), ("otto", {"compression_ratio": 10}),
                                       ("diesel", {"compression_ratio": 20, "cutoff_ratio": 2.5})])
def test_cycle_efficiency_matches_formula(cycle, kw):
    r = heat_engine_cycle(cycle, **kw)["result"]
    assert r["efficiency"] == pytest.approx(r["formula_efficiency"], rel=1e-4)
    assert r["efficiency"] <= r["carnot_limit"] * (1 + 1e-5)       # numerical-integration tolerance


def test_carnot_is_one_minus_tc_over_th():
    assert heat_engine_cycle("carnot", t_hot=500, t_cold=300)["result"]["formula_efficiency"] == pytest.approx(0.4)


def test_modern_validation():
    with pytest.raises(ValueError):
        special_relativity(1.0)
    with pytest.raises(ValueError):
        hydrogen_spectrum(2, 3)
    with pytest.raises(ValueError):
        heat_engine_cycle("stirling")
    with pytest.raises(ValueError):
        radioactive_decay([1.0], [1, 2], 1)
