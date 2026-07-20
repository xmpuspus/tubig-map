"""Build data/data_centers.geojson from a hand-curated site list.

OSM's telecom=data_center coverage for the Philippines is junk (mistagged ISP
shops), so sites come from operator press releases and reporting, geocoded via
Nominatim with a per-site precision label. Every site carries its source URL.
No water figures are invented: water_disclosure is null unless an operator
actually published one.
"""

import json
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "data_centers.geojson"
CACHE = ROOT / "data" / "raw" / "geocode_cache.json"
UA = {"User-Agent": "tubig-map/0.1 (civic-data research; xpuspus@gmail.com)"}

# status: operational | building | planned. mw is null where undisclosed.
# water_disclosure: the ONLY operator-published water metric in the PH is
# Digital Edge NARRA1's WUE. Everything else is null or qualitative.
SITES = [
    dict(
        name="VITRO Sta. Rosa",
        operator="ePLDT",
        city="Santa Rosa",
        province="Laguna",
        status="operational",
        mw=50,
        water_disclosure=None,
        query="Santa Rosa, Laguna, Philippines",
        precision="city",
        source="https://www.datacenterdynamics.com/en/news/pldt-launches-sta-rosa-data-center/",
    ),
    dict(
        name="VITRO Paranaque",
        operator="ePLDT",
        city="Paranaque",
        province="Metro Manila",
        status="operational",
        mw=None,
        water_disclosure=None,
        lat=14.463,
        lon=121.0275,
        precision="building (OSM way 553651276)",
        source="https://www.openstreetmap.org/way/553651276",
    ),
    dict(
        name="STT GDC Fairview",
        operator="STT GDC / Globe / Ayala",
        city="Quezon City",
        province="Metro Manila",
        status="building",
        mw=124,
        water_disclosure="rainwater harvesting, unquantified",
        query="Fairview, Quezon City, Philippines",
        precision="district",
        source="https://pcij.org/2026/01/11/data-centers-raise-concerns/",
    ),
    dict(
        name="STT GDC Makati",
        operator="STT GDC / Globe / Ayala",
        city="Makati",
        province="Metro Manila",
        status="operational",
        mw=1.2,
        water_disclosure="rainwater harvesting, unquantified",
        query="Makati, Philippines",
        precision="city",
        source="https://pcij.org/2026/01/11/data-centers-raise-concerns/",
    ),
    dict(
        name="NARRA1",
        operator="Digital Edge",
        city="Binan",
        province="Laguna",
        status="operational",
        mw=10,
        water_disclosure="WUE 1.355 L/kWh (annualized, operator-published)",
        query="Laguna Technopark, Binan, Laguna, Philippines",
        precision="campus",
        source="https://datacentremagazine.com/company-reports/digital-edge-data-centre-sustainability-front-and-centre",
    ),
    dict(
        name="DH-MNL1",
        operator="Digital Halo",
        city="Cainta",
        province="Rizal",
        status="operational",
        mw=None,
        water_disclosure=None,
        query="Cainta, Rizal, Philippines",
        precision="city",
        source="https://www.eco-business.com/news/high-costs-higher-risks-can-the-philippines-power-its-data-centre-hub-ambitions/",
    ),
    dict(
        name="Equinix MN1",
        operator="Equinix",
        city="Carmona",
        province="Cavite",
        status="operational",
        mw=None,
        water_disclosure=None,
        query="Carmona, Cavite, Philippines",
        precision="city",
        source="https://www.datacentermap.com/philippines/",
    ),
    dict(
        name="Equinix MN3",
        operator="Equinix",
        city="Manila",
        province="Metro Manila",
        status="operational",
        mw=None,
        water_disclosure=None,
        query="Manila, Philippines",
        precision="city",
        source="https://www.datacentermap.com/philippines/",
    ),
    dict(
        name="EdgeConneX Manila",
        operator="EdgeConneX",
        city="Manila (Ermita)",
        province="Metro Manila",
        status="operational",
        mw=None,
        water_disclosure=None,
        query="Ermita, Manila, Philippines",
        precision="district",
        source="https://www.datacentermap.com/philippines/",
    ),
    dict(
        name="YCO Cloud Centers Malvar",
        operator="YCO",
        city="Malvar",
        province="Batangas",
        status="operational",
        mw=None,
        water_disclosure=None,
        query="Light Industry and Science Park IV, Malvar, Batangas, Philippines",
        precision="campus",
        source="https://www.datacentermap.com/philippines/",
    ),
    dict(
        name="Reliance IT Center",
        operator="Converge ICT",
        city="Pasig",
        province="Metro Manila",
        status="operational",
        mw=None,
        water_disclosure=None,
        query="Reliance IT Center, Pasig, Philippines",
        precision="building",
        source="https://www.datacentermap.com/philippines/",
    ),
    dict(
        name="DITO edge Mandaue",
        operator="DITO",
        city="Mandaue",
        province="Cebu",
        status="operational",
        mw=None,
        water_disclosure=None,
        query="Mandaue, Cebu, Philippines",
        precision="city",
        source="https://www.datacentermap.com/philippines/",
    ),
    dict(
        name="DITO CO64",
        operator="DITO",
        city="Butuan",
        province="Agusan del Norte",
        status="operational",
        mw=None,
        water_disclosure=None,
        lat=8.9365,
        lon=125.5394,
        precision="building (OSM way 842083113)",
        source="https://www.openstreetmap.org/way/842083113",
    ),
    dict(
        name="VITRO Trece Martires",
        operator="ePLDT",
        city="Trece Martires",
        province="Cavite",
        status="planned",
        mw=100,
        water_disclosure=None,
        query="Trece Martires, Cavite, Philippines",
        precision="city",
        source="https://www.mordorintelligence.com/industry-reports/philippines-data-center-market",
    ),
]


def geocode(query, cache):
    if query in cache:
        return cache[query]
    r = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": query, "format": "json", "limit": 1},
        headers=UA,
        timeout=30,
    )
    r.raise_for_status()
    hits = r.json()
    if not hits:
        cache[query] = None
        return None
    cache[query] = {
        "lat": float(hits[0]["lat"]),
        "lon": float(hits[0]["lon"]),
        "display": hits[0]["display_name"],
    }
    time.sleep(1.1)
    return cache[query]


def main():
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    features = []
    for s in SITES:
        if "lat" not in s:
            hit = geocode(s["query"], cache)
            if hit is None:
                print(f"GEOCODE MISS: {s['name']} ({s['query']})")
                continue
            s["lat"], s["lon"] = hit["lat"], hit["lon"]
            print(
                f"{s['name']:<24} -> {s['lat']:.4f},{s['lon']:.4f}  [{s['precision']}]  {hit['display'][:70]}"
            )
        props = {k: v for k, v in s.items() if k not in ("lat", "lon", "query")}
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [s["lon"], s["lat"]]},
                "properties": props,
            }
        )
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, indent=1))
    OUT.write_text(json.dumps({"type": "FeatureCollection", "features": features}, indent=1))
    n_water = sum(1 for f in features if f["properties"]["water_disclosure"])
    print(f"\nsites={len(features)} with_any_water_disclosure={n_water}")


if __name__ == "__main__":
    main()
