"""Checking a student's coefficients for a chemical equation: atom and charge tallies per side."""
from collections import Counter
from math import gcd

from app.core.registry import tool
from app.modules.chemistry.formula import element_counts, parse_equation
from app.modules.chemistry.stoichiometry import _balance, _format


@tool(
    domain="chemistry",
    name="check_balance",
    description=(
        "Check proposed whole-number coefficients for an equation: counts every element (and charge) on each side, "
        "says whether it is balanced and whether the coefficients are the smallest set, and gives the correct "
        "balanced equation. coefficients are in the order the species appear. "
        "Example: equation='H2 + O2 -> H2O', coefficients=[2,1,2]."
    ),
)
def check_balance(equation: str, coefficients: list[int]) -> dict:
    eq = parse_equation(equation)
    species = eq.species()
    if len(coefficients) != len(species):
        raise ValueError(f"need {len(species)} coefficients, one per species")
    if any(int(c) != c or c < 0 for c in coefficients):
        raise ValueError("coefficients must be whole numbers >= 0")
    left, right = Counter(), Counter()
    for c, (_, s, side) in zip(coefficients, species):
        tally = left if side < 0 else right
        for el, n in element_counts(s.formula).items():
            tally[el] += int(c) * n
        if s.charge:
            tally["charge"] += int(c) * s.charge
    elements = sorted((set(left) | set(right)) - {"charge"})
    rows = [{"element": el, "left": left[el], "right": right[el], "balanced": left[el] == right[el]} for el in elements]
    has_charge = any(s.charge for _, s, _ in species)
    if has_charge:
        rows.append({"element": "charge", "left": left["charge"], "right": right["charge"], "balanced": left["charge"] == right["charge"]})
    correct = _balance(eq)
    all_zero = all(c == 0 for c in coefficients)
    balanced = not all_zero and all(r["balanced"] for r in rows) and all(c > 0 for c in coefficients)
    g = 0
    for c in coefficients:
        g = gcd(g, int(c))
    return {
        "result": {
            "balanced": balanced,
            "smallest": balanced and g == 1,
            "multiple_of_smallest": g if balanced else None,
            "tally": rows,
            "correct_coefficients": correct,
            "correct_equation": _format(eq, correct),
            "species": [s.text for _, s, _ in species],
            "sides": [side for _, _, side in species],
        },
        "units": "atom counts (dimensionless); charge in elementary charges",
        "assumptions": ["Coefficients multiply whole formula units; every coefficient must be at least 1"],
    }
