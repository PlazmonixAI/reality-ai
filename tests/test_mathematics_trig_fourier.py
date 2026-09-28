import math

import numpy as np
import pytest

from app.modules.mathematics.trig_fourier import fourier_series, trig_exact


@pytest.mark.parametrize("deg, s, c, t", [
    (30, "1/2", "sqrt(3)/2", "sqrt(3)/3"), (45, "sqrt(2)/2", "sqrt(2)/2", "1"),
    (150, "1/2", "-sqrt(3)/2", "-sqrt(3)/3"), (225, "-sqrt(2)/2", "-sqrt(2)/2", "1"), (90, "1", "0", "undefined"),
])
def test_exact_values(deg, s, c, t):
    r = trig_exact(deg)["result"]
    assert (r["sin"], r["cos"], r["tan"]) == (s, c, t)
    assert r["sin_value"] == pytest.approx(math.sin(math.radians(deg)))


def test_quadrant_and_reference_angle():
    r = trig_exact(210)
    assert r["quadrant"] == 3 and r["reference_angle_deg"] == 30
    assert r["radians"] == "7*pi/6"


def test_square_wave_coefficients():
    r = fourier_series("square", math.pi, 9)["result"]
    for n, bn in enumerate(r["b"], start=1):
        assert bn == pytest.approx(4 / (n * math.pi) if n % 2 else 0, abs=1e-6)
    assert np.allclose(r["a"], 0, atol=1e-9) and r["a0"] == pytest.approx(0, abs=1e-9)


def test_sawtooth_and_triangle():
    b = fourier_series("sawtooth", 1.0, 5)["result"]["b"]
    assert b == pytest.approx([2 * (-1) ** (n + 1) / (n * math.pi) for n in range(1, 6)], abs=1e-6)
    a = fourier_series("triangle", 1.0, 5)["result"]["a"]
    assert a == pytest.approx([8 / (n * math.pi) ** 2 if n % 2 else 0 for n in range(1, 6)], abs=1e-6)


def test_expression_x_squared():
    # x^2 on [-pi, pi]: a0 = 2 pi^2 / 3, a_n = 4 (-1)^n / n^2
    r = fourier_series("x^2", math.pi, 4)["result"]
    assert r["a0"] == pytest.approx(2 * math.pi**2 / 3, rel=1e-8)
    assert r["a"] == pytest.approx([4 * (-1) ** n / n**2 for n in range(1, 5)], rel=1e-7)


def test_error_falls_and_gibbs_overshoot():
    e5 = fourier_series("triangle", 1.0, 5)["result"]["rms_error"]
    e25 = fourier_series("triangle", 1.0, 25)["result"]["rms_error"]
    assert e25 < e5 / 5
    over = fourier_series("square", math.pi, 101, n_points=10001)["result"]["max_partial_sum"]
    assert over == pytest.approx(1.179, abs=0.01)          # Gibbs: ~9% of the jump of 2


def test_fourier_validation():
    with pytest.raises(ValueError):
        fourier_series("x + y")
    with pytest.raises(ValueError):
        fourier_series("square", -1)
