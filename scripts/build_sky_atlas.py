"""Build the sky atlas catalogues in app/data/space/ from open source catalogues.

Sources (all fetched from GitHub; licences in frontend/assets/textures/CREDITS.md):
  - d3-celestial (Olaf Frohn, BSD 3-Clause): IAU constellation stick figures, names (with Hindi) and boundaries
  - OpenNGC (Mattia Verga, CC BY-SA 4.0): NGC/IC objects with types, sizes, position angles and redshifts
  - Open Exoplanet Catalogue (Hanno Rein et al., MIT): planets and the position and distance of their stars
  - Celestia (GPL): open star clusters with distances

Run:  python scripts/build_sky_atlas.py
"""
from __future__ import annotations

import csv
import io
import json
import math
import re
from pathlib import Path

import httpx

OUT = Path(__file__).resolve().parents[1] / "app" / "data" / "space"
D3 = "https://raw.githubusercontent.com/ofrohn/d3-celestial/master/data/"
NGC = "https://raw.githubusercontent.com/mattiaverga/OpenNGC/master/database_files/NGC.csv"
OEC = "https://raw.githubusercontent.com/OpenExoplanetCatalogue/oec_tables/master/comma_separated/open_exoplanet_catalogue.txt"
OPEN = "https://raw.githubusercontent.com/CelestiaProject/CelestiaContent/master/data/openclusters.dsc"


def fetch(url: str) -> str:
    r = httpx.get(url, timeout=300, follow_redirects=True)
    r.raise_for_status()
    return r.text


def unit(ra_deg: float, dec_deg: float) -> tuple[float, float, float]:
    a, d = math.radians(ra_deg), math.radians(dec_deg)
    return math.cos(d) * math.cos(a), math.cos(d) * math.sin(a), math.sin(d)


def hms(text: str, hours: bool) -> float | None:
    if not text or not text.strip():
        return None
    s = text.strip()
    sign = -1 if s.startswith("-") else 1
    parts = [float(p) for p in re.split(r"[:\s]+", s.lstrip("+-")) if p]
    v = parts[0] + (parts[1] / 60 if len(parts) > 1 else 0) + (parts[2] / 3600 if len(parts) > 2 else 0)
    return sign * v


def constellations(stars: list[dict]) -> list[dict]:
    """Stick figures with each vertex matched to the nearest bright catalogue star (HIP), so lines join real stars in 3D."""
    lines = json.loads(fetch(D3 + "constellations.lines.json"))
    names = json.loads(fetch(D3 + "constellations.json"))
    borders = json.loads(fetch(D3 + "constellations.borders.json"))
    bright = [(unit(float(s["ra_h"]) * 15, float(s["dec_deg"])), s["hip"]) for s in stars if s["hip"] and float(s["mag"]) <= 6.5]

    def match(lon: float, lat: float) -> str | None:
        u = unit(lon % 360, lat)
        best, hip = math.cos(math.radians(0.4)), None  # within 0.4°
        for v, h in bright:
            c = u[0] * v[0] + u[1] * v[1] + u[2] * v[2]
            if c > best:
                best, hip = c, h
        return hip

    info = {f["id"]: f for f in names["features"]}
    out = []
    for f in lines["features"]:
        cid = f["id"]
        n = info.get(cid, {}).get("properties", {})
        lab = info.get(cid, {}).get("geometry", {}).get("coordinates", [0, 0])
        segs = []
        for line in f["geometry"]["coordinates"]:
            segs.append([{"ra": round(lon % 360, 4), "dec": round(lat, 4), "hip": match(lon, lat)} for lon, lat in line])
        out.append({"abbr": cid, "name": n.get("name", cid), "hindi": n.get("hi", ""), "genitive": n.get("gen", ""),
                    "rank": int(n.get("rank", 3) or 3), "label_ra": round(lab[0] % 360, 3), "label_dec": round(lab[1], 3), "lines": segs})
    bmap = []
    for f in borders["features"]:
        for line in f["geometry"]["coordinates"] if f["geometry"]["type"] == "MultiLineString" else [f["geometry"]["coordinates"]]:
            bmap.append([[round(lon % 360, 3), round(lat, 3)] for lon, lat in line])
    return out, bmap


