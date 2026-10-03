"""ASM Teach: the curriculum catalogue, experiments checked against textbook answers, practice and the board reader."""
import math

import pytest

import app.modules  # noqa: F401
from app.modules.teach.core import BOARDS, CATALOG, SCENES, SUBJECTS, parse_eq, pretty
from app.modules.teach.lab import teach_catalog, teach_experiment, teach_practice, teach_recognize
from tests.helpers import new_client


def out(exp_id, **values):
    return {o["name"]: o["value"] for o in teach_experiment(exp_id, values)["result"]["outputs"]}


def test_catalogue_covers_every_class_and_subject():
    assert len(CATALOG) >= 250
    counts = teach_catalog()["result"]["counts"]
    for cls in ("9", "10", "11", "12"):
        for subject in SUBJECTS:
            assert counts[cls][subject] >= 8, (cls, subject)
    for e in CATALOG.values():
        assert set(e.boards) <= set(BOARDS) and e.scene in SCENES and e.eqs and e.steps, e.id


def test_catalogue_filters():
    r = teach_catalog(cls=10, subject="physics", board="ICSE")["result"]
    assert r["items"] and all(i["class"] == 10 and i["subject"] == "physics" and "ICSE" in i["boards"] for i in r["items"])
    assert any(i["id"] == "p10-lever" for i in r["items"])
    assert not any(i["id"] == "p10-lever" for i in teach_catalog(board="NCERT")["result"]["items"])
    assert [i["id"] for i in teach_catalog(query="pendulum period")["result"]["items"]] == ["p11-pendulum"]
    with pytest.raises(ValueError):
        teach_catalog(cls=8)


def test_every_experiment_computes_at_its_defaults():
    for e in CATALOG.values():
        r = teach_experiment(e.id)["result"]
        assert all(o["value"] is not None and math.isfinite(o["value"]) for o in r["outputs"]), e.id
        if r["graph"]:
            vals = [v for s in r["graph"]["series"] for v in s["values"]]
            assert sum(v is not None for v in vals) > len(vals) // 2, e.id
        for q in e.eqs:
            parse_eq(q)


