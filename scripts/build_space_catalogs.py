"""Build the compact space catalogues in app/data/space/ from public source catalogues.

Run once (network needed):  python scripts/build_space_catalogs.py
Sources (downloaded from GitHub):
- Moons, dwarf planets, asteroids, comets, galaxies and globular clusters: Celestia Content
  (github.com/CelestiaProject/CelestiaContent, data/*.ssc and *.dsc, GPL-2.0-or-later), whose orbital
  elements come from JPL/SSD and the IAU and whose galaxy distances come from NED, RC3 and Karachentsev+ 2004.
- Stars: the HYG database v4.1 (github.com/astronexus/HYG-Database, CC BY-SA 4.0), which merges Hipparcos,
  Yale Bright Star and Gliese catalogues.
The output files keep only the columns the engine tools use.
"""
from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path

import httpx

OUT = Path(__file__).resolve().parent.parent / "app" / "data" / "space"
CELESTIA = "https://raw.githubusercontent.com/CelestiaProject/CelestiaContent/master/data/"
HYG = "https://raw.githubusercontent.com/astronexus/HYG-Database/main/hyg/CURRENT/hygdata_v41.csv"

# Major moons we render, with the reference plane their Celestia elements are given in.
# "ecliptic" = ecliptic J2000 of the parent (Celestia's default), "equator_j2000" = Earth's mean equator J2000,
# "planet_equator" = the parent planet's IAU equator (node measured from the ICRF equator).
MOONS = {
    "Phobos": "planet_equator", "Deimos": "planet_equator",
    "Io": "ecliptic", "Europa": "ecliptic", "Ganymede": "ecliptic", "Callisto": "ecliptic",
    "Mimas": "ecliptic", "Enceladus": "ecliptic", "Tethys": "ecliptic", "Dione": "ecliptic", "Rhea": "ecliptic",
    "Titan": "ecliptic", "Hyperion": "ecliptic", "Iapetus": "ecliptic", "Phoebe": "ecliptic",
    "Miranda": "ecliptic", "Ariel": "ecliptic", "Umbriel": "ecliptic", "Titania": "ecliptic", "Oberon": "ecliptic",
    "Proteus": "ecliptic", "Triton": "ecliptic", "Nereid": "ecliptic",
    "Charon": None, "Nix": None, "Hydra": None, "Kerberos": None, "Styx": None,  # frame read from the file
}
DWARFS = ["Ceres", "Haumea", "Makemake", "Eris", "Gonggong", "Quaoar", "Sedna"]
ASTEROIDS = ["2 Pallas", "3 Juno", "4 Vesta", "10 Hygiea", "16 Psyche", "21 Lutetia", "243 Ida", "433 Eros",
             "951 Gaspra", "25143 Itokawa", "101955 Bennu", "162173 Ryugu",
             "4179 Toutatis", "486958 Arrokoth", "2060 Chiron", "10199 Chariklo"]
COMETS = ["1P Halley", "2P Encke", "19P Borrelly", "55P Tempel-Tuttle", "109P Swift-Tuttle", "46P Wirtanen",
          "C 1995 O1 (Hale-Bopp)", "C 1996 B2 (Hyakutake)", "C 2020 F3 (NEOWISE)", "C 2023 A3 (Tsuchinshan-ATLAS)",
          "C 2006 P1 (McNaught)"]
ORBIT_KEYS = ["Epoch", "Period", "SemiMajorAxis", "Eccentricity", "Inclination", "AscendingNode",
              "ArgOfPericenter", "MeanAnomaly"]


def fetch(url: str) -> str:
    r = httpx.get(url, timeout=300, follow_redirects=True)
    r.raise_for_status()
    return r.text


def ssc_objects(text: str) -> dict[str, dict]:
    """Parse the objects of a Celestia .ssc file (commented-out orbit blocks included)."""
    text = re.sub(r"(?m)^([ \t]*[^#\s\n][^#\n]*?)[ \t]*#.*$", r"\1", text)  # drop trailing comments
    text = re.sub(r"(?m)^[ \t]*#", "\t", text)  # un-comment "Overridden by CustomOrbit" element blocks
    out = {}
    for m in re.finditer(r'(?m)^"([^"]+)"\s+"(Sol[^"]*)"\s*\n\{(.*?)\n\}', text, re.S):
        names, parent, body = m.groups()
        name = names.split(":")[0]
        orbit = re.search(r"EllipticalOrbit\s*\{([^}]*)\}", body)
        if not orbit:
            continue
        el = {}
        for k in ORBIT_KEYS:
            km = re.search(rf"\b{k}\s+([-+\d.eE]+)", orbit.group(1))
            if km:
                el[k] = float(km.group(1))
        if len(el) < len(ORBIT_KEYS):
            continue
        frame = re.search(r"OrbitFrame\s*\{\s*(\w+)", body)
        radius = re.search(r"\bRadius\s+([\d.eE+]+)", body)
        axes = re.search(r"SemiAxes\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)", body)
        mass = re.search(r"Mass(?:<kg>)?\s+([\d.eE+]+)", body)
        r_km = float(radius.group(1)) if radius else (sum(map(float, axes.groups())) / 3 if axes else None)
        out.setdefault(name, {"names": names, "parent": parent, "orbit": el, "radius_km": r_km,
                              "mass_kg": float(mass.group(1)) if mass else None,
                              "frame": frame.group(1) if frame else None})
    return out


