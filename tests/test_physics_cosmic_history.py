import math

import pytest

from app.modules.physics.cosmic_history import _gstar, _mev_of_t, _t_of_mev, cosmic_history
from app.modules.physics.universe import cosmology


@pytest.fixture(scope="module")
def hist():
    return cosmic_history()["result"]


def epoch(h, key):
    return next(e for e in h["epochs"] if e["key"] == key)


def test_planck_scale(hist):
    assert hist["planck_time_s"] == pytest.approx(5.391e-44, rel=1e-3)
    assert hist["planck_temperature_k"] == pytest.approx(1.4168e32, rel=1e-3)


def test_radiation_era_clock():
    # t ≈ 0.74 s at 1 MeV with g* = 10.75; about 4.5 minutes when deuterium survives (0.07 MeV, g* = 3.36)
    assert _t_of_mev(1.0) == pytest.approx(2.42 / math.sqrt(10.75), rel=0.01)
    assert _t_of_mev(0.07) == pytest.approx(269, rel=0.01)
    assert _gstar(1e7) == pytest.approx(106.75, rel=1e-3) and _gstar(10) == pytest.approx(10.75, rel=1e-3)
    assert _gstar(0.01) == pytest.approx(3.36, rel=1e-3)
    for mev in (1e6, 1000, 1.0, 0.05):
        assert _mev_of_t(_t_of_mev(mev)) == pytest.approx(mev, rel=1e-9)


def test_late_epochs_match_the_cosmology_tool(hist):
    today = epoch(hist, "today")
    ref = cosmology(z=1089.8)["result"]
    assert today["age_years"] / 1e9 == pytest.approx(ref["age_now_gyr"], rel=1e-4)
    cmb = epoch(hist, "cmb")
    assert cmb["age_years"] / 1e9 == pytest.approx(ref["age_then_gyr"], rel=1e-3)
    assert 360_000 < cmb["age_years"] < 390_000          # "380,000 years after the Big Bang"
    assert cmb["temperature_k"] == pytest.approx(2.7255 * 1090.8, rel=1e-6)
    assert hist["observable_universe_diameter_ly"] / 1e9 == pytest.approx(ref["observable_universe_diameter_gly"], rel=2e-3)
    assert cmb["observable_patch_size_ly"] == pytest.approx(hist["observable_universe_diameter_ly"] / 1090.8, rel=1e-6)


def test_equality_and_acceleration(hist):
    eq = epoch(hist, "equality")
    assert eq["redshift"] == pytest.approx(0.3111 / 9.14e-5 - 1, rel=1e-6)    # z_eq ≈ 3400
    acc = epoch(hist, "acceleration")
    assert acc["redshift"] == pytest.approx((2 * (1 - 0.3111 - 9.14e-5) / 0.3111) ** (1 / 3) - 1, rel=1e-6)  # ≈ 0.63
    sun = epoch(hist, "sun")
    assert hist["age_now_years"] - sun["age_years"] == pytest.approx(4.568e9, rel=1e-6)


def test_order_frames_and_colours(hist):
    times = [e["time_s"] for e in hist["epochs"]]
    assert times == sorted(times) and hist["epochs"][0]["key"] == "planck" and hist["epochs"][-1]["key"] == "today"
    f = hist["frames"]
    assert len(f) == 120 and all(a["time_s"] < b["time_s"] for a, b in zip(f, f[1:]))
    assert all(a["temperature_k"] > b["temperature_k"] for a, b in zip(f, f[1:]))  # the universe only cools
    assert epoch(hist, "cmb")["colour"].startswith("#ff")                           # 3,000 K glows orange
    assert epoch(hist, "today")["colour"] is None


def test_bad_input():
    with pytest.raises(ValueError):
        cosmic_history(h0=10)
    with pytest.raises(ValueError):
        cosmic_history(n_frames=5)
