import math

import numpy as np
import pytest

from app.modules.physics.electrostatics import K_E, coulomb_force, electric_field


def test_coulomb_force():
    r = coulomb_force(1e-6, 1e-6, 1.0)
    assert r["result"] == pytest.approx(8.9875517923e-3)
    assert r["nature"] == "repulsive"
    assert coulomb_force(1e-6, -2e-6, 0.05)["nature"] == "attractive"


def test_point_charge_field_and_potential():
    r = electric_field([{"q": 1e-9, "x": 0, "y": 0}], [-2, 2], [-2, 2], points=[[1, 0], [0, 2]])
    p1, p2 = r["result"]["probes"]
    assert p1["magnitude"] == pytest.approx(K_E * 1e-9)
    assert p1["ex"] == pytest.approx(K_E * 1e-9) and p1["ey"] == pytest.approx(0, abs=1e-12)
    assert p1["potential"] == pytest.approx(K_E * 1e-9)
    assert p2["magnitude"] == pytest.approx(K_E * 1e-9 / 4)


def test_dipole_superposition():
    q, d = 2e-9, 0.4
    charges = [{"q": q, "x": -d / 2, "y": 0}, {"q": -q, "x": d / 2, "y": 0}]
    r = electric_field(charges, [-1, 1], [-1, 1], points=[[0, 0], [0, 0.7]])
    mid, bis = r["result"]["probes"]
    assert mid["ex"] == pytest.approx(2 * K_E * q / (d / 2) ** 2)      # both fields point + -> -
    assert bis["potential"] == pytest.approx(0, abs=1e-9)               # bisector is equipotential
    assert bis["ey"] == pytest.approx(0, abs=1e-6)


def test_dipole_field_lines_end_on_negative_charge():
    charges = [{"q": 1e-9, "x": -0.5, "y": 0}, {"q": -1e-9, "x": 0.5, "y": 0}]
    lines = electric_field(charges, [-2, 2], [-1.5, 1.5], lines_per_charge=12)["field_lines"]
    assert len(lines) == 12
    ends_at_neg = sum(math.hypot(l[-1][0] - 0.5, l[-1][1]) < 0.1 for l in lines)
    assert ends_at_neg >= 8


def test_field_lines_follow_field():
    charges = [{"q": 1e-9, "x": 0, "y": 0}]
    lines = electric_field(charges, [-1, 1], [-1, 1], lines_per_charge=8)["field_lines"]
    for l in lines:   # radial lines from a lone charge: direction stays constant
        a0 = math.atan2(l[1][1], l[1][0]); a1 = math.atan2(l[-1][1], l[-1][0])
        assert abs(math.remainder(a1 - a0, 2 * math.pi)) < 1e-3


def test_grid_shapes():
    r = electric_field([{"q": 1e-9, "x": 0, "y": 0}], [-2, 2], [-1, 1], grid=40)
    g = r["grid"]
    assert len(g["x"]) == 40 and len(g["y"]) == 20
    assert np.array(g["potential"]).shape == (20, 40)


def test_electrostatics_validation():
    with pytest.raises(ValueError):
        electric_field([], [-1, 1], [-1, 1])
    with pytest.raises(ValueError):
        electric_field([{"q": 1, "x": 0, "y": 0}], [1, -1], [-1, 1])
    with pytest.raises(ValueError):
        coulomb_force(1, 1, 0)
