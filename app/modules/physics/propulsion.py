"""Rocket propulsion: Tsiolkovsky equation, multi-stage delta-v, staging optimisation, thrust parameters."""
import math
from typing import Any

import numpy as np
from scipy.optimize import brentq

from app.core.registry import tool

G0 = 9.80665  # standard gravity, m/s^2 (defines Isp in seconds)


def _positive(name: str, value: float | None) -> None:
    if value is not None and not value > 0:
        raise ValueError(f"{name} must be positive")


@tool(
    domain="physics",
    name="rocket_equation",
    description=(
        "Tsiolkovsky rocket equation dv = ve ln(m0/mf). Give any three of: delta_v (m/s), exhaust velocity "
        "(exhaust_velocity in m/s OR isp in s), initial_mass (kg), final_mass (kg); the missing one is solved. "
        "Example: isp=311, initial_mass=549054, final_mass=25600 -> delta_v."
    ),
)
def rocket_equation(
    delta_v: float | None = None,
    isp: float | None = None,
    exhaust_velocity: float | None = None,
    initial_mass: float | None = None,
    final_mass: float | None = None,
) -> dict:
    if isp is not None and exhaust_velocity is not None:
        raise ValueError("Give isp or exhaust_velocity, not both")
    for name, v in (("delta_v", delta_v), ("isp", isp), ("exhaust_velocity", exhaust_velocity),
                    ("initial_mass", initial_mass), ("final_mass", final_mass)):
        _positive(name, v)
    ve = exhaust_velocity if exhaust_velocity is not None else (isp * G0 if isp is not None else None)
    known = {"delta_v": delta_v, "exhaust_velocity": ve, "initial_mass": initial_mass, "final_mass": final_mass}
    missing = [k for k, v in known.items() if v is None]
    if len(missing) != 1:
        raise ValueError(f"Give exactly three of delta_v, isp/exhaust_velocity, initial_mass, final_mass "
                         f"(missing: {missing})")
    if initial_mass is not None and final_mass is not None and final_mass >= initial_mass:
        raise ValueError("final_mass must be less than initial_mass")

    solve_for = missing[0]
    if solve_for == "delta_v":
        delta_v = ve * math.log(initial_mass / final_mass)
        result, units = delta_v, "m/s"
    elif solve_for == "exhaust_velocity":
        ve = delta_v / math.log(initial_mass / final_mass)
        result, units = ve, "m/s"
    elif solve_for == "initial_mass":
        initial_mass = final_mass * math.exp(delta_v / ve)
        result, units = initial_mass, "kg"
    else:
        final_mass = initial_mass * math.exp(-delta_v / ve)
        result, units = final_mass, "kg"

    propellant = initial_mass - final_mass
    return {
        "result": result,
        "solved_for": solve_for,
        "delta_v": delta_v,
        "exhaust_velocity": ve,
        "isp": ve / G0,
        "initial_mass": initial_mass,
        "final_mass": final_mass,
        "propellant_mass": propellant,
        "mass_ratio": initial_mass / final_mass,
        "propellant_fraction": propellant / initial_mass,
        "units": f"{units} (velocities m/s, masses kg, isp s)",
        "assumptions": [
            "Ideal rocket in free space: no gravity or drag losses",
            f"Constant exhaust velocity; isp = ve / g0 with g0 = {G0} m/s^2",
        ],
    }


def _stage_list(stages: list[dict[str, Any]], required: tuple[str, ...]) -> list[dict[str, float]]:
    if not stages:
        raise ValueError("Give at least one stage")
    out = []
    for n, s in enumerate(stages, 1):
        missing = [k for k in required if k not in s]
        if missing:
            raise ValueError(f"Stage {n} is missing {missing}")
        vals = {k: float(s[k]) for k in required}
        for k, v in vals.items():
            if not v > 0 and not (k == "dry_mass" and v == 0):
                raise ValueError(f"Stage {n}: {k} must be positive")
        out.append(vals)
    return out


@tool(
    domain="physics",
    name="multi_stage_delta_v",
    description=(
        "Total delta-v of a multi-stage rocket. stages: list ordered from FIRST (bottom) to LAST (top), each "
        "{isp (s), propellant_mass (kg), dry_mass (kg, structure + engines)}; payload_mass in kg. "
        "Example: stages=[{isp:282,propellant_mass:395700,dry_mass:25600},{isp:348,propellant_mass:92670,dry_mass:3900}], "
        "payload_mass=15000."
    ),
)
def multi_stage_delta_v(stages: list[dict[str, Any]], payload_mass: float) -> dict:
    if payload_mass < 0:
        raise ValueError("payload_mass must be >= 0")
    st = _stage_list(stages, ("isp", "propellant_mass", "dry_mass"))
    # Mass above each stage (upper stages + payload)
    above = [payload_mass + sum(s["propellant_mass"] + s["dry_mass"] for s in st[k + 1:]) for k in range(len(st))]
    per_stage = []
    for k, s in enumerate(st):
        m0 = above[k] + s["propellant_mass"] + s["dry_mass"]
        mf = above[k] + s["dry_mass"]
        if mf <= 0:
            raise ValueError("The top stage needs dry_mass > 0 or a payload")
        dv = s["isp"] * G0 * math.log(m0 / mf)
        per_stage.append({"stage": k + 1, "delta_v": dv, "initial_mass": m0, "burnout_mass": mf,
                          "mass_ratio": m0 / mf})
    liftoff = per_stage[0]["initial_mass"]
    return {
        "result": sum(p["delta_v"] for p in per_stage),
        "stages": per_stage,
        "liftoff_mass": liftoff,
        "payload_fraction": payload_mass / liftoff,
        "units": "delta-v in m/s, masses in kg",
        "assumptions": [
            "Serial staging: each stage burns all propellant then is dropped",
            "Ideal delta-v (no gravity, drag or steering losses)",
        ],
    }


