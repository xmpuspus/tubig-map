"""Fetch PH golf course polygons from OSM and build data/golf_courses.geojson.

Reproducible source for the golf layer: Overpass query for leisure=golf_course
inside the Philippines admin boundary, area in hectares computed in EPSG:32651,
DENR May 2024 conservation-directive courses flagged by name match.
"""

import json
import re
import sys
from pathlib import Path

import geopandas as gpd
import osm2geojson
import requests

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "golf_overpass.json"
OUT = ROOT / "data" / "golf_courses.geojson"

OVERPASS = "https://overpass-api.de/api/interpreter"
QUERY = """
[out:json][timeout:180];
area["name:en"="Philippines"]["boundary"="administrative"]["admin_level"="2"]->.a;
(way["leisure"="golf_course"](area.a);relation["leisure"="golf_course"](area.a););
out geom;
"""
UA = {"User-Agent": "tubig-map/0.1 (civic-data research; xpuspus@gmail.com)"}

# The 13 courses named in the DENR water-conservation directive, May 2024.
# Source: GMA News 2024-05-07 (denr-golf-courses-el-nino/905945).
DENR_13 = {
    "camp-aguinaldo": r"aguinaldo",
    "veterans": r"veterans",
    "army-kagitingan": r"kagitingan|army.*golf",
    "villamor": r"villamor",
    "club-intramuros": r"intramuros",
    "philippine-navy": r"navy.*golf|philippine navy",
    "wack-wack": r"wack[- ]?wack",
    "manila-golf": r"^manila golf",
    "valley-golf": r"^valley golf",
    "sun-valley": r"sun valley",
    "alabang": r"alabang",
    "foresthills": r"forest ?hills",
    "eastridge": r"east ?ridge",
}


def fetch_raw():
    r = requests.post(OVERPASS, data={"data": QUERY}, headers=UA, timeout=200)
    r.raise_for_status()
    RAW.parent.mkdir(parents=True, exist_ok=True)
    RAW.write_bytes(r.content)


def denr_match(name):
    low = name.lower()
    for slug, pat in DENR_13.items():
        if re.search(pat, low):
            return slug
    return None


def main():
    if "--refetch" in sys.argv or not RAW.exists():
        fetch_raw()

    raw = json.loads(RAW.read_text())
    fc = osm2geojson.json2geojson(raw)
    gdf = gpd.GeoDataFrame.from_features(fc["features"], crs="EPSG:4326")

    # osm2geojson nests tags under properties.tags
    tags = gdf["tags"].apply(lambda t: t or {})
    gdf["name"] = tags.apply(lambda t: t.get("name", ""))
    gdf["osm_type"] = gdf["type"]
    gdf["osm_id"] = gdf["id"]

    # polygons only; OSM occasionally has stray points/lines under this tag
    gdf = gdf[gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].copy()

    gdf["hectares"] = gdf.to_crs(epsg=32651).area / 10_000
    gdf["denr_2024"] = gdf["name"].apply(denr_match)

    keep = gdf[["name", "osm_type", "osm_id", "hectares", "denr_2024", "geometry"]]
    keep = keep.sort_values("hectares", ascending=False).reset_index(drop=True)
    keep.to_file(OUT, driver="GeoJSON")

    matched = keep[keep["denr_2024"].notna()]
    print(
        f"features={len(keep)} named={int((keep['name'] != '').sum())} total_ha={keep['hectares'].sum():.0f}"
    )
    print(f"denr_13 matched {matched['denr_2024'].nunique()}/13:")
    for _, row in matched.iterrows():
        print(f"  {row['denr_2024']:<18} <- {row['name']} ({row['hectares']:.0f} ha)")
    missing = set(DENR_13) - set(matched["denr_2024"])
    if missing:
        print(f"denr_13 NOT found in OSM: {sorted(missing)}")


if __name__ == "__main__":
    main()
