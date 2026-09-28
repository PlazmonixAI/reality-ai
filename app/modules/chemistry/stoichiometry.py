"""Molar mass, equation balancing and reaction stoichiometry (limiting reagent, theoretical yield)."""
import math

import sympy as sp

from app.core.registry import tool
from app.modules.chemistry.formula import (
    CHARGE_KEY, element_counts, molar_mass_of, parse_equation, split_species,
)
from app.modules.chemistry.periodic_table import ATOMIC_WEIGHTS


@tool(
    domain="chemistry",
    name="molar_mass",
    description=(
        "Molar mass (g/mol) and mass-percent composition of a chemical formula. Supports brackets and "
        "hydrates. Examples: 'H2O', 'Ca(OH)2', 'K4[Fe(CN)6]', 'CuSO4.5H2O'."
    ),
)
def molar_mass(formula: str) -> dict:
    sp_ = split_species(formula)
    counts = element_counts(sp_.formula)
    total = sum(ATOMIC_WEIGHTS[el] * n for el, n in counts.items())
    composition = {
        el: {"atoms": n, "mass_percent": 100 * ATOMIC_WEIGHTS[el] * n / total}
        for el, n in sorted(counts.items())
    }
    return {
        "result": total,
        "molar_mass_si": total / 1000,
        "composition": composition,
        "units": "g/mol (molar_mass_si in kg/mol)",
        "assumptions": ["IUPAC standard atomic weights (abridged)", "Electron mass of any ionic charge neglected"],
    }


def _balance(eq) -> list[int]:
    """Smallest positive integer coefficients conserving atoms and charge."""
    entries = eq.species()
    keys = sorted({el for _, s, _ in entries for el in element_counts(s.formula)})
    if any(s.charge for _, s, _ in entries):
        keys.append(CHARGE_KEY)
    rows = []
    for key in keys:
        row = []
        for _, s, side in entries:
            n = s.charge if key == CHARGE_KEY else element_counts(s.formula).get(key, 0)
            row.append(-side * n)  # reactants +, products -
        rows.append(row)
    null = sp.Matrix(rows).nullspace()
    if len(null) != 1:
        raise ValueError(
            "Equation cannot be balanced uniquely" if null else "Equation cannot be balanced (check formulas)"
        )
    vec = null[0]
    lcm = sp.ilcm(*[sp.fraction(v)[1] for v in vec])
    ints = [int(v * lcm) for v in vec]
    if all(v < 0 for v in ints):
        ints = [-v for v in ints]
    if any(v <= 0 for v in ints):
        raise ValueError("No balancing with all-positive coefficients; check which side each species is on")
    g = math.gcd(*ints)
    return [v // g for v in ints]


def _format(eq, coeffs) -> str:
    n = len(eq.reactants)

    def side(items, cs):
        return " + ".join((f"{c} " if c != 1 else "") + s.text + (f"({s.state})" if s.state else "")
                          for c, (_, s) in zip(cs, items))
    return f"{side(eq.reactants, coeffs[:n])} -> {side(eq.products, coeffs[n:])}"


@tool(
    domain="chemistry",
    name="balance_equation",
    description=(
        "Balance a chemical equation (atoms and charge) with the smallest whole-number coefficients. "
        "Separate species with ' + ' (spaces) and sides with '->' or '='. Ions: 'Fe^3+', 'MnO4-'. "
        "Example: 'C3H8 + O2 -> CO2 + H2O'."
    ),
)
def balance_equation(equation: str) -> dict:
    eq = parse_equation(equation)
    coeffs = _balance(eq)
    names = [s.text for _, s, _ in eq.species()]
    return {
        "result": _format(eq, coeffs),
        "coefficients": dict(zip(names, coeffs)),
        "units": "dimensionless (mole ratios)",
        "assumptions": ["Coefficients from the null space of the atom/charge conservation matrix (sympy)",
                        "Any coefficients written in the input are ignored"],
    }


@tool(
    domain="chemistry",
    name="stoichiometry",
    description=(
        "Limiting reagent and theoretical yields. equation is balanced automatically. Give the amount of each "
        "starting reactant as masses (grams) and/or moles, e.g. masses={'H2': 4, 'O2': 32}. Returns moles "
        "reacted, product amounts (mol and g) and leftover excess reactants."
    ),
)
def stoichiometry(
    equation: str,
    masses: dict[str, float] | None = None,
    moles: dict[str, float] | None = None,
) -> dict:
    eq = parse_equation(equation)
    coeffs = _balance(eq)
    entries = [(c, s, side) for c, (_, s, side) in zip(coeffs, eq.species())]
    reactants = {s.text: (c, s) for c, s, side in entries if side < 0}
    products = {s.text: (c, s) for c, s, side in entries if side > 0}

    given: dict[str, float] = {}
    for label, data, to_mol in (("masses", masses, True), ("moles", moles, False)):
        for name, amount in (data or {}).items():
            if name not in reactants:
                raise ValueError(f"{name!r} in {label} is not a reactant; reactants are {sorted(reactants)}")
            if name in given:
                raise ValueError(f"{name!r} given twice")
            if amount < 0:
                raise ValueError(f"Amount of {name!r} must be >= 0")
            given[name] = amount / molar_mass_of(name) if to_mol else float(amount)
    if not given:
        raise ValueError("Give the amount of at least one reactant (masses in g or moles)")

    # Extent of reaction is limited by the scarcest given reactant.
    extents = {name: n / reactants[name][0] for name, n in given.items()}
    limiting = min(extents, key=extents.get)
    xi = extents[limiting]

    def amounts(name, coeff, n_mol):
        mm = molar_mass_of(name)
        return {"moles": n_mol, "grams": n_mol * mm, "molar_mass": mm, "coefficient": coeff}

    return {
        "result": {
            "limiting_reagent": limiting,
            "products": {name: amounts(name, c, c * xi) for name, (c, _) in products.items()},
            "reactants_consumed": {name: amounts(name, c, c * xi) for name, (c, _) in reactants.items()},
            "excess_remaining": {name: amounts(name, reactants[name][0], n - reactants[name][0] * xi)
                                 for name, n in given.items() if name != limiting},
        },
        "balanced_equation": _format(eq, coeffs),
        "extent_of_reaction": xi,
        "units": "moles in mol, masses in g, molar masses in g/mol",
        "assumptions": [
            "Reaction goes to completion (theoretical yield, 100% efficiency)",
            "Reactants not listed are assumed to be in excess",
        ],
    }

