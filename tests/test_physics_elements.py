import math

import numpy as np
import pytest

from app.modules.physics.elements import elements_to_state, state_to_elements

KM = 1e3
MU_EARTH = 3.986004418e14


def test_curtis_example_4_3():
    # Curtis Ex. 4.3: r = (-6045, -3490, 2500) km, v = (-3.457, 6.618, 2.533) km/s
    r = state_to_elements([-6045 * KM, -3490 * KM, 2500 * KM], [-3.457 * KM, 6.618 * KM, 2.533 * KM])
    el = r["result"]
    assert r["specific_angular_momentum"] == pytest.approx(58_310e6, rel=1e-3)
    assert el["inclination_deg"] == pytest.approx(153.2, abs=0.1)
    assert el["raan_deg"] == pytest.approx(255.3, abs=0.1)
    assert el["eccentricity"] == pytest.approx(0.1712, abs=1e-4)
    assert el["arg_periapsis_deg"] == pytest.approx(20.07, abs=0.05)
    assert el["true_anomaly_deg"] == pytest.approx(28.45, abs=0.05)
    assert el["semi_major_axis"] == pytest.approx(8788 * KM, rel=1e-3)
    assert r["orbit_type"] == "elliptical"


def test_curtis_example_4_7():
    # Curtis Ex. 4.7: h = 80000 km^2/s, e = 1.4, i = 30, RAAN = 40, w = 60, nu = 30 deg
    # Expected r = (-4040, 4815, 3629) km, v = (-10.39, -4.772, 1.744) km/s
    e = 1.4
    p = (80_000 * KM**2) ** 2 / MU_EARTH
    a = p / (1 - e**2)
    r = elements_to_state(a, e, 30, 40, 60, 30)
    assert r["result"]["position"] == pytest.approx([-4040 * KM, 4815 * KM, 3629 * KM], rel=2e-3)
    assert r["result"]["velocity"] == pytest.approx([-10.39 * KM, -4.772 * KM, 1.744 * KM], rel=2e-3)


def test_circular_equatorial_orbit():
    r = elements_to_state(7e6, 0.0)
    assert r["result"]["position"] == pytest.approx([7e6, 0, 0])
    assert r["result"]["velocity"][1] == pytest.approx(math.sqrt(MU_EARTH / 7e6))
    back = state_to_elements(r["result"]["position"], r["result"]["velocity"])
    assert back["orbit_type"] == "circular"
    assert back["result"]["inclination_deg"] == pytest.approx(0)
    assert any("RAAN undefined" in a for a in back["assumptions"])


@pytest.mark.parametrize("elements", [
    (7.2e6, 0.05, 51.6, 120.0, 45.0, 200.0),
    (2.6e7, 0.73, 63.4, 300.0, 270.0, 10.0),     # Molniya-like
    (4.2164e7, 0.001, 0.5, 80.0, 30.0, 90.0),
    (-2e7, 1.5, 100.0, 10.0, 350.0, 60.0),       # hyperbolic
])
def test_round_trip(elements):
    a, e, i, raan, w, nu = elements
    state = elements_to_state(*elements)["result"]
    back = state_to_elements(state["position"], state["velocity"])["result"]
    assert back["semi_major_axis"] == pytest.approx(a, rel=1e-9)
    assert back["eccentricity"] == pytest.approx(e, abs=1e-9)
    assert back["inclination_deg"] == pytest.approx(i, abs=1e-7)
    assert back["raan_deg"] == pytest.approx(raan, abs=1e-6)
    assert back["arg_periapsis_deg"] == pytest.approx(w, abs=1e-6)
    assert back["true_anomaly_deg"] == pytest.approx(nu, abs=1e-6)


def test_period_and_apsides():
    r = state_to_elements(*elements_to_state(2.6e7, 0.5)["result"].values())
    assert r["periapsis_radius"] == pytest.approx(1.3e7)
    assert r["apoapsis_radius"] == pytest.approx(3.9e7)
    assert r["period"] == pytest.approx(2 * math.pi * math.sqrt(2.6e7**3 / MU_EARTH))


def test_hyperbolic_has_no_period():
    r = state_to_elements([7e6, 0, 0], [0, 12_000, 0])
    assert r["orbit_type"] == "hyperbolic"
    assert r["period"] is None and r["apoapsis_radius"] is None


def test_invalid_inputs():
    with pytest.raises(ValueError):
        elements_to_state(7e6, 1.2)                # hyperbolic needs a < 0
    with pytest.raises(ValueError):
        elements_to_state(-2e7, 1.5, true_anomaly_deg=170)  # beyond asymptote
    with pytest.raises(ValueError):
        state_to_elements([7e6, 0, 0], [7000, 0, 0])  # radial
    with pytest.raises(ValueError):
        state_to_elements([7e6, 0], [0, 7000, 0])


def test_results_are_plain_floats():
    r = state_to_elements([7e6, 0, 0], [0, 7600, 1000])
    assert all(type(v) is float for v in r["result"].values())
    assert np.isfinite(r["specific_energy"])
