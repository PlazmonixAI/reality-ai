import math

import numpy as np
import pytest

from app.modules.chemistry.electrochem import F, R, galvanic_cell
from app.modules.chemistry.energy_profile import fraction_above, reaction_profile
from app.modules.chemistry.real_gases import van_der_waals, vapor_pressure
from app.modules.chemistry.solutions import molarity_dilution


# --- molarity & dilution -------------------------------------------------------------

def test_molarity_from_formula():
    # 15.96 g CuSO4 (159.6 g/mol) in 500 mL -> 0.2 mol/L
    r = molarity_dilution(solute_mass=15.96, volume=0.5e-3, formula="CuSO4")["result"]
    assert r["molar_mass"] == pytest.approx(159.6, abs=0.05)
    assert r["concentration"] == pytest.approx(0.2, rel=1e-3)
    assert r["concentration_si"] == pytest.approx(200, rel=1e-3)


def test_dilution_c1v1_c2v2():
    r = molarity_dilution(solute_mass=58.44, volume=1e-3, molar_mass=58.44, final_volume=4e-3)["result"]
    assert r["concentration_before_dilution"] == pytest.approx(1.0)
    assert r["concentration"] == pytest.approx(0.25)
    assert r["dilution_factor"] == pytest.approx(4)


def test_solubility_limit_and_redissolving():
    # 1 mol in 1 L with a 0.5 mol/L limit: half stays solid; diluting to 2 L dissolves it all
    r = molarity_dilution(solute_mass=100, volume=1e-3, molar_mass=100, solubility=0.5)["result"]
    assert r["saturated"] and r["concentration"] == pytest.approx(0.5)
    assert r["undissolved_mass"] == pytest.approx(50)
    r = molarity_dilution(solute_mass=100, volume=1e-3, molar_mass=100, solubility=0.5, final_volume=2e-3)["result"]
    assert r["concentration"] == pytest.approx(0.5) and r["undissolved_mass"] == pytest.approx(0)


@pytest.mark.parametrize("kw", [{"volume": 0}, {"final_volume": 0.5e-3}, {"molar_mass": None, "formula": None}])
def test_molarity_validation(kw):
    args = {"solute_mass": 1, "volume": 1e-3, "molar_mass": 10} | kw
    with pytest.raises(ValueError):
        molarity_dilution(**args)


# --- galvanic cells --------------------------------------------------------------------

def test_daniell_cell_standard():
    r = galvanic_cell("Zn", "Cu")["result"]
    assert r["standard_potential"] == pytest.approx(1.10)
    assert r["electrons_transferred"] == 2
    assert r["delta_g_standard"] == pytest.approx(-2 * F * 1.10)
    assert r["delta_g_standard"] / 1000 == pytest.approx(-212.3, abs=0.1)  # kJ/mol
    assert r["log10_k"] == pytest.approx(37.2, abs=0.1)
    assert r["overall"] == "Zn + Cu2+ -> Zn2+ + Cu"


def test_nernst_concentration_dependence():
    # Q = [Zn2+]/[Cu2+] = 0.01/1 -> E = 1.10 + 0.0592/2 * 2 = 1.159 V
    r = galvanic_cell("Zn", "Cu", anode_concentration=0.01, cathode_concentration=1)["result"]
    assert r["cell_potential"] == pytest.approx(1.10 + 0.05916, abs=2e-4)
    assert r["nernst_slope"] == pytest.approx(0.05916 / 2, abs=1e-5)


def test_mixed_charges_silver_copper():
    # Cu + 2Ag+: n = 2, Q = [Cu2+]/[Ag+]^2
    r = galvanic_cell("Cu", "Ag", anode_concentration=1, cathode_concentration=0.1)["result"]
    assert r["electrons_transferred"] == 2
    assert r["cell_potential"] == pytest.approx(0.46 - 0.05916 / 2 * 2, abs=2e-4)
    assert galvanic_cell("Al", "Cu")["result"]["electrons_transferred"] == 6


def test_cell_reversed_not_spontaneous_and_equilibrium():
    r = galvanic_cell("Cu", "Zn")["result"]
    assert r["standard_potential"] == pytest.approx(-1.10) and not r["spontaneous"]
    # At Q = K the cell is dead
    d = galvanic_cell("Zn", "Cu")["result"]
    t = 298.15
    assert d["standard_potential"] - R * t * math.log(10) / (2 * F) * d["log10_k"] == pytest.approx(0, abs=1e-12)


def test_cell_validation():
    for args in [("Zn", "Zn"), ("Xx", "Cu")]:
        with pytest.raises(ValueError):
            galvanic_cell(*args)
    with pytest.raises(ValueError):
        galvanic_cell("Zn", "Cu", anode_concentration=0)


# --- van der Waals ------------------------------------------------------------------------

A_CO2, B_CO2 = 0.3640, 4.267e-5


def test_vdw_critical_point_co2():
    r = van_der_waals(A_CO2, B_CO2, 350)["result"]
    assert r["critical_temperature"] == pytest.approx(304.0, abs=0.5)
    assert r["critical_pressure"] / 1e5 == pytest.approx(74.0, abs=0.3)
    assert r["critical_molar_volume"] == pytest.approx(3 * B_CO2)
    assert r["saturation"] is None


