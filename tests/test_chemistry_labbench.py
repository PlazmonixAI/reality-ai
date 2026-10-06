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
        if any(HF[k] is None for k in list(r["products"]) + list(r["reactants"])):
            assert r["dh"] is None, r["name"]  # a complex or organic species with no tabulated ΔHf
            continue
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


def run(vessels, actions=(), dt=1.0):
    return lab_step(vessels, list(actions), dt)["result"]


def test_delivery_tube_carries_co2_into_limewater():
    res = run([{"id": "gen", "kind": "boiling_tube", "gas_to": "lw"}, {"id": "lw", "kind": "test_tube"}],
              [{"type": "add", "vessel": "gen", "chemical": "marble", "amount": 1.0}, {"type": "add", "vessel": "gen", "chemical": "hcl", "amount": 5},
               {"type": "add", "vessel": "lw", "chemical": "limewater", "amount": 10}], dt=0.5)
    gen, lw = res["vessels"]
    assert gen["gases"] and gen["gases"][0]["piped_to"] == "lw"
    assert lw["solids"] and lw["solids"][0]["species"] == "CaCO3(s)"  # milky
    assert any(e["reaction"] == "Carbon dioxide and limewater" and e["vessel"] == "lw" for e in res["events"])
    # keep bubbling: limewater (2e-4 mol) is used up, then excess CO2 dissolves the chalk again
    for _ in range(10):
        vs = [{"id": v["id"], "kind": v["kind"], "contents": v["contents"], "T": v["T"], **({"gas_to": "lw"} if v["id"] == "gen" else {})}
              for v in res["vessels"]]
        res = run(vs, dt=3)
    assert res["vessels"][1]["contents"].get("CaCO3(s)", 0) < 1e-6 and res["vessels"][1]["contents"].get("Ca(HCO3)2(aq)", 0) > 1e-4


def test_gas_jar_collects_oxygen_and_relights_a_glowing_splint():
    res = run([{"id": "gen", "kind": "conical", "gas_to": "jar"}, {"id": "jar", "kind": "gas_jar"}],
              [{"type": "add", "vessel": "gen", "chemical": "h2o2", "amount": 20}, {"type": "add", "vessel": "gen", "chemical": "mno2", "amount": 0.5}], dt=20)
    jar = res["vessels"][1]
    held = jar["contents"]["O2(g)"]
    assert held == pytest.approx(250 / V_M, rel=1e-3)  # full: 0.0102 mol in 250 mL; the rest spilled out
    res = run([{"id": "jar", "kind": "gas_jar", "contents": jar["contents"]}], [{"type": "test", "vessel": "jar", "test": "glowing_splint"}])
    assert "back into flame" in res["tests"][0]["result"]


def test_thiocyanate_and_copper_ammine_colours():
    res = bench({"type": "add", "chemical": "fecl3", "amount": 5}, {"type": "add", "chemical": "kscn", "amount": 5})
    v = res["vessels"][0]
    r, g, b = (int(v["liquid_colour"][i:i + 2], 16) for i in (1, 3, 5))
    assert r > 150 and g < 100 and b < 100  # blood red
    assert res["events"][0]["delta_h_kj_per_mol"] is None  # Fe(SCN)3 has no tabulated enthalpy of formation
    res = bench({"type": "add", "chemical": "cuso4", "amount": 5}, {"type": "add", "chemical": "ammonia", "amount": 1}, dt=0.01)
    assert any(s["species"] == "Cu(OH)2(s)" for s in res["vessels"][0]["solids"])
    res = bench({"type": "add", "chemical": "cuso4", "amount": 5}, {"type": "add", "chemical": "ammonia", "amount": 15}, dt=20)
    v = res["vessels"][0]
    assert v["contents"].get("Cu(OH)2(s)", 0) < 1e-6 and v["contents"]["Cu(NH3)4(OH)2(aq)"] == pytest.approx(0.0025, rel=1e-3)
    r, g, b = (int(v["liquid_colour"][i:i + 2], 16) for i in (1, 3, 5))
    assert b > 150 and r < 80  # deep blue


