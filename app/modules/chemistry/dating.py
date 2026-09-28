"""Radiometric dating: ages from the remaining parent fraction or the daughter/parent ratio."""
import math

import numpy as np

from app.core.registry import tool

YEAR = 365.25 * 86400
# Parent → daughter systems: half-life (years), fraction of decays that give the measured daughter
SYSTEMS = {
    "C-14": ("N-14", 5730.0, 1.0),
    "K-40/Ar-40": ("Ar-40", 1.248e9, 0.1072),
    "U-238/Pb-206": ("Pb-206", 4.468e9, 1.0),
    "U-235/Pb-207": ("Pb-207", 7.04e8, 1.0),
    "Rb-87/Sr-87": ("Sr-87", 4.97e10, 1.0),
}


@tool(
    domain="chemistry",
    name="radiometric_dating",
    description=(
        "Radiometric (carbon) dating: how old a sample is (bone, wood, fossil, rock) from radioactive decay and its "
        "half-life. system: " + ", ".join(SYSTEMS) + " (or give half_life_years). "
        "Give fraction_remaining (parent left / parent at start, e.g. C-14 activity ratio) or daughter_parent_ratio "
        "(radiogenic daughter atoms per parent atom). Optional relative_error on the measurement gives an age range. "
        "Example: system='C-14', fraction_remaining=0.25 -> 11460 years."
    ),
)
def radiometric_dating(
    system: str = "C-14",
    fraction_remaining: float | None = None,
    daughter_parent_ratio: float | None = None,
    half_life_years: float | None = None,
    relative_error: float = 0.0,
    n_points: int = 300,
) -> dict:
    if half_life_years is None:
        if system not in SYSTEMS:
            raise ValueError(f"system must be one of {', '.join(SYSTEMS)} (or give half_life_years)")
        daughter, half, branch = SYSTEMS[system]
    else:
        if half_life_years <= 0:
            raise ValueError("half_life_years must be positive")
        daughter, half, branch = "daughter", half_life_years, 1.0
    if (fraction_remaining is None) == (daughter_parent_ratio is None):
        raise ValueError("give exactly one of fraction_remaining or daughter_parent_ratio")
    if not 0 <= relative_error < 1:
        raise ValueError("relative_error must be in [0, 1)")
    lam = math.log(2) / half

    def age(f=None, r=None):
        if f is not None:
            return -math.log(f) / lam
        # D* = branch · (P0 − P) = branch · P (e^{λt} − 1) → t = ln(1 + r/branch)/λ
        return math.log(1 + r / branch) / lam

    if fraction_remaining is not None:
        if not 0 < fraction_remaining <= 1:
            raise ValueError("fraction_remaining must be in (0, 1]")
        t = age(f=fraction_remaining)
        lo, hi = age(f=min(1.0, fraction_remaining * (1 + relative_error))), age(f=fraction_remaining * (1 - relative_error))
        f_now = fraction_remaining
    else:
        if daughter_parent_ratio < 0:
            raise ValueError("daughter_parent_ratio must be >= 0")
        t = age(r=daughter_parent_ratio)
        lo, hi = age(r=daughter_parent_ratio * (1 - relative_error)), age(r=daughter_parent_ratio * (1 + relative_error))
        f_now = math.exp(-lam * t)
    span = max(3 * half, 1.3 * t)
    ts = np.linspace(0, span, n_points)
    parent = np.exp(-lam * ts)
    return {
        "result": {
            "age_years": t,
            "age_range_years": [lo, hi],
            "half_lives_elapsed": t / half,
            "half_life_years": half,
            "decay_constant_per_year": lam,
            "fraction_remaining": f_now,
            "daughter_parent_ratio": branch * (1 / f_now - 1),
            "daughter": daughter,
            "useful_range_years": [0.01 * half, 10 * half],
        },
        "curve": {"t_years": ts.tolist(), "parent_fraction": parent.tolist(), "daughter_per_initial_parent": (branch * (1 - parent)).tolist()},
        "units": "times in years; fractions and ratios dimensionless",
        "assumptions": ["Closed system: no parent or daughter gained or lost since formation",
                        "No daughter present at the start (or it has been corrected for)",
                        "K-40 → Ar-40 uses the 10.72 % electron-capture branch"],
    }
