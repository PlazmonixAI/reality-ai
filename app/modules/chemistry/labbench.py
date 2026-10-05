"""Virtual chemistry lab: a bench of glassware where chemicals are added, mixed, poured and heated.

Each vessel holds amounts of species (mol) at one temperature. A step of `dt` seconds:
  1. applies the user's actions (add a chemical, pour part of one vessel into another, heat with a burner);
  2. runs every reaction whose reactants (and any catalyst or solvent it needs) are present and whose temperature
     threshold is met, by the extent its rate allows; equations are balanced by the shared balancer and the heat
     released comes from standard enthalpies of formation (ΔH_r = Σν ΔH_f(products) − Σν ΔH_f(reactants));
  3. balances energy: reaction heat + burner heat − heat lost to the room, over the heat capacity of the contents and
     the glass; water caps the temperature at its boiling point and boils away with ΔH_vap;
  4. lets gases escape (reported with their volume and their test), and works out what can be seen: pH from the
     strong and weak acids and bases present, indicator colours from the pH, solution colour and precipitates.
Nothing is scripted by time: what happens follows from what is in the vessel and how hot it is.
"""
from __future__ import annotations

import math
from typing import Any

from app.core.registry import tool
from app.modules.chemistry.formula import element_counts, molar_mass_of, parse_equation
from app.modules.chemistry.stoichiometry import _balance

R_GAS = 8.314462618
ROOM_T = 25.0
DH_VAP_WATER = 40_650.0      # J/mol at 100 °C
C_WATER = 4.18               # J/(g K)
C_SOLID = 0.8                # J/(g K), typical for salts and oxides
C_GLASS = 0.84

# Standard enthalpies of formation at 298 K, kJ/mol (CRC Handbook / NBS tables; aqueous salts as their ions)
HF: dict[str, float] = {
    "H2O(l)": -285.83, "H2O(g)": -241.82, "H2(g)": 0.0, "O2(g)": 0.0, "CO2(g)": -393.51, "NH3(g)": -45.94,
    "SO2(g)": -296.83, "SO3(g)": -395.72, "NO2(g)": 33.18,
    "Na(s)": 0.0, "K(s)": 0.0, "Ca(s)": 0.0, "Mg(s)": 0.0, "Zn(s)": 0.0, "Fe(s)": 0.0, "Cu(s)": 0.0, "Al(s)": 0.0,
    "S(s)": 0.0, "Ag(s)": 0.0,
    "NaOH(aq)": -470.11, "NaOH(s)": -425.8, "KOH(aq)": -482.37, "Ca(OH)2(aq)": -1002.82, "Ca(OH)2(s)": -985.2,
    "HCl(aq)": -167.16, "H2SO4(aq)": -909.27, "HNO3(aq)": -207.36, "CH3COOH(aq)": -485.76, "NH3(aq)": -80.29,
    "NaCl(aq)": -407.28, "NaCl(s)": -411.15, "KCl(aq)": -419.53, "MgCl2(aq)": -801.17, "ZnCl2(aq)": -488.21,
    "FeCl2(aq)": -423.4, "CaCl2(aq)": -877.15, "AlCl3(aq)": -1032.5, "CuCl2(aq)": -269.55,
    "MgSO4(aq)": -1376.12, "ZnSO4(aq)": -1063.16, "Na2SO4(aq)": -1389.51, "K2SO4(aq)": -1414.03, "MnSO4(aq)": -1130.02,
    "NaNO3(aq)": -447.48, "KNO3(aq)": -459.74, "KNO3(s)": -494.63, "CH3COONa(aq)": -726.13,
    "NH4Cl(aq)": -299.67, "NH4Cl(s)": -314.43,
    "CaCO3(s)": -1206.92, "NaHCO3(s)": -950.81, "Na2CO3(aq)": -1157.38, "CaO(s)": -634.92, "MgO(s)": -601.6,
    "AgNO3(aq)": -101.78, "AgCl(s)": -127.01, "AgI(s)": -61.84, "KI(aq)": -307.57,
    "BaCl2(aq)": -871.96, "BaSO4(s)": -1473.2,
    "Pb(NO3)2(aq)": -416.42, "Pb(NO3)2(s)": -451.9, "PbI2(s)": -175.48, "PbO(s)": -219.0,
    "CuSO4(aq)": -844.5, "CuSO4(s)": -771.36, "CuSO4.5H2O(s)": -2279.65, "Cu(OH)2(s)": -449.8, "Cu(NO3)2(aq)": -349.95,
    "CuO(s)": -157.3, "Cu2(OH)2CO3(s)": -1051.4,
    "FeSO4(aq)": -998.37, "FeSO4(s)": -928.4, "FeSO4.7H2O(s)": -3014.6, "Fe(OH)2(s)": -569.0, "FeCl3(aq)": -549.98,
    "Fe(OH)3(s)": -823.0, "Fe2O3(s)": -824.2, "Fe2(SO4)3(aq)": -2824.8, "FeS(s)": -100.0,
    "H2O2(aq)": -191.17, "KMnO4(aq)": -793.8, "KMnO4(s)": -837.2, "K2MnO4(s)": -1184.0, "MnO2(s)": -520.03,
    "Na2S2O3(aq)": -1132.5,
    # concentrated acids, carbon, sugars, iodine
    "H2SO4(l)": -813.99, "HNO3(l)": -174.10, "NO(g)": 91.29, "C(s)": 0.0, "C12H22O11(s)": -2226.1, "C12H22O11(aq)": None,
    "C2H5OH(l)": -277.69, "C2H5OH(aq)": -288.3, "CH3COOH(l)": -484.3, "CH3COOC2H5(l)": -479.3, "CHI3(s)": None, "HCOONa(aq)": None,
    "KNaC4H4O6(aq)": None,
    "C6H12O6(aq)": -1263.07, "I2(aq)": 22.6, "Na2S4O6(aq)": -1704.4, "NaI(aq)": -295.31,
    # qualitative analysis
    "KSCN(aq)": -175.94, "Fe(SCN)3(aq)": None, "(NH4)2SO4(aq)": -1174.29, "Cu(NH3)4(OH)2(aq)": -808.48, "Ag(NH3)2Cl(aq)": -278.45,
    "Zn(OH)2(s)": -641.91, "Mg(OH)2(s)": -924.54, "Al(OH)3(s)": -1276.0, "PbCl2(s)": -359.41, "CaC2O4(s)": -1360.6,
    "(NH4)2C2O4(aq)": -1090.12, "K2Cr2O7(aq)": -1995.06, "Cr2(SO4)3(aq)": None, "Ca(HCO3)2(aq)": -1926.81,
    "Cu2O(s)": -168.6, "C6H11O7Na(aq)": None, "C6H11O7NH4(aq)": None, "Ag(NH3)2OH(aq)": -341.28, "NH4NO3(aq)": -339.87,
    "Fe(NO)SO4(aq)": None, "LiCl(aq)": -445.6, "LiCl(s)": -408.27, "SrCl2(aq)": -880.1, "SrCl2(s)": -828.85,
    # salts left behind when a solution is evaporated to dryness
    "NaNO3(s)": -467.85, "Na2SO4(s)": -1387.08, "KCl(s)": -436.75, "MgSO4(s)": -1284.9, "ZnSO4(s)": -982.8, "CaCl2(s)": -795.42,
    "CH3COONa(s)": -708.8, "MgCl2(s)": -641.32, "Na2CO3(s)": -1130.68, "KOH(s)": -424.6, "ZnCl2(s)": -415.05, "CuCl2(s)": -220.1,
    "Cu(NO3)2(s)": -302.9, "AlCl3(s)": -704.2, "KI(s)": -327.9, "BaCl2(s)": -855.0, "AgNO3(s)": -124.4, "K2SO4(s)": -1437.8,
}

