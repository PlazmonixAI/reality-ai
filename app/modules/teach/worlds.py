"""ASM Teach worlds: what each experiment looks like in real life.

A world is a picture type (drawn by frontend/js/teach/worlds_*.js) plus the numbers it needs. Every number is an
expression evaluated here by the engine in the experiment's namespace (its inputs, its computed outputs and the
physical constants), so the browser draws engine results only. When a teacher types a new value, the outputs and
these world numbers are recomputed together and the picture changes the way the real thing would.

Spec values:
  number or expression string   evaluated to a float (None if not a real number)
  "list:N:expr"                 the values of expr for kk = 1..N (N is an expression too; at most 60 terms)
  text keys (lines, title, ...) text with {expr} placeholders formatted to 4 significant figures
  dicts and lists               evaluated item by item
"""
from __future__ import annotations

import math
import re
from functools import lru_cache
from typing import Any

import numpy as np

from app.modules.teach.core import CATALOG, _call, _lambdify

TEXT_KEYS = {"lines", "title", "label", "sub", "name", "nameA", "nameB", "left", "right", "meter", "peak", "rms", "top", "bottom",
             "Vtext", "distText", "load", "markLabel", "barLabel", "dir", "kind", "colour", "metal", "tint", "leftTint", "rightTint",
             "reactant", "product", "dot", "solidColour", "gasColour", "labels", "el", "onlyA", "onlyB", "both"}
FLAG_KEYS = {"sea", "escape", "field", "split", "single", "slab", "heat", "ice", "mirror", "comet"}
MAX_TERMS = 60
WORLDS: dict[str, dict[str, Any]] = {}


def W(exp_id: str, world: str, **spec: Any) -> None:
    if exp_id in WORLDS:
        raise ValueError(f"duplicate world for {exp_id}")
    WORLDS[exp_id] = {"type": world, **spec}


_SUP = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")


def fmt(x: Any, digits: int = 4) -> str:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return str(x)
    if not math.isfinite(v):
        return "no real value"
    if v != 0 and (abs(v) >= 1e6 or abs(v) < 1e-3):
        m, e = f"{v:.{digits - 1}e}".split("e")
        return f"{m}×10{str(int(e)).translate(_SUP)}"
    s = f"{v:.{digits}g}"
    if "e" in s:
        s = f"{v:.{max(0, digits - 1 - int(math.floor(math.log10(abs(v)))))}f}"
    if abs(v) >= 1000:
        whole, _, frac = s.partition(".")
        s = f"{int(float(whole)):,}" + (f".{frac}" if frac else "")
    return s


@lru_cache(maxsize=4096)
def _compiled(expr: str):
    return _lambdify(expr)


def _num(expr: str, ns: dict[str, Any]) -> Any:
    f, names = _compiled(expr)
    val = _call(f, names, ns)
    return val


def _scalar(v: Any) -> float | None:
    try:
        x = float(np.asarray(v, dtype=float))
    except (TypeError, ValueError):
        return None
    return round(x, 12) if math.isfinite(x) else None


def _text(s: str, ns: dict[str, Any]) -> str:
    def sub(m: re.Match) -> str:
        try:
            return fmt(_scalar(_num(m.group(1), ns)))
        except Exception:  # noqa: BLE001 - a bad placeholder shows as a dash, never breaks the lesson
            return "–"
    return re.sub(r"\{([^{}]+)\}", sub, s)


def _eval(key: str, spec: Any, ns: dict[str, Any]) -> Any:
    if isinstance(spec, dict):
        return {k: _eval(k, v, ns) for k, v in spec.items()}
    if isinstance(spec, (list, tuple)):
        return [_eval(key, v, ns) for v in spec]
    if isinstance(spec, bool) or key in FLAG_KEYS:
        return spec if isinstance(spec, bool) else bool(_scalar(_num(str(spec), ns)))
    if spec is None:
        return None
    if isinstance(spec, (int, float)):
        return float(spec)
    if key in TEXT_KEYS and not spec.startswith("list:"):
        return _text(spec, ns)
    if spec.startswith("list:"):
        _, n_expr, expr = spec.split(":", 2)
        n = _scalar(_num(n_expr, ns)) or 0
        kk = np.arange(1, int(max(0, min(MAX_TERMS, round(n)))) + 1, dtype=float)
        if not len(kk):
            return []
        vals = np.broadcast_to(np.asarray(_num(expr, {**ns, "kk": kk}), dtype=float), kk.shape)
        return [round(float(v), 12) if math.isfinite(v) else None for v in vals]
    try:
        return _scalar(_num(spec, ns))
    except Exception:  # noqa: BLE001
        return None


def world_for(exp_id: str, ns: dict[str, Any]) -> dict[str, Any] | None:
    spec = WORLDS.get(exp_id)
    if spec is None:
        return None
    return {k: (_eval(k, v, ns) if k != "type" else v) for k, v in spec.items()}


