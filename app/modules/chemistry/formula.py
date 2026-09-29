"""Chemical formula and equation parsing. Not a tool module.

Formulas: element symbols, counts, nested () [] {}, hydrates ('CuSO4.5H2O', 'CuSO4·5H2O', 'CuSO4*5H2O'),
charges as a suffix ('Fe^3+', 'SO4^2-', 'OH-', 'Na+'), optional state ('(aq)', '(s)', '(l)', '(g)').
Equations: species separated by ' + ' (spaces required), sides by '->', '=>', '=', '<=>', '⇌' or '→'.
"""
import re
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction

from app.modules.chemistry.periodic_table import ATOMIC_WEIGHTS

_STATE = re.compile(r"\((s|l|g|aq)\)$")
_CHARGE = re.compile(r"(?:\^(\d*)([+-])|([+-]+))$")
_ARROW = re.compile(r"\s*(?:<=>|<->|⇌|->|=>|→|=)\s*")
_TOKEN = re.compile(r"([A-Z][a-z]?)|(\d+)|([(\[{])|([)\]}])")
_CLOSE = {"(": ")", "[": "]", "{": "}"}
CHARGE_KEY = "charge"


@dataclass(frozen=True)
class Species:
    text: str          # as written, without state
    formula: str       # without charge
    state: str | None  # 's', 'l', 'g', 'aq' or None
    charge: int


def split_species(text: str) -> Species:
    s = text.strip()
    state = None
    m = _STATE.search(s)
    if m:
        state, s = m.group(1), s[: m.start()].strip()
    charge = 0
    m = _CHARGE.search(s)
    if m and m.start() > 0:
        if m.group(3):
            charge = len(m.group(3)) * (1 if m.group(3)[0] == "+" else -1)
        else:
            charge = int(m.group(1) or 1) * (1 if m.group(2) == "+" else -1)
        formula = s[: m.start()]
    else:
        formula = s
    if not formula:
        raise ValueError(f"Empty formula in {text!r}")
    return Species(text=s, formula=formula, state=state, charge=charge)


def _parse_group(formula: str, pos: int, closer: str | None) -> tuple[Counter, int]:
    counts: Counter = Counter()
    while pos < len(formula):
        m = _TOKEN.match(formula, pos)
        if not m:
            raise ValueError(f"Unexpected character {formula[pos]!r} in formula {formula!r}")
        element, _digits, opener, close = m.groups()
        pos = m.end()
        if close:
            if close != closer:
                raise ValueError(f"Unbalanced brackets in formula {formula!r}")
            return counts, pos
        if element:
            if element not in ATOMIC_WEIGHTS:
                raise ValueError(f"Unknown element {element!r} in formula {formula!r}")
            sub: Counter = Counter({element: 1})
        elif opener:
            sub, pos = _parse_group(formula, pos, _CLOSE[opener])
        else:
            raise ValueError(f"Misplaced number in formula {formula!r}")
        n = re.match(r"\d+", formula[pos:])
        mult = 1
        if n:
            mult, pos = int(n.group()), pos + n.end()
            if mult == 0:
                raise ValueError(f"Zero count in formula {formula!r}")
        for k, v in sub.items():
            counts[k] += v * mult
    if closer:
        raise ValueError(f"Unclosed bracket in formula {formula!r}")
    return counts, pos


def element_counts(formula: str) -> Counter:
    """Atom counts for a neutral formula, including hydrate parts ('CuSO4.5H2O')."""
    formula = formula.strip()
    if not formula:
        raise ValueError("Empty formula")
    total: Counter = Counter()
    for part in re.split(r"[.·*•]", formula):
        part = part.strip()
        m = re.match(r"(\d+)(.*)", part)
        coeff, body = (int(m.group(1)), m.group(2)) if m else (1, part)
        if not body:
            raise ValueError(f"Empty component in formula {formula!r}")
        counts, _ = _parse_group(body, 0, None)
        for k, v in counts.items():
            total[k] += coeff * v
    return total


def molar_mass_of(formula: str) -> float:
    """Molar mass in g/mol of a formula, possibly with charge/state suffixes."""
    counts = element_counts(split_species(formula).formula)
    return sum(ATOMIC_WEIGHTS[el] * n for el, n in counts.items())


@dataclass(frozen=True)
class Equation:
    reactants: list[tuple[Fraction, Species]]
    products: list[tuple[Fraction, Species]]

    def species(self) -> list[tuple[Fraction, Species, int]]:
        """(coefficient, species, side) with side -1 for reactants, +1 for products."""
        return [(c, s, -1) for c, s in self.reactants] + [(c, s, 1) for c, s in self.products]


def _parse_side(text: str) -> list[tuple[Fraction, Species]]:
    terms = [t for t in re.split(r"\s+\+\s+", text.strip()) if t]
    if not terms:
        raise ValueError("Each side of the equation needs at least one species")
    out = []
    for term in terms:
        m = re.match(r"^(\d+(?:\.\d+)?(?:/\d+)?)\s*(.+)$", term)
        # A leading number followed by a letter or bracket is a coefficient.
        if m and re.match(r"[A-Z(\[{]", m.group(2)):
            coeff, body = Fraction(m.group(1)), m.group(2)
        else:
            coeff, body = Fraction(1), term
        if coeff <= 0:
            raise ValueError(f"Coefficient must be positive in {term!r}")
        out.append((coeff, split_species(body)))
    return out


def parse_equation(text: str) -> Equation:
    parts = _ARROW.split(text.strip())
    if len(parts) != 2:
        raise ValueError("Equation needs exactly one arrow, e.g. 'H2 + O2 -> H2O'")
    eq = Equation(_parse_side(parts[0]), _parse_side(parts[1]))
    names = [s.text for _, s, _ in eq.species()]
    if len(set(names)) != len(names):
        raise ValueError("A species appears more than once in the equation")
    return eq
