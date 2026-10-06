"""Real telescope images of nebulae and star clusters for the Universe Map.

Source: the Stellarium nebula texture set (github.com/Stellarium/stellarium, nebulae/default), which records each
image's credit and its exact position on the sky. Only images whose credit is an openly licensed observatory are
kept: NASA/ESA Hubble (public domain / CC BY 4.0), ESO (CC BY 4.0), NOIRLab/KPNO/CTIO (CC BY 4.0), SDSS and
2MASS (free with acknowledgement). Images from the Digitized Sky Survey and from individual photographers are
left out. Galaxies are left out too: the map draws its galaxies itself (frontend/js/space/galaxyart.js).

Writes frontend/assets/dso/<id>.jpg and app/data/space/dso_images.json.
Run:  python scripts/build_dso_images.py
"""
from __future__ import annotations

import csv
import io
import json
import math
import re
from pathlib import Path

import httpx
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://raw.githubusercontent.com/Stellarium/stellarium/master/nebulae/default/"
OUT_IMG = ROOT / "frontend" / "assets" / "dso"
OUT_JSON = ROOT / "app" / "data" / "space" / "dso_images.json"
FREE = re.compile(r"(ESO|Hubble|NASA|ESA\b|NOIRLab|KPNO|CTIO|Sloan|SDSS|2MASS|Spitzer|Webb|JWST|Chandra)", re.I)
NOT_FREE = re.compile(r"(Digitized Sky Survey|DSS)", re.I)
GALAXY_TYPES = {"Galaxy", "Galaxy pair", "Galaxy triplet", "Galaxy group"}


def unit(ra, dec):
    a, d = math.radians(ra), math.radians(dec)
    return (math.cos(d) * math.cos(a), math.cos(d) * math.sin(a), math.sin(d))


def centre_and_size(corners):
    v = [unit(ra, dec) for ra, dec in corners]
    c = [sum(x[i] for x in v) / 4 for i in range(3)]
    n = math.sqrt(sum(x * x for x in c))
    c = [x / n for x in c]
    ra = math.degrees(math.atan2(c[1], c[0])) % 360
    dec = math.degrees(math.asin(c[2]))
    ang = lambda a, b: math.degrees(math.acos(max(-1, min(1, sum(p * q for p, q in zip(a, b))))))  # noqa: E731
    return ra, dec, ang(v[0], v[1]), ang(v[1], v[2])


def object_id(url: str) -> str | None:
    m = re.match(r"^(m|n|i)(\d+)", url.lower())
    if not m:
        return None
    return {"m": "M", "n": "NGC", "i": "IC"}[m.group(1)] + f" {int(m.group(2))}"


def main() -> None:
    tex = json.loads(httpx.get(BASE + "textures.json", timeout=60).text, strict=False)
    with (ROOT / "app" / "data" / "space" / "deepsky.csv").open() as f:
        rows = list(csv.DictReader(f))
    by_id = {}
    for r in rows:
        by_id[r["id"]] = r
        if r["messier"]:
            by_id[r["messier"]] = r
    OUT_IMG.mkdir(parents=True, exist_ok=True)
    out = []
    for s in tex["subTiles"]:
        credit = {k.lower(): v for k, v in s.get("imageCredits", {}).items()}.get("short", "")
        if not FREE.search(credit) or NOT_FREE.search(credit):
            continue
        oid = object_id(s["imageUrl"])
        row = by_id.get(oid) if oid else None
        if row is None or row["type"] in GALAXY_TYPES:
            continue
        ra, dec, w, h = centre_and_size(s["worldCoords"][0])
        r = httpx.get(BASE + s["imageUrl"], timeout=60)
        if r.status_code != 200:
            continue
        im = Image.open(io.BytesIO(r.content)).convert("RGB")
        im.thumbnail((640, 640))
        name = re.sub(r"[^a-z0-9]+", "-", (row["messier"] or row["id"]).lower()).strip("-")
        im.save(OUT_IMG / f"{name}.jpg", quality=82, optimize=True, progressive=True)
        out.append({"id": row["id"], "messier": row["messier"], "name": row["common"] or row["messier"] or row["id"],
                    "type": row["type"], "file": f"{name}.jpg", "ra_deg": round(ra, 5), "dec_deg": round(dec, 5),
                    "width_deg": round(w, 5), "height_deg": round(h, 5), "credit": credit})
        print(name, row["type"], credit[:50])
    OUT_JSON.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(len(out), "images")


if __name__ == "__main__":
    main()
