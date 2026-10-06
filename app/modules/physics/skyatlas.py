"""The sky atlas: everything named between the stars and the edge of the observable universe.

- Constellations: the 88 IAU constellations as stick figures (d3-celestial), each line vertex matched to the real
  catalogue star (HYG), so the figures join stars at their true 3D distances. Names in English, Latin genitive
  and Hindi. Boundaries as sky lines.
- Deep sky: named NGC/IC/Messier objects (OpenNGC) with directions; famous nebulae and clusters get distances from
  the literature table below, open clusters from Celestia's catalogue, globular clusters from Celestia's.
- Exoplanets: every confirmed planetary system with a distance (Open Exoplanet Catalogue), in 3D.
- Large-scale structure: galaxy groups, clusters, superclusters, great walls and voids, and record-distance objects.
  Objects given by redshift are placed at their comoving distance from the Friedmann equation (Planck 2018 ΛCDM).
- More galaxies: NGC/IC galaxies with a measured redshift that are not in the distance catalogue, placed by redshift.
"""
from __future__ import annotations

import csv
import json
import math
from functools import lru_cache

import numpy as np
from scipy import integrate

from app.core.registry import tool
from app.modules.physics.universe import (C_KM_S, DATA, EQ_TO_GAL, PC_LY, _frame, galactocentric, galaxy_table, radec_unit,
                                          star_table)

H0, OMEGA_M, OMEGA_R = 67.66, 0.3111, 9.14e-5
OMEGA_L = 1 - OMEGA_M - OMEGA_R


@lru_cache(maxsize=1)
def _chi_table() -> tuple[np.ndarray, np.ndarray]:
    """Comoving distance (Gly) against redshift for flat ΛCDM, tabulated once and interpolated."""
    zs = np.concatenate([np.linspace(0, 0.1, 201)[:-1], np.geomspace(0.1, 1100, 600)])
    e = lambda z: math.sqrt(OMEGA_R * (1 + z) ** 4 + OMEGA_M * (1 + z) ** 3 + OMEGA_L)  # noqa: E731
    hubble_gly = C_KM_S / H0 * PC_LY / 1000
    chi = [0.0]
    for a, b in zip(zs[:-1], zs[1:]):
        chi.append(chi[-1] + integrate.quad(lambda z: 1 / e(z), a, b, epsrel=1e-10)[0])
    return zs, np.array(chi) * hubble_gly


def comoving_gly(z) -> np.ndarray:
    zs, chi = _chi_table()
    return np.interp(np.asarray(z, float), zs, chi)


# ---------- famous nebulae and clusters: distances (ly) from the literature, rounded ----------
# Orion Nebula 1344 (VLBA parallax, Menten+ 2007); Crab 6500 (Trimble 1973); Eagle 5700; Lagoon/Trifid 4100;
# Ring 2570 (Gaia); Helix 650 (Gaia); Carina 8500; others from standard references (approximate).
NEBULA_DIST_LY = {
    "M 42": 1344, "M 43": 1344, "NGC 2024": 1350, "IC 434": 1375, "M 1": 6500, "M 16": 5700, "M 8": 4100, "M 20": 4100,
    "M 17": 5500, "NGC 3372": 8500, "M 57": 2570, "NGC 7293": 650, "M 27": 1360, "NGC 6543": 3300, "NGC 2237": 5200,
    "NGC 2244": 5200, "NGC 7000": 2590, "IC 5070": 2590, "NGC 6960": 2400, "NGC 6992": 2400, "NGC 2070": 161000,
    "M 45": 444, "M 44": 577, "NGC 869": 7500, "NGC 884": 7500, "NGC 4755": 6400, "M 11": 6200, "NGC 6302": 3400,
    "IC 1805": 7500, "IC 1848": 7500, "M 97": 2030, "M 76": 2500, "NGC 1499": 1000, "NGC 7635": 7100, "M 78": 1350,
    "NGC 6357": 5500, "NGC 6334": 5500, "M 7": 980, "M 6": 1600, "M 41": 2300, "M 35": 2800, "M 36": 4100, "M 37": 4500,
    "M 38": 3500, "M 39": 1000, "M 47": 1600, "M 48": 2500, "M 50": 3200, "M 52": 5000, "M 67": 2700, "M 93": 3600,
    "M 103": 8500, "NGC 3242": 4600, "NGC 2392": 6500, "NGC 7009": 4700, "NGC 6826": 3200, "NGC 2264": 2700, "IC 2602": 490,
    "IC 2391": 500, "NGC 2632": 577, "IC 4703": 5700, "IC 1396": 2400, "NGC 281": 9500, "IC 2177": 3800, "IC 405": 1500,
    "IC 443": 5000, "NGC 1952": 6500, "NGC 6514": 4100, "NGC 6523": 4100, "NGC 1976": 1344, "NGC 6720": 2570,
    "NGC 6853": 1360, "NGC 6618": 5500, "NGC 6611": 5700, "NGC 1432": 444,
}

