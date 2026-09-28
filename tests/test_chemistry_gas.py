import pytest

from app.modules.chemistry.gas import R, ideal_gas_law


def test_molar_volume_stp():
    r = ideal_gas_law(pressure=101325, moles=1, temperature=273.15)
    assert r["result"] == pytest.approx(0.022414, rel=1e-4)
    assert r["conversions"]["volume_litres"] == pytest.approx(22.414, rel=1e-4)


@pytest.mark.parametrize("unknown", ["pressure", "volume", "moles", "temperature"])
def test_solve_each_variable(unknown):
    full = {"pressure": 2e5, "volume": 0.01, "moles": 2e5 * 0.01 / (R * 300), "temperature": 300.0}
    r = ideal_gas_law(**{k: v for k, v in full.items() if k != unknown})
    assert r["solved_for"] == unknown
    assert r["result"] == pytest.approx(full[unknown])


@pytest.mark.parametrize("kwargs", [
    {"pressure": 1e5, "volume": 1},
    {"pressure": 1e5, "volume": 1, "moles": 1, "temperature": 300},
    {"pressure": 1e5, "volume": 1, "temperature": -5},
])
def test_gas_validation(kwargs):
    with pytest.raises(ValueError):
        ideal_gas_law(**kwargs)


def test_maxwell_boltzmann_nitrogen_300k():
    from app.modules.chemistry.gas import maxwell_boltzmann
    import math
    r = maxwell_boltzmann(28.014, 300)
    M = 0.028014
    assert r["result"]["rms_speed"] == pytest.approx(math.sqrt(3 * R * 300 / M))
    assert r["result"]["rms_speed"] == pytest.approx(516.8, abs=0.5)
    assert r["result"]["most_probable_speed"] < r["result"]["mean_speed"] < r["result"]["rms_speed"]


def test_maxwell_boltzmann_normalised_and_peaked():
    import numpy as np
    from app.modules.chemistry.gas import maxwell_boltzmann
    r = maxwell_boltzmann(4.0026, 500, n_points=4000)
    v, f = np.array(r["curve"]["speed"]), np.array(r["curve"]["probability_density"])
    assert np.trapezoid(f, v) == pytest.approx(1.0, abs=1e-3)
    assert v[np.argmax(f)] == pytest.approx(r["result"]["most_probable_speed"], rel=2e-3)


def test_maxwell_boltzmann_validation():
    from app.modules.chemistry.gas import maxwell_boltzmann
    with pytest.raises(ValueError):
        maxwell_boltzmann(-1, 300)