@tool(
    domain="physics",
    name="optimize_staging",
    description=(
        "Lightest multi-stage rocket that achieves a target delta-v (Lagrange-multiplier optimum, restricted "
        "staging). stages: bottom-to-top list of {isp (s), structural_fraction (dry/(dry+propellant), 0-1)}. "
        "Example: delta_v=9000, payload_mass=10000, stages=[{isp:300,structural_fraction:0.1},"
        "{isp:450,structural_fraction:0.12}]."
    ),
)
def optimize_staging(delta_v: float, payload_mass: float, stages: list[dict[str, Any]]) -> dict:
    _positive("delta_v", delta_v)
    _positive("payload_mass", payload_mass)
    st = _stage_list(stages, ("isp", "structural_fraction"))
    c = np.array([s["isp"] * G0 for s in st])
    eps = np.array([s["structural_fraction"] for s in st])
    if np.any(eps >= 1):
        raise ValueError("structural_fraction must be between 0 and 1")

    # Upper bound on delta-v: each stage all-propellant limit, mass ratio -> 1/eps.
    dv_max = float(np.sum(c * np.log(1 / eps)))
    if delta_v >= dv_max:
        raise ValueError(f"Target delta-v is unreachable with these stages (max {dv_max:.0f} m/s at infinite mass)")

    # Mass ratio of stage i: n_i = (c_i eta - 1) / (c_i eps_i eta); find eta so sum c_i ln n_i = delta_v.
    def ratios(eta):
        return (c * eta - 1) / (c * eps * eta)

    def residual(eta):
        return float(np.sum(c * np.log(ratios(eta))) - delta_v)

    lo = float(np.max(1 / (c * (1 - eps)))) * (1 + 1e-12)   # all n_i = 1 here -> residual < 0
    hi = lo * 2
    while residual(hi) < 0:
        hi *= 2
        if hi > 1e12:
            raise ValueError("Could not bracket the staging optimum")
    eta = brentq(residual, lo, hi, xtol=1e-18, rtol=1e-14)
    n = ratios(eta)

    # Build masses from the top stage down.
    upper = payload_mass
    rows = []
    for i in reversed(range(len(st))):
        # n_i = (m_prop + m_dry + upper) / (m_dry + upper); m_dry = eps/(1-eps) m_prop
        stage_mass = upper * (n[i] - 1) / (1 - n[i] * eps[i])
        m_dry = eps[i] * stage_mass
        rows.append({
            "stage": i + 1,
            "stage_mass": stage_mass,
            "propellant_mass": stage_mass - m_dry,
            "dry_mass": m_dry,
            "mass_ratio": float(n[i]),
            "delta_v": float(c[i] * math.log(n[i])),
        })
        upper += stage_mass
    rows.reverse()
    return {
        "result": {"liftoff_mass": upper, "stages": rows},
        "payload_fraction": payload_mass / upper,
        "units": "masses in kg, delta-v in m/s",
        "assumptions": [
            "Minimises lift-off mass for fixed Isp and structural fraction per stage (Lagrange multipliers)",
            "Ideal delta-v; no gravity/drag losses; structural fraction independent of stage size",
        ],
    }


@tool(
    domain="physics",
    name="thrust_parameters",
    description=(
        "Engine/vehicle performance from thrust and Isp: mass flow rate, exhaust velocity, thrust-to-weight "
        "ratio (if mass given) and burn time (if propellant_mass given). gravity defaults to Earth g0. "
        "Example: thrust=7607000, isp=282, mass=549054, propellant_mass=395700."
    ),
)
def thrust_parameters(
    thrust: float,
    isp: float,
    mass: float | None = None,
    propellant_mass: float | None = None,
    gravity: float = G0,
) -> dict:
    for name, v in (("thrust", thrust), ("isp", isp), ("mass", mass),
                    ("propellant_mass", propellant_mass), ("gravity", gravity)):
        _positive(name, v)
    ve = isp * G0
    mdot = thrust / ve
    out: dict[str, Any] = {"mass_flow_rate": mdot, "exhaust_velocity": ve}
    if mass is not None:
        out["thrust_to_weight"] = thrust / (mass * gravity)
        out["can_lift_off"] = out["thrust_to_weight"] > 1
    if propellant_mass is not None:
        if mass is not None and propellant_mass >= mass:
            raise ValueError("propellant_mass must be less than the total mass")
        out["burn_time"] = propellant_mass / mdot
    return {
        "result": out,
        "units": "mass flow kg/s, exhaust velocity m/s, burn time s, thrust-to-weight dimensionless",
        "assumptions": [
            "Constant thrust and Isp (vacuum or sea-level value as supplied)",
            f"Thrust-to-weight at the given mass using g = {gravity} m/s^2",
        ],
    }
