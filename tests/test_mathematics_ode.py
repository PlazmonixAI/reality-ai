import math

import pytest

from app.modules.mathematics.ode import solve_ode


def test_exponential_decay():
    r = solve_ode(["y"], ["-k*y"], [1.0], [0, 2], parameters={"k": 0.5})
    assert r["result"]["final"]["y"] == pytest.approx(math.exp(-1.0), rel=1e-7)
    assert len(r["result"]["t"]) == 201


def test_harmonic_oscillator():
    # x'' = -w^2 x, x(0)=1, v(0)=0  ->  x = cos(w t), v = -w sin(w t)
    w, t1 = 2.0, 3.0
    r = solve_ode(["x", "v"], ["v", "-w**2*x"], [1, 0], [0, t1], parameters={"w": w})
    assert r["result"]["final"]["x"] == pytest.approx(math.cos(w * t1), abs=1e-6)
    assert r["result"]["final"]["v"] == pytest.approx(-w * math.sin(w * t1), abs=1e-6)


def test_time_dependent_rhs():
    # y' = 2t, y(0) = 0  ->  y = t^2
    r = solve_ode(["y"], ["2*t"], [0], [0, 3], n_points=4)
    assert r["result"]["y"]["y"] == pytest.approx([0, 1, 4, 9], abs=1e-8)


def test_logistic_stiff_solver():
    # Logistic growth closed form: K / (1 + (K/y0 - 1) e^{-rt})
    K, r0, y0, t1 = 100.0, 1.5, 5.0, 4.0
    r = solve_ode(["N"], ["r*N*(1 - N/K)"], [y0], [0, t1], parameters={"r": r0, "K": K}, method="LSODA")
    expected = K / (1 + (K / y0 - 1) * math.exp(-r0 * t1))
    assert r["result"]["final"]["N"] == pytest.approx(expected, rel=1e-6)


def test_undefined_name_rejected():
    with pytest.raises(ValueError, match="undefined"):
        solve_ode(["y"], ["-k*y"], [1], [0, 1])


def test_length_mismatch_rejected():
    with pytest.raises(ValueError):
        solve_ode(["x", "v"], ["v"], [1, 0], [0, 1])


def test_bad_method_rejected():
    with pytest.raises(ValueError):
        solve_ode(["y"], ["-y"], [1], [0, 1], method="Euler")