# ================================================================ physics: motion
W("p9-speed", "drive", v="v_avg", dist="d", lines=["Distance {d} m in {t} s", "Average speed {v_avg} m/s = {kmh} km/h", "Velocity (net displacement / time) {vel} m/s"])
W("p9-third-eq", "drive", v0="u", v1="v", dist="s", lines=["Starts at {u} m/s, accelerates at {a} m/s²", "After {s} m: {v} m/s, taking {t} s"])
W("p9-stopping", "stopping", d1="d_think", d2="d_brake", kmh="kmh")
W("p9-circular", "circle", r="r", T="T", v="v")
W("p11-centripetal", "circle", r="r", T="T", v="v", ac="ac")
W("p9-momentum", "push", m="m", F=0, acc=0, lines=["Momentum p = mv = {p} kg m/s", "Mass {m} kg moving at {v} m/s"])
W("p9-newton2", "push", m="m", F="F", acc="a", lines=["Speed goes from {u} to {v} m/s in {t} s", "Force needed F = ma = {F} N"])
W("p9-catch", "push", m="m", F="F", acc="-v/t", lines=["Stopping a {m} kg ball at {v} m/s in {t} s", "Average force on the hands {F} N: pull the hands back to take longer"])
W("p11-power-motor", "motor", m="m", v="v", lines=["Useful power {P_out} W", "Power drawn {P_in} W at {eta}% efficiency"])
W("p9-power", "motor", m=10, v="Pw/1000", lines=["{Pw} W for {hrs} h a day, {days} days", "Energy used {E_kwh} kWh = {E_J} J"])
W("p9-recoil", "collide", m1="m2", u1=0, m2="m1", u2=0, v1="v2", v2="v1", lines=["Before firing everything is at rest: total momentum 0", "Bullet {m1} kg at {v1} m/s, gun recoils at {v2} m/s"])
W("p9-stick", "collide", m1="m1", u1="u1", m2="m2", u2="u2", v1="v", v2="v", lines=["They stick and move on together at {v} m/s", "Kinetic energy lost {ke_lost} J"])
W("p11-elastic", "collide", m1="m1", u1="u1", m2="m2", u2="u2", v1="v1", v2="v2", lines=["Elastic: momentum and kinetic energy are both kept", "After: {v1} m/s and {v2} m/s"])
W("p11-relative", "trains", vA="vA/3.6", vB="-vB/3.6", d="d*1000", title="Closing speed {vAB} km/h: they meet after {t_meet} min")
W("p11-range-angle", "fall", H="R/4", v="v0", title="Range {R} m at {th}°; the same range at {90 - th}°", lines=["Largest range {R_max} m at 45°"])
W("p9-freefall", "fall", H="h", v="v", lines=["Falls {h} m in {t} s", "Speed on landing {v} m/s"])
W("p9-ke", "push", m="m", F=0, acc=0, lines=["Kinetic energy ½mv² = {KE} J", "Double the speed and the energy is four times"])
W("p9-pe", "fall", H="h", v="sqrt(2*g*h)", title="Raised {h} m: stored energy mgh = {PE} J")
W("p9-energy-cons", "fall", H="H", v="v", PE="PE", KE="KE", title="At {h} m: PE + KE = {total} J all the way down")
W("p11-atwood", "atwood", m1="m1", m2="m2", acc="a", T="T")
W("p11-lift", "lift", acc="a", R="R", kg="R_kg")
W("p11-banking", "banked", th="th", lines=["Best speed with no friction {v_opt} m/s", "Fastest safe speed {v_max} m/s"])
W("p10-pulley", "tackle", n="n", L="L", E="E", MA="MA")
W("p11-com", "seesaw", m1="m1", x1="x1", m2="m2", x2="x2", xcm="xcm")
W("p11-torque", "wrench", F="F", r="r", th="th", tau="tau")
W("p11-rolling", "roll", th="th", v="v", time="t")
W("p11-skater", "spin", w1="w1", w2="w2")
W("p11-spring-energy", "spring", x="x", F="-k*x", lines=["Stretched {x} m: spring pulls back with {F} N", "Stored energy ½kx² = {U} J"])
W("p11-hooke", "spring", x="x/100", F="-F", lines=["A {Mg} g load pulls with {F} N", "The spring stretches {x} cm"])
W("p11-young", "stretch", dL="dL/1000", L="L", load="{Mk} kg", lines=["Stress {stress} Pa, strain {strain}", "The wire stretches {dL} mm"])
W("p9-g-planet", "weigh", items=[{"W": "9.80665", "m": 1, "name": "Earth"}, {"W": "g", "m": 1, "name": "This planet"}])
W("p9-weight", "weigh", items=[{"W": "W", "m": "m", "name": "Here (g = {g})"}, {"W": "W_moon", "m": "m", "name": "On the Moon"}])
W("p11-orbit", "orbit", R=6.371e6, hgt="h*1000", title="{h} km up: {v} m/s, one lap every {T} min", lines=["Orbit radius {r} m"])
W("p11-escape", "orbit", R="R_e*6.371e6", hgt="R_e*6.371e6*0.3", escape=True, title="Escape speed {ve} km/s", lines=["Orbit speed near the surface {vo} km/s"])
W("p11-g-height", "orbit", R=6.371e6, hgt="h*1000", title="g at {h} km up: {g_h} m/s²", lines=["g at {h} km deep: {g_d} m/s²"])
W("p11-kepler", "orbit", R=6.96e8, hgt="a*1.496e11 - 6.96e8", title="Orbit of {a} AU: one year there is {T} Earth years", lines=["Orbital speed {v} km/s"])
W("p11-errors", "bars", vals=["ea", "eb", "ez"], hi=2, labels=["A", "B", "Z"], lines=["Error in Z = |p|·error in A + |q|·error in B = {ez}%"])

# ---------------------------------------------------------------- fluids
W("p9-pressure", "pressure", F="F", A="A", P="Pr")
W("p11-hydraulic", "hydraulic", d1="d1/100", d2="d2/100", F1="F1", F2="F2")
W("p11-pressure-depth", "depth", hd="h", title="At {h} m: gauge {Pg} Pa, total {Pabs} Pa")
W("p9-archimedes", "float", rhoO="1000*rel_d", rhoL="rho", lines=["Loses {Fb} N of weight in the liquid", "Relative density {rel_d}"])
W("p9-rel-density", "float", rhoO="rho", rhoL="rho_l", lines=["Density {rho} kg/m³, relative density {rd}"])
W("p11-venturi", "venturi", v1="v1", v2="v2", dP="dP")
W("p11-stokes", "stokes", vt="vt", r="r/1000")
W("p11-capillary", "capillary", hc="h/100")

# ---------------------------------------------------------------- heat
W("p10-calorimetry", "heat", items=[{"T": "T1", "label": "{m1} kg at {T1} °C"}, {"T": "Tf", "label": "mixed: {Tf} °C", "heat": False}, {"T": "T2", "label": "{m2} kg at {T2} °C"}], lines=["Heat passed from hot to cold {Q} J"])
W("p10-latent", "heat", items=[{"T": 0, "label": "{m} kg of ice at 0 °C", "ice": True}, {"T": "Tf", "label": "water at {Tf} °C", "heat": True}], lines=["Melting takes {Q_melt} J, warming {Q_warm} J", "Total {Q} J"])
W("p11-specific-heat", "heat", items=[{"T": "20", "label": "start"}, {"T": "20 + dT", "label": "after {Q} J", "heat": True}], lines=["{m} kg warmed by {dT} K needs Q = mcΔT = {Q} J"])
W("p11-cooling", "heat", items=[{"T": "T0", "label": "at the start"}, {"T": "T", "label": "after {t} min"}], lines=["Cooling towards {Ts} °C: now {T} °C, losing {rate} °C per minute"])
W("p11-expansion", "rod", dL="L*alpha*dT", dT="dT", lines=["A {L} m rod grows by {dL} m when heated by {dT} K"])
W("p11-conduction", "conduct", H="H")
W("p11-stefan", "glow", Tk="T", lam="lam_max*1e-9", P="P")
W("p11-isothermal", "piston", ratio="V2/V1", speed="sqrt(T)/40", lines=["Isothermal: the gas stays at {T} K", "Work done by the gas {W} J, final pressure {P2} Pa"])
W("p11-adiabatic", "piston", ratio="ratio", speed="sqrt(T2)/40", lines=["Squeezed fast, no heat escapes", "Temperature rises to {T2} K, pressure {P2} Pa"])
W("p11-carnot", "engine", Th="Th", Tc="Tc", Qh="Qh", Qc="Qc", W="W", eta="eta/100")  # eta is in %
W("p11-vrms", "gasbox", items=[{"n": 40, "speed": "v_rms/2000", "label": "molecules at {T} K: rms speed {v_rms} m/s"}])

