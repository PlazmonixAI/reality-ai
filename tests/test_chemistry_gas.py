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
