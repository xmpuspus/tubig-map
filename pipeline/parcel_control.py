"""A second frame for the same question: real green-space parcels, not pixels.

pipeline/matched_control.py answered "is golf turf greener than nearby grass?"
by masking Sentinel-2 to WorldCover grass pixels inside a 1 km ring. That is one
frame. The site then went on naming a parcel-based control as "the obvious next
study" while already leading with the pixel answer, which is the same
name-the-fix-and-stop this loop keeps catching.

This builds the parcel frame. Instead of grass pixels wherever they fall, it
uses whole managed green-space parcels from OSM (parks, cemeteries, pitches,
meadows, recreation grounds), filtered to those WorldCover agrees are mostly
grass, and measures NDVI over each parcel in the same Feb-Apr windows with the
same cloud mask.

Why it matters that this is a different frame rather than a different threshold:
a parcel is a managed unit with an owner and a mowing regime, so it is a much
closer counterfactual to a golf course than an arbitrary grass pixel that might
be a road verge or a gap between buildings. If the two frames disagree, the
honest uncertainty on the surviving claim is wider than a threshold sweep of one
frame suggests, and that is worth publishing.

Writes data/parcel_control.csv, one row per golf course, carrying the NDVI of
the green-space parcels within 5 km of it.
"""

import csv
import json
import sys
from pathlib import Path

import ee
import geopandas as gpd
import osm2geojson
import requests

sys.path.insert(0, str(Path(__file__).parent))
from _gee_init import init  # noqa: E402
from ndvi_anomaly import WINDOWS, masked_ndvi_median  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "greenspace_overpass.json"
OUT_CSV = ROOT / "data" / "parcel_control.csv"
UA = {"User-Agent": "tubig-map/0.3 (civic-data research; xpuspus@gmail.com)"}

NEAR_KM = 5.0
MIN_HA = 2.0
MIN_GRASS = 0.5  # WorldCover must agree the parcel is mostly grass
BATCH = 60

# Managed open green space, excluding anything that is obviously not comparable
# (golf itself, forest, farmland).
QUERY = """
[out:json][timeout:300];
(
  way["leisure"="park"](13.8,120.5,15.4,121.6);
  relation["leisure"="park"](13.8,120.5,15.4,121.6);
  way["landuse"="cemetery"](13.8,120.5,15.4,121.6);
  relation["landuse"="cemetery"](13.8,120.5,15.4,121.6);
  way["leisure"="pitch"](13.8,120.5,15.4,121.6);
  way["landuse"="meadow"](13.8,120.5,15.4,121.6);
  way["landuse"="grass"](13.8,120.5,15.4,121.6);
  way["leisure"="recreation_ground"](13.8,120.5,15.4,121.6);
);
out geom;
"""


def fetch_parcels():
    if not RAW.exists():
        r = requests.post(
            "https://overpass-api.de/api/interpreter", data={"data": QUERY}, headers=UA, timeout=320
        )
        r.raise_for_status()
        RAW.parent.mkdir(parents=True, exist_ok=True)
        RAW.write_bytes(r.content)
    fc = osm2geojson.json2geojson(json.loads(RAW.read_text()))
    g = gpd.GeoDataFrame.from_features(fc["features"], crs="EPSG:4326")
    g = g[g.geometry.type.isin(["Polygon", "MultiPolygon"])].copy()
    g["kind"] = g["tags"].apply(lambda t: (t or {}).get("leisure") or (t or {}).get("landuse") or "other")
    g["parcel_name"] = g["tags"].apply(lambda t: (t or {}).get("name") or "")
    m = g.to_crs(32651)
    g["hectares"] = m.geometry.area / 10_000
    g = g[g.hectares >= MIN_HA].reset_index(drop=True)
    g["pid"] = [f"p{i}" for i in range(len(g))]
    return g[["pid", "kind", "parcel_name", "hectares", "geometry"]]