# ---------------------------------------------------------------- sound and waves
W("p9-echo", "echo", d="d", v="v", time="t", sea=True, title="Echo after {t} s: the sea bed is {d} m down")
W("p9-sound-temp", "echo", d=340, v="v", time="2*340/v", title="At {Tc} °C sound travels {v} m/s")
W("p11-string", "standing", nh="nh", f="f", kind="string", lines=["Wave speed {v} m/s, wavelength {lam} m"])
W("p12-sonometer-ac", "standing", nh=1, f="f", kind="string", lines=["A {M} kg load: tension {T} N, frequency {f} Hz"])
W("p11-pipes", "standing", nh="nh", f="f_open", kind="open", lines=["Open pipe {f_open} Hz, closed pipe {f_closed} Hz"])
W("p11-resonance-tube", "standing", nh=2, f="f", kind="closed", lines=["Wavelength {lam} m, speed of sound {v} m/s, end correction {e} cm"])
W("p11-beats", "beats", f1="f1", f2="f2", fb="fb")
W("p11-doppler", "doppler", vs="vs", f="f", fh="f_heard")

# ---------------------------------------------------------------- electricity
W("p10-resistivity", "loop", I=1, V="R", parts=[{"label": "R = {R} Ω", "P": "R"}], title="A {L} m wire of {dmm} mm: R = {R} Ω", Vtext="")
W("p10-joule-heating", "loop", I="I", V="V", parts=[{"label": "{R} Ω", "P": "Pw"}], title="{Pw} W of heat: {H} J in {t} s")
W("p12-drift", "loop", I="I", V=1, parts=[{"label": "copper wire", "P": 0}], title="Electrons drift at only {vd} m/s", Vtext="")
W("p12-temp-res", "loop", I=1, V=1, parts=[{"label": "{R} Ω at {Tc} °C", "P": "R/10"}], title="Resistance at {Tc} °C: {R} Ω", Vtext="")
W("p12-internal", "loop", I="I", V="Ec", parts=[{"label": "R = {R} Ω", "P": "P"}], title="I = {I} A, terminal voltage {V} V", lines=["Lost inside the cell: {Ec - V} V"])
W("p12-kirchhoff", "loop", I="I", V="E1", parts=[{"label": "R = {R} Ω", "P": "V*I"}], title="Through R: {I} A at {V} V", lines=["From cell 1: {I1} A, from cell 2: {I2} A"])
W("p12-ammeter", "loop", I="Ig", V=1, parts=[{"label": "shunt {S} Ω", "P": 0}, {"label": "series {Rs} Ω", "P": 0}], meter="G", title="Shunt {S} Ω for an ammeter, series {Rs} Ω for a voltmeter")
W("p12-diode", "loop", I="I/1000", V="V", parts=[{"label": "diode", "P": "V*I/1000"}], title="{V} V forward: {I} mA flows")
W("p12-zener", "loop", I="Is/1000", V="Vin", parts=[{"label": "Rs", "P": 0}, {"label": "Zener {Vz} V", "P": 0}, {"label": "load", "P": 0}], title="Load gets {Vz} V; the Zener takes {Iz} mA")
W("p12-lr", "loop", I="I", V="Ec", parts=[{"label": "R {R} Ω", "P": "I**2*R"}, {"label": "L {L} H", "P": 0}], title="After {t} s: {I} A (time constant {tau} s)")
W("p12-metre-bridge", "bridge", l="l", meter="G", lines=["Balance at {l} cm: S = {S} Ω"])
W("p12-mb-combination", "bridge", l="ls", meter="G", lines=["Series {Rs} Ω balances at {ls} cm", "Parallel {Rp} Ω balances at {lp} cm"])
W("p12-potentiometer", "bridge", l="Min(100, l1/4)", meter="G", lines=["Balance lengths {l1} cm and {l2} cm", "E₂ = {E2} V"])
W("p12-pot-internal", "bridge", l="Min(100, l1/5)", meter="G", lines=["Open circuit {l1} cm, with {R} Ω: {l2} cm", "Internal resistance r = {r} Ω"])
W("p12-galvanometer", "loop", I="E/(R + G)", V="E", parts=[{"label": "R {R} Ω", "P": 0}, {"label": "shunt {S} Ω", "P": 0}], meter="G", title="Galvanometer resistance {G} Ω", lines=["Figure of merit {k} A per division"])
W("p12-capacitor", "capacitor", d="d/1000", K="K", fill=1, lines=["C = {C} pF, charge {Q} nC", "Stored energy {U} J"])
W("p12-cap-combo", "capacitor", d=0.002, fill=1, lines=["Series {Cs} µF", "Parallel {Cp} µF"])
W("p12-rc", "capacitor", d=0.002, fill="Vc/V0", bar="Vc/V0", barLabel="{Vc} V", lines=["After {t} s: capacitor at {Vc} V, current {I} A", "Time constant RC = {tau} s"])
W("p12-dipole", "dipole", lines=["Dipole moment {p} C m", "On the axis {E_axial} N/C, on the bisector {E_eq} N/C"])
W("p12-dipole-torque", "dipole", field=True, th="th", tau="tau", lines=["At {th}°: torque {tau} N m", "Energy {U} J"])
W("p12-gauss", "dipole", lines=["Line of charge: E = {E_line} N/C", "Sheet of charge: E = {E_sheet} N/C"])
W("p10-wire-field", "bfield", kind="wire", I="I", lines=["{I} A: B = {B} T at {r} m"])
W("p10-solenoid", "bfield", kind="solenoid", I="I", lines=["{n} turns per metre: B = {B} T inside"])
W("p12-loop", "bfield", kind="wire", I="I", lines=["On the axis B = {B} T, at the centre {B0} T"])
W("p12-inductance", "bfield", kind="solenoid", I="I", lines=["Self-inductance {L} H, stored energy {U} J"])
W("p10-force-wire", "bfield", kind="magnet", F="F", lines=["Force on the wire {F} N"])
W("p12-parallel-wires", "bfield", kind="parallel", I1="I1", I2="I2", d="d", lines=["Force per metre {F_L} N/m"])
W("p12-cyclotron", "bfield", kind="spiral", r="r/1000", lines=["Circle radius {r} mm, {f} MHz"])
W("p12-coil-torque", "bfield", kind="coil", f=5, lines=["Torque {tau} N m, magnetic moment {m} A m²"])
W("p12-generator", "bfield", kind="coil", f="f", lines=["Peak EMF {E0} V, rms {Erms} V at {f} Hz"])
W("p12-motional", "bfield", kind="rails", v="v", lines=["EMF {emf} V drives {I} A", "Force needed to keep it moving {F} N"])
W("p12-ac-rms", "ac", peak="peak {V0} V", rms="rms {Vrms} V", lines=["Power in {R} Ω: {P} W"])
W("p12-rectifier", "ac", peak="peak {Vm} V", rms="", lines=["Half wave gives {Vdc_half} V dc, full wave {Vdc_full} V dc"])
W("p12-lcr", "ac", peak="", rms="", lines=["Impedance {Z} Ω, current {I} A, phase {phi}°", "Resonance at {f0} Hz"])
W("p12-transformer", "ac", peak="", rms="", lines=["{Vp} V in, {Vs} V out", "Secondary current {Is} A"])