# ---------- large-scale structure (published positions and distances, rounded) ----------
# kind, name, RA (h), Dec (°), distance in Mly or redshift z, radius in Mly, one-line note
STRUCTURES = [
    ("group", "Local Group", 0.712, 41.27, {"mly": 1.0}, 5.0, "The Milky Way, Andromeda, Triangulum and about 80 dwarf galaxies"),
    ("cluster", "Virgo Cluster", 12.45, 12.72, {"mly": 53.8}, 7.5, "About 1,500 galaxies around the giant elliptical M87; the heart of our supercluster"),
    ("cluster", "Fornax Cluster", 3.633, -35.45, {"mly": 62}, 3.0, "The second richest cluster within 100 million ly"),
    ("group", "Eridanus Group", 3.5, -21.0, {"mly": 75}, 3.0, "A loose group of about 200 galaxies"),
    ("cluster", "Centaurus Cluster", 12.81, -41.31, {"mly": 170}, 6.0, "Abell 3526, part of the Hydra–Centaurus Supercluster"),
    ("cluster", "Hydra Cluster", 10.61, -27.53, {"mly": 158}, 5.0, "Abell 1060, about 160 bright galaxies"),
    ("cluster", "Norma Cluster", 16.25, -60.9, {"mly": 220}, 7.0, "Abell 3627, near the centre of the Great Attractor"),
    ("cluster", "Perseus Cluster", 3.33, 41.51, {"mly": 240}, 8.0, "Abell 426, the brightest X-ray cluster in the sky"),
    ("cluster", "Coma Cluster", 13.0, 27.98, {"mly": 321}, 10.0, "Abell 1656, over 1,000 galaxies; where dark matter was first inferred (Zwicky, 1933)"),
    ("cluster", "Leo Cluster", 11.74, 19.83, {"mly": 330}, 6.0, "Abell 1367"),
    ("cluster", "Hercules Cluster", 16.09, 17.7, {"mly": 500}, 6.0, "Abell 2151, rich in colliding spirals"),
    ("supercluster", "Virgo Supercluster", 12.45, 12.72, {"mly": 53.8}, 55.0, "Our home supercluster (the Local Supercluster)"),
    ("supercluster", "Laniakea Supercluster", 16.5, -55.0, {"mly": 250}, 260.0, "About 100,000 galaxies flowing towards the Great Attractor (Tully et al., 2014)"),
    ("attractor", "Great Attractor", 16.25, -60.9, {"mly": 220}, 20.0, "The gravitational centre pulling the Local Group at about 600 km/s"),
    ("supercluster", "Hydra–Centaurus Supercluster", 12.0, -40.0, {"mly": 160}, 50.0, "The nearest neighbour supercluster"),
    ("supercluster", "Perseus–Pisces Supercluster", 2.0, 35.0, {"mly": 250}, 60.0, "A long chain of clusters across the northern sky"),
    ("supercluster", "Coma Supercluster", 12.5, 27.0, {"mly": 300}, 50.0, "The Coma and Leo clusters and the filaments between them"),
    ("supercluster", "Hercules Supercluster", 16.1, 17.0, {"mly": 500}, 50.0, "Abell 2151, 2147 and 2152"),
    ("supercluster", "Shapley Supercluster", 13.46, -31.5, {"mly": 650}, 100.0, "The most massive concentration of galaxies within a billion light years"),
    ("supercluster", "Horologium–Reticulum Supercluster", 3.3, -50.0, {"mly": 700}, 275.0, "One of the largest superclusters in the local universe"),
    ("supercluster", "Pisces–Cetus Supercluster Complex", 1.0, -10.0, {"mly": 670}, 500.0, "A filament of superclusters about a billion light years long"),
    ("wall", "CfA2 Great Wall", 13.0, 30.0, {"mly": 300}, 250.0, "A sheet of galaxies 500 million ly long, found in 1989"),
    ("wall", "Sculptor Wall", 0.5, -30.0, {"mly": 400}, 150.0, "The southern counterpart of the Great Wall"),
    ("wall", "Sloan Great Wall", 12.5, 0.0, {"z": 0.073}, 690.0, "1.4 billion light years long (Gott et al., 2005)"),
    ("void", "Local Void", 18.6, 18.0, {"mly": 75}, 75.0, "An almost empty region right next to the Local Group"),
    ("void", "Boötes Void", 14.33, 46.0, {"mly": 700}, 165.0, "The Great Nothing: about 60 galaxies in a sphere 330 million ly wide"),
    ("cluster", "Abell 1689", 13.19, -1.34, {"z": 0.183}, 3.0, "One of the strongest gravitational lenses known"),
    ("cluster", "Bullet Cluster", 6.98, -55.95, {"z": 0.296}, 3.0, "Two clusters that collided: the clearest direct evidence of dark matter"),
    ("cluster", "Pandora's Cluster (Abell 2744)", 0.24, -30.4, {"z": 0.308}, 3.0, "Four clusters merging; a JWST deep field"),
    ("cluster", "Abell 370", 2.66, -1.58, {"z": 0.375}, 3.0, "Where the first giant gravitational arc was seen"),
    ("cluster", "Phoenix Cluster", 23.73, -42.72, {"z": 0.597}, 4.0, "Forms stars at about 500 Suns a year in its central galaxy"),
    ("cluster", "El Gordo", 1.04, -49.25, {"z": 0.87}, 5.0, "The largest known distant cluster, about 3 million billion Suns"),
    ("wall", "Hercules–Corona Borealis Great Wall", 15.8, 27.0, {"z": 2.0}, 5000.0, "Perhaps the largest structure known, about 10 billion ly across"),
    ("wall", "Huge Large Quasar Group", 10.8, 14.0, {"z": 1.27}, 2000.0, "73 quasars spanning about 4 billion ly"),
]
# record-distance and famous far objects: name, RA (h), Dec (°), redshift z, note
FAR = [
    ("Cygnus A", 19.99, 40.73, 0.0561, "The brightest radio galaxy in the sky"),
    ("3C 273", 12.485, 2.05, 0.158, "The first quasar identified (1963); a black hole of 900 million Suns"),
    ("TON 618", 12.47, 31.48, 2.219, "A quasar powered by one of the most massive black holes known (~66 billion Suns)"),
    ("Earendel", 1.62, -8.46, 6.2, "The most distant single star seen, magnified by a lensing cluster (Welch et al., 2022)"),
    ("GN-z11", 12.61, 62.24, 10.6, "A galaxy seen 400 million years after the Big Bang (HST and JWST)"),
    ("JADES-GS-z14-0", 3.546, -27.87, 14.32, "The most distant galaxy confirmed so far (JWST, 2024): 290 million years after the Big Bang"),
    ("Hubble Ultra Deep Field", 3.545, -27.79, 7.0, "About 10,000 galaxies in a patch of sky a tenth the size of the full Moon"),
    ("Hubble Deep Field", 12.61, 62.22, 3.0, "The first deep field (1995): 3,000 galaxies in an empty-looking patch of sky"),
]


