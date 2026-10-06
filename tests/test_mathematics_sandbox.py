import math

import numpy as np
import pytest
import sympy as sp

from app.core.parsing import parse_expression
from app.modules.mathematics.sandbox import sandbox


def run(*entries, **window):
    return sandbox(list(entries), **window)["result"]


def pts(item, kind):
    return sorted(p["x"] for p in item["points"] if p["kind"] == kind)


def test_roots_turning_points_and_intercept():
    r = run("y = x^2 - 2", "x^3 - 3x")
    sq, cubic = r["items"]
    assert pts(sq, "root") == pytest.approx([-math.sqrt(2), math.sqrt(2)], abs=1e-9)
    assert pts(sq, "minimum") == pytest.approx([0.0], abs=1e-6)
    assert next(p for p in sq["points"] if p["kind"] == "y-intercept")["y"] == pytest.approx(-2)
    assert pts(cubic, "maximum") == pytest.approx([-1.0], abs=1e-6)
    assert pts(cubic, "minimum") == pytest.approx([1.0], abs=1e-6)
    assert pts(cubic, "root") == pytest.approx([-math.sqrt(3), 0, math.sqrt(3)], abs=1e-9)


def test_intersections_of_two_curves():
    r = run("y = x", "y = x^2")
    xs = sorted(c["x"] for c in r["intersections"])
    assert xs == pytest.approx([0.0, 1.0], abs=1e-9)


def test_implicit_circle_lies_on_radius_three():
    r = run("x^2 + y^2 = 9")
    seg = np.array(r["items"][0]["segments"])
    assert len(seg) > 100
    rad = np.hypot(seg[:, 0], seg[:, 1])
    assert rad == pytest.approx(3.0, abs=0.02)


def test_region_below_a_line_is_half_the_window():
    r = run("y < 0", x_min=-5, x_max=5, y_min=-5, y_max=5)
    assert r["items"][0]["area_fraction"] == pytest.approx(0.5, abs=0.01)
    r = run("x^2 + y^2 <= 4", x_min=-5, x_max=5, y_min=-5, y_max=5)  # circle of area 4π in a 100-unit window
    assert r["items"][0]["area_fraction"] == pytest.approx(4 * math.pi / 100, abs=0.01)


def test_sliders_functions_and_values():
    r = run("a = 3", "f(x) = a x^2", "f(2) + 1", "y = f(x) - a", "2^10", "sqrt(-4)")
    slider, fdef, val, curve, big, imag = r["items"]
    assert slider["kind"] == "slider" and slider["value"] == 3
    assert val["value"] == pytest.approx(13)
    assert pts(curve, "root") == pytest.approx([-1, 1], abs=1e-9)
    assert big["value"] == 1024
    assert imag["value"] is None and imag["imag"] == pytest.approx(2)


def test_polar_parametric_points_and_vertical_lines():
    r = run("r = 2", "(3cos(t), 3sin(t))", "A = (1, -2)", "x = 4")
    polar, para, point, vert = r["items"]
    assert np.hypot(polar["x"], polar["y"]) == pytest.approx(2.0, abs=1e-4)  # coordinates rounded to 5 decimals
    assert np.hypot(para["x"], para["y"]) == pytest.approx(3.0, abs=1e-4)
    assert (point["label"], point["x"], point["y"]) == ("A", 1.0, -2.0)
    assert set(vert["x"]) == {4.0}


def test_asymptotes_are_not_joined():
    r = run("y = tan(x)", x_min=-3, x_max=3, y_min=-5, y_max=5)
    y = r["items"][0]["y"]
    assert any(v is None for v in y)
    assert pts(r["items"][0], "root") == pytest.approx([0.0], abs=1e-9)  # ±π are outside the window


def test_errors_are_reported_per_line():
    r = run("y = k x", "y = x +", "g(3)", "y = x")
    kinds = [i["kind"] for i in r["items"]]
    assert kinds == ["error", "error", "error", "curve"]
    assert "k = 1" in r["items"][0]["error"]
    with pytest.raises(ValueError):
        sandbox(["y = x"], x_min=1, x_max=0)
    with pytest.raises(ValueError):
        sandbox(["x"] * 31)


def test_parse_expression_with_user_functions():
    x = sp.Symbol("x")
    assert parse_expression("f(3) + 1", functions={"f": sp.Lambda(x, x**2)}) == 10
    with pytest.raises(ValueError):
        parse_expression("f(1)", functions={"__f": sp.Lambda(x, x)})
