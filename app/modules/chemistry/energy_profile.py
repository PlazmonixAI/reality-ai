"""Reaction energy profiles: activation energy, catalysts, Arrhenius rates and the fraction of
molecules energetic enough to react."""
import math

import numpy as np
from scipy.special import erfc

from app.core.registry import tool

R = 8.314462618  # J/(mol K)


def fraction_above(e: float, t: float) -> float:
    """Fraction of molecules with translational kinetic energy ≥ e (3D Maxwell-Boltzmann, per mole)."""
    x = e / (R * t)
    return float(2 * math.sqrt(x / math.pi) * math.exp(-x) + erfc(math.sqrt(x)))


def _profile(x: np.ndarray, ea: float, dh: float) -> np.ndarray:
    """Smooth single-barrier path: flat reactants (0), cosine rise to Ea at x = 0.5, fall to ΔH, flat products."""
    y = np.zeros_like(x)
    up = (x >= 0.15) & (x < 0.5)
    down = (x >= 0.5) & (x <= 0.85)
    y[up] = ea * (1 - np.cos(np.pi * (x[up] - 0.15) / 0.35)) / 2
    y[down] = dh + (ea - dh) * (1 + np.cos(np.pi * (x[down] - 0.5) / 0.35)) / 2
    y[x > 0.85] = dh
    return y


@tool(
    domain="chemistry",
    name="reaction_profile",
    description=(
        "Energy profile of a one-step reaction with forward activation energy (J/mol) and reaction enthalpy ΔH "
        "(J/mol), optionally with a catalyst that lowers the barrier to catalyst_activation_energy. Returns reverse "
        "barrier, Arrhenius rate constants, catalytic speed-up, the fraction of molecules with energy ≥ Ea "
        "(Maxwell-Boltzmann) and plot-ready profile and energy-distribution curves. "
        "Example: activation_energy=75000, reaction_enthalpy=-40000, catalyst_activation_energy=50000."
    ),
)
def reaction_profile(
    activation_energy: float,
    reaction_enthalpy: float,
    catalyst_activation_energy: float | None = None,
    temperature: float = 298.15,
    pre_exponential: float = 1e13,
    n_points: int = 201,
) -> dict:
    if activation_energy <= 0:
        raise ValueError("activation_energy must be positive (J/mol)")
    if activation_energy < reaction_enthalpy:
        raise ValueError("the transition state must lie above the products: activation_energy >= reaction_enthalpy")
    if catalyst_activation_energy is not None:
        if not 0 < catalyst_activation_energy <= activation_energy:
            raise ValueError("catalyst_activation_energy must be positive and no larger than activation_energy")
        if catalyst_activation_energy < reaction_enthalpy:
            raise ValueError("catalysed barrier must lie above the products")
    if temperature <= 0 or pre_exponential <= 0:
        raise ValueError("temperature (K) and pre_exponential (1/s) must be positive")
    if not 20 <= n_points <= 5000:
        raise ValueError("n_points must be between 20 and 5000")

    rt = R * temperature
    k = lambda e: pre_exponential * math.exp(-e / rt)  # noqa: E731
    x = np.linspace(0, 1, n_points)
    ea_r = activation_energy - reaction_enthalpy
    out = {
        "reverse_activation_energy": ea_r,
        "exothermic": reaction_enthalpy < 0,
        "k_forward": k(activation_energy),
        "k_reverse": k(ea_r),
        "equilibrium_constant": math.exp(-reaction_enthalpy / rt),
        "fraction_above_barrier": fraction_above(activation_energy, temperature),
        "half_life_forward": math.log(2) / k(activation_energy),
    }
    profiles = {"coordinate": x.tolist(), "energy": _profile(x, activation_energy, reaction_enthalpy).tolist()}
    if catalyst_activation_energy is not None:
        eac = catalyst_activation_energy
        out |= {
            "catalysed": {
                "activation_energy": eac,
                "reverse_activation_energy": eac - reaction_enthalpy,
                "k_forward": k(eac),
                "k_reverse": k(eac - reaction_enthalpy),
                "rate_enhancement": math.exp((activation_energy - eac) / rt),
                "fraction_above_barrier": fraction_above(eac, temperature),
                "half_life_forward": math.log(2) / k(eac),
            }
        }
        profiles["energy_catalysed"] = _profile(x, eac, reaction_enthalpy).tolist()
    # Maxwell-Boltzmann energy distribution, f(E) = 2 sqrt(E/π) (RT)^(-3/2) exp(-E/RT), per J/mol
    e_top = max(activation_energy * 1.3, 10 * rt)
    es = np.linspace(0, e_top, 400)
    f = 2 * np.sqrt(es / math.pi) * rt**-1.5 * np.exp(-es / rt)
    return {
        "result": out,
        "profile": profiles,
        "distribution": {"energy": es.tolist(), "density": f.tolist()},
        "units": "energies in J/mol, rate constants in 1/s (first-order, same units as pre_exponential), "
                 "half-lives in s, density in mol/J",
        "assumptions": [
            "Single elementary step with the same pre-exponential factor forward, reverse and catalysed",
            "Equilibrium constant from ΔH only (ΔS ≈ 0), consistent with equal pre-exponential factors",
            "Fraction above the barrier uses the 3D Maxwell-Boltzmann kinetic-energy distribution",
            "Profile shape is schematic; only the energies of reactants, transition state and products are physical",
        ],
    }
