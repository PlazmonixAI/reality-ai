import math

import pytest
import sympy as sp

from app.modules.mathematics.calculus import differentiate, integrate, limit, series


def same(a: str, b: str) -> bool:
    return sp.simplify(sp.sympify(a) - sp.sympify(b)) == 0


def test_derivative_product_rule():
    r = differentiate("x**2*sin(x)")
    assert same(r["result"], "2*x*sin(x) + x**2*cos(x)")
    assert r["units"]


def test_second_derivative():
    assert same(differentiate("x**4", order=2)["result"], "12*x**2")


def test_derivative_other_variable():
    assert same(differentiate("exp(a*t)", variable="t")["result"], "a*exp(a*t)")


def test_derivative_bad_order():
    with pytest.raises(ValueError):
        differentiate("x", order=0)


def test_indefinite_integral():
    r = integrate("3*x**2 + cos(x)")
    assert r["definite"] is False
    assert same(r["result"], "x**3 + sin(x)")


def test_definite_integral_polynomial():
    r = integrate("x**2", lower=0, upper=3)
    assert r["numeric"] == pytest.approx(9.0)


def test_gaussian_integral():
    r = integrate("exp(-x**2)", lower="-oo", upper="oo")
    assert r["numeric"] == pytest.approx(math.sqrt(math.pi))


def test_definite_integral_symbolic_limit():
    assert integrate("sin(x)", lower=0, upper="pi")["numeric"] == pytest.approx(2.0)


def test_integral_numeric_fallback():
    # sin(sin(x)) has no elementary antiderivative; known value ~0.430606103120691
    r = integrate("sin(sin(x))", lower=0, upper=1)
    assert r["numeric"] == pytest.approx(0.430606103120691, rel=1e-9)


def test_integral_needs_both_limits():
    with pytest.raises(ValueError):
        integrate("x", lower=0)


def test_limit_sinx_over_x():
    r = limit("sin(x)/x", point=0)
    assert r["numeric"] == pytest.approx(1.0)
    assert r["exists"] is True


def test_limit_e_definition():
    assert limit("(1 + 1/n)**n", variable="n", point="oo")["numeric"] == pytest.approx(math.e)


def test_one_sided_limits():
    assert limit("1/x", point=0, direction="+")["result"] == "oo"
    assert limit("1/x", point=0, direction="-")["result"] == "-oo"


def test_limit_bad_direction():
    with pytest.raises(ValueError):
        limit("x", direction="up")


def test_series_exp():
    r = series("exp(x)", order=4)
    assert same(r["result"], "1 + x + x**2/2 + x**3/6")
    assert "O(x**4)" in r["with_order_term"]


def test_series_about_point():
    assert same(series("log(x)", point=1, order=3)["result"], "(x - 1) - (x - 1)**2/2")