# What each species looks like (display data): colour, and how strongly a dissolved species tints water
LOOK: dict[str, tuple[str, float]] = {
    "CHI3(s)": ("#f2d23c", 0), "KNaC4H4O6(aq)": ("#ffffff", 0.0),
    "CuSO4(aq)": ("#2f7fd8", 6.0), "Cu(NO3)2(aq)": ("#2f86d8", 6.0), "CuCl2(aq)": ("#2bb3a3", 6.0), "FeSO4(aq)": ("#b9d98a", 2.0),
    "FeCl2(aq)": ("#b9d98a", 2.0), "FeCl3(aq)": ("#d8a032", 8.0), "Fe2(SO4)3(aq)": ("#d9b347", 6.0), "KMnO4(aq)": ("#8a1c8c", 400.0),
    "Ca(OH)2(aq)": ("#ffffff", 0.0),
    "CuSO4.5H2O(s)": ("#2f7fd8", 0), "CuSO4(s)": ("#e8eaea", 0), "Cu(OH)2(s)": ("#7fb3e8", 0), "Fe(OH)2(s)": ("#5f7a4a", 0),
    "Fe(OH)3(s)": ("#9a4b1c", 0), "AgCl(s)": ("#f4f4f2", 0), "AgI(s)": ("#f0e6a0", 0), "PbI2(s)": ("#f5c400", 0),
    "BaSO4(s)": ("#f7f7f7", 0), "CaCO3(s)": ("#f2f2ee", 0), "MnO2(s)": ("#2a2a2a", 0), "CuO(s)": ("#1e1e1e", 0),
    "Cu(s)": ("#b5653a", 0), "Ag(s)": ("#b8bcc2", 0), "S(s)": ("#f1e06a", 0), "PbO(s)": ("#e8c34a", 0), "Fe2O3(s)": ("#8e3b1e", 0),
    "MgO(s)": ("#ffffff", 0), "CaO(s)": ("#f4f4f0", 0), "Cu2(OH)2CO3(s)": ("#3fa37a", 0), "FeS(s)": ("#2b2b2b", 0),
    "K2MnO4(s)": ("#1f5a2f", 0), "KMnO4(s)": ("#4b0b55", 0), "FeSO4.7H2O(s)": ("#b6dba8", 0), "FeSO4(s)": ("#f2f2ea", 0),
    "Na(s)": ("#c9ccd0", 0), "K(s)": ("#c9ccd0", 0), "Ca(s)": ("#d7d7d2", 0), "Mg(s)": ("#d9dbe0", 0), "Zn(s)": ("#a8adb3", 0),
    "Fe(s)": ("#55585e", 0), "Al(s)": ("#d6d9de", 0), "NaHCO3(s)": ("#ffffff", 0), "NaCl(s)": ("#ffffff", 0),
    "NaOH(s)": ("#ffffff", 0), "KNO3(s)": ("#ffffff", 0), "NH4Cl(s)": ("#ffffff", 0), "Ca(OH)2(s)": ("#ffffff", 0),
    "Pb(NO3)2(s)": ("#ffffff", 0),
    "Fe(SCN)3(aq)": ("#9b0d0d", 300.0), "Cu(NH3)4(OH)2(aq)": ("#1a3fb5", 40.0), "K2Cr2O7(aq)": ("#f08a1c", 30.0), "Cr2(SO4)3(aq)": ("#3f8f4a", 20.0),
    "I2(aq)": ("#9a5a14", 200.0), "Fe(NO)SO4(aq)": ("#5a3010", 120.0), "Ag(NH3)2OH(aq)": ("#ffffff", 0.0),
    "Zn(OH)2(s)": ("#f4f4f2", 0), "Mg(OH)2(s)": ("#f7f7f5", 0), "Al(OH)3(s)": ("#eef2f2", 0), "PbCl2(s)": ("#f7f7f5", 0), "CaC2O4(s)": ("#f7f7f5", 0),
    "Cu2O(s)": ("#b3321e", 0), "C(s)": ("#151515", 0), "C12H22O11(s)": ("#ffffff", 0), "LiCl(s)": ("#ffffff", 0), "SrCl2(s)": ("#ffffff", 0),
}
FLAME = {"Li": ("crimson red", "#d42a2a"), "Na": ("golden yellow", "#f5c518"), "K": ("lilac", "#b58cd8"), "Ca": ("brick red", "#e0602a"),
         "Sr": ("crimson", "#d01c3c"), "Ba": ("apple green", "#8bcf5a"), "Cu": ("blue-green", "#2bb3a3")}

GAS_TEST = {
    "H2(g)": "Hydrogen: a lighted splint held at the mouth goes out with a squeaky pop",
    "CO2(g)": "Carbon dioxide: turns limewater milky",
    "O2(g)": "Oxygen: relights a glowing splint",
    "NH3(g)": "Ammonia: pungent smell, turns moist red litmus blue",
    "SO2(g)": "Sulphur dioxide: choking smell, turns acidified potassium dichromate paper green",
    "NO2(g)": "Nitrogen dioxide: brown fumes",
    "SO3(g)": "Sulphur trioxide: white fumes",
    "H2O(g)": "Steam: condenses as droplets on the cool upper part of the tube",
    "NO(g)": "Nitrogen monoxide: colourless, turns brown at the mouth of the tube as it meets air",
}

# ---------------------------------------------------------------- the shelf
# kind: solid (amount in g), liquid (pure, amount in mL, density g/mL), solution (amount in mL, conc mol/L in water),
# indicator (a few drops). gives: species added per unit.
CHEMICALS: dict[str, dict[str, Any]] = {}


def _chem(cid, name, kind, group, species=None, conc=None, density=None, note="", extra=None):
    CHEMICALS[cid] = {"id": cid, "name": name, "kind": kind, "group": group, "species": species, "conc": conc, "density": density,
                      "note": note, "extra": extra or {}}  # extra: other dissolved species, mol/L (a reagent made of two chemicals)


for cid, name, sp_, note in [
    ("sodium", "Sodium metal", "Na(s)", "Kept under kerosene. Use a pea-sized piece (about 0.1 g)."),
    ("potassium", "Potassium metal", "K(s)", "More reactive than sodium. Use the smallest piece."),
    ("calcium", "Calcium granules", "Ca(s)", ""),
    ("magnesium", "Magnesium ribbon", "Mg(s)", "Burns with a dazzling white light: do not look straight at it."),
    ("zinc", "Zinc granules", "Zn(s)", ""), ("iron", "Iron filings", "Fe(s)", ""), ("copper", "Copper turnings", "Cu(s)", ""),
    ("aluminium", "Aluminium foil", "Al(s)", ""), ("sulphur", "Sulphur powder", "S(s)", ""),
    ("marble", "Marble chips (CaCO₃)", "CaCO3(s)", ""), ("baking_soda", "Sodium hydrogen carbonate", "NaHCO3(s)", ""),
    ("blue_vitriol", "Copper sulphate crystals (CuSO₄·5H₂O)", "CuSO4.5H2O(s)", ""),
    ("green_vitriol", "Ferrous sulphate crystals (FeSO₄·7H₂O)", "FeSO4.7H2O(s)", ""),
    ("malachite", "Basic copper carbonate", "Cu2(OH)2CO3(s)", ""), ("permanganate_s", "Potassium permanganate crystals", "KMnO4(s)", ""),
    ("lead_nitrate_s", "Lead nitrate crystals", "Pb(NO3)2(s)", "Toxic. Heat only in a fume cupboard."),
    ("mno2", "Manganese dioxide", "MnO2(s)", "A catalyst: it is not used up."),
    ("quicklime", "Quicklime (CaO)", "CaO(s)", ""), ("slaked_lime", "Slaked lime (Ca(OH)₂)", "Ca(OH)2(s)", ""),
    ("ammonium_chloride", "Ammonium chloride", "NH4Cl(s)", ""), ("salt", "Sodium chloride", "NaCl(s)", ""),
    ("caustic_soda", "Sodium hydroxide pellets", "NaOH(s)", "Corrosive."), ("potassium_nitrate", "Potassium nitrate", "KNO3(s)", ""),
]:
    _chem(cid, name, "solid", "Metals and non-metals" if sp_ in ("Na(s)", "K(s)", "Ca(s)", "Mg(s)", "Zn(s)", "Fe(s)", "Cu(s)", "Al(s)", "S(s)") else "Solids", sp_, note=note)

_chem("water", "Distilled water", "liquid", "Water and liquids", "H2O(l)", density=1.0)
_chem("conc_h2so4", "Concentrated sulphuric acid", "pure", "Acids", "H2SO4(l)", density=1.84, note="Always add acid to water, slowly. It gets very hot.")
_chem("conc_hno3", "Concentrated nitric acid", "pure", "Acids", "HNO3(l)", density=1.51, note="Fume cupboard: it gives brown fumes with metals.")
_chem("sugar", "Sugar (sucrose)", "solid", "Solids", "C12H22O11(s)")
_chem("ethanol", "Ethanol", "pure", "Organic", "C2H5OH(l)", density=0.789, note="Flammable: keep away from the burner flame.")
_chem("glacial_acetic", "Glacial acetic acid", "pure", "Organic", "CH3COOH(l)", density=1.049, note="With ethanol and a few drops of concentrated sulphuric acid, warm it to make an ester.")
_chem("fehling_a", "Fehling's solution A (copper sulphate)", "solution", "Test reagents", "CuSO4(aq)", conc=0.28, note="Mix equal volumes of A and B just before use.")
_chem("fehling_b", "Fehling's solution B (alkaline sodium potassium tartrate)", "solution", "Test reagents", "KNaC4H4O6(aq)", conc=1.24,
      extra={"NaOH(aq)": 2.5}, note="The tartrate keeps the copper in solution: a deep blue liquid, not a precipitate.")
