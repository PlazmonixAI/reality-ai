"""Chemical equilibrium: ICE-table solver for any stoichiometry, Kc <-> Kp conversion."""
import math

from scipy.optimize import brentq

from app.core.registry import tool
from app.modules.chemistry.formula import parse_equation

R_L_BAR = 0.08314462618  # L bar / (mol K)


def _log_q(nu: list[float], conc: list[float]) -> float:
    total = 0.0
    for n, c in zip(nu, conc):
        if c <= 0:
            return -math.inf if n > 0 else math.inf
        total += n * math.log(c)
    return total


@tool(
    domain="chemistry",
    name="equilibrium_ice",
    description=(
        "Solve an ICE table: equilibrium amounts from initial amounts and K. equation uses given coefficients "
        "(e.g. 'N2 + 3 H2 <=> 2 NH3'); solids/liquids marked (s)/(l) are left out of K. initial: starting "
        "concentrations (M, for Kc) or partial pressures (bar, for Kp); missing species start at 0. "
        "Example: equation='H2 + I2 <=> 2 HI', k=50.5, initial={'H2': 1, 'I2': 1}."
    ),
)
def equilibrium_ice(equation: str, k: float, initial: dict[str, float], kind: str = "Kc") -> dict:
    if not k > 0:
        raise ValueError("Equilibrium constant k must be positive")
    if kind not in ("Kc", "Kp"):
        raise ValueError("kind must be 'Kc' (concentrations, M) or 'Kp' (partial pressures, bar)")
    eq = parse_equation(equation)
    tracked = [(float(c) * side, s.text) for c, s, side in eq.species() if s.state not in ("s", "l")]
    names = [n for _, n in tracked]
    unknown = set(initial) - set(names)
    if unknown:
        raise ValueError(f"Unknown species in initial: {sorted(unknown)}; expected some of {names}")
    if not any(nu < 0 for nu, _ in tracked) and not any(nu > 0 for nu, _ in tracked):
        raise ValueError("No aqueous or gaseous species to put in the equilibrium expression")
    nu = [n for n, _ in tracked]
    c0 = [float(initial.get(name, 0.0)) for name in names]
    if any(c < 0 for c in c0):
        raise ValueError("Initial amounts must be >= 0")
    ln_k = math.log(k)

    # Extent x is limited by reactants running out (upper) and products running out (lower).
    upper = min((c / -n for n, c in zip(nu, c0) if n < 0), default=math.inf)
    lower = max((-c / n for n, c in zip(nu, c0) if n > 0), default=-math.inf)
    if upper <= lower:
        raise ValueError("No reaction possible: every tracked species on one side starts at zero")

    def from_bound(x_bound: float, direction: int):
        """Concentrations as bound + direction*y, with the species that hit zero at the bound set to exactly 0."""
        base = [c + n * x_bound for n, c in zip(nu, c0)]
        scale = max(max(c0), 1e-300)
        base = [0.0 if abs(b) <= 1e-12 * scale else b for b in base]
        return lambda y: [b + direction * n * y for n, b in zip(nu, base)]

    def solve(x_bound: float, direction: int, y_hi: float) -> float:
        conc = from_bound(x_bound, direction)

        def g(y):
            return direction * (_log_q(nu, conc(y)) - ln_k)
        while g(y_hi) < 0:  # unbounded side: expand until the root is bracketed
            y_hi *= 2
            if y_hi > 1e300:
                raise ValueError("Could not bracket the equilibrium")
        y_lo = y_hi * 1e-200
        if g(y_lo) > 0:
            return y_lo
        return brentq(g, y_lo, y_hi, xtol=1e-300, rtol=1e-15, maxiter=1000)

    if math.isfinite(lower) and math.isfinite(upper):
        mid = (lower + upper) / 2
        f_mid = _log_q(nu, [c + n * mid for n, c in zip(nu, c0)]) - ln_k
        if f_mid >= 0:
            y = solve(lower, 1, (upper - lower) / 2)
            conc = from_bound(lower, 1)(y)
            x = lower + y
        else:
            y = solve(upper, -1, (upper - lower) / 2)
            conc = from_bound(upper, -1)(y)
            x = upper - y
    elif math.isfinite(lower):
        y = solve(lower, 1, max(max(c0), 1.0))
        conc, x = from_bound(lower, 1)(y), lower + y
    else:
        y = solve(upper, -1, max(max(c0), 1.0))
        conc, x = from_bound(upper, -1)(y), upper - y

    q = math.exp(_log_q(nu, conc))
    unit = "M" if kind == "Kc" else "bar"
    reactant_names = [nm for n, nm in tracked if n < 0]
    conversion = {nm: (c0[i] - conc[i]) / c0[i] for i, nm in enumerate(names)
                  if nm in reactant_names and c0[i] > 0}
    return {
        "result": {name: c for name, c in zip(names, conc)},
        "extent": x,
        "direction": "forward" if x > 0 else "reverse" if x < 0 else "at equilibrium",
        "reaction_quotient_check": q,
        "fraction_converted": conversion,
        "units": f"equilibrium {'concentrations in M' if kind == 'Kc' else 'partial pressures in bar'}; "
                 f"extent in {unit}",
        "assumptions": [
            f"Ideal behaviour ({kind} written with {'concentrations' if kind == 'Kc' else 'partial pressures'})",
            "Pure solids and liquids have activity 1 and are omitted",
            "Constant temperature and volume",
        ],
    }


@tool(
    domain="chemistry",
    name="kc_kp_convert",
    description=(
        "Convert between Kc (mol/L) and Kp (bar): Kp = Kc (RT)^dn, dn = moles gas products - moles gas reactants. "
        "Give equation (gas species marked (g); if no states are marked, all species count) or delta_n. "
        "Example: k=0.5, from_kind='Kc', equation='N2(g) + 3 H2(g) <=> 2 NH3(g)', temperature=673."
    ),
)
def kc_kp_convert(
    k: float,
    temperature: float,
    from_kind: str = "Kc",
    equation: str | None = None,
    delta_n: float | None = None,
) -> dict:
    if not k > 0 or not temperature > 0:
        raise ValueError("k and temperature (K) must be positive")
    if from_kind not in ("Kc", "Kp"):
        raise ValueError("from_kind must be 'Kc' or 'Kp'")
    if (equation is None) == (delta_n is None):
        raise ValueError("Give either equation or delta_n")
    if equation is not None:
        eq = parse_equation(equation)
        entries = eq.species()
        any_states = any(s.state for _, s, _ in entries)
        delta_n = float(sum(side * c for c, s, side in entries if (s.state == "g" or not any_states)))
    factor = (R_L_BAR * temperature) ** delta_n
    converted = k * factor if from_kind == "Kc" else k / factor
    return {
        "result": converted,
        "to_kind": "Kp" if from_kind == "Kc" else "Kc",
        "delta_n": delta_n,
        "units": "Kp referenced to 1 bar, Kc to 1 mol/L (dimensionless ratios)",
        "assumptions": ["Ideal gases", f"R = {R_L_BAR} L bar/(mol K)"],
    }
