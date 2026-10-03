"""Virtual chemistry lab: balanced equations, Hess's-law enthalpies, stoichiometric amounts, heat balance, pH and
indicator colours, gases with their volumes, boiling."""
import math

import pytest

from app.modules.chemistry.formula import element_counts
from app.modules.chemistry.labbench import CHEMICALS, HF, REACTIONS, lab_catalog, lab_step

V_M = 8.314462618 * 298.15 / 101325 * 1e6  # mL per mole of ideal gas at 25 °C, 1 atm (24,465 mL)


def bench(*actions, kind="beaker", heat=0.0, dt=1.0):
    return lab_step([{"id": "v", "kind": kind, "heat": heat}], [dict(a, vessel="v") for a in actions], dt)["result"]


def again(res, steps, dt, heat=0.0):
    for _ in range(steps):
        v = res["vessels"][0]
        res = lab_step([{"id": "v", "kind": v["kind"], "contents": v["contents"], "T": v["T"], "indicators": v["indicators"], "heat": heat}], [], dt)["result"]
    return res


def test_every_reaction_conserves_atoms_and_uses_hess_law():
    for r in REACTIONS:
        left, right = {}, {}
        for side, out in ((r["reactants"], left), (r["products"], right)):
            for k, n in side.items():
                for el, m in element_counts(k[: k.rindex("(")]).items():
                    out[el] = out.get(el, 0) + n * m
        assert left == right, r["name"]
        dh = sum(n * HF[k] for k, n in r["products"].items()) - sum(n * HF[k] for k, n in r["reactants"].items())
        assert r["dh"] == pytest.approx(dh), r["name"]
    names = {r["name"] for r in REACTIONS}
    assert {"Sodium and water", "Neutralisation: HCl and NaOH", "Lead nitrate and potassium iodide", "Magnesium burns in air"} <= names
    assert len(lab_catalog()["result"]["chemicals"]) == len(CHEMICALS) >= 40


def test_neutralisation_enthalpy_and_temperature_rise():
    r = next(r for r in REACTIONS if r["name"] == "Neutralisation: HCl and NaOH")
    assert r["dh"] == pytest.approx(-55.84, abs=0.01)  # textbook −55.8 to −57 kJ/mol
    res = bench({"type": "add", "chemical": "hcl", "amount": 25}, {"type": "add", "chemical": "naoh", "amount": 50}, dt=0.01)
    v = res["vessels"][0]
    heat_cap = 75 * 4.18 + 100 * 0.84 + 1.0  # 75 mL of solution plus the beaker's glass
    assert v["T"] - 25 == pytest.approx(0.05 * 55840 / heat_cap, rel=0.02)
    assert v["ph"] == pytest.approx(7.0)


def test_sodium_and_water_gives_hydrogen_and_an_alkali():
    res = bench({"type": "add", "chemical": "water", "amount": 100}, {"type": "add", "chemical": "sodium", "amount": 0.2299},
                {"type": "add", "chemical": "phenolphthalein"}, dt=20)
    v = res["vessels"][0]
    h2 = next(g for g in v["gases"] if g["gas"] == "H2")
    assert h2["mol"] == pytest.approx(0.005, rel=2e-3) and h2["volume_ml"] == pytest.approx(0.005 * V_M, rel=2e-3)
    assert "pop" in h2["test"]
    assert v["ph"] == pytest.approx(13.0, abs=0.01)  # 0.01 mol NaOH in 0.1 L
    r, g, b = (int(v["liquid_colour"][i:i + 2], 16) for i in (1, 3, 5))
    assert r > 200 and g < 150  # phenolphthalein pink
    assert v["T"] > 26


def test_precipitate_mass_from_the_limiting_reagent():
    res = bench({"type": "add", "chemical": "pbno3", "amount": 5}, {"type": "add", "chemical": "ki", "amount": 5}, kind="test_tube")
    pbi2 = next(s for s in res["vessels"][0]["solids"] if s["name"] == "PbI2")
    assert pbi2["mass_g"] == pytest.approx(0.0025 / 2 * 461.0, rel=1e-3)  # KI limits: 2 KI per PbI₂
    assert pbi2["colour"] == "#f5c400" and "yellow" in res["events"][0]["observation"]


