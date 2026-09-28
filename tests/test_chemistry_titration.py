import math

import numpy as np
import pytest

from app.modules.chemistry.titration import buffer_ph, titration_curve


def test_strong_acid_strong_base():
    r = titration_curve("strong_acid", 0.1, 25, 0.1)
    res = r["result"]
    assert res["equivalence_volume"] == pytest.approx(25)
    assert res["equivalence_ph"] == pytest.approx(7.0, abs=1e-6)
    assert res["initial_ph"] == pytest.approx(1.0, abs=1e-6)
    # 12.5 mL added: [H+] = 0.1*12.5 / 37.5
    assert res["half_equivalence_ph"] == pytest.approx(-math.log10(1.25 / 37.5), abs=1e-6)
    assert "bromothymol blue" in res["indicators"]


def test_weak_acid_half_equivalence_is_pka():
    res = titration_curve("weak_acid", 0.1, 25, 0.1, pka=4.76)["result"]
    assert res["half_equivalence_ph"] == pytest.approx(4.76, abs=0.01)
    # 0.05 M acetate at equivalence: pOH = (pKb - log C)/2
    assert res["equivalence_ph"] == pytest.approx(14 - 0.5 * (14 - 4.76 - math.log10(0.05)), abs=0.01)
    assert res["indicators"] == ["phenolphthalein"]


def test_weak_base_with_strong_acid():
    res = titration_curve("weak_base", 0.1, 25, 0.1, pkb=4.75)["result"]
    assert res["half_equivalence_ph"] == pytest.approx(14 - 4.75, abs=0.01)
    assert res["equivalence_ph"] == pytest.approx(0.5 * (14 - 4.75 - math.log10(0.05)), abs=0.01)


def test_curve_steepest_at_equivalence():
    r = titration_curve("weak_acid", 0.05, 20, 0.1, pka=4.2, n_points=801)
    v, slope = np.array(r["curve"]["volume"]), np.array(r["curve"]["slope"])
    assert v[np.argmax(slope)] == pytest.approx(10, abs=0.1)


def test_buffer_equal_parts_and_added_acid():
    assert buffer_ph(0.1, 0.1, 4.76)["result"] == pytest.approx(4.76, abs=0.01)
    r = buffer_ph(0.1, 0.1, 4.76, volume=1, added_acid=0.01)
    assert r["result"] == pytest.approx(4.76 + math.log10(0.09 / 0.11), abs=0.005)
    assert r["henderson_hasselbalch"] == pytest.approx(4.76 + math.log10(0.09 / 0.11))


def test_buffer_capacity_matches_numerical_derivative():
    r0 = buffer_ph(0.1, 0.1, 4.76)
    d = 1e-5
    ph1 = buffer_ph(0.1, 0.1, 4.76, added_base=d)["result"]
    assert d / (ph1 - r0["result"]) == pytest.approx(r0["buffer_capacity"], rel=1e-3)


def test_titration_validation():
    with pytest.raises(ValueError):
        titration_curve("weak_acid", 0.1, 25, 0.1)
    with pytest.raises(ValueError):
        titration_curve("salt", 0.1, 25, 0.1)
