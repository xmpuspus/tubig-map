"""Dry-season stay-green measurement for every OSM golf polygon.

For each course, compares Sentinel-2 NDVI inside the course against a 30-300 m
control ring around it (other golf land excluded), across three windows:

  base    Feb-Apr 2019-2023 pooled median (normal dry seasons)
  elnino  Feb-Apr 2024 (El Nino drought, the DENR-directive season)
  latest  Feb-Apr 2026

The irrigation signal is (golf - ring) in the El Nino window minus the same gap
in the base window: turf that stays green while its surroundings brown beyond
the normal seasonal gap is being watered. This measures greenness, not liters;
it is an indicator, not a meter reading.

Earth Engine: Cloud Score+ per-pixel mask (cs_cdf >= 0.65), 10 m scale,
batched reduceRegions per leaves-ph gotchas (multi-band image so results key
by band name; osm_id coerced to str on join).
"""

import csv
import sys
from pathlib import Path

import ee
import geopandas as gpd
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).parent))
from _gee_init import init

ROOT = Path(__file__).resolve().parent.parent
GOLF = ROOT / "data" / "golf_courses.geojson"
OUT_CSV = ROOT / "data" / "ndvi_anomaly.csv"
OUT_GJ = ROOT / "data" / "golf_ndvi.geojson"

WINDOWS = {
    "base": [(f"{y}-02-01", f"{y}-04-30") for y in range(2019, 2024)],
    "elnino": [("2024-02-01", "2024-04-30")],
    "latest": [("2026-02-01", "2026-04-30")],
}
CS_THRESH = 0.65
BATCH = 40


def masked_ndvi_median(ranges, region):
    # linkCollection joins on system:index, and merge() rewrites indices, so the
    # Cloud Score+ join must happen per date range BEFORE merging (a post-merge
    # link inner-joins to nothing and silently yields an empty collection).
    csp = ee.ImageCollection("GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED")

    def to_ndvi(img):
        mask = img.select("cs_cdf").gte(CS_THRESH)
        return img.normalizedDifference(["B8", "B4"]).rename("ndvi").updateMask(mask)

    ndvi_cols = []
    for start, end in ranges:
        col = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(region)
            .filterDate(start, end)
            .linkCollection(csp, ["cs_cdf"])
        )
        ndvi_cols.append(col.map(to_ndvi))
    merged = ndvi_cols[0]
    for col in ndvi_cols[1:]:
        merged = merged.merge(col)
    return merged.median()


def build_geometries():
    """Client-side inner polygons and control rings, both keyed by osm_id."""
    gdf = gpd.read_file(GOLF).to_crs(epsg=32651)
    all_golf = unary_union(gdf.geometry.values)
    rows = []
    for _, r in gdf.iterrows():
        inner = r.geometry.buffer(-20)
        if inner.is_empty:
            inner = r.geometry
        ring = r.geometry.buffer(300).difference(r.geometry.buffer(30)).difference(all_golf)
        if ring.is_empty:
            continue
        rows.append((str(r.osm_id), r["name"], inner.simplify(5), ring.simplify(5)))
    back = gpd.GeoSeries([g for _, _, i, ring in rows for g in (i, ring)], crs="EPSG:32651").to_crs(epsg=4326)
    feats = []
    for idx, (osm_id, _name, _, _) in enumerate(rows):
        feats.append(dict(osm_id=osm_id, kind="golf", geom=back.iloc[idx * 2]))
        feats.append(dict(osm_id=osm_id, kind="ring", geom=back.iloc[idx * 2 + 1]))
    return rows, feats


def reduce_batch(feats):
    ee_feats = [
        ee.Feature(ee.Geometry(f["geom"].__geo_interface__), {"osm_id": f["osm_id"], "kind": f["kind"]})
        for f in feats
    ]
    fc = ee.FeatureCollection(ee_feats)
    region = fc.geometry().bounds()
    img = ee.Image.cat(
        masked_ndvi_median(WINDOWS["base"], region).rename("base"),
        masked_ndvi_median(WINDOWS["elnino"], region).rename("elnino"),
        masked_ndvi_median(WINDOWS["latest"], region).rename("latest"),
    )
    out = img.reduceRegions(fc, ee.Reducer.mean(), scale=10, tileScale=4).getInfo()
    rows = {}
    for f in out["features"]:
        p = f["properties"]
        rows[(p["osm_id"], p["kind"])] = {k: p.get(k) for k in ("base", "elnino", "latest")}
    return rows


def main():
    init()
    rows, feats = build_geometries()
    # cluster batches geographically so each composite covers a tight bbox
    feats.sort(key=lambda f: (round(f["geom"].centroid.y, 1), f["geom"].centroid.x))
    results = {}
    for i in range(0, len(feats), BATCH):
        chunk = feats[i : i + BATCH]
        results.update(reduce_batch(chunk))
        print(f"batch {i // BATCH + 1}/{(len(feats) + BATCH - 1) // BATCH} done ({len(results)} rows)")

    table = []
    for osm_id, name, _, _ in rows:
        g = results.get((osm_id, "golf"), {})
        r = results.get((osm_id, "ring"), {})
        if not g or not r or g.get("elnino") is None or r.get("elnino") is None:
            continue
        rec = dict(
            osm_id=osm_id,
            name=name,
            golf_base=g.get("base"),
            golf_elnino=g["elnino"],
            golf_latest=g.get("latest"),
            ring_base=r.get("base"),
            ring_elnino=r["elnino"],
            ring_latest=r.get("latest"),
        )
        if g.get("base") is not None and r.get("base") is not None:
            rec["gap_elnino"] = g["elnino"] - r["elnino"]
            rec["gap_base"] = g["base"] - r["base"]
            rec["irrigation_signal"] = rec["gap_elnino"] - rec["gap_base"]
        table.append(rec)

    cols = [
        "osm_id",
        "name",
        "golf_base",
        "golf_elnino",
        "golf_latest",
        "ring_base",
        "ring_elnino",
        "ring_latest",
        "gap_elnino",
        "gap_base",
        "irrigation_signal",
    ]
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for rec in table:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in rec.items()})

    gdf = gpd.read_file(GOLF)
    gdf["osm_id"] = gdf["osm_id"].astype(str)
    by_id = {rec["osm_id"]: rec for rec in table}
    for col in ("golf_elnino", "ring_elnino", "gap_elnino", "gap_base", "irrigation_signal"):
        gdf[col] = gdf["osm_id"].map(lambda i, col=col: by_id.get(i, {}).get(col))
        gdf[col] = gdf[col].astype(float).round(4)
    gdf.to_file(OUT_GJ, driver="GeoJSON")

    scored = [rec for rec in table if "irrigation_signal" in rec]
    scored.sort(key=lambda rec: rec["irrigation_signal"], reverse=True)
    print(f"\nmeasured={len(table)} with_signal={len(scored)}")
    print("top stay-green signals (El Nino 2024):")
    for rec in scored[:12]:
        print(f"  {rec['irrigation_signal']:+.3f}  {rec['name'] or rec['osm_id']}")


if __name__ == "__main__":
    main()
