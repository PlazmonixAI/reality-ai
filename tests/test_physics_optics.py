import math

import pytest

from app.modules.physics.optics import lens_mirror, refraction


def _meet(ray, x):
    """y of a ray's outgoing segment at x (linear extrapolation)."""
    (x1, y1), (x2, y2) = ray[1], ray[2]
    return y1 + (y2 - y1) * (x - x1) / (x2 - x1)


def test_converging_lens_real_image():
    r = lens_mirror("converging_lens", 0.10, 0.30, 0.02)
    res = r["result"]
    assert res["image_distance"] == pytest.approx(0.15)
    assert res["magnification"] == pytest.approx(-0.5)
    assert res["image_type"] == "real" and res["orientation"] == "inverted"
    for ray in r["geometry"]["rays"]:
        assert _meet(ray, 0.15) == pytest.approx(-0.01, abs=1e-12)


def test_magnifying_glass_virtual_image():
    r = lens_mirror("converging_lens", 0.10, 0.05, 0.01)["result"]
    assert r["image_distance"] == pytest.approx(-0.10)
    assert r["magnification"] == pytest.approx(2)
    assert r["image_type"] == "virtual" and r["orientation"] == "upright"


def test_diverging_lens():
    r = lens_mirror("diverging_lens", 0.10, 0.20, 0.03)
    assert r["result"]["image_distance"] == pytest.approx(-0.2 / 3)
    assert r["result"]["magnification"] == pytest.approx(1 / 3)
    # Backward extensions of the outgoing rays meet at the virtual image
    for ray in r["geometry"]["rays"]:
        assert _meet(ray, -0.2 / 3) == pytest.approx(0.01, abs=1e-12)


def test_concave_mirror_real_image_in_front():
    r = lens_mirror("concave_mirror", 0.10, 0.30, 0.02)
    assert r["result"]["image_distance"] == pytest.approx(0.15)
    assert r["geometry"]["image"]["x"] == pytest.approx(-0.15)
    for ray in r["geometry"]["rays"]:
        assert _meet(ray, -0.15) == pytest.approx(-0.01, abs=1e-12)


def test_convex_mirror_virtual_behind():
    r = lens_mirror("convex_mirror", 0.10, 0.10, 0.02)
    assert r["result"]["image_distance"] == pytest.approx(-0.05)
    assert r["result"]["magnification"] == pytest.approx(0.5)
    assert r["geometry"]["image"]["x"] == pytest.approx(0.05)


def test_object_at_focus():
    r = lens_mirror("converging_lens", 0.1, 0.1)["result"]
    assert r["image_distance"] is None and "focal" in r["image_type"]


def test_snell_air_to_water():
    r = refraction(1.0, 1.33, 45)["result"]
    assert r["refraction_deg"] == pytest.approx(math.degrees(math.asin(math.sin(math.radians(45)) / 1.33)))
    assert r["refraction_deg"] == pytest.approx(32.12, abs=0.01)
    assert r["critical_angle_deg"] is None


def test_normal_incidence_reflectance():
    r = refraction(1.0, 1.5, 0)["result"]
    assert r["reflectance"] == pytest.approx(0.04)
    assert r["refraction_deg"] == pytest.approx(0)


def test_brewster_angle_kills_p_reflection():
    b = math.degrees(math.atan(1.5))
    r = refraction(1.0, 1.5, b)["result"]
    assert r["brewster_angle_deg"] == pytest.approx(b)
    assert r["reflectance_p"] == pytest.approx(0, abs=1e-12)


def test_total_internal_reflection():
    crit = math.degrees(math.asin(1 / 1.5))
    assert refraction(1.5, 1.0, 10)["result"]["critical_angle_deg"] == pytest.approx(crit)
    assert refraction(1.5, 1.0, crit - 0.5)["result"]["total_internal_reflection"] is False
    tir = refraction(1.5, 1.0, crit + 0.5)["result"]
    assert tir["total_internal_reflection"] is True and tir["reflectance"] == 1


def test_optics_validation():
    with pytest.raises(ValueError):
        lens_mirror("prism", 0.1, 0.2)
    with pytest.raises(ValueError):
        refraction(0.5, 1, 10)
    with pytest.raises(ValueError):
        refraction(1, 1.5, 90)
