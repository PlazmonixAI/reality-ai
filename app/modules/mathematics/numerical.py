"""Numerical root finding and optimisation (scipy.optimize)."""
import numpy as np
import sympy as sp
from scipy import optimize

from app.core.parsing import parse_equation, parse_expression, symbol
from app.core.registry import tool


@tool(
    domain="mathematics",
    name="find_root",
    description=(
        "Numerically find a real root of f(x) = 0 (or 'lhs = rhs'). Give bracket=[a, b] where f changes sign "
        "(Brent's method, guaranteed), or an initial guess x0 (Newton's method). "
        "Example: expression='cos(x) - x', bracket=[0, 1]."
    ),
)
def find_root(
    expression: str,
    variable: str = "x",
    bracket: list[float] | None = None,
    x0: float | None = None,
    tol: float = 1e-12,
) -> dict:
    if bracket is None and x0 is None:
        raise ValueError("Give either bracket=[a, b] or an initial guess x0")
    expr, var = parse_equation(expression), symbol(variable)
    extra = expr.free_symbols - {var}
    if extra:
        raise ValueError(f"Expression has unknown symbols besides {variable}: {sorted(map(str, extra))}")
    f = sp.lambdify(var, expr, modules="numpy")

    if bracket is not None:
        if len(bracket) != 2:
            raise ValueError("bracket must be [a, b]")
        a, b = map(float, bracket)
        fa, fb = float(f(a)), float(f(b))
        if np.sign(fa) == np.sign(fb) and fa != 0 and fb != 0:
            raise ValueError(f"f(a)={fa:g} and f(b)={fb:g} have the same sign; bracket does not contain a root")
        sol = optimize.root_scalar(f, bracket=(a, b), method="brentq", xtol=tol)
        method = "Brent's method (scipy brentq) on the given bracket"
    else:
        fprime = sp.lambdify(var, sp.diff(expr, var), modules="numpy")
        sol = optimize.root_scalar(f, x0=float(x0), fprime=fprime, method="newton", xtol=tol)
        method = "Newton's method with exact symbolic derivative, from x0"
    if not sol.converged:
        raise ValueError(f"Root finding did not converge: {sol.flag}")
    root = float(sol.root)
    return {
        "result": root,
        "residual": float(f(root)),
        "iterations": int(sol.iterations),
        "units": "units of the variable",
        "assumptions": [method, f"Tolerance {tol}", "Returns one root; other roots may exist"],
    }


@tool(
    domain="mathematics",
    name="optimize",
    description=(
        "Numerically minimise (or maximise) a function of one or more variables. "
        "variables: names; x0: starting point; bounds: optional [low, high] per variable (null for unbounded). "
        "Example: expression='(x-1)**2 + (y+2)**2', variables=['x','y'], x0=[0,0]."
    ),
)
def optimize_function(
    expression: str,
    variables: list[str],
    x0: list[float],
    bounds: list[list[float | None] | None] | None = None,
    maximize: bool = False,
) -> dict:
    if not variables or len(variables) != len(x0):
        raise ValueError("variables and x0 must be non-empty and the same length")
    expr = parse_expression(expression)
    syms = [symbol(v) for v in variables]
    extra = expr.free_symbols - set(syms)
    if extra:
        raise ValueError(f"Expression has unknown symbols: {sorted(map(str, extra))}")

    sign = -1.0 if maximize else 1.0
    f = sp.lambdify([syms], sign * expr, modules="numpy")
    grad = sp.lambdify([syms], [sign * sp.diff(expr, s) for s in syms], modules="numpy")

    scipy_bounds = None
    if bounds is not None:
        if len(bounds) != len(variables):
            raise ValueError("bounds must have one entry per variable")
        scipy_bounds = [(None, None) if b is None else tuple(b) for b in bounds]
        for lo, hi in scipy_bounds:
            if lo is not None and hi is not None and lo > hi:
                raise ValueError(f"Invalid bound [{lo}, {hi}]: low > high")

    method = "L-BFGS-B" if scipy_bounds else "BFGS"
    res = optimize.minimize(
        lambda x: float(f(x)),
        np.array(x0, dtype=float),
        jac=lambda x: np.array(grad(x), dtype=float),
        method=method,
        bounds=scipy_bounds,
    )
    if not res.success:
        raise ValueError(f"Optimisation did not converge: {res.message}")
    return {
        "result": {
            "x": {name: float(v) for name, v in zip(variables, res.x)},
            "value": float(sign * res.fun),
        },
        "goal": "maximum" if maximize else "minimum",
        "iterations": int(res.nit),
        "units": "x in the variables' units; value in the expression's units",
        "assumptions": [
            f"Gradient-based local search ({method}) with exact symbolic gradient",
            "Finds a local optimum near x0; not guaranteed to be global",
        ],
    }
