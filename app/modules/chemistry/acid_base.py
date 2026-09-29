"""pH and pOH of strong and weak monoprotic acids/bases, including water autoionisation."""
import math

from scipy.optimize import brentq

from app.core.registry import tool

KW_25C = 1.0e-14
_KINDS = ("strong_acid", "strong_base", "weak_acid", "weak_base")


@tool(
    domain="chemistry",
    name="ph",
    description=(
        "pH, pOH, [H+] and [OH-] of an aqueous solution at 25 C. kind: strong_acid, strong_base, weak_acid "
        "(needs ka or pka) or weak_base (needs kb or pkb). concentration in mol/L. For strong acids/bases "
        "releasing several H+/OH- per formula unit set equivalents (e.g. Ba(OH)2 -> 2). "
        "Example: kind='weak_acid', concentration=0.1, ka=1.8e-5."
    ),
)
def ph(
    kind: str,
    concentration: float,
    ka: float | None = None,
    pka: float | None = None,
    kb: float | None = None,
    pkb: float | None = None,
    equivalents: int = 1,
) -> dict:
    if kind not in _KINDS:
        raise ValueError(f"kind must be one of {_KINDS}")
    if not concentration > 0:
        raise ValueError("concentration must be positive")
    if equivalents < 1:
        raise ValueError("equivalents must be >= 1")
    kw = KW_25C
    acid = kind.endswith("acid")

    if kind.startswith("strong"):
        c = concentration * equivalents
        # Charge balance with water: x^2 - c x - Kw = 0 for the dominant ion
        main = (c + math.sqrt(c * c + 4 * kw)) / 2
        ionisation = 1.0
        assumptions = ["Complete dissociation", "Water autoionisation included (matters below ~1e-6 M)"]
        k_value = None
    else:
        if equivalents != 1:
            raise ValueError("equivalents applies to strong acids/bases only (weak ones are monoprotic here)")
        k_given = (ka, pka) if acid else (kb, pkb)
        if (k_given[0] is None) == (k_given[1] is None):
            raise ValueError(f"Give exactly one of {'ka or pka' if acid else 'kb or pkb'}")
        k_value = k_given[0] if k_given[0] is not None else 10 ** (-k_given[1])
        if not k_value > 0:
            raise ValueError("Dissociation constant must be positive")
        c = concentration

        # Exact charge balance: x = K c/(K + x) + Kw/x, x = [H+] (acid) or [OH-] (base)
        def f(x):
            return x - k_value * c / (k_value + x) - kw / x

        main = brentq(f, 1e-300 + math.sqrt(kw) * 1e-3, c + math.sqrt(kw) + 1, xtol=1e-30, rtol=1e-14)
        ionisation = (k_value / (k_value + main))
        assumptions = ["Monoprotic weak acid/base, exact equilibrium with water autoionisation"]

    other = kw / main
    h, oh = (main, other) if acid else (other, main)
    p_h = -math.log10(h)
    return {
        "result": p_h,
        "pOH": -math.log10(oh),
        "h_concentration": h,
        "oh_concentration": oh,
        "percent_ionised": 100 * ionisation,
        "dissociation_constant": k_value,
        "units": "pH and pOH dimensionless; concentrations in mol/L",
        "assumptions": [*assumptions, "25 C (Kw = 1.0e-14)", "Ideal solution (activities = concentrations)"],
    }
