"""Build an atom: element, charge, isotope stability, electron configuration, nuclear binding energy."""
from app.core.registry import tool
from app.modules.chemistry.periodic_table import ATOMIC_WEIGHTS

SYMBOLS = list(ATOMIC_WEIGHTS)          # the table is ordered by atomic number
NAMES = ("Hydrogen Helium Lithium Beryllium Boron Carbon Nitrogen Oxygen Fluorine Neon Sodium Magnesium "
         "Aluminium Silicon Phosphorus Sulfur Chlorine Argon Potassium Calcium").split()
# Stable (or observationally stable) mass numbers for Z = 1..20.
STABLE = {
    1: (1, 2), 2: (3, 4), 3: (6, 7), 4: (9,), 5: (10, 11), 6: (12, 13), 7: (14, 15), 8: (16, 17, 18), 9: (19,),
    10: (20, 21, 22), 11: (23,), 12: (24, 25, 26), 13: (27,), 14: (28, 29, 30), 15: (31,), 16: (32, 33, 34, 36),
    17: (35, 37), 18: (36, 38, 40), 19: (39, 41), 20: (40, 42, 43, 44, 46, 48),
}
MAX_Z = 20
_L = "spdf"


def electron_configuration(n_electrons: int) -> list[tuple[int, str, int]]:
    """Subshell filling by the Madelung (n + l) rule: [(n, 'p', count), ...]."""
    order = sorted(((n, l) for n in range(1, 8) for l in range(0, min(n, 4))), key=lambda nl: (nl[0] + nl[1], nl[0]))
    out, left = [], n_electrons
    for n, l in order:
        if left <= 0:
            break
        k = min(left, 2 * (2 * l + 1))
        out.append((n, _L[l], k))
        left -= k
    return out


def binding_energy_mev(z: int, n: int) -> float:
    """Semi-empirical (Weizsaecker) mass formula, MeV."""
    a = z + n
    av, as_, ac, aa, ap = 15.75, 17.8, 0.711, 23.7, 11.18
    pair = 0.0 if a % 2 else (ap / a**0.5 if z % 2 == 0 else -ap / a**0.5)
    return av * a - as_ * a ** (2 / 3) - ac * z * (z - 1) / a ** (1 / 3) - aa * (n - z) ** 2 / a + pair


@tool(
    domain="chemistry",
    name="nuclear_binding_energy",
    description=(
        "Nuclear binding energy from the semi-empirical mass formula for a nucleus with Z protons and N neutrons "
        "(total and per nucleon, MeV). Example: protons=26, neutrons=30 (iron-56)."
    ),
)
def nuclear_binding_energy(protons: int, neutrons: int) -> dict:
    if protons < 1 or neutrons < 0 or protons + neutrons < 2:
        raise ValueError("Need at least one proton and a mass number >= 2")
    be = binding_energy_mev(protons, neutrons)
    return {
        "result": be,
        "per_nucleon": be / (protons + neutrons),
        "units": "MeV",
        "assumptions": ["Liquid-drop (Weizsaecker) formula; accurate to ~1% for medium/heavy nuclei, poor for very light ones"],
    }


@tool(
    domain="chemistry",
    name="atom_builder",
    description=(
        "Describe an atom or ion built from protons, neutrons and electrons (up to 20 protons): element, mass "
        "number, charge, isotope notation, whether the nucleus is stable, electron configuration, shell "
        "populations and binding energy. Example: protons=6, neutrons=6, electrons=6."
    ),
)
def atom_builder(protons: int, neutrons: int, electrons: int) -> dict:
    if not 0 <= protons <= MAX_Z or neutrons < 0 or electrons < 0:
        raise ValueError(f"protons must be 0..{MAX_Z}; neutrons and electrons must be >= 0")
    if neutrons > 30 or electrons > 30:
        raise ValueError("At most 30 neutrons and 30 electrons")
    a, charge = protons + neutrons, protons - electrons
    config = electron_configuration(electrons)
    shells: dict[int, int] = {}
    for n, _, k in config:
        shells[n] = shells.get(n, 0) + k
    if protons == 0:
        element = None
    else:
        element = {"symbol": SYMBOLS[protons - 1], "name": NAMES[protons - 1],
                   "standard_atomic_weight": ATOMIC_WEIGHTS[SYMBOLS[protons - 1]]}
    stable = protons > 0 and a in STABLE[protons]
    sign = "" if charge == 0 else (f"{abs(charge) if abs(charge) > 1 else ''}{'+' if charge > 0 else '-'}")
    be = binding_energy_mev(protons, neutrons) if protons and a >= 2 else None
    return {
        "result": {
            "element": element,
            "mass_number": a,
            "charge": charge,
            "notation": f"{element['symbol']}-{a}{('^' + sign) if sign else ''}" if element else None,
            "is_ion": charge != 0,
            "stable_nucleus": stable if protons else None,
            "electron_configuration": " ".join(f"{n}{l}{k}" for n, l, k in config),
            "shells": [shells[n] for n in sorted(shells)],
            "valence_electrons": shells[max(shells)] if shells else 0,
        },
        "binding_energy": {"total": be, "per_nucleon": be / a if be is not None else None},
        "units": "charge in elementary charges, binding energy MeV, atomic weight g/mol",
        "assumptions": [
            "Stability from the list of stable/observationally stable isotopes (Z <= 20)",
            "Electron configuration by the Aufbau (Madelung n + l) rule; shells as in the Bohr model",
            "Binding energy from the semi-empirical mass formula (rough for very light nuclei)",
        ],
    }