def moons() -> list[dict]:
    objs = {**ssc_objects(fetch(CELESTIA + "solarsys.ssc")), **ssc_objects(fetch(CELESTIA + "dwarfplanets.ssc"))}
    rows = []
    for name, frame in MOONS.items():
        o = objs[name]
        if frame is None:
            frame = {"EquatorJ2000": "equator_j2000", "EclipticJ2000": "ecliptic", None: "ecliptic"}[o["frame"]]
        el = o["orbit"]
        rows.append({"id": name.lower(), "name": name, "parent": o["parent"].split("/")[-1].lower(),
                     "radius_km": round(o["radius_km"], 2), "mass_kg": o["mass_kg"], "frame": frame,
                     "epoch_jd": el["Epoch"], "period_days": el["Period"], "a_km": el["SemiMajorAxis"],
                     "e": el["Eccentricity"], "i_deg": el["Inclination"], "node_deg": el["AscendingNode"],
                     "argp_deg": el["ArgOfPericenter"], "m0_deg": el["MeanAnomaly"]})
    return rows


def small_bodies() -> list[dict]:
    rows = []
    groups = (("dwarf planet", "dwarfplanets.ssc", DWARFS), ("asteroid", "asteroids.ssc", ASTEROIDS),
              ("asteroid", "outersys.ssc", ASTEROIDS), ("comet", "comets.ssc", COMETS))
    seen = set()
    for kind, fname, wanted in groups:
        objs = ssc_objects(fetch(CELESTIA + fname))
        for key, o in objs.items():
            full = o["names"].split(":")
            label = next((w for w in wanted if w == key or w in full), None)
            if label is None or label in seen or o["parent"] != "Sol":
                continue
            seen.add(label)
            el = o["orbit"]
            display = re.sub(r"^C \d{4} \w+ \((.*)\)$", r"\1", label)  # "C 1995 O1 (Hale-Bopp)" → "Hale-Bopp"
            display = re.sub(r"^\d+ ", "", display) if kind != "comet" else display
            kind_here = "centaur" if label in ("2060 Chiron", "10199 Chariklo") else \
                "Kuiper belt object" if label == "486958 Arrokoth" else \
                kind
            rows.append({"id": re.sub(r"[^a-z0-9]+", "_", display.lower()).strip("_"), "name": display,
                         "designation": label, "kind": kind_here,
                         "radius_km": round(o["radius_km"], 3) if o["radius_km"] else None,
                         "epoch_jd": el["Epoch"], "period_days": el["Period"] * 365.25, "a_au": el["SemiMajorAxis"],
                         "e": el["Eccentricity"], "i_deg": el["Inclination"], "node_deg": el["AscendingNode"],
                         "argp_deg": el["ArgOfPericenter"], "m0_deg": el["MeanAnomaly"]})
    missing = set(DWARFS + ASTEROIDS + COMETS) - seen
    if missing:
        raise SystemExit(f"not found in Celestia data: {sorted(missing)}")
    return rows


def dsc(text: str, kind: str) -> list[dict]:
    rows = []
    for m in re.finditer(rf'(?m)^{kind}\s+"([^"]+)"\s*\{{(.*?)\}}', text, re.S):
        names, body = m.groups()
        get = lambda k: (re.search(rf"\b{k}\s+\"?([-+\w.]+)", body) or [None, None])[1]
        rows.append({"name": names.split(":")[0], "type": get("Type") or "", "ra_h": float(get("RA")),
                     "dec_deg": float(get("Dec")), "dist_ly": float(get("Distance")),
                     "radius_ly": float(get("Radius")), "abs_mag": float(get("AbsMag") or "nan")})
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def stars() -> list[dict]:
    rows = []
    for r in csv.DictReader(io.StringIO(fetch(HYG))):
        dist = float(r["dist"] or 1e5)
        mag = float(r["mag"] or 99)
        if r["proper"] == "Sol" or dist >= 1e5 or not (mag <= 7.0 or dist <= 30):
            continue
        rows.append({"hip": r["hip"], "name": r["proper"], "bayer": r["bayer"], "flam": r["flam"], "con": r["con"],
                     "ra_h": round(float(r["ra"]), 6), "dec_deg": round(float(r["dec"]), 5), "dist_pc": round(dist, 4),
                     "mag": mag, "abs_mag": round(float(r["absmag"]), 3), "spect": r["spect"], "ci": r["ci"]})
    return rows


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "moons.json").write_text(json.dumps(moons(), indent=1))
    (OUT / "small_bodies.json").write_text(json.dumps(small_bodies(), indent=1))
    write_csv(OUT / "stars.csv", stars())
    write_csv(OUT / "galaxies.csv", dsc(fetch(CELESTIA + "galaxies.dsc"), "Galaxy"))
    write_csv(OUT / "globulars.csv", dsc(fetch(CELESTIA + "globulars.dsc"), "Globular"))
    print("wrote", sorted(p.name for p in OUT.iterdir()))
