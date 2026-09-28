"""Solution concentration: molarity from mass, dilution (C1V1 = C2V2) and a solubility limit."""
from app.core.registry import tool
from app.modules.chemistry.formula import molar_mass_of


@tool(
    domain="chemistry",
    name="molarity_dilution",
    description=(
        "Molarity of a solution made by dissolving a solute, optionally diluted to a final volume. "
        "Give formula (e.g. 'NaCl') or molar_mass (g/mol), solute_mass (g) and volume (m^3); final_volume (m^3) "
        "dilutes it (C1V1 = C2V2). solubility (mol/L) caps the dissolved amount and reports any excess solid. "
        "Example: formula='CuSO4', solute_mass=15.96, volume=0.5e-3 -> 0.2 mol/L."
    ),
)
def molarity_dilution(
    solute_mass: float,
    volume: float,
    formula: str | None = None,
    molar_mass: float | None = None,
    final_volume: float | None = None,
    solubility: float | None = None,
) -> dict:
    if molar_mass is None:
        if not formula:
            raise ValueError("Give a formula or a molar_mass (g/mol)")
        molar_mass = molar_mass_of(formula)
    if molar_mass <= 0:
        raise ValueError("molar_mass must be positive (g/mol)")
    if solute_mass < 0:
        raise ValueError("solute_mass cannot be negative")
    if volume <= 0:
        raise ValueError("volume must be positive (m^3)")
    if final_volume is not None and final_volume < volume:
        raise ValueError("final_volume must be at least the starting volume (dilution only adds solvent)")
    if solubility is not None and solubility <= 0:
        raise ValueError("solubility must be positive (mol/L)")

    moles_added = solute_mass / molar_mass
    litres = volume * 1000
    dissolved = moles_added if solubility is None else min(moles_added, solubility * litres)
    c1 = dissolved / litres  # mol/L
    v2 = final_volume if final_volume is not None else volume
    c2 = dissolved / (v2 * 1000)
    # A dilution can dissolve more solid if a saturated solution with excess solid is diluted.
    if solubility is not None and final_volume is not None:
        dissolved_after = min(moles_added, solubility * v2 * 1000)
        c2 = dissolved_after / (v2 * 1000)
    else:
        dissolved_after = dissolved
    return {
        "result": {
            "molar_mass": molar_mass,
            "moles": moles_added,
            "moles_dissolved": dissolved_after,
            "undissolved_mass": (moles_added - dissolved_after) * molar_mass,
            "saturated": solubility is not None and moles_added >= solubility * v2 * 1000,
            "concentration": c2,
            "concentration_before_dilution": c1,
            "concentration_si": c2 * 1000,
            "dilution_factor": v2 / volume,
            "mass_concentration": dissolved_after * molar_mass / (v2 * 1000),
        },
        "units": "concentration in mol/L (concentration_si in mol/m^3), masses in g, molar_mass in g/mol, volumes in m^3",
        "assumptions": [
            "Volume of the solution equals the volume given (solute volume neglected)",
            "Dilution conserves moles of solute: C1 V1 = C2 V2",
            "Solubility treated as a sharp limit at this temperature",
        ],
    }
