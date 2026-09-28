"""Pressure–temperature phase diagrams: sublimation, vaporisation and melting curves meeting at the triple
point, the critical point, and the phase at any (T, P)."""
import math

import numpy as np

from app.core.registry import tool

R = 8.314462618
# Triple point (K, Pa), critical point (K, Pa), a third vapour-pressure point (K, Pa),
# sublimation (ΔH_sub J/mol, or a second point), fusion ΔH (J/mol) and ΔV (m³/mol, liquid − solid).
SUBSTANCES = {
    "water": {"name": "Water", "triple": (273.16, 611.657), "critical": (647.096, 22.064e6), "vap_mid": (373.124, 101325.0),
              "dh_sub": 51060.0, "dh_fus": 6008.0, "dv_fus": 18.015e-6 / 0.99984 - 18.015e-6 / 0.9167},
    "co2": {"name": "Carbon dioxide", "triple": (216.58, 517.95e3), "critical": (304.13, 7.3773e6), "vap_mid": (273.15, 3.4851e6),
            "sub_point": (194.686, 101325.0), "dh_fus": 9020.0, "dv_fus": 44.01e-6 / 1.178 - 44.01e-6 / 1.512},
}


class _Diagram:
    def __init__(self, d: dict):
        self.d = d
        self.tt, self.pt = d["triple"]
        self.tc, self.pc = d["critical"]
        # ln P = A + B/T + C ln T through the triple, middle and critical points
        pts = [d["triple"], d["vap_mid"], d["critical"]]
        m = np.array([[1, 1 / t, math.log(t)] for t, _ in pts])
        self.coef = np.linalg.solve(m, [math.log(p) for _, p in pts])
        # Sublimation: Clausius–Clapeyron from the triple point (ΔH_sub given, or fitted through a second point)
        if "dh_sub" in d:
            self.dh_sub = d["dh_sub"]
        else:
            ts, ps = d["sub_point"]
            self.dh_sub = R * math.log(self.pt / ps) / (1 / ts - 1 / self.tt)

    def p_vap(self, t):
        a, b, c = self.coef
        return np.exp(a + b / np.asarray(t, float) + c * np.log(np.asarray(t, float)))

    def p_sub(self, t):
        return self.pt * np.exp(-self.dh_sub / R * (1 / np.asarray(t, float) - 1 / self.tt))

    def t_melt(self, p):
        # Integrated Clapeyron with constant ΔH and ΔV: P − Pt = (ΔH/ΔV) ln(T/Tt)
        return self.tt * np.exp((np.asarray(p, float) - self.pt) * self.d["dv_fus"] / self.d["dh_fus"])

    def phase(self, t: float, p: float) -> str:
        if t >= self.tc and p >= self.pc:
            return "supercritical fluid"
        boundary = self.p_sub(t) if t < self.tt else self.p_vap(t) if t <= self.tc else math.inf
        if p < boundary:
            return "gas"
        return "solid" if t < float(self.t_melt(p)) else "liquid"


@tool(
    domain="chemistry",
    name="phase_diagram",
    description=(
        "Pressure–temperature phase diagram of water or co2: sublimation, vaporisation (to the critical point) and "
        "melting curves, triple and critical points, and the phase (solid, liquid, gas, supercritical) at an optional "
        "temperature (K) and pressure (Pa), with the boiling and melting points at that pressure. "
        "Example: substance='water', temperature=298.15, pressure=101325."
    ),
)
def phase_diagram(
    substance: str = "water",
    temperature: float | None = None,
    pressure: float | None = None,
    p_max: float | None = None,
    n_points: int = 200,
) -> dict:
    key = substance.strip().lower()
    if key not in SUBSTANCES:
        raise ValueError(f"substance must be one of {', '.join(SUBSTANCES)}")
    if (temperature is None) != (pressure is None):
        raise ValueError("give both temperature and pressure (or neither)")
    if temperature is not None and (temperature <= 0 or pressure <= 0):
        raise ValueError("temperature (K) and pressure (Pa) must be positive")
    if not 20 <= n_points <= 5000:
        raise ValueError("n_points must be between 20 and 5000")
    dg = _Diagram(SUBSTANCES[key])
    p_top = p_max or dg.pc * 10
    if p_top <= dg.pt:
        raise ValueError("p_max must exceed the triple-point pressure")
    t_sub = np.linspace(dg.tt * 0.7, dg.tt, n_points)
    t_vap = np.linspace(dg.tt, dg.tc, n_points)
    p_melt = np.geomspace(dg.pt, p_top, n_points)
    state = None
    if temperature is not None:
        boil = None
        if dg.pt < pressure < dg.pc:  # invert the vapour curve by bisection on T in [Tt, Tc]
            lo, hi = dg.tt, dg.tc
            for _ in range(80):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if dg.p_vap(mid) < pressure else (lo, mid)
            boil = (lo + hi) / 2
        subl = None
        if pressure < dg.pt:
            subl = 1 / (1 / dg.tt - R * math.log(pressure / dg.pt) / dg.dh_sub)
        state = {
            "temperature": temperature, "pressure": pressure, "phase": dg.phase(temperature, pressure),
            "boiling_point": boil, "sublimation_point": subl,
            "melting_point": float(dg.t_melt(pressure)) if pressure >= dg.pt else None,
            "vapour_pressure": float(dg.p_vap(temperature)) if dg.tt <= temperature <= dg.tc else float(dg.p_sub(temperature)) if temperature < dg.tt else None,
        }
    return {
        "result": {
            "substance": dg.d["name"],
            "triple_point": {"temperature": dg.tt, "pressure": dg.pt},
            "critical_point": {"temperature": dg.tc, "pressure": dg.pc},
            "melting_slope_pa_per_k": dg.d["dh_fus"] / (dg.tt * dg.d["dv_fus"]),
            "sublimation_enthalpy": dg.dh_sub,
            "state": state,
        },
        "curves": {
            "sublimation": {"temperature": t_sub.tolist(), "pressure": dg.p_sub(t_sub).tolist()},
            "vaporisation": {"temperature": t_vap.tolist(), "pressure": dg.p_vap(t_vap).tolist()},
            "melting": {"temperature": dg.t_melt(p_melt).tolist(), "pressure": p_melt.tolist()},
        },
        "units": "temperature in K, pressure in Pa, enthalpy in J/mol, slope in Pa/K",
        "assumptions": ["Vapour curve: ln P = A + B/T + C ln T through the triple, normal/mid and critical points",
                        "Sublimation: Clausius–Clapeyron with constant ΔH_sub; melting: integrated Clapeyron with constant ΔH and ΔV",
                        "Single solid phase (water's high-pressure ices are not modelled); CO2 fusion data approximate"],
    }
