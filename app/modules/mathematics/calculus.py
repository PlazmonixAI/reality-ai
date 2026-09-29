"""Symbolic calculus: derivatives, integrals, limits, series (sympy)."""
import sympy as sp

from app.core.parsing import parse_expression, parse_point, symbol
from app.core.registry import tool


def _numeric(expr: sp.Expr) -> float | None:
    """Float value of a closed-form result, or None if it is not a finite real number."""
    if not expr.is_number:
        return None
    value = complex(sp.N(expr))
    if value.imag != 0 or value.real in (float("inf"), float("-inf")) or value.real != value.real:
        return None
    return value.real


@tool(
    domain="mathematics",
    name="differentiate",
    symbolic=True,
    description="Symbolic derivative of an expression. Example: expression='sin(x)*x**2', variable='x', order=1.",
)
def differentiate(expression: str, variable: str = "x", order: int = 1) -> dict:
    if order < 1:
        raise ValueError("order must be >= 1")
    expr, var = parse_expression(expression), symbol(variable)
    derivative = sp.simplify(sp.diff(expr, var, order))
    return {
        "result": str(derivative),
        "latex": sp.latex(derivative),
        "units": "units of expression / units of variable^order",
        "assumptions": ["Exact symbolic differentiation (sympy.diff), result simplified"],
    }


@tool(
    domain="mathematics",
    name="integrate",
    symbolic=True,
    description=(
        "Symbolic integral. Omit lower/upper for an indefinite integral; give both for a definite one. "
        "Limits may be numbers or strings like 'pi', 'oo', '-oo'. Example: expression='exp(-x**2)', "
        "lower='-oo', upper='oo'."
    ),
)
def integrate(
    expression: str,
    variable: str = "x",
    lower: str | float | None = None,
    upper: str | float | None = None,
) -> dict:
    expr, var = parse_expression(expression), symbol(variable)
    if (lower is None) != (upper is None):
        raise ValueError("Give both lower and upper for a definite integral, or neither")

    if lower is None:
        antiderivative = sp.integrate(expr, var)
        if antiderivative.has(sp.Integral):
            raise ValueError(f"No closed-form antiderivative found for {expression!r}")
        return {
            "result": str(antiderivative),
            "latex": sp.latex(antiderivative),
            "definite": False,
            "units": "units of expression * units of variable",
            "assumptions": ["Constant of integration omitted", "Symbolic integration (sympy.integrate)"],
        }

    a, b = parse_point(lower), parse_point(upper)
    exact = sp.integrate(expr, (var, a, b))
    assumptions = ["Symbolic definite integration (sympy.integrate)"]
    numeric = None if exact.has(sp.Integral) else _numeric(exact)
    if numeric is None and exact.has(sp.Integral):
        # No closed form: fall back to adaptive numerical quadrature.
        numeric = float(sp.Integral(expr, (var, a, b)).evalf())
        exact = sp.Float(numeric)
        assumptions = ["No closed form found; value from numerical quadrature (mpmath)"]
    return {
        "result": str(exact),
        "numeric": numeric,
        "latex": sp.latex(exact),
        "definite": True,
        "units": "units of expression * units of variable",
        "assumptions": assumptions,
    }


@tool(
    domain="mathematics",
    name="limit",
    symbolic=True,
    description=(
        "Limit of an expression as variable -> point. point may be a number or 'oo'/'-oo'. "
        "direction: '+-' (two-sided), '+' (from above) or '-' (from below). Example: expression='sin(x)/x', point=0."
    ),
)
def limit(expression: str, variable: str = "x", point: str | float = 0, direction: str = "+-") -> dict:
    if direction not in ("+", "-", "+-"):
        raise ValueError("direction must be '+', '-' or '+-'")
    expr, var, p = parse_expression(expression), symbol(variable), parse_point(point)
    if p.is_infinite and direction == "+-":
        direction = "-" if p == sp.oo else "+"
    value = sp.limit(expr, var, p, dir=direction)
    return {
        "result": str(value),
        "numeric": _numeric(value),
        "exists": value.is_finite is not False and not isinstance(value, sp.AccumBounds),
        "units": "units of expression",
        "assumptions": [f"Symbolic limit (sympy.limit), direction '{direction}'"],
    }


@tool(
    domain="mathematics",
    name="series",
    symbolic=True,
    description=(
        "Taylor/Laurent series of an expression around a point, up to (not including) the given order. "
        "Example: expression='exp(x)', point=0, order=5."
    ),
)
def series(expression: str, variable: str = "x", point: str | float = 0, order: int = 6) -> dict:
    if order < 1:
        raise ValueError("order must be >= 1")
    expr, var, p = parse_expression(expression), symbol(variable), parse_point(point)
    expansion = sp.series(expr, var, p, order)
    polynomial = expansion.removeO()
    return {
        "result": str(polynomial),
        "with_order_term": str(expansion),
        "latex": sp.latex(expansion),
        "units": "units of expression",
        "assumptions": [f"Series about {p}, truncated at order {order} (sympy.series)"],
    }