def measure(parcels):
    """NDVI per parcel per window, plus the WorldCover grass fraction."""
    lc = ee.ImageCollection("ESA/WorldCover/v200").first().select("Map")
    rows = {}
    for i in range(0, len(parcels), BATCH):
        chunk = parcels.iloc[i : i + BATCH]
        feats = [
            ee.Feature(ee.Geometry(r.geometry.__geo_interface__), {"pid": r.pid}) for r in chunk.itertuples()
        ]
        fc = ee.FeatureCollection(feats)
        region = fc.geometry().bounds()
        bands = [masked_ndvi_median(WINDOWS[w], region).rename(w) for w in WINDOWS]
        bands.append(lc.eq(30).rename("grass_frac"))
        out = ee.Image.cat(*bands).reduceRegions(fc, ee.Reducer.mean(), scale=10, tileScale=4).getInfo()
        for f in out["features"]:
            p = f["properties"]
            rows[p["pid"]] = {k: p.get(k) for k in list(WINDOWS) + ["grass_frac"]}
        print(f"  parcels {min(i + BATCH, len(parcels))}/{len(parcels)}", flush=True)
    return rows


def main():
    init()
    parcels = fetch_parcels()
    print(f"green-space parcels at least {MIN_HA} ha: {len(parcels)}")
    vals = measure(parcels)
    parcels["grass_frac"] = parcels.pid.map(lambda p: (vals.get(p) or {}).get("grass_frac"))
    for w in WINDOWS:
        parcels[w] = parcels.pid.map(lambda p, w=w: (vals.get(p) or {}).get(w))

    keep = parcels[(parcels.grass_frac.fillna(0) >= MIN_GRASS) & parcels["base"].notna()].reset_index(
        drop=True
    )
    print(f"parcels WorldCover agrees are at least {int(100 * MIN_GRASS)}% grass: {len(keep)}")
    print("  by kind:", keep.kind.value_counts().to_dict())

    golf = gpd.read_file(ROOT / "data" / "golf_ndvi.geojson")
    golf["osm_id"] = golf["osm_id"].astype(str)
    gm = golf.to_crs(32651)
    pm = keep.to_crs(32651)

    out = []
    for i, gr in gm.iterrows():
        d = pm.geometry.distance(gr.geometry) / 1000.0
        near = pm[d <= NEAR_KM]
        if near.empty:
            continue
        rec = {
            "osm_id": gr.osm_id,
            "name": golf.loc[i, "name"],
            "n_parcels": len(near),
            "n_non_cemetery": int((near.kind != "cemetery").sum()),
        }
        for w in WINDOWS:
            rec[f"parcel_{w}"] = float(near[w].mean())
            nc = near[near.kind != "cemetery"]
            rec[f"parcel_nc_{w}"] = float(nc[w].mean()) if len(nc) else None
        gb = golf.loc[i, "golf_base"]
        if gb is not None and rec.get("parcel_base") is not None:
            rec["parcel_gap_base"] = gb - rec["parcel_base"]
            if rec.get("parcel_nc_base") is not None:
                rec["parcel_gap_base_nc"] = gb - rec["parcel_nc_base"]
        out.append(rec)

    cols = ["osm_id", "name", "n_parcels", "n_non_cemetery"]
    for w in WINDOWS:
        cols += [f"parcel_{w}", f"parcel_nc_{w}"]
    cols += ["parcel_gap_base", "parcel_gap_base_nc"]
    with open(OUT_CSV, "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        wr.writeheader()
        for rec in out:
            wr.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in rec.items()})
    gaps = [r["parcel_gap_base"] for r in out if r.get("parcel_gap_base") is not None]
    print(f"\nwrote {OUT_CSV.relative_to(ROOT)} courses={len(out)}")
    if gaps:
        print(f"  mean course-minus-parcel gap: {sum(gaps) / len(gaps):+.4f}")


if __name__ == "__main__":
    main()