_chem("licl", "Lithium chloride", "solid", "Solids", "LiCl(s)", note="For flame tests.")
_chem("srcl2", "Strontium chloride", "solid", "Solids", "SrCl2(s)", note="For flame tests.")
_chem("h2o2", "Hydrogen peroxide (6 %)", "solution", "Water and liquids", "H2O2(aq)", conc=1.76)
for cid, name, sp_, c, group, note in [
    ("hcl", "Dilute hydrochloric acid", "HCl(aq)", 2.0, "Acids", ""), ("h2so4", "Dilute sulphuric acid", "H2SO4(aq)", 1.0, "Acids", ""),
    ("hno3", "Dilute nitric acid", "HNO3(aq)", 1.0, "Acids", ""), ("acetic", "Acetic acid (ethanoic acid)", "CH3COOH(aq)", 1.0, "Acids", ""),
    ("naoh", "Sodium hydroxide solution", "NaOH(aq)", 1.0, "Bases", ""), ("koh", "Potassium hydroxide solution", "KOH(aq)", 1.0, "Bases", ""),
    ("ammonia", "Ammonia solution", "NH3(aq)", 2.0, "Bases", ""), ("limewater", "Limewater (Ca(OH)₂)", "Ca(OH)2(aq)", 0.02, "Bases", ""),
    ("nacl_aq", "Sodium chloride solution", "NaCl(aq)", 1.0, "Salt solutions", ""), ("agno3", "Silver nitrate solution", "AgNO3(aq)", 0.1, "Salt solutions", "Stains skin."),
    ("bacl2", "Barium chloride solution", "BaCl2(aq)", 0.5, "Salt solutions", "Toxic."), ("cuso4", "Copper sulphate solution", "CuSO4(aq)", 0.5, "Salt solutions", ""),
    ("feso4", "Ferrous sulphate solution", "FeSO4(aq)", 0.5, "Salt solutions", ""), ("fecl3", "Ferric chloride solution", "FeCl3(aq)", 0.5, "Salt solutions", ""),
    ("pbno3", "Lead nitrate solution", "Pb(NO3)2(aq)", 0.5, "Salt solutions", "Toxic."), ("ki", "Potassium iodide solution", "KI(aq)", 0.5, "Salt solutions", ""),
    ("na2co3", "Sodium carbonate solution", "Na2CO3(aq)", 1.0, "Salt solutions", ""), ("na2so4", "Sodium sulphate solution", "Na2SO4(aq)", 0.5, "Salt solutions", ""),
    ("thio", "Sodium thiosulphate solution", "Na2S2O3(aq)", 0.1, "Salt solutions", ""), ("kmno4", "Potassium permanganate solution", "KMnO4(aq)", 0.02, "Salt solutions", ""),
    ("zncl2", "Zinc chloride solution", "ZnCl2(aq)", 0.5, "Salt solutions", ""),
    ("znso4", "Zinc sulphate solution", "ZnSO4(aq)", 0.5, "Salt solutions", ""), ("mgso4", "Magnesium sulphate solution", "MgSO4(aq)", 0.5, "Salt solutions", ""),
    ("alcl3", "Aluminium chloride solution", "AlCl3(aq)", 0.5, "Salt solutions", ""), ("cacl2", "Calcium chloride solution", "CaCl2(aq)", 0.5, "Salt solutions", ""),
    ("nano3", "Sodium nitrate solution", "NaNO3(aq)", 0.5, "Salt solutions", ""), ("nh4cl_aq", "Ammonium chloride solution", "NH4Cl(aq)", 1.0, "Salt solutions", ""),
    ("kscn", "Potassium thiocyanate solution", "KSCN(aq)", 0.1, "Test reagents", "Test for Fe³⁺: blood red."),
    ("amm_oxalate", "Ammonium oxalate solution", "(NH4)2C2O4(aq)", 0.25, "Test reagents", "Test for Ca²⁺: white precipitate."),
    ("dichromate", "Potassium dichromate solution", "K2Cr2O7(aq)", 0.05, "Test reagents", "Acidify it; SO₂ turns it from orange to green."),
    ("iodine", "Iodine solution", "I2(aq)", 0.05, "Test reagents", "Turns starch blue-black."),
    ("tollens", "Tollens' reagent", "Ag(NH3)2OH(aq)", 0.1, "Test reagents", "Make fresh. Warm with an aldehyde or glucose: silver mirror."),
    ("glucose", "Glucose solution", "C6H12O6(aq)", 0.5, "Test reagents", "A reducing sugar."),
]:
    _chem(cid, name, "solution", group, sp_, conc=c, note=note)
for cid, name in [("phenolphthalein", "Phenolphthalein"), ("methyl_orange", "Methyl orange"), ("litmus", "Litmus solution"), ("universal", "Universal indicator"), ("starch", "Starch solution")]:
    _chem(cid, name, "indicator", "Indicators")

EQUIPMENT: dict[str, dict[str, Any]] = {
    "beaker": {"name": "Beaker (250 mL)", "capacity": 250, "glass": 100, "flame": 300.0, "loss": 1.2, "max_t": 400},
    "conical": {"name": "Conical flask (250 mL)", "capacity": 250, "glass": 120, "flame": 300.0, "loss": 1.1, "max_t": 400},
    "test_tube": {"name": "Test tube", "capacity": 20, "glass": 15, "flame": 120.0, "loss": 0.25, "max_t": 700},
    "boiling_tube": {"name": "Boiling tube", "capacity": 50, "glass": 30, "flame": 160.0, "loss": 0.35, "max_t": 700},
    "crucible": {"name": "Crucible (porcelain)", "capacity": 30, "glass": 30, "flame": 600.0, "loss": 0.6, "max_t": 1000},
    "dish": {"name": "Evaporating dish", "capacity": 100, "glass": 80, "flame": 300.0, "loss": 1.0, "max_t": 600},
    "burette": {"name": "Burette (50 mL)", "capacity": 50, "glass": 60, "flame": 0.0, "loss": 0.5, "max_t": 60},
    "cylinder": {"name": "Measuring cylinder (100 mL)", "capacity": 100, "glass": 90, "flame": 0.0, "loss": 0.8, "max_t": 60},
    "gas_jar": {"name": "Gas jar (250 mL)", "capacity": 250, "glass": 150, "flame": 0.0, "loss": 1.0, "max_t": 60, "holds_gas": True},
    "watch_glass": {"name": "Watch glass", "capacity": 10, "glass": 20, "flame": 0.0, "loss": 0.4, "max_t": 60},
}
TOOLS = {"burner": "Bunsen burner on a tripod and gauze (or a holder for tubes)", "stand": "Burette stand", "dropper": "Dropper (one drop = 0.05 mL)",
         "pipette": "Pipette (10 or 25 mL, exact)", "thermometer": "Thermometer (reads the vessel's temperature)", "delivery_tube": "Delivery tube (sends a vessel's gas into another vessel)",
         "funnel": "Funnel and filter paper", "splint": "Splint, lighted or glowing (tests the gas)", "litmus": "Red and blue litmus paper",
         "ph_paper": "pH paper", "flame_wire": "Nichrome wire for flame tests"}
FILM_ML = {"burette": 0.6, "pipette": 0.2, "conical": 0.8, "beaker": 1.0, "test_tube": 0.2, "boiling_tube": 0.3, "cylinder": 0.6}  # wet film after washing
TESTS = ("litmus_red", "litmus_blue", "ph_paper", "lighted_splint", "glowing_splint", "flame")

# ---------------------------------------------------------------- reactions
# eq: written with states; min_t: lowest temperature (°C) at which it goes; rate: fraction of the limiting reactant
# used per second once it can go (100 = at once, as for ions in solution); needs: species that must be present but are not used up (catalyst, solvent).
REACTIONS: list[dict[str, Any]] = []


def _rx(eq, see, min_t=-50.0, rate=100.0, needs=(), air=False, name="", unless=(), max_t=None, coeffs=None):
    left, right = (x.strip() for x in eq.split("->"))
    if " + " not in left and " + " not in right and left[: left.rindex("(")] == right[: right.rindex("(")]:
        reac, prod = {left: 1}, {right: 1}  # a change of state, such as dissolving: one formula unit each side
    else:
        e = parse_equation(eq)
        coeffs = coeffs or _balance(e)  # explicit coefficients only where the balance is not unique (redox with two routes)
        n = len(e.reactants)
        key = lambda s: f"{s.text}({s.state})"  # noqa: E731
        reac = {key(s): c for (_, s), c in zip(e.reactants, coeffs[:n])}
        prod = {key(s): c for (_, s), c in zip(e.products, coeffs[n:])}
    for k in list(reac) + list(prod):
        if k not in HF:
            raise ValueError(f"no enthalpy of formation for {k}")
    known = all(HF[k] is not None for k in list(reac) + list(prod))
    dh = sum(c * HF[k] for k, c in prod.items()) - sum(c * HF[k] for k, c in reac.items()) if known else None
    side = lambda d: " + ".join((f"{c} " if c != 1 else "") + k for k, c in d.items())  # noqa: E731
    REACTIONS.append({"name": name or eq, "reactants": reac, "products": prod, "dh": dh, "see": see, "min_t": min_t, "rate": rate,
                      "needs": tuple(needs), "unless": tuple(unless), "max_t": max_t, "air": air, "equation": f"{side(reac)} → {side(prod)}"})