def test_maxwell_equal_area_reduced():
    # Reduced vdW: at Tr = 0.9 the coexistence pressure is Pr = 0.647 (textbook)
    tc = 8 * A_CO2 / (27 * R * B_CO2)
    r = van_der_waals(A_CO2, B_CO2, 0.9 * tc)["result"]
    s = r["saturation"]
    assert s["pressure"] / r["critical_pressure"] == pytest.approx(0.647, abs=1e-3)
    # Areas really are equal: integrate P numerically between the liquid and gas volumes
    v = np.linspace(s["v_liquid"], s["v_gas"], 200001)
    p = R * 0.9 * tc / (v - B_CO2) - A_CO2 / v**2
    assert np.trapezoid(p - s["pressure"], v) == pytest.approx(0, abs=1e-6 * s["pressure"] * (s["v_gas"] - s["v_liquid"]))
    assert s["v_liquid"] < r["critical_molar_volume"] < s["v_gas"]


def test_vdw_state_and_phases():
    tc = 8 * A_CO2 / (27 * R * B_CO2)
    r = van_der_waals(A_CO2, B_CO2, 0.9 * tc)["result"]
    s = r["saturation"]
    mid = (s["v_liquid"] + s["v_gas"]) / 2
    st = van_der_waals(A_CO2, B_CO2, 0.9 * tc, molar_volume=mid)["result"]["state"]
    assert st["phase"] == "liquid + vapour" and st["pressure"] == pytest.approx(s["pressure"])
    assert 0 < st["vapour_fraction"] < 1
    gas = van_der_waals(A_CO2, B_CO2, 400, molar_volume=0.1)["result"]["state"]
    assert gas["phase"] == "supercritical fluid"
    assert gas["compressibility"] == pytest.approx(1, abs=0.01)  # nearly ideal when dilute


def test_vdw_validation():
    with pytest.raises(ValueError):
        van_der_waals(A_CO2, 0, 300)
    with pytest.raises(ValueError):
        van_der_waals(A_CO2, B_CO2, 300, molar_volume=B_CO2 / 2)


# --- Clausius-Clapeyron ----------------------------------------------------------------

def test_water_boils_lower_on_everest():
    r = vapor_pressure(40650, 373.15, pressure=33700)["result"]
    assert r["boiling_point_at_pressure"] - 273.15 == pytest.approx(71, abs=1.5)


def test_clausius_clapeyron_roundtrip_and_normal_point():
    r = vapor_pressure(40650, 373.15, temperature=373.15)["result"]
    assert r["vapor_pressure"] == pytest.approx(101325)
    p = vapor_pressure(40650, 373.15, temperature=350)["result"]["vapor_pressure"]
    back = vapor_pressure(40650, 373.15, pressure=p)["result"]["boiling_point_at_pressure"]
    assert back == pytest.approx(350)
    # Water at 25 °C: CC with constant ΔH gives ~3.7 kPa (real 3.17 kPa: ΔH grows as T falls)
    p25 = vapor_pressure(40650, 373.15, temperature=298.15)["result"]["vapor_pressure"]
    assert 3000 < p25 < 4200


def test_trouton_benzene():
    # Benzene: ΔHvap 30.7 kJ/mol, Tb 353.2 K -> ΔS ≈ 87 J/(mol K), Trouton ratio ≈ 1
    r = vapor_pressure(30700, 353.2)["result"]
    assert r["entropy_vap"] == pytest.approx(86.9, abs=0.3)
    assert r["trouton_ratio"] == pytest.approx(1, abs=0.02)


# --- reaction profiles ------------------------------------------------------------------

def test_catalyst_speedup_and_profile():
    r = reaction_profile(75000, -40000, catalyst_activation_energy=50000)
    x = r["result"]
    assert x["reverse_activation_energy"] == pytest.approx(115000)
    assert x["catalysed"]["rate_enhancement"] == pytest.approx(math.exp(25000 / (R * 298.15)))
    assert x["catalysed"]["rate_enhancement"] == pytest.approx(2.4e4, rel=0.02)
    # Catalyst does not change the equilibrium: kf/kr is the same
    c = x["catalysed"]
    assert c["k_forward"] / c["k_reverse"] == pytest.approx(x["k_forward"] / x["k_reverse"])
    assert x["k_forward"] / x["k_reverse"] == pytest.approx(x["equilibrium_constant"])
    prof = r["profile"]
    assert max(prof["energy"]) == pytest.approx(75000) and prof["energy"][-1] == pytest.approx(-40000)
    assert max(prof["energy_catalysed"]) == pytest.approx(50000)


def test_fraction_above_barrier_matches_distribution():
    t = 500.0
    r = reaction_profile(20000, 5000, temperature=t, n_points=50)
    e, f = np.array(r["distribution"]["energy"]), np.array(r["distribution"]["density"])
    # Density integrates to the covered fraction (trapezoid is slightly low at the sqrt(E) cusp at 0)
    assert np.trapezoid(f, e) == pytest.approx(1 - fraction_above(e[-1], t), abs=2e-3)
    # Numerical tail integral agrees with the closed form
    ee = np.linspace(20000, 400000, 200001)
    ff = 2 * np.sqrt(ee / math.pi) * (R * t) ** -1.5 * np.exp(-ee / (R * t))
    assert np.trapezoid(ff, ee) == pytest.approx(fraction_above(20000, t), rel=1e-5)
    assert r["result"]["fraction_above_barrier"] == pytest.approx(fraction_above(20000, t))
    assert fraction_above(0, t) == pytest.approx(1)


@pytest.mark.parametrize("args", [(0, 0), (10000, 20000), (50000, 0, 60000), (50000, -1000, 0)])
def test_profile_validation(args):
    with pytest.raises(ValueError):
        reaction_profile(*args)
