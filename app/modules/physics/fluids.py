"""Fluids: Archimedes' buoyancy and steady incompressible flow through a pipe (continuity + Bernoulli)."""
import math

import numpy as np

from app.core.registry import tool

G0 = 9.80665


@tool(
    domain="physics",
    name="buoyancy",
    description=(
        "Archimedes' principle for a solid block of given density (kg/m³) and volume (m³) in a fluid of "
        "fluid_density: floats or sinks, fraction submerged, buoyant force, apparent weight and the extra load a "
        "floating block can carry before sinking. Example: object_density=917, volume=1, fluid_density=1025 (ice in sea water)."
    ),
)
def buoyancy(object_density: float, volume: float, fluid_density: float = 998.0, gravity: float = G0,
             added_mass: float = 0.0) -> dict:
    if object_density <= 0 or volume <= 0 or fluid_density <= 0 or gravity <= 0:
        raise ValueError("densities, volume and gravity must be positive")
    if added_mass < 0:
        raise ValueError("added_mass must be >= 0 (kg placed on the block)")
    mass = object_density * volume + added_mass
    weight = mass * gravity
    full_buoyancy = fluid_density * volume * gravity
    floats = weight <= full_buoyancy
    frac = weight / full_buoyancy if floats else 1.0
    buoy = full_buoyancy * frac
    return {
        "result": {
            "floats": floats,
            "fraction_submerged": frac,
            "buoyant_force": buoy,
            "weight": weight,
            "apparent_weight": weight - buoy,
            "net_upward_force_fully_submerged": full_buoyancy - weight,
            "average_density": mass / volume,
            "extra_load_capacity": max(0.0, (fluid_density * volume - mass)),
            "sinking_acceleration": (weight - full_buoyancy) / mass if not floats else 0.0,
        },
        "units": "forces in N, masses in kg, densities in kg/m³, acceleration in m/s²",
        "assumptions": ["Buoyant force = weight of displaced fluid (Archimedes)", "Static fluid; the sinking "
                        "acceleration ignores drag and added-mass effects"],
    }


@tool(
    domain="physics",
    name="pipe_flow",
    description=(
        "Steady incompressible, inviscid flow through a pipe whose diameter and height change along its length: "
        "continuity A v = Q gives the speed and Bernoulli p + ½ρv² + ρgh = const gives the pressure. diameters (m) "
        "and heights (m) are lists at the section points along the pipe; flow_rate in m³/s; inlet_pressure in Pa. "
        "Example: diameters=[0.1,0.05,0.1], heights=[0,0,0], flow_rate=0.01 (a Venturi meter)."
    ),
)
def pipe_flow(diameters: list[float], flow_rate: float, heights: list[float] | None = None, inlet_pressure: float = 200_000.0,
              density: float = 998.0, gravity: float = G0, n_points: int = 200) -> dict:
    d = np.asarray(diameters, float)
    if d.ndim != 1 or len(d) < 2:
        raise ValueError("give at least two diameters")
    h = np.zeros_like(d) if heights is None else np.asarray(heights, float)
    if h.shape != d.shape:
        raise ValueError("heights must match diameters")
    if np.any(d <= 0) or flow_rate < 0 or density <= 0:
        raise ValueError("diameters and density must be positive, flow_rate >= 0")
    if not 2 <= n_points <= 5000:
        raise ValueError("n_points must be between 2 and 5000")
    # Smoothly interpolate the pipe shape between section points for plotting
    s = np.linspace(0, len(d) - 1, n_points)
    dd = np.interp(s, np.arange(len(d)), d)
    hh = np.interp(s, np.arange(len(d)), h)
    area = math.pi * dd**2 / 4
    v = flow_rate / area
    head = inlet_pressure + 0.5 * density * v[0] ** 2 + density * gravity * hh[0]
    p = head - 0.5 * density * v**2 - density * gravity * hh
    a_sec = math.pi * d**2 / 4
    v_sec = flow_rate / a_sec
    p_sec = head - 0.5 * density * v_sec**2 - density * gravity * h
    return {
        "result": {
            "section_speeds": v_sec.tolist(),
            "section_pressures": p_sec.tolist(),
            "max_speed": float(v.max()),
            "min_pressure": float(p.min()),
            "cavitation_risk": bool(p.min() < 2339.0),  # water vapour pressure at 20 °C
            "total_head_pressure": float(head),
            "mass_flow_rate": density * flow_rate,
        },
        "profile": {"position": s.tolist(), "diameter": dd.tolist(), "height": hh.tolist(), "speed": v.tolist(), "pressure": p.tolist()},
        "units": "SI: m, m/s, Pa, m³/s, kg/s",
        "assumptions": ["Steady, incompressible, inviscid (no friction losses) flow along a streamline",
                        "Uniform speed across each cross-section", "Cavitation flagged below 2.339 kPa (water at 20 °C)"],
    }