@lru_cache(maxsize=1)
def _load():
    con = json.loads((DATA / "constellations.json").read_text())
    with (DATA / "deepsky.csv").open() as f:
        dso = list(csv.DictReader(f))
    with (DATA / "exoplanets.csv").open() as f:
        exo = list(csv.DictReader(f))
    with (DATA / "openclusters.csv").open() as f:
        ocl = list(csv.DictReader(f))
    with (DATA / "globulars.csv").open() as f:
        glob = list(csv.DictReader(f))
    return con, dso, exo, ocl, glob


@lru_cache(maxsize=1)
def dso_images() -> dict[str, dict]:
    """OpenNGC id → real telescope image (scripts/build_dso_images.py): file, credit and size on the sky."""
    path = DATA / "dso_images.json"
    return {r["id"]: r for r in json.loads(path.read_text())} if path.exists() else {}


def _hip_positions() -> dict[str, tuple[np.ndarray, float]]:
    """HIP id → (equatorial unit vector, distance ly) for the catalogue stars."""
    s = star_table()
    with (DATA / "stars.csv").open() as f:
        hips = [r["hip"] for r in csv.DictReader(f)]
    return {h: (s["unit"][:, i], float(s["dist_ly"][i])) for i, h in enumerate(hips) if h}


def _r(v: np.ndarray, nd: int = 4) -> list[float]:
    return [round(float(x), nd) for x in v]


def _ra_deg_unit(ra_deg: float, dec: float) -> np.ndarray:
    return radec_unit(ra_deg / 15.0, dec)