# ---------------------------------------------------------------- light
W("p10-snell", "refract", i="i", r="r", n2="n2", top="n₁ = {n1}", bottom="n₂ = {n2}", lines=["Bends by {dev}°"])
W("p10-index-speed", "refract", i=40, r="asin(sin(40*pi/180)/n)*180/pi", n2="n", top="air", bottom="n = {n}", lines=["Light slows to {v} m/s"])
W("p10-slab", "refract", i="i", r="r", n2="n", slab=True, top="air", bottom="glass n = {n}", lines=["Comes out parallel at {e}°, shifted {d} cm"])
W("p12-tir", "refract", i="C + 5", r=None, n2="n1", top="n = {n2}", bottom="n = {n1}", lines=["Critical angle {C}°: beyond it, total internal reflection"])
W("p12-brewster", "refract", i="thB", r="r", n2="n", top="air", bottom="n = {n}", lines=["At Brewster's angle {thB}° the reflected light is fully polarised"])
W("p12-ydse", "fringes", lam="lam*1e-9", beta="beta*1e-3", title="Fringe width {beta} mm", lines=["Slits {d} mm apart, screen {D} m away"])
W("p12-single-slit", "fringes", lam="lam*1e-9", beta="w*1e-3/2", single=True, title="Central bright band {w} mm wide")
W("p12-malus", "polar", th="th", f="I/I0")
W("p12-photoelectric", "photo", lam="lam*1e-9", K="Kmax")
W("p12-spectrum", "levels", n1="n1", n2="n2", lam="lam*1e-9", E="E")
W("p12-binding", "nucleus", Z="Z", A="A", lines=["Binding energy {BE} MeV", "{BEA} MeV per nucleon"])
W("p12-em-waves", "wave", lam="lam", lamRel="log(lam*1e9)/log(10)", lines=["{f} Hz, wavelength {lam} m", "Photon energy {E} eV"])
W("p12-de-broglie", "wave", lam="lam*1e-9", lamRel="lam", colour="#7fd3ff", lines=["An electron through {V} V", "λ = {lam} nm"])

