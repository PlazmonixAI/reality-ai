"""Lambert's problem, launch windows and interplanetary missions."""
import math

import numpy as np
import pytest

from app.modules.physics.interplanetary import (MU_SUN, conic_state, interplanetary_mission, interplanetary_porkchop, lambert)


def test_lambert_curtis_example_5_2():
    v1, v2 = lambert(np.array([5000, 10000, 2100]) * 1e3, np.array([-14600, 2500, 7000]) * 1e3, 3600, 3.986004418e14)
    assert np.allclose(v1 / 1e3, [-5.9925, 1.9254, 3.2456], atol=2e-4)
    assert np.allclose(v2 / 1e3, [-3.3125, -4.1966, -0.38529], atol=2e-4)


def test_lambert_consistent_with_kepler_propagation():
    r1 = np.array([1.0, 0.1, 0.0]) * 1.496e11
    r2 = np.array([-0.3, 1.4, 0.05]) * 1.496e11
    tof = 200 * 86400
    v1, _ = lambert(r1, r2, tof, MU_SUN)
    r, _ = conic_state(r1, v1, tof)
    assert np.allclose(r, r2, rtol=1e-7)


def test_mars_2026_window():
    r = interplanetary_porkchop("earth", "mars", "2026-08-01", 240, 150, 400, n_depart=30, n_tof=25)["result"]
    b = r["best"]
    assert "2026-10" <= b["depart"][:7] <= "2026-12"
    assert 7 < b["c3_km2s2"] < 14
    assert 5000 < b["total_delta_v"] < 7000
    assert r["hohmann_tof_days"] == pytest.approx(259, abs=12)


def test_jupiter_needs_much_more_energy():
    r = interplanetary_porkchop("earth", "jupiter", "2026-06-01", 450, n_depart=20, n_tof=20)["result"]
    assert 75 < r["best"]["c3_km2s2"] < 110
    assert 700 < r["best"]["tof_days"] < 1700


def test_mission_burns_and_position():
    m = interplanetary_mission("2026-11-01", "earth", "mars", tof_days=300, at="2027-04-01")["result"]
    vinf = m["vinf_departure"]
    r0 = 6.378137e6 + 200e3
    assert m["departure_burn"] == pytest.approx(math.sqrt(vinf**2 + 2 * 3.986004418e14 / r0) - math.sqrt(3.986004418e14 / r0))
    assert m["now"]["phase"] == "cruise" and 0 < m["now"]["progress"] < 1
    assert len(m["path_au"]) == 200
    assert np.allclose(m["path_au"][-1], m["target_at_arrival_au"], atol=1e-6)
    later = interplanetary_mission("2026-11-01", "earth", "mars", tof_days=300, at="2028-01-01")["result"]
    assert later["now"]["phase"] == "arrived"
    with pytest.raises(ValueError):
        interplanetary_mission("2026-11-01", "earth", "earth", tof_days=300)