def test_marble_gives_its_carbon_dioxide_over_time():
    res = bench({"type": "add", "chemical": "hcl", "amount": 50}, {"type": "add", "chemical": "marble", "amount": 2.0018}, dt=10)
    total = sum(g["mol"] for g in res["vessels"][0]["gases"] if g["gas"] == "CO2")
    for _ in range(40):
        res = again(res, 1, 10)
        total += sum(g["mol"] for g in res["vessels"][0]["gases"] if g["gas"] == "CO2")
    assert total == pytest.approx(0.02, rel=0.01)  # 2.0 g CaCO₃ = 0.02 mol → 0.02 mol CO₂


def test_heating_water_boils_at_100_and_boils_away():
    res = bench({"type": "add", "chemical": "water", "amount": 100}, heat=1.0, dt=30)
    res = again(res, 15, 30, heat=1.0)
    v = res["vessels"][0]
    assert v["T"] == pytest.approx(100.0) and v["boiling"] and v["volume_ml"] < 100


def test_dissolving_ammonium_chloride_cools_the_water():
    res = bench({"type": "add", "chemical": "water", "amount": 50}, {"type": "add", "chemical": "ammonium_chloride", "amount": 5}, dt=30)
    res = again(res, 2, 30)
    assert res["vessels"][0]["T"] < 22


def test_heating_blue_vitriol_drives_off_water():
    res = bench({"type": "add", "chemical": "blue_vitriol", "amount": 2.4968}, kind="test_tube", heat=1.0, dt=20)
    res = again(res, 12, 20, heat=1.0)
    v = res["vessels"][0]
    assert v["contents"].get("CuSO4(s)", 0) == pytest.approx(0.01, rel=0.01)


def test_ph_of_standard_solutions():
    assert bench({"type": "add", "chemical": "water", "amount": 90}, {"type": "add", "chemical": "hcl", "amount": 5}, dt=0)["vessels"][0]["ph"] == pytest.approx(-math.log10(0.01 / 0.095), abs=0.01)
    assert bench({"type": "add", "chemical": "acetic", "amount": 100}, dt=0)["vessels"][0]["ph"] == pytest.approx(2.37, abs=0.02)  # 1 M acetic acid
    buf = bench({"type": "add", "chemical": "acetic", "amount": 50}, {"type": "add", "chemical": "naoh", "amount": 25}, dt=0.01)
    assert buf["vessels"][0]["ph"] == pytest.approx(4.74, abs=0.01)  # half-neutralised: pH = pKa


def test_permanganate_is_decolourised_by_iron_ii_in_acid():
    res = bench({"type": "add", "chemical": "kmno4", "amount": 5}, {"type": "add", "chemical": "h2so4", "amount": 5},
                {"type": "add", "chemical": "feso4", "amount": 10}, kind="boiling_tube")
    assert "KMnO4(aq)" not in res["vessels"][0]["contents"] and "decolourised" in res["events"][0]["observation"]


def test_pour_moves_liquid_and_heat():
    res = lab_step([{"id": "a", "kind": "beaker", "contents": {"H2O(l)": 100 / 18.015}, "T": 80}, {"id": "b", "kind": "beaker", "contents": {"H2O(l)": 100 / 18.015}, "T": 20}],
                   [{"type": "pour", "from": "a", "to": "b", "volume_ml": 50}], 0)["result"]
    a, b = res["vessels"]
    assert a["volume_ml"] == pytest.approx(50, rel=1e-3) and b["volume_ml"] == pytest.approx(150, rel=1e-3)
    assert 20 < b["T"] < 80


def test_input_checks():
    with pytest.raises(ValueError):
        lab_step([{"id": "x", "kind": "spaceship"}])
    with pytest.raises(ValueError):
        lab_step([{"id": "x", "kind": "beaker"}], [{"type": "add", "vessel": "x", "chemical": "unobtainium", "amount": 1}])
    with pytest.raises(ValueError):
        lab_step([{"id": "x", "kind": "beaker", "contents": {"Kryptonite(s)": 1}}])