# ================================================================ chemistry
W("c9-concentration", "solution", items=[{"n": "mass_pct*3", "strength": "mass_pct/40", "label": "{ms} g in {mw} g water", "sub": "{mass_pct}% by mass"}])
W("c9-solubility", "solution", items=[{"n": "max_dissolve*2", "strength": 0.4, "solid": "excess/(added + 1e-9)", "label": "{added} g added, {max_dissolve} g dissolves", "sub": "{excess} g stays as solid"}])
W("c9-kelvin", "heat", items=[{"T": "Tc", "label": "{Tc} °C = {Tk} K"}])
W("c9-mole", "balance", m="m", lines=["{m} g = {n} mol", "= {Np} particles"])
W("c9-molecular-mass", "molecule", atoms=[{"el": "C", "n": "nC"}, {"el": "H", "n": "nH", "colour": "#ffffff"}, {"el": "O", "n": "nO", "colour": "#e74c3c"}, {"el": "N", "n": "nN", "colour": "#3498db"}], lines=["Molecular mass {M} u, carbon {pC}%"])
W("c9-avg-atomic-mass", "bars", vals=["p1", "100 - p1"], labels=["mass {m1}", "mass {m2}"], lines=["Average atomic mass {Mavg} u"])
W("c9-const-proportion", "balance", m="mW", lines=["{mH} g hydrogen + {mO} g oxygen", "always make {mW} g water (1 : 8 by mass)"])
W("c10-dilution", "solution", items=[{"n": 60, "strength": "M1/4", "fill": "V1/Max(V1, V2)", "label": "{V1} mL of {M1} mol/L"}, {"n": "60*V1/V2", "strength": "M2/4", "fill": "V2/Max(V1, V2)", "label": "add water to {V2} mL", "sub": "{M2} mol/L, pH {pH2}"}])
W("c10-decomposition", "heatTube", lines=["{m} g of CaCO₃ gives {mCaO} g of CaO", "and {mCO2} g of CO₂ ({V_CO2} L)"])
W("c10-combustion", "burner", Q="Q*1e6", T=80, lines=["{m} kg of fuel releases {Q} MJ", "enough to boil {water} kg of water"])
W("c10-alkane", "molecule", atoms=[{"el": "C", "n": "n"}, {"el": "H", "n": "H", "colour": "#ffffff"}], lines=["C{n}H{H}: {M} u, burns with {O2} mol of O₂"])
W("c10-gas-volume", "balance", m="m", lines=["{n} mol fills {V} L at STP", "density {rho} g/L"])
W("c10-percent-comp", "bars", vals=["pct", "100 - pct"], labels=["element", "rest"], hi=0, lines=["{pct}% by mass"])
W("c10-electrolysis", "electrolysis", I="I", m="m", lines=["{I} A for {t} min: {Q} C", "deposits {m} g of metal"])
W("c12-faraday", "electrolysis", I="I", m="m", lines=["{Q} C = {ne} mol of electrons", "deposits {m} g"])
W("c11-molarity", "solution", items=[{"n": "M*40", "strength": "M/2", "label": "{n} mol in {V} mL", "sub": "{M} mol/L, {mb} mol/kg"}])
W("c11-limiting", "equilibrium", fA="nN2/(nN2 + nH2)", dir="Makes {mNH3} g of NH₃", lines=["{nN2} mol N₂ and {nH2} mol H₂: the one that runs out first decides"])
W("c11-empirical", "bars", vals=["pC", "pH", "pO"], labels=["C", "H", "O"], lines=["C {pC}%, H {pH}%, O {pO}%"])
W("c11-photon", "wave", lam="lam*1e-9", lines=["{lam} nm: {nu} Hz", "Each photon {E} J, {E_mol} kJ per mole"])
W("c11-debroglie", "wave", lam="lam", lamRel="Max(0.3, log(lam*1e12 + 1)/log(10))", colour="#7fd3ff", lines=["A {m} kg particle at {v} m/s", "has a wavelength of {lam} m"])
W("c11-uncertainty", "wave", lam=5e-7, colour="#7fd3ff", lines=["Pinned down to {dx} m", "its speed is uncertain by at least {dv} m/s"])
W("c11-dipole", "dipole", lines=["Observed {mu_obs} D of {mu_ionic} D if fully ionic", "{ionic}% ionic character"])
W("c11-bond-order", "orbitals", n="Min(5, Abs(Nb - Na)/2)", lines=["Bond order ({Nb} − {Na})/2 = {bo}"])
W("c11-dalton", "gasbox", items=[{"n": "40*x1", "colour": "#2a78d6", "label": "gas 1: {p1} atm"}, {"n": "40*(1 - x1)", "colour": "#eb6834", "label": "gas 2: {p2} atm"}], lines=["Total {P} atm = sum of partial pressures"])
W("c11-graham", "gasbox", items=[{"n": 25, "speed": "0.8", "colour": "#2a78d6", "label": "M = {M1}"}, {"n": 25, "speed": "0.8/ratio", "colour": "#eb6834", "label": "M = {M2}"}], lines=["The lighter gas spreads {ratio} times faster"])
W("c11-vdw", "piston", ratio=1, speed="sqrt(T)/30", lines=["Real gas {P_real} atm, ideal {P_ideal} atm", "Compressibility Z = {Zc}"])
W("c11-first-law", "piston", ratio="1 + dV/2", speed=0.5, lines=["Heat in {q} J, work {w} J", "Internal energy changes by {dU} J"])
W("c11-dh-du", "piston", ratio=1.5, speed=0.5, lines=["ΔU = {dU} kJ/mol, Δn(gas) = {dng}", "ΔH = {dH} kJ/mol"])
W("c11-gibbs", "downhill", dG="dG", lines=["ΔH = {dH} kJ/mol, ΔS = {dS} J/(mol K) at {T} K", "Turns spontaneous at {Tc} K; K = {K}"])
W("c11-calorimeter", "burner", Q="q*1000", T="25 + dT", lines=["Temperature rose {dT} K: {q} kJ", "ΔU = {dU} kJ/mol"])
W("c11-kp-kc", "equilibrium", fA=0.5, dir="Kp = {Kp}", lines=["Kc = {Kc}, Δn(gas) = {dng}, T = {T} K"])
W("c11-ksp", "solution", items=[{"n": "Min(120, s*1e5)", "strength": 0.2, "solid": 0.6, "label": "saturated", "sub": "solubility {s} mol/L = {s_g} g/L"}])
W("c11-dou", "molecule", atoms=[{"el": "C", "n": "nC"}, {"el": "H", "n": "nH", "colour": "#ffffff"}, {"el": "N", "n": "nN", "colour": "#3498db"}], lines=["Degree of unsaturation {dou}: rings plus double bonds"])
W("c11-reaction-quotient", "equilibrium", fA="1/(1 + Qr)", dir="{direction}", lines=["Q = {Qr}, K = {K}", "ΔG = {dG} kJ/mol"])
W("c12-raoult", "vapour", xA="xA", yA="yA", p="p", lines=["Vapour pressure {p} kPa", "Vapour is {yA} A"])
W("c12-henry", "solution", items=[{"n": "Min(140, x*1e5)", "strength": 0.15, "gas": "p/10", "label": "gas at {p} kPa", "sub": "{mol_L} mol/L dissolves"}])
W("c12-bp", "solution", items=[{"n": 0, "strength": 0.15, "T": 100, "heat": True, "label": "pure water boils at 100 °C"}, {"n": "mb*60", "strength": 0.3, "T": "100 + dTb", "heat": True, "label": "solution", "sub": "boils {dTb} K higher"}])
W("c12-fp", "solution", items=[{"n": 0, "strength": 0.15, "T": 0, "Tlo": -20, "Thi": 20, "label": "pure water freezes at 0 °C"}, {"n": "mb*60", "strength": 0.3, "T": "-dTf", "Tlo": -20, "Thi": 20, "label": "solution", "sub": "freezes {dTf} K lower"}])
W("c12-osmotic", "osmosis", Pi="Pi_kPa*1000")
W("c12-molar-mass", "solution", items=[{"n": 20, "strength": 0.3, "T": "100 + dTb", "heat": True, "label": "boiling point up {dTb} K", "sub": "molar mass {M2} g/mol"}])
W("c12-nernst", "cell", E="E", lines=["E = E° − (0.0592/n) log Q = {E} V"])
W("c12-cell-gibbs", "cell", E="E0", lines=["ΔG = −nFE = {dG} kJ/mol", "log K = {log10K}"])
W("c12-daniell-conc", "cell", E="E", left="Zn in {cZn} mol/L", right="Cu in {cCu} mol/L", lines=["E = {E} V, ΔG = {dG} kJ/mol"])
W("c12-conductivity", "electrolysis", I="kappa*100", m=0, lines=["Molar conductivity {Lm} S cm²/mol"])
W("c12-kohlrausch", "electrolysis", I="Lm/50", m=0, lines=["At {C} mol/L: {Lm} S cm²/mol", "At infinite dilution {L0}"])
W("c12-first-order", "kinetics", frac="A/A0", speed=0.4, lines=["After {t} s: {A} mol/L", "Half-life {t_half} s"])
W("c12-zero-order", "kinetics", frac="Max(0, A/A0)", speed=0.4, lines=["After {t} s: {A} mol/L", "Half-life {t_half} s"])
W("c12-rate-law", "kinetics", frac=0.6, speed="Min(1, rate*2)", lines=["Rate {rate} mol/(L s)", "Overall order {order}"])
W("c12-arrhenius", "hill", Ea="Ea", frac="frac", dH=-40, lines=["At {T} K: k = {k} per s", "Fraction with enough energy {frac}"])
W("c12-arrhenius-two", "hill", Ea="Ea", frac="Min(1, ratio/20)", dH=-40, lines=["{T1} K → {T2} K: k from {k1} to {k2}", "{ratio} times faster"])
W("c12-thiosulphate", "kinetics", frac="Max(0, 1 - 30/t)", speed="Min(1, (T + 10)/80)", product="#f1d36b", lines=["The cross disappears after {t} s", "Rate {rate} per s"])
W("c12-spin-moment", "orbitals", n="n", lines=["μ = √(n(n + 2)) = {mu} BM"])
W("c12-cfse", "orbitals", split=True, t2g="t2g", eg="eg", D="D0/200", lines=["CFSE = {cfse} kJ/mol ({cfse_D} Δo)"])
W("c12-unit-cell", "crystal", Z="Zc", rho="rho*1000")
W("c12-beer", "colorimeter", A="A", Tr="T/100")
W("c12-chromatography", "chroma", ds="ds", df="df", Rf="Rf")
W("c12-neutralisation-heat", "heat", items=[{"T": 25, "label": "{Va} mL acid"}, {"T": "25 + dT", "label": "mixed: up {dT} K"}, {"T": 25, "label": "{Vb} mL alkali"}], lines=["{q} J for {n} mol: ΔH = {dH} kJ/mol"])
W("c12-dissolution-heat", "heat", items=[{"T": 25, "label": "water"}, {"T": "25 - dT", "label": "after dissolving {ms} g"}], lines=["ΔH(solution) = {dH} kJ/mol"])
W("c12-mohr-salt-prep", "yieldDish", got="got", theo="theo", pct="pct", colour="#bfe3d0")
W("c12-acetanilide", "yieldDish", got="got", theo="theo", pct="pct", colour="#ffffff")

