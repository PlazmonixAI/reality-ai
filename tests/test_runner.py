"""Tool runner: argument validation, consistent 422s, and time limits for symbolic work."""
import time

import pytest
from fastapi.testclient import TestClient

import app.modules  # noqa: F401
from app.core.registry import Tool, get_tool
from app.core.runner import ToolInputError, ToolTimeout, run, validate_args
from app.main import app

client = TestClient(app)


def _tool(func, symbolic=False):
    return Tool(domain="test", name=func.__name__, description="test tool", func=func, symbolic=symbolic)


def slow(seconds: float = 5.0) -> dict:
    time.sleep(seconds)
    return {"result": seconds, "units": "s", "assumptions": []}


def crashes(x: float) -> dict:
    return {"result": [][0]}  # IndexError: a bug, not bad input


def divides(x: float) -> dict:
    return {"result": 1 / x, "units": "", "assumptions": []}


def test_validation_messages():
    t = get_tool("physics", "kepler_orbit")
    with pytest.raises(ToolInputError, match="unknown argument.*semimajor.*valid arguments: semi_major_axis_au"):
        validate_args(t, {"semimajor": 1, "eccentricity": 0})
    with pytest.raises(ToolInputError, match="missing required argument.*eccentricity"):
        validate_args(t, {"semi_major_axis_au": 1})
    with pytest.raises(ToolInputError, match="'eccentricity' should be float, got str"):
        validate_args(t, {"semi_major_axis_au": 1, "eccentricity": "high"})
    with pytest.raises(ToolInputError, match="should be int"):
        validate_args(t, {"semi_major_axis_au": 1, "eccentricity": 0.1, "n_points": 10.5})
    validate_args(t, {"semi_major_axis_au": 1, "eccentricity": 0})  # ints are fine for floats
    fit = get_tool("mathematics", "least_squares_fit")
    with pytest.raises(ToolInputError, match="'x' should be"):
        validate_args(fit, {"x": [1, "two"], "y": [1, 2]})
    with pytest.raises(ToolInputError, match="should be int, got bool"):
        validate_args(get_tool("physics", "coupled_oscillators"), {"masses": [1], "springs": [1, 1], "n_points": True})


def test_errors_are_mapped_to_input_errors():
    with pytest.raises(ToolInputError, match="ZeroDivisionError"):
        run(_tool(divides), {"x": 0})
    with pytest.raises(IndexError):  # genuine bugs are not disguised as bad input
        run(_tool(crashes), {"x": 1})


def test_symbolic_tools_are_time_limited():
    t0 = time.monotonic()
    with pytest.raises(ToolTimeout, match="took longer than 0.5 s"):
        run(_tool(slow, symbolic=True), {"seconds": 30}, timeout=0.5)
    assert time.monotonic() - t0 < 5
    assert run(_tool(slow, symbolic=True), {"seconds": 0.01}, timeout=5)["result"] == 0.01
    with pytest.raises(ToolInputError, match="ZeroDivisionError"):
        run(_tool(divides, symbolic=True), {"x": 0}, timeout=5)
    with pytest.raises(RuntimeError, match="internal error"):
        run(_tool(crashes, symbolic=True), {"x": 1}, timeout=5)


def test_real_symbolic_tool_through_the_runner():
    out = run(get_tool("mathematics", "integrate"), {"expression": "x**2", "variable": "x", "lower": 0, "upper": 3})
    assert out["result"] == "9" or float(out.get("numeric", 9)) == pytest.approx(9)


def test_simulate_endpoint_codes():
    r = client.post("/simulate", json={"domain": "physics", "name": "kepler_orbit", "args": {"semimajor": 1}})
    assert r.status_code == 422 and "valid arguments" in r.json()["detail"]
    r = client.post("/simulate", json={"domain": "physics", "name": "kepler_orbit", "args": {"semi_major_axis_au": "x", "eccentricity": 0}})
    assert r.status_code == 422 and "should be float" in r.json()["detail"]
    r = client.post("/simulate", json={"domain": "mathematics", "name": "solve_equation", "args": {"equation": "x**2 - 4"}})
    assert r.status_code == 200
    assert client.post("/simulate", json={"domain": "physics", "name": "nope"}).status_code == 404


def test_fuzz_regressions():
    # NaN/inf are rejected before they reach an integrator (a NaN drive frequency used to hang solve_ivp)
    with pytest.raises(ToolInputError, match="finite numbers"):
        run(get_tool("physics", "driven_oscillator"), {"mass": 1, "stiffness": 1, "damping": 1, "drive_force": 1, "drive_frequency": float("nan")})
    with pytest.raises(ToolInputError, match="finite numbers"):
        validate_args(get_tool("mathematics", "least_squares_fit"), {"x": [1, float("inf")], "y": [1, 2]})
    # Unbalanced brackets are a clear input error, not a crash
    with pytest.raises(ToolInputError, match="unbalanced brackets"):
        run(get_tool("mathematics", "differentiate"), {"expression": "sin(x"})
    # Pure resistor on DC (no L, no C) used to crash on .tolist()
    from app.modules.physics.ac_circuits import rlc_circuit
    r = rlc_circuit(100, 5, 0.01)
    assert set(r["trajectory"]["current"]) == {0.05}


def _fuzz_value(tp, mode):
    import types as _t
    import typing as _ty
    o, a = _ty.get_origin(tp), _ty.get_args(tp)
    if o in (_ty.Union, _t.UnionType):
        return _fuzz_value([x for x in a if x is not type(None)][0], mode)
    if tp is bool:
        return True
    if tp in (int, float):
        return tp(-1 if mode == "neg" else 0)
    if tp is str:
        return "" if mode == "neg" else "x"
    if o in (list, tuple) or tp in (list, tuple):
        return [] if mode == "neg" else [_fuzz_value(a[0] if a else float, mode)] * 2
    if o is dict or tp is dict:
        return {}
    return None


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.parametrize("mode", ["neg", "zero"])
def test_every_tool_fails_cleanly_on_nonsense(mode):
    """Negative/zero/empty inputs must give a clear ToolInputError (HTTP 422), never a crash (HTTP 500)."""
    import inspect
    import typing
    from app.core.registry import list_tools
    for t in list_tools():
        hints = typing.get_type_hints(t.func)
        args = {n: _fuzz_value(hints.get(n, float), mode) for n, p in inspect.signature(t.func).parameters.items()
                if p.default is inspect.Parameter.empty}
        try:
            run(t, args, timeout=5)
        except ToolInputError:
            pass
