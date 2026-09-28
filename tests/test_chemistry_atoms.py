import pytest

from app.modules.chemistry.atoms import atom_builder, electron_configuration, nuclear_binding_energy


def test_carbon_12():
    r = atom_builder(6, 6, 6)["result"]
    assert r["element"]["symbol"] == "C" and r["element"]["name"] == "Carbon"
    assert r["mass_number"] == 12 and r["charge"] == 0 and r["stable_nucleus"] is True
    assert r["electron_configuration"] == "1s2 2s2 2p2"
    assert r["shells"] == [2, 4] and r["notation"] == "C-12"


def test_carbon_14_unstable():
    assert atom_builder(6, 8, 6)["result"]["stable_nucleus"] is False


def test_sodium_ion():
    r = atom_builder(11, 12, 10)["result"]
    assert r["charge"] == 1 and r["notation"] == "Na-23^+" and r["shells"] == [2, 8]


def test_oxide_ion():
    r = atom_builder(8, 8, 10)["result"]
    assert r["charge"] == -2 and r["notation"] == "O-16^2-"


def test_potassium_fills_4s_before_3d():
    assert atom_builder(19, 20, 19)["result"]["electron_configuration"] == "1s2 2s2 2p6 3s2 3p6 4s1"
    assert atom_builder(20, 20, 20)["result"]["shells"] == [2, 8, 8, 2]


def test_madelung_order_beyond_calcium():
    # Scandium: 4s fills before 3d
    cfg = electron_configuration(21)
    assert cfg[-1] == (3, "d", 1) and (4, "s", 2) in cfg


def test_iron_56_binding_energy():
    r = nuclear_binding_energy(26, 30)
    assert r["per_nucleon"] == pytest.approx(8.79, rel=0.01)


def test_calcium_40_binding_energy():
    assert nuclear_binding_energy(20, 20)["result"] == pytest.approx(342.05, rel=0.03)


def test_empty_nucleus():
    r = atom_builder(0, 1, 0)["result"]
    assert r["element"] is None and r["stable_nucleus"] is None


def test_atom_validation():
    with pytest.raises(ValueError):
        atom_builder(21, 20, 21)
    with pytest.raises(ValueError):
        nuclear_binding_energy(1, 0)
