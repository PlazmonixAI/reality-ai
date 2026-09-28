import pytest

from app.modules.mathematics.algebra import solve_equation


def test_quadratic_roots():
    assert sorted(solve_equation("x**2 - 4 = 0")["result"]) == ["-2", "2"]


def test_other_variable_and_complex_roots():
    assert solve_equation("2*t + 6", variable="t")["result"] == ["-3"]
    assert sorted(solve_equation("x**2 + 1 = 0")["result"]) == ["-I", "I"]


def test_bad_input():
    with pytest.raises(ValueError):
        solve_equation("x**2 = (")
