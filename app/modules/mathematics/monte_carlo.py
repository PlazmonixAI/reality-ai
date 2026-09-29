"""Monte Carlo estimation: π by random darts and definite integrals by random sampling, with the
1/√N convergence of the error."""
import math

import numpy as np
import sympy as sp
from scipy.integrate import quad

from app.core.parsing import parse_expression, symbol
from app.core.registry import tool

MAX_SAMPLES = 5_000_000


@tool(
    domain="mathematics",
    name="monte_carlo",
    description=(
        "Monte Carlo estimation with a reproducible seed. method='pi': throw n_samples darts at the unit square "
        "and count those inside the quarter circle (π ≈ 4 · inside/N). method='integral': estimate ∫_a^b f(x) dx "
        "as (b−a)·mean f(U), compared with adaptive quadrature. Returns the estimate, its standard error, a "
        "convergence curve and sample points for plotting. Example: method='pi', n_samples=10000."
    ),
)
def monte_carlo(
    method: str = "pi",
    n_samples: int = 10_000,
    expression: str | None = None,
    a: float = 0.0,
    b: float = 1.0,
    seed: int = 1,
    n_plot: int = 2000,
) -> dict:
    if not 1 <= n_samples <= MAX_SAMPLES:
        raise ValueError(f"n_samples must be between 1 and {MAX_SAMPLES}")
    if not 0 <= n_plot <= 20_000:
        raise ValueError("n_plot must be between 0 and 20000")
    rng = np.random.default_rng(seed)
    checkpoints = np.unique(np.geomspace(1, n_samples, 60).astype(int))
    if method == "pi":
        pts = rng.random((n_samples, 2))
        inside = np.sum(pts**2, axis=1) <= 1
        running = 4 * np.cumsum(inside) / np.arange(1, n_samples + 1)
        p = inside.mean()
        est, exact = 4 * p, math.pi
        se = 4 * math.sqrt(p * (1 - p) / n_samples)
        samples = {"x": pts[:n_plot, 0].tolist(), "y": pts[:n_plot, 1].tolist(), "hit": inside[:n_plot].tolist()}
        extra = {"inside": int(inside.sum())}
    elif method == "integral":
        if not expression:
            raise ValueError("method='integral' needs an expression in x")
        if not a < b:
            raise ValueError("need a < b")
        x = symbol("x")
        expr = parse_expression(expression)
        if expr.free_symbols - {x}:
            raise ValueError(f"Unknown symbols {sorted(map(str, expr.free_symbols - {x}))}")
        f = sp.lambdify(x, expr, modules="numpy")
        u = a + (b - a) * rng.random(n_samples)
        with np.errstate(all="ignore"):
            fu = np.asarray(f(u), float) * np.ones_like(u)
        if not np.all(np.isfinite(fu)):
            raise ValueError("f is undefined or infinite somewhere on [a, b]")
        vals = (b - a) * fu
        running = np.cumsum(vals) / np.arange(1, n_samples + 1)
        est = float(vals.mean())
        se = float(vals.std(ddof=1) / math.sqrt(n_samples)) if n_samples > 1 else float("nan")
        exact = quad(lambda t: float(f(t)), a, b, limit=200)[0]
        # For the plot: points under/over the curve inside the bounding box (hit-or-miss picture)
        xs = np.linspace(a, b, 400)
        with np.errstate(all="ignore"):
            fx = np.asarray(f(xs), float) * np.ones_like(xs)
        lo, hi = min(0.0, float(fx.min())), max(0.0, float(fx.max()))
        k = min(n_plot, n_samples)
        py = lo + (hi - lo) * rng.random(k)
        fk = fu[:k]
        hit = np.where(fk >= 0, (py >= 0) & (py <= fk), (py < 0) & (py >= fk))
        samples = {"x": u[:k].tolist(), "y": py.tolist(), "hit": hit.tolist(), "curve_x": xs.tolist(), "curve_y": fx.tolist()}
        extra = {}
    else:
        raise ValueError("method must be 'pi' or 'integral'")
    err = np.abs(running[checkpoints - 1] - exact)
    return {
        "result": {
            "estimate": float(est),
            "standard_error": float(se),
            "exact": float(exact),
            "error": float(est - exact),
            "error_in_standard_errors": float(abs(est - exact) / se) if se > 0 else None,
            "n_samples": n_samples,
            **extra,
        },
        "convergence": {"n": checkpoints.tolist(), "estimate": running[checkpoints - 1].tolist(), "abs_error": err.tolist(),
                        "expected_error": (se * np.sqrt(n_samples / checkpoints)).tolist()},
        "samples": samples,
        "units": "dimensionless (π) or the integral's units",
        "assumptions": ["Pseudo-random uniform samples (numpy PCG64) with the given seed",
                        "Error falls like σ/√N; the standard error is estimated from the samples"],
    }