# ================================================================ mathematics
W("m9-parallelogram", "quad", b1="b1", b2="b2", h="h", Ap="A_par", At="A_trap")
W("m9-mean", "bars", vals="list:n:first + (kk - 1)*step", mark="mean", markLabel="mean {mean}", lines=["{n} values, total {total}", "Mean = median = {mean}"])
W("m10-ap", "stairs", vals="list:n:a + (kk - 1)*d", lines=["nth term {an}", "Sum of {n} terms {Sn}"])
W("m11-gp", "stairs", vals="list:n:a*r**(kk - 1)", lines=["nth term {an}", "Sum {Sn}"])
W("m11-means", "bars", vals=["a", "AM", "GM", "HM", "b"], labels=["a", "AM", "GM", "HM", "b"], hi=1, lines=["AM {AM} ≥ GM {GM} ≥ HM {HM}"])
W("m10-recurring-deposit", "money", vals="list:n:P*kk + P*kk*(kk + 1)/24*r/100", lines=["Pay {P} a month for {n} months", "Maturity value {MV} (interest {I})"])
W("m10-compound", "money", vals="list:n:P*(1 + r/100)**kk", lines=["Amount after {n} years {A}", "Compound interest {CI}, simple would be {SI}"])
W("m10-distance", "plane", pts=[{"x": "x1", "y": "y1", "label": "A"}, {"x": "x2", "y": "y2", "label": "B"}, {"x": "mx", "y": "my", "label": "M"}], segs=[[0, 1]], lines=["AB = {d}", "Midpoint ({mx}, {my})"])
W("m10-section", "plane", pts=[{"x": "x1", "y": "y1", "label": "A"}, {"x": "x2", "y": "y2", "label": "B"}, {"x": "px", "y": "py", "label": "P", "colour": "#FF5B2E"}], segs=[[0, 1]], lines=["P divides AB in {m} : {n}", "P = ({px}, {py})"])
W("m10-triangle-area", "plane", pts=[{"x": "x1", "y": "y1"}, {"x": "x2", "y": "y2"}, {"x": "x3", "y": "y3"}], segs=[[0, 1], [1, 2], [2, 0]], poly=[0, 1, 2], lines=["Area {A}"])
W("m11-point-line", "plane", pts=[{"x": "x0", "y": "y0", "label": "P"}], line=["A", "B", "C"], lines=["Line {A}x + {B}y + {C} = 0", "Distance from P: {d}"])
W("m11-line", "plane", pts=[{"x": "x1", "y": "y1"}, {"x": "x2", "y": "y2"}], segs=[[0, 1]], line=["m", "-1", "c"], lines=["Slope {m}, angle {ang}°", "y = {m}x + {c}"])
W("m10-two-angles", "tower", H="h", x="x", d="d", al="be", be="al")
W("m10-tangent", "tangent", r="r", d="d", L="t")
W("m10-frustum", "solid", kind="frustum", R="R", r="r", h="h", lines=["Slant height {l} cm", "Volume {V} cm³, curved surface {CSA} cm²"])
W("m10-combined", "solid", kind="conehemi", R="r", h="h", lines=["Volume {V} cm³", "Surface area {SA} cm²"])
W("m12-box", "solid", kind="box", s="s", x="x", lines=["Volume {V} cm³", "Best cut {x_best} cm gives {V_best} cm³"])
W("m10-dice", "dice", S="S", ways="ways", P="P")
W("m10-probability", "bag", total="total", fav="fav", P="P", lines=["P(not) = {Pnot}"])
W("m10-mode", "bars", vals=["f0", "f1", "f2"], labels=["before", "modal", "after"], hi=1, lines=["Mode = {mode}"])
W("m10-median", "bars", vals=["cf", "f", "n - cf - f"], labels=["below", "median class", "above"], hi=1, lines=["Median = {median}"])
W("m11-variance", "bars", vals="list:n:kk", mark="mean", markLabel="mean {mean}", lines=["Variance {var}, standard deviation {sd}"])
W("m12-binomial-dist", "bars", vals="list:n + 1:binomial(n, kk - 1)*p**(kk - 1)*(1 - p)**(n - kk + 1)", hi="r", labels="list:n + 1:kk - 1", lines=["P(X = {r}) = {Pr}", "Mean {mean}, variance {var}"])
W("m10-zeros", "plane", pts=[{"x": "(-b + sqrt(b**2 - 4*a*c))/(2*a)", "y": 0, "label": "α"}, {"x": "(-b - sqrt(b**2 - 4*a*c))/(2*a)", "y": 0, "label": "β"}], lines=["Sum of zeros −b/a = {s}", "Product c/a = {p}"])
W("m11-radian", "angle", A="deg", lines=["{deg}° = {rad} rad", "Arc length {s} cm on radius {r} cm"])
W("m11-compound-angle", "angle", A="A", B="B", lines=["sin(A + B) = {lhs}", "cos(A + B) = {cosAB}"])
W("m12-inverse-trig", "angle", A="asn", lines=["sin⁻¹({x}) = {asn}°", "cos⁻¹ = {acs}°, tan⁻¹ = {atn}°"])
W("m11-de-moivre", "complex", r="r", th="th", n="n", lines=["zⁿ has length {rn} and angle {argn}°", "= {re} + {im}i"])
W("m11-perm-comb", "arrange", n="n", r="r", lines=["Arrangements nPr = {nPr}", "Selections nCr = {nCr}"])
W("m11-binomial", "bars", vals="list:n + 1:binomial(n, kk - 1)", hi="r", labels="list:n + 1:kk - 1", lines=["Coefficients of (a + b)^{n}", "Term {r + 1} = {T}"])
W("m11-3d-distance", "space", pts=[{"x": "x1", "y": "y1", "z": "z1"}, {"x": "x2", "y": "y2", "z": "z2"}], segs=[[0, 1]], lines=["Distance {d}"])
W("m12-line-angle", "space", lineDirs=[{"v": ["a1", "b1", "c1"]}, {"v": ["a2", "b2", "c2"]}], lines=["Angle between the lines {th}°"])
W("m12-plane-distance", "space", pts=[{"x": "x0", "y": "y0", "z": "z0"}], lineDirs=[{"v": ["a", "b", "c"], "p": ["x0", "y0", "z0"]}], lines=["Distance to the plane {D}"])
W("m12-skew", "space", lineDirs=[{"v": [1, 0, 0], "p": [0, 0, 0]}, {"v": ["cos(th*pi/180)", "sin(th*pi/180)", 0], "p": [0, 0, "h"]}], lines=["Shortest distance {d}"])
W("m11-prob-union", "venn", onlyA="{PA - PAB}", both="{PAB}", onlyB="{PB - PAB}", overlap="PAB/Max(1e-9, Min(PA, PB))", lines=["P(A or B) = {PAorB}"])
W("m11-sets", "venn", onlyA="{onlyA}", both="{nAB}", onlyB="{onlyB}", overlap="nAB/Max(1e-9, Min(nA, nB))", lines=["n(A ∪ B) = {nAorB}"])
W("m12-conditional", "venn", onlyA="{PA - PAB}", both="{PAB}", onlyB="{PB - PAB}", overlap="PAB/Max(1e-9, Min(PA, PB))", lines=["P(A|B) = {PAgB}, P(B|A) = {PBgA}"])
W("m12-bayes", "population", prior="prior", sens="sens", fpr="fpr", post="post")
W("m12-det", "matrix", a="a", b="b", c="c", d="d", lines=["det = {D2}: the square's area scales by this", "3 × 3 determinant {D3}"])
W("m12-inverse-2x2", "matrix", a="a", b="b", c="c", d="d", lines=["det = {det}", "Inverse [[{i11}, {i12}], [{i21}, {i22}]]"])
W("m12-cramer", "plane", pts=[{"x": "x", "y": "y", "label": "solution"}], line=["a1", "b1", "-c1"], lines=["{a1}x + {b1}y = {c1} and {a2}x + {b2}y = {c2}", "x = {x}, y = {y}"])
W("m12-rate", "ripple", r="r", drdt="drdt", lines=["Radius {r} cm growing {drdt} cm/s", "Area grows {dAdt} cm²/s"])
W("m12-lpp", "lpp", corners=[[0, 0], [0, "A"], ["Min(A, B)", "A - Min(A, B)"], ["Min(A, B)", 0]], p="p", q="q", Zmax="Zmax", best="2*(Zmax == Z_2) + 1*(Zmax == Z_1)*(Zmax != Z_2)", lines=["Maximum Z = {Zmax}"])

