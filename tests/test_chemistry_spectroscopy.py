import math

import numpy as np
import pytest

from app.modules.chemistry.spectroscopy import absorbance_spectrum, beer_lambert


def test_absorbance_from_concentration():
    r = beer_lambert(2400, 1, concentration=2e-4)["result"]
    assert r["absorbance"] == pytest.approx(0.48)
    assert r["transmittance"] == pytest.approx(10 ** -0.48)


@pytest.mark.parametrize("key, value", [("absorbance", 0.7), ("transmittance", 0.25)])
def test_solves_for_concentration(key, value):
    r = beer_lambert(1500, 2, **{key: value})["result"]
    a = value if key == "absorbance" else -math.log10(value)
    assert r["concentration"] == pytest.approx(a / 3000)


def test_linear_in_concentration_and_path():
    a1 = beer_lambert(100, 1, concentration=0.01)["result"]["absorbance"]
    assert beer_lambert(100, 2, concentration=0.02)["result"]["absorbance"] == pytest.approx(4 * a1)


def test_spectrum_peak():
    r = absorbance_spectrum([{"wavelength": 525, "epsilon": 2400, "width": 25}], 1e-4, 1, probe=525)
    assert r["result"]["lambda_max"] == pytest.approx(525)
    assert r["result"]["probe_absorbance"] == pytest.approx(0.24)
    a = np.array(r["spectrum"]["absorbance"])
    assert a.max() == pytest.approx(0.24)
    assert np.allclose(r["spectrum"]["transmittance"], 10 ** -a)


def test_spectroscopy_validation():
    with pytest.raises(ValueError):
        beer_lambert(100, 1, concentration=0.1, absorbance=1)
    with pytest.raises(ValueError):
        beer_lambert(100, 1, transmittance=0)
