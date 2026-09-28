import pytest
import sympy as sp

from app.core.parsing import parse_expression, symbol


def test_parses_math():
    x = sp.Symbol("x")
    assert parse_expression("2x + x^2") == 2 * x + x**2


def test_keeps_multiletter_names():
    assert parse_expression("prey*rate").free_symbols == {sp.Symbol("prey"), sp.Symbol("rate")}


@pytest.mark.parametrize("bad", [
    "().__class__",
    "x.subs(x, 1)",
    "__import__('os')",
    "lambda: 1",
    "x; y",
    "",
    "x" * 2000,
])
def test_rejects_unsafe_input(bad):
    with pytest.raises(ValueError):
        parse_expression(bad)


@pytest.mark.parametrize("bad", ["1x", "_x", "a b", "x-y"])
def test_rejects_bad_symbol_names(bad):
    with pytest.raises(ValueError):
        symbol(bad)


def test_single_letters_are_plain_symbols():
    # N, S, Q, gamma are sympy objects by default; here they must be variables.
    expr = parse_expression("gamma*N + S + Q")
    assert {str(s) for s in expr.free_symbols} == {"gamma", "N", "S", "Q"}


def test_constants_and_functions():
    assert parse_expression("ln(E) + sin(pi/2)") == 2
