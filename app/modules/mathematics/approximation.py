"""Approximation explorers: Taylor polynomials, Riemann sums, Newton's method."""
import math

import numpy as np
import sympy as sp
from scipy.integrate import quad

from app.core.parsing import parse_expression, parse_point, symbol
from app.core.registry import tool


def _f1(expression: str, variable: str = "x"):
    x = symbol(variable)
    expr = parse_expression(expression)
    if expr.free_symbols - {x}:
        raise ValueError(f"The expression may only use {variable}")
    return x, expr, sp.lambdify(x, expr, modules="numpy")


def _samples(fn, xs):
    with np.errstate(all="ignore"):
        ys = np.asarray(fn(xs.astype(complex)), dtype=complex) * np.ones_like(xs)
    ok = np.isfinite(ys) & (np.abs(ys.imag) <= 1e-12 * np.maximum(1, np.abs(ys.real)))
    return [float(v.real) if k else None for v, k in zip(ys, ok)]


@tool(
    domain="mathematics",
    name="taylor_approximation",
    description=(
        "Taylor polynomial of f(x) about a centre up to the given order, with plot-ready samples of f and the "
        "polynomial on [start, stop] and the maximum error there. Example: expression='sin(x)', centre=0, "
        "order=7, start=-6, stop=6."
    ),
)
def taylor_approximation(expression: str, order: int, start: float, stop: float, centre: float = 0.0,
                         n_points: int = 400) -> dict:
    if not 0 <= order <= 30:
        raise ValueError("order must be 0..30")
    if not start < stop or not 2 <= n_points <= 5000:
        raise ValueError("Need start < stop and 2..5000 points")
    x, expr, fn = _f1(expression)
    c = parse_point(centre)
    coeffs = [sp.nsimplify(sp.diff(expr, x, k).subs(x, c) / sp.factorial(k)) for k in range(order + 1)]
    if any(not cf.is_finite for cf in coeffs):
        raise ValueError(f"f is not {order} times differentiable at the centre")
    p_fn = sp.lambdify(x, sum(cf * (x - c) ** k for k, cf in enumerate(coeffs)), modules="numpy")
    xs = np.linspace(start, stop, n_points)
    fy, py = _samples(fn, xs), _samples(p_fn, xs)
    errs = [abs(a - b) for a, b in zip(fy, py) if a is not None and b is not None]
    return {
        "result": {"polynomial": str(sp.expand(sum(cf * (x - c) ** k for k, cf in enumerate(coeffs)))),
                   "coefficients": [str(cf) for cf in coeffs], "max_error": max(errs) if errs else None},
        "curve": {"x": xs.tolist(), "function": fy, "polynomial": py},
        "units": "dimensionless (units of f)",
        "assumptions": ["P_n(x) = sum f^(k)(c)/k! (x - c)^k, coefficients exact (sympy)"],
    }