# curves for the area and slope pictures: 60 sample points computed here (k = 1..60)
_X = "{lo} + ({hi} - ({lo}))*(kk - 1)/59"
W("m12-riemann", "area", xs="list:60:" + _X.format(lo=0, hi="b"), fy="list:60:(" + _X.format(lo=0, hi="b") + ")**2",
  rx="list:n:(kk - 1)*b/n", rh="list:n:(kk*b/n)**2", rw="b/n", lines=["{n} rectangles: {S}", "Exact {exact}, error {err}"])
W("m12-area-between", "area", xs="list:60:" + _X.format(lo=0, hi="xm"), fy="list:60:kk*0 + (" + _X.format(lo=0, hi="xm") + ")*xm",
  gy="list:60:(" + _X.format(lo=0, hi="xm") + ")**2", lines=["Between y = {k}x and y = x²: area {A}"])
W("m12-by-parts", "area", xs="list:60:" + _X.format(lo=0, hi="b"), fy="list:60:(" + _X.format(lo=0, hi="b") + ")*exp(" + _X.format(lo=0, hi="b") + ")",
  lines=["∫ x eˣ dx from 0 to {b} = {I}"])
W("m11-first-principle", "secant", xs="list:60:" + _X.format(lo="a - 1.5", hi="a + h + 1"), fy="list:60:(" + _X.format(lo="a - 1.5", hi="a + h + 1") + ")**n",
  x0="a", x1="a + h", slope="exact", lines=["Secant slope {secant}", "Exact derivative {exact}"])
W("m12-mvt", "secant", xs="list:60:" + _X.format(lo="a - 0.5", hi="b + 0.5"), fy="list:60:(" + _X.format(lo="a - 0.5", hi="b + 0.5") + ")**3 - (" + _X.format(lo="a - 0.5", hi="b + 0.5") + ")",
  x0="a", x1="b", slope="slope", lines=["Chord slope {slope}", "The tangent is parallel at c = {c}"])

# lenses on an optical bench (focal lengths in cm)
W("p10-lens-power", "lensbench", lenses=[{"x": 0, "f": "ft"}], lines=["P₁ = {P1} D, P₂ = {P2} D", "Together {Pt} D: one lens of f = {ft} cm"])
W("p10-myopia", "lensbench", lenses=[{"x": 0, "f": "100/P_myopia"}], lines=["Short sight: a {P_myopia} D concave lens", "Long sight: a {P_hyper} D convex lens"])
W("p12-lensmaker", "lensbench", lenses=[{"x": 0, "f": "f"}], lines=["n = {n}, R₁ = {R1} cm, R₂ = {R2} cm", "f = {f} cm, power {P} D"])
W("p12-telescope", "lensbench", lenses=[{"x": 0, "f": "fo"}, {"x": "fo + fe", "f": "fe"}], lines=["Telescope: magnifies {M_tel} times, tube {L_tel} cm", "Microscope: {M_mic} times"])
W("p12-convex-mirror", "lensbench", mirror=True, lenses=[{"x": 0, "f": "-f"}], lines=["Radius of curvature {Rm} cm", "Focal length {f} cm"])
W("p12-concave-lens", "lensbench", lenses=[{"x": 0, "f": "f2"}], lines=["Combination focal length {F} cm", "Concave lens alone: {f2} cm"])
W("p12-liquid-n", "lensbench", lenses=[{"x": 0, "f": "fl"}], lines=["Liquid lens focal length {fl} cm", "Refractive index of the liquid {n}"])
W("p12-min-dev", "refract", i="i", r="A/2", n2="n", top="air", bottom="prism n = {n}", lines=["Minimum deviation {dm}° at incidence {i}°"])
W("p12-glass-slab", "refract", i=30, r="asin(sin(pi/6)/n)*180/pi", n2="n", slab=True, top="air", bottom="glass", lines=["Real depth {real} cm, apparent {app} cm", "n = {n}"])

# ---------------------------------------------------------------- maths graphs as real things
def _curve(lo, hi, expr: str) -> tuple[str, str]:
    x = _X.format(lo=lo, hi=hi)
    return "list:60:" + x, "list:60:" + expr.replace("X", "(" + x + ")")