def test_flame_tests_litmus_and_ph_paper():
    for chem, word in (("salt", "golden yellow"), ("srcl2", "crimson"), ("licl", "crimson red")):
        res = bench({"type": "add", "chemical": chem, "amount": 0.5}, {"type": "test", "test": "flame"}, kind="watch_glass")
        assert word in res["tests"][0]["result"]
    res = bench({"type": "add", "chemical": "bacl2", "amount": 2}, {"type": "test", "test": "flame"})
    assert "apple green" in res["tests"][0]["result"]
    res = bench({"type": "add", "chemical": "naoh", "amount": 10}, {"type": "test", "test": "litmus_red"}, {"type": "test", "test": "ph_paper"})
    assert "turns blue" in res["tests"][0]["result"] and res["tests"][1]["ph"] == 14
    res = bench({"type": "add", "chemical": "hcl", "amount": 10}, {"type": "test", "test": "litmus_red"})
    assert "does not change" in res["tests"][0]["result"]
    res = bench({"type": "add", "chemical": "zinc", "amount": 1}, {"type": "add", "chemical": "hcl", "amount": 10},
                {"type": "test", "test": "lighted_splint"}, kind="test_tube")
    assert "pop" in res["tests"][0]["result"]


def test_filter_leaves_the_precipitate_on_the_paper():
    res = run([{"id": "a", "kind": "beaker"}, {"id": "b", "kind": "conical"}],
              [{"type": "add", "vessel": "a", "chemical": "agno3", "amount": 20}, {"type": "add", "vessel": "a", "chemical": "nacl_aq", "amount": 10}])
    a = res["vessels"][0]
    res = run([{"id": "a", "kind": "beaker", "contents": a["contents"]}, {"id": "b", "kind": "conical"}], [{"type": "filter", "from": "a", "to": "b"}])
    a, b = res["vessels"]
    assert set(a["contents"]) == {"AgCl(s)"} and a["contents"]["AgCl(s)"] == pytest.approx(0.002, rel=1e-4)
    assert "AgCl(s)" not in b["contents"] and b["contents"]["NaNO3(aq)"] == pytest.approx(0.002, rel=1e-4)


def test_evaporating_salt_water_leaves_crystals():
    res = bench({"type": "add", "chemical": "nacl_aq", "amount": 10}, kind="dish", heat=1.0, dt=60)
    res = again(res, 6, 60, heat=1.0)
    v = res["vessels"][0]
    assert "H2O(l)" not in v["contents"]
    assert v["contents"]["NaCl(s)"] == pytest.approx(0.01, rel=1e-4)  # 0.585 g of salt back


def test_concentrated_sulphuric_acid_dilution_and_sugar():
    res = bench({"type": "add", "chemical": "water", "amount": 50}, {"type": "add", "chemical": "conc_h2so4", "amount": 2}, dt=20)
    v = res["vessels"][0]
    n = 2 * 1.84 / 98.079
    assert v["contents"]["H2SO4(aq)"] == pytest.approx(n, rel=1e-3) and v["T"] > 30  # ΔH ≈ −96 kJ/mol: it gets hot
    res = bench({"type": "add", "chemical": "sugar", "amount": 5}, {"type": "add", "chemical": "conc_h2so4", "amount": 5}, dt=60)
    assert res["vessels"][0]["contents"].get("C(s)", 0) > 0.1
    assert "C12H22O11(aq)" not in res["vessels"][0]["contents"]


def test_starch_turns_blue_black_with_iodine():
    res = bench({"type": "add", "chemical": "water", "amount": 20}, {"type": "add", "chemical": "starch"},
                {"type": "add", "chemical": "iodine", "amount": 1})
    r, g, b = (int(res["vessels"][0]["liquid_colour"][i:i + 2], 16) for i in (1, 3, 5))
    assert r < 60 and g < 60 and b < 110


