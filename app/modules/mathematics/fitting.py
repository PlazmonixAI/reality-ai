"""Least-squares regression: linear, polynomial, exponential, power and logarithmic models with
standard errors and R²."""
import math

import numpy as np
from scipy.optimize import curve_fit

from app.core.registry import tool

MODELS = {
    "linear": ("y = a + b x", lambda x, a, b: a + b * x),
    "exponential": ("y = a e^(b x)", lambda x, a, b: a * np.exp(b * x)),
    "power": ("y = a x^b", lambda x, a, b: a * np.power(x, b)),
    "logarithmic": ("y = a + b ln x", lambda x, a, b: a + b * np.log(x)),
}


@tool(
    domain="mathematics",
    name="least_squares_fit",
    description=(
        "Least-squares fit of data points: model 'linear', 'polynomial' (with degree), 'exponential' (a e^(bx)), "
        "'power' (a x^b) or 'logarithmic' (a + b ln x). Returns coefficients with standard errors, R², RMS error, "
        "residuals and a plot-ready fitted curve. Example: x=[1,2,3,4], y=[2.1,3.9,6.2,7.8], model='linear'."
    ),
)
def least_squares_fit(x: list[float], y: list[float], model: str = "linear", degree: int = 2, n_curve: int = 200) -> dict:
    xs, ys = np.asarray(x, float), np.asarray(y, float)
    if xs.shape != ys.shape or xs.ndim != 1:
        raise ValueError("x and y must be lists of the same length")
    if not (np.all(np.isfinite(xs)) and np.all(np.isfinite(ys))):
        raise ValueError("data must be finite numbers")
    n = len(xs)
    if not 2 <= n_curve <= 10_000:
        raise ValueError("n_curve must be between 2 and 10000")
    if model == "polynomial":
        if not 1 <= degree <= 10:
            raise ValueError("degree must be between 1 and 10")
        p = degree + 1
    elif model in MODELS:
        p = 2
    else:
        raise ValueError(f"model must be one of polynomial, {', '.join(MODELS)}")
    if n < p:
        raise ValueError(f"need at least {p} points for this model")
    if len(np.unique(xs)) < p:
        raise ValueError(f"need at least {p} distinct x values")
    if model in ("power", "logarithmic") and np.any(xs <= 0):
        raise ValueError(f"{model} model needs x > 0")

    if model in ("linear", "polynomial"):
        deg = 1 if model == "linear" else degree
        v = np.vander(xs, deg + 1, increasing=True)  # columns 1, x, x², ...
        coef, *_ = np.linalg.lstsq(v, ys, rcond=None)
        fit = v @ coef
        dof = n - (deg + 1)
        s2 = float(np.sum((ys - fit) ** 2) / dof) if dof > 0 else float("nan")
        cov = s2 * np.linalg.inv(v.T @ v) if dof > 0 else np.full((deg + 1, deg + 1), np.nan)
        f = lambda t: np.vander(np.atleast_1d(t), deg + 1, increasing=True) @ coef  # noqa: E731
        names = [f"c{i}" for i in range(deg + 1)] if model == "polynomial" else ["a", "b"]
        equation = "y = " + " + ".join(f"{c:.6g}" + ("" if i == 0 else " x" if i == 1 else f" x^{i}") for i, c in enumerate(coef))
    else:
        form, fn = MODELS[model]
        # Start from the linearised fit (ln y for exponential/power), then true least squares in y
        if model == "exponential" and np.all(ys > 0):
            b0, a0 = np.polyfit(xs, np.log(ys), 1)
            guess = [math.exp(a0), b0]
        elif model == "power" and np.all(ys > 0):
            b0, a0 = np.polyfit(np.log(xs), np.log(ys), 1)
            guess = [math.exp(a0), b0]
        elif model == "logarithmic":
            b0, a0 = np.polyfit(np.log(xs), ys, 1)
            guess = [a0, b0]
        else:
            guess = [float(np.mean(ys)) or 1.0, 0.1]
        try:
            coef, cov = curve_fit(fn, xs, ys, p0=guess, maxfev=20000)
        except RuntimeError as exc:
            raise ValueError(f"fit did not converge: {exc}") from None
        fit = fn(xs, *coef)
        f = lambda t: fn(np.atleast_1d(t), *coef)  # noqa: E731
        names = ["a", "b"]
        equation = form.replace("a", f"{coef[0]:.6g}", 1).replace("b", f"{coef[1]:.6g}", 1)
    resid = ys - fit
    ss_res = float(np.sum(resid**2))
    ss_tot = float(np.sum((ys - ys.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 1.0
    lo, hi = float(xs.min()), float(xs.max())
    pad = 0.05 * (hi - lo or 1)
    if model in ("power", "logarithmic"):
        cx = np.linspace(max(lo - pad, lo / 2), hi + pad, n_curve)
    else:
        cx = np.linspace(lo - pad, hi + pad, n_curve)
    se = np.sqrt(np.clip(np.diag(cov), 0, None)) if np.all(np.isfinite(cov)) else [None] * len(coef)
    return {
        "result": {
            "model": model,
            "equation": equation,
            "coefficients": {k: float(c) for k, c in zip(names, coef)},
            "standard_errors": {k: (float(s) if s is not None else None) for k, s in zip(names, se)},
            "r_squared": r2,
            "rms_error": math.sqrt(ss_res / n),
            "n_points": n,
        },
        "residuals": resid.tolist(),
        "fitted": fit.tolist(),
        "curve": {"x": cx.tolist(), "y": f(cx).tolist()},
        "units": "coefficients in the units implied by the model and data",
        "assumptions": ["Ordinary least squares: minimises Σ(y − ŷ)² with equal weights, errors in y only",
                        "Standard errors assume independent, normally distributed residuals"],
    }
