"""Ideal gas law PV = nRT and the Maxwell-Boltzmann speed distribution."""
import math

import numpy as np

from app.core.registry import tool

R = 8.314462618  # J/(mol K), exact since the 2019 SI redefinition


@tool(
    domain="chemistry",
    name="ideal_gas_law",
    description=(
        "Ideal gas law PV = nRT in SI units. Give any three of pressure (Pa), volume (m^3), moles (mol), "
        "temperature (K); the missing one is solved. Example: pressure=101325, moles=1, temperature=273.15 -> volume."
    ),
)
def ideal_gas_law(
    pressure: float | None = None,
    volume: float | None = None,
    moles: float | None = None,
    temperature: float | None = None,
) -> dict:
    known = {"pressure": pressure, "volume": volume, "moles": moles, "temperature": temperature}
    missing = [k for k, v in known.items() if v is None]
    if len(missing) != 1:
        raise ValueError(f"Give exactly three of pressure, volume, moles, temperature (missing: {missing})")
    for k, v in known.items():
        if v is not None and not v > 0:
            raise ValueError(f"{k} must be positive (temperature in kelvin)")

    unknown = missing[0]
    if unknown == "pressure":
        pressure = moles * R * temperature / volume
    elif unknown == "volume":
        volume = moles * R * temperature / pressure
    elif unknown == "moles":
        moles = pressure * volume / (R * temperature)
    else:
        temperature = pressure * volume / (moles * R)
    values = {"pressure": pressure, "volume": volume, "moles": moles, "temperature": temperature}
    units = {"pressure": "Pa", "volume": "m^3", "moles": "mol", "temperature": "K"}
    return {
        "result": values[unknown],
        "solved_for": unknown,
        "state": values,
        "conversions": {
            "pressure_atm": pressure / 101325,
            "pressure_bar": pressure / 1e5,
            "volume_litres": volume * 1000,
            "temperature_celsius": temperature - 273.15,
        },
        "units": f"{units[unknown]} (SI: Pa, m^3, mol, K)",
        "assumptions": ["Ideal gas: no intermolecular forces, point particles", f"R = {R} J/(mol K)"],
    }


@tool(
    domain="chemistry",
    name="maxwell_boltzmann",
    description=(
        "Maxwell-Boltzmann molecular speed distribution for an ideal gas: most probable, mean and rms speeds "
        "and a plot-ready probability density curve. molar_mass in g/mol, temperature in K. "
        "Example: molar_mass=28.014 (N2), temperature=300."
    ),
)
def maxwell_boltzmann(molar_mass: float, temperature: float, n_points: int = 200, max_speed: float | None = None) -> dict:
    if molar_mass <= 0 or temperature <= 0:
        raise ValueError("molar_mass (g/mol) and temperature (K) must be positive")
    if not 2 <= n_points <= 10_000:
        raise ValueError("n_points must be between 2 and 10000")
    m = molar_mass / 1000  # kg/mol
    a = R * temperature / m  # kT/m per molecule, via molar quantities
    v_p, v_mean, v_rms = math.sqrt(2 * a), math.sqrt(8 * a / math.pi), math.sqrt(3 * a)
    top = max_speed if max_speed else 4 * v_p
    if top <= 0:
        raise ValueError("max_speed must be positive")
    v = np.linspace(0, top, n_points)
    pdf = 4 * math.pi * (1 / (2 * math.pi * a)) ** 1.5 * v**2 * np.exp(-v**2 / (2 * a))
    return {
        "result": {"most_probable_speed": v_p, "mean_speed": v_mean, "rms_speed": v_rms},
        "curve": {"speed": v.tolist(), "probability_density": pdf.tolist()},
        "units": "speeds in m/s, probability density in s/m",
        "assumptions": ["Ideal gas in thermal equilibrium", "Classical (non-quantum) statistics"],
    }
