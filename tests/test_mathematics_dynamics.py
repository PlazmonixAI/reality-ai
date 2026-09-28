import math

import numpy as np
import pytest

from app.modules.mathematics.dynamics import phase_portrait, slope_field


def test_slope_field_values():
    r = slope_field("x - y", [-2, 2], [-2, 2], grid=5)
    f = r["field"]
    assert f["slope"][0][0] == pytest.approx(f["x"][0] - f["y"][0])


def test_solution_curve_matches_exact():
    # y' = x - y, y(0) = 1  ->  y = x - 1 + 2 e^{-x}
    r = slope_field("x - y", [-1, 3], [-5, 5], points=[[0, 1]])
    c = r["curves"][0]
    x, y = np.array(c["x"]), np.array(c["y"])
    assert y == pytest.approx(x - 1 + 2 * np.exp(-x), abs=1e-5)
    assert x.min() == pytest.approx(-1, abs=1e-6) and x.max() == pytest.approx(3, abs=1e-6)


def test_lotka_volterra_equilibria():
    eq = phase_portrait("x - x*y", "x*y - y", [0, 3], [0, 3])["result"]["equilibria"]
    kinds = {(round(e["x"], 6), round(e["y"], 6)): e["type"] for e in eq}
    assert kinds == {(0.0, 0.0): "saddle", (1.0, 1.0): "center"}


@pytest.mark.parametrize("dx, dy, kind", [
    ("y", "-x - 0.5*y", "stable spiral"),
    ("y", "-x + 0.5*y", "unstable spiral"),
    ("-x", "-2*y", "stable node"),
    ("x", "2*y", "unstable node"),
    ("x", "-y", "saddle"),
    ("y", "-x", "center"),
])
def test_linear_classification(dx, dy, kind):
    eq = phase_portrait(dx, dy, [-1, 1], [-1, 1])["result"]["equilibria"]
    assert len(eq) == 1 and eq[0]["type"] == kind


def test_harmonic_trajectory_is_a_circle():
    tr = phase_portrait("y", "-x", [-2, 2], [-2, 2], points=[[1, 0]], duration=2 * math.pi)["trajectories"][0]
    r = np.hypot(tr["x"], tr["y"])
    assert r == pytest.approx(1, abs=1e-6)


def test_dynamics_validation():
    with pytest.raises(ValueError):
        slope_field("x + z", [-1, 1], [-1, 1])
    with pytest.raises(ValueError):
        phase_portrait("x", "y", [1, -1], [-1, 1])
