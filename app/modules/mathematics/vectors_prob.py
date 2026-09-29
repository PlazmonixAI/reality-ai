"""Vector operations and probability distributions (with a central-limit-theorem sampler)."""
import math

import numpy as np
from scipy import stats

from app.core.registry import tool


def _vec(v, name):
    a = np.asarray(v, dtype=float)
    if a.shape not in ((2,), (3,)) or not np.all(np.isfinite(a)):
        raise ValueError(f"{name} must have 2 or 3 finite components")
    return np.pad(a, (0, 3 - len(a)))


@tool(
    domain="mathematics",
    name="vector_operations",
    description=(
        "Operations on two vectors (2D or 3D): sum, difference, magnitudes, dot product, cross product, angle "
        "between them, and the projection of a onto b. Example: a=[3,1], b=[1,2]."
    ),
)
def vector_operations(a: list[float], b: list[float]) -> dict:
    u, v = _vec(a, "a"), _vec(b, "b")
    nu, nv = float(np.linalg.norm(u)), float(np.linalg.norm(v))
    dot = float(u @ v)
    cross = np.cross(u, v)
    angle = math.degrees(math.acos(max(-1.0, min(1.0, dot / (nu * nv))))) if nu and nv else None
    proj = (dot / (nv * nv)) * v if nv else np.zeros(3)
    return {
        "result": {
            "sum": (u + v).tolist(), "difference": (u - v).tolist(), "magnitude_a": nu, "magnitude_b": nv,
            "dot": dot, "cross": cross.tolist(), "cross_magnitude": float(np.linalg.norm(cross)),
            "angle_deg": angle, "projection_a_on_b": proj.tolist(),
            "scalar_projection": dot / nv if nv else None,
        },
        "units": "same units as the components (dot/cross in their product)",
        "assumptions": ["2D vectors are treated as 3D with z = 0 (cross product along z)"],
    }


def _dist(kind: str, params: dict):
    p = {k: float(v) for k, v in (params or {}).items()}
    try:
        if kind == "normal":
            if p.get("sd", 1) <= 0: raise ValueError
            return stats.norm(p.get("mean", 0), p.get("sd", 1)), False
        if kind == "uniform":
            lo, hi = p.get("low", 0), p.get("high", 1)
            if hi <= lo: raise ValueError
            return stats.uniform(lo, hi - lo), False
        if kind == "exponential":
            if p.get("rate", 1) <= 0: raise ValueError
            return stats.expon(scale=1 / p.get("rate", 1)), False
        if kind == "binomial":
            n, q = int(p.get("n", 10)), p.get("p", 0.5)
            if n < 1 or not 0 <= q <= 1: raise ValueError
            return stats.binom(n, q), True
        if kind == "poisson":
            if p.get("rate", 1) <= 0: raise ValueError
            return stats.poisson(p.get("rate", 1)), True
    except ValueError:
        raise ValueError(f"Invalid parameters for {kind}: {params}") from None
    raise ValueError("kind must be normal, uniform, exponential, binomial or poisson")


@tool(
    domain="mathematics",
    name="probability_distribution",
    description=(
        "Probability distribution summary and plot-ready PMF/PDF and CDF. kind: normal {mean, sd}, uniform "
        "{low, high}, exponential {rate}, binomial {n, p}, poisson {rate}. Optional interval [a, b] gives "
        "P(a <= X <= b). Example: kind='binomial', params={n:20,p:0.3}, interval=[4,8]."
    ),
)
def probability_distribution(kind: str, params: dict | None = None, interval: list[float] | None = None) -> dict:
    d, discrete = _dist(kind, params or {})
    mean, var = float(d.mean()), float(d.var())
    lo, hi = d.ppf(0.0005), d.ppf(0.9995)
    if discrete:
        x = np.arange(int(lo), int(hi) + 1)
        density = d.pmf(x)
    else:
        x = np.linspace(lo, hi, 400)
        density = d.pdf(x)
    prob = None
    if interval is not None:
        a, b = float(interval[0]), float(interval[1])
        if a > b:
            raise ValueError("interval must be [a, b] with a <= b")
        prob = float(d.cdf(b) - (d.cdf(math.ceil(a) - 1) if discrete else d.cdf(a)))
    return {
        "result": {"mean": mean, "variance": var, "sd": math.sqrt(var), "probability": prob},
        "discrete": discrete,
        "curve": {"x": x.tolist(), "density": density.tolist(), "cdf": d.cdf(x).tolist()},
        "units": "x in the variable's units; density is probability (PMF) or probability per unit (PDF)",
        "assumptions": ["scipy.stats distributions"],
    }


@tool(
    domain="mathematics",
    name="sample_means",
    description=(
        "Central limit theorem demo: draw n_samples random samples of size sample_size from a distribution "
        "(same kinds as probability_distribution), and return the histogram of sample means with the normal "
        "curve predicted by the CLT. Example: kind='exponential', params={rate:1}, sample_size=30, n_samples=2000."
    ),
)
def sample_means(kind: str, sample_size: int, n_samples: int = 2000, params: dict | None = None,
                 seed: int = 0, bins: int = 40) -> dict:
    if not 1 <= sample_size <= 1000 or not 10 <= n_samples <= 50_000 or not 5 <= bins <= 200:
        raise ValueError("sample_size 1..1000, n_samples 10..50000, bins 5..200")
    d, _ = _dist(kind, params or {})
    rng = np.random.default_rng(seed)
    means = d.rvs(size=(n_samples, sample_size), random_state=rng).mean(axis=1)
    mu, sigma = float(d.mean()), float(d.std()) / math.sqrt(sample_size)
    counts, edges = np.histogram(means, bins=bins)
    centres = (edges[:-1] + edges[1:]) / 2
    width = edges[1] - edges[0]
    return {
        "result": {"mean_of_means": float(means.mean()), "sd_of_means": float(means.std(ddof=1)),
                   "clt_mean": mu, "clt_sd": sigma,
                   "skewness": float(stats.skew(means))},
        "histogram": {"x": centres.tolist(), "density": (counts / (n_samples * width)).tolist()},
        "clt_curve": {"x": centres.tolist(), "density": stats.norm(mu, sigma).pdf(centres).tolist()},
        "units": "same units as the variable",
        "assumptions": ["Pseudo-random samples (numpy PCG64, fixed seed)", "CLT: means ~ Normal(mu, sigma/sqrt(n))"],
    }
