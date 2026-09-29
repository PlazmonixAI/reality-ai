import math

import numpy as np
import pytest

from app.modules.chemistry.colligative import colligative_properties
from app.modules.chemistry.dating import radiometric_dating
from app.modules.chemistry.reactions import check_balance
from app.modules.chemistry.speciation import acid_speciation, alphas


# --- balancing checker ----------------------------------------------------------------------

def test_check_balance_correct_and_multiple():
    r = check_balance("C3H8 + O2 -> CO2 + H2O", [1, 5, 3, 4])["result"]
    assert r["balanced"] and r["smallest"]
    assert {t["element"]: (t["left"], t["right"]) for t in r["tally"]} == {"C": (3, 3), "H": (8, 8), "O": (10, 10)}
    d = check_balance("C3H8 + O2 -> CO2 + H2O", [2, 10, 6, 8])["result"]
    assert d["balanced"] and not d["smallest"] and d["multiple_of_smallest"] == 2


def test_check_balance_wrong_and_charge():
    w = check_balance("H2 + O2 -> H2O", [1, 1, 1])["result"]
    assert not w["balanced"] and w["correct_coefficients"] == [2, 1, 2]
    assert {t["element"]: t["balanced"] for t in w["tally"]} == {"H": True, "O": False}
    # Ionic: Cu + Ag+ -> Cu^2+ + Ag needs 1, 2, 1, 2 (charge balances too)
    ok = check_balance("Cu + Ag+ -> Cu^2+ + Ag", [1, 2, 1, 2])["result"]
    assert ok["balanced"] and any(t["element"] == "charge" for t in ok["tally"])
    bad = check_balance("Cu + Ag+ -> Cu^2+ + Ag", [1, 1, 1, 1])["result"]
    assert not bad["balanced"]
    assert not check_balance("H2 + O2 -> H2O", [0, 0, 0])["result"]["balanced"]
    with pytest.raises(ValueError):
        check_balance("H2 + O2 -> H2O", [2, 1])


# --- polyprotic speciation ----------------------------------------------------------------------

PHOSPHORIC = [2.15, 7.20, 12.35]


def test_phosphoric_fractions_cross_at_pka():
    for i, pka in enumerate(PHOSPHORIC):
        a = alphas(np.array([pka]), PHOSPHORIC)[:, 0]
        assert a[i] == pytest.approx(a[i + 1], rel=1e-9)
    grid = np.linspace(0, 14, 50)
    assert np.allclose(alphas(grid, PHOSPHORIC).sum(axis=0), 1)
    # Intermediate H2PO4− peaks near (pKa1 + pKa2)/2 = 4.675 with α ≈ 0.994
    r = acid_speciation(PHOSPHORIC, ph=4.675)["result"]
    assert r["at_ph"]["dominant"] == 1 and r["at_ph"]["fractions"][1] == pytest.approx(0.9944, abs=5e-4)


def test_ph_of_acid_solutions():
    # 0.1 M H3PO4: first dissociation dominates, x²/(C − x) = Ka1 → pH ≈ 1.63 for pKa1 = 2.15
    # (textbooks quoting 1.62 use Ka1 = 7.5e-3); 0.1 M acetic acid (pKa 4.76): pH ≈ 2.88
    ka = 10**-2.15
    x = (-ka + math.sqrt(ka * ka + 4 * ka * 0.1)) / 2
    assert acid_speciation(PHOSPHORIC, 0.1)["result"]["ph_of_acid_solution"] == pytest.approx(-math.log10(x), abs=2e-3)
    assert acid_speciation([4.76], 0.1)["result"]["ph_of_acid_solution"] == pytest.approx(2.88, abs=0.01)
    # Carbonic acid at pH 8.3 (≈ (6.35 + 10.33)/2): bicarbonate dominates (~98 %)
    c = acid_speciation([6.35, 10.33], ph=8.34)["result"]["at_ph"]
    assert c["dominant"] == 1 and c["fractions"][1] > 0.97
    assert acid_speciation([6.35, 10.33])["result"]["species"] == ["H₂A", "HA⁻", "A²⁻"]


