"""Real gases and phase change: van der Waals isotherms (with Maxwell's equal-area rule) and
Clausius-Clapeyron vapour pressure."""
import math

import numpy as np
from scipy.optimize import brentq

from app.core.registry import tool

R = 8.314462618  # J/(mol K)


def _vdw_p(v, t, a, b):
    return R * t / (v - b) - a / v**2


def _extrema(t: float, a: float, b: float) -> tuple[float, float] | None:
    """Molar volumes of the local minimum and maximum of P(V) below Tc (dP/dV = 0), else None."""
    dp = lambda v: -R * t / (v - b) ** 2 + 2 * a / v**3  # noqa: E731
    vs = b * (1 + np.geomspace(1e-4, 1e4, 4000))
    s = np.sign(dp(vs))
    idx = np.nonzero(np.diff(s))[0]
    if len(idx) < 2:
        return None
    v_min = brentq(dp, vs[idx[0]], vs[idx[0] + 1])
    v_max = brentq(dp, vs[idx[1]], vs[idx[1] + 1])
    return v_min, v_max


def _outer_roots(p: float, t: float, a: float, b: float) -> tuple[float, float]:
    """Smallest and largest real roots V > b of P(V) = p (the liquid and gas volumes)."""
    roots = np.roots([p, -(p * b + R * t), a, -a * b])
    real = sorted(r.real for r in roots if abs(r.imag) < 1e-9 * abs(r) and r.real > b)
    return real[0], real[-1]


def _saturation(t: float, a: float, b: float) -> dict | None:
    """Maxwell equal-area construction: P_sat with ∫(P - P_sat) dV = 0 between liquid and gas volumes."""
    ext = _extrema(t, a, b)
    if ext is None:
        return None
    p_lo, p_hi = _vdw_p(ext[0], t, a, b), _vdw_p(ext[1], t, a, b)
    lo = max(p_lo, p_hi * 1e-12)
    hi = p_hi

    def area(p):
        vl, vg = _outer_roots(p, t, a, b)
        integral = R * t * math.log((vg - b) / (vl - b)) + a * (1 / vg - 1 / vl)
        return integral - p * (vg - vl)

    span = hi - lo
    p_sat = brentq(area, lo + 1e-9 * span, hi - 1e-9 * span, xtol=1e-12 * hi, rtol=1e-12)
    vl, vg = _outer_roots(p_sat, t, a, b)
    return {"pressure": p_sat, "v_liquid": vl, "v_gas": vg, "spinodal_volumes": list(ext)}


@tool(
    domain="chemistry",
    name="van_der_waals",
    description=(
        "Van der Waals real-gas isotherm P = RT/(Vm-b) - a/Vm^2 for constants a (Pa m^6/mol^2) and b (m^3/mol) "
        "at temperature (K): critical point, the ideal-gas isotherm for comparison, compressibility Z, and below Tc "
        "the liquid-vapour coexistence pressure from Maxwell's equal-area rule. Optional molar_volume (m^3/mol) "
        "gives the state there. Example: a=0.3640, b=4.267e-5 (CO2), temperature=280."
    ),
)
def van_der_waals(
    a: float,
    b: float,
    temperature: float,
    molar_volume: float | None = None,
    v_max_factor: float = 40.0,
    n_points: int = 400,
) -> dict:
    if a < 0 or b <= 0:
        raise ValueError("a must be non-negative and b positive (SI: Pa m^6/mol^2, m^3/mol)")
    if temperature <= 0:
        raise ValueError("temperature must be positive (K)")
    if not 20 <= n_points <= 5000:
        raise ValueError("n_points must be between 20 and 5000")
    if v_max_factor <= 2:
        raise ValueError("v_max_factor must exceed 2 (the plot runs from just above b to v_max_factor * b)")
    if molar_volume is not None and molar_volume <= b:
        raise ValueError("molar_volume must be larger than b (the excluded volume)")

    tc, pc, vc = (8 * a / (27 * R * b), a / (27 * b**2), 3 * b) if a > 0 else (0.0, math.inf, 3 * b)
    v = b * np.geomspace(1.15, v_max_factor, n_points)
    p = _vdw_p(v, temperature, a, b)
    sat = _saturation(temperature, a, b) if a > 0 and temperature < tc * (1 - 1e-6) else None
    physical = p.copy()
    if sat:
        inside = (v > sat["v_liquid"]) & (v < sat["v_gas"])
        physical[inside] = sat["pressure"]
    state = None
    if molar_volume is not None:
        pv = float(_vdw_p(molar_volume, temperature, a, b))
        phase = "supercritical fluid" if temperature >= tc else "gas" if not sat or molar_volume >= sat["v_gas"] else \
            "liquid" if molar_volume <= sat["v_liquid"] else "liquid + vapour"
        p_phys = sat["pressure"] if phase == "liquid + vapour" else pv
        state = {
            "molar_volume": molar_volume,
            "pressure": p_phys,
            "vdw_curve_pressure": pv,
            "ideal_pressure": R * temperature / molar_volume,
            "compressibility": p_phys * molar_volume / (R * temperature),
            "phase": phase,
            "vapour_fraction": (molar_volume - sat["v_liquid"]) / (sat["v_gas"] - sat["v_liquid"]) if phase == "liquid + vapour" else None,
        }
    return {
        "result": {
            "critical_temperature": tc,
            "critical_pressure": pc,
            "critical_molar_volume": vc,
            "critical_compressibility": 3 / 8,
            "reduced_temperature": temperature / tc if tc else math.inf,
            "boyle_temperature": a / (R * b),
            "saturation": sat,
            "state": state,
        },
        "isotherm": {
            "molar_volume": v.tolist(),
            "pressure_vdw": p.tolist(),
            "pressure_physical": physical.tolist(),
            "pressure_ideal": (R * temperature / v).tolist(),
        },
        "units": "pressure in Pa, molar volume in m^3/mol, temperature in K",
        "assumptions": [
            "Van der Waals equation of state: a = attraction, b = excluded volume per mole",
            "Below Tc the unstable/metastable loop is replaced by the Maxwell equal-area tie line",
            "Quantitative only near the ideal limit; vdW critical Z = 3/8 is larger than real gases (~0.29)",
        ],
    }