TYPES = {"*": "Star", "**": "Double star", "*Ass": "Stellar association", "OCl": "Open cluster", "GCl": "Globular cluster",
         "Cl+N": "Cluster with nebula", "G": "Galaxy", "GPair": "Galaxy pair", "GTrpl": "Galaxy triplet", "GGroup": "Galaxy group",
         "PN": "Planetary nebula", "HII": "Emission nebula", "DrkN": "Dark nebula", "EmN": "Emission nebula", "Neb": "Nebula",
         "RfN": "Reflection nebula", "SNR": "Supernova remnant", "Nova": "Nova"}


def deep_sky() -> list[dict]:
    rows = list(csv.DictReader(io.StringIO(fetch(NGC)), delimiter=";"))
    out = []
    for r in rows:
        if r["Type"] in ("Dup", "NonEx", "Other", ""):
            continue
        ra, dec = hms(r["RA"], True), hms(r["Dec"], False)
        if ra is None or dec is None:
            continue
        mag = r["V-Mag"] or r["B-Mag"]
        common = r["Common names"].split(",")[0].strip()
        messier = f"M {int(r['M'])}" if r["M"] else ""
        z = float(r["Redshift"]) if r["Redshift"] else None
        bright = mag and float(mag) <= 12.5
        if not (common or messier or bright or (r["Type"] == "G" and z)):
            continue
        name = re.sub(r"^(NGC|IC)0*(\d+)", r"\1 \2", r["Name"])
        out.append({"id": name, "messier": messier, "common": common, "type": TYPES.get(r["Type"], r["Type"]),
                    "ra_h": round(ra, 6), "dec_deg": round(dec, 5), "mag": float(mag) if mag else "",
                    "major_arcmin": r["MajAx"] or "", "minor_arcmin": r["MinAx"] or "", "pa_deg": r["PosAng"] or "",
                    "hubble": r["Hubble"], "redshift": z if z is not None else ""})
    return out


def exoplanets() -> list[dict]:
    rows = list(csv.DictReader(io.StringIO(fetch(OEC))))
    systems: dict[tuple, dict] = {}
    for r in rows:
        if "Confirmed planets" not in (r.get("list") or "") or not r["system_distance"] or not r["system_rightascension"]:
            continue
        key = (r["system_rightascension"], r["system_declination"])
        host = re.sub(r"\s+[a-z](\s.*)?$", "", r["name"]).strip()
        s = systems.setdefault(key, {"host": host, "ra_h": round(hms(r["system_rightascension"], True), 6),
                                     "dec_deg": round(hms(r["system_declination"], False), 5),
                                     "dist_pc": float(r["system_distance"]), "planets": [], "methods": set(), "year": 9999,
                                     "star_temp_k": r["hoststar_temperature"] or ""})
        s["planets"].append(r["name"])
        s["methods"].add(r["discoverymethod"] or "unknown")
        if r["discoveryyear"]:
            s["year"] = min(s["year"], int(float(r["discoveryyear"])))
    out = []
    for s in systems.values():
        out.append({**s, "planets": "|".join(sorted(s["planets"])), "methods": "|".join(sorted(s["methods"])), "n": len(s["planets"]),
                    "year": "" if s["year"] == 9999 else s["year"]})
    return sorted(out, key=lambda s: s["dist_pc"])


def open_clusters() -> list[dict]:
    text = fetch(OPEN)
    out = []
    for m in re.finditer(r'OpenCluster\s+"([^"]+)"\s*\{([^}]*)\}', text):
        body = dict(re.findall(r"(\w+)\s+([-\d.eE+]+)", m.group(2)))
        if "Distance" not in body:
            continue
        out.append({"name": m.group(1).split(":")[0], "ra_h": float(body["RA"]), "dec_deg": float(body["Dec"]),
                    "dist_ly": float(body["Distance"]), "radius_ly": float(body.get("Radius", 10))})
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    with (OUT / "stars.csv").open() as f:
        stars = list(csv.DictReader(f))
    con, borders = constellations(stars)
    (OUT / "constellations.json").write_text(json.dumps({"constellations": con, "borders": borders}, separators=(",", ":")))
    write_csv(OUT / "deepsky.csv", deep_sky())
    write_csv(OUT / "exoplanets.csv", exoplanets())
    write_csv(OUT / "openclusters.csv", open_clusters())
    for name in ("constellations.json", "deepsky.csv", "exoplanets.csv", "openclusters.csv"):
        print(name, (OUT / name).stat().st_size)