@pytest.mark.parametrize("exp_id,values,name,expected,rel", [
    ("p11-projectile", {"v0": 20, "th": 45, "g": 9.8}, "R", 40.816, 1e-4),        # v²/g
    ("p11-projectile", {"v0": 20, "th": 45, "g": 9.8}, "H", 10.204, 1e-4),
    ("p11-pendulum", {"L": 1, "g": 9.8}, "T", 2.00709, 1e-5),                     # 2π√(1/9.8)
    ("p10-convex-lens", {"do": 30, "f_l": 10}, "v", 15.0, 1e-9),                   # 1/v = 1/10 − 1/30
    ("p10-convex-lens", {"do": 30, "f_l": 10}, "m", -0.5, 1e-9),
    ("p10-concave-mirror", {"do": 30, "f_m": 15}, "v", -30.0, 1e-9),               # object at C
    ("p10-parallel", {"V": 12, "R1": 4, "R2": 6, "R3": 12}, "Rp", 2.0, 1e-9),
    ("p10-ohm", {"V": 6, "R": 12}, "I", 0.5, 1e-9),
    ("p12-bohr", {"n": 1, "Z": 1}, "E", -13.6057, 1e-5),
    ("p12-spectrum", {"n1": 2, "n2": 3}, "lam", 656.11, 1e-4),                     # H-alpha (Rydberg, infinite nuclear mass)
    ("p12-photoelectric", {"lam": 300, "phi": 2.3}, "Kmax", 1.8328, 1e-4),
    ("p12-de-broglie", {"V": 100}, "lam", 0.12264, 1e-3),                          # 1.227/√V nm
    ("p11-escape", {"M_e": 1, "R_e": 1}, "ve", 11.186, 1e-3),
    ("p11-orbit", {"h": 400}, "v", 7672.6, 1e-3),
    ("p11-carnot", {"Th": 600, "Tc": 300, "Qh": 1000}, "eta", 50.0, 1e-9),
    ("p11-vrms", {"T": 300, "M": 28}, "v_rms", 516.9, 1e-3),                        # N₂ at 300 K
    ("p9-echo", {"t": 2, "v": 343}, "d", 343.0, 1e-9),
    ("p12-lcr", {"Vrms": 220, "R": 20, "L": 0.2, "C": 50, "f": 50}, "f0", 50.329, 1e-4),
    ("c10-ph", {"logH": -3}, "pH", 3.0, 1e-12),
    ("c11-weak-acid", {"Ka": 1.8e-5, "C": 0.1}, "pH", 2.8753, 1e-4),                # acetic acid 0.1 M
    ("c11-ideal-gas", {"n": 1, "T": 273.15, "V": 22.414}, "P", 1.0, 1e-3),
    ("c12-nernst", {"E0": 1.10, "n": 2, "logQ": 1, "T": 298}, "E", 1.0704, 1e-4),  # Daniell cell, Q = 10
    ("c12-first-order", {"A0": 1, "k": 0.05, "t": 20}, "t_half", 13.863, 1e-4),
    ("c12-spin-moment", {"n": 5}, "mu", 5.916, 1e-3),
    ("c12-unit-cell", {"Zc": 4, "M": 63.55, "a": 361}, "rho", 8.97, 2e-3),          # copper, fcc
    ("c12-fp", {"Kf": 1.86, "w2": 10, "M2": 58.44, "w1": 200, "i": 2}, "dTf", 3.183, 1e-3),
    ("c9-avg-atomic-mass", {"m1": 35, "p1": 75, "m2": 37}, "Mavg", 35.5, 1e-9),
    # volumetric analysis: CBSE practical examples
    ("c12-kmno4-oxalic", {"w": 6.3035, "Vf": 1000, "V1": 20, "V2": 40}, "M2", 0.01, 1e-4),   # 0.05 M oxalic acid, 2·0.05·20 = 5·M·40
    ("c12-kmno4-oxalic", {"w": 1.575, "Vf": 250, "V1": 10, "V2": 10}, "S", 3.159, 1e-3),     # ≈ 0.02 M KMnO₄
    ("c12-kmno4-mohr", {"w": 19.607, "Vf": 1000, "V1": 20, "V2": 20}, "M2", 0.01, 1e-4),    # 0.05 M Mohr's salt, 0.05·20 = 5·M·20
    ("c11-naoh-oxalic", {"w": 6.3035, "Vf": 1000, "V1": 10, "V2": 10}, "M2", 0.1, 1e-4),    # 2·0.05·10 = M·10
    ("c11-naoh-oxalic", {"w": 6.3035, "Vf": 1000, "V1": 10, "V2": 10}, "S", 4.0, 1e-3),
    ("c11-hcl-na2co3", {"w": 5.2995, "Vf": 1000, "V1": 20, "V2": 20}, "M2", 0.1, 1e-4),     # 0.05 M Na₂CO₃
    ("c11-hcl-na2co3", {"w": 5.2995, "Vf": 1000, "V1": 20, "V2": 20}, "S", 3.646, 1e-3),
    ("m9-heron", {"a": 5, "b": 6, "c": 7}, "A", 14.6969, 1e-5),                     # 6√6
    ("m10-quadratic", {"a": 1, "b": -5, "c": 6}, "x1", 3.0, 1e-12),
    ("m10-ap", {"a": 3, "d": 4, "n": 10}, "Sn", 210.0, 1e-12),
    ("m10-dice", {"S": 7}, "P", 1 / 6, 1e-5),
    ("m12-box", {"s": 18, "x": 3}, "V_best", 432.0, 1e-12),
    ("m12-riemann", {"b": 3, "n": 200}, "S", 8.9326, 1e-4),
    ("m12-bayes", {"prior": 0.01, "sens": 0.99, "fpr": 0.05}, "post", 0.16667, 1e-4),
    ("m11-perm-comb", {"n": 8, "r": 3}, "nCr", 56.0, 1e-9),
    ("m11-gp", {"a": 2, "r": 3, "n": 6}, "Sn", 728.0, 1e-9),
])
def test_textbook_values(exp_id, values, name, expected, rel):
    assert out(exp_id, **values)[name] == pytest.approx(expected, rel=rel)