_xs, _fy = _curve(-6, 6, "a*X**2 + b*X + c")
W("m9-polynomial", "coaster", xs=_xs, fy=_fy, marks=[{"x": "x0", "y": "p0", "label": "p({x0}) = {p0}"}], lines=["p(x) = {a}x² + {b}x + {c}", "At x = {x0} the track is at height {p0}"])
_xs, _fy = _curve(-2, 5, "X**3 + b*X**2 + c*X + d")
W("m9-cubic", "coaster", xs=_xs, fy=_fy, marks=[{"x": "k", "y": "pk", "label": "p({k}) = {pk}"}], lines=["Where the track touches the ground, p(x) = 0: a zero"])
_xs, _fy = _curve(-10, 10, "(c - a*X)/b")
W("m9-linear-eq", "coaster", xs=_xs, fy=_fy, marks=[{"x": "xint", "y": 0, "label": "x-intercept {xint}"}, {"x": 0, "y": "yint", "label": "y-intercept {yint}"}], lines=["{a}x + {b}y = {c}: a straight ramp of slope {slope}"])
_xs, _fy = _curve(-10, 10, "a*X**2 + b*X + c")
W("m10-quadratic", "coaster", xs=_xs, fy=_fy, marks=[{"x": "x1", "y": 0, "label": "x₁ = {x1}"}, {"x": "x2", "y": 0, "label": "x₂ = {x2}"}, {"x": "xv", "y": "a*xv**2 + b*xv + c", "label": "turning point"}],
  lines=["Discriminant {D}: the track meets the ground at the roots"])
W("m10-linear-pair", "plane", pts=[{"x": "x", "y": "y", "label": "meet "}], line=["a1", "b1", "-c1"], line2=["a2", "b2", "-c2"], lines=["Two straight roads cross at ({x}, {y})", "det = {det} (0 means parallel roads)"])
W("m11-sine-graph", "ferris", A="A", D="D", fy="list:60:A*sin(B*(" + _X.format(lo=0, hi="4*pi") + ") + C) + D", ang="list:60:B*(" + _X.format(lo=0, hi="4*pi") + ") + C",
  lines=["Height = {A} sin({B}x + {C}) + {D}", "One turn every {period}; highest {ymax}, lowest {ymin}"])
W("m11-circle", "plane", pts=[{"x": "h", "y": "k", "label": "centre "}], circle=["h", "k", "r"], lines=["A running track of radius {r}", "Area {area}, one lap {circ}"])
W("m11-parabola", "dish", a="a", xs="list:60:a*(" + _X.format(lo=-3, hi=3) + ")**2", fy="list:60:2*a*(" + _X.format(lo=-3, hi=3) + ")",
  rays="list:7:2*a*(kk - 4)*0.75", hx="list:7:a*((kk - 4)*0.75)**2", lines=["A dish y² = {4*a}x sends every ray to the focus", "Focus ({focus}, 0), latus rectum {LR}"])
W("m11-ellipse", "conicorbit", c="c", xs="list:60:a*cos(" + _X.format(lo=0, hi="2*pi") + ")", fy="list:60:b*sin(" + _X.format(lo=0, hi="2*pi") + ")",
  lines=["A planet's orbit: the Sun sits at a focus, {c} from the centre", "Eccentricity {e}, area {area}"])
W("m11-hyperbola", "conicorbit", comet=True, c="c", slope="slope", xs="list:60:a*cosh(" + _X.format(lo=-2, hi=2) + ")", fy="list:60:b*sinh(" + _X.format(lo=-2, hi=2) + ")",
  lines=["A comet swings past the Sun once and leaves", "Eccentricity {e}; it heads out along slope ±{slope}"])
W("m11-limit", "angle", A="x0*180/pi", lines=["At {x0} rad: sin x / x = {val}", "The arc and the chord become equal as x → 0"])
_xs, _fy = _curve(-3, 3, "sin(a*X**2)")
W("m12-chain", "coaster", xs=_xs, fy=_fy, fp=_curve(-3, 3, "2*a*X*cos(a*X**2)")[1], marks=[{"x": "x0", "y": "f0", "label": "slope here {d0}"}], lines=["f(x) = sin({a}x²): the chain rule gives f′ = 2{a}x cos({a}x²)"])
_xs, _fy = _curve(-2, 8, "Heaviside(p - X)*((3*p - 6)/p*X + 1) + Heaviside(X - p)*(3*X - 5)")
W("m12-continuity", "coaster", xs=_xs, fy=_fy, marks=[{"x": "p", "y": "3*p - 5", "label": "the join at x = {p}"}], lines=["With k = {k} the two pieces of track meet with no gap"])
_xs, _fy = _curve(-5, 6, "a*X**3 + b*X**2 + c*X + d")
W("m12-cubic-extrema", "coaster", xs=_xs, fy=_fy, fp=_curve(-5, 6, "3*a*X**2 + 2*b*X + c")[1],
  marks=[{"x": "x1", "y": "fmin", "label": "valley"}, {"x": "x2", "y": "a*x2**3 + b*x2**2 + c*x2 + d", "label": "hilltop"}], lines=["Hilltop and valley where the slope f′(x) = 0"])
_xs, _fy = _curve(-5, 5, "X**2")
W("m12-tangent", "coaster", xs=_xs, fy=_fy, tl=_curve(-5, 5, "2*a*X - a**2")[1], marks=[{"x": "a", "y": "a**2", "label": "touch point"}], lines=["Tangent y = {m}x + ({c})", "Normal slope {mn}"])
_xs, _fy = _curve("a", "b", "X**n")
W("m12-integral-power", "area", xs=_xs, fy=_fy, lines=["∫ xⁿ dx from {a} to {b} = {I}"])
_xs, _fy = _curve(0, "b", "2*sqrt(a*X)")
W("m12-area-parabola", "area", xs=_xs, fy=_fy, gy=_curve(0, "b", "-2*sqrt(a*X)")[1], lines=["Area inside y² = {4*a}x up to x = {b}: {A}"])
_xs, _fy = _curve("-a", "a", "b*sqrt(Max(0, 1 - X**2/a**2))")
W("m12-area-ellipse", "area", xs=_xs, fy=_fy, gy=_curve("-a", "a", "-b*sqrt(Max(0, 1 - X**2/a**2))")[1], lines=["Area of the ellipse πab = {A}"])
W("m12-growth", "colony", vals="list:60:y0*exp(k*(" + _X.format(lo=0, hi=20) + "))", lines=["Starts at {y0}, rate k = {k}", "After {x0}: {y}; doubles every {double}"])
W("m12-linear-de", "tank", yinf="yinf", vals="list:60:Q/P + (y0 - Q/P)*exp(-P*(" + _X.format(lo=0, hi=20) + "))", lines=["dy/dx + {P}y = {Q}", "At x = {x0}: y = {y}; settles at {yinf}"])