@tool(
    domain="mathematics",
    name="riemann_sum",
    description=(
        "Approximate the integral of f(x) on [a, b] with n subintervals by the left, right, midpoint, trapezoid "
        "or simpson rule; compares with the accurate integral and returns the shapes (rectangles/trapezoids) "
        "for drawing. Example: expression='x^2', a=0, b=2, n=8, method='midpoint'."
    ),
)
def riemann_sum(expression: str, a: float, b: float, n: int, method: str = "midpoint") -> dict:
    if method not in ("left", "right", "midpoint", "trapezoid", "simpson"):
        raise ValueError("method must be left, right, midpoint, trapezoid or simpson")
    if not a < b or not 1 <= n <= 2000:
        raise ValueError("Need a < b and 1 <= n <= 2000")
    if method == "simpson" and n % 2:
        raise ValueError("Simpson's rule needs an even n")
    _, _, fn = _f1(expression)
    f = lambda t: float(np.real(fn(complex(t))))   # noqa: E731
    edges = np.linspace(a, b, n + 1)
    h = (b - a) / n
    shapes, total = [], 0.0
    if method in ("left", "right", "midpoint"):
        for x0, x1 in zip(edges[:-1], edges[1:]):
            xs = {"left": x0, "right": x1, "midpoint": (x0 + x1) / 2}[method]
            y = f(xs)
            total += y * h
            shapes.append({"x0": float(x0), "x1": float(x1), "y0": y, "y1": y, "sample_x": float(xs)})
    elif method == "trapezoid":
        for x0, x1 in zip(edges[:-1], edges[1:]):
            y0, y1 = f(x0), f(x1)
            total += (y0 + y1) * h / 2
            shapes.append({"x0": float(x0), "x1": float(x1), "y0": y0, "y1": y1})
    else:
        ys = [f(t) for t in edges]
        total = h / 3 * (ys[0] + ys[-1] + 4 * sum(ys[1:-1:2]) + 2 * sum(ys[2:-1:2]))
        for x0, x1 in zip(edges[:-1], edges[1:]):
            shapes.append({"x0": float(x0), "x1": float(x1), "y0": f(x0), "y1": f(x1)})
    exact, _ = quad(f, a, b, limit=200)
    xs = np.linspace(a - 0.1 * (b - a), b + 0.1 * (b - a), 400)
    return {
        "result": {"approximation": total, "integral": exact, "error": total - exact},
        "shapes": shapes,
        "curve": {"x": xs.tolist(), "y": _samples(fn, xs)},
        "units": "units of f times units of x",
        "assumptions": [f"{method} rule with n = {n}", "Reference integral by adaptive quadrature (scipy quad)"],
    }


@tool(
    domain="mathematics",
    name="newton_method",
    description=(
        "Newton's method x_{n+1} = x_n - f(x_n)/f'(x_n) from x0, returning every iterate with its tangent line "
        "for drawing, whether it converged, and the observed convergence order. Example: expression='x^2 - 2', x0=1."
    ),
)
def newton_method(expression: str, x0: float, max_iter: int = 50, tol: float = 1e-12) -> dict:
    if not 1 <= max_iter <= 100:
        raise ValueError("max_iter must be 1..100")
    x, expr, fn = _f1(expression)
    dfn = sp.lambdify(x, sp.diff(expr, x), modules="numpy")
    steps, xn, status = [], float(x0), "max iterations reached"
    for _ in range(max_iter):
        fx, dfx = float(fn(xn)), float(dfn(xn))
        if not math.isfinite(fx) or not math.isfinite(dfx):
            status = "diverged (non-finite value)"; break
        if dfx == 0:
            steps.append({"x": xn, "f": fx, "slope": dfx, "next": None})
            status = "stopped: zero derivative"; break
        nxt = xn - fx / dfx
        steps.append({"x": xn, "f": fx, "slope": dfx, "next": nxt})
        if abs(nxt - xn) <= tol * max(1.0, abs(nxt)):
            xn = nxt; status = "converged"; break
        big_step = abs(nxt - xn) > 1e-6 * max(1.0, abs(nxt))
        if big_step and any(abs(nxt - s["x"]) <= 1e-9 * max(1.0, abs(nxt)) for s in steps[:-1]):
            xn = nxt; status = "cycling (no convergence)"; break
        xn = nxt
        if abs(xn) > 1e12:
            status = "diverged"; break
    # Observed order from the last three errors that are still above rounding noise.
    errs = [abs(s["x"] - xn) for s in steps]
    errs = [e for e in errs if e > 1e-10 * max(1.0, abs(xn))]
    order = None
    if status == "converged" and len(errs) >= 3:
        e1, e2, e3 = errs[-3:]
        order = math.log(e3 / e2) / math.log(e2 / e1)
    return {
        "result": {"root": xn if status == "converged" else None, "status": status, "iterations": len(steps),
                   "residual": float(fn(xn)) if math.isfinite(xn) else None, "convergence_order": order},
        "steps": steps,
        "units": "units of x",
        "assumptions": ["Exact derivative from sympy", f"Stop when the step is below {tol} (relative)"],
    }
