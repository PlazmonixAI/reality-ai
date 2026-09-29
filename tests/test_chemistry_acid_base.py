import pytest

from app.modules.chemistry.acid_base import ph


def test_strong_acid():
    r = ph("strong_acid", 0.01)
    assert r["result"] == pytest.approx(2.0, abs=1e-6)
    assert r["pOH"] == pytest.approx(12.0, abs=1e-6)


def test_very_dilute_strong_acid_includes_water():
    # 1e-8 M HCl is slightly acidic (6.98), not basic (8)
    assert ph("strong_acid", 1e-8)["result"] == pytest.approx(6.978, abs=1e-3)


def test_strong_base_with_equivalents():
    # 0.05 M Ba(OH)2 -> [OH-] = 0.1 -> pH 13
    assert ph("strong_base", 0.05, equivalents=2)["result"] == pytest.approx(13.0, abs=1e-6)


def test_acetic_acid():
    r = ph("weak_acid", 0.1, ka=1.8e-5)
    assert r["result"] == pytest.approx(2.875, abs=2e-3)
    assert r["percent_ionised"] == pytest.approx(1.33, abs=0.01)


def test_ammonia():
    assert ph("weak_base", 0.1, kb=1.8e-5)["result"] == pytest.approx(11.125, abs=2e-3)


def test_pka_and_ka_agree():
    assert ph("weak_acid", 0.05, pka=4.76)["result"] == pytest.approx(
        ph("weak_acid", 0.05, ka=10 ** -4.76)["result"])


def test_extremely_dilute_weak_acid_near_neutral():
    assert ph("weak_acid", 1e-9, pka=4.76)["result"] == pytest.approx(7.0, abs=0.01)


def test_ph_plus_poh_is_14():
    r = ph("weak_base", 0.02, pkb=4.2)
    assert r["result"] + r["pOH"] == pytest.approx(14)


@pytest.mark.parametrize("kwargs", [
    {"kind": "neutral", "concentration": 0.1},
    {"kind": "strong_acid", "concentration": 0},
    {"kind": "weak_acid", "concentration": 0.1},
    {"kind": "weak_acid", "concentration": 0.1, "ka": 1e-5, "pka": 5},
    {"kind": "weak_acid", "concentration": 0.1, "ka": 1e-5, "equivalents": 2},
])
def test_ph_validation(kwargs):
    with pytest.raises(ValueError):
        ph(**kwargs)
