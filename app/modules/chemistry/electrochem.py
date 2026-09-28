"""Galvanic cells: standard cell potential, Nernst equation, free energy and equilibrium constant."""
import math

import numpy as np

from app.core.registry import tool

F = 96485.33212  # C/mol
R = 8.314462618  # J/(mol K)

# A few standard reduction potentials at 25 °C (V vs SHE), textbook values: symbol -> (ion, electrons, E°).
ELECTRODES = {
    "Li": ("Li+", 1, -3.04), "K": ("K+", 1, -2.93), "Mg": ("Mg2+", 2, -2.37), "Al": ("Al3+", 3, -1.66),
    "Zn": ("Zn2+", 2, -0.76), "Fe": ("Fe2+", 2, -0.44), "Ni": ("Ni2+", 2, -0.25), "Pb": ("Pb2+", 2, -0.13),
    "H2": ("H+", 1, 0.0), "Cu": ("Cu2+", 2, 0.34), "Ag": ("Ag+", 1, 0.80), "Au": ("Au3+", 3, 1.50),
}


def _half(name: str) -> tuple[str, int, float]:
    if name not in ELECTRODES:
        raise ValueError(f"Unknown electrode {name!r}; choose from {', '.join(ELECTRODES)}")
    return ELECTRODES[name]


def _overall(anode: str, ion_a: str, ka: int, cathode: str, ion_c: str, kc: int) -> str:
    c = lambda k, s: s if k == 1 else f"{k} {s}"  # noqa: E731
    if cathode == "H2":  # 2 H+ + 2 e- -> H2: kc counts electrons/1, so kc H+ make kc/2 H2
        return f"{c(ka, anode)} + {c(kc, 'H+')} -> {c(ka, ion_a)} + {c(kc // 2, 'H2') if kc % 2 == 0 else f'{kc}/2 H2'}"
    if anode == "H2":
        left = c(ka // 2, "H2") if ka % 2 == 0 else f"{ka}/2 H2"
        return f"{left} + {c(kc, ion_c)} -> {c(ka, 'H+')} + {c(kc, cathode)}"
    return f"{c(ka, anode)} + {c(kc, ion_c)} -> {c(ka, ion_a)} + {c(kc, cathode)}"


@tool(
    domain="chemistry",
    name="galvanic_cell",
    description=(
        "Galvanic (voltaic) cell from two metal/ion electrodes: standard potential E°, Nernst potential E at the "
        "given ion concentrations (mol/L) and temperature (K), ΔG = -nFE, equilibrium constant K, and E vs log10 Q. "
        f"Electrodes: {', '.join(ELECTRODES)} (H2 means the standard hydrogen electrode, 1 bar H2). "
        "Example: anode='Zn', cathode='Cu', anode_concentration=1, cathode_concentration=1 -> 1.10 V."
    ),
)
def galvanic_cell(
    anode: str,
    cathode: str,
    anode_concentration: float = 1.0,
    cathode_concentration: float = 1.0,
    temperature: float = 298.15,
) -> dict:
    if anode == cathode:
        raise ValueError("anode and cathode must be different electrodes (use a concentration cell elsewhere)")
    ion_a, za, ea = _half(anode)
    ion_c, zc, ec = _half(cathode)
    if anode_concentration <= 0 or cathode_concentration <= 0:
        raise ValueError("ion concentrations must be positive (mol/L)")
    if temperature <= 0:
        raise ValueError("temperature must be positive (K)")

    n = za * zc // math.gcd(za, zc)
    # anode: M -> M^za+ + za e- (x n/za); cathode: M^zc+ + zc e- -> M (x n/zc)
    log_q = (n / za) * math.log10(anode_concentration) - (n / zc) * math.log10(cathode_concentration)
    e0 = ec - ea
    slope = R * temperature * math.log(10) / (n * F)
    e = e0 - slope * log_q
    dg0, dg = -n * F * e0, -n * F * e
    ln_k = n * F * e0 / (R * temperature)
    lq = np.linspace(-8, 8, 161)
    return {
        "result": {
            "standard_potential": e0,
            "cell_potential": e,
            "electrons_transferred": n,
            "reaction_quotient": 10**log_q,
            "log10_q": log_q,
            "delta_g_standard": dg0,
            "delta_g": dg,
            "log10_k": ln_k / math.log(10),
            "spontaneous": e > 0,
            "nernst_slope": slope,
            "anode": {"electrode": anode, "ion": ion_a, "charge": za, "reduction_potential": ea},
            "cathode": {"electrode": cathode, "ion": ion_c, "charge": zc, "reduction_potential": ec},
            "overall": _overall(anode, ion_a, n // za, cathode, ion_c, n // zc),
        },
        "nernst_curve": {"log10_q": lq.tolist(), "potential": (e0 - slope * lq).tolist()},
        "units": "potentials in V, ΔG in J/mol, concentrations in mol/L, temperature in K",
        "assumptions": [
            "Standard reduction potentials at 25 °C (textbook values); E° taken as temperature-independent",
            "Activities approximated by concentrations (ideal dilute solutions); H2 at 1 bar",
            "Open-circuit (zero-current) potential: no overpotential or IR drop",
        ],
    }
