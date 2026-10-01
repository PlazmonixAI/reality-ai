"""ASM Teach listen mode: spoken classroom sentences to experiments, values and equations."""
import pytest

import app.modules  # noqa: F401
from app.modules.teach.explore import teach_explore
from app.modules.teach.listen import spoken_to_math, teach_listen


def L(text, current=None):
    return teach_listen(text, current=current)["result"]


@pytest.mark.parametrize("said,expected", [
    ("t equals 2 pi root l by g", "t = 2 pi sqrt(l / g )"),
    ("v equals u plus a into t", "v = u + a * t"),
    ("x square minus five x plus six equals zero", "x ^ 2 - 5 x + 6 = 0"),
    ("e equals m c squared", "e = m c ^ 2"),
])
def test_spoken_maths(said, expected):
    assert spoken_to_math(said) == expected


def test_spoken_equation_opens_its_experiment():
    r = L("so the time period t equals 2 pi root l by g")
    assert r["action"] == "open" and r["experiment"]["id"] == "p11-pendulum"
    assert r["equation"] == "T = 2 pi sqrt(L / g )"  # recased the way the textbook writes it


def test_topic_and_values():
    r = L("let us look at a simple pendulum of length 2 metres")
    assert r["experiment"]["id"] == "p11-pendulum" and r["values"] == {"L": 2.0}
    t = L("now take the angle of elevation 45 degrees and distance 20 metres for the tower")
    assert t["experiment"]["id"] == "m10-heights" and t["values"] == {"th": 45.0, "d": 20.0}


def test_units_are_converted_and_values_update_the_open_experiment():
    r = L("make the length 150 centimetres", current="p11-pendulum")
    assert r["action"] == "update" and r["values"] == {"L": 1.5}


def test_values_are_clamped_to_the_parameter_range():
    assert L("pendulum length 50 metres")["values"]["L"] == 5.0  # the experiment allows 0.1 to 5 m


def test_unknown_equation_goes_to_the_equation_lab():
    r = L("y equals sine x plus cos x")
    assert r["action"] == "explore"
    assert teach_explore(r["equation"])["result"]["kind"] == "function"


def test_small_talk_does_nothing():
    assert L("hello class good morning")["action"] == "none"
    with pytest.raises(ValueError):
        teach_listen("  ")
