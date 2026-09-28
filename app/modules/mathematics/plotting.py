"""Sampling expressions for plotting (numpy)."""
import numpy as np
import sympy as sp

from app.core.parsing import parse_expression, symbol
from app.core.registry import tool

MAX_POINTS = 10_000


@tool(
    domain="mathematics",
    name="evaluate_function",
    description=(
        "Sample y = f(x) at evenly spaced points for plotting. Points where f is undefined or not real "
        "are returned as null. Optional parameters substitute named constants. "
        "Example: expression='sin(x)/x', start=-10, stop=10, n_points=400."
    ),
)
def evaluate_function(
    expression: str,
    start: float,
    stop: float,
    variable: str = "x",
    n_points: int = 400,
    parameters: dict[str, float] | None = None,
) -> dict:
    if not start < stop:
        raise ValueError("start must be less than stop")
    if not 2 <= n_points <= MAX_POINTS:
        raise ValueError(f"n_points must be between 2 and {MAX_POINTS}")
    var = symbol(variable)
    expr = parse_expression(expression).subs({symbol(k): float(v) for k, v in (parameters or {}).items()})
    extra = expr.free_symbols - {var}
    if extra:
        raise ValueError(f"Unknown symbols {sorted(map(str, extra))}; give them in parameters")
    f = sp.lambdify(var, expr, modules="numpy")
    x = np.linspace(start, stop, n_points)
    with np.errstate(all="ignore"):
        y = np.asarray(f(x.astype(complex)), dtype=complex) * np.ones_like(x)
    real = np.isfinite(y) & (np.abs(y.imag) <= 1e-12 * np.maximum(1.0, np.abs(y.real)))
    values = [float(v.real) if ok else None for v, ok in zip(y, real)]
    finite = [v for v in values if v is not None]
    return {
        "result": {"x": x.tolist(), "y": values},
        "y_range": [min(finite), max(finite)] if finite else None,
        "undefined_points": int(len(values) - len(finite)),
        "units": "x in the variable's units; y in the expression's units",
        "assumptions": ["Evaluated numerically in double precision; non-real or non-finite values are null"],
    }
