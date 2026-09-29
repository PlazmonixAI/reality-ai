"""Acid-base titration curves and buffers, solved exactly from the charge balance (25 C)."""
import math

import numpy as np
from scipy.optimize import brentq

from app.core.registry import tool

KW = 1.0e-14
INDICATORS = {
    "methyl orange": (3.1, 4.4), "methyl red": (4.4, 6.2), "bromothymol blue": (6.0, 7.6),
    "phenol red": (6.8, 8.4), "phenolphthalein": (8.2, 10.0), "thymolphthalein": (9.3, 10.5),
}


def _solve_h(balance) -> float:
    """[H+] from a charge-balance residual f(h) that increases with h; bracketed over pH -1..15."""
    return 10 ** brentq(lambda p: balance(10 ** p), -15.0, 1.0, xtol=1e-12)


def solution_ph(acid_total: float, acid_ka: float | None, base_total: float, base_kb: float | None,
                strong_acid: float = 0.0, strong_base: float = 0.0) -> float:
    """pH of a mixture: a monoprotic acid (total conc., Ka; None = strong), a monoprotic base (total, Kb; None =
    strong), plus extra strong acid/base, all as concentrations (M). Exact charge balance with water."""
    kbh = None if base_kb is None else KW / base_kb        # Ka of the conjugate acid BH+

    def balance(h: float) -> float:
        # positive charges - negative charges, as a function of h; increasing in h
        a_minus = acid_total if acid_ka is None else acid_total * acid_ka / (acid_ka + h)
        bh_plus = base_total if kbh is None else base_total * h / (h + kbh)
        return h + bh_plus + strong_base - KW / h - a_minus - strong_acid
    return -math.log10(_solve_h(lambda h: balance(h)))


@tool(
    domain="chemistry",
    name="titration_curve",
    description=(
        "Titration curve computed exactly from the charge balance. analyte: strong_acid, weak_acid, strong_base "
        "or weak_base (monoprotic; weak ones need pka / pkb), titrated with a strong base (for acids) or strong "
        "acid (for bases). Concentrations in mol/L, volumes in mL. Returns pH vs titrant volume, the equivalence "
        "volume and pH, the half-equivalence pH and suitable indicators. Example: analyte='weak_acid', pka=4.76, "
        "analyte_concentration=0.1, analyte_volume=25, titrant_concentration=0.1."
    ),
)
def titration_curve(
    analyte: str,
    analyte_concentration: float,
    analyte_volume: float,
    titrant_concentration: float,
    pka: float | None = None,
    pkb: float | None = None,
    max_volume: float | None = None,
    n_points: int = 301,
) -> dict:
    if analyte not in ("strong_acid", "weak_acid", "strong_base", "weak_base"):
        raise ValueError("analyte must be strong_acid, weak_acid, strong_base or weak_base")
    if min(analyte_concentration, analyte_volume, titrant_concentration) <= 0:
        raise ValueError("Concentrations and volume must be positive")
    if analyte == "weak_acid" and pka is None or analyte == "weak_base" and pkb is None:
        raise ValueError("Weak analytes need pka (acid) or pkb (base)")
    if not 11 <= n_points <= 5001:
        raise ValueError("n_points must be between 11 and 5001")
    acid = analyte.endswith("acid")
    ka = 10 ** -pka if analyte == "weak_acid" else None
    kb = 10 ** -pkb if analyte == "weak_base" else None
    n0 = analyte_concentration * analyte_volume                  # mmol
    v_eq = n0 / titrant_concentration
    vmax = max_volume or 2 * v_eq
    vols = np.linspace(0, vmax, n_points)

    def ph_at(v: float) -> float:
        vt = analyte_volume + v
        c_an, c_ti = n0 / vt, titrant_concentration * v / vt
        if acid:
            return solution_ph(c_an, ka, 0.0, None, strong_base=c_ti)
        return solution_ph(0.0, None, c_an, kb, strong_acid=c_ti)

    ph = np.array([ph_at(v) for v in vols])
    ph_eq, ph_half = ph_at(v_eq), ph_at(v_eq / 2)
    slope = np.gradient(ph, vols)
    return {
        "result": {
            "equivalence_volume": v_eq,
            "equivalence_ph": ph_eq,
            "half_equivalence_ph": ph_half,
            "initial_ph": float(ph[0]),
            "indicators": [name for name, (lo, hi) in INDICATORS.items() if lo <= ph_eq <= hi],
        },
        "curve": {"volume": vols.tolist(), "ph": ph.tolist(), "slope": slope.tolist()},
        "indicator_ranges": INDICATORS,
        "units": "volumes mL, concentrations mol/L, pH dimensionless",
        "assumptions": [
            "25 C (Kw = 1e-14), ideal solutions (activities = concentrations), volumes additive",
            "Monoprotic acid/base; titrant is a strong base (for acids) or strong acid (for bases)",
        ],
    }


@tool(
    domain="chemistry",
    name="buffer_ph",
    description=(
        "pH of a buffer of a weak acid HA and its conjugate base A- (concentrations in mol/L, volume in L), "
        "optionally after adding strong acid or base (moles). Exact charge-balance pH plus the "
        "Henderson-Hasselbalch estimate and the buffer capacity. Example: acid_concentration=0.1, "
        "base_concentration=0.1, pka=4.76, volume=1, added_acid=0.01."
    ),
)
def buffer_ph(
    acid_concentration: float,
    base_concentration: float,
    pka: float,
    volume: float = 1.0,
    added_acid: float = 0.0,
    added_base: float = 0.0,
) -> dict:
    if acid_concentration < 0 or base_concentration < 0 or volume <= 0 or added_acid < 0 or added_base < 0:
        raise ValueError("Concentrations, volume and additions must be non-negative (volume > 0)")
    ka = 10 ** -pka
    total = acid_concentration + base_concentration
    # Conjugate base arrives as its sodium salt: Na+ is a spectator equal to base_concentration.
    na = base_concentration + added_base / volume
    cl = added_acid / volume
    h = _solve_h(lambda h: h + na - KW / h - total * ka / (ka + h) - cl)
    ph = -math.log10(h)
    # Henderson-Hasselbalch with stoichiometric neutralisation
    a_eff = acid_concentration + (added_acid - added_base) / volume
    b_eff = base_concentration - (added_acid - added_base) / volume
    hh = pka + math.log10(b_eff / a_eff) if a_eff > 0 and b_eff > 0 else None
    capacity = math.log(10) * (KW / h + h + total * ka * h / (ka + h) ** 2)
    return {
        "result": ph,
        "henderson_hasselbalch": hh,
        "buffer_capacity": capacity,
        "ratio_base_to_acid": (b_eff / a_eff) if a_eff > 0 and b_eff > 0 else None,
        "h_concentration": h,
        "units": "pH dimensionless; buffer capacity mol/(L pH); concentrations mol/L",
        "assumptions": ["25 C, ideal solution; conjugate base supplied as its sodium salt",
                        "Exact charge balance (HH is shown for comparison; it fails when the buffer is exhausted)"],
    }
