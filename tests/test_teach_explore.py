"""ASM Teach Equation Lab: identities, impossible equations, exact solutions, curves, dimensions and chemistry."""
import math

import pytest

import app.modules  # noqa: F401  (registers tools)
from app.modules.teach.explore import teach_explore


def R(text, **kw):
    return teach_explore(text, **kw)["result"]


@pytest.mark.parametrize("text", ["sin(x)^2 + cos(x)^2 = 1", "sin(2x) = 2 sin(x) cos(x)", "cos(x)^2 - sin(x)^2 = cos(2x)",
                                  "1/(1-sin(x)) + 1/(1+sin(x)) = 2 sec(x)^2", "(a+b)^2 = a^2 + 2ab + b^2", "tan(x) = sin(x)/cos(x)"])
def test_identities_are_proved(text):
    r = R(text)
    assert r["kind"] == "identity" and r["valid"]
    assert r["steps"][-1].startswith("= 0")


@pytest.mark.parametrize("text", ["sin(x)^2 + cos(x)^2 = 2", "(a+b)^2 = a^2 + b^2 + 2ab + 1"])
def test_impossible_identities_are_caught(text):
    r = R(text)
    assert r["kind"] == "contradiction" and not r["valid"]


def test_arithmetic_statement():
    assert R("2 + 2 = 4")["valid"] and not R("2 + 2 = 5")["valid"]


def test_trig_general_solution():
    r = R("sin(x) = 1/2")
    joined = " ".join(r["solutions"])
    assert r["valid"] and "π/6" in joined and "5π/6" in joined and "n ∈ ℤ" in joined
    assert any(abs(m["x"] - math.pi / 6) < 1e-4 for m in r["plot"]["marks"])


def test_no_real_solution_explains_range():
    r = R("sin(x) = 2")
    assert not r["valid"] and "[−1, 1]" in r["verdict"]


def test_quadratic_roots_and_general_formula():
    r = R("x^2 - 5x + 6 = 0")
    assert r["solutions"] == ["x = 2", "x = 3"]
    g = R("a x^2 + b x + c = 0")
    assert any("√" in s and "2a" in s for s in g["steps"])
    assert g["solutions"] == ["x = 1", "x = 2"]  # defaults a = 1, b = -3, c = 2
    assert R("a x^2 + b x + c = 0", values={"a": 1, "b": 0, "c": -9})["solutions"] == ["x = −3", "x = 3"]


def test_function_study():
    r = R("y = x^3 - 3x")
    assert r["derivative"] == "3x² − 3"
    assert [p["x"] for p in r["turning_points"]] == pytest.approx([-1, 1])
    assert r["zeros"] == pytest.approx([-math.sqrt(3), 0, math.sqrt(3)], abs=1e-5)
    t = R("y = tan(x)")
    assert t["period"] == "π" and t["zeros"] == pytest.approx([-math.pi, 0, math.pi], abs=1e-5)  # poles are not zeros


def test_implicit_curves_and_conics():
    c = R("x^2 + y^2 = 4")
    assert c["conic"] == "a circle" and c["segments"]
    for x0, y0, x1, y1 in c["segments"][:50]:
        assert math.hypot(x0, y0) == pytest.approx(2, abs=0.05)
    assert R("x^2/4 + y^2/9 = 1")["conic"] == "an ellipse"
    assert R("x^2 - y^2 = 1")["conic"] == "a hyperbola"
    assert R("y^2 = 4x")["kind"] == "curve" and R("y^2 = 4x")["conic"] == "a parabola"
    assert not R("x^2 + y^2 = -1")["valid"]


def test_surface_contours():
    r = R("z = sin(x)*cos(y)")
    assert r["kind"] == "surface" and len(r["contours"]) == 9 and r["contours"][4]["segments"]


def test_physics_formula_value_and_dimensions():
    r = R("T = 2π√(L/g)", values={"L": 1, "g": 9.81})
    assert r["valid"] and r["value"] == pytest.approx(2 * math.pi * math.sqrt(1 / 9.81), rel=1e-5)
    assert r["dimensions"]["consistent"] and r["dimensions"]["reading"]["T"] == "time period"
    p = R("PV = nRT", values={"n": 1, "R": 8.314, "T": 273.15, "V": 0.0224})
    assert p["value"] == pytest.approx(8.314 * 273.15 / 0.0224, rel=1e-4)  # about one atmosphere
    assert p["dimensions"]["reading"]["T"] == "temperature"


@pytest.mark.parametrize("text", ["F = m*v", "v = u + a", "E = m*c", "s = u*t + a*t"])
def test_dimensionally_wrong_formulas_are_rejected(text):
    r = R(text)
    assert r["kind"] == "formula" and not r["valid"] and "cannot be right" in r["verdict"]


@pytest.mark.parametrize("text", ["v = u + a*t", "s = u*t + a*t^2/2", "E = m*c^2", "F = m*a", "v^2 = u^2 + 2*a*s"])
def test_correct_formulas_pass(text):
    assert R(text)["valid"]


def test_chemistry_balancing_and_impossible_reactions():
    r = R("H2 + O2 -> H2O")
    assert r["valid"] and r["coefficients"] == {"H2": 2, "O2": 1, "H2O": 2}
    assert R("Fe + O2 = Fe2O3")["coefficients"] == {"Fe": 4, "O2": 3, "Fe2O3": 2}
    assert R("C3H8 + O2 → CO2 + H2O")["coefficients"] == {"C3H8": 1, "O2": 5, "CO2": 3, "H2O": 4}
    bad = R("H2 + O2 -> NaCl")
    assert not bad["valid"] and "only on the left" in bad["verdict"]


def test_bad_input_is_a_clear_error():
    with pytest.raises(ValueError):
        teach_explore("")
    with pytest.raises(ValueError):
        teach_explore("sin(x = 2")


@pytest.mark.parametrize("text,kind", [("sin²x + cos²x = 1", "identity"), ("sin 2x = 2 sin x cos x", "identity"),
                                       ("sinx = 1/2", "equation"), ("y = sin x + cos x", "function")])
def test_board_notation_for_functions(text, kind):
    assert R(text)["kind"] == kind


def test_euler_number_prints_as_e():
    assert R("log x = 1")["solutions"] == ["x = e"]