# metals with water and acids
_rx("Na(s) + H2O(l) -> NaOH(aq) + H2(g)", "The sodium melts into a silvery ball and darts about on the water, hissing", rate=0.6, name="Sodium and water")
_rx("K(s) + H2O(l) -> KOH(aq) + H2(g)", "The potassium bursts into a lilac flame and skates over the water", rate=1.5, name="Potassium and water")
_rx("Ca(s) + H2O(l) -> Ca(OH)2(aq) + H2(g)", "Calcium sinks and bubbles steadily; the water turns cloudy", rate=0.08, name="Calcium and water")
_rx("Mg(s) + HCl(aq) -> MgCl2(aq) + H2(g)", "Rapid fizzing; the magnesium disappears and the tube gets warm", rate=0.35, name="Magnesium and hydrochloric acid")
_rx("Zn(s) + HCl(aq) -> ZnCl2(aq) + H2(g)", "Steady bubbles of gas on the zinc", rate=0.04, name="Zinc and hydrochloric acid")
_rx("Zn(s) + H2SO4(aq) -> ZnSO4(aq) + H2(g)", "Steady bubbles of gas on the zinc", rate=0.04, name="Zinc and sulphuric acid")
_rx("Mg(s) + H2SO4(aq) -> MgSO4(aq) + H2(g)", "Rapid fizzing; the magnesium disappears", rate=0.35, name="Magnesium and sulphuric acid")
_rx("Fe(s) + HCl(aq) -> FeCl2(aq) + H2(g)", "Slow bubbles; the solution turns pale green", rate=0.015, name="Iron and hydrochloric acid")
_rx("Al(s) + HCl(aq) -> AlCl3(aq) + H2(g)", "After a short delay (the oxide layer) the foil fizzes vigorously", rate=0.05, name="Aluminium and hydrochloric acid")
# neutralisation
_rx("HCl(aq) + NaOH(aq) -> NaCl(aq) + H2O(l)", "No visible change, but the solution warms up", name="Neutralisation: HCl and NaOH")
_rx("H2SO4(aq) + NaOH(aq) -> Na2SO4(aq) + H2O(l)", "No visible change, but the solution warms up", name="Neutralisation: H₂SO₄ and NaOH")
_rx("HNO3(aq) + NaOH(aq) -> NaNO3(aq) + H2O(l)", "No visible change, but the solution warms up", name="Neutralisation: HNO₃ and NaOH")
_rx("HCl(aq) + KOH(aq) -> KCl(aq) + H2O(l)", "No visible change, but the solution warms up", name="Neutralisation: HCl and KOH")
_rx("H2SO4(aq) + KOH(aq) -> K2SO4(aq) + H2O(l)", "No visible change, but the solution warms up", name="Neutralisation: H₂SO₄ and KOH")
_rx("CH3COOH(aq) + NaOH(aq) -> CH3COONa(aq) + H2O(l)", "No visible change", name="Neutralisation: acetic acid and NaOH")
_rx("HCl(aq) + NH3(aq) -> NH4Cl(aq)", "No visible change", name="Hydrochloric acid and ammonia")
_rx("HCl(aq) + Ca(OH)2(aq) -> CaCl2(aq) + H2O(l)", "No visible change", name="Hydrochloric acid and limewater")
# carbonates and hydrogen carbonates
_rx("CaCO3(s) + HCl(aq) -> CaCl2(aq) + H2O(l) + CO2(g)", "Brisk effervescence from the marble chips", rate=0.05, name="Marble and hydrochloric acid")
_rx("NaHCO3(s) + HCl(aq) -> NaCl(aq) + H2O(l) + CO2(g)", "Vigorous fizzing", rate=0.5, name="Baking soda and hydrochloric acid")
_rx("NaHCO3(s) + CH3COOH(aq) -> CH3COONa(aq) + H2O(l) + CO2(g)", "Fizzing, and the mixture cools", rate=0.3, name="Baking soda and vinegar")
_rx("Na2CO3(aq) + HCl(aq) -> NaCl(aq) + H2O(l) + CO2(g)", "Effervescence", rate=2.0, name="Sodium carbonate and hydrochloric acid")
_rx("CO2(g) + Ca(OH)2(aq) -> CaCO3(s) + H2O(l)", "The limewater turns milky", name="Carbon dioxide and limewater")
# precipitation (double displacement)
_rx("AgNO3(aq) + NaCl(aq) -> AgCl(s) + NaNO3(aq)", "A curdy white precipitate", name="Silver nitrate and sodium chloride")
_rx("AgNO3(aq) + HCl(aq) -> AgCl(s) + HNO3(aq)", "A curdy white precipitate", name="Silver nitrate and hydrochloric acid")
_rx("AgNO3(aq) + KI(aq) -> AgI(s) + KNO3(aq)", "A pale yellow precipitate", name="Silver nitrate and potassium iodide")
_rx("BaCl2(aq) + Na2SO4(aq) -> BaSO4(s) + NaCl(aq)", "A thick white precipitate", name="Barium chloride and sodium sulphate")
_rx("BaCl2(aq) + H2SO4(aq) -> BaSO4(s) + HCl(aq)", "A thick white precipitate", name="Barium chloride and sulphuric acid")
_rx("Pb(NO3)2(aq) + KI(aq) -> PbI2(s) + KNO3(aq)", "A bright yellow precipitate of lead iodide", name="Lead nitrate and potassium iodide")
_rx("CuSO4(aq) + NaOH(aq) -> Cu(OH)2(s) + Na2SO4(aq)", "A pale blue precipitate", unless=("KNaC4H4O6(aq)",), name="Copper sulphate and sodium hydroxide")
_rx("FeSO4(aq) + NaOH(aq) -> Fe(OH)2(s) + Na2SO4(aq)", "A dirty green precipitate", name="Ferrous sulphate and sodium hydroxide")
_rx("FeCl3(aq) + NaOH(aq) -> Fe(OH)3(s) + NaCl(aq)", "A reddish-brown precipitate", name="Ferric chloride and sodium hydroxide")
# displacement
_rx("Fe(s) + CuSO4(aq) -> FeSO4(aq) + Cu(s)", "A brown coat of copper forms on the iron; the blue colour fades to pale green", rate=0.02, name="Iron displaces copper")
_rx("Zn(s) + CuSO4(aq) -> ZnSO4(aq) + Cu(s)", "Brown copper appears on the zinc; the blue colour fades", rate=0.03, name="Zinc displaces copper")
_rx("Mg(s) + CuSO4(aq) -> MgSO4(aq) + Cu(s)", "Brown copper appears at once; the blue colour fades", rate=0.2, name="Magnesium displaces copper")
_rx("Cu(s) + AgNO3(aq) -> Cu(NO3)2(aq) + Ag(s)", "Shiny grey crystals of silver grow on the copper; the solution turns blue", rate=0.01, name="Copper displaces silver")
# oxides and bases with water and acids
_rx("CaO(s) + H2O(l) -> Ca(OH)2(aq)", "Hissing and a lot of heat: quicklime is slaked", rate=0.4, name="Quicklime and water")
_rx("CuO(s) + HCl(aq) -> CuCl2(aq) + H2O(l)", "The black powder dissolves to a blue-green solution", rate=0.05, name="Copper oxide and hydrochloric acid")
_rx("CuO(s) + H2SO4(aq) -> CuSO4(aq) + H2O(l)", "The black powder dissolves to a blue solution", rate=0.05, name="Copper oxide and sulphuric acid")
# dissolving (need water)
_rx("CuSO4(s) -> CuSO4(aq)", "The white powder turns blue and dissolves, warming the water", rate=0.4, needs=("H2O(l)",), name="Anhydrous copper sulphate dissolves")
_rx("CuSO4.5H2O(s) -> CuSO4(aq) + H2O(l)", "The blue crystals dissolve to a blue solution", rate=0.08, needs=("H2O(l)",), name="Copper sulphate crystals dissolve")
_rx("FeSO4.7H2O(s) -> FeSO4(aq) + H2O(l)", "The crystals dissolve to a pale green solution", rate=0.08, needs=("H2O(l)",), name="Ferrous sulphate dissolves")
_rx("NaCl(s) -> NaCl(aq)", "The salt dissolves", rate=0.2, needs=("H2O(l)",), name="Salt dissolves")
_rx("NaOH(s) -> NaOH(aq)", "The pellets dissolve and the solution gets hot", rate=0.2, needs=("H2O(l)",), name="Sodium hydroxide dissolves")
_rx("KNO3(s) -> KNO3(aq)", "The crystals dissolve and the solution turns cold", rate=0.15, needs=("H2O(l)",), name="Potassium nitrate dissolves")
_rx("NH4Cl(s) -> NH4Cl(aq)", "The crystals dissolve and the solution turns cold", rate=0.2, needs=("H2O(l)",), name="Ammonium chloride dissolves")
_rx("Pb(NO3)2(s) -> Pb(NO3)2(aq)", "The crystals dissolve", rate=0.15, needs=("H2O(l)",), name="Lead nitrate dissolves")
_rx("KMnO4(s) -> KMnO4(aq)", "Purple streaks spread through the water", rate=0.05, needs=("H2O(l)",), name="Potassium permanganate dissolves")
_rx("Ca(OH)2(s) -> Ca(OH)2(aq)", "A little dissolves; the rest stays as a white suspension", rate=0.02, needs=("H2O(l)",), name="Slaked lime dissolves")
# redox in solution
_rx("KMnO4(aq) + FeSO4(aq) + H2SO4(aq) -> K2SO4(aq) + MnSO4(aq) + Fe2(SO4)3(aq) + H2O(l)", "The purple permanganate is decolourised at once", name="Permanganate oxidises Fe²⁺")
_rx("H2O2(aq) -> H2O(l) + O2(g)", "Vigorous bubbling and the liquid gets warm", rate=0.25, needs=("MnO2(s)",), name="Hydrogen peroxide decomposes (MnO₂ catalyst)")
_rx("Na2S2O3(aq) + HCl(aq) -> NaCl(aq) + SO2(g) + S(s) + H2O(l)", "The solution slowly turns cloudy yellow as sulphur forms", rate=0.02, name="Thiosulphate and acid")
_rx("NH4Cl(aq) + NaOH(aq) -> NaCl(aq) + NH3(g) + H2O(l)", "A pungent smell of ammonia", min_t=50, rate=0.05, name="Ammonium salt and alkali (warm)")
_rx("NH4Cl(s) + Ca(OH)2(s) -> CaCl2(aq) + NH3(g) + H2O(g)", "A pungent smell of ammonia rises from the tube", min_t=80, rate=0.05, name="Ammonia from ammonium chloride and slaked lime")
# heating solids
_rx("CuSO4.5H2O(s) -> CuSO4(s) + H2O(g)", "The blue crystals turn white and water droplets form at the mouth of the tube", min_t=110, rate=0.04, name="Heating copper sulphate crystals")
_rx("FeSO4.7H2O(s) -> FeSO4(s) + H2O(g)", "The green crystals lose their water and turn white", min_t=100, rate=0.04, name="Heating ferrous sulphate crystals")
_rx("FeSO4(s) -> Fe2O3(s) + SO2(g) + SO3(g)", "The solid turns reddish brown and gives off a choking smell", min_t=480, rate=0.02, name="Ferrous sulphate decomposes")
_rx("CaCO3(s) -> CaO(s) + CO2(g)", "The chips glow; quicklime is left", min_t=840, rate=0.01, name="Limestone decomposes")
_rx("Cu2(OH)2CO3(s) -> CuO(s) + CO2(g) + H2O(g)", "The green powder turns black", min_t=290, rate=0.05, name="Copper carbonate decomposes")
_rx("Pb(NO3)2(s) -> PbO(s) + NO2(g) + O2(g)", "Crackling, brown fumes and a yellow residue", min_t=470, rate=0.03, name="Lead nitrate decomposes")
_rx("KMnO4(s) -> K2MnO4(s) + MnO2(s) + O2(g)", "The crystals crackle and turn black-green; the gas relights a glowing splint", min_t=240, rate=0.03, name="Potassium permanganate decomposes")
_rx("Fe(s) + S(s) -> FeS(s)", "The mixture glows red and leaves black iron sulphide (no longer attracted to a magnet)", min_t=500, rate=0.2, name="Iron and sulphur combine")
# burning in air (oxygen from the air, not from the vessel)
_rx("Mg(s) + O2(g) -> MgO(s)", "The ribbon burns with a dazzling white flame, leaving white ash", min_t=650, rate=0.3, air=True, name="Magnesium burns in air")
_rx("S(s) + O2(g) -> SO2(g)", "The sulphur melts and burns with a blue flame, giving a choking smell", min_t=250, rate=0.1, air=True, name="Sulphur burns in air")
_rx("Cu(s) + O2(g) -> CuO(s)", "The copper turns black on its surface", min_t=300, rate=0.003, air=True, name="Copper heated in air")
# concentrated acids
_rx("H2SO4(l) -> H2SO4(aq)", "The acid sinks and mixes; the solution gets very hot", rate=0.5, needs=("H2O(l)",), name="Diluting concentrated sulphuric acid")
_rx("HNO3(l) -> HNO3(aq)", "The acid mixes with the water and warms it", rate=0.5, needs=("H2O(l)",), name="Diluting concentrated nitric acid")
_rx("C12H22O11(s) -> C(s) + H2O(g)", "The sugar turns yellow, then brown, then swells into a steaming black column of carbon", rate=0.05,
    needs=("H2SO4(l)",), name="Concentrated sulphuric acid dehydrates sugar")
