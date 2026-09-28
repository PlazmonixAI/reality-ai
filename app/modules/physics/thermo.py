"""Ideal-gas heat-engine cycles (Carnot, Otto, Diesel) on a PV diagram, with work computed numerically."""
import math

import numpy as np

from app.core.registry import tool

R = 8.314462618


def _isotherm(n, t, va, vb, k=600):
    v = np.linspace(va, vb, k)
    return v, n * R * t / v


def _adiabat(pa, va, vb, gamma, k=600):
    v = np.linspace(va, vb, k)
    return v, pa * (va / v) ** gamma


def _straight(va, vb, pa, pb, k=40):
    return np.linspace(va, vb, k), np.linspace(pa, pb, k)


@tool(
    domain="physics",
    name="heat_engine_cycle",
    description=(
        "Ideal-gas heat engine cycle on a PV diagram. cycle 'carnot' (t_hot, t_cold, expansion_ratio of the hot "
        "isotherm), 'otto' (compression_ratio, heat input via t_max) or 'diesel' (compression_ratio, cutoff_ratio). "
        "Start state: p1 (Pa), v1 (m^3), moles n, heat-capacity ratio gamma. Returns the corner states, the PV "
        "path, net work (integral of P dV), heat in/out and efficiency vs the textbook formula. "
        "Example: cycle='otto', compression_ratio=8, t_max=2000."
    ),
)
def heat_engine_cycle(
    cycle: str,
    moles: float = 1.0,
    gamma: float = 1.4,
    p1: float = 100_000.0,
    v1: float | None = None,
    t_hot: float = 600.0,
    t_cold: float = 300.0,
    expansion_ratio: float = 2.0,
    compression_ratio: float = 8.0,
    t_max: float = 2000.0,
    cutoff_ratio: float = 2.0,
) -> dict:
    if moles <= 0 or not 1 < gamma <= 1.7 or p1 <= 0:
        raise ValueError("moles and p1 must be positive; gamma in (1, 1.7]")
    cv = R / (gamma - 1)
    cp = cv + R
    paths, states = [], []

    if cycle == "carnot":
        if not t_hot > t_cold > 0 or expansion_ratio <= 1:
            raise ValueError("Need t_hot > t_cold > 0 and expansion_ratio > 1")
        va = v1 or moles * R * t_hot / (4 * p1)
        vb = va * expansion_ratio
        ratio = (t_hot / t_cold) ** (1 / (gamma - 1))
        vc, vd = vb * ratio, va * ratio
        pa, pb = moles * R * t_hot / va, moles * R * t_hot / vb
        pc, pd = moles * R * t_cold / vc, moles * R * t_cold / vd
        states = [(pa, va), (pb, vb), (pc, vc), (pd, vd)]
        paths = [_isotherm(moles, t_hot, va, vb), _adiabat(pb, vb, vc, gamma), _isotherm(moles, t_cold, vc, vd), _adiabat(pd, vd, va, gamma)]
        q_in = moles * R * t_hot * math.log(vb / va)
        formula = 1 - t_cold / t_hot
        names = ["isothermal expansion (hot)", "adiabatic expansion", "isothermal compression (cold)", "adiabatic compression"]
    elif cycle in ("otto", "diesel"):
        r = compression_ratio
        if r <= 1:
            raise ValueError("compression_ratio must be > 1")
        va = v1 or moles * R * 300.0 / p1          # start at 300 K by default
        ta = p1 * va / (moles * R)
        vb = va / r
        pb = p1 * r**gamma
        tb = pb * vb / (moles * R)
        if cycle == "otto":
            if t_max <= tb:
                raise ValueError(f"t_max must exceed the compressed temperature {tb:.0f} K")
            pc = pb * t_max / tb
            vc = vb
            pd = pc * (vc / va) ** gamma
            states = [(p1, va), (pb, vb), (pc, vc), (pd, va)]
            paths = [_adiabat(p1, va, vb, gamma), _straight(vb, vc, pb, pc), _adiabat(pc, vc, va, gamma), _straight(va, va, pd, p1)]
            q_in = moles * cv * (t_max - tb)
            formula = 1 - r ** (1 - gamma)
            names = ["adiabatic compression", "constant-volume heating", "adiabatic expansion (power)", "constant-volume cooling"]
        else:
            rc = cutoff_ratio
            if not 1 < rc < r:
                raise ValueError("cutoff_ratio must be between 1 and the compression ratio")
            vc = vb * rc
            tc = tb * rc
            pd = pb * (vc / va) ** gamma
            states = [(p1, va), (pb, vb), (pb, vc), (pd, va)]
            paths = [_adiabat(p1, va, vb, gamma), _straight(vb, vc, pb, pb), _adiabat(pb, vc, va, gamma), _straight(va, va, pd, p1)]
            q_in = moles * cp * (tc - tb)
            formula = 1 - (rc**gamma - 1) / (gamma * r ** (gamma - 1) * (rc - 1))
            names = ["adiabatic compression", "constant-pressure heating (fuel burns)", "adiabatic expansion (power)", "constant-volume cooling"]
    else:
        raise ValueError("cycle must be 'carnot', 'otto' or 'diesel'")

    # Net work = closed-loop integral of P dV along the path (trapezoid rule on each leg).
    work = float(sum(np.trapezoid(p, v) for v, p in paths))
    efficiency = work / q_in
    temps = [p * v / (moles * R) for p, v in states]
    return {
        "result": {"net_work": work, "heat_in": q_in, "heat_out": q_in - work, "efficiency": efficiency,
                   "formula_efficiency": formula, "carnot_limit": 1 - min(temps) / max(temps)},
        "states": [{"p": p, "v": v, "t": t} for (p, v), t in zip(states, temps)],
        "legs": [{"name": nm, "v": v.tolist(), "p": p.tolist()} for nm, (v, p) in zip(names, paths)],
        "units": "pressure Pa, volume m^3, temperature K, energy J, efficiency fraction",
        "assumptions": ["Ideal gas with constant heat capacities", "Reversible (quasi-static) legs",
                        "Net work integrated numerically around the PV loop"],
    }
