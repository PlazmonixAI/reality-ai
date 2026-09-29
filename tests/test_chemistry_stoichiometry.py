import pytest

from app.modules.chemistry.formula import element_counts, split_species
from app.modules.chemistry.stoichiometry import balance_equation, molar_mass, stoichiometry


@pytest.mark.parametrize("formula, expected", [
    ("H2O", 18.015),
    ("NaCl", 58.44),
    ("CO2", 44.009),
    ("C6H12O6", 180.156),
    ("Ca(OH)2", 74.092),
    ("CuSO4.5H2O", 249.677),
    ("CuSO4·5H2O", 249.677),
    ("K4[Fe(CN)6]", 368.345),
    ("Al2(SO4)3", 342.132),
    ("(NH4)3PO4", 149.086),
])
def test_molar_mass(formula, expected):
    assert molar_mass(formula)["result"] == pytest.approx(expected, abs=2e-3)


def test_composition_percent():
    comp = molar_mass("H2O")["composition"]
    assert comp["H"]["atoms"] == 2
    assert comp["O"]["mass_percent"] == pytest.approx(88.81, abs=0.01)
    assert sum(c["mass_percent"] for c in comp.values()) == pytest.approx(100)


def test_si_molar_mass():
    assert molar_mass("H2O")["molar_mass_si"] == pytest.approx(0.018015)


@pytest.mark.parametrize("bad", ["Xy2", "H2O)", "(H2O", "h2o", "H0", ""])
def test_bad_formulas(bad):
    with pytest.raises(ValueError):
        molar_mass(bad)


def test_ion_and_state_parsing():
    s = split_species("SO4^2-(aq)")
    assert (s.formula, s.charge, s.state) == ("SO4", -2, "aq")
    assert split_species("OH-").charge == -1
    assert split_species("Fe+++").charge == 3
    assert element_counts("Mg3(PO4)2") == {"Mg": 3, "P": 2, "O": 8}


@pytest.mark.parametrize("equation, coeffs", [
    ("H2 + O2 -> H2O", [2, 1, 2]),
    ("C3H8 + O2 -> CO2 + H2O", [1, 5, 3, 4]),
    ("Fe + O2 = Fe2O3", [4, 3, 2]),
    ("KMnO4 + HCl -> KCl + MnCl2 + H2O + Cl2", [2, 16, 2, 2, 8, 5]),
    ("C6H12O6 + O2 -> CO2 + H2O", [1, 6, 6, 6]),
    ("MnO4- + Fe^2+ + H+ -> Mn^2+ + Fe^3+ + H2O", [1, 5, 8, 1, 5, 4]),
    ("Cu + NO3- + H+ -> Cu^2+ + NO + H2O", [3, 2, 8, 3, 2, 4]),
])
def test_balance(equation, coeffs):
    assert list(balance_equation(equation)["coefficients"].values()) == coeffs


def test_balance_ignores_given_coefficients():
    assert balance_equation("4 H2 + 7 O2 -> 3 H2O")["result"] == "2 H2 + O2 -> 2 H2O"


def test_unbalanceable():
    with pytest.raises(ValueError):
        balance_equation("H2O -> CO2")


def test_limiting_reagent_by_mass():
    # 4 g H2 (1.98 mol) + 16 g O2 (0.5 mol): O2 limits, 1.0 mol (18.02 g) water
    r = stoichiometry("H2 + O2 -> H2O", masses={"H2": 4, "O2": 16})["result"]
    assert r["limiting_reagent"] == "O2"
    assert r["products"]["H2O"]["grams"] == pytest.approx(18.016, abs=1e-2)
    assert r["excess_remaining"]["H2"]["grams"] == pytest.approx(4 - 2.016, abs=1e-2)


def test_haber_by_moles():
    # 3 mol N2 + 6 mol H2: H2 limits -> 4 mol NH3
    r = stoichiometry("N2 + H2 -> NH3", moles={"N2": 3, "H2": 6})["result"]
    assert r["limiting_reagent"] == "H2"
    assert r["products"]["NH3"]["moles"] == pytest.approx(4)
    assert r["excess_remaining"]["N2"]["moles"] == pytest.approx(1)


def test_single_reactant_given():
    # Combustion of 44.1 g propane (1 mol) -> 3 mol CO2 (132.03 g)
    r = stoichiometry("C3H8 + O2 -> CO2 + H2O", masses={"C3H8": 44.097})["result"]
    assert r["products"]["CO2"]["moles"] == pytest.approx(3, rel=1e-4)
    assert r["reactants_consumed"]["O2"]["moles"] == pytest.approx(5, rel=1e-4)


def test_stoichiometry_validation():
    with pytest.raises(ValueError, match="not a reactant"):
        stoichiometry("H2 + O2 -> H2O", masses={"H2O": 1})
    with pytest.raises(ValueError):
        stoichiometry("H2 + O2 -> H2O")