_rx("Cu(s) + HNO3(l) -> Cu(NO3)2(aq) + NO2(g) + H2O(l)", "Thick brown fumes of nitrogen dioxide; the liquid turns green, then blue", rate=0.1,
    name="Copper and concentrated nitric acid")
_rx("Cu(s) + HNO3(aq) -> Cu(NO3)2(aq) + NO(g) + H2O(l)", "Slow bubbles of a colourless gas that turns brown at the mouth; the solution turns blue",
    rate=0.004, name="Copper and dilute nitric acid")
_rx("C12H22O11(s) -> C12H22O11(aq)", "The sugar dissolves", rate=0.05, needs=("H2O(l)",), unless=("H2SO4(l)",), name="Sugar dissolves")
# qualitative analysis: cations
_rx("FeCl3(aq) + KSCN(aq) -> Fe(SCN)3(aq) + KCl(aq)", "A blood-red colour: Fe³⁺ is present", name="Thiocyanate test for Fe³⁺")
_rx("CuSO4(aq) + NH3(aq) + H2O(l) -> Cu(OH)2(s) + (NH4)2SO4(aq)", "A pale blue precipitate with a little ammonia", name="Copper sulphate and a little ammonia")
_rx("Cu(OH)2(s) + NH3(aq) -> Cu(NH3)4(OH)2(aq)", "In excess ammonia the precipitate dissolves to a deep blue solution: Cu²⁺ is present", rate=0.5,
    name="Excess ammonia: tetraamminecopper(II)")
_rx("ZnSO4(aq) + NaOH(aq) -> Zn(OH)2(s) + Na2SO4(aq)", "A white gelatinous precipitate", name="Zinc sulphate and sodium hydroxide")
_rx("ZnCl2(aq) + NaOH(aq) -> Zn(OH)2(s) + NaCl(aq)", "A white gelatinous precipitate", name="Zinc chloride and sodium hydroxide")
_rx("MgSO4(aq) + NaOH(aq) -> Mg(OH)2(s) + Na2SO4(aq)", "A white precipitate", name="Magnesium sulphate and sodium hydroxide")
_rx("AlCl3(aq) + NaOH(aq) -> Al(OH)3(s) + NaCl(aq)", "A white gelatinous precipitate", name="Aluminium chloride and sodium hydroxide")
_rx("Pb(NO3)2(aq) + HCl(aq) -> PbCl2(s) + HNO3(aq)", "A white precipitate of lead chloride", name="Lead nitrate and hydrochloric acid")
_rx("CaCl2(aq) + (NH4)2C2O4(aq) -> CaC2O4(s) + NH4Cl(aq)", "A white precipitate of calcium oxalate: Ca²⁺ is present", name="Oxalate test for Ca²⁺")
_rx("AgCl(s) + NH3(aq) -> Ag(NH3)2Cl(aq)", "The white precipitate dissolves in ammonia: it was silver chloride", rate=0.3, name="Silver chloride dissolves in ammonia")
_rx("CaCl2(aq) + Na2CO3(aq) -> CaCO3(s) + NaCl(aq)", "A white precipitate of calcium carbonate", name="Calcium chloride and sodium carbonate")
# anions
_rx("FeSO4(aq) + NaNO3(aq) + H2SO4(l) -> Fe2(SO4)3(aq) + Na2SO4(aq) + NO(g) + H2O(l)", "Where the concentrated acid meets the solution, a ring forms",
    rate=2.0, name="Nitrate reduced by Fe²⁺ in concentrated acid")
_rx("FeSO4(aq) + NO(g) -> Fe(NO)SO4(aq)", "A brown ring: nitrate is present", name="Brown ring test")
_rx("K2Cr2O7(aq) + SO2(g) + H2SO4(aq) -> K2SO4(aq) + Cr2(SO4)3(aq) + H2O(l)", "The orange dichromate turns green: the gas is sulphur dioxide", name="Sulphur dioxide reduces dichromate")
_rx("CaCO3(s) + CO2(g) + H2O(l) -> Ca(HCO3)2(aq)", "With more carbon dioxide the milkiness clears again",
    unless=("Ca(OH)2(aq)", "HCl(aq)", "H2SO4(aq)", "HNO3(aq)", "CH3COOH(aq)", "CaCl2(aq)", "CH3COONa(aq)"), name="Excess carbon dioxide clears limewater")
_rx("NH3(g) -> NH3(aq)", "The ammonia dissolves in the water", needs=("H2O(l)",), max_t=40, name="Ammonia dissolves in water")
# iodine
_rx("H2O2(aq) + KI(aq) + H2SO4(aq) -> I2(aq) + K2SO4(aq) + H2O(l)", "The solution slowly turns yellow-brown as iodine forms (blue-black with starch)", rate=0.05,
    name="Hydrogen peroxide oxidises iodide")
_rx("Na2S2O3(aq) + I2(aq) -> Na2S4O6(aq) + NaI(aq)", "The brown iodine colour is discharged", name="Thiosulphate reduces iodine")
# sugars
_rx("C6H12O6(aq) + Ag(NH3)2OH(aq) -> C6H11O7NH4(aq) + Ag(s) + NH3(aq) + H2O(l)", "A silver mirror coats the inside of the tube: a reducing sugar", min_t=50, rate=0.05,
    name="Tollens' test (silver mirror)")
_rx("C6H12O6(aq) + Cu(OH)2(s) + NaOH(aq) -> C6H11O7Na(aq) + Cu2O(s) + H2O(l)", "On warming, the blue precipitate turns brick red: a reducing sugar", min_t=60, rate=0.05,
    name="Trommer's test (red copper(I) oxide)")
_rx("C6H12O6(aq) + CuSO4(aq) + NaOH(aq) -> C6H11O7Na(aq) + Cu2O(s) + Na2SO4(aq) + H2O(l)", "On warming, the deep blue Fehling's solution gives a brick red precipitate: a reducing sugar",
    min_t=60, rate=0.05, needs=("KNaC4H4O6(aq)",), name="Fehling's test")
# alcohols, acids and esters
_rx("C2H5OH(l) -> C2H5OH(aq)", "The ethanol mixes with the water in any amount", rate=0.5, needs=("H2O(l)",), name="Ethanol mixes with water")
_rx("CH3COOH(l) -> CH3COOH(aq)", "The acid mixes with the water", rate=0.5, needs=("H2O(l)",), name="Diluting glacial acetic acid")
_rx("CH3COOH(l) + C2H5OH(l) -> CH3COOC2H5(l) + H2O(l)", "A sweet, fruity smell: ethyl ethanoate, an ester, has formed", min_t=60, rate=0.01,
    needs=("H2SO4(l)",), name="Esterification (ethyl ethanoate)")
_rx("C2H5OH(aq) + I2(aq) + NaOH(aq) -> CHI3(s) + HCOONa(aq) + NaI(aq) + H2O(l)", "Pale yellow crystals with an antiseptic smell: iodoform",
    min_t=50, rate=0.05, coeffs=[1, 4, 6, 1, 1, 5, 5], name="Iodoform test")
