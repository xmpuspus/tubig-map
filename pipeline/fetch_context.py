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

CORRECTED AGAIN 2026-07-20 (round 5), after obtaining the primary document.

nwrb.gov.ph returns 403, but the Internet Archive has the resolution, and a
convergence critic pointed that out. It is a scanned PDF titled

    "RESOLUTION NO. 001-0904, Policy Recommendations for Metro Manila
     Critical Areas", approved 22 September 2004

and it says two things this project had wrong.

First, it is NOT a ban. It adopts eight policy recommendations on how water
permit applications are processed, keyed jointly to whether an area is critical
and whether MWSS already serves it adequately. Paragraph 1 revokes or suspends
permits "in areas adequately served by MWSS, regardless of whether or not
located in critical areas". The Supreme Court in G.R. No. 208383 (2016)
characterised NWRB as having imposed "a total ban on deep water drilling in
Metro Manila, as well as Guiguinto, Bocaue, Marilao, and Meycauayan in Bulacan,
and Dasmarinas in Cavite", but that is the Court describing NWRB's practice,
including later issuances, not a quotation of this resolution's operative text.

Second, the areas are sub-city, not whole Metro Manila. The resolution names
eight critical areas verbatim:

    Area 1: Guiguinto, Bulacan
    Area 2: Bocaue and Marilao, Bulacan
    Area 3: Meycauayan, Bulacan and North Caloocan
    Area 4: Navotas, Caloocan and West Quezon City
    Area 5: Makati, Mandaluyong, Pasig and Pateros
    Area 6: Paranaque and Pasay
    Area 7: Las Pinas and Muntinlupa
    Area 8: Dasmarinas, Cavite

So Manila, Malabon, Marikina, San Juan, Taguig and Valenzuela are NOT in the
2004 designation, and drawing Metro Manila whole overstated it exactly as the
five-province version had, one scale down.

This layer now carries the designated LGUs as status "designated", and Metro
Manila as a whole plus Rizal as status "reported", which is the extent the
Supreme Court and contemporaneous press describe for the later ban but which no
located document defines. Laguna stays dropped: no source names it.
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

# The eight critical areas designated verbatim in NWRB Res. 001-0904 (2004),
# resolved to the LGUs that OSM can draw. "North Caloocan" and "West Quezon
# City" are sub-city districts with no admin boundary, so Caloocan and Quezon
# City are drawn whole and flagged as partial in the layer.
DESIGNATED = [
    "Guiguinto",
    "Bocaue",
    "Marilao",
    "Meycauayan",  # Bulacan
    "Caloocan",
    "Navotas",
    "Quezon City",  # Areas 3, 4
    "Makati",
    "Mandaluyong",
    "Pasig",
    "Pateros",  # Area 5
    "Parañaque",
    "Pasay",  # Area 6
    "Las Piñas",
    "Muntinlupa",  # Area 7
    "Dasmariñas",  # Area 8
]
PARTIAL = {"Caloocan": "North Caloocan only", "Quezon City": "West Quezon City only"}
# Wider extent the Supreme Court and 2008 press describe for a later ban, with
# no locatable defining document.
REPORTED = ["Metro Manila", "Rizal"]

# Bound every query to Luzon. Without this, "Pateros" resolves to Pateros,
# Washington State, which is larger than Metro Manila's smallest LGU and so wins
# any "keep the biggest polygon" rule. It shipped a US town into the map once.
PH_BBOX = "(13.8,120.5,15.4,121.6)"
_LGU = "".join(f'  relation["name"="{n}"]["boundary"="administrative"]{PH_BBOX};\n' for n in DESIGNATED)
QUERY = f"""
[out:json][timeout:300];
(
{_LGU}  relation["name"="Metro Manila"]["boundary"="administrative"]["admin_level"="3"]{PH_BBOX};
  relation["name"="Rizal"]["boundary"="administrative"]["admin_level"="4"]{PH_BBOX};
);
out geom;
"""

SOURCE = {
    "designated": "critical area designated in NWRB Res. 001-0904 (22 Sept 2004)",
    "reported": (
        "wider extent described by SC G.R. No. 208383 (2016) and 2008 press; no defining document located"
    ),
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

    want = {n: "designated" for n in DESIGNATED} | {n: "reported" for n in REPORTED}
    gdf = gdf[gdf["name"].isin(want)].copy()
    gdf["status"] = gdf["name"].map(want)
    gdf["source"] = gdf["status"].map(SOURCE)
    gdf["extent_note"] = gdf["name"].map(PARTIAL)

    # OSM returns both a municipality and a same-named province in places
    # (Rizal is also a Bulacan municipality). Keep the largest polygon per name,
    # except Rizal where the province is the intended feature anyway.
    gdf["_area"] = gdf.to_crs(32651).geometry.area
    gdf = gdf.sort_values("_area", ascending=False).drop_duplicates(subset="name", keep="first")
    gdf = gdf[["name", "status", "source", "extent_note", "geometry"]].sort_values("name")
    gdf["geometry"] = gdf.geometry.simplify(0.0005)
    gdf.to_file(OUT, driver="GeoJSON")

    # Fail loudly rather than shipping a polygon from another country.
    outside = [
        row["name"]
        for _, row in gdf.iterrows()
        if not (
            117 < row.geometry.bounds[0]
            and row.geometry.bounds[2] < 127
            and 4 < row.geometry.bounds[1]
            and row.geometry.bounds[3] < 21
        )
    ]
    if outside:
        raise SystemExit(f"geometry outside the Philippines for: {outside}")

    for _, row in gdf.iterrows():
        print(f"{row['name']:<16} {row['status']:<9} {row.geometry.geom_type}")
    missing = set(want) - set(gdf["name"])
    if missing:
        print(f"WARNING not returned by Overpass: {sorted(missing)}")
    print(f"areas={len(gdf)} bytes={OUT.stat().st_size}")


if __name__ == "__main__":
    main()
