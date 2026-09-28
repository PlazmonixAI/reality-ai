"""Numerical initial value problems for systems of first-order ODEs (scipy solve_ivp)."""
import numpy as np
import sympy as sp
from scipy.integrate import solve_ivp

from app.core.parsing import parse_expression, symbol
from app.core.registry import tool

_METHODS = ("RK45", "RK23", "DOP853", "Radau", "BDF", "LSODA")
MAX_POINTS = 10_000


@tool(
    domain="mathematics",
    name="solve_ode",
    description=(
        "Numerically solve a system of first-order ODEs dy_i/dt = f_i(t, y) from initial values. "
        "variables: state names; equations: right-hand side for each variable (may use t, the variables and "
        "any names in parameters); initial: starting values; t_span: [t0, t1]. Higher-order ODEs must be "
        "rewritten as first-order systems. Example (harmonic oscillator): variables=['x','v'], "
        "equations=['v','-omega**2*x'], parameters={'omega': 2}, initial=[1, 0], t_span=[0, 10]."
    ),
)
def solve_ode(
    variables: list[str],
    equations: list[str],
    initial: list[float],
    t_span: list[float],
    parameters: dict[str, float] | None = None,
    n_points: int = 201,
    method: str = "RK45",
    rtol: float = 1e-8,
    atol: float = 1e-10,
) -> dict:
    if not variables or len(variables) != len(equations) or len(variables) != len(initial):
        raise ValueError("variables, equations and initial must be non-empty and the same length")
    if len(set(variables)) != len(variables):
        raise ValueError("variable names must be unique")
    if len(t_span) != 2 or t_span[0] == t_span[1]:
        raise ValueError("t_span must be [t0, t1] with t0 != t1")
    if not 2 <= n_points <= MAX_POINTS:
        raise ValueError(f"n_points must be between 2 and {MAX_POINTS}")
    if method not in _METHODS:
        raise ValueError(f"method must be one of {_METHODS}")

    parameters = parameters or {}
    t = sp.Symbol("t")
    state = [symbol(v) for v in variables]
    if t in state:
        raise ValueError("'t' is reserved for time and cannot be a state variable")
    param_values = {symbol(k): float(v) for k, v in parameters.items()}

    rhs = [parse_expression(e).subs(param_values) for e in equations]
    allowed = set(state) | {t}
    for eq, expr in zip(equations, rhs):
        unknown = expr.free_symbols - allowed
        if unknown:
            raise ValueError(f"Equation {eq!r} uses undefined names: {sorted(map(str, unknown))}")

    f = sp.lambdify((t, state), rhs, modules="numpy")

    def fun(time, y):
        return np.array(f(time, y), dtype=float)

    t_eval = np.linspace(t_span[0], t_span[1], n_points)
    sol = solve_ivp(fun, t_span, np.array(initial, dtype=float), method=method,
                    t_eval=t_eval, rtol=rtol, atol=atol)
    if not sol.success:
        raise ValueError(f"ODE integration failed: {sol.message}")

    return {
        "result": {
            "t": sol.t.tolist(),
            "y": {name: sol.y[i].tolist() for i, name in enumerate(variables)},
            "final": {name: float(sol.y[i, -1]) for i, name in enumerate(variables)},
        },
        "evaluations": int(sol.nfev),
        "units": "t in the time units of the equations; each variable in its own units",
        "assumptions": [
            f"Numerical integration with scipy solve_ivp ({method}), rtol={rtol}, atol={atol}",
            f"Solution sampled at {n_points} evenly spaced times",
        ],
    }
