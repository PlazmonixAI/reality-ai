"""Colligative properties: boiling-point elevation, freezing-point depression, vapour-pressure lowering
and osmotic pressure — they depend on how many particles are dissolved, not what they are."""
import math

from app.core.registry import tool
from app.modules.chemistry.formula import molar_mass_of

R = 8.314462618
# Solvent data: Kb, Kf (K·kg/mol), normal boiling and freezing points (°C), molar mass (g/mol), density (kg/L)
SOLVENTS = {
    "water": (0.512, 1.86, 100.0, 0.0, 18.015, 0.997),
    "benzene": (2.53, 5.12, 80.1, 5.5, 78.11, 0.877),
    "cyclohexane": (2.79, 20.0, 80.7, 6.6, 84.16, 0.779),
    "acetic_acid": (3.07, 3.90, 117.9, 16.6, 60.05, 1.049),
}


@tool(
    domain="chemistry",
    name="colligative_properties",
    description=(
        "Colligative properties of a dilute solution: dissolve solute_mass (g) of a solute (formula or molar_mass) "
        "in solvent_mass (kg) of a solvent (water, benzene, cyclohexane, acetic_acid). van_t_hoff is the number of "
        "particles per formula unit (NaCl ≈ 2, CaCl2 ≈ 3, sugar = 1). Returns molality, ΔTb = i Kb m, ΔTf = i Kf m, new "
        "boiling/freezing points, vapour-pressure ratio (Raoult) and osmotic pressure. Example: formula='NaCl', "
        "solute_mass=58.44, solvent_mass=1, van_t_hoff=2."
    ),
)
def colligative_properties(
    solute_mass: float,
    solvent_mass: float = 1.0,
    formula: str | None = None,
    molar_mass: float | None = None,
    van_t_hoff: float = 1.0,
    solvent: str = "water",
    temperature: float = 298.15,
) -> dict:
    if solvent not in SOLVENTS:
        raise ValueError(f"solvent must be one of {', '.join(SOLVENTS)}")
    if molar_mass is None:
        if not formula:
            raise ValueError("give a formula or a molar_mass (g/mol)")
        molar_mass = molar_mass_of(formula)
    if molar_mass <= 0 or solute_mass < 0 or solvent_mass <= 0 or van_t_hoff < 1 or temperature <= 0:
        raise ValueError("molar_mass, solvent_mass and temperature must be positive, solute_mass >= 0, van_t_hoff >= 1")
    kb, kf, tb, tf, m_solv, dens = SOLVENTS[solvent]
    n = solute_mass / molar_mass
    molality = n / solvent_mass
    particles = van_t_hoff * molality
    x_solvent = (solvent_mass * 1000 / m_solv) / (solvent_mass * 1000 / m_solv + van_t_hoff * n)
    volume_l = solvent_mass / dens  # dilute: solution volume ≈ solvent volume
    osm = van_t_hoff * (n / volume_l) * 1000 * R * temperature  # Pa (mol/L → mol/m³)
    return {
        "result": {
            "molar_mass": molar_mass,
            "moles": n,
            "molality": molality,
            "particle_molality": particles,
            "boiling_point_elevation": kb * particles,
            "freezing_point_depression": kf * particles,
            "boiling_point": tb + kb * particles,
            "freezing_point": tf - kf * particles,
            "vapour_pressure_ratio": x_solvent,
            "osmotic_pressure": osm,
            "osmotic_pressure_atm": osm / 101325,
        },
        "solvent": {"name": solvent, "kb": kb, "kf": kf, "boiling_point": tb, "freezing_point": tf},
        "units": "molality in mol/kg, temperatures in °C (differences in K), osmotic pressure in Pa (and atm)",
        "assumptions": ["Ideal dilute solution; non-volatile solute", "van 't Hoff factor taken as given (real salts are a bit lower)",
                        "Osmotic pressure uses the solvent volume as the solution volume"],
    }
