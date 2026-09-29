"""Slope fields for y' = f(x, y) and phase portraits for 2D autonomous systems, with equilibrium classification."""
import numpy as np
import sympy as sp
from scipy.integrate import solve_ivp
from scipy.optimize import fsolve

from app.core.parsing import parse_expression, symbol
from app.core.registry import tool

MAX_CURVES = 20


def _fn(expr_text: str, names: tuple[str, ...]):
    syms = [symbol(n) for n in names]
    expr = parse_expression(expr_text)
    extra = expr.free_symbols - set(syms)
    if extra:
        raise ValueError(f"Unknown symbols {sorted(map(str, extra))}; use only {', '.join(names)}")
    return expr, syms, sp.lambdify(syms, expr, modules="numpy")


def _check_ranges(x_range, y_range, grid):
    if len(x_range) != 2 or len(y_range) != 2 or x_range[0] >= x_range[1] or y_range[0] >= y_range[1]:
        raise ValueError("Ranges must be [min, max] with min < max")
    if not 5 <= grid <= 60:
        raise ValueError("grid must be between 5 and 60")


def _integrate(rhs, start, t_span, box):
    def leave(_t, z):
        return min(z[0] - box[0], box[1] - z[0], z[1] - box[2], box[3] - z[1])
    leave.terminal = True
    sol = solve_ivp(rhs, t_span, start, events=leave, max_step=abs(t_span[1] - t_span[0]) / 400, rtol=1e-8, atol=1e-10)
    return sol.y


@tool(
    domain="mathematics",
    name="slope_field",
    description=(
        "Slope field of the first-order ODE dy/dx = f(x, y) on a grid, plus solution curves through the given "
        "initial points (integrated both forwards and backwards until they leave the window). "
        "Example: expression='x - y', x_range=[-3,3], y_range=[-3,3], points=[[0,1]]."
    ),
)
def slope_field(expression: str, x_range: list[float], y_range: list[float], grid: int = 21,
                points: list[list[float]] | None = None) -> dict:
    _check_ranges(x_range, y_range, grid)
    if points and len(points) > MAX_CURVES:
        raise ValueError(f"At most {MAX_CURVES} initial points")
    _, _, f = _fn(expression, ("x", "y"))
    xs, ys = np.linspace(*x_range, grid), np.linspace(*y_range, grid)
    X, Y = np.meshgrid(xs, ys)
    with np.errstate(all="ignore"):
        S = np.asarray(f(X, Y), dtype=float) * np.ones_like(X)
    slopes = [[None if not np.isfinite(v) else float(v) for v in row] for row in S]
    box = (x_range[0] - 1e-9, x_range[1] + 1e-9, y_range[0] - (y_range[1] - y_range[0]), y_range[1] + (y_range[1] - y_range[0]))

    def rhs(_x, z):
        return [1.0, float(f(z[0], z[1]))]

    curves = []
    for p in points or []:
        back = _integrate(rhs, [float(p[0]), float(p[1])], (0, -(x_range[1] - x_range[0])), box)
        fwd = _integrate(rhs, [float(p[0]), float(p[1])], (0, x_range[1] - x_range[0]), box)
        xs_c = np.concatenate([back[0][::-1], fwd[0][1:]]); ys_c = np.concatenate([back[1][::-1], fwd[1][1:]])
        curves.append({"x": xs_c.tolist(), "y": ys_c.tolist(), "start": [float(p[0]), float(p[1])]})
    return {
        "result": {"curves": len(curves)},
        "field": {"x": xs.tolist(), "y": ys.tolist(), "slope": slopes},
        "curves": curves,
        "units": "dimensionless",
        "assumptions": ["Solution curves by RK45 (scipy solve_ivp), stopped when they leave the window"],
    }


