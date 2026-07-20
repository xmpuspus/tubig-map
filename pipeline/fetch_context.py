"""Fetch NWRB deep-well moratorium area boundaries from OSM.

The moratorium covers Metro Manila, Bulacan, Cavite, Rizal, and Laguna
(NWRB announcements; see docs/SOURCES.md). Metro Manila is an OSM
admin_level=3 region; the four provinces are admin_level=4. Geometries are
simplified for web delivery.
"""

import json
from pathlib import Path

import geopandas as gpd
import osm2geojson
import requests

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "moratorium_overpass.json"
OUT = ROOT / "data" / "moratorium_areas.geojson"
UA = {"User-Agent": "tubig-map/0.1 (civic-data research; xpuspus@gmail.com)"}

QUERY = """
[out:json][timeout:180];
(
  relation["name"="Metro Manila"]["boundary"="administrative"]["admin_level"="3"];
  relation["name"="Bulacan"]["boundary"="administrative"]["admin_level"="4"];
  relation["name"="Cavite"]["boundary"="administrative"]["admin_level"="4"];
  relation["name"="Rizal"]["boundary"="administrative"]["admin_level"="4"];
  relation["name"="Laguna"]["boundary"="administrative"]["admin_level"="4"];
);
out geom;
"""


def main():
    if not RAW.exists():
        r = requests.post(
            "https://overpass-api.de/api/interpreter", data={"data": QUERY}, headers=UA, timeout=200
        )
        r.raise_for_status()
        RAW.parent.mkdir(parents=True, exist_ok=True)
        RAW.write_bytes(r.content)

    fc = osm2geojson.json2geojson(json.loads(RAW.read_text()))
    gdf = gpd.GeoDataFrame.from_features(fc["features"], crs="EPSG:4326")
    gdf["name"] = gdf["tags"].apply(lambda t: (t or {}).get("name", ""))
    gdf = gdf[["name", "geometry"]]
    gdf["geometry"] = gdf.geometry.simplify(0.001)  # ~100 m, plenty for a context fill
    gdf.to_file(OUT, driver="GeoJSON")
    for _, row in gdf.iterrows():
        print(f"{row['name']:<14} {row.geometry.geom_type}")
    print(f"areas={len(gdf)} bytes={OUT.stat().st_size}")


if __name__ == "__main__":
    main()
