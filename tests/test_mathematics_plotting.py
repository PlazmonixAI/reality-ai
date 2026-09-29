import math

import pytest

from app.modules.mathematics.plotting import evaluate_function


def test_samples_sine():
    r = evaluate_function("sin(x)", 0, math.pi, n_points=3)
    assert r["result"]["x"] == pytest.approx([0, math.pi / 2, math.pi])
    assert r["result"]["y"] == pytest.approx([0, 1, 0], abs=1e-12)


def test_undefined_points_are_null():
    r = evaluate_function("sqrt(x)", -1, 1, n_points=5)
    assert r["result"]["y"][:2] == [None, None]
    assert r["result"]["y"][4] == pytest.approx(1)
    assert r["undefined_points"] == 2


def test_pole_is_null():
    assert evaluate_function("1/x", -1, 1, n_points=3)["result"]["y"][1] is None


def test_parameters():
    r = evaluate_function("a*x^2 + b", 0, 2, n_points=3, parameters={"a": 3, "b": 1})
    assert r["result"]["y"] == pytest.approx([1, 4, 13])


def test_constant_expression_broadcasts():
    assert evaluate_function("5", 0, 1, n_points=4)["result"]["y"] == [5, 5, 5, 5]


def test_validation():
    with pytest.raises(ValueError):
        evaluate_function("x", 1, 0)
    with pytest.raises(ValueError, match="Unknown symbols"):
        evaluate_function("a*x", 0, 1)