def _classify(eig: np.ndarray) -> str:
    re, im = eig.real, eig.imag
    tol = 1e-9
    if np.all(np.abs(im) > tol):
        if np.all(np.abs(re) < tol):
            return "center"
        return "stable spiral" if np.all(re < 0) else "unstable spiral"
    if re[0] * re[1] < -tol:
        return "saddle"
    if np.all(np.abs(re) < tol) or np.any(np.abs(re) < tol):
        return "degenerate (non-isolated / needs higher-order analysis)"
    return "stable node" if np.all(re < 0) else "unstable node"


@tool(
    domain="mathematics",
    name="phase_portrait",
    description=(
        "Phase portrait of the autonomous system dx/dt = f(x, y), dy/dt = g(x, y): direction field on a grid, "
        "trajectories from initial points, and equilibrium points classified by the Jacobian's eigenvalues "
        "(node, saddle, spiral, center). Example (predator-prey): dx='x - x*y', dy='x*y - y', x_range=[0,3], "
        "y_range=[0,3], points=[[1,0.5]]."
    ),
)
def phase_portrait(dx: str, dy: str, x_range: list[float], y_range: list[float], grid: int = 21,
                   points: list[list[float]] | None = None, duration: float = 20.0) -> dict:
    _check_ranges(x_range, y_range, grid)
    if points and len(points) > MAX_CURVES:
        raise ValueError(f"At most {MAX_CURVES} initial points")
    if duration <= 0:
        raise ValueError("duration must be positive")
    ef, syms, f = _fn(dx, ("x", "y"))
    eg, _, g = _fn(dy, ("x", "y"))
    jac = sp.lambdify(syms, sp.Matrix([[sp.diff(ef, s) for s in syms], [sp.diff(eg, s) for s in syms]]), modules="numpy")

    xs, ys = np.linspace(*x_range, grid), np.linspace(*y_range, grid)
    X, Y = np.meshgrid(xs, ys)
    with np.errstate(all="ignore"):
        U = np.asarray(f(X, Y), dtype=float) * np.ones_like(X)
        V = np.asarray(g(X, Y), dtype=float) * np.ones_like(X)

    # Equilibria: fsolve from a coarse grid of starts, keep distinct converged roots inside the window.
    eq = []
    for x0 in np.linspace(*x_range, 7):
        for y0 in np.linspace(*y_range, 7):
            sol, info, ok, _ = fsolve(lambda z: [f(*z), g(*z)], [x0, y0], full_output=True)
            if ok != 1 or np.max(np.abs(info["fvec"])) > 1e-9:
                continue
            if not (x_range[0] <= sol[0] <= x_range[1] and y_range[0] <= sol[1] <= y_range[1]):
                continue
            if any(np.hypot(*(sol - e)) < 1e-6 * (1 + np.hypot(*e)) for e in eq):
                continue
            eq.append(sol)
    equilibria = []
    for e in eq:
        J = np.array(jac(*e), dtype=float)
        ev = np.linalg.eigvals(J)
        equilibria.append({"x": float(e[0]), "y": float(e[1]), "type": _classify(ev),
                           "eigenvalues": [[float(v.real), float(v.imag)] for v in ev], "jacobian": J.tolist()})

    span = max(x_range[1] - x_range[0], y_range[1] - y_range[0])
    box = (x_range[0] - span, x_range[1] + span, y_range[0] - span, y_range[1] + span)

    def rhs(_t, z):
        return [float(f(*z)), float(g(*z))]

    trajectories = []
    for p in points or []:
        z = _integrate(rhs, [float(p[0]), float(p[1])], (0, duration), box)
        trajectories.append({"x": z[0].tolist(), "y": z[1].tolist(), "start": [float(p[0]), float(p[1])]})
    return {
        "result": {"equilibria": equilibria},
        "field": {"x": xs.tolist(), "y": ys.tolist(), "u": U.tolist(), "v": V.tolist()},
        "trajectories": trajectories,
        "units": "dimensionless",
        "assumptions": ["Equilibria found numerically (fsolve from a grid) inside the window",
                        "Classification from the linearisation (Jacobian eigenvalues)"],
    }