def test_fehling_iodoform_and_ester():
    res = bench({"type": "add", "chemical": "fehling_a", "amount": 2}, {"type": "add", "chemical": "fehling_b", "amount": 2}, dt=0.5, kind="test_tube")
    v = res["vessels"][0]
    assert "Cu(OH)2(s)" not in v["contents"]  # the tartrate keeps the copper in solution
    res = bench({"type": "add", "chemical": "fehling_a", "amount": 2}, {"type": "add", "chemical": "fehling_b", "amount": 2},
                {"type": "add", "chemical": "glucose", "amount": 2}, kind="test_tube", heat=1.0, dt=60)
    assert res["vessels"][0]["contents"].get("Cu2O(s)", 0) > 1e-5 and any(e["reaction"] == "Fehling's test" for e in res["events"])
    res = bench({"type": "add", "chemical": "water", "amount": 5}, {"type": "add", "chemical": "ethanol", "amount": 0.5},
                {"type": "add", "chemical": "iodine", "amount": 10}, {"type": "add", "chemical": "naoh", "amount": 3}, kind="boiling_tube", heat=0.6, dt=60)
    assert res["vessels"][0]["contents"].get("CHI3(s)", 0) > 0
    r = next(r for r in REACTIONS if r["name"] == "Esterification (ethyl ethanoate)")
    assert r["dh"] == pytest.approx(-479.3 + -285.83 - (-484.3 + -277.69), abs=0.05)
    res = bench({"type": "add", "chemical": "glacial_acetic", "amount": 3}, {"type": "add", "chemical": "ethanol", "amount": 3},
                {"type": "add", "chemical": "conc_h2so4", "amount": 0.5}, kind="boiling_tube", heat=0.5, dt=120)
    assert res["vessels"][0]["contents"].get("CH3COOC2H5(l)", 0) > 0


def test_rinsing_a_burette_keeps_the_titrant_strength():
    def titrant_strength(prep):
        r = lab_step([{"id": "b", "kind": "burette"}], [prep, {"type": "add", "vessel": "b", "chemical": "naoh", "amount": 20}], 0)["result"]
        c = r["vessels"][0]["contents"]
        return c["NaOH(aq)"] / (c["H2O(l)"] * 18.015 / 1000)
    washed = titrant_strength({"type": "wash", "vessel": "b"})
    rinsed = titrant_strength({"type": "rinse", "vessel": "b", "chemical": "naoh"})
    assert rinsed == pytest.approx(1.0, rel=1e-5)  # still 1 mol/L
    assert washed == pytest.approx(20 / 20.6, rel=1e-5)  # the 0.6 mL water film dilutes it


def test_gas_cylinder_co2_turns_limewater_milky():
    # 100 mL of 0.02 M limewater holds 2 mmol Ca(OH)2; 24.5 mL of CO2 at 25 °C is 1.0 mmol, so 1.0 mmol CaCO3 (0.100 g) forms
    r = bench({"type": "add", "chemical": "limewater", "amount": 100}, {"type": "gas", "gas": "CO2(g)", "volume_ml": V_M * 1e-3}, dt=2.0)
    v = r["vessels"][0]
    assert v["contents"]["CaCO3(s)"] == pytest.approx(1e-3, rel=1e-3)
    assert v["contents"]["Ca(OH)2(aq)"] == pytest.approx(1e-3, rel=1e-3)
    assert "cylinder" in r["log"][-1]


def test_gas_cylinder_fills_a_gas_jar_and_checks_input():
    r = bench({"type": "gas", "gas": "O2(g)", "volume_ml": 100}, kind="gas_jar")
    assert r["vessels"][0]["contents"]["O2(g)"] == pytest.approx(100 / V_M, rel=1e-5)
    with pytest.raises(ValueError):
        bench({"type": "gas", "gas": "Xe(g)", "volume_ml": 10})
    with pytest.raises(ValueError):
        bench({"type": "gas", "gas": "O2(g)", "volume_ml": -1})


def test_reagent_bottle_pours_like_any_vessel():
    r = lab_step([{"id": "b", "kind": "reagent_bottle"}, {"id": "t", "kind": "test_tube"}],
                 [{"type": "add", "vessel": "b", "chemical": "hcl", "amount": 250}, {"type": "pour", "from": "b", "to": "t", "volume_ml": 5}], 0)["result"]
    b, t = r["vessels"]
    assert b["volume_ml"] == pytest.approx(245, rel=1e-3) and t["volume_ml"] == pytest.approx(5, rel=1e-3)
    assert {g["id"] for g in lab_catalog()["result"]["gases"]} >= {"CO2(g)", "O2(g)", "H2(g)"}