@tool(
    domain="chemistry",
    name="vapor_pressure",
    description=(
        "Clausius-Clapeyron vapour pressure ln(P/P_ref) = -ΔH_vap/R (1/T - 1/T_ref) for a liquid with molar "
        "enthalpy of vaporisation enthalpy_vap (J/mol) and normal boiling point boiling_point (K, at 101325 Pa). "
        "Optional temperature (K) gives the vapour pressure there; optional pressure (Pa) gives the boiling "
        "temperature there. Example: enthalpy_vap=40650, boiling_point=373.15 (water), pressure=33700 (Everest)."
    ),
)
def vapor_pressure(
    enthalpy_vap: float,
    boiling_point: float,
    reference_pressure: float = 101325.0,
    temperature: float | None = None,
    pressure: float | None = None,
    t_min: float | None = None,
    t_max: float | None = None,
    n_points: int = 200,
) -> dict:
    if enthalpy_vap <= 0 or boiling_point <= 0 or reference_pressure <= 0:
        raise ValueError("enthalpy_vap (J/mol), boiling_point (K) and reference_pressure (Pa) must be positive")
    if temperature is not None and temperature <= 0:
        raise ValueError("temperature must be positive (K)")
    if pressure is not None and pressure <= 0:
        raise ValueError("pressure must be positive (Pa)")
    if not 10 <= n_points <= 5000:
        raise ValueError("n_points must be between 10 and 5000")
    k = enthalpy_vap / R
    p_of = lambda t: reference_pressure * np.exp(-k * (1 / t - 1 / boiling_point))  # noqa: E731
    t_of = lambda p: 1 / (1 / boiling_point - math.log(p / reference_pressure) / k)  # noqa: E731
    lo = t_min if t_min is not None else boiling_point * 0.7
    hi = t_max if t_max is not None else boiling_point * 1.15
    if not 0 < lo < hi:
        raise ValueError("need 0 < t_min < t_max")
    ts = np.linspace(lo, hi, n_points)
    boil = None
    if pressure is not None:
        denom = 1 / boiling_point - math.log(pressure / reference_pressure) / k
        if denom <= 0:
            raise ValueError("pressure too high for the Clausius-Clapeyron extrapolation")
        boil = t_of(pressure)
    return {
        "result": {
            "vapor_pressure": float(p_of(temperature)) if temperature is not None else None,
            "boiling_point_at_pressure": boil,
            "entropy_vap": enthalpy_vap / boiling_point,
            "trouton_ratio": enthalpy_vap / boiling_point / 88.0,
            "slope_ln_p_vs_inv_t": -k,
        },
        "curve": {"temperature": ts.tolist(), "pressure": p_of(ts).tolist()},
        "units": "pressure in Pa, temperature in K, enthalpy in J/mol, entropy in J/(mol K)",
        "assumptions": [
            "ΔH_vap constant over the temperature range",
            "Vapour is an ideal gas and the liquid volume is negligible next to the vapour volume",
            "Trouton's rule: ΔS_vap ≈ 88 J/(mol K) for many non-hydrogen-bonded liquids",
        ],
    }
