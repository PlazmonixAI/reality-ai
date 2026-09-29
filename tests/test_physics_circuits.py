import pytest

from app.modules.physics.circuits import dc_circuit


def V(a, b, value, **kw):
    return {"type": "voltage_source", "a": a, "b": b, "value": value, **kw}


def R(a, b, value):
    return {"type": "resistor", "a": a, "b": b, "value": value}


def test_series_divider():
    r = dc_circuit([V("1", "0", 9), R("1", "2", 1000), R("2", "0", 2000)])["result"]
    assert r["node_voltages"]["2"] == pytest.approx(6.0, rel=1e-6)
    assert r["components"][1]["current"] == pytest.approx(0.003, rel=1e-6)
    assert r["components"][0]["current"] == pytest.approx(-0.003, rel=1e-6)   # current leaves the + terminal


def test_parallel_resistors():
    r = dc_circuit([V("a", "g", 12), R("a", "g", 4), R("a", "g", 12)])["result"]
    currents = [c["current"] for c in r["components"][1:]]
    assert currents == pytest.approx([3, 1], rel=1e-6)
    assert r["power_supplied"] == pytest.approx(48, rel=1e-6)


def test_two_source_network():
    # Node x joins 10 V via 1 ohm, 5 V via 2 ohm and ground via 3 ohm: Vx = 12.5 / (1 + 1/2 + 1/3)
    r = dc_circuit([V("p", "0", 10), V("q", "0", 5), R("p", "x", 1), R("q", "x", 2), R("x", "0", 3)])["result"]
    assert r["node_voltages"]["x"] == pytest.approx(12.5 / (1 + 0.5 + 1 / 3), rel=1e-6)


def test_balanced_wheatstone_bridge():
    comps = [V("t", "0", 10), R("t", "a", 100), R("a", "0", 200), R("t", "b", 50), R("b", "0", 100), R("a", "b", 1000)]
    bridge = dc_circuit(comps)["result"]["components"][-1]
    assert abs(bridge["current"]) < 1e-9


def test_power_conservation():
    comps = [V("1", "0", 12, internal_resistance=0.5), R("1", "2", 3), R("2", "0", 6), R("2", "0", 6),
             {"type": "current_source", "a": "2", "b": "0", "value": 0.5}]
    r = dc_circuit(comps)["result"]
    assert r["power_supplied"] == pytest.approx(r["power_dissipated"], rel=1e-6)


def test_internal_resistance_short_circuit():
    r = dc_circuit([V("1", "0", 1.5, internal_resistance=0.3), {"type": "wire", "a": "1", "b": "0"}])["result"]
    assert abs(r["components"][1]["current"]) == pytest.approx(1.5 / (0.3 + 1e-4), rel=1e-6)


def test_current_source_into_resistor():
    r = dc_circuit([{"type": "current_source", "a": "1", "b": "0", "value": 0.002}, R("1", "0", 5000)])["result"]
    assert r["node_voltages"]["1"] == pytest.approx(10, rel=1e-6)


def test_floating_part_has_no_current():
    r = dc_circuit([V("1", "0", 5), R("1", "0", 10), R("1", "dangling", 100)])["result"]
    assert abs(r["components"][2]["current"]) < 1e-9


def test_ideal_source_loop_is_rejected():
    with pytest.raises(ValueError, match="singular"):
        dc_circuit([V("1", "0", 5), V("1", "0", 3)])


@pytest.mark.parametrize("comps", [
    [],
    [{"type": "capacitor", "a": "1", "b": "0", "value": 1}],
    [R("1", "1", 5)],
    [R("1", "0", -5)],
])
def test_circuit_validation(comps):
    with pytest.raises(ValueError):
        dc_circuit(comps)