# flame-test salts dissolve
_rx("LiCl(s) -> LiCl(aq)", "The salt dissolves", rate=0.2, needs=("H2O(l)",), name="Lithium chloride dissolves")
_rx("SrCl2(s) -> SrCl2(aq)", "The salt dissolves", rate=0.2, needs=("H2O(l)",), name="Strontium chloride dissolves")
# evaporating to dryness leaves the dissolved salts as crystals
for _salt in ("NaCl", "KCl", "KNO3", "NaNO3", "Na2SO4", "K2SO4", "MgSO4", "ZnSO4", "CuSO4", "FeSO4", "CaCl2", "MgCl2", "ZnCl2", "CuCl2", "AlCl3",
              "CH3COONa", "Na2CO3", "NaOH", "KOH", "KI", "BaCl2", "AgNO3", "Cu(NO3)2", "NH4Cl", "Pb(NO3)2", "KMnO4", "LiCl", "SrCl2"):
    _rx(f"{_salt}(aq) -> {_salt}(s)", "The water has gone: crystals of the dissolved salt are left", unless=("H2O(l)",), name=f"{_salt} crystallises")


# ---------------------------------------------------------------- vessel physics
def _mass(contents: dict[str, float]) -> float:
    return sum(n * molar_mass_of(_formula(k)) for k, n in contents.items() if n > 0)


def _formula(key: str) -> str:
    return key[: key.rindex("(")]


def _water_ml(c: dict[str, float]) -> float:
    return c.get("H2O(l)", 0.0) * 18.015  # 1 g ≈ 1 mL


def _heat_capacity(c: dict[str, float], kind: str) -> float:
    water = _water_ml(c)
    solids = sum(n * molar_mass_of(_formula(k)) for k, n in c.items() if k.endswith("(s)"))
    return water * C_WATER + solids * C_SOLID + EQUIPMENT[kind]["glass"] * C_GLASS + 1.0


def _volume_ml(c: dict[str, float]) -> float:
    water = _water_ml(c)
    solid = sum(n * molar_mass_of(_formula(k)) for k, n in c.items() if k.endswith("(s)")) / 2.5  # ~2.5 g/mL for salts
    return water + solid


def _ph(c: dict[str, float]) -> float | None:
    V = _water_ml(c) / 1000.0
    if V < 1e-4:
        return None
    g = lambda k: max(0.0, c.get(k, 0.0))  # noqa: E731
    strong_h = g("HCl(aq)") + g("HNO3(aq)") + 2 * g("H2SO4(aq)")
    strong_oh = g("NaOH(aq)") + g("KOH(aq)") + 2 * g("Ca(OH)2(aq)")
    net = strong_h - strong_oh
    if net > 1e-7 * V:
        return -math.log10(net / V)
    if -net > 1e-7 * V:
        return 14 + math.log10(-net / V)
    ka, kb = 1.8e-5, 1.8e-5
    ha, a_, b_, bh = g("CH3COOH(aq)"), g("CH3COONa(aq)"), g("NH3(aq)"), g("NH4Cl(aq)")
    if ha > 0 and a_ > 0:
        return -math.log10(ka) + math.log10(a_ / ha)
    if ha > 0:
        return -math.log10(math.sqrt(ka * ha / V))
    if b_ > 0 and bh > 0:
        return 14 - (-math.log10(kb) + math.log10(bh / b_))
    if b_ > 0:
        return 14 + math.log10(math.sqrt(kb * b_ / V))
    if g("Na2CO3(aq)") > 0:
        return 14 + math.log10(math.sqrt(2.1e-4 * g("Na2CO3(aq)") / V))
    if bh > 0:
        return -math.log10(math.sqrt(1e-14 / kb * bh / V))
    if a_ > 0:
        return 14 + math.log10(math.sqrt(1e-14 / ka * a_ / V))
    for k, pka in (("FeCl3(aq)", 2.2), ("CuSO4(aq)", 7.5), ("ZnCl2(aq)", 9.0), ("AlCl3(aq)", 5.0)):  # metal-ion hydrolysis
        if g(k) > 0:
            return -math.log10(math.sqrt(10 ** -pka * g(k) / V))
    return 7.0


def _mix(stops, x):
    for i in range(1, len(stops)):
        if x <= stops[i][0]:
            (a, ca), (b, cb) = stops[i - 1], stops[i]
            f = max(0.0, min(1.0, (x - a) / (b - a)))
            return [round(ca[k] + (cb[k] - ca[k]) * f) for k in range(3)]
    return list(stops[-1][1])


INDICATOR_STOPS = {
    "phenolphthalein": [(0, (250, 250, 250)), (8.2, (250, 250, 250)), (10.0, (232, 60, 150)), (14, (232, 60, 150))],
    "methyl_orange": [(0, (220, 40, 40)), (3.1, (220, 40, 40)), (4.4, (240, 200, 40)), (14, (240, 200, 40))],
    "litmus": [(0, (215, 40, 50)), (5.0, (215, 40, 50)), (8.0, (60, 70, 200)), (14, (60, 70, 200))],
    "universal": [(0, (210, 30, 40)), (3, (240, 120, 40)), (5, (245, 200, 50)), (7, (80, 170, 70)), (9, (40, 120, 190)), (11, (70, 60, 170)), (14, (110, 40, 140))],
}


def _hex(rgb):
    return "#" + "".join(f"{max(0, min(255, int(v))):02x}" for v in rgb)


def _rgb(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]


def _appearance(c: dict[str, float], indicators: list[str], ph: float | None) -> dict[str, Any]:
    V = max(_water_ml(c), 1e-6) / 1000.0
    colour, alpha = [236, 242, 248], 0.12  # clear water
    weight = 0.0
    tint = [0.0, 0.0, 0.0]
    for k, n in c.items():
        if k.endswith("(aq)") and n > 0 and k in LOOK and LOOK[k][1] > 0:
            a = 1 - math.exp(-LOOK[k][1] * n / V)
            rgb = _rgb(LOOK[k][0])
            tint = [t + a * v for t, v in zip(tint, rgb)]
            weight += a
    if weight > 0:
        f = min(1.0, weight)
        colour = [(1 - f) * colour[i] + f * tint[i] / weight for i in range(3)]
        alpha = 0.12 + 0.75 * f
    if "starch" in indicators and c.get("I2(aq)", 0) > 1e-7:  # starch-iodine complex
        a = 1 - math.exp(-4000 * c["I2(aq)"] / V)
        colour = [(1 - a) * colour[i] + a * v for i, v in enumerate((20, 24, 70))]
        alpha = max(alpha, 0.12 + 0.85 * a)
    indicators = [i for i in indicators if i in INDICATOR_STOPS]
    if ph is not None and indicators:
        ind = _mix(INDICATOR_STOPS[indicators[-1]], ph)
        clear = indicators[-1] == "phenolphthalein" and ph < 8.2
        if not clear:
            colour = [0.35 * colour[i] + 0.65 * ind[i] for i in range(3)]
            alpha = max(alpha, 0.7)
    cloudy = c.get("S(s)", 0) > 0 or c.get("CaCO3(s)", 0) > 0 and _water_ml(c) > 1 and c.get("CaCO3(s)", 0) < 0.002
    solids = [{"species": k, "name": _formula(k), "colour": LOOK.get(k, ("#dddddd", 0))[0], "mass_g": n * molar_mass_of(_formula(k))}
              for k, n in sorted(c.items()) if k.endswith("(s)") and n > 1e-9]
    return {"liquid_colour": _hex(colour), "liquid_alpha": round(alpha, 3), "cloudy": bool(cloudy), "solids": solids}


GAS_JAR_MOL = 0.25e-3 * 101325 / (R_GAS * (ROOM_T + 273.15))  # what a 250 mL jar holds at 25 °C, 1 atm