def test_speciation_validation():
    with pytest.raises(ValueError):
        acid_speciation([7.2, 2.15])
    with pytest.raises(ValueError):
        acid_speciation([4.76], 0)


# --- colligative ---------------------------------------------------------------------------

def test_freezing_and_boiling_water():
    r = colligative_properties(58.44, 1, formula="NaCl", van_t_hoff=2)["result"]
    assert r["molality"] == pytest.approx(1.0, rel=1e-3)
    assert r["freezing_point_depression"] == pytest.approx(3.72, rel=1e-3)
    assert r["boiling_point"] == pytest.approx(100 + 1.024, rel=1e-4)
    s = colligative_properties(342.3, 1, formula="C12H22O11")["result"]  # 1 mol sucrose
    assert s["freezing_point"] == pytest.approx(-1.86, rel=2e-3)


def test_vapour_pressure_and_osmosis():
    # 1 mol of solute particles in 1 kg water: x_water = 55.51 / 56.51
    r = colligative_properties(180.16, 1, formula="C6H12O6")["result"]
    assert r["vapour_pressure_ratio"] == pytest.approx(55.51 / 56.51, rel=1e-3)
    # 0.1 mol glucose in ~1 L at 298 K: Π ≈ 0.1 × 0.08206 × 298 ≈ 2.44 atm
    o = colligative_properties(18.016, 1, formula="C6H12O6")["result"]
    assert o["osmotic_pressure_atm"] == pytest.approx(2.44, abs=0.02)
    b = colligative_properties(12.8, 0.1, molar_mass=128.17, solvent="benzene")["result"]  # naphthalene
    assert b["freezing_point_depression"] == pytest.approx(5.12 * 12.8 / 128.17 / 0.1, rel=1e-6)


# --- radiometric dating ----------------------------------------------------------------------

def test_carbon_dating():
    r = radiometric_dating("C-14", fraction_remaining=0.25)["result"]
    assert r["age_years"] == pytest.approx(2 * 5730) and r["half_lives_elapsed"] == pytest.approx(2)
    e = radiometric_dating("C-14", fraction_remaining=0.5, relative_error=0.02)["result"]
    lo, hi = e["age_range_years"]
    assert lo < 5730 < hi


def test_daughter_ratio_and_k_ar_branch():
    u = radiometric_dating("U-238/Pb-206", daughter_parent_ratio=1.0)["result"]
    assert u["age_years"] == pytest.approx(4.468e9)
    k = radiometric_dating("K-40/Ar-40", daughter_parent_ratio=0.1072)["result"]
    assert k["age_years"] == pytest.approx(1.248e9)  # one half-life: half the parent gone, 10.72 % of it as Ar
    # Earth's age from U-238/Pb-206 ≈ 4.54 Gyr ↔ D/P ≈ 1.02
    t = radiometric_dating("U-238/Pb-206", daughter_parent_ratio=2 ** (4.54e9 / 4.468e9) - 1)["result"]["age_years"]
    assert t == pytest.approx(4.54e9)


def test_dating_validation():
    with pytest.raises(ValueError):
        radiometric_dating("C-14")
    with pytest.raises(ValueError):
        radiometric_dating("C-14", fraction_remaining=0.5, daughter_parent_ratio=1)
    with pytest.raises(ValueError):
        radiometric_dating("Unobtainium", fraction_remaining=0.5)


def test_whole_reaction_events_for_molecule_counts():
    from app.modules.chemistry.stoichiometry import stoichiometry
    # 4 N2 + 5 H2 molecules: only one complete N2 + 3 H2 event fits → 2 NH3, 3 N2 and 2 H2 left
    r = stoichiometry("N2 + H2 -> NH3", moles={"N2": 4, "H2": 5}, whole_reactions=True)["result"]
    assert r["products"]["NH3"]["moles"] == 2
    assert r["excess_remaining"]["N2"]["moles"] == 3 and r["excess_remaining"]["H2"]["moles"] == 2
    cont = stoichiometry("N2 + H2 -> NH3", moles={"N2": 4, "H2": 5})["result"]
    assert cont["products"]["NH3"]["moles"] == pytest.approx(10 / 3) and "H2" not in cont["excess_remaining"]
