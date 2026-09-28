import math

import pytest

from app.modules.chemistry.equilibrium import equilibrium_ice, kc_kp_convert


def test_hydrogen_iodide():
    # Textbook: 1.0 M H2 + 1.0 M I2, Kc = 50.5 -> x = sqrt(K)/(2+sqrt(K)), [HI] = 2x
    r = equilibrium_ice("H2 + I2 <=> 2 HI", 50.5, {"H2": 1.0, "I2": 1.0})
    s = math.sqrt(50.5)
    x = s / (2 + s)
    assert r["result"]["HI"] == pytest.approx(2 * x, rel=1e-12)
    assert r["result"]["H2"] == pytest.approx(1 - x, rel=1e-12)
    assert r["direction"] == "forward"


def test_dinitrogen_tetroxide_quadratic():
    # 4x^2 = K (0.1 - x)
    k = 4.64e-3
    x = (-k + math.sqrt(k * k + 16 * k * 0.1)) / 8
    r = equilibrium_ice("N2O4 <=> 2 NO2", k, {"N2O4": 0.1})["result"]
    assert r["NO2"] == pytest.approx(2 * x, rel=1e-10)
    assert r["N2O4"] == pytest.approx(0.1 - x, rel=1e-10)


def test_reverse_direction_haber():
    r = equilibrium_ice("N2 + 3 H2 <=> 2 NH3", 0.5, {"NH3": 1.0})
    c = r["result"]
    assert r["direction"] == "reverse"
    assert c["NH3"] ** 2 / (c["N2"] * c["H2"] ** 3) == pytest.approx(0.5, rel=1e-10)
    assert c["H2"] == pytest.approx(3 * c["N2"])


def test_solids_excluded_kp():
    r = equilibrium_ice("CaCO3(s) <=> CaO(s) + CO2(g)", 0.25, {}, kind="Kp")
    assert r["result"] == {"CO2": pytest.approx(0.25)}


@pytest.mark.parametrize("k", [1e30, 1e-30])
def test_extreme_k_keeps_precision(k):
    c = equilibrium_ice("A <=> B", k, {"A": 0.1})["result"]
    assert c["B"] / c["A"] == pytest.approx(k, rel=1e-6)
    assert c["A"] + c["B"] == pytest.approx(0.1)


def test_weak_acid_via_ice():
    # Acetic acid 0.1 M, Ka 1.8e-5 (no water): x^2/(0.1-x) = Ka
    ka = 1.8e-5
    c = equilibrium_ice("CH3COOH <=> H+ + CH3COO-", ka, {"CH3COOH": 0.1})["result"]
    assert c["H+"] == pytest.approx((-ka + math.sqrt(ka * ka + 0.4 * ka)) / 2, rel=1e-10)


def test_ice_validation():
    with pytest.raises(ValueError):
        equilibrium_ice("A <=> B", -1, {"A": 1})
    with pytest.raises(ValueError, match="Unknown species"):
        equilibrium_ice("A <=> B", 1, {"C": 1})
    with pytest.raises(ValueError, match="No reaction"):
        equilibrium_ice("A + B <=> C", 1, {"A": 1})


def test_kc_to_kp_haber():
    # Kp = Kc (RT)^-2 for N2 + 3H2 <=> 2NH3
    r = kc_kp_convert(0.5, 673, equation="N2(g) + 3 H2(g) <=> 2 NH3(g)")
    assert r["delta_n"] == -2
    assert r["result"] == pytest.approx(0.5 * (0.08314462618 * 673) ** -2)


def test_kp_to_kc_ignores_solids():
    r = kc_kp_convert(0.25, 1100, from_kind="Kp", equation="CaCO3(s) <=> CaO(s) + CO2(g)")
    assert r["delta_n"] == 1
    assert r["result"] == pytest.approx(0.25 / (0.08314462618 * 1100))
    assert r["to_kind"] == "Kc"


def test_kc_kp_round_trip():
    kp = kc_kp_convert(3.2, 500, delta_n=1)["result"]
    assert kc_kp_convert(kp, 500, from_kind="Kp", delta_n=1)["result"] == pytest.approx(3.2)