def _step_vessel(v: dict[str, Any], dt: float, power: float, events: list[dict], t_now: float,
                 inflow: dict[str, float] | None = None) -> dict[str, Any]:
    kind = v["kind"]
    holds = EQUIPMENT[kind].get("holds_gas", False)
    c = {k: float(n) for k, n in v.get("contents", {}).items() if n > 1e-12}
    T = float(v.get("T", ROOM_T))
    gases: dict[str, float] = {}
    happened = []
    q = 0.0  # J released into the vessel
    sub = max(1, min(40, int(math.ceil(dt / 0.25))))
    h = dt / sub
    for _ in range(sub):
        for k, n in (inflow or {}).items():  # gas bubbling in through a delivery tube, spread over the step
            k = "H2O(l)" if k == "H2O(g)" else k  # steam condenses in the cool vessel
            c[k] = c.get(k, 0.0) + n / sub
        for r in REACTIONS:
            if T < r["min_t"] or any(c.get(nd, 0) <= 0 for nd in r["needs"]) or any(c.get(u, 0) > 1e-12 for u in r["unless"]):
                continue
            if r["max_t"] is not None and T > r["max_t"]:
                continue
            reac = {k: n for k, n in r["reactants"].items() if not (r["air"] and k == "O2(g)")}
            if any(c.get(k, 0) <= 1e-12 for k in reac):
                continue
            lim = min(c[k] / n for k, n in reac.items())
            xi = lim * (1 - math.exp(-r["rate"] * h)) if r["rate"] < 50 else lim
            if xi <= 1e-15:
                continue
            for k, n in reac.items():
                c[k] -= n * xi
                if c[k] < 1e-14:
                    c.pop(k)
            for k, n in r["products"].items():
                c[k] = c.get(k, 0.0) + n * xi
            q += -(r["dh"] or 0.0) * 1000 * xi  # reactions with no tabulated ΔH are taken as thermoneutral
            happened.append((r, xi))
        # gases leave; CO₂ meeting limewater in the same vessel reacts first (handled above on the next pass)
        held = 0.0
        for k in [k for k in c if k.endswith("(g)")]:
            if k == "CO2(g)" and c.get("Ca(OH)2(aq)", 0) > 0:
                continue
            if holds and k != "H2O(g)":  # a gas jar keeps what fits and the rest spills out of the mouth
                keep = min(c[k], max(0.0, GAS_JAR_MOL - held))
                held += keep
                if c[k] - keep > 1e-15:
                    gases[k] = gases.get(k, 0.0) + c[k] - keep
                c[k] = keep
                if keep <= 1e-15:
                    c.pop(k)
                continue
            gases[k] = gases.get(k, 0.0) + c.pop(k)
        # energy: reactions, burner, room
        cap = _heat_capacity(c, kind)
        loss = EQUIPMENT[kind]["loss"] * (T - ROOM_T)
        E = q + (power - loss) * h
        q = 0.0
        T_new = T + E / cap
        boil = 100.0
        if c.get("H2O(l)", 0) > 0 and T_new > boil:
            extra = (T_new - boil) * cap
            n_evap = min(c["H2O(l)"], extra / DH_VAP_WATER)
            c["H2O(l)"] -= n_evap
            gases["H2O(g)"] = gases.get("H2O(g)", 0.0) + n_evap
            if c["H2O(l)"] <= 1e-9:
                c.pop("H2O(l)")
                T_new = boil + (extra - n_evap * DH_VAP_WATER) / _heat_capacity(c, kind)
            else:
                T_new = boil
        T = min(max(T_new, -20.0), EQUIPMENT[kind]["max_t"])
    # report
    seen = {}
    for r, xi in happened:
        s = seen.setdefault(r["name"], {"reaction": r["name"], "equation": r["equation"], "observation": r["see"],
                                         "delta_h_kj_per_mol": None if r["dh"] is None else round(r["dh"], 2), "extent_mol": 0.0})
        s["extent_mol"] += xi
    for s in seen.values():
        events.append({"t": t_now, "vessel": v["id"], **s, "extent_mol": float(f"{s['extent_mol']:.4g}")})
    gas_out = []
    for k, n in gases.items():
        if n > 1e-9 and (k != "H2O(g)" or n > 1e-6):
            vol = n * R_GAS * (ROOM_T + 273.15) / 101325 * 1e6
            gas_out.append({"gas": _formula(k), "species": k, "mol": float(f"{n:.4g}"), "volume_ml": float(f"{vol:.4g}"), "test": GAS_TEST.get(k, "")})
    ph = _ph(c)
    look = _appearance(c, list(v.get("indicators", [])), ph)
    vol = _volume_ml(c)
    out = {"id": v["id"], "kind": kind, "name": EQUIPMENT[kind]["name"], "contents": {k: float(f"{n:.6g}") for k, n in sorted(c.items())},
           "indicators": list(v.get("indicators", [])), "T": round(T, 2), "volume_ml": round(vol, 2), "mass_g": round(_mass(c), 3),
           "ph": None if ph is None else round(ph, 2), "gases": gas_out, "boiling": any(g["species"] == "H2O(g)" and g["mol"] > 1e-6 for g in gas_out) and T >= 99.9,
           "overflow": vol > EQUIPMENT[kind]["capacity"], "reacting": [s["reaction"] for s in seen.values()], **look}
    if v.get("gas_to"):
        out["gas_to"] = v["gas_to"]
    out["_gas_raw"] = {k: n for k, n in gases.items() if n > 1e-12}
    return out


def _run_test(v: dict[str, Any], test: str) -> dict[str, Any]:
    """What a test on a stepped vessel shows: litmus, pH paper, a lighted or glowing splint at the mouth, or a flame test."""
    c, ph = v["contents"], v["ph"]
    gas = {g["species"] for g in v["gases"]} | {k for k, n in c.items() if k.endswith("(g)") and n > 1e-9}
    gas.discard("H2O(g)")
    if test in ("litmus_red", "litmus_blue"):
        colour = "red" if test == "litmus_red" else "blue"
        if ph is None:  # no liquid: moist litmus held in the gas
            acid = gas & {"CO2(g)", "SO2(g)", "NO2(g)", "SO3(g)"}
            if colour == "red" and "NH3(g)" in gas:
                return {"result": "Moist red litmus turns blue: the gas is alkaline (ammonia)", "colour": "#3c46c8"}
            if colour == "blue" and acid:
                return {"result": "Moist blue litmus turns red: the gas is acidic", "colour": "#d72832"}
            return {"result": f"The {colour} litmus does not change", "colour": "#d72832" if colour == "red" else "#3c46c8"}
        if colour == "red" and ph > 8:
            return {"result": f"Red litmus turns blue: the solution is basic (pH {ph:.1f})", "colour": "#3c46c8"}
        if colour == "blue" and ph < 5:
            return {"result": f"Blue litmus turns red: the solution is acidic (pH {ph:.1f})", "colour": "#d72832"}
        return {"result": f"The {colour} litmus does not change", "colour": "#d72832" if colour == "red" else "#3c46c8"}
    if test == "ph_paper":
        if ph is None:
            return {"result": "Nothing liquid to dip the paper in", "colour": "#e8d9a0"}
        return {"result": f"The paper matches pH {round(ph)} on the chart", "colour": _hex(_mix(INDICATOR_STOPS["universal"], ph)), "ph": round(ph)}
    if test == "lighted_splint":
        if "H2(g)" in gas:
            return {"result": "A squeaky pop: the gas is hydrogen"}
        if "O2(g)" in gas:
            return {"result": "The splint burns more brightly: the gas is oxygen"}
        if gas & {"CO2(g)", "NH3(g)", "SO2(g)", "NO2(g)"}:
            return {"result": "The flame goes out: the gas does not support burning"}
        return {"result": "The splint keeps burning as it does in air"}
    if test == "glowing_splint":
        if "O2(g)" in gas:
            return {"result": "The glowing splint bursts back into flame: the gas is oxygen"}
        return {"result": "The splint keeps glowing faintly and does not relight"}
    if test == "flame":
        metals: set[str] = set()
        for k, n in c.items():
            if n > 1e-9 and not k.endswith("(g)"):
                metals |= set(element_counts(_formula(k))) & set(FLAME)
        if not metals:
            return {"result": "No colour: the flame stays pale blue"}
        if "Na" in metals and len(metals) > 1:  # sodium's yellow swamps the rest unless seen through cobalt glass
            others = ", ".join(f"{m} ({FLAME[m][0]})" for m in sorted(metals - {"Na"}))
            return {"result": f"A strong golden yellow flame from sodium; through blue cobalt glass: {others}", "colour": FLAME["Na"][1]}
        m = sorted(metals)[0]
        return {"result": f"The flame turns {FLAME[m][0]}: {m} is present", "colour": FLAME[m][1]}
    raise ValueError(f"test must be one of {', '.join(TESTS)}")


def _lower(name: str) -> str:
    """"Sodium metal" → "sodium metal", but formulas such as "CuSO₄" keep their capitals."""
    return name[0].lower() + name[1:] if len(name) > 1 and name[1].islower() else name


def _add(v: dict[str, Any], chem: dict[str, Any], amount: float) -> str:
    c = v.setdefault("contents", {})
    if chem["kind"] == "indicator":
        if chem["id"] not in v.setdefault("indicators", []):
            v["indicators"].append(chem["id"])
        return f"Added a few drops of {_lower(chem['name'])}"
    if amount <= 0:
        raise ValueError("amount must be positive")
    if chem["kind"] == "solid":
        n = amount / molar_mass_of(_formula(chem["species"]))
        c[chem["species"]] = c.get(chem["species"], 0.0) + n
        return f"Added {amount:g} g of {_lower(chem['name'])}"
    if chem["kind"] == "pure":
        n = amount * chem["density"] / molar_mass_of(_formula(chem["species"]))
        c[chem["species"]] = c.get(chem["species"], 0.0) + n
        return f"Added {amount:g} mL of {_lower(chem['name'])}"
    if chem["kind"] == "liquid":
        c["H2O(l)"] = c.get("H2O(l)", 0.0) + amount * chem["density"] / 18.015
        return f"Added {amount:g} mL of {_lower(chem['name'])}"
    n = chem["conc"] * amount / 1000
    c[chem["species"]] = c.get(chem["species"], 0.0) + n
    for sp, conc in chem.get("extra", {}).items():
        c[sp] = c.get(sp, 0.0) + conc * amount / 1000
    c["H2O(l)"] = c.get("H2O(l)", 0.0) + amount / 18.015  # dilute solutions: about 1 g of water per mL
    return f"Added {amount:g} mL of {_lower(chem['name'])} ({chem['conc']:g} mol/L)"


@tool(domain="chemistry", name="lab_catalog",
      description="The virtual chemistry lab's shelf: chemicals (solids, liquids, solutions with concentrations, indicators), "
                  "glassware with capacities, tools, and the reactions the lab knows with balanced equations and ΔH.")
