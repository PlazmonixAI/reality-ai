import math

import numpy as np
import pytest

from app.modules.mathematics.approximation import newton_method, riemann_sum, taylor_approximation
from app.modules.mathematics.complex_linear import complex_numbers, linear_transform_2d


def test_taylor_sine():
    r = taylor_approximation("sin(x)", 5, -1, 1)
    assert r["result"]["coefficients"] == ["0", "1", "0", "-1/6", "0", "1/120"]
    # Lagrange bound on [-1, 1]: |error| <= 1/7!
    assert r["result"]["max_error"] <= 1 / math.factorial(7) + 1e-12


def test_taylor_about_a_point():
    r = taylor_approximation("exp(x)", 3, 0, 2, centre=1)
    assert r["result"]["coefficients"] == ["E", "E", "E/2", "E/6"]
    x = np.array(r["curve"]["x"]); p = np.array(r["curve"]["polynomial"], dtype=float)
    f = np.array(r["curve"]["function"], dtype=float)
    k = np.argmin(abs(x - 1))
    assert p[k] == pytest.approx(f[k], abs=1e-8)            # agree to 4th order near the centre


def test_taylor_error_shrinks_with_order():
    e3 = taylor_approximation("cos(x)", 4, -2, 2)["result"]["max_error"]
    e9 = taylor_approximation("cos(x)", 10, -2, 2)["result"]["max_error"]
    assert e9 < e3 / 1000


@pytest.mark.parametrize("method, expected", [
    ("left", 2.1875), ("right", 3.1875), ("midpoint", 2.65625), ("trapezoid", 2.6875), ("simpson", 8 / 3),
])
def test_riemann_rules_x_squared(method, expected):
    r = riemann_sum("x^2", 0, 2, 8, method)["result"]
    assert r["approximation"] == pytest.approx(expected)
    assert r["integral"] == pytest.approx(8 / 3)


def test_midpoint_error_order_two():
    e1 = abs(riemann_sum("exp(x)", 0, 1, 10, "midpoint")["result"]["error"])
    e2 = abs(riemann_sum("exp(x)", 0, 1, 20, "midpoint")["result"]["error"])
    assert e1 / e2 == pytest.approx(4, rel=0.01)


def test_riemann_validation():
    with pytest.raises(ValueError):
        riemann_sum("x", 0, 1, 3, "simpson")
    with pytest.raises(ValueError):
        riemann_sum("x", 1, 0, 4)


def test_newton_sqrt2_quadratic():
    r = newton_method("x^2 - 2", 1)["result"]
    assert r["root"] == pytest.approx(math.sqrt(2), abs=1e-14)
    assert r["convergence_order"] == pytest.approx(2, abs=0.1)


def test_newton_double_root_is_linear_and_cycle_detected():
    r = newton_method("(x-1)^2", 3)["result"]
    assert r["status"] == "converged" and r["root"] == pytest.approx(1, abs=1e-9)
    assert newton_method("x^3 - 2*x + 2", 0)["result"]["status"].startswith("cycling")


def test_complex_product_and_roots():
    r = complex_numbers([1, 1], [0, 2], 4)["result"]
    assert r["product"] == pytest.approx([-2, 2]) and r["quotient"] == pytest.approx([0.5, -0.5])
    assert r["product_polar"]["argument_deg"] == pytest.approx(135)
    roots = [complex(*z) for z in r["roots"]]
    assert all(abs(z**4 - complex(1, 1)) < 1e-12 for z in roots)
    assert len({round(z.real, 9) + 1j * round(z.imag, 9) for z in roots}) == 4


@pytest.mark.parametrize("m, kind, det", [
    ([[0, -1], [1, 0]], "rotation", 1), ([[1, 0], [0, -1]], "reflection", -1), ([[1, 1], [0, 1]], "shear", 1),
    ([[1, 2], [2, 4]], "projection onto a line (singular)", 0), ([[3, 0], [0, 3]], "uniform scaling", 9),
])
def test_linear_transform_types(m, kind, det):
    r = linear_transform_2d(m)["result"]
    assert r["type"] == kind and r["determinant"] == pytest.approx(det, abs=1e-12)


def test_eigenvectors_are_invariant():
    r = linear_transform_2d([[2, 1], [1, 2]])["result"]
    A = np.array([[2, 1], [1, 2]])
    for e in r["eigen"]:
        assert A @ np.array(e["vector"]) == pytest.approx(e["value"] * np.array(e["vector"]))
    assert sorted(e["value"] for e in r["eigen"]) == pytest.approx([1, 3])
