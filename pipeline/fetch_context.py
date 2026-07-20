"""Fetch the NWRB deep-well restriction areas from OSM, at the level they exist.

WHAT CHANGED AND WHY (2026-07-20, doubt loop round 1)

v1 drew five whole provinces (Metro Manila, Bulacan, Cavite, Rizal, Laguna) and
labelled them "NWRB deep-well moratorium areas". The only source was a law firm
article that says "Certain areas, especially in Metro Manila and nearby
provinces (e.g., Bulacan, Cavite, Rizal, Laguna), have been declared critical or
over-extracted", which is hedged, illustrative, and cites no resolution number.
Turning that into five hard province polygons overstated the restriction badly:
it asserted uniform province-wide coverage that no source supports, and it
inflated every "inside the restricted area" count on the site.

The primary evidence available is the Supreme Court's quotation of NWRB
Resolution No. 001-0904 in First Mega Holdings Corp. v. Guiguinto Water District,
G.R. No. 208383, 8 June 2016 (786 Phil. 746):

    "the NWRB had imposed a total ban on deep water drilling in Metro Manila,
     as well as Guiguinto, Bocaue, Marilao, and Meycauayan in Bulacan, and
     Dasmarinas in Cavite to prevent over-extraction of ground water."

So the named coverage is Metro Manila as a region, four Bulacan municipalities,
and one Cavite city. Laguna appears in no primary source found and is dropped.
Rizal is reported to have been added by a later amendment extending the ban to
"Metro Manila and Rizal towns", but the amending resolution number and the
specific towns are not recoverable from public sources, so Rizal is carried as
a separate, explicitly labelled "reported" area rather than as a confirmed one.

nwrb.gov.ph returns 403 to automated fetches, so the resolution PDF itself is a
documented boundary in docs/DOUBT-LOOP.md.
"""

import json
from pathlib import Path

import geopandas as gpd
import osm2geojson
import requests

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "moratorium_overpass_v2.json"
OUT = ROOT / "data" / "moratorium_areas.geojson"
UA = {"User-Agent": "tubig-map/0.2 (civic-data research; xpuspus@gmail.com)"}

# Named in the Supreme Court's quotation of NWRB Res. 001-0904.
NAMED = ["Metro Manila", "Guiguinto", "Bocaue", "Marilao", "Meycauayan", "Dasmariñas"]
# Reported later extension; specific municipalities not identified in any source found.
REPORTED = ["Rizal"]

QUERY = """
[out:json][timeout:240];
(
  relation["name"="Metro Manila"]["boundary"="administrative"]["admin_level"="3"];
  relation["name"="Guiguinto"]["boundary"="administrative"];
  relation["name"="Bocaue"]["boundary"="administrative"];
  relation["name"="Marilao"]["boundary"="administrative"];
  relation["name"="Meycauayan"]["boundary"="administrative"];
  relation["name"="Dasmariñas"]["boundary"="administrative"];
  relation["name"="Rizal"]["boundary"="administrative"]["admin_level"="4"];
);
out geom;
"""

SOURCE = {
    "named": "NWRB Res. 001-0904, as quoted in SC G.R. No. 208383 (2016)",
    "reported": "reported later extension; amending resolution not located",
}


def main():
    if not RAW.exists():
        r = requests.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": QUERY},
            headers=UA,
            timeout=260,
        )
        r.raise_for_status()
        RAW.parent.mkdir(parents=True, exist_ok=True)
        RAW.write_bytes(r.content)

    fc = osm2geojson.json2geojson(json.loads(RAW.read_text()))
    gdf = gpd.GeoDataFrame.from_features(fc["features"], crs="EPSG:4326")
    gdf["name"] = gdf["tags"].apply(lambda t: (t or {}).get("name", ""))
    gdf["admin_level"] = gdf["tags"].apply(lambda t: (t or {}).get("admin_level", ""))

    want = {n: "named" for n in NAMED} | {n: "reported" for n in REPORTED}
    gdf = gdf[gdf["name"].isin(want)].copy()
    gdf["status"] = gdf["name"].map(want)
    gdf["source"] = gdf["status"].map(SOURCE)

    # OSM returns both a municipality and a same-named province in places
    # (Rizal is also a Bulacan municipality). Keep the largest polygon per name,
    # except Rizal where the province is the intended feature anyway.
    gdf["_area"] = gdf.to_crs(32651).geometry.area
    gdf = gdf.sort_values("_area", ascending=False).drop_duplicates(subset="name", keep="first")
    gdf = gdf[["name", "status", "source", "geometry"]].sort_values("name")
    gdf["geometry"] = gdf.geometry.simplify(0.0005)
    gdf.to_file(OUT, driver="GeoJSON")

    for _, row in gdf.iterrows():
        print(f"{row['name']:<16} {row['status']:<9} {row.geometry.geom_type}")
    missing = set(want) - set(gdf["name"])
    if missing:
        print(f"WARNING not returned by Overpass: {sorted(missing)}")
    print(f"areas={len(gdf)} bytes={OUT.stat().st_size}")


if __name__ == "__main__":
    main()