def lab_catalog() -> dict:
    return {"result": {"chemicals": list(CHEMICALS.values()), "equipment": [{"id": k, **v} for k, v in EQUIPMENT.items()], "tools": TOOLS, "tests": list(TESTS),
                       "reactions": [{"name": r["name"], "equation": r["equation"], "delta_h_kj_per_mol": None if r["dh"] is None else round(r["dh"], 2), "min_t": r["min_t"],
                                      "needs": list(r["needs"]), "observation": r["see"]} for r in REACTIONS]},
            "units": {"capacity": "mL", "delta_h_kj_per_mol": "kJ per mole of reaction as written", "min_t": "degC", "conc": "mol/L"},
            "assumptions": ["Standard enthalpies of formation at 298 K (CRC / NBS tables)", "Equations balanced by the engine"]}


@tool(domain="chemistry", name="lab_step",
      description="Virtual chemistry lab: advance a bench of vessels by dt seconds after applying actions. vessels: "
                  "[{id, kind, contents{species: mol}, T (°C), indicators[], heat (0..1 burner setting)}]; kind is one of "
                  "beaker, conical, test_tube, boiling_tube, crucible, dish, burette, cylinder, gas_jar, watch_glass; gas_to "
                  "(optional) sends the vessel's gas through a delivery tube into another vessel. actions: {type: 'add', vessel, "
                  "chemical, amount (g for solids, mL for liquids and solutions)}, {type: 'pour', from, to, volume_ml}, "
                  "{type: 'filter', from, to} (solids stay on the paper), {type: 'empty', vessel}, {type: 'wash', vessel} (a film of "
                  "water stays), {type: 'rinse', vessel, chemical} (a film of that solution stays), {type: 'test', vessel, test} with test "
                  "one of litmus_red, litmus_blue, ph_paper, lighted_splint, glowing_splint, flame. Returns each vessel's contents, temperature, pH, colour, solids, gases given off "
                  "with their tests, and the reactions that ran with balanced equations and ΔH.")
def lab_step(vessels: list[dict], actions: list[dict] | None = None, dt: float = 1.0, t: float = 0.0) -> dict:
    if not isinstance(vessels, list) or len(vessels) > 20:
        raise ValueError("vessels must be a list of at most 20 vessels")
    if not 0 <= dt <= 600:
        raise ValueError("dt must be between 0 and 600 seconds")
    bench: dict[str, dict] = {}
    for v in vessels:
        if not isinstance(v, dict) or v.get("kind") not in EQUIPMENT or not v.get("id"):
            raise ValueError(f"each vessel needs an id and a kind from {', '.join(EQUIPMENT)}")
        contents = v.get("contents") or {}
        if not isinstance(contents, dict) or any(k not in HF for k in contents):
            raise ValueError("vessel contents must use species the lab knows (see lab_catalog)")
        bench[str(v["id"])] = {"id": str(v["id"]), "kind": v["kind"], "contents": {k: float(n) for k, n in contents.items() if float(n) > 0},
                               "T": float(v.get("T", ROOM_T)), "indicators": [i for i in v.get("indicators", []) if i in INDICATOR_STOPS or i == "starch"],
                               "gas_to": str(v["gas_to"]) if v.get("gas_to") else None,
                               "heat": max(0.0, min(1.0, float(v.get("heat", 0) or 0)))}
    log: list[str] = []
    tests: list[tuple[str, str]] = []
    for a in actions or []:
        kind = a.get("type")
        if kind == "add":
            v, chem = bench.get(str(a.get("vessel"))), CHEMICALS.get(a.get("chemical"))
            if not v or not chem:
                raise ValueError("add needs an existing vessel and a chemical from lab_catalog")
            log.append(_add(v, chem, float(a.get("amount", 0) or 0)))
        elif kind == "pour":
            src, dst = bench.get(str(a.get("from"))), bench.get(str(a.get("to")))
            if not src or not dst or src is dst:
                raise ValueError("pour needs two different vessels")
            vol = _volume_ml(src["contents"])
            want = float(a.get("volume_ml", vol))
            f = 1.0 if vol <= 0 or want >= vol else max(0.0, want / vol)
            # liquids and anything dissolved or suspended go with the pour; heat goes with it too
            moved_cap, keep_cap = 0.0, _heat_capacity(dst["contents"], dst["kind"])
            for k in list(src["contents"]):
                if k.endswith("(s)") and f < 1.0:
                    continue
                n = src["contents"][k] * f
                src["contents"][k] -= n
                dst["contents"][k] = dst["contents"].get(k, 0.0) + n
                moved_cap += n * molar_mass_of(_formula(k)) * (C_WATER if k == "H2O(l)" else C_SOLID)
            if moved_cap > 0:
                dst["T"] = (dst["T"] * keep_cap + src["T"] * moved_cap) / (keep_cap + moved_cap)
            for i in src["indicators"]:
                if i not in dst["indicators"]:
                    dst["indicators"].append(i)
            log.append(f"Poured {min(want, vol):.3g} mL from {_lower(EQUIPMENT[src['kind']]['name'])} into {_lower(EQUIPMENT[dst['kind']]['name'])}")
        elif kind == "filter":
            src, dst = bench.get(str(a.get("from"))), bench.get(str(a.get("to")))
            if not src or not dst or src is dst:
                raise ValueError("filter needs two different vessels")
            moved = 0.0
            for k in [k for k in src["contents"] if not k.endswith("(s)")]:
                n = src["contents"].pop(k)
                dst["contents"][k] = dst["contents"].get(k, 0.0) + n
                moved += n
            for i in src["indicators"]:
                if i not in dst["indicators"]:
                    dst["indicators"].append(i)
            src["indicators"] = []
            left = [_formula(k) for k, n in src["contents"].items() if k.endswith("(s)") and n > 1e-9]
            log.append(f"Filtered into {_lower(EQUIPMENT[dst['kind']]['name'])}: the filtrate went through"
                       + (f"; {', '.join(left)} stayed on the filter paper" if left else "; nothing was left on the paper"))
        elif kind == "empty":
            v = bench.get(str(a.get("vessel")))
            if v:
                v["contents"], v["indicators"], v["T"] = {}, [], ROOM_T
        elif kind in ("wash", "rinse"):
            # Washing leaves a wet film of distilled water; rinsing with a solution leaves a film of that solution instead,
            # which is why a burette or pipette is rinsed with the liquid it will hold.
            v = bench.get(str(a.get("vessel")))
            if not v:
                raise ValueError(f"{kind} needs an existing vessel")
            film = FILM_ML.get(v["kind"], 0.5)
            v["contents"], v["indicators"], v["T"] = {}, [], ROOM_T
            if kind == "wash":
                _add(v, CHEMICALS["water"], film)
                log.append(f"Washed the {_lower(EQUIPMENT[v['kind']]['name'])} with distilled water: about {film:g} mL stays on the glass")
            else:
                chem = CHEMICALS.get(a.get("chemical"))
                if not chem or chem["kind"] in ("solid", "indicator"):
                    raise ValueError("rinse needs a liquid or solution from lab_catalog")
                _add(v, chem, film)
                log.append(f"Rinsed the {_lower(EQUIPMENT[v['kind']]['name'])} with {_lower(chem['name'])}: the film left is the same solution")
        elif kind == "test":
            if str(a.get("vessel")) not in bench or a.get("test") not in TESTS:
                raise ValueError(f"test needs an existing vessel and a test from {', '.join(TESTS)}")
            tests.append((str(a["vessel"]), a["test"]))
        else:
            raise ValueError("action type must be add, pour, filter, empty, wash, rinse or test")
    # vessels that pipe gas into another go first, so the gas arrives in the same step
    order: list[str] = []
    def visit(vid: str, seen: tuple = ()) -> None:  # noqa: E306
        if vid in order or vid in seen:
            return
        for src in bench.values():
            if src["gas_to"] == vid:
                visit(src["id"], seen + (vid,))
        order.append(vid)
    for vid in bench:
        visit(vid)
    events: list[dict] = []
    inflow: dict[str, dict[str, float]] = {}
    done: dict[str, dict] = {}
    for vid in order:
        v = bench[vid]
        o = _step_vessel(v, dt, v["heat"] * EQUIPMENT[v["kind"]]["flame"], events, t + dt, inflow.get(vid))
        raw = o.pop("_gas_raw")
        if v["gas_to"] in bench and v["gas_to"] != vid and v["gas_to"] not in done:
            tgt = inflow.setdefault(v["gas_to"], {})
            for k, n in raw.items():
                tgt[k] = tgt.get(k, 0.0) + n
            for g in o["gases"]:
                g["piped_to"] = v["gas_to"]
        done[vid] = o
    out = [done[vid] for vid in bench]
    results = [{"vessel": vid, "test": name, **_run_test(done[vid], name)} for vid, name in tests]
    return {"result": {"vessels": out, "events": events, "log": log, "tests": results, "t": t + dt},
            "units": {"T": "degC", "contents": "mol", "volume_ml": "mL", "mass_g": "g", "delta_h_kj_per_mol": "kJ/mol", "gases.volume_ml": "mL at 25 degC, 1 atm"},
            "assumptions": ["Dilute solutions: about 1 g of water per mL, heat capacity of water 4.18 J/(g K)",
                            "Reactions with no threshold go as soon as their reactants meet; rates are typical classroom rates",
                            "Gases escape at once (a gas jar keeps up to its volume; a delivery tube carries them on) and are reported at 25 °C and 1 atm",
                            "Reactions with no tabulated enthalpy of formation for a complex or organic product are treated as thermoneutral (ΔH reported as null)",
                            "The burner delivers a few hundred watts into the vessel; glass and contents lose heat to the room"]}
