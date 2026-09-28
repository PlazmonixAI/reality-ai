import pytest

from app.modules.chemistry.vsepr import molecule_shape

CASES = [
    ("CO2", "AX2", "linear", [180.0]),
    ("BF3", "AX3", "trigonal planar", [120.0]),
    ("CH4", "AX4", "tetrahedral", [109.47]),
    ("NH3", "AX3E1", "trigonal pyramidal", [109.47]),
    ("H2O", "AX2E2", "bent", [109.47]),
    ("SO2", "AX2E1", "bent", [120.0]),
    ("PCl5", "AX5", "trigonal bipyramidal", [90.0, 120.0, 180.0]),
    ("SF4", "AX4E1", "seesaw", [90.0, 120.0, 180.0]),
    ("ClF3", "AX3E2", "T-shaped", [90.0, 180.0]),
    ("XeF2", "AX2E3", "linear", [180.0]),
    ("SF6", "AX6", "octahedral", [90.0, 180.0]),
    ("IF5", "AX5E1", "square pyramidal", [90.0, 180.0]),
    ("XeF4", "AX4E2", "square planar", [90.0, 180.0]),
    ("NO3^-", "AX3", "trigonal planar", [120.0]),
    ("NH4^+", "AX4", "tetrahedral", [109.47]),
    ("SO4^2-", "AX4", "tetrahedral", [109.47]),
    ("ClO3^-", "AX3E1", "trigonal pyramidal", [109.47]),
]


@pytest.mark.parametrize("formula, axe, shape, angles", CASES)
def test_textbook_shapes(formula, axe, shape, angles):
    r = molecule_shape(formula)["result"]
    assert r["axe"] == axe and r["molecular_geometry"] == shape
    assert r["ideal_bond_angles"] == pytest.approx(angles, abs=0.05)


def test_lone_pairs_compress_angles():
    h2o = molecule_shape("H2O")["result"]["compressed_bond_angles"][0]
    nh3 = molecule_shape("NH3")["result"]["compressed_bond_angles"][0]
    assert h2o < nh3 < 109.47


def test_direct_domain_counts():
    assert molecule_shape(bonding_domains=4, lone_pairs=2)["result"]["molecular_geometry"] == "square planar"


def test_vsepr_validation():
    with pytest.raises(ValueError):
        molecule_shape("H2")
    with pytest.raises(ValueError):
        molecule_shape()
