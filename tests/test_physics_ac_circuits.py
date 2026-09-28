import math

import numpy as np
import pytest

from app.modules.physics.ac_circuits import rlc_circuit, rlc_frequency_response


def at(r, key, t):
    return float(np.interp(t, r["trajectory"]["t"], r["trajectory"][key]))


def test_rc_charging_one_time_constant():
    r = rlc_circuit(resistance=1000, capacitance=1e-6, voltage=5, duration=0.005)
    assert r["result"]["time_constant"] == pytest.approx(1e-3)
    assert at(r, "v_capacitor", 1e-3) == pytest.approx(5 * (1 - math.exp(-1)), rel=1e-6)
    assert at(r, "current", 0) == pytest.approx(5 / 1000)


def test_rl_current_rise():
    r = rlc_circuit(resistance=10, inductance=0.5, voltage=12, duration=0.25)
    assert r["result"]["time_constant"] == pytest.approx(0.05)
    assert at(r, "current", 0.05) == pytest.approx(1.2 * (1 - math.exp(-1)), rel=1e-6)
    assert at(r, "v_inductor", 0) == pytest.approx(12, rel=1e-6)


def test_rlc_underdamped_ringing_frequency():
    R, L, C = 5, 0.1, 1e-4
    r = rlc_circuit(resistance=R, inductance=L, capacitance=C, voltage=1, duration=0.2, n_points=20000)
    wd = math.sqrt(1 / (L * C) - (R / (2 * L)) ** 2)
    assert r["result"]["damped_frequency_hz"] == pytest.approx(wd / (2 * math.pi))
    i, t = np.array(r["trajectory"]["current"]), np.array(r["trajectory"]["t"])
    z = t[1:][np.diff(np.sign(i)) != 0]
    assert 2 * np.mean(np.diff(z)) == pytest.approx(2 * math.pi / wd, rel=1e-3)
    assert r["trajectory"]["v_capacitor"][-1] == pytest.approx(1, abs=0.05)


def test_kirchhoff_voltage_law_holds():
    r = rlc_circuit(resistance=20, inductance=0.05, capacitance=2e-5, voltage=3, source="ac", frequency=100, duration=0.05)
    tr = r["trajectory"]
    total = np.array(tr["v_resistor"]) + np.array(tr["v_inductor"]) + np.array(tr["v_capacitor"])
    assert np.allclose(total, tr["v_source"])


def test_ac_rc_steady_state_amplitude():
    R, C, f, V = 1000, 1e-6, 200, 1
    r = rlc_circuit(resistance=R, capacitance=C, voltage=V, source="ac", frequency=f, duration=0.05, n_points=20000)
    w = 2 * math.pi * f
    vc = np.array(r["trajectory"]["v_capacitor"])[-5000:]
    assert vc.max() == pytest.approx(V / math.sqrt(1 + (w * R * C) ** 2), rel=1e-3)


def test_frequency_response_resonance():
    r = rlc_frequency_response(resistance=10, inductance=0.01, capacitance=1e-6, voltage=2, n_points=4001)
    res = r["result"]
    assert res["resonant_frequency_hz"] == pytest.approx(1 / (2 * math.pi * math.sqrt(1e-8)))
    assert res["quality_factor"] == pytest.approx(10)
    f, i = np.array(r["curve"]["frequency"]), np.array(r["curve"]["current"])
    assert i.max() == pytest.approx(0.2, rel=1e-4)
    half = f[i >= 0.2 / math.sqrt(2)]
    assert half[-1] - half[0] == pytest.approx(res["bandwidth_hz"], rel=2e-2)


def test_rlc_validation():
    with pytest.raises(ValueError):
        rlc_circuit(resistance=0, voltage=1, duration=1)
    with pytest.raises(ValueError):
        rlc_frequency_response(resistance=1, inductance=0, capacitance=1e-6)
