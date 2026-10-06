import math

import numpy as np
import pytest

from app.modules.physics.skyatlas import comoving_gly, sky_atlas
from app.modules.physics.universe import cosmology, galaxy_catalog


@pytest.fixture(scope="module")
def atlas():
    return sky_atlas()["result"]


def test_all_88_constellations(atlas):
    cons = atlas["constellations"]
    # 88 IAU constellations; Serpens is drawn as two figures (Caput and Cauda)
    assert len({c["abbr"] for c in cons}) >= 88
    names = {c["name"] for c in cons}
    assert {"Orion", "Ursa Major", "Crux", "Cassiopeia", "Scorpius"} <= names
    orion = next(c for c in cons if c["abbr"] == "Ori")
    assert orion["hindi"]
    verts = [p for c in cons for line in c["lines"] for p in line]
    matched = sum(p["distance_ly"] is not None for p in verts)
    assert matched / len(verts) > 0.95
    assert len(atlas["constellation_borders"]) > 200


def test_orion_stars_at_real_distances(atlas):
    orion = next(c for c in atlas["constellations"] if c["abbr"] == "Ori")
    d = [p["distance_ly"] for line in orion["lines"] for p in line if p["distance_ly"]]
    # Betelgeuse, Rigel and the belt are hundreds of ly away, pi3 Ori (the shield) only 26 ly
    assert max(d) < 2500 and min(d) > 20  # pi3 Ori is 26 ly away
    for line in orion["lines"]:
        for p in line:
            assert np.linalg.norm(p["unit"]) == pytest.approx(1, abs=1e-4)
            if p["distance_ly"]:
                assert np.linalg.norm(p["xyz_ly"]) == pytest.approx(p["distance_ly"], abs=0.06)


def test_nebula_distances(atlas):
    m42 = next(d for d in atlas["deep_sky"] if d["messier"] == "M 42")
    assert m42["distance_ly"] == pytest.approx(1344, rel=0.01)
    # Orion Nebula is about 8.3 kpc + 0.4 kpc from the galactic centre (anticentre direction)
    r = math.hypot(*m42["galactocentric_kpc"][:2])
    assert 8.3 < r < 9.0


def test_comoving_distance_matches_cosmology_tool():
    for z in (0.1, 1.0, 3.0):
        ref = cosmology(z=z)["result"]["comoving_distance_gly"]
        assert float(comoving_gly(z)) == pytest.approx(ref, rel=2e-3)


def test_structures_and_far_objects(atlas):
    s = {x["name"]: x for x in atlas["structures"]}
    virgo = s["Virgo Cluster"]
    assert virgo["distance_mly"] == pytest.approx(53.8)
    assert math.sqrt(virgo["x_mly"] ** 2 + virgo["y_mly"] ** 2 + virgo["z_mly"] ** 2) == pytest.approx(53.8, rel=1e-3)
    for f in atlas["far_objects"]:
        assert f["distance_mly"] == pytest.approx(float(comoving_gly(f["redshift"])) * 1000, rel=1e-3)
        assert f["distance_mly"] < 46_500  # inside the observable universe


def test_exoplanets_and_clusters(atlas):
    exo = atlas["exoplanets"]
    assert exo["count"] > 3000 and exo["planet_count"] >= exo["count"]
    i = exo["host"].index("Proxima Centauri")
    assert exo["distance_ly"][i] == pytest.approx(4.24, abs=0.05)
    assert exo["n"][i] >= 2
    oc = atlas["open_clusters"]
    assert oc["count"] > 1000
    r = np.hypot(oc["x_kpc"], oc["y_kpc"])
    assert 6 < np.median(r) < 11  # open clusters sit in the disc around the Sun's orbit


def test_bad_input():
    with pytest.raises(ValueError):
        sky_atlas(layers=["planets"])
    with pytest.raises(ValueError):
        sky_atlas(exoplanet_limit=0)


def test_galaxy_catalog_with_redshift_galaxies():
    base = galaxy_catalog(max_distance_mly=6000, limit=25000)["result"]
    more = galaxy_catalog(max_distance_mly=6000, limit=25000, include_redshift=True)["result"]
    nb = len(base["name"]) if "name" in base else base["count"]
    nm = len(more["name"]) if "name" in more else more["count"]
    assert nm > nb


def test_galaxies_have_common_names():
    r = galaxy_catalog(max_distance_mly=100)["result"]
    names = dict(zip(r["name"], r["common_name"]))
    assert names["M 51"] == "Whirlpool Galaxy"
    assert names["M 104"] == "Sombrero Galaxy"
    assert names["LMC"] == "Large Magellanic Cloud"
    assert sum(1 for c in r["common_name"] if c) > 40
