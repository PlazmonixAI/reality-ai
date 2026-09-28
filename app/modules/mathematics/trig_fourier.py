"""Exact trigonometric values on the unit circle, and Fourier series of periodic functions."""
import math

import numpy as np
import sympy as sp

from app.core.parsing import parse_expression, symbol
from app.core.registry import tool


@tool(
    domain="mathematics",
    name="trig_exact",
    symbolic=True,
    description=(
        "Unit-circle values for an angle in degrees: exact symbolic sin, cos, tan (e.g. sqrt(3)/2), their "
        "decimal values, the point (cos, sin), quadrant and reference angle. Example: angle_deg=150."
    ),
)
def trig_exact(angle_deg: float) -> dict:
    ang = sp.nsimplify(angle_deg, rational=True)
    rad = ang * sp.pi / 180
    s, c = sp.nsimplify(sp.sin(rad)), sp.nsimplify(sp.cos(rad))
    t = sp.zoo if c == 0 else sp.simplify(s / c)
    a = float(angle_deg) % 360
    quadrant = None if a % 90 == 0 else int(a // 90) + 1
    ref = min(a % 180, 180 - a % 180)
    return {
        "result": {
            "sin": str(s), "cos": str(c), "tan": "undefined" if t == sp.zoo else str(t),
            "sin_value": float(s), "cos_value": float(c), "tan_value": None if t == sp.zoo else float(t),
        },
        "radians": str(sp.nsimplify(rad)),
        "radians_value": float(rad),
        "quadrant": quadrant,
        "reference_angle_deg": ref,
        "units": "angle in degrees (radians also given); trig values dimensionless",
        "assumptions": ["Exact forms from sympy; non-special angles are shown as sin(...)/cos(...) expressions"],
    }


_PRESETS = {
    "square": lambda x, L: np.where(np.mod(x + L, 2 * L) < L, -1.0, 1.0),
    "sawtooth": lambda x, L: (np.mod(x + L, 2 * L) - L) / L,
    "triangle": lambda x, L: 1 - 2 * np.abs(np.mod(x + L, 2 * L) - L) / L,
}


@tool(
    domain="mathematics",
    name="fourier_series",
    description=(
        "Fourier series of a function with period 2L on [-L, L]: coefficients a0, a_n, b_n (numerical "
        "integration) and the partial sum with n_terms harmonics. function is 'square', 'sawtooth', 'triangle' "
        "or an expression in x (e.g. 'x^2', 'abs(sin(x))'). Returns plot-ready original and partial sum and the "
        "RMS error. Example: function='square', half_period=3.14159, n_terms=9."
    ),
)
def fourier_series(function: str, half_period: float = math.pi, n_terms: int = 5, n_points: int = 1001) -> dict:
    if half_period <= 0:
        raise ValueError("half_period must be positive")
    if not 0 <= n_terms <= 200:
        raise ValueError("n_terms must be between 0 and 200")
    if not 51 <= n_points <= 10_001:
        raise ValueError("n_points must be between 51 and 10001")
    L = float(half_period)
    if function in _PRESETS:
        f = lambda x: _PRESETS[function](x, L)                      # noqa: E731
    else:
        x_sym = symbol("x")
        expr = parse_expression(function)
        if expr.free_symbols - {x_sym}:
            raise ValueError("The expression may only use x")
        g = sp.lambdify(x_sym, expr, modules="numpy")
        f = lambda x: np.asarray(g(x), dtype=float) * np.ones_like(x)   # noqa: E731

    # Coefficients by the midpoint rule over one period: spectrally accurate for smooth periodic functions,
    # and it never samples exactly at a jump (the presets jump at 0 and +-L).
    m = 20_000
    h = 2 * L / m
    xs = -L + h * (np.arange(m) + 0.5)
    fx = f(xs)
    if not np.all(np.isfinite(fx)):
        raise ValueError("Function is not finite on [-L, L]")
    integ = lambda y: float(np.sum(y) * h)   # noqa: E731
    a0 = integ(fx) / L
    k = np.arange(1, n_terms + 1)
    a = np.array([integ(fx * np.cos(n * math.pi * xs / L)) / L for n in k])
    b = np.array([integ(fx * np.sin(n * math.pi * xs / L)) / L for n in k])

    x = np.linspace(-2 * L, 2 * L, n_points)
    partial = a0 / 2 + sum(a[i] * np.cos(k[i] * math.pi * x / L) + b[i] * np.sin(k[i] * math.pi * x / L) for i in range(n_terms)) \
        if n_terms else np.full_like(x, a0 / 2)
    original = f(x)
    rms = float(np.sqrt(np.mean((partial - original) ** 2)))
    return {
        "result": {"a0": a0, "a": a.tolist(), "b": b.tolist(), "rms_error": rms,
                   "max_partial_sum": float(np.max(partial)), "max_function": float(np.max(original))},
        "curve": {"x": x.tolist(), "function": original.tolist(), "partial_sum": partial.tolist()},
        "units": "dimensionless (same units as the function)",
        "assumptions": ["f(x) = a0/2 + sum a_n cos(n pi x / L) + b_n sin(n pi x / L)",
                        "Coefficients by the midpoint rule with 20,000 points per period"],
    }
