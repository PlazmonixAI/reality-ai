"""Reaction kinetics: integrated rate laws (orders 0, 1, 2), half-life, Arrhenius equation."""
import math

import numpy as np

from app.core.registry import tool
from app.modules.chemistry.gas import R

_K_UNITS = {0: "M/s", 1: "1/s", 2: "1/(M s)"}


def _concentration(order: int, k: float, a0: float, t: np.ndarray) -> np.ndarray:
    if order == 0:
        return np.maximum(a0 - k * t, 0.0)
    if order == 1:
        return a0 * np.exp(-k * t)
    return 1 / (1 / a0 + k * t)


@tool(
    domain="chemistry",
    name="reaction_kinetics",
    description=(
        "Integrated rate law for a reaction A -> products of order 0, 1 or 2 (rate = k[A]^order). Give "
        "rate_constant and initial_concentration, plus time (s) to get [A](t), or concentration to get the time "
        "to reach it. Always returns the half-life and a plot-ready decay curve. Concentrations in mol/L (M). "
        "Example: order=1, rate_constant=0.005, initial_concentration=1, time=100."
    ),
)
def reaction_kinetics(
    order: int,
    rate_constant: float,
    initial_concentration: float,
    time: float | None = None,
    concentration: float | None = None,
    n_points: int = 101,
) -> dict:
    if order not in (0, 1, 2):
        raise ValueError("order must be 0, 1 or 2")
    if rate_constant <= 0 or initial_concentration <= 0:
        raise ValueError("rate_constant and initial_concentration must be positive")
    if time is not None and concentration is not None:
        raise ValueError("Give time or concentration, not both")
    if not 2 <= n_points <= 10_000:
        raise ValueError("n_points must be between 2 and 10000")
    k, a0 = rate_constant, initial_concentration

    half_life = {0: a0 / (2 * k), 1: math.log(2) / k, 2: 1 / (k * a0)}[order]
    out: dict = {"half_life": half_life}
    if time is not None:
        if time < 0:
            raise ValueError("time must be >= 0")
        out["concentration"] = float(_concentration(order, k, a0, np.array(time)))
        out["fraction_remaining"] = out["concentration"] / a0
        t_end = time
    elif concentration is not None:
        if not 0 < concentration <= a0 and not (order == 0 and concentration == 0):
            raise ValueError("concentration must be between 0 and initial_concentration")
        if order == 0:
            t = (a0 - concentration) / k
        elif order == 1:
            t = math.log(a0 / concentration) / k
        else:
            t = (1 / concentration - 1 / a0) / k
        out["time"] = t
        t_end = t
    else:
        t_end = 0.0
    t_end = t_end if t_end > 0 else 5 * half_life
    t = np.linspace(0, t_end, n_points)

    return {
        "result": out,
        "curve": {"t": t.tolist(), "concentration": _concentration(order, k, a0, t).tolist()},
        "rate_law": f"rate = k[A]^{order}",
        "units": f"concentration in M (mol/L), time and half-life in s, k in {_K_UNITS[order]}",
        "assumptions": ["Single reactant, irreversible, constant temperature",
                        "Zero-order reaction stops when A is used up" if order == 0 else "Integrated rate law"],
    }


@tool(
    domain="chemistry",
    name="arrhenius",
    description=(
        "Arrhenius equation k = A exp(-Ea/RT). Mode 1: give pre_exponential, activation_energy (J/mol) and "
        "temperature (K) -> k. Mode 2 (two temperatures): give k1 at t1 plus any two of k2, t2, activation_energy; "
        "the third is solved. Example: k1=1e-3, t1=298, t2=308, activation_energy=50000 -> k2."
    ),
)
def arrhenius(
    activation_energy: float | None = None,
    pre_exponential: float | None = None,
    temperature: float | None = None,
    k1: float | None = None,
    t1: float | None = None,
    k2: float | None = None,
    t2: float | None = None,
) -> dict:
    for name, v in (("pre_exponential", pre_exponential), ("temperature", temperature), ("k1", k1),
                    ("t1", t1), ("k2", k2), ("t2", t2)):
        if v is not None and not v > 0:
            raise ValueError(f"{name} must be positive (temperatures in K)")
    if activation_energy is not None and activation_energy < 0:
        raise ValueError("activation_energy must be >= 0")

    if pre_exponential is not None:
        if activation_energy is None or temperature is None:
            raise ValueError("Mode 1 needs pre_exponential, activation_energy and temperature")
        k = pre_exponential * math.exp(-activation_energy / (R * temperature))
        return {
            "result": k,
            "solved_for": "rate_constant",
            "units": "same units as pre_exponential",
            "assumptions": ["Arrhenius equation with temperature-independent A and Ea", f"R = {R} J/(mol K)"],
        }

    if k1 is None or t1 is None:
        raise ValueError("Give pre_exponential (mode 1) or k1 and t1 (mode 2)")
    unknown = [n for n, v in (("k2", k2), ("t2", t2), ("activation_energy", activation_energy)) if v is None]
    if len(unknown) != 1:
        raise ValueError("Mode 2: give exactly two of k2, t2, activation_energy")
    solve_for = unknown[0]
    if solve_for == "k2":
        k2 = k1 * math.exp(-activation_energy / R * (1 / t2 - 1 / t1))
        result, units = k2, "same units as k1"
    elif solve_for == "t2":
        if activation_energy == 0:
            raise ValueError("With zero activation energy k does not depend on temperature")
        t2 = 1 / (1 / t1 - R * math.log(k2 / k1) / activation_energy)
        if t2 <= 0:
            raise ValueError("No positive temperature gives that rate constant")
        result, units = t2, "K"
    else:
        if math.isclose(t1, t2):
            raise ValueError("t1 and t2 must differ to find the activation energy")
        activation_energy = -R * math.log(k2 / k1) / (1 / t2 - 1 / t1)
        if activation_energy < 0:
            raise ValueError("Data imply a negative activation energy (k falls as T rises)")
        result, units = activation_energy, "J/mol"
    a = k1 * math.exp(activation_energy / (R * t1))
    return {
        "result": result,
        "solved_for": solve_for,
        "activation_energy": activation_energy,
        "pre_exponential": a,
        "k1": k1, "t1": t1, "k2": k2, "t2": t2,
        "units": f"{units} (Ea in J/mol, temperatures in K)",
        "assumptions": ["Arrhenius equation with temperature-independent A and Ea", f"R = {R} J/(mol K)"],
    }
