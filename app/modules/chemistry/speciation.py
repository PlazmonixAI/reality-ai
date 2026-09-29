"""Polyprotic acids: fractions of each protonation state (α) vs pH, and the pH of the acid solution."""
import math

import numpy as np
from scipy.optimize import brentq

from app.core.registry import tool

KW = 1.0e-14  # at 25 °C


def alphas(ph: np.ndarray, pkas: list[float]) -> np.ndarray:
    """Fractions α_j (j protons removed) for H_nA at each pH; shape (n+1, len(ph))."""
    h = 10.0 ** (-np.atleast_1d(np.asarray(ph, float)))
    ka = 10.0 ** (-np.asarray(pkas, float))
    # term_j = [H+]^(n−j) · K1…Kj, computed in logs to avoid overflow
    n = len(pkas)
    logs = []
    cum = 0.0
    for j in range(n + 1):
        if j:
            cum += math.log(ka[j - 1])
        logs.append((n - j) * np.log(h) + cum)
    logs = np.array(logs)
    logs -= logs.max(axis=0)
    t = np.exp(logs)
    return t / t.sum(axis=0)


@tool(
    domain="chemistry",
    name="acid_speciation",
    description=(
        "Speciation of a polyprotic acid H_nA with the given pKa values (ascending) at 25 °C: the fraction of each "
        "form (H_nA … A^n−) across pH 0–14, the fractions at a chosen pH, the average number of protons bound, and "
        "the pH of a solution of the pure acid at concentration (mol/L). Example: pkas=[2.15, 7.20, 12.35] (phosphoric acid)."
    ),
)
def acid_speciation(pkas: list[float], concentration: float = 0.1, ph: float | None = None, n_points: int = 281) -> dict:
    if not 1 <= len(pkas) <= 6:
        raise ValueError("give 1 to 6 pKa values")
    if any(b < a for a, b in zip(pkas, pkas[1:])):
        raise ValueError("pKa values must be in ascending order")
    if concentration <= 0:
        raise ValueError("concentration must be positive (mol/L)")
    if not 10 <= n_points <= 5000:
        raise ValueError("n_points must be between 10 and 5000")
    n = len(pkas)
    grid = np.linspace(0, 14, n_points)
    frac = alphas(grid, pkas)

    # pH of the pure acid: charge balance [H+] = [OH−] + C Σ j α_j
    def balance(p):
        a = alphas(np.array([p]), pkas)[:, 0]
        h = 10.0**-p
        return h - KW / h - concentration * sum(j * a[j] for j in range(n + 1))

    ph_acid = brentq(balance, -2, 14, xtol=1e-12)
    at = None
    if ph is not None:
        a = alphas(np.array([ph]), pkas)[:, 0]
        at = {"ph": ph, "fractions": a.tolist(), "dominant": int(np.argmax(a)),
              "protons_bound": float(sum((n - j) * a[j] for j in range(n + 1)))}
    sub, sup = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉"), str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
    names = []
    for j in range(n + 1):
        hcount = n - j
        h = "" if hcount == 0 else "H" if hcount == 1 else "H" + str(hcount).translate(sub)
        charge = "" if j == 0 else "⁻" if j == 1 else str(j).translate(sup) + "⁻"
        names.append(f"{h}A{charge}")
    return {
        "result": {
            "species": names,
            "ph_of_acid_solution": ph_acid,
            "at_ph": at,
            "crossover_ph": list(pkas),
            "max_intermediate_fraction": [float(frac[j].max()) for j in range(1, n)],
        },
        "curves": {"ph": grid.tolist(), "fractions": frac.tolist()},
        "units": "fractions dimensionless; concentration in mol/L",
        "assumptions": ["Ideal solution (activities = concentrations), 25 °C, Kw = 1.0e-14",
                        "Adjacent species have equal fractions where pH = pKa"],
    }
