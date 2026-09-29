import math

import numpy as np
import pytest

from app.modules.chemistry.phases import SUBSTANCES, _Diagram, phase_diagram
from app.modules.physics.perturbations import density, j2_precession, orbital_decay


# --- J2 precession -----------------------------------------------------------------------------

def test_iss_nodal_regression():
    r = j2_precession(400e3, inclination_deg=51.6, duration_days=3)["result"]
    assert r["raan_rate_deg_per_day"] == pytest.approx(-5.0, abs=0.05)  # textbook ISS value ≈ −5°/day
    assert r["raan_rate_numerical_deg_per_day"] == pytest.approx(r["raan_rate_deg_per_day"], rel=0.01)
    assert r["period_minutes"] == pytest.approx(92.56, abs=0.05)


def test_sun_synchronous_and_critical_inclination():
    r = j2_precession(800e3, propagate=False)["result"]
    assert r["sun_synchronous_inclination_deg"] == pytest.approx(98.6, abs=0.05)
    ss = j2_precession(800e3, inclination_deg=r["sun_synchronous_inclination_deg"], propagate=False)["result"]
    assert ss["raan_rate_deg_per_day"] == pytest.approx(360 / 365.2422, rel=1e-9)
    # At the critical inclination 63.4° the perigee does not move (Molniya orbits)
    m = j2_precession(500e3, 39_000e3, inclination_deg=math.degrees(math.acos(math.sqrt(0.2))), propagate=False)["result"]
    assert m["perigee_rate_deg_per_day"] == pytest.approx(0, abs=1e-12)
    polar = j2_precession(700e3, inclination_deg=90, propagate=False)["result"]
    assert polar["raan_rate_deg_per_day"] == pytest.approx(0, abs=1e-12)


def test_j2_validation():
    with pytest.raises(ValueError):
        j2_precession(400e3, 300e3)
    with pytest.raises(ValueError):
        j2_precession(400e3, body="sun")


# --- drag decay -------------------------------------------------------------------------------

def test_density_model_is_continuous_enough_and_decreasing():
    hs = np.arange(100, 1000, 5.0)
    rho = np.array([density(h) for h in hs])
    assert np.all(np.diff(rho) < 0)
    assert density(400) == pytest.approx(3.725e-12)


def test_constant_density_matches_closed_form():
    # da/dt = −k √a with k = ρ √μ / B  →  √a(t) = √a0 − k t / 2
    rho, b, mu, re = 2e-12, 100.0, 3.986004418e14, 6.378137e6
    out = orbital_decay(500e3, b, max_days=30, density_model="constant", constant_density=rho)
    t = np.array(out["curve"]["t_days"]) * 86400
    k = rho * math.sqrt(mu) / b
    expect = (math.sqrt(re + 500e3) - k * t / 2) ** 2 - re
    assert np.allclose(np.array(out["curve"]["altitude_km"]) * 1000, expect, atol=1.0)


def test_decay_lifetimes_order():
    iss = orbital_decay(400e3, 140)["result"]
    assert iss["reentered"] and 100 < iss["lifetime_days"] < 2000
    assert iss["initial_decay_rate_m_per_day"] == pytest.approx(3.725e-12 * math.sqrt(3.986004418e14 * 6.778137e6) / 140 * 86400, rel=1e-6)
    low = orbital_decay(250e3, 50)["result"]
    high = orbital_decay(700e3, 50, max_days=3650)["result"]
    assert low["lifetime_days"] < 30 and not high["reentered"]


# --- phase diagrams ----------------------------------------------------------------------------

def test_water_everyday_states():
    s = phase_diagram("water", 298.15, 101325)["result"]["state"]
    assert s["phase"] == "liquid" and s["boiling_point"] == pytest.approx(373.124, abs=1e-6)
    assert s["melting_point"] == pytest.approx(273.15, abs=0.01)  # ice melts at 0 °C at 1 atm
    assert phase_diagram("water", 260, 500)["result"]["state"]["phase"] == "solid"
    assert phase_diagram("water", 300, 1000)["result"]["state"]["phase"] == "gas"
    assert phase_diagram("water", 700, 4e7)["result"]["state"]["phase"] == "supercritical fluid"


def test_water_vapour_pressure_and_ice_anomaly():
    dg = _Diagram(SUBSTANCES["water"])
    assert float(dg.p_vap(298.15)) == pytest.approx(3169.9, rel=0.03)  # steam tables
    assert float(dg.p_sub(263.15)) == pytest.approx(259.9, rel=0.03)  # ice at −10 °C
    r = phase_diagram("water")["result"]
    assert r["melting_slope_pa_per_k"] == pytest.approx(-1.35e7, rel=0.02)  # pressure melts ice
    assert float(dg.p_vap(dg.tc)) == pytest.approx(dg.pc, rel=1e-9)


def test_co2_dry_ice_and_liquid():
    s = phase_diagram("co2", 180, 101325)["result"]["state"]
    assert s["phase"] == "solid" and s["sublimation_point"] == pytest.approx(194.686, rel=1e-9)
    assert phase_diagram("co2", 293.15, 101325)["result"]["state"]["phase"] == "gas"
    assert phase_diagram("co2", 250, 2e6)["result"]["state"]["phase"] == "liquid"
    dg = _Diagram(SUBSTANCES["co2"])
    assert float(dg.p_vap(293.15)) == pytest.approx(5.73e6, rel=0.02)
    assert phase_diagram("co2")["result"]["sublimation_enthalpy"] == pytest.approx(26.1e3, rel=0.03)
    assert phase_diagram("co2")["result"]["melting_slope_pa_per_k"] > 0


def test_phase_validation():
    with pytest.raises(ValueError):
        phase_diagram("mercury")
    with pytest.raises(ValueError):
        phase_diagram("water", temperature=300)