@tool(
    domain="physics",
    name="sky_atlas",
    description=(
        "The named universe for the Universe map: the 88 constellations (stick figures joining real stars in 3D, names "
        "in English, Latin and Hindi, boundaries), named nebulae and star clusters (with distances where known), "
        "exoplanet systems, open and globular clusters, and the large-scale structure (galaxy groups, clusters, "
        "superclusters, great walls, voids and record-distance objects placed at comoving distance from redshift). "
        "frame: 'ecliptic' (default, matches star_catalog), 'galactic' or 'equatorial'. layers: any of "
        "constellations, deep_sky, exoplanets, clusters, structures."
    ),
)
def sky_atlas(frame: str = "ecliptic", layers: list[str] | None = None, exoplanet_limit: int = 4000) -> dict:
    rot = _frame(frame)
    allowed = {"constellations", "deep_sky", "exoplanets", "clusters", "structures"}
    layers = list(layers or sorted(allowed))
    if not set(layers) <= allowed:
        raise ValueError(f"layers must be from {sorted(allowed)}")
    if not 1 <= exoplanet_limit <= 5000:
        raise ValueError("exoplanet_limit must be 1..5000")
    con, dso, exo, ocl, glob = _load()
    out: dict = {"frame": frame}

    if "constellations" in layers:
        hp = _hip_positions()
        cons = []
        for c in con["constellations"]:
            lines, pts = [], []
            for seg in c["lines"]:
                line = []
                for p in seg:
                    u = _ra_deg_unit(p["ra"], p["dec"])
                    if p["hip"] in hp:
                        uu, d = hp[p["hip"]]
                        pos = rot @ uu * d
                    else:
                        d, pos = None, rot @ u * 300.0  # unmatched faint vertex: drawn at 300 ly in its direction
                    line.append({"unit": _r(rot @ u, 5), "xyz_ly": _r(pos, 2), "distance_ly": None if d is None else round(d, 1)})
                    pts.append(pos)
                lines.append(line)
            centre = np.mean(pts, axis=0) if pts else np.zeros(3)
            cons.append({"abbr": c["abbr"], "name": c["name"], "hindi": c["hindi"], "genitive": c["genitive"], "rank": c["rank"],
                         "label_unit": _r(rot @ _ra_deg_unit(c["label_ra"], c["label_dec"]), 5), "centre_ly": _r(centre, 1), "lines": lines})
        out["constellations"] = cons
        out["constellation_borders"] = [[_r(rot @ _ra_deg_unit(lon, lat), 4) for lon, lat in line] for line in con["borders"]]

    if "deep_sky" in layers:
        ocl_by_name = {r["name"].replace(" ", ""): r for r in ocl}
        glob_by_name = {r["name"].replace(" ", ""): r for r in glob}
        items, images = [], dso_images()
        for r in dso:
            if not (r["common"] or r["messier"] or r["id"] in images) or r["type"] in ("Galaxy", "Galaxy pair", "Galaxy triplet", "Galaxy group"):
                continue
            dist = NEBULA_DIST_LY.get(r["messier"]) or NEBULA_DIST_LY.get(r["id"])
            src = "literature" if dist else None
            if not dist:
                for nm in (r["id"], r["messier"]):
                    hit = ocl_by_name.get(nm.replace(" ", "")) or glob_by_name.get(nm.replace(" ", ""))
                    if hit:
                        dist, src = float(hit["dist_ly"]), "Celestia catalogue"
                        break
            ueq = radec_unit(float(r["ra_h"]), float(r["dec_deg"]))
            u = rot @ ueq
            gc = galactocentric(ueq, dist / PC_LY / 1000) if dist else None
            name = r["common"] or r["messier"] or r["id"]
            img = images.get(r["id"])
            items.append({"name": name, "id": r["id"], "messier": r["messier"], "type": r["type"],
                          "magnitude": float(r["mag"]) if r["mag"] else None, "size_arcmin": float(r["major_arcmin"]) if r["major_arcmin"] else None,
                          "unit": _r(u, 5), "distance_ly": dist, "distance_source": src,
                          "xyz_ly": _r(u * dist, 2) if dist else None, "galactocentric_kpc": _r(gc, 4) if gc is not None else None,
                          "image": None if img is None else {"file": img["file"], "credit": img["credit"], "width_deg": img["width_deg"],
                                                             "height_deg": img["height_deg"],
                                                             "width_ly": round(math.radians(img["width_deg"]) * dist, 3) if dist else None}})
        out["deep_sky"] = items

    if "exoplanets" in layers:
        exo = exo[:exoplanet_limit]
        u = rot @ radec_unit([float(e["ra_h"]) for e in exo], [float(e["dec_deg"]) for e in exo])
        d = np.array([float(e["dist_pc"]) for e in exo]) * PC_LY
        xyz = u * d
        out["exoplanets"] = {
            "count": len(exo), "planet_count": int(sum(int(e["n"]) for e in exo)),
            "host": [e["host"] for e in exo], "planets": [e["planets"].split("|") for e in exo], "n": [int(e["n"]) for e in exo],
            "methods": [e["methods"].split("|") for e in exo], "year": [int(e["year"]) if e["year"] else None for e in exo],
            "distance_ly": d.round(2).tolist(), "x_ly": xyz[0].round(3).tolist(), "y_ly": xyz[1].round(3).tolist(), "z_ly": xyz[2].round(3).tolist(),
        }

    if "clusters" in layers:  # open clusters in the Galaxy, galactocentric kpc like physics.milky_way
        eq = radec_unit([float(r["ra_h"]) for r in ocl], [float(r["dec_deg"]) for r in ocl])
        g = galactocentric(eq, np.array([float(r["dist_ly"]) for r in ocl]) / PC_LY / 1000)
        out["open_clusters"] = {"count": len(ocl), "name": [r["name"] for r in ocl],
                                "distance_ly": [round(float(r["dist_ly"]), 1) for r in ocl],
                                "x_kpc": g[0].round(4).tolist(), "y_kpc": g[1].round(4).tolist(), "z_kpc": g[2].round(4).tolist()}

    if "structures" in layers:  # galactic frame, millions of light years, like physics.galaxy_catalog
        items = []
        for kind, name, ra, dec, where, radius, note in STRUCTURES:
            d = where["mly"] if "mly" in where else float(comoving_gly(where["z"])) * 1000
            v = EQ_TO_GAL @ radec_unit(ra, dec) * d
            items.append({"kind": kind, "name": name, "distance_mly": round(d, 2), "redshift": where.get("z"),
                          "radius_mly": radius, "x_mly": round(float(v[0]), 3), "y_mly": round(float(v[1]), 3), "z_mly": round(float(v[2]), 3), "note": note})
        far = []
        for name, ra, dec, z, note in FAR:
            d = float(comoving_gly(z)) * 1000
            v = EQ_TO_GAL @ radec_unit(ra, dec) * d
            far.append({"name": name, "redshift": z, "distance_mly": round(d, 1), "x_mly": round(float(v[0]), 2),
                        "y_mly": round(float(v[1]), 2), "z_mly": round(float(v[2]), 2), "note": note})
        out["structures"], out["far_objects"] = items, far

    return {
        "result": out,
        "units": "constellation and star positions in light years, open clusters in galactocentric kpc, structures in millions of light years (galactic frame)",
        "assumptions": [
            "Constellation figures: IAU stick figures from d3-celestial, vertices matched to HYG stars within 0.4°",
            "Nebula and cluster distances: literature values (rounded) or the Celestia catalogue; objects without a measured distance have a direction only",
            "Exoplanets: Open Exoplanet Catalogue, confirmed planets with a known system distance",
            f"Objects given by redshift sit at their comoving distance in flat ΛCDM (H0 = {H0}, Ωm = {OMEGA_M})",
            "Structure positions and sizes are published values, rounded; large structures are drawn as spheres of their typical radius",
        ],
    }


@lru_cache(maxsize=1)
def redshift_galaxies() -> dict:
    """NGC/IC galaxies with a redshift (OpenNGC) that are not already in the distance catalogue."""
    _, dso, *_ = _load()
    have = {n.replace(" ", "").upper() for n in galaxy_table()["name"]}
    rows = [r for r in dso if r["type"] == "Galaxy" and r["redshift"] and 0.004 <= float(r["redshift"]) <= 0.5
            and r["id"].replace(" ", "").upper() not in have and (r["messier"].replace(" ", "").upper() not in have if r["messier"] else True)]
    z = np.array([float(r["redshift"]) for r in rows])
    return {"name": [r["common"] or r["messier"] or r["id"] for r in rows], "type": [r["hubble"] or "" for r in rows],
            "unit": radec_unit([float(r["ra_h"]) for r in rows], [float(r["dec_deg"]) for r in rows]),
            "dist_ly": comoving_gly(z) * 1e9, "z": z,
            "major_arcmin": np.array([float(r["major_arcmin"]) if r["major_arcmin"] else 0.5 for r in rows])}
