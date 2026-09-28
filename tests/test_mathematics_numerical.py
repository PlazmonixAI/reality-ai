import math

import pytest

from app.modules.mathematics.numerical import find_root, optimize_function


def test_dottie_number_bracket():
    r = find_root("cos(x) - x", bracket=[0, 1])
    assert r["result"] == pytest.approx(0.7390851332151607, abs=1e-12)


def test_sqrt2_newton():
    r = find_root("x**2 = 2", x0=1)
    assert r["result"] == pytest.approx(math.sqrt(2), abs=1e-12)


def test_root_bad_bracket():
    with pytest.raises(ValueError, match="same sign"):
        find_root("x**2 + 1", bracket=[-1, 1])


def test_root_needs_bracket_or_guess():
    with pytest.raises(ValueError):
        find_root("x - 1")


def test_minimize_quadratic():
    r = optimize_function("(x-1)**2 + (y+2)**2 + 3", ["x", "y"], [0, 0])
    assert r["result"]["x"]["x"] == pytest.approx(1, abs=1e-6)
    assert r["result"]["x"]["y"] == pytest.approx(-2, abs=1e-6)
    assert r["result"]["value"] == pytest.approx(3)


def test_rosenbrock():
    r = optimize_function("(1-x)**2 + 100*(y - x**2)**2", ["x", "y"], [-1.2, 1])
    assert r["result"]["x"]["x"] == pytest.approx(1, abs=1e-4)
    assert r["result"]["x"]["y"] == pytest.approx(1, abs=1e-4)


def test_maximize():
    # Max of x*(10 - x) is 25 at x = 5
    r = optimize_function("x*(10 - x)", ["x"], [1], maximize=True)
    assert r["result"]["x"]["x"] == pytest.approx(5, abs=1e-6)
    assert r["result"]["value"] == pytest.approx(25)


def test_bounded_minimum():
    # Unconstrained min of (x-3)^2 is at 3; with x <= 1 it's at the bound
    r = optimize_function("(x-3)**2", ["x"], [0], bounds=[[None, 1]])
    assert r["result"]["x"]["x"] == pytest.approx(1, abs=1e-6)


def test_unknown_symbol_rejected():
    with pytest.raises(ValueError, match="unknown"):
        optimize_function("x + a", ["x"], [0])