def test_graph_sweeps_and_paths():
    g = teach_experiment("p11-projectile", {"v0": 20, "th": 45})["result"]["graph"]
    assert g["path"] and g["series"][0]["name"] == "x" and g["series"][1]["name"] == "y"
    assert g["series"][0]["values"][-1] == pytest.approx(40.8163, rel=1e-4) and abs(g["series"][1]["values"][-1]) < 1e-9
    g = teach_experiment("p11-pendulum")["result"]["graph"]
    assert g["x"]["name"] == "L" and g["cursor"] == 1.0 and not g["path"]


def test_input_checks():
    with pytest.raises(ValueError, match="between"):
        teach_experiment("p11-pendulum", {"L": 50})
    with pytest.raises(ValueError, match="no input"):
        teach_experiment("p11-pendulum", {"mass": 2})
    with pytest.raises(ValueError):
        teach_experiment("no-such-experiment")


def test_practice_answers_come_from_the_engine():
    r = teach_practice("p9-first-eq", count=6, seed=7)["result"]
    assert len(r["questions"]) == 6
    for q in r["questions"]:
        v = q["values"]
        assert q["answer"] == pytest.approx(v["u"] + v["a"] * v["t"], rel=1e-3)
        assert q["choices"][q["correct_index"]] == q["answer"] and len(set(q["choices"])) == len(q["choices"])
        assert q["solution"][-1].startswith("So the final velocity is")
    assert teach_practice("p9-first-eq", count=3, seed=7)["result"]["questions"][0]["text"] == r["questions"][0]["text"]
    with pytest.raises(ValueError):
        teach_practice("p9-first-eq", count=50)


def test_practice_works_for_every_experiment():
    for e in CATALOG.values():
        assert teach_practice(e.id, count=2, seed=3)["result"]["questions"], e.id


@pytest.mark.parametrize("written,expected", [
    ("v = u + at", "p9-first-eq"), ("s = ut + ½at²", "p9-second-eq"), ("PV = nRT", "c11-ideal-gas"),
    ("T = 2π√(L/g)", "p11-pendulum"), ("V = IR", "p10-ohm"), ("1/f = 1/v - 1/u", "p10-convex-lens"),
    ("KE = ½mv²", "p9-ke"), ("P1V1 = P2V2", "c11-boyle"), ("E = mc^2", "p12-binding"), ("pH = -log10(H)", "c10-ph"),
    ("Q = mcΔT", "p11-specific-heat"), ("F = G m1 m2 / r^2", "p9-gravitation"),
])
def test_board_reader_finds_the_experiment(written, expected):
    r = teach_recognize(written)["result"]
    assert r["matches"][0]["id"] == expected or any(m["id"] == expected and m["score"] == 1.0 for m in r["matches"]), r["matches"][:3]


def test_board_reader_rearranges_and_falls_back_to_topics():
    r = teach_recognize("v = u + at")["result"]
    assert "a = (-u + v)/t" in [x["pretty"] for x in r["rearranged"]] or any(x["for"] == "a" for x in r["rearranged"])
    r = teach_recognize("ohm's law")["result"]
    assert r["matches"][0]["id"] == "p10-ohm" and r["read_as"] is None
    with pytest.raises(ValueError):
        teach_recognize("  ")


def test_pretty_equations():
    assert pretty("s = u*t + a*t**2/2") == "s = ut + at²/2"
    assert pretty("T = 2*pi*sqrt(L/g)") == "T = 2π√(L/g)"
    assert pretty("n1*sin(i) = n2*sin(r)") == "n₁·sin(i) = n₂·sin(r)"


def test_teach_tools_over_http():
    client, _ = new_client()
    r = client.post("/simulate", json={"domain": "teach", "name": "experiment", "args": {"experiment_id": "p11-pendulum", "values": {"L": 2}}})
    assert r.status_code == 200 and r.json()["result"]["outputs"][0]["value"] == pytest.approx(2.8384, rel=1e-4)
    r = client.post("/simulate", json={"domain": "teach", "name": "experiment", "args": {"experiment_id": "p11-pendulum", "values": {"L": -1}}})
    assert r.status_code == 422
    r = client.post("/simulate", json={"domain": "teach", "name": "recognize", "args": {"equation": "V = IR"}})
    assert r.status_code == 200 and r.json()["result"]["matches"][0]["id"] == "p10-ohm"
