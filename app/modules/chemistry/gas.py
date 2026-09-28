"""Ideal gas law PV = nRT."""
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
